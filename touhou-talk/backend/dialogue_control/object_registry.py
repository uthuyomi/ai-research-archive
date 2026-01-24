# persona_core/core/dialogue_control/object_registry.py
"""
object_registry.py
===========================
会話内に登場する「実体（オブジェクト）」を管理するレジストリ。

ここでいう「オブジェクト」とは
--------------------------------
- 実在が確認された人物・存在
- 実体として存在すると会話内で合意されたもの
- 話題(topic)とは異なり、「ある／ない」が重要なもの

例：
- 射命丸文（キャラクター実体）
- 博麗神社（場所）
- 人工知能（概念だが“存在するもの”として扱われる）
- 金属片（※今回のログでは「存在が未確認」だった → ここが重要）

TopicTracker との違い
---------------------
Topic:
- 会話の話題・文脈
- 比喩や推測も含む
- ドリフトしてもよい（制御対象）

Object:
- 「存在する前提で扱ってよいか」が重要
- ユーザー否定が入った瞬間、即座に制約対象になる
- 断定質問・属性付与・過去行動の仮定に直結する

このモジュールの役割
--------------------
- LLMに「存在を勝手に確定させない」
- ユーザーが否定した実体を二度と断定扱いしない
- 「未確認オブジェクト」に対して質問制約をかける
- drift_detector / prompt.constraints と連携する前提

重要な設計方針
--------------
- NLPはやらない（外部で抽出）
- 判断は「状態」で行う
- 推測と実在を厳密に分ける
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


# ============================================================
# Object 状態定義
# ============================================================

class ObjectStatus(str, Enum):
    """
    オブジェクトの存在状態。

    - CONFIRMED:
        存在が確認されている（ユーザー or システム合意）
    - ASSUMED:
        仮定的に存在すると扱われている
        ※断定質問は禁止
    - DENIED:
        ユーザーによって「存在しない／持っていない」と否定された
    - UNKNOWN:
        話題には出たが、存在状態が未整理
    """
    CONFIRMED = "confirmed"
    ASSUMED = "assumed"
    DENIED = "denied"
    UNKNOWN = "unknown"


# ============================================================
# データ構造
# ============================================================

@dataclass
class ObjectEvidence:
    """
    オブジェクト存在に関する根拠ログ。

    - turn_index: 発話ターン
    - role: "user" | "ai" | "system"
    - text: 根拠発話
    - note: 任意メモ
    """
    turn_index: int
    role: str
    text: str
    note: str = ""


@dataclass
class ObjectNode:
    """
    実体オブジェクトノード。

    - object_id:
        内部ID（正規化済み）
    - label:
        表示用名称
    - status:
        ObjectStatus
    - evidence:
        存在・否定の履歴
    - last_updated_turn:
        最終更新ターン
    """
    object_id: str
    label: str
    status: ObjectStatus = ObjectStatus.UNKNOWN
    evidence: List[ObjectEvidence] = field(default_factory=list)
    last_updated_turn: int = 0


# ============================================================
# ObjectRegistry
# ============================================================

class ObjectRegistry:
    """
    会話中の「実体オブジェクト」を一元管理するレジストリ。

    想定利用箇所
    ------------
    - server.py
    - intent_parser（否定・所持判定）
    - drift_detector
    - prompt.constraints（断定質問抑制）

    重要：
    このクラスは「安全装置」。
    多少保守的でも問題ない。
    """

    def __init__(self) -> None:
        self._objects: Dict[str, ObjectNode] = {}
        self._turn_index: int = 0

    # --------------------------------------------------------
    # turn lifecycle
    # --------------------------------------------------------

    def on_turn_start(self, turn_index: int) -> None:
        """
        ターン開始時に呼び出す。
        """
        self._turn_index = turn_index

    # --------------------------------------------------------
    # public accessors
    # --------------------------------------------------------

    def get(self, name: str) -> Optional[ObjectNode]:
        object_id, _ = self._normalize(name)
        return self._objects.get(object_id)

    def list_all(self) -> List[ObjectNode]:
        return list(self._objects.values())

    def list_by_status(self, status: ObjectStatus) -> List[ObjectNode]:
        return [o for o in self._objects.values() if o.status == status]

    # --------------------------------------------------------
    # registration / update
    # --------------------------------------------------------

    def register_assumed(
        self,
        *,
        name: str,
        role: str,
        text: str,
        note: str = "",
    ) -> None:
        """
        「存在するかもしれない」前提で話題に出た場合。

        例：
        - 「その金属片の名前は？」
        - 「持っていると仮定して」

        ASSUMED は非常に危険なので、
        後続で CONFIRMED or DENIED に必ず遷移させる設計を推奨。
        """
        object_id, label = self._normalize(name)

        node = self._objects.get(object_id)
        if node is None:
            node = ObjectNode(
                object_id=object_id,
                label=label,
                status=ObjectStatus.ASSUMED,
                last_updated_turn=self._turn_index,
            )
            self._objects[object_id] = node

        # DENIED を勝手に復活させない
        if node.status == ObjectStatus.DENIED:
            node.evidence.append(
                ObjectEvidence(
                    turn_index=self._turn_index,
                    role=role,
                    text=text,
                    note=f"(assumed-but-denied) {note}".strip(),
                )
            )
            node.last_updated_turn = self._turn_index
            return

        node.status = ObjectStatus.ASSUMED
        node.last_updated_turn = self._turn_index
        node.evidence.append(
            ObjectEvidence(
                turn_index=self._turn_index,
                role=role,
                text=text,
                note=note,
            )
        )

    def confirm(
        self,
        *,
        name: str,
        role: str,
        text: str,
        note: str = "",
    ) -> None:
        """
        オブジェクトの存在が確認された場合。

        例：
        - 「それは持っている」
        - 「確かに存在する」
        """
        object_id, label = self._normalize(name)

        node = self._objects.get(object_id)
        if node is None:
            node = ObjectNode(
                object_id=object_id,
                label=label,
                status=ObjectStatus.CONFIRMED,
                last_updated_turn=self._turn_index,
            )
            self._objects[object_id] = node
        else:
            node.status = ObjectStatus.CONFIRMED
            node.last_updated_turn = self._turn_index

        node.evidence.append(
            ObjectEvidence(
                turn_index=self._turn_index,
                role=role,
                text=text,
                note=note,
            )
        )

    def deny(
        self,
        *,
        name: str,
        role: str,
        text: str,
        reason: str = "",
    ) -> None:
        """
        ユーザーが明確に否定した場合。

        例：
        - 「それは持っていない」
        - 「触れたことも見たこともない」

        これが入ったオブジェクトは
        以後、断定質問・前提化を絶対にしない。
        """
        object_id, label = self._normalize(name)

        node = self._objects.get(object_id)
        if node is None:
            node = ObjectNode(
                object_id=object_id,
                label=label,
                status=ObjectStatus.DENIED,
                last_updated_turn=self._turn_index,
            )
            self._objects[object_id] = node
        else:
            node.status = ObjectStatus.DENIED
            node.last_updated_turn = self._turn_index

        node.evidence.append(
            ObjectEvidence(
                turn_index=self._turn_index,
                role=role,
                text=text,
                note=f"(denied) {reason}".strip(),
            )
        )

    # --------------------------------------------------------
    # safety checks
    # --------------------------------------------------------

    def can_assume_exists(self, name: str) -> bool:
        """
        このオブジェクトを「存在前提」で扱ってよいか？

        False の場合：
        - 名前は？
        - どこで拾った？
        - いつから持っている？

        などの質問は禁止。
        """
        node = self.get(name)
        if node is None:
            return False
        return node.status == ObjectStatus.CONFIRMED

    def is_denied(self, name: str) -> bool:
        node = self.get(name)
        return node is not None and node.status == ObjectStatus.DENIED

    def should_use_cautious_language(self, name: str) -> bool:
        """
        断定せず、仮定・確認口調にすべきか。

        True の場合：
        - 「もし存在するとしたら」
        - 「仮にそういうものがあるなら」
        """
        node = self.get(name)
        if node is None:
            return True
        return node.status in (ObjectStatus.ASSUMED, ObjectStatus.UNKNOWN)

    # --------------------------------------------------------
    # normalization
    # --------------------------------------------------------

    def _normalize(self, raw: str) -> tuple[str, str]:
        """
        オブジェクト名正規化。

        - 大文字小文字の揺れ吸収
        - 表示ラベルは保持
        """
        label = (raw or "").strip()
        object_id = label.lower()
        if not object_id:
            object_id = "_empty_"
            label = "_empty_"
        return object_id, label
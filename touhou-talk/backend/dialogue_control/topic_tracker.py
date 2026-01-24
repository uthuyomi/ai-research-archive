# persona_core/core/dialogue_control/topic_tracker.py
"""
topic_tracker.py
===========================
会話の「話題」を構造として追跡するモジュール。

狙い
----
LLM に「会話の一貫性」を丸投げすると、長いやり取りで以下が起きやすい：

- 直前まで存在していなかった物体・設定を「既にある前提」で質問する
- ユーザーが否定した内容を、別の言い回しで復活させる
- 途中から詩的・飛躍的な連想が混ざり、発話の根拠が不明になる（ドリフト）

TopicTracker は、こうした「話題の暴走」を抑えるために
"話題の状態" を明示的に管理する。

ここでやること（LLMにやらせない）
--------------------------------
- いまの主話題は何か
- どの話題が派生したか
- その話題は「確定」か「仮」か「否定済み」か
- ユーザーが話題を否定・訂正した履歴の保持
- 「話題の根拠（どの発話で生えたか）」の保持

ここでやらないこと
------------------
- 高度なNLP（固有表現抽出の精度追求など）
- LLMによる自動抽出（ここは構造レイヤであるべき）
- 意味理解の断定

入力は「抽出済みトピック候補」を想定する。
（抽出器は後で作ってもいいし、暫定はルールでよい）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


# ============================================================
# 話題の状態（重要：ここが暴走抑制の核）
# ============================================================

class TopicStatus(str, Enum):
    """
    Topic の確からしさ / 扱い方の状態。

    - ACTIVE:
        いま主に話している話題（フォーカス中）
    - AVAILABLE:
        直近に出た話題。フォーカス外だが参照可能
    - SPECULATIVE:
        推測・比喩・仮定・可能性として出た話題
        ※確定した実体のように扱ってはいけない
    - REJECTED:
        ユーザーが否定・訂正・違和感指摘をした話題
        ※基本は再利用禁止（復活させる場合は確認が必要）
    - DORMANT:
        しばらく触れていない話題（ログとして残る）
    """
    ACTIVE = "active"
    AVAILABLE = "available"
    SPECULATIVE = "speculative"
    REJECTED = "rejected"
    DORMANT = "dormant"


# ============================================================
# データ構造
# ============================================================

@dataclass
class TopicEvidence:
    """
    話題の根拠（どこで出たか）を保存する。

    - turn_index: 会話ターン番号（0-based）
    - role: "user" or "ai"
    - text: 根拠となった発話（全体じゃなくても良いが、簡易保存）
    - note: 任意のメモ（抽出理由やルール）
    """
    turn_index: int
    role: str
    text: str
    note: str = ""


@dataclass
class TopicNode:
    """
    話題ノード。

    - topic_id:
        内部ID（正規化済み文字列が基本）
    - label:
        表示用（オリジナル表現）
    - status:
        TopicStatus
    - parent_id:
        派生元話題（ツリー構造）
    - children_ids:
        派生話題
    - evidence:
        出現根拠
    - last_touched_turn:
        最終参照ターン（ドーマント判定に使う）
    - rejected_reason:
        REJECTED になった理由（ユーザー否定など）
    """
    topic_id: str
    label: str
    status: TopicStatus = TopicStatus.AVAILABLE
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    evidence: List[TopicEvidence] = field(default_factory=list)
    last_touched_turn: int = 0
    rejected_reason: str = ""


# ============================================================
# TopicTracker
# ============================================================

class TopicTracker:
    """
    会話中の Topic を管理する中核。

    想定運用
    --------
    server.py 側でターンごとに以下を呼ぶ：

      1) tracker.on_turn_start(turn_index)
      2) tracker.register_candidates(...候補...)   # ここは暫定ルールでも良い
      3) tracker.apply_user_corrections(...否定/訂正シグナル...)  # intent/stateと連携
      4) tracker.finalize_focus(...)

    ここでは「候補抽出」は外部に置く前提だが、
    最低限動かせるようにルールベースの簡易補助も用意する。
    """

    def __init__(
        self,
        *,
        max_topics: int = 64,
        dormant_after_turns: int = 8,
        allow_revival: bool = False,
    ):
        """
        Args:
            max_topics:
                保持する話題数上限（古いものからdormant化/削除判断に使う）
            dormant_after_turns:
                最終タッチからこのターン数以上で DORMANT 扱い
            allow_revival:
                REJECTED を自動復活させるか（基本False推奨）
        """
        self.max_topics = max_topics
        self.dormant_after_turns = dormant_after_turns
        self.allow_revival = allow_revival

        self._turn_index: int = 0
        self._topics: Dict[str, TopicNode] = {}

        # 現在フォーカス中の話題ID（主話題）
        self._active_topic_id: Optional[str] = None

        # ターンごとのフォーカス履歴
        self._focus_history: List[Optional[str]] = []

    # ------------------------------------------------------------
    # public getters
    # ------------------------------------------------------------

    @property
    def turn_index(self) -> int:
        return self._turn_index

    @property
    def active_topic_id(self) -> Optional[str]:
        return self._active_topic_id

    def get_active_topic(self) -> Optional[TopicNode]:
        if self._active_topic_id is None:
            return None
        return self._topics.get(self._active_topic_id)

    def get_topic(self, topic_id: str) -> Optional[TopicNode]:
        return self._topics.get(topic_id)

    def list_topics(self) -> List[TopicNode]:
        # 安定した順序（出現順っぽく）にしたいなら last_touched_turn などでソート
        return sorted(self._topics.values(), key=lambda t: t.last_touched_turn, reverse=True)

    # ------------------------------------------------------------
    # turn lifecycle
    # ------------------------------------------------------------

    def on_turn_start(self, turn_index: int) -> None:
        """
        ターン開始時に呼ぶ。
        - turn_index を更新
        - dormant 判定を適用
        """
        self._turn_index = turn_index
        self._apply_dormant_rules()
        self._focus_history.append(self._active_topic_id)

    # ------------------------------------------------------------
    # topic registration
    # ------------------------------------------------------------

    def register_candidates(
        self,
        *,
        role: str,
        text: str,
        candidates: List[str],
        speculative: bool = False,
        parent_hint: Optional[str] = None,
        note: str = "",
    ) -> None:
        """
        話題候補を登録する。

        Args:
            role: "user" or "ai"
            text: 発話テキスト（根拠として保存）
            candidates: 話題候補（文字列）
            speculative: Trueなら SPECULATIVE として登録
            parent_hint: 派生元トピック（無ければactive_topic）
            note: evidenceに残すメモ
        """
        parent_id = parent_hint or self._active_topic_id

        for raw in candidates:
            topic_id, label = self._normalize_topic(raw)

            # REJECTED が既にある場合は基本触らない（復活事故防止）
            existing = self._topics.get(topic_id)
            if existing and existing.status == TopicStatus.REJECTED and not self.allow_revival:
                # 根拠だけ積んで「また出た」記録は残す（検出器が後で使える）
                existing.evidence.append(
                    TopicEvidence(
                        turn_index=self._turn_index,
                        role=role,
                        text=text,
                        note=f"(rejected-topic-mentioned) {note}".strip(),
                    )
                )
                existing.last_touched_turn = self._turn_index
                continue

            if topic_id not in self._topics:
                # 新規作成
                status = TopicStatus.SPECULATIVE if speculative else TopicStatus.AVAILABLE
                node = TopicNode(
                    topic_id=topic_id,
                    label=label,
                    status=status,
                    parent_id=parent_id,
                    last_touched_turn=self._turn_index,
                )
                node.evidence.append(
                    TopicEvidence(
                        turn_index=self._turn_index,
                        role=role,
                        text=text,
                        note=note,
                    )
                )
                self._topics[topic_id] = node

                # 親子接続
                if parent_id and parent_id in self._topics:
                    parent = self._topics[parent_id]
                    if topic_id not in parent.children_ids:
                        parent.children_ids.append(topic_id)

            else:
                # 既存更新
                node = self._topics[topic_id]
                node.last_touched_turn = self._turn_index
                node.evidence.append(
                    TopicEvidence(
                        turn_index=self._turn_index,
                        role=role,
                        text=text,
                        note=note,
                    )
                )

                # speculative を優先して下げる（確定を勝手に外さない）
                if speculative and node.status not in (TopicStatus.REJECTED, TopicStatus.ACTIVE):
                    node.status = TopicStatus.SPECULATIVE

                # 親子接続（parent_idが変わっても上書きは基本しない。最初の根を尊重）
                if node.parent_id is None and parent_id is not None:
                    node.parent_id = parent_id
                    if parent_id in self._topics:
                        parent = self._topics[parent_id]
                        if topic_id not in parent.children_ids:
                            parent.children_ids.append(topic_id)

        self._enforce_max_topics()

    # ------------------------------------------------------------
    # user corrections / rejection
    # ------------------------------------------------------------

    def reject_topic(
        self,
        *,
        topic: str,
        reason: str,
        role: str = "user",
        text: str = "",
        note: str = "",
    ) -> None:
        """
        ユーザーによって否定・訂正された話題を REJECTED にする。

        例：
        - 「それ持ってない」
        - 「その聞き方おかしい」
        - 「話が飛んでる」

        重要：
        REJECTED は再利用禁止が基本。
        """
        topic_id, label = self._normalize_topic(topic)

        node = self._topics.get(topic_id)
        if node is None:
            node = TopicNode(
                topic_id=topic_id,
                label=label,
                status=TopicStatus.REJECTED,
                last_touched_turn=self._turn_index,
                rejected_reason=reason,
            )
            node.evidence.append(
                TopicEvidence(
                    turn_index=self._turn_index,
                    role=role,
                    text=text,
                    note=f"(rejected-created) {note}".strip(),
                )
            )
            self._topics[topic_id] = node
        else:
            node.status = TopicStatus.REJECTED
            node.rejected_reason = reason
            node.last_touched_turn = self._turn_index
            node.evidence.append(
                TopicEvidence(
                    turn_index=self._turn_index,
                    role=role,
                    text=text,
                    note=f"(rejected) {note}".strip(),
                )
            )

        # active が rejected になったらフォーカス解除（安全）
        if self._active_topic_id == topic_id:
            self._active_topic_id = None

        self._enforce_max_topics()

    def apply_user_corrections(
        self,
        *,
        user_text: str,
        correction_signals: List[Tuple[str, str]],
    ) -> None:
        """
        ユーザー発言から「否定/訂正」を適用するためのユーティリティ。

        Args:
            user_text:
                ユーザー発言全文
            correction_signals:
                [(topic, reason), ...] の形で外部が渡す。
                ※ここで自然言語解析はしない（外部でルール化する）
        """
        for topic, reason in correction_signals:
            self.reject_topic(topic=topic, reason=reason, role="user", text=user_text)

    # ------------------------------------------------------------
    # focus control
    # ------------------------------------------------------------

    def set_focus(self, topic: str) -> None:
        """
        主話題（ACTIVE）を設定する。

        注意：
        - REJECTED は原則フォーカス不可
        - SPECULATIVE はフォーカスできるが、後続の制約で「断定質問禁止」になるべき
        """
        topic_id, label = self._normalize_topic(topic)

        node = self._topics.get(topic_id)
        if node is None:
            # 未登録の話題をいきなり ACTIVE にするのは危険なので
            # AVAILABLE として登録し、それをフォーカスにする。
            node = TopicNode(
                topic_id=topic_id,
                label=label,
                status=TopicStatus.AVAILABLE,
                last_touched_turn=self._turn_index,
            )
            node.evidence.append(
                TopicEvidence(
                    turn_index=self._turn_index,
                    role="system",
                    text="",
                    note="(focus-created)",
                )
            )
            self._topics[topic_id] = node

        # rejected をフォーカスにしない
        if node.status == TopicStatus.REJECTED and not self.allow_revival:
            self._active_topic_id = None
            return

        # 以前の active を available に落とす
        if self._active_topic_id and self._active_topic_id in self._topics:
            prev = self._topics[self._active_topic_id]
            if prev.status == TopicStatus.ACTIVE:
                # rejected 以外に落とす
                prev.status = TopicStatus.AVAILABLE

        # 新しい active
        node.status = TopicStatus.ACTIVE
        node.last_touched_turn = self._turn_index
        self._active_topic_id = topic_id

        self._enforce_max_topics()

    def finalize_focus(
        self,
        *,
        suggested_focus: Optional[str],
        fallback_to_recent: bool = True,
    ) -> Optional[str]:
        """
        ターン末尾で「このターンのフォーカス」を確定させる。

        - suggested_focus があればそれを優先
        - なければ最近触った AVAILABLE/SPECULATIVE のうち最上位を採用
        - それもなければ None

        Returns:
            active_topic_id
        """
        if suggested_focus:
            self.set_focus(suggested_focus)
            return self._active_topic_id

        if fallback_to_recent:
            candidates = [
                t for t in self._topics.values()
                if t.status in (TopicStatus.AVAILABLE, TopicStatus.SPECULATIVE, TopicStatus.ACTIVE)
            ]
            if candidates:
                candidates.sort(key=lambda t: t.last_touched_turn, reverse=True)
                self.set_focus(candidates[0].topic_id)
                return self._active_topic_id

        return self._active_topic_id

    # ------------------------------------------------------------
    # safety helpers
    # ------------------------------------------------------------

    def is_topic_confirmed(self, topic: str) -> bool:
        """
        話題が「確定扱い可能」かどうか。

        ここでは簡易に：
        - SPECULATIVE / REJECTED は confirmed ではない
        - ACTIVE / AVAILABLE は confirmed
        とする。

        ※将来、object_registry と接続して「実体確認済み」判定に差し替える。
        """
        topic_id, _ = self._normalize_topic(topic)
        node = self._topics.get(topic_id)
        if node is None:
            return False
        return node.status in (TopicStatus.ACTIVE, TopicStatus.AVAILABLE)

    def should_avoid_assertive_questions(self) -> bool:
        """
        現在フォーカスの話題が SPECULATIVE の場合など、
        「断定質問（例：それの名前は？ どこで拾った？）を避けるべき」か。

        この戻り値は、prompt/constraints で使用する想定。
        """
        active = self.get_active_topic()
        if active is None:
            return False
        return active.status == TopicStatus.SPECULATIVE

    def get_rejected_topics(self) -> List[TopicNode]:
        return [t for t in self._topics.values() if t.status == TopicStatus.REJECTED]

    # ------------------------------------------------------------
    # internal: normalization
    # ------------------------------------------------------------

    def _normalize_topic(self, raw: str) -> Tuple[str, str]:
        """
        話題の正規化。

        目的：
        - "人工知能" と "AI" を同一扱いにしたい、などを将来やるための入口。
        現段階では:
        - 前後空白除去
        - 全角/半角などは触らない（不用意な破壊を避ける）
        - 小文字化（英字のみ）
        """
        label = (raw or "").strip()
        topic_id = label.lower()
        # 空は無視したいが、呼び出し側で候補を弾く想定。ここは保険。
        if not topic_id:
            topic_id = "_empty_"
            label = "_empty_"
        return topic_id, label

    # ------------------------------------------------------------
    # internal: dormant / max enforcement
    # ------------------------------------------------------------

    def _apply_dormant_rules(self) -> None:
        """
        一定ターン触れていない話題を DORMANT に落とす。
        ACTIVE は落とさない。
        REJECTED もそのまま。
        """
        for node in self._topics.values():
            if node.status in (TopicStatus.ACTIVE, TopicStatus.REJECTED):
                continue

            turns_since = self._turn_index - node.last_touched_turn
            if turns_since >= self.dormant_after_turns:
                node.status = TopicStatus.DORMANT

    def _enforce_max_topics(self) -> None:
        """
        話題数が増えすぎた場合の整理。
        - REJECTED は残す（再発防止のため）
        - ACTIVE は残す
        - それ以外は古いものから削る
        """
        if len(self._topics) <= self.max_topics:
            return

        # 保護対象
        protected = set()
        if self._active_topic_id:
            protected.add(self._active_topic_id)
        for t in self._topics.values():
            if t.status == TopicStatus.REJECTED:
                protected.add(t.topic_id)

        # 削除候補
        candidates = [
            t for t in self._topics.values()
            if t.topic_id not in protected
        ]
        # 古い順
        candidates.sort(key=lambda t: t.last_touched_turn)

        while len(self._topics) > self.max_topics and candidates:
            victim = candidates.pop(0)
            # 親のchildrenからも外す（整合性）
            if victim.parent_id and victim.parent_id in self._topics:
                parent = self._topics[victim.parent_id]
                if victim.topic_id in parent.children_ids:
                    parent.children_ids.remove(victim.topic_id)

            # 子の親参照を外す（必要なら将来「孤児扱い」もできる）
            for cid in victim.children_ids:
                if cid in self._topics:
                    self._topics[cid].parent_id = None

            del self._topics[victim.topic_id]

    # ------------------------------------------------------------
    # optional helper: very simple extractor (temporary)
    # ------------------------------------------------------------

    @staticmethod
    def naive_extract_topics(text: str) -> List[str]:
        """
        暫定の超単純抽出（本番では別モジュールにする）。

        方針：
        - 日本語の形態素解析などはしない
        - 代わりに「引用符」「カギ括弧」や明確な名詞フレーズっぽいものだけ拾う
        - 使うなら server.py で "雑に候補を作る" 用

        例：
        - 『人工知能』 -> 人工知能
        - 「外貨」 -> 外貨

        ※精度は低い。暴走抑止の最低限用途。
        """
        if not text:
            return []

        topics: List[str] = []
        pairs = [("「", "」"), ("『", "』"), ("（", "）")]
        for l, r in pairs:
            start = 0
            while True:
                i = text.find(l, start)
                if i < 0:
                    break
                j = text.find(r, i + 1)
                if j < 0:
                    break
                inner = text[i + 1 : j].strip()
                if inner:
                    topics.append(inner)
                start = j + 1

        # 重複除去しつつ順序保持
        seen = set()
        uniq: List[str] = []
        for t in topics:
            key = t.strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            uniq.append(t)

        return uniq
# persona_core/memory/long_term.py
"""
long_term.py
===========================
人格OSにおける「長期記憶（Long-term Memory）」の受け皿。

役割：
- salience によって「重要」と判断された会話断片のみを受け取る
- SessionMemory や PromptBuilder とは独立
- ここでは一切「参照」しない（保存専用）

思想：
- 覚えすぎない
- 解釈しない
- 使わない
- ただ「残すに値するか」を通過したものだけを保持する

この段階では：
- クラスタリングしない
- 要約しない
- 感情付与しない
- 再利用しない

※ 将来：
  - Retrieval
  - Value / Trait Drift
  - Identity Continuity
  の入力になることを想定
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from memory.salience import SalienceResult


# =========================
# 記憶単位
# =========================

@dataclass(frozen=True)
class LongTermMemoryItem:
    """
    長期記憶の最小単位。

    ここでは「意味」や「解釈」を持たせない。
    あくまで「その時そう言われた」という事実ログ。
    """
    user_text: str
    ai_text: str
    salience_score: float

    # メタ情報（後段で使う可能性があるもの）
    created_at: datetime = field(default_factory=datetime.utcnow)
    tags: tuple[str, ...] = ()   # まだ使わないが、後で拡張可能


# =========================
# Long-term Memory Container
# =========================

class LongTermMemory:
    """
    長期記憶のコンテナ。

    - salience を通過したものだけを保持
    - 明示的に add() されたもの以外は入らない
    - ここから勝手に参照されることはない
    """

    def __init__(
        self,
        *,
        salience_threshold: float = 0.5,
        max_items: int = 500,
    ) -> None:
        """
        salience_threshold:
            これ以上の salience.score を持つ発言のみ保存対象。

        max_items:
            保存上限。
            超えた場合は古いものから捨てる（LRU ではない）。
        """
        self._salience_threshold = float(salience_threshold)
        self._max_items = int(max_items)

        # 実体は単純な配列
        self._items: List[LongTermMemoryItem] = []

    # =========================
    # public API
    # =========================

    def add(
        self,
        *,
        user_text: str,
        ai_text: str,
        salience: SalienceResult,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """
        長期記憶に追加する。

        戻り値：
        - True  : 保存された
        - False : salience が閾値未満で破棄された

        ※ 判断は salience のみ。
           内容・感情・文脈は一切見ない。
        """

        # salience による一次フィルタ
        if salience.score < self._salience_threshold:
            return False

        item = LongTermMemoryItem(
            user_text=user_text,
            ai_text=ai_text,
            salience_score=salience.score,
            tags=tuple(tags) if tags else (),
        )

        self._items.append(item)

        # 上限超過時は古いものから捨てる
        if len(self._items) > self._max_items:
            overflow = len(self._items) - self._max_items
            if overflow > 0:
                self._items = self._items[overflow:]

        return True

    # =========================
    # read-only helpers
    # =========================

    def count(self) -> int:
        """
        現在保持している長期記憶数。
        """
        return len(self._items)

    def all_items(self) -> List[LongTermMemoryItem]:
        """
        全件取得。

        ※ 現フェーズではデバッグ・確認用途のみ。
           server / builder から直接使う想定はしない。
        """
        return list(self._items)

    def clear(self) -> None:
        """
        全消去。

        テスト・セッションリセット用。
        """
        self._items.clear()
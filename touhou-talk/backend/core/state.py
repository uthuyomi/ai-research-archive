# persona_core/core/state.py
"""
state.py
---------------------------------
人格OSにおける「現在状態（State）」を管理するモジュール。

ここで扱う State は感情そのものではない。
「会話の文脈上、今どの距離・深さ・フェーズにいるか」
という *制御用の状態* を表す。

重要：
- LLMに直接渡すための感情表現ではない
- Prompt生成・Policy判断・Memory制御のための中間構造

今回追加（会話モード）：
- 「話変わる」等の明示的切替を “一時フラグ” ではなく
  永続する状態遷移（mode）として保持するための概念。
- ここでは state が mode を保持するだけ（検出・切替や Memory 分離は別レイヤの責務）。
"""

from dataclasses import dataclass
from enum import Enum


# =========================
# Enum 定義
# =========================

class Mood(str, Enum):
    """
    会話の雰囲気レベル。
    感情ではなく「空気感・張り詰め度」に近い。
    """
    CALM = "calm"          # 落ち着いている（通常）
    PLAYFUL = "playful"    # 軽い冗談・柔らかめ
    SERIOUS = "serious"    # 真面目・集中
    TENSE = "tense"        # 緊張・警戒・異変対応


class Distance(str, Enum):
    """
    ユーザーとの心理的距離感。

    ※ これは「好感度」ではない。
       キャラが踏み込みすぎないための安全装置。
    """
    FAR = "far"            # 初対面・様子見
    NORMAL = "normal"      # 通常会話
    CLOSE = "close"        # 信頼がある状態


class Phase(str, Enum):
    """
    会話の目的フェーズ。

    ここを誤ると
    - 雑談なのに説教
    - 相談なのに軽口
    という事故が起きる。
    """
    IDLE = "idle"              # 何も起きていない状態
    CHAT = "chat"              # 雑談・通常会話
    CARE = "care"              # 気遣い・フォロー
    EXPLANATION = "explanation"  # 説明・解説モード


class ConversationMode(str, Enum):
    """
    会話の参照文脈を切り替えるためのモード。

    Phase が「目的（解説/雑談/ケア）」なら、
    Mode は「どの文脈バッファを参照して会話を継続するか」を決める軸。

    - TECHNICAL: 技術・設計・実装の対話（前提の連続性が重要）
    - CASUAL: 雑談・キャラ会話（技術文脈を混ぜない）
    """
    TECHNICAL = "technical"
    CASUAL = "casual"


# =========================
# State 本体
# =========================

@dataclass
class ConversationState:
    """
    人格OSが保持する現在の会話状態。

    この State は「現在値」だけを持つ。
    履歴・記憶は memory 層の責務。

    conversation_mode:
    - 明示的切替が入ったら以後継続する状態（自動では戻さない）
    - どの memory / prompt 文脈を参照するかのスイッチに使う想定
    """
    mood: Mood = Mood.CALM
    distance: Distance = Distance.NORMAL
    depth: int = 0
    phase: Phase = Phase.CHAT

    # 追加：会話モード（文脈参照の継続軸）
    conversation_mode: ConversationMode = ConversationMode.TECHNICAL

    # -------------------------
    # 内部安全補正
    # -------------------------

    def clamp(self) -> None:
        """
        状態の安全補正。

        depth や enum の破綻が
        そのまま Prompt に漏れるのを防ぐ。
        """
        if self.depth < 0:
            self.depth = 0
        elif self.depth > 3:
            # 深掘りしすぎると人格が壊れやすいため上限を設ける
            self.depth = 3

        # enum は dataclass + Enum で基本破綻しないが、
        # 何か外部から上書きされた場合の最低限の保険
        if not isinstance(self.mood, Mood):
            try:
                self.mood = Mood(str(self.mood))
            except Exception:
                self.mood = Mood.CALM

        if not isinstance(self.distance, Distance):
            try:
                self.distance = Distance(str(self.distance))
            except Exception:
                self.distance = Distance.NORMAL

        if not isinstance(self.phase, Phase):
            try:
                self.phase = Phase(str(self.phase))
            except Exception:
                self.phase = Phase.CHAT

        if not isinstance(self.conversation_mode, ConversationMode):
            try:
                self.conversation_mode = ConversationMode(str(self.conversation_mode))
            except Exception:
                self.conversation_mode = ConversationMode.TECHNICAL

    # =========================
    # 状態更新ロジック
    # =========================

    def on_user_input(
        self,
        *,
        is_emotional: bool,
        is_metaphor: bool,
        is_question: bool,
        is_casual: bool,
    ) -> None:
        """
        ユーザー入力を受け取った際の状態変化。

        ※ intent.py の解析結果をそのまま渡す想定。
        ※ conversation_mode の切替は別レイヤ（turn controller 等）が行う想定。
           ここでは mood/phase/depth の “制御用状態” のみ更新する。
        """

        # -------------------------
        # 深さ（話題の踏み込み度）
        # -------------------------
        if is_emotional:
            # 感情的入力は深さを一段階上げる
            self.depth += 1
        else:
            # 感情が伴わない雑談は徐々に浅く戻す
            self.depth = max(self.depth - 1, 0)

        # -------------------------
        # フェーズ制御
        # -------------------------
        if is_emotional and not is_metaphor:
            # 比喩ではなく本気の感情なら CARE
            self.phase = Phase.CARE
        elif is_question:
            # 純粋な質問は説明フェーズ
            self.phase = Phase.EXPLANATION
        else:
            self.phase = Phase.CHAT

        # -------------------------
        # ムード制御
        # -------------------------
        if is_casual:
            self.mood = Mood.PLAYFUL
        elif is_emotional:
            self.mood = Mood.SERIOUS
        else:
            self.mood = Mood.CALM

        self.clamp()

    def on_ai_response(self) -> None:
        """
        AIが応答した後の状態調整。

        「踏み込みっぱなし」「支援モード固定」
        にならないための自己復帰処理。

        ※ conversation_mode は “会話の継続軸” なのでここでは変更しない。
        """

        # CAREフェーズは引きずらない
        if self.phase == Phase.CARE:
            self.phase = Phase.CHAT

        # 深さは少しずつ戻す（即ゼロにはしない）
        if self.depth > 0:
            self.depth -= 1

        # 緊張状態は一度で解除
        if self.mood == Mood.TENSE:
            self.mood = Mood.CALM

        self.clamp()

    # =========================
    # デバッグ・可視化
    # =========================

    def debug(self) -> str:
        """
        ログ・検証用の状態表示。
        """
        return (
            f"[State] "
            f"mode={self.conversation_mode.value}, "
            f"mood={self.mood.value}, "
            f"distance={self.distance.value}, "
            f"depth={self.depth}, "
            f"phase={self.phase.value}"
        )
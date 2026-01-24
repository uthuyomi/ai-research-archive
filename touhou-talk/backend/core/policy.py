"""
policy.py
---------------------------------
Intent とキャラ定義を元に、
「この発言でどこまで踏み込んでいいか」を決定するモジュール。

ここは人格OSのブレーキ。
感情ケア・説教・メタ発言の暴走を防ぐ。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional

from .intent import Intent


# =========================
# ポリシーモード定義（行動制御）
# =========================

PolicyMode = Literal[
    "CHAT",        # 通常会話
    "CARE_LIGHT",  # 軽い気遣い（深入りしない）
    "CARE_STRICT", # 強制的に抑制（医者・看護師禁止）
    "ANSWER_ONLY", # 質問にだけ答える
]


# =========================
# Temporal Axis（軽量）
# =========================
# intent.py 側に同名の定義がある前提だが、
# ここは「依存を増やさず」「壊さず」「受け取れたら効かせる」ための最小定義に留める。
TemporalAxis = Literal[
    "past",
    "present",
    "future",
    "if",
    "unknown",
]


def _extract_temporal_axis(intent_like: Any) -> TemporalAxis:
    """
    Intent / IntentResult のどちらが来ても受け取れるようにする。

    - server.py が Intent（boolean集合）を渡してくる場合：temporal_axis は無い → unknown
    - どこかで IntentResult を渡すようになった場合：temporal_axis を拾う → if / past / future 等が効く

    ※ ここでは “判定” はしない（解析は intent.py 側の責務）
       ただ属性があれば拾うだけ。
    """
    axis = getattr(intent_like, "temporal_axis", None)
    if axis in ("past", "present", "future", "if", "unknown"):
        return axis  # type: ignore[return-value]
    return "unknown"


# =========================
# PolicyDecision（行動制御）
# =========================

@dataclass(frozen=True)
class PolicyDecision:
    """
    LLM に渡す前の「行動制御判断」。

    ・どういうモードで話すか
    ・質問／助言を許可するか
    ・（任意）説明（メタ）を許可するか
    ・暴走防止の文字数制限

    NOTE:
    - allow_explanation は PromptBuilder 側が getattr で参照する前提のため
      追加しても互換性を壊さない（むしろ明示化できる）。
    """
    mode: PolicyMode
    allow_questions: bool
    allow_advice: bool
    max_response_length: int

    # PromptBuilder / server.py 側は getattr(...) で見る想定
    allow_explanation: bool = True


# =========================
# PolicyResult（禁止ルール / builder 用）
# =========================

@dataclass(frozen=True)
class PolicyResult:
    """
    PromptBuilder に渡すための
    「絶対に破ってはいけない制約」。

    これは人格・会話状態に関係なく適用される。
    """
    block_explanation: bool = True              # AI/システム説明禁止
    block_modern_world: bool = True             # 現代技術・外界説明禁止
    block_over_guidance: bool = True            # 説教・人生指導禁止
    block_psychological_diagnosis: bool = True  # 診断・決めつけ禁止


# =========================
# キャラごとの性格係数
# =========================

CHARACTER_POLICY_PROFILE = {
    "reimu": {
        # 霊夢は達観しすぎない・深入りしない
        "care_tolerance": 0.3,
        "advice_tolerance": 0.4,
        "talkativeness": 0.5,
    },
    "youmu": {
        # 妖夢は真面目すぎるので抑制強め
        "care_tolerance": 0.15,
        "advice_tolerance": 0.2,
        "talkativeness": 0.45,
    },
    # 他キャラは後で追加
}


# =========================
# Policy Engine
# =========================

class PolicyEngine:
    """
    Policy の中核エンジン。

    - decide(): 行動制御（会話の仕方）
    - evaluate(): 禁止ルール（builder 用）
    """

    @classmethod
    def decide(
        cls,
        character_id: str,
        intent: Intent,
        *,
        temporal_axis: Optional[TemporalAxis] = None,
        boundary_level: Optional[str] = None,
    ) -> PolicyDecision:
        """
        Intent + キャラ性格から
        「今どう振る舞うか」を決定する。
        """

        # -------------------------
        # キャラプロファイル（安全デフォルト）
        # -------------------------
        profile = CHARACTER_POLICY_PROFILE.get(character_id)
        if profile is None:
            profile = {
                "care_tolerance": 0.2,
                "advice_tolerance": 0.2,
                "talkativeness": 0.4,
            }

        care_tol = float(profile.get("care_tolerance", 0.2))
        advice_tol = float(profile.get("advice_tolerance", 0.2))
        talk = float(profile.get("talkativeness", 0.4))

        # -------------------------
        # temporal_axis 決定
        # -------------------------
        if temporal_axis in ("past", "present", "future", "if", "unknown"):
            axis: TemporalAxis = temporal_axis
        else:
            axis = _extract_temporal_axis(intent)

        # -------------------------
        # 時間軸ブレーキ（最優先）
        # -------------------------
        if axis == "if":
            if intent.is_emotional or intent.is_metaphor:
                return PolicyDecision(
                    mode="CARE_STRICT",
                    allow_questions=False,
                    allow_advice=False,
                    max_response_length=max(60, int(150 * talk)),
                )

            return PolicyDecision(
                mode="ANSWER_ONLY" if intent.is_question else "CHAT",
                allow_questions=False,
                allow_advice=False,
                max_response_length=max(60, int(180 * talk)),
            )

        if axis == "future":
            future_max = max(60, int(210 * talk))

            if intent.is_emotional and intent.is_metaphor:
                return PolicyDecision(
                    mode="CARE_STRICT",
                    allow_questions=False,
                    allow_advice=False,
                    max_response_length=max(60, int(160 * talk)),
                )

            if intent.is_emotional:
                return PolicyDecision(
                    mode="CARE_LIGHT",
                    allow_questions=care_tol > 0.25,
                    allow_advice=False,
                    max_response_length=future_max,
                )

            if intent.is_question:
                return PolicyDecision(
                    mode="ANSWER_ONLY",
                    allow_questions=False,
                    allow_advice=False,
                    max_response_length=max(60, int(220 * talk)),
                )

            if intent.is_casual:
                return PolicyDecision(
                    mode="CHAT",
                    allow_questions=True,
                    allow_advice=False,
                    max_response_length=max(60, int(240 * talk)),
                )

            return PolicyDecision(
                mode="CHAT",
                allow_questions=True,
                allow_advice=False,
                max_response_length=future_max,
            )

        # -------------------------
        # 既存ロジック（present / past / unknown）
        # -------------------------

        if intent.is_emotional and intent.is_metaphor:
            return PolicyDecision(
                mode="CARE_STRICT",
                allow_questions=False,
                allow_advice=False,
                max_response_length=max(60, int(160 * talk)),
            )

        if intent.is_emotional:
            return PolicyDecision(
                mode="CARE_LIGHT",
                allow_questions=care_tol > 0.25,
                allow_advice=advice_tol > 0.3,
                max_response_length=max(60, int(220 * talk)),
            )

        if intent.is_question:
            return PolicyDecision(
                mode="ANSWER_ONLY",
                allow_questions=False,
                allow_advice=False,
                max_response_length=max(60, int(240 * talk)),
            )

        if intent.is_casual:
            return PolicyDecision(
                mode="CHAT",
                allow_questions=True,
                allow_advice=False,
                max_response_length=max(60, int(260 * talk)),
            )

        return PolicyDecision(
            mode="CHAT",
            allow_questions=True,
            allow_advice=advice_tol > 0.35,
            max_response_length=max(60, int(240 * talk)),
        )

    @staticmethod
    def evaluate() -> PolicyResult:
        """
        PromptBuilder 用の
        静的ポリシー制約を返す。
        """
        return PolicyResult()
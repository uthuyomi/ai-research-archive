# prompt/group_decision.py
"""
group_decision.py
===========================
グループチャットにおいて
「この場で誰が喋るか」を決めるための Decision Prompt 専用モジュール。

役割
----
- GroupState と user input を受け取る
- LLM に判断させるための prompt を組み立てる
- 出力は JSON のみを強制する

やらないこと
--------------
- 発話生成
- 記憶操作
- 意味解析
"""

from __future__ import annotations

from typing import Dict
from core.group_state import GroupState


# ==================================================
# Prompt Builder
# ==================================================

def build_group_decision_prompt(
    *,
    group_state: GroupState,
    user_input: str | None,
) -> Dict[str, str]:
    """
    グループ発話決定用の prompt を生成する。
    """

    # -------------------------
    # 安全な入力整形
    # -------------------------

    if user_input is None:
        user_input = ""

    # -------------------------
    # Group 状態の要約
    # -------------------------

    participants = group_state.participants
    recent_turns = group_state.recent_turns[-3:]  # 直近のみ

    participants_text = ", ".join(participants)

    recent_lines: list[str] = []
    for turn in recent_turns:
        for utt in turn.utterances:
            recent_lines.append(f"{utt.speaker_id}: {utt.content}")

    recent_block = (
        "\n".join(recent_lines)
        if recent_lines
        else "(no recent utterances)"
    )

    # -------------------------
    # system prompt
    # -------------------------

    system_prompt = (
        "You are a STRICT decision engine for a group conversation.\n"
        "Your ONLY task is to decide which participants should speak next.\n"
        "\n"
        "IMPORTANT RULES:\n"
        "- You MUST output JSON ONLY.\n"
        "- You MUST NOT include explanations or natural language.\n"
        "- You MUST choose speakers ONLY from the provided participant list.\n"
        "- You MUST NOT invent narrators, guides, observers, or unnamed entities.\n"
        "- If the user does not clearly address anyone, choose AT MOST ONE speaker.\n"
        "- If no one should respond, return an empty list.\n"
        "- The user is a participant but MUST NOT be selected as a speaker.\n"
        "\n"
        "Decision guidelines:\n"
        "- Short acknowledgements or agreement usually continue the previous speaker.\n"
        "- Simple agreement (e.g. \"I see\", \"That makes sense\") should NOT switch speakers.\n"
        "- Do NOT switch speakers unless there is a clear conversational reason.\n"
        "- If a character just expressed a mood, opinion, or atmosphere, they are the default responder.\n"
        "- Silence should be chosen ONLY if responding would feel unnatural in conversation.\n"
        "\n"
        "Allowed speakers:\n"
        f"{participants_text}\n"
        "\n"
        "Output format:\n"
        "{\n"
        '  \"speakers\": [\"character_id\"]\n'
        "}\n"
    )

    # -------------------------
    # user prompt
    # -------------------------

    user_prompt = (
        "Group participants:\n"
        f"{participants_text}\n\n"
        "Recent conversation:\n"
        f"{recent_block}\n\n"
        "User input:\n"
        f"{user_input}\n\n"
        "Decide who should speak next."
    )

    return {
        "system": system_prompt,
        "user": user_prompt,
    }
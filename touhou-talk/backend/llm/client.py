"""
client.py
===========================
LLM（外界）との通信を担当する唯一のモジュール。

設計原則：
- 人格OSは LLM の存在を一切意識しない
- OpenAI / モデル名 / APIキー / API仕様差分はこの層で完結
- 入力は「messages構造」のみ
- 出力は「テキストのみ」

.env 依存：
- OPENAI_API_KEY : OpenAI APIキー（必須）
- LLM_MODEL      : 使用モデル名（任意）

このモジュールは
人格OSにとっての「声帯の外側」「外界との喉」。
"""

from __future__ import annotations

import os
import time
from typing import Dict, Optional, List

# -------------------------------------------------
# .env を明示的に読み込む（cmd / PowerShell 対策）
# -------------------------------------------------
from dotenv import load_dotenv
load_dotenv()

# -------------------------------------------------
# OpenAI SDK
# -------------------------------------------------
from openai import OpenAI
from openai.types.chat import ChatCompletion


# =================================================
# LLM Client
# =================================================

class LLMClient:
    """
    LLM 呼び出し専用クラス。

    人格OS側はこのクラスを
    - 「テキストを投げる箱」
    - 「テキストが返る箱」
    としてのみ扱う。

    👉 モデル仕様差分・API仕様変更はすべてここで吸収する
    """

    def __init__(
        self,
        *,
        model: Optional[str] = None,
        temperature: float = 0.6,
        max_tokens: int = 512,
        timeout_sec: float = 15.0,
        retry: int = 2,
    ) -> None:
        """
        初期化。

        - APIキーは必ず環境変数から取得
        - モデル名は 引数 → 環境変数 → デフォルト の順で解決
        """

        # -------------------------
        # API Key（必須）
        # -------------------------
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Please define it in your environment variables or .env file."
            )

        # -------------------------
        # Model name（任意）
        # -------------------------
        # 1. 明示的に渡された model
        # 2. .env の LLM_MODEL
        # 3. フォールバック
        self.model = (
            model
            or os.getenv("LLM_MODEL")
            or "gpt-5.1-chat-latest"
        )

        # -------------------------
        # Generation parameters（人格OS向け）
        # -------------------------
        # ※ 人格OSは「temperature を指定できる」前提で良い
        # ※ 実際に送るかどうかは下層で判断する
        self.temperature = temperature

        # 内部名は max_tokens のまま保持
        # （OpenAI API 側では max_completion_tokens に変換）
        self.max_tokens = max_tokens

        self.timeout_sec = timeout_sec
        self.retry = retry

        # -------------------------
        # OpenAI client
        # -------------------------
        # 人格OSが唯一「外界」に触れる場所
        self._client = OpenAI(api_key=api_key)

    # =================================================
    # public API
    # =================================================

    def generate(
        self,
        *,
        system: str,
        user: str,
    ) -> str:
        """
        system / user を受け取り、
        LLM からのテキスト応答を返す。

        人格OSが呼ぶ唯一の関数。
        """

        # -------------------------
        # messages 構造（OpenAI 標準）
        # -------------------------
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        last_error: Optional[Exception] = None

        # -------------------------
        # retry loop
        # -------------------------
        for attempt in range(self.retry + 1):
            try:
                completion = self._call_llm(messages)
                return self._extract_text(completion)

            except Exception as e:
                last_error = e
                # 軽いバックオフ（人格OSに揺れを伝播させない）
                time.sleep(0.5 * (attempt + 1))

        # 全試行失敗時
        raise RuntimeError("LLM call failed after retries") from last_error

    # =================================================
    # internal
    # =================================================

    def _call_llm(self, messages: List[Dict[str, str]]) -> ChatCompletion:
        """
        実際の LLM 呼び出し。

        ここで行うこと：
        - OpenAI 新旧仕様差分の吸収
        - モデルごとの「送ってはいけない引数」の除外

        👉 人格OSはこの事情を一切知らなくてよい
        """

        # -------------------------
        # 共通引数（全モデル共通）
        # -------------------------
        kwargs = {
            "model": self.model,
            "messages": messages,
            # 🔵 新仕様：max_tokens → max_completion_tokens
            "max_completion_tokens": self.max_tokens,
            "timeout": self.timeout_sec,
        }

        # -------------------------
        # temperature の扱い（重要）
        # -------------------------
        # gpt-5.1-chat-latest 系は temperature を受け付けない
        # → 指定すると 400 BadRequest になる
        #
        # 将来 temperature 対応モデルに切り替えた場合のみ
        # ここを有効化すればよい
        #
        # if self.temperature != 1.0:
        #     kwargs["temperature"] = self.temperature

        return self._client.chat.completions.create(**kwargs)

    def _extract_text(self, completion: ChatCompletion) -> str:
        """
        ChatCompletion からテキストのみを安全に抽出。

        ※ ここでは一切加工しない
           → guard.py / repair.py の責務
        """

        if not completion.choices:
            return ""

        message = completion.choices[0].message
        if not message or not message.content:
            return ""

        return message.content.strip()
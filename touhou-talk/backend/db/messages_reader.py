# db/messages_reader.py
"""
messages_reader.py
===================
DB(messages) から会話履歴を取得する読み取り専用モジュール。

Public API:
- read_messages(session_id: str, limit: int = 12) -> list[dict]

責務：
- DB から messages を取得するだけ
- role/content をそのまま返す（正規化は server 側）
- 失敗時は例外を投げる（server 側で握りつぶす設計）
"""

from typing import List, Dict
from db.connection import get_cursor


def read_messages(*, session_id: str, limit: int = 12) -> List[Dict[str, str]]:
    """
    指定 session_id の直近 messages を取得する。

    戻り値例:
    [
        {"role": "user", "content": "..."},
        {"role": "ai", "content": "..."},
    ]
    """

    sql = """
        SELECT role, content
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """

    with get_cursor() as cur:
        cur.execute(sql, (session_id, limit))
        rows = cur.fetchall()

    # DB は DESC なので、文脈としては昇順に直す
    rows.reverse()

    out: List[Dict[str, str]] = []
    for r in rows:
        role = r.get("role")
        content = r.get("content")

        if not isinstance(role, str):
            continue
        if not isinstance(content, str):
            continue

        out.append(
            {
                "role": role,
                "content": content,
            }
        )

    return out
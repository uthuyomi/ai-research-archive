"""
conversation_reader.py
======================
user_id（Supabase Auth）・character_id・session_key から
conversation_id（UUID）を取得・生成する中継モジュール。

責務：
- user_id + character_id + session_key をキーに conversations を一意に決定
- 既存 conversation があれば取得
- なければ新規作成して取得
- UUID の生成・管理はすべて DB に委譲

設計方針：
- Python 側では UUID を生成しない
- messages_reader / server.py に DB 構造を漏らさない
- 「conversation_id を解決する」ことだけに専念
"""

from db.connection import get_cursor


# ==================================================
# Public API
# ==================================================

def get_or_create_conversation_id(
    *,
    user_id: str,
    character_id: str,
    session_key: str = "default",
) -> str:
    """
    user_id + character_id + session_key に対応する
    conversation_id(UUID) を返す。

    - 既存ならそれを返す
    - なければ新規作成して返す

    Returns:
        conversation_id (str, UUID)
    """

    # --------------------------------------------------
    # Validation
    # --------------------------------------------------
    if not isinstance(user_id, str) or not user_id.strip():
        raise ValueError("user_id must be a non-empty string")

    if not isinstance(character_id, str) or not character_id.strip():
        raise ValueError("character_id must be a non-empty string")

    if not isinstance(session_key, str) or not session_key.strip():
        raise ValueError("session_key must be a non-empty string")

    # --------------------------------------------------
    # 固定モード（DB 制約に合わせる）
    # --------------------------------------------------
    mode = "single"

    # --------------------------------------------------
    # 1. 既存 conversation を探す
    # --------------------------------------------------
    select_sql = """
        SELECT id
        FROM conversations
        WHERE user_id = %s
          AND character_id = %s
          AND session_key = %s
          AND mode = %s
        LIMIT 1
    """

    with get_cursor() as cur:
        cur.execute(
            select_sql,
            (user_id, character_id, session_key, mode),
        )
        row = cur.fetchone()

        if row and "id" in row:
            return str(row["id"])

    # --------------------------------------------------
    # 2. なければ新規作成
    # --------------------------------------------------
    insert_sql = """
        INSERT INTO conversations (user_id, character_id, mode, session_key)
        VALUES (%s, %s, %s, %s)
        RETURNING id
    """

    with get_cursor(commit=True) as cur:
        cur.execute(
            insert_sql,
            (user_id, character_id, mode, session_key),
        )
        new_row = cur.fetchone()

        if not new_row or "id" not in new_row:
            raise RuntimeError("Failed to create conversation")

    return str(new_row["id"])
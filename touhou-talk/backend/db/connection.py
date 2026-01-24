"""
connection.py
===================
Supabase Postgres への接続を一元管理するモジュール。

責務：
- DATABASE_URL を唯一の情報源として使用
- psycopg2 による Postgres 直結
- cursor / connection の生成をここに集約
- 他モジュールに SQL を書かせても、接続方法は変えさせない

設計方針：
- Supabase client は使わない
- RLS / API Key は一切関与しない
- 「DB直結」専用
"""

from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Generator, Optional
from contextlib import contextmanager


# ==================================================
# 設定
# ==================================================

DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Supabase Dashboard → Settings → Database → Connection string (URI) を確認してください。"
    )


# ==================================================
# Connection factory
# ==================================================

def get_connection():
    """
    新しい DB connection を返す。

    注意：
    - 毎回新規 connection
    - pooling は行わない（必要になったら別モジュールで対応）
    """
    return psycopg2.connect(
        DATABASE_URL,
        cursor_factory=RealDictCursor,
    )


# ==================================================
# Context manager
# ==================================================

@contextmanager
def get_cursor(commit: bool = False) -> Generator:
    """
    with 構文用の cursor 取得ヘルパ。

    使用例：
    with get_cursor() as cur:
        cur.execute("SELECT 1")

    commit=True を指定した場合のみ commit する。
    （read-only 前提コードでは指定しない）
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        yield cur

        if commit:
            conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()


# ==================================================
# Health check
# ==================================================

def ping() -> bool:
    """
    DB に接続できるかだけを確認する簡易チェック。
    """
    try:
        with get_cursor() as cur:
            cur.execute("SELECT 1;")
            cur.fetchone()
        return True
    except Exception:
        return False
# core/character_factory.py
"""
character_factory.py
===========================
キャラクタープロファイル生成の導線専用モジュール。

責務：
- character_id と user_input を受け取る
- 可変対応キャラクターの場合のみ、動的 CharacterProfile を生成する
- 非対応キャラクターには一切手を触れない（ここでは扱わない）

設計方針：
- CharacterProfile の「生成」を行うが、
  その中身（人格定義・prompt構成ロジック）は各キャラ側に委譲する
- core.character / prompt.builder の思想を侵食しない
- 状態・Intent・Policy・Memory を一切参照しない
"""

from __future__ import annotations

from typing import Callable, Dict

from core.character import CharacterProfile


# ============================================================
# 可変キャラ用ビルダー import
# ============================================================
# NOTE:
# - ここでは「にとり」だけを登録する
# - 他キャラはこのファイルでは一切扱わない
# - import 失敗は即エラーでよい（起動時に気づくため）

from character.nitori_dynamic import build_nitori_profile
from character.reimu_dynamic import build_reimu_profile
from character.marisa_dynamic import build_marisa_profile
from character.alice_dynamic import build_alice_profile
from character.youmu_dynamic import build_youmu_profile
from character.aya_dynamic import build_aya_profile
from character.momiji_dynamic import build_momiji_profile
from character.sakuya_dynamic import build_sakuya_profile
from character.flandre_dynamic import build_flandre_profile
from character.satori_dynamic import build_satori_profile
from character.koishi_dynamic import build_koishi_profile



# ============================================================
# 可変キャラクター登録テーブル
# ============================================================
# character_id → build_profile(user_input) 関数
#
# 重要：
# - ここに載っているキャラのみ「毎ターン再構築」される
# - それ以外は server 側で旧ルートに流す想定

DYNAMIC_CHARACTER_BUILDERS: Dict[str, Callable[[str], CharacterProfile]] = {
    "nitori": build_nitori_profile,
    "reimu": build_reimu_profile,
    "marisa": build_marisa_profile,
    "alice": build_alice_profile,  
    "youmu": build_youmu_profile,
    "aya": build_aya_profile,
    "momiji": build_momiji_profile,
    "sakuya": build_sakuya_profile,
    "flandre": build_flandre_profile,
    "satori": build_satori_profile,
    "koishi": build_koishi_profile,
    
}


# ============================================================
# Public API
# ============================================================

def build_character_profile(
    *,
    character_id: str,
    user_input: str,
) -> CharacterProfile:
    """
    キャラクタープロファイルを生成する。

    - 可変対応キャラの場合：
        対応する builder を呼び、毎ターン新規 CharacterProfile を返す

    - 非対応キャラの場合：
        この関数は責務外
        （server 側で get_character_profile にフォールバックする）

    NOTE:
    - ここでは fallback 処理を持たない
    - 「可変かどうか」の判断のみを行う
    """

    try:
        builder = DYNAMIC_CHARACTER_BUILDERS[character_id]
    except KeyError:
        raise ValueError(
            f"Character '{character_id}' is not registered as dynamic."
        )

    # user_input をそのまま渡す
    # 解釈・加工・正規化はキャラ側の責務
    return builder(user_input)
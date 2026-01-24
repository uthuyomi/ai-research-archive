# persona_core/core/character.py
"""
character.py
===========================
dynamic キャラクタープロンプト前提の人格定義モジュール。

このファイルの役割は以下に限定される：

- CharacterSystem / CharacterPrompt / CharacterProfile の型定義（DTO）
- character_factory を唯一の人格生成導線として公開する

重要：
- static CharacterProfile（CHARACTERS）は存在しない
- キャラ個別定義の import は一切行わない
- 判断・状態・Intent・Memory・時間軸は扱わない
- このファイルは「純データ定義＋生成委譲」に徹する
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


# ==================================================
# DTO 定義
# ==================================================

@dataclass(frozen=True)
class CharacterSystem:
    """
    system プロンプトに相当する世界固定情報。
    """
    world: str
    self_recognition: str


@dataclass(frozen=True)
class CharacterPrompt:
    """
    キャラクタープロンプト構造。

    NOTE:
    - すべて完成済みデータとして扱う
    - この型自体はロジックを持たない
    """
    roleplay: List[str] = field(default_factory=list)
    persona: List[str] = field(default_factory=list)
    speech: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class CharacterProfile:
    """
    キャラクター人格のスナップショット。

    NOTE:
    - dynamic 前提：毎ターン新規生成される
    - static キャラという概念は存在しない
    """
    name: str
    style_label: Optional[str] = None

    # 言語制約
    first_person: str = "私"
    second_person: Optional[str] = None

    # system / prompt
    system: Optional[CharacterSystem] = None
    prompt: Optional[CharacterPrompt] = None

    # 数値人格パラメータ
    calmness: float = 0.7
    emotional_variance: float = 0.4
    distance_bias: float = 0.5
    intervention_level: float = 0.4
    initiative: float = 0.5
    metaphor_preference: float = 0.4
    boundary_sensitivity: float = 0.6


# ==================================================
# dynamic 人格生成導線（唯一）
# ==================================================

from core.character_factory import build_character_profile


def get_character_profile(
    *,
    character_id: str,
    user_input: str,
) -> CharacterProfile:
    """
    dynamic 前提のキャラクタープロファイル生成関数。

    - 毎ターン CharacterProfile を再構築する
    - static fallback / 旧互換は一切存在しない
    """
    return build_character_profile(
        character_id=character_id,
        user_input=user_input,
    )
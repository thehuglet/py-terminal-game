from copy import copy

from branch_game.ezterm import RGBA
from branch_game.models import RuneRarity

RUNE_RARITY_COLOR = {
    RuneRarity.COMMON: RGBA(1.0, 1.0, 1.0, 1.0),
    RuneRarity.UNCOMMON: RGBA(0.2, 0.8, 0.4, 1.0),
    RuneRarity.RARE: RGBA(0.85, 0.25, 0.3, 1.0),
}

RUNE_RARITY_MAX_BRANCH_COUNT = {
    RuneRarity.COMMON: 2,
    RuneRarity.UNCOMMON: 3,
    RuneRarity.RARE: 4,
}


def rune_rarity_color(rarity: RuneRarity) -> RGBA:
    return copy(RUNE_RARITY_COLOR[rarity])


def rune_rarity_max_branch_count(rarity: RuneRarity) -> int:
    return copy(RUNE_RARITY_MAX_BRANCH_COUNT[rarity])

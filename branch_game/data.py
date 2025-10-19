from branch_game.ezterm import RGBA
from branch_game.models import NodeRarity


NODE_RARITY_COLOR = {
    NodeRarity.COMMON: RGBA(1.0, 1.0, 1.0, 1.0),
    NodeRarity.UNCOMMON: RGBA(0.2, 0.8, 0.4, 1.0),
    NodeRarity.RARE: RGBA(0.85, 0.25, 0.3, 1.0),
}

NODE_RARITY_MAX_BRANCH_COUNT = {
    NodeRarity.COMMON: 2,
    NodeRarity.UNCOMMON: 3,
    NodeRarity.RARE: 4,
}

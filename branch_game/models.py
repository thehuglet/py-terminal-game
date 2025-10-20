from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from blessed import Terminal

from branch_game.screen_buffer import Screen


# class RuneRarity(Enum):
#     COMMON = auto()
#     UNCOMMON = auto()
#     RARE = auto()


# @dataclass
# class Rune:
#     rarity: RuneRarity
#     children: list[Rune] = field(default_factory=list)
#     is_sentinel: bool = field(default=False, kw_only=True)


# @dataclass
# class RuneData:
#     pass


# @dataclass
# class TreeViewItem:
#     rune_ref: Rune
#     display_name: str
#     depth: int


# @dataclass
# class InventoryItemRune:
#     # data: JokerData
#     pass


# class State(Enum):
#     COMPOSING_TREE = auto()
#     NODE_DRAFTING = auto()


class GameState:
    pass


@dataclass
class NavigatingTree(GameState):
    selected_view_item_index: int


class RuneRarity(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()


@dataclass
class RuneData:
    display_name: str


@dataclass
class Rune:
    rarity: RuneRarity
    data: RuneData


@dataclass
class Node:
    rune: Rune
    children: list[Node] = field(default_factory=list)
    is_sentinel: bool = False


@dataclass
class TreeViewItem:
    node: Node
    depth: int


@dataclass
class AppContext:
    terminal: Terminal
    screen: Screen
    state: GameState
    node_tree: Node
    owned_runes: list[Rune] = field(default_factory=list)

    # inventory: list[InventoryItemNode] = field(default_factory=list)
    # state: State = field(default=State.COMPOSING_TREE, init=False)
    # selected_item_index: int = field(default=0, init=False)
    # node_draft: NodeDraft | None = None
    # node_draft_selected_inventory_index: int = 0
    # debug_msg: str = ""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from blessed import Terminal

from branch_game.screen_buffer import Screen


class GameState:
    pass


@dataclass
class NavigatingTree(GameState):
    selected_view_item_index: int


@dataclass
class DraftingNode(GameState):
    parent_view_item: TreeViewItem
    draft_node_index_in_tree_view: int
    selected_owned_rune_index: int


class RuneRarity(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()


@dataclass
class RuneData:
    points: int
    display_name: str


@dataclass
class Rune:
    rarity: RuneRarity
    data: RuneData


@dataclass
class Node:
    rune: Rune
    children: list[Node] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    is_sentinel: bool = False


@dataclass
class TreeViewItem:
    node: Node
    depth: int


@dataclass
class Context:
    terminal: Terminal
    screen: Screen
    state: GameState
    node_tree: Node
    owned_runes: list[Rune] = field(default_factory=list)  # type: ignore[reportUnknownVariableType]
    tick_count: int = 0

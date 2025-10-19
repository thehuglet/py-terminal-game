from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from blessed import Terminal

from branch_game.screen_buffer import Screen


class UIAction(Enum):
    TREE_VIEW_MOVE_UP = auto()
    TREE_VIEW_MOVE_DOWN = auto()
    ADD_NODE_DRAFT = auto()
    CONFIRM_NODE_DRAFT = auto()


class NodeRarity(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()


@dataclass
class Node:
    rarity: NodeRarity
    children: list[Node] = field(default_factory=list)
    is_sentinel: bool = field(default=False, kw_only=True)


@dataclass
class TreeViewItem:
    node: Node
    depth: int
    is_draft: bool = False


@dataclass
class NodeDraft:
    node: Node
    parent: Node | None
    index: int
    depth: int


class State(Enum):
    COMPOSING_TREE = auto()
    NODE_DRAFTING = auto()


@dataclass
class AppContext:
    terminal: Terminal
    screen: Screen
    root_node: Node

    state: State = field(default=State.COMPOSING_TREE, init=False)
    selected_item_index: int = field(default=0, init=False)
    node_draft: NodeDraft | None = None
    debug_msg: str = ""

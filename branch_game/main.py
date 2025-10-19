from __future__ import annotations
from copy import copy
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from random import choice, random
from typing import Callable
from blessed import Terminal
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs
from branch_game.ezterm import BACKGROUND_COLOR, RGBA, RichText, fill_screen_background
from branch_game.fps_limiter import create_fps_limiter
import branch_game.ezterm as ezterm

class AppStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


class State(Enum):
    COMPOSING_TREE = auto()
    NODE_DRAFTING = auto()


class UIAction(Enum):
    TREE_VIEW_MOVE_UP = auto()
    TREE_VIEW_MOVE_DOWN = auto()
    ADD_NODE_DRAFT = auto()
    CONFIRM_NODE_DRAFT = auto()


class NodeRarity(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()


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


@dataclass
class AppContext:
    terminal: Terminal
    screen: Screen
    root_node: Node

    state: State = field(default=State.COMPOSING_TREE, init=False)
    selected_item_index: int = field(default=0, init=False)
    tree_view: list[TreeViewItem] = field(default_factory=list)
    node_draft: NodeDraft | None = None
    debug_msg: str = ""

def refresh_tree_view(ctx: AppContext):
    ctx.tree_view = generate_tree_view(ctx)


def get_available_node_branch_slots(node: Node) -> int:
    branch_slots = NODE_RARITY_MAX_BRANCH_COUNT[node.rarity]

    return max(0, branch_slots - len(node.children))


def generate_tree_view(ctx: AppContext) -> list[TreeViewItem]:
    tree_view: list[TreeViewItem] = []

    def walk_tree(node: Node, depth: int = 0) -> list[TreeViewItem]:
        out = [TreeViewItem(node, depth)]

        for child in node.children:
            out.extend(walk_tree(child, depth + 1))
        return out

    tree_view.extend(walk_tree(ctx.root_node))

    if ctx.node_draft:
        index = ctx.node_draft.index
        depth = ctx.node_draft.depth
        draft_item = TreeViewItem(ctx.node_draft.node, depth, True)
        tree_view.insert(index, draft_item)

    return tree_view


def tick(
    ctx: AppContext, print_at: Callable[[int, int, RichText | list[RichText]], None]
) -> AppStatus:
    key = ctx.terminal.inkey(timeout=0.1)
    if key == "q":
        return AppStatus.EXIT

    # < = = | Input to UIAction mapping | = = >
    ui_action: UIAction | None = None

    if ctx.state == State.COMPOSING_TREE:
        can_move_up: bool = ctx.selected_item_index > 0
        can_move_down: bool = ctx.selected_item_index < (len(ctx.tree_view)) - 1
        selected_node: Node = ctx.tree_view[ctx.selected_item_index].node
        can_add_branch: bool = get_available_node_branch_slots(selected_node) > 0

        if key.name == "KEY_UP" and can_move_up:
            ui_action = UIAction.TREE_VIEW_MOVE_UP
        elif key.name == "KEY_DOWN" and can_move_down:
            ui_action = UIAction.TREE_VIEW_MOVE_DOWN
        elif key == "b" and can_add_branch:
            ui_action = UIAction.ADD_NODE_DRAFT
    elif ctx.state == State.NODE_DRAFTING:
        if key.name == "KEY_ENTER":
            ui_action = UIAction.CONFIRM_NODE_DRAFT

    # < = = | Action execution | = = >
    match ui_action:
        case UIAction.TREE_VIEW_MOVE_UP:
            ctx.selected_item_index -= 1
        case UIAction.TREE_VIEW_MOVE_DOWN:
            ctx.selected_item_index += 1
        case UIAction.ADD_NODE_DRAFT:
            selected_view_item = ctx.tree_view[ctx.selected_item_index]
            # TODO: remove this, this is just for testing
            random_rarity = choice(list(NodeRarity))

            ctx.node_draft = NodeDraft(
                node=Node(random_rarity),
                parent=selected_view_item.node,
                index=ctx.selected_item_index + 1,
                depth=selected_view_item.depth + 1,
            )

            refresh_tree_view(ctx)
            ctx.state = State.NODE_DRAFTING
        case UIAction.CONFIRM_NODE_DRAFT:
            if ctx.node_draft:
                new_node = ctx.node_draft.node

                if parent_node := ctx.node_draft.parent:
                    parent_node.children.insert(0, new_node)
                else:
                    # This handles the case of a node at the root
                    ctx.root_node = new_node

            # clears the node draft
            ctx.node_draft = None

            # move cursor onto the newly created node
            ctx.selected_item_index += 1

            refresh_tree_view(ctx)

            ctx.state = State.COMPOSING_TREE
        case _:
            pass

    # < = = | Rendering | = = >
    for index, tree_view_item in enumerate(ctx.tree_view):
        text_segments: list[RichText] = []

        regular_node_alpha = 0.4
        rich_text_color = copy(NODE_RARITY_COLOR[tree_view_item.node.rarity])
        rich_text_color.a *= regular_node_alpha

        is_selected: bool = index == ctx.selected_item_index

        # Override color for highlighting based on the context
        if is_selected and ctx.state != State.NODE_DRAFTING:
            branch_count = len(tree_view_item.node.children)
            max_branch_count = NODE_RARITY_MAX_BRANCH_COUNT[tree_view_item.node.rarity]
            suffix = RichText(f" ({branch_count}/{max_branch_count})", RGBA(1.0, 0.8, 0.5, 0.4))
            text_segments.append(suffix)
            highlighted_node_alpha = 1.0
            rich_text_color = copy(NODE_RARITY_COLOR[tree_view_item.node.rarity])
            rich_text_color.a *= highlighted_node_alpha
        if tree_view_item.is_draft:
            rich_text_color = RGBA(0.5, 1.0, 1.0, 0.5)

        rich_text = RichText("node", color=rich_text_color)
        text_segments.insert(0, rich_text)

        print_at(2 * tree_view_item.depth, index, text_segments)

    print_at(0, 20, RichText(ctx.debug_msg))

    flush_diffs(ctx.terminal, buffer_diff(ctx.screen))
    return AppStatus.RUNNING


def main():
    terminal = Terminal()
    screen = Screen(terminal.width, terminal.height)
    print_at = partial(ezterm.print_at, terminal, screen)

    # ctx = Context()
    ctx = AppContext(
        terminal,
        screen,
        Node(NodeRarity.COMMON, is_sentinel=True),
    )
    fill_screen_background(terminal, screen, BACKGROUND_COLOR)
    refresh_tree_view(ctx)
    fps_limiter = create_fps_limiter(60)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        while True:
            tick_outcome: AppStatus = tick(ctx, print_at)
            if tick_outcome == AppStatus.EXIT:
                break

            _ = fps_limiter()


if __name__ == "__main__":
    main()

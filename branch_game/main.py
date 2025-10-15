from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from functools import partial
from typing import Callable
from blessed import Terminal
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs
from branch_game.ezterm import RichText
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


@dataclass
class Node:
    children: list[Node] = field(default_factory=list)
    is_sentinel: bool = field(kw_only=False, default=True)


@dataclass
class TreeViewItem:
    node: Node | None
    depth: int
    is_draft: bool = False


@dataclass
class NodeDraft:
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


def generate_tree_view(ctx: AppContext) -> list[TreeViewItem]:
    tree_view: list[TreeViewItem] = []

    if node := ctx.root_node:

        def walk_tree(node: Node, depth: int = 0) -> list[TreeViewItem]:
            out = [TreeViewItem(node, depth)]
            for child in node.children:
                out.extend(walk_tree(child, depth + 1))
            return out

        tree_view.extend(walk_tree(node))

    if ctx.node_draft:
        index = ctx.node_draft.index
        depth = ctx.node_draft.depth
        node_draft = TreeViewItem(None, depth, True)
        tree_view.insert(index, node_draft)

    return tree_view


def tick(ctx: AppContext, print_at: Callable[[int, int, RichText], None]) -> AppStatus:
    key = ctx.terminal.inkey(timeout=0.1)
    if key == "q":
        return AppStatus.EXIT

    # < = = | Input to action translation | = = >
    ui_action: UIAction | None = None

    if ctx.state == State.COMPOSING_TREE:
        can_move_up: bool = ctx.selected_item_index > 0
        can_move_down: bool = ctx.selected_item_index < (len(ctx.tree_view)) - 1

        if key.name == "KEY_UP" and can_move_up:
            ui_action = UIAction.TREE_VIEW_MOVE_UP
        elif key.name == "KEY_DOWN" and can_move_down:
            ui_action = UIAction.TREE_VIEW_MOVE_DOWN
        elif key == "b":
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
            if ctx.root_node:
                selected_view_item = ctx.tree_view[ctx.selected_item_index]
                ctx.node_draft = NodeDraft(
                    parent=selected_view_item.node,
                    index=ctx.selected_item_index + 1,
                    depth=selected_view_item.depth + 1,
                )
            else:
                ctx.node_draft = NodeDraft(
                    parent=None,
                    index=0,
                    depth=0,
                )

            refresh_tree_view(ctx)
            ctx.state = State.NODE_DRAFTING
        case UIAction.CONFIRM_NODE_DRAFT:
            if ctx.node_draft:
                new_node = Node()

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

    # Rendering
    for index, tree_view_item in enumerate(ctx.tree_view):
        text = RichText("node", color=(155, 155, 155))

        is_selected: bool = index == ctx.selected_item_index

        if is_selected and ctx.state != State.NODE_DRAFTING:
            text.color = (255, 255, 150)

        if tree_view_item.is_draft:
            text.color = (75, 120, 155)

        print_at(2 * tree_view_item.depth, index, text)

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
        Node(
            [Node()],
        ),
    )
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

from __future__ import annotations

from copy import copy
from enum import Enum, auto
from functools import partial
from random import choice
from typing import Callable

from blessed import Terminal
from blessed.keyboard import Keystroke

from branch_game.data import RUNE_RARITY_COLOR, RUNE_RARITY_MAX_BRANCH_COUNT
import branch_game.ezterm as ezterm
from branch_game.ezterm import BACKGROUND_COLOR, RGBA, RichText, fill_screen_background
from branch_game.fps_limiter import create_fps_limiter
from branch_game.models import (
    AppContext,
    NavigatingTree,
    Node,
    Rune,
    RuneData,
    RuneRarity,
    TreeViewItem,
)
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs


class AppStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


class UIAction(Enum):
    TREE_VIEW_MOVE_UP = auto()
    TREE_VIEW_MOVE_DOWN = auto()
    ADD_NODE_DRAFT = auto()
    NODE_DRAFT_CYCLE_AVAILABLE_NODES_LEFT = auto()
    NODE_DRAFT_CYCLE_AVAILABLE_NODES_RIGHT = auto()
    CONFIRM_NODE_DRAFT = auto()


def generate_tree_view(ctx: AppContext) -> list[TreeViewItem]:
    tree_view: list[TreeViewItem] = []

    def walk_tree(node: Node, depth: int = 0) -> list[TreeViewItem]:
        out: list[TreeViewItem] = []

        if not node.is_sentinel:
            out.append(TreeViewItem(node, depth))

        for child in node.children:
            out.extend(walk_tree(child, depth + 1 if not node.is_sentinel else depth))
        return out

    tree_view.extend(walk_tree(ctx.node_tree))

    return tree_view


def tick(
    ctx: AppContext,
    _delta_time: float,
    print_at: Callable[[int, int, RichText | list[RichText]], None],
) -> AppStatus:
    key: Keystroke = ctx.terminal.inkey(timeout=0.1)

    if key == "q":
        return AppStatus.EXIT

    # < = = | Input to UIAction mapping | = = >
    ui_action: UIAction | None = None

    tree_view: list[TreeViewItem] = generate_tree_view(ctx)

    match ctx.state:
        case NavigatingTree(selected_view_item_index=selected_view_item_index):
            tree_nav_can_move_up: bool = selected_view_item_index > 0
            tree_nav_can_move_down: bool = selected_view_item_index < (len(tree_view)) - 1
            selected_node: Node = tree_view[selected_view_item_index].node
            max_allowed_branches: int = RUNE_RARITY_MAX_BRANCH_COUNT[selected_node.rune.rarity]
            can_add_branch: bool = len(selected_node.children) < max_allowed_branches

            if key.name == "KEY_UP" and tree_nav_can_move_up:
                ui_action = UIAction.TREE_VIEW_MOVE_UP
            elif key.name == "KEY_DOWN" and tree_nav_can_move_down:
                ui_action = UIAction.TREE_VIEW_MOVE_DOWN
            elif key == "b" and can_add_branch:
                ui_action = UIAction.ADD_NODE_DRAFT
        case _:
            pass

    # if ctx.state == State.COMPOSING_TREE:
    #     tree_nav_can_move_up: bool = ctx.selected_item_index > 0
    #     tree_nav_can_move_down: bool = ctx.selected_item_index < (len(tree_view)) - 1
    #     selected_node: Node = tree_view[ctx.selected_item_index].node
    #     can_add_branch: bool = get_available_node_branch_slots(selected_node) > 0

    #     if key.name == "KEY_UP" and tree_nav_can_move_up:
    #         ui_action = UIAction.TREE_VIEW_MOVE_UP
    #     elif key.name == "KEY_DOWN" and tree_nav_can_move_down:
    #         ui_action = UIAction.TREE_VIEW_MOVE_DOWN
    #     elif key == "b" and can_add_branch:
    #         ui_action = UIAction.ADD_NODE_DRAFT

    # elif ctx.state == State.NODE_DRAFTING:
    #     draft_can_move_prev: bool = ctx.node_draft_selected_inventory_index > 0
    #     draft_can_move_next: bool = ctx.node_draft_selected_inventory_index < len(ctx.inventory) - 1

    #     if key.name == "KEY_ENTER":
    #         ui_action = UIAction.CONFIRM_NODE_DRAFT
    #     elif key.name == "KEY_LEFT" and draft_can_move_prev:
    #         ui_action = UIAction.NODE_DRAFT_CYCLE_AVAILABLE_NODES_LEFT
    #     elif key.name == "KEY_RIGHT" and draft_can_move_next:
    #         ui_action = UIAction.NODE_DRAFT_CYCLE_AVAILABLE_NODES_RIGHT

    # # < = = | Action execution | = = >
    # match ui_action:
    #     case UIAction.TREE_VIEW_MOVE_UP:
    #         ctx.selected_item_index -= 1
    #     case UIAction.TREE_VIEW_MOVE_DOWN:
    #         ctx.selected_item_index += 1
    #     case UIAction.ADD_NODE_DRAFT:
    #         selected_view_item = tree_view[ctx.selected_item_index]
    #         # TODO: remove this, this is just for testing
    #         random_rarity = choice(list(RuneRarity))

    #         ctx.node_draft = NodeDraft(
    #             node=Node(random_rarity),
    #             parent=selected_view_item.node,
    #             index=ctx.selected_item_index + 1,
    #             depth=selected_view_item.depth + 1,
    #         )

    #         # Update tree view immediately
    #         tree_view = generate_tree_view(ctx)
    #         ctx.state = State.NODE_DRAFTING

    #     case UIAction.NODE_DRAFT_CYCLE_AVAILABLE_NODES_LEFT:
    #         ctx.selected_item_index -= 1
    #     case UIAction.NODE_DRAFT_CYCLE_AVAILABLE_NODES_RIGHT:
    #         ctx.selected_item_index += 1
    #     case UIAction.CONFIRM_NODE_DRAFT:
    #         if ctx.node_draft:
    #             new_node = ctx.node_draft.node

    #             if parent_node := ctx.node_draft.parent:
    #                 parent_node.children.insert(0, new_node)
    #             else:
    #                 # This handles the case of a node at the root
    #                 ctx.rune_tree = new_node

    #         # clears the node draft
    #         ctx.node_draft = None

    #         # Update tree view immediately
    #         tree_view = generate_tree_view(ctx)
    #         # move cursor onto the newly created node
    #         ctx.selected_item_index += 1

    #         # Reset to 0 after we exit out of drafting
    #         ctx.node_draft_selected_inventory_index = 0

    #         ctx.state = State.COMPOSING_TREE
    #     case _:
    #         pass

    # < = = | Flat rendering of the tree | = = >
    for index, item in enumerate(tree_view):
        text_segments: list[RichText] = []

        text_segments.append(
            RichText(item.node.rune.data.display_name, color=RGBA(1.0, 1.0, 1.0, 1.0))
        )

        print_at(2 * item.depth, index, text_segments)

    #     text_segments: list[RichText] = []
    #     is_selected: bool = index == ctx.selected_item_index and ctx.state != State.NODE_DRAFTING

    # default_text = RichText(tree_view_item.name)
    # text_segments.append(RichText(""))

    # if tree_view_item.is_draft:
    #     pass
    # elif is_selected:
    #     pass
    # else:
    #     # Default rendering
    #     rich_text = RichText("node", color=RGBA(1.0, 1.0, 1.0, 1.0))
    #     text_segments.append(rich_text)

    # print_at(2 * tree_view_item.depth, index, text_segments)

    # text_segments: list[RichText] = []

    # regular_node_alpha = 0.4
    # rich_text_color = copy(NODE_RARITY_COLOR[tree_view_item.node.rarity])
    # rich_text_color.a *= regular_node_alpha

    # is_selected: bool = index == ctx.selected_item_index

    # # Override color for highlighting based on the context
    # # TODO: rework this rendering code for each case
    # if is_selected and ctx.state != State.NODE_DRAFTING:
    #     branch_count = len(tree_view_item.node.children)
    #     max_branch_count = NODE_RARITY_MAX_BRANCH_COUNT[tree_view_item.node.rarity]
    #     suffix = RichText(f" ({branch_count}/{max_branch_count})", RGBA(1.0, 0.8, 0.5, 0.4))
    #     text_segments.append(suffix)
    #     highlighted_node_alpha = 1.0
    #     rich_text_color = copy(NODE_RARITY_COLOR[tree_view_item.node.rarity])
    #     rich_text_color.a *= highlighted_node_alpha
    # if tree_view_item.is_draft:
    #     rich_text_color = RGBA(0.5, 1.0, 1.0, 0.5)

    # rich_text = RichText("node", color=rich_text_color)
    # text_segments.insert(0, rich_text)

    # print_at(2 * tree_view_item.depth, index, text_segments)

    # print_at(0, 20, RichText(ctx.debug_msg))

    flush_diffs(ctx.terminal, buffer_diff(ctx.screen))
    return AppStatus.RUNNING


def main():
    terminal = Terminal()
    screen = Screen(terminal.width, terminal.height)
    print_at = partial(ezterm.print_at, terminal, screen)
    ctx = AppContext(
        terminal,
        screen,
        state=NavigatingTree(selected_view_item_index=0),
        node_tree=Node(Rune(RuneRarity.COMMON, RuneData("dummy")), is_sentinel=True),
    )

    # TODO: remove this later
    # temp node tree rendering testing
    ctx.node_tree.children.extend(
        [
            Node(
                Rune(
                    RuneRarity.COMMON,
                    RuneData("foo"),
                )
            ),
            Node(
                Rune(
                    RuneRarity.UNCOMMON,
                    RuneData("bar"),
                )
            ),
        ]
    )

    # temp initial inventory for testing
    ctx.owned_runes = [
        Rune(RuneRarity.COMMON, RuneData("foo")),
        Rune(RuneRarity.COMMON, RuneData("bar")),
        Rune(RuneRarity.UNCOMMON, RuneData("uwu")),
        Rune(RuneRarity.RARE, RuneData("baz")),
    ]

    fill_screen_background(terminal, screen, BACKGROUND_COLOR)
    fps_limiter = create_fps_limiter(120)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        delta_time: float = 0.0

        while True:
            tick_outcome: AppStatus = tick(ctx, delta_time, print_at)
            if tick_outcome == AppStatus.EXIT:
                break

            delta_time = fps_limiter()


if __name__ == "__main__":
    main()

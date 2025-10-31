from __future__ import annotations

from enum import Enum, auto
from functools import partial
import math
from typing import Callable

from blessed import Terminal
from blessed.keyboard import Keystroke

import branch_game.ezterm as ezterm
from branch_game.data import RUNE_RARITY_MAX_BRANCH_COUNT, rune_rarity_color
from branch_game.ezterm import BACKGROUND_COLOR, RichText, fill_screen_background
from branch_game.fps_limiter import create_fps_limiter
from branch_game.models import (
    Context,
    DraftingNode,
    NavigatingTree,
    Node,
    Rune,
    RuneData,
    RuneRarity,
    TreeViewItem,
)
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs

type PrintAtCallable = Callable[[int, int, RichText | list[RichText]], None]


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


class InputAction(Enum):
    TREE_NAV_MOVE_UP = auto()
    TREE_NAV_MOVE_DOWN = auto()
    DRAFT_NEW_BRANCHING_NODE = auto()
    DRAFTING_NODE_SELECT_PREV_RUNE = auto()
    DRAFTING_NODE_SELECT_NEXT_RUNE = auto()
    CONFIRM_NODE_DRAFT = auto()


def render_carousel(ctx: Context, print_at: PrintAtCallable) -> None:
    assert isinstance(ctx.state, DraftingNode), "Expected DraftingNode state."

    sel = ctx.state.selected_owned_rune_index
    total = len(ctx.owned_runes)
    side = 2  # how many items to show per side
    gap = 3
    y = 20

    screen_center_x = ctx.screen.width // 2

    # Selected rune (always centered)
    sel_name = ctx.owned_runes[sel].data.display_name
    sel_x = int(screen_center_x - (len(sel_name) // 2))
    sel_color = rune_rarity_color(ctx.owned_runes[sel].rarity)
    sel_color.a = 1.0
    # simple clip guard
    if 0 <= sel_x < ctx.screen.width:
        print_at(sel_x, y, RichText(sel_name, sel_color, bold=True))

    # Right side: place items to the right of the selected item
    x_right = sel_x + len(sel_name) + gap
    for i in range(1, side + 1):
        idx = sel + i
        if idx >= total:
            break
        name = ctx.owned_runes[idx].data.display_name
        # alpha falls off with distance
        alpha = max(0.05, 0.5**i)
        color = rune_rarity_color(ctx.owned_runes[idx].rarity)
        color.a *= alpha
        if x_right + len(name) > 0 and x_right < ctx.screen.width:
            print_at(x_right, y, RichText(name, color))
        x_right += len(name) + gap

    # Left side: place items to the left of the selected item (grow leftwards)
    x_left = sel_x - gap
    for i in range(1, side + 1):
        idx = sel - i
        if idx < 0:
            break
        name = ctx.owned_runes[idx].data.display_name
        alpha = max(0.05, 0.5**i)
        color = rune_rarity_color(ctx.owned_runes[idx].rarity)
        color.a *= alpha
        # compute start x for this name (we place names leftwards)
        x_left -= len(name)
        if x_left + len(name) > 0 and x_left < ctx.screen.width:
            print_at(x_left, y, RichText(name, color))
        x_left -= gap


def generate_tree_view(ctx: Context) -> list[TreeViewItem]:
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
    ctx: Context,
    _delta_time: float,
    print_at: PrintAtCallable,
) -> ProgramStatus:
    key: Keystroke = ctx.terminal.inkey(timeout=0.1)
    if key == "q":
        return ProgramStatus.EXIT

    tree_view: list[TreeViewItem] = generate_tree_view(ctx)

    # --- Hotkey to input action mapping ---
    maybe_input_action: InputAction | None = None

    if isinstance(ctx.state, NavigatingTree):
        selected_item_index: int = ctx.state.selected_view_item_index
        can_move_up: bool = selected_item_index > 0
        can_move_down: bool = selected_item_index < (len(tree_view)) - 1

        selected_node: Node = tree_view[selected_item_index].node
        max_allowed_branches: int = RUNE_RARITY_MAX_BRANCH_COUNT[selected_node.rune.rarity]
        can_add_branch: bool = len(selected_node.children) < max_allowed_branches

        if key.name == "KEY_UP" and can_move_up:
            maybe_input_action = InputAction.TREE_NAV_MOVE_UP

        if key.name == "KEY_DOWN" and can_move_down:
            maybe_input_action = InputAction.TREE_NAV_MOVE_DOWN

        if key == "b" and can_add_branch and len(ctx.owned_runes) > 0:
            maybe_input_action = InputAction.DRAFT_NEW_BRANCHING_NODE

    if isinstance(ctx.state, DraftingNode):
        rune_index: int = ctx.state.selected_owned_rune_index
        can_move_prev_rune: bool = rune_index > 0
        can_move_next_rune: bool = rune_index < len(ctx.owned_runes) - 1

        if key.name == "KEY_ENTER":
            maybe_input_action = InputAction.CONFIRM_NODE_DRAFT

        if key.name == "KEY_LEFT" and can_move_prev_rune:
            maybe_input_action = InputAction.DRAFTING_NODE_SELECT_PREV_RUNE

        if key.name == "KEY_RIGHT" and can_move_next_rune:
            maybe_input_action = InputAction.DRAFTING_NODE_SELECT_NEXT_RUNE

    # --- Input action execution ---
    match maybe_input_action:
        case InputAction.TREE_NAV_MOVE_UP:
            assert isinstance(ctx.state, NavigatingTree)
            ctx.state.selected_view_item_index -= 1

        case InputAction.TREE_NAV_MOVE_DOWN:
            assert isinstance(ctx.state, NavigatingTree)
            ctx.state.selected_view_item_index += 1

        case InputAction.DRAFT_NEW_BRANCHING_NODE:
            assert isinstance(ctx.state, NavigatingTree)
            ctx.state = DraftingNode(
                parent_view_item=tree_view[ctx.state.selected_view_item_index],
                draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,
                selected_owned_rune_index=0,
            )

        case InputAction.DRAFTING_NODE_SELECT_PREV_RUNE:
            assert isinstance(ctx.state, DraftingNode)
            ctx.state.selected_owned_rune_index -= 1

        case InputAction.DRAFTING_NODE_SELECT_NEXT_RUNE:
            assert isinstance(ctx.state, DraftingNode)
            ctx.state.selected_owned_rune_index += 1

        case InputAction.CONFIRM_NODE_DRAFT:
            assert isinstance(ctx.state, DraftingNode)
            raise Exception("Not implemented.")

        case _:
            pass

    if isinstance(ctx.state, DraftingNode):
        depth: int = ctx.state.parent_view_item.depth + 1
        tree_view.insert(
            ctx.state.draft_node_index_in_tree_view,
            TreeViewItem(Node(ctx.owned_runes[ctx.state.selected_owned_rune_index]), depth),
        )

    # --- View tree rendering---
    for index, item in enumerate(tree_view):
        text_segments: list[RichText] = []

        item_is_selected: bool = (
            isinstance(ctx.state, NavigatingTree) and ctx.state.selected_view_item_index == index
        )
        item_is_ghost: bool = (
            isinstance(ctx.state, DraftingNode) and ctx.state.draft_node_index_in_tree_view == index
        )

        if item_is_selected:
            text = item.node.rune.data.display_name
            color = rune_rarity_color(item.node.rune.rarity)
            text_segments.append(RichText(text, color))
        else:
            text = item.node.rune.data.display_name
            color = rune_rarity_color(item.node.rune.rarity)
            color.a *= 0.5
            text_segments.append(RichText(text, color))

        if item_is_ghost:
            color.a = 0.7 + 0.2 * math.sin(ctx.tick_count * 0.65)

        print_at(2 * item.depth, index, text_segments)

    # --- Carousel: keep selected item centered and shift neighbors around it ---
    if isinstance(ctx.state, DraftingNode) and ctx.owned_runes:
        render_carousel(ctx, print_at)

    flush_diffs(ctx.terminal, buffer_diff(ctx.screen))
    return ProgramStatus.RUNNING


def main() -> None:
    terminal = Terminal()
    screen = Screen(terminal.width, terminal.height)
    print_at = partial(ezterm.print_at, terminal, screen)
    ctx = Context(
        terminal,
        screen,
        state=NavigatingTree(selected_view_item_index=0),
        node_tree=Node(Rune(RuneRarity.COMMON, RuneData(0, "dummy")), is_sentinel=True),
    )

    # TODO: remove this later
    # temp node tree rendering testing
    ctx.node_tree.children.extend(
        [
            Node(
                Rune(
                    RuneRarity.COMMON,
                    RuneData(0, "foo"),
                )
            ),
            Node(
                Rune(
                    RuneRarity.UNCOMMON,
                    RuneData(0, "bar"),
                ),
                children=[
                    Node(
                        Rune(
                            RuneRarity.RARE,
                            RuneData(0, "baz"),
                        )
                    )
                ],
            ),
        ]
    )

    # temp initial inventory for testing
    ctx.owned_runes = [
        Rune(RuneRarity.COMMON, RuneData(10, "foo")),
        Rune(RuneRarity.COMMON, RuneData(3, "bar")),
        Rune(RuneRarity.UNCOMMON, RuneData(30, "boop")),
        Rune(RuneRarity.RARE, RuneData(23, "abcd")),
        Rune(RuneRarity.UNCOMMON, RuneData(69, "aaaaaaaaaaaaaaaaaa")),
    ]

    fill_screen_background(terminal, screen, BACKGROUND_COLOR)
    fps_limiter = create_fps_limiter(144)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        delta_time: float = 0.0

        while True:
            tick_outcome: ProgramStatus = tick(ctx, delta_time, print_at)
            if tick_outcome == ProgramStatus.EXIT:
                break

            ctx.tick_count += 1
            delta_time = fps_limiter()


if __name__ == "__main__":
    main()

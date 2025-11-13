from __future__ import annotations

import math
from abc import ABC
from enum import Enum, auto
from functools import partial
from typing import Callable, cast

from blessed import Terminal
from blessed.keyboard import Keystroke

import branch_game.ezterm as ezterm
from branch_game.data import (
    RUNE_RARITY_MAX_BRANCH_COUNT,
    rune_rarity_color,
    rune_rarity_max_branch_count,
)
from branch_game.data_types import (
    Context,
    DraftingNode,
    FPSCounter,
    NavigatingTree,
    Node,
    Rune,
    RuneData,
    RuneRarity,
    TreeViewItem,
)
from branch_game.ezterm import BACKGROUND_COLOR, RGBA, RichText, fill_screen_background
from branch_game.fps_counter import render_fps_counter, update_fps_counter
from branch_game.fps_limiter import create_fps_limiter
from branch_game.helpers import insert_child, tree_view_index_to_node_child_index
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs

type PrintAtCallable = Callable[[int, int, RichText | list[RichText]], None]


class ProgramStatus(Enum):
    RUNNING = auto()
    EXIT = auto()


class InputAction(Enum):
    MOVE_CURSOR_UP = auto()
    MOVE_CURSOR_DOWN = auto()
    NEW_DRAFT = auto()
    SELECT_PREV_RUNE = auto()
    SELECT_NEXT_RUNE = auto()
    CONFIRM_DRAFT = auto()
    CANCEL_DRAFT = auto()
    MOVE_DRAFT_UP = auto()
    MOVE_DRAFT_DOWN = auto()


# def render_carousel(ctx: Context, print_at: PrintAtCallable) -> None:
#     assert isinstance(ctx.state, DraftingNode), "Expected DraftingNode state."

#     sel = ctx.state.selected_owned_rune_index
#     total = len(ctx.owned_runes)
#     side = 2  # how many items to show per side
#     gap = 3
#     y = 20

#     screen_center_x = ctx.screen.width // 2

#     # Selected rune (always centered)
#     sel_name = ctx.owned_runes[sel].data.display_name
#     sel_x = int(screen_center_x - (len(sel_name) // 2))
#     sel_color = rune_rarity_color(ctx.owned_runes[sel].rarity)
#     sel_color.a = 1.0
#     # simple clip guard
#     if 0 <= sel_x < ctx.screen.width:
#         print_at(sel_x, y, RichText(sel_name, sel_color, bold=True))

#     # Right side: place items to the right of the selected item
#     x_right = sel_x + len(sel_name) + gap
#     for i in range(1, side + 1):
#         idx = sel + i
#         if idx >= total:
#             break
#         name = ctx.owned_runes[idx].data.display_name
#         # alpha falls off with distance
#         alpha = max(0.05, 0.5**i)
#         color = rune_rarity_color(ctx.owned_runes[idx].rarity)
#         color.a *= alpha
#         if x_right + len(name) > 0 and x_right < ctx.screen.width:
#             print_at(x_right, y, RichText(name, color))
#         x_right += len(name) + gap

#     # Left side: place items to the left of the selected item (grow leftwards)
#     x_left = sel_x - gap
#     for i in range(1, side + 1):
#         idx = sel - i
#         if idx < 0:
#             break
#         name = ctx.owned_runes[idx].data.display_name
#         alpha = max(0.05, 0.5**i)
#         color = rune_rarity_color(ctx.owned_runes[idx].rarity)
#         color.a *= alpha
#         # compute start x for this name (we place names leftwards)
#         x_left -= len(name)
#         if x_left + len(name) > 0 and x_left < ctx.screen.width:
#             print_at(x_left, y, RichText(name, color))
#         x_left -= gap


def generate_tree_view(ctx: Context) -> list[TreeViewItem]:
    tree_view: list[TreeViewItem] = []

    def walk_tree(node: Node, depth: int = 0) -> list[TreeViewItem]:
        out: list[TreeViewItem] = []
        out.append(TreeViewItem(node, depth))

        for child in node.children:
            out.extend(walk_tree(child, depth + 1))
        return out

    tree_view.extend(walk_tree(ctx.node_tree))

    return tree_view


def tick(
    ctx: Context,
    delta_time: float,
    print_at: PrintAtCallable,
    fps_counter: FPSCounter,
) -> ProgramStatus:
    key: Keystroke = ctx.terminal.inkey(timeout=0.0)
    if key == "q":
        return ProgramStatus.EXIT

    tree_view: list[TreeViewItem] = generate_tree_view(ctx)

    # --- Hotkey to input action mapping ---
    maybe_input_action: InputAction | None = None

    if isinstance(ctx.state, NavigatingTree):
        selected_item_index = ctx.state.selected_view_item_index
        can_move_cursor_up = selected_item_index > 0
        can_move_cursor_down = selected_item_index < (len(tree_view)) - 1

        selected_node = tree_view[selected_item_index].node
        max_allowed_branches = RUNE_RARITY_MAX_BRANCH_COUNT[selected_node.rune.rarity]
        is_under_branch_limit = len(selected_node.children) < max_allowed_branches
        owns_any_runes = len(ctx.owned_runes) > 0

        # can_move_child_up =

        if key.name == "KEY_UP" and can_move_cursor_up:
            maybe_input_action = InputAction.MOVE_CURSOR_UP

        elif key.name == "KEY_DOWN" and can_move_cursor_down:
            maybe_input_action = InputAction.MOVE_CURSOR_DOWN

        elif key == "b" and owns_any_runes and is_under_branch_limit:
            maybe_input_action = InputAction.NEW_DRAFT

        # elif key.name == "KEY_CTRL_UP" and can_move_child_up:
        #     pass

        # elif key.name == "KEY_CTRL_DOWN" and can_move_child_down:
        #     pass

    elif isinstance(ctx.state, DraftingNode):
        selected_rune_index = ctx.state.selected_rune_index
        is_first_rune = selected_rune_index == 0
        is_last_rune = selected_rune_index == len(ctx.owned_runes) - 1
        # is_first_child = ctx.state.

        if key == "z":
            maybe_input_action = InputAction.CANCEL_DRAFT

        elif key.name == "KEY_ENTER":
            maybe_input_action = InputAction.CONFIRM_DRAFT

            # diff = (
            #     ctx.state.draft_node_index_in_tree_view
            #     - ctx.state.starting_draft_node_index_in_tree_view
            # )

            # ctx.state.parent_view_item.node.children.insert(
            #     diff, Node(rune=ctx.owned_runes[ctx.state.selected_owned_rune_index])
            # )
            #
            parent_node = tree_view[ctx.state.tree_view_index].node
            insert_child(
                parent_node,
            )

            _ = ctx.owned_runes.pop(ctx.state.selected_rune_index)

            # Update tree this frame
            tree_view = generate_tree_view(ctx)

            # revert back to pre-draft position
            ctx.state = NavigatingTree(ctx.state.tree_view_index)

        elif key.name == "KEY_LEFT" and not is_first_rune:
            maybe_input_action = InputAction.SELECT_PREV_RUNE

        elif key.name == "KEY_RIGHT" and not is_last_rune:
            maybe_input_action = InputAction.SELECT_NEXT_RUNE

        elif key.name == "KEY_UP":
            maybe_input_action = InputAction.MOVE_DRAFT_UP

        elif key.name == "KEY_DOWN":
            maybe_input_action = InputAction.MOVE_DRAFT_DOWN

    # --- Input action execution ---
    if isinstance(ctx.state, NavigatingTree):
        if maybe_input_action == InputAction.MOVE_CURSOR_UP:
            ctx.state.selected_view_item_index -= 1

        elif maybe_input_action == InputAction.MOVE_CURSOR_DOWN:
            ctx.state.selected_view_item_index += 1

        elif maybe_input_action == InputAction.NEW_DRAFT:
            ctx.state = DraftingNode(
                tree_view_index=ctx.state.selected_view_item_index + 1,
                selected_rune_index=0,
            )
            # parent_view_item=tree_view[ctx.state.selected_view_item_index],
            # draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,
            # selected_owned_rune_index=0,
            # starting_draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,

    elif isinstance(ctx.state, DraftingNode):
        if maybe_input_action == InputAction.SELECT_PREV_RUNE:
            ctx.state.selected_rune_index -= 1

        elif maybe_input_action == InputAction.SELECT_NEXT_RUNE:
            ctx.state.selected_rune_index += 1

        elif maybe_input_action == InputAction.CONFIRM_DRAFT:
            pass  # TODO: implement me

        elif maybe_input_action == InputAction.CANCEL_DRAFT:
            pass  # TODO: implement me

        elif maybe_input_action == InputAction.MOVE_DRAFT_UP:
            pass  # TODO: implement me

        elif maybe_input_action == InputAction.MOVE_DRAFT_DOWN:
            pass  # TODO: implement me

    # match maybe_input_action:
    #     case InputAction.NEW_DRAFT:
    #         assert isinstance(ctx.state, NavigatingTree)
    #         ctx.state = DraftingNode(
    #             parent_view_item=tree_view[ctx.state.selected_view_item_index],
    #             draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,
    #             selected_owned_rune_index=0,
    #             starting_draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,
    #         )

    #     case InputAction.CONFIRM_DRAFT:
    #         assert isinstance(ctx.state, DraftingNode)

    #         diff = (
    #             ctx.state.draft_node_index_in_tree_view
    #             - ctx.state.starting_draft_node_index_in_tree_view
    #         )

    #         ctx.state.parent_view_item.node.children.insert(
    #             diff, Node(rune=ctx.owned_runes[ctx.state.selected_owned_rune_index])
    #         )
    #         # Update tree this frame
    #         tree_view = generate_tree_view(ctx)

    #         _ = ctx.owned_runes.pop(ctx.state.selected_owned_rune_index)

    #         # revert back to pre-draft position
    #         ctx.state = NavigatingTree(ctx.state.draft_node_index_in_tree_view)

    #     case InputAction.CANCEL_DRAFT:
    #         assert isinstance(ctx.state, DraftingNode)
    #         # This ensures the cursor is restored
    #         # to it's pre-drafting position
    #         prev_index_in_tree_view: int = ctx.state.draft_node_index_in_tree_view - 1
    #         ctx.state = NavigatingTree(prev_index_in_tree_view)

    #     case InputAction.MOVE_DRAFT_UP:
    #         assert isinstance(ctx.state, DraftingNode)

    #         child_index = tree_view_index_to_node_child_index(ctx.state)
    #         children_count = len(ctx.state.parent_view_item.node.children)
    #         is_not_first_child = child_index > children_count

    #         if is_not_first_child:
    #             ctx.state.draft_node_index_in_tree_view -= 1

    #     case InputAction.MOVE_DRAFT_DOWN:
    #         assert isinstance(ctx.state, DraftingNode)
    #         diff = (
    #             ctx.state.draft_node_index_in_tree_view
    #             - ctx.state.starting_draft_node_index_in_tree_view
    #         )

    #         child_index = tree_view_index_to_node_child_index(ctx.state)
    #         children_count = len(ctx.state.parent_view_item.node.children)
    #         is_not_last_child = child_index < children_count

    #         if is_not_last_child:
    #             ctx.state.draft_node_index_in_tree_view += 1

    # --- Debugging section ---
    # if isinstance(ctx.state, DraftingNode):
    #     foo = (
    #         ctx.state.draft_node_index_in_tree_view
    #         - ctx.state.starting_draft_node_index_in_tree_view
    #     )
    #     ctx.debug_line = str(foo)

    # This injects the extra ghost draft node into the tree
    # before rendering, so that it doesn't physically exist
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
            # node label
            text = item.node.rune.data.display_name
            main_label_color = rune_rarity_color(item.node.rune.rarity)
            text_segments.append(RichText(text, main_label_color))

            # branch (current/max) display
            current_branches: int = len(item.node.children)
            max_branches: int = rune_rarity_max_branch_count(item.node.rune.rarity)
            text_segments.append(
                RichText(f" ({current_branches}/{max_branches})", main_label_color)
            )

            # stat display
            stat_displays: list[str] = []
            stat_points = item.node.rune.data.points
            stat_mult = item.node.rune.data.mult

            if stat_points >= 1:
                stat_displays.append(f"+{stat_points} points")
            if stat_mult >= 2:
                stat_displays.append(f"+{stat_mult} mult")

            desc_text: str = " ".join(stat_displays)
            text_segments.append(RichText(f"  ({desc_text})", RGBA(1.0, 1.0, 1.0, 0.4)))
        elif item_is_ghost:
            min_alpha: float = 0.3
            max_alpha: float = 1.0

            # node label
            text = item.node.rune.data.display_name
            main_label_color = rune_rarity_color(item.node.rune.rarity)
            main_label_color.a = 0.3 + (max_alpha - min_alpha) * (
                math.sin(5.0 * ctx.tick_count * delta_time) * 0.5 + 0.5
            )
            text_segments.append(RichText(text, main_label_color))

            # branch (current/max) display
            current_branches = len(item.node.children)
            max_branches = rune_rarity_max_branch_count(item.node.rune.rarity)
            text_segments.append(
                RichText(f" ({current_branches}/{max_branches})", main_label_color)
            )

            # stat display
            stat_displays = []
            stat_points = item.node.rune.data.points
            stat_mult = item.node.rune.data.mult

            if stat_points >= 1:
                stat_displays.append(f"+{stat_points} points")
            if stat_mult >= 2:
                stat_displays.append(f"+{stat_mult} mult")

            desc_text = " ".join(stat_displays)
            text_segments.append(RichText(f"  ({desc_text})", RGBA(1.0, 1.0, 1.0, 0.4)))
        else:
            text = item.node.rune.data.display_name
            main_label_color = rune_rarity_color(item.node.rune.rarity)
            main_label_color.a *= 0.5
            text_segments.append(RichText(text, main_label_color))

        print_at(2 * item.depth, index, text_segments)

    # dev: state debug display
    print_at(1, 28, RichText(f"State: {ctx.state.__class__.__name__}"))

    # universal debug line
    print_at(1, 29, RichText(ctx.debug_line, RGBA(1.0, 0.0, 0.0, 1.0)))

    # --- Carousel: keep selected item centered and shift neighbors around it ---
    # if isinstance(ctx.state, DraftingNode) and ctx.owned_runes:
    #     render_carousel(ctx, print_at)

    # --- FPS Counter ---
    update_fps_counter(fps_counter, delta_time)
    render_fps_counter(
        ctx.terminal,
        ctx.screen,
        fps_counter,
    )

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
        node_tree=Node(Rune(RuneRarity.COMMON, RuneData(5, 1, "X Pik"))),
    )
    fps_counter = FPSCounter()

    # TODO: remove this later
    # temp node tree rendering testing
    # ctx.node_tree.children.extend(
    #     [
    #         Node(
    #             Rune(
    #                 RuneRarity.COMMON,
    #                 RuneData(5, 1, "Pik"),
    #             )
    #         ),
    #     ]
    # )

    # temp initial inventory for testing
    ctx.owned_runes = [
        Rune(RuneRarity.COMMON, RuneData(20, 1, "Pik")),
        Rune(RuneRarity.COMMON, RuneData(3, 2, "Vek")),
        Rune(RuneRarity.COMMON, RuneData(3, 2, "Vek")),
        Rune(RuneRarity.COMMON, RuneData(3, 2, "Vek")),
        Rune(RuneRarity.COMMON, RuneData(3, 2, "Vek")),
    ]

    fill_screen_background(terminal, screen, BACKGROUND_COLOR)
    fps_limiter = create_fps_limiter(144)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        delta_time: float = 0.0

        while True:
            tick_outcome: ProgramStatus = tick(ctx, delta_time, print_at, fps_counter)
            if tick_outcome == ProgramStatus.EXIT:
                break

            ctx.tick_count += 1
            delta_time = fps_limiter()


if __name__ == "__main__":
    main()

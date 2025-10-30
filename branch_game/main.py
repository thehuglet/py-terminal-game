from __future__ import annotations

from copy import copy
from enum import Enum, auto
from functools import partial
from typing import Callable

from blessed import Terminal
from blessed.keyboard import Keystroke

import branch_game.ezterm as ezterm
from branch_game.data import RUNE_RARITY_COLOR, RUNE_RARITY_MAX_BRANCH_COUNT
from branch_game.ezterm import BACKGROUND_COLOR, RichText, fill_screen_background
from branch_game.fps_limiter import create_fps_limiter
from branch_game.models import (
    AppContext,
    DraftingNode,
    GameState,
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


class InputAction(Enum):
    TREE_NAV_MOVE_UP = auto()
    TREE_NAV_MOVE_DOWN = auto()
    DRAFT_NEW_BRANCHING_NODE = auto()
    DRAFTING_NODEq_MOVE_PREV_RUNE = auto()
    DRAFTING_NODE_MOVE_NEXT_RUNE = auto()
    CONFIRM_NODE_DRAFT = auto()


def translate_input(
    key: Keystroke,
    state: GameState,
    owned_runes: list[Rune],
    tree_view: list[TreeViewItem],
) -> tuple[InputAction, type[GameState]] | None:
    if isinstance(state, NavigatingTree):
        selected_item_index = state.selected_view_item_index
        can_move_up: bool = selected_item_index > 0
        can_move_down: bool = selected_item_index < (len(tree_view)) - 1

        selected_node: Node = tree_view[selected_item_index].node
        max_allowed_branches: int = RUNE_RARITY_MAX_BRANCH_COUNT[selected_node.rune.rarity]
        can_add_branch: bool = len(selected_node.children) < max_allowed_branches

        if key.name == "KEY_UP" and can_move_up:
            return (InputAction.TREE_NAV_MOVE_UP, NavigatingTree)

        if key.name == "KEY_DOWN" and can_move_down:
            return (InputAction.TREE_NAV_MOVE_DOWN, NavigatingTree)

        if key == "b" and can_add_branch and len(owned_runes) > 0:
            return (InputAction.DRAFT_NEW_BRANCHING_NODE, NavigatingTree)

    if isinstance(state, DraftingNode):
        rune_index = state.selected_owned_rune_index
        can_move_prev_rune: bool = rune_index > 0
        can_move_next_rune: bool = rune_index < len(owned_runes) - 1

        if key.name == "KEY_ENTER":
            return (InputAction.CONFIRM_NODE_DRAFT, DraftingNode)

        if key.name == "KEY_LEFT" and can_move_prev_rune:
            return (InputAction.DRAFTING_NODE_MOVE_PREV_RUNE, DraftingNode)

        if key.name == "KEY_RIGHT" and can_move_next_rune:
            return (InputAction.DRAFTING_NODE_MOVE_NEXT_RUNE, DraftingNode)

    return None


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

    tree_view: list[TreeViewItem] = generate_tree_view(ctx)

    # --- Hotkey to input action mapping ---
    maybe_input_action: InputAction | None = translate_input(
        key, ctx.state, ctx.owned_runes, tree_view
    )

    # --- Input action execution ---
    match (ctx.state, maybe_input_action):
        case (NavigatingTree() as state, InputAction.TREE_NAV_MOVE_UP):
            state.selected_view_item_index -= 1

        case (NavigatingTree() as state, InputAction.TREE_NAV_MOVE_DOWN):
            state.selected_view_item_index += 1

        # case (NavigatingTree() as state, InputAction)

        # case _:
        #     pass

    # if (maybe_input_action := action) is InputAction.TREE_NAV_MOVE_UP:
    #     assert isinstance(ctx.state, NavigatingTree)
    #     ctx.state.selected_view_item_index -= 1

    # elif maybe_input_action is InputAction.TREE_NAV_MOVE_DOWN:
    #     assert isinstance(ctx.state, NavigatingTree)
    #     ctx.state.selected_view_item_index += 1

    # elif maybe_input_action is InputAction.DRAFT_NEW_BRANCHING_NODE:
    #     assert isinstance(ctx.state, NavigatingTree)

    #     ctx.state = DraftingNode(
    #         tree_view[ctx.state.selected_view_item_index],
    #         draft_node_index_in_tree_view=ctx.state.selected_view_item_index + 1,
    #         selected_owned_rune_index=0,
    #     )

    # elif maybe_input_action is InputAction.DRAFTING_NODE_MOVE_PREV_RUNE:
    #     assert isinstance(ctx.state, DraftingNode)
    #     ctx.state.selected_owned_rune_index -= 1

    # elif maybe_input_action is InputAction.DRAFTING_NODE_MOVE_NEXT_RUNE:
    #     assert isinstance(ctx.state, DraftingNode)
    #     ctx.state.selected_owned_rune_index += 1

    # elif maybe_input_action is InputAction.CONFIRM_NODE_DRAFT:
    #     assert isinstance(ctx.state, DraftingNode)

    # --- Additional per-tick logic ---
    if isinstance(ctx.state, DraftingNode):
        depth: int = ctx.state.parent.depth + 1
        tree_view.insert(
            ctx.state.draft_node_index_in_tree_view,
            TreeViewItem(Node(ctx.owned_runes[ctx.state.selected_owned_rune_index]), depth),
        )

    # --- Rendering of the tree ---
    for index, item in enumerate(tree_view):
        text_segments: list[RichText] = []

        if isinstance(ctx.state, NavigatingTree) and ctx.state.selected_view_item_index == index:
            text = item.node.rune.data.display_name
            color = copy(RUNE_RARITY_COLOR[item.node.rune.rarity])
            text_segments.append(RichText(text, color))
        else:
            text = item.node.rune.data.display_name
            color = copy(RUNE_RARITY_COLOR[item.node.rune.rarity])
            color.a *= 0.5
            text_segments.append(RichText(text, color))

        print_at(2 * item.depth, index, text_segments)

    # --- Carousel: keep selected item centered and shift neighbors around it ---
    if isinstance(ctx.state, DraftingNode) and ctx.owned_runes:
        sel = ctx.state.selected_owned_rune_index
        total = len(ctx.owned_runes)
        side = 2  # how many items to show per side
        gap = 3
        y = 20

        screen_center_x = ctx.screen.width // 2

        # Selected rune (always centered)
        sel_name = ctx.owned_runes[sel].data.display_name
        sel_x = int(screen_center_x - (len(sel_name) // 2))
        sel_color = copy(RUNE_RARITY_COLOR[ctx.owned_runes[sel].rarity])
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
            color = copy(RUNE_RARITY_COLOR[ctx.owned_runes[idx].rarity])
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
            color = copy(RUNE_RARITY_COLOR[ctx.owned_runes[idx].rarity])
            color.a *= alpha
            # compute start x for this name (we place names leftwards)
            x_left -= len(name)
            if x_left + len(name) > 0 and x_left < ctx.screen.width:
                print_at(x_left, y, RichText(name, color))
            x_left -= gap

    flush_diffs(ctx.terminal, buffer_diff(ctx.screen))
    return AppStatus.RUNNING


def main() -> None:
    terminal = Terminal()
    screen = Screen(terminal.width, terminal.height)
    print_at = partial(ezterm.print_at, terminal, screen)
    ctx = AppContext(
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
        Rune(RuneRarity.COMMON, RuneData(10, "booper")),
        Rune(RuneRarity.COMMON, RuneData(3, "bar")),
        Rune(RuneRarity.UNCOMMON, RuneData(30, "loooooool")),
        Rune(RuneRarity.RARE, RuneData(23, "a")),
        Rune(RuneRarity.UNCOMMON, RuneData(69, "Eren uwu")),
    ]

    fill_screen_background(terminal, screen, BACKGROUND_COLOR)
    fps_limiter = create_fps_limiter(60)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        delta_time: float = 0.0

        while True:
            tick_outcome: AppStatus = tick(ctx, delta_time, print_at)
            if tick_outcome == AppStatus.EXIT:
                break

            delta_time = fps_limiter()


if __name__ == "__main__":
    main()

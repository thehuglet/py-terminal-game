from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from blessed import Terminal
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs
from branch_game.ezterm import RichText, print_at
from branch_game.fps_limiter import create_fps_limiter
from typing import cast

terminal = Terminal()
screen = Screen(terminal.width, terminal.height)

RGB = tuple[int, int, int]


class TickOutcome(Enum):
    RUNNING = auto()
    EXIT = auto()


class State(Enum):
    BASE_PLACEHOLDER = auto()
    ADD_BRANCH_PENDING = auto()


@dataclass
class Branch:
    # parent: Branch | None = None
    children: list[Branch] = field(default_factory=list)


@dataclass
class BranchDisplay:
    branch: Branch | None
    depth: int
    is_pending: bool = False


@dataclass
class PendingBranch:
    parent: Branch | None
    index: int
    depth: int


@dataclass
class Context:
    root_branch: Branch | None = None

    state: State = field(default=State.BASE_PLACEHOLDER, init=False)
    selected_branch_index: int = field(default=0, init=False)
    branch_displays: list[BranchDisplay] = field(default_factory=list)
    pending_branch: PendingBranch | None = None
    debug_msg: str = ""


def t_print(x: int, y: int, text: RichText) -> None:
    """Print helper"""
    return print_at(screen, terminal, x, y, text)


def update_visual_branches(ctx: Context):
    ctx.branch_displays = generate_branch_displays(ctx)


def generate_branch_displays(ctx: Context) -> list[BranchDisplay]:
    branch_displays: list[BranchDisplay] = []

    if branch := ctx.root_branch:

        def walk_tree(branch: Branch, depth: int = 0) -> list[BranchDisplay]:
            out = [BranchDisplay(branch, depth)]
            for child in branch.children:
                out.extend(walk_tree(child, depth + 1))
            return out

        branch_displays.extend(walk_tree(branch))

    if ctx.pending_branch:
        index = ctx.pending_branch.index
        depth = ctx.pending_branch.depth
        pending_branch = BranchDisplay(None, depth, True)
        branch_displays.insert(index, pending_branch)

    return branch_displays


def tick(ctx: Context) -> TickOutcome:
    key = terminal.inkey(timeout=0.1)

    if key == "q":
        return TickOutcome.EXIT

    if ctx.state == State.BASE_PLACEHOLDER:
        can_move_up: bool = ctx.selected_branch_index > 0
        can_move_down: bool = ctx.selected_branch_index < (len(ctx.branch_displays)) - 1

        if key.name == "KEY_UP" and can_move_up:
            ctx.selected_branch_index -= 1
        elif key.name == "KEY_DOWN" and can_move_down:
            ctx.selected_branch_index += 1
        elif key == "b":
            if ctx.root_branch:
                selected_branch_display = ctx.branch_displays[ctx.selected_branch_index]
                ctx.pending_branch = PendingBranch(
                    parent=selected_branch_display.branch,
                    index=ctx.selected_branch_index + 1,
                    depth=selected_branch_display.depth + 1,
                )
            else:
                ctx.pending_branch = PendingBranch(
                    parent=None,
                    index=0,
                    depth=0,
                )

            update_visual_branches(ctx)
            ctx.state = State.ADD_BRANCH_PENDING
            ctx.debug_msg = str(ctx.branch_displays)

    elif ctx.state == State.ADD_BRANCH_PENDING:
        if key.name == "KEY_ENTER":
            if ctx.pending_branch:
                new_branch = Branch()

                if parent_branch := ctx.pending_branch.parent:
                    parent_branch.children.insert(0, new_branch)
                else:
                    # This handles the case of a branch at the root
                    ctx.root_branch = new_branch

            # clears the pending draft
            ctx.pending_branch = None
            update_visual_branches(ctx)

            ctx.state = State.BASE_PLACEHOLDER

    # rendering
    for index, branch_display in enumerate(ctx.branch_displays):
        text = RichText("branch", color=(155, 155, 155))

        is_selected: bool = index == ctx.selected_branch_index

        if is_selected and ctx.state != State.ADD_BRANCH_PENDING:
            text.color = (255, 255, 150)

        if branch_display.is_pending:
            text.color = (75, 120, 155)

        t_print(2 * branch_display.depth, index, text)

    t_print(0, 20, RichText(ctx.debug_msg))

    flush_diffs(terminal, buffer_diff(screen))
    return TickOutcome.RUNNING


def main():
    ctx = Context()
    fps_limiter = create_fps_limiter(60)

    with terminal.cbreak(), terminal.hidden_cursor(), terminal.fullscreen():
        while True:
            tick_outcome = tick(ctx)
            if tick_outcome == TickOutcome.EXIT:
                break

            _ = fps_limiter()


if __name__ == "__main__":
    main()

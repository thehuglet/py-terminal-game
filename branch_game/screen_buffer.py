import sys
from copy import deepcopy
from dataclasses import dataclass, field

from blessed import Terminal

# A cell is a tuple of (character, ANSI style string)
ScreenCell = tuple[str, str]


@dataclass
class ScreenBuffer:
    width: int
    height: int
    cells: list[list[ScreenCell]]


@dataclass
class Screen:
    width: int
    height: int
    old_buffer: ScreenBuffer = field(init=False)
    new_buffer: ScreenBuffer = field(init=False)

    def __post_init__(self):
        self.old_buffer = create_buffer(self.width, self.height)
        self.new_buffer = create_buffer(self.width, self.height)


def create_buffer(width: int, height: int) -> ScreenBuffer:
    cells = [[(" ", "") for _ in range(width)] for _ in range(height)]
    return ScreenBuffer(width=width, height=height, cells=cells)


def draw_to_buffer(buffer: ScreenBuffer) -> None:
    """Example frame drawing logic."""
    width, height = buffer.width, buffer.height
    cells = buffer.cells

    for x in range(width):
        cells[0][x] = ("─", "")
        cells[height - 1][x] = ("─", "")
    for y in range(height):
        cells[y][0] = ("│", "")
        cells[y][width - 1] = ("│", "")
    cells[0][0] = ("┌", "")
    cells[0][width - 1] = ("┐", "")
    cells[height - 1][0] = ("└", "")
    cells[height - 1][width - 1] = ("┘", "")

    label = "Hello, Screen Buffer!"
    x_start = max((width - len(label)) // 2, 1)
    y = height // 2
    for i, char in enumerate(label):
        if 0 <= x_start + i < width:
            cells[y][x_start + i] = (char, "")

def buffer_diff(screen: Screen) -> list[tuple[int, int, ScreenCell]]:
    old: ScreenBuffer = screen.old_buffer
    new: ScreenBuffer = screen.new_buffer

    diffs: list[tuple[int, int, ScreenCell]] = []
    for y in range(new.height):
        for x in range(new.width):
            if old.cells[y][x] != new.cells[y][x]:
                diffs.append((y, x, new.cells[y][x]))

    screen.old_buffer = deepcopy(new)  # full frame copy
    screen.new_buffer = create_buffer(screen.width, screen.height)

    return diffs


def flush_diffs(term: Terminal, diffs: list[tuple[int, int, ScreenCell]]) -> None:
    output: list[str] = []
    for y, x, (char, style) in diffs:
        output.append(term.move(y, x) + style + char)
    _ = sys.stdout.write("".join(output))
    _ = sys.stdout.flush()

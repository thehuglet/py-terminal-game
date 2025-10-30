from dataclasses import dataclass, field
from typing import cast
from blessed import Terminal
from numpy.typing import NDArray
from branch_game.screen_buffer import Screen, ScreenBuffer
import numpy as np


@dataclass
class RGBA:
    r: float
    g: float
    b: float
    a: float

    def __getitem__(self, key: int | slice) -> float | tuple[float, ...]:
        components = (self.r, self.g, self.b, self.a)
        return components[key]


BACKGROUND_COLOR = RGBA(0.0, 0.0, 0.0, 1.0)


@dataclass
class RichText:
    text: str
    color: RGBA = field(default_factory=lambda: RGBA(1.0, 1.0, 1.0, 1.0))
    bold: bool = False
    bg: RGBA | None = None


def _make_style(term: Terminal, fg: RGBA, bg: RGBA | None, bold: bool) -> str:
    if not term.does_styling:
        return term.normal

    fg_str = term.color_rgb(*_rgba_to_rgb_int(fg))
    maybe_bold_str: str = term.bold if bold else ""
    style: str = (
        term.normal
        + maybe_bold_str
        + fg_str
        + term.on_color_rgb(*_rgba_to_rgb_int(BACKGROUND_COLOR))
    )
    return style


def _rgba_to_rgb_int(col_rgba: RGBA) -> tuple[int, int, int]:
    col_rgb = np.array(col_rgba[:3], dtype=np.float64)
    alpha = cast(float, col_rgba[3])

    # scale and round
    scaled: NDArray[np.int_] = np.clip(np.round(col_rgb * alpha * 255), 0, 255).astype(int)

    r, g, b = scaled  # pyright:ignore[reportAny]
    return r, g, b


def fill_screen_background(terminal: Terminal, screen: Screen, color: RGBA):
    bg_style = terminal.on_color_rgb(*_rgba_to_rgb_int(color))

    for y in range(screen.new_buffer.height):
        for x in range(screen.new_buffer.width):
            screen.new_buffer.cells[y][x] = (" ", bg_style)


def print_at(
    term: Terminal, screen: Screen, x: int, y: int, text: RichText | list[RichText]
) -> None:
    """Draws rich text into the screen buffer at (x, y). Each character is styled individually."""
    buffer: ScreenBuffer = screen.new_buffer

    # Normalize text to list in case of RichText for simplicity
    if isinstance(text, RichText):
        text = [text]

    if not (0 <= y < buffer.height):
        return  # Y out of bounds

    px = x  # track horizontal position across segments
    cells = buffer.cells

    for text_segment in text:
        style = _make_style(term, text_segment.color, text_segment.bg, text_segment.bold)
        for char in text_segment.text:
            if 0 <= px < buffer.width:
                cells[y][px] = (char, style)
            px += 1

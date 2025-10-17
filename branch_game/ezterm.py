from dataclasses import dataclass, field
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


@dataclass
class RichText:
    text: str
    color: RGBA = field(default_factory=lambda: RGBA(1.0, 1.0, 1.0, 1.0))
    bg: RGBA | None = None


def _make_style(term: Terminal, fg: RGBA, bg: RGBA | None) -> str:
    if not term.does_styling:
        style = ""
    else:
        fg_str = term.color_rgb(*_rgba_to_rgb_int(fg))
        bg_str = term.on_color_rgb(*_rgba_to_rgb_int(bg)) if bg else ""
        style = fg_str + bg_str
    return style


def _rgba_to_rgb_int(col_rgba: RGBA) -> tuple[int, int, int]:
    """This returns RGB in ints because blessed uses ints."""
    col_rgb = col_rgba[:3]
    alpha = col_rgba[3]

    col_rgb_scaled: NDArray[np.float64] = np.array(col_rgb) * alpha
    col_rgb_int: NDArray[np.int32] = np.clip(np.round(col_rgb_scaled * 255).astype(int), 0, 255)
    return tuple(col_rgb_int)


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
        style = _make_style(term, text_segment.color, text_segment.bg)
        for char in text_segment.text:
            if 0 <= px < buffer.width:
                cells[y][px] = (char, style)
            px += 1

# rich_terminal.py

from dataclasses import dataclass
from typing import Tuple, Optional
from blessed import Terminal
from branch_game.screen_buffer import ScreenBuffer, ScreenCell

RGB = Tuple[int, int, int]

@dataclass(frozen=True)
class RichText:
    text: str
    color: RGB
    bg: Optional[RGB] = None

# Internal style cache
_style_cache: dict[Tuple[RGB, Optional[RGB]], str] = {}

def _make_style(term: Terminal, fg: RGB, bg: Optional[RGB]) -> str:
    key = (fg, bg)
    if key in _style_cache:
        return _style_cache[key]

    if not term.does_styling:
        style = ""
    else:
        fg_str = term.color_rgb(*fg)
        bg_str = term.on_color_rgb(*bg) if bg else ""
        style = fg_str + bg_str

    _style_cache[key] = style
    return style

def draw_text(buffer: ScreenBuffer, term: Terminal, x: int, y: int, rich: RichText) -> None:
    """
    Draws rich text into the screen buffer at (x, y).
    Each character of the string is styled individually (same style).
    """
    if not (0 <= y < buffer.height):
        return  # Y out of bounds

    style = _make_style(term, rich.color, rich.bg)
    cells = buffer.cells

    for i, char in enumerate(rich.text):
        px = x + i
        if 0 <= px < buffer.width:
            cells[y][px] = (char, style)

from dataclasses import dataclass, field
from blessed import Terminal
from branch_game.screen_buffer import Screen, ScreenBuffer

RGB = tuple[int, int, int]


@dataclass
class RichText:
    text: str
    color: RGB = field(default=(255, 255, 255))
    bg: RGB | None = None


def _make_style(term: Terminal, fg: RGB, bg: RGB | None) -> str:
    if not term.does_styling:
        style = ""
    else:
        fg_str = term.color_rgb(*fg)
        bg_str = term.on_color_rgb(*bg) if bg else ""
        style = fg_str + bg_str
    return style


def print_at(term: Terminal, screen: Screen, x: int, y: int, text: RichText) -> None:
    """
    Draws rich text into the screen buffer at (x, y).
    Each character of the string is styled individually (same style).
    """
    buffer: ScreenBuffer = screen.new_buffer

    if not (0 <= y < buffer.height):
        return  # Y out of bounds

    style = _make_style(term, text.color, text.bg)
    cells = buffer.cells

    for i, char in enumerate(text.text):
        px = x + i
        if 0 <= px < buffer.width:
            cells[y][px] = (char, style)

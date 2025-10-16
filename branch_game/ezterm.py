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


def print_at(term: Terminal, screen: Screen, x: int, y: int, text: RichText | list[RichText]) -> None:
    """ Draws rich text into the screen buffer at (x, y). Each character is styled individually. """
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

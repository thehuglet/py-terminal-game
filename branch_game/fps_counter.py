from blessed import Terminal

from branch_game.ezterm import RGBA, RichText, print_at
from branch_game.models import FPSCounter
from branch_game.screen_buffer import Screen


def update_fps_counter(fps: FPSCounter, dt: float) -> None:
    if dt <= 0.0:
        return
    inst = 1.0 / dt
    if fps.ema <= 0.0:
        fps.ema = inst
    else:
        fps.ema = fps.ema * (1.0 - fps.alpha) + inst * fps.alpha


def render_fps_counter(
    terminal: Terminal,
    screen: Screen,
    fps: FPSCounter,
    screen_width: int,
) -> None:
    s = f"{fps.ema:5.1f} FPS"
    x = max(0, screen_width - len(s) - 1)
    color = RGBA(1.0, 1.0, 1.0, 1.0)
    color.a = 1.0
    print_at(terminal, screen, x, 0, RichText(s, color, bold=True))

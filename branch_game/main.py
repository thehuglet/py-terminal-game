from typing import Callable
from blessed import Terminal
from branch_game.screen_buffer import Screen, buffer_diff, flush_diffs
from branch_game.ezterm import RichText, print_at
from branch_game.fps_limiter import create_fps_limiter

terminal = Terminal()
screen = Screen(terminal.width, terminal.height)

def t_print(x: int, y: int, rich: RichText) -> None:
    """Print helper"""
    return print_at(screen, terminal, x, y, rich)

def tick() -> bool:
    inp = terminal.inkey(timeout=0.1)
    if inp.lower() == 'q':
        return False

    t_print(0, 1, RichText("hello"))

    flush_diffs(terminal, buffer_diff(screen))

    return True


def main():
    fps_limiter = create_fps_limiter(60)

    print(terminal.enter_fullscreen())
    print(terminal.hide_cursor())
    print(terminal.clear())

    with (
        terminal.cbreak(),
        terminal.hidden_cursor(),
        terminal.fullscreen()
    ):
        while True:
            running = tick()

            if not running:
                break

            _ = fps_limiter()

            # Handle input
            # inp = terminal.inkey(timeout=0.1)
            # if inp.lower() == 'q':
            # 	break
            # elif inp.code == terminal.KEY_UP and direction != (0, 1):
            # 	direction = (0, -1)
            # elif inp.code == terminal.KEY_DOWN and direction != (0, -1):
            # 	direction = (0, 1)
            # elif inp.code == terminal.KEY_LEFT and direction != (1, 0):
            # 	direction = (-1, 0)
            # elif inp.code == terminal.KEY_RIGHT and direction != (-1, 0):
            # 	direction = (1, 0)


if __name__ == "__main__":
    main()

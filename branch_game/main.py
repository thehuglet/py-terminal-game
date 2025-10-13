# snake_game.py

import time
import random
from blessed import Terminal
from branch_game.screen_buffer import Screen, create_buffer, buffer_diff, flush_diffs
from branch_game.ezterm import RichText, draw_text

# TODO: use functools.partial to make drawing less boilerplatey

def main():
    term = Terminal()
    width, height = term.width, term.height

    print(term.enter_fullscreen())
    print(term.hide_cursor())
    print(term.clear())

    screen = Screen(width, height)
    # old_buf = create_buffer(width, height)
    # new_buf = create_buffer(width, height)

    snake = [(width // 2, height // 2)]
    direction = (1, 0)  # start moving right
    food = None

    def place_food():
        while True:
            fx = random.randint(1, width - 2)
            fy = random.randint(1, height - 2)
            if (fx, fy) not in snake:
                return (fx, fy)

    food = place_food()

    with term.cbreak(), term.hidden_cursor():
        while True:
            # # Clear new buffer
            # new_buf = create_buffer(width, height)

            # Draw border frame with draw_text()
            top_border = "┌" + "─" * (width - 2) + "┐"
            bottom_border = "└" + "─" * (width - 2) + "┘"
            draw_text(, term, 0, 0, RichText(top_border, (255, 255, 255)))
            draw_text(new_buf, term, 0, height - 1, RichText(bottom_border, (255, 255, 255)))

            for y in range(1, height - 1):
                draw_text(new_buf, term, 0, y, RichText("│", (255, 255, 255)))
                draw_text(new_buf, term, width - 1, y, RichText("│", (255, 255, 255)))

            # Draw snake (green blocks)
            for x, y in snake:
                draw_text(new_buf, term, x, y, RichText("█", (0, 200, 0)))

            # Draw food (red circle)
            fx, fy = food
            draw_text(new_buf, term, fx, fy, RichText("●", (255, 50, 50)))

            # Compute and flush diffs
            diffs = buffer_diff(screen)
            flush_diffs(term, diffs)
            old_buf = new_buf

            # Handle input
            inp = term.inkey(timeout=0.1)
            if inp.lower() == 'q':
                break
            elif inp.code == term.KEY_UP and direction != (0, 1):
                direction = (0, -1)
            elif inp.code == term.KEY_DOWN and direction != (0, -1):
                direction = (0, 1)
            elif inp.code == term.KEY_LEFT and direction != (1, 0):
                direction = (-1, 0)
            elif inp.code == term.KEY_RIGHT and direction != (-1, 0):
                direction = (1, 0)

            # Move snake
            head_x, head_y = snake[0]
            dx, dy = direction
            new_head = (head_x + dx, head_y + dy)

            # Check collisions with walls or self
            if (new_head[0] <= 0 or new_head[0] >= width - 1 or
                new_head[1] <= 0 or new_head[1] >= height - 1 or
                new_head in snake):
                # Game Over
                game_over_text = " GAME OVER "
                draw_text(new_buf, term,
                          max((width - len(game_over_text)) // 2, 0),
                          height // 2,
                          RichText(game_over_text, (255, 0, 0)))
                # flush_diffs(term, buffer_diff(old_buf, new_buf))
                flush_diffs(term, buffer_diff(screen))
                break

            snake.insert(0, new_head)

            # Check if food eaten
            if new_head == food:
                food = place_food()
            else:
                snake.pop()  # remove tail

    print(term.normal_cursor())
    print(term.exit_fullscreen())
    print(term.clear())

if __name__ == "__main__":
    main()

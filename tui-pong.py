#!/usr/bin/env python3

import os
import sys
import time
import random
import shutil

FPS = 60
FRAME_TIME = 1.0 / FPS

PADDLE_HEIGHT = 5
PADDLE_MARGIN = 3
WIN_SCORE = 10

PLAYER_SPEED = 1.5
AI_SPEED = 0.55


class Terminal:
    def __init__(self):
        self.windows = os.name == "nt"
        self.old_settings = None

    def __enter__(self):
        if not self.windows:
            import termios
            import tty

            self.old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())

        sys.stdout.write("\x1b[?1049h")  # alternate screen
        sys.stdout.write("\x1b[?25l")    # hide cursor
        sys.stdout.write("\x1b[2J")
        sys.stdout.flush()

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.windows and self.old_settings:
            import termios
            termios.tcsetattr(
                sys.stdin,
                termios.TCSADRAIN,
                self.old_settings,
            )

        sys.stdout.write("\x1b[?25h")
        sys.stdout.write("\x1b[?1049l")
        sys.stdout.flush()

    def keys(self):
        if self.windows:
            return self._windows_keys()

        return self._unix_keys()

    def _windows_keys(self):
        import msvcrt

        result = []

        while msvcrt.kbhit():
            ch = msvcrt.getwch()

            if ch in ("\x00", "\xe0"):
                # Consume special-key code even though Pong does not use it.
                msvcrt.getwch()
            else:
                result.append(ch.lower())

        return result

    def _unix_keys(self):
        import select

        result = []

        while select.select([sys.stdin], [], [], 0)[0]:
            ch = sys.stdin.read(1)

            if ch == "\x1b":
                result.append("ESC")
            else:
                result.append(ch.lower())

        return result


class Pong:
    def __init__(self):
        self.left_score = 0
        self.right_score = 0

        self.width = 0
        self.height = 0

        self.left_y = 0.0
        self.right_y = 0.0

        self.ball_x = 0.0
        self.ball_y = 0.0

        self.ball_dx = 1.0
        self.ball_dy = 0.0

        self.running = True
        self.message = ""

        self.resize()
        self.reset_ball()

    def resize(self):
        size = shutil.get_terminal_size((80, 24))

        self.width = max(40, size.columns)
        self.height = max(15, size.lines)

        play_height = self.height - 4

        if self.left_y == 0:
            self.left_y = play_height / 2
            self.right_y = play_height / 2

        max_y = self.bottom - PADDLE_HEIGHT

        self.left_y = min(max(self.left_y, self.top), max_y)
        self.right_y = min(max(self.right_y, self.top), max_y)

    @property
    def top(self):
        return 2

    @property
    def bottom(self):
        return self.height - 2

    @property
    def left_x(self):
        return PADDLE_MARGIN

    @property
    def right_x(self):
        return self.width - PADDLE_MARGIN - 1

    def reset_ball(self, direction=None):
        self.ball_x = self.width / 2
        self.ball_y = (self.top + self.bottom) / 2

        if direction is None:
            direction = random.choice((-1, 1))

        self.ball_dx = direction * 0.65
        self.ball_dy = random.uniform(-0.35, 0.35)

    def handle_input(self, keys):
        for key in keys:
            if key in ("q", "ESC"):
                self.running = False

            elif key == "w":
                self.left_y -= PLAYER_SPEED

            elif key == "s":
                self.left_y += PLAYER_SPEED

            elif key == "r":
                self.left_score = 0
                self.right_score = 0
                self.message = ""
                self.left_y = (self.top + self.bottom - PADDLE_HEIGHT) / 2
                self.right_y = self.left_y
                self.reset_ball()

        max_y = self.bottom - PADDLE_HEIGHT
        self.left_y = min(max(self.left_y, self.top), max_y)

    def update_ai(self):
        paddle_center = self.right_y + (PADDLE_HEIGHT - 1) / 2

        # Follow the ball while it is coming toward the AI.
        # Otherwise drift back toward the center.
        if self.ball_dx > 0:
            target = self.ball_y
        else:
            target = (self.top + self.bottom) / 2

        if target < paddle_center - 0.5:
            self.right_y -= AI_SPEED
        elif target > paddle_center + 0.5:
            self.right_y += AI_SPEED

        max_y = self.bottom - PADDLE_HEIGHT
        self.right_y = min(max(self.right_y, self.top), max_y)

    def update(self):
        self.update_ai()

        self.ball_x += self.ball_dx
        self.ball_y += self.ball_dy

        # Top / bottom wall
        if self.ball_y <= self.top:
            self.ball_y = self.top
            self.ball_dy = abs(self.ball_dy)

        elif self.ball_y >= self.bottom:
            self.ball_y = self.bottom
            self.ball_dy = -abs(self.ball_dy)

        # Left paddle
        if self.ball_dx < 0 and self.ball_x <= self.left_x + 1:
            if (
                self.left_y - 0.5
                <= self.ball_y
                <= self.left_y + PADDLE_HEIGHT - 0.5
            ):
                self.ball_x = self.left_x + 1
                self._bounce(self.left_y, direction=1)

        # Right paddle / AI
        if self.ball_dx > 0 and self.ball_x >= self.right_x - 1:
            if (
                self.right_y - 0.5
                <= self.ball_y
                <= self.right_y + PADDLE_HEIGHT - 0.5
            ):
                self.ball_x = self.right_x - 1
                self._bounce(self.right_y, direction=-1)

        # Score
        if self.ball_x < 0:
            self.right_score += 1
            self.check_winner()
            self.reset_ball(direction=-1)

        elif self.ball_x >= self.width:
            self.left_score += 1
            self.check_winner()
            self.reset_ball(direction=1)

    def _bounce(self, paddle_y, direction):
        paddle_center = paddle_y + (PADDLE_HEIGHT - 1) / 2

        offset = (
            self.ball_y - paddle_center
        ) / (PADDLE_HEIGHT / 2)

        speed = min(abs(self.ball_dx) * 1.05, 1.25)

        self.ball_dx = direction * speed
        self.ball_dy += offset * 0.25
        self.ball_dy = max(-0.8, min(0.8, self.ball_dy))

    def check_winner(self):
        if self.left_score >= WIN_SCORE:
            self.message = "YOU WIN - R to restart"
            self.left_score = 0
            self.right_score = 0

        elif self.right_score >= WIN_SCORE:
            self.message = "AI WINS - R to restart"
            self.left_score = 0
            self.right_score = 0

    def draw(self):
        self.resize()

        canvas = [
            [" "] * self.width
            for _ in range(self.height)
        ]

        score = f" TUI PONG   YOU {self.left_score} : {self.right_score} AI "
        score_x = max(0, (self.width - len(score)) // 2)

        for i, ch in enumerate(score):
            if score_x + i < self.width:
                canvas[0][score_x + i] = ch

        help_text = "W/S move   AI opponent   Q quit   R reset"
        help_x = max(0, (self.width - len(help_text)) // 2)

        for i, ch in enumerate(help_text):
            if help_x + i < self.width:
                canvas[1][help_x + i] = ch

        for x in range(self.width):
            canvas[self.top - 1][x] = "─"
            canvas[self.bottom + 1][x] = "─"

        center = self.width // 2

        for y in range(self.top, self.bottom + 1):
            if y % 2 == 0:
                canvas[y][center] = "│"

        for i in range(PADDLE_HEIGHT):
            ly = int(self.left_y) + i
            ry = int(self.right_y) + i

            if self.top <= ly <= self.bottom:
                canvas[ly][self.left_x] = "█"

            if self.top <= ry <= self.bottom:
                canvas[ry][self.right_x] = "█"

        bx = int(round(self.ball_x))
        by = int(round(self.ball_y))

        if 0 <= bx < self.width and 0 <= by < self.height:
            canvas[by][bx] = "●"

        if self.message:
            y = self.height // 2
            x = max(0, (self.width - len(self.message)) // 2)

            for i, ch in enumerate(self.message):
                if x + i < self.width:
                    canvas[y][x + i] = ch

        output = "\x1b[H" + "\n".join(
            "".join(row)
            for row in canvas
        )

        sys.stdout.write(output)
        sys.stdout.flush()


def main():
    game = Pong()

    with Terminal() as terminal:
        previous = time.perf_counter()
        accumulator = 0.0

        while game.running:
            now = time.perf_counter()
            delta = now - previous
            previous = now

            accumulator += delta

            game.handle_input(terminal.keys())

            while accumulator >= FRAME_TIME:
                game.update()
                accumulator -= FRAME_TIME

            game.draw()

            elapsed = time.perf_counter() - now
            sleep_time = FRAME_TIME - elapsed

            if sleep_time > 0:
                time.sleep(sleep_time)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

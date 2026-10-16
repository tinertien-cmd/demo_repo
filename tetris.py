"""俄罗斯方块。使用项目里的 venv 运行：venv/bin/python tetris.py"""

import random
import sys

import pygame

COLS = 10
ROWS = 20
CELL = 30
PANEL = 180
MARGIN = 20
WIDTH = MARGIN * 2 + COLS * CELL + PANEL
HEIGHT = MARGIN * 2 + ROWS * CELL
FPS = 60

# 每种方块用 1 表示占格。颜色按方块种类固定。
SHAPES = {
    "I": (
        [
            [0, 0, 0, 0],
            [1, 1, 1, 1],
            [0, 0, 0, 0],
            [0, 0, 0, 0],
        ],
        (80, 220, 230),
    ),
    "O": (
        [
            [1, 1],
            [1, 1],
        ],
        (240, 210, 70),
    ),
    "T": (
        [
            [0, 1, 0],
            [1, 1, 1],
            [0, 0, 0],
        ],
        (170, 90, 220),
    ),
    "S": (
        [
            [0, 1, 1],
            [1, 1, 0],
            [0, 0, 0],
        ],
        (90, 200, 90),
    ),
    "Z": (
        [
            [1, 1, 0],
            [0, 1, 1],
            [0, 0, 0],
        ],
        (220, 70, 80),
    ),
    "J": (
        [
            [1, 0, 0],
            [1, 1, 1],
            [0, 0, 0],
        ],
        (70, 110, 220),
    ),
    "L": (
        [
            [0, 0, 1],
            [1, 1, 1],
            [0, 0, 0],
        ],
        (230, 150, 50),
    ),
}

LINE_SCORES = {1: 100, 2: 300, 3: 500, 4: 800}


def rotate(matrix):
    return [list(row) for row in zip(*matrix[::-1])]


def new_bag():
    names = list(SHAPES)
    random.shuffle(names)
    return names


class Piece:
    def __init__(self, name):
        self.name = name
        self.matrix, self.color = SHAPES[name]
        self.matrix = [row[:] for row in self.matrix]
        self.row = 0
        self.col = COLS // 2 - len(self.matrix[0]) // 2


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.bag = []
        self.next_name = self.take_name()
        self.piece = self.spawn()
        self.score = 0
        self.lines = 0
        self.game_over = False
        self.paused = False
        self.drop_ms = 0

    def take_name(self):
        if not self.bag:
            self.bag = new_bag()
        return self.bag.pop()

    def spawn(self):
        piece = Piece(self.next_name)
        self.next_name = self.take_name()
        if self.hits(piece.matrix, piece.row, piece.col):
            self.game_over = True
        return piece

    @property
    def level(self):
        return self.lines // 10 + 1

    @property
    def interval(self):
        return max(80, 800 - (self.level - 1) * 70)

    def hits(self, matrix, row, col):
        for r, line in enumerate(matrix):
            for c, cell in enumerate(line):
                if not cell:
                    continue
                br, bc = row + r, col + c
                if br < 0 or br >= ROWS or bc < 0 or bc >= COLS:
                    return True
                if self.board[br][bc] is not None:
                    return True
        return False

    def try_move(self, drow, dcol):
        piece = self.piece
        row, col = piece.row + drow, piece.col + dcol
        if self.hits(piece.matrix, row, col):
            return False
        piece.row, piece.col = row, col
        return True

    def try_rotate(self):
        piece = self.piece
        turned = rotate(piece.matrix)
        for drow, dcol in ((0, 0), (0, -1), (0, 1), (0, -2), (0, 2), (-1, 0)):
            if not self.hits(turned, piece.row + drow, piece.col + dcol):
                piece.matrix = turned
                piece.row += drow
                piece.col += dcol
                return True
        return False

    def lock(self):
        piece = self.piece
        for r, line in enumerate(piece.matrix):
            for c, cell in enumerate(line):
                if cell and 0 <= piece.row + r < ROWS:
                    self.board[piece.row + r][piece.col + c] = piece.color
        cleared = self.clear_lines()
        if cleared:
            self.lines += cleared
            self.score += LINE_SCORES[cleared] * self.level
        self.drop_ms = 0
        self.piece = self.spawn()

    def clear_lines(self):
        kept = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(kept)
        empty = [[None for _ in range(COLS)] for _ in range(cleared)]
        self.board = empty + kept
        return cleared

    def soft_drop(self):
        if self.try_move(1, 0):
            self.score += 1
            return True
        self.lock()
        return False

    def hard_drop(self):
        dropped = 0
        while self.try_move(1, 0):
            dropped += 1
        self.score += dropped * 2
        self.lock()

    def ghost_row(self):
        piece = self.piece
        row = piece.row
        while not self.hits(piece.matrix, row + 1, piece.col):
            row += 1
        return row

    def tick(self, dt):
        if self.game_over or self.paused:
            return
        self.drop_ms += dt
        while self.drop_ms >= self.interval:
            self.drop_ms -= self.interval
            if not self.try_move(1, 0):
                self.lock()
                break


def draw_cell(surface, x, y, color, ghost=False):
    rect = pygame.Rect(x, y, CELL - 1, CELL - 1)
    if ghost:
        pygame.draw.rect(surface, color, rect, 1)
        return
    pygame.draw.rect(surface, color, rect)
    shine = tuple(min(255, channel + 40) for channel in color)
    pygame.draw.rect(surface, shine, (x, y, CELL - 1, 4))


def draw_matrix(surface, matrix, color, origin_x, origin_y, ghost=False):
    for r, line in enumerate(matrix):
        for c, cell in enumerate(line):
            if cell:
                draw_cell(
                    surface,
                    origin_x + c * CELL,
                    origin_y + r * CELL,
                    color,
                    ghost,
                )


def make_font(size, bold=False):
    for name in ("pingfangsc", "pingfang", "heiti sc", "stheitisc", "songti sc"):
        path = pygame.font.match_font(name, bold=bold)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("俄罗斯方块")
    clock = pygame.time.Clock()
    title_font = make_font(28, bold=True)
    text_font = make_font(20)
    small_font = make_font(16)
    game = Game()
    move_delay = 0
    move_dir = 0
    soft_delay = 0

    while True:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    game.reset()
                    continue
                if event.key == pygame.K_p and not game.game_over:
                    game.paused = not game.paused
                    continue
                if game.game_over or game.paused:
                    continue
                if event.key == pygame.K_LEFT:
                    move_dir = -1
                    move_delay = 0
                    game.try_move(0, -1)
                elif event.key == pygame.K_RIGHT:
                    move_dir = 1
                    move_delay = 0
                    game.try_move(0, 1)
                elif event.key in (pygame.K_UP, pygame.K_x):
                    game.try_rotate()
                elif event.key == pygame.K_DOWN:
                    soft_delay = 0
                    game.soft_drop()
                elif event.key == pygame.K_SPACE:
                    game.hard_drop()
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    keys = pygame.key.get_pressed()
                    if keys[pygame.K_LEFT]:
                        move_dir = -1
                    elif keys[pygame.K_RIGHT]:
                        move_dir = 1
                    else:
                        move_dir = 0

        if move_dir and not game.game_over and not game.paused:
            move_delay += dt
            if move_delay >= 160:
                move_delay = 60
                game.try_move(0, move_dir)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_DOWN] and not game.game_over and not game.paused:
            soft_delay += dt
            if soft_delay >= 50:
                soft_delay = 0
                game.soft_drop()

        game.tick(dt)

        screen.fill((18, 20, 28))
        board_x = MARGIN
        board_y = MARGIN
        pygame.draw.rect(
            screen,
            (28, 32, 44),
            (board_x, board_y, COLS * CELL, ROWS * CELL),
        )
        for r in range(ROWS):
            for c in range(COLS):
                color = game.board[r][c]
                if color is not None:
                    draw_cell(screen, board_x + c * CELL, board_y + r * CELL, color)

        if not game.game_over:
            ghost = game.ghost_row()
            if ghost != game.piece.row:
                draw_matrix(
                    screen,
                    game.piece.matrix,
                    game.piece.color,
                    board_x + game.piece.col * CELL,
                    board_y + ghost * CELL,
                    ghost=True,
                )
            draw_matrix(
                screen,
                game.piece.matrix,
                game.piece.color,
                board_x + game.piece.col * CELL,
                board_y + game.piece.row * CELL,
            )

        panel_x = board_x + COLS * CELL + 24
        screen.blit(title_font.render("俄罗斯方块", True, (240, 240, 245)), (panel_x, 24))
        lines = [
            f"分数  {game.score}",
            f"行数  {game.lines}",
            f"等级  {game.level}",
        ]
        for index, line in enumerate(lines):
            screen.blit(text_font.render(line, True, (210, 214, 224)), (panel_x, 80 + index * 32))

        screen.blit(text_font.render("下一个", True, (210, 214, 224)), (panel_x, 190))
        next_matrix, next_color = SHAPES[game.next_name]
        draw_matrix(screen, next_matrix, next_color, panel_x, 230)

        help_lines = [
            "← →  移动",
            "↑     旋转",
            "↓     加速",
            "空格  落底",
            "P     暂停",
            "R     重开",
            "Q     退出",
        ]
        for index, line in enumerate(help_lines):
            screen.blit(small_font.render(line, True, (150, 156, 170)), (panel_x, 380 + index * 24))

        if game.paused:
            overlay("已暂停", screen, text_font)
        elif game.game_over:
            overlay("游戏结束  按 R 重开", screen, text_font)

        pygame.display.flip()


def overlay(message, screen, font):
    shade = pygame.Surface((COLS * CELL, ROWS * CELL), pygame.SRCALPHA)
    shade.fill((10, 12, 18, 170))
    screen.blit(shade, (MARGIN, MARGIN))
    text = font.render(message, True, (245, 245, 250))
    rect = text.get_rect(center=(MARGIN + COLS * CELL // 2, MARGIN + ROWS * CELL // 2))
    screen.blit(text, rect)


if __name__ == "__main__":
    main()

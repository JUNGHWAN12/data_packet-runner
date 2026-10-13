"""Warped City 3겹 패럴랙스 배경과 네트워크 케이블 바닥."""

import math
import random

import arcade

from . import assets
from . import config as C

# (이미지, 이동 비율, 아래쪽 y)
LAYERS = [
    ("skyline-a", 0.08, C.SCREEN_H - 240 * C.BG_SCALE),   # 하늘 위쪽 일부는 화면 밖
    ("buildings-bg", 0.22, C.GROUND_Y - 30),
    ("near-buildings-bg", 0.45, C.GROUND_Y - 90),
]


class Parallax:
    def __init__(self, tint=(255, 255, 255)):
        """tint: 배경을 어둡게 할 때 곱할 색 (게임 중에는 장애물·아이템이 잘 보이도록 어둡게)."""
        self.layers = []
        for name, factor, bottom in LAYERS:
            texture = assets.background(name)
            tile_w = texture.width * C.BG_SCALE
            sprites = arcade.SpriteList()
            for _ in range(math.ceil(C.SCREEN_W / tile_w) + 1):
                # 위치는 hit box가 아닌 텍스처 크기 기준으로 잡는다 (투명 가장자리 때문에 이음새가 생기지 않도록)
                sprite = arcade.Sprite(texture, scale=C.BG_SCALE)
                sprite.color = tint
                sprite.center_y = bottom + sprite.height / 2
                sprites.append(sprite)
            self.layers.append((sprites, factor, tile_w))

    def update(self, scroll: float) -> None:
        for sprites, factor, tile_w in self.layers:
            offset = (scroll * factor) % tile_w
            for i, sprite in enumerate(sprites):
                sprite.center_x = i * tile_w - offset + tile_w / 2

    def draw(self) -> None:
        for sprites, _, _ in self.layers:
            sprites.draw(pixelated=True)


TRACE = (28, 58, 104)
VIA = (60, 120, 190)


def draw_ground(scroll: float, gaps=()) -> None:
    """바닥 = 데이터가 지나가는 네트워크 케이블. gaps의 (왼쪽 x, 폭, 복구 여부)는 끊어진 구간."""
    arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.GROUND_Y, C.GROUND_DARK)
    # 회로 배선 무늬
    upper, lower = C.GROUND_Y - 54, C.GROUND_Y - 108
    for y in (upper, lower):
        arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, y - 2, y + 1, TRACE)
    step = 144
    x = -(scroll % step)
    i = int(scroll // step)
    while x < C.SCREEN_W + step:
        y = upper if i % 2 == 0 else lower
        arcade.draw_lrbt_rectangle_filled(x - 6, x + 6, y - 6, y + 6, VIA)
        arcade.draw_lrbt_rectangle_filled(x + 70, x + 73, lower, upper, TRACE)
        x += step
        i += 1
    # 빛나는 케이블 윗면
    arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, C.GROUND_Y - 18, C.GROUND_Y - 6, (*C.CYAN, 50))
    arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, C.GROUND_Y - 6, C.GROUND_Y, C.CYAN)

    for left, width, repaired in gaps:
        right = left + width
        if right < 0 or left > C.SCREEN_W:
            continue
        arcade.draw_lrbt_rectangle_filled(left, right, 0, C.GROUND_Y, (2, 3, 10))
        if repaired:
            # 재전송으로 복구된 연결: 점선 다리
            for sx in range(int(left), int(right), 24):
                arcade.draw_lrbt_rectangle_filled(sx, min(sx + 14, right), C.GROUND_Y - 6, C.GROUND_Y, C.CYAN)
            continue
        # 끊어진 케이블 끝의 불꽃
        for edge in (left, right):
            arcade.draw_lrbt_rectangle_filled(edge - 5, edge + 5, C.GROUND_Y - 15, C.GROUND_Y, C.RED)
            for _ in range(3):
                sx = edge + random.uniform(-15, 15)
                sy = C.GROUND_Y + random.uniform(-21, 15)
                arcade.draw_lrbt_rectangle_filled(sx - 2, sx + 2, sy - 2, sy + 2, (255, 220, 120))

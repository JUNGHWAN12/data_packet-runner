"""입자와 떠오르는 점수 글자."""

import math
import random

import arcade

from . import assets


class Effects:
    def __init__(self):
        self.particles: list = []   # [x, y, vx, vy, life, max_life, color, size]
        self.popups: list = []      # [Text, life]

    def burst(self, x: float, y: float, color, count: int = 12, speed: float = 330, size: float = 4) -> None:
        for _ in range(count):
            angle = random.uniform(0, math.tau)
            v = random.uniform(0.3, 1.0) * speed
            life = random.uniform(0.3, 0.6)
            self.particles.append([x, y, math.cos(angle) * v, math.sin(angle) * v, life, life, color, size])

    def spark(self, x: float, y: float, color) -> None:
        """슬라이딩 마찰 불꽃: 뒤쪽 위로 튄다."""
        life = random.uniform(0.15, 0.3)
        self.particles.append([x, y, -random.uniform(60, 220), random.uniform(80, 260), life, life, color, 3])

    def popup(self, value: str, x: float, y: float, color, size: float = 27) -> None:
        label = assets.text(value, x, y, color, size, anchor_x="center", anchor_y="center")
        self.popups.append([label, 0.9])

    def update(self, dt: float, world_dx: float) -> None:
        for p in self.particles:
            p[0] += p[2] * dt + world_dx
            p[1] += p[3] * dt
            p[3] -= 450 * dt
            p[4] -= dt
        self.particles = [p for p in self.particles if p[4] > 0]
        for pop in self.popups:
            pop[0].y += 75 * dt
            pop[1] -= dt
        self.popups = [p for p in self.popups if p[1] > 0]

    def draw(self) -> None:
        for x, y, _, _, life, max_life, color, size in self.particles:
            alpha = int(255 * life / max_life)
            arcade.draw_lrbt_rectangle_filled(x - size, x + size, y - size, y + size, (*color[:3], alpha))
        for label, life in self.popups:
            label.color = (*label.color[:3], int(255 * min(1.0, life / 0.4)))
            label.draw()

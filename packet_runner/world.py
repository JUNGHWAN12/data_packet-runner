"""장애물·아이템·바닥 틈을 만들고 왼쪽으로 흘려보낸다."""

import math
import random

import arcade

from . import assets
from . import config as C
from . import patterns as P

SPAWN_X = C.SCREEN_W + 225   # 패턴이 처음 놓이는 화면 밖 x


class Obstacle(arcade.Sprite):
    """혼잡 구간(바닥) 또는 오류 구름(공중). left_x/box_w가 판정 기준이고, 그림은 그 위치에 맞춰 놓인다."""

    def __init__(self, kind: str, left_x: float):
        texture = assets.icon("congestion" if kind == P.CONGESTION else "error_cloud")
        super().__init__(texture)
        self.kind = kind
        self.left_x = left_x
        self.box_w = P.width_of(kind, 0)
        self.passed = False
        self.hit = False
        self.place()

    @property
    def right_x(self) -> float:
        return self.left_x + self.box_w

    def place(self) -> None:
        l, b, r, t = assets.content_box(self.texture)
        self.center_x = self.left_x + self.box_w / 2
        if self.kind == P.CONGESTION:
            self.center_y = C.GROUND_Y - b + self.height / 2          # 그림 아래 끝 = 바닥
        else:
            self.center_y = C.GROUND_Y + C.CLOUD_TOP + 8 - t + self.height / 2  # 구름 위 끝 = 판정 위쪽

    def rect(self) -> arcade.Rect:
        if self.kind == P.CONGESTION:
            return arcade.LBWH(self.left_x, C.GROUND_Y, self.box_w, C.CONGESTION_BOX[1])
        return arcade.LBWH(self.left_x, C.GROUND_Y + C.CLOUD_BOTTOM, self.box_w, C.CLOUD_TOP - C.CLOUD_BOTTOM)


class Item(arcade.Sprite):
    def __init__(self, kind: str, x: float, y: float):
        super().__init__(assets.icon(kind))
        self.kind = kind            # fragment / token
        self.base_y = y
        self.center_x, self.center_y = x, y
        self.phase = random.uniform(0, math.tau)

    def animate(self, t: float) -> None:
        self.center_y = self.base_y + math.sin(t * 5 + self.phase) * 4

    def rect(self) -> arcade.Rect:
        return arcade.LBWH(self.center_x - 27, self.center_y - 27, 54, 54)


class Gap:
    def __init__(self, left_x: float, width: float):
        self.left_x = left_x
        self.width = width
        self.passed = False
        self.fell = False
        self.repaired = False
        self.sign = arcade.Sprite(assets.icon("unplug"))

    @property
    def right_x(self) -> float:
        return self.left_x + self.width

    def place(self) -> None:
        self.sign.center_x = self.left_x + self.width / 2
        self.sign.center_y = C.GROUND_Y - 78
        self.sign.visible = not self.repaired


class World:
    def __init__(self, seed: int | None = None):
        self.picker = P.PatternPicker(seed)
        self.rng = self.picker.rng
        self.obstacles = arcade.SpriteList()
        self.items = arcade.SpriteList()
        self.signs = arcade.SpriteList()
        self.gaps: list[Gap] = []
        self.next_spawn = 750.0     # 첫 패턴까지 거리(px)
        self.spawning = True
        self.last_token_t = -99.0
        self.anim_t = 0.0

    # --- 생성 ---
    def _spawn_pattern(self, t: float, lost_pool: int, overshoot: float) -> None:
        zone = P.zone_at(t)
        # 약간 앞선 시각의 속도로 간격을 잡는다 → 실제로는 시간 간격이 같거나 더 넉넉해진다
        speed = P.speed_at(t + 2.5)
        pattern = self.picker.pick(zone)
        lead = (SPAWN_X - C.PLAYER_X) / speed
        if t + lead + P.pattern_duration(pattern, speed) > C.GAME_TIME - C.SPAWN_STOP_BEFORE + 3:
            self.spawning = False   # 서버 도착 전에 끝나지 않는 패턴은 만들지 않는다
            return
        spawns, length = P.layout(pattern, speed, C.ZONE_REST[zone])
        origin = SPAWN_X - overshoot
        for s in spawns:
            x = origin + s.x
            if s.kind in (P.CONGESTION, P.CLOUD):
                self.obstacles.append(Obstacle(s.kind, x))
            elif s.kind == P.GAP:
                gap = Gap(x, s.width)
                gap.place()
                self.gaps.append(gap)
                self.signs.append(gap.sign)
            elif s.kind == "fragment":
                self.items.append(Item("fragment", x, s.y))
            elif s.kind == "token_slot":
                chance = 0.45 if lost_pool > 0 else 0.08
                if t - self.last_token_t > 15 and self.rng.random() < chance:
                    self.items.append(Item("token", x, s.y))
                    self.last_token_t = t
        self.next_spawn = length - overshoot

    # --- 매 프레임 ---
    def update(self, dt: float, speed: float, t: float, lost_pool: int) -> None:
        self.anim_t += dt
        dx = -speed * dt
        for o in self.obstacles:
            o.left_x += dx
            o.place()
        for item in self.items:
            item.center_x += dx
            item.animate(self.anim_t)
        for gap in self.gaps:
            gap.left_x += dx
            gap.place()

        for o in [o for o in self.obstacles if o.right_x < -225]:
            o.remove_from_sprite_lists()
        for item in [i for i in self.items if i.center_x < -150]:
            item.remove_from_sprite_lists()
        for gap in [g for g in self.gaps if g.right_x < -225]:
            gap.sign.remove_from_sprite_lists()
            self.gaps.remove(gap)

        if self.spawning:
            self.next_spawn -= speed * dt
            if self.next_spawn <= 0:
                self._spawn_pattern(t, lost_pool, -self.next_spawn)

    def ground_below(self, x: float = C.PLAYER_X) -> bool:
        for gap in self.gaps:
            if not gap.repaired and gap.left_x <= x - C.FOOT_HALF and x + C.FOOT_HALF <= gap.right_x:
                return False
        return True

    def gap_under(self, x: float = C.PLAYER_X) -> Gap | None:
        for gap in self.gaps:
            if gap.left_x - 30 <= x <= gap.right_x + 30:
                return gap
        return None

    # --- 그리기 ---
    def gap_shapes(self) -> list:
        return [(g.left_x, g.width, g.repaired) for g in self.gaps]

    def draw_error_fields(self) -> None:
        """오류 구름 아래의 번개 영역: 이 높이(서 있는 키) 아래로 슬라이딩해야 지나갈 수 있다."""
        for o in self.obstacles:
            if o.kind != P.CLOUD or o.right_x < -30 or o.left_x > C.SCREEN_W + 30:
                continue
            bottom = C.GROUND_Y + C.CLOUD_BOTTOM
            top = C.GROUND_Y + C.CLOUD_TOP - 135
            arcade.draw_lrbt_rectangle_filled(o.left_x, o.right_x, bottom, top, (*C.RED, 45))
            arcade.draw_lrbt_rectangle_filled(o.left_x, o.right_x, bottom, bottom + 4, C.RED)
            for k in range(2):
                x = o.left_x + o.box_w * (0.3 + 0.4 * k)
                points = []
                y = top
                while y > bottom:
                    points.append((x + random.uniform(-13, 13), y))
                    y -= 21
                points.append((x, bottom))
                arcade.draw_line_strip(points, (255, 170, 185), 3)

    def draw(self) -> None:
        self.signs.draw(pixelated=True)
        self.draw_error_fields()
        self.obstacles.draw(pixelated=True)
        self.items.draw(pixelated=True)

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

    ICONS = {P.CONGESTION: "congestion", P.CLOUD: "error_cloud", P.SPIKE: "spike_warning"}

    def __init__(self, kind: str, left_x: float):
        texture = assets.icon(self.ICONS[kind])
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
        elif self.kind == P.SPIKE:
            self.center_y = C.GROUND_Y + C.SPIKE_BOX[1] + 12 - b + self.height / 2  # 탑 꼭대기 위 경고 표시
        else:
            self.center_y = C.GROUND_Y + C.CLOUD_TOP + 8 - t + self.height / 2  # 구름 위 끝 = 판정 위쪽

    def rects(self) -> list:
        """충돌 판정 사각형들. 그림보다 조금 안쪽으로 잡는다."""
        cx = self.left_x + self.box_w / 2
        if self.kind == P.CONGESTION:
            return [arcade.LBWH(cx - hw, C.GROUND_Y + lo, hw * 2, hi - lo) for lo, hi, hw in C.CONGESTION_TIERS]
        if self.kind == P.SPIKE:
            return [arcade.LBWH(cx - C.SPIKE_HIT_W / 2, C.GROUND_Y, C.SPIKE_HIT_W, C.SPIKE_BOX[1] - 6)]
        return [arcade.LBWH(cx - C.CLOUD_HIT_W / 2, C.GROUND_Y + C.CLOUD_BOTTOM, C.CLOUD_HIT_W,
                            C.CLOUD_TOP - C.CLOUD_BOTTOM)]

    def hits(self, box: arcade.Rect) -> bool:
        return any(box.overlaps(r) for r in self.rects())


class Item(arcade.Sprite):
    # 피싱 미끼 그림은 위쪽에 낚싯바늘이 붙어 있어, 01/10 부분이 판정 위치에 오도록 그림을 위로 올린다
    DRAW_OFFSET = {"phish": 15}

    def __init__(self, kind: str, x: float, y: float):
        super().__init__(assets.icon(kind))
        self.kind = kind            # fragment / token / shield / magnet / phish
        self.base_y = y
        self.offset = self.DRAW_OFFSET.get(kind, 0)
        self.center_x, self.center_y = x, y + self.offset
        self.phase = random.uniform(0, math.tau)
        self.passed = False         # 피싱 미끼를 무사히 지나쳤는지
        self.pulled = False         # 라우팅 자석에 끌려오는 중
        self.first = False          # 처음 나온 피싱 미끼 (안내 글자 표시)

    def animate(self, t: float) -> None:
        if not self.pulled:
            self.center_y = self.base_y + self.offset + math.sin(t * 5 + self.phase) * 4

    def pull_toward(self, x: float, y: float, dt: float) -> None:
        """라우팅 자석: 플레이어 쪽으로 끌려온다."""
        self.pulled = True
        dx, dy = x - self.center_x, y - self.center_y
        dist = math.hypot(dx, dy) or 1.0
        step = min(dist, C.MAGNET_PULL * dt)
        self.center_x += dx / dist * step
        self.center_y += dy / dist * step
        self.base_y = self.center_y - self.offset

    def rect(self) -> arcade.Rect:
        half = P.ITEM_SIZE / 2
        return arcade.LBWH(self.center_x - half, self.center_y - self.offset - half, P.ITEM_SIZE, P.ITEM_SIZE)


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
        self.last_item_t = {"token": -99.0, "shield": -99.0, "magnet": -99.0}
        self.phish_seen = 0
        self.anim_t = 0.0
        self.phish_label = assets.text("가짜 데이터!", 0, 0, C.RED, 21, anchor_x="center")
        self.spike_label = assets.text("2단 점프!", 0, 0, (255, 159, 69), 21, anchor_x="center")

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
            if s.kind in P.OBSTACLES:
                self.obstacles.append(Obstacle(s.kind, x))
            elif s.kind == P.PHISH:
                bait = Item("phish", x, s.y)
                bait.first = self.phish_seen < 2      # 처음 두 개에는 '가짜 데이터!' 안내를 붙인다
                self.phish_seen += 1
                self.items.append(bait)
            elif s.kind == P.GAP:
                gap = Gap(x, s.width)
                gap.place()
                self.gaps.append(gap)
                self.signs.append(gap.sign)
            elif s.kind == "fragment":
                self.items.append(Item("fragment", x, s.y))
            elif s.kind == "item_slot":
                kind = self._pick_item(t, zone, lost_pool)
                if kind:
                    self.items.append(Item(kind, x, s.y))
                    self.last_item_t[kind] = t
        self.next_spawn = length - overshoot

    def _pick_item(self, t: float, zone: int, lost_pool: int) -> str | None:
        """패턴 사이 아이템 자리에 놓을 아이템. 잃은 점수가 있으면 재전송 토큰이 우선."""
        if lost_pool > 0 and t - self.last_item_t["token"] > 15 and self.rng.random() < 0.45:
            return "token"
        for kind, from_zone, every, chance in C.ITEM_RULES:
            if zone >= from_zone and t - self.last_item_t[kind] > every and self.rng.random() < chance:
                return kind
        if t - self.last_item_t["token"] > 15 and self.rng.random() < 0.08:
            return "token"
        return None

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

    def ceiling(self, x: float = C.PLAYER_X, ahead: float = 0.0) -> bool:
        """지금 일어서면(ahead > 0이면 앞으로 ahead px 안에서) 오류 구름에 닿는지."""
        w, h = C.STAND_BOX
        stand = arcade.LBWH(x - w / 2 - 4, C.GROUND_Y, w + 8 + ahead, h)
        return any(o.kind == P.CLOUD and o.hits(stand) for o in self.obstacles)

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
            cx, half = o.center_x, C.CLOUD_HIT_W / 2
            # 바깥은 옅은 빛, 실제 충돌 폭만 진하게 칠해 그림과 판정을 맞춘다
            arcade.draw_lrbt_rectangle_filled(o.left_x, o.right_x, bottom, top, (*C.RED, 18))
            arcade.draw_lrbt_rectangle_filled(cx - half, cx + half, bottom, top, (*C.RED, 50))
            arcade.draw_lrbt_rectangle_filled(cx - half, cx + half, bottom, bottom + 4, C.RED)
            for k in range(2):
                x = cx - half + C.CLOUD_HIT_W * (0.3 + 0.4 * k)
                points = []
                y = top
                while y > bottom:
                    points.append((x + random.uniform(-13, 13), y))
                    y -= 21
                points.append((x, bottom))
                arcade.draw_line_strip(points, (255, 170, 185), 3)

    def draw_spikes(self) -> None:
        """트래픽 폭주: 패킷 상자가 높이 쌓인 탑. 한 번 점프로는 못 넘는다."""
        block = C.SPIKE_BOX[1] / 8
        for o in self.obstacles:
            if o.kind != P.SPIKE or o.right_x < -30 or o.left_x > C.SCREEN_W + 30:
                continue
            for i in range(8):
                bottom = C.GROUND_Y + i * block
                # 위로 갈수록 붉어지는 그래프 막대
                color = (255, 160 - i * 12, 70 - i * 4)
                arcade.draw_lrbt_rectangle_filled(o.left_x + 3, o.right_x - 3, bottom + 3, bottom + block - 3, (*color, 120))
                arcade.draw_lrbt_rectangle_outline(o.left_x + 3, o.right_x - 3, bottom + 3, bottom + block - 3, color, 3)
                arcade.draw_lrbt_rectangle_filled(o.left_x + 14, o.left_x + 34, bottom + 14, bottom + 20, color)
            self.spike_label.x = o.center_x
            self.spike_label.y = o.top + 14
            self.spike_label.draw()

    def draw(self) -> None:
        self.signs.draw(pixelated=True)
        self.draw_error_fields()
        self.draw_spikes()
        self.obstacles.draw(pixelated=True)
        self.items.draw(pixelated=True)
        for item in self.items:
            if item.kind == "phish" and item.first and not item.passed:
                self.phish_label.x, self.phish_label.y = item.center_x, item.top + 10
                self.phish_label.draw()

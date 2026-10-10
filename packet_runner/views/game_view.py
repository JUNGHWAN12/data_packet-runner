"""본게임 180초."""

import math
import random

import arcade

from .. import assets
from .. import config as C
from .. import patterns as P
from ..autopilot import Autopilot
from ..background import Parallax, draw_ground
from ..effects import Effects
from ..hud import Hud
from ..player import PlayerBody, PlayerSprite, Pose
from ..scoring import ScoreBoard
from ..world import World


class GameView(arcade.View):
    def __init__(self, seed: int | None = None):
        super().__init__()
        self.body = PlayerBody()
        self.player = PlayerSprite()
        self.badge = arcade.Sprite(assets.icon("packet"))
        self.player_list = arcade.SpriteList()
        self.player_list.extend([self.player, self.badge])
        self.server = arcade.Sprite(assets.icon("server"))
        self.server.visible = False
        self.server_list = arcade.SpriteList()
        self.server_list.append(self.server)

        self.world = World(seed)
        self.background = Parallax()
        self.effects = Effects()
        self.hud = Hud()
        self.score = ScoreBoard()
        self.autopilot = Autopilot() if self.window.autoplay else None

        self.t = 0.0
        self.scroll = 0.0
        self.speed = P.speed_at(0)
        self.slow_mult = 1.0
        self.slow_timer = 0.0
        self.invincible = 0.0
        self.shake_time = 0.0
        self.zone = 0
        self.zone_banner = 2.5
        self.arriving = False
        self.arrival_t = 0.0

        self.hint = assets.text("Space 점프   ·   공중에서 Space 한 번 더 = 2단 점프   ·   ↓ 누르고 있기 = 슬라이딩",
                                C.SCREEN_W / 2, 810, C.WHITE, 27, anchor_x="center")
        self.banner = assets.text("", C.SCREEN_W / 2, 660, C.WHITE, 51, anchor_x="center")
        self.banner_sub = assets.text("", C.SCREEN_W / 2, 600, C.CYAN, 24, anchor_x="center")
        self._set_banner()

    # --- 입력 ---
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self.autopilot:
            return
        if symbol in (arcade.key.SPACE, arcade.key.UP):
            self.body.press_jump()
        elif symbol == arcade.key.DOWN:
            self.body.press_down()

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.DOWN and not self.autopilot:
            self.body.release_down()

    # --- 진행 ---
    def _set_banner(self) -> None:
        self.banner.text = f"구간 {self.zone + 1} · {C.ZONES[self.zone][1]}"
        self.banner_sub.text = ["낮은 속도로 점프와 슬라이딩을 익혀요",
                                "새 장애물 '트래픽 폭주'는 Space를 두 번 눌러 2단 점프로 넘어요",
                                "서버가 가까워요! 끝까지 전달하세요"][self.zone]
        self.zone_banner = 2.5

    def on_update(self, delta_time: float) -> None:
        dt = min(delta_time, 1 / 30)
        if self.arriving:
            self._update_arrival(dt)
            return

        self.t += dt
        zone = P.zone_at(self.t)
        if zone != self.zone:
            self.zone = zone
            self._set_banner()
        self.zone_banner = max(0.0, self.zone_banner - dt)

        target = C.HIT_SLOW if self.slow_timer > 0 else 1.0
        self.slow_mult += (target - self.slow_mult) * min(1.0, dt * 8)
        self.speed = P.speed_at(self.t) * self.slow_mult
        self.scroll += self.speed * dt
        self.slow_timer = max(0.0, self.slow_timer - dt)
        self.invincible = max(0.0, self.invincible - dt)

        self.world.update(dt, self.speed, self.t, self.score.lost_pool)
        if self.autopilot:
            self.autopilot.control(self.body, self.world, self.speed)
        ground = self.world.ground_below()
        # 점프하면 착지할 때까지 앞으로 나아가는 거리 안에 구름이 있으면, 슬라이딩 중 점프를 보류한다
        cloud_ahead = self.world.ceiling(ahead=self.speed * P.AIR_TIME)
        self.body.update(dt, ground, self.world.ceiling(), cloud_ahead)
        if self.body.double_jumped:
            self.effects.burst(C.PLAYER_X, self.body.feet_y, C.CYAN, 16, 300, 4)
        if self.body.fell(ground):
            self._on_fall()

        self._check_collisions()
        self._update_server()
        self.background.update(self.scroll)
        self.effects.update(dt, -self.speed * dt)
        self.player.sync(self.body, dt, self.speed, self.invincible)
        if self.body.pose == Pose.SLIDE and self.body.on_ground and random.random() < 0.7:
            self.effects.spark(C.PLAYER_X + random.uniform(-40, 20), C.GROUND_Y + 4, random.choice((C.CYAN, C.WHITE)))
        self._place_badge()
        self._update_shake(dt)
        self.hud.update(self.score.score, self.score.fragments, self.score.collisions, self.t, C.ZONES[self.zone][1])

        if self.t >= C.GAME_TIME:
            self.arriving = True
            self.world.spawning = False
            gained = self.score.arrive()
            self.effects.popup(f"+{gained} 전송 완료!", self.server.center_x, self.server.top + 30, C.PURPLE, 39)

    def _check_collisions(self) -> None:
        box = self.body.rect()
        for o in self.world.obstacles:
            if not o.hit and self.invincible <= 0 and o.hits(box):
                o.hit = True
                self._on_hit(o.center_x, self.body.feet_y + 60)
            if not o.passed and o.right_x < C.PLAYER_X - box.width / 2:
                o.passed = True
                if not o.hit:
                    self.effects.popup(f"+{self.score.add_pass()}", C.PLAYER_X, self.body.feet_y + 165, C.CYAN, 21)
        for gap in self.world.gaps:
            if not gap.passed and gap.right_x < C.PLAYER_X - C.FOOT_HALF:
                gap.passed = True
                if not gap.fell:
                    self.effects.popup(f"+{self.score.add_pass()}", C.PLAYER_X, self.body.feet_y + 165, C.CYAN, 21)
        for item in [i for i in self.world.items if box.overlaps(i.rect())]:
            if item.kind == "fragment":
                gained = self.score.add_fragment()
                self.effects.burst(item.center_x, item.center_y, C.GREEN, 10, 240, 3)
                self.effects.popup(f"+{gained}", item.center_x, item.center_y + 36, C.GREEN, 18)
            else:
                gained, restored = self.score.use_token()
                self.effects.burst(item.center_x, item.center_y, C.YELLOW, 24, 390, 4)
                label = f"재전송 완료 +{gained}" if restored else f"+{gained}"
                self.effects.popup(label, item.center_x, item.center_y + 45, C.YELLOW, 27)
            item.remove_from_sprite_lists()

    def _on_hit(self, x: float, y: float) -> None:
        lost = self.score.penalize()
        self.slow_timer = C.HIT_SLOW_TIME
        self.invincible = C.INVINCIBLE_TIME
        self.shake_time = 0.25
        self.effects.burst(C.PLAYER_X, y, C.RED, 20, 390, 4)
        self.effects.popup("ERROR! 패킷 손실" + (f" -{lost}" if lost else ""), C.PLAYER_X + 60, y + 135, C.RED, 27)

    def _on_fall(self) -> None:
        gap = self.world.gap_under()
        if gap:
            gap.fell = True
            gap.repaired = True       # 끊어진 연결을 복구하고 그 자리에서 다시 달린다
            gap.place()
        lost = self.score.penalize()
        self.body.respawn()
        self.invincible = C.INVINCIBLE_TIME
        self.slow_timer = C.HIT_SLOW_TIME
        self.shake_time = 0.25
        self.effects.burst(C.PLAYER_X, C.GROUND_Y + 45, C.CYAN, 24, 390, 4)
        self.effects.popup("연결 끊김! 재전송" + (f" -{lost}" if lost else ""), C.PLAYER_X + 60, C.GROUND_Y + 225, C.RED, 27)

    def _update_server(self) -> None:
        remain = C.GAME_TIME - self.t
        if remain <= 4.0:
            self.server.visible = True
            l, b, r, t = assets.content_box(self.server.texture)
            self.server.center_x = C.PLAYER_X + 165 + P.speed_at(self.t) * remain
            self.server.center_y = C.GROUND_Y - b + self.server.height / 2

    def _update_arrival(self, dt: float) -> None:
        self.arrival_t += dt
        k = min(1.0, self.arrival_t / C.ARRIVAL_TIME)
        # 패킷이 서버 안으로 빨려 들어간다
        self.player.center_x = C.PLAYER_X + (self.server.center_x - C.PLAYER_X) * k
        self.player.scale = max(0.05, 1 - k)
        self.badge.visible = False
        if random.random() < 0.5:
            self.effects.burst(self.server.center_x, self.server.center_y, C.PURPLE, 3, 300, 3)
        self.effects.update(dt, 0)
        if self.arrival_t >= C.ARRIVAL_TIME:
            from .result_view import ResultView
            self.window.show_view(ResultView(self.score))

    def _place_badge(self) -> None:
        bob = math.sin(self.t * 6) * 3
        top = assets.content_box(self.player.texture)[3] * C.CHAR_SCALE   # 현재 프레임 그림의 위 끝
        self.badge.position = (C.PLAYER_X - 6, round(self.body.feet_y + top + 30 + bob))
        self.badge.alpha = self.player.alpha

    def _update_shake(self, dt: float) -> None:
        if self.shake_time > 0:
            self.shake_time -= dt
            self.window.shake(random.uniform(-9, 9), random.uniform(-9, 9))
        else:
            self.window.shake(0, 0)

    # --- 그리기 ---
    def on_draw(self) -> None:
        self.clear((5, 8, 20))
        with self.window.camera.activate():
            self.background.draw()
            tint = C.ZONE_TINTS[self.zone]
            if tint:
                arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, tint)
            draw_ground(self.scroll, self.world.gap_shapes())
            self.world.draw()
            self.server_list.draw(pixelated=True)
            self.player_list.draw(pixelated=True)
            self.effects.draw()
            if self.window.debug:
                self._draw_debug()
            self.hud.draw()
            if self.t < C.HINT_TIME:
                arcade.draw_lrbt_rectangle_filled(180, 1740, 788, 863, (5, 8, 20, 190))
                self.hint.draw()
            if self.zone_banner > 0:
                self.banner.draw()
                self.banner_sub.draw()

    def _draw_debug(self) -> None:
        arcade.draw_rect_outline(self.body.rect(), arcade.color.YELLOW, 3)
        for o in self.world.obstacles:
            for r in o.rects():
                arcade.draw_rect_outline(r, arcade.color.RED, 3)
        for i in self.world.items:
            arcade.draw_rect_outline(i.rect(), arcade.color.GREEN, 2)

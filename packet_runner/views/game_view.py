"""본게임 180초."""

import math
import random
from collections import deque

import arcade

from .. import assets
from .. import config as C
from .. import patterns as P
from ..autopilot import Autopilot
from ..background import Parallax, draw_ground
from ..effects import Effects
from ..hud import Hud
from ..player import PlayerBody, PlayerSprite, Pose
from ..powerups import PowerUps
from ..scoring import ScoreBoard
from ..world import World


SHIELD_BLUE = (110, 193, 255)


class GameView(arcade.View):
    def __init__(self, seed: int | None = None):
        super().__init__()
        self.body = PlayerBody()
        self.player = PlayerSprite()
        self.badge = arcade.Sprite(assets.icon("packet"))
        self.player_list = arcade.SpriteList()
        self.player_list.extend([self.player, self.badge])
        # 공중제비 잔상: 지난 프레임들의 모습을 하늘색으로 옅게 남긴다
        self.trail: deque = deque(maxlen=8)
        self.ghosts = arcade.SpriteList()
        for alpha in (120, 75, 40):
            ghost = arcade.Sprite(self.player.frames["flip_tuck_b"], scale=C.CHAR_SCALE)
            ghost.color = C.CYAN
            ghost.alpha = alpha
            ghost.visible = False
            self.ghosts.append(ghost)
        # 2단 점프한 자리에 잠깐 남는 발밑 폭발
        self.burst = arcade.Sprite(C.GENERATED / "runner" / "dj_burst.png", scale=C.CHAR_SCALE)
        self.burst.visible = False
        self.burst_life = 0.0
        self.fx_list = arcade.SpriteList()
        self.fx_list.append(self.burst)
        self.server = arcade.Sprite(assets.icon("server"))
        self.server.visible = False
        self.server_list = arcade.SpriteList()
        self.server_list.append(self.server)

        self.world = World(seed)
        self.background = Parallax()
        self.effects = Effects()
        self.hud = Hud(self.window.ranking.best_today_score())
        self.score = ScoreBoard()
        self.powerups = PowerUps()
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
        self.bonus_label = assets.text("", C.SCREEN_W / 2, 820, C.YELLOW, 39, anchor_x="center")
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
        self.banner_sub.text = ["낮은 속도로 점프와 슬라이딩을 익혀요   ·   보라색 자석은 데이터 조각을 끌어와요",
                                "트래픽 폭주는 2단 점프로!   빨간 가짜 데이터(피싱)는 슬라이딩으로 피해요",
                                "스팸 미사일! 오른쪽 끝의 ! 경고를 보고 점프·슬라이딩으로 피해요"][self.zone]
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
        self.powerups.update(dt)

        self.world.update(dt, self.speed, self.t, self.score.lost_pool)
        if self.autopilot:
            self.autopilot.control(self.body, self.world, self.speed)
        ground = self.world.ground_below()
        # 점프하면 착지할 때까지 앞으로 나아가는 거리 안에 구름이 있으면, 슬라이딩 중 점프를 보류한다
        cloud_ahead = self.world.ceiling(ahead_time=P.AIR_TIME)
        self.body.update(dt, ground, self.world.ceiling(), cloud_ahead)
        if self.body.double_jumped:
            self.effects.burst(C.PLAYER_X, self.body.feet_y, C.CYAN, 8, 300, 3)
            self.burst_life = 0.25
            self.burst.center_x = C.PLAYER_X
            self.burst.center_y = self.body.feet_y + 6 - self.burst.height / 2
        if self.body.fell(ground):
            self._on_fall()

        if self.powerups.active("magnet"):
            self._pull_fragments(dt)
        self._check_collisions()
        self._update_server()
        self.background.update(self.scroll)
        self.effects.update(dt, -self.speed * dt)
        self.player.sync(self.body, dt, self.speed, self.invincible)
        if self.body.pose == Pose.SLIDE and self.body.on_ground and random.random() < 0.7:
            self.effects.spark(C.PLAYER_X + random.uniform(-40, 20), C.GROUND_Y + 4, random.choice((C.CYAN, C.WHITE)))
        self._place_badge()
        self._update_trail(dt)
        self._update_shake(dt)
        self.hud.update(self.score.score, self.score.fragments, self.score.collisions, self.t, C.ZONES[self.zone][1],
                        {kind: self.powerups.fraction(kind) for kind in ("shield", "magnet")},
                        self.world.bonus.collected)
        if self.world.bonus.in_bonus:
            self.bonus_label.text = f"보너스 타임  {math.ceil(self.world.bonus.bonus_left)}"

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
            self._collect(item)
            item.remove_from_sprite_lists()
        # 피싱 미끼를 건드리지 않고 지나치면 보너스
        for item in self.world.items:
            if item.kind == "phish" and not item.passed and item.center_x + P.ITEM_SIZE / 2 < C.PLAYER_X - box.width / 2:
                item.passed = True
                gained = self.score.avoid_phish()
                self.effects.popup(f"가짜 데이터 피함 +{gained}", C.PLAYER_X + 40, self.body.feet_y + 200, C.GREEN, 21)

    def _collect(self, item) -> None:
        x, y = item.center_x, item.center_y
        if item.kind == "fragment":
            gained = self.score.add_fragment()
            self.effects.burst(x, y, C.GREEN, 10, 240, 3)
            self.effects.popup(f"+{gained}", x, y + 36, C.GREEN, 18)
        elif item.kind == "token":
            gained, restored = self.score.use_token()
            self.effects.burst(x, y, C.YELLOW, 24, 390, 4)
            label = f"재전송 완료 +{gained}" if restored else f"+{gained}"
            self.effects.popup(label, x, y + 45, C.YELLOW, 27)
        elif item.kind == "letter":
            bonus = self.world.bonus
            started = bonus.collect()
            self.score.letters = bonus.collected
            self.effects.burst(x, y, C.YELLOW, 20, 360, 4)
            self.effects.popup(f"{item.letter}!  ({bonus.collected}/{len(C.BONUS_WORD)})", x + 30, y + 60, C.YELLOW, 30)
            if started:
                self.score.bonus = True
                self.world.start_bonus()
                self.banner.text = "보너스 타임!"
                self.banner_sub.text = "PACKET 조각이 모두 모여 하나의 데이터가 완성됐어요!"
                self.zone_banner = 2.5
        elif item.kind == "phish":
            lost = self.score.take_phish()
            self.shake_time = 0.15
            self.effects.burst(x, y, C.RED, 18, 330, 4)
            self.effects.popup("피싱 주의! 가짜 데이터" + (f" -{lost}" if lost else ""), x + 40, y + 60, C.RED, 27)
        else:
            self.powerups.activate(item.kind)
            color = SHIELD_BLUE if item.kind == "shield" else C.PURPLE
            label = "방화벽 실드! 한 번 막아 줘요" if item.kind == "shield" else "라우팅 자석! 데이터를 끌어와요"
            self.effects.burst(x, y, color, 24, 390, 4)
            self.effects.popup(label, x + 40, y + 60, color, 27)

    def _pull_fragments(self, dt: float) -> None:
        """라우팅 자석: 앞쪽의 진짜 데이터 조각만 끌어온다 (가짜는 끌려오지 않는다)."""
        target_y = self.body.feet_y + 55
        for item in self.world.items:
            if item.kind == "fragment" and -80 < item.center_x - C.PLAYER_X < C.MAGNET_REACH:
                item.pull_toward(C.PLAYER_X, target_y, dt)

    def _shield_block(self, y: float) -> bool:
        """방화벽 실드가 있으면 충돌·추락을 막는다."""
        if not self.powerups.absorb():
            return False
        self.score.blocked += 1
        self.invincible = C.SHIELD_GRACE
        self.effects.burst(C.PLAYER_X, y, SHIELD_BLUE, 28, 420, 4)
        self.effects.popup("방화벽 차단!", C.PLAYER_X + 60, y + 135, SHIELD_BLUE, 30)
        return True

    def _on_hit(self, x: float, y: float) -> None:
        if self._shield_block(y):
            return
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
        self.body.respawn()
        if self._shield_block(C.GROUND_Y + 60):
            return
        lost = self.score.penalize()
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
            self.window.show_view(ResultView(self.score, self.world.picker.seed))

    def _place_badge(self) -> None:
        bob = math.sin(self.t * 6) * 3
        top = assets.content_box(self.player.texture)[3] * C.CHAR_SCALE   # 현재 프레임 그림의 위 끝
        self.badge.position = (C.PLAYER_X - 6, round(self.body.feet_y + top + 30 + bob))
        self.badge.alpha = self.player.alpha

    def _update_trail(self, dt: float) -> None:
        self.burst.visible = self.burst_life > 0
        if self.burst_life > 0:
            self.burst_life -= dt
            self.burst.center_x -= self.speed * dt
            self.burst.alpha = int(255 * max(0.0, self.burst_life) / 0.25)
        if self.player.flip > 0:
            # 잔상은 세계와 함께 왼쪽으로 흘러가야 앞으로 날아가는 느낌이 난다
            self.trail = deque(((t, x - self.speed * dt, y, a) for t, x, y, a in self.trail), maxlen=8)
            self.trail.append((self.player.texture, self.player.center_x, self.player.center_y, self.player.angle))
        else:
            self.trail.clear()
        for i, ghost in enumerate(self.ghosts):
            back = 2 * i + 2
            ghost.visible = len(self.trail) >= back
            if ghost.visible:
                ghost.texture, ghost.center_x, ghost.center_y, ghost.angle = self.trail[-back]

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
            tint = C.BONUS_TINT if self.world.bonus.in_bonus else C.ZONE_TINTS[self.zone]
            if tint:
                arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, tint)
            draw_ground(self.scroll, self.world.gap_shapes())
            self.world.draw()
            self.server_list.draw(pixelated=True)
            self.fx_list.draw(pixelated=True)
            self.ghosts.draw(pixelated=True)
            self._draw_powerups()
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
            elif self.world.bonus.in_bonus:
                self.bonus_label.draw()

    def _draw_powerups(self) -> None:
        cx, cy = C.PLAYER_X, self.player.center_y
        if self.powerups.active("magnet"):
            # 자석: 보라색 고리와, 끌려오는 조각까지 이어지는 선
            pulse = 0.5 + 0.5 * math.sin(self.t * 10)
            arcade.draw_circle_outline(cx, cy, 95 + 8 * pulse, (*C.PURPLE, 150), 3)
            for item in self.world.items:
                if item.pulled:
                    arcade.draw_line(cx, cy, item.center_x, item.center_y, (*C.PURPLE, 90), 2)
        if self.powerups.active("shield"):
            # 실드: 파란 보호막. 끝나기 3초 전부터 깜빡인다
            remain = self.powerups.remaining["shield"]
            if remain > 3 or int(remain * 8) % 2 == 0:
                arcade.draw_circle_filled(cx, cy, 88, (*SHIELD_BLUE, 40))
                arcade.draw_circle_outline(cx, cy, 88, (*SHIELD_BLUE, 200), 4)

    def _draw_debug(self) -> None:
        arcade.draw_rect_outline(self.body.rect(), arcade.color.YELLOW, 3)
        for o in self.world.obstacles:
            for r in o.rects():
                arcade.draw_rect_outline(r, arcade.color.RED, 3)
        for i in self.world.items:
            arcade.draw_rect_outline(i.rect(), arcade.color.GREEN, 2)

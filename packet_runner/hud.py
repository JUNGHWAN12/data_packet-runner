"""게임 화면 위쪽 정보: 점수, 데이터 수, 패킷 손실, 오늘 최고 점수, 서버까지 진행률(남은 시간은 숫자로 보여 주지 않는다)."""

import arcade

from . import assets
from . import config as C

BAR_L, BAR_R, BAR_Y = 585, 1335, 1000


class Hud:
    def __init__(self, best_today: int = 0):
        self.best_today = best_today
        self.best = assets.text("", C.SCREEN_W - 45, 969, (170, 190, 220), 21, anchor_x="right")
        self.score = assets.text("", 45, 1014, C.WHITE, 33)
        self.fragments = assets.text("", 45, 969, C.GREEN, 21)
        self.zone = assets.text("", C.SCREEN_W / 2, 945, C.CYAN, 18, anchor_x="center")
        self.collisions = assets.text("", C.SCREEN_W - 45, 1014, C.RED, 21, anchor_x="right")
        self.icons = arcade.SpriteList()
        self.marker = arcade.Sprite(assets.icon("packet"))
        self.goal = arcade.Sprite(assets.icon("server"), scale=0.2)
        self.goal.position = (BAR_R + 39, BAR_Y)
        self.icons.extend([self.goal, self.marker])

    def update(self, score: int, fragments: int, collisions: int, t: float, zone_name: str) -> None:
        self.score.text = f"점수 {score:,}"
        self.fragments.text = f"데이터 조각 × {fragments}"
        self.zone.text = zone_name
        self.collisions.text = f"패킷 손실 {collisions}"
        # 오늘 최고 점수를 도전 목표로 보여 주고, 넘어서면 강조한다
        if self.best_today == 0:
            self.best.text, self.best.color = "오늘 첫 기록에 도전!", (170, 190, 220)
        elif score > self.best_today:
            self.best.text, self.best.color = "오늘 최고 기록 경신 중!", C.YELLOW
        else:
            self.best.text, self.best.color = f"오늘 최고 {self.best_today:,}", (170, 190, 220)
        progress = min(1.0, t / C.GAME_TIME)
        self.marker.position = (BAR_L + (BAR_R - BAR_L) * progress, BAR_Y)

    def draw(self) -> None:
        arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 900, C.SCREEN_H, (5, 8, 20, 150))
        arcade.draw_lrbt_rectangle_filled(BAR_L, BAR_R, BAR_Y - 5, BAR_Y + 5, (40, 60, 100))
        arcade.draw_lrbt_rectangle_filled(BAR_L, self.marker.center_x, BAR_Y - 5, BAR_Y + 5, C.CYAN)
        for x in (BAR_L + (BAR_R - BAR_L) / 3, BAR_L + (BAR_R - BAR_L) * 2 / 3):
            arcade.draw_lrbt_rectangle_filled(x - 2, x + 2, BAR_Y - 12, BAR_Y + 12, (120, 150, 200))
        self.icons.draw(pixelated=True)
        for label in (self.score, self.fragments, self.zone, self.collisions, self.best):
            label.draw()

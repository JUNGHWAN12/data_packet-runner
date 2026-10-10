"""시작 화면: 제목·조작법·장애물 안내와 오늘의 순위표를 번갈아 보여 준다."""

import math

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..player import PlayerBody, PlayerSprite
from ..ranking_board import RankingBoard

LEGEND = [
    ("congestion", "네트워크 혼잡", "점프", 0.65),
    ("unplug", "연결 단절(틈)", "점프", 1.0),
    ("error_cloud", "통신 오류 구름", "슬라이딩", 0.42),
    ("spike_warning", "트래픽 폭주", "2단 점프", 1.0),
    ("fragment", "데이터 조각", "+10점", 1.0),
    ("token", "재전송 토큰", "잃은 점수 복구", 1.0),
]


class TitleView(arcade.View):
    def __init__(self):
        super().__init__()
        self.t = 0.0
        self.scroll = 0.0
        self.background = Parallax()
        self.body = PlayerBody()
        self.player = PlayerSprite()
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)

        cx = C.SCREEN_W / 2
        self.title_glow = assets.text(C.TITLE, cx + 5, 840 - 5, (*C.CYAN, 120), 81, anchor_x="center")
        self.title = assets.text(C.TITLE, cx, 840, C.WHITE, 81, anchor_x="center")
        self.subtitle = assets.text("장애물을 넘어 데이터를 목적지 서버까지 전달하라!", cx, 758, C.CYAN, 27,
                                    anchor_x="center")
        self.controls = assets.text("Space 점프     공중에서 Space 한 번 더  2단 점프     ↓ 누르고 있기  슬라이딩",
                                    cx, 675, C.WHITE, 27, anchor_x="center")
        self.start = assets.text("Space를 눌러 시작", cx, 240, C.YELLOW, 36, anchor_x="center")

        # 오늘의 순위표 (기록이 하나라도 있으면 안내 화면과 번갈아 보여 준다)
        self.board = RankingBoard(top=960)
        self._refresh_board()
        # 운영자: F9를 누르고 있으면 오늘 순위 초기화
        self.reset_hold: float | None = None
        self.notice = assets.text("", cx, 60, (170, 190, 220), 21, anchor_x="center")
        self.notice_time = 0.0

        self.legend_icons = arcade.SpriteList()
        self.legend_labels = []
        x0, step = 348, 245
        for i, (name, label, action, scale) in enumerate(LEGEND):
            x = x0 + step * i
            sprite = arcade.Sprite(assets.icon(name), scale=scale)
            sprite.position = (x, 532)
            self.legend_icons.append(sprite)
            self.legend_labels.append(assets.text(label, x, 450, C.WHITE, 20, anchor_x="center"))
            self.legend_labels.append(assets.text(action, x, 417, C.YELLOW, 20, anchor_x="center"))

    def _refresh_board(self) -> None:
        ranking = self.window.ranking
        self.has_records = bool(ranking.records)
        self.board.set_data(ranking.top_today(), None, ranking.best_all_time())

    @property
    def showing_board(self) -> bool:
        return self.has_records and int(self.t // C.TITLE_SWAP_TIME) % 2 == 1

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in (arcade.key.SPACE, arcade.key.ENTER):
            from .game_view import GameView
            self.window.show_view(GameView())
        elif symbol == arcade.key.F9:
            self.reset_hold = 0.0

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.F9:
            self.reset_hold = None
            self.notice_time = 0.0

    def on_update(self, delta_time: float) -> None:
        self.t += delta_time
        self.notice_time = max(0.0, self.notice_time - delta_time)
        if self.reset_hold is not None:
            self.reset_hold += delta_time
            self.notice.text = f"오늘 순위 초기화: {C.RESET_HOLD - self.reset_hold:.0f}초 더 누르고 있으세요"
            self.notice_time = 0.5
            if self.reset_hold >= C.RESET_HOLD:
                self.window.ranking.reset_today()
                self._refresh_board()
                self.reset_hold = None
                self.notice.text = "오늘 순위를 초기화했습니다 (이전 파일은 data 폴더에 백업)"
                self.notice_time = 4.0
        self.scroll += 180 * delta_time
        self.background.update(self.scroll)
        self.player.sync(self.body, delta_time, 390, 0)

    def on_draw(self) -> None:
        self.clear((5, 8, 20))
        with self.window.camera.activate():
            self.background.draw()
            arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, (5, 8, 20, 120))
            draw_ground(self.scroll)
            self.player_list.draw(pixelated=True)
            if self.showing_board:
                self.board.draw()
            else:
                arcade.draw_lrbt_rectangle_filled(225, 1695, 382, 592, (5, 8, 20, 190))
                self.legend_icons.draw(pixelated=True)
                for label in self.legend_labels:
                    label.draw()
                self.title_glow.draw()
                self.title.draw()
                self.subtitle.draw()
                self.controls.draw()
            if math.sin(self.t * 5) > -0.3:
                self.start.draw()
            if self.notice_time > 0:
                self.notice.draw()

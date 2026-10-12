"""시작 화면: 제목과 오늘의 순위표를 번갈아 보여 준다. 조작법·장애물 안내는 튜토리얼 화면에서 한다."""

import math

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..booth import HoldTimer
from ..logs import log
from ..player import PlayerBody, PlayerSprite
from ..ranking_board import RankingBoard


CREDIT = ("AI 생성 이미지 포함: 캐릭터의 슬라이딩·2단 점프 동작 그림(ChatGPT)     "
          "그림 irmirx · ansimuz · Lucide   글꼴 IBM Plex Sans KR")


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
        self.title_glow = assets.text(C.TITLE, cx + 6, 690 - 6, (*C.CYAN, 120), 108, anchor_x="center")
        self.title = assets.text(C.TITLE, cx, 690, C.WHITE, 108, anchor_x="center")
        self.subtitle = assets.text("장애물을 넘어 데이터를 목적지 서버까지 전달하라!", cx, 590, C.CYAN, 33,
                                    anchor_x="center")
        self.start = assets.text("Space를 눌러 시작", cx, 215, C.YELLOW, 42, anchor_x="center")
        # 학교 생성형 AI 사용 지침: AI 생성 이미지가 들어 있음을 밝힌다 (출처는 assets/CREDITS.md)
        self.credit = assets.text(CREDIT, cx, 108, (150, 165, 200), 18, anchor_x="center", anchor_y="center")

        # 오늘의 순위표 (기록이 하나라도 있으면 안내 화면과 번갈아 보여 준다)
        self.board = RankingBoard(top=960)
        self._refresh_board()
        # 운영자: F9를 누르고 있으면 오늘 순위 초기화
        self.reset_hold = HoldTimer(C.RESET_HOLD)
        self.notice = assets.text("", cx, 60, (170, 190, 220), 21, anchor_x="center")
        self.notice_time = 0.0

    def _refresh_board(self) -> None:
        ranking = self.window.ranking
        self.has_records = bool(ranking.records)
        self.board.set_data(ranking.top_today(), None, ranking.best_all_time())

    @property
    def showing_board(self) -> bool:
        return self.has_records and int(self.t // C.TITLE_SWAP_TIME) % 2 == 1

    @property
    def ready(self) -> bool:
        """결과 화면에서 Space를 연타하던 관람객이 곧바로 다음 판을 시작하지 않도록 잠깐 기다린다."""
        return self.t >= C.TITLE_INPUT_LOCK

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol in (arcade.key.SPACE, arcade.key.ENTER) and self.ready:
            if self.window.autoplay:        # 자동 플레이(테스트·데모)는 튜토리얼 없이 바로
                from .game_view import GameView
                self.window.show_view(GameView())
            else:
                from .tutorial_view import TutorialView
                self.window.show_view(TutorialView())
        elif symbol == arcade.key.F9:
            self.reset_hold.press()

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.F9:
            self.reset_hold.release()
            self.notice_time = 0.0

    def on_update(self, delta_time: float) -> None:
        self.t += delta_time
        self.notice_time = max(0.0, self.notice_time - delta_time)
        if self.reset_hold.update(delta_time):
            log.info("운영자가 오늘 순위를 초기화함")
            self.window.ranking.reset_today()
            self._refresh_board()
            self.notice.text = "오늘 순위를 초기화했습니다 (이전 파일은 data 폴더에 백업)"
            self.notice_time = 4.0
        elif self.reset_hold.active:
            self.notice.text = f"오늘 순위 초기화: {self.reset_hold.remaining:.0f}초 더 누르고 있으세요"
            self.notice_time = 0.5
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
                self.title_glow.draw()
                self.title.draw()
                self.subtitle.draw()
            if self.ready and math.sin(self.t * 5) > -0.3:
                self.start.draw()
            half = self.credit.content_width / 2 + 24      # 바닥 회로 무늬 위에서도 읽히도록 어두운 띠
            arcade.draw_lrbt_rectangle_filled(C.SCREEN_W / 2 - half, C.SCREEN_W / 2 + half, 92, 124, (*C.GROUND_DARK, 235))
            self.credit.draw()
            if self.notice_time > 0:
                self.notice.draw()
            self.window.draw_overlay()

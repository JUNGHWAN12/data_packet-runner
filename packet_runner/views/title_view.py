"""시작 화면: 제목과 오늘의 순위표를 번갈아 보여 준다. 조작법·장애물 안내는 튜토리얼 화면에서 한다.

운영자 키 (화면에는 안내하지 않음)
- F9 3초: 오늘 순위 초기화
- F8 3초: 순위 편집 — 부적절한 이름 하나를 골라 '???'로 바꾼다 (점수·순위는 그대로)
"""

import math

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..booth import HoldTimer
from ..logs import log
from ..player import PlayerBody, PlayerSprite
from ..ranking import ANONYMOUS
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
        # 운영자: F9를 누르고 있으면 오늘 순위 초기화, F8을 누르고 있으면 순위 편집
        self.reset_hold = HoldTimer(C.RESET_HOLD)
        self.edit_hold = HoldTimer(C.EDIT_HOLD)
        self.editing = False
        self.edit_items: list = []          # 고를 수 있는 기록 (오늘 TOP 10 + 따로 보이는 역대 1위)
        self.edit_cursor = 0
        self.edit_confirm = False           # Enter를 한 번 눌러 "바꿀까요?"를 묻는 중
        self.edit_idle = 0.0
        self.edit_title = assets.text("운영자 순위 편집", cx, 1022, (255, 140, 140), 30, anchor_x="center",
                                      anchor_y="center")
        self.edit_help = assets.text("", cx, 262, C.WHITE, 27, anchor_x="center", anchor_y="center")
        self.edit_help2 = assets.text("", cx, 212, (170, 190, 220), 24, anchor_x="center", anchor_y="center")
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

    # --- 운영자 순위 편집 ---
    def _start_edit(self) -> None:
        log.info("운영자 순위 편집 시작")
        self.editing = True
        self.edit_cursor = 0
        self.edit_confirm = False
        self.edit_idle = 0.0
        self.notice_time = 0.0
        self._refresh_edit()

    def _end_edit(self) -> None:
        log.info("운영자 순위 편집 끝")
        self.editing = False
        self.board.footer_selected = False
        self.board.highlight_color = C.YELLOW
        self._refresh_board()

    def _refresh_edit(self) -> None:
        ranking = self.window.ranking
        self.edit_items = ranking.editable()
        self.board.set_data(ranking.top_today(), None, ranking.best_all_time())
        self.edit_cursor = min(self.edit_cursor, max(0, len(self.edit_items) - 1))
        self._show_cursor()

    def _show_cursor(self) -> None:
        on_best = self._cursor_on_best_line()
        self.board.highlight = None if on_best or not self.edit_items else self.edit_cursor
        self.board.footer_selected = on_best
        self.board.highlight_color = (255, 120, 120)
        if not self.edit_items:
            self.edit_help.text, self.edit_help.color = "바꿀 기록이 없습니다", C.WHITE
            self.edit_help2.text = "F8: 끝내기"
        elif self.edit_confirm:
            r = self.edit_items[self.edit_cursor]
            where = "역대 1위" if on_best else f"오늘 {self.edit_cursor + 1}위"
            self.edit_help.text = f"{where} {r.name} ({r.score:,}점) 이름을 ???로 바꿀까요?"
            self.edit_help.color = C.YELLOW
            self.edit_help2.text = "Enter: 바꾸기      다른 키: 취소"
        else:
            self.edit_help.text = "↑↓ 고르기      Enter: 이름을 ???로 바꾸기"
            self.edit_help.color = C.WHITE
            self.edit_help2.text = f"F8: 끝내기 (입력이 없으면 {C.EDIT_TIMEOUT:.0f}초 뒤 자동으로 끝남)"

    def _cursor_on_best_line(self) -> bool:
        """커서가 오늘 TOP 10 밖의 '역대 1위' 줄에 있는지."""
        return bool(self.edit_items) and self.edit_cursor == len(self.window.ranking.top_today())

    def _edit_key(self, symbol: int) -> None:
        self.edit_idle = 0.0
        if symbol == arcade.key.F8:
            self._end_edit()
            return
        if not self.edit_items:
            return
        if symbol in (arcade.key.UP, arcade.key.DOWN):
            step = -1 if symbol == arcade.key.UP else 1
            self.edit_cursor = (self.edit_cursor + step) % len(self.edit_items)
            self.edit_confirm = False
        elif symbol == arcade.key.ENTER:
            record = self.edit_items[self.edit_cursor]
            if not self.edit_confirm:
                if record.name == ANONYMOUS:
                    self._notify("이미 ??? 입니다", 2.0)
                else:
                    self.edit_confirm = True
            else:
                old = record.name
                where = "역대 1위" if self._cursor_on_best_line() else f"오늘 {self.edit_cursor + 1}위"
                try:
                    changed = self.window.ranking.anonymize(record)
                except OSError as error:
                    log.warning("순위 편집 저장 실패: %s", error)
                    self._notify("저장하지 못했습니다 (logs/game.log 참고)", 3.0)
                    changed = False
                if changed:
                    log.info("운영자가 이름을 ???로 바꿈: %s %s %d점", where, old, record.score)
                    self._notify(f"{where} {old} → ??? 로 바꿨습니다", 3.0)
                self.edit_confirm = False
                self._refresh_edit()
                return
        else:
            self.edit_confirm = False       # 다른 키는 취소
        self._show_cursor()

    def _notify(self, text: str, seconds: float) -> None:
        self.notice.text = text
        self.notice_time = seconds

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if self.editing:
            self._edit_key(symbol)
            return
        if symbol in (arcade.key.SPACE, arcade.key.ENTER) and self.ready:
            if self.window.autoplay:        # 자동 플레이(테스트·데모)는 튜토리얼 없이 바로
                from .game_view import GameView
                self.window.show_view(GameView())
            else:
                from .tutorial_view import TutorialView
                self.window.show_view(TutorialView())
        elif symbol == arcade.key.F9:
            self.reset_hold.press()
        elif symbol == arcade.key.F8:
            self.edit_hold.press()

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.F9:
            self.reset_hold.release()
            self.notice_time = 0.0
        elif symbol == arcade.key.F8:
            self.edit_hold.release()

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
        if self.edit_hold.update(delta_time):
            self._start_edit()
        elif self.edit_hold.active:
            self.notice.text = f"순위 편집: {self.edit_hold.remaining:.0f}초 더 누르고 있으세요"
            self.notice_time = 0.5
        if self.editing:
            self.edit_idle += delta_time
            if self.edit_idle >= C.EDIT_TIMEOUT:
                self._end_edit()
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
            if self.editing:
                self.edit_title.draw()
                self.board.draw()
                self.edit_help.draw()
                self.edit_help2.draw()
            elif self.showing_board:
                self.board.draw()
            else:
                self.title_glow.draw()
                self.title.draw()
                self.subtitle.draw()
            if not self.editing and self.ready and math.sin(self.t * 5) > -0.3:
                self.start.draw()
            half = self.credit.content_width / 2 + 24      # 바닥 회로 무늬 위에서도 읽히도록 어두운 띠
            arcade.draw_lrbt_rectangle_filled(C.SCREEN_W / 2 - half, C.SCREEN_W / 2 + half, 92, 124, (*C.GROUND_DARK, 235))
            self.credit.draw()
            if self.notice_time > 0:
                self.notice.draw()
            self.window.draw_overlay()

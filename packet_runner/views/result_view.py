"""결과 화면: 점수 요약 → (오늘 TOP 10이면) 이름 입력 → 오늘의 순위표 → 시작 화면으로 자동 복귀."""

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..logs import log
from ..ranking import ANONYMOUS, finalize_name, is_allowed_name
from ..ranking_board import RankingBoard
from ..scoring import ScoreBoard, grade_for

GRADE_COLORS = {"S": C.YELLOW, "A": C.CYAN, "B": C.GREEN, "C": C.WHITE}
MESSAGE = ("데이터가 목적지에 도착했습니다! 실제 네트워크에서도 데이터 유실을 확인하고\n"
           "필요하면 재전송해 안정적으로 전달합니다.")
LETTER_KEYS = {getattr(arcade.key, ch): ch for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ"}


class ResultView(arcade.View):
    def __init__(self, score: ScoreBoard, seed: int = 0):
        super().__init__()
        self.score = score
        self.seed = seed
        self.grade = grade_for(score.score)
        self.ranking = self.window.ranking
        self.rank = self.ranking.rank_if_added(score.score, score.collisions)
        self.qualifies = self.rank <= C.RANKING_SIZE

        self.t = 0.0
        self.phase = "summary"
        self.phase_t = 0.0
        self.board_until = C.RESULT_TIME
        self.background = Parallax()
        self.background.update(0)
        cx = C.SCREEN_W / 2

        rank_line = (f"오늘 {self.rank}위! 이름을 남겨 보세요" if self.qualifies
                     else f"오늘 {self.rank}위")
        self.summary = [
            assets.text("데이터 전송 완료!", cx, 900, C.CYAN, 60, anchor_x="center"),
            assets.text(f"{score.score:,}점", cx - 135, 735, C.WHITE, 78, anchor_x="center"),
            assets.text(self.grade, cx + 255, 720, GRADE_COLORS[self.grade], 132, anchor_x="center"),
            assets.text("등급", cx + 255, 682, C.WHITE, 21, anchor_x="center"),
            assets.text(f"수집한 데이터 조각  {score.fragments}개", cx, 585, C.GREEN, 27, anchor_x="center"),
            assets.text(f"패킷 손실(충돌·추락)  {score.collisions}회", cx, 537, C.RED, 27, anchor_x="center"),
            assets.text(f"재전송 토큰 {score.tokens}개  ·  방화벽 차단 {score.blocked}회  ·  PACKET 글자 "
                        f"{score.letters}/{len(C.BONUS_WORD)}" + ("  (보너스 타임!)" if score.bonus else ""),
                        cx, 489, C.YELLOW, 27, anchor_x="center"),
            assets.text(f"가짜 데이터(피싱)  피함 {score.phish_avoided}  ·  걸림 {score.phished}", cx, 441,
                        (255, 150, 165), 27, anchor_x="center"),
            assets.text(MESSAGE, cx, 370, C.WHITE, 24, anchor_x="center", multiline=True, width=1500,
                        align="center"),
            assets.text(rank_line, cx, 250, C.YELLOW if self.qualifies else C.WHITE, 33, anchor_x="center"),
        ]

        # 이름 입력
        self.name = ""
        self.entry_deadline = 0.0
        self.entry_labels = [
            assets.text(f"오늘 {self.rank}위!", cx, 820, C.YELLOW, 72, anchor_x="center"),
            assets.text("순위표에 남길 이름을 입력하세요 (영문 3자)", cx, 720, C.WHITE, 33, anchor_x="center"),
            assets.text("A~Z 입력   ·   Backspace 지우기   ·   Enter 확정", cx, 330, (170, 190, 220), 24,
                        anchor_x="center"),
            assets.text("실명 대신 별명을 써 주세요", cx, 280, (170, 190, 220), 21, anchor_x="center"),
        ]
        self.letters = [assets.text("", cx + (i - 1) * 150, 470, C.CYAN, 96, anchor_x="center") for i in range(3)]
        self.entry_error = assets.text("", cx, 390, C.RED, 24, anchor_x="center")

        # 순위표
        self.board = RankingBoard(top=960)
        self.board_note = assets.text("", cx, 175, C.WHITE, 27, anchor_x="center")
        self.countdown = assets.text("", cx, 110, (150, 170, 200), 21, anchor_x="center")

    # --- 단계 전환 ---
    def _next_after_summary(self) -> None:
        if self.qualifies:
            self.phase = "entry"
            self.entry_deadline = self.t + C.NAME_TIME
        else:
            self._save(ANONYMOUS)
        self.phase_t = 0.0

    def _save(self, name: str) -> None:
        record = self.ranking.new_record(name, self.score.score, self.score.fragments, self.score.collisions,
                                         self.grade, self.seed)
        try:
            rank = self.ranking.add(record)
        except OSError as error:      # 저장에 실패해도 게임은 계속 (화면에는 그대로 보여 준다)
            log.warning("랭킹 저장 실패: %s", error)
            rank = self.rank
        else:
            log.info("기록 저장: 오늘 %d위 %d점 (%s)", rank, self.score.score, "이름 입력" if name != ANONYMOUS else "익명")
        highlight = rank - 1 if rank <= C.RANKING_SIZE else None
        self.board.set_data(self.ranking.top_today(), highlight, self.ranking.best_all_time())
        if highlight is None:
            top = self.ranking.top_today()
            gap = top[-1].score - self.score.score + 1 if len(top) == C.RANKING_SIZE else 0
            self.board_note.text = f"이번 기록: 오늘 {rank}위" + (f"  ·  TOP 10까지 {gap:,}점!" if gap > 0 else "")
        else:
            self.board_note.text = f"{name}  {self.score.score:,}점  ·  오늘 {rank}위"
        self.phase = "board"
        self.phase_t = 0.0
        self.board_until = max(C.RESULT_TIME, self.t + C.BOARD_MIN_TIME)

    def _back(self) -> None:
        from .title_view import TitleView
        self.window.show_view(TitleView())

    # --- 입력 ---
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        confirm = symbol in (arcade.key.SPACE, arcade.key.ENTER)
        # 결과를 볼 시간을 주고, Space 연타로 순위표·시작 화면을 지나 다음 판까지 넘어가지 않도록 잠근다
        if self.phase == "summary":
            if confirm and self.t > C.RESULT_SKIP_LOCK:
                self._next_after_summary()
        elif self.phase == "entry":
            self._entry_key(symbol)
        elif self.phase == "board" and confirm and self.phase_t > C.RESULT_SKIP_LOCK:
            self._back()

    def _entry_key(self, symbol: int) -> None:
        # 한/영 상태와 관계없이 동작하도록 문자 입력(on_text)이 아니라 키 코드로 받는다
        if symbol in LETTER_KEYS and len(self.name) < C.NAME_LEN:
            self.name += LETTER_KEYS[symbol]
            self.entry_error.text = ""
        elif symbol == arcade.key.BACKSPACE:
            self.name = self.name[:-1]
        elif symbol == arcade.key.ENTER and len(self.name) == C.NAME_LEN:
            if is_allowed_name(self.name):
                self._save(self.name)
                return
            self.entry_error.text = "다른 이름을 입력해 주세요"
            self.name = ""
        else:
            return
        # 입력 중이면 최소 3초는 더 기다린다
        self.entry_deadline = max(self.entry_deadline, self.t + 3.0)

    # --- 진행 ---
    def on_update(self, delta_time: float) -> None:
        self.t += delta_time
        self.phase_t += delta_time
        if self.phase == "summary":
            if self.t >= C.SUMMARY_TIME:
                self._next_after_summary()
            else:
                self.countdown.text = "Space: 다음" if self.t > C.RESULT_SKIP_LOCK else ""
        elif self.phase == "entry":
            remain = self.entry_deadline - self.t
            if remain <= 0:
                self._save(finalize_name(self.name))
                return
            for i, label in enumerate(self.letters):
                label.text = self.name[i] if i < len(self.name) else ""
            self.countdown.text = f"{int(remain) + 1}초 남음"
        else:
            remain = self.board_until - self.t
            if remain <= 0:
                self._back()
                return
            skip = "  (Space: 바로 이동)" if self.phase_t > C.RESULT_SKIP_LOCK else ""
            self.countdown.text = f"{int(remain) + 1}초 뒤 처음 화면으로 돌아갑니다{skip}"

    # --- 그리기 ---
    def on_draw(self) -> None:
        self.clear((5, 8, 20))
        with self.window.camera.activate():
            self.background.draw()
            draw_ground(0)
            arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, (5, 8, 20, 170))
            if self.phase == "summary":
                for label in self.summary:
                    label.draw()
            elif self.phase == "entry":
                self._draw_entry()
            else:
                self.board.draw()
                self.board_note.draw()
            self.countdown.draw()
            self.window.draw_overlay()

    def _draw_entry(self) -> None:
        for label in self.entry_labels:
            label.draw()
        cx = C.SCREEN_W / 2
        for i, label in enumerate(self.letters):
            x = cx + (i - 1) * 150
            active = i == len(self.name)
            color = C.YELLOW if active and int(self.t * 3) % 2 == 0 else (90, 120, 170)
            arcade.draw_lrbt_rectangle_filled(x - 55, x + 55, 440, 448, color)   # 밑줄 칸
            label.draw()
        self.entry_error.draw()

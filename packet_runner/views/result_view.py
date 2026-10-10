"""결과 화면 40초 → 시작 화면으로 자동 복귀."""

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..scoring import ScoreBoard, grade_for

GRADE_COLORS = {"S": C.YELLOW, "A": C.CYAN, "B": C.GREEN, "C": C.WHITE}
MESSAGE = ("데이터가 목적지에 도착했습니다! 실제 네트워크에서도 데이터 유실을 확인하고\n"
           "필요하면 재전송해 안정적으로 전달합니다.")


class ResultView(arcade.View):
    def __init__(self, score: ScoreBoard):
        super().__init__()
        self.t = 0.0
        self.background = Parallax()
        self.background.update(0)
        grade = grade_for(score.score)
        cx = C.SCREEN_W / 2
        self.labels = [
            assets.text("데이터 전송 완료!", cx, 900, C.CYAN, 60, anchor_x="center"),
            assets.text(f"{score.score:,}점", cx - 135, 735, C.WHITE, 78, anchor_x="center"),
            assets.text(grade, cx + 255, 720, GRADE_COLORS[grade], 132, anchor_x="center"),
            assets.text("등급", cx + 255, 682, C.WHITE, 21, anchor_x="center"),
            assets.text(f"수집한 데이터 조각  {score.fragments}개", cx, 585, C.GREEN, 27, anchor_x="center"),
            assets.text(f"패킷 손실(충돌·추락)  {score.collisions}회", cx, 537, C.RED, 27, anchor_x="center"),
            assets.text(f"재전송 토큰  {score.tokens}개", cx, 489, C.YELLOW, 27, anchor_x="center"),
            assets.text(MESSAGE, cx, 390, C.WHITE, 24, anchor_x="center", multiline=True, width=1500,
                        align="center"),
        ]
        self.countdown = assets.text("", cx, 225, (150, 170, 200), 21, anchor_x="center")

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        # 결과를 볼 시간을 주기 위해 처음 2초 동안은 넘기지 않는다
        if symbol in (arcade.key.SPACE, arcade.key.ENTER) and self.t > 2.0:
            self._back()

    def _back(self) -> None:
        from .title_view import TitleView
        self.window.show_view(TitleView())

    def on_update(self, delta_time: float) -> None:
        self.t += delta_time
        remain = max(0, int(C.RESULT_TIME - self.t) + 1)
        self.countdown.text = f"{remain}초 뒤 처음 화면으로 돌아갑니다  (Space: 바로 이동)"
        if self.t >= C.RESULT_TIME:
            self._back()

    def on_draw(self) -> None:
        self.clear((5, 8, 20))
        with self.window.camera.activate():
            self.background.draw()
            draw_ground(0)
            arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, (5, 8, 20, 170))
            for label in self.labels:
                label.draw()
            self.countdown.draw()

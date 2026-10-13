"""오늘의 TOP 10 순위표 (시작 화면·결과 화면 공용)."""

import arcade

from . import assets
from . import config as C
from .ranking import Record

ROW_H = 50
HALF_W = 460
MEDALS = [(255, 215, 90), (215, 225, 235), (230, 160, 100)]   # 1~3위 숫자 색


class RankingBoard:
    def __init__(self, top: float = 880):
        self.cx = C.SCREEN_W / 2
        self.top = top
        self.first_row = top - 125
        self.title = assets.text("오늘의 TOP 10", self.cx, top - 62, C.YELLOW, 36, anchor_x="center")
        self.empty = assets.text("아직 오늘 기록이 없어요. 첫 번째 주인공이 되어 보세요!", self.cx, self.first_row - 60,
                                 C.WHITE, 24, anchor_x="center")
        self.footer = assets.text("", self.cx, 0, C.PURPLE, 21, anchor_x="center")
        self.rows: list = []
        self.highlight: int | None = None
        self.highlight_color = C.YELLOW
        self.footer_selected = False        # 운영자 순위 편집에서 '역대 1위' 줄을 골랐을 때
        self.bottom = self.first_row - 60

    def set_data(self, records: list, highlight: int | None = None, best: Record | None = None) -> None:
        self.rows = []
        self.highlight = highlight
        for i, r in enumerate(records):
            y = self.first_row - i * ROW_H
            color = C.YELLOW if i == highlight else C.WHITE
            rank_color = MEDALS[i] if i < len(MEDALS) else color
            self.rows.append([
                assets.text(f"{i + 1}", self.cx - 330, y, rank_color, 27, anchor_x="right"),
                assets.text(r.name, self.cx - 250, y, color, 27),
                assets.text(f"{r.score:,}점", self.cx + 160, y, color, 27, anchor_x="right"),
                assets.text(f"{r.grade}등급", self.cx + 200, y, (170, 190, 220), 20),
                assets.text(f"손실 {r.collisions}", self.cx + 420, y, (255, 150, 165), 20, anchor_x="right"),
            ])
        last_row = self.first_row - (max(len(records), 1) - 1) * ROW_H
        self.footer.y = last_row - 62
        self.footer.text = f"역대 1위   {best.name}   {best.score:,}점" if best else ""
        self.bottom = self.footer.y - 30

    def draw(self) -> None:
        arcade.draw_lrbt_rectangle_filled(self.cx - HALF_W, self.cx + HALF_W, self.bottom, self.top, (5, 8, 20, 210))
        arcade.draw_lrbt_rectangle_outline(self.cx - HALF_W, self.cx + HALF_W, self.bottom, self.top, (*C.CYAN, 120), 3)
        self.title.draw()
        if not self.rows:
            self.empty.draw()
        if self.highlight is not None and self.highlight < len(self.rows):
            y = self.first_row - self.highlight * ROW_H
            arcade.draw_lrbt_rectangle_filled(self.cx - HALF_W + 20, self.cx + HALF_W - 20, y - 14, y + 34,
                                              (*self.highlight_color, 45))
        for row in self.rows:
            for label in row:
                label.draw()
        if self.footer.text and self.footer_selected:
            arcade.draw_lrbt_rectangle_filled(self.cx - HALF_W + 20, self.cx + HALF_W - 20, self.footer.y - 12,
                                              self.footer.y + 32, (*self.highlight_color, 45))
        if self.footer.text:
            arcade.draw_lrbt_rectangle_filled(self.cx - HALF_W + 20, self.cx + HALF_W - 20, self.footer.y + 40,
                                              self.footer.y + 42, (*C.CYAN, 90))
            self.footer.draw()

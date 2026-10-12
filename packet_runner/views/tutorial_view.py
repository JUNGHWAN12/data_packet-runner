"""튜토리얼: 조작 연습 → 피해야 할 장애물 → 모으면 좋은 아이템. 끝나면 본게임을 시작한다.

Enter를 누르면 언제든 건너뛰고 바로 시작한다.
"""

import math
import random

import arcade

from .. import assets
from .. import config as C
from ..background import Parallax, draw_ground
from ..effects import Effects
from ..player import PlayerBody, PlayerSprite, Pose
from ..tutorial import Practice

RUN_SPEED = 180          # 배경이 흐르는 속도 (시작 화면과 같게)
PAGE_TITLES = ["조작 연습", "피해야 할 장애물", "모으면 좋은 아이템"]
PAGE_SUBTITLES = ["", "부딪히면 점수를 잃고 잠깐 느려져요", "먹으면 점수를 얻거나 도움을 받아요"]

# 조작 연습 카드: (단계, 키, 이름, 설명)
PRACTICE_CARDS = [
    ("jump", ["Space"], "점프", "장애물을 뛰어넘어요"),
    ("double", ["Space", "Space"], "2단 점프", "공중에서 한 번 더!"),
    ("slide", ["↓"], "슬라이딩", "누르고 있는 동안 쭉"),
]
INSTRUCTIONS = {
    "jump": "Space를 눌러 점프해 보세요!",
    "double": "점프한 뒤 공중에서 Space를 한 번 더 눌러 보세요!",
    "slide": "↓ 키를 누르고 있어 보세요!",
    None: "완벽해요! 이제 피해야 할 장애물을 알아봐요",
}
# 안내 카드: (아이콘, 이름, 동작 — "[키]"는 키 그림, 설명, 등장 구간)
OBSTACLE_CARDS = [
    ("congestion", "네트워크 혼잡", ["[Space]", "점프"], "주황 원뿔을 뛰어넘어요", "1구간"),
    ("unplug", "연결 단절(틈)", ["[Space]", "점프"], "끊긴 바닥에 빠지지 않게", "1구간"),
    ("error_cloud", "통신 오류 구름", ["[↓]", "슬라이딩"], "번개 아래로 미끄러져요", "1구간"),
    ("spike_warning", "트래픽 폭주", ["[Space]", "[Space]"], "높이 쌓인 탑은 2단 점프로", "2구간"),
    ("phish", "가짜 데이터(피싱)", ["[↓]", "슬라이딩"], "빨간 조각은 먹지 말아요", "2구간"),
    ("spam", "스팸 미사일", ["[Space]", "또는", "[↓]"], "! 경고 뒤 낮게·높게 날아와요", "3구간"),
]
ITEM_CARDS = [
    ("fragment", "데이터 조각", ["+10점"], "많이 모을수록 높은 점수", None),
    ("token", "재전송 토큰", ["잃은 점수 되찾기"], "잃은 데이터를 다시 보내요", None),
    ("shield", "방화벽 실드", ["충돌 한 번 막기"], "파란 보호막이 지켜 줘요", None),
    ("magnet", "라우팅 자석", ["조각 끌어오기"], "6초 동안 주변 조각이 모여요", None),
    ("letter", "PACKET 글자", ["6글자 → 보너스 타임"], "높은 곳의 글자는 점프로!", None),
]
ZONE_COLORS = {"1구간": C.CYAN, "2구간": (255, 170, 80), "3구간": C.PURPLE}

CARD_FILL = (10, 16, 36, 225)
CARD_BORDER = (70, 95, 150)
KEY_FACE, KEY_SIDE, KEY_EDGE = (34, 48, 86), (12, 18, 40), (150, 180, 235)


class KeyCap:
    """키보드 키 모양 그림. pressed면 눌린 모습(아래로 내려가고 노랗게)."""

    DEPTH = 6

    def __init__(self, label: str, size: float = 21):
        self.label = label
        self.text = assets.text(label, 0, 0, C.WHITE, size, anchor_x="center", anchor_y="center")
        self.w = max(54, self.text.content_width + 30)
        self.h = size * 2 + 8

    def draw(self, left: float, cy: float, pressed: bool = False) -> None:
        right, bottom = left + self.w, cy - self.h / 2
        arcade.draw_lrbt_rectangle_filled(left, right, bottom - self.DEPTH, bottom - self.DEPTH + self.h, KEY_SIDE)
        shift = self.DEPTH if pressed else 0
        face = C.YELLOW if pressed else KEY_FACE
        arcade.draw_lrbt_rectangle_filled(left, right, bottom - shift, bottom - shift + self.h, face)
        arcade.draw_lrbt_rectangle_outline(left, right, bottom - shift, bottom - shift + self.h, KEY_EDGE, 2)
        self.text.color = (20, 20, 30) if pressed else C.WHITE
        self.text.position = (left + self.w / 2, cy - shift + 2)
        self.text.draw()


class ActionRow:
    """"[Space] 점프"처럼 키 그림과 글자를 한 줄로 늘어놓는다."""

    GAP = 12

    def __init__(self, tokens: list[str], color=C.YELLOW, size: float = 25):
        self.parts = []
        for token in tokens:
            if token.startswith("[") and token.endswith("]"):
                key = KeyCap(token[1:-1])
                self.parts.append((key, key.w))
            else:
                label = assets.text(token, 0, 0, color, size, anchor_y="center")
                self.parts.append((label, label.content_width))
        self.w = sum(w for _, w in self.parts) + self.GAP * (len(self.parts) - 1)

    def draw(self, left: float, cy: float, pressed=lambda label: False) -> None:
        x = left
        for part, w in self.parts:
            if isinstance(part, KeyCap):
                part.draw(x, cy, pressed(part.label))
            else:
                part.position = (x, cy)
                part.draw()
            x += w + self.GAP


def draw_card(cx: float, cy: float, w: float, h: float, border=CARD_BORDER, fill=CARD_FILL, width: int = 3) -> None:
    arcade.draw_lrbt_rectangle_filled(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, fill)
    arcade.draw_lrbt_rectangle_outline(cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, border, width)


def draw_check(x: float, y: float) -> None:
    arcade.draw_circle_filled(x, y, 24, C.GREEN)
    arcade.draw_line_strip([(x - 12, y + 1), (x - 3, y - 9), (x + 13, y + 10)], (10, 40, 25), 6)


class InfoCard:
    """장애물·아이템 안내 카드: 왼쪽 아이콘, 오른쪽 이름·동작·설명, 오른쪽 위 등장 구간."""

    W, H = 540, 230

    def __init__(self, cx: float, cy: float, entry):
        name, title, action, note, zone = entry
        self.cx, self.cy = cx, cy
        texture = assets.letter("P") if name == "letter" else assets.icon(name)
        self.icon = arcade.Sprite(texture, scale=min(1.0, 110 / max(texture.width, texture.height)))
        self.icon.position = (cx - self.W / 2 + 85, cy)
        self.text_x = cx - self.W / 2 + 165
        self.title = assets.text(title, self.text_x, cy + 52, C.WHITE, 28, anchor_y="center")
        self.action = ActionRow(action)
        self.note = assets.text(note, self.text_x, cy - 68, (170, 190, 220), 18, anchor_y="center")
        self.zone = None
        if zone:
            self.zone = assets.text(zone, cx + self.W / 2 - 20, cy + self.H / 2 - 24, ZONE_COLORS[zone], 17,
                                    anchor_x="right", anchor_y="center")

    def draw(self) -> None:
        draw_card(self.cx, self.cy, self.W, self.H)
        self.title.draw()
        self.action.draw(self.text_x, self.cy - 6)
        self.note.draw()
        if self.zone:
            right, cy = self.cx + self.W / 2 - 10, self.cy + self.H / 2 - 24
            left = right - self.zone.content_width - 20
            arcade.draw_lrbt_rectangle_outline(left, right, cy - 16, cy + 16, self.zone.color, 2)
            self.zone.draw()


def grid(entries: list, rows_y=(700, 450), step: float = 570) -> list[InfoCard]:
    """세 개씩 줄을 지어 가운데 정렬로 카드를 놓는다."""
    cards = []
    for row, y in enumerate(rows_y):
        chunk = entries[row * 3:row * 3 + 3]
        x0 = C.SCREEN_W / 2 - step * (len(chunk) - 1) / 2
        cards += [InfoCard(x0 + step * i, y, entry) for i, entry in enumerate(chunk)]
    return cards


class TutorialView(arcade.View):
    PRACTICE_X = (860, 1230, 1600)   # 조작 연습 카드 가운데 x (왼쪽은 캐릭터가 연습하는 자리)
    PRACTICE_Y, PRACTICE_W, PRACTICE_H = 560, 340, 330

    def __init__(self):
        super().__init__()
        self.page = 0
        self.t = 0.0
        self.page_t = 0.0
        self.scroll = 0.0
        self.background = Parallax()
        self.effects = Effects()        # 캐릭터 주변 (배경과 함께 흘러감)
        self.ui_effects = Effects()     # 카드 위 (제자리)
        self.body = PlayerBody()
        self.player = PlayerSprite()
        self.player_list = arcade.SpriteList()
        self.player_list.append(self.player)
        self.practice = Practice()
        self.done_t: float | None = None
        self.space_flash = 0.0

        cx = C.SCREEN_W / 2
        self.page_title = assets.text("", cx, 935, C.CYAN, 48, anchor_x="center", anchor_y="center")
        self.subtitle = assets.text("", cx, 862, C.WHITE, 27, anchor_x="center", anchor_y="center")
        self.prompt = assets.text("", cx, 255, C.YELLOW, 33, anchor_x="center", anchor_y="center")
        self.skip = assets.text("Enter: 튜토리얼 건너뛰고 바로 시작", cx, 80, (130, 150, 190), 19,
                                anchor_x="center", anchor_y="center")

        self.practice_cards = []
        for x, (step, keys, name, desc) in zip(self.PRACTICE_X, PRACTICE_CARDS):
            caps = [KeyCap(key, 24) for key in keys]
            self.practice_cards.append({
                "step": step, "x": x, "caps": caps,
                "name": assets.text(name, x, self.PRACTICE_Y - 15, C.WHITE, 36, anchor_x="center",
                                    anchor_y="center"),
                "desc": assets.text(desc, x, self.PRACTICE_Y - 78, (170, 190, 220), 21, anchor_x="center",
                                    anchor_y="center"),
            })
        self.obstacle_cards = grid(OBSTACLE_CARDS)
        self.item_cards = grid(ITEM_CARDS)
        self.card_icons = arcade.SpriteList()
        self._show_page()

    # --- 페이지 ---
    def _show_page(self) -> None:
        self.page_t = 0.0
        self.page_title.text = PAGE_TITLES[self.page]
        self.subtitle.text = PAGE_SUBTITLES[self.page]
        self.subtitle.color = C.WHITE
        self.card_icons.clear()
        for card in self._info_cards():
            self.card_icons.append(card.icon)
        self.prompt.text = ["", "Space: 다음", "Space를 눌러 출발!"][self.page]

    def _info_cards(self) -> list[InfoCard]:
        return [[], self.obstacle_cards, self.item_cards][self.page]

    def _next_page(self) -> None:
        self.body.release_down()        # 연습 중 ↓를 누른 채 넘어가도 일어서게
        if self.page == len(PAGE_TITLES) - 1:
            self._start_game()
            return
        self.page += 1
        self._show_page()

    def _start_game(self) -> None:
        from .game_view import GameView
        self.window.show_view(GameView())

    # --- 입력 ---
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ENTER and self.t > 0.5:
            self._start_game()
        elif self.page == 0:
            if symbol in (arcade.key.SPACE, arcade.key.UP):
                self.body.press_jump()
                self.space_flash = 0.15
            elif symbol == arcade.key.DOWN:
                self.body.press_down()
        elif symbol == arcade.key.SPACE and self.page_t > C.TUTORIAL_LOCK:
            self._next_page()

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.DOWN:
            self.body.release_down()

    # --- 진행 ---
    def on_update(self, delta_time: float) -> None:
        if self.window.paused:
            return
        dt = min(delta_time, 1 / 30)
        self.t += dt
        self.page_t += dt
        self.space_flash = max(0.0, self.space_flash - dt)
        self.scroll += RUN_SPEED * dt
        self.background.update(self.scroll)
        self.body.update(dt, True)

        if self.page == 0:
            for step in self.practice.observe(self.body):
                card = next(c for c in self.practice_cards if c["step"] == step)
                self.ui_effects.burst(card["x"], self.PRACTICE_Y, C.GREEN, 26, 380, 5)
            instruction = INSTRUCTIONS[self.practice.next_step]
            if self.subtitle.text != instruction:
                self.subtitle.text = instruction
                self.subtitle.color = C.GREEN if self.practice.complete else C.YELLOW
            if self.practice.complete and self.done_t is None:
                self.done_t = self.page_t
            finished = self.done_t is not None and self.page_t - self.done_t > 1.6
            if finished or self.page_t > C.TUTORIAL_PRACTICE_TIME:
                self._next_page()
        elif self.page_t > C.TUTORIAL_PAGE_TIME:
            self._next_page()
            return

        if self.body.double_jumped:
            self.effects.burst(C.PLAYER_X, self.body.feet_y, C.CYAN, 8, 300, 3)
        if self.body.pose == Pose.SLIDE and random.random() < 0.7:
            self.effects.spark(C.PLAYER_X + random.uniform(-40, 20), C.GROUND_Y + 4, random.choice((C.CYAN, C.WHITE)))
        self.effects.update(dt, -RUN_SPEED * dt)
        self.ui_effects.update(dt, 0)
        self.player.sync(self.body, dt, 390, 0)

    # --- 그리기 ---
    def on_draw(self) -> None:
        self.clear((5, 8, 20))
        with self.window.camera.activate():
            self.background.draw()
            arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, (5, 8, 20, 150))
            draw_ground(self.scroll)
            self.effects.draw()
            self.player_list.draw(pixelated=True)
            self._draw_header()
            if self.page == 0:
                self._draw_practice()
            else:
                for card in self._info_cards():
                    card.draw()
                self.card_icons.draw(pixelated=True)
                self._draw_prompt()
            self.ui_effects.draw()
            self.skip.draw()
            self.window.draw_overlay()

    def _draw_header(self) -> None:
        cx = C.SCREEN_W / 2
        for i in range(len(PAGE_TITLES)):
            x = cx + (i - 1) * 44
            if i == self.page:
                arcade.draw_circle_filled(x, 1012, 10, C.CYAN)
            else:
                arcade.draw_circle_outline(x, 1012, 9, (110, 130, 170), 3)
        self.page_title.draw()
        if self.subtitle.text:
            self.subtitle.draw()

    def _draw_practice(self) -> None:
        pulse = 0.5 + 0.5 * math.sin(self.t * 6)
        next_step = self.practice.next_step

        def pressed(label: str) -> bool:
            return self.space_flash > 0 if label == "Space" else self.body.down_held

        for card in self.practice_cards:
            x, y = card["x"], self.PRACTICE_Y
            done = self.practice.done[card["step"]]
            if done:
                draw_card(x, y, self.PRACTICE_W, self.PRACTICE_H, C.GREEN, (14, 44, 34, 225), 4)
            elif card["step"] == next_step:
                border = (255, 224, 102, int(110 + 145 * pulse))
                draw_card(x, y, self.PRACTICE_W, self.PRACTICE_H, border, CARD_FILL, 4)
            else:
                draw_card(x, y, self.PRACTICE_W, self.PRACTICE_H)
            caps = card["caps"]
            width = sum(c.w for c in caps) + 16 * (len(caps) - 1)
            left = x - width / 2
            for cap in caps:
                cap.draw(left, y + 75, pressed(cap.label))
                left += cap.w + 16
            card["name"].draw()
            card["desc"].draw()
            if done:
                draw_check(x + self.PRACTICE_W / 2 - 34, y + self.PRACTICE_H / 2 - 34)

    def _draw_prompt(self) -> None:
        ready = self.page_t > C.TUTORIAL_LOCK
        if not ready or math.sin(self.t * 5) > -0.3:
            self.prompt.color = C.YELLOW if ready else (120, 110, 70)
            self.prompt.draw()
        # 자동으로 넘어가기까지 남은 시간 막대
        cx, half = C.SCREEN_W / 2, 180
        left = 1 - min(1.0, self.page_t / C.TUTORIAL_PAGE_TIME)
        arcade.draw_lrbt_rectangle_filled(cx - half, cx + half, 207, 213, (40, 55, 90))
        arcade.draw_lrbt_rectangle_filled(cx - half, cx - half + 2 * half * left, 207, 213, (120, 150, 200))

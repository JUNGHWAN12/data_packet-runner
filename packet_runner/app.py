"""게임 창. 어떤 창 크기에서도 1920×1080 화면을 비율을 유지해(레터박스) 보여 준다."""

import arcade

from . import assets
from . import config as C
from .booth import HoldTimer
from .ranking import Ranking


def _window_size() -> tuple[int, int]:
    """창 모드에서는 모니터보다 크지 않게 줄인다 (게임 화면은 항상 1920×1080 기준으로 그린다)."""
    try:
        screen_w, screen_h = arcade.get_display_size()
    except Exception:
        return C.SCREEN_W, C.SCREEN_H
    scale = min(1.0, screen_w * 0.9 / C.SCREEN_W, screen_h * 0.9 / C.SCREEN_H)
    return int(C.SCREEN_W * scale), int(C.SCREEN_H * scale)


class GameWindow(arcade.Window):
    """booth=True(부스 운영 모드): 전체 화면, 마우스 커서 숨김, 개발용 키(F3·F11) 끔."""

    def __init__(self, fullscreen: bool = False, autoplay: bool = False, booth: bool = False):
        super().__init__(*_window_size(), C.TITLE, fullscreen=fullscreen or booth, resizable=True)
        self.autoplay = autoplay
        self.booth = booth
        self.debug = False
        self.focused = True             # 다른 창을 누르면 False → 게임을 멈추고 "화면을 클릭해 주세요"
        self.quit_hold = HoldTimer(C.QUIT_HOLD)
        self.set_mouse_visible(not self.fullscreen)
        self.ranking = Ranking(C.RANKING_PATH)
        assets.load_font()
        self.camera = arcade.Camera2D(
            position=(C.SCREEN_W / 2, C.SCREEN_H / 2),
            projection=arcade.LRBT(-C.SCREEN_W / 2, C.SCREEN_W / 2, -C.SCREEN_H / 2, C.SCREEN_H / 2),
        )
        self._fit_camera(self.width, self.height)
        self.focus_title = assets.text("화면을 한 번 클릭해 주세요", C.SCREEN_W / 2, 590, C.YELLOW, 54,
                                       anchor_x="center", anchor_y="center")
        self.focus_sub = assets.text("다른 창이 선택되어 키가 눌리지 않아요  ·  게임은 잠시 멈춰 있어요",
                                     C.SCREEN_W / 2, 500, C.WHITE, 27, anchor_x="center", anchor_y="center")
        self.quit_notice = assets.text("", C.SCREEN_W / 2, 40, (255, 190, 120), 21, anchor_x="center",
                                       anchor_y="center")
        arcade.schedule(self.tick, 1 / 30)

    def _fit_camera(self, width: int, height: int) -> None:
        scale = min(width / C.SCREEN_W, height / C.SCREEN_H)
        vw, vh = C.SCREEN_W * scale, C.SCREEN_H * scale
        self.camera.viewport = arcade.LBWH((width - vw) / 2, (height - vh) / 2, vw, vh)

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._fit_camera(width, height)

    def shake(self, dx: float, dy: float) -> None:
        self.camera.position = (C.SCREEN_W / 2 + dx, C.SCREEN_H / 2 + dy)

    # --- 운영·개발용 키 (화면에는 안내하지 않음) ---
    def on_key_press(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ESCAPE:
            self.quit_hold.press()      # 관람객이 실수로 끄지 않도록 3초 동안 누르고 있어야 종료
        elif self.booth:
            return
        elif symbol == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
            self.set_mouse_visible(not self.fullscreen)
        elif symbol == arcade.key.F3:
            self.debug = not self.debug

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ESCAPE:
            self.quit_hold.release()

    def tick(self, dt: float) -> None:
        if self.quit_hold.update(dt):
            self.close()

    # --- 창 선택 상태 (키 입력을 받을 수 있는지) ---
    def on_activate(self) -> None:
        self.focused = True

    def on_deactivate(self) -> None:
        self.focused = False

    def on_mouse_press(self, x: int, y: int, button: int, modifiers: int) -> None:
        self.focused = True

    @property
    def paused(self) -> bool:
        """키 입력을 받을 수 없어 게임·튜토리얼을 멈춰야 하는지 (자동 플레이는 멈추지 않음)."""
        return not self.focused and not self.autoplay

    def draw_overlay(self) -> None:
        """모든 화면 맨 위에 그리는 운영 안내. 각 View의 on_draw 끝(카메라 안)에서 부른다."""
        if self.paused:
            arcade.draw_lrbt_rectangle_filled(0, C.SCREEN_W, 0, C.SCREEN_H, (5, 8, 20, 200))
            self.focus_title.draw()
            self.focus_sub.draw()
        if self.quit_hold.active:
            self.quit_notice.text = f"종료하려면 ESC를 {self.quit_hold.remaining:.0f}초 더 누르고 있으세요"
            self.quit_notice.draw()

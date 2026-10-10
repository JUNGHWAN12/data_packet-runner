"""게임 창. 어떤 창 크기에서도 1920×1080 화면을 비율을 유지해(레터박스) 보여 준다."""

import arcade

from . import assets
from . import config as C
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
    def __init__(self, fullscreen: bool = False, autoplay: bool = False):
        super().__init__(*_window_size(), C.TITLE, fullscreen=fullscreen, resizable=True)
        self.autoplay = autoplay
        self.debug = False
        self.ranking = Ranking(C.RANKING_PATH)
        assets.load_font()
        self.camera = arcade.Camera2D(
            position=(C.SCREEN_W / 2, C.SCREEN_H / 2),
            projection=arcade.LRBT(-C.SCREEN_W / 2, C.SCREEN_W / 2, -C.SCREEN_H / 2, C.SCREEN_H / 2),
        )
        self._fit_camera(self.width, self.height)

    def _fit_camera(self, width: int, height: int) -> None:
        scale = min(width / C.SCREEN_W, height / C.SCREEN_H)
        vw, vh = C.SCREEN_W * scale, C.SCREEN_H * scale
        self.camera.viewport = arcade.LBWH((width - vw) / 2, (height - vh) / 2, vw, vh)

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        self._fit_camera(width, height)

    def shake(self, dx: float, dy: float) -> None:
        self.camera.position = (C.SCREEN_W / 2 + dx, C.SCREEN_H / 2 + dy)

    def on_key_press(self, symbol: int, modifiers: int) -> None:
        # 운영·개발용 키 (화면에는 안내하지 않음)
        if symbol == arcade.key.ESCAPE:
            self.close()
        elif symbol == arcade.key.F11:
            self.set_fullscreen(not self.fullscreen)
        elif symbol == arcade.key.F3:
            self.debug = not self.debug

"""게임 창. 어떤 창 크기에서도 1920×1080 화면을 비율을 유지해(레터박스) 보여 준다."""

import platform
import time

import arcade

from . import assets
from . import config as C
from .booth import CrashGuard, HoldTimer
from .logs import log
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
    """booth=True(부스 운영 모드): 전체 화면, 마우스 커서 숨김, 개발용 키(F3·F11) 끔, 창 닫기 막기.
    launcher=True(부스 런처에서 실행): 부스 모드와 같지만 한 판이 끝나면 스스로 꺼져(종료 코드 0) 런처로 돌아간다.
    시작 화면에서 ESC를 누르거나 아무도 1분 동안 누르지 않아도 꺼진다. 창 닫기(Alt+F4)도 허용한다."""

    def __init__(self, fullscreen: bool = False, autoplay: bool = False, booth: bool = False,
                 launcher: bool = False):
        self._ready = False             # 창 준비가 끝나기 전의 오류는 복구하지 않는다
        booth = booth or launcher
        super().__init__(*_window_size(), C.TITLE, fullscreen=fullscreen or booth, resizable=True)
        self.autoplay = autoplay
        self.booth = booth
        self.launcher = launcher
        self.debug = False
        self.focused = True             # 다른 창을 누르면 False → 게임을 멈추고 "화면을 클릭해 주세요"
        self.quit_hold = HoldTimer(C.QUIT_HOLD)
        self.close_notice = 0.0         # 부스 모드에서 창 닫기를 막았을 때 안내를 보여 줄 남은 시간
        self.crashes = CrashGuard(*C.CRASH_LIMIT)
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
        log.info("창 %dx%d, 전체 화면=%s, 부스 모드=%s, 자동 플레이=%s | Python %s, Arcade %s, %s | %s (OpenGL %s)",
                 self.width, self.height, self.fullscreen, booth, autoplay, platform.python_version(),
                 arcade.version.VERSION, platform.platform(), self.ctx.info.RENDERER,
                 ".".join(map(str, self.ctx.gl_version)))
        self._ready = True

    def _fit_camera(self, width: int, height: int) -> None:
        scale = min(width / C.SCREEN_W, height / C.SCREEN_H)
        vw, vh = C.SCREEN_W * scale, C.SCREEN_H * scale
        self.camera.viewport = arcade.LBWH((width - vw) / 2, (height - vh) / 2, vw, vh)

    def on_resize(self, width: int, height: int) -> None:
        super().on_resize(width, height)
        if hasattr(self, "camera"):     # 창을 만드는 도중에 오는 크기 변경은 __init__ 끝에서 맞춘다
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
        elif symbol == arcade.key.F12:
            raise RuntimeError("F12: 오류 복구 시험")     # 개발 모드에서 자동 복구가 되는지 확인하는 키

    def on_key_release(self, symbol: int, modifiers: int) -> None:
        if symbol == arcade.key.ESCAPE:
            self.quit_hold.release()

    def tick(self, dt: float) -> None:
        self.close_notice = max(0.0, self.close_notice - dt)
        if self.quit_hold.update(dt):
            log.info("ESC를 눌러 종료")
            self.close()

    def on_close(self) -> None:
        """Alt+F4·창 닫기 버튼. 부스 모드에서는 관람객이 끄지 못하도록 무시하고 ESC 3초로만 끈다."""
        if self.booth and not self.launcher:
            log.info("창 닫기 요청을 무시함 (부스 모드)")
            self.close_notice = 3.0
            return
        super().on_close()

    def end_session(self, reason: str) -> None:
        """한 사람의 체험이 끝났을 때: 런처 모드면 프로그램을 끝내 런처로, 아니면 시작 화면으로."""
        if self.launcher:
            log.info("%s — 런처로 돌아가기 위해 종료", reason)
            self.close()
            return
        from .views.title_view import TitleView
        self.show_view(TitleView())

    # --- 오류 복구 ---
    def dispatch_event(self, *args):
        """화면 갱신·그리기·키 입력은 모두 여기를 지난다. 오류가 나면 기록하고 시작 화면으로 돌아간다."""
        try:
            return super().dispatch_event(*args)
        except Exception:
            if not self._ready:
                raise
            self._recover(args[0] if args else "?")

    def _recover(self, event: str) -> None:
        view = self.current_view
        where = type(view).__name__ + (view.describe() if hasattr(view, "describe") else "")
        log.exception("오류 발생 (%s, %s) — 시작 화면으로 복구", event, where)
        if not self.crashes.record(time.monotonic()):
            log.critical("짧은 시간에 오류가 되풀이되어 프로그램을 끝냄")
            raise                       # main()이 기록하고 끝내면 run_booth.bat이 다시 시작한다
        self.shake(0, 0)
        self.quit_hold.release()
        from .views.title_view import TitleView
        self.show_view(TitleView())

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
        elif self.close_notice > 0:
            self.quit_notice.text = "종료하려면 ESC를 3초 동안 누르고 있으세요"
            self.quit_notice.draw()

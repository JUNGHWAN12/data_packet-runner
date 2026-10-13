"""부스 무인 운영용 시간 판정 (Arcade 비의존 — 단위 테스트 대상)."""


class HoldTimer:
    """일정 시간 누르고 있어야 동작하는 운영자 키 (ESC 종료, F9 순위 초기화)."""

    def __init__(self, need: float):
        self.need = need
        self.held: float | None = None

    def press(self) -> None:
        self.held = 0.0

    def release(self) -> None:
        self.held = None

    def update(self, dt: float) -> bool:
        """다 누르고 있었으면 한 번만 True."""
        if self.held is None:
            return False
        self.held += dt
        if self.held >= self.need:
            self.held = None
            return True
        return False

    @property
    def active(self) -> bool:
        return self.held is not None

    @property
    def remaining(self) -> float:
        return max(0.0, self.need - (self.held or 0.0))


class CrashGuard:
    """오류가 나면 시작 화면으로 복구하되, 짧은 시간에 되풀이되면 더 버티지 않고 프로그램을 끝낸다
    (같은 오류로 끝없이 돌지 않도록 — 부스 실행 파일 run_booth.bat이 프로그램을 새로 시작한다)."""

    def __init__(self, limit: int = 5, window: float = 30.0):
        self.limit = limit
        self.window = window
        self.times: list[float] = []

    def record(self, now: float) -> bool:
        """오류 시각을 기록한다. 아직 복구해도 되면 True."""
        self.times = [t for t in self.times if now - t < self.window] + [now]
        return len(self.times) <= self.limit


class IdleWatch:
    """게임 중 자리 비움: warn초 동안 입력이 없으면 경고, grace초 더 없으면 끝."""

    def __init__(self, warn: float, grace: float):
        self.warn = warn
        self.grace = grace
        self.idle = 0.0

    def poke(self) -> None:
        self.idle = 0.0

    def update(self, dt: float) -> None:
        self.idle += dt

    @property
    def warning(self) -> bool:
        return self.warn <= self.idle < self.warn + self.grace

    @property
    def expired(self) -> bool:
        return self.idle >= self.warn + self.grace

    @property
    def left(self) -> float:
        return max(0.0, self.warn + self.grace - self.idle)

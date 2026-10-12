"""아이템 효과 상태: 방화벽 실드, 라우팅 자석 (Arcade 비의존 — 단위 테스트 대상)."""

from . import config as C

DURATIONS = {"shield": C.SHIELD_TIME, "magnet": C.MAGNET_TIME}


class PowerUps:
    def __init__(self):
        self.remaining = {kind: 0.0 for kind in DURATIONS}

    def activate(self, kind: str) -> None:
        self.remaining[kind] = DURATIONS[kind]       # 이미 있으면 시간을 다시 채운다

    def update(self, dt: float) -> None:
        for kind in self.remaining:
            self.remaining[kind] = max(0.0, self.remaining[kind] - dt)

    def active(self, kind: str) -> bool:
        return self.remaining[kind] > 0

    def fraction(self, kind: str) -> float:
        return self.remaining[kind] / DURATIONS[kind]

    def absorb(self) -> bool:
        """충돌·추락을 실드가 막으면 True. 실드는 한 번 막으면 사라진다."""
        if self.active("shield"):
            self.remaining["shield"] = 0.0
            return True
        return False

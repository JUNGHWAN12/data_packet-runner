"""PACKET 글자 모으기 → 보너스 타임 (Arcade 비의존 — 단위 테스트 대상)."""

from . import config as C


class BonusLetters:
    def __init__(self):
        self.collected = 0              # 모은 글자 수 (P, A, C, K, E, T 순서)
        self.last_spawn_t = C.LETTER_FIRST - C.LETTER_EVERY
        self.on_field = False           # 지금 화면에 나와 있는 글자가 있는지
        self.bonus_left = 0.0
        self.done = False               # 한 판에 보너스는 한 번

    @property
    def next_letter(self) -> str | None:
        return None if self.collected >= len(C.BONUS_WORD) else C.BONUS_WORD[self.collected]

    def due(self, t: float) -> bool:
        """지금 글자를 하나 내보낼 차례인지."""
        return (not self.done and not self.on_field and self.next_letter is not None
                and t - self.last_spawn_t >= C.LETTER_EVERY)

    def spawned(self, t: float) -> None:
        self.on_field = True
        self.last_spawn_t = t

    def missed(self) -> None:
        self.on_field = False           # 같은 글자가 나중에 다시 나온다

    def collect(self) -> bool:
        """글자를 먹음. 마지막 글자였으면 보너스 타임을 시작하고 True."""
        self.on_field = False
        self.collected += 1
        if self.collected == len(C.BONUS_WORD):
            self.bonus_left = C.BONUS_TIME
            self.done = True
            return True
        return False

    def update(self, dt: float) -> None:
        self.bonus_left = max(0.0, self.bonus_left - dt)

    @property
    def in_bonus(self) -> bool:
        return self.bonus_left > 0

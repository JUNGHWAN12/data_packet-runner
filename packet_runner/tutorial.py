"""튜토리얼 조작 연습 판정 (Arcade 비의존 로직 — 단위 테스트 대상)."""

from . import config as C
from .player import PlayerBody, Pose

STEPS = ("jump", "double", "slide")


class Practice:
    """점프 → 2단 점프 → 슬라이딩을 실제로 해 봤는지 기록한다. 순서와 관계없이 해 본 것은 체크된다."""

    def __init__(self):
        self.done = dict.fromkeys(STEPS, False)
        self.was_on_ground = True

    def observe(self, body: PlayerBody) -> list[str]:
        """body.update() 뒤에 호출. 이번 프레임에 새로 해낸 단계 목록을 돌려준다."""
        hits = []
        if self.was_on_ground and not body.on_ground and body.vy > 0:
            hits.append("jump")
        if body.double_jumped:
            hits.append("double")
        if body.pose == Pose.SLIDE and body.on_ground and body.slide_time >= C.TUTORIAL_SLIDE_HOLD:
            hits.append("slide")
        self.was_on_ground = body.on_ground
        new = [step for step in hits if not self.done[step]]
        for step in new:
            self.done[step] = True
        return new

    @property
    def next_step(self) -> str | None:
        return next((step for step in STEPS if not self.done[step]), None)

    @property
    def complete(self) -> bool:
        return all(self.done.values())

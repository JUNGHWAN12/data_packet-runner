"""장애물 패턴과 난이도 곡선 (Arcade 비의존 — 단위 테스트 대상).

장애물은 완전 무작위가 아니라 '피할 수 있다고 검증된 패턴' 중에서 고른다.
패턴 안의 시각은 장애물 왼쪽 끝이 플레이어(발 중심)에 닿는 시각(초)이다.
"""

import random
from dataclasses import dataclass

from . import config as C

CONGESTION = "congestion"   # 네트워크 혼잡 구간 — 점프
CLOUD = "cloud"             # 통신 오류 구름 — 슬라이딩
GAP = "gap"                 # 연결 단절 구간(바닥 틈) — 점프
SPIKE = "spike"             # 트래픽 폭주(높이 쌓인 패킷 탑) — 2단 점프

ACTION = {CONGESTION: "jump", GAP: "jump", CLOUD: "slide", SPIKE: "double"}

# 앞 장애물이 끝난 뒤 다음 장애물이 시작될 때까지 필요한 최소 시간(초)
# (점프 체공 0.77초, 2단 점프 체공 약 1.2초, 반응 여유 약 0.3초를 기준으로 계산)
MIN_SPACING = {
    ("jump", "jump"): 0.95,
    ("jump", "slide"): 0.85,
    ("jump", "double"): 1.15,
    ("slide", "jump"): 0.75,
    ("slide", "slide"): 0.3,
    ("slide", "double"): 0.95,
    ("double", "jump"): 1.3,
    ("double", "slide"): 1.0,
    ("double", "double"): 1.35,
}

JUMP_APEX = C.JUMP_VELOCITY ** 2 / (2 * C.GRAVITY)
AIR_TIME = 2 * C.JUMP_VELOCITY / C.GRAVITY


@dataclass(frozen=True)
class Pattern:
    name: str
    items: tuple       # ((종류, 시작 시각), ...)
    zone: int          # 이 구간부터 등장


PATTERNS = [
    Pattern("congestion", ((CONGESTION, 0.0),), 0),
    Pattern("cloud", ((CLOUD, 0.0),), 0),
    Pattern("gap", ((GAP, 0.0),), 0),
    Pattern("double_congestion", ((CONGESTION, 0.0), (CONGESTION, 1.15)), 1),
    Pattern("congestion_cloud", ((CONGESTION, 0.0), (CLOUD, 1.05)), 1),
    Pattern("gap_congestion", ((GAP, 0.0), (CONGESTION, 1.3)), 1),
    Pattern("cloud_congestion", ((CLOUD, 0.0), (CONGESTION, 1.05)), 1),
    Pattern("spike", ((SPIKE, 0.0),), 1),
    Pattern("congestion_spike", ((CONGESTION, 0.0), (SPIKE, 1.35)), 1),
    Pattern("cloud_tunnel", ((CLOUD, 0.0), (CLOUD, 0.6)), 2),
    Pattern("gap_gap", ((GAP, 0.0), (GAP, 1.3)), 2),
    Pattern("gauntlet", ((CONGESTION, 0.0), (GAP, 1.15), (CLOUD, 2.5)), 2),
    Pattern("spike_cloud", ((SPIKE, 0.0), (CLOUD, 1.2)), 2),
    Pattern("gap_spike", ((GAP, 0.0), (SPIKE, 1.5)), 2),
]


def speed_at(t: float) -> float:
    keys = C.SPEED_KEYS
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            return v0 + (v1 - v0) * (t - t0) / (t1 - t0)
    return keys[-1][1]


def zone_at(t: float) -> int:
    zone = 0
    for i, (start, _) in enumerate(C.ZONES):
        if t >= start:
            zone = i
    return zone


def width_of(kind: str, speed: float) -> float:
    if kind == CONGESTION:
        return C.CONGESTION_BOX[0]
    if kind == CLOUD:
        return C.CLOUD_W
    if kind == SPIKE:
        return C.SPIKE_BOX[0]
    return speed * C.GAP_TIME


def duration_of(kind: str, speed: float) -> float:
    return width_of(kind, speed) / speed


def pattern_duration(pattern: Pattern, speed: float) -> float:
    kind, start = pattern.items[-1]
    return start + duration_of(kind, speed)


def rest_after(pattern: Pattern, zone_rest: float) -> float:
    """패턴 뒤 쉬는 시간. 다음 패턴이 무엇으로 시작해도 피할 수 있도록 마지막 장애물 기준으로 늘린다."""
    last = ACTION[pattern.items[-1][0]]
    return max(zone_rest, max(v for (a, _), v in MIN_SPACING.items() if a == last))


def jump_arc_height(dt: float) -> float:
    """점프 최고점을 기준으로 dt초 떨어진 시점의 발 높이."""
    return JUMP_APEX - 0.5 * C.GRAVITY * dt * dt


@dataclass
class Spawn:
    kind: str          # congestion / cloud / gap / fragment / token_slot
    x: float           # 패턴 시작 지점 기준 거리(px)
    y: float = 0.0     # 아이템 중심 높이(화면 좌표)
    width: float = 0.0


def layout(pattern: Pattern, speed: float, rest: float) -> tuple[list, float]:
    """패턴을 실제 배치(px)로 바꾼다. (배치 목록, 다음 패턴까지 거리)"""
    spawns = []
    for kind, start in pattern.items:
        x = start * speed
        w = width_of(kind, speed)
        spawns.append(Spawn(kind, x, width=w))
        center = x + w / 2
        if ACTION[kind] == "double":
            # 2단 점프로만 닿는 높이에 놓아 보너스처럼 보이게 한다
            for dt, h in ((-0.15, C.SPIKE_BOX[1] + 40), (0.0, C.SPIKE_BOX[1] + 110), (0.15, C.SPIKE_BOX[1] + 40)):
                spawns.append(Spawn("fragment", center + dt * speed, C.GROUND_Y + 57 + h))
        elif ACTION[kind] == "jump":
            # 점프 궤적을 따라 데이터 조각을 놓아 '언제 뛰어야 하는지' 보여 준다
            for dt in (-0.18, 0.0, 0.18):
                spawns.append(Spawn("fragment", center + dt * speed, C.GROUND_Y + 57 + jump_arc_height(dt)))
        else:
            for dx in (-66, 0, 66):
                spawns.append(Spawn("fragment", center + dx, C.GROUND_Y + 36))
    end = pattern_duration(pattern, speed) * speed
    # 쉬는 구간: 바닥 근처 데이터 조각 한 줄 + 재전송 토큰 후보 자리
    for i in range(3):
        spawns.append(Spawn("fragment", end + (0.25 + 0.15 * i) * speed, C.GROUND_Y + 60))
    spawns.append(Spawn("token_slot", end + 0.75 * speed, C.GROUND_Y + 90))
    return spawns, end + rest_after(pattern, rest) * speed


class PatternPicker:
    """구간에 맞는 패턴을 고른다. 새 구간의 패턴일수록 자주 나오고, 같은 패턴은 3번 연속 나오지 않는다."""

    def __init__(self, seed: int | None = None):
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.history: list = []

    def pick(self, zone: int) -> Pattern:
        pool = [p for p in PATTERNS if p.zone <= zone]
        weights = [2.0 if p.zone == zone else 1.0 for p in pool]
        while True:
            choice = self.rng.choices(pool, weights)[0]
            if self.history[-2:] != [choice.name, choice.name]:
                break
        self.history.append(choice.name)
        return choice

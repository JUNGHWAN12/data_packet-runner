"""모든 패턴이 피할 수 있는 간격인지, 장애물 크기가 의도한 동작을 강제하는지 검사한다."""

import pytest

from packet_runner import config as C
from packet_runner import patterns as P

ZONE_SPEEDS = {
    0: [v for t, v in C.SPEED_KEYS],                       # 처음 구간 패턴은 끝까지 나올 수 있음
    1: [v for t, v in C.SPEED_KEYS if t >= C.ZONES[1][0] - 5],
    2: [v for t, v in C.SPEED_KEYS if t >= C.ZONES[2][0] - 5],
}


@pytest.mark.parametrize("pattern", P.PATTERNS, ids=lambda p: p.name)
def test_pattern_spacing(pattern):
    speeds = [v for z in range(pattern.zone, 3) for v in ZONE_SPEEDS[z]]
    for speed in speeds:
        for (k1, t1), (k2, t2) in zip(pattern.items, pattern.items[1:]):
            gap = t2 - (t1 + P.duration_of(k1, speed))
            need = P.MIN_SPACING[(P.ACTION[k1], P.ACTION[k2])]
            assert gap >= need - 1e-9, f"{pattern.name}: {k1}->{k2} at {speed}px/s gap {gap:.2f}s < {need}s"


def test_rest_between_patterns_is_enough():
    assert min(C.ZONE_REST) >= max(P.MIN_SPACING.values())


def test_cloud_forces_slide():
    slide_top = C.SLIDE_BOX[1]
    stand_top = C.STAND_BOX[1]
    assert slide_top < C.CLOUD_BOTTOM < stand_top           # 슬라이딩하면 통과, 서 있으면 충돌
    assert P.JUMP_APEX + stand_top < C.CLOUD_TOP             # 점프로 넘을 수 없음


def test_congestion_can_be_jumped():
    assert P.JUMP_APEX > C.CONGESTION_BOX[1] * 2


def test_gap_can_be_jumped():
    for _, speed in C.SPEED_KEYS:
        gap_px = P.width_of(P.GAP, speed)
        assert P.AIR_TIME * speed > gap_px + 2 * C.FOOT_HALF + 0.2 * speed


def test_speed_curve():
    assert P.speed_at(0) == C.SPEED_KEYS[0][1]
    assert P.speed_at(60) == pytest.approx((C.SPEED_KEYS[1][1] + C.SPEED_KEYS[2][1]) / 2)
    assert P.speed_at(999) == C.SPEED_KEYS[-1][1]
    assert [P.zone_at(t) for t in (0, 59.9, 60, 119.9, 120, 179)] == [0, 0, 1, 1, 2, 2]


def test_picker_respects_zone_and_repeats():
    picker = P.PatternPicker(seed=42)
    for zone in (0, 1, 2):
        for _ in range(300):
            assert picker.pick(zone).zone <= zone
    h = picker.history
    assert all(not (h[i] == h[i + 1] == h[i + 2]) for i in range(len(h) - 2))


def test_layout_items_follow_pattern_order():
    pattern = next(p for p in P.PATTERNS if p.name == "gauntlet")
    spawns, length = P.layout(pattern, 600, 1.0)
    obstacles = [s for s in spawns if s.kind in (P.CONGESTION, P.GAP, P.CLOUD)]
    assert [s.kind for s in obstacles] == [k for k, _ in pattern.items]
    assert length > max(s.x for s in obstacles)

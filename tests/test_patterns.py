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


def test_cloud_forces_slide():
    slide_top = C.SLIDE_BOX[1]
    stand_top = C.STAND_BOX[1]
    assert slide_top < C.CLOUD_BOTTOM < stand_top           # 슬라이딩하면 통과, 서 있으면 충돌


def test_congestion_can_be_jumped():
    assert P.JUMP_APEX > C.CONGESTION_BOX[1] * 2


def test_congestion_hitbox_follows_cone_and_stays_inside_footprint():
    tiers = C.CONGESTION_TIERS
    widths = [hw for _, _, hw in tiers]
    assert widths == sorted(widths, reverse=True)           # 위로 갈수록 좁아짐
    assert all(hw * 2 <= C.CONGESTION_BOX[0] for hw in widths)
    assert tiers[-1][1] <= C.CONGESTION_BOX[1]
    assert all(a[1] == b[0] for a, b in zip(tiers, tiers[1:]))   # 단 사이에 빈틈 없음


def test_hitboxes_are_narrower_than_pictures():
    assert C.CLOUD_HIT_W < C.CLOUD_W
    assert C.SPIKE_HIT_W < C.SPIKE_BOX[0] - 6


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


def _double_jump_peak(tap_delay: float) -> float:
    """첫 점프 후 tap_delay초에 2단 점프했을 때 발의 최고 높이."""
    h = C.JUMP_VELOCITY * tap_delay - 0.5 * C.GRAVITY * tap_delay ** 2
    return h + C.DOUBLE_JUMP_VELOCITY ** 2 / (2 * C.GRAVITY)


def test_spike_needs_double_jump():
    assert P.JUMP_APEX < C.SPIKE_BOX[1] - 6                 # 한 번 점프로는 못 넘음 (충돌 높이 기준)
    for tap in (0.1, 0.2, 0.3, 0.4, 0.5, 0.6):               # 두 번째 Space를 언제 눌러도 넘을 수 있음
        assert _double_jump_peak(tap) > C.SPIKE_BOX[1]


def test_cloud_cannot_be_double_jumped():
    highest_feet = max(_double_jump_peak(t / 100) for t in range(1, 77))
    assert highest_feet + C.STAND_BOX[1] < C.CLOUD_TOP


def test_rest_after_covers_any_next_pattern():
    for pattern in P.PATTERNS:
        last = P.ACTION[pattern.items[-1][0]]
        for first in {P.ACTION[p.items[0][0]] for p in P.PATTERNS}:
            assert P.rest_after(pattern, min(C.ZONE_REST)) >= P.MIN_SPACING[(last, first)]


def test_phish_is_dodged_by_slide_but_hits_standing_player():
    bottom = C.PHISH_Y - P.ITEM_SIZE / 2
    assert C.SLIDE_BOX[1] < bottom < C.STAND_BOX[1]


def test_phish_layout_puts_real_fragments_at_slide_height():
    pattern = next(p for p in P.PATTERNS if p.name == "phish")
    spawns, _ = P.layout(pattern, 600, 1.0)
    bait = [s for s in spawns if s.kind == P.PHISH]
    real = [s for s in spawns if s.kind == "fragment" and abs(abs(s.x - bait[0].x) - 0.2 * 600) < 1]
    assert len(bait) == 1 and len(real) == 2
    for s in real:                             # 슬라이딩하면서도 진짜는 먹을 수 있다
        assert s.y - P.ITEM_SIZE / 2 < C.GROUND_Y + C.SLIDE_BOX[1]


def test_low_missile_needs_jump_high_missile_needs_slide():
    half = C.MISSILE_BOX[1] / 2
    low_bottom, low_top = C.MISSILE_LOW_Y - half, C.MISSILE_LOW_Y + half
    high_bottom = C.MISSILE_HIGH_Y - half
    assert low_bottom < C.SLIDE_BOX[1]                       # 낮은 미사일: 슬라이딩으로는 못 피함
    assert P.JUMP_APEX > low_top + 50                        # 점프로 넉넉히 넘음
    assert C.SLIDE_BOX[1] < high_bottom < C.STAND_BOX[1]     # 높은 미사일: 슬라이딩하면 통과, 서 있으면 충돌


def test_missile_arrives_with_static_obstacles_even_when_speed_changes():
    static_x, dt = C.SCREEN_W + 400.0, 1 / 120
    missile_x = P.missile_start_x(static_x)
    t, arrive = 0.0, {}
    while len(arrive) < 2:
        speed = 450 + 300 * (t % 1.0)                       # 감속·가속이 섞여도
        static_x -= speed * dt
        missile_x -= speed * C.MISSILE_FACTOR * dt
        t += dt
        if static_x <= C.PLAYER_X and "static" not in arrive:
            arrive["static"] = t
        if missile_x <= C.PLAYER_X and "missile" not in arrive:
            arrive["missile"] = t
    assert abs(arrive["static"] - arrive["missile"]) < 0.02

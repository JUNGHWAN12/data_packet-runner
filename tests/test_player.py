import pytest

from packet_runner import config as C
from packet_runner import patterns as P
from packet_runner.player import PlayerBody, Pose

DT = 1 / 120


def run(body, seconds, ground=True):
    for _ in range(int(seconds / DT)):
        body.update(DT, ground)


def test_jump_height_and_air_time():
    body = PlayerBody()
    body.press_jump()
    peak, t = 0.0, 0.0
    while True:
        body.update(DT, True)
        t += DT
        peak = max(peak, body.feet_y - C.GROUND_Y)
        if body.on_ground:
            break
    assert peak == pytest.approx(P.JUMP_APEX, rel=0.03)
    assert t == pytest.approx(P.AIR_TIME, abs=0.03)


def test_slide_changes_hitbox_and_min_time():
    body = PlayerBody()
    body.press_down()
    body.update(DT, True)
    assert body.pose == Pose.SLIDE
    assert body.rect().height == C.SLIDE_BOX[1]
    body.release_down()
    body.update(DT, True)
    assert body.pose == Pose.SLIDE              # 톡 눌러도 최소 시간은 유지
    run(body, C.MIN_SLIDE)
    assert body.pose == Pose.RUN
    assert body.rect().height == C.STAND_BOX[1]


def test_jump_cancels_slide():
    body = PlayerBody()
    body.press_down()
    body.update(DT, True)
    body.press_jump()
    body.update(DT, True)
    assert body.pose == Pose.JUMP and body.vy > 0


def test_fast_fall_lands_sooner_and_slides():
    normal = PlayerBody()
    normal.press_jump()
    fast = PlayerBody()
    fast.press_jump()
    t_normal = t_fast = 0.0
    while not normal.on_ground or t_normal == 0:
        normal.update(DT, True)
        t_normal += DT
    fast.update(DT, True)
    fast.press_down()
    t_fast = DT
    while not fast.on_ground:
        fast.update(DT, True)
        t_fast += DT
    assert t_fast < t_normal * 0.8
    assert fast.pose == Pose.SLIDE


def test_jump_buffer_before_landing():
    body = PlayerBody()
    body.press_jump()
    body.update(DT, True)
    while body.feet_y - C.GROUND_Y > 5 or body.vy > 0:
        body.update(DT, True)
    body.press_jump()                          # 착지 직전에 누름
    run(body, 0.05)
    assert body.vy > 0                         # 착지하자마자 다시 점프


def test_fall_into_gap_and_coyote_jump():
    body = PlayerBody()
    body.update(DT, False)                     # 발밑이 틈이 됨
    assert not body.on_ground
    body.press_jump()                          # 코요테 시간 안의 점프는 허용
    body.update(DT, False)
    assert body.vy > 0

    falling = PlayerBody()
    run(falling, 0.5, ground=False)
    assert falling.fell(False)
    falling.respawn()
    assert falling.on_ground and falling.feet_y == C.GROUND_Y


def test_double_jump_once_per_air_time():
    body = PlayerBody()
    body.press_jump()
    run(body, 0.3)
    body.press_jump()
    body.update(DT, True)
    assert body.vy == pytest.approx(C.DOUBLE_JUMP_VELOCITY - C.GRAVITY * DT, rel=0.01)
    run(body, 0.1)
    vy_before = body.vy
    body.press_jump()                          # 세 번째는 무시
    body.update(DT, True)
    assert body.vy < vy_before
    while not body.on_ground:
        body.update(DT, True)
    assert body.air_jumps == 1                 # 착지하면 다시 쓸 수 있음


def test_jump_press_right_before_landing_is_kept_for_ground_jump():
    body = PlayerBody()
    body.press_jump()
    body.update(DT, True)
    while body.vy > 0 or body.feet_y - C.GROUND_Y > 20:
        body.update(DT, True)
    body.press_jump()                          # 착지 직전 입력 → 2단 점프가 아니라 착지 후 점프
    landed = False
    for _ in range(int(0.1 / DT)):
        body.update(DT, True)
        landed = landed or body.vy > C.DOUBLE_JUMP_VELOCITY
    assert landed                              # 땅에서 새로 뛴 속도
    assert body.air_jumps == 1                 # 2단 점프는 아직 남아 있음


def test_walking_off_edge_allows_rescue_jump():
    body = PlayerBody()
    run(body, 0.2, ground=False)               # 코요테 시간이 지난 뒤
    body.press_jump()
    body.update(DT, False)
    assert body.vy > 0                         # 공중 점프로 살아날 수 있음

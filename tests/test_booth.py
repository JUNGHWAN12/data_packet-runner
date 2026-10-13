from packet_runner.booth import CrashGuard, HoldTimer, IdleWatch


def test_hold_fires_once_after_full_time():
    hold = HoldTimer(3.0)
    assert not hold.update(5.0)          # 누르지 않았으면 아무 일 없음
    hold.press()
    assert hold.active and not hold.update(2.9)
    assert round(hold.remaining, 2) == 0.1
    assert hold.update(0.2)
    assert not hold.active and not hold.update(1.0)


def test_hold_resets_when_released_early():
    hold = HoldTimer(3.0)
    hold.press()
    hold.update(2.5)
    hold.release()
    hold.press()
    assert not hold.update(2.5)          # 처음부터 다시 3초


def test_idle_warns_then_expires_and_input_resets():
    idle = IdleWatch(warn=15.0, grace=10.0)
    idle.update(14.9)
    assert not idle.warning and not idle.expired
    idle.update(0.2)
    assert idle.warning and round(idle.left, 1) == 9.9
    idle.poke()
    assert not idle.warning and idle.left == 25.0
    idle.update(25.0)
    assert idle.expired and not idle.warning


def test_crash_guard_allows_a_few_then_stops():
    guard = CrashGuard(limit=3, window=30.0)
    assert guard.record(0.0) and guard.record(1.0) and guard.record(2.0)
    assert not guard.record(3.0)            # 30초 안에 네 번째
    assert guard.record(40.0)               # 오래된 오류는 잊는다 (40초 시점엔 하나뿐)

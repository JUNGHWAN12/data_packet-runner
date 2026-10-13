from packet_runner import config as C
from packet_runner.powerups import PowerUps


def test_shield_blocks_once_then_disappears():
    p = PowerUps()
    assert not p.absorb()
    p.activate("shield")
    assert p.absorb()
    assert not p.active("shield")
    assert not p.absorb()


def test_effects_expire_and_refresh():
    p = PowerUps()
    p.activate("magnet")
    p.update(C.MAGNET_TIME / 2)
    assert p.active("magnet") and abs(p.fraction("magnet") - 0.5) < 1e-9
    p.activate("magnet")                       # 다시 먹으면 시간이 다시 찬다
    assert p.fraction("magnet") == 1.0
    p.update(C.MAGNET_TIME + 0.1)
    assert not p.active("magnet") and p.fraction("magnet") == 0.0


def test_shield_expires_without_hit():
    p = PowerUps()
    p.activate("shield")
    p.update(C.SHIELD_TIME)
    assert not p.absorb()

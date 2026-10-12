from packet_runner import config as C
from packet_runner.player import PlayerBody
from packet_runner.tutorial import Practice

DT = 1 / 60


def run(body: PlayerBody, practice: Practice, seconds: float) -> list[str]:
    seen = []
    for _ in range(round(seconds / DT)):
        body.update(DT, True)
        seen += practice.observe(body)
    return seen


def test_jump_then_double_jump():
    body, practice = PlayerBody(), Practice()
    assert practice.next_step == "jump"
    body.press_jump()
    assert run(body, practice, 0.15) == ["jump"]
    assert practice.next_step == "double"
    body.press_jump()                       # 공중에서 한 번 더
    assert run(body, practice, 1.5) == ["double"]
    assert practice.next_step == "slide" and not practice.complete


def test_slide_needs_holding():
    body, practice = PlayerBody(), Practice()
    body.press_down()
    run(body, practice, 0.1)
    body.release_down()                     # 톡 누르고 떼면 짧게 미끄러지고 끝
    assert run(body, practice, 1.0) == []
    body.press_down()
    assert run(body, practice, C.TUTORIAL_SLIDE_HOLD + 0.1) == ["slide"]


def test_each_step_counts_once_and_completes():
    body, practice = PlayerBody(), Practice()
    seen = []
    for _ in range(2):
        body.press_jump()
        seen += run(body, practice, 0.2)
        body.press_jump()
        seen += run(body, practice, 1.5)
    body.press_down()
    seen += run(body, practice, 0.6)
    assert seen == ["jump", "double", "slide"]
    assert practice.complete and practice.next_step is None

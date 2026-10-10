from packet_runner import config as C
from packet_runner.scoring import ScoreBoard, grade_for


def test_basic_scores():
    s = ScoreBoard()
    s.add_fragment()
    s.add_pass()
    s.arrive()
    assert s.score == C.SCORE_FRAGMENT + C.SCORE_PASS + C.SCORE_ARRIVAL
    assert (s.fragments, s.passed) == (1, 1)


def test_penalty_never_goes_below_zero():
    s = ScoreBoard(score=10)
    assert s.penalize() == 10
    assert s.score == 0
    assert s.penalize() == 0
    assert s.score == 0
    assert s.collisions == 2
    assert s.lost_pool == 10      # 실제로 깎인 점수만 유실 데이터로 기록


def test_token_restores_one_loss():
    s = ScoreBoard(score=100)
    s.penalize()
    s.penalize()
    assert (s.score, s.lost_pool) == (40, 60)
    gained, restored = s.use_token()
    assert (gained, restored) == (30, True)
    assert (s.score, s.lost_pool) == (70, 30)


def test_token_without_loss_gives_bonus():
    s = ScoreBoard()
    gained, restored = s.use_token()
    assert (gained, restored) == (C.SCORE_TOKEN_FALLBACK, False)
    assert s.score == C.SCORE_TOKEN_FALLBACK


def test_token_cannot_create_points_lost_at_zero():
    s = ScoreBoard()
    s.penalize()                  # 0점에서 충돌 → 잃은 점수 없음
    gained, restored = s.use_token()
    assert not restored
    assert s.score == C.SCORE_TOKEN_FALLBACK


def test_grade_boundaries():
    thresholds = [t for t, _ in C.GRADES]
    grades = [g for _, g in C.GRADES]
    for t, g in zip(thresholds, grades):
        assert grade_for(t) == g
    assert grade_for(thresholds[0] - 1) == grades[1]
    assert grade_for(0) == grades[-1]

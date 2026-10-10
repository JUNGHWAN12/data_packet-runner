import json
from datetime import datetime, timedelta

import pytest

from packet_runner import config as C
from packet_runner.ranking import ANONYMOUS, Ranking, Record, finalize_name, is_allowed_name


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock():
    return Clock(datetime(2026, 10, 10, 10, 0, 0))


@pytest.fixture
def ranking(tmp_path, clock):
    return Ranking(tmp_path / "ranking.json", clock=clock)


def add(ranking, clock, name, score, collisions=0, minutes=1):
    clock.now += timedelta(minutes=minutes)
    return ranking.add(ranking.new_record(name, score, 0, collisions, "A", 0))


def test_order_score_then_collisions_then_earlier(ranking, clock):
    add(ranking, clock, "AAA", 5000, collisions=2)
    add(ranking, clock, "BBB", 6000, collisions=5)
    add(ranking, clock, "CCC", 5000, collisions=1)
    add(ranking, clock, "DDD", 5000, collisions=1)     # 같은 점수·충돌 → 먼저 한 CCC가 앞
    assert [r.name for r in ranking.today()] == ["BBB", "CCC", "DDD", "AAA"]


def test_rank_if_added_and_top10(ranking, clock):
    for i in range(12):
        add(ranking, clock, "AAA", 1000 * (i + 1))
    assert len(ranking.top_today()) == C.RANKING_SIZE
    assert ranking.rank_if_added(12000, 0) == 2         # 같은 점수는 먼저 한 기록이 앞
    assert ranking.rank_if_added(99999, 0) == 1
    assert ranking.rank_if_added(500, 0) == 13
    assert ranking.rank_if_added(3001, 0) == C.RANKING_SIZE     # 4000~12000 아홉 개 다음
    assert ranking.rank_if_added(2500, 0) == C.RANKING_SIZE + 1


def test_today_resets_at_midnight_but_keeps_records(ranking, clock):
    add(ranking, clock, "OLD", 9000)
    clock.now = datetime(2026, 10, 11, 0, 0, 1)
    assert ranking.today() == []
    assert ranking.best_today_score() == 0
    assert ranking.best_all_time().name == "OLD"        # 역대 1위로는 남는다
    assert ranking.rank_if_added(10, 0) == 1


def test_saved_records_survive_restart(tmp_path, ranking, clock):
    add(ranking, clock, "KIM", 4321, collisions=3)
    again = Ranking(tmp_path / "ranking.json", clock=clock)
    assert again.today()[0] == ranking.today()[0]


def test_save_keeps_backup_and_leaves_no_temp(tmp_path, ranking, clock):
    add(ranking, clock, "AAA", 100)
    add(ranking, clock, "BBB", 200)
    assert (tmp_path / "ranking.json.bak").exists()
    assert not (tmp_path / "ranking.json.tmp").exists()
    backup = json.loads((tmp_path / "ranking.json.bak").read_text(encoding="utf-8"))
    assert len(backup["records"]) == 1                  # 저장 직전 상태


def test_broken_file_is_moved_aside(tmp_path, clock):
    path = tmp_path / "ranking.json"
    path.write_text("{ 반쯤 쓰인 파일", encoding="utf-8")
    ranking = Ranking(path, clock=clock)
    assert ranking.records == []
    assert list(tmp_path.glob("ranking_broken_*.json"))
    add(ranking, clock, "NEW", 10)                      # 이어서 정상 저장
    assert Ranking(path, clock=clock).today()[0].name == "NEW"


def test_reset_today_keeps_other_days_and_backs_up(tmp_path, ranking, clock):
    add(ranking, clock, "OLD", 9000)
    clock.now = datetime(2026, 10, 11, 9, 0, 0)
    add(ranking, clock, "NEW", 100)
    ranking.reset_today()
    assert ranking.today() == []
    assert [r.name for r in ranking.records] == ["OLD"]
    assert list(tmp_path.glob("ranking_reset_*.json"))


@pytest.mark.parametrize("name, ok", [
    ("ABC", True), ("abc", False), ("AB", False), ("ABCD", False), ("A1C", False),
    ("가나다", False), ("A-C", False), ("SEX", False),
])
def test_name_rules(name, ok):
    assert is_allowed_name(name) is ok


def test_finalize_name_on_timeout():
    assert finalize_name("") == ANONYMOUS
    assert finalize_name("ab") == "AB-"
    assert finalize_name("KIM") == "KIM"
    assert finalize_name("SEX") == ANONYMOUS


def test_record_has_all_fields(ranking, clock):
    record = ranking.new_record("LEE", 10, 1, 2, "C", 77)
    assert record == Record("LEE", 10, 1, 2, "C", "2026-10-10T10:00:00", 77)

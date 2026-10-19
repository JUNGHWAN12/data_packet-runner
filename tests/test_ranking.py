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


def test_banned_names_are_three_capital_letters():
    # 선생님이 목록을 고칠 때 소문자·2글자·숫자를 넣으면 그 이름은 막히지 않으므로 여기서 잡는다
    bad = [n for n in C.BANNED_NAMES if not (len(n) == C.NAME_LEN and n.isascii() and n.isalpha() and n.isupper())]
    assert bad == []


def test_banned_names_match_booth_common_list():
    # 부스의 세 게임이 같은 금칙어 119개를 쓴다. 한 게임만 고치면 다른 게임에서 등록되는 이름이 생긴다.
    assert len(C.BANNED_NAMES) == 119


@pytest.mark.parametrize("name", ["FKU", "SHT", "PRN", "NGR", "KMS", "JRL", "TLQ", "WHW", "GAY", "EHD",
                                  "SUS", "WHS", "QUD", "YMB"])  # 부스 공통 목록에서 더한 것
def test_banned_samples(name):
    assert not is_allowed_name(name)
    assert finalize_name(name.lower()) == ANONYMOUS


@pytest.mark.parametrize("name", ["KIM", "LEE", "PAK", "JIN", "SBS", "SSG", "BTS", "ZZZ", "AAA"])
def test_common_names_still_allowed(name):
    assert is_allowed_name(name)


def test_finalize_name_on_timeout():
    assert finalize_name("") == ANONYMOUS
    assert finalize_name("ab") == "AB-"
    assert finalize_name("KIM") == "KIM"
    assert finalize_name("SEX") == ANONYMOUS


def test_record_has_all_fields(ranking, clock):
    record = ranking.new_record("LEE", 10, 1, 2, "C", 77)
    assert record == Record("LEE", 10, 1, 2, "C", "2026-10-10T10:00:00", 77)


def test_anonymize_keeps_score_and_rank_and_saves(tmp_path, ranking, clock):
    add(ranking, clock, "AAA", 900)
    add(ranking, clock, "BAD", 800)
    bad = ranking.top_today()[1]
    assert ranking.anonymize(bad)
    assert [(r.name, r.score) for r in ranking.top_today()] == [("AAA", 900), (ANONYMOUS, 800)]
    reloaded = Ranking(ranking.path, clock=ranking.clock)          # 파일에도 저장됨
    assert [r.name for r in reloaded.top_today()] == ["AAA", ANONYMOUS]
    assert ranking.path.with_name(ranking.path.name + ".bak").exists()
    assert not ranking.anonymize(bad)                               # 이미 ???
    assert not ranking.anonymize(Record("ZZZ", 1, 0, 0, "C", "2026-10-10T10:00:00"))   # 목록에 없는 기록


def test_editable_adds_all_time_best_from_another_day(ranking, clock):
    add(ranking, clock, "OLD", 9000)                                # 어제 기록이 역대 1위
    clock.now += timedelta(days=1)
    add(ranking, clock, "NEW", 100)
    assert [r.name for r in ranking.editable()] == ["NEW", "OLD"]
    add(ranking, clock, "TOP", 9500)                                # 오늘 기록이 역대 1위면 한 번만
    assert [r.name for r in ranking.editable()] == ["TOP", "NEW"]

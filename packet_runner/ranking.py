"""로컬 랭킹: 체험 PC 한 대에 기록을 저장하고 오늘의 순위를 계산한다 (Arcade 비의존 — 단위 테스트 대상).

- 기록은 data/ranking.json 한 파일에 모두 쌓고, '오늘'은 플레이한 날짜로 거른다.
- 순위: 점수 높은 순 → 충돌 적은 순 → 먼저 달성한 순.
- 저장은 임시 파일에 쓴 뒤 바꿔 끼우므로 전원이 꺼져도 파일이 반쯤 쓰인 채로 남지 않는다.
"""

import json
import os
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from . import config as C

ANONYMOUS = "???"


@dataclass
class Record:
    name: str
    score: int
    fragments: int
    collisions: int
    grade: str
    played_at: str      # ISO 형식 로컬 시각, 예: 2026-10-10T14:03:22
    seed: int = 0


def sort_key(record: Record) -> tuple:
    return (-record.score, record.collisions, record.played_at)


class Ranking:
    def __init__(self, path: Path = C.RANKING_PATH, clock=datetime.now):
        self.path = Path(path)
        self.clock = clock
        self.records: list[Record] = []
        self.load()

    # --- 파일 ---
    def load(self) -> None:
        self.records = []
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self.records = [Record(**row) for row in data["records"]]
        except (ValueError, KeyError, TypeError):
            # 깨진 파일은 지우지 않고 옆으로 옮겨 두고 빈 랭킹으로 시작한다 (게임은 멈추지 않는다)
            broken = self.path.with_name(f"ranking_broken_{self._stamp()}.json")
            os.replace(self.path, broken)
            self.records = []

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_name(self.path.name + ".bak"))
        temp = self.path.with_name(self.path.name + ".tmp")
        payload = {"version": 1, "records": [asdict(r) for r in self.records]}
        temp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(temp, self.path)

    def _stamp(self) -> str:
        return self.clock().strftime("%Y%m%d_%H%M%S")

    # --- 조회 ---
    def today(self) -> list[Record]:
        day = self.clock().date().isoformat()
        return sorted((r for r in self.records if r.played_at[:10] == day), key=sort_key)

    def top_today(self, size: int = C.RANKING_SIZE) -> list[Record]:
        return self.today()[:size]

    def best_today_score(self) -> int:
        today = self.today()
        return today[0].score if today else 0

    def best_all_time(self) -> Record | None:
        return min(self.records, key=sort_key) if self.records else None

    def rank_if_added(self, score: int, collisions: int) -> int:
        """지금 이 점수를 기록하면 오늘 몇 위인지. 같은 점수·충돌이면 먼저 달성한 사람이 앞선다."""
        return 1 + sum(1 for r in self.today() if (-r.score, r.collisions) <= (-score, collisions))

    # --- 변경 ---
    def add(self, record: Record) -> int:
        rank = self.rank_if_added(record.score, record.collisions)
        self.records.append(record)
        self.save()
        return rank

    def new_record(self, name: str, score: int, fragments: int, collisions: int, grade: str, seed: int) -> Record:
        played_at = self.clock().isoformat(timespec="seconds")
        return Record(name, score, fragments, collisions, grade, played_at, seed)

    def reset_today(self) -> None:
        """운영자용: 오늘 기록만 지운다. 지우기 전 파일 전체를 백업한다."""
        if self.path.exists():
            shutil.copy2(self.path, self.path.with_name(f"ranking_reset_{self._stamp()}.json"))
        day = self.clock().date().isoformat()
        self.records = [r for r in self.records if r.played_at[:10] != day]
        self.save()


# --- 이름 (영문 3자) ---

def is_allowed_name(name: str) -> bool:
    return (len(name) == C.NAME_LEN and name.isascii() and name.isalpha() and name.isupper()
            and name not in C.BANNED_NAMES)


def finalize_name(partial: str) -> str:
    """시간이 다 됐을 때: 입력한 글자 뒤를 '-'로 채운다. 아무것도 없거나 부적절하면 '???'."""
    if not partial:
        return ANONYMOUS
    name = partial.upper()[:C.NAME_LEN].ljust(C.NAME_LEN, "-")
    return ANONYMOUS if name in C.BANNED_NAMES else name

"""로그 파일: 부스에서 생긴 오류와 판마다의 기록을 logs/game.log에 남긴다 (1MB씩 최대 5개 보관)."""

import logging
import logging.handlers
from pathlib import Path

log = logging.getLogger("packet_runner")


def setup(path: Path) -> None:
    """파일 로그를 켠다. 폴더에 쓸 수 없으면 화면(터미널)에만 남기고 게임은 계속한다."""
    for handler in list(log.handlers):
        log.removeHandler(handler)
        handler.close()
    log.setLevel(logging.INFO)
    log.propagate = False
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    log.addHandler(console)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = logging.handlers.RotatingFileHandler(path, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    except OSError as error:
        log.warning("로그 파일을 열 수 없음 (%s) — 화면에만 기록", error)
        return
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%Y-%m-%d %H:%M:%S"))
    log.addHandler(handler)

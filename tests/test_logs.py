import logging

from packet_runner import logs
from packet_runner.logs import log


def test_setup_writes_to_file_and_can_be_repeated(tmp_path):
    path = tmp_path / "logs" / "game.log"
    logs.setup(path)
    logs.setup(path)                        # 두 번 불러도 같은 줄이 두 번 쓰이지 않는다
    log.info("게임 시작 seed=%d", 42)
    for handler in log.handlers:
        handler.flush()
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1 and lines[0].endswith("INFO 게임 시작 seed=42")


def test_unwritable_folder_falls_back_to_console(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    logs.setup(blocker / "logs" / "game.log")   # 파일 아래에 폴더를 만들 수 없음
    assert all(not isinstance(h, logging.FileHandler) for h in log.handlers)
    log.info("그래도 오류 없이 계속")

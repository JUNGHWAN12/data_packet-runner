"""데이터 패킷 러너 실행: python main.py [--booth | --fullscreen] [--autoplay]"""

import argparse
import sys

import arcade

from packet_runner import config as C
from packet_runner import logs
from packet_runner.app import GameWindow
from packet_runner.logs import log
from packet_runner.views.title_view import TitleView


def main() -> None:
    parser = argparse.ArgumentParser(description="데이터 패킷 러너")
    parser.add_argument("--fullscreen", action="store_true", help="전체 화면으로 실행")
    parser.add_argument("--booth", action="store_true",
                        help="부스 운영 모드: 전체 화면, 마우스 커서 숨김, 개발용 키(F3·F11) 끔")
    parser.add_argument("--autoplay", action="store_true", help="자동 플레이(테스트·데모용)")
    args = parser.parse_args()

    logs.setup(C.LOG_PATH)
    log.info("===== 시작 %s", " ".join(sys.argv[1:]))
    try:
        window = GameWindow(fullscreen=args.fullscreen, autoplay=args.autoplay, booth=args.booth)
        window.show_view(TitleView())
        arcade.run()
    except Exception:
        # 화면 안에서 복구하지 못한 오류: 기록하고 오류 코드로 끝낸다 → run_booth.bat이 다시 시작
        log.exception("복구하지 못한 오류로 종료")
        sys.exit(1)
    log.info("===== 정상 종료")


if __name__ == "__main__":
    main()

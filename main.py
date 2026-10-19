"""데이터 패킷 러너 실행: python main.py [--launcher | --booth | --fullscreen] [--autoplay] [--check]"""

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
    parser.add_argument("--launcher", action="store_true",
                        help="부스 런처에서 실행: 부스 모드 + 한 판이 끝나거나 시작 화면에서 ESC를 누르면 꺼짐")
    parser.add_argument("--autoplay", action="store_true", help="자동 플레이(테스트·데모용)")
    parser.add_argument("--check", action="store_true", help="창을 띄우지 않고 파일·저장 폴더만 확인하고 끝냄")
    args = parser.parse_args()

    logs.setup(C.LOG_PATH)
    log.info("===== 시작 %s", " ".join(sys.argv[1:]))
    if args.check:
        sys.exit(check())
    try:
        window = GameWindow(fullscreen=args.fullscreen, autoplay=args.autoplay, booth=args.booth,
                            launcher=args.launcher)
        window.show_view(TitleView())
        arcade.run()
    except Exception:
        # 화면 안에서 복구하지 못한 오류: 기록하고 오류 코드로 끝낸다 → run_booth.bat이 다시 시작
        log.exception("복구하지 못한 오류로 종료")
        sys.exit(1)
    log.info("===== 정상 종료")


def check() -> int:
    """설치 점검: 게임에 필요한 파일이 있고 순위·로그 폴더에 쓸 수 있는지 (실행 파일을 만든 뒤 확인용)."""
    needed = [*C.FONT_PATHS, C.GENERATED / "icons" / "packet.png", C.GENERATED / "bg" / "skyline-a.png",
              C.GENERATED / "runner" / "run_0.png", C.GENERATED / "runner" / "dj_burst.png"]
    missing = [str(p) for p in needed if not p.exists()]
    for folder in (C.RANKING_PATH.parent, C.LOG_PATH.parent):
        try:
            folder.mkdir(parents=True, exist_ok=True)
            probe = folder / ".write_test"
            probe.write_text("ok")
            probe.unlink()
        except OSError as error:
            missing.append(f"{folder} (쓸 수 없음: {error})")
    # 콘솔 없는 .exe에서는 print가 보이지 않으므로 logs/game.log에도 남긴다
    result = "설치 점검: 문제 없음" if not missing else "설치 점검 문제: " + ", ".join(missing)
    for line in (f"게임 파일: {C.ROOT}", f"순위·로그: {C.DATA_ROOT}", result):
        print(line)
        log.info(line)
    return 0 if not missing else 1


if __name__ == "__main__":
    main()

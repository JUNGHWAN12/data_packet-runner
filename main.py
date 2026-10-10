"""데이터 패킷 러너 실행: python main.py [--fullscreen] [--autoplay]"""

import argparse

import arcade

from packet_runner.app import GameWindow
from packet_runner.views.title_view import TitleView


def main() -> None:
    parser = argparse.ArgumentParser(description="데이터 패킷 러너")
    parser.add_argument("--fullscreen", action="store_true", help="전체 화면으로 실행")
    parser.add_argument("--autoplay", action="store_true", help="자동 플레이(테스트·데모용)")
    args = parser.parse_args()

    window = GameWindow(fullscreen=args.fullscreen, autoplay=args.autoplay)
    window.show_view(TitleView())
    arcade.run()


if __name__ == "__main__":
    main()

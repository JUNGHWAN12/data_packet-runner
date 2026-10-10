"""원본 에셋(assets/source)을 게임용 이미지(assets/generated)로 변환한다.

    python tools/build_assets.py

- 러너 시트: 프레임을 잘라 같은 크기 캔버스에 발 위치·머리 위치를 맞춰 저장하고,
  JUMP DOWN 프레임을 회전해 슬라이딩 프레임을 만든다.
- Warped City 배경: 학교 부스에 맞지 않는 'BAR' 간판 글자를 'NET'으로 바꾼다.
- Lucide 아이콘: 24px로 래스터화 → 픽셀 정리 → 정수 배 확대 → 네온 발광.
  (cairosvg가 필요하다. 없으면 아이콘 단계만 건너뛴다.)

생성된 이미지는 저장소에 함께 커밋되어 있으므로 게임 실행에는 이 스크립트가 필요 없다.
"""

from pathlib import Path

from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "assets" / "source"
OUT = ROOT / "assets" / "generated"

# 러너 시트(runner_sheet.png)의 프레임 영역 (left, top, right, bottom) — 오른쪽·아래 포함
RUNNER_FRAMES = {
    "run_0": (22, 14, 74, 97),
    "run_1": (96, 4, 160, 97),
    "run_2": (174, 16, 249, 97),
    "run_3": (274, 14, 328, 97),
    "run_4": (350, 5, 410, 97),
    "run_5": (428, 18, 499, 97),
    "jump_up": (25, 164, 70, 260),
    "jump_down": (96, 164, 157, 255),
}
# 슬라이딩: JUMP DOWN을 뒤로 젖히는 방향(반시계)으로 회전한 각도
SLIDE_ANGLES = {"slide_0": 40, "slide_1": 75}
CANVAS = (120, 100)  # 모든 러너 프레임 공통 캔버스 (발 = 맨 아래 줄)
HEAD_ROWS = 35       # 머리 중심을 구할 때 보는 위쪽 줄 수

ICONS = {
    # 이름: (Lucide 아이콘, 색상, 확대 배수)
    "congestion": ("traffic-cone", "#FFB347", 5),
    "error_cloud": ("cloud-lightning", "#FF5D73", 8),
    "unplug": ("unplug", "#FF5D73", 3),
    "fragment": ("binary", "#7DFF9A", 3),
    "token": ("refresh-cw", "#FFE066", 3),
    "server": ("server", "#C49BFF", 9),
    "packet": ("mail", "#5EF2FF", 2),
}
GLOW_PAD = 12


def _trim(img: Image.Image) -> Image.Image:
    return img.crop(img.getbbox())


def _head_center_x(img: Image.Image) -> float:
    alpha = img.getchannel("A")
    xs = [x for y in range(min(HEAD_ROWS, img.height)) for x in range(img.width) if alpha.getpixel((x, y)) > 0]
    return sum(xs) / len(xs)


def _place(frame: Image.Image, center_x: float) -> Image.Image:
    canvas = Image.new("RGBA", CANVAS, (0, 0, 0, 0))
    left = round(CANVAS[0] / 2 - center_x)
    canvas.alpha_composite(frame, (left, CANVAS[1] - frame.height))
    return canvas


def _crop(sheet: Image.Image, name: str) -> Image.Image:
    l, t, r, b = RUNNER_FRAMES[name]
    return sheet.crop((l, t, r + 1, b + 1))


def build_runner() -> None:
    sheet = Image.open(SRC / "runner_sheet.png").convert("RGBA")
    out = OUT / "runner"
    out.mkdir(parents=True, exist_ok=True)
    # 달리기 프레임은 시트에서 이미 발 위치가 맞춰져 있으므로 아래 끝을 그대로 기준으로 쓴다.
    for name in RUNNER_FRAMES:
        frame = _crop(sheet, name)
        _place(frame, _head_center_x(frame)).save(out / f"{name}.png")
    jump_down = _crop(sheet, "jump_down")
    for name, angle in SLIDE_ANGLES.items():
        rotated = _trim(jump_down.rotate(angle, resample=Image.NEAREST, expand=True))
        _place(rotated, rotated.width / 2).save(out / f"{name}.png")
    print(f"runner: {len(RUNNER_FRAMES) + len(SLIDE_ANGLES)} frames -> {out}")


# 'NET' 글자 (3x6 픽셀)
GLYPHS = {
    "N": ["101", "111", "111", "101", "101", "101"],
    "E": ["111", "100", "110", "100", "100", "111"],
    "T": ["111", "010", "010", "010", "010", "010"],
}
BAR_SIGN = (426, 54, 436, 59)  # near-buildings-bg.png 안의 'BAR' 글자 영역 (포함)


def build_background() -> None:
    out = OUT / "bg"
    out.mkdir(parents=True, exist_ok=True)
    for name in ("skyline-a", "buildings-bg"):
        Image.open(SRC / "warped-city" / f"{name}.png").convert("RGBA").save(out / f"{name}.png")

    near = Image.open(SRC / "warped-city" / "near-buildings-bg.png").convert("RGBA")
    l, t, r, b = BAR_SIGN
    panel = near.getpixel((l - 1, t))  # 글자 바로 왼쪽 = 간판 바탕색
    ink = next(near.getpixel((x, t)) for x in range(l, r + 1) if near.getpixel((x, t)) != panel)
    for y in range(t, b + 1):
        for x in range(l, r + 1):
            near.putpixel((x, y), panel)
    for i, ch in enumerate("NET"):
        for dy, row in enumerate(GLYPHS[ch]):
            for dx, bit in enumerate(row):
                if bit == "1":
                    near.putpixel((l + i * 4 + dx, t + dy), ink)
    near.save(out / "near-buildings-bg.png")
    print(f"background: 3 layers -> {out}")


def _hex_to_rgb(color: str) -> tuple:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))


def build_icons() -> None:
    try:
        import cairosvg
    except ImportError:
        print("icons: cairosvg가 없어 건너뜀 (pip install cairosvg)")
        return
    import io

    out = OUT / "icons"
    out.mkdir(parents=True, exist_ok=True)
    for name, (icon, color, scale) in ICONS.items():
        svg = (SRC / "icons" / f"{icon}.svg").read_text(encoding="utf-8").replace("currentColor", color)
        png = cairosvg.svg2png(bytestring=svg.encode(), output_width=24, output_height=24)
        img = Image.open(io.BytesIO(png)).convert("RGBA")
        # 반투명 가장자리를 없애 픽셀아트처럼 만든다
        rgb = _hex_to_rgb(color)
        alpha = img.getchannel("A").point(lambda a: 255 if a >= 110 else 0)
        crisp = Image.new("RGBA", img.size, rgb + (0,))
        crisp.putalpha(alpha)
        big = crisp.resize((24 * scale, 24 * scale), Image.NEAREST)
        canvas = Image.new("RGBA", (big.width + GLOW_PAD * 2, big.height + GLOW_PAD * 2), (0, 0, 0, 0))
        canvas.alpha_composite(big, (GLOW_PAD, GLOW_PAD))
        glow_alpha = canvas.getchannel("A").filter(ImageFilter.GaussianBlur(GLOW_PAD / 2)).point(lambda a: int(a * 0.8))
        glow = Image.new("RGBA", canvas.size, rgb + (0,))
        glow.putalpha(glow_alpha)
        glow.alpha_composite(canvas)
        glow.save(out / f"{name}.png")
    print(f"icons: {len(ICONS)} -> {out}")


if __name__ == "__main__":
    build_runner()
    build_background()
    build_icons()

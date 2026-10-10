"""원본 에셋(assets/source)을 게임용 이미지(assets/generated)로 변환한다.

    python tools/build_assets.py

- 러너 시트: 프레임을 잘라 같은 크기 캔버스에 발 위치·머리 위치를 맞춰 저장한다.
- 슬라이딩 시트: 크게 그려진 슬라이딩 동작을 원본 러너 크기로 줄이고, 먼지를 지우고,
  가장자리를 선명하게 정리해 같은 캔버스에 맞춘다.
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
# 슬라이딩 시트(runner_slide_sheet.webp)는 8프레임: 달리기 2 → 젖히기 → 눕기 2 → 일어서기 2 → 달리기.
# 가운데 5프레임을 쓴다. (이름, 시트에서의 순서, 가운데 정렬 기준)
SLIDE_FRAMES = [
    ("slide_in", 2, "head"),      # 몸을 뒤로 젖히며 들어감
    ("slide_0", 3, "box"),        # 눕기 시작
    ("slide_1", 4, "box"),        # 완전히 누워 미끄러짐 (유지 동작)
    ("slide_out_0", 5, "head"),   # 손 짚고 일어남
    ("slide_out_1", 6, "head"),   # 다시 달리기 자세
]
SLIDE_SCALE = 0.44   # 슬라이딩 시트 → 원본 러너 크기 (머리 크기가 같아지는 배율)
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
    print(f"runner: {len(RUNNER_FRAMES)} frames -> {out}")


def _frame_columns(img: Image.Image) -> list:
    """투명한 세로줄로 나뉜 프레임들의 (왼쪽, 오른쪽) x 범위."""
    alpha = img.getchannel("A").point(lambda a: 255 if a >= 128 else 0)
    filled = [alpha.crop((x, 0, x + 1, img.height)).getbbox() is not None for x in range(img.width)]
    columns, start = [], None
    for x, on in enumerate(filled + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            columns.append((start, x))
            start = None
    return columns


def _remove_dust(img: Image.Image) -> Image.Image:
    """갈색 먼지 효과를 지운다 (게임에서는 코드로 불꽃 입자를 그린다)."""
    pixels = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = pixels[x, y]
            if a and r - b >= 20 and r <= 185 and g <= 160:
                pixels[x, y] = (0, 0, 0, 0)
    return img


def build_slide() -> None:
    sheet = Image.open(SRC / "runner_slide_sheet.webp").convert("RGBA")
    columns = _frame_columns(sheet)
    out = OUT / "runner"
    for name, index, align in SLIDE_FRAMES:
        left, right = columns[index]
        frame = _trim(_remove_dust(sheet.crop((left, 0, right, sheet.height))))
        size = (round(frame.width * SLIDE_SCALE), round(frame.height * SLIDE_SCALE))
        frame = frame.resize(size, Image.LANCZOS)
        # 반투명 가장자리를 없애 원본 픽셀아트처럼 선명하게
        frame.putalpha(frame.getchannel("A").point(lambda a: 255 if a >= 128 else 0))
        frame = _trim(frame)
        center = _head_center_x(frame) if align == "head" else frame.width / 2
        _place(frame, center).save(out / f"{name}.png")
    print(f"slide: {len(SLIDE_FRAMES)} frames -> {out}")


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
    build_slide()
    build_background()
    build_icons()

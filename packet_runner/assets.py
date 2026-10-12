"""이미지·글꼴 불러오기."""

from functools import cache

import arcade

from . import config as C


def load_font() -> None:
    for path in C.FONT_PATHS:
        arcade.load_font(path)


@cache
def icon(name: str) -> arcade.Texture:
    return arcade.load_texture(C.GENERATED / "icons" / f"{name}.png")


@cache
def background(name: str) -> arcade.Texture:
    return arcade.load_texture(C.GENERATED / "bg" / f"{name}.png")


@cache
def content_box(texture: arcade.Texture) -> tuple:
    """텍스처에서 투명하지 않은 영역 (left, bottom, right, top) — 텍스처 왼쪽 아래 기준 px."""
    left, top, right, bottom = texture.image.getbbox()
    h = texture.image.height
    return left, h - bottom, right, h - top


@cache
def letter(ch: str) -> arcade.Texture:
    """PACKET 글자 아이템: 노란 테두리 동그라미 안의 글자 (Galmuri 글꼴로 그린다)."""
    from PIL import Image, ImageDraw, ImageFont

    size = 84
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, size - 5, size - 5), fill=(20, 24, 40, 230), outline=(*C.YELLOW, 255), width=6)
    font = ImageFont.truetype(str(C.FONT_PATHS[1]), 46)
    draw.text((size / 2, size / 2 + 2), ch, font=font, fill=(*C.YELLOW, 255), anchor="mm")
    return arcade.Texture(img, hash=f"bonus-letter-{ch}")


def text(value: str, x: float, y: float, color=C.WHITE, size: float = 24, **kwargs) -> arcade.Text:
    kwargs.setdefault("bold", True)
    return arcade.Text(value, x, y, color, size, font_name=C.FONT_NAME, **kwargs)

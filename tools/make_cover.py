#!/usr/bin/env python3
"""Generate the A4 book cover (2480 x 3508, 300 dpi)."""
from __future__ import annotations
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = ROOT / "tools" / "fonts"
OUT = ROOT / "figures" / "cover.png"

W, H = 2480, 3508
PAPER = "#F7F4EC"
INK = "#1B2A2F"
TEAL = "#136F63"
DEEP = "#0D3B38"
AMBER = "#C07A2C"
MUTED = "#6B7885"


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def tracked(draw: ImageDraw.ImageDraw, xy, text, fnt, fill, spacing=0, anchor="la"):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=fnt, fill=fill, anchor=anchor)
        x += draw.textlength(ch, font=fnt) + spacing


def main() -> None:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img, "RGBA")

    # paper grain
    rnd = random.Random(2026)
    for _ in range(26000):
        x, y = rnd.randrange(W), rnd.randrange(H)
        g = rnd.randrange(120, 200)
        draw.point((x, y), fill=(g, g, g, 10))

    # left accent bar
    draw.rectangle([0, 0, 26, H], fill=TEAL)

    # top label
    label_font = font("NotoSansSC-Regular.otf", 42)
    tracked(draw, (250, 250), "TRAFFIC SIGNAL CONTROL ENGINEERING", label_font, TEAL, 6)
    draw.line([(250, 340), (W - 250, 340)], fill=(19, 111, 99, 90), width=3)

    # title
    title_font = font("NotoSansSC-Bold.otf", 300)
    draw.text((238, 560), "交通信号", font=title_font, fill=INK)
    draw.text((238, 900), "控制工程", font=title_font, fill=INK)

    # subtitle
    sub_font = font("NotoSansSC-Regular.otf", 118)
    draw.text((250, 1290), "数据、配时与执行", font=sub_font, fill=TEAL)
    draw.line([(250, 1450), (780, 1450)], fill=AMBER, width=8)

    # one-line positioning
    desc_font = font("NotoSansSC-Regular.otf", 52)
    draw.text((250, 1490), "从一次检测事件，到一次真实的绿灯", font=desc_font, fill=MUTED)

    # author
    author_font = font("NotoSansSC-Bold.otf", 76)
    draw.text((250, 1640), "郭海锋", font=author_font, fill=INK)
    suffix_font = font("NotoSansSC-Regular.otf", 46)
    draw.text((250 + draw.textlength("郭海锋", font=author_font) + 28, 1672), "著", font=suffix_font, fill=MUTED)

    # source-code credit
    credit_font = font("NotoSansSC-Regular.otf", 36)
    draw.text((250, 1762), "本书源码由视途智能 WaySense 团队提供", font=credit_font, fill=MUTED)

    # lower panel
    panel_top = 1960
    draw.rectangle([0, panel_top, W, H], fill=DEEP)
    draw.rectangle([0, panel_top, W, panel_top + 10], fill=AMBER)

    # grid
    for gy in range(panel_top + 150, 3300, 120):
        draw.line([(160, gy), (W - 160, gy)], fill=(255, 255, 255, 14), width=2)
    xs = [520, 1040, 1560, 2080]
    for x in xs:
        draw.line([(x, panel_top + 110), (x, 3300)], fill=(255, 255, 255, 55), width=4)

    # green bands
    for offset, alpha in [(0, 95), (300, 55)]:
        pts = [(300, 3100 - offset), (W - 260, 2340 - offset),
               (W - 260, 2340 - offset + 210), (300, 3100 - offset + 210)]
        draw.polygon(pts, fill=(73, 196, 158, alpha))

    # signal heads at each intersection
    for i, x in enumerate(xs):
        cy = panel_top + 230
        draw.rounded_rectangle([x - 30, cy - 78, x + 30, cy + 78], radius=18, fill="#101A1D")
        for k, color in enumerate(["#D64545", "#E0A72A", "#37B37A"]):
            r = 16
            y = cy - 46 + k * 46
            on = color == "#37B37A"
            draw.ellipse([x - r, y - r, x + r, y + r], fill=color if on else "#2A3239")
        draw.text((x, 3290), f"S{i+1}", font=font("NotoSansSC-Bold.otf", 46), fill="#EAF3EF", anchor="ma")

    # panel caption
    cap_font = font("NotoSansSC-Regular.otf", 54)
    small = font("NotoSansSC-Regular.otf", 30)
    tracked(draw, (300, 3370), "DATA  ·  TIMING  ·  EXECUTION", small, "#8FC9BB", 4)

    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT, optimize=True)
    print(OUT)


if __name__ == "__main__":
    main()

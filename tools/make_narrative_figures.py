#!/usr/bin/env python3
"""Generate the narrative/architecture figures added during the editorial pass."""

from __future__ import annotations

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FIGURES = ROOT / "figures"
FONT_PATH = Path(
    "/System/Library/AssetsV2/com_apple_MobileAsset_Font8/"
    "86ba2c91f017a3749571a82f2c6d890ac7ffb2fb.asset/AssetData/PingFang.ttc"
)

INK = "#1F2933"
MUTED = "#52606D"
ACCENT = "#136F63"
ACCENT_2 = "#2F6B5F"
LIGHT = "#E8F3F1"
PAPER = "#FBFAF6"
GRID = "#EEECE4"
CORAL = "#B94A3A"
GOLD = "#A8792D"
WHITE = "#FFFFFF"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size, index=1 if bold else 0)


def canvas(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (w, h), PAPER)
    return image, ImageDraw.Draw(image)


def text(draw, xy, s, size=30, bold=False, fill=INK, anchor=None):
    draw.text(xy, s, font=font(size, bold), fill=fill, anchor=anchor)


def center(draw, box, s, size=30, bold=False, fill=INK):
    x1, y1, x2, y2 = box
    draw.multiline_text(
        ((x1 + x2) / 2, (y1 + y2) / 2),
        s,
        font=font(size, bold),
        fill=fill,
        anchor="mm",
        align="center",
        spacing=8,
    )


def arrow(draw, start, end, color=MUTED, width=5, dash=None):
    if dash:
        x1, y1 = start
        x2, y2 = end
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        n = max(1, int(length / dash))
        for i in range(n):
            a = i / n
            b = min(1, (i + 0.55) / n)
            draw.line(
                (x1 + (x2 - x1) * a, y1 + (y2 - y1) * a,
                 x1 + (x2 - x1) * b, y1 + (y2 - y1) * b),
                fill=color, width=width,
            )
    else:
        draw.line((start, end), fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        d = 1 if x2 > x1 else -1
        pts = [(x2, y2), (x2 - 20 * d, y2 - 11), (x2 - 20 * d, y2 + 11)]
    else:
        d = 1 if y2 > y1 else -1
        pts = [(x2, y2), (x2 - 11, y2 - 20 * d), (x2 + 11, y2 - 20 * d)]
    draw.polygon(pts, fill=color)


def grid(draw, w, h, step=80):
    for x in range(0, w, step):
        draw.line((x, 0, x, h), fill=GRID, width=1)
    for y in range(0, h, step):
        draw.line((0, y, w, y), fill=GRID, width=1)


def battle_map():
    w, h = 3200, 1600
    image, draw = canvas(w, h)
    grid(draw, w, h, 80)

    road_y = 820
    x0, x1 = 220, 2980
    draw.rounded_rectangle((x0, road_y - 34, x1, road_y + 34), radius=34, fill="#E6EFEC")
    draw.line((x0, road_y, x1, road_y), fill=ACCENT, width=6)
    draw.line((x0, road_y - 16, x1, road_y - 16), fill="#A9C5BE", width=2)
    draw.line((x0, road_y + 16, x1, road_y + 16), fill="#A9C5BE", width=2)

    nodes = [(420, "S1"), (1080, "S2"), (1760, "S3"), (2440, "S4")]
    for x, label in nodes:
        draw.ellipse((x - 54, road_y - 54, x + 54, road_y + 54), fill=WHITE, outline=ACCENT, width=7)
        center(draw, (x - 54, road_y - 54, x + 54, road_y + 54), label, 50, True, ACCENT)

    # six battle markers: x, y, number, label, node line target
    markers = [
        (930, 540, "1", "漏检", (1080, 766)),
        (1200, 330, "2", "版本竞争", (1080, 766)),
        (1760, 330, "3", "周期发散", (1760, 766)),
        (1960, 560, "4", "协调失真", (1760, 766)),
        (2520, 1040, "5", "命令分家", (2440, 874)),
        (1720, 1120, "6", "评价误判", (1760, 874)),
    ]
    for x, y, num, label, target in markers:
        draw.line((x, y, target[0], target[1]), fill="#B9C8C3", width=3)
        draw.ellipse((x - 46, y - 46, x + 46, y + 46), fill=CORAL, outline=WHITE, width=5)
        center(draw, (x - 46, y - 46, x + 46, y + 46), num, 44, True, WHITE)
        tw = draw.textlength(label, font=font(60, True))
        draw.rounded_rectangle((x + 58, y - 38, x + 78 + tw, y + 38), radius=15, fill=WHITE, outline="#E2D8CA", width=2)
        text(draw, (x + 68, y), label, 60, True, INK, anchor="lm")

    # small reading-path legend
    lx, ly = 220, 1380
    text(draw, (lx, ly - 80), "三条读法", 38, True, MUTED)
    items = [(ACCENT, "战理线", None), (GOLD, "源码线", "dash"), (CORAL, "评点线", "dot")]
    for i, (color, label, style) in enumerate(items):
        x = lx + 190 + i * 460
        if style == "dash":
            for j in range(5):
                draw.line((x + j * 34, ly, x + j * 34 + 20, ly), fill=color, width=5)
        elif style == "dot":
            for j in range(6):
                draw.ellipse((x + j * 32, ly - 5, x + j * 32 + 10, ly + 5), fill=color)
        else:
            draw.line((x, ly, x + 150, ly), fill=color, width=5)
        text(draw, (x + 170, ly), label, 44, True, color, anchor="lm")

    text(draw, (230, 120), "S1—S4：一个晚高峰里的六场仗", 90, True, INK)
    text(draw, (230, 255), "六个现场不是六个孤立案例；它们共用同一条走廊、同一个时间基准。", 44, False, MUTED)
    image.save(FIGURES / "battle-map.png")


def six_layers():
    w, h = 2600, 1500
    image, draw = canvas(w, h)
    grid(draw, w, h, 80)
    text(draw, (110, 90), "六个层面，一本状态账", 86, True, INK)
    text(draw, (110, 225), "每一层回答一个固定问题，保管一类对象；层与层之间靠版本、时间和证据对齐。", 44, False, MUTED)
    layers = [
        ("物理控制层", "路口由什么设备执行信号", "信号机 / 检测器 / 实时阶段"),
        ("领域模型层", "系统如何描述道路和信号", "路口 / 车道 / 相位 / 方案"),
        ("算法计算层", "如何从需求得到候选方案", "流量比 / Webster / MaxBand"),
        ("数据层", "状态如何到达计算和评价", "事件 / Kafka / Flink / 时序库"),
        ("命令层", "方案如何安全到达设备", "校验 / 批次 / 确认 / 回滚"),
        ("观测层", "系统如何知道方案生效", "实时状态 / 日志 / 评价"),
    ]
    positions = [(110, 300), (920, 300), (1730, 300), (110, 820), (920, 820), (1730, 820)]
    for (title, q, objs), (x, y) in zip(layers, positions):
        draw.rounded_rectangle((x, y, x + 680, y + 380), radius=26, fill=WHITE, outline="#C9D8D4", width=3)
        draw.rounded_rectangle((x, y, x + 680, y + 72), radius=26, fill=LIGHT)
        draw.rectangle((x, y + 46, x + 680, y + 72), fill=LIGHT)
        text(draw, (x + 30, y + 36), title, 50, True, ACCENT)
        text(draw, (x + 30, y + 118), q, 44, True, INK)
        text(draw, (x + 30, y + 182), objs, 38, False, MUTED)
        text(draw, (x + 30, y + 268), "证据：字段 / 版本 / 时间", 36, False, MUTED)
        if x < 1500:
            arrow(draw, (x + 680, y + 190), (x + 790, y + 190), color="#A9C5BE", width=4)
    # bottom ledger spine
    draw.rounded_rectangle((110, 1270, 2410, 1370), radius=22, fill="#F4EFE6", outline="#D8C8B8", width=2)
    center(draw, (110, 1270, 2410, 1370), "六个层面各自保管状态；跨层传递时，都要带上来源、版本和时间", 44, True, "#6B4E32")
    image.save(FIGURES / "six-layers.png")


def offset_propagation():
    w, h = 2600, 1200
    image, draw = canvas(w, h)
    grid(draw, w, h, 80)
    text(draw, (110, 90), "S1—S4 的偏移传播", 86, True, INK)
    text(draw, (110, 225), "共同周期 92 s；正向累计行程时间 26 / 58 / 76 s。", 44, False, MUTED)
    axis_y = 690
    x0, x1 = 180, 2360
    draw.line((x0, axis_y, x1, axis_y), fill="#A9C5BE", width=6)
    # one cycle bracket
    draw.line((x0, 380, x1, 380), fill="#E2D8CA", width=3)
    draw.line((x0, 365, x0, 395), fill="#E2D8CA", width=3)
    draw.line((x1, 365, x1, 395), fill="#E2D8CA", width=3)
    text(draw, ((x0 + x1) / 2, 350), "一个周期 C = 92 s", 40, True, MUTED, anchor="ms")
    scale = (x1 - x0) / 92
    offsets = [0, 26, 58, 76]
    labels = ["S1", "S2", "S3", "S4"]
    for label, t in zip(labels, offsets):
        x = x0 + t * scale
        draw.rectangle((x - 92, axis_y - 105, x + 92, axis_y + 105), fill=LIGHT, outline="#BFD8D2", width=2)
        draw.line((x, axis_y - 140, x, axis_y + 140), fill=ACCENT, width=5)
        draw.ellipse((x - 18, axis_y - 18, x + 18, axis_y + 18), fill=WHITE, outline=ACCENT, width=4)
        text(draw, (x, axis_y + 175), label, 54, True, ACCENT, anchor="ma")
        text(draw, (x, axis_y + 235), f"{t} s", 40, False, MUTED, anchor="ma")
    for i in range(3):
        a = x0 + offsets[i] * scale
        b = x0 + offsets[i + 1] * scale
        arrow(draw, (a + 110, axis_y - 150), (b - 110, axis_y - 150), color=CORAL, width=4)
        t = offsets[i + 1] - offsets[i]
        text(draw, ((a + b) / 2, axis_y - 182), f"{t} s", 40, True, CORAL, anchor="ms")
    text(draw, (180, 1035), "偏移不是四个独立数字：从 S1 的基准出发，按有向路段累计行程时间推进；", 40, False, INK)
    text(draw, (180, 1085), "速度、路段顺序或关键阶段一变，后面的偏移都要重算。", 40, False, INK)
    image.save(FIGURES / "offset-propagation.png")


def coordination_tables():
    w, h = 3000, 1300
    image, draw = canvas(w, h)
    grid(draw, w, h, 80)
    text(draw, (110, 90), "生产协调的四张表", 86, True, INK)
    text(draw, (110, 225), "字段之间能互相解释，协调结果才可复算。", 44, False, MUTED)
    boxes = [
        ("link_list", "有向拓扑", "From / To / Length", "拓扑缺失"),
        ("subregion_stage_plan_table", "单点 StagePlan", "周期 / 阶段 / 绿窗", "方案不闭合"),
        ("maxband_input_table", "占比空间", "窗口 / 速度 / 相序", "状态不可行"),
        ("maxband_output_table", "周期 / 偏移 / 带宽", "Cycle / offset_abs / b", "结果不可实现"),
    ]
    xs = [100, 860, 1620, 2380]
    for (name, sub, fields, fail), x in zip(boxes, xs):
        draw.rounded_rectangle((x, 320, x + 620, 720), radius=24, fill=WHITE, outline="#C9D8D4", width=3)
        draw.rounded_rectangle((x, 320, x + 620, 390), radius=24, fill=LIGHT)
        draw.rectangle((x, 364, x + 620, 390), fill=LIGHT)
        text(draw, (x + 28, 350), name, 40, True, ACCENT)
        text(draw, (x + 28, 430), sub, 48, True, INK)
        text(draw, (x + 28, 500), fields, 36, False, MUTED)
        draw.rounded_rectangle((x + 28, 590, x + 592, 660), radius=15, fill="#FBF0ED", outline="#E2BDB4", width=2)
        text(draw, (x + 48, 625), "失败点：" + fail, 36, False, CORAL, anchor="lm")
        if x < 2300:
            arrow(draw, (x + 620, 520), (x + 720, 520), color="#A9C5BE", width=5)
    draw.rounded_rectangle((90, 850, 2910, 980), radius=22, fill="#F4EFE6", outline="#D8C8B8", width=2)
    center(draw, (90, 850, 2910, 980), "验收不是看某一张表“有值”，而是看四张表能否互相复算：拓扑 → 行程时间；单点 → 闭合；MaxBand → 状态；扫描 → 可实现", 42, True, "#6B4E32")
    text(draw, (110, 1080), "一张表的字段缺失，后面可能仍然输出“看起来正常”的零带宽或旧方案。", 40, False, INK)
    image.save(FIGURES / "coordination-tables.png")


if __name__ == "__main__":
    battle_map()
    six_layers()
    offset_propagation()
    coordination_tables()
    print("narrative figures written")

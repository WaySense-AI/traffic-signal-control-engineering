#!/usr/bin/env python3
"""Generate original raster figures used by the manuscript."""

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
LIGHT = "#E8F3F1"
LINE = "#B8C4CC"
CODE = "#F4F6F7"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size=size, index=1 if bold else 0)


def canvas(width: int, height: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    image = Image.new("RGB", (width, height), "white")
    return image, ImageDraw.Draw(image)


def centered_text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    text: str,
    text_font: ImageFont.FreeTypeFont,
    fill: str = INK,
) -> None:
    bounds = draw.multiline_textbbox((0, 0), text, font=text_font, spacing=8)
    x = (box[0] + box[2] - bounds[2]) / 2
    y = (box[1] + box[3] - bounds[3]) / 2
    draw.multiline_text((x, y), text, font=text_font, fill=fill, spacing=8)


def arrow(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: str = MUTED,
    width: int = 4,
) -> None:
    draw.line((start, end), fill=color, width=width)
    x1, y1 = start
    x2, y2 = end
    if abs(x2 - x1) >= abs(y2 - y1):
        direction = 1 if x2 > x1 else -1
        points = [(x2, y2), (x2 - 18 * direction, y2 - 10), (x2 - 18 * direction, y2 + 10)]
    else:
        direction = 1 if y2 > y1 else -1
        points = [(x2, y2), (x2 - 10, y2 - 18 * direction), (x2 + 10, y2 - 18 * direction)]
    draw.polygon(points, fill=color)


def draw_system_loop() -> None:
    image, draw = canvas(1800, 900)
    draw.text((100, 55), "交通信号控制的完整闭环", font=font(52, True), fill=INK)
    labels = [
        (100, 260, 380, 420, "检测数据\n流量 / 速度 / 排队"),
        (520, 260, 800, 420, "统一状态\n路网 / 信号 / 质量"),
        (940, 260, 1220, 420, "控制计算\n周期 / 绿信比 / 协调"),
        (1360, 260, 1640, 420, "方案校验\n安全 / 版本 / 设备"),
        (1360, 590, 1640, 750, "设备执行\n信号机 / 控制模式"),
        (940, 590, 1220, 750, "实时状态\n周期 / 阶段 / 确认"),
        (520, 590, 800, 750, "效果评价\n速度 / 溢出 / 拥堵"),
        (100, 590, 380, 750, "持续修正\n推荐 / 调度 / 回滚"),
    ]
    for x1, y1, x2, y2, label in labels:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=22, fill=LIGHT, outline=ACCENT, width=3)
        centered_text(draw, (x1, y1, x2, y2), label, font(30, True))
    arrow(draw, (380, 340), (500, 340))
    arrow(draw, (800, 340), (920, 340))
    arrow(draw, (1220, 340), (1340, 340))
    arrow(draw, (1500, 420), (1500, 570))
    arrow(draw, (1340, 670), (1240, 670))
    arrow(draw, (940, 670), (820, 670))
    arrow(draw, (520, 670), (400, 670))
    arrow(draw, (240, 570), (240, 440))
    image.save(FIGURES / "system-closed-loop.png")


def draw_plan_lifecycle() -> None:
    image, draw = canvas(2000, 760)
    draw.text((100, 55), "信号方案生命周期", font=font(52, True), fill=INK)
    states = [
        "草稿",
        "已计算",
        "已校验",
        "已调度",
        "设备接受",
        "运行确认",
    ]
    xs = [100, 405, 710, 1015, 1320, 1625]
    for x, label in zip(xs, states):
        draw.rounded_rectangle((x, 280, x + 250, 420), radius=18, fill=LIGHT, outline=ACCENT, width=3)
        centered_text(draw, (x, 280, x + 250, 420), label, font(29, True))
    for x in xs[:-1]:
        arrow(draw, (x + 250, 350), (x + 300, 350))
    draw.rounded_rectangle((1000, 555, 1250, 675), radius=18, fill="#FFF4E5", outline="#B26A00", width=3)
    centered_text(draw, (1000, 555, 1250, 675), "失败", font(29, True), fill="#7A4300")
    draw.rounded_rectangle((1320, 555, 1660, 675), radius=18, fill=CODE, outline=MUTED, width=3)
    centered_text(draw, (1320, 555, 1660, 675), "回滚并重新确认", font(27, True))
    arrow(draw, (1125, 420), (1125, 540), color="#B26A00")
    arrow(draw, (1250, 615), (1300, 615), color=MUTED)
    image.save(FIGURES / "plan-lifecycle.png")


def draw_stage_timeline() -> None:
    image, draw = canvas(1800, 760)
    draw.text((90, 45), "周期由阶段总时长构成", font=font(48, True), fill=INK)
    x0, y0, width, height = 110, 230, 1580, 180
    total = 90
    stages = [
        ("阶段 A", 28, "#27AE60"),
        ("绿闪", 3, "#F2C94C"),
        ("黄灯", 3, "#F2994A"),
        ("全红", 2, "#EB5757"),
        ("阶段 B", 21, "#27AE60"),
        ("绿闪", 3, "#F2C94C"),
        ("黄灯", 3, "#F2994A"),
        ("全红", 2, "#EB5757"),
        ("阶段 C", 17, "#27AE60"),
        ("绿闪", 3, "#F2C94C"),
        ("黄灯", 3, "#F2994A"),
        ("全红", 2, "#EB5757"),
    ]
    current = x0
    for label, seconds, color in stages:
        segment_width = width * seconds / total
        draw.rectangle(
            (current, y0, current + segment_width, y0 + height),
            fill=color,
            outline="white",
            width=2,
        )
        if seconds >= 10:
            centered_text(
                draw,
                (int(current), y0, int(current + segment_width), y0 + height),
                f"{label}\n{seconds}s",
                font(23, True),
                fill=INK if color in {"#F2C94C", "#F2994A"} else "white",
            )
        current += segment_width
    draw.line((x0, 510, x0 + width, 510), fill=INK, width=4)
    draw.text((x0, 540), "0s", font=font(25), fill=MUTED)
    draw.text((x0 + width - 40, 540), "90s", font=font(25), fill=MUTED)
    draw.text(
        (x0, 620),
        "纯绿、绿闪、黄灯和全红采用同一时间口径；周期一致性必须始终成立。",
        font=font(27),
        fill=MUTED,
    )
    image.save(FIGURES / "stage-timeline.png")


def draw_green_wave() -> None:
    image, draw = canvas(1800, 900)
    left, top, right, bottom = 190, 120, 1680, 760
    draw.line((left, bottom, right, bottom), fill=INK, width=4)
    draw.line((left, bottom, left, top), fill=INK, width=4)

    # time axis: 0..150 s
    for t in (0, 30, 60, 90, 120, 150):
        x = left + (right - left) * t / 150
        draw.line((x, bottom, x, bottom + 8), fill=INK, width=2)
        draw.text((x - 14, bottom + 16), str(t), font=font(22), fill=MUTED)
    draw.text((right - 55, bottom + 44), "时间/s", font=font(24), fill=MUTED)
    draw.text((left - 70, top - 42), "距离", font=font(24), fill=MUTED)

    # four intersections, S1 at the top
    stops = [170, 340, 510, 680]
    names = ["S1", "S2", "S3", "S4"]
    greens = [(0, 45), (20, 65), (40, 85), (60, 105)]
    for stop, name, (g0, g1) in zip(stops, names, greens):
        draw.line((left, stop, right, stop), fill=LINE, width=2)
        draw.text((left - 58, stop - 13), name, font=font(26, True), fill=INK)
        x0 = left + (right - left) * g0 / 150
        x1 = left + (right - left) * g1 / 150
        draw.rounded_rectangle((int(x0), stop - 13, int(x1), stop + 13), radius=10, fill="#8FD3C7")

    # a band of trajectories that clears all four greens
    def x_at(t: float) -> float:
        return left + (right - left) * t / 150
    y0, y3 = stops[0], stops[-1]
    starts = (5, 15, 25)
    travel = 75
    band = [(x_at(starts[0]), y0), (x_at(starts[0] + travel), y3),
            (x_at(starts[-1] + travel), y3), (x_at(starts[-1]), y0)]
    draw.polygon(band, fill="#E6F3F0")
    draw.line(band + [band[0]], fill="#A9D8CE", width=2)
    for t0 in starts:
        draw.line((x_at(t0), y0, x_at(t0 + travel), y3), fill=ACCENT, width=5)

    # bandwidth bracket at the bottom
    bx0, bx1, by = x_at(starts[0]), x_at(starts[-1]), 818
    draw.line((bx0, by, bx1, by), fill=ACCENT, width=4)
    draw.line((bx0, by - 10, bx0, by + 10), fill=ACCENT, width=4)
    draw.line((bx1, by - 10, bx1, by + 10), fill=ACCENT, width=4)
    draw.text(((bx0 + bx1) / 2 - 28, by - 38), "带宽", font=font(24, True), fill=ACCENT)

    draw.text((x_at(76), 270), "绿波带", font=font(28, True), fill=ACCENT)
    draw.text((x_at(76), 305), "车辆连续通过四个路口", font=font(21), fill=MUTED)
    image.save(FIGURES / "green-wave.png")

def draw_single_point_pipeline() -> None:
    image, draw = canvas(2000, 900)
    draw.text((90, 45), "单点配时计算链", font=font(48, True), fill=INK)
    labels = [
        (90, 230, 360, 390, "需求\n方向流量 / 时段"),
        (450, 230, 720, 390, "需求指标\n流量比 / 关键比"),
        (810, 230, 1080, 390, "结构筛选\n同相序候选"),
        (1170, 230, 1440, 390, "周期\n标定 / Webster"),
        (1530, 230, 1800, 390, "绿信比\n加权 / 修复"),
        (1530, 590, 1800, 750, "完整方案"),
        (1170, 590, 1440, 750, "安全校验"),
        (810, 590, 1080, 750, "指标比较"),
        (450, 590, 720, 750, "推荐审核"),
        (90, 590, 360, 750, "调度下发"),
    ]
    for x1, y1, x2, y2, label in labels:
        draw.rounded_rectangle((x1, y1, x2, y2), radius=20, fill=LIGHT, outline=ACCENT, width=3)
        centered_text(draw, (x1, y1, x2, y2), label, font(25, True))
    for start, end in (
        ((360, 310), (430, 310)),
        ((720, 310), (790, 310)),
        ((1080, 310), (1150, 310)),
        ((1440, 310), (1510, 310)),
        ((1665, 390), (1665, 570)),
        ((1530, 670), (1460, 670)),
        ((1170, 670), (1100, 670)),
        ((810, 670), (740, 670)),
        ((450, 670), (380, 670)),
    ):
        arrow(draw, start, end)
    image.save(FIGURES / "single-point-pipeline.png")


def draw_data_pipeline() -> None:
    image, draw = canvas(2000, 850)
    draw.text((90, 45), "实时交通数据链路", font=font(48, True), fill=INK)
    lanes = [
        ("检测事件", 140),
        ("信号状态", 330),
        ("控制任务", 520),
    ]
    for label, y in lanes:
        draw.rounded_rectangle((90, y, 360, y + 120), radius=18, fill=LIGHT, outline=ACCENT, width=3)
        centered_text(draw, (90, y, 360, y + 120), label, font(27, True))
        arrow(draw, (360, y + 60), (520, y + 60))
    draw.rounded_rectangle((540, 200, 830, 670), radius=20, fill=CODE, outline=MUTED, width=3)
    centered_text(draw, (540, 200, 830, 670), "Kafka\n事件通道", font(36, True))
    arrow(draw, (830, 435), (980, 435))
    draw.rounded_rectangle((1000, 200, 1360, 670), radius=20, fill=LIGHT, outline=ACCENT, width=3)
    centered_text(draw, (1000, 200, 1360, 670), "Flink\n时间窗口\n状态关联\n指标计算", font(31, True))
    arrow(draw, (1360, 435), (1510, 435))
    draw.rounded_rectangle((1530, 200, 1890, 670), radius=20, fill=CODE, outline=MUTED, width=3)
    centered_text(draw, (1530, 200, 1890, 670), "Doris / 搜索\n历史查询\n控制评价", font(31, True))
    draw.text(
        (90, 750),
        "事件时间、幂等键和状态版本决定链路是否可重放。",
        font=font(27),
        fill=MUTED,
    )
    image.save(FIGURES / "data-pipeline.png")


def draw_queue_response() -> None:
    image, draw = canvas(1800, 950)
    draw.text((90, 45), "固定方案下的周期排队响应", font=font(48, True), fill=INK)
    left, top, right, bottom = 170, 180, 1660, 790
    draw.line((left, bottom, right, bottom), fill=INK, width=4)
    draw.line((left, bottom, left, top), fill=INK, width=4)

    capacity = 20
    y_capacity = bottom - (bottom - top) * capacity / 40
    draw.line((left, y_capacity, right, y_capacity), fill="#B26A00", width=4)
    draw.text((right - 210, y_capacity - 44), "存储上限 20 辆", font=font(24, True), fill="#7A4300")

    values = [5.5, 10.75, 19.75, 28.75, 34.0, 35.5]
    xs = [
        left + (right - left) * index / max(1, len(values) - 1)
        for index in range(len(values))
    ]
    ys = [
        bottom - (bottom - top) * value / 40
        for value in values
    ]
    draw.line(list(zip(xs, ys)), fill=ACCENT, width=7)
    for index, (x, y, value) in enumerate(zip(xs, ys, values), start=1):
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=ACCENT)
        draw.text((x - 14, bottom + 28), str(index), font=font(22), fill=MUTED)
        draw.text((x - 26, y - 44), f"{value:g}", font=font(22, True), fill=INK)
    draw.text((right - 40, bottom + 28), "周期", font=font(24), fill=MUTED)
    draw.text((85, top), "车辆", font=font(24), fill=MUTED)
    draw.text((left + 28, top + 20), "理论排队（未限存储）", font=font(23, True), fill=ACCENT)
    draw.text(
        (left, 850),
        "当每周期到达超过服务能力时，排队持续累积；达到存储上限后，超出部分必须记录为上游溢出。",
        font=font(25),
        fill=MUTED,
    )
    image.save(FIGURES / "queue-response.png")


def draw_command_states() -> None:
    image, draw = canvas(2100, 920)
    draw.text((90, 50), "命令开始、确认与未知状态", font=font(50, True), fill=INK)
    nodes = {
        "requested": (90, 260, 340, 390),
        "accepted": (480, 260, 730, 390),
        "dispatched": (870, 260, 1120, 390),
        "observed": (1580, 260, 1950, 390),
        "unknown": (870, 590, 1120, 720),
        "failed": (1280, 590, 1540, 720),
        "rolled_back": (1600, 590, 1990, 720),
    }
    fill_by_name = {
        "unknown": "#FFF4E5",
        "failed": "#FBE9E7",
        "rolled_back": "#EEF5F3",
    }
    for name, box in nodes.items():
        draw.rounded_rectangle(box, radius=20, fill=fill_by_name.get(name, LIGHT), outline=ACCENT, width=3)
        centered_text(draw, box, name, font(27, True))
    arrow(draw, (340, 325), (460, 325))
    arrow(draw, (730, 325), (850, 325))
    arrow(draw, (1120, 325), (1560, 325))
    arrow(draw, (995, 390), (995, 570), color="#B26A00")
    arrow(draw, (1120, 655), (1260, 655), color=MUTED)
    arrow(draw, (1540, 655), (1580, 655), color=MUTED)
    arrow(draw, (1120, 590), (1560, 410), color="#B26A00")
    draw.text((410, 220), "accept", font=font(22), fill=MUTED)
    draw.text((760, 220), "dispatch", font=font(22), fill=MUTED)
    draw.text((1250, 220), "observe", font=font(22), fill=MUTED)
    draw.text((1015, 490), "timeout", font=font(22, True), fill="#7A4300")
    draw.text((1190, 465), "late observe", font=font(22, True), fill="#7A4300")
    draw.text((1140, 535), "fail", font=font(22), fill=MUTED)
    draw.text((1548, 535), "rollback", font=font(22), fill=MUTED)
    draw.text(
        (90, 810),
        "超时进入 unknown；迟到观测可收敛为 observed，明确拒绝或核查证据才收敛为 failed。",
        font=font(25),
        fill=MUTED,
    )
    image.save(FIGURES / "command-states.png")


def draw_adaptive_response() -> None:
    image, draw = canvas(1800, 900)
    draw.text((90, 45), "目标交替时的平滑响应", font=font(48, True), fill=INK)
    left, top, right, bottom = 150, 170, 1660, 750
    draw.line((left, bottom, right, bottom), fill=INK, width=4)
    draw.line((left, bottom, left, top), fill=INK, width=4)
    center_y = (top + bottom) / 2
    draw.line((left, center_y, right, center_y), fill=LINE, width=3)

    target = [10, -10, 10, -10, 10, -10, 10, -10, 10, -10]
    alpha_values = (0.3, 1.0)
    colors = (ACCENT, "#B26A00")
    for alpha, color in zip(alpha_values, colors):
        value = 0.0
        points = []
        for index, goal in enumerate(target):
            value = (1 - alpha) * value + alpha * goal
            x = left + (right - left) * index / (len(target) - 1)
            y = center_y - (bottom - top) * value / 28
            points.append((x, y))
        draw.line(points, fill=color, width=7)
        for point in points:
            draw.ellipse((point[0] - 7, point[1] - 7, point[0] + 7, point[1] + 7), fill=color)
    draw.text((right - 490, top + 20), "α = 0.3", font=font(24, True), fill=ACCENT)
    draw.text((right - 490, top + 60), "α = 1.0", font=font(24, True), fill="#7A4300")
    draw.text(
        (left, 810),
        "平滑降低摆动幅度，但目标持续交替时仍可能形成残余振荡；死区和确认负责把振荡转成保持决策。",
        font=font(25),
        fill=MUTED,
    )
    image.save(FIGURES / "adaptive-response.png")



def draw_request_lifecycle() -> None:
    """Ten hops from the platform button to a dispatched plan."""
    image, draw = canvas(1600, 1220)
    rows = [
        ("浏览器", "GET 请求：路口 ID + 起止日期", "日期字符串"),
        ("Java 控制器", "校验日期、方案、调度是否存在", "yyyy-MM-dd"),
        ("Java 服务", "日期转 Unix 秒，使用 JVM 时区", "Unix 秒"),
        ("Feign", "调 Python：/get_site_pattern_lib", "配置 URL"),
        ("Flask 路由", "转交单点优化任务", "Python datetime"),
        ("任务装配", "读拓扑：车道、相位、阶段、方案", "数据库快照"),
        ("参数配置", "周期五点、饱和流率、最小绿", "配置值"),
        ("流量", "15 分钟流向，多天平均，96 点", "15 min"),
        ("算法入口", "Model 或 Gradient Green 两条路", "周期 / 绿时"),
        ("结果回写", "DTO 返回前端，确认后下发", "秒 / 相位"),
    ]
    top = 100
    step = 108
    for index, (actor, action, tag) in enumerate(rows):
        y = top + index * step
        center = y + 34
        draw.ellipse((70, center - 26, 122, center + 26), fill=ACCENT)
        number = font(26, True)
        bounds = draw.textbbox((0, 0), str(index + 1), font=number)
        draw.text(
            (96 - (bounds[2] - bounds[0]) / 2, center - (bounds[3] - bounds[1]) / 2 - 2),
            str(index + 1),
            font=number,
            fill="white",
        )
        draw.text((165, center - 24), actor, font=font(31, True), fill=INK)
        draw.text((470, center - 21), action, font=font(28), fill=INK)
        tag_font = font(24)
        tag_width = draw.textbbox((0, 0), tag, font=tag_font)[2]
        draw.text((1470 - tag_width, center - 17), tag, font=tag_font, fill=MUTED)
        if index < len(rows) - 1:
            draw.line((96, center + 26, 96, center + step - 26), fill=LINE, width=3)
    image.save(FIGURES / "request-lifecycle.png")



def draw_fifteen_minute_grid() -> None:
    """How 15-minute input is rebuilt from 5-minute rows."""
    image, draw = canvas(1800, 1050)
    boxes = [
        ("1 分钟车道\n窗口 60 s\n水位线 30 s", 60),
        ("5 分钟路口\n窗口 300 s\n水位线 0", 470),
        ("ODP 5 分钟明细\nMySQL", 880),
        ("每 5 分钟重算\n最近 15 分钟", 1290),
    ]
    for label, x in boxes:
        draw.rounded_rectangle((x, 110, x + 330, 240), radius=16, fill=LIGHT, outline=ACCENT, width=3)
        centered_text(draw, (x, 110, x + 330, 240), label, font(26, True))
    for x in (390, 800, 1210):
        arrow(draw, (x + 70, 175), (x + 130, 175))

    # three overlapping 15-minute windows, each shifted by 5 minutes
    left, top, unit = 200, 360, 37
    span = 15 * unit
    labels = ["起点 t-15", "起点 t-10", "起点 t-5"]
    for index in range(3):
        x = left + index * 5 * unit
        y = top + index * 90
        draw.rounded_rectangle((x, y, x + span, y + 52), radius=8, fill=CODE, outline=MUTED, width=2)
        draw.text((x + 14, y + 12), labels[index], font=font(24), fill=INK)
    draw.line((left + span, top - 20, left + span, top + 300), fill=ACCENT, width=3)
    draw.text((left + span + 10, top - 40), "当前时刻 t", font=font(24, True), fill=ACCENT)
    draw.text((1180, 430), "同一时刻表里存在 3 份\n互相重叠的 15 分钟副本", font=font(27), fill=MUTED)
    draw.text((1180, 540), "直接 SUM 会把流量放大三倍", font=font(27, True), fill="#A33A2B")

    draw.rounded_rectangle((200, 760, 700, 860), radius=14, fill="white", outline=ACCENT, width=3)
    centered_text(draw, (200, 760, 700, 860), "MOD(start_minute, 15) = 0", font(26, True))
    draw.rounded_rectangle((760, 760, 1260, 860), radius=14, fill=LIGHT, outline=ACCENT, width=3)
    centered_text(draw, (760, 760, 1260, 860), "唯一 15 分钟栅格", font(26, True))
    draw.rounded_rectangle((1320, 760, 1720, 860), radius=14, fill=CODE, outline=MUTED, width=3)
    centered_text(draw, (1320, 760, 1720, 860), "算法输入", font(26, True))
    arrow(draw, (700, 810), (760, 810))
    arrow(draw, (1260, 810), (1320, 810))
    draw.line((860, 660, 860, 740), fill=MUTED, width=3)
    arrow(draw, (860, 720), (860, 750))

    draw.text(
        (100, 940),
        "15 分钟不是独立窗口，而是每 5 分钟对最近三段 5 分钟数据重新求和；去重靠查询层的模运算约定，代码里没有文档化。",
        font=font(24),
        fill=MUTED,
    )
    image.save(FIGURES / "fifteen-minute-grid.png")



def draw_ring_barrier() -> None:
    """Two rings, a shared barrier and an overlap phase, as stored in the schema."""
    image, draw = canvas(1800, 980)
    left, right = 220, 1600
    barrier = 900
    rows = [
        ("环 1", 220, [("阶段 A", 220, 640, LIGHT), ("阶段 B", 640, barrier, LIGHT), ("阶段 C", barrier, right, CODE)]),
        ("环 2", 400, [("阶段 A", 220, 640, LIGHT), ("阶段 D", 640, barrier, LIGHT), ("阶段 C", barrier, right, CODE)]),
    ]
    for label, y, blocks in rows:
        draw.text((70, y + 40), label, font=font(30, True), fill=INK)
        for text, x0, x1, fill in blocks:
            draw.rounded_rectangle((x0, y, x1, y + 90), radius=10, fill=fill, outline=ACCENT, width=3)
            centered_text(draw, (x0, y, x1, y + 90), text, font(27, True))

    draw.line((barrier, 190, barrier, 540), fill="#A33A2B", width=4)
    draw.text((barrier + 12, 160), "屏障 barrier", font=font(25, True), fill="#A33A2B")

    draw.rounded_rectangle((560, 340, 700, 378), radius=8, fill="#F3E4C8", outline="#A36B1B", width=2)
    centered_text(draw, (560, 340, 700, 378), "搭接", font(22, True))
    draw.line((630, 378, 630, 400), fill="#A36B1B", width=2)

    draw.text((220, 600), "每个阶段 = 一组相位位图；两个环共用一个屏障同步点。", font=font(27), fill=MUTED)
    draw.text((220, 660), "落库：r_split_plan（环方案）+ r_split_sequence（ring_no / phase / barrier_no）+ split_sequence（阶段顺序）。", font=font(25), fill=MUTED)
    draw.text((220, 720), "读取时由 RingManager 在内存里拼装；数据库不校验屏障与环号的组合。", font=font(25), fill=MUTED)
    draw.text((220, 810), "代价：表达力强，但同一结构在库表、内存对象、算法输入里是三套表示。", font=font(25, True), fill=INK)
    image.save(FIGURES / "ring-barrier.png")


def draw_dispatch_timeline() -> None:
    """One batch dispatch on a time axis: assemble, push, ACK window, retries."""
    image, draw = canvas(1800, 900)
    left, right = 180, 1680
    scale = (right - left) / 3.0  # three minutes across the canvas

    def x_of(minutes: float) -> float:
        return left + minutes * scale

    lanes = [("ai-auxiliary", 180), ("integration-data", 340), ("设备", 500)]
    for label, y in lanes:
        draw.text((40, y + 30), label, font=font(26, True), fill=INK)
        draw.line((left, y + 45, right, y + 45), fill=LINE, width=2)

    draw.line((left, 120, left, 620), fill=LINE, width=2)
    for minute in range(4):
        x = x_of(minute)
        draw.line((x, 110, x, 630), fill="#E3E8EC", width=1)
        draw.text((x - 20, 650), f"{minute} min", font=font(24), fill=MUTED)

    draw.ellipse((x_of(0.25) - 9, 213, x_of(0.25) + 9, 231), fill=ACCENT)
    draw.text((x_of(0.25) + 16, 200), "T+15s 组装任务", font=font(24, True), fill=INK)

    for minute in (1, 2, 3):
        draw.ellipse((x_of(minute) - 9, 373, x_of(minute) + 9, 391), fill=ACCENT)
        draw.ellipse((x_of(minute) - 9, 213, x_of(minute) + 9, 231), fill=ACCENT)
    draw.text((x_of(1) + 16, 360), "ElasticJob 每分钟取任务", font=font(24), fill=INK)

    draw.rectangle((x_of(1), 510, x_of(1) + 8 / 60 * scale, 560), fill="#F3E4C8", outline="#A36B1B", width=2)
    draw.text((x_of(1) + 8 / 60 * scale + 12, 516), "ACK 窗口 8 s", font=font(23, True), fill="#A36B1B")
    draw.text((x_of(1) + 16, 470), "TCP 单向写", font=font(24), fill=INK)

    draw.annotate if False else None
    draw.line((x_of(2), 560, x_of(2.9), 560), fill="#A33A2B", width=2)
    draw.text((x_of(2.05), 575), "未确认 → 下一轮重试，最多 3 次，无退避", font=font(22, True), fill="#A33A2B")
    draw.text((x_of(2.05), 610), "结束时间已过 → TASK_ENDTIME_EXPIRE，不再重试", font=font(22), fill=MUTED)

    draw.text((left, 760), "一次“下发成功”至少有四个含义：任务已建、任务已推、设备已 ACK、运行已确认。", font=font(26, True), fill=INK)
    draw.text((left, 810), "四级之间隔着分钟级调度和 8 秒关联窗口；任何一级断了，界面仍可能显示“已下发”。", font=font(24), fill=MUTED)
    image.save(FIGURES / "dispatch-timeline.png")


def main() -> None:
    FIGURES.mkdir(exist_ok=True)
    draw_system_loop()
    draw_plan_lifecycle()
    draw_stage_timeline()
    draw_green_wave()
    draw_single_point_pipeline()
    draw_data_pipeline()
    draw_queue_response()
    draw_command_states()
    draw_adaptive_response()
    draw_request_lifecycle()
    draw_fifteen_minute_grid()
    draw_ring_barrier()
    draw_dispatch_timeline()
    print("generated 13 figures")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Build the engineering-book DOCX from Markdown sources."""

from __future__ import annotations

import re
import json
from datetime import date
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import (
    WD_ALIGN_PARAGRAPH,
    WD_BREAK,
    WD_LINE_SPACING,
    WD_TAB_ALIGNMENT,
    WD_TAB_LEADER,
)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.shared import Cm, Inches, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"
BUILD = ROOT / "build"
BOOK_VERSION = "v3.19"
OUTPUT = BUILD / f"交通信号控制工程_{BOOK_VERSION}.docx"

FONT_BODY = "Noto Sans SC"
FONT_CODE = "Noto Sans Mono CJK SC"
BLACK = "000000"
INK = "1F2933"
MUTED = "52606D"
ACCENT = "136F63"
AFTERWORD_SIGNATURE = "郭海锋，2026年11月，杭州"
LIGHT = "EEF5F3"
CODE_FILL = "F4F6F7"
TABLE_HEADER = "D9E8E5"
TABLE_BORDER = "D9D9D9"

PART_INFO = {
    "part-01": ("第一部分 从路口到系统", "建立控制闭环、系统架构、领域模型与安全不变量。"),
    "part-02": ("第二部分 从交通到控制输入", "把检测数据、质量、容量和实时状态转换为控制输入。"),
    "part-03": ("第三部分 单点信号控制", "从相序、周期、绿信比到自适应和安全降级。"),
    "part-04": ("第四部分 区域协调控制", "组织子区、公共周期、相位差、带宽和时空图。"),
    "part-05": ("第五部分 平台工程", "连接算法、实时数据、命令状态和前端工作流。"),
    "part-06": ("第六部分 评价与综合实践", "评价控制效果并把全书链路落到完整案例。"),
    "part-07": (
        "第七部分 生产源码精读",
        "逐段阅读 WaySense 的真实 Python、Java、Flink 和前端实现。",
    ),
}


def _braced_argument(text: str, start: int) -> tuple[str, int]:
    while start < len(text) and text[start].isspace():
        start += 1
    if start >= len(text) or text[start] != "{":
        raise ValueError(f"expected '{{' at position {start}")
    depth = 0
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1 : index], index + 1
    raise ValueError("unbalanced braces in equation")


def _replace_fractions(text: str) -> str:
    while True:
        marker = text.find(r"\frac")
        if marker < 0:
            return text
        numerator, after_numerator = _braced_argument(text, marker + 5)
        denominator, after_denominator = _braced_argument(text, after_numerator)
        replacement = f"({numerator})/({denominator})"
        text = text[:marker] + replacement + text[after_denominator:]


def _replace_square_roots(text: str) -> str:
    while True:
        marker = text.find(r"\sqrt")
        if marker < 0:
            return text
        argument_start = marker + 5
        while argument_start < len(text) and text[argument_start].isspace():
            argument_start += 1
        if argument_start < len(text) and text[argument_start] == "{":
            argument, after = _braced_argument(text, marker + 5)
        else:
            match = re.match(r"[A-Za-z0-9]+", text[argument_start:])
            if match is None:
                raise ValueError(f"expected square-root argument at position {marker}")
            argument = match.group(0)
            after = argument_start + len(argument)
        text = text[:marker] + f"√({argument})" + text[after:]


def _replace_command_arguments(text: str, command: str) -> str:
    marker = "\\" + command
    while True:
        start = text.find(marker)
        if start < 0:
            return text
        argument, after = _braced_argument(text, start + len(marker))
        text = text[:start] + argument + text[after:]


def _replace_accent(text: str, command: str, combining_mark: str) -> str:
    greek = {
        "alpha": "α",
        "beta": "β",
        "delta": "δ",
        "Delta": "Δ",
        "eta": "η",
        "lambda": "λ",
        "rho": "ρ",
        "tau": "τ",
        "theta": "θ",
        "xi": "ξ",
    }
    pattern = re.compile(
        rf"\\{command}\s*(?:\{{([^{{}}]+)\}}|\\([A-Za-z]+)|([A-Za-z]))"
    )

    def replace(match: re.Match[str]) -> str:
        token = match.group(1) or greek.get(match.group(2), match.group(2)) or match.group(3)
        if token.startswith("\\"):
            return greek.get(token[1:], token) + combining_mark
        return "".join(character + combining_mark for character in token)

    return pattern.sub(replace, text)


UPRIGHT_OPEN = "\ue000"
UPRIGHT_CLOSE = "\ue001"


def _protect_upright(text: str) -> str:
    """Mark math fragments that must stay upright (units, function names)."""
    for command in ("mathrm", "text", "operatorname"):
        text = re.sub(
            r"\\" + command + r"\{([^{}]*)\}",
            lambda m: UPRIGHT_OPEN + m.group(1) + UPRIGHT_CLOSE,
            text,
        )
    return text


def latex_to_unicode(text: str) -> str:
    """Convert the small LaTeX subset used by the manuscript to readable text."""

    text = (

        text.replace(r"\begin{cases}", "")
        .replace(r"\end{cases}", "")
        .replace(r"\begin{aligned}", "\n")
        .replace(r"\end{aligned}", "")
    )
    text = text.replace(r"\_", "_")
    text = _replace_accent(text, "overline", "\u0304")
    text = _replace_accent(text, "bar", "\u0304")
    text = _replace_accent(text, "hat", "^")
    text = _replace_fractions(text)
    text = _replace_square_roots(text)
    text = _protect_upright(text)
    for command in ("mathbf", "mathcal", "mathbb"):
        text = _replace_command_arguments(text, command)

    replacements = {
        r"\left": "",
        r"\right": "",
        r"\qquad": "    ",
        r"\quad": "  ",
        r"\cdot": "×",
        r"\times": "×",
        r"\approx": "≈",
        r"\le": "≤",
        r"\ge": "≥",
        r"\neq": "≠",
        r"\ne": "≠",
        r"\notin": "∉",
        r"\forall": "∀",
        r"\in": " ∈ ",
        r"\to": " → ",
        r"\cap": " ∩ ",
        r"\bigcap": " ∩ ",
        r"\bigcup": " ∪ ",
        r"\land": " ∧ ",
        r"\lor": " ∨ ",
        r"\mid": " | ",
        r"\subseteq": " ⊆ ",
        r"\bmod": " " + UPRIGHT_OPEN + "mod" + UPRIGHT_CLOSE + " ",
        r"\sum": UPRIGHT_OPEN + "Σ" + UPRIGHT_CLOSE,
        r"\max": UPRIGHT_OPEN + "max" + UPRIGHT_CLOSE,
        r"\min": UPRIGHT_OPEN + "min" + UPRIGHT_CLOSE,
        r"\lfloor": UPRIGHT_OPEN + "floor(" + UPRIGHT_CLOSE,
        r"\rfloor": UPRIGHT_OPEN + ")" + UPRIGHT_CLOSE,
        r"\lceil": UPRIGHT_OPEN + "ceil(" + UPRIGHT_CLOSE,
        r"\rceil": UPRIGHT_OPEN + ")" + UPRIGHT_CLOSE,
        r"\infty": "∞",
        r"\ldots": "…",
        r"\dots": "…",
        r"\cdots": "⋯",
        r"\pm": "±",
        r"\alpha": "α",
        r"\beta": "β",
        r"\gamma": "γ",
        r"\delta": "δ",
        r"\Delta": "Δ",
        r"\epsilon": "ε",
        r"\eta": "η",
        r"\theta": "θ",
        r"\xi": "ξ",
        r"\lambda": "λ",
        r"\mu": "μ",
        r"\pi": "π",
        r"\rho": "ρ",
        r"\sigma": "σ",
        r"\tau": "τ",
        r"\phi": "φ",
        r"\Phi": "Φ",
        r"\omega": "ω",
        r"\ell": "ℓ",
        r"\log": UPRIGHT_OPEN + "log" + UPRIGHT_CLOSE,
        r"\ln": UPRIGHT_OPEN + "ln" + UPRIGHT_CLOSE,
        r"\mathbb": "",
        r"\,": " ",
        r"\;": " ",
        r"\!": "",
        r"\{": "{",
        r"\}": "}",
        r"\%": "%",
        r"\|": "‖",
        r"\_": "_",
        r"\ ": " ",
        "\\\\": "\n",
        "&": " ",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"\s*=\s*", " = ", text)
    # Sub/superscripts stay as markers; the DOCX writer turns them into real
    # subscript/superscript runs instead of literal "_(" / "^(" text.
    text = re.sub(r"_\{([^{}]*)\}", r"_{\1}", text)
    text = re.sub(r"\^\{([^{}]*)\}", r"^{\1}", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = text.strip()
    unsupported = sorted(set(re.findall(r"\\[A-Za-z]+", text)))
    if unsupported:
        raise ValueError(f"unsupported LaTeX commands: {unsupported}")
    return text


def normalize_inline_math(text: str) -> str:
    return re.sub(
        r"\\\((.+?)\\\)",
        lambda match: latex_to_unicode(match.group(1)),
        text,
    )


def set_run_font(run, name: str, size: float | None = None, bold: bool | None = None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), name)
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), FONT_BODY)
    if size is not None:
        run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_border(cell, color: str = TABLE_BORDER) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = f"w:{edge}"
        element = borders.find(qn(tag))
        if element is None:
            element = OxmlElement(tag)
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), color)


def set_paragraph_shading(paragraph, fill: str) -> None:
    p_pr = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    p_pr.append(shading)


def remove_style_border(style) -> None:
    p_pr = style.element.get_or_add_pPr()
    border = p_pr.find(qn("w:pBdr"))
    if border is not None:
        p_pr.remove(border)


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = " PAGE "
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    run._r.extend((begin, instruction, separate, end))
    set_run_font(run, FONT_BODY, 8.5)
    run.font.color.rgb = RGBColor.from_string(MUTED)



def add_heading_inline(paragraph, text: str, size: float) -> None:
    """Render a heading text with inline code, keeping the heading size."""
    text = normalize_inline_math(text)
    pattern = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            run = paragraph.add_run(text[position : match.start()])
            set_run_font(run, FONT_BODY, size, True)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, FONT_BODY, size, True)
        else:
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, FONT_CODE, size * 0.92, True)
            run.font.color.rgb = RGBColor.from_string(INK)
        position = match.end()
    if position < len(text):
        run = paragraph.add_run(text[position:])
        set_run_font(run, FONT_BODY, size, True)


MATH_TOKEN = re.compile(r"\\(.+?)\\")
MATH_SPLIT = re.compile(r"(_\{[^{}]*\}|\^\{[^{}]*\}|_[A-Za-z0-9+\-*]|\^[A-Za-z0-9+\-*])")


def math_segments(text: str) -> list[tuple[str, str | None]]:
    """Split converted math text into normal / subscript / superscript parts."""
    segments: list[tuple[str, str | None]] = []
    position = 0
    for match in MATH_SPLIT.finditer(text):
        if match.start() > position:
            segments.append((text[position : match.start()], None))
        token = match.group(0)
        if token.startswith("_"):
            body = token[2:-1] if token.startswith("_{") else token[1:]
            segments.append((body, "sub"))
        else:
            body = token[2:-1] if token.startswith("^{") else token[1:]
            segments.append((body, "sup"))
        position = match.end()
    if position < len(text):
        segments.append((text[position:], None))
    return segments


UPRIGHT_RE = re.compile(UPRIGHT_OPEN + r"(.*?)" + UPRIGHT_CLOSE)


def add_math_runs(paragraph, text: str, size: float, bold: bool = False) -> None:
    for body, mode in math_segments(text):
        if not body:
            continue
        for part in UPRIGHT_RE.split(body):
            if not part:
                continue
            upright = False
            if part.startswith(UPRIGHT_OPEN) and part.endswith(UPRIGHT_CLOSE):
                part = part[1:-1]
                upright = True
            run = paragraph.add_run(part)
            set_run_font(run, FONT_BODY, size, bold)
            run.italic = not upright
            if mode == "sub":
                run.font.subscript = True
            elif mode == "sup":
                run.font.superscript = True


def add_inline(paragraph, text: str) -> None:
    pattern = re.compile(
        r"(\*\*.+?\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\)|\\\(.+?\\\))"
    )
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            run = paragraph.add_run(text[position : match.start()])
            set_run_font(run, FONT_BODY, 10.5)
        token = match.group(0)
        if token.startswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, FONT_BODY, 10.5, True)
        elif token.startswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, FONT_CODE, 9.4)
            run.font.color.rgb = RGBColor.from_string(ACCENT)
        elif token.startswith("\\("):
            add_math_runs(paragraph, latex_to_unicode(token[2:-2]), 10.5)
        else:
            link_match = re.fullmatch(r"\[([^\]]+)\]\(([^)]+)\)", token)
            if link_match is None:
                raise AssertionError(f"invalid inline token: {token}")
            label, url = link_match.groups()
            add_hyperlink(paragraph, label, url)
        position = match.end()
    if position < len(text):
        run = paragraph.add_run(text[position:])
        set_run_font(run, FONT_BODY, 10.5)


def add_hyperlink(paragraph, label: str, url: str) -> None:
    relationship_id = paragraph.part.relate_to(url, RT.HYPERLINK, is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), relationship_id)
    run = paragraph.add_run(label)
    set_run_font(run, FONT_BODY, 10.5)
    run.font.color.rgb = RGBColor.from_string(ACCENT)
    run.font.underline = True
    hyperlink.append(run._r)
    paragraph._p.append(hyperlink)


def configure_document(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.15)
    section.bottom_margin = Cm(2.1)
    section.left_margin = Cm(2.25)
    section.right_margin = Cm(2.25)
    section.header_distance = Cm(1.0)
    section.footer_distance = Cm(0.9)

    normal = document.styles["Normal"]
    normal.font.name = FONT_BODY
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(INK)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    normal.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    normal.paragraph_format.line_spacing = Pt(24)
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.widow_control = True

    for style_name, size, before, after in (
        ("Title", 30, 0, 18),
        ("Heading 1", 20, 0, 16),
        ("Heading 2", 14, 15, 7),
        ("Heading 3", 11.5, 11, 5),
    ):
        style = document.styles[style_name]
        style.font.name = FONT_BODY
        style.font.size = Pt(size)
        style.font.bold = style_name != "Heading 3"
        style.font.color.rgb = RGBColor.from_string(BLACK)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True
        if style_name == "Heading 1":
            style.paragraph_format.line_spacing = 1.15
        remove_style_border(style)

    caption = document.styles["Caption"]
    caption.font.name = FONT_BODY
    caption.font.size = Pt(8.5)
    caption.font.color.rgb = RGBColor.from_string(MUTED)
    caption.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
    caption.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    caption.paragraph_format.space_after = Pt(8)
    for style_name, bold in (("FigureCaption", False), ("TableCaption", True)):
        style = document.styles.add_style(style_name, WD_STYLE_TYPE.PARAGRAPH)
        style.base_style = caption
        style.font.name = FONT_BODY
        style.font.size = Pt(9)
        style.font.bold = bold
        style.font.color.rgb = RGBColor.from_string(INK)
        style.element.rPr.rFonts.set(qn("w:eastAsia"), FONT_BODY)
        style.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        style.paragraph_format.space_after = Pt(6)

    add_page_number(section.footer.paragraphs[0])
    document.core_properties.title = "交通信号控制工程：数据、配时与执行"
    document.core_properties.subject = "交通信号控制工程"
    document.core_properties.author = "郭海锋"
    document.core_properties.keywords = "交通信号控制, 配时, 绿波, 自适应控制, 系统工程"


def add_cover(document: Document) -> None:
    cover_path = ROOT / "figures" / "cover.png"
    if cover_path.exists():
        section = document.sections[0]
        section.different_first_page_header_footer = True
        section.left_margin = Cm(0)
        section.right_margin = Cm(0)
        section.top_margin = Cm(0)
        section.bottom_margin = Cm(0)
        section.footer_distance = Cm(0)
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        paragraph.paragraph_format.line_spacing = 1.0
        picture = paragraph.add_run().add_picture(str(cover_path), width=Cm(20.95))
        doc_properties = picture._inline.docPr
        doc_properties.set("descr", "封面：交通信号控制工程，作者郭海锋")
        doc_properties.set("title", "封面")
        new_section = document.add_section(WD_SECTION.NEW_PAGE)
        new_section.left_margin = Cm(2.25)
        new_section.right_margin = Cm(2.25)
        new_section.top_margin = Cm(2.15)
        new_section.bottom_margin = Cm(2.1)
        new_section.footer_distance = Cm(0.9)
        new_section.different_first_page_header_footer = False
        new_section.footer.is_linked_to_previous = False
        add_page_number(new_section.footer.paragraphs[0])
        return

    for _ in range(4):
        document.add_paragraph()
    label = document.add_paragraph()
    label.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = label.add_run("TRAFFIC SIGNAL CONTROL ENGINEERING")
    set_run_font(run, FONT_BODY, 12, True)
    run.font.color.rgb = RGBColor.from_string(ACCENT)

    title = document.add_paragraph(style="Title")
    title.paragraph_format.space_before = Pt(10)
    run = title.add_run("交通信号控制工程")
    set_run_font(run, FONT_BODY, 30, True)
    run.font.color.rgb = RGBColor.from_string(BLACK)

    subtitle = document.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(26)
    run = subtitle.add_run("数据、配时与执行")
    set_run_font(run, FONT_BODY, 18, False)
    run.font.color.rgb = RGBColor.from_string(BLACK)

    description = document.add_paragraph()
    description.paragraph_format.right_indent = Cm(1.6)
    run = description.add_run(
        "从路口冲突、检测数据、单点配时和区域协调，到实时链路、设备下发与效果评价。"
    )
    set_run_font(run, FONT_BODY, 11)
    run.font.color.rgb = RGBColor.from_string(MUTED)

    author = document.add_paragraph()
    run = author.add_run("郭海锋 著")
    set_run_font(run, FONT_BODY, 13, True)
    run.font.color.rgb = RGBColor.from_string(INK)

    for _ in range(6):
        document.add_paragraph()
    meta = document.add_paragraph()
    run = meta.add_run(f"{BOOK_VERSION} · {date.today().isoformat()}")
    set_run_font(run, FONT_BODY, 10, True)
    run.font.color.rgb = RGBColor.from_string(INK)



def add_frontispiece(document: Document) -> bool:
    """Insert the full-page frontispiece after the cover, without a folio."""
    frontispiece_path = ROOT / "figures" / "frontispiece.png"
    if not frontispiece_path.exists():
        return False

    section = document.sections[-1]
    section.left_margin = Cm(0)
    section.right_margin = Cm(0)
    section.top_margin = Cm(0)
    section.bottom_margin = Cm(0)
    section.footer_distance = Cm(0)
    section.footer.is_linked_to_previous = False
    for paragraph in section.footer.paragraphs:
        paragraph.clear()

    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(0)
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    paragraph.paragraph_format.line_spacing = 1.0
    picture = paragraph.add_run().add_picture(str(frontispiece_path), height=Cm(28.5))
    doc_properties = picture._inline.docPr
    doc_properties.set(
        "descr",
        "扉页：道以立本，术以致用，知行相证，方为工程；作者郭海锋",
    )
    doc_properties.set("title", "扉页")

    body = document.add_section(WD_SECTION.NEW_PAGE)
    body.left_margin = Cm(2.25)
    body.right_margin = Cm(2.25)
    body.top_margin = Cm(2.15)
    body.bottom_margin = Cm(2.1)
    body.footer_distance = Cm(0.9)
    body.different_first_page_header_footer = False
    body.footer.is_linked_to_previous = False
    add_page_number(body.footer.paragraphs[0])
    return True

def add_contents(
    document: Document,
    chapters: list[tuple[str, str, str]],
    page_map: dict[str, int],
) -> None:
    heading = document.add_heading("目录", level=1)
    heading.paragraph_format.page_break_before = True
    for run in heading.runs:
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:ascii"), FONT_BODY)
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:hAnsi"), FONT_BODY)
        run._element.get_or_add_rPr().get_or_add_rFonts().set(qn("w:eastAsia"), FONT_BODY)
    last_part = ""
    for part_dir, title, description in chapters:
        if part_dir == "appendices" and last_part != "appendices":
            p = document.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run("附录")
            set_run_font(run, FONT_BODY, 10, True)
            last_part = "appendices"
        if part_dir in PART_INFO and part_dir != last_part:
            p = document.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            run = p.add_run(PART_INFO[part_dir][0])
            set_run_font(run, FONT_BODY, 10, True)
            last_part = part_dir
        p = document.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.6)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.tab_stops.add_tab_stop(
            Cm(15.6), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS
        )
        run = p.add_run(title)
        set_run_font(run, FONT_BODY, 9.5)
        run.font.color.rgb = RGBColor.from_string(MUTED)
        if title in page_map:
            page_run = p.add_run(f"\t{page_map[title]}")
            set_run_font(page_run, FONT_BODY, 9.5)
            page_run.font.color.rgb = RGBColor.from_string(MUTED)


def add_part_page(document: Document, part_dir: str) -> None:
    title, description = PART_INFO[part_dir]
    p = document.add_heading(title, level=1)
    p.paragraph_format.page_break_before = True
    p.paragraph_format.space_before = Cm(4.2)
    for run in p.runs:
        set_run_font(run, FONT_BODY, 24, True)
        run.font.color.rgb = RGBColor.from_string(BLACK)
    p2 = document.add_paragraph()
    p2.paragraph_format.space_after = Pt(18)
    run = p2.add_run(description)
    set_run_font(run, FONT_BODY, 11)
    run.font.color.rgb = RGBColor.from_string(MUTED)

    opener_path = ROOT / "figures" / f"{part_dir}-opener.png"
    if opener_path.exists():
        image_p = document.add_paragraph()
        image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        image_p.paragraph_format.space_before = Pt(4)
        image_p.paragraph_format.space_after = Pt(14)
        image_p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        image_p.paragraph_format.line_spacing = 1.0
        picture = image_p.add_run().add_picture(str(opener_path), width=Cm(16.2))
        doc_properties = picture._inline.docPr
        doc_properties.set("descr", "")
        doc_properties.set("title", "部分题图（装饰）")

    overview_path = MANUSCRIPT / "part-overviews" / f"{part_dir}.md"
    if overview_path.exists():
        parse_markdown(
            document,
            overview_path.read_text(encoding="utf-8"),
            first_h1=True,
        )


def add_code_block(document: Document, text: str, language: str = "") -> None:
    lines = text.rstrip("\n").splitlines() or [""]
    p = document.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.right_indent = Cm(0.2)
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after = Pt(8)
    p.paragraph_format.line_spacing = 1.0
    p.paragraph_format.keep_together = len(lines) <= 22
    set_paragraph_shading(p, CODE_FILL)
    for index, line in enumerate(lines):
        if index:
            p.add_run().add_break()
        run = p.add_run(line.replace("\t", "    "))
        set_run_font(run, FONT_CODE, 8.1 if len(lines) > 16 else 8.5)
        run.font.color.rgb = RGBColor.from_string(INK)


def add_equation_block(document: Document, text: str) -> None:
    # Source formulas are wrapped for readability. Ordinary newlines must not
    # become printed line breaks; only an explicit LaTeX "\\" may break a line.
    # Split on that explicit break before conversion, so the LaTeX converter
    # never has to guess whether a backslash pair is a line break or content.
    text = text.replace("\\\\", "\x00")
    text = re.sub(r"\s*\n\s*", " ", text)
    chunks = text.split("\x00")
    converted: list[str] = []
    for chunk in chunks:
        converted.extend(line.strip() for line in latex_to_unicode(chunk).splitlines() if line.strip())
    lines = converted or [""]
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.space_before = Pt(5)
    paragraph.paragraph_format.space_after = Pt(7)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    paragraph.paragraph_format.line_spacing = Pt(13)
    paragraph.paragraph_format.keep_together = True
    for index, line in enumerate(lines):
        add_math_runs(paragraph, line, 10.2)
        if index < len(lines) - 1:
            paragraph.runs[-1].add_break()

def add_table(document: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    columns = len(rows[0])
    table = document.add_table(rows=len(rows), cols=columns)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    table.style = "Table Grid"
    header_row = table.rows[0]
    header_row_properties = header_row._tr.get_or_add_trPr()
    table_header = OxmlElement("w:tblHeader")
    table_header.set(qn("w:val"), "true")
    header_row_properties.append(table_header)
    for row in table.rows:
        row_properties = row._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))
    for row_index, row in enumerate(rows):
        for column_index in range(columns):
            cell = table.cell(row_index, column_index)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell.text = ""
            paragraph = cell.paragraphs[0]
            add_inline(
                paragraph,
                row[column_index] if column_index < len(row) else "",
            )
            set_cell_border(cell)
            if row_index == 0:
                set_cell_shading(cell, TABLE_HEADER)
            elif row_index % 2 == 0:
                set_cell_shading(cell, "F7FAF9")
            for paragraph in cell.paragraphs:
                paragraph.paragraph_format.space_after = Pt(2)
                paragraph.paragraph_format.line_spacing = 1.05
                for run in paragraph.runs:
                    set_run_font(run, FONT_BODY, 9.0, row_index == 0)
    document.add_paragraph().paragraph_format.space_after = Pt(1)


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_markdown(document: Document, text: str, first_h1: bool = True) -> bool:
    lines = text.splitlines()
    index = 0
    first_h1 = first_h1
    pending_table_caption = None
    pending_page_break = False
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue

        if stripped == "<!-- pagebreak -->":
            pending_page_break = True
            index += 1
            continue

        if stripped.startswith("```"):
            language = stripped[3:].strip()
            index += 1
            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            add_code_block(document, "\n".join(block), language)
            continue

        if stripped.startswith("# "):
            paragraph = document.add_heading("", level=1)
            add_heading_inline(paragraph, stripped[2:].strip(), 20)
            paragraph.paragraph_format.page_break_before = not first_h1
            first_h1 = False
            index += 1
            continue
        if stripped.startswith("## "):
            paragraph = document.add_heading("", level=2)
            add_heading_inline(paragraph, stripped[3:].strip(), 14)
            index += 1
            continue
        if stripped.startswith("### "):
            paragraph = document.add_heading("", level=3)
            add_heading_inline(paragraph, stripped[4:].strip(), 11.5)
            index += 1
            continue

        if re.match(r"^表\s*[0-9A-Z前]+-\d+\s+", stripped):
            pending_table_caption = stripped
            index += 1
            continue

        image_match = re.fullmatch(r"!\[(.+?)\]\((.+?)\)", stripped)
        if image_match:
            alt, relative = image_match.groups()
            image_path = ROOT / relative
            if image_path.exists():
                paragraph = document.add_paragraph()
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.space_before = Pt(6)
                paragraph.paragraph_format.space_after = Pt(3)
                # Exact line spacing on Normal clips inline images to one line.
                paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
                paragraph.paragraph_format.line_spacing = 1.0
                paragraph.paragraph_format.keep_with_next = True
                image_run = paragraph.add_run()
                picture = image_run.add_picture(str(image_path), width=Inches(6.05))
                document_properties = picture._inline.docPr
                document_properties.set("descr", alt)
                document_properties.set("title", alt)
                caption = document.add_paragraph(alt, style="FigureCaption")
                caption.paragraph_format.keep_together = True
            index += 1
            continue

        if stripped.startswith("|") and index + 1 < len(lines):
            separator = lines[index + 1].strip()
            if re.fullmatch(r"\|?[\s:|-]+\|?", separator) and "-" in separator:
                rows = [split_table_row(stripped)]
                index += 2
                while index < len(lines) and lines[index].strip().startswith("|"):
                    rows.append(split_table_row(lines[index]))
                    index += 1
                if pending_table_caption:
                    caption = document.add_paragraph(pending_table_caption, style="TableCaption")
                    caption.paragraph_format.keep_with_next = True
                    if pending_page_break:
                        caption.paragraph_format.page_break_before = True
                        pending_page_break = False
                    pending_table_caption = None
                add_table(document, rows)
                continue

        if stripped.startswith("- "):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.55)
            paragraph.paragraph_format.first_line_indent = Cm(-0.35)
            paragraph.paragraph_format.space_after = Pt(3)
            bullet = paragraph.add_run("· ")
            set_run_font(bullet, FONT_BODY, 10.5)
            add_inline(paragraph, stripped[2:])
            index += 1
            continue

        numbered = re.match(r"^\d+\.\s+(.*)$", stripped)
        if numbered:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.55)
            paragraph.paragraph_format.first_line_indent = Cm(-0.55)
            paragraph.paragraph_format.space_after = Pt(3)
            prefix = stripped[: stripped.index(".") + 1]
            add_inline(paragraph, f"{prefix} {numbered.group(1)}")
            index += 1
            continue

        if stripped.startswith(">"):
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.left_indent = Cm(0.7)
            paragraph.paragraph_format.right_indent = Cm(0.7)
            add_inline(paragraph, stripped.lstrip("> "))
            index += 1
            continue

        if stripped == AFTERWORD_SIGNATURE:
            paragraph = document.add_paragraph()
            paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            paragraph.paragraph_format.space_before = Pt(220)
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.keep_together = True
            add_inline(paragraph, stripped)
            index += 1
            continue

        if stripped == "\\[":
            index += 1
            block = []
            while index < len(lines) and lines[index].strip() != "\\]":
                block.append(lines[index])
                index += 1
            index += 1
            add_equation_block(document, "\n".join(block))
            continue

        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if not candidate:
                break
            if candidate.startswith(("#", "```", "![", "|", "- ", ">", "\\[", "表 ")):
                break
            if re.match(r"^\d+\.\s+", candidate):
                break
            paragraph_lines.append(candidate)
            index += 1
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.first_line_indent = Pt(21)
        add_inline(paragraph, " ".join(paragraph_lines))
    return first_h1


def chapter_files() -> list[tuple[str, str, str, Path]]:
    result = []
    for path in sorted(MANUSCRIPT.glob("part-[0-9][0-9]/*.md")):
        text = path.read_text(encoding="utf-8")
        title_match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        if not title_match:
            raise RuntimeError(f"missing title: {path}")
        chapter_match = re.search(r"第\s*(\d+)\s*章", title_match.group(1))
        chapter_no = int(chapter_match.group(1)) if chapter_match else 999
        result.append((path.parent.name, f"{chapter_no:02d}", title_match.group(1), path))
    return sorted(result, key=lambda item: item[1])


def main() -> None:
    BUILD.mkdir(exist_ok=True)
    document = Document()
    configure_document(document)
    add_cover(document)
    has_frontispiece = add_frontispiece(document)

    about = MANUSCRIPT / "00-about.md"
    if about.exists():
        parse_markdown(
            document,
            about.read_text(encoding="utf-8"),
            first_h1=has_frontispiece,
        )

    preface = MANUSCRIPT / "00-preface.md"
    parse_markdown(document, preface.read_text(encoding="utf-8"), first_h1=False)

    tour = MANUSCRIPT / "00-tour.md"
    tour_title = ""
    tour_text = ""
    if tour.exists():
        tour_text = tour.read_text(encoding="utf-8")
        match = re.search(r"^# (.+)$", tour_text, flags=re.MULTILINE)
        tour_title = match.group(1).strip() if match else "导论"

    chapters = chapter_files()
    page_map_path = ROOT / "tools" / "toc-pages.json"
    page_map = (
        json.loads(page_map_path.read_text(encoding="utf-8"))
        if page_map_path.exists()
        else {}
    )
    appendix_entries = []
    for path in sorted((MANUSCRIPT / "appendices").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        if match:
            appendix_entries.append(("appendices", match.group(1), ""))
    afterword = MANUSCRIPT / "99-afterword.md"
    afterword_title = ""
    if afterword.exists():
        match = re.search(r"^# (.+)$", afterword.read_text(encoding="utf-8"), flags=re.MULTILINE)
        afterword_title = match.group(1).strip() if match else "后记"
    front_entries = [("front", tour_title, "")] if tour_title else []
    back_entries = [("back", afterword_title, "")] if afterword_title else []
    add_contents(
        document,
        front_entries
        + [(part, title, "") for part, _, title, _ in chapters]
        + appendix_entries
        + back_entries,
        page_map,
    )

    if tour_text:
        parse_markdown(document, tour_text, first_h1=False)

    current_part = ""
    for part, _, _, path in chapters:
        if part != current_part:
            add_part_page(document, part)
            current_part = part
        parse_markdown(document, path.read_text(encoding="utf-8"), first_h1=False)

    part = document.add_paragraph()
    part.paragraph_format.page_break_before = True
    part.paragraph_format.space_before = Cm(4.2)
    run = part.add_run("附录")
    set_run_font(run, FONT_BODY, 24, True)
    part_note = document.add_paragraph()
    part_note.paragraph_format.space_after = Pt(24)
    run = part_note.add_run(
        "符号、公式、数据字典、接口映射、实验环境、源码路线、出版检查与练习思路。"
    )
    set_run_font(run, FONT_BODY, 11)
    run.font.color.rgb = RGBColor.from_string(MUTED)
    for path in sorted((MANUSCRIPT / "appendices").glob("*.md")):
        parse_markdown(document, path.read_text(encoding="utf-8"), first_h1=False)

    if afterword.exists():
        parse_markdown(document, afterword.read_text(encoding="utf-8"), first_h1=False)

    document.save(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    main()

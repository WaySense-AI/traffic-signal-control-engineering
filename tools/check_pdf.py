#!/usr/bin/env python3
"""Validate a rendered book PDF before it is accepted as a deliverable.

The checks exist because LibreOffice fails silently in two ways that both
change the book: a missing font configuration substitutes other fonts (the
354-page book collapses to ~261 pages), and a wrong filter drops PDF tagging.
Either one invalidates the table-of-contents page numbers, so the render must
fail loudly instead of producing a plausible-looking file.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "tools" / "book-meta.json"

BODY_FONT = "NotoSansSC"


def run(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, encoding="utf-8", errors="replace")


def check(pdf: Path, expect_pages: int | None) -> list[str]:
    problems: list[str] = []
    if not pdf.exists() or pdf.stat().st_size == 0:
        return [f"missing or empty PDF: {pdf}"]

    with open(pdf, "rb") as handle:
        if handle.read(5) != b"%PDF-":
            problems.append("file does not start with %PDF-")

    info = run(["pdfinfo", str(pdf)])
    pages = int(re.search(r"^Pages:\s+(\d+)", info, re.M).group(1))
    tagged = re.search(r"^Tagged:\s+(\w+)", info, re.M)
    size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+)", info, re.M)

    if tagged is None or tagged.group(1) != "yes":
        problems.append("PDF is not tagged (title/structure navigation is lost)")
    if size is None or not (
        abs(float(size.group(1)) - 595.3) < 1 and abs(float(size.group(2)) - 841.9) < 1
    ):
        problems.append(f"page size is not A4: {size.group(0) if size else 'unknown'}")

    if expect_pages is not None and pages != expect_pages:
        problems.append(
            f"page count is {pages}, expected {expect_pages}; "
            "fonts or layout changed, so the table of contents is stale"
        )

    fonts = run(["pdffonts", str(pdf)])
    rows = []
    pattern = re.compile(
        r"^(\S+)\s+(.+?)\s+(\S+)\s+(yes|no|Builtin)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+$"
    )
    for line in fonts.splitlines()[2:]:
        match = pattern.match(line.strip())
        if match:
            rows.append((match.group(1), match.group(4)))
    names = [name for name, _ in rows]
    if not any(BODY_FONT.lower() in name.lower() for name in names):
        problems.append(
            f"body font {BODY_FONT} is missing; LibreOffice substituted fonts"
        )
    unembedded = [name for name, emb in rows if emb != "yes"]
    if unembedded:
        problems.append("fonts not embedded: " + ", ".join(unembedded))

    print(f"pages: {pages}")
    print(f"tagged: {'yes' if tagged and tagged.group(1) == 'yes' else 'no'}")
    print(f"fonts: {len(rows)} embedded subsets")
    print(f"body font: {'present' if any(BODY_FONT.lower() in n.lower() for n in names) else 'MISSING'}")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument(
        "--expect-pages",
        type=int,
        default=None,
        help="expected page count; defaults to tools/book-meta.json",
    )
    args = parser.parse_args()

    expect = args.expect_pages
    if expect is None and META.exists():
        expect = json.loads(META.read_text(encoding="utf-8")).get("pages")

    problems = check(Path(args.pdf), expect)
    if problems:
        print("\nPDF CHECK FAILED:", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        return 2
    print("PDF check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

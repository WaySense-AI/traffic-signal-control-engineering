#!/usr/bin/env python3
"""Extract chapter start pages from a rendered PDF for the static TOC."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = ROOT / "manuscript"


def chapter_titles() -> list[str]:
    titles = []
    tour = MANUSCRIPT / "00-tour.md"
    if tour.exists():
        match = re.search(r"^# (.+)$", tour.read_text(encoding="utf-8"), re.MULTILINE)
        if match:
            titles.append(match.group(1).strip())
    for path in sorted(MANUSCRIPT.glob("part-[0-9][0-9]/*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        if match:
            titles.append(match.group(1).strip())
    for path in sorted((MANUSCRIPT / "appendices").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = re.search(r"^# (.+)$", text, flags=re.MULTILINE)
        if match:
            titles.append(match.group(1).strip())
    afterword = MANUSCRIPT / "99-afterword.md"
    if afterword.exists():
        match = re.search(r"^# (.+)$", afterword.read_text(encoding="utf-8"), flags=re.MULTILINE)
        if match:
            titles.append(match.group(1).strip())
    return titles


def normalize(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf")
    parser.add_argument("--out", default=str(ROOT / "tools" / "toc-pages.json"))
    args = parser.parse_args()

    text = subprocess.check_output(
        ["pdftotext", "-layout", args.pdf, "-"],
        text=True,
        encoding="utf-8",
    )
    pages = text.split("\f")
    titles = chapter_titles()

    toc_start: int | None = None
    for index, page in enumerate(pages):
        normalized_lines = [normalize(line) for line in page.splitlines()]
        if "目录" in normalized_lines:
            toc_start = index
            break
    if toc_start is None:
        raise SystemExit("cannot find table of contents")

    page_map: dict[str, int] = {}
    # The table of contents uses dot leaders; skip every page that still looks
    # like a TOC page so TOC entries cannot be mistaken for chapter starts.
    toc_end = toc_start
    for index in range(toc_start, len(pages)):
        if pages[index].count("......") >= 5:
            toc_end = index
        else:
            break
    search_start = toc_end + 1
    for title in titles:
        for index in range(search_start, len(pages)):
            if pages[index].count("......") >= 5:
                continue  # still a table-of-contents page
            normalized_lines = [normalize(line) for line in pages[index].splitlines()]
            if title in normalized_lines:
                page_map[title] = index + 1
                break
            # LibreOffice can wrap a long chapter title onto a second line.
            # Restrict fuzzy matching to the page-heading area so later
            # cross-references in body text cannot be mistaken for the start.
            heading_area = re.sub(
                r"\s+",
                "",
                " ".join(
                    line
                    for line in normalized_lines[:8]
                    if line
                ),
            )
            if re.sub(r"\s+", "", title) in heading_area:
                page_map[title] = index + 1
                break

    missing = [title for title in titles if title not in page_map]
    if missing:
        raise SystemExit("missing chapter pages: " + ", ".join(missing))

    output = Path(args.out)
    output.write_text(
        json.dumps(page_map, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(output)


if __name__ == "__main__":
    main()

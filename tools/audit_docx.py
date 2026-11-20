#!/usr/bin/env python3
"""Audit the built DOCX for accessibility and structural defects."""

from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn


ROOT = Path(__file__).resolve().parents[1]
META = ROOT / "tools" / "book-meta.json"


def current_version() -> str:
    """Version string from book-meta.json, so the default paths never drift."""
    try:
        return json.loads(META.read_text(encoding="utf-8")).get("version", "")
    except (OSError, ValueError):
        return ""


def audit(path: Path) -> dict:
    findings: list[dict[str, str]] = []
    document = Document(path)

    images = list(document.inline_shapes)
    for index, shape in enumerate(images, 1):
        properties = shape._inline.docPr
        description = (properties.get("descr") or "").strip()
        title = (properties.get("title") or "").strip()
        if not description and title == "部分题图（装饰）":
            # Decorative part-opener art is intentional: empty alt, no caption,
            # and no figure number. Do not count it as a missing-alt failure.
            continue
        if not description:
            findings.append(
                {
                    "severity": "high",
                    "target": f"image {index}",
                    "message": "image lacks alternative text",
                }
            )

    for index, table in enumerate(document.tables, 1):
        header = table.rows[0]._tr.find(f".//{qn('w:tblHeader')}")
        if header is None:
            findings.append(
                {
                    "severity": "medium",
                    "target": f"table {index}",
                    "message": "table header row is not marked as repeating",
                }
            )

    levels = [
        int(paragraph.style.name.split()[-1])
        for paragraph in document.paragraphs
        if paragraph.style.name.startswith("Heading")
        and paragraph.style.name.split()[-1].isdigit()
    ]
    for previous, current in zip(levels, levels[1:]):
        if current > previous + 1:
            findings.append(
                {
                    "severity": "medium",
                    "target": "heading outline",
                    "message": f"heading level jumps from H{previous} to H{current}",
                }
            )

    if not any(level == 1 for level in levels):
        findings.append(
            {
                "severity": "high",
                "target": "heading outline",
                "message": "document has no level-1 headings",
            }
        )

    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
        if broken:
            findings.append(
                {
                    "severity": "high",
                    "target": broken,
                    "message": "corrupt ZIP member",
                }
            )
        if "word/media" not in "".join(archive.namelist()):
            findings.append(
                {
                    "severity": "low",
                    "target": "package",
                    "message": "document has no embedded media",
                }
            )

    counts = {"high": 0, "medium": 0, "low": 0}
    for finding in findings:
        counts[finding["severity"]] += 1

    try:
        display_path = str(path.relative_to(ROOT))
    except ValueError:
        display_path = str(path)
    return {
        "file": display_path,
        "images": len(images),
        "tables": len(document.tables),
        "headings": len(levels),
        "counts": counts,
        "findings": findings,
    }


def main() -> int:
    version = current_version()
    suffix = f"_{version}" if version else ""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "docx",
        nargs="?",
        default=str(ROOT / "build" / f"交通信号控制工程{suffix}.docx"),
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "build" / f"a11y-report-{version or 'v3'}.json"),
    )
    args = parser.parse_args()

    report = audit(Path(args.docx).resolve())
    output = Path(args.out)
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["counts"], ensure_ascii=False))
    for finding in report["findings"]:
        print(
            f"- {finding['severity']}: {finding['message']} ({finding['target']})"
        )
    return 0 if report["counts"]["high"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

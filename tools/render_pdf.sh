#!/usr/bin/env bash
# Render the book DOCX to a checked, tagged A4 PDF without CodeX runtimes.
#
# Usage:
#   tools/render_pdf.sh <input.docx> <output.pdf> [--expect-pages N]
#
# Renderer resolution order: $BOOK_SOFFICE, /Applications/LibreOffice.app,
# then `soffice` on PATH. The repo ships tools/fonts.conf because a LibreOffice
# process that cannot see the macOS fonts substitutes them and silently changes
# pagination; tools/check_pdf.py then fails the render instead of shipping it.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -lt 2 ]]; then
  echo "usage: $0 <input.docx> <output.pdf> [--expect-pages N]" >&2
  exit 64
fi

INPUT="$1"
OUTPUT="$2"
shift 2
EXPECT_ARGS=("$@")

if [[ ! -f "$INPUT" ]]; then
  echo "input not found: $INPUT" >&2
  exit 66
fi

if [[ -n "${BOOK_SOFFICE:-}" ]]; then
  SOFFICE="$BOOK_SOFFICE"
elif [[ -x /Applications/LibreOffice.app/Contents/MacOS/soffice ]]; then
  SOFFICE=/Applications/LibreOffice.app/Contents/MacOS/soffice
else
  SOFFICE="$(command -v soffice || true)"
fi

if [[ -z "${SOFFICE:-}" || ! -x "$SOFFICE" ]]; then
  echo "LibreOffice not found. Install it or set BOOK_SOFFICE." >&2
  exit 69
fi

if [[ ! -f "$ROOT/tools/fonts.conf" ]]; then
  echo "missing tools/fonts.conf; refusing to render with substituted fonts" >&2
  exit 78
fi

OUTPUT_DIR="$(cd "$(dirname "$OUTPUT")" && pwd)"
mkdir -p "$OUTPUT_DIR"
PROFILE="$(mktemp -d /tmp/signal-book-lo.XXXXXX)"
trap 'rm -rf -- "$PROFILE"' EXIT

# The filter data has to be one argument; it enables structure tagging, which
# plain `--convert-to pdf` does not produce on every LibreOffice build.
FILTER='pdf:writer_pdf_Export:{"UseTaggedPDF":{"type":"boolean","value":"true"}}'

FONTCONFIG_FILE="${FONTCONFIG_FILE:-$ROOT/tools/fonts.conf}" \
FONTCONFIG_PATH="${FONTCONFIG_PATH:-$ROOT/tools}" \
  "$SOFFICE" \
    "-env:UserInstallation=file://$PROFILE" \
    --invisible --headless --norestore \
    --convert-to "$FILTER" \
    --outdir "$OUTPUT_DIR" \
    "$INPUT" >/dev/null

RENDERED="$OUTPUT_DIR/$(basename "${INPUT%.*}").pdf"
if [[ "$RENDERED" != "$OUTPUT" ]]; then
  mv -f "$RENDERED" "$OUTPUT"
fi

if [[ ${#EXPECT_ARGS[@]} -gt 0 ]]; then
  python3 "$ROOT/tools/check_pdf.py" "$OUTPUT" "${EXPECT_ARGS[@]}"
else
  python3 "$ROOT/tools/check_pdf.py" "$OUTPUT"
fi
echo "rendered: $OUTPUT"

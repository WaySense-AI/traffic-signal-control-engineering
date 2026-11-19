#!/usr/bin/env bash
# Download the open-source fonts used by the book build.
# License: Noto fonts are SIL Open Font License 1.1.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/tools/fonts"
mkdir -p "$OUT"

BASE="https://raw.githubusercontent.com/notofonts/noto-cjk/main/Sans"
fetch() {
  local url="$1" name="$2"
  if [[ -f "$OUT/$name" ]]; then
    echo "exists: $name"
    return
  fi
  echo "fetch: $name"
  curl -L --fail --max-time 300 -o "$OUT/$name" "$url"
}

fetch "$BASE/SubsetOTF/SC/NotoSansSC-Regular.otf" "NotoSansSC-Regular.otf"
fetch "$BASE/SubsetOTF/SC/NotoSansSC-Bold.otf" "NotoSansSC-Bold.otf"
fetch "$BASE/Mono/NotoSansMonoCJKsc-Regular.otf" "NotoSansMonoCJKsc-Regular.otf"
fetch "$BASE/Mono/NotoSansMonoCJKsc-Bold.otf" "NotoSansMonoCJKsc-Bold.otf"

echo
echo "Fonts are in: $OUT"
echo "macOS:  cp \"$OUT\"/*.otf ~/Library/Fonts/"
echo "Linux:  sudo cp \"$OUT\"/*.otf /usr/share/fonts/opentype/noto/ && sudo fc-cache -f"

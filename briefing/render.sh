#!/usr/bin/env bash
# Render briefing JSON to PDF with whichever Python has reportlab (installs it if none does).
# Usage: briefing/render.sh briefing.json OUT.pdf
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
PY=""
for p in python3 /usr/local/bin/python3 python3.13 python3.12 python3.11; do
  if command -v "$p" >/dev/null 2>&1 && "$p" -c 'import reportlab' 2>/dev/null; then PY="$p"; break; fi
done
if [ -z "$PY" ]; then
  python3 -m pip install -q reportlab 2>/dev/null || python3 -m pip install -q --break-system-packages reportlab
  PY=python3
fi
exec "$PY" "$HERE/build_pdf.py" "$1" "$2"

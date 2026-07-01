#!/usr/bin/env bash
# Gruen/Rot-Gate fuer das Projekt.
# Stufe 1: deterministische stdlib-Tests, KEIN Netz.
# Stufe 2: extract_facts-Tests via uv+Pillow (deterministisch; nur der allererste
#          uv-Lauf laedt Pillow einmalig in den uv-Cache).
set -euo pipefail
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -p 'test_*.py' -v
if command -v uv >/dev/null 2>&1; then
  uv run --with pillow python3 -W error::DeprecationWarning -m unittest tests.test_extract_facts -v
else
  echo "FEHLT: uv — extract_facts-Tests nicht ausgefuehrt, Gate unvollstaendig." >&2
  echo "Install: brew install uv" >&2
  exit 1
fi

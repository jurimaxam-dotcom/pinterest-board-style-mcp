#!/usr/bin/env bash
# Gruen/Rot-Gate fuer das Projekt: deterministische stdlib-Tests, KEIN Netz.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m unittest discover -s tests -p 'test_*.py' -v

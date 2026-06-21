#!/usr/bin/env python3
"""validate_tokens.py — minimaler DTCG-/Schema-Check fuer board-style tokens.json (stdlib only).

Kein jsonschema-Dependency (zero-install-Prinzip v1): prueft die fuer uns wichtigen
Invarianten strukturell. Exit 0 = ok, Exit 1 = invalid (alle Probleme gelistet).

    python3 scripts/validate_tokens.py examples/<slug>.tokens.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
DIM = re.compile(r"^[0-9.]+(px|rem)$")
ROLES = ["background", "surface", "text", "primary", "accent", "muted"]
ENUMS = {
    "temperature": {"warm", "cool", "neutral"},
    "saturation": {"muted", "balanced", "vibrant"},
    "contrast": {"low", "medium", "high"},
    "density": {"airy", "balanced", "dense"},
}


def _color_token(t, errs, where):
    if not isinstance(t, dict) or "$value" not in t:
        errs.append(f"{where}: kein Token-Objekt mit $value")
        return
    if not (isinstance(t["$value"], str) and HEX.match(t["$value"])):
        errs.append(f"{where}.$value ist kein Hex (#rrggbb[aa]): {t.get('$value')!r}")


def validate(doc) -> list[str]:
    errs: list[str] = []

    color = doc.get("color")
    if not isinstance(color, dict):
        errs.append("Top-Level 'color' fehlt oder ist kein Objekt")
    else:
        for r in ROLES:
            if r not in color:
                errs.append(f"color.{r} fehlt")
            else:
                _color_token(color[r], errs, f"color.{r}")
        pal = color.get("palette")
        keys = [k for k in pal if not k.startswith("$")] if isinstance(pal, dict) else []
        if not isinstance(pal, dict) or len(keys) < 3:
            errs.append("color.palette braucht >=3 Eintraege")
        else:
            for k in keys:
                _color_token(pal[k], errs, f"color.palette.{k}")

    rad = doc.get("radius")
    if isinstance(rad, dict) and "base" in rad:
        b = rad["base"]
        val = b.get("$value") if isinstance(b, dict) else b
        if not (isinstance(val, str) and DIM.match(val)):
            errs.append(f"radius.base.$value ist keine Dimension (px/rem): {val!r}")

    bs = (doc.get("$extensions") or {}).get("boardStyle")
    if not isinstance(bs, dict):
        errs.append("$extensions.boardStyle fehlt")
    else:
        if not (isinstance(bs.get("mood"), list) and len(bs["mood"]) >= 2):
            errs.append("boardStyle.mood braucht >=2 Adjektive")
        for f, allowed in ENUMS.items():
            if bs.get(f) not in allowed:
                errs.append(f"boardStyle.{f}={bs.get(f)!r} nicht in {sorted(allowed)}")
        conf = bs.get("confidence")
        if not isinstance(conf, dict):
            errs.append("boardStyle.confidence fehlt")
        else:
            for k in ("color", "typography", "overall"):
                v = conf.get(k)
                if not (isinstance(v, (int, float)) and 0 <= v <= 1):
                    errs.append(f"boardStyle.confidence.{k}={v!r} nicht in [0,1]")
        outl = bs.get("outliers")
        if not isinstance(outl, list):
            errs.append("boardStyle.outliers muss eine Liste sein (ggf. leer)")
        else:
            for i, o in enumerate(outl):
                if not (isinstance(o, dict) and "image" in o and "why" in o):
                    errs.append(f"boardStyle.outliers[{i}] braucht image+why")
        typo = bs.get("typography")
        if not (isinstance(typo, dict) and "classification" in typo):
            errs.append("boardStyle.typography{classification,...} fehlt")
    return errs


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if not args:
        print("usage: validate_tokens.py <tokens.json>", file=sys.stderr)
        return 2
    p = Path(args[0])
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — bewusst breit: jeder Lade-/Parse-Fehler ist invalid
        print(f"FEHLER: {p} nicht lesbar / kein JSON: {e}", file=sys.stderr)
        return 2
    errs = validate(doc)
    if errs:
        print(f"INVALID ({len(errs)} Problem(e)) in {p}:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print(f"OK — {p} ist ein valides board-style DTCG-Dokument.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

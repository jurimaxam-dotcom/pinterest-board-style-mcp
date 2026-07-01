#!/usr/bin/env python3
"""validate_tokens.py — minimaler DTCG-/Schema-Check fuer board-style tokens.json (stdlib only).

Kein jsonschema-Dependency (zero-install-Prinzip v1): prueft die fuer uns wichtigen
Invarianten strukturell. Exit 0 = ok, Exit 1 = invalid (alle Probleme gelistet).

    python3 scripts/validate_tokens.py examples/<slug>.tokens.json

Mit --facts wird zusaetzlich das ΔE-Gate geprueft: jede Vision-Farbe (Rollen, palette,
accentPalette) muss nahe an der GEMESSENEN Palette aus facts.json liegen (extract_facts.py),
und temperature muss zur Messung passen. Das macht Farb-Halluzination zu einem roten Gate:

    python3 scripts/validate_tokens.py examples/<slug>.tokens.json --facts .cache/<slug>/facts.json
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

MAX_DELTA_E = 30.0  # CIE76: < ~2 unsichtbar, ~10 gleiche Farbfamilie, > 30 andere Farbe

HEX = re.compile(r"^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")
DIM = re.compile(r"^[0-9.]+(px|rem)$")
ROLES = ["background", "surface", "text", "primary", "accent", "muted"]
ENUMS = {
    "temperature": {"warm", "cool", "neutral"},
    "saturation": {"muted", "balanced", "vibrant"},
    "contrast": {"low", "medium", "high"},
    "density": {"airy", "balanced", "dense"},
}
# Stufe-1-Erweiterung: additive, OPTIONALE Felder (nur validiert, wenn vorhanden).
UI_ROLES = {"background", "decoration", "component-shape"}
IMAGE_ROLES = {"hero-bg", "bleed-band", "focal", "texture", "wall", "atmosphere"}
FONT_ROLES = {"heading", "body"}


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
        _validate_rich_fields(bs, errs)
    return errs


def _validate_rich_fields(bs: dict, errs: list[str]) -> None:
    """Additive Stufe-1-Felder: nur pruefen, wenn vorhanden (fehlend ist erlaubt)."""
    acc = bs.get("accentPalette")
    if acc is not None:
        if not isinstance(acc, list):
            errs.append("boardStyle.accentPalette muss eine Liste sein")
        else:
            for i, a in enumerate(acc):
                _color_token(a, errs, f"boardStyle.accentPalette[{i}]")

    wf = bs.get("webfonts")
    if wf is not None:
        if not isinstance(wf, list):
            errs.append("boardStyle.webfonts muss eine Liste sein")
        else:
            for i, w in enumerate(wf):
                if not isinstance(w, dict) or w.get("role") not in FONT_ROLES:
                    errs.append(f"boardStyle.webfonts[{i}].role nicht in {sorted(FONT_ROLES)}")
                elif not isinstance(w.get("stack") or w.get("family"), str):
                    errs.append(f"boardStyle.webfonts[{i}] braucht stack/family (string)")

    mo = bs.get("motifs")
    if mo is not None:
        if not isinstance(mo, list):
            errs.append("boardStyle.motifs muss eine Liste sein")
        else:
            for i, m in enumerate(mo):
                if not (isinstance(m, dict) and "name" in m and m.get("uiRole") in UI_ROLES):
                    errs.append(f"boardStyle.motifs[{i}] braucht name + uiRole in {sorted(UI_ROLES)}")

    ir = bs.get("imageRoles")
    if ir is not None:
        if not isinstance(ir, dict):
            errs.append("boardStyle.imageRoles muss ein Objekt sein")
        else:
            for k, roles in ir.items():
                if not isinstance(roles, list) or any(r not in IMAGE_ROLES for r in roles):
                    errs.append(f"boardStyle.imageRoles[{k}] hat unbekannte Rolle (erlaubt: {sorted(IMAGE_ROLES)})")

    ec = bs.get("edgeColors")
    if ec is not None:
        if not isinstance(ec, dict):
            errs.append("boardStyle.edgeColors muss ein Objekt sein")
        else:
            for k, v in ec.items():
                if not isinstance(v, dict):
                    errs.append(f"boardStyle.edgeColors[{k}] muss {{top,bottom}} sein")
                    continue
                for pos in ("top", "bottom"):
                    val = v.get(pos)
                    if not (isinstance(val, str) and HEX.match(val)):
                        errs.append(f"boardStyle.edgeColors[{k}].{pos} ist kein Hex: {val!r}")


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")[:6]  # #rrggbbaa: Alpha fuer den Farbvergleich ignorieren
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _srgb_to_lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    def linearize(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (linearize(v) for v in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t: float) -> float:
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116

    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(hex_a: str, hex_b: str) -> float:
    """CIE76-Farbabstand zweier Hex-Farben (0 = identisch, ~100 = schwarz/weiss)."""
    lab_a, lab_b = _srgb_to_lab(_hex_to_rgb(hex_a)), _srgb_to_lab(_hex_to_rgb(hex_b))
    return math.sqrt(sum((a - b) ** 2 for a, b in zip(lab_a, lab_b)))


def _claimed_colors(doc) -> list[tuple[str, str]]:
    claimed = []
    color = doc.get("color") or {}
    for role in ROLES:
        tok = color.get(role)
        if isinstance(tok, dict) and isinstance(tok.get("$value"), str) and HEX.match(tok["$value"]):
            claimed.append((f"color.{role}", tok["$value"]))
    pal = color.get("palette")
    if isinstance(pal, dict):
        for k, tok in pal.items():
            if not k.startswith("$") and isinstance(tok, dict) \
                    and isinstance(tok.get("$value"), str) and HEX.match(tok["$value"]):
                claimed.append((f"color.palette.{k}", tok["$value"]))
    acc = ((doc.get("$extensions") or {}).get("boardStyle") or {}).get("accentPalette")
    if isinstance(acc, list):
        for i, tok in enumerate(acc):
            if isinstance(tok, dict) and isinstance(tok.get("$value"), str) and HEX.match(tok["$value"]):
                claimed.append((f"boardStyle.accentPalette[{i}]", tok["$value"]))
    return claimed


def validate_against_facts(doc, facts, max_delta_e: float = MAX_DELTA_E) -> list[str]:
    """ΔE-Gate: Vision-Farben muessen nahe an der gemessenen Palette/edgeColors liegen."""
    errs: list[str] = []
    anchors = [p["hex"] for p in facts.get("palette", []) if isinstance(p, dict) and p.get("hex")]
    for edges in (facts.get("edgeColors") or {}).values():
        if isinstance(edges, dict):
            anchors.extend(v for v in (edges.get("top"), edges.get("bottom")) if v)
    if not anchors:
        return ["facts: keine gemessene Palette/edgeColors — ΔE-Gate nicht pruefbar"]

    for where, hex_value in _claimed_colors(doc):
        nearest = min(anchors, key=lambda a: delta_e(hex_value, a))
        distance = delta_e(hex_value, nearest)
        if distance > max_delta_e:
            errs.append(
                f"{where}={hex_value} ist ΔE {distance:.0f} von der gemessenen Palette entfernt "
                f"(naechster Anker {nearest}, erlaubt <= {max_delta_e:.0f}) — halluzinierte Farbe?"
            )

    measured_temp = (facts.get("metrics") or {}).get("temperature")
    claimed_temp = ((doc.get("$extensions") or {}).get("boardStyle") or {}).get("temperature")
    if measured_temp and claimed_temp and measured_temp != claimed_temp:
        errs.append(
            f"boardStyle.temperature={claimed_temp!r} widerspricht der Messung ({measured_temp!r})"
        )
    return errs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="board-style tokens.json validieren (Struktur + optionales ΔE-Gate)")
    ap.add_argument("tokens", help="Pfad zur tokens.json")
    ap.add_argument("--facts", help="facts.json aus extract_facts.py -> ΔE-Gate gegen gemessene Farben")
    ap.add_argument("--max-delta-e", type=float, default=MAX_DELTA_E,
                    help=f"ΔE-Toleranz fuer das Fakten-Gate (Default {MAX_DELTA_E:.0f})")
    args = ap.parse_args(argv)

    p = Path(args.tokens)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — bewusst breit: jeder Lade-/Parse-Fehler ist invalid
        print(f"FEHLER: {p} nicht lesbar / kein JSON: {e}", file=sys.stderr)
        return 2
    errs = validate(doc)
    if args.facts:
        try:
            facts = json.loads(Path(args.facts).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            print(f"FEHLER: {args.facts} nicht lesbar / kein JSON: {e}", file=sys.stderr)
            return 2
        errs += validate_against_facts(doc, facts, max_delta_e=args.max_delta_e)
    if errs:
        print(f"INVALID ({len(errs)} Problem(e)) in {p}:", file=sys.stderr)
        for e in errs:
            print(f"  - {e}", file=sys.stderr)
        return 1
    suffix = " (inkl. ΔE-Gate gegen gemessene Fakten)" if args.facts else ""
    print(f"OK — {p} ist ein valides board-style DTCG-Dokument{suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

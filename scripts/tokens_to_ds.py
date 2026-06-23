#!/usr/bin/env python3
r"""tokens_to_ds.py — DTCG board-style tokens -> Claude-Design-Design-System (stdlib only).

Deterministischer Emitter (KEIN Vision/LLM, KEIN Netz, KEIN Timestamp -> byte-stabil
fuer das Test-Gate). Liest das von der board-style-extractor-Skill erzeugte
`<slug>.tokens.json` (+ optional den `<slug>.style.md`-Brief) und schreibt einen
importierbaren Claude-Design-Design-System-Ordner:

    <out>/
    |- styles.css         # nur @import-Zeilen (Compiler-Einstieg)
    |- tokens/
    |   |- colors.css     # :root { --color-*: <hex>; }
    |   \- radius.css      # :root { --radius-base: <dim>; }  (nur falls radius vorhanden)
    |- readme.md          # Manifest: CONTENT + VISUAL FOUNDATIONS (Werte + Direktiven)
    \- SKILL.md           # name: <slug>-design, user-invocable: true

Trennung gewahrt: Die Vision-Analyse bleibt unangetastet; dies ist reine
JSON(+Brief)->CSS/MD-Transformation gegen den stabilen tokens.json-Vertrag.

    python3 scripts/tokens_to_ds.py examples/<slug>.tokens.json [--style PFAD] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

ROLES = ["background", "surface", "text", "primary", "accent", "muted"]


# ----------------------------------------------------------------------------- helpers

def _clean_comment(text: str) -> str:
    """Macht einen String als CSS-Kommentar-Inhalt sicher (kein vorzeitiges `*/`)."""
    return text.replace("*/", "* /").strip()


def _title_and_vibe(style_md: str) -> tuple[str | None, str | None]:
    """Aus dem style.md: H1-Titel (ohne fuehrendes 'Style:') + Vibe-Absatz (H1 bis erstes H2)."""
    title = None
    vibe_lines: list[str] = []
    seen_h1 = False
    for line in style_md.splitlines():
        if line.startswith("# "):
            title = re.sub(r"^style:\s*", "", line[2:].strip(), flags=re.IGNORECASE)
            seen_h1 = True
            continue
        if line.startswith("## "):
            break
        if seen_h1:
            vibe_lines.append(line)
    vibe = "\n".join(vibe_lines).strip() or None
    return title, vibe


def _section(style_md: str, needle: str) -> str | None:
    """Inhalt des ersten ## -Abschnitts, dessen Ueberschrift `needle` enthaelt (bis naechstes H2)."""
    out: list[str] = []
    capturing = False
    for line in style_md.splitlines():
        if line.startswith("## "):
            if capturing:
                break
            capturing = needle.lower() in line[3:].lower()
            continue
        if capturing:
            out.append(line)
    body = "\n".join(out).strip()
    return body or None


def _palette_items(palette: dict) -> list[tuple[str, dict]]:
    """Palette-Eintraege numerisch sortiert ('0','1',...,'10'); $-Keys raus."""
    keys = [k for k in palette if not k.startswith("$")]
    keys.sort(key=lambda k: int(k) if k.isdigit() else 1_000_000)
    return [(k, palette[k]) for k in keys]


# ----------------------------------------------------------------------------- emitters

def emit_colors_css(color: dict, slug: str) -> str:
    lines = [
        f'/* Farben - abgeleitet aus Pinterest-Board "{slug}". Auto-generiert, nicht von Hand editieren. */',
        ":root {",
        "  /* Semantische Rollen */",
    ]
    for role in ROLES:
        tok = color.get(role)
        if not isinstance(tok, dict) or "$value" not in tok:
            continue
        desc = tok.get("$description", "")
        suffix = f"  /* {_clean_comment(desc)} */" if desc else ""
        lines.append(f"  --color-{role}: {tok['$value']};{suffix}")

    palette = color.get("palette")
    if isinstance(palette, dict):
        lines.append("")
        lines.append("  /* Palette nach Dominanz */")
        for key, tok in _palette_items(palette):
            if not isinstance(tok, dict) or "$value" not in tok:
                continue
            desc = tok.get("$description", "")
            suffix = f"  /* {_clean_comment(desc)} */" if desc else ""
            lines.append(f"  --color-palette-{key}: {tok['$value']};{suffix}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def emit_radius_css(radius: dict) -> str | None:
    base = radius.get("base") if isinstance(radius, dict) else None
    if not isinstance(base, dict) or "$value" not in base:
        return None
    desc = base.get("$description", "")
    suffix = f"  /* {_clean_comment(desc)} */" if desc else ""
    return (
        "/* Radius - inferiert aus dem Board. Auto-generiert. */\n"
        ":root {\n"
        f"  --radius-base: {base['$value']};{suffix}\n"
        "}\n"
    )


def emit_styles_css(title: str, imports: list[str]) -> str:
    head = f'/* "{title}" - Design System (auto-generiert aus einem Pinterest-Board).\n' \
           "   Compiler-Einstieg: ausschliesslich @import-Zeilen. */\n"
    body = "\n".join(f'@import "{rel}";' for rel in imports)
    return head + body + "\n"


def emit_skill(slug: str, title: str) -> str:
    desc = (
        f'Use this skill to generate well-branded interfaces and assets in the "{title}" '
        "style (derived from a Pinterest moodboard). Contains color tokens, radius and "
        "visual/content guidelines as a foundations design system."
    )
    return (
        "---\n"
        f"name: {slug}-design\n"
        f"description: {desc}\n"
        "user-invocable: true\n"
        "---\n\n"
        "Read the `readme.md` in this skill and explore the token files under `tokens/`.\n\n"
        "When creating visual artifacts (mocks, prototypes, slides) or production code, use the "
        "CSS custom properties from `styles.css` (`--color-*`, `--radius-base`) and follow the "
        "Do/Don't directives in the readme. Pull colours from these tokens instead of inventing new ones.\n\n"
        "This is a **foundations** design system (colours + radius + style guidance) distilled from a "
        "moodboard: it ships **no** prebuilt components and **no** font files. Treat typography as "
        "*guidance* (classification only), never as bundled fonts.\n\n"
        "If invoked without further guidance, ask what the user wants to build, then act as an expert "
        "designer working in this palette and vibe.\n"
    )


def emit_readme(doc: dict, slug: str, title: str, vibe: str | None,
                directives: str | None, outliers_md: str | None,
                image_names: list[str] | None = None) -> str:
    color = doc.get("color", {})
    bs = (doc.get("$extensions") or {}).get("boardStyle", {})
    typo = bs.get("typography", {}) if isinstance(bs.get("typography"), dict) else {}
    conf = bs.get("confidence", {}) if isinstance(bs.get("confidence"), dict) else {}
    src = bs.get("source", {}) if isinstance(bs.get("source"), dict) else {}

    out: list[str] = [f"# {title} - Design System", ""]
    out.append("> Auto-generiert aus einem Pinterest-Board (Foundations-only: Farben, Radius, "
               "Stil-Guidance). Keine Komponenten, keine Font-Dateien.")
    out.append("> Import in Claude Design: Share-Menue -> File type **Design System** setzen.")
    out.append("")
    if vibe:
        out += ["## Vibe", "", vibe, ""]

    # CONTENT FUNDAMENTALS
    out += ["## Content Fundamentals", ""]
    if bs.get("mood"):
        out.append(f"- **Mood:** {', '.join(bs['mood'])}")
    if bs.get("era"):
        out.append(f"- **Era:** {bs['era']}")
    if typo:
        bits = [f"{k}: {typo[k]}" for k in ("classification", "weight", "case", "formality") if typo.get(k)]
        ct = conf.get("typography")
        suffix = f" _(inferiert, confidence {ct})_" if ct is not None else " _(inferiert)_"
        out.append(f"- **Typografie:** {', '.join(bits)}{suffix} - nur Klassifikation, keine Font-Dateien.")
    out.append("")

    # VISUAL FOUNDATIONS
    out += ["## Visual Foundations", "", "### Farben", "",
            "| Token | Hex | Rolle | Notiz |", "|---|---|---|---|"]
    for role in ROLES:
        tok = color.get(role)
        if isinstance(tok, dict) and "$value" in tok:
            note = _md_cell(tok.get("$description", ""))
            out.append(f"| `--color-{role}` | `{tok['$value']}` | {role} | {note} |")
    palette = color.get("palette")
    if isinstance(palette, dict):
        for key, tok in _palette_items(palette):
            if isinstance(tok, dict) and "$value" in tok:
                note = _md_cell(tok.get("$description", ""))
                out.append(f"| `--color-palette-{key}` | `{tok['$value']}` | palette | {note} |")
    out.append("")

    rad = doc.get("radius")
    if isinstance(rad, dict) and isinstance(rad.get("base"), dict):
        out += ["### Radius", "",
                f"- `--radius-base`: `{rad['base'].get('$value')}` - {_md_cell(rad['base'].get('$description', ''))}", ""]

    foundation_bits = []
    for label, field in (("Temperatur", "temperature"), ("Saturation", "saturation"),
                         ("Kontrast", "contrast"), ("Dichte", "density")):
        if bs.get(field):
            foundation_bits.append(f"**{label}:** {bs[field]}")
    if foundation_bits:
        out += ["### Charakter", "", "- " + " · ".join(foundation_bits), ""]
    if bs.get("texture"):
        out += [f"- **Textur:** {bs['texture']}", ""]
    if bs.get("imagery"):
        out += [f"- **Bildsprache:** {bs['imagery']}", ""]

    if directives:
        out += ["## Direktiven (Do / Don't)", "", directives, ""]

    if outliers_md:
        out += ["## Ausreisser (aus der Aggregation ausgeschlossen)", "", outliers_md, ""]
    elif bs.get("outliers"):
        out += ["## Ausreisser (aus der Aggregation ausgeschlossen)", ""]
        for o in bs["outliers"]:
            if isinstance(o, dict):
                out.append(f"- **Image {o.get('image')}** - {o.get('why', '')}")
        out.append("")

    if bs.get("notes"):
        out += ["## Hinweis", "", _md_text(bs["notes"]), ""]

    if image_names:
        out += ["## Referenz-Bilder", "",
                f"{len(image_names)} Board-Bilder sind als Assets im Ordner `images/` mitgeliefert.", ""]
        for name in image_names:
            out.append(f"- `images/{name}`")
        out.append("")

    # Token-Index
    out += ["## Token-Dateien", "",
            "- `styles.css` - Einstieg (@import)",
            "- `tokens/colors.css` - Farb-Custom-Properties",
            ]
    if isinstance(rad, dict) and isinstance(rad.get("base"), dict):
        out.append("- `tokens/radius.css` - Radius")
    out.append("")

    co, ct, cov = conf.get("color"), conf.get("typography"), conf.get("overall")
    foot = f"Quelle: {src.get('board_slug', slug)}"
    if src.get("image_count") is not None:
        foot += f" · {src['image_count']} Pins"
    if cov is not None:
        foot += f" · confidence overall {cov} (Farbe {co} / Typo {ct})"
    out += ["---", "", f"*{foot}*", ""]
    return "\n".join(out)


def _md_cell(text: str) -> str:
    """Beschreibung tauglich fuer eine Markdown-Tabellenzelle (keine Pipes/Newlines)."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _md_text(text: str) -> str:
    return text.replace("\n", " ").strip()


# ----------------------------------------------------------------------------- build

def build(doc: dict, style_md: str, out_dir: Path, images_dir: Path | None = None) -> list[Path]:
    color = doc.get("color")
    if not isinstance(color, dict):
        raise ValueError("tokens.json hat kein 'color'-Objekt - ist das ein board-style tokens.json?")

    bs = (doc.get("$extensions") or {}).get("boardStyle", {})
    src = bs.get("source", {}) if isinstance(bs.get("source"), dict) else {}
    slug = src.get("board_slug") or out_dir.name

    title, vibe = _title_and_vibe(style_md) if style_md else (None, None)
    title = title or slug
    directives = _section(style_md, "Direktiv") if style_md else None
    outliers_md = _section(style_md, "Ausrei") if style_md else None

    tokens_dir = out_dir / "tokens"
    tokens_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    imports = ["tokens/colors.css"]
    image_names: list[str] = []

    if images_dir is not None and images_dir.exists():
        images_out = out_dir / "images"
        images_out.mkdir(parents=True, exist_ok=True)
        for src in sorted(images_dir.iterdir(), key=lambda p: p.name):
            if src.is_file() and src.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
                shutil.copy2(src, images_out / src.name)
                image_names.append(src.name)

    (tokens_dir / "colors.css").write_text(emit_colors_css(color, slug), encoding="utf-8")
    written.append(tokens_dir / "colors.css")

    radius_css = emit_radius_css(doc.get("radius", {}))
    if radius_css is not None:
        (tokens_dir / "radius.css").write_text(radius_css, encoding="utf-8")
        written.append(tokens_dir / "radius.css")
        imports.append("tokens/radius.css")

    (out_dir / "styles.css").write_text(emit_styles_css(title, imports), encoding="utf-8")
    written.append(out_dir / "styles.css")

    (out_dir / "readme.md").write_text(
        emit_readme(doc, slug, title, vibe, directives, outliers_md, image_names=image_names or None),
        encoding="utf-8",
    )
    written.append(out_dir / "readme.md")

    (out_dir / "SKILL.md").write_text(emit_skill(slug, title), encoding="utf-8")
    written.append(out_dir / "SKILL.md")

    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="DTCG board-style tokens.json -> Claude-Design-Design-System-Ordner.")
    parser.add_argument("tokens", help="Pfad zu <slug>.tokens.json")
    parser.add_argument("--style", help="Pfad zu <slug>.style.md (Default: neben tokens.json)")
    parser.add_argument("--out", help="Ziel-Ordner (Default: <tokens-ordner>/<slug>-design-system)")
    parser.add_argument("--images", help="Optionaler Ordner mit Referenz-Bildern, die in `images/` kopiert werden")
    args = parser.parse_args(argv)

    tokens_path = Path(args.tokens)
    try:
        doc = json.loads(tokens_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 - jeder Lade-/Parse-Fehler ist ein Input-Fehler
        print(f"FEHLER: {tokens_path} nicht lesbar / kein JSON: {e}", file=sys.stderr)
        return 2

    # style.md aufloesen: --style, sonst <stem ohne .tokens>.style.md
    if args.style:
        style_path: Path | None = Path(args.style)
    else:
        guess = tokens_path.with_name(tokens_path.name.replace(".tokens.json", ".style.md"))
        style_path = guess if guess.exists() else None
    style_md = ""
    if style_path and style_path.exists():
        style_md = style_path.read_text(encoding="utf-8")

    bs = (doc.get("$extensions") or {}).get("boardStyle", {})
    slug = (bs.get("source", {}) or {}).get("board_slug") \
        or tokens_path.name.replace(".tokens.json", "")
    out_dir = Path(args.out) if args.out else tokens_path.parent / f"{slug}-design-system"
    images_dir = Path(args.images) if args.images else None
    if images_dir is not None and not images_dir.exists():
        print(f"FEHLER: Bild-Ordner nicht gefunden: {images_dir}", file=sys.stderr)
        return 2

    try:
        written = build(doc, style_md, out_dir, images_dir=images_dir)
    except ValueError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    print(f"OK - Design System geschrieben nach {out_dir}/")
    for p in written:
        print(f"  - {p.relative_to(out_dir.parent)}")
    if not style_md:
        print("  (Hinweis: kein style.md gefunden - Vibe/Direktiven uebersprungen)", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

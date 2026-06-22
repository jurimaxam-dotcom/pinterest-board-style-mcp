#!/usr/bin/env python3
"""build_style_skill.py — Stufe 2: aus tokens.json (+ Bild-Cache) ein portables Style-Skill bauen.

Deterministisch (stdlib only, kein Netz, kein Timestamp, byte-stabil): liest ein
board-style DTCG-`tokens.json` und den lokalen Bild-Cache und erzeugt einen self-contained
Skill-Ordner, der in Claude Code und Claude Desktop installierbar ist:

    examples/<slug>-style-skill/
      SKILL.md            Agent-Skills-Frontmatter + Build-Methode (Stufe 3)
      readme.md           Vibe + Direktiven + Akzent-Palette + Motiv-Inventar + Bild-Rollen
      styles.css          nur @import der tokens/*
      tokens/colors.css   Kernpalette (--color-*) + Akzent-/Wuerze-Palette (--accent-*)
      tokens/typography.css  Best-Match-Font-Stacks (--font-heading/--font-body)
      tokens/radius.css   --radius-*
      tokens/spacing.css  aus density abgeleitete --space-*
      tokens/shadow.css   aus Materialitaet/Kontrast abgeleitete --shadow-*
      images/             die gebuendelten Board-Bilder (aus dem Cache kopiert)
      README-INSTALL.md   3-Zeilen-Anleitung (Code / Desktop)

    python3 scripts/build_style_skill.py <tokens.json> <cache_dir> [out_dir]

Alles Inferierte (Fonts, Spacing, Shadow) ist im Output als solches markiert. Fehlende
optionale Stufe-1-Felder (webfonts, accentPalette, motifs, ...) degradieren sauber.
Exit 0 = ok, Exit 2 = Eingabefehler (kaputtes JSON, fehlende Argumente).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

CORE_ROLES = ["background", "surface", "text", "primary", "accent", "muted"]

CLASS_STACK = {
    "sans": "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    "serif": "Georgia, Cambria, 'Times New Roman', Times, serif",
    "mono": "'SF Mono', 'Roboto Mono', Menlo, Consolas, monospace",
    "slab": "Rockwell, 'Roboto Slab', Georgia, serif",
    "display": "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
}

SPACING_SCALE = {  # rem-Werte je density-Tendenz
    "airy":     [0.5, 1.0, 1.5, 2.5, 4.0, 6.0],
    "balanced": [0.25, 0.5, 1.0, 1.5, 2.5, 4.0],
    "dense":    [0.25, 0.5, 0.75, 1.0, 1.5, 2.25],
}

SHADOW_SETS = {
    "crisp": ["0 1px 0 rgba(0,0,0,.18)", "0 2px 4px rgba(0,0,0,.20)", "0 6px 12px rgba(0,0,0,.22)"],
    "soft":  ["0 1px 3px rgba(0,0,0,.10)", "0 6px 18px rgba(0,0,0,.12)", "0 18px 40px rgba(0,0,0,.16)"],
    "none":  ["none", "none", "none"],
}

TOKEN_FILES = ["colors.css", "typography.css", "radius.css", "spacing.css", "shadow.css"]


# ------------------------------------------------------------------ Helfer

def _board_style(doc: dict) -> dict:
    return (doc.get("$extensions") or {}).get("boardStyle") or {}


def _slug(doc: dict, tokens_path: Path) -> str:
    src = _board_style(doc).get("source") or {}
    slug = src.get("board_slug")
    if isinstance(slug, str) and slug.strip():
        return slug.strip()
    return tokens_path.name.replace(".tokens.json", "").replace(".json", "")


def _hex(token) -> str | None:
    if isinstance(token, dict):
        token = token.get("$value")
    return token if isinstance(token, str) else None


def _palette_keys(palette: dict) -> list[str]:
    keys = [k for k in palette if not k.startswith("$")]
    return sorted(keys, key=lambda k: (not k.isdigit(), int(k) if k.isdigit() else k))


def _fmt(n: float) -> str:
    return f"{n:g}"


def _font_stacks(bs: dict) -> dict:
    classification = (bs.get("typography") or {}).get("classification", "sans")
    derived = CLASS_STACK.get(classification, CLASS_STACK["sans"])
    stacks = {"heading": derived, "body": derived}
    for wf in bs.get("webfonts") or []:
        role = wf.get("role")
        stack = wf.get("stack") or wf.get("family")
        if role in stacks and isinstance(stack, str) and stack.strip():
            stacks[role] = stack.strip()
    return stacks


# ------------------------------------------------------------------ CSS-Generatoren

def gen_colors(doc: dict, bs: dict) -> str:
    color = doc.get("color") or {}
    out = ["/* colors.css — Kernpalette + Akzent-/Wuerze-Palette aus dem Board. */", ":root {"]
    for role in CORE_ROLES:
        hx = _hex(color.get(role))
        if hx:
            out.append(f"  --color-{role}: {hx};")
    palette = color.get("palette")
    if isinstance(palette, dict):
        out.append("")
        out.append("  /* volle Palette nach Dominanz */")
        for k in _palette_keys(palette):
            hx = _hex(palette[k])
            if hx:
                out.append(f"  --color-palette-{k}: {hx};")
    accents = bs.get("accentPalette")
    if isinstance(accents, list) and accents:
        out.append("")
        out.append("  /* Akzent-/Wuerze-Palette — SPARSAM einsetzen (Ausreisser als Wuerze) */")
        for i, a in enumerate(accents):
            hx = _hex(a)
            if not hx:
                continue
            note = " — ".join(x for x in (a.get("name"), a.get("usage")) if isinstance(x, str) and x)
            comment = f"  /* {note} */" if note else ""
            out.append(f"  --accent-{i}: {hx};{comment}")
    out.append("}")
    return "\n".join(out) + "\n"


def gen_typography(bs: dict) -> str:
    stacks = _font_stacks(bs)
    classification = (bs.get("typography") or {}).get("classification", "sans")
    inferred = " (Best-Match inferiert, kein erfundener Fontname)"
    return (
        "/* typography.css — Best-Match-Webfonts" + inferred + ". */\n"
        ":root {\n"
        f"  --font-heading: {stacks['heading']};\n"
        f"  --font-body: {stacks['body']};\n"
        f"  /* Klassifikation aus dem Board: {classification} */\n"
        "}\n"
    )


def gen_radius(doc: dict) -> str:
    base = _hex((doc.get("radius") or {}).get("base")) or "4px"
    m = re.match(r"^([0-9.]+)(px|rem)$", base)
    if m:
        n, unit = float(m.group(1)), m.group(2)
    else:
        n, unit = 4.0, "px"
    return (
        "/* radius.css — abgeleitet aus der Kantenschaerfe des Boards. */\n"
        ":root {\n"
        f"  --radius-sm: {_fmt(round(n * 0.5, 2))}{unit};\n"
        f"  --radius-base: {_fmt(n)}{unit};\n"
        f"  --radius-lg: {_fmt(round(n * 3, 2))}{unit};\n"
        "  --radius-full: 999px;\n"
        "}\n"
    )


def gen_spacing(bs: dict) -> str:
    density = bs.get("density", "balanced")
    scale = SPACING_SCALE.get(density, SPACING_SCALE["balanced"])
    lines = [f"  --space-{i + 1}: {_fmt(v)}rem;" for i, v in enumerate(scale)]
    return (
        f"/* spacing.css — Scale abgeleitet aus density={density}. */\n"
        ":root {\n" + "\n".join(lines) + "\n}\n"
    )


def gen_shadow(bs: dict) -> str:
    shadow = bs.get("shadow") or {}
    style = shadow.get("style") if isinstance(shadow, dict) else None
    if style not in SHADOW_SETS:
        style = {"high": "crisp", "low": "soft"}.get(bs.get("contrast"), "soft")
    sm, md, lg = SHADOW_SETS[style]
    note = shadow.get("note") if isinstance(shadow, dict) else None
    head = f"/* shadow.css — Elevation aus Materialitaet/Kontrast (style={style}).{(' ' + note) if note else ''} */"
    return (
        head + "\n:root {\n"
        f"  --shadow-sm: {sm};\n"
        f"  --shadow-md: {md};\n"
        f"  --shadow-lg: {lg};\n"
        "}\n"
    )


def gen_styles_index() -> str:
    lines = ["/* styles.css — bindet alle Token-Ebenen ein. In dein Projekt importieren. */"]
    lines += [f'@import "tokens/{f}";' for f in TOKEN_FILES]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ Markdown-Generatoren

def gen_skill_md(slug: str, bs: dict) -> str:
    mood = ", ".join(bs.get("mood") or []) or "siehe readme.md"
    desc = (
        f"Use when building any web UI in the visual style of the Pinterest board '{slug}'. "
        f"Applies the bundled design tokens (colors, typography, radius, spacing, shadow) and "
        f"the board imagery as immersive elements. Vibe: {mood}."
    )
    return (
        "---\n"
        f"name: {slug}-style\n"
        f"description: {desc}\n"
        "---\n\n"
        f"# {slug} — Style-Skill\n\n"
        "Baust du etwas „im Stil dieses Boards\", folge dieser Methode — die Tokens sind\n"
        "**Sprungbrett, nicht Kaefig**:\n\n"
        "1. **Sieh dir die Bilder in `images/` an** (nicht nur die Tokens lesen) — sie tragen\n"
        "   Atmosphaere, Material und Motive, die kein Hex-Wert transportiert.\n"
        "2. **Denke iterativ**: erst Konzept, dann Entwurf, dann gegen die Direktiven (readme.md)\n"
        "   selbst kritisieren und verfeinern. „Nicht gut → verbessern\" ist eingeplant.\n"
        "3. **Importiere `styles.css`** und nutze die CSS-Variablen: Kernpalette als Grund,\n"
        "   `--accent-*` nur sparsam als Wuerze.\n"
        "4. **Nutze die Bilder immersiv** statt sie nur in Karten zu rahmen — je nach Bild-Rolle\n"
        "   (siehe readme.md): `hero-bg`/`bleed-band`/`atmosphere` direkt einbetten und mit\n"
        "   Gradient-Overlay (>=4 Stops, fade zur `--color-background`) + `text-shadow` bleeden\n"
        "   lassen; full-bleed Baender via `width:100vw;left:50%;transform:translateX(-50%)`,\n"
        "   oben+unten zur Hintergrundfarbe ausgeblendet. ODER ein **Motiv aus dem Inventar**\n"
        "   als SVG/CSS neu erschaffen (planetfoermiger Button, Bogen-Karte, Spot-Deko).\n"
        "5. **Kritisiere den Entwurf** gegen die Do/Don't-Direktiven und verfeinere.\n"
    )


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {x}" for x in items) + "\n" if items else ""


def gen_readme(slug: str, doc: dict, bs: dict, image_names: list[str]) -> str:
    out = [f"# {slug} — Style-Brief\n"]

    mood = ", ".join(bs.get("mood") or [])
    era = bs.get("era")
    vibe_bits = [b for b in (mood, era) if isinstance(b, str) and b]
    if vibe_bits:
        out.append("## Vibe\n")
        out.append(" · ".join(vibe_bits) + "\n")
    facts = []
    for f in ("temperature", "saturation", "contrast", "density"):
        if bs.get(f):
            facts.append(f"**{f}**: {bs[f]}")
    if facts:
        out.append(" | ".join(facts) + "\n")
    for f in ("texture", "imagery"):
        if isinstance(bs.get(f), str) and bs[f]:
            out.append(f"**{f.capitalize()}**: {bs[f]}\n")

    color = doc.get("color") or {}
    out.append("## Kernpalette\n")
    rows = []
    for role in CORE_ROLES:
        hx = _hex(color.get(role))
        if hx:
            rows.append(f"- `{hx}` — **{role}** (`var(--color-{role})`)")
    out.append("\n".join(rows) + "\n")

    accents = bs.get("accentPalette")
    if isinstance(accents, list) and accents:
        out.append("## Akzent-/Wuerze-Palette (sparsam!)\n")
        rows = []
        for i, a in enumerate(accents):
            hx = _hex(a)
            if not hx:
                continue
            name = a.get("name") or ""
            usage = a.get("usage") or ""
            rows.append(f"- `{hx}` — {name} (`var(--accent-{i})`) — {usage}".rstrip(" —"))
        out.append("\n".join(rows) + "\n")

    fonts = _font_stacks(bs)
    out.append("## Typografie (Best-Match, inferiert)\n")
    out.append(f"- Heading: `{fonts['heading']}` (`var(--font-heading)`)")
    out.append(f"- Body: `{fonts['body']}` (`var(--font-body)`)\n")

    motifs = bs.get("motifs")
    if isinstance(motifs, list) and motifs:
        out.append("## Motiv-/Objekt-Inventar (als UI-Element neu erschaffen)\n")
        rows = []
        for m in motifs:
            name = m.get("name") or "?"
            role = m.get("uiRole") or "?"
            desc = m.get("description") or ""
            rows.append(f"- **{name}** → _{role}_ — {desc}".rstrip(" —"))
        out.append("\n".join(rows) + "\n")

    roles = bs.get("imageRoles")
    if isinstance(roles, dict) and roles:
        out.append("## Bild-Rollen (fuer immersive Einbettung)\n")
        rows = []
        for k in sorted(roles):
            rs = roles[k]
            rs = ", ".join(rs) if isinstance(rs, list) else str(rs)
            rows.append(f"- `images/{k}.jpg` → {rs}")
        out.append("\n".join(rows) + "\n")

    out.append("## Do / Don't\n")
    out.append(_bullet_list([
        "**Do**: Kernpalette als Grund, `--accent-*` nur als sparsame Wuerze.",
        "**Do**: mindestens ein Board-Bild immersiv bleeden ODER ein Motiv als SVG/CSS neu erschaffen.",
        "**Do**: gegen diese Direktiven selbst kritisieren und iterieren.",
        "**Don't**: alle Akzentfarben gleichzeitig — das zerstoert den Vibe.",
        "**Don't**: Bilder lieblos in eckige Karten sperren, wenn sie bleeden koennten.",
        "**Don't**: templated Defaults (Bootstrap-Blau, generische Schatten) gegen den Board-Charakter.",
    ]).rstrip("\n"))
    out.append("")

    if image_names:
        out.append(f"## Bilder\n\n{len(image_names)} Board-Bilder in `images/` (Referenz + direkt einbettbar).\n")

    notes = bs.get("notes")
    if isinstance(notes, str) and notes:
        out.append(f"## Notes\n\n{notes}\n")

    return "\n".join(out)


def gen_install_md(slug: str) -> str:
    name = f"{slug}-style"
    return (
        f"# Installation — {name}\n\n"
        "**Claude Code (projektlokal):** diesen Ordner nach `.claude/skills/" + name + "/` kopieren,\n"
        "dann Session neu starten (Live-Reload greift fuer neue Skill-Ordner nicht).\n\n"
        "**Claude Code (global):** nach `~/.claude/skills/" + name + "/` kopieren.\n\n"
        "**Claude Desktop:** den Ordner als Skill hochladen (Skill-Upload im UI).\n\n"
        "**Direkt im Web-Projekt:** `styles.css` importieren und die CSS-Variablen nutzen;\n"
        "`images/` liegt bereit fuer Hero-/Bleed-/Pano-Einbettung.\n"
    )


# ------------------------------------------------------------------ Orchestrierung

def build_skill(tokens_path, cache_dir, out_dir) -> dict:
    """Baut das Skill-Paket. Gibt ein Summary-dict zurueck."""
    tokens_path, cache_dir, out_dir = Path(tokens_path), Path(cache_dir), Path(out_dir)
    doc = json.loads(tokens_path.read_text(encoding="utf-8"))
    bs = _board_style(doc)
    slug = _slug(doc, tokens_path)

    images_dir = out_dir / "images"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tokens").mkdir(parents=True, exist_ok=True)
    # images/ frisch aufbauen, damit kein verwaister Stand bleibt (Determinismus/Sauberkeit)
    if images_dir.exists():
        for old in images_dir.glob("*.jpg"):
            old.unlink()
    images_dir.mkdir(parents=True, exist_ok=True)

    image_names = []
    if cache_dir.is_dir():
        for src in sorted(cache_dir.glob("*.jpg")):
            (images_dir / src.name).write_bytes(src.read_bytes())
            image_names.append(src.name)

    files = {
        "tokens/colors.css": gen_colors(doc, bs),
        "tokens/typography.css": gen_typography(bs),
        "tokens/radius.css": gen_radius(doc),
        "tokens/spacing.css": gen_spacing(bs),
        "tokens/shadow.css": gen_shadow(bs),
        "styles.css": gen_styles_index(),
        "SKILL.md": gen_skill_md(slug, bs),
        "readme.md": gen_readme(slug, doc, bs, image_names),
        "README-INSTALL.md": gen_install_md(slug),
    }
    for rel, content in files.items():
        (out_dir / rel).write_text(content, encoding="utf-8")

    return {"slug": slug, "out_dir": str(out_dir), "files": sorted(files), "images": len(image_names)}


def main(argv=None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if len(args) < 2:
        print("usage: build_style_skill.py <tokens.json> <cache_dir> [out_dir]", file=sys.stderr)
        return 2
    tokens_path = Path(args[0])
    cache_dir = Path(args[1])
    try:
        doc = json.loads(tokens_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — jeder Lade-/Parse-Fehler ist ein Eingabefehler
        print(f"FEHLER: {tokens_path} nicht lesbar / kein JSON: {e}", file=sys.stderr)
        return 2
    slug = _slug(doc, tokens_path)
    out_dir = Path(args[2]) if len(args) >= 3 else (tokens_path.resolve().parents[1]
                                                    / "examples" / f"{slug}-style-skill")
    summary = build_skill(tokens_path, cache_dir, out_dir)
    print(f"OK — {summary['slug']}-style nach {summary['out_dir']} "
          f"({len(summary['files'])} Dateien, {summary['images']} Bilder).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

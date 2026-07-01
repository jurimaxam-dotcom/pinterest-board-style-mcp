#!/usr/bin/env python3
"""mcp_server.py — stdio-MCP-Server: Pinterest-Board -> Style-Referenz fuer Claude.

NUR Python-Standardbibliothek (kein pip, kein OAuth). Spricht das MCP-Protokoll
(JSON-RPC 2.0, newline-delimited) ueber stdin/stdout. Loggt ausschliesslich nach stderr
(stdout ist reserviert fuer das Protokoll!).

Tool: get_board_style(board_url, [max_images])
  -> laedt die letzten <=25 Pins eines OEFFENTLICHEN Boards via RSS und gibt sie INLINE als
     Bild-Content-Bloecke (base64) + eine Analyse-Anweisung zurueck. Dadurch "sieht" Claude die
     Bilder direkt -> funktioniert in Claude Code UND Claude Desktop (kein Read-Tool noetig).
     Loest den Schmerz: kein manuelles Bilder-Runterladen, kein Claude-Erklaeren.

Bildgroesse: 400x300 (klein) -> moderater Payload, fuer Farb-/Mood-/Style-Analyse voellig genug.

Global registrieren (projektuebergreifend):
    claude mcp add board-style -- python3 /ABS/PFAD/scripts/mcp_server.py
oder via committed .mcp.json (Claude Code), bzw. claude_desktop_config.json (Desktop).
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_board as fb  # noqa: E402  (lokaler Import erst nach sys.path-Fix moeglich)

SERVER_NAME = "pinterest-board-style"
SERVER_VERSION = "0.2.0"
DEFAULT_PROTOCOL = "2024-11-05"
IMAGE_SIZE = "400x300"               # kleine i.pinimg-Variante -> moderater Payload
CACHE_ROOT = Path.home() / ".cache" / "pinterest-board-style"  # immer schreibbar (auch in Desktop)
FACTS_SCRIPT = Path(__file__).resolve().with_name("extract_facts.py")
FACTS_TIMEOUT = 120                  # Sekunden; erster uv-Lauf laedt ggf. Pillow in den uv-Cache

INSTRUCTION = """Die folgenden {count} Bilder sind das Pinterest-Board "{slug}".
Hinweis: Der interne MCP-Cache liegt auf dem Host unter {cache}; diesen Host-Pfad NICHT fuer HTML/CSS-Einbettung verwenden.
Fuer echte Einbettung in Artefakte den separaten EMBEDDABLE_IMAGE_SOURCES-Block mit data:image-Quellen verwenden.
Folgt ein MEASURED_FACTS-Block, sind dessen Palette, metrics und edgeColors der VERBINDLICHE Anker: Farben daraus ableiten, nicht frei schaetzen.
Analysiere sie GEMEINSAM und leite einen wiederverwendbaren Design-Style ab (nicht je Bild einzeln):
- Farben: dominante Hex-Werte in Rollen (background, surface, text, primary, accent, muted) + palette nach Dominanz.
- Mehrheitsentscheidung ueber alle Bilder fuer mood, era, temperature (warm/cool/neutral), saturation, contrast, density.
- Ausreisser (Stilbruch/Fremdfarbe) SEPARAT halten, nicht in die Aggregation einrechnen.
- Marken-/Ad-Overlays (Logos, CTA-Leisten, Werbe-Headlines) sind Chrome, NICHT der Style -> ausschliessen.
- Typografie nur inferiert: 2-3 BEST-MATCH-Webfonts (Google Fonts + System-Stack) mit CSS-Fallback-Stack
  und confidence — KEINE erfundenen Fontnamen.
- Auffaellige Einzelfarben/-motive als Akzent-/Wuerze-Palette SEPARAT mitfuehren (sparsam einsetzbar),
  statt sie nur als Ausreisser zu verwerfen.
- Form/Material: Kantenschaerfe -> radius, Materialitaet -> shadow/Textur, Bilddichte -> density.
- Gegenstaendliche Motive (Planet, Wiese, Rakete, Bogen) als Inventar je mit kurzer Beschreibung und
  vorgeschlagener UI-Rolle (background | decoration | component-shape).
- Jedes Bild nach Einbettungs-Rolle klassifizieren und seine Randfarben oben/unten sampeln.

Gib aus:
1) DTCG-tokens.json: color.* ($value Hex, $type "color"), radius.base, und $extensions.boardStyle mit
   mood, era, temperature, saturation, contrast, density, typography, outliers, confidence, source PLUS
   additiv: webfonts[{role(heading|body), family, stack, confidence}], accentPalette[{$value, name, usage}],
   shadow{style(crisp|soft|none), note}, motifs[{name, description, uiRole}], imageRoles{"NN":
   [hero-bg|bleed-band|focal|texture|wall|atmosphere]}, edgeColors{"NN": {top, bottom}} (Hex je Bild-Nr).
2) einen kurzen Style-Brief: Vibe-Absatz + Do/Don't-Direktiven + Palette.

Daraus baut scripts/build_style_skill.py ein portables Style-Skill (Tokens + Bilder) fuer Claude
Code/Desktop. Nutze den Style als Referenz fuer das, was im aktuellen Projekt gebaut wird."""


def log(*a):
    print("[mcp_server]", *a, file=sys.stderr, flush=True)


def render_instruction(count, slug, cache) -> str:
    """INSTRUCTION mit den Laufzeitwerten fuellen — bewusst .replace statt .format,
    weil INSTRUCTION literale JSON-{...} (Schema-Beispiele) enthaelt, die str.format als
    Platzhalter missdeuten und mit KeyError abbrechen wuerde."""
    return (INSTRUCTION
            .replace("{count}", str(count))
            .replace("{slug}", str(slug))
            .replace("{cache}", str(cache)))


def try_extract_facts(images_dir: Path):
    """Stufe 1a: deterministische Pixel-Fakten via `uv run extract_facts.py` (Pillow).
    Graceful: ohne uv oder bei Fehlern -> None, die Analyse laeuft dann Vision-only."""
    uv = shutil.which("uv")
    if not uv:
        log("uv nicht gefunden — Pixel-Fakten uebersprungen (Vision-only-Analyse).")
        return None
    facts_path = Path(images_dir) / "facts.json"
    try:
        subprocess.run(
            [uv, "run", str(FACTS_SCRIPT), str(images_dir), "-o", str(facts_path)],
            check=True, capture_output=True, timeout=FACTS_TIMEOUT,
        )
        return json.loads(facts_path.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001 — Fakten sind ein Anker, kein Blocker
        log("Fakten-Extraktion fehlgeschlagen (weiter Vision-only):", repr(e))
        return None


def render_measured_facts(facts: dict, facts_path: Path) -> str:
    return (
        "MEASURED_FACTS (deterministisch aus den Pixeln gemessen — verbindlicher Anker):\n"
        + json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n\nRegeln fuer die Analyse:\n"
        "- Alle color.*-$value und palette-Eintraege MUESSEN nahe an dieser gemessenen Palette liegen"
        " — keine Farben erfinden, die die Pixel nicht hergeben.\n"
        "- edgeColors aus diesem Block uebernehmen, NICHT schaetzen.\n"
        "- temperature/saturation/contrast aus metrics uebernehmen; nur bei starkem visuellem"
        " Widerspruch abweichen und das in $extensions.boardStyle begruenden.\n"
        f"- Gespeichert unter: {facts_path}\n"
    )


def render_embeddable_image_sources(manifest_path: Path, image_count: int) -> str:
    lines = [
        "EMBEDDABLE_IMAGE_SOURCES",
        f"{image_count} embeddable data URI sources were written to:",
        str(manifest_path),
        "Use that JSON manifest for HTML <img src> and CSS background-image values. Do not use /Users/tom cache paths for embedding.",
    ]
    return "\n".join(lines) + "\n"


def discover_sandbox_root() -> Path:
    for env_name in ("CLAUDE_USER_FILES_PATH", "CLAUDE_COWORK_USER_FILES_PATH", "CLAUDE_SANDBOX_ROOT"):
        value = os.getenv(env_name)
        if value:
            return Path(value).expanduser()
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        prefs = data.get("preferences") or {}
        for key in ("coworkUserFilesPath",):
            value = prefs.get(key) or data.get(key)
            if value:
                return Path(value).expanduser()
    return Path.home() / "Documents" / "Claude"


def write_export_bundle(assets: dict, *, export_dir: str | os.PathLike[str], export_format: str) -> Path:
    export_dir = Path(export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    images_dir = export_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    embeddable_images = []
    for img in assets.get("images", []):
        src_path = img.get("path")
        dest = images_dir / img.get("file", f"{img['n']:02d}.jpg")
        if src_path and Path(src_path).exists():
            shutil.copy2(src_path, dest)
        elif img.get("data"):
            dest.write_bytes(img["data"])
        if dest.exists():
            encoded = base64.b64encode(dest.read_bytes()).decode("ascii")
            data_uri = f"data:image/jpeg;base64,{encoded}"
            embeddable_images.append({
                "file": dest.name,
                "src": data_uri,
                "html": f'<img src="{data_uri}" alt="{dest.name}">',
                "css": f"background-image: url('{data_uri}');",
            })

    slug = assets.get("slug", export_dir.name)
    (export_dir / "analysis.md").write_text(
        f"Board: {assets.get('board_url')}\nSlug: {slug}\nImages: {assets.get('image_count')}\n",
        encoding="utf-8",
    )
    (export_dir / "readme.md").write_text(
        f"# {slug} — Design-System-Export\n\n"
        f"Diese Ordnerstruktur ist fuer Claude Design/Claude Desktop vorbereitet. "
        f"Die Bilder liegen in `images/`. Echte Design-Tokens entstehen erst nach der "
        f"Vision-Analyse (siehe `scripts/build_style_skill.py`).\n",
        encoding="utf-8",
    )
    (export_dir / "SKILL.md").write_text(
        f"---\nname: {slug}-design\ndescription: Use this package as image reference material for board-derived UI work.\nuser-invocable: true\n---\n\n"
        "Use the images in `images/` as style references. Derive design tokens from the "
        "board analysis (tokens.json), not from this package.\n",
        encoding="utf-8",
    )
    (export_dir / "embeddable-images.json").write_text(
        json.dumps({"images": embeddable_images}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return export_dir


# ------------------------------------------------------------------ Tool-Logik

def tool_get_board_style(args: dict):
    board_url = (args or {}).get("board_url")
    if not isinstance(board_url, str) or not board_url.strip():
        raise ValueError("Parameter 'board_url' (string) fehlt.")
    max_images = int((args or {}).get("max_images") or 25)
    export_format = (args or {}).get("export_format") or "style-skill"
    export_dir = (args or {}).get("export_dir")
    if export_format not in {"none", "design-system", "style-skill"}:
        raise ValueError("Parameter 'export_format' muss eine von: none, design-system, style-skill sein.")
    url = board_url.strip()
    log("get_board_style:", url, f"(max_images={max_images})")
    if fb.is_short_url(url):
        url = fb.resolve_short_url(url)
        log("Kurzlink aufgeloest ->", url)

    _, slug = fb.derive_rss_and_slug(url)
    out_dir = CACHE_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    assets = fb.fetch_board_assets(
        url,
        max_images=max_images,
        size=IMAGE_SIZE,
        mode="persistent",
        out_dir=out_dir,
    )
    blobs = [img["data"] for img in assets["images"]]

    log(f"{len(blobs)} Bilder geladen -> Analyse-Anweisung gesendet.")
    intro = {"type": "text", "text": render_instruction(len(blobs), assets["slug"], Path(assets["out_dir"]))}
    facts = try_extract_facts(Path(assets["out_dir"]))
    facts_block = (
        [{"type": "text", "text": render_measured_facts(facts, Path(assets["out_dir"]) / "facts.json")}]
        if facts else []
    )
    encoded_images = [base64.b64encode(d).decode("ascii") for d in blobs]
    images = [
        {"type": "image", "data": encoded, "mimeType": "image/jpeg"}
        for encoded in encoded_images
    ]
    output = [intro] + facts_block + images
    if export_format != "none":
        target_dir = Path(export_dir) if export_dir else discover_sandbox_root() / assets["slug"] / export_format
        write_export_bundle(assets, export_dir=target_dir, export_format=export_format)
        output.append({"type": "text", "text": render_embeddable_image_sources(target_dir / "embeddable-images.json", len(encoded_images))})
        output.append({"type": "text", "text": f"Export gespeichert unter: {target_dir}"})
    return output


TOOLS = [
    {
        "name": "get_board_style",
        "description": (
            "Holt die Bilder eines OEFFENTLICHEN Pinterest-Boards (letzte <=25 Pins, via RSS, "
            "keine Auth/keine Keys) und gibt sie INLINE als Bilder + eine Analyse-Anweisung zurueck, "
            "sodass Claude daraus einen wiederverwendbaren Design-Style (DTCG-Tokens + Brief) ableitet "
            "und als Referenz fuers aktuelle Projekt nutzt. Erstellt standardmaessig zusaetzlich ein "
            "style-skill-Paket mit images/ in einem Claude-sichtbaren Sandbox-/Upload-Pfad, damit Claude "
            "die Board-Bilder in gebauten Artefakten einbetten kann. "
            "Eingabe: eine Board-URL wie https://www.pinterest.com/<user>/<board>/."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "board_url": {
                    "type": "string",
                    "description": "Board-URL, z.B. https://www.pinterest.com/<user>/<board>/",
                },
                "max_images": {
                    "type": "integer",
                    "description": "max. Anzahl Bilder (Default 25).",
                },
                "export_format": {
                    "type": "string",
                    "description": "Optionaler Export-Modus: style-skill (Default), design-system oder none.",
                },
                "export_dir": {
                    "type": "string",
                    "description": "Optionaler Zielordner fuer den Export (wenn leer: Claude-sichtbarer Sandbox-/Upload-Pfad/<slug>/<format>/).",
                },
            },
            "required": ["board_url"],
        },
    }
]

TOOL_FUNCS = {"get_board_style": tool_get_board_style}


# ------------------------------------------------------------------ JSON-RPC

def ok(rid, result):
    return {"jsonrpc": "2.0", "id": rid, "result": result}


def err(rid, code, message):
    return {"jsonrpc": "2.0", "id": rid, "error": {"code": code, "message": message}}


def handle(req: dict):
    """-> response dict ODER None (bei Notifications, die keine Antwort kriegen)."""
    method = req.get("method")
    rid = req.get("id")
    is_notification = "id" not in req

    if method == "initialize":
        proto = (req.get("params") or {}).get("protocolVersion") or DEFAULT_PROTOCOL
        return ok(rid, {
            "protocolVersion": proto,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        })
    if method == "ping":
        return ok(rid, {})
    if method == "tools/list":
        return ok(rid, {"tools": TOOLS})
    if method == "tools/call":
        params = req.get("params") or {}
        name = params.get("name")
        fn = TOOL_FUNCS.get(name)
        if not fn:
            return err(rid, -32602, f"Unbekanntes Tool: {name}")
        try:
            content = fn(params.get("arguments") or {})
            return ok(rid, {"content": content, "isError": False})
        except Exception as e:  # noqa: BLE001 — Tool-Fehler als isError an Claude zurueckgeben
            log("tool error:", repr(e))
            return ok(rid, {"content": [{"type": "text", "text": f"FEHLER: {e}"}], "isError": True})
    if is_notification:
        return None  # z.B. notifications/initialized
    return err(rid, -32601, f"Methode nicht unterstuetzt: {method}")


def main():
    log(f"{SERVER_NAME} {SERVER_VERSION} bereit (stdio).")
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            log("JSON-Parse-Fehler:", e)
            continue
        try:
            resp = handle(req)
        except Exception as e:  # noqa: BLE001
            log("handler crash:", traceback.format_exc())
            resp = err(req.get("id"), -32603, f"Interner Fehler: {e}")
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()

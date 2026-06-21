#!/usr/bin/env python3
"""mcp_server.py — stdio-MCP-Server: Pinterest-Board -> Style-Referenz fuer Claude.

NUR Python-Standardbibliothek (kein pip, kein OAuth). Spricht das MCP-Protokoll
(JSON-RPC 2.0, newline-delimited) ueber stdin/stdout. Loggt ausschliesslich nach stderr
(stdout ist reserviert fuer das Protokoll!).

Tool: get_board_style(board_url, [max_images])
  -> laedt die letzten <=25 Pins eines OEFFENTLICHEN Boards via RSS nach .cache/<slug>/
     und gibt Claude den Pfad + eine fertige Analyse-Anweisung zurueck. Claude liest die
     Bilder dann selbst (Read-Tool) und leitet daraus einen Style (DTCG-Tokens + Brief) ab.
     Loest genau den Schmerz: kein manuelles Bilder-Runterladen, kein Claude-Erklaeren.

Global registrieren (projektuebergreifend):
    claude mcp add board-style -- python3 /ABS/PFAD/scripts/mcp_server.py
oder via committed .mcp.json, wenn dieses Repo das Arbeitsverzeichnis ist.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_board as fb  # noqa: E402  (lokaler Import erst nach sys.path-Fix moeglich)

SERVER_NAME = "pinterest-board-style"
SERVER_VERSION = "0.1.0"
DEFAULT_PROTOCOL = "2024-11-05"

INSTRUCTION = """Ich habe die {count} Bilder des Pinterest-Boards "{slug}" heruntergeladen nach:
  {cache}

Lies ALLE diese Bilder mit dem Read-Tool (sie sind nummeriert):
{files}

Leite daraus GEMEINSAM einen wiederverwendbaren Design-Style ab (nicht je Bild einzeln):
- Farben: dominante Hex-Werte in Rollen (background, surface, text, primary, accent, muted) + palette nach Dominanz.
- Mehrheitsentscheidung ueber alle Bilder fuer mood, era, temperature (warm/cool/neutral), saturation, contrast, density.
- Ausreisser (Stilbruch/Fremdfarbe) SEPARAT halten, nicht in die Aggregation einrechnen.
- Marken-/Ad-Overlays (Logos, CTA-Leisten, Werbe-Headlines) sind Chrome, NICHT der Style -> ausschliessen.
- Typografie nur inferiert (niedrige confidence), keine Fontnamen erfinden.

Gib aus:
1) DTCG-tokens.json: color.* ($value Hex, $type "color"), radius.base, und $extensions.boardStyle
   (mood, era, temperature, saturation, contrast, density, typography, outliers, confidence, source).
2) einen kurzen Style-Brief: Vibe-Absatz + Do/Don't-Direktiven + Palette.

Nutze diesen Style anschliessend als Referenz fuer das, was im aktuellen Projekt gebaut wird."""


def log(*a):
    print("[mcp_server]", *a, file=sys.stderr, flush=True)


# ------------------------------------------------------------------ Tool-Logik

def fetch_to_cache(board_url: str, max_images: int):
    """RSS -> Bilder nach .cache/<slug>/ (still; nutzt nur nicht-druckende fb-Funktionen)."""
    rss_url, slug = fb.derive_rss_and_slug(board_url)
    items = fb.parse_items(fb.http_get(rss_url, max_bytes=5_000_000))
    if not items:
        raise fb.FetchError("Keine Bild-Pins gefunden — ist das Board oeffentlich und die URL korrekt?")
    out_dir = (Path.cwd() / ".cache" / slug)
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for it in items:
        if len(saved) >= max_images:
            break
        dest = out_dir / f"{len(saved) + 1:02d}.jpg"
        try:
            fb.download_one(it["image_url_raw"], "1200x", dest)  # still, kein stdout
        except fb.FetchError as e:
            log("skip image:", e)
            continue
        saved.append(str(dest.resolve()))
    if len(saved) < 3:
        raise fb.FetchError(f"Nur {len(saved)} Bilder ladbar (<3) — zu wenig Signal fuer einen Style.")
    return slug, out_dir.resolve(), saved


def tool_get_board_style(args: dict):
    board_url = (args or {}).get("board_url")
    if not isinstance(board_url, str) or not board_url.strip():
        raise ValueError("Parameter 'board_url' (string) fehlt.")
    max_images = int((args or {}).get("max_images") or 25)
    slug, cache_dir, paths = fetch_to_cache(board_url.strip(), max_images)
    files = "\n".join(f"  - {p}" for p in paths)
    text = INSTRUCTION.format(count=len(paths), slug=slug, cache=cache_dir, files=files)
    return [{"type": "text", "text": text}]


TOOLS = [
    {
        "name": "get_board_style",
        "description": (
            "Laedt die Bilder eines OEFFENTLICHEN Pinterest-Boards (letzte <=25 Pins, via RSS, "
            "keine Auth/keine Keys) herunter und gibt eine fertige Analyse-Anweisung zurueck, "
            "sodass Claude daraus einen wiederverwendbaren Design-Style (DTCG-Tokens + Brief) "
            "ableitet und als Referenz fuer das aktuelle Projekt nutzt. "
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

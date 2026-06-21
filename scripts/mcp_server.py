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

INSTRUCTION = """Die folgenden {count} Bilder sind das Pinterest-Board "{slug}" (Originale liegen lokal in {cache}).
Analysiere sie GEMEINSAM und leite einen wiederverwendbaren Design-Style ab (nicht je Bild einzeln):
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

def tool_get_board_style(args: dict):
    board_url = (args or {}).get("board_url")
    if not isinstance(board_url, str) or not board_url.strip():
        raise ValueError("Parameter 'board_url' (string) fehlt.")
    max_images = int((args or {}).get("max_images") or 25)

    rss_url, slug = fb.derive_rss_and_slug(board_url.strip())
    items = fb.parse_items(fb.http_get(rss_url, max_bytes=5_000_000))
    if not items:
        raise fb.FetchError("Keine Bild-Pins gefunden — ist das Board oeffentlich und die URL korrekt?")

    out_dir = CACHE_ROOT / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    blobs = []
    for it in items:
        if len(blobs) >= max_images:
            break
        url = fb.upgrade_image_url(it["image_url_raw"], IMAGE_SIZE)
        try:
            data = fb.http_get(url, binary=True)
        except fb.FetchError as e:
            log("skip image:", e)
            continue
        (out_dir / f"{len(blobs) + 1:02d}.jpg").write_bytes(data)
        blobs.append(data)
    if len(blobs) < 3:
        raise fb.FetchError(f"Nur {len(blobs)} Bilder ladbar (<3) — zu wenig Signal fuer einen Style.")

    intro = {"type": "text", "text": INSTRUCTION.format(count=len(blobs), slug=slug, cache=out_dir)}
    images = [
        {"type": "image", "data": base64.b64encode(d).decode("ascii"), "mimeType": "image/jpeg"}
        for d in blobs
    ]
    return [intro] + images


TOOLS = [
    {
        "name": "get_board_style",
        "description": (
            "Holt die Bilder eines OEFFENTLICHEN Pinterest-Boards (letzte <=25 Pins, via RSS, "
            "keine Auth/keine Keys) und gibt sie INLINE als Bilder + eine Analyse-Anweisung zurueck, "
            "sodass Claude daraus einen wiederverwendbaren Design-Style (DTCG-Tokens + Brief) ableitet "
            "und als Referenz fuers aktuelle Projekt nutzt. "
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

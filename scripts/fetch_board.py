#!/usr/bin/env python3
"""fetch_board.py — Pinterest-Board (oeffentlicher RSS-Feed) -> lokale Bilder + manifest.json.

v1 des board-style-extractor. NUR Python-Standardbibliothek: kein OAuth, keine pip-Installs.
Holt die letzten ~25 Pins eines OEFFENTLICHEN Boards via .rss, laedt je Pin das groesste
zuverlaessige Bild (i.pinimg 1200x, Fallback kleiner) nach <out>/<slug>/NN.jpg und schreibt
ein manifest.json. Die Skill `board-style-extractor` liest danach diese Bilder.

Beispiel:
    python3 scripts/fetch_board.py https://www.pinterest.com/homedepot/bath-ideas-and-inspiration/

Hintergrund (Recon 2026-06-21): Die Bild-URL steckt HTML-escaped im <description> (kein
<media:content>/<enclosure>); xml.etree dekodiert die Entities, danach Regex auf i.pinimg.
Die Variante `originals` ist 403-blockiert -> groesste verlaessliche Variante = 1200x (<=2576px,
damit ohne Resize direkt vision-tauglich).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MIN_IMAGES = 3
# Groessenvarianten, in denen i.pinimg ein Bild ausliefert (gross -> klein).
SIZE_FALLBACKS = ["1200x", "736x", "564x", "474x"]
# https://i.pinimg.com/<size>/<rest...>.jpg  — Gruppe 1 = Groesse, Gruppe 2 = Pfad-Rest.
PINIMG_RE = re.compile(r"https://i\.pinimg\.com/([^/\"'<>\s]+)/([^\"'<>\s]+)")


class FetchError(Exception):
    """Erwarteter, dem User erklaerbarer Fehler (klare Meldung statt Stacktrace)."""


# Kurzlink-/Share-Hosts, die Pinterest auf eine Board-URL weiterleitet.
SHORT_HOSTS = ("pin.it",)


def is_short_url(url: str) -> bool:
    """True fuer Pinterest-Kurzlinks (z.B. https://pin.it/abc), die erst aufgeloest werden muessen."""
    host = urllib.parse.urlparse(url.strip()).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in SHORT_HOSTS)


def resolve_short_url(url: str, *, timeout: int = 15, _opener=urllib.request.urlopen) -> str:
    """Kurzlink dem Redirect folgen -> finale Pinterest-URL (ohne Query/Fragment).

    `_opener` ist injizierbar (Tests); Default folgt Redirects via urllib automatisch.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with _opener(req, timeout=timeout) as resp:
            final = resp.geturl()
    except urllib.error.HTTPError as e:           # Redirect-Ziel ist auch bei Fehlercode bekannt
        final = e.geturl()
    except urllib.error.URLError as e:
        raise FetchError(f"Kurzlink nicht aufloesbar ({url}): {e.reason}") from e
    p = urllib.parse.urlsplit(final)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def derive_rss_and_slug(board_url: str):
    """Board-URL oder fertige .rss-URL -> (rss_url, slug)."""
    url = board_url.strip().rstrip("/")
    if url.endswith(".rss"):
        rss_url, path = url, url[:-4]
    else:
        rss_url, path = url + ".rss", url
    if re.search(r"pinterest\.com/pin/", path):
        raise FetchError(
            "Das ist ein einzelner Pin, kein Board — bitte die Board-URL teilen "
            "(.../<user>/<board>/): " + board_url
        )
    m = re.search(r"pinterest\.com/([^/]+)/([^/]+)$", path)
    if not m:
        raise FetchError(
            "URL sieht nicht wie ein Board aus (erwartet .../<user>/<board>): " + board_url
        )
    user, board = m.group(1), m.group(2)
    slug = re.sub(r"[^a-z0-9]+", "-", f"{user}-{board}".lower()).strip("-")
    return rss_url, slug


def http_get(url: str, *, binary: bool = False, timeout: int = 25, max_bytes: int = 20_000_000):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read(max_bytes + 1)  # +1, um Ueberschreitung zu erkennen
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise FetchError(
                "Feed nicht gefunden (HTTP 404). Board nicht oeffentlich oder URL falsch — "
                "v1 nutzt den oeffentlichen RSS-Feed; private Boards erst ab v2 (OAuth)."
            ) from e
        raise FetchError(f"HTTP {e.code} beim Laden von {url}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"Netzwerkfehler bei {url}: {e.reason}") from e
    if len(data) > max_bytes:
        raise FetchError(f"Antwort > {max_bytes} Bytes — aus Sicherheitsgruenden abgebrochen: {url}")
    return data if binary else data.decode("utf-8", "replace")


def upgrade_image_url(url: str, size: str) -> str:
    """i.pinimg.com/<size>/<path> -> gewuenschte Groessenvariante."""
    m = PINIMG_RE.match(url)
    if not m:
        return url
    return f"https://i.pinimg.com/{size}/{m.group(2)}"


def extract_image_url(description: str | None):
    """Roh-Bild-URL (Originalgroesse aus dem Feed) aus dem <description>-HTML ziehen."""
    if not description:
        return None
    m = PINIMG_RE.search(description)
    if not m:
        return None
    raw = f"https://i.pinimg.com/{m.group(1)}/{m.group(2)}"
    # description haengt manchmal Text an die URL — an Dateiendung abschneiden.
    em = re.match(r"(.+?\.(?:jpg|jpeg|png|gif|webp))", raw, re.IGNORECASE)
    return em.group(1) if em else raw


def parse_items(xml_text: str):
    # Schutz vor XXE / Billion-Laughs: der stdlib-Parser expandiert Entities; eine DTD/Entity-
    # Definition gehoert nicht in einen Pinterest-RSS-Feed -> ablehnen. (Statt pip-Dependency
    # `defusedxml`, um die zero-install-Vorgabe von v1 zu wahren.)
    if re.search(r"<!DOCTYPE|<!ENTITY", xml_text, re.IGNORECASE):
        raise FetchError("RSS enthaelt eine DTD/Entity-Definition — aus Sicherheitsgruenden abgelehnt.")
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise FetchError(f"RSS liess sich nicht parsen: {e}") from e
    items = []
    for item in root.iter("item"):
        img = extract_image_url(item.findtext("description"))
        if img:
            items.append(
                {
                    "pin_title": (item.findtext("title") or "").strip(),
                    "pin_link": (item.findtext("link") or "").strip(),
                    "image_url_raw": img,
                }
            )
    return items


def download_one(raw_url: str, primary_size: str, dest: Path) -> str:
    """Versuche Groessen primary -> Fallbacks; speichere die erste, die laedt. -> benutzte URL."""
    sizes = [primary_size] + [s for s in SIZE_FALLBACKS if s != primary_size]
    last: Exception | None = None
    for size in sizes:
        url = upgrade_image_url(raw_url, size)
        try:
            dest.write_bytes(http_get(url, binary=True))
            return url
        except FetchError as e:
            last = e
    raise last if last else FetchError(f"Kein Download fuer {raw_url}")


def download_images(items, out_dir: Path, primary_size: str, limit=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for it in items:
        if limit and len(saved) >= limit:
            break
        n = len(saved) + 1
        fname = f"{n:02d}.jpg"
        try:
            used = download_one(it["image_url_raw"], primary_size, out_dir / fname)
        except FetchError as e:
            print(f"  ! Bild {n} uebersprungen: {e}", file=sys.stderr)
            continue
        saved.append({"n": n, "file": fname, "image_url": used, **it})
        print(f"  + {fname}  {used}")
    return saved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Pinterest-Board -> lokale Bilder + manifest.json (v1, RSS, nur stdlib)."
    )
    ap.add_argument("board_url", help="z.B. https://www.pinterest.com/<user>/<board>/")
    ap.add_argument("--limit", type=int, default=None, help="max. Anzahl Bilder")
    ap.add_argument("--out", default=".cache", help="Zielbasis-Ordner (Default .cache)")
    ap.add_argument("--size", default="1200x", help="i.pinimg-Groessenvariante (Default 1200x)")
    args = ap.parse_args(argv)

    try:
        board_url = args.board_url.strip()
        if is_short_url(board_url):
            board_url = resolve_short_url(board_url)
            print(f"Kurzlink aufgeloest -> {board_url}")
        rss_url, slug = derive_rss_and_slug(board_url)
        print(f"RSS:  {rss_url}")
        print(f"slug: {slug}")
        items = parse_items(http_get(rss_url, max_bytes=5_000_000))
        if not items:
            raise FetchError("Keine Bild-Pins im Feed gefunden (leer oder unerwartetes Format).")
        out_dir = Path(args.out) / slug
        print(f"-> lade nach {out_dir}")
        saved = download_images(items, out_dir, args.size, args.limit)
    except FetchError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    if len(saved) < MIN_IMAGES:
        print(
            f"FEHLER: nur {len(saved)} Bilder geladen (< {MIN_IMAGES}) — zu wenig Signal.",
            file=sys.stderr,
        )
        return 3

    manifest = {
        "board_url": args.board_url,
        "rss_url": rss_url,
        "slug": slug,
        "size_variant": args.size,
        "fetched_count": len(saved),
        "images": saved,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nFertig: {len(saved)} Bilder + manifest.json in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

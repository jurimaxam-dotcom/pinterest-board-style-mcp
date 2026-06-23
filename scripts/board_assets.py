#!/usr/bin/env python3
"""Gemeinsame Asset-Pipeline fuer Pinterest-Boards: RSS -> Bilder -> runtime/temp/persistent."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
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
SIZE_FALLBACKS = ["1200x", "736x", "564x", "474x"]
PINIMG_RE = re.compile(r'https://i\.pinimg\.com/([^/"\'<>\s]+)/([^"\'<>\s]+)')
SHORT_HOSTS = ("pin.it",)


class FetchError(Exception):
    """Erwarteter, dem User erklaerbarer Fehler."""


def is_short_url(url: str) -> bool:
    host = urllib.parse.urlparse(url.strip()).netloc.lower()
    return any(host == h or host.endswith("." + h) for h in SHORT_HOSTS)


def resolve_short_url(url: str, *, timeout: int = 15, _opener=urllib.request.urlopen) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with _opener(req, timeout=timeout) as resp:
            final = resp.geturl()
    except urllib.error.HTTPError as e:
        final = e.geturl()
    except urllib.error.URLError as e:
        raise FetchError(f"Kurzlink nicht aufloesbar ({url}): {e.reason}") from e
    p = urllib.parse.urlsplit(final)
    return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path, "", ""))


def derive_rss_and_slug(board_url: str):
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
            data = resp.read(max_bytes + 1)
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
    m = PINIMG_RE.match(url)
    if not m:
        return url
    return f"https://i.pinimg.com/{size}/{m.group(2)}"


def extract_image_url(description: str | None):
    if not description:
        return None
    m = PINIMG_RE.search(description)
    if not m:
        return None
    raw = f"https://i.pinimg.com/{m.group(1)}/{m.group(2)}"
    em = re.match(r"(.+?\.(?:jpg|jpeg|png|gif|webp))", raw, re.IGNORECASE)
    return em.group(1) if em else raw


def parse_items(xml_text: str):
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


def _download_bytes(raw_url: str, size: str) -> tuple[str, bytes]:
    sizes = [size] + [s for s in SIZE_FALLBACKS if s != size]
    last: Exception | None = None
    for size_name in sizes:
        url = upgrade_image_url(raw_url, size_name)
        try:
            return url, http_get(url, binary=True)
        except FetchError as e:
            last = e
    raise last if last else FetchError(f"Kein Download fuer {raw_url}")


def fetch_board_assets(
    board_url: str,
    *,
    max_images: int | None = 25,
    size: str = "1200x",
    mode: str = "persistent",
    out_dir: str | os.PathLike[str] | None = None,
    temp_dir: str | os.PathLike[str] | None = None,
):
    """Lade Bilder eines Boards in runtime/temp/persistent Modus herunter."""
    if mode not in {"runtime", "temp", "persistent"}:
        raise ValueError(f"Unsupported mode: {mode}")

    url = board_url.strip()
    if is_short_url(url):
        url = resolve_short_url(url)
    rss_url, slug = derive_rss_and_slug(url)
    items = parse_items(http_get(rss_url, max_bytes=5_000_000))
    if not items:
        raise FetchError("Keine Bild-Pins im Feed gefunden (leer oder unerwartetes Format).")

    target_dir: Path | None = None
    if mode == "temp":
        target_dir = Path(temp_dir) if temp_dir is not None else Path(tempfile.mkdtemp(prefix=f"board-style-{slug}-"))
    elif mode == "persistent":
        target_dir = Path(out_dir) if out_dir is not None else Path(".cache") / slug

    if target_dir is not None:
        target_dir.mkdir(parents=True, exist_ok=True)

    images = []
    for item in items:
        if max_images is not None and len(images) >= max_images:
            break
        n = len(images) + 1
        fname = f"{n:02d}.jpg"
        try:
            used_url, data = _download_bytes(item["image_url_raw"], size)
        except FetchError as e:
            continue
        path = None
        if target_dir is not None:
            path = target_dir / fname
            path.write_bytes(data)
        images.append(
            {
                "n": n,
                "file": fname,
                "path": str(path) if path is not None else None,
                "image_url": used_url,
                "data": data,
                "pin_title": item.get("pin_title", ""),
                "pin_link": item.get("pin_link", ""),
                "image_url_raw": item.get("image_url_raw", ""),
            }
        )

    if len(images) < MIN_IMAGES:
        raise FetchError(f"Nur {len(images)} Bilder ladbar (<{MIN_IMAGES}) — zu wenig Signal.")

    return {
        "board_url": board_url,
        "rss_url": rss_url,
        "slug": slug,
        "size_variant": size,
        "image_count": len(images),
        "out_dir": str(target_dir) if target_dir is not None else None,
        "mode": mode,
        "images": images,
    }


def download_images(items, out_dir: Path, primary_size: str, limit=None):
    out_dir.mkdir(parents=True, exist_ok=True)
    saved = []
    for it in items:
        if limit and len(saved) >= limit:
            break
        n = len(saved) + 1
        fname = f"{n:02d}.jpg"
        try:
            used = _download_bytes(it["image_url_raw"], primary_size)[0]
            data = _download_bytes(it["image_url_raw"], primary_size)[1]
        except FetchError as e:
            print(f"  ! Bild {n} uebersprungen: {e}", file=sys.stderr)
            continue
        dest = out_dir / fname
        dest.write_bytes(data)
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
        assets = fetch_board_assets(
            board_url,
            max_images=args.limit,
            size=args.size,
            mode="persistent",
            out_dir=Path(args.out) / derive_rss_and_slug(board_url)[1],
        )
        print(f"RSS:  {assets['rss_url']}")
        print(f"slug: {assets['slug']}")
        print(f"-> lade nach {assets['out_dir']}")
        saved = []
        for it in assets["images"]:
            saved.append(
                {
                    "n": it["n"],
                    "file": it["file"],
                    "image_url": it["image_url"],
                    "pin_title": it["pin_title"],
                    "pin_link": it["pin_link"],
                    "image_url_raw": it["image_url_raw"],
                }
            )
    except FetchError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 2

    manifest = {
        "board_url": args.board_url,
        "rss_url": assets["rss_url"],
        "slug": assets["slug"],
        "size_variant": args.size,
        "fetched_count": len(saved),
        "images": saved,
    }
    out_dir = Path(assets["out_dir"])
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nFertig: {len(saved)} Bilder + manifest.json in {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

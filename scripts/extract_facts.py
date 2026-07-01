#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pillow"]
# ///
"""extract_facts.py — deterministische Pixel-Fakten eines Board-Bilder-Ordners (Stufe 1a).

Misst, was messbar ist, damit die Vision-Analyse (Stufe 1b) nur noch urteilt, wo Urteil
noetig ist: Palette + Dominanz (Median-Cut ueber ALLE Bilder), Randfarben je Bild
(edgeColors oben/unten), Temperatur/Saettigung/Kontrast. Ausgabe: facts.json.

Braucht Pillow — laeuft ohne Installation via uv (PEP-723-Header oben):
    uv run scripts/extract_facts.py <bilder-ordner> [-o facts.json]

Byte-reproduzierbar: gleiche Bilder -> gleiches facts.json (feste Thumbnail-Groesse,
Median-Cut, keine Zufallsquellen).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageStat

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
THUMB = 48                    # Analyse-Aufloesung je Bild (Pixel-Kante)
PALETTE_COLORS = 8            # Median-Cut-Cluster ueber alle Bilder
EDGE_BAND = 5                 # ~10% von THUMB: Zeilen fuer top/bottom-Randfarbe

TEMPERATURE_DELTA = 15        # mean(R) - mean(B): > +delta warm, < -delta cool
SATURATION_LOW, SATURATION_HIGH = 50, 140    # mittlere HSV-S (0-255)
CONTRAST_LOW, CONTRAST_HIGH = 80, 160        # Luma-Spread p95 - p5 (0-255)


class FactsError(Exception):
    """Erwarteter, dem User erklaerbarer Fehler."""


def _rgb_to_hex(rgb) -> str:
    r, g, b = (int(round(v)) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def _band_hex(thumb: Image.Image, top: int, bottom: int) -> str:
    band = thumb.crop((0, top, thumb.width, bottom))
    return _rgb_to_hex(ImageStat.Stat(band).mean)


def _histogram_percentile(histogram: list[int], pct: float) -> int:
    total = sum(histogram)
    target = pct * total
    cumulative = 0
    for value, count in enumerate(histogram):
        cumulative += count
        if cumulative >= target:
            return value
    return len(histogram) - 1


def _classify(value: float, low: float, high: float) -> str:
    if value < low:
        return "low"
    if value > high:
        return "high"
    return "medium"


def extract_facts(images_dir) -> dict:
    images_dir = Path(images_dir)
    files = sorted(p for p in images_dir.iterdir()
                   if p.suffix.lower() in IMAGE_EXTS and p.is_file())
    if not files:
        raise FactsError(f"Keine Bilder ({'/'.join(sorted(IMAGE_EXTS))}) in: {images_dir}")

    thumbs: list[tuple[str, Image.Image]] = []
    for path in files:
        with Image.open(path) as img:
            thumbs.append((path.stem, img.convert("RGB").resize((THUMB, THUMB), Image.Resampling.BILINEAR)))

    edge_colors = {
        stem: {
            "top": _band_hex(thumb, 0, EDGE_BAND),
            "bottom": _band_hex(thumb, THUMB - EDGE_BAND, THUMB),
        }
        for stem, thumb in thumbs
    }

    sheet = Image.new("RGB", (THUMB, THUMB * len(thumbs)))
    for i, (_, thumb) in enumerate(thumbs):
        sheet.paste(thumb, (0, i * THUMB))
    total_pixels = sheet.width * sheet.height

    quantized = sheet.quantize(colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT)
    pal = quantized.getpalette()
    counts = quantized.getcolors(maxcolors=total_pixels) or []
    palette = sorted(
        (
            {
                "hex": _rgb_to_hex(pal[idx * 3:idx * 3 + 3]),
                "dominance": round(count / total_pixels, 4),
            }
            for count, idx in counts
        ),
        key=lambda e: (-e["dominance"], e["hex"]),
    )

    mean_r, _, mean_b = ImageStat.Stat(sheet).mean
    delta = mean_r - mean_b
    temperature = "warm" if delta > TEMPERATURE_DELTA else "cool" if delta < -TEMPERATURE_DELTA else "neutral"

    mean_saturation = ImageStat.Stat(sheet.convert("HSV")).mean[1]

    luma_histogram = sheet.convert("L").histogram()
    luma_spread = _histogram_percentile(luma_histogram, 0.95) - _histogram_percentile(luma_histogram, 0.05)

    return {
        "source": {"images_dir": str(images_dir), "image_count": len(files)},
        "palette": palette,
        "metrics": {
            "temperature": temperature,
            "saturation": _classify(mean_saturation, SATURATION_LOW, SATURATION_HIGH),
            "contrast": _classify(luma_spread, CONTRAST_LOW, CONTRAST_HIGH),
        },
        "edgeColors": edge_colors,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Deterministische Pixel-Fakten eines Bilder-Ordners -> facts.json")
    ap.add_argument("images_dir", help="Ordner mit Board-Bildern (NN.jpg/NN.png)")
    ap.add_argument("-o", "--out", help="Zielpfad (Default: <images_dir>/facts.json)")
    args = ap.parse_args(argv)

    try:
        facts = extract_facts(args.images_dir)
    except FactsError as e:
        print(f"FEHLER: {e}", file=sys.stderr)
        return 1

    out = Path(args.out) if args.out else Path(args.images_dir) / "facts.json"
    out.write_text(json.dumps(facts, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"OK — {facts['source']['image_count']} Bilder gemessen -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

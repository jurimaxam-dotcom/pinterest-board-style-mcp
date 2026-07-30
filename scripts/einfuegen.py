#!/usr/bin/env python3
"""Einfuegen: passt einen Freisteller farblich an ein Board an, damit er sich
in Mockups einfuegt statt aufgeklebt zu wirken.

Drei Stufen: (1) Reinhard-Farbtransfer Richtung der Statistik der Board-Bilder,
(2) Kanten-Feathering gegen den Sticker-Look, (3) Dunstschleier + Korn passend
zur Bildsprache. Aufruf:

  uv run --with pillow,numpy python3 scripts/einfuegen.py \\
      <freisteller.png> <board-cache-dir> <ausgabe.png> \\
      [--staerke 0.55] [--dunst "#80969c"] [--dunst-anteil 0.18] [--korn 2.5]
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def board_statistik(cache_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Mittelwert und Streuung je RGB-Kanal ueber alle Board-Bilder."""
    pixel = []
    for jpg in sorted(cache_dir.glob("[0-9][0-9].jpg")):
        im = Image.open(jpg).convert("RGB")
        im.thumbnail((256, 256))
        pixel.append(np.asarray(im, dtype=np.float64).reshape(-1, 3))
    if not pixel:
        sys.exit(f"FEHLER: keine NN.jpg in {cache_dir}")
    alle = np.concatenate(pixel)
    return alle.mean(axis=0), alle.std(axis=0) + 1e-6


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("freisteller")
    p.add_argument("cache_dir")
    p.add_argument("ausgabe")
    p.add_argument("--staerke", type=float, default=0.55,
                   help="Anteil des Farbtransfers (0=aus, 1=voll)")
    p.add_argument("--dunst", default=None, help="Hex-Farbe des Dunstschleiers")
    p.add_argument("--dunst-anteil", type=float, default=0.18)
    p.add_argument("--korn", type=float, default=2.5, help="Korn-Sigma in Graustufen")
    a = p.parse_args()

    bild = Image.open(a.freisteller).convert("RGBA")
    rgba = np.asarray(bild, dtype=np.float64)
    rgb, alpha = rgba[..., :3], rgba[..., 3]
    motiv = alpha > 8  # nur echte Motiv-Pixel zaehlen, nicht der transparente Rand

    # 1 — Reinhard-Transfer: Statistik des Motivs an die des Boards angleichen
    ref_m, ref_s = board_statistik(Path(a.cache_dir))
    src_m = rgb[motiv].mean(axis=0)
    src_s = rgb[motiv].std(axis=0) + 1e-6
    transferiert = (rgb - src_m) / src_s * ref_s + ref_m
    rgb = rgb * (1 - a.staerke) + transferiert * a.staerke

    # 2 — Dunstschleier: zieht das Motiv in die Atmosphaere des Boards
    if a.dunst:
        dunst = np.array([int(a.dunst.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)],
                         dtype=np.float64)
        rgb = rgb * (1 - a.dunst_anteil) + dunst * a.dunst_anteil

    # 3 — Korn, nur auf dem Motiv (deterministisch, damit Laeufe vergleichbar bleiben)
    if a.korn > 0:
        rng = np.random.default_rng(6)
        rgb = rgb + rng.normal(0, a.korn, rgb.shape) * motiv[..., None]

    # 4 — Feathering: Alpha leicht erodieren und weichzeichnen gegen harte Maskenkanten
    a_img = Image.fromarray(alpha.astype(np.uint8), mode="L")
    erodiert = a_img.filter(ImageFilter.MinFilter(3))
    weich = erodiert.filter(ImageFilter.GaussianBlur(1.2))
    alpha = np.minimum(alpha, np.asarray(weich, dtype=np.float64))

    ergebnis = np.dstack([np.clip(rgb, 0, 255), alpha]).astype(np.uint8)
    Image.fromarray(ergebnis, mode="RGBA").save(a.ausgabe)
    print(f"OK — eingepasst (Transfer {a.staerke:.0%}, "
          f"Dunst {a.dunst or 'aus'}) → {a.ausgabe}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Nebelplatte: macht aus einem Pin eine erweiterbare Hintergrund-Atmosphaere.

Drei Stufen: (1) Motiv per Vision-Vollmaske entfernen und das Loch mit dem
lokalen Farbmittel fuellen (bei Wolken/Nebel unsichtbar), (2) die Platte per
gespiegeltem Cross-Fade auf Wunschbreite erweitern, (3) mehrschichtiges
Rauschen darueber, damit die Spiegelung nicht auffaellt. Klassik statt
Bildmodell — funktioniert fuer niederfrequente Atmosphaere (Nebel, Wolken,
Dunst), NICHT fuer strukturierte Hintergruende (Gebaeude, Muster). Aufruf:

  uv run --with pillow,numpy python3 scripts/nebelplatte.py \\
      <pin.jpg> <ausgabe.png> [--maske vollmaske.png] \\
      [--breite 2400] [--hoehe 800] [--rauschen 4]
"""
import argparse

import numpy as np
from PIL import Image, ImageFilter, ImageOps


def loch_fuellen(bild: Image.Image, maske_pfad: str) -> Image.Image:
    """Ersetzt die Motiv-Pixel durch das stark geglaettete Umfeld."""
    alpha = Image.open(maske_pfad).split()[-1]
    if alpha.size != bild.size:
        raise SystemExit("FEHLER: Maske nicht deckungsgleich — freisteller.swift mit --voll fahren")
    # Motiv grosszuegig fassen (dilatieren + weiche Kante), damit kein Saum bleibt
    zone = alpha.filter(ImageFilter.MaxFilter(15)).filter(ImageFilter.GaussianBlur(6))
    # Fuellung = Bild auf 1/24 verkleinert und zurueckskaliert: lokales Farbmittel
    winzig = bild.resize((max(1, bild.width // 24), max(1, bild.height // 24)))
    fuellung = winzig.resize(bild.size).filter(ImageFilter.GaussianBlur(12))
    return Image.composite(fuellung, bild, zone)


def erweitern(platte: Image.Image, breite: int, hoehe: int) -> Image.Image:
    """Kachelt die Platte per Spiegelung und blendet die Stoesse weich ueber.

    Gegen den Rorschach-Effekt: jede Kachel bekommt einen leicht anderen
    Zoom und Versatz (deterministisch), damit keine Symmetrieachse entsteht.
    """
    rng = np.random.default_rng(6)
    basis = ImageOps.fit(platte, (breite // 2 + breite // 8, hoehe))
    ueberlappung = basis.width // 3
    schritt = basis.width - ueberlappung
    rampe = np.tile(np.linspace(0, 255, ueberlappung), (hoehe, 1)).astype(np.uint8)
    blende = Image.new("L", basis.size, 255)
    blende.paste(Image.fromarray(rampe, mode="L"), (0, 0))

    ergebnis = Image.new("RGB", (breite, hoehe))
    x, gespiegelt = 0, False
    while x < breite:
        stueck = ImageOps.mirror(basis) if gespiegelt else basis
        # Symmetrie brechen: 4–12 % hineinzoomen und den Ausschnitt verschieben
        zoom = 1.04 + rng.uniform(0, 0.08)
        zb, zh = int(stueck.width * zoom), int(stueck.height * zoom)
        gross = stueck.resize((zb, zh))
        dx = rng.integers(0, zb - stueck.width + 1)
        dy = rng.integers(0, zh - stueck.height + 1)
        stueck = gross.crop((dx, dy, dx + stueck.width, dy + stueck.height))
        ergebnis.paste(stueck, (x, 0), blende if x > 0 else None)
        x += schritt
        gespiegelt = not gespiegelt
    return ergebnis


def rauschen(bild: Image.Image, staerke: float) -> Image.Image:
    """Mehrschichtiges Helligkeitsrauschen bricht Spiegel-Symmetrien auf."""
    rng = np.random.default_rng(6)
    arr = np.asarray(bild, dtype=np.float64)
    for radius, gewicht in ((90, 0.6), (25, 0.3), (4, 0.1)):
        grob = rng.normal(0, 255, (bild.height // 8, bild.width // 8))
        schicht = Image.fromarray(np.clip(grob + 128, 0, 255).astype(np.uint8), "L")
        schicht = schicht.resize(bild.size).filter(ImageFilter.GaussianBlur(radius))
        arr += (np.asarray(schicht, dtype=np.float64)[..., None] - 128) / 128 * staerke * gewicht
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("pin")
    p.add_argument("ausgabe")
    p.add_argument("--maske", help="Vollmaske aus freisteller.swift --voll")
    p.add_argument("--breite", type=int, default=2400)
    p.add_argument("--hoehe", type=int, default=800)
    p.add_argument("--rauschen", type=float, default=4.0)
    p.add_argument("--ausschnitt", default=None,
                   help="ruhige Quellregion als Bruchteile l,o,r,u — z.B. 0,0.3,0.6,0.9. "
                        "Markante Strukturen (Tuerme, Gebaeude) aussparen, sonst Rorschach-Effekt")
    a = p.parse_args()

    platte = Image.open(a.pin).convert("RGB")
    if a.maske:
        platte = loch_fuellen(platte, a.maske)
    if a.ausschnitt:
        l, o, r, u = (float(x) for x in a.ausschnitt.split(","))
        platte = platte.crop((int(l * platte.width), int(o * platte.height),
                              int(r * platte.width), int(u * platte.height)))
    banner = erweitern(platte, a.breite, a.hoehe)
    if a.rauschen > 0:
        banner = rauschen(banner, a.rauschen)
    banner.save(a.ausgabe, quality=88)
    print(f"OK — Nebelplatte {banner.width}×{banner.height} px → {a.ausgabe}")


if __name__ == "__main__":
    main()

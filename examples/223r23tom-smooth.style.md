# Style: smooth (223r23Tom)

Das Board atmet kuehle, gedaempfte Weite. Jedes Bild stellt etwas sehr Kleines — eine Silhouette,
ein Flugzeug, einen leuchtenden Zellkern — gegen einen ueberwaeltigend grossen, dunstigen Raum.
Die Farben bleiben in einem engen Blaugruen-Graugruen-Korridor, die Saettigung ist zurueckgenommen,
der Kontrast dagegen hart: fast schwarze Tiefen neben hellem Wolken- und Betonlicht.
Das Ergebnis wirkt cinematisch und kontemplativ, nie dekorativ — Ruhe mit Spannung darunter.

## Palette

**Rollen**

| Rolle | Hex | Notiz |
|---|---|---|
| background | `#0b1e27` | tiefes Blaugruen-Schwarz, ruhigste Grossflaeche |
| surface | `#2c4145` | Petrolblau, angehobene Flaeche im Dunst |
| text | `#b6beb6` | helles Betongrau-Gruen, staerkster Kontrast zum Grund |
| primary | `#80969c` | Dunst-Blaugrau, dominanteste Farbe des Boards |
| accent | `#5c7682` | Horizontblau der Wolken- und Glutlinien |
| muted | `#5f7274` | entsaettigtes Graugruen, Nebeluebergang |

**Top-Palette (nach dominance)**

| # | Hex | dominance | Rolle / Notiz |
|---|---|---|---|
| 0 | `#80969c` | 0.16 | Leitfarbe, Dunst-Blaugrau |
| 1 | `#4a5556` | 0.13 | Beton- und Sturmgrau |
| 2 | `#142426` | 0.13 | dunkles Petrol, Tiefenschatten |
| 3 | `#5f7274` | 0.12 | Nebelgraugruen |
| 4 | `#050f13` | 0.12 | nahezu Schwarz, Bildrand und Vortex-Tiefe |
| 5 | `#2c4145` | 0.11 | Petrolblau der Wasser- und Netzflaechen |
| 6 | `#b6beb6` | 0.11 | Lichtflaechen, Wolken und Beton |
| 7 | `#748079` | 0.11 | moosiges Graugruen, Vegetation im Dunst |

**Akzente:** `#5c7682` Horizontblau (Links, Fokus) · `#779ab0` Alpendunst (Hover, hellster Akzent) ·
`#717a61` gedaempftes Grasgruen · `#636979` Vortex-Violettgrau (seltener Kaltakzent).

## Direktiven

**Do**

- Auf dunklem Grund bauen (`#0b1e27` bis `#050f13`) und Helligkeit als knappe Ressource behandeln —
  hell ist Licht, nicht Flaeche.
- Tiefe ueber gestaffelte Dunstebenen erzeugen: nach hinten aufhellen und entsaettigen,
  nicht ueber Schlagschatten oder Rahmen.
- Grosszuegigen Leerraum lassen; das Hauptelement klein setzen und den Raum um es herum wirken lassen.
- Harte, gerade Kanten fuer Struktur (Radius `2px`), weiche Verlaeufe nur fuer Atmosphaere.
- Kontrast ueber Helligkeit fahren, nicht ueber Buntheit: helles Graugruen auf tiefem Petrol.
- Schatten weit und sehr dunkel streuen (`0 24px 64px rgba(5,15,19,0.55)`), nie als Objektkontur.

**Don't**

- Keine warmen oder bunten Flaechen — kein Orange, Rot, Magenta, kein warmes Beige als Hintergrund.
- Keine gesaettigten Signalfarben; Akzente bleiben innerhalb des Blaugruen-Korridors.
- Keine stark gerundeten Formen (Pills, Cards mit 16px+), keine Glassmorphism-Panels.
- Keine dichten Raster oder volle Layouts — Dichte zerstoert die Weite des Boards.
- Kein hartes Kantenlicht und keine glaenzenden Digitalflaechen.

## Typo / Textur / Bildsprache

- **Typo (inferiert, confidence 0.25):** Sans, leicht bis regular, weit gesperrte Versalien,
  zurueckhaltend-editorial — Schrift tritt hinter das Bild zurueck. Nur Bild 6 zeigt ueberhaupt
  gesetzten Text, daher bewusst keine konkrete Schriftempfehlung.
- **Textur:** weicher Dunst und Volumenlicht, feines Korn in den Tiefen, matte Betonoberflaechen.
- **Bildsprache:** winzige Figur oder einzelnes Objekt in grossem Naturraum; Wolkenmeere,
  Sturmfronten, Bergdunst, Lichtstrahl als Fluchtpunkt, starke Tiefenstaffelung durch Nebelebenen.

## Ausreisser

Keine. Alle sechs Bilder liegen im selben kuehlen, entsaettigten Blaugruen-Korridor mit hohem
Helligkeitskontrast. Bild 1 (heller Korridor mit Gras) und Bild 6 (Alpenpanorama) sind die hellsten
Vertreter, teilen aber Temperatur, Dunstschichtung und Massstabskontrast des Medians und bleiben
deshalb in der Aggregation.

---

Quelle: 6 Pins · confidence overall 0.78

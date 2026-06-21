# Meubels (kvdwerf) - Design System

> Auto-generiert aus einem Pinterest-Board (Foundations-only: Farben, Radius, Stil-Guidance). Keine Komponenten, keine Font-Dateien.
> Import in Claude Design: Share-Menue -> File type **Design System** setzen.

## Vibe

Ein **Designer-Möbel-Board** mit klarer Material- und Formsprache: schlankes **Mattschwarz-Metall**
trifft auf **helles Naturholz** (Eiche/Esche/Kiefer) und **Walnuss**, freigestellt auf weißem
Seamless oder in ruhigen Beton-/Greige-Vignetten. Der Look ist **mid-century × skandinavisch**:
minimalistisch, skulptural, material-ehrlich, viel Negativraum, hoher Hell-Dunkel-Kontrast.
Akzentfarben sind selten und gedämpft — der „Pop" entsteht aus **Form und Material**, nicht aus Farbe.

## Content Fundamentals

- **Mood:** minimalist, mid-century, sculptural, scandinavian, material-honest
- **Era:** Mid-Century-Modern x zeitgenoessisches skandinavisches Design
- **Typografie:** classification: sans, weight: light, case: lowercase, formality: understated-modern _(inferiert, confidence 0.2)_ - nur Klassifikation, keine Font-Dateien.

## Visual Foundations

### Farben

| Token | Hex | Rolle | Notiz |
|---|---|---|---|
| `--color-background` | `#F1EFEA` | background | Off-White; neutraler Seamless-/Studio-Hintergrund der Produktshots. dominance 0.78, confidence 0.88 |
| `--color-surface` | `#C7C5C0` | surface | kuehles Beton-/Hellgrau (Boeden, Waende). dominance 0.45, confidence 0.78 |
| `--color-text` | `#1F1E1C` | text | Mattschwarz; schlanke Metallrahmen + Kontrast (Signatur-'Linie'). dominance 0.58, confidence 0.85 |
| `--color-primary` | `#C7A876` | primary | helles Naturholz (Eiche/Esche/Kiefer); dominantes Material. dominance 0.62, confidence 0.82 |
| `--color-accent` | `#5E4632` | accent | Walnuss/Dunkelholz; zweites Signatur-Material. ACHTUNG: kein konsistenter CHROMA-Akzent im Board — Akzent ist materiell, nicht farbig. dominance 0.40, confidence 0.7 |
| `--color-muted` | `#5F7A7C` | muted | gedaempftes Petrol/Teal; der haeufigste nicht-neutrale Ton (Wandakzente), aber vereinzelt. dominance 0.18, confidence 0.5 |
| `--color-palette-0` | `#F1EFEA` | palette | Off-White. dominance 0.78 |
| `--color-palette-1` | `#C7A876` | palette | helles Naturholz. dominance 0.62 |
| `--color-palette-2` | `#1F1E1C` | palette | Mattschwarz (Metall). dominance 0.58 |
| `--color-palette-3` | `#C7C5C0` | palette | Beton-/Hellgrau. dominance 0.45 |
| `--color-palette-4` | `#5E4632` | palette | Walnuss. dominance 0.40 |
| `--color-palette-5` | `#5F7A7C` | palette | gedaempftes Petrol/Teal (vereinzelter Akzent). dominance 0.18 |
| `--color-palette-6` | `#B06A4E` | palette | Terracotta/Oxblood (vereinzelter Akzent). dominance 0.15 |
| `--color-palette-7` | `#8C8A6E` | palette | Salbei/Olive (vereinzelter Wandton). dominance 0.15 |

### Radius

- `--radius-base`: `2px` - inferiert: ueberwiegend scharfe, geometrische Kanten (A-Frames, Trapez, Hairpin, Cantilever); nur vereinzelt skulpturale Kurven (Bugholz). confidence 0.6

### Charakter

- **Temperatur:** neutral · **Saturation:** muted · **Kontrast:** high · **Dichte:** airy

- **Textur:** matte Holzmaserung (Eiche/Esche/Walnuss), pulverbeschichtetes schlankes Schwarz-Metall, roher Beton; low-gloss, material-honest, taktil

- **Bildsprache:** Produkt-/Studio-Fotografie auf neutralem Seamless + vereinzelt gestylte Interior-Vignetten; viel Negativraum, weiches Tageslicht

## Direktiven (Do / Don't)

- **DO** Kontrast aus **hellem Holz + Mattschwarz-Metall** als Leitmotiv; weiß/Beton als ruhiger Grund.
- **DO** schlanke, lineare Metallrahmen (Hairpin, A-Frame, Cantilever) — die „gezeichnete Linie" ist die Signatur.
- **DO** scharfe, geometrische Kanten; Material-Ehrlichkeit (sichtbare Maserung, low-gloss, roher Beton).
- **DO** viel Weißraum / Negativraum; ein Objekt im Fokus statt voller Szene.
- **DON'T** kräftige Primärfarben (Blau/Gelb/Rot) — die brechen den Look (s. Ausreißer).
- **DON'T** Hochglanz, schwere Polster-Opulenz, dekorative Rundungen als Default.

## Ausreisser (aus der Aggregation ausgeschlossen)

- **Image 12** — grell-primärfarbige Draht-Bänke (Grün/Rot); brechen die gedämpfte Palette.
- **Image 15** — Transforming-Möbel in Primärfarben (Blau/Gelb/Grün/Rot/Lila) + Person; chromatischer & stilistischer Ausreißer.
- **Image 16** — Outdoor-Kontext (Backstein/Hof); Kontext-Ausreißer (Palette Schwarz+Kiefer bleibt on-theme).

## Hinweis

Organisches Board OHNE Marken-Chrome — aber deutlich HETEROGENER als ein art-direktetes Kampagnen-Board: Produkt-Shots mit wechselnden Hintergruenden und verstreuten, inkonsistenten Akzentfarben. Das hoch-konfidente Signal ist MATERIAL/FORM (helles Holz + Walnuss + schlankes Mattschwarz-Metall, skulpturale Geometrie), NICHT eine kohaerente Akzentpalette. confidence ist daher NICHT hoeher als beim chrome-belasteten Board — Chrome-Entfernung loest ein Problem, Heterogenitaet bringt ein anderes.

## Token-Dateien

- `styles.css` - Einstieg (@import)
- `tokens/colors.css` - Farb-Custom-Properties
- `tokens/radius.css` - Radius

---

*Quelle: kvdwerf-meubels · 24 Pins · confidence overall 0.6 (Farbe 0.7 / Typo 0.2)*

# kvdwerf-meubels — Style-Brief

## Vibe

minimalist, mid-century, sculptural, scandinavian, material-honest · Mid-Century-Modern x zeitgenoessisches skandinavisches Design

**temperature**: neutral | **saturation**: muted | **contrast**: high | **density**: airy

**Texture**: matte Holzmaserung (Eiche/Esche/Walnuss), pulverbeschichtetes schlankes Schwarz-Metall, roher Beton; low-gloss, material-honest, taktil

**Imagery**: Produkt-/Studio-Fotografie auf neutralem Seamless + vereinzelt gestylte Interior-Vignetten; viel Negativraum, weiches Tageslicht

## Kernpalette

- `#F1EFEA` — **background** (`var(--color-background)`)
- `#C7C5C0` — **surface** (`var(--color-surface)`)
- `#1F1E1C` — **text** (`var(--color-text)`)
- `#C7A876` — **primary** (`var(--color-primary)`)
- `#5E4632` — **accent** (`var(--color-accent)`)
- `#5F7A7C` — **muted** (`var(--color-muted)`)

## Akzent-/Wuerze-Palette (sparsam!)

- `#B06A4E` — Terracotta (`var(--accent-0)`) — sparsamer Warm-Akzent fuer einzelne CTAs/Hover (Wandton 09, Stuhllehne 06)
- `#5F7A7C` — Petrol/Teal (`var(--accent-1)`) — ruhiger Sekundaer-Akzent fuer Links/Badges (Wand 02)
- `#7A8C5E` — Olive/Salbei (`var(--accent-2)`) — vereinzelter Naturton; dezenter Tertiaer-Akzent (Wand 03)

## Typografie (Best-Match, inferiert)

- Heading: `Inter, 'Helvetica Neue', Arial, sans-serif` (`var(--font-heading)`)
- Body: `'Work Sans', system-ui, -apple-system, sans-serif` (`var(--font-body)`)

## Motiv-/Objekt-Inventar (als UI-Element neu erschaffen)

- **Trapez/A-Frame-Silhouette** → _component-shape_ — schraege, sich nach unten verjuengende geometrische Kante (Hocker 01, Stuehle 13/20/23)
- **Schlanke Schwarz-Metall-Linie** → _decoration_ — duenne pulverbeschichtete Drahtkontur als Rahmen/Bein (04, 14, 16, 23)
- **Naturholz-Maserung** → _background_ — warme Eiche/Esche-Flaeche als grosse ruhige Materialflaeche
- **Bugholz-Lamellen** → _decoration_ — gestapelte gebogene Holzschichten, skulpturaler Schwung (19, 24)

## Bild-Rollen (fuer immersive Einbettung)

- `images/01.jpg` → focal, wall
- `images/02.jpg` → atmosphere, wall
- `images/03.jpg` → focal, wall
- `images/04.jpg` → hero-bg, atmosphere, wall
- `images/05.jpg` → focal, wall
- `images/06.jpg` → atmosphere, wall
- `images/07.jpg` → focal, wall
- `images/08.jpg` → focal, wall
- `images/09.jpg` → atmosphere, texture, wall
- `images/10.jpg` → focal, wall
- `images/11.jpg` → atmosphere, focal, wall
- `images/12.jpg` → focal, wall
- `images/13.jpg` → bleed-band, texture, wall
- `images/14.jpg` → focal, wall
- `images/15.jpg` → focal, wall
- `images/16.jpg` → bleed-band, atmosphere, wall
- `images/17.jpg` → hero-bg, atmosphere, wall
- `images/18.jpg` → bleed-band, focal, wall
- `images/19.jpg` → hero-bg, atmosphere, wall
- `images/20.jpg` → focal, wall
- `images/21.jpg` → bleed-band, atmosphere, wall
- `images/22.jpg` → texture, focal, wall
- `images/23.jpg` → focal, wall
- `images/24.jpg` → focal, wall

## Do / Don't

- **Do**: Kernpalette als Grund, `--accent-*` nur als sparsame Wuerze.
- **Do**: mindestens ein Board-Bild immersiv bleeden ODER ein Motiv als SVG/CSS neu erschaffen.
- **Do**: gegen diese Direktiven selbst kritisieren und iterieren.
- **Don't**: alle Akzentfarben gleichzeitig — das zerstoert den Vibe.
- **Don't**: Bilder lieblos in eckige Karten sperren, wenn sie bleeden koennten.
- **Don't**: templated Defaults (Bootstrap-Blau, generische Schatten) gegen den Board-Charakter.

## Bilder

24 Board-Bilder in `images/` (Referenz + direkt einbettbar).

## Notes

Organisches Board OHNE Marken-Chrome — aber deutlich HETEROGENER als ein art-direktetes Kampagnen-Board: Produkt-Shots mit wechselnden Hintergruenden und verstreuten, inkonsistenten Akzentfarben. Das hoch-konfidente Signal ist MATERIAL/FORM (helles Holz + Walnuss + schlankes Mattschwarz-Metall, skulpturale Geometrie), NICHT eine kohaerente Akzentpalette. confidence ist daher NICHT hoeher als beim chrome-belasteten Board — Chrome-Entfernung loest ein Problem, Heterogenitaet bringt ein anderes.

# 223r23tom-smooth — Style-Brief

## Vibe

atmosphaerisch, einsam, cinematisch, weit, kontemplativ · Gegenwart — 2020er AI-Cinematic / Midjourney-Ästhetik mit Anleihen an Romantik-Landschaftsmalerei (erhabene Weite, winzige Figur)

**temperature**: cool | **saturation**: muted | **contrast**: high | **density**: airy

**Texture**: weicher Dunst und Volumenlicht, feines Filmkorn in den Tiefen, matte Betonoberflaechen, keine glaenzenden oder glatten Digitalflaechen

**Imagery**: einzelne kleine Figur oder Objekt in ueberwaeltigend grossem Naturraum; Wolkenmeere, Sturmfronten, Bergdunst, Lichtstrahl als Fluchtpunkt; starke Tiefenstaffelung durch Nebelebenen

## Kernpalette

- `#0b1e27` — **background** (`var(--color-background)`)
- `#2c4145` — **surface** (`var(--color-surface)`)
- `#b6beb6` — **text** (`var(--color-text)`)
- `#80969c` — **primary** (`var(--color-primary)`)
- `#5c7682` — **accent** (`var(--color-accent)`)
- `#5f7274` — **muted** (`var(--color-muted)`)

## Akzent-/Wuerze-Palette (sparsam!)

- `#5c7682` — Horizontblau (`var(--accent-0)`) — Links, aktive Zustaende, Fokusringe
- `#779ab0` — Alpendunst (`var(--accent-1)`) — hellster Akzent — Hover, Hervorhebung auf dunklem Grund
- `#717a61` — Grasgruen gedaempft (`var(--accent-2)`) — sekundaerer Akzent, Erfolgs-/Naturkontext
- `#636979` — Vortex-Violettgrau (`var(--accent-3)`) — seltener Kaltakzent, Randglow

## Typografie (Best-Match, inferiert)

- Heading: `"Inter", "Helvetica Neue", Arial, sans-serif` (`var(--font-heading)`)
- Body: `"Inter", "Helvetica Neue", Arial, sans-serif` (`var(--font-body)`)

## Motiv-/Objekt-Inventar (als UI-Element neu erschaffen)

- **Nebelebenen** → _background_ — gestaffelte, nach hinten aufhellende Dunstschichten erzeugen Tiefe (Bild 3, 4, 6)
- **Lichtstrahl als Fluchtpunkt** → _decoration_ — vertikaler oder diagonaler Lichtkeil zieht den Blick ins Zentrum (Bild 1, 5)
- **Winzige Figur im Grossraum** → _decoration_ — einzelne kleine Silhouette gegen weite Flaeche — extremer Massstabskontrast (Bild 3, 4, 5)
- **Harte Betonkante** → _component-shape_ — gerade, scharf abgeschnittene Architekturkante schneidet die weiche Natur (Bild 1, 3, 4)
- **Leuchtendes Fadennetz** → _decoration_ — feine helle Linien auf dunklem Grund, Verzweigungsstruktur (Bild 2, 5)

## Bild-Rollen (fuer immersive Einbettung)

- `images/01.jpg` → hero-bg, atmosphere
- `images/02.jpg` → texture, hero-bg
- `images/03.jpg` → hero-bg, focal, atmosphere
- `images/04.jpg` → bleed-band, atmosphere
- `images/05.jpg` → hero-bg, texture
- `images/06.jpg` → hero-bg, focal

## Do / Don't

- **Do**: Kernpalette als Grund, `--accent-*` nur als sparsame Wuerze.
- **Do**: mindestens ein Board-Bild immersiv bleeden ODER ein Motiv als SVG/CSS neu erschaffen.
- **Do**: gegen diese Direktiven selbst kritisieren und iterieren.
- **Don't**: alle Akzentfarben gleichzeitig — das zerstoert den Vibe.
- **Don't**: Bilder lieblos in eckige Karten sperren, wenn sie bleeden koennten.
- **Don't**: templated Defaults (Bootstrap-Blau, generische Schatten) gegen den Board-Charakter.

## Bilder

6 Board-Bilder in `images/` (Referenz + direkt einbettbar).

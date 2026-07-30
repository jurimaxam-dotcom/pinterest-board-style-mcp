---
name: 223r23tom-smooth-style
description: Use when building any web UI in the visual style of the Pinterest board '223r23tom-smooth'. Applies the bundled design tokens (colors, typography, radius, spacing, shadow) and the board imagery as immersive elements. Vibe: atmosphaerisch, einsam, cinematisch, weit, kontemplativ.
---

# 223r23tom-smooth — Style-Skill

Baust du etwas „im Stil dieses Boards", folge dieser Methode — die Tokens sind
**Sprungbrett, nicht Kaefig**:

1. **Sieh dir die Bilder in `images/` an** (nicht nur die Tokens lesen) — sie tragen
   Atmosphaere, Material und Motive, die kein Hex-Wert transportiert.
2. **Denke iterativ**: erst Konzept, dann Entwurf, dann gegen die Direktiven (readme.md)
   selbst kritisieren und verfeinern. „Nicht gut → verbessern" ist eingeplant.
3. **Importiere `styles.css`** und nutze die CSS-Variablen: Kernpalette als Grund,
   `--accent-*` nur sparsam als Wuerze.
4. **Nutze die Bilder immersiv** statt sie nur in Karten zu rahmen — je nach Bild-Rolle
   (siehe readme.md): `hero-bg`/`bleed-band`/`atmosphere` direkt einbetten und mit
   Gradient-Overlay (>=4 Stops, fade zur `--color-background`) + `text-shadow` bleeden
   lassen; full-bleed Baender via `width:100vw;left:50%;transform:translateX(-50%)`,
   oben+unten zur Hintergrundfarbe ausgeblendet. ODER ein **Motiv aus dem Inventar**
   als SVG/CSS neu erschaffen (planetfoermiger Button, Bogen-Karte, Spot-Deko).
5. **Kritisiere den Entwurf** gegen die Do/Don't-Direktiven und verfeinere.

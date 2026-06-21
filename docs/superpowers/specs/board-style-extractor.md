# Spec: board-style-extractor (v1, RSS)

**Datum:** 2026-06-21 · **Status:** umgesetzt + ausgeliefert · **Scope:** project(Pinterest MCP)

> **Update 2026-06-22:** Fetcher + Skill + **MCP-Server** (`scripts/mcp_server.py`) sind ausgeliefert
> und getestet (`./test.sh`, 19 Tests). Der RSS-Weg (≤25 öffentliche Pins) ist der **finale** Ansatz;
> OAuth/API ist optional/deferred (`v2-oauth-api.md`). Die unten stehende „bewusst ohne MCP"-Formulierung
> beschreibt nur die ursprüngliche v1-Reihenfolge, nicht den Endstand.

## Ziel / Hypothese

v1 validiert das **Produktrisiko**: Lässt sich aus den Bildern eines **öffentlichen**
Pinterest-Boards ein Style ableiten, der sich „wie das Board" anfühlt — **bevor** OAuth/MCP
gebaut wird. Bewusst ohne OAuth/API/MCP, über den öffentlichen Board-`.rss`-Feed.

## Nicht-Ziele (YAGNI)

OAuth · Pinterest-API v5 · MCP-Server · private Boards · K-means-Farben (erst Vision;
deterministisch nur, falls Vision-Farben wackeln) · Resize-Pipeline (1200x passt schon) ·
Multi-Board-Merge · Style-Dictionary-CSS-Gen · `pin.it`-Short-Links.

## Architektur / Datenfluss

```
Board-URL (User)
  └─ .rss ableiten:  https://www.pinterest.com/<user>/<board>.rss
      └─ scripts/fetch_board.py   (nur Python-stdlib: urllib + xml.etree + re)
           • GET .rss (Browser-User-Agent) → <item>-Liste (~25 Pins)
           • Bild-URL aus <description> (HTML-escaped <img src=...>) regexen
           • i.pinimg-Größensegment → 1200x upgraden (Fallback 736x/564x/474x)
           • Download → .cache/<slug>/01.jpg, 02.jpg, …
           • manifest.json  (Nr → {pin_title, pin_link, image_url})
      └─ Skill board-style-extractor   (FOLGT nach Script)
           • Read-Tool auf alle Bilder (visuell, in Reihenfolge nummeriert)
           • Prompt = Rolle + DTCG-Schema + Aggregations-Regeln, Temp 0–0.1
           • analysiert ALLE Bilder GEMEINSAM (nicht einzeln)
      └─ Output
           • examples/<slug>.tokens.json   (valides DTCG + $extensions)
           • examples/<slug>.style.md       (lesbarer Brief)
```

**Verantwortungstrennung:** `fetch_board.py` macht nur I/O (Pins → lokale Bilder), die Skill
nur Analyse. Jede Einheit ist allein testbar.

## Komponenten

### 1. `scripts/fetch_board.py` — Fetcher (nur stdlib)

- **CLI:** `python3 scripts/fetch_board.py <board-url> [--limit N] [--out DIR] [--size 1200x]`
- **Input:** Board-URL (`…/<user>/<board>/`) oder fertige `.rss`-URL.
- **Output:** `.cache/<slug>/NN.jpg` (durchnummeriert) + `manifest.json`.
- **Schritte:** URL→`.rss`+slug ableiten · GET mit Browser-UA · `xml.etree` parsen ·
  je `<item>` Bild-URL aus `<description>` regexen · auf `1200x` upgraden ·
  download (Fallback-Größen bei Fehlschlag) · `manifest.json` schreiben.
- **Exit-Codes:** `0` ok · `2` Fetch-/Parse-Fehler (mit klarer Meldung) · `3` < 3 Bilder geladen.

### 2. `.claude/skills/board-style-extractor/SKILL.md` — Orchestrierung (FOLGT)

Ruft Script → liest Bilder via Read → analysiert nach Schema → schreibt `tokens.json` + `style.md`.

## Extraktions-Schema (Kern der Skill)

Sieben Dimensionen, jeweils **Mehrheits-Aggregat über das ganze Board**, mit `confidence`:

1. **Farben** — dominante Hexes in DTCG-Rollen: `background`, `surface`, `text`, `primary`,
   `accent`, `muted` + rohe `palette[]` (nach Dominanz gerankt); jede Farbe trägt `dominance` (0–1).
2. **Mood** — Adjektive + `era`, `temperature` (warm/kühl), `saturation`, `contrast`.
3. **Typografie-Gefühl** *(inferiert, niedrigere confidence)* — `serif|sans|mono|display|handwritten`,
   Gewicht-Tendenz, Groß-/Kleinschreibung, Formalität.
4. **Dichte/Komposition** — `density`, Whitespace, `radius`-Tendenz, Border-Präsenz.
5. **Textur/Oberfläche** — flat vs. texturiert, Grain, Gradients, Schatten.
6. **Bildsprache** — Foto/Illustration/3D/Flat-Vector; Treatment (Duoton, Film-Grain…).
7. **Ausreißer** — Pins, die nicht zum Stil passen → **separat** (Bild-Nr + Grund), nie mitteln.

**Aggregations-Regeln:** alle Bilder in EINEM Request, nummeriert; Farben nach Fläche/Häufigkeit
gewichten (`dominance`); kategoriale Felder per Mehrheit; Ausreißer raushalten; inferierte
Felder (Typo) niedrigere `confidence`. Structured-Output / Temp 0–0.1.

## Output — zwei Dateien

- **`<slug>.tokens.json`** — maschinen-präzise, **DTCG-valide** (Style Dictionary lesbar).
  Nicht-Token-Wissen (Mood, Ausreißer, confidence) unter `$extensions.boardStyle`.
- **`<slug>.style.md`** — qualitativer **Brief** (Vibe-Absatz + Do/Don't + Palette + Ausreißer).
  Tokens fangen die *Werte*, der Brief die *Richtung* — Claude braucht beides.

```json
{
  "color": {
    "background": { "$value": "#1a1a1a", "$type": "color",
                    "$description": "dominant; dominance 0.62, confidence 0.9" },
    "accent":     { "$value": "#ff5c00", "$type": "color",
                    "$description": "dominance 0.18, confidence 0.8" }
  },
  "radius": { "base": { "$value": "0px", "$type": "dimension",
                        "$description": "inferiert: scharfe Kanten" } },
  "$extensions": {
    "boardStyle": {
      "mood": ["brutalist","high-contrast"], "era": "Y2K-revival",
      "outliers": [{ "image": 14, "why": "pastellig, bricht Palette" }],
      "confidence": { "color": 0.9, "typography": 0.55 }
    }
  }
}
```

## Fehlerbehandlung

- **Privates/falsches Board** → `.rss` 404 → klare Meldung („Board nicht öffentlich oder URL
  falsch — v1 nutzt den öffentlichen RSS-Feed; private Boards erst ab v2 (OAuth)").
- **Leerer Feed / keine Bild-Pins** → Abbruch (Exit 2).
- **Einzelne Downloads schlagen fehl** → überspringen + loggen; weiter, solange **≥ 3 Bilder**
  (sonst zu wenig Signal → Exit 3).

## Empirisch verifiziert (Recon 2026-06-21)

- **RSS lebt:** User- und Board-Feeds liefern HTTP 200, `text/xml`, RSS 2.0, ~25 `<item>`.
- **Board-Format bestätigt:** `https://www.pinterest.com/<user>/<board>.rss`.
- **Bild-URL** steckt HTML-escaped im `<description>` (kein `<media:content>`/`<enclosure>`).
- **Bildvarianten** (i.pinimg): `236x→236px · 474x · 564x · 736x · 1200x→1200×1800px (200)`;
  **`originals` = 403** → größte zuverlässige Variante ist `1200x` (≤2576px ⇒ kein Resize).
- **Test-Board:** `homedepot/bath-ideas-and-inspiration` (öffentlich, 25 Pins).

## Test / Validierung

- **Funktional:** Script auf echtem Board → `manifest.json` + Bilder; `tokens.json` (Skill, später)
  gegen DTCG-Schema validieren.
- **Qualitäts-Gate (menschlich):** „Fühlt sich der Style wie das Board an?" — die Produkthypothese.
  Optional: Claude baut ein Mini-UI aus den Tokens, Vergleich zum Board.

## Offene Punkte / nächste Schritte

1. `fetch_board.py` bauen + einmal gegen Test-Board verifizieren (Tag-Parsing). ← **jetzt**
2. Skill `board-style-extractor` (Schema + Prompt) — erst nach grünem Fetcher.
3. Beispiel-Output (`examples/<slug>.*`) committen.
4. Danach: v2 (offizielle API + OAuth), v3 (MCP-Server).

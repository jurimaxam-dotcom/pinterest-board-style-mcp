---
name: board-style-extractor
description: Use when turning a Pinterest board into a reusable design style. Analyzes ALL board images together (vision) and produces W3C-DTCG design tokens (<slug>.tokens.json) plus a human-readable style brief (<slug>.style.md) in examples/. Triggers on Pinterest boards, moodboards, "board to style / design tokens / style template".
---

# board-style-extractor

Wandelt ein Pinterest-Board in eine wiederverwendbare Design-Style-Vorlage: analysiert **alle**
Board-Bilder **gemeinsam** und erzeugt DTCG-Design-Tokens (`tokens.json`) + einen lesbaren
Style-Brief (`style.md`).

## Input
Eine **Board-URL** ODER ein bereits gefuellter **`.cache/<slug>/`** (mit `manifest.json`).

## Ablauf (strikt der Reihe nach)

1. **Bilder beschaffen** (falls noch kein Cache vorhanden):
   `python3 scripts/fetch_board.py "<board-url>"` → `.cache/<slug>/NN.jpg` + `manifest.json`.
2. **Manifest lesen**: `.cache/<slug>/manifest.json` → `slug`, `images[]`, `fetched_count`.
3. **Alle Bilder laden**: jedes `.cache/<slug>/NN.jpg` der Reihe nach mit dem **Read-Tool** in
   EINEN Analysekontext. Bildnummer `NN` = „Image NN" in der Analyse.
4. **Gemeinsam analysieren** nach dem Analyse-Prompt + den Aggregations-Regeln unten — alle
   Bilder zusammen, nie einzeln zusammengeschustert.
5. **Output schreiben**:
   - `examples/<slug>.tokens.json` — exakt nach `dtcg.schema.json` (in diesem Skill-Ordner).
   - `examples/<slug>.style.md` — nach der Brief-Vorlage unten.
6. **Validieren (Pflicht-Gate)**: `python3 scripts/validate_tokens.py examples/<slug>.tokens.json`.
   Muss „OK" liefern. Bei Fehlern: korrigieren und erneut — **nie** ein invalides File belassen.

## Analyse-Prompt (Rolle + Haltung)

> Du bist ein praeziser **Design-System-Analyst**. Dir liegen alle Bilder eines Pinterest-Boards
> gemeinsam vor (Image 1..N). Leite den **gemeinsamen** visuellen Stil des Boards ab — nicht den
> einzelner Bilder. Erfinde nichts, was die Pixel nicht hergeben. Arbeite analytisch und
> deterministisch (keine kreative Varianz, keine Ausschmueckung). Output ausschliesslich:
> das DTCG-JSON (Schema unten) + der Brief.

## Aggregations-Regeln (scharf)

- **Farben (pixel-gegruendet, hohe confidence):** je Bild die 2–3 flaechen-dominanten Farben
  bestimmen, ueber alle Bilder zu Clustern zusammenfassen. `dominance` (0–1) = Anteil der
  Bilder/Flaeche, in denen ein Cluster auftritt. `palette` nach `dominance` ranken.
  Rollen-Zuweisung: groesste ruhige Flaeche → `background`; staerkster Kontrast dazu → `text`;
  wiederkehrende Sattfarbe → `accent`/`primary`; gedaempfte Zwischentoene → `surface`/`muted`.
- **Mehrheitsentscheidung (kategoriale Felder):** `temperature`, `saturation`, `contrast`,
  `density`, `era`, `imagery` per **Mehrheit ueber die Bilder**; bei Gleichstand entscheidet,
  was die flaechen-dominanten Bilder zeigen.
- **Ausreisser strikt isolieren:** Bilder, deren Palette/Mood deutlich vom Board-Median
  abweichen (Fremd-Dominantfarbe, Stilbruch), **NICHT** in die Aggregation einrechnen.
  Stattdessen in `$extensions.boardStyle.outliers` mit Bildnummer + kurzem Grund. Lieber 1–3
  Ausreisser rausnehmen als den Median verwaessern.
- **Typografie (inferiert, niedrige confidence):** nur Klassifikation (`serif`/`sans`/`mono`/
  `display`/`handwritten`/`mixed`), Gewichts-Tendenz, Gross-/Kleinschreibung, Formalitaet —
  **keine konkreten Fontnamen erfinden**. `confidence.typography` entsprechend niedrig halten.
- **confidence:** `color` hoch (Pixel), `typography` niedrig (inferiert), `overall` als
  gewichteter Mittelwert (Farbe staerker gewichtet).

## Output 1 — `tokens.json` (DTCG)

Struktur **exakt** nach `dtcg.schema.json`:
- `color.{background,surface,text,primary,accent,muted}` + `color.palette.{0,1,…}` —
  je `$value` = Hex (`#rrggbb`), `$description` = „dominance X, confidence Y".
- `radius.base` — `$value` in px (`0px` scharf … `16px` stark gerundet), `$description` = „inferiert: …".
- `$extensions.boardStyle` — `mood[]`, `era`, `temperature`, `saturation`, `contrast`, `density`,
  `typography{classification,weight,case,formality}`, `texture`, `imagery`, `outliers[]`,
  `confidence{color,typography,overall}`, `source{board_slug,image_count}`.

## Output 2 — `style.md` (Brief)

1. `# Style: <Board-Titel>` + 1 Vibe-Absatz (3–4 Saetze: was das Board ausstrahlt).
2. **Palette** — Hex-Liste der Rollen + Top-Palette (jeweils Hex + Rolle/Notiz).
3. **Direktiven (Do / Don't)** — 4–7 konkrete Bau-Anweisungen
   (z.B. „scharfe Kanten, hoher Kontrast, viel Weissraum; KEINE Verlaeufe, keine Pastelltoene").
4. **Typo / Textur / Bildsprache** — je 1 Zeile (Typo mit „(inferiert)" kennzeichnen).
5. **Ausreisser** — welche Bildnummern ausgeschlossen wurden + warum.
6. *Fusszeile:* `Quelle: <N> Pins · confidence overall <…>`.

## Mechanik-Hinweis (Ehrlichkeit)

In Claude Code wird der Stil von **mir** (Vision) erzeugt; ein `SKILL.md` kann **keinen**
API-`temperature`-Wert und **kein** echtes Constrained Decoding setzen — das sind Parameter des
laufenden API-Calls. Durchsetzung hier = **exaktes Schema + `validate_tokens.py`-Gate** (korrigieren
bis gruen). **Echtes** Structured Output / Constrained Decoding mit `temperature` 0–0.1 greift im
**v2-Pfad**, wenn ein Script `dtcg.schema.json` als `output_format` an die Anthropic-API uebergibt —
**dieselbe** Schema-Datei wird dort wiederverwendet.

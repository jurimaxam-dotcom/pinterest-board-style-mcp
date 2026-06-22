# Design-Spec: Kreatives Style-Skill (Board → beeindruckendes Produkt)

**Datum:** 2026-06-22
**Branch:** `feat/creative-style-skill`
**Status:** Entwurf zur Review

## Problem

Die bestehende Pipeline erzeugt aus einem Pinterest-Board DTCG-Tokens + Style-Brief und
verpackt das via `tokens_to_ds.py` für den **Import ins Claude-Design-Produkt**. Nutzer, die
**kein** Claude Design haben, sondern in **Claude Code** und **Claude Desktop** arbeiten,
können damit nichts anfangen: Es gibt keinen Mechanismus, der den Stil beim Bauen anwendet,
und der Inhalt ist *Foundations-only* (nur Farben/Radius/Vibe).

## Ziel

Ein **portables, generatives Style-Skill** pro Board, das in Claude Code und Claude Desktop
installierbar ist. Sagt der Nutzer „bau mir eine Website in diesem Stil", soll das Ergebnis
qualitativ an Claude Design heranreichen — durch eine vorgeschriebene **kreative,
iterative Build-Methode** plus ein reichhaltiges Style-System, das die Original-Board-Bilder
einschließt.

### Leitprinzip: Kreativität mit Spielraum

Die Token-Daten sind **Sprungbrett, nicht Käfig**. Das Skill ermutigt Claude:
- die Daten zu interpretieren, zu erweitern, zu kombinieren — nicht nur Hex-Werte einzusetzen;
- **auffällige Einzelelemente** (heute als Ausreißer ausgeschlossen) als sparsame **Akzente**
  zu nutzen — sie werden als optionale „Würze-Palette" mitgeführt, nicht weggeworfen;
- konkrete **visuelle Motive aus den Bildern** (eine Linienform, ein Materialkontrast)
  aufzugreifen und gestalterisch auszubauen;
- **iterativ und lange zu denken**: ansehen → entwerfen → gegen die Direktiven selbst
  kritisieren → verfeinern. Explorativ — „nicht gut → verbessern" ist eingeplant, kein Fehler.

## Nicht-Ziele (YAGNI)

- **Keine** pixel-genaue Font-Identifikation. Wir liefern *nächstgelegene Webfonts* (Best-Match),
  klar als Inferenz markiert.
- **Keine** Komponenten-Bibliothek / kein fertiger Code als Artefakt — das Skill *beschreibt*,
  Claude *baut* zur Laufzeit.
- **Kein** Live-Netzzugriff beim Bauen (Board-Fetch passiert nur einmal bei der Erzeugung).
- Der bestehende `tokens_to_ds.py` (Claude-Design-Import) bleibt unangetastet — dies ist ein
  zweiter Ausgabepfad daneben.

## Zielnutzer & Umgebung

Claude Code (`.claude/skills/<slug>-design/`) und Claude Desktop (Skill-Upload). Beide laden
dasselbe Agent-Skills-`SKILL.md`-Format. *(Zu verifizieren, s. offene Punkte.)*

## Architektur

Gewählter Ansatz: **statisches, gebündeltes Skill-Paket** (Approach 1 aus dem Brainstorming).
Self-contained, portabel, reproduzierbar, kein Netz beim Bauen. Klare Trennung von
nicht-deterministischer Vision-Analyse und deterministischem Paket-Assembly:

| Stufe | Wer macht es | Determinismus | Output |
|---|---|---|---|
| 1. Board-Analyse (Vision) | Claude via MCP `get_board_style` | nicht-det. | reiches `tokens.json` + `style.md` |
| 2. Paket-Assembly | Python (neuer Adapter) | **deterministisch, testbar** | Skill-Ordner |
| 3. Anwendung (Build) | Claude + Skill-Direktiven | nicht-det. (kreativ) | das Produkt (Website etc.) |

Nur **Stufe 2** kommt ans `test.sh`-Gate. Stufe 1 und 3 werden menschlich/explorativ bewertet
(Jays „wir schauen mal").

### Stufe 1 — reichere Vision-Analyse

Die `INSTRUCTION` in `scripts/mcp_server.py` wird erweitert, sodass Claude beim Board-Scan
zusätzlich liefert (alles als `$extensions.boardStyle` im `tokens.json`):

- **Typo-Klassifikation** → 2–3 **Best-Match-Webfonts** (Google Fonts + System-Stack) mit
  Confidence und CSS-Fallback-Stack. Kein erfundener Fontname.
- **Akzent-/Würze-Palette**: auffällige Einzelfarben/-motive, getrennt von der Kernpalette,
  als „sparsam einsetzbar" markiert (statt sie nur als Ausreißer zu verwerfen).
- **Form-/Material-Hinweise**: Kantenschärfe → Radius, Materialität → Schatten/Textur,
  Liniencharakter → Border, Bilddichte → Spacing-Tendenz.
- **Bildmotive**: kurze Liste konkret beschriebener visueller Elemente als Inspirationsanker.

### Stufe 2 — Paket-Assembly (`scripts/build_style_skill.py`, neu)

Liest `<slug>.tokens.json` (+ optional `.style.md`) und den lokalen Bild-Cache, erzeugt
deterministisch (stdlib, kein Timestamp, byte-stabil):

```
examples/<slug>-style-skill/
  SKILL.md            # Agent-Skills-Frontmatter (name, description) + Build-Methode
  readme.md           # Vibe + volle Direktiven + Akzent-Palette + Bildmotive
  styles.css          # @import der Token-Dateien
  tokens/
    colors.css        # Kernpalette + Akzent-Palette als --color-* / --accent-*
    typography.css    # Best-Match-Font-Stacks als --font-*
    radius.css        # --radius-*
    spacing.css       # abgeleitete --space-* Scale
    shadow.css        # --shadow-* (aus Materialität)
  images/             # die gebündelten Board-Bilder (aus dem Cache kopiert)
  README-INSTALL.md   # 3-Zeilen-Anleitung: wohin in Code / wie in Desktop
```

Das **Volle Style-System (Variante B)** steckt in `tokens/*` + `readme.md`: Spacing-Scale,
Type-Scale, Radius/Shadow, Komponenten-Direktiven (Button/Card/Nav/Input), Layout-Prinzipien,
Qualitäts-Direktiven gegen templated Defaults. Alles Inferierte ist als solches markiert.

### Stufe 3 — die Build-Methode im SKILL.md

`SKILL.md` weist Claude an, beim „bau X im Stil"-Auftrag:
1. die Bilder in `images/` **anzusehen** (nicht nur die Tokens lesen);
2. **iterativ/lange zu denken**: erst Konzept, dann Entwurf;
3. Kernpalette als Grund, **Akzente sparsam** aus der Würze-Palette;
4. mindestens ein **Bildmotiv kreativ aufzugreifen** und auszubauen;
5. den Entwurf **gegen die Do/Don't-Direktiven selbst zu kritisieren** und zu verfeinern.

## Verifikation

**Deterministisch (am `test.sh`-Gate, neu in `tests/test_all.py`):**
- alle erwarteten Dateien vorhanden (SKILL.md, readme, styles.css, alle tokens/*, images/ nicht leer);
- `styles.css` enthält nur `@import`;
- `colors.css` enthält Kernrollen **und** Akzent-Palette als `--color-*` / `--accent-*`;
- `typography.css` enthält `--font-*` mit Fallback-Stack;
- SKILL.md-Frontmatter hat valides `name` + `description` (Agent-Skills-Format);
- **Byte-Determinismus**: zweimal erzeugen → identisch;
- Fehlerfall (kaputtes JSON) → Exit 2.
- Jeder Test einmal **rot gesehen**, bevor grün.

**Explorativ (durch Jay):** Skill in Claude Code/Desktop installieren, „bau eine Landingpage
im Stil" → Qualität beurteilen. Iterieren.

## Offene Punkte (vor/während Implementierung zu klären)

1. **Skill-Frontmatter & Desktop-Loading verifizieren** (Context7 / Claude-Doku): exaktes
   Agent-Skills-Frontmatter und wie Claude Desktop ein Skill installiert. Die Portabilitäts-These
   hängt daran.
2. **Bild-Bundling-Größe**: 25 Bilder à 400×300 — Paketgröße prüfen; ggf. Anzahl/Größe deckeln
   und das im README transparent machen (kein stilles Truncating).
3. **`get_board_style`-INSTRUCTION-Erweiterung** darf den bestehenden DTCG-Output (für
   `tokens_to_ds.py`) nicht brechen — die neuen Felder sind additiv unter `$extensions`.

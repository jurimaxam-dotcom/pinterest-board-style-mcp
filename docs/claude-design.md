# Claude Design (Anthropic-Produkt) — Referenz & Projekt-Bezug

**Stand:** 2026-06-21 (recherchiert in offiziellen Quellen, s.u.)
**Warum hier:** „Claude Design" ist der primäre *Konsument* des Outputs dieses Projekts
(Board → Style). Der frühere Scout-Report-Satz „Claude Design ist kein Produkt" war **falsch**.

## Was es ist
Anthropic-Labs-Produkt, Start **17.04.2026**, powered by **Opus 4.7**, Research Preview
(Pro/Max/Team/Enterprise). Erzeugt Designs/Prototypen/Slides/One-Pager kollaborativ; Verfeinerung
per Chat / Inline-Kommentar / Direkt-Edit / Slider.

## Design-Systems (Kern-Feature) — offiziell dokumentiert
- **Quellen rein:** Text-Prompt · Bilder + Dokumente (DOCX/PPTX/XLSX) · **Codebase** · **Web-Capture**
  (Elemente direkt von der Website greifen) · seit 17.06.2026 **GitHub-Import**.
- **Extrahiert:** Farbpalette (**primary/secondary/accent**) · Typografie (Font-Family/-Größe/-Gewicht)
  · Components (Buttons/Cards/Navigation) · Layout (Spacing/Grid/Seitenstruktur).
- **Auto-Vererbung:** jedes neue Projekt nutzt das System automatisch (kein erneutes Hochladen).
- **Auto-Korrektur:** Output wird gegen das System geprüft & korrigiert, *bevor* der User es sieht;
  Enterprise kann ein System „locken".
- **Editieren:** „Remix" → Chat-Interface; **bidirektionaler Sync mit Claude Code**; `/design`-Terminal-Command.

## Was NICHT dokumentiert ist (wichtige Lücke)
Anthropic veröffentlicht das *Was* (Farben/Typo/Components/Layout), **nicht das Wie**: keine Angaben zu
**Dominanz-Gewichtung, Mittelung, Konflikt-Auflösung oder Ausreißer-Behandlung** bei uneinheitlichen
Inputs. Der Help-Center-Artikel sagt dazu explizit nichts → die Extraktions-Methodik ist eine **Blackbox**.

## Bezug zu diesem Projekt
- Genau die verborgene Logik (Gewichtung/Ausreißer) macht unser MCP **transparent & steuerbar**:
  `dominance`-Felder pro Farbe, **Ausreißer-Isolation**, **Chrome-Ausschluss** (Logos/Ad-Overlays ≠ Stil).
- **Anschlussfähig:** Claude Design importiert Systeme aus **GitHub / Raw-Uploads** → unsere
  **DTCG-`tokens.json`** ist genau so ein importierbares Design-System-Artefakt.
- **Positionierung:** „Pinterest-Board → portables Style-System", das Claude Design *oder* Claude Code konsumiert.
  Kein Konkurrent, sondern der transparente **Moodboard-→-System-Zubringer**.
- **Möglicher nächster Schritt:** `tokens.json`-Struktur an Claude-Designs GitHub-Import-Format angleichen.

## Quellen
- https://www.anthropic.com/news/claude-design-anthropic-labs
- https://support.claude.com/en/articles/14604397-set-up-your-design-system-in-claude-design
- https://support.claude.com/en/articles/14604416-get-started-with-claude-design
- https://claude.com/product/design
- https://venturebeat.com/technology/anthropic-ships-major-claude-design-overhaul-with-design-system-imports-code-round-trips-and-a-fix-for-its-token-burning-problem

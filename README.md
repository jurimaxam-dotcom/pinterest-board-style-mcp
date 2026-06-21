# Pinterest Board → Claude Style

Verwandle ein **Pinterest-Board** in eine wiederverwendbare **Design-Style-Vorlage**
(DTCG `tokens.json` + Style-Brief), an der sich Claude Code / Claudes Design-Fähigkeit
beim Bauen orientiert.

> **Status: v1-Prototyp (in Entwicklung).** Dieser erste Schritt validiert den wertvollen
> Teil — *Board-Bilder → valider Style* — über den öffentlichen Board-RSS-Feed, **bevor**
> OAuth/MCP gebaut wird.

## Idee

Du pflegst ein Board als Moodboard. Statt den Stil mühsam in Worte zu fassen, liest Claude
die Board-Bilder, analysiert sie gemeinsam und destilliert daraus reproduzierbare
Design-Tokens (Farben, Typografie-Gefühl, Spacing-Charakter, Mood) im **W3C-DTCG-Format**.

## Wie es funktioniert (v1)

1. **Fetch** — Board-`.rss`-Feed (`…/<user>/<board>.rss`) liefert die letzten ~20 Pins ohne OAuth.
2. **Bilder** — Pin-Bilder herunterladen, auf Vision-Größe resizen (≤ 2576 px lange Kante).
3. **Analyse** — Skill `board-style-extractor` gibt alle Bilder gemeinsam an Claudes Vision,
   aggregiert (Mehrheitsfarben, Dominanz, Ausreißer separat).
4. **Output** — valider DTCG-`tokens.json` + kurzer Style-Brief.

## Roadmap

- **v1 (jetzt):** RSS-Prototyp + `board-style-extractor`-Skill → Style-Qualität validieren.
- **v2:** offizielle Pinterest-API v5 + lokales OAuth (Trial-Tier reicht fürs **eigene** Konto, kein Video-Review).
- **v3:** lokaler MCP-Server (`.mcp.json` im Repo) → „clone & go", Claude zieht Boards selbst.

## Eigene Boards (Auth-Modell)

Gedacht für **deine selbst erstellten Boards**. Ab v2 legt jede:r eine eigene kostenlose
Pinterest-App an; OAuth läuft lokal, Trial-Tier genügt fürs eigene Konto — **kein**
Pinterest-Standard-Access / Video-Review nötig.

## Struktur

```
.
├── docs/                         # Recherche, Architektur, Brainstorming
│   └── research/                 # Scout-Report (Markt, API, Patterns)
├── scripts/                      # RSS-Fetcher (v1) — folgt
├── .claude/skills/
│   └── board-style-extractor/    # Style-Extraktions-Skill — folgt
└── examples/                     # Beispiel-Outputs (tokens.json) — folgt
```

## Status der Komponenten

| Komponente | Status |
|---|---|
| Scout-Recherche | ✅ `docs/research/` |
| Architektur-Entscheidung (RSS-first) | ✅ |
| Datenfluss + Extraktions-Schema | 🔄 Brainstorming |
| RSS-Fetcher | ⬜ geplant |
| `board-style-extractor`-Skill | ⬜ geplant |

---

*Kein offizielles Pinterest- oder Anthropic-Projekt. Nutzt öffentliche Board-RSS-Feeds bzw.
ab v2 die offizielle Pinterest-API mit deinem eigenen Account.*

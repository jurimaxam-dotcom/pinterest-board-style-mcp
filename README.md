# Pinterest Board → Claude Style (MCP)

Verwandle ein **öffentliches Pinterest-Board** in eine wiederverwendbare **Design-Style-Vorlage**
(W3C-DTCG `tokens.json` + Style-Brief), die Claude direkt als Referenz beim Bauen nutzt.

**Zero-Auth. Zero-Install. Nur Python-stdlib.** Kein Pinterest-Account-Login, keine API-Keys,
keine `pip install`. Du machst dein Board öffentlich (ein Toggle) — fertig.

## Das Problem, das es löst

Du baust gerade etwas und willst den Look eines Pinterest-Boards als Style-Referenz. Bisher:
jedes Bild einzeln runterladen und Claude erklären, was es damit tun soll. **Mit diesem MCP:**
ein Satz — *„erstell mir einen Style aus diesem Board"* — und Claude holt die Bilder, analysiert
sie und nutzt den Style direkt für dein Projekt.

## Quick Start

**Voraussetzung:** Python 3 (auf macOS/Linux vorinstalliert) + Claude Code (oder Desktop).

```bash
git clone <dieses-repo> pinterest-board-style
cd pinterest-board-style

# Global registrieren -> in JEDEM Projekt verfügbar:
claude mcp add board-style -- python3 "$(pwd)/scripts/mcp_server.py"
```

*(Alternativ: einfach dieses Repo in Claude Code öffnen — die mitgelieferte `.mcp.json`
registriert den Server automatisch, solange das Repo dein Arbeitsverzeichnis ist.)*

Dann in **irgendeinem** Chat:

> „Erstell mir einen Style aus diesem Pinterest-Board: `https://www.pinterest.com/<user>/<board>/`
> und benutz ihn für die App, die ich gerade baue."

Claude ruft das Tool `get_board_style` auf → lädt die Bilder → liest sie → erzeugt
DTCG-Tokens + Style-Brief → designt damit weiter.

## Wie es funktioniert

```
Board-URL  ──►  MCP get_board_style  ──►  .rss (≤25 Pins, keine Auth)  ──►  Bilder nach .cache/
                                                                                    │
   Claude liest die Bilder (Vision)  ◄───────────────────────────────────────────  ┘
                     │
                     ▼
   tokens.json (DTCG: Farben/Radius/$extensions)  +  style.md (Vibe + Do/Don't)
                     │
                     ▼
   Claude nutzt den Style als Referenz fürs aktuelle Projekt
```

Die Analyse erkennt **Marken-/Ad-Overlays** (Logos, CTA-Leisten) als Chrome und schließt sie aus,
hält **Ausreißer-Bilder** separat und aggregiert per Mehrheit über alle Bilder.

## Grenzen (ehrlich)

- **Nur öffentliche Boards.** Privat → klarer Fehler. (Privat-Support via optionalem OAuth: siehe
  `docs/superpowers/specs/v2-oauth-api.md` — bewusst nicht Pflicht, um „clone & läuft" zu wahren.)
- **Die neuesten ~25 Pins**, nicht kuratiert. Tipp: ein **eigenes Board mit ≤25 gezielten Pins**
  anlegen — genau der Sweet Spot für ein Design-Moodboard.

## Zwei Wege, es zu nutzen

| Weg | Wann | Verfügbar |
|---|---|---|
| **MCP** (`get_board_style`) | überall, projektübergreifend, autonom | jedes Projekt + Claude Desktop |
| **Skill** `board-style-extractor` | wenn *dieses* Repo dein Arbeitsverzeichnis ist | Claude Code (auto-load) |

Beide teilen denselben Kern: `scripts/fetch_board.py` (RSS → Bilder) + dasselbe DTCG-Schema.

## Struktur

```
.
├── scripts/
│   ├── fetch_board.py        # RSS-Fetcher (stdlib): Board → .cache/<slug>/ + manifest.json
│   ├── mcp_server.py         # stdio-MCP-Server (stdlib): Tool get_board_style
│   └── validate_tokens.py    # DTCG-Validator (stdlib)
├── .claude/skills/
│   └── board-style-extractor/  # Skill (SKILL.md + dtcg.schema.json)
├── .mcp.json                 # Auto-Registrierung bei offenem Repo
├── examples/                 # Beispiel-Outputs (tokens.json + style.md)
└── docs/                     # Recherche, Specs (inkl. optionaler OAuth-Pfad)
```

## Komponenten

| Komponente | Status |
|---|---|
| RSS-Fetcher (`fetch_board.py`) | ✅ |
| Skill `board-style-extractor` (+ DTCG-Schema) | ✅ |
| DTCG-Validator (`validate_tokens.py`) | ✅ |
| **stdio-MCP-Server (`mcp_server.py`)** | ✅ |
| Beispiel-Läufe (`examples/`) | ✅ Home Depot + kvdwerf/meubels |
| Optionaler OAuth-Pfad (private Boards) | 📄 spezifiziert, nicht Pflicht |

---

*Kein offizielles Pinterest- oder Anthropic-Projekt. Nutzt den öffentlichen Board-RSS-Feed.*

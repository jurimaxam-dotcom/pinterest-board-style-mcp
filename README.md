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
Board-URL  ──►  MCP get_board_style  ──►  .rss (≤25 Pins, keine Auth)  ──►  Bilder nach ~/.cache/pinterest-board-style/
                                                                                    │
   Claude liest die Bilder (Vision)  ◄───────────────────────────────────────────  ┘
                     │
                     ▼
   tokens.json (DTCG: Farben/Radius + Webfonts/Akzente/Motive/Bild-Rollen)  +  style.md
                     │
          ┌──────────┴────────────┐
          ▼                        ▼
   tokens_to_ds.py          build_style_skill.py
   → Import in Claude        → portables Style-Skill (SKILL.md + tokens/*.css + images/)
     Design                    für Claude Code & Desktop: „bau X im Stil dieses Boards"
```

Die Analyse erkennt **Marken-/Ad-Overlays** (Logos, CTA-Leisten) als Chrome und schließt sie aus,
hält **Ausreißer-Bilder** separat (als sparsame Akzent-/Würze-Palette) und aggregiert per Mehrheit
über alle Bilder. Sie liefert zusätzlich **Best-Match-Webfonts**, ein **Motiv-Inventar** (Objekte aus
den Bildern mit vorgeschlagener UI-Rolle) und eine **Bild-Rollen-Klassifikation** für immersive
Einbettung (hero-bg, bleed-band, atmosphere, …).

**Zwei Ausgabe-Pfade** ab demselben `tokens.json`: `tokens_to_ds.py` für den **Claude-Design-Import**,
`build_style_skill.py` für ein **portables, generatives Style-Skill**, das beim Bauen den Stil anwendet —
inklusive der gebündelten Board-Bilder als immersive Elemente.

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

## Cache & Verifikation

- **Cache-Orte:** Der **MCP-Server** legt Bilder unter `~/.cache/pinterest-board-style/<slug>/` ab
  (immer schreibbar — auch wenn das Arbeitsverzeichnis read-only ist, z.B. in Claude Desktop). Das
  **CLI** `fetch_board.py` cachet projektlokal nach `./.cache/<slug>/` (per `--out` änderbar).
- **Tests:** `./test.sh` — deterministische stdlib-Tests (kein Netz, RSS-Fixture): URL-Ableitung,
  RSS-Parsing, XXE-Guard, Validator (grün **und** rot), MCP-Protokoll + Fehlerfälle.
- **Validator-Strenge (ehrlich):** `validate_tokens.py` prüft die **Kern-Invarianten** (Hex-Farben,
  Pflicht-Rollen, Enums, confidence-Range) — **nicht** das vollständige JSON-Schema. Das komplette
  DTCG-Schema liegt in `.claude/skills/board-style-extractor/dtcg.schema.json`.

## Struktur

```
.
├── scripts/
│   ├── fetch_board.py        # RSS-Fetcher (stdlib, CLI): Board → ./.cache/<slug>/ + manifest.json
│   ├── mcp_server.py         # stdio-MCP-Server (stdlib); Cache: ~/.cache/pinterest-board-style/
│   ├── validate_tokens.py    # Token-Validator (stdlib): Kern-Invarianten + Stufe-1-Felder
│   ├── tokens_to_ds.py       # Adapter: tokens.json → Claude-Design-Import
│   └── build_style_skill.py  # Adapter: tokens.json + Bilder → portables Style-Skill (Code/Desktop)
├── .claude/skills/
│   └── board-style-extractor/  # Skill (SKILL.md + dtcg.schema.json = volles DTCG-Schema)
├── tests/                    # stdlib-Tests (kein Netz) + RSS-Fixture
├── test.sh                   # Grün/Rot-Gate
├── .mcp.json                 # Auto-Registrierung bei offenem Repo
├── examples/                 # Beispiel-Outputs (tokens.json + style.md)
└── docs/                     # Recherche, Specs (inkl. optionaler OAuth-Pfad)
```

## Komponenten

| Komponente | Status |
|---|---|
| RSS-Fetcher (`fetch_board.py`) | ✅ |
| Skill `board-style-extractor` (+ volles DTCG-Schema `dtcg.schema.json`) | ✅ |
| Token-Validator (`validate_tokens.py`) — Kern-Invarianten + optionale Stufe-1-Felder | ✅ |
| **stdio-MCP-Server (`mcp_server.py`)** — reichere Vision-Analyse (Webfonts/Akzente/Motive/Bild-Rollen) | ✅ |
| Adapter Claude-Design-Import (`tokens_to_ds.py`) | ✅ |
| **Adapter portables Style-Skill (`build_style_skill.py`)** — Tokens + Bilder → SKILL.md/CSS/images, byte-deterministisch | ✅ |
| Test-Gate (`./test.sh`, stdlib, kein Netz) | ✅ 40 Tests |
| Beispiel-Läufe (`examples/`) | ✅ Home Depot + kvdwerf/meubels |
| Optionaler OAuth-Pfad (private Boards) | 📄 spezifiziert, nicht Pflicht |

---

*Kein offizielles Pinterest- oder Anthropic-Projekt. Nutzt den öffentlichen Board-RSS-Feed.*

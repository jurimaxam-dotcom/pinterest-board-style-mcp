# Pinterest Board → Claude Style (MCP)

*Deutsch · [English](README.md)*

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
git clone https://github.com/jurimaxam-dotcom/pinterest-board-style-mcp.git
cd pinterest-board-style-mcp

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
   extract_facts.py (uv+Pillow, optional): gemessene Palette/edgeColors/metrics  ◄─ ┤
                     │  = verbindlicher Anker (MEASURED_FACTS)                      │
                     ▼                                                              │
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
inklusive der gebündelten Board-Bilder als immersive Elemente. Der Design-System-Export kann optional
mit `--images <ordner>` Referenz-Bilder direkt in den Output-Ordner kopieren.

## Anti-Halluzinations-Pipeline

Vision-Modelle erfinden gern Farben, die zum „Vibe" passen, aber nicht im Board vorkommen.
Dieses Repo macht daraus ein **messbares, rotes Gate**:

1. `extract_facts.py` misst deterministisch Pixel-Fakten (Palette, edgeColors, Sättigung,
   Kontrast, Farbtemperatur) — uv+Pillow, PEP 723, kein Setup.
2. Die Vision-Analyse bekommt diese Fakten als verbindlichen Anker (`MEASURED_FACTS`) mitgeliefert.
3. `validate_tokens.py --facts` prüft jede Vision-Farbe per **ΔE-Distanz (CIE76)** gegen die
   gemessene Palette. Halluzinierte Farben ⇒ Validator rot.

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

- **Cache-/Export-Orte:** Der **MCP-Server** legt Rohbilder intern unter
  `~/.cache/pinterest-board-style/<slug>/` ab (robust bei read-only Arbeitsverzeichnissen). Jeder
  normale MCP-Aufruf exportiert zusätzlich automatisch ein `style-skill`-Paket mit `images/` in einen
  Claude-sichtbaren Sandbox-/Upload-Pfad: `<claude-files>/<slug>/style-skill/`. Mit
  `export_format: "none"` lässt sich dieser Export bewusst abschalten; mit `export_format:
  "design-system"` wird stattdessen ein Design-System-Rohpaket (Bilder + Manifest, ohne Tokens)
  geschrieben — echte Tokens entstehen erst nach der Vision-Analyse via `build_style_skill.py`. Das **CLI**
  `fetch_board.py` cachet projektlokal nach `./.cache/<slug>/` (per `--out` änderbar).
- **Einbettung im Chat:** Für Claude-Desktop-Artefakte sind Host-Pfade wie `/Users/<name>/...` nicht
  zuverlässig lesbar. Der MCP schreibt deshalb im Exportpaket `embeddable-images.json` mit
  `data:image/jpeg;base64,...`-Quellen und gibt im Tool-Result nur den Manifestpfad zurück. Die
  Data-URIs sind die primäre Quelle für `<img src>` und CSS-`background-image`; sie stehen bewusst
  nicht direkt im Tool-Result, damit Claudes 1MB-Result-Limit nicht gerissen wird.
- **Tests:** `./test.sh` — zwei Stufen: (1) deterministische stdlib-Tests (kein Netz, RSS-Fixture):
  URL-Ableitung, RSS-Parsing, XXE-Guard, Validator (grün **und** rot), MCP-Protokoll + Fehlerfälle;
  (2) `extract_facts`-Tests via `uv run --with pillow` (synthetische PNG-Fixtures, deterministisch —
  nur der allererste uv-Lauf lädt Pillow einmalig in den uv-Cache).
- **Validator-Strenge (ehrlich):** `validate_tokens.py` prüft die **Kern-Invarianten** (Hex-Farben,
  Pflicht-Rollen, Enums, confidence-Range) — **nicht** das vollständige JSON-Schema. Das komplette
  DTCG-Schema liegt in `.claude/skills/board-style-extractor/dtcg.schema.json`. Mit
  `--facts .cache/<slug>/facts.json` kommt das **ΔE-Gate** dazu: jede Vision-Farbe muss nahe an der
  gemessenen Palette liegen (CIE76, Default ≤ 30), `temperature` muss zur Messung passen —
  halluzinierte Farben werden damit zu einem roten Gate statt zu einem stillen Fehler.

## Struktur

```
.
├── scripts/
│   ├── board_assets.py       # Gemeinsame Asset-Pipeline: RSS → Bilder in runtime/temp/persistent Modi
│   ├── fetch_board.py        # RSS-Fetcher (stdlib, CLI): Board → ./.cache/<slug>/ + manifest.json
│   ├── extract_facts.py      # Pixel-Fakten (uv+Pillow, PEP 723): Palette/edgeColors/metrics → facts.json
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
| Pixel-Fakten (`extract_facts.py`, uv+Pillow) — gemessene Palette/edgeColors/metrics als Analyse-Anker | ✅ |
| Skill `board-style-extractor` (+ volles DTCG-Schema `dtcg.schema.json`) | ✅ |
| Token-Validator (`validate_tokens.py`) — Kern-Invarianten + Stufe-1-Felder + ΔE-Gate gegen facts.json | ✅ |
| **stdio-MCP-Server (`mcp_server.py`)** — reichere Vision-Analyse (Webfonts/Akzente/Motive/Bild-Rollen) + optionaler Export-Ordner fuer Bild-Rohpakete (Tokens erst nach Analyse) | ✅ |
| Adapter Claude-Design-Import (`tokens_to_ds.py`) | ✅ |
| **Adapter portables Style-Skill (`build_style_skill.py`)** — Tokens + Bilder → SKILL.md/CSS/images, byte-deterministisch | ✅ |
| Test-Gate (`./test.sh`, stdlib, kein Netz) | ✅ 83 Tests |
| Beispiel-Läufe (`examples/`) | ✅ Home Depot + kvdwerf/meubels |
| Optionaler OAuth-Pfad (private Boards) | 📄 spezifiziert, nicht Pflicht |

---

*Kein offizielles Pinterest- oder Anthropic-Projekt. Nutzt den öffentlichen Board-RSS-Feed.*

# Pinterest Board → Claude Style (MCP)

*English · [Deutsch](README.de.md)*

[![tests](https://github.com/jurimaxam-dotcom/pinterest-board-style-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/jurimaxam-dotcom/pinterest-board-style-mcp/actions/workflows/test.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Turn a **public Pinterest board** into a reusable **design style template**
(W3C-DTCG `tokens.json` + style brief) that Claude uses directly as a reference while building.

**Zero auth. Zero install. Python stdlib only.** No Pinterest login, no API keys,
no `pip install`. Make your board public (one toggle) — done.

## The problem it solves

You're building something and want the look of a Pinterest board as a style reference.
Until now: download every image by hand and explain to Claude what to do with them.
**With this MCP:** one sentence — *"create a style from this board"* — and Claude fetches
the images, analyzes them, and applies the style to your project.

## Quick start

**Requirements:** Python 3 (preinstalled on macOS/Linux) + Claude Code (or Claude Desktop).

```bash
git clone https://github.com/jurimaxam-dotcom/pinterest-board-style-mcp.git
cd pinterest-board-style-mcp

# Register globally -> available in EVERY project:
claude mcp add board-style -- python3 "$(pwd)/scripts/mcp_server.py"
```

*(Alternative: just open this repo in Claude Code — the bundled `.mcp.json` registers the
server automatically as long as the repo is your working directory.)*

Then, in **any** chat:

> "Create a style from this Pinterest board: `https://www.pinterest.com/<user>/<board>/`
> and use it for the app I'm building."

Claude calls the `get_board_style` tool → fetches the images → reads them → produces
DTCG tokens + a style brief → keeps designing with it.

## How it works

```
Board URL  ──►  MCP get_board_style  ──►  .rss (≤25 pins, no auth)  ──►  images to ~/.cache/pinterest-board-style/
                                                                                    │
   extract_facts.py (uv+Pillow, optional): measured palette/edgeColors/metrics  ◄─ ┤
                     │  = binding anchor (MEASURED_FACTS)                           │
                     ▼                                                              │
   Claude reads the images (vision)  ◄───────────────────────────────────────────  ┘
                     │
                     ▼
   tokens.json (DTCG: colors/radius + webfonts/accents/motifs/image roles)  +  style.md
                     │
          ┌──────────┴────────────┐
          ▼                        ▼
   tokens_to_ds.py          build_style_skill.py
   → import into Claude      → portable style skill (SKILL.md + tokens/*.css + images/)
     Design                    for Claude Code & Desktop: "build X in this board's style"
```

The analysis detects **brand/ad overlays** (logos, CTA bars) as chrome and excludes them,
keeps **outlier images** separate (as a sparse accent/spice palette), and aggregates by
majority across all images. It also delivers **best-match web fonts**, a **motif inventory**
(objects from the images with a suggested UI role), and an **image role classification** for
immersive embedding (hero-bg, bleed-band, atmosphere, …).

**Two output paths** from the same `tokens.json`: `tokens_to_ds.py` for the
**Claude Design import**, `build_style_skill.py` for a **portable, generative style skill**
that applies the style while building — including the bundled board images as immersive
elements. The design-system export can optionally copy reference images into the output
folder via `--images <dir>`.

## Anti-hallucination pipeline

Vision models love to invent colors that match the "vibe" but don't exist in the board.
This repo turns that failure mode into a **measurable, red gate**:

1. `extract_facts.py` deterministically measures pixel facts (palette, edge colors,
   saturation, contrast, color temperature) — uv+Pillow, PEP 723, no setup.
2. The vision analysis receives these facts as a binding anchor (`MEASURED_FACTS`).
3. `validate_tokens.py --facts` checks every vision-derived color against the measured
   palette via **ΔE distance (CIE76)**. Hallucinated colors ⇒ validator fails.

## Limits (honest)

- **Public boards only.** Private → clear error. (Private-board support via optional OAuth:
  see `docs/superpowers/specs/v2-oauth-api.md` — deliberately not required, to keep
  "clone & run" intact.)
- **The latest ~25 pins**, uncurated. Tip: create a **dedicated board with ≤25 targeted
  pins** — exactly the sweet spot for a design moodboard.

## Two ways to use it

| Path | When | Available in |
|---|---|---|
| **MCP** (`get_board_style`) | anywhere, cross-project, autonomous | every project + Claude Desktop |
| **Skill** `board-style-extractor` | when *this* repo is your working directory | Claude Code (auto-load) |

Both share the same core: `scripts/fetch_board.py` (RSS → images) + the same DTCG schema.

## Cache & verification

- **Cache/export locations:** The **MCP server** stores raw images internally under
  `~/.cache/pinterest-board-style/<slug>/` (robust with read-only working directories).
  Every normal MCP call additionally auto-exports a `style-skill` package with `images/` to a
  Claude-visible sandbox/upload path: `<claude-files>/<slug>/style-skill/`. Set
  `export_format: "none"` to disable this export; `export_format: "design-system"` writes a
  raw design-system package instead (images + manifest, no tokens) — real tokens only exist
  after the vision analysis via `build_style_skill.py`. The **CLI** `fetch_board.py` caches
  project-locally to `./.cache/<slug>/` (changeable via `--out`).
- **Embedding in chat:** For Claude Desktop artifacts, host paths like `/Users/<name>/...`
  are not reliably readable. The MCP therefore writes `embeddable-images.json` with
  `data:image/jpeg;base64,...` sources into the export package and returns only the manifest
  path in the tool result. The data URIs are the primary source for `<img src>` and CSS
  `background-image`; they are deliberately kept out of the tool result so Claude's 1 MB
  result limit is never hit.
- **Tests:** `./test.sh` — two stages: (1) deterministic stdlib tests (no network,
  RSS fixture): URL derivation, RSS parsing, XXE guard, validator (green **and** red),
  MCP protocol + error cases; (2) `extract_facts` tests via `uv run --with pillow`
  (synthetic PNG fixtures, deterministic — only the very first uv run downloads Pillow once
  into the uv cache).
- **Validator strictness (honest):** `validate_tokens.py` checks the **core invariants**
  (hex colors, required roles, enums, confidence range) — **not** the full JSON schema. The
  complete DTCG schema lives in `.claude/skills/board-style-extractor/dtcg.schema.json`.
  With `--facts .cache/<slug>/facts.json` the **ΔE gate** kicks in: every vision color must
  be close to the measured palette (CIE76, default ≤ 30) and `temperature` must match the
  measurement — hallucinated colors become a red gate instead of a silent error.

## Structure

```
.
├── scripts/
│   ├── board_assets.py       # Shared asset pipeline: RSS → images in runtime/temp/persistent modes
│   ├── fetch_board.py        # RSS fetcher (stdlib, CLI): board → ./.cache/<slug>/ + manifest.json
│   ├── extract_facts.py      # Pixel facts (uv+Pillow, PEP 723): palette/edgeColors/metrics → facts.json
│   ├── mcp_server.py         # stdio MCP server (stdlib); cache: ~/.cache/pinterest-board-style/
│   ├── validate_tokens.py    # Token validator (stdlib): core invariants + stage-1 fields
│   ├── tokens_to_ds.py       # Adapter: tokens.json → Claude Design import
│   └── build_style_skill.py  # Adapter: tokens.json + images → portable style skill (Code/Desktop)
├── .claude/skills/
│   └── board-style-extractor/  # Skill (SKILL.md + dtcg.schema.json = full DTCG schema)
├── tests/                    # stdlib tests (no network) + RSS fixture
├── test.sh                   # green/red gate
├── .mcp.json                 # auto-registration when the repo is open
├── examples/                 # example outputs (tokens.json + style.md)
└── docs/                     # research, specs (incl. optional OAuth path)
```

## Components

| Component | Status |
|---|---|
| RSS fetcher (`fetch_board.py`) | ✅ |
| Pixel facts (`extract_facts.py`, uv+Pillow) — measured palette/edgeColors/metrics as analysis anchor | ✅ |
| Skill `board-style-extractor` (+ full DTCG schema `dtcg.schema.json`) | ✅ |
| Token validator (`validate_tokens.py`) — core invariants + stage-1 fields + ΔE gate against facts.json | ✅ |
| **stdio MCP server (`mcp_server.py`)** — richer vision analysis (webfonts/accents/motifs/image roles) + optional export folder for raw image packages (tokens only after analysis) | ✅ |
| Adapter Claude Design import (`tokens_to_ds.py`) | ✅ |
| **Adapter portable style skill (`build_style_skill.py`)** — tokens + images → SKILL.md/CSS/images, byte-deterministic | ✅ |
| Test gate (`./test.sh`, stdlib, no network) | ✅ 83 tests |
| Example runs (`examples/`) | ✅ Home Depot + kvdwerf/meubels |
| Optional OAuth path (private boards) | 📄 specified, not required |

---

*Not an official Pinterest or Anthropic project. Uses the public board RSS feed.*

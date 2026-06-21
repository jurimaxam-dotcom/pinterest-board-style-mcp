---
type: research
thema: "Pinterest ↔ Claude Code/Claude Design Integration: Board-Bilder als automatische Style-Vorlage"
projekt: "Pinterest MCP"
datum: 2026-06-21
ausgeloest: /scout
---

## Kontext

Greenfield-Projekt (leerer Ordner, kein Git). Ziel: User pflegen ein Pinterest-Board als
Moodboard; Claude Code soll dieses Board **automatisch lesen, die Bilder analysieren und
daraus eine wiederverwendbare Style-Vorlage** (Design-Tokens/Brief) ableiten, an der es sich
beim Bauen orientiert. Plausibler nächster Schritt: ein **lokaler MCP-Server**, der Board-Pins
holt + die Bilder an Claude übergibt, plus eine **Skill**, die die Style-Ableitung kapselt.

> **„Claude Design" ist kein Produkt.** Gemeint ist Claudes Frontend-/Design-Fähigkeit — offiziell
> abgebildet durch das Anthropic-Plugin **`frontend-design`** (SKILL.md) + das Cookbook
> *„Prompting for frontend aesthetics"* (12.11.2025). Genau das ist der „Claude-Design"-Teil.

---

## Funde

### A) Pinterest-MCP-Server (GitHub) — fast alle brandneu, write-fokussiert, 0 Sterne

| Tool / Repo | Was es ist | Reife | Verdikt |
|---|---|---|---|
| **HusamAri/pinterest-mcp** | Read-only MCP für Claude Code: `list_boards`, `list_board_pins`, `get_pin` (offizielle API v5, OAuth, Token-Refresh, `~/.pinterest-mcp/tokens.json`). | ⭐0 · JS · 2026-05 | **Referenz (bestes Vorbild für Auth/Plumbing)** |
| **what-name/pinterest-mcp** | Full-coverage v5, gehostet auf Cloudflare Workers, **Per-User-OAuth** via `claude mcp add --transport http`. | ⭐0 · TS · 2026-03 | **Referenz (HTTP+OAuth-Muster)** |
| **salshwauva/pinterest-mcp** | TS, voller Read/Write inkl. `list_board_pins`, `list_board_section_pins`, OAuth-Auto-Refresh. Sauberes README. | ⭐0 · TS · 2026-05 | **Referenz (TS-Struktur)** |
| **mks044/pinterest-mcp** | „Für Claude Code", Python. Nur 3 Tools: `pinterest_search`, `pinterest_download`, `pinterest_board(url, limit)` — nimmt **Board-URL** (Scraping-Pfad, keine OAuth). | ⭐0 · Py · 2026-03 | Referenz (URL/Scraping-Variante) |
| clugtu / Fydel-Tools / collactivelabs / CDataSoftware | Generische v5-Wrapper (Pins erstellen, Boards, Analytics). collactivelabs älter (Node v14). | ⭐0–9 | ignorieren (write-lastig) |

**Keiner** dieser Server macht den Style-Schritt — sie liefern rohe Pin-Daten und hören dort auf.

### B) Nächster Nachbar konzeptionell — aber falsche Richtung

| Tool / Repo | Was es ist | Reife | Verdikt |
|---|---|---|---|
| **Dragon-hearted/MoodBoarder** | CLI (TS/Bun), ruft lokale `claude`-CLI für **Vision-Analyse**: extrahiert „visual DNA" (subject, mood, lighting, composition, **5-Hex-Palette**, 3 Dominantfarben, style, era, texture); bei Videos **Keyframe-Voting per Frequenz/Mode**. Dann: synthetisiert Pinterest-**Such**-Keywords → **scrapet** Pinterest (Playwright, eingeloggt, `/originals/`-Upgrade) → baut Deliverable-Ordner. | ⭐0 · TS · 2026-06 | **Referenz (Extraktions-Schema + Multi-Frame-Aggregation) — aber Gegenrichtung** |

MoodBoarder geht **Referenzbild → mehr Pinterest-Bilder** (baut Moodboards). Du willst die
**Umkehrung**: **Board → Style für Claude Code**. Seine „visual DNA"-Extraktion (Palette,
Mood, Voting über mehrere Bilder) ist trotzdem die beste konkrete Vorlage fürs Extraktions-Schema.
Achtung: nutzt **Scraping**, nicht die offizielle API (ToS-Risiko).

### C) Relevante Docs (verifiziert)

| Quelle | Kernpunkt |
|---|---|
| **Pinterest API v5** (OpenAPI-Spec) | `GET /v5/boards` → `GET /v5/boards/{id}/pins` liefert Pins **inkl. `media.images`** (kein Pin-Detail-Nachladen nötig). Bild-URLs auf `i.pinimg.com` in `150x150 / 400x300 / 600x / 1200x` — **`1200x` = Maximum** des dokumentierten Schemas. |
| **Pinterest Auth/Tiers** | OAuth2 Authorization-Code, Scopes `boards:read`+`pins:read`. **Trial reicht fürs eigene Konto; andere User anbinden → Standard Access mit Pflicht-Video-Review** (zeigt kompletten OAuth-Flow). Das ist die eigentliche Hürde. Access-Token 30 Tage, Continuous-Refresh-Token 60 Tage (rotieren). |
| **Rate Limits** | Lese-Endpoints = `org_read`: **Trial 1.000 Req/Tag/App**, Standard 1.000 Req/Min/User. `page_size=100` + `bookmark`-Pagination. |
| **MCP in Claude Code** | **stdio**-Transport für lokalen Server; `claude mcp add … -- node …` bzw. `.mcp.json` (Project-Scope). **Zentral:** ein Tool gibt Bilder als Content-Block `{ type:"image", data:<base64 ohne data:-Präfix>, mimeType }` zurück → Claude „sieht" sie im Vision-Input. Achtung `MAX_MCP_OUTPUT_TOKENS` (Default 25k) — gilt für Bild-Output. |
| **Claude Code Skills** | `SKILL.md` mit `name`+`description`, Progressive Disclosure (nur Description im Kontext, Body lädt bei Invoke). Auto-Load, wenn Description auf „Pinterest/Board/Style/Moodboard" matcht. |
| **Claude Vision** | Bild **vor** Text, mehrere Bilder mit `Image 1:`/`Image 2:` nummerieren, Rolle/Schema in System-Prompt. Opus 4.8: ≤**2576 px** lange Kante / ≤4784 visual-tokens; max **100 Bilder**/Request (200k-Modelle), ≤10 MB/Bild, ≤32 MB/Request. Vorher resizen. |
| **Structured Outputs** (14.11.2025) | **Constrained decoding** erzwingt valides JSON-Schema (statt Prompt-Hoffnung), Temp 0–0.1. GA u.a. Opus 4.8. Garantiert *valides*, nicht *korrektes* JSON. |
| **DTCG (W3C Design Tokens)** | Seit 28.10.2025 **erste stabile Version (2025.10)**. Token = `{ "$value", "$type", "$description" }`, Composite-Typen `typography/shadow/border/gradient`, Aliase `{color.primary}`. **Style Dictionary** generiert daraus CSS/iOS/Android. → Zielformat des extrahierten Styles. |

---

## Empfehlung

### Architektur (drei Bausteine)

1. **MCP-Server (stdio, lokal)** — `get_board_style` / `get_board_images`:
   `GET /v5/boards/{id}/pins` (page_size=100, bookmark) → `media.images['1200x'].url` je Pin →
   Bilder **herunterladen, auf ≤2576 px resizen** → als `{type:"image",data:base64,mimeType}`-
   Content-Blocks zurückgeben (vorher nummeriert). **Plumbing von `HusamAri` übernehmen**
   (OAuth + Token-Refresh), TS-Struktur ggf. von `salshwauva`.
2. **Skill `board-style-extractor`** (`.claude/skills/…/SKILL.md`) — Workflow: MCP-Tool aufrufen
   → alle Board-Bilder **gemeinsam** analysieren → **aggregierten** Style (Mehrheits-Farben,
   `dominance`-Felder, Ausreißer separat) → als **DTCG-`tokens.json` + kurzer Brief** speichern.
   Extraktions-Dimensionen am `frontend-design`-Skill + MoodBoarders „visual DNA" orientieren.
3. **Persistenz** — `tokens.json` + Brief in `.claude/`/`CLAUDE.md` ablegen; Claude Code liest
   sie zur Laufzeit als Style-Vorlage (Token-Update propagiert ohne Prompt-Änderung). Optional
   **Style Dictionary** → echtes CSS.

### Übernehmen / meiden

- **Übernehmen:** `HusamAri` (Auth/Refresh/Read-Tools), `salshwauva` (TS-Layout), MoodBoarders
  Extraktions-Schema + Multi-Bild-Voting, **DTCG** als Token-Format, **Structured Outputs** für
  stabilen JSON-Output.
- **Meiden:** Scraping-Pfad (MoodBoarder/mks044) — ToS-Risiko, fragil; nur als Fallback denken.
  Write/Analytics-Tools der Full-Wrapper (Scope-Overkill für deinen Read-Use-Case).

### Strategische Hürde (vorab klären)

Die Technik ist gelöst — **die echte Hürde ist organisatorisch**: Sobald **andere** (die WG-
Mitbewohnerinnen) ihre Boards anbinden sollen, braucht die App **Standard Access mit Video-
Review**. Für „nur mein eigenes Konto" reicht **Trial** sofort. **Zero-Setup-Fallback** für
schnellen Prototyp: offizieller Board-**`.rss`**-Feed (`…/<user>/<board>.rss`, letzte ~20 Pins,
auch fremde öffentliche Boards) — gut, um den Style-Loop zu testen, **bevor** man OAuth/Review baut.

### Konkreter nächster Schritt

**Prototyp ohne API-Hürde:** Board-`.rss` → Bilder ziehen → manuell an Claude Code geben →
`board-style-extractor`-Skill bauen, die einen DTCG-`tokens.json` ausgibt. Wenn der **Style-Loop
überzeugt**, erst dann den MCP-Server mit offizieller OAuth-Anbindung (`HusamAri` als Vorlage)
bauen. So validierst du den wertvollen Teil (Bild→Style) vor dem teuren Teil (App-Review).

---

## Quellen

**GitHub-Repos**
- https://github.com/HusamAri/pinterest-mcp · https://github.com/salshwauva/pinterest-mcp
- https://github.com/what-name/pinterest-mcp · https://github.com/mks044/pinterest-mcp
- https://github.com/Dragon-hearted/MoodBoarder · https://github.com/clugtu/pinterest-mcp

**Pinterest API**
- https://developers.pinterest.com/docs/api/v5/ · OpenAPI: https://github.com/pinterest/api-description
- Tiers: https://developers.pinterest.com/docs/key-concepts/access-tiers/
- Auth: https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/
- Rate Limits: https://developers.pinterest.com/docs/reference/rate-limits/

**Claude Code / Anthropic**
- MCP: https://code.claude.com/docs/en/mcp · Skills: https://code.claude.com/docs/en/skills
- Vision: https://platform.claude.com/docs/en/build-with-claude/vision
- Structured Outputs: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
- Frontend-Aesthetics-Cookbook: https://platform.claude.com/cookbook/coding-prompting-for-frontend-aesthetics
- frontend-design SKILL.md: https://github.com/anthropics/claude-code/blob/main/plugins/frontend-design/skills/frontend-design/SKILL.md

**Design Tokens**
- DTCG-Spec 2025.10: https://www.designtokens.org/tr/drafts/format/ · Style Dictionary: https://styledictionary.com/info/dtcg/

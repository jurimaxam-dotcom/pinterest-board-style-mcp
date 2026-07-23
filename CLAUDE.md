# Pinterest MCP

MCP-Server, der ein Pinterest-Board in wiederverwendbare Design-Artefakte
übersetzt: W3C-DTCG-Design-Tokens (`<slug>.tokens.json`) plus menschenlesbarer
Style-Brief (`<slug>.style.md`), abgelegt unter `examples/`. Python (stdlib),
Server-Definition in `.mcp.json` (`board-style` → `scripts/mcp_server.py`).

## Gate (grün/rot)

```bash
./test.sh
```

## Bausteine

- `scripts/mcp_server.py` — stdio-MCP-Server (Tool-Definitionen)
- `.claude/skills/board-style-extractor` — Skill: Board-Bilder gesamthaft
  analysieren (Vision) und Tokens + Brief erzeugen
- Cache unter `~/.cache/pinterest-board-style/`

## Konventionen

- Tokens strikt W3C-DTCG-Format; Brief beschreibt Palette, Typo, Spacing,
  Bildsprache in Prosa.
- Keine Pinterest-Credentials im Repo.

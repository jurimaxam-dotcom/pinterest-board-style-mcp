# Projektregeln — Pinterest MCP

## Nach MCP-/Claude-Desktop-relevanten Änderungen

- Nach Änderungen an `scripts/mcp_server.py`, `.mcp.json`, Claude-Desktop-Tool-Verträgen oder Exportpfaden nicht nur Code ändern, sondern den Nutzbarkeitszustand prüfen.
- Immer mindestens `./test.sh` ausführen und das Ergebnis berichten.
- Prüfen, ob `~/Library/Application Support/Claude/claude_desktop_config.json` dieses Repo bzw. den geänderten MCP-Server referenziert.
- Wenn Claude Desktop die Änderung erst nach einem Neustart sieht, das klar sagen und den Neustart selbst anstoßen, sofern Jay die notwendige Approval-Freigabe gibt. Nicht bei Jay abladen.
- Nach Exportpfad-Änderungen zusätzlich sagen, welcher Pfad für Claude Desktop erwartet wird, z. B. `/Users/tom/Documents/Claude/<slug>/style-skill/`.
- Bei Bild-Einbettungsfragen nicht auf `/Users/tom/...`-Host-Pfade als Lösung verweisen. Prüfen, dass `get_board_style` einen `EMBEDDABLE_IMAGE_SOURCES`-Block liefert, der auf `embeddable-images.json` im Exportpaket zeigt. Die großen `data:image/jpeg;base64,...`-Werte gehören in diese Manifest-Datei, nicht direkt ins Tool-Result, sonst greift Claudes 1MB-Limit.

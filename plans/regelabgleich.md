# Regelabgleich (Setup-Audit 22.10.2026)

Herkunft: globales Doku-/Regel-Audit vom 22.10.2026 (`~/.claude/docs/evidence/setup-check-2026-10-22.md`, Abschnitt 2.4).
Jay: „die ganze Dokumentation und Regeln und CLAUDE.md-Files durchchecken, ob es da Widersprüche gibt". Nur Regeldateien,
kein Code.

- [ ] `CLAUDE.md` lädt `AGENTS.md` nicht: Claude liest AGENTS.md nur, wenn keine eigene CLAUDE.md da ist
      (`~/.claude/docs/ablage-nach-ladezeitpunkt.md:19–21`). Claude sieht deshalb test.sh-Pflicht, Desktop-Config-Prüfung
      und den embeddable-images-Vertrag (`AGENTS.md:3–10`) nie; Codex sieht die CLAUDE.md nie.
      Fix: Inhalt der CLAUDE.md nach AGENTS.md ziehen, CLAUDE.md = Stub `@AGENTS.md` (Muster `~/.claude/docs/regelbasis.md`).
- [ ] `AGENTS.md:7–8` „Neustart, sofern Jay die Approval-Freigabe gibt" streichen — Dauererlaubnis für Apps
      beenden/starten (`~/.claude/CLAUDE.md:16–17`). Der zu prüfende Server `board-style` steht derzeit nicht in
      `claude_desktop_config.json` — klären, ob er registriert werden soll.

Nächster Schritt: beide Haken in einem Commit, danach den in AGENTS.md genannten Test laufen lassen.

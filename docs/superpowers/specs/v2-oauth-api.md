# Spec: v2 — Offizielle Pinterest API v5 + lokales OAuth

**Datum:** 2026-06-21 · **Status:** Entwurf, wartet auf Freigabe · **Scope:** project(Pinterest MCP)
**Voraussetzung:** v1 (RSS-Fetcher + Skill) validiert (2 PoC-Läufe grün).

## Ziel / Abgrenzung

v2 ersetzt den RSS-Zugang durch die **offizielle Pinterest-API v5** für das **eigene Konto** —
**Trial-Tier, kein Video-Review, kein Hosting**. Jeder Cloner legt seine **eigene** kostenlose
Pinterest-App an; OAuth läuft **lokal**.

**Was RSS nicht kann, API schon:**
- volle Board-Größe (nicht nur die letzten ~25 Pins),
- **eigene private** Boards (RSS nur öffentliche),
- strukturierte `media.images` inkl. `1200x` + `dominant_color` (statt fragiles HTML-Parsing).

**Nicht-Ziele (YAGNI):** MCP-Server (v3) · Multi-User / Standard-Access / Video-Review · Hosting ·
Write-/Analytics-Scopes · Webhooks · Refresh-Daemon · Style-Dictionary-CSS.

## Kerninvariante (Architektur)

Die saubere Trennung **bleibt**: Auth/IO ist Plumbing, die **Skill (Analyse) bleibt 1:1 unverändert**.
Stabiler Vertrag = `.cache/<slug>/NN.jpg` + `manifest.json`. Die Skill kennt **nur** diesen Vertrag
und merkt nicht, ob die Bilder via RSS oder API kamen.

```
                ┌─ pinterest_auth.py (NEU) ──► .pinterest-tokens.json (0600, gitignored)
                │     login · get_access_token · refresh
fetch_board.py ─┤
  --source api ─┘──► v5 /boards, /boards/{id}/pins ──┐
  --source rss ─────► RSS (wie v1) ──────────────────┤
                                                      ▼
                          gemeinsamer Code: download_images() + manifest.json
                                                      ▼
                       .cache/<slug>/  ──►  Skill board-style-extractor (UNVERÄNDERT)
```

---

## 1. OAuth-Flow (lokal, Trial, kein Webhook/Review)

Confidential Client (v5 kennt **kein PKCE** → `client_secret` nötig), läuft ausschließlich lokal.

**Login-Schritte** — `python3 scripts/pinterest_auth.py login`:
1. Startet lokalen Loopback-Server `http://127.0.0.1:8585/callback` (stdlib `http.server`).
2. Öffnet Browser (`webbrowser`) auf die Authorize-URL:
   `https://www.pinterest.com/oauth/?response_type=code&client_id=$ID&redirect_uri=http://127.0.0.1:8585/callback&scope=boards:read,pins:read&state=$RANDOM`
3. Nutzer bestätigt → Redirect auf `…/callback?code=…&state=…`. Server prüft `state` (CSRF), greift `code`.
4. **Token-Exchange:** `POST https://api.pinterest.com/v5/oauth/token`
   - Header `Authorization: Basic base64(client_id:client_secret)`, `Content-Type: application/x-www-form-urlencoded`
   - Body `grant_type=authorization_code&code=$CODE&redirect_uri=http://127.0.0.1:8585/callback&continuous_refresh=true`
     — **`continuous_refresh=true` ist Pflicht** fuer den 60-Tage-Rotations-Refresh-Token.
   - Antwort: `access_token` (Prefix `pina`, `expires_in` 2592000 = 30 d), `refresh_token` (Prefix `pinr`, `refresh_token_expires_in` 5184000 = 60 d, `refresh_token_expires_at` absolut, **rotiert bei jedem Refresh**), `token_type: bearer`, `scope`.
5. Schreibt `.pinterest-tokens.json` (Perms **0600**).

**Token-Persistenz & Refresh:**
- Datei `.pinterest-tokens.json` (Repo-Root, bereits in `.gitignore`, zusätzlich `chmod 600`).
  Inhalt: `access_token`, `refresh_token`, `access_expires_at` (absolut), `refresh_expires_at`, `scope`, `obtained_at`.
- `get_access_token()`: lädt Datei → wenn access < ~120 s gültig: Refresh (`grant_type=refresh_token&refresh_token=…`),
  **rotierten** refresh_token zurückschreiben → wenn refresh abgelaufen: klarer Fehler „bitte erneut `login`".
- **Secrets:** `PINTEREST_CLIENT_ID` / `PINTEREST_CLIENT_SECRET` aus Umgebung bzw. `.env` (gitignored). Nie im Code, nie committet.

**Sicherheit:** `state`-CSRF · Loopback-only (kein öffentlicher Endpoint) · Token-Datei 0600 ·
`.env` + `.pinterest-tokens.json` + `.pinterest-mcp/` sind bereits gitignored · `client_secret` lebt nur lokal.

---

## 2. API-Aufrufe (v5)

Basis `https://api.pinterest.com/v5`, Header `Authorization: Bearer $ACCESS_TOKEN`.

**a) Board-ID auflösen** (URL liefert nur user/slug, API braucht `board_id`):
`GET /v5/boards?page_size=100[&bookmark=…]` → `items[].{id,name}`; Slug ↔ name normalisiert matchen.
Bei mehreren/unklaren Treffern: Board-Liste ausgeben + `--board-id` verlangen.

**b) Pins des Boards:**
`GET /v5/boards/{board_id}/pins?page_size=100[&bookmark=…]` → `items[]` (PinRead). Pro Pin:
- `media.images["1200x"].url` (Fallback: größte vorhandene Variante 736x/600x/…),
- Bonus: `id`, `title`, `description`, `link`, **`dominant_color`** (Pinterest liefert Dominantfarbe → optionales Analyse-Signal),
- Pagination via `bookmark` bis erschöpft → **volle** Board-Größe.

**c) Bild-Download** wie v1 (1200x ≤ 2576 px ⇒ kein Resize).

**Rate Limits:** Trial 1.000 Req/Tag/App; ein Board = 1 Boards-Call + ⌈pins/100⌉ Pins-Calls → unkritisch.

---

## 3. Integration (Trennung wahren)

- **NEU `scripts/pinterest_auth.py`** — nur Auth/Token (stdlib `http.server`+`webbrowser`+`urllib`). Kein Bild-Handling, keine Analyse.
- **ERWEITERT `scripts/fetch_board.py`** — neues Flag `--source {auto,rss,api}` (Default `auto`: API wenn Tokens da, sonst RSS).
  Der API-Zweig importiert `pinterest_auth.get_access_token()`, holt Pins, mappt auf **dieselbe** interne
  `items`-Struktur (`{pin_title, pin_link, image_url_raw, [dominant_color]}`) und ruft **denselben**
  `download_images()` + Manifest-Writer auf wie der RSS-Zweig.
- **`manifest.json`** gewinnt `source: "api"|"rss"` + optional `dominant_color` je Bild. Bestehende Felder unverändert → **Skill bleibt 1:1**.
- **Skill `board-style-extractor`:** unverändert. (Optionale Mini-Iteration *später*: vorhandene `dominant_color` als Hinweis in die Farbaggregation geben — nicht v2-Pflicht.)
- Gemeinsamer Code bleibt vorerst in `fetch_board.py` (download+manifest sind schon dort); wird die Datei zu groß → `_board_cache.py` extrahieren (Refactor-Option, kein Muss).

---

## Build-Schritt 0 — gegen offizielle Doku verifiziert (2026-06-21 · Context7 `/websites/developers_pinterest` + OpenAPI `v5/openapi.yaml`)

- **Authorize-URL bestaetigt:** `https://www.pinterest.com/oauth/?client_id=…&redirect_uri=…&response_type=code&scope=boards:read,pins:read&state=…` (Scopes **komma**-separiert).
- **Token-Endpoint bestaetigt:** `POST https://api.pinterest.com/v5/oauth/token`, `Authorization: Basic b64(client_id:client_secret)`, `Content-Type: application/x-www-form-urlencoded`.
- **Korrektur `continuous_refresh=true`:** beim `authorization_code`-Exchange Pflicht → 60-Tage-**Rotations**-Refresh-Token; jede Refresh-Antwort enthaelt einen NEUEN `refresh_token` (→ zurueckschreiben).
- **Token-Antwort bestaetigt:** `access_token` (`pina…`, 30 d), `refresh_token` (`pinr…`, 60 d, `refresh_token_expires_at` absolut), `token_type: bearer`, `scope`.
- **Refresh bestaetigt:** `grant_type=refresh_token&refresh_token=…[&scope=boards:read]`.
- **`media.images`-Keys bestaetigt:** `150x150`, `400x300`, `600x`, **`1200x`** — je `{width,height,url}` (i.pinimg). `1200x` = groesste, nicht hochskaliert (reale Aufloesung ≤ 1200).
- **`dominant_color`** je Pin bestaetigt (kann `null` sein) → optionales Analyse-Signal (nur ins Manifest, s. Entscheidung 4).
- **Pagination:** `bookmark` (Query-Param) + `items[]`; **page_size Default 25, max 100** → explizit `page_size=100`.
- **Media-Guard:** nur Pins mit `media.media_type == "image"` und vorhandenem `images["1200x"]`; Videos/Mehrfach-Medien ueberspringen (oder groesste vorhandene Variante).

## Build-Reihenfolge

0. **Verifikation zuerst (Context7/Pinterest-Doku):** exakte v5-OAuth-Param-/Endpoint-Namen gegen aktuelle Doku prüfen (analog zur RSS-Recon — erst Fakten, dann Code).
1. **Dev-App anlegen** (manuell, dokumentiert): developers.pinterest.com → App → client_id/secret, redirect_uri `http://127.0.0.1:8585/callback`, scopes `boards:read`+`pins:read`, Trial.
2. `pinterest_auth.py` (login + get_access_token + refresh) → einmal `login` testen (eigener Account).
3. `fetch_board.py --source api` → eigenes Board holen; **Manifest-Parität** zum RSS-Pfad prüfen.
4. Skill **unverändert** über den API-Cache laufen lassen (Regressionstest: gleiche Pipeline, gleiches Output-Format).
5. README/Docs: „Eigene Pinterest-App in 5 Schritten" + `.env.example`.

## Sicherheits-/Privacy-Checkliste

- `.env` (Secrets) + `.pinterest-tokens.json` (Tokens) gitignored ✓ (vorhanden); zusätzlich `chmod 600`.
- `.env.example` mit Platzhaltern committen (kein echter Secret).
- Kein Token/Secret in Logs (Auth-Modul redacted).
- `state`-CSRF, Loopback-only, keine Webhooks.

## Entscheidungen (freigegeben 2026-06-21 — alle 5 Empfehlungen übernommen)

1. **Token-Store-Ort:** Repo-lokal `.pinterest-tokens.json` *(Empfehlung — einfach, schon gitignored)* vs. `~/.config/pinterest-board-style/tokens.json` (kann gar nicht versehentlich committet werden, via `--token-store`).
2. **Redirect-Port:** fix `8585` *(Empfehlung — muss in App-Registrierung eingetragen werden)* vs. dynamisch; via Env überschreibbar.
3. **`--source auto`-Default mit RSS-Fallback behalten?** *(Empfehlung: ja — öffentliche Boards bleiben ohne Login schnell testbar.)*
4. **`dominant_color`:** in v2 nur ins Manifest schreiben (ungenutzt), Skill-Integration als separate Mini-Iteration — ok?
5. **stdlib-only bestätigt?** Auth-Loopback via `http.server`+`webbrowser`+`urllib` = weiterhin **kein** pip-Install.

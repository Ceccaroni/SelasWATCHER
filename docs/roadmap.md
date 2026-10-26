# Roadmap — SelasWATCHER

> Reihenfolge, nicht Kalender. Schätzung in Claude-Code-Sessions. SoT für Architektur: `docs/konzept.md`.

## Phase 0 — Scaffolding ✅ (S001)
Repo-Grundgerüst nach Selas-Konventionen. Konzept + offene Entscheidungen dokumentiert.

## Phase 1 — Entscheid & Verifikation ✅ (S001)
- Entscheide getroffen (`docs/konzept.md` §6: Menüleiste, Python, Quellen, 5 Min/Schwere).
- Feed-URLs real verifiziert (`curl`, HTTP 200 + Content-Type → `docs/konzept.md` §5). Erkenntnis: 7× RSS/Atom, 3× JSON-API, BACS ohne Feed (→ HTML, Phase 4).
- Offen: ADR zum Architektur-Entscheid (`adr-generator`).

## Phase 2 — MVP Kern ✅ (S001, reviewt)
- **Fetcher mit Typ-Adaptern:** `rss`/`atom` via `feedparser`; `json` (CISA KEV, NVD, GitHub) je eigener kleiner Mapper auf gemeinsames internes Eintrags-Format. Timeout-/Fehlertoleranz pro Quelle (Regel #3).
- Dedup über lokale State-Datei (ID-Strategie je Quelle aus §5 — Achtung CERT-Bund WID-ID, BleepingComputer Item-pubDate).
- Relevanz-/Schwere-Scoring (Stichwort-Heuristik + Technologie-Watchlist), Schwellen aus Config.
- Native macOS-Notification bei Treffer (schwereabhängig laut/leise).
- **Smoke-Test:** künstlichen «Treffer» einspeisen → Notification erscheint.

## Phase 3 — Menüleiste & Betrieb ✅ (S001, reviewt + Smoke-Test)
- Menüleisten-App (`rumps`, `selaswatcher/app.py`): Selas-Symbol-Icon (Template, tönt hell/dunkel), rotes Icon + Zähler bei ungelesenen HIGH, Liste der letzten ~30 Treffer, Klick öffnet Artikel; „Jetzt prüfen"/„Als gelesen"/„Konfiguration öffnen"/„Beenden". Worker-Thread pollt, Main-Thread aktualisiert UI.
- Config-Datei (Quellen/Watchlist/Intervall) — eine Quelle = eine Zeile (`config.toml`, gitignored).
- Autostart via LaunchAgent (`launchagent/` + `scripts/install-autostart.sh`/`uninstall-autostart.sh`).
- `README.md` §Betrieb: Einrichten/Start/Autostart/Config/Log dokumentiert.

## Phase 4 — Feinschliff (nach Bedarf)
- **BACS HTML-Polling** (eigenes Ticket): schonendes Scraping der Vorfall-Liste, da kein Feed.
- **CISA Advisories** alternativen Fetch-Weg prüfen (RSS `all.xml` ist WAF-geblockt/403).
- **Härtung:** fehlgeschlagene HIGH-Notification nicht still als „gesehen" verbuchen (Retry/Alarm); `seen`-Liste deckeln/prunen (wächst sonst unbegrenzt); NVD/GitHub-Pagination falls Baseline-Fenster >1 Seite nötig.
- Fehlalarm-Tuning nach echtem Betrieb (Regel #2).
- Optional: zusätzliche Quellen (The Hacker News, Netzwoche …), NVD-API-Key via Env, optionaler E-Mail-/Slack-Fallback.

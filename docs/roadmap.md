# Roadmap — SelasWATCHER

> Reihenfolge, nicht Kalender. Schätzung in Claude-Code-Sessions. SoT für Architektur: `docs/konzept.md`.

## Phase 0 — Scaffolding ✅ (S001)
Repo-Grundgerüst nach Selas-Konventionen. Konzept + offene Entscheidungen dokumentiert.

## Phase 1 — Entscheid & Verifikation ✅ (S001)
- Entscheide getroffen (`docs/konzept.md` §6: Menüleiste, Python, Quellen, 5 Min/Schwere).
- Feed-URLs real verifiziert (`curl`, HTTP 200 + Content-Type → `docs/konzept.md` §5). Erkenntnis: 7× RSS/Atom, 3× JSON-API, BACS ohne Feed (→ HTML, Phase 4).
- Offen: ADR zum Architektur-Entscheid (`adr-generator`).

## Phase 2 — MVP Kern (~1–2 Sessions)
- **Fetcher mit Typ-Adaptern:** `rss`/`atom` via `feedparser`; `json` (CISA KEV, NVD, GitHub) je eigener kleiner Mapper auf gemeinsames internes Eintrags-Format. Timeout-/Fehlertoleranz pro Quelle (Regel #3).
- Dedup über lokale State-Datei (ID-Strategie je Quelle aus §5 — Achtung CERT-Bund WID-ID, BleepingComputer Item-pubDate).
- Relevanz-/Schwere-Scoring (Stichwort-Heuristik + Technologie-Watchlist), Schwellen aus Config.
- Native macOS-Notification bei Treffer (schwereabhängig laut/leise).
- **Smoke-Test:** künstlichen «Treffer» einspeisen → Notification erscheint.

## Phase 3 — Menüleiste & Betrieb (~1 Session)
- Menüleisten-App (`rumps`): Status-Icon, Badge bei neuem Treffer, Liste der letzten Treffer, Klick öffnet Artikel.
- Config-Datei (Quellen, Watchlist, Intervall, Schwellen) — eine Quelle = eine Zeile.
- Autostart via LaunchAgent; Verhalten bei Netzausfall/Neustart geprüft.
- `README.md`: Start/Stop/Autostart/Deinstallation dokumentieren.

## Phase 4 — Feinschliff (nach Bedarf)
- **BACS HTML-Polling** (eigenes Ticket): schonendes Scraping der Vorfall-Liste, da kein Feed.
- Fehlalarm-Tuning nach echtem Betrieb (Regel #2).
- Optional: zusätzliche Quellen (The Hacker News, Netzwoche …), NVD-API-Key via Env, optionaler E-Mail-/Slack-Fallback.

# Archiv — SelasWATCHER

> Ältere Session-Einträge, Stand-Snapshots, überholte Entscheide. Beim Session-Start NICHT laden — nur bei Bedarf greppen.

## S001 — 2026-10-26 — Scaffolding + Architektur + MVP-Kern
- Repo-Grundgerüst nach Selas-Konventionen; Architektur mit Adrian bestätigt (`docs/konzept.md` §6, ADR `docs/adr/0001`).
- Feed-URLs real verifiziert (`curl`): 7 RSS/Atom + 3 JSON-API; BACS ohne Feed→Phase 4; CISA-Advisories-RSS 403/WAF→deaktiviert.
- MVP-Kern gebaut (builder/Opus) + reviewt: `selaswatcher/` (fetch/dedup/score/notify), CLI poll/watch/test-notify. End-to-End real belegt (cert-bund-wid → HIGH-Notification). [[TICKET-001]]+[[TICKET-002]] erledigt.
- MVP gepusht (github.com/Ceccaroni/SelasWATCHER). Phase 3 [[TICKET-003]] gebaut (builder/Opus) + reviewt + Smoke-Test: Menüleisten-App (`app.py`, rumps) mit Selas-Symbol-Icon (Template + roter Alarm/Zähler), Recent-Liste, Worker/Main-Thread-Trennung; LaunchAgent + install/uninstall-Skripte; README-Betrieb; Icons aus Selas-Marke in `assets/icons/`.
- **LIVE:** Phase 3 gepusht; Autostart installiert (LaunchAgent). Läuft dauerhaft in der Menüleiste.
- **Nachjustierung (Realbetrieb):** Menü-Feedback („Jetzt prüfen"/Status) + Testalarm; Alarm-Reset nur per „Alle als gelesen"; klickbare Banner via terminal-notifier (+Fallback osascript, Install-Skript). **52-Alarm-Flut behoben:** nur HIGH bannert, Vuln-DBs nur bei Stack-Treffer, Watchlist = echter Stack ohne node/php, NVD aus. **Inventar-Matching** (`inventory.py`): GitHub-Advisories paketgenau gegen `package-lock.json` des Selas-Repos (836 Pakete) → HIGH nur bei genutztem Paket (Treffer real: undici/happy-dom/nodemailer/next/…). PHP-Krisen weiterhin via Kritisch-Keywords.
- **Nachjustierung 2 (Realbetrieb):** „Alle als gelesen" leert jetzt zusätzlich die Meldungsliste (`app.py` `_on_mark_all_read`) — Menü war durch stumme MEDIUM-`[UPDATE]`-Flut (CERT-Bund) unübersichtlich; Dedup-State (`seen.json`) bleibt bewusst unberührt. Node-Brotli-Alarm (CVE-2026-111497) bestätigt abgedeckt; Watcher ist versionsblind (Dedup per WID-ID, kein Versionsabgleich) → der Fix im Selas-Repo (Node 22.23.4, extern) muss ihm nicht mitgeteilt werden.
- **Nachjustierung 3 (Realbetrieb):** MEDIUM-Flut in der Menüliste eingedämmt (`app.py` `_prune_recent`) — statt pauschal 30 gemischt jetzt **alle HIGH + die letzten 15 nicht-HIGH** (Konstante `MAX_RECENT_MEDIUM`); HIGH können nicht mehr aus dem Menü gedrängt werden. Logik per Mini-Sim verifiziert (Reihenfolge erhalten, alle HIGH behalten).
- Backlog: [[TICKET-004]] Phase 4 (BACS HTML, Härtung, py2app-Notifications).

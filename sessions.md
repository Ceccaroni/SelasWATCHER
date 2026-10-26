# Sessions — SelasWATCHER

> Max. ~3 kompakte Einträge. Ältestes beim neuen Eintrag im Volltext nach `archive.md`. Details ins Ticket-File.

## S001 — 2026-10-26 — Scaffolding + Architektur + MVP-Kern
- Repo-Grundgerüst nach Selas-Konventionen; Architektur mit Adrian bestätigt (`docs/konzept.md` §6, ADR `docs/adr/0001`).
- Feed-URLs real verifiziert (`curl`): 7 RSS/Atom + 3 JSON-API; BACS ohne Feed→Phase 4; CISA-Advisories-RSS 403/WAF→deaktiviert.
- MVP-Kern gebaut (builder/Opus) + reviewt: `selaswatcher/` (fetch/dedup/score/notify), CLI poll/watch/test-notify. End-to-End real belegt (cert-bund-wid → HIGH-Notification). [[TICKET-001]]+[[TICKET-002]] erledigt.
- MVP gepusht (github.com/Ceccaroni/SelasWATCHER). Phase 3 [[TICKET-003]] gebaut (builder/Opus) + reviewt + Smoke-Test: Menüleisten-App (`app.py`, rumps) mit Selas-Symbol-Icon (Template + roter Alarm/Zähler), Recent-Liste, Worker/Main-Thread-Trennung; LaunchAgent + install/uninstall-Skripte; README-Betrieb; Icons aus Selas-Marke in `assets/icons/`.
- **LIVE:** Phase 3 gepusht; Autostart installiert (LaunchAgent, PID aktiv, pollt sauber). SelasWATCHER läuft dauerhaft in der Menüleiste. Backlog: [[TICKET-004]] Phase 4 (BACS HTML, Härtung, py2app-Notifications).

# Sessions — SelasWATCHER

> Max. ~3 kompakte Einträge. Ältestes beim neuen Eintrag im Volltext nach `archive.md`. Details ins Ticket-File.

## S001 — 2026-10-26 — Scaffolding + Architektur + MVP-Kern
- Repo-Grundgerüst nach Selas-Konventionen; Architektur mit Adrian bestätigt (`docs/konzept.md` §6, ADR `docs/adr/0001`).
- Feed-URLs real verifiziert (`curl`): 7 RSS/Atom + 3 JSON-API; BACS ohne Feed→Phase 4; CISA-Advisories-RSS 403/WAF→deaktiviert.
- MVP-Kern gebaut (builder/Opus) + reviewt: `selaswatcher/` (fetch/dedup/score/notify), CLI poll/watch/test-notify. End-to-End real belegt (cert-bund-wid → HIGH-Notification). [[TICKET-001]]+[[TICKET-002]] erledigt.
- Repo public gepusht (Scaffold): github.com/Ceccaroni/SelasWATCHER. **MVP committet, aber noch nicht gepusht** (wartet auf «push»).
- **Offen/nächstes:** TICKET-003 Phase 3 — Menüleisten-App + Autostart (LaunchAgent) + README-Betrieb. Erst damit läuft es dauerhaft.

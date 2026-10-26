# Tickets — DONE (abgeschlossen)

> Kurzbilanz pro abgeschlossenem Ticket. Beim Session-Start NICHT laden, nur bei Bedarf greppen.

- **TICKET-001 — Scaffolding + Architektur-Entscheid** (S001): Selas-konformes Grundgerüst; Architektur bestätigt (Menüleiste/Python/5-Min/Schwere); Feed-URLs verifiziert (7 RSS/Atom + 3 JSON, BACS→Phase 4, CISA-Advisories 403→aus); ADR `docs/adr/0001`.
- **TICKET-002 — MVP-Kern** (S001): `selaswatcher/` Fetcher (Typ-Adapter rss/atom/json) + Dedup (First-Run-Baseline, `[UPDATE]`-Erkennung) + Scoring (Watchlist=HIGH) + osascript-Notification; CLI poll/watch/test-notify. Reviewt (osascript-Injection/untrusted-input sauber), End-to-End real belegt. Phase-4-Härtung offen (→ TICKET-004).

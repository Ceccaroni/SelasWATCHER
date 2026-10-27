# Tickets — INDEX (offen)

> Nur OFFENE Tickets. Abgeschlossene → `DONE.md`. Board-Zeilen kurz halten, Details im Ticket-File.

## In Arbeit
- _(keine)_

## Backlog
- **TICKET-004** (Phase 4) — Härtung + fehlende Quellen. **Teil-erledigt:** Notify-Fail-Retry ✅ + `seen`-Cap ✅ (S002); CISA-Advisories reaktiviert ✅ (S003: `alerts.xml` + Wrapper-Filter + `always_high`); Wächter-fürs-Wächter ✅ (S003: Quelle-fällt-still-aus → Health-Alarm); BACS HTML-Polling ✅ (S004: Typ `html` + `_fetch_bacs`, `always_high`, Markup-Bruch → Health-Alarm); Fehlalarm-Tuning Breach-Lärm ✅ (S005: `datenleck`/`data breach`/`breach` HIGH→MEDIUM); Fehlalarm-Tuning Runde 2 ✅ (S006: CERT-Bund/BSI schwere-gegated via `Source.severity_tagged` — Stack-Treffer bannert nur bei `[hoch]`/`[kritisch]`; `ransomware` HIGH→MEDIUM, S005-„bleibt HIGH" aufgehoben); Fehlalarm-Tuning Runde 3 ✅ (S007: GitHub-Inventar-Treffer schwere-gegated — Banner nur bei GitHub `critical`/`high`, `moderate`/`low`→MEDIUM; killt die transitive npm-DoS/ReDoS-Flut). PHP-Loudness ✅ **geklärt** (S006): PHP2Shell feuert HIGH dreifach (CISA-Advisory `always_high` + News-Keywords) — zudem PHP bei Adrian deinstalliert, Gründungsfall-Garant steht. **Offen:** nur noch py2app für gebrandete Notifications. → `docs/roadmap.md` Phase 4.

## Erledigt → `DONE.md`
- [[TICKET-001]] Scaffolding + Architektur · [[TICKET-002]] MVP-Kern · [[TICKET-003]] Menüleiste + Autostart.

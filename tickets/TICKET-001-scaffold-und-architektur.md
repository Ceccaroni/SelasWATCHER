# TICKET-001 — Scaffolding + Architektur-Entscheid

**Status:** in Arbeit (Scaffolding erledigt, Entscheid offen)
**Erstellt:** 2026-10-26 (S001)

## Ziel
Repo-Grundgerüst nach Selas-Konventionen anlegen und die grundlegenden Architektur-Entscheidungen treffen, damit der MVP gebaut werden kann.

## Erledigt (S001)
- Grundgerüst angelegt: `CLAUDE.md`, `README.md`, `.gitignore`, `sessions.md`, `archive.md`, `.claude/rules/security.md`, `docs/{DOCS-INDEX,konzept,roadmap}.md`, `tickets/{INDEX,DONE}.md`.
- Produktidee, Pipeline, Quellen-Vorschläge und offene Entscheidungen dokumentiert → `docs/konzept.md`.
- Git-Repo initialisiert.

## Entscheide getroffen (Adrian, S001) → `docs/konzept.md` §6
1. Runtime-Form: **Menüleisten-App**.
2. Stack: **Python + `feedparser` + `rumps`**.
3. Quellen: drei fixe + **alle** Erweiterungen (CISA, BSI/CERT-Bund, heise Security, BleepingComputer, NVD/CVE, GitHub Advisory).
4. Takt: **5 Min**, laut nur bei hoher Schwere; Technologie-Watchlist = immer hohe Schwere.

## Feed-URLs verifiziert ✅ (S001, `curl` HTTP 200) → `docs/konzept.md` §5
- 7× RSS/Atom, 3× JSON-API (CISA KEV, NVD, GitHub Advisory), BACS ohne Feed → HTML-Polling Phase 4.
- Erkenntnis: Fetcher braucht Typ-Adapter (rss/json/html); Dedup-ID je Quelle unterschiedlich (CERT-Bund WID-ID, BleepingComputer Item-pubDate).

## Offen (danach)
- Architektur-Entscheid als ADR festhalten (`adr-generator`).
- Folge-Tickets TICKET-002 (MVP-Kern) / TICKET-003 (Menüleiste+Betrieb) schärfen.

## Definition of Done
Entscheide getroffen + dokumentiert ✅, Feed-URLs verifiziert ✅, ADR geschrieben ⬜, Folge-Tickets geschärft ⬜. Dann schliessen.

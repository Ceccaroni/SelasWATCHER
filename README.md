# SelasWATCHER

Kleines, eigenständiges **macOS-Frühwarn-Tool**. Überwacht Security-/IT-Quellen per RSS/Atom, erkennt potenzielle Bedrohungen und meldet sie **sofort** nativ auf dem Mac. Läuft unauffällig im Hintergrund (Autostart beim Login), rein lokal.

> Auslöser: eine Security-Krise früh und von selbst mitbekommen, nicht erst über Dritte.

## Status
**Phase 0 — Scaffolding.** Noch kein Code. Architektur-Entscheid offen → `docs/konzept.md` §6.

## Idee in einem Satz
Feeds pollen → Neues erkennen (Dedup) → nach Relevanz/Schwere bewerten → bei Treffer native macOS-Notification (schwereabhängig) + Eintrag in der Menüleisten-Liste.

## Geplante Quellen
`inside-it.ch`, BACS/NCSC (Aktuelle Vorfälle), `20min.ch/digital` — plus vorgeschlagene Erweiterungen (CISA, BSI/CERT-Bund, heise Security, BleepingComputer u. a.). Details & Verifikationsstand: `docs/konzept.md` §5.

## Dokumentation
- `docs/konzept.md` — Produkt, Architektur, Quellen, offene Entscheidungen (Source of Truth)
- `docs/roadmap.md` — Bau-Phasen
- `CLAUDE.md` — Arbeits-/Projektregeln
- `tickets/` — Aufgaben

## Betrieb (Start / Stop / Autostart)
_Wird dokumentiert, sobald der MVP steht (Phase 3)._

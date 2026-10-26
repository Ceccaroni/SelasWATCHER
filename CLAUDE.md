# CLAUDE.md — SelasWATCHER

> **Diese Datei wird zu Beginn JEDER Session gelesen.** Kompakt halten. Details liegen in den verlinkten Docs. Source-of-Truth-Matrix: `docs/DOCS-INDEX.md`.

## Einzeiler
SelasWATCHER — eigenständiges, kleines **macOS-Frühwarn-Tool**. Überwacht Security-/IT-Quellen per RSS/Atom, erkennt potenzielle Bedrohungen und meldet sie **SOFORT** nativ auf dem Mac. Läuft unauffällig im Hintergrund (Autostart beim Login). Rein lokal, nur für Adrian. Auslöser: die PHP-Sicherheitskrise (KW 43/2026), von der Adrian erst über Freunde erfuhr — das darf nie wieder passieren.

## Aktueller Stand

> Nur Ist-Zustand (kompakt). Verlauf → `sessions.md`/`archive.md` · Tickets → `tickets/INDEX.md`.

- **Phase 3 fertig & reviewt (S001, 2026-10-26).** Repo public: https://github.com/Ceccaroni/SelasWATCHER (Branch `master`). ADR: `docs/adr/0001`.
- **Menüleisten-App lauffähig:** `python -m selaswatcher.app` — Selas-Symbol als Template-Icon (tönt hell/dunkel), bei ungelesenen HIGH → rotes Icon + Zähler; Menü listet letzte ~30 Meldungen (Klick öffnet Artikel), „Jetzt prüfen"/„Als gelesen"/„Konfiguration öffnen"/„Beenden". Polling im Worker-Thread, UI-Updates im Main-Thread. Smoke-Test bestanden (startet sauber, Worker pollt, kein Crash).
- **Kern (CLI weiterhin):** `python -m selaswatcher {poll,watch,test-notify}`. Fetcher Typ-Adapter (7 RSS/Atom + JSON: CISA KEV, NVD, GitHub), Dedup+Baseline, Scoring (Watchlist=HIGH), osascript-Notifications. `cisa-advisories` deaktiviert (403/WAF). State `~/.selaswatcher/seen.json`.
- **Autostart:** LaunchAgent-Vorlage + `scripts/install-autostart.sh`/`uninstall-autostart.sh` — **erstellt, aber NICHT installiert** (Nutzer führt Install bewusst aus).
- **Offen:** Phase 3 lokal committet, **Push + Autostart-Installation warten auf Adrians Wort**. Phase-4-Backlog → TICKET-004 (`docs/roadmap.md`): BACS HTML-Polling, Härtung (Notify-Fail-Retry, seen-Cap, CISA-Alt), py2app für gebrandete Notifications, Fehlalarm-Tuning.

## Goldene Regeln
1. **SOFORT-Meldung ist das Kernversprechen.** Lieber eine Bedrohung einmal zu viel melden als eine verpassen. Eine verpasste echte Bedrohung ist der einzige echte Fehler.
2. **Signal vor Lärm — aber im Zweifel melden.** Fehlalarm-Flut führt dazu, dass man das Tool ignoriert; hohe Schwere laut, niedrige leise/gesammelt. Die Balance ist einstellbar, nicht hartcodiert.
3. **Robustheit vor Features.** Das Ding muss zuverlässig laufen: Netzausfall, Feed-Timeout, kaputtes XML, Mac-Neustart — nichts darf den Watcher still sterben lassen.
4. **Wartbarkeit vor Eleganz.** Adrian wartet das nebenbei. Eine Quelle hinzufügen muss eine Ein-Zeilen-Config-Änderung sein, kein Refactor.
5. **Nichts aus dem Gedächtnis behaupten** bei Feed-URLs, Feed-Formaten, macOS-Notification-APIs, `launchd`-Verhalten — verifizieren (`researcher` / echter Abruf) und belegen.
6. **Quellen: seriös UND schnell.** Offizielle (BACS/NCSC, CISA) für Autorität + schnelle (heise Security, BleepingComputer) fürs Tempo. Die PHP-Krise wäre bei den schnellen zuerst aufgeschlagen.
7. **Lokal bleibt lokal.** Keine Lese-/Nutzungsdaten in die Cloud. Das Tool holt nur öffentliche Feeds und meldet lokal.

## Scope (Kurzform)
**IN:** RSS/Atom-Polling mehrerer Quellen · Dedup (schon gesehen) · Relevanz-/Schwere-Heuristik (Stichwörter: CVE, Zero-Day, Exploit, Ransomware, Datenleck, aktiv ausgenutzt, PHP, …) · native macOS-Notifications (schwereabhängig) · Menüleisten-Status + Liste der letzten Treffer · Autostart beim Login · einfache Quellen-/Stichwort-Config.
**OUT (vorerst):** eigene Website/Server · Multi-User · Cloud-Sync · E-Mail-/Slack-Versand (später evtl. optional) · Datenbank (eine lokale State-Datei reicht) · Windows/Linux.

## Harte Constraints
- Plattform: **macOS** (darwin), Autostart via **LaunchAgent** (`launchd`). Kein Root nötig.
- Betrieb: **ein Nutzer, eine Maschine, lokal.** Kein Serverbetrieb, kein Kundenbezug → kein Prod-Deploy-Gate nötig.
- Abhängigkeiten minimal halten (Regel #4). Offline-tolerant (Regel #3).
- Nur öffentliche Feeds; keine Authentifizierung, keine Secrets im Repo.

## Repo-Karte
```
CLAUDE.md                  # diese Datei
README.md                  # Kurzbeschrieb + Betrieb (Start/Stop/Autostart)
sessions.md                # Sitzungs-Journal (max. ~3 kompakte Einträge)
archive.md                 # Archiv (ältere Sessions, Snapshots) — nur greppen
.claude/rules/
  security.md              # Umgang mit externen Feeds (untrusted input) + lokale Hygiene
docs/
  DOCS-INDEX.md            # Source-of-Truth-Matrix
  konzept.md               # Produkt + Architektur-Vorschlag + Quellenliste + offene Entscheidungen (SoT)
  roadmap.md               # Bau-Phasen
tickets/
  INDEX.md                 # offene Tickets
  DONE.md                  # abgeschlossene Tickets
  TICKET-*.md
```

## Schätz-Einheit
In **Claude-Code-Sessions**, nicht in Stunden. Eine Session = fokussierter Block, endet committet + (ab MVP) lauffähig + mit `sessions.md`-Eintrag.

## Session-Ritual
- **Start:** diese Datei → letzter `sessions.md`-Eintrag → `tickets/INDEX.md`.
- **Ende:** `sessions.md`-Eintrag (kompakt) → Tickets aktualisieren (Done → `tickets/DONE.md`) → **CLAUDE.md «Aktueller Stand» prüfen** → committen (Push/Tag nur auf ausdrückliches Wort).
- **Doku-Hygiene:** «Aktueller Stand» schlank halten (nur Ist-Zustand, keine Historie). Neues Doc? → Source-of-Truth-Header + Eintrag in `docs/DOCS-INDEX.md`.

## Entscheidungs-Log
> Hier nur aktive Kern-Entscheide. Details → `docs/konzept.md`.

- **Eigenständiges Tool, keine Erweiterung von Selas.** Eigenes Repo, eigener Lebenszyklus. (2026-10-26, S001)
- **Runtime-Form = Menüleisten-App mit Autostart** (Adrian S001) — «immer sichtbar + sofort» ohne Bildschirmplatz. → `docs/konzept.md`
- **Stack = Python + `feedparser` + `rumps`** (Adrian S001) — schnell gebaut, wartungsarm; Swift verworfen (Aufwand). → `docs/konzept.md`
- **Takt = 5 Min, laut nur bei hoher Schwere; Technologie-Watchlist = immer hohe Schwere** (Adrian S001, Kontext: Selas = wachsende SaaS mit aktiven Usern). → `docs/konzept.md` §6

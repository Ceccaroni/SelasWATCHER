# CLAUDE.md — SelasWATCHER

> **Diese Datei wird zu Beginn JEDER Session gelesen.** Kompakt halten. Details liegen in den verlinkten Docs. Source-of-Truth-Matrix: `docs/DOCS-INDEX.md`.

## Einzeiler
SelasWATCHER — eigenständiges, kleines **macOS-Frühwarn-Tool**. Überwacht Security-/IT-Quellen per RSS/Atom, erkennt potenzielle Bedrohungen und meldet sie **SOFORT** nativ auf dem Mac. Läuft unauffällig im Hintergrund (Autostart beim Login). Rein lokal, nur für Adrian. Auslöser: die PHP-Sicherheitskrise (KW 43/2026), von der Adrian erst über Freunde erfuhr — das darf nie wieder passieren.

## Aktueller Stand

> Nur Ist-Zustand (kompakt). Verlauf → `sessions.md`/`archive.md` · Tickets → `tickets/INDEX.md`.

- **Phase 3 fertig & reviewt (S001, 2026-10-26).** Repo public: https://github.com/Ceccaroni/SelasWATCHER (Branch `master`). ADR: `docs/adr/0001`.
- **Menüleisten-App lauffähig:** `python -m selaswatcher.app` — Selas-Symbol als Template-Icon (tönt hell/dunkel), bei ungelesenen HIGH → rotes Icon + Zähler; Menü listet Meldungen (Klick öffnet Artikel) — **alle HIGH + die letzten 15 nicht-HIGH** (MEDIUM/LOW gedeckelt, damit eine MEDIUM-Flut die HIGH nicht verdrängt), „Jetzt prüfen"/„Alle als gelesen" (setzt Alarm zurück **und** leert die Liste; `seen.json` bleibt)/„Konfiguration öffnen"/„Beenden". Polling im Worker-Thread, UI-Updates im Main-Thread. Smoke-Test bestanden (startet sauber, Worker pollt, kein Crash).
- **Kern (CLI weiterhin):** `python -m selaswatcher {poll,watch,test-notify}`. Fetcher Typ-Adapter (RSS/Atom + JSON: CISA KEV/NVD/GitHub + **HTML: BACS**), Dedup+Baseline, Scoring (Watchlist=HIGH, CERT-Bund/BSI schwere-gegated S006), osascript-Notifications. `cisa-advisories` reaktiviert (S003): `alerts.xml` statt `all.xml` (kein ICS-Lärm), KEV-Wrapper gefiltert, Rest = `always_high`. State `~/.selaswatcher/seen.json`.
- **BACS/NCSC (S004):** Autoritative CH-Quelle via **HTML-Polling** (`sources.py` Typ `html` + `_fetch_bacs`), da kein Feed existiert (real verifiziert) — Seite „Aktuelle Vorfälle" ist server-gerendert (Nuxt-SSR), stdlib-Parsing, **keine bs4-Dependency**, kein WAF (Default-UA reicht). Einstufung **`always_high`** wie CISA (jeder Eintrag bannert; ~1/Monat → keine Flut), weil normales Keyword-Scoring die PHP-Warnung nur MEDIUM gäbe (Gründungsfall-Risiko). Markup-Bruch (0 Einträge trotz echtem Body) → Exception → Wächter-fürs-Wächter meldet den stillen Ausfall (Regel #3). `docs/konzept.md` §5/§6.5.
- **LIVE (S001, 2026-10-26):** Phase 3 auf `master` gepusht. **Autostart installiert** (`~/Library/LaunchAgents/ch.selas.selaswatcher.plist`, RunAtLoad/KeepAlive) — App läuft dauerhaft, pollt sauber (Log `~/Library/Logs/selaswatcher.log`). Deinstallieren: `scripts/uninstall-autostart.sh`.
- **Meldelogik (nach 52-Alarm-Flut überarbeitet):** Nur **HIGH** macht ein Banner (klickbar via terminal-notifier, Fallback osascript); MEDIUM/LOW nur stumm in der Menüliste.
- **Fehlalarm-Tuning (S005, 2026-10-27):** Breach/Leak-Begriffe `datenleck`/`data breach`/`breach` von `high_keywords` → `generic_keywords` (= **MEDIUM**, kein Banner) — ein Fremd-Breach (z. B. Uni Kopenhagen) ist Lärm. Ein uns betreffender Breach bleibt HIGH über **Watchlist** (Stack/Provider genannt) oder **Dringlichkeits-Keyword** (actively exploited/zero-day/rce/…); `ransomware` zunächst bewusst HIGH gelassen — **in S006 revidiert** (siehe unten). PHP-Gründungsfall unberührt (hängt an BACS/CISA `always_high`, nicht an „breach").
- **Fehlalarm-Tuning Runde 2 (S006, 2026-10-27):** Zwei Realbetrieb-Lärmquellen gedämpft (Regel #2), Regel #1 gewahrt. **(a) CERT-Bund/BSI schwere-gegated:** neue `Source.severity_tagged`-Flag (cert-bund-wid + buerger-cert) + `scoring._severity_tag` — ein Stack-Watchlist-Treffer bannert nur noch bei `[hoch]`/`[kritisch]`, `[mittel]`/`[niedrig]` → MEDIUM (stumm). Killt den täglichen Node/Docker/Postgres-`[mittel]`-Dauerbanner. **(b) `ransomware` → MEDIUM** (von `high_keywords` nach `generic_keywords`, wie `breach` in S005; S005-„bleibt HIGH" damit aufgehoben): nacktes Ransomware-News = Fremd-Lärm (Safepay-CH-Fälle ohne Selas-Bezug); HIGH nur noch mit Stack/Provider (Watchlist) oder zweitem Dringlichkeits-Keyword. **Schutz:** Dringlichkeits-Keyword schlägt das Schwere-Gate (aktive Ausnutzung bannert immer); unlesbarer Tag bei Stack-Treffer → im Zweifel HIGH. Verifiziert über echten `score()`-Pfad (12 Fälle). `docs/konzept.md` §4/§6.7.
- **Fehlalarm-Tuning Runde 3 (S007, 2026-10-27):** GitHub-Advisory-**Inventar-Treffer schwere-gegated** — bannert nur noch bei GitHub-Schwere `critical`/`high` (`severity_hint`, war im `score()`-Inventarzweig bisher ungenutzt); `moderate`/`low` → MEDIUM. Killt die HIGH-Flut aus moderaten DoS/ReDoS der 836 transitiven npm-Pakete (undici/qs/nodemailer). KEV unberührt. Variante „nur critical" verworfen (hätte high-RCE im eigenen Stack entschärft). Live gegen GitHub-API + 3 synthetische Fälle verifiziert. `docs/konzept.md` §4/§6.8.
- **Inventar-Matching (Dependabot-Prinzip):** `selaswatcher/inventory.py` liest die `package-lock.json` des echten Projekts (`[inventory] project_paths` in `config.toml`, lokal: Selas-Repo = 836 Pakete inkl. transitiv). **GitHub-Advisories werden paketgenau dagegen gematcht** → gemeldet nur, wenn ein tatsächlich genutztes Paket betroffen ist (sonst ignoriert); **Banner (HIGH) nur bei GitHub-Schwere `critical`/`high`, `moderate`/`low` → MEDIUM** (S007, schwere-gegated wie CERT-Bund). KEV = Titel-Watchlist; **NVD aus** (Firehose). Infra-Teile (Postgres/Docker/Node-Runtime/Next.js/Supabase) + PHP-Krisen über Infra-Watchlist bzw. News-Kritisch-Keywords. `docs/konzept.md` §4.
- **Härtung (S002):** fehlgeschlagene HIGH-Zustellung wird **nicht mehr still als gesehen verbucht** → Retry im nächsten Poll (`poller.py` `to_mark`/`failed_high`; App zeigt sie trotzdem rot + dedupliziert den Retry per `dedup_id` in `_drain`). `seen.json` **gedeckelt** via `State.prune` + `[state] seen_cap` (Default 2000). `docs/konzept.md`-Meldelogik unverändert.
- **Wächter-fürs-Wächter (S003):** Eine Quelle, die **still ausfällt** (403, kaputter Feed), meldet sich jetzt selbst: `poller` zählt Fehlschläge in Folge (persistent in `seen.json`: `fail_streak`/`health_warned`), ab `[health] fail_threshold` Polls (Default 6 ≈ 30 Min) **einmal** HIGH-Banner „Quelle X fällt aus" (`source_id="health"`), re-armt bei Erholung. `0` = aus. Verhindert, dass ein blinder Watcher unbemerkt Warnungen verschluckt (Regel #1/#3). → `docs/konzept.md` §6.6.
- **Offen (Backlog) → TICKET-004 (Phase 4):** py2app für gebrandete Notifications, Fehlalarm-Tuning nach echtem Betrieb. Alles optional/nach Bedarf.

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
- **Takt = 5 Min, laut nur bei hoher Schwere; Technologie-Watchlist = immer hohe Schwere** (Adrian S001, Kontext: Selas = wachsende SaaS mit aktiven Usern) — **in S006 verfeinert**: bei schwere-getaggten Quellen (CERT-Bund/BSI) zählt die Quellen-Schwere, Watchlist-Treffer bannert dort nur bei `[hoch]`/`[kritisch]`. → `docs/konzept.md` §6
- **CISA-Alerts = immer HIGH** (Adrian S003) — `alerts.xml` (kuratiert) statt `all.xml` (ICS-Firehose), KEV-Wrapper gefiltert, Rest bannert via `Source.always_high`. Neue „immer HIGH"-Klasse neben der Watchlist, um Gründungsfälle wie die PHP-Krise sicher zu fangen. → `docs/konzept.md` §6.5
- **BACS/NCSC = immer HIGH** (Adrian S004) — dieselbe `always_high`-Klasse wie CISA: autoritative, niederfrequente CH-Warnungen; Keyword-Scoring hätte die PHP-Warnung nur MEDIUM gegeben. HTML-Polling, weil kein Feed existiert. → `docs/konzept.md` §5/§6.5
- **CERT-Bund/BSI schwere-gegated + `ransomware` → MEDIUM** (Adrian S006) — zwei Realbetrieb-Lärmquellen (Node/Docker/Postgres-`[mittel]`-Flut; Fremd-Ransomware ohne Selas-Bezug) auf MEDIUM gedämpft; HIGH bleibt bei Stack+hoch/kritisch bzw. Stack/Provider oder Dringlichkeits-Keyword. Hebt die S005-Entscheidung „`ransomware` bleibt HIGH" auf. → `docs/konzept.md` §6.7
- **GitHub-Inventar-Treffer schwere-gegated** (Adrian S007) — Banner nur bei GitHub-Schwere `critical`/`high`, `moderate`/`low` → MEDIUM. Dämpft die DoS/ReDoS-Flut aus transitiven npm-Paketen; dieselbe Linie wie das CERT-Bund-Gate (Quellen-Schwere respektieren). Variante „nur critical" verworfen (Regel #1). → `docs/konzept.md` §6.8

---
title: "ADR-0001: Architektur und Quellen von SelasWATCHER"
status: "Accepted"
date: "2026-10-26"
authors: "Adrian Lanz"
tags: ["architecture", "decision", "macos", "security-monitoring"]
supersedes: ""
superseded_by: ""
---

# ADR-0001: Architektur und Quellen von SelasWATCHER

## Status

**Accepted** (Adrian Lanz, 2026-10-26, Session 001)

## Context

Adrian wurde erst über Freunde auf die PHP-Sicherheitskrise (KW 43/2026) aufmerksam — zu spät und rein zufällig. SelasWATCHER soll dafür sorgen, dass **relevante IT-/Security-Bedrohungen sofort und von selbst** auf dem Mac sichtbar werden, ohne dass jemand aktiv Seiten abklappern muss.

Der geschäftliche Hintergrund schärft die Anforderung: Selas ist eine wachsende SaaS mit aktiven Usern. Eine Bedrohung gegen den eigenen Technologie-Stack (PHP, Next.js, Node, Supabase/Postgres, Docker, Infomaniak) ist damit **geschäftskritisch** und muss Vorrang vor generischer Security-News haben.

Rahmenbedingungen:

- Plattform: **macOS** (ein Nutzer, eine Maschine, lokal). Kein Serverbetrieb, kein Kundenbezug, kein Root.
- Kernversprechen: keine verpasste Bedrohung — im Zweifel lieber einmal zu viel melden.
- Wartbarkeit vor Eleganz: Adrian wartet das Tool nebenbei; eine neue Quelle soll eine Ein-Zeilen-Config-Änderung sein.
- Robustheit vor Features: Netzausfall, Feed-Timeout, kaputtes XML oder ein Mac-Neustart dürfen den Watcher nicht still sterben lassen.

Dieser ADR hält den am 2026-10-26 (Session 001) mit Adrian getroffenen Grundsatzentscheid fest. Es handelt sich um mehrere gekoppelte Einzelentscheide (Runtime-Form, Stack, Pipeline, Quellen, Datenschutz), die zusammen die MVP-Architektur definieren.

## Decision

Es wurden fünf gekoppelte Entscheide getroffen:

1. **Runtime-Form = macOS-Menüleisten-App mit Autostart.** Permanent sichtbares Menüleisten-Icon (beruhigt: «läuft»), das sich bei Treffern färbt/badged; Klick zeigt die letzten Treffer mit Direkt-Link. Autostart via LaunchAgent-Plist in `~/Library/LaunchAgents/` (`RunAtLoad` + `KeepAlive`): startet beim Login, Neustart nach Absturz.

2. **Stack = Python 3 + `feedparser` + `rumps`.** `feedparser` für robustes RSS/Atom-Parsing, `rumps` für die Menüleisten-App, native macOS-Notifications. In Stunden statt Wochen gebaut, winzige Codebasis, neue Quelle = eine Config-Zeile (Wartbarkeit, Regel #4). Für `.app` + Autostart genügt ein venv + LaunchAgent, kein signiertes App-Bundle nötig.

3. **Verarbeitungs-Pipeline:** Poll aller Quellen alle **5 Minuten** (ETag/Last-Modified zur Lastschonung) → **Dedup** gegen lokale State-Datei (`~/.selaswatcher/seen.json`) mit First-Run-Baseline (beim Erststart nichts nachträglich melden) → **Relevanz-/Schwere-Heuristik** (Stichwörter auf Titel+Summary) → **schwereabhängige native Notification**: laut/kritisch nur bei hoher Schwere, mittel als normale Notification, niedrig nur gesammelt im Menü. **Hohe Schwere** = Zero-Day / aktiv ausgenutzt / RCE / Notfall-Patch / Ransomware / Datenleck **oder jeder Treffer auf der Technologie-Watchlist** (PHP, Next.js, Node, Supabase/Postgres, Docker, Infomaniak) — Stack-Relevantes schreit immer zuerst. Schwellen und Watchlist sind konfigurierbar, nicht hartcodiert (Regel #2).

4. **Quellen & Feed-Typen (verifiziert 2026-10-26 via `curl`, HTTP 200 + Content-Type real geprüft):** 10 aktive Quellen in drei Typen, der Fetcher braucht daher **einen kleinen Typ-Adapter je Feed-Typ**:
   - **7× RSS/Atom** → direkt via `feedparser`: inside-it.ch, 20min/digital, CISA Advisories+Alerts, CERT-Bund WID, Bürger-CERT (BSI), heise Security, BleepingComputer.
   - **3× JSON-API** → eigener kleiner Fetcher je Quelle mit Mapping auf ein gemeinsames internes Format: CISA KEV, NVD/CVE, GitHub Advisory DB.
   - **BACS/NCSC (CH-Behörde) hat keinen Feed** (alle Kandidatenpfade 404, nur HTML) → **HTML-Polling als Phase 4** (eigenes Ticket). Bis dahin ist die behördliche Autorität durch CISA KEV + CERT-Bund inhaltlich abgedeckt.

5. **Lokal-only, keine Cloud/Telemetrie.** Das Tool holt ausschliesslich öffentliche Feeds und meldet lokal. Keine Lese-/Nutzungsdaten verlassen die Maschine. Externe Feeds gelten als **untrusted input** und werden entsprechend behandelt (siehe `.claude/rules/security.md`).

## Consequences

### Positive

- **POS-001**: In Stunden statt Wochen gebaut und mit einer winzigen, gut wartbaren Codebasis — eine neue Quelle ist eine Config-Zeile (erfüllt Regel #4).
- **POS-002**: Die Menüleisten-App liefert «immer sichtbar + sofort», ohne Bildschirmplatz zu kosten oder abzulenken; das permanente Icon signalisiert zusätzlich, dass der Watcher läuft.
- **POS-003**: Stack-relevante Bedrohungen (Technologie-Watchlist) lösen immer eine laute Notification aus und «schreien zuerst» — das Kernversprechen gegen eine zweite PHP-Krise ist direkt in die Schwere-Heuristik eingebaut.
- **POS-004**: Autostart via LaunchAgent (`RunAtLoad` + `KeepAlive`) macht den Betrieb robust gegen Login-Neustarts und Abstürze (erfüllt Regel #3).
- **POS-005**: Lokal-only ohne Cloud/Telemetrie hält die Angriffsfläche und den Wartungsaufwand minimal und erfüllt «Lokal bleibt lokal» (Regel #7).

### Negative

- **NEG-001**: Python benötigt ein venv auf der Zielmaschine; Setup und Dependency-Pflege sind manuell (bewusst in Kauf genommen gegenüber einer nativen Swift-`.app`).
- **NEG-002**: Native Notifications über `osascript`/`terminal-notifier` sind im MVP nicht klickbar — der Direkt-Link steht zunächst nur in der Menüleisten-Liste, nicht in der Notification selbst.
- **NEG-003**: Die Schweizer Behördenquelle BACS/NCSC ist im MVP nicht abgedeckt; sie folgt erst in Phase 4 über HTML-Polling. Bis dahin besteht Abhängigkeit von der inhaltlichen Überlappung mit CISA KEV + CERT-Bund.
- **NEG-004**: Die JSON-APIs (NVD, GitHub Advisory) haben Rate-Limits; NVD empfiehlt einen API-Key. Ein Key muss später über eine Env-Var ergänzt werden (nicht ins Repo) und erhöht die Konfigurationslast.
- **NEG-005**: Die Stichwort-/Schwere-Heuristik braucht Tuning: Zu aggressiv erzeugt Fehlalarm-Flut (Tool wird ignoriert, Regel #2), zu konservativ riskiert verpasste Treffer (Regel #1). Die Balance muss laufend justiert werden.

## Alternatives Considered

### Stiller Hintergrund-Daemon (nur Notifications)

- **ALT-001**: **Beschreibung**: Prozess ohne UI, der ausschliesslich bei Treffern eine Push-Notification feuert — niedrigste Aufdringlichkeit, geringster Aufwand.
- **ALT-002**: **Rejection Reason**: Kein permanenter Status-Anker. Man sieht nicht, ob der Watcher überhaupt läuft, und verpasste/weggeklickte Notifications sind unwiederbringlich — widerspricht «immer sichtbar».

### Immer offenes Fenster (Adrians erste Idee)

- **ALT-003**: **Beschreibung**: Dauerhaft geöffnetes Fenster mit der Treffer-Liste, maximale Sichtbarkeit.
- **ALT-004**: **Rejection Reason**: Kostet dauerhaft Bildschirmplatz und lenkt ab. Die Menüleisten-App liefert dasselbe «ich sehe es sofort» deutlich unaufdringlicher.

### Nativer Swift-Menüleisten-App

- **ALT-005**: **Beschreibung**: Native macOS-App in Swift, ohne Python-Env, mit besseren kritischen Notifications und signierbarem `.app`-Bundle.
- **ALT-006**: **Rejection Reason**: Wochen- statt Stundenaufwand, weiter weg von Adrians üblichem Stack und höhere Wartungslast — verstösst gegen «Wartbarkeit vor Eleganz» (Regel #4). Nur bei harter Forderung nach einer signierten nativen App zu überdenken.

### The Hacker News / Netzwoche als zusätzliche Quellen

- **ALT-007**: **Beschreibung**: Im Research vorgeschlagene weitere Security-Feeds.
- **ALT-008**: **Rejection Reason**: Adrian wählte bewusst die anderen Quellen; die ausgewählte Menge deckt Autorität (CISA, CERT-Bund) und Tempo (heise, BleepingComputer) bereits ab. Nachträgliche Aufnahme bleibt eine Ein-Zeilen-Config-Änderung.

## Implementation Notes

- **IMP-001**: Fetcher mit **Typ-Adaptern** (`rss`/`atom` via `feedparser`, `json` je API, `html` für BACS in Phase 4) auf ein gemeinsames internes Format mappen. Quellen als Config-Liste, damit eine neue Quelle eine Zeile bleibt (Regel #4).
- **IMP-002**: Quellenspezifische Dedup-Fallstricke beachten: CERT-Bund WID hat kein `guid` → Dedup über WID-ID (z. B. `WID-SEC-2026-4079`), `[UPDATE]` mit neuem `pubDate` als neue Version werten; BleepingComputer Channel-`pubDate` = Build-Zeit → Item-`pubDate` verwenden; CISA-Advisories-Feed ist gross (~5–6 MB) → ETag/Last-Modified zwingend.
- **IMP-003**: First-Run-Baseline: Beim Erststart gesehene Einträge in die State-Datei schreiben, aber nicht melden (sonst Notification-Flut). Offline-Toleranz und Fehlerisolierung pro Quelle, damit ein kaputter Feed den Watcher nicht killt (Regel #3).
- **IMP-004**: NVD-API-Key später über Env-Var ergänzen (nicht ins Repo). Externe Feed-Inhalte als untrusted input behandeln (`.claude/rules/security.md`).
- **IMP-005**: Erfolgskriterien: Watcher läuft nach Login dauerhaft (LaunchAgent), eine Stack-relevante Bedrohung erzeugt binnen eines Poll-Zyklus (≤ 5 Min) eine laute Notification, keine Duplikate über Neustarts hinweg.

## References

- **REF-001**: [`docs/konzept.md`](../konzept.md) — **Source of Truth** für Produktidee, Architektur, vollständige Begründung, Quellenliste (§5) und verifizierte Feed-URLs.
- **REF-002**: `CLAUDE.md` — Entscheidungs-Log und Goldene Regeln (#1–#7).
- **REF-003**: `.claude/rules/security.md` — Umgang mit externen Feeds (untrusted input) und lokale Hygiene.

# Konzept — SelasWATCHER

> **Source of Truth** für Produktidee, Architektur und Quellen. Entscheide hier festhalten; andere Docs referenzieren.
> Stand: 2026-10-26 (S001). Status: **Architektur bestätigt** (Adrian) + **Feed-URLs verifiziert** (§5). Bereit für MVP-Bau.

## 1. Problem & Versprechen
Adrian wurde erst über Freunde auf die PHP-Sicherheitskrise (KW 43/2026) aufmerksam — zu spät, zu zufällig. SelasWATCHER soll sicherstellen, dass **relevante IT-/Security-Bedrohungen sofort und von selbst** auf dem Mac sichtbar werden, ohne dass Adrian aktiv Seiten abklappern muss.

**Kernversprechen:** Keine verpasste Bedrohung. Lieber eine zu viel melden als eine zu wenig (CLAUDE.md Regel #1).

## 2. Runtime-Form — Vorschlag: Menüleisten-App mit Autostart
Drei Optionen abgewogen:

| Variante | «immer sichtbar» | Aufdringlichkeit | Aufwand | Wartung |
|---|---|---|---|---|
| **A. Menüleisten-App** (empfohlen) | Icon in Menüleiste, färbt/badged bei Treffer, Klick = Liste | mittel, steuerbar | mittel | gering |
| B. Stiller Hintergrund-Daemon (nur Notifications) | nein, nur Push bei Treffer | niedrig | gering | gering |
| C. Immer offenes Fenster (Adrians erste Idee) | ja, voll | hoch, nimmt Platz | mittel | mittel |

**Empfehlung A:** Eine Menüleisten-App ist die macOS-native, eleganteste Antwort auf «immer sichtbar + sofort». Das Icon ist permanent präsent (beruhigt: «läuft»), stört aber nicht; bei einem Treffer färbt es sich/zeigt einen Badge **und** feuert eine native Notification. Zusätzlich: Klick aufs Icon zeigt die letzten Treffer mit Direkt-Link. Variante C (Dauerfenster) kostet Bildschirmplatz und lenkt ab; der Menüleisten-Ansatz liefert dasselbe «ich sehe es sofort» unaufdringlicher.

**Autostart:** LaunchAgent-Plist in `~/Library/LaunchAgents/` (`RunAtLoad` + `KeepAlive`) → startet beim Login, wird nach Absturz neu gestartet.

## 3. Stack — Vorschlag: Python
- **Python 3** + `feedparser` (RSS/Atom-Parsing, extrem robust gegenüber kaputtem XML) + `rumps` (Menüleisten-App) + native Notifications (`pync`/`terminal-notifier` oder direkt `UNUserNotification` via `pyobjc`).
- Begründung: in Stunden statt Tagen gebaut, winzige Codebasis, eine neue Quelle = eine Zeile Config (Regel #4). Nachteil: braucht ein Python-Env; für eine echte `.app` + Autostart genügt aber ein venv + LaunchAgent, kein App-Bundle nötig.
- **Alternative: nativer Swift-Menüleisten-App** — nativer, kein Python-Env, bessere «kritische» Notifications; aber deutlich mehr Bau-/Wartungsaufwand und weiter weg von Adrians üblichem Stack. Nur wenn «es muss eine echte signierte .app sein» gefordert ist.

## 4. Verarbeitungs-Pipeline
1. **Poll** aller Quellen im Intervall (Vorschlag: 5 Min; pro Quelle konfigurierbar). ETag/Last-Modified nutzen, um Bandbreite/Last zu schonen.
2. **Dedup:** Jeder Eintrag per stabiler ID (GUID/Link) gegen lokale State-Datei (`~/.selaswatcher/seen.json` o. ä.) — nur Neues wird betrachtet.
3. **Relevanz-/Schwere-Scoring (quellentyp-bewusst, Stand nach 52-Alarm-Flut):**
   - **Vuln-Datenbanken** (CISA KEV, NVD, GitHub = `source.vulndb`) sind ein Firehose über ALLE Hersteller → melden nur bei eigenem Stack:
     - **GitHub Advisory** → **paketgenauer Abgleich gegen das Inventar** (`inventory.py` liest `package-lock.json`, inkl. transitiver Pakete): HIGH nur, wenn ein tatsächlich genutztes Paket betroffen ist (Dependabot-Prinzip), sonst ignoriert.
     - **CISA KEV** → Infra-Watchlist nur gegen den **Titel** (Produktname), sonst ignoriert.
     - **NVD** → deaktiviert (zu laut; Titel = Beschreibungstext).
   - **News-Quellen** (inside-it, 20min, heise, CERT-Bund, BleepingComputer): HIGH bei Infra-Watchlist (next.js/node.js/supabase/postgres(ql)/docker/infomaniak) **oder** Kritisch-Keyword (zero-day/aktiv ausgenutzt/RCE/Ransomware/breach …) — so kommen auch PHP-Krisen rein; MEDIUM bei generischem Security-Keyword; sonst LOW. Matching durchweg wortgrenzen-basiert.
4. **Melden:** **Nur HIGH** erzeugt ein Banner (klickbar via terminal-notifier, Fallback osascript; Ton bei HIGH). MEDIUM/LOW landen **stumm in der Menüliste** (kein Push). Alles konfigurierbar (Regel #2).
5. **Anzeigen:** Menüleisten-Liste der letzten N Treffer, Klick öffnet den Artikel.

## 5. Quellen — verifiziert 2026-10-26 (S001, `curl -sI`, HTTP 200 + Content-Type real geprüft)

**Wichtig fürs Design:** Nicht alle Quellen sind RSS/Atom. Es gibt drei Typen → der Fetcher braucht pro Typ einen kleinen Adapter:
- **`rss`/`atom`** → direkt via `feedparser`.
- **`json`** (CISA KEV, NVD, GitHub Advisory) → eigener kleiner Fetcher je Quelle, Felder auf das gemeinsame interne Format mappen.
- **`html`** (nur BACS — kein Feed vorhanden) → schonendes HTML-Polling der Vorfall-Liste (eigenes Ticket, Phase 4).

| Quelle | Typ | URL | Dedup-ID | Datum | Sprache |
|---|---|---|---|---|---|
| inside-it.ch | rss | `https://www.inside-it.ch/rss.xml` | `guid` (= URL) | `pubDate` | de |
| 20min Digital | rss | `https://partner-feeds.20min.ch/rss/20minuten/digital` | `guid` (= URL) | `pubDate` | de-ch |
| CISA Advisories+Alerts | rss | `https://www.cisa.gov/cybersecurity-advisories/all.xml` | `guid` (`/node/N`) | `pubDate` | en |
| CISA KEV (aktiv ausgenutzt) | json | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` | `cveID` | `dateAdded` | en |
| CERT-Bund WID | rss | `https://wid.cert-bund.de/content/public/securityAdvisory/rss` | **WID-ID aus Titel/Link** (kein `guid`!) | `pubDate` | de |
| Bürger-CERT (BSI) | rss | `https://wid.cert-bund.de/content/public/buergercert/rss` | `<id>` | `pubDate` | de |
| heise Security | atom | `https://www.heise.de/security/feed.xml` | `<id>` (`urn:bid:…`) | `<updated>`/`<published>` | de |
| BleepingComputer | rss | `https://www.bleepingcomputer.com/feed/` | `guid` (= URL) | **Item**-`pubDate` (nicht Channel!) | en |
| NVD (CVE) | json-API | `https://services.nvd.nist.gov/rest/json/cves/2.0` | CVE-`id` | `lastModified` | en |
| GitHub Advisory DB | json-API | `https://api.github.com/advisories?ecosystem=composer` (auch `npm` etc.) | `ghsa_id` | `updated_at` | en |
| **BACS/NCSC (CH-Behörde)** | **html** | `https://www.bacs.admin.ch/de/aktuelle-vorfaelle` | aus gescrapten Einträgen | — | de |

**Quellenspezifische Hinweise:**
- **BACS:** Kein offizieller RSS/Atom-Feed (alle Kandidatenpfade 404, GovCERT liefert nur HTML). Nutzer wünscht die Quelle ausdrücklich → **HTML-Polling als eigenes Ticket (Phase 4).** Bis dahin ist die behördliche Autorität durch CISA + CERT-Bund abgedeckt (inhaltlich grosse Überlappung).
- **CERT-Bund WID:** Kein `guid`; Dedup über die WID-ID (z. B. `WID-SEC-2026-4079`). Updates kommen als `[UPDATE]` mit neuem `pubDate` → `pubDate` allein ist KEIN Dedup-Schlüssel; (WID-ID + pubDate) als «neue Version» werten.
- **CISA Advisories-RSS** (`all.xml`): beim MVP-Bau (S001) als **HTTP 403 (WAF-geblockt)** verifiziert — auch mit Browser-UA, also kein Header-Problem → **Quelle deaktiviert** (`sources.cisa-advisories = false`). CISA KEV (JSON) deckt das kritische „aktiv ausgenutzt"-Signal ab. Alternativen Fetch-Weg in Phase 4 prüfen. (Feed wäre sonst ~5–6 MB → ETag zwingend.)
- **NVD & GitHub** sind JSON-APIs mit Query-Parametern für «geändert seit» (NVD: `lastModStartDate`/`lastModEndDate`; GitHub: `per_page`/Zeitfilter). NVD empfiehlt einen API-Key gegen Rate-Limits — ggf. später via Env-Var (nicht ins Repo, `.claude/rules/security.md`).
- **BleepingComputer:** Channel-`pubDate` = Build-Zeit → fürs «neu seit» das Item-`pubDate` verwenden.

*The Hacker News / Netzwoche aus dem Research-Vorschlag: vorerst NICHT aufgenommen (Adrian wählte die anderen; können später als Ein-Zeilen-Config ergänzt werden).*

## 6. Getroffene Entscheidungen (Adrian, 2026-10-26 / S001)
1. **Runtime-Form:** Menüleisten-App (Variante A).
2. **Stack:** Python + `feedparser` + `rumps`.
3. **Quellen:** die drei fixen + **alle** Erweiterungen aus §5 (CISA KEV+Alerts, BSI/CERT-Bund, heise Security, BleepingComputer, NVD/CVE, GitHub Advisory).
4. **Takt:** Poll alle **5 Min**; laute/kritische Notification **nur bei hoher Schwere**. Hohe Schwere = Zero-Day/aktiv ausgenutzt/RCE/Notfall-Patch/Ransomware/Datenleck **oder** Treffer auf der Technologie-Watchlist (PHP, Next.js, Node, Supabase/Postgres, Docker, Infomaniak) — weil Selas eine wachsende SaaS mit aktiven Usern ist, schreit Stack-Relevantes immer sofort.

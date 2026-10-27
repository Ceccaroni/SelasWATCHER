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
     - **GitHub Advisory** → **paketgenauer Abgleich gegen das Inventar** (`inventory.py` liest `package-lock.json`, inkl. transitiver Pakete): gemeldet nur, wenn ein tatsächlich genutztes Paket betroffen ist (Dependabot-Prinzip), sonst ignoriert. **BANNER (HIGH) zusätzlich schwere-gegated** (S007): nur bei GitHub-Schwere `critical`/`high` (`severity_hint`); `moderate`/`low` in einem genutzten Paket — meist DoS/ReDoS (undici/qs/nodemailer) — → MEDIUM (stumm), kein Sofort-Handeln (Regel #2).
     - **CISA KEV** → Infra-Watchlist nur gegen den **Titel** (Produktname), sonst ignoriert.
     - **NVD** → deaktiviert (zu laut; Titel = Beschreibungstext).
   - **News-Quellen** (inside-it, 20min, heise, CERT-Bund, BleepingComputer): HIGH bei Dringlichkeits-Keyword (zero-day/aktiv ausgenutzt/RCE/unauthenticated/emergency-patch) **oder** Infra-Watchlist (next.js/node.js/supabase/postgres(ql)/docker/infomaniak) — so kommen auch PHP-Krisen rein; MEDIUM bei generischem Security-Keyword (inkl. **ransomware/breach** — S005/S006: Fremd-Lärm, erst HIGH mit Stack-/Dringlichkeits-Signal); sonst LOW. **Schwere-getaggte Quellen** (CERT-Bund/BSI, `Source.severity_tagged`, S006): ein Watchlist-Treffer bannert nur bei `[hoch]`/`[kritisch]` — `[mittel]`/`[niedrig]` → MEDIUM (stumm), um die tägliche [mittel]-Flut (Node/Docker/Postgres) zu dämpfen; ein Dringlichkeits-Keyword bleibt auch hier HIGH. Matching durchweg wortgrenzen-basiert.
4. **Melden:** **Nur HIGH** erzeugt ein Banner (klickbar via terminal-notifier, Fallback osascript; Ton bei HIGH). MEDIUM/LOW landen **stumm in der Menüliste** (kein Push). Alles konfigurierbar (Regel #2).
5. **Anzeigen:** Menüleisten-Liste der letzten N Treffer, Klick öffnet den Artikel.

## 5. Quellen — verifiziert 2026-10-26 (S001, `curl -sI`, HTTP 200 + Content-Type real geprüft)

**Wichtig fürs Design:** Nicht alle Quellen sind RSS/Atom. Es gibt drei Typen → der Fetcher braucht pro Typ einen kleinen Adapter:
- **`rss`/`atom`** → direkt via `feedparser`.
- **`json`** (CISA KEV, NVD, GitHub Advisory) → eigener kleiner Fetcher je Quelle, Felder auf das gemeinsame interne Format mappen.
- **`html`** (nur BACS — kein Feed vorhanden) → schonendes HTML-Polling der Vorfall-Liste (umgesetzt S004).

| Quelle | Typ | URL | Dedup-ID | Datum | Sprache |
|---|---|---|---|---|---|
| inside-it.ch | rss | `https://www.inside-it.ch/rss.xml` | `guid` (= URL) | `pubDate` | de |
| 20min Digital | rss | `https://partner-feeds.20min.ch/rss/20minuten/digital` | `guid` (= URL) | `pubDate` | de-ch |
| CISA Alerts | rss | `https://www.cisa.gov/cybersecurity-advisories/alerts.xml` | `guid` (`/node/N`) | `pubDate` | en |
| CISA KEV (aktiv ausgenutzt) | json | `https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json` | `cveID` | `dateAdded` | en |
| CERT-Bund WID | rss | `https://wid.cert-bund.de/content/public/securityAdvisory/rss` | **WID-ID aus Titel/Link** (kein `guid`!) | `pubDate` | de |
| Bürger-CERT (BSI) | rss | `https://wid.cert-bund.de/content/public/buergercert/rss` | `<id>` | `pubDate` | de |
| heise Security | atom | `https://www.heise.de/security/feed.xml` | `<id>` (`urn:bid:…`) | `<updated>`/`<published>` | de |
| BleepingComputer | rss | `https://www.bleepingcomputer.com/feed/` | `guid` (= URL) | **Item**-`pubDate` (nicht Channel!) | en |
| NVD (CVE) | json-API | `https://services.nvd.nist.gov/rest/json/cves/2.0` | CVE-`id` | `lastModified` | en |
| GitHub Advisory DB | json-API | `https://api.github.com/advisories?ecosystem=composer` (auch `npm` etc.) | `ghsa_id` | `updated_at` | en |
| **BACS/NCSC (CH-Behörde)** | **html** | `https://www.bacs.admin.ch/de/aktuelle-vorfaelle` | absolute Detail-URL (`/de/<slug>`) | ausgeschriebenes dt. Datum (Card) | de |

**Quellenspezifische Hinweise:**
- **BACS/NCSC (S004 umgesetzt, real verifiziert):** Kein RSS/Atom/JSON-Feed (kein `<link rel="alternate">`, `/rss`+`/de/rss`+alte NCSC-Pfade 404, Sitemap/robots ohne Feed). Darum **HTML-Polling** der Seite „Aktuelle Vorfälle" (`/de/aktuelle-vorfaelle`; `ncsc.admin.ch` → 301 auf bacs). Die Seite ist **server-gerendert** (Nuxt-SSR, Inhalt im Roh-HTML trotz JS-Framework) mit regulärem Card-Markup → stdlib-Parsing, **keine bs4-Dependency** (Regel #4). Pro Card: Datum (`meta-info__item`, dt. Langformat), Titel (`h3`), relativer Detail-Link (`card__footer__action`, gegen `https://www.bacs.admin.ch` aufgelöst), Summary (`card__description`). **Kein WAF** — Default-UA `SelasWATCHER/0.1` liefert 200 (anders als CISA), kein ETag/Last-Modified. Niederfrequent (~1 Eintrag/Monat). **Einstufung: `always_high`** wie CISA (§6.5) — die kuratierten BACS-Warnungen sind autoritative CH-Dringlichkeitssignale; das normale Keyword-Scoring hätte z. B. die PHP-Warnung nur MEDIUM gegeben (Titel nur „Sicherheitsupdates", dt. Textbegriffe matchen die engl. `high_keywords` nicht) → Gründungsfall-Risiko. **Robustheit:** liefert die Seite echten Inhalt, aber 0 geparste Einträge (Markup geändert), wirft der Adapter bewusst eine Exception → der Wächter-fürs-Wächter (§6.6) meldet den stillen Ausfall, statt ihn als „gesund, 0 neu" zu verschlucken (Regel #3).
- **CERT-Bund WID:** Kein `guid`; Dedup über die WID-ID (z. B. `WID-SEC-2026-4079`). Updates kommen als `[UPDATE]` mit neuem `pubDate` → `pubDate` allein ist KEIN Dedup-Schlüssel; (WID-ID + pubDate) als «neue Version» werten.
- **CISA Advisories/Alerts** (S003 reaktiviert): Der 403/WAF aus S001 war **header-getriggert**, nicht die URL. CISAs Akamai-WAF blockt `python-requests` mit `SelasWATCHER/0.1` (403), lässt aber einen **Browser-UA + vollständigen Accept-Header-Satz** durch (empirisch 5/5 stabil; `_CISA_HEADERS`, nur für diese Quelle). `curl` kam schon immer durch → S001-Verifikation per curl war irreführend; maßgeblich ist der `requests`-Pfad. Inhaltlich: `all.xml` ist zu ~77 % **ICS-/OT-Advisories** (Siemens, Hitachi Energy, Moxa …) — für den Web-/SaaS-Stack reiner Lärm, erzeugt sogar Fehlalarm-HIGH (ICS-Summary mit „node.js"/„rce"). Stattdessen der dedizierte **`alerts.xml`** (107 KB statt 5.7 MB). Davon ~26/30 „CISA Adds … to Catalog"-**KEV-Wrapper** → im Fetcher gefiltert (`_CISA_KEV_WRAPPER_RE`), weil `cisa-kev` (JSON) dieselben Einträge paketgenau abdeckt. Der Rest (~4 in 6 Wochen: PHP, BeyondTrust, Ivanti, Citrix …) ist CISAs „sofort handeln"-Stream → **`always_high`** (jeder Alert bannert; §6.5). So hätte die PHP-Krise (Gründungsfall) ein Banner erzeugt.
- **NVD & GitHub** sind JSON-APIs mit Query-Parametern für «geändert seit» (NVD: `lastModStartDate`/`lastModEndDate`; GitHub: `per_page`/Zeitfilter). NVD empfiehlt einen API-Key gegen Rate-Limits — ggf. später via Env-Var (nicht ins Repo, `.claude/rules/security.md`).
- **BleepingComputer:** Channel-`pubDate` = Build-Zeit → fürs «neu seit» das Item-`pubDate` verwenden.

*The Hacker News / Netzwoche aus dem Research-Vorschlag: vorerst NICHT aufgenommen (Adrian wählte die anderen; können später als Ein-Zeilen-Config ergänzt werden).*

## 6. Getroffene Entscheidungen (Adrian, 2026-10-26 / S001)
1. **Runtime-Form:** Menüleisten-App (Variante A).
2. **Stack:** Python + `feedparser` + `rumps`.
3. **Quellen:** die drei fixen + **alle** Erweiterungen aus §5 (CISA KEV+Alerts, BSI/CERT-Bund, heise Security, BleepingComputer, NVD/CVE, GitHub Advisory).
4. **Takt:** Poll alle **5 Min**; laute/kritische Notification **nur bei hoher Schwere**. Hohe Schwere = Zero-Day/aktiv ausgenutzt/RCE/Notfall-Patch/Ransomware/Datenleck **oder** Treffer auf der Technologie-Watchlist (PHP, Next.js, Node, Supabase/Postgres, Docker, Infomaniak) — weil Selas eine wachsende SaaS mit aktiven Usern ist, schreit Stack-Relevantes immer sofort.
5. **CISA-Alerts = immer HIGH** (Adrian, S003). Nach dem Wrapper-Filter (§5) ist `alerts.xml` CISAs hand-kuratierter Dringlichkeits-Stream (~4/6 Wochen). Jeder verbleibende Alert bannert (`Source.always_high`), unabhängig von Watchlist/Keywords — bewusst eine neue „immer HIGH"-Klasse neben der Watchlist (#4), um Gründungsfälle wie die PHP-Krise sicher zu fangen (Regel #1). Niedrige Frequenz hält die Flut-Gefahr klein (Regel #2). **BACS/NCSC = ebenfalls `always_high`** (Adrian, S004) — dieselbe Klasse: autoritative, niederfrequente CH-Warnungen; das Keyword-Scoring hätte die PHP-Warnung nur MEDIUM gegeben (§5-Hinweis BACS), was den Gründungsfall verfehlt hätte.
6. **Wächter-fürs-Wächter** (Adrian, S003). Eine Quelle, die **still ausfällt** (403, kaputter Feed), ist der gefährlichste Zustand — der Watcher schwiege, obwohl er blind ist. Daher zählt `poller` pro Quelle die Fehlschläge in Folge (persistent in `seen.json`); ab `[health] fail_threshold` Polls (Default 6 ≈ 30 Min) meldet er **einmal** einen HIGH-Banner „Quelle X fällt aus" und re-armt bei Erholung. Schwelle filtert kurze Netz-Blips (Regel #3), `0` schaltet den Wächter ab. Der Meta-Alarm läuft über denselben Notifier-/Menü-Weg wie echte Treffer (`source_id="health"`).
7. **Fehlalarm-Tuning Runde 2** (Adrian, S006, 2026-10-27). Zwei Lärmquellen aus dem Realbetrieb entschärft, beide im bestehenden Rahmen (kein neuer Baustein, kein ADR): **(a) CERT-Bund/BSI-Schwere respektieren** — ein Stack-Watchlist-Treffer aus einer schwere-getaggten Quelle (`Source.severity_tagged`, Tag-Parsing `scoring._severity_tag`) bannert nur noch bei `[hoch]`/`[kritisch]`; `[mittel]`/`[niedrig]` landen stumm in der Liste. Grund: CERT-Bund meldet Node/Docker/Postgres fast täglich als `[mittel]` → sonst Watchlist-Dauerbanner (Regel #2). **(b) `ransomware` → MEDIUM** (wie `breach` in S005; dort noch bewusst HIGH gelassen, hier auf Adrians Entscheid revidiert): nacktes Ransomware-News ist Fremd-Lärm (Safepay: 8 CH-Fälle in 6 Wochen, ohne Selas-Bezug) → HIGH nur noch mit Stack/Provider (Watchlist) **oder** zweitem Dringlichkeits-Keyword. **Regel #1 gewahrt:** aktive Ausnutzung bannert immer (Dringlichkeits-Keyword schlägt das Schwere-Gate), ein unlesbarer Schwere-Tag bei Stack-Treffer → im Zweifel HIGH, und MEDIUM bleibt sichtbar in der Menüliste (nicht verpasst, nur leise). Verifiziert über den echten `score()`-Pfad (12 Fälle grün).
8. **Fehlalarm-Tuning Runde 3** (Adrian, S007, 2026-10-27). GitHub-Advisory-Inventar-Treffer **schwere-gegatet**: ein betroffenes Paket bannert nur noch bei GitHub-Schwere `critical`/`high` (`severity_hint`, vom Fetcher aus `adv.severity` gesetzt — wurde bisher gefüllt, aber im Scoring nie gelesen); `moderate`/`low` → MEDIUM (stumm). Grund: die 836 transitiven npm-Pakete erzeugen laufend moderate DoS/ReDoS-Advisories (undici/qs/nodemailer) → HIGH-Flut. Dieselbe Linie wie das CERT-Bund-Gate (#7): Quellen-Schwere respektieren. **Regel #1 gewahrt:** `critical`/`high` im genutzten Paket bannert weiter, KEV (aktiv ausgenutzt) läuft über den eigenen Fallback (`severity_hint=HIGH`) unverändert, MEDIUM bleibt in der Liste sichtbar. Variante „nur `critical`" bewusst **verworfen** (hätte ein high-RCE im eigenen Stack nur in die Liste gelegt). Live gegen die GitHub-API + 3 synthetische Fälle verifiziert.

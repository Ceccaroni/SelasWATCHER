# TICKET-005 — Next.js-Exposure-Check (Vercel Next.js `[hoch]`)

**Status:** ✅ **erledigt 2026-10-30 — NICHT betroffen.** Prod läuft `next 16.4.2` (= hinter dem Fix `16.4.1`), `sharp 0.35.5` (= geforderte Mindestversion). **Kein Patch nötig** (analog zum Node.js-Fall).
**Erstellt:** 2026-10-30
**Typ:** Untersuchung / Verifikation — **keine Code-Änderung am Watcher erwartet.**

## Ergebnis (2026-10-30, autoritativ belegt)

**Advisory:** WID-SEC-2026-3973 ([hoch], UPDATE 30.10.2026) = **Next.js Out-of-Band Security Update vom 14.10.2026** (Primärquelle: [nextjs.org/blog/nextjs-security-update-october-14-2026](https://nextjs.org/blog/nextjs-security-update-october-14-2026)). Drei Schwachstellen:
- **GHSA-673q-mjm6-r5xr** (Critical, **RCE**) — `use cache`-Funktionen, die mehrere Typed Arrays zurückgeben (App Router + Cache Components). Upstream React: GHSA-xqc2-xf4c-x3h3.
- **CVE-2026-96889 / GHSA-2464-fhr4-w9xw** (Critical, **RCE**) — Image-Optimization-API mit SVG auf glibc-Linux. Erfordert zusätzlich **`sharp >= 0.35.5`** (gepatchtes Next.js liefert das automatisch mit).
- **GHSA-p3m5-59mp-jv5r** (High, **DoS**) — Server Actions (App Router mit ≥1 Server Action) → CPU-Erschöpfung. Upstream React: GHSA-h3gv-c5rc-p453.

**Fix-Versionen:** `16.4.1` (Active LTS) und `15.5.28` (Maintenance LTS). **Betroffener Bereich** `>=16.0.0 <=16.4.0`; `16.4.2`/`16.4.3` sind spätere Releases auf der 16.4-Linie (nach dem Security-Patch).

**Installierte Selas-Version (prod = Docker-Build aus dem Repo):** `next 16.4.2` — `package.json:43` **und** `package-lock.json` (`node_modules/next = 16.4.2`) deckungsgleich; kein abweichender Pin im Dockerfile. `sharp` aufgelöst = **`0.35.5`** (exakt die geforderte Mindestversion).

**Semver-Verdikt:** `16.4.2` > `16.4.1` (Fix) und ausserhalb `>=16.0.0 <=16.4.0` → **alle drei Fixes enthalten.** Zusatz-Anforderung `sharp >= 0.35.5` ebenfalls erfüllt (`0.35.5`). Selas nutzt Server Actions stark (47 Dateien mit `"use server"`) — die DoS-CVE wäre also relevant gewesen, ist aber durch `16.4.2` abgedeckt. `use cache` wird nicht genutzt (0 Treffer).

**→ Nicht betroffen, kein Handlungsdruck.** Kein echter Handlungspunkt → keine `sessions.md`-Notiz nötig.

## Ziel
Klären, ob die **tatsächlich in Selas deployte Next.js-Version** von dem CERT-Bund-Advisory
„**[UPDATE] [hoch] Vercel Next.js: Mehrere Schwachstellen**" betroffen ist — also ob Adrian
**patchen muss** oder bereits auf einer gefixten Version läuft. Reine Betroffenheits-Prüfung,
analog zum Node.js-Fall (WID-SEC-2026-4117: prod lief bereits auf `node:22.23.4-alpine` =
gepatcht → kein Handlungsdruck).

**Auslöser:** Der Vercel-Next.js-`[hoch]`-Eintrag bannerte im Realbetrieb als HIGH (Stack-Treffer
`next.js` auf der Watchlist + `[hoch]` → S006-Gate greift korrekt). SelasWATCHER sagt „schau hin" —
dieses Ticket **schaut hin**.

## Aufgabe (Schritte)
1. **Advisory identifizieren.** Die exakte WID-SEC-Nummer ist noch offen. Aus dem CERT-Bund-RSS
   holen und nach dem Vercel/Next.js-Eintrag greppen:
   ```
   curl -sS -m 25 -A "SelasWATCHER/diag" \
     "https://wid.cert-bund.de/content/public/securityAdvisory/rss" | grep -i -B2 -A4 "Next.js"
   ```
   → Titel (Schwere-Tag), `link` (WID-SEC-Nummer), `description`, `pubDate` notieren.

2. **Betroffene Versionen + CVEs ermitteln (autoritativ, Regel #5 — nichts aus dem Gedächtnis).**
   - ⚠️ **Fallstrick:** Das CERT-Bund-Portal (`.../portal/wid/securityadvisory?name=WID-SEC-...`)
     ist **client-side gerendert (Nuxt/Angular)** — `WebFetch`/`curl` bekommen nur die leere Shell.
     Erprobte offene JSON/CSAF-Endpunkte gibt es nicht (alle 404). Das RSS liefert nur Titel +
     Kurzbeschreibung, **keine Versionen/CVEs.**
   - Für Versionen + CVEs die **Primärquelle** nutzen: Vercel/Next.js Security Advisories
     (`github.com/vercel/next.js/security/advisories`) bzw. die offiziellen Next.js-Release-/
     Security-Notes (nextjs.org). `WebSearch` → autoritative Seite → `WebFetch`.
   - Erfassen: betroffene Versionsbereiche, **Fix-Version(en)**, CVE-IDs, höchste Schwere.

3. **Installierte Selas-Version lesen.** Selas-Repo ist als Inventar-Pfad gesetzt
   (`config.toml` → `[inventory] project_paths = ["/Users/lanz/Documents/REPOS/Selas"]`).
   Version aus mehreren Quellen gegenprüfen (prod = Docker):
   ```
   S=/Users/lanz/Documents/REPOS/Selas
   grep -n '"next"' "$S/package.json"
   # exakte aufgelöste Version aus dem Lockfile:
   .venv/bin/python -c "import json; d=json.load(open('$S/package-lock.json')); \
     print(d['packages'].get('node_modules/next',{}).get('version'))"
   grep -rin 'next' "$S"/Dockerfile* 2>/dev/null
   ```
   Falls vorhanden kann auch `selaswatcher.inventory.load_inventory_versions(cfg)` die aufgelöste
   Lockfile-Version liefern (dasselbe, was das Scoring nutzt).

4. **Verdikt per Semver.** Liegt die installierte Version im verwundbaren Bereich?
   Für die Bereichsauswertung das projekteigene `selaswatcher/semver.py` (`in_range`) nutzen —
   nicht neu erfinden. **Regel #1:** im Zweifel (unparsebarer Bereich, Prerelease, unklare
   Version) als **betroffen** behandeln.

5. **Melden.** Knappes Ergebnis an Adrian:
   - WID-SEC-Nummer + CVEs + betroffene Bereiche (mit Quelle verlinkt).
   - Installierte Selas-Next.js-Version (prod/Docker).
   - **Betroffen: ja/nein** + ggf. Fix-Version + konkrete Patch-Empfehlung.

## Was NICHT Teil des Auftrags ist (Scope-Guard)
- **Keine** Änderung an Scoring/Watchlist/Watcher-Code. Kein S009-Tuning (eigenes Backlog-Item,
  TICKET-004).
- **Kein** Patch am Selas-Repo ausführen — nur die Empfehlung aussprechen. Selas ist ein
  fremdes, prod-kritisches Repo; Änderungen dort entscheidet Adrian separat.
- Fällt bei der Prüfung ein Watcher-Verbesserungsgedanke an → **notieren**, nicht bauen.

## Definition of Done
- WID-SEC-Nummer, CVEs und betroffene Versionsbereiche **autoritativ belegt** (Primärquelle
  verlinkt, nicht aus dem Gedächtnis — Regel #5).
- Deployte Next.js-Version aus Lockfile/Docker gelesen und zitiert.
- Semver-Verdikt (betroffen / bereits gepatcht) + klare Patch-Empfehlung an Adrian gemeldet.
- Optional: Einzeiler-Notiz in `sessions.md`, falls ein echter Handlungspunkt rausfällt.

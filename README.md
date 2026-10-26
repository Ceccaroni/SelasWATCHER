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

### Einrichten (einmalig)
```bash
cd /Pfad/zu/SelasWATCHER
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### Manuell starten (Menüleisten-App)
```bash
.venv/bin/python -m selaswatcher.app
```
Das Icon erscheint in der Menüleiste. Bei einem HIGH-Treffer wird es rot und
zeigt die Anzahl ungelesener HIGH-Meldungen; das Menü listet die letzten ~30
gemeldeten Einträge (neueste zuerst). Klick auf einen Eintrag öffnet die Quelle
im Browser. Beenden über den Menüpunkt „Beenden".

Zusätzlich gibt es weiterhin die CLI (ohne Menüleiste):
```bash
.venv/bin/python -m selaswatcher poll          # ein Durchlauf
.venv/bin/python -m selaswatcher watch         # Endlosschleife
.venv/bin/python -m selaswatcher test-notify   # Beispiel-Notification
```

### Autostart beim Login (LaunchAgent)
```bash
./scripts/install-autostart.sh     # installieren / aktualisieren (idempotent)
./scripts/uninstall-autostart.sh   # wieder entfernen
```
Das Install-Skript ermittelt das venv-Python und den Repo-Pfad, füllt die Vorlage
`launchagent/ch.selas.selaswatcher.plist` und lädt sie nach
`~/Library/LaunchAgents/`. Voraussetzung ist ein eingerichtetes `.venv` (siehe oben).

### Konfiguration
Die Config liegt als `config.toml` im Repo-Verzeichnis **oder** in
`~/.selaswatcher/` (CWD hat Vorrang). Vorlage kopieren und anpassen:
```bash
cp config.example.toml config.toml
```
Fehlt `config.toml`, laufen die eingebauten Defaults aus `selaswatcher/config.py`.

- **Quelle an-/abschalten:** eine Zeile unter `[sources]`, z. B. `"heise-security" = false`.
- **Watchlist erweitern:** einen Begriff in die `watchlist`-Liste unter `[scoring]`
  aufnehmen, z. B. `"laravel"` — Treffer sind immer HIGH.

Den Menüpunkt „Konfiguration öffnen" nutzen, um die aktive `config.toml` direkt
zu öffnen (bzw. `~/.selaswatcher/` im Finder, falls noch keine existiert).

### Log
```
~/Library/Logs/selaswatcher.log
```
(Nur im Autostart-Betrieb geschrieben; manuell gestartet geht das Log nach stderr.)

### Notifications (klickbare Banner)
SelasWATCHER meldet bevorzugt über **`terminal-notifier`** — dann ist das **Banner
klickbar** und öffnet den Artikel direkt im Standardbrowser. Ist es nicht vorhanden
oder (noch) nicht berechtigt, fällt die Meldung automatisch auf `osascript` zurück
(nicht klickbar, aber zuverlässig — es geht nie eine Meldung verloren).

Installieren (ohne Homebrew/Compiler, lädt das vorkompilierte offizielle Release):
```bash
./scripts/install-terminal-notifier.sh      # -> ~/.selaswatcher/terminal-notifier.app
```
**Einmalige Berechtigung:** Beim ersten Alarm verlangt macOS die Freigabe.
Systemeinstellungen → **Mitteilungen** → **terminal-notifier** → *Mitteilungen erlauben*.
Danach sind die Banner klickbar. (Der Absender heißt „terminal-notifier"; ein
gebrandeter Absender „SelasWATCHER" käme mit einem `py2app`-Bundle — Phase 4.)

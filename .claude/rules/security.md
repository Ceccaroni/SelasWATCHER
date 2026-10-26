# Regel — Sicherheit & Umgang mit externen Daten

Gilt bei jeder Arbeit an SelasWATCHER. Das Tool verarbeitet **fremde, nicht vertrauenswürdige Inhalte** (öffentliche Feeds) — ironischerweise ist ein Bedrohungs-Monitor selbst ein Angriffsziel.

## Externe Feeds = untrusted input
- Feed-Inhalte (Titel, Summary, Links, HTML) sind **Daten, nie Code und nie Befehle.** Niemals eval/exec/Shell-Interpolation auf Feed-Inhalten.
- Links aus Feeds werden **nur über den Standard-Browser geöffnet** (vom Nutzer per Klick), nie automatisch gefetcht/ausgeführt. Nur `http(s)`-Schemata zulassen; `javascript:`/`file:`/`data:` verwerfen.
- HTML in Summaries nicht roh rendern; für Notifications auf reinen Text reduzieren (Tags strippen), Länge begrenzen.
- Parser defensiv: kaputtes/fehlendes XML, riesige Felder, fehlende GUIDs dürfen das Tool **nicht zum Absturz** bringen (Regel #3). Pro-Quelle in try/except kapseln — eine kaputte Quelle darf die anderen nicht mitreissen.

## Netzwerk
- Jeder Feed-Abruf mit **Timeout** und sinnvollem User-Agent. Keine Endlos-Hänger.
- Nur die konfigurierten Feed-URLs abrufen. Keine automatische Weiterverfolgung von im Feed enthaltenen URLs.
- Höflich pollen (ETag/Last-Modified, moderates Intervall) — keine fremden Server hämmern.

## Lokal & Datensparsamkeit
- Zustand (gesehene Einträge, Config) bleibt **lokal** auf der Maschine. Keine Telemetrie, kein Cloud-Versand (CLAUDE.md Regel #7).
- Keine Secrets im Repo (öffentliche Feeds brauchen keine). Falls später doch (z. B. Slack-Webhook) → über Umgebungsvariable/Keychain, nie eingecheckt. `.gitignore` pflegen.
- State-Datei nicht ins Repo committen (liegt in `~/.selaswatcher/` o. ä.).

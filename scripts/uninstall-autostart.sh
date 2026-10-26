#!/usr/bin/env bash
# Deinstalliert den SelasWATCHER-LaunchAgent: entladen + Plist löschen. Idempotent.
set -euo pipefail

LABEL="ch.selas.selaswatcher"
TARGET="${HOME}/Library/LaunchAgents/${LABEL}.plist"

if [[ -f "${TARGET}" ]]; then
  launchctl unload "${TARGET}" 2>/dev/null || true
  rm -f "${TARGET}"
  echo "LaunchAgent entfernt: ${TARGET}"
else
  echo "Kein LaunchAgent installiert (${TARGET} fehlt) — nichts zu tun."
fi

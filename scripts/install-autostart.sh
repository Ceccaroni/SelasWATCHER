#!/usr/bin/env bash
# Installiert den SelasWATCHER-LaunchAgent (Autostart beim Login). Idempotent.
# Ermittelt venv-Python + Repo-Pfad, füllt die Plist-Vorlage und lädt sie per launchctl.
set -euo pipefail

LABEL="ch.selas.selaswatcher"
MODULE="selaswatcher.app"

# Repo-Root = übergeordnetes Verzeichnis dieses Skripts.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TEMPLATE="${REPO_ROOT}/launchagent/${LABEL}.plist"
PYTHON="${REPO_ROOT}/.venv/bin/python3"
TARGET="${HOME}/Library/LaunchAgents/${LABEL}.plist"
LOG_PATH="${HOME}/Library/Logs/selaswatcher.log"

if [[ ! -x "${PYTHON}" ]]; then
  echo "Fehler: venv-Python nicht gefunden unter ${PYTHON}" >&2
  echo "Zuerst venv anlegen:  python3 -m venv .venv && .venv/bin/pip install -r requirements.txt" >&2
  exit 1
fi

if [[ ! -f "${TEMPLATE}" ]]; then
  echo "Fehler: Plist-Vorlage nicht gefunden: ${TEMPLATE}" >&2
  exit 1
fi

mkdir -p "${HOME}/Library/LaunchAgents"

# Platzhalter ersetzen und an den Zielort schreiben.
sed -e "s|__PYTHON__|${PYTHON}|g" \
    -e "s|__MODULE__|${MODULE}|g" \
    -e "s|__WORKDIR__|${REPO_ROOT}|g" \
    -e "s|__HOME__|${HOME}|g" \
    "${TEMPLATE}" > "${TARGET}"

# Idempotent: ggf. laufende Instanz entladen, dann neu laden.
if launchctl list "${LABEL}" >/dev/null 2>&1; then
  launchctl unload "${TARGET}" 2>/dev/null || true
fi
launchctl load "${TARGET}"

echo "LaunchAgent installiert: ${TARGET}"
echo "Status:"
launchctl list "${LABEL}" 2>/dev/null || echo "  (noch nicht in launchctl list — ggf. kurz warten)"
echo "Log: ${LOG_PATH}"

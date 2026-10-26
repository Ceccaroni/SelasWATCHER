#!/usr/bin/env bash
# Installiert terminal-notifier (für KLICKBARE Banner) ohne Homebrew/Compiler:
# lädt das offizielle, vorkompilierte Release-Zip (universal x86_64+arm64),
# verifiziert die SHA-256 und legt die .app nach ~/.selaswatcher/ ab.
# Hintergrund: auf Intel-Macs mit macOS 26 baut brew nur noch aus Quellcode (CLT-Zwang).
set -euo pipefail

VERSION="3.1.0"
URL="https://github.com/julienXX/terminal-notifier/releases/download/${VERSION}/terminal-notifier-${VERSION}.zip"
SHA256="e969d4ae20287da1ba55495ae31dcedd8e9069deb8ce4eed24f6561a5fc3e4d5"

DEST="${HOME}/.selaswatcher"
APP="${DEST}/terminal-notifier.app"
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT

echo "Lade terminal-notifier ${VERSION} …"
curl -fsSL -o "${TMP}/tn.zip" "${URL}"

echo "Verifiziere SHA-256 …"
GOT="$(shasum -a 256 "${TMP}/tn.zip" | awk '{print $1}')"
if [[ "${GOT}" != "${SHA256}" ]]; then
  echo "Fehler: SHA-256 stimmt nicht (erwartet ${SHA256}, erhalten ${GOT})" >&2
  exit 1
fi

( cd "${TMP}" && unzip -q tn.zip )
SRC="$(find "${TMP}" -maxdepth 2 -name 'terminal-notifier.app' -type d | head -1)"
if [[ -z "${SRC}" ]]; then
  echo "Fehler: terminal-notifier.app im Zip nicht gefunden" >&2
  exit 1
fi

mkdir -p "${DEST}"
rm -rf "${APP}"
cp -R "${SRC}" "${APP}"
echo "Installiert: ${APP}"
echo
echo "WICHTIG: Beim ersten Alarm muss macOS terminal-notifier erlauben."
echo "Systemeinstellungen → Mitteilungen → 'terminal-notifier' → Mitteilungen erlauben."
echo "Bis dahin meldet SelasWATCHER automatisch über osascript (nicht klickbar)."

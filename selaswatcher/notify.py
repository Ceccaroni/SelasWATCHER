"""Native macOS-Notifications.

Bevorzugt `terminal-notifier` (Banner ist KLICKBAR -> öffnet den Artikel via
`-open URL`). Ist terminal-notifier nicht vorhanden ODER verweigert macOS ihm die
Berechtigung (Rückgabecode != 0), fällt die Meldung automatisch auf `osascript`
zurück (nicht klickbar, aber zuverlässig) — so geht nie eine Meldung verloren.

Schwere-Logik unverändert:
  HIGH   -> mit Ton (Sosumi) + Titel-Präfix "🔴".
  MEDIUM -> ohne Ton.
  LOW    -> gar keine Notification (nur Log/State).
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path

from .model import HIGH, Entry

log = logging.getLogger(__name__)

HIGH_SOUND = "Sosumi"
_TIMEOUT = 10


def _find_terminal_notifier() -> str | None:
    """terminal-notifier im PATH, in Homebrew-Pfaden oder in ~/.selaswatcher/ suchen.
    Unter launchd ist der PATH minimal -> absolute Fallback-Pfade sind nötig."""
    found = shutil.which("terminal-notifier")
    if found:
        return found
    candidates = [
        Path.home() / ".selaswatcher" / "terminal-notifier.app" / "Contents" / "MacOS" / "terminal-notifier",
        Path("/usr/local/bin/terminal-notifier"),
        Path("/opt/homebrew/bin/terminal-notifier"),
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


TERMINAL_NOTIFIER = _find_terminal_notifier()


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text[:limit].rstrip() + "…" if len(text) > limit else text


def _parts(entry: Entry) -> tuple[str, str, str]:
    """(title, subtitle, message) — gemeinsam für beide Notifier-Wege."""
    prefix = "🔴 " if entry.severity == HIGH else ""
    title = _truncate(f"{prefix}{entry.title}", 120)
    subtitle = f"{entry.source_name} · {entry.severity}"
    message = _truncate(entry.summary, 200) or entry.url or "Neue Meldung"
    return title, subtitle, message


def notify_entry(entry: Entry) -> bool:
    """Feuert ein Banner NUR für HIGH (drop-everything: eigener Stack oder kritisch).
    MEDIUM/LOW erzeugen bewusst kein Banner — sie landen stumm in der Menüliste
    (Regel #2: keine Alarm-Flut). True, wenn ein Banner gesendet wurde.
    Erst terminal-notifier (klickbar), bei Fehlschlag Fallback auf osascript."""
    if entry.severity != HIGH:
        return False

    if TERMINAL_NOTIFIER and _notify_terminal(entry):
        return True
    return _notify_osascript(entry)


def notify_sample() -> bool:
    """Beispiel-HIGH-Notification für den Smoke-Test (ohne Netz)."""
    sample = Entry(
        source_id="test",
        source_name="SelasWATCHER Test",
        dedup_id="test-1",
        title='Zero-Day in PHP aktiv ausgenutzt — "Notfall-Patch"',
        url="https://example.com/advisory",
        summary="Beispiel-Notification zum Prüfen der Anbindung. Klick öffnet den Link.",
        published=None,
        lang="de",
        severity=HIGH,
        matched_terms=["php", "zero-day", "aktiv ausgenutzt"],
    )
    return notify_entry(sample)


# --- terminal-notifier (klickbar) -----------------------------------------


def _notify_terminal(entry: Entry) -> bool:
    """Via terminal-notifier. Argumente als Liste (keine Shell) -> kein Escaping/Injection.
    Rückgabe False bei Fehler (z. B. fehlende Notification-Berechtigung) -> Fallback."""
    title, subtitle, message = _parts(entry)
    cmd = [
        TERMINAL_NOTIFIER,
        "-title", title,
        "-subtitle", subtitle,
        "-message", message,
    ]
    if entry.url:
        cmd += ["-open", entry.url]  # macht das Banner klickbar
    if entry.severity == HIGH:
        cmd += ["-sound", HIGH_SOUND]
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, timeout=_TIMEOUT, text=True)
        if res.returncode == 0:
            return True
        log.warning("terminal-notifier fehlgeschlagen (rc=%s): %s — Fallback osascript",
                    res.returncode, (res.stderr or res.stdout).strip())
        return False
    except (subprocess.SubprocessError, OSError) as exc:
        log.warning("terminal-notifier nicht ausführbar (%s) — Fallback osascript", exc)
        return False


# --- osascript-Fallback (nicht klickbar) ----------------------------------


def _escape(text: str) -> str:
    """Backslash und Anführungszeichen für AppleScript-String escapen, Zeilenumbrüche raus."""
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return text.replace("\r", " ").replace("\n", " ")


def _notify_osascript(entry: Entry) -> bool:
    title, subtitle, message = _parts(entry)
    body = entry.url or message
    script = (
        f'display notification "{_escape(body)}" '
        f'with title "{_escape(title)}" '
        f'subtitle "{_escape(subtitle)}"'
    )
    if entry.severity == HIGH:
        script += f' sound name "{_escape(HIGH_SOUND)}"'
    try:
        subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=_TIMEOUT)
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        log.error("Notification fehlgeschlagen (osascript): %s", exc)
        return False

"""Native macOS-Notifications via osascript.

HIGH  -> mit Ton (Sosumi) + Titel-Präfix "🔴".
MEDIUM-> ohne Ton.
LOW   -> gar keine Notification (nur Log/State).

Feed-Text wird für den AppleScript-String escaped (Anführungszeichen/Backslashes);
osascript wird ohne Shell aufgerufen (Liste statt String) — keine Injection.
"""

from __future__ import annotations

import logging
import subprocess

from .model import HIGH, MEDIUM, Entry

log = logging.getLogger(__name__)

HIGH_SOUND = "Sosumi"
_OSASCRIPT_TIMEOUT = 10


def _escape(text: str) -> str:
    """Backslash und Anführungszeichen für AppleScript-String escapen, Zeilenumbrüche raus."""
    text = text.replace("\\", "\\\\").replace('"', '\\"')
    return text.replace("\r", " ").replace("\n", " ")


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    return text[:limit].rstrip() + "…" if len(text) > limit else text


def notify_entry(entry: Entry) -> bool:
    """Feuert eine Notification abhängig von entry.severity. True, wenn gesendet."""
    if entry.severity not in (HIGH, MEDIUM):
        return False

    prefix = "🔴 " if entry.severity == HIGH else ""
    title = _truncate(f"{prefix}{entry.title}", 120)
    subtitle = f"{entry.source_name} · {entry.severity}"
    body = entry.url or _truncate(entry.summary, 200)

    script = (
        f'display notification "{_escape(body)}" '
        f'with title "{_escape(title)}" '
        f'subtitle "{_escape(subtitle)}"'
    )
    if entry.severity == HIGH:
        script += f' sound name "{_escape(HIGH_SOUND)}"'

    return _run(script)


def notify_sample() -> bool:
    """Beispiel-HIGH-Notification für den Smoke-Test (ohne Netz)."""
    sample = Entry(
        source_id="test",
        source_name="SelasWATCHER Test",
        dedup_id="test-1",
        title='Zero-Day in PHP aktiv ausgenutzt — "Notfall-Patch"',
        url="https://example.com/advisory",
        summary="Beispiel-Notification zum Prüfen der osascript-Anbindung.",
        published=None,
        lang="de",
        severity=HIGH,
        matched_terms=["php", "zero-day", "aktiv ausgenutzt"],
    )
    return notify_entry(sample)


def _run(script: str) -> bool:
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            timeout=_OSASCRIPT_TIMEOUT,
        )
        return True
    except (subprocess.SubprocessError, OSError) as exc:
        log.error("Notification fehlgeschlagen: %s", exc)
        return False

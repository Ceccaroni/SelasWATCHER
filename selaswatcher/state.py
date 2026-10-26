"""Dedup-State + ETag/Last-Modified-Cache in ~/.selaswatcher/seen.json.

Pro Quelle: gesehene dedup_ids, Versions-Stände (published je id, für
[UPDATE]-Erkennung), etag/modified (conditional GET) und last_run.

First-Run-Baseline: Beim allerersten Lauf einer Quelle werden alle aktuell
vorhandenen Einträge still als gesehen markiert und NICHT gemeldet.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .model import Entry

log = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path.home() / ".selaswatcher" / "seen.json"

# Max. gesehene IDs je Quelle. Großzügig über jedem realen Feed-Fenster, damit
# gedeckelte (= alte, längst nicht mehr ausgelieferte) IDs nicht erneut als "neu"
# auftauchen. `<= 0` schaltet das Deckeln ab.
DEFAULT_SEEN_CAP = 2000


def _parse_iso(value: str | None) -> datetime | None:
    """Robustes ISO-8601-Parsen (inkl. 'Z' und reinem Datum)."""
    if not value:
        return None
    s = value.strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        try:
            return datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            return None


class State:
    """Persistenter Dedup-/Cache-Zustand."""

    def __init__(self, path: Path = DEFAULT_STATE_PATH) -> None:
        self.path = Path(path)
        self._data: dict[str, Any] = {}
        self.load()

    # --- Laden / Speichern -------------------------------------------------

    def load(self) -> None:
        if not self.path.is_file():
            self._data = {}
            return
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                self._data = data
            else:
                log.warning("seen.json hat unerwartetes Format — starte leer")
                self._data = {}
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("seen.json unlesbar (%s) — starte leer", exc)
            self._data = {}

    def save(self) -> None:
        """Atomar schreiben (temp -> os.replace)."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        except OSError as exc:
            log.error("State konnte nicht gespeichert werden: %s", exc)

    # --- Pro-Quelle-Zugriff ------------------------------------------------

    def source_state(self, source_id: str) -> dict[str, Any]:
        return self._data.setdefault(
            source_id,
            {
                "seen": [],
                "versions": {},
                "etag": None,
                "modified": None,
                "last_run": None,
                "initialized": False,
            },
        )

    def is_first_run(self, source_id: str) -> bool:
        return not self.source_state(source_id).get("initialized", False)

    def last_run(self, source_id: str) -> datetime | None:
        return _parse_iso(self.source_state(source_id).get("last_run"))

    def set_last_run(self, source_id: str, when: datetime | None = None) -> None:
        when = when or datetime.now(timezone.utc)
        self.source_state(source_id)["last_run"] = when.isoformat()

    # --- Dedup-Logik -------------------------------------------------------

    def is_new(self, source_id: str, entry: Entry) -> bool:
        st = self.source_state(source_id)
        if entry.dedup_id not in st["seen"]:
            return True
        # Gleiche ID, aber neuere published-Version (z. B. CERT-Bund [UPDATE]).
        prev = st["versions"].get(entry.dedup_id)
        prev_dt = _parse_iso(prev)
        if entry.published and prev_dt and entry.published > prev_dt:
            return True
        return False

    def filter_new(self, source_id: str, entries: list[Entry]) -> list[Entry]:
        return [e for e in entries if self.is_new(source_id, e)]

    def mark_seen(self, source_id: str, entries: list[Entry]) -> None:
        st = self.source_state(source_id)
        for e in entries:
            if e.dedup_id not in st["seen"]:
                st["seen"].append(e.dedup_id)
            if e.published:
                st["versions"][e.dedup_id] = e.published.isoformat()

    def mark_all_seen(self, source_id: str, entries: list[Entry]) -> None:
        """First-Run-Baseline: alles still als gesehen markieren."""
        st = self.source_state(source_id)
        st["initialized"] = True
        self.mark_seen(source_id, entries)

    def prune(self, cap: int = DEFAULT_SEEN_CAP) -> None:
        """Pro Quelle die seen-Liste auf die letzten `cap` IDs deckeln (FIFO:
        älteste zuerst raus) und versions passend mitziehen. Verhindert, dass
        seen.json unbegrenzt wächst. `cap <= 0` deaktiviert das Deckeln."""
        if cap <= 0:
            return
        for st in self._data.values():
            if not isinstance(st, dict):
                continue
            seen = st.get("seen")
            if not isinstance(seen, list) or len(seen) <= cap:
                continue
            kept = seen[-cap:]
            st["seen"] = kept
            versions = st.get("versions")
            if isinstance(versions, dict):
                kept_set = set(kept)
                st["versions"] = {k: v for k, v in versions.items() if k in kept_set}

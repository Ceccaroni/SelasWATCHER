"""Orchestrierung: je Quelle fetch -> neue Einträge -> score -> notify.

Robustheit: jede Quelle in try/except — eine kaputte Quelle bricht die anderen
nicht ab. First-Run einer Quelle = stille Baseline (keine Meldungen).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from .model import HIGH, MEDIUM, Entry
from .notify import notify_entry
from .scoring import score
from .sources import enabled_sources, fetch_source
from .state import State

log = logging.getLogger(__name__)


@dataclass
class SourceResult:
    source_id: str
    fetched: int = 0
    new: int = 0
    high: int = 0
    medium: int = 0
    error: str | None = None


@dataclass
class PollResult:
    results: list[SourceResult] = field(default_factory=list)


def poll_once(
    config: dict[str, Any],
    state: State,
    notifier: Callable[[Entry], bool] = notify_entry,
) -> PollResult:
    """Ein Zyklus über alle aktivierten Quellen."""
    poll = PollResult()

    for source in enabled_sources(config):
        res = SourceResult(source_id=source.id)
        try:
            entries = fetch_source(source, state, config)
            res.fetched = len(entries)

            if state.is_first_run(source.id):
                # Stille Baseline — keine Altmeldungs-Flut.
                state.mark_all_seen(source.id, entries)
                log.info("%s: First-Run-Baseline (%d Einträge still markiert)", source.id, res.fetched)
            else:
                new_entries = state.filter_new(source.id, entries)
                res.new = len(new_entries)
                for entry in new_entries:
                    score(entry, config)
                    if entry.severity in (HIGH, MEDIUM):
                        if notifier(entry):
                            if entry.severity == HIGH:
                                res.high += 1
                            else:
                                res.medium += 1
                        log.info("[%s] %s — %s", entry.severity, entry.source_name, entry.title)
                state.mark_seen(source.id, new_entries)

            state.set_last_run(source.id)
        except Exception as exc:  # bewusst breit: Quelle isolieren (Regel #3)
            res.error = f"{type(exc).__name__}: {exc}"
            log.warning("Quelle %s fehlgeschlagen: %s", source.id, res.error)

        poll.results.append(res)

    state.save()
    return poll


def format_summary(poll: PollResult) -> str:
    """Kompakte Zusammenfassung: je Quelle geholt / neu / gemeldet(H/M) + Fehler."""
    lines = ["Quelle                geholt   neu  gemeldet"]
    for r in poll.results:
        if r.error:
            lines.append(f"{r.source_id:<20}  FEHLER: {r.error}")
        else:
            lines.append(
                f"{r.source_id:<20} {r.fetched:>6} {r.new:>5}  "
                f"H{r.high}/M{r.medium}"
            )
    return "\n".join(lines)

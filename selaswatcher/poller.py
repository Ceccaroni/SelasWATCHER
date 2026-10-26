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
from .state import DEFAULT_SEEN_CAP, State

log = logging.getLogger(__name__)


@dataclass
class SourceResult:
    source_id: str
    fetched: int = 0
    new: int = 0
    high: int = 0
    medium: int = 0
    failed_high: int = 0  # HIGH, deren Zustellung scheiterte -> Retry (nicht als gesehen verbucht)
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
                # Nur erfolgreich behandelte Einträge als gesehen verbuchen. Eine
                # HIGH-Meldung, deren Zustellung scheiterte, bleibt bewusst "neu",
                # damit der nächste Poll sie erneut versucht (Regel #1: eine
                # verpasste Bedrohung ist der einzige echte Fehler).
                to_mark: list[Entry] = []
                for entry in new_entries:
                    score(entry, config)
                    if entry.severity == HIGH:
                        if notifier(entry):
                            res.high += 1
                            to_mark.append(entry)
                            log.info("[%s] %s — %s", entry.severity, entry.source_name, entry.title)
                        else:
                            # Beide Notifier-Wege gescheitert -> NICHT verbuchen (Retry).
                            # Das rote Menü-Icon signalisiert es bereits sichtbar.
                            res.failed_high += 1
                            log.error(
                                "HIGH-Zustellung FEHLGESCHLAGEN — Retry im nächsten Poll: %s — %s",
                                entry.source_name, entry.title,
                            )
                    else:
                        if entry.severity == MEDIUM:
                            notifier(entry)  # bewusst stumm (kein Banner) -> nur Menüliste
                            res.medium += 1
                            log.info("[%s] %s — %s", entry.severity, entry.source_name, entry.title)
                        to_mark.append(entry)  # MEDIUM/LOW gelten als behandelt
                state.mark_seen(source.id, to_mark)

            state.set_last_run(source.id)
        except Exception as exc:  # bewusst breit: Quelle isolieren (Regel #3)
            res.error = f"{type(exc).__name__}: {exc}"
            log.warning("Quelle %s fehlgeschlagen: %s", source.id, res.error)

        poll.results.append(res)

    # seen-Liste deckeln, damit seen.json nicht unbegrenzt wächst (Regel #3).
    cap = int(config.get("state", {}).get("seen_cap", DEFAULT_SEEN_CAP))
    state.prune(cap)
    state.save()
    return poll


def format_summary(poll: PollResult) -> str:
    """Kompakte Zusammenfassung: je Quelle geholt / neu / gemeldet(H/M) + Fehler."""
    lines = ["Quelle                geholt   neu  gemeldet"]
    for r in poll.results:
        if r.error:
            lines.append(f"{r.source_id:<20}  FEHLER: {r.error}")
        else:
            line = (
                f"{r.source_id:<20} {r.fetched:>6} {r.new:>5}  "
                f"H{r.high}/M{r.medium}"
            )
            if r.failed_high:
                line += f"  ⚠ {r.failed_high} HIGH-Zustellung fehlgeschlagen (Retry)"
            lines.append(line)
    return "\n".join(lines)

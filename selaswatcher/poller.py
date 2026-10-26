"""Orchestrierung: je Quelle fetch -> neue Einträge -> score -> notify.

Robustheit: jede Quelle in try/except — eine kaputte Quelle bricht die anderen
nicht ab. First-Run einer Quelle = stille Baseline (keine Meldungen).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable

from .model import HIGH, MEDIUM, Entry
from .notify import notify_entry
from .scoring import score
from .sources import Source, enabled_sources, fetch_source
from .state import DEFAULT_SEEN_CAP, State

log = logging.getLogger(__name__)

# Wächter-fürs-Wächter: so viele Fehlschläge IN FOLGE -> einmal HIGH-Alarm,
# dass eine Quelle still ausfällt. Überschreibbar via [health] fail_threshold.
DEFAULT_FAIL_THRESHOLD = 6


def _health_entry(source: Source, streak: int, error: str | None) -> Entry:
    """Synthetischer HIGH-Eintrag: 'Quelle X fällt aus'. Geht über denselben
    Notifier-Weg wie echte Treffer (Banner + rotes Menü-Icon). URL leer -> nicht
    klickbar; dedup_id mit Minuten-Stempel, damit ein SPÄTERER Ausfall erneut meldet."""
    now = datetime.now(timezone.utc)
    return Entry(
        source_id="health",
        source_name="SelasWATCHER",
        dedup_id=f"health:{source.id}:{now:%Y%m%d%H%M}",
        title=f"⚠ Quelle {source.name!r} fällt aus ({streak} Polls in Folge)",
        url="",
        summary=(
            f"Seit {streak} Abrufen kein Erfolg (letzter Fehler: {error}). "
            f"Der Watcher könnte über diese Quelle Warnungen verpassen — bitte prüfen."
        ),
        published=now,
        lang="de",
        severity=HIGH,
        matched_terms=["health"],
    )


@dataclass
class SourceResult:
    source_id: str
    fetched: int = 0
    new: int = 0
    high: int = 0
    medium: int = 0
    failed_high: int = 0  # HIGH, deren Zustellung scheiterte -> Retry (nicht als gesehen verbucht)
    error: str | None = None
    health_alarm: bool = False  # Quelle fiel lange genug aus -> Health-Alarm gemeldet


@dataclass
class PollResult:
    results: list[SourceResult] = field(default_factory=list)


def _fail_threshold(config: dict[str, Any]) -> int:
    return int(config.get("health", {}).get("fail_threshold", DEFAULT_FAIL_THRESHOLD))


def _maybe_health_alarm(
    source: Source,
    state: State,
    config: dict[str, Any],
    notifier: Callable[[Entry], bool],
    error: str | None,
) -> bool:
    """Fehlschlag verbuchen; ab `fail_threshold` Polls in Folge EINMAL Alarm melden.
    Bei gescheiterter Zustellung nicht als gewarnt markieren -> Retry nächster Poll
    (Regel #1). Gibt True zurück, wenn in diesem Poll ein Health-Alarm gesendet wurde."""
    threshold = _fail_threshold(config)
    streak = state.note_fetch_fail(source.id)
    if threshold <= 0 or streak < threshold or state.health_warned(source.id):
        return False
    if notifier(_health_entry(source, streak, error)):
        state.set_health_warned(source.id, True)
        log.error("Quelle %s seit %d Polls down -> Health-Alarm gemeldet", source.id, streak)
        return True
    log.error("Quelle %s seit %d Polls down -> Health-Alarm-Zustellung fehlgeschlagen (Retry)",
              source.id, streak)
    return False


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
            # Gesund: Fehlerzähler + Health-Warnung zurücksetzen (Erholung still loggen).
            prev_streak = state.note_fetch_ok(source.id)
            if _fail_threshold(config) > 0 and prev_streak >= _fail_threshold(config):
                log.info("Quelle %s wieder erreichbar (war %d Polls down)", source.id, prev_streak)
        except Exception as exc:  # bewusst breit: Quelle isolieren (Regel #3)
            res.error = f"{type(exc).__name__}: {exc}"
            log.warning("Quelle %s fehlgeschlagen: %s", source.id, res.error)
            # Wächter-fürs-Wächter: Dauerausfall einmal laut melden (Regel #1).
            res.health_alarm = _maybe_health_alarm(source, state, config, notifier, res.error)

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
            line = f"{r.source_id:<20}  FEHLER: {r.error}"
            if r.health_alarm:
                line += "  🚨 Health-Alarm gemeldet (Dauerausfall)"
            lines.append(line)
        else:
            line = (
                f"{r.source_id:<20} {r.fetched:>6} {r.new:>5}  "
                f"H{r.high}/M{r.medium}"
            )
            if r.failed_high:
                line += f"  ⚠ {r.failed_high} HIGH-Zustellung fehlgeschlagen (Retry)"
            lines.append(line)
    return "\n".join(lines)

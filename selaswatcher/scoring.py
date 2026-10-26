"""Schwere-Bewertung HIGH / MEDIUM / LOW.

Stichwortlisten und Watchlist kommen vollständig aus der Config. Technologie-
Watchlist-Treffer sind immer HIGH (konzept.md §6: Selas = wachsende SaaS mit
aktiven Usern, Stack-Relevantes schreit sofort).

Matching: Watchlist per Substring (Regel #1 — lieber zu viel melden, kritische
Tech nie verpassen). Keywords per Wortgrenze (Regel #2 — Fehlalarm-Flut
vermeiden, z. B. 'RCE' soll nicht in 'source' matchen).
"""

from __future__ import annotations

import re
from typing import Any

from .model import HIGH, LOW, MEDIUM, Entry


def _watchlist_hits(text: str, terms: list[str]) -> list[str]:
    return [t for t in terms if t.lower() in text]


def _keyword_hits(text: str, terms: list[str]) -> list[str]:
    hits = []
    for t in terms:
        if re.search(r"\b" + re.escape(t.lower()) + r"\b", text):
            hits.append(t)
    return hits


def score(entry: Entry, config: dict[str, Any]) -> None:
    """Setzt entry.severity und entry.matched_terms in-place."""
    scfg = config.get("scoring", {})
    watchlist = scfg.get("watchlist", [])
    high_kw = scfg.get("high_keywords", [])
    generic_kw = scfg.get("generic_keywords", [])

    text = f"{entry.title} {entry.summary}".lower()

    matched: list[str] = []
    wl = _watchlist_hits(text, watchlist)
    hk = _keyword_hits(text, high_kw)
    gk = _keyword_hits(text, generic_kw)
    matched.extend(wl)
    matched.extend(hk)
    matched.extend(gk)
    entry.matched_terms = matched

    # HIGH: Watchlist-Treffer, HIGH-Keyword, oder Quellen-Hint (KEV/GitHub crit|high).
    if wl or hk or entry.severity_hint == HIGH:
        entry.severity = HIGH
        return

    # MEDIUM: generischer Security-Treffer oder Eintrag einer reinen Security-Quelle.
    from .sources import SOURCES

    source = SOURCES.get(entry.source_id)
    is_security_source = bool(source and source.security)
    if gk or is_security_source:
        entry.severity = MEDIUM
        return

    entry.severity = LOW

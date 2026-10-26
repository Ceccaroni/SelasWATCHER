"""Schwere-Bewertung HIGH / MEDIUM / LOW.

Stichwortlisten und Watchlist kommen vollständig aus der Config. Matching durchweg
per **Wortgrenze** (Regel #2 — Fehlalarm-Flut vermeiden: 'node' darf nicht in
beliebigem Text matchen, 'RCE' nicht in 'source').

Quellentyp-bewusst (Lehre aus der 52-Alarm-Flut):
- **Vuln-Datenbanken** (CISA KEV, NVD, GitHub = `source.vulndb`) sind ein Firehose
  über ALLE Hersteller. Sie melden nur, wenn der EIGENE Stack getroffen ist
  (Watchlist). Alles andere ist für uns irrelevant -> LOW (keine Meldung).
- **News-Quellen** (inside-it, 20min, heise, CERT-Bund, …): HIGH bei Watchlist/
  Kritisch-Keyword, MEDIUM bei generischem Security-Keyword, sonst LOW.

Nur HIGH erzeugt ein Banner (siehe notify.py); MEDIUM landet stumm in der Menüliste.
"""

from __future__ import annotations

import re
from typing import Any

from .model import HIGH, LOW, MEDIUM, Entry


def _word_hits(text: str, terms: list[str]) -> list[str]:
    """Terme mit Wortgrenze (\\b) suchen, case-insensitive (text ist bereits lower)."""
    hits = []
    for t in terms:
        if re.search(r"\b" + re.escape(t.lower()) + r"\b", text):
            hits.append(t)
    return hits


# Rückwärtskompatible Aliase (werden in Diagnosen genutzt).
_watchlist_hits = _word_hits
_keyword_hits = _word_hits


def score(entry: Entry, config: dict[str, Any]) -> None:
    """Setzt entry.severity und entry.matched_terms in-place."""
    scfg = config.get("scoring", {})
    watchlist = scfg.get("watchlist", [])
    high_kw = scfg.get("high_keywords", [])
    generic_kw = scfg.get("generic_keywords", [])

    from .sources import SOURCES

    source = SOURCES.get(entry.source_id)

    # Vuln-Datenbank (Firehose): nur melden, wenn der EIGENE Stack betroffen ist.
    if source and source.vulndb:
        # Paketgenauer Abgleich (Dependabot-Prinzip): nennt die Quelle betroffene
        # Pakete (GitHub Advisory) und ist ein Inventar konfiguriert, dann HIGH nur,
        # wenn ein tatsächlich genutztes Paket dabei ist.
        from .inventory import load_inventory

        inv = load_inventory(config)
        if entry.affected_packages and inv:
            hits = sorted({p.lower() for p in entry.affected_packages} & inv)
            entry.matched_terms = hits
            entry.severity = HIGH if hits else LOW
            return
        # Fallback (KEV ohne Paketangabe, oder GitHub ohne Inventar): Watchlist
        # nur gegen den TITEL (= Produktname) — die Beschreibung erzeugt Fehltreffer.
        wl = _word_hits(entry.title.lower(), watchlist)
        entry.matched_terms = wl
        entry.severity = HIGH if wl else LOW
        return

    # News-Quelle: Titel + Summary bewerten.
    text = f"{entry.title} {entry.summary}".lower()
    wl = _word_hits(text, watchlist)
    hk = _word_hits(text, high_kw)
    gk = _word_hits(text, generic_kw)
    entry.matched_terms = wl + hk + gk

    # Stack oder Kritisch-Keyword -> HIGH (Banner).
    if wl or hk:
        entry.severity = HIGH
        return
    # Generischer Security-Treffer -> MEDIUM (nur Menüliste, kein Banner).
    if gk:
        entry.severity = MEDIUM
        return
    entry.severity = LOW

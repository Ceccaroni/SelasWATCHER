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


# Schwere-Tag autoritativer DE-Quellen (CERT-Bund/BSI): Titel führt "[mittel]",
# "[hoch]", "[kritisch]" o. ä. (ggf. nach "[UPDATE]"). Treibt bei source.severity_tagged
# die Banner-Entscheidung, damit die tägliche [mittel]-Flut (Node/Docker/Postgres)
# nicht mehr bannert (Regel #2).
_SEV_TAG_RE = re.compile(r"\[(kritisch|hoch|mittel|niedrig)\]", re.I)


def _severity_tag(title: str) -> str | None:
    """CERT-Bund-Schwere aus dem Titel ziehen ('hoch'/'kritisch'/'mittel'/'niedrig') oder None."""
    m = _SEV_TAG_RE.search(title)
    return m.group(1).lower() if m else None


def score(entry: Entry, config: dict[str, Any]) -> None:
    """Setzt entry.severity und entry.matched_terms in-place."""
    scfg = config.get("scoring", {})
    watchlist = scfg.get("watchlist", [])
    high_kw = scfg.get("high_keywords", [])
    generic_kw = scfg.get("generic_keywords", [])

    from .sources import SOURCES

    source = SOURCES.get(entry.source_id)

    # Kuratierte Dringlichkeits-Quelle (CISA-Alerts, BACS): jeder Eintrag ist per
    # Definition ein "sofort handeln"-Signal -> HIGH (konzept.md §6).
    if source and source.always_high:
        entry.severity = HIGH
        entry.matched_terms = ["always_high"]
        return

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
            # BANNER (HIGH) nur bei kritischer/hoher Advisory-Schwere (severity_hint,
            # vom GitHub-Fetcher gesetzt). Ein moderate/low Advisory in einem genutzten
            # (oft transitiven) Paket — meist DoS/ReDoS, z. B. undici/qs/nodemailer —
            # ist kein Sofort-Handeln -> MEDIUM, stumm in der Liste (S007, Regel #2).
            if not hits:
                entry.severity = LOW  # nicht unser Paket
            elif entry.severity_hint == HIGH:
                entry.severity = HIGH
            else:
                entry.severity = MEDIUM
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

    # Dringlichkeits-Keyword (aktiv ausgenutzt, zero-day, rce, unauthenticated, …) -> immer HIGH.
    # Regel #1: aktive Ausnutzung nie verschlucken, egal wie die Quelle sie einstuft.
    # (ransomware/breach sind bewusst NICHT hier, sondern generisch -> MEDIUM, siehe config.py.)
    if hk:
        entry.severity = HIGH
        return

    # Schwere-getaggte Quelle (CERT-Bund/BSI): Stack-Treffer bannert nur noch, wenn die
    # Quelle selbst hoch/kritisch meldet — die tägliche [mittel]-Flut (Node/Docker/Postgres)
    # landet stumm in der Liste (Regel #2). Unlesbarer Tag -> im Zweifel laut (Regel #1).
    # Fremd-Produkte (kein Stack-Bezug) bannern nicht: generisch -> MEDIUM, sonst LOW.
    if source and source.severity_tagged:
        if wl:
            tag = _severity_tag(entry.title)
            entry.severity = MEDIUM if tag in ("mittel", "niedrig") else HIGH
            return
        entry.severity = MEDIUM if gk else LOW
        return

    # Übrige News-Quellen: Stack-Treffer -> HIGH (Banner).
    if wl:
        entry.severity = HIGH
        return
    # Generischer Security-Treffer -> MEDIUM (nur Menüliste, kein Banner).
    if gk:
        entry.severity = MEDIUM
        return
    entry.severity = LOW

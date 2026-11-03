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
from .semver import in_range


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


# Rang der Titel-Schwere (kritisch=4 … niedrig=1; 0 = kein/unlesbarer Tag). Für die
# [UPDATE]-Re-Banner-Dämpfung (S012): ein schwere-getaggtes Advisory, das nur mit neuer
# published-Version erneut auftaucht, bannert nur bei Schwere-Anstieg erneut (Regel #2);
# gleicher/niedrigerer Rang -> stumm. Rang 0 (unlesbar) -> im Zweifel laut (Regel #1).
_SEV_RANK = {"niedrig": 1, "mittel": 2, "hoch": 3, "kritisch": 4}


def severity_tag_rank(title: str) -> int:
    """Rang der Titel-Schwere (1–4; 0 = kein/unlesbarer Tag)."""
    return _SEV_RANK.get(_severity_tag(title) or "", 0)


def _version_affected(
    name: str,
    ranges: dict[str, list[str]],
    installed: dict[str, set[str]],
) -> bool:
    """Ist die INSTALLIERTE Version von `name` wirklich im verwundbaren Bereich?

    Dependabot-Prinzip: ein Advisory für ein genutztes Paket zählt nur, wenn die konkret
    installierte Version im `vulnerable_version_range` liegt (sonst ist bereits gepatcht).

    Regel #1 — nur SICHER entwarnen: Fehlt der Bereich (z. B. KEV ohne Range), fehlt die
    installierte Version (Paket nur in package.json, kein Lockfile) oder ist der Bereich
    nicht eindeutig auswertbar (semver.in_range -> None), gilt das Paket als betroffen.
    `False` nur, wenn ALLE installierten Versionen nachweislich ausserhalb liegen."""
    rngs = ranges.get(name)
    if not rngs:
        return True  # kein Bereich bekannt -> im Zweifel melden
    vers = installed.get(name)
    if not vers:
        return True  # installierte Version unbekannt -> im Zweifel melden
    for ver in vers:
        for rng in rngs:
            res = in_range(ver, rng)
            if res is None or res is True:  # unsicher ODER drin -> betroffen
                return True
    return False  # jede installierte Version nachweislich ausserhalb -> gepatcht


def score(entry: Entry, config: dict[str, Any]) -> None:
    """Setzt entry.severity und entry.matched_terms in-place."""
    scfg = config.get("scoring", {})
    watchlist = scfg.get("watchlist", [])
    high_kw = scfg.get("high_keywords", [])
    generic_kw = scfg.get("generic_keywords", [])
    infra_kw = scfg.get("infra_keywords", [])

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
        from .inventory import load_inventory, load_inventory_versions

        inv = load_inventory(config)
        if entry.affected_packages and inv:
            name_hits = sorted({p.lower() for p in entry.affected_packages} & inv)
            # VERSIONS-GATE (Dependabot-Prinzip, S008): nur die Pakete behalten, deren
            # INSTALLIERTE Version wirklich im verwundbaren Bereich liegt. Das killt die
            # Fehlalarm-Flut aus Advisories gegen Versionen, die man längst gepatcht hat
            # (z. B. alle undici-Advisories < 7.30.1, während 7.30.1 installiert ist).
            # Regel #1: unbekannter Bereich/unbekannte Version/uneindeutig -> gilt als betroffen.
            versions = load_inventory_versions(config)
            hits = [n for n in name_hits if _version_affected(n, entry.affected_ranges, versions)]
            entry.matched_terms = hits
            # BANNER (HIGH) nur bei kritischer/hoher Advisory-Schwere (severity_hint,
            # vom GitHub-Fetcher gesetzt). Ein moderate/low Advisory in einem genutzten
            # (oft transitiven) Paket — meist DoS/ReDoS, z. B. undici/qs/nodemailer —
            # ist kein Sofort-Handeln -> MEDIUM, stumm in der Liste (S007, Regel #2).
            if not hits:
                entry.severity = LOW  # nicht unser Paket ODER installierte Version nicht betroffen
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
    inf = _word_hits(text, infra_kw)
    entry.matched_terms = wl + hk + gk + inf

    # Dringlichkeits-Keyword (aktiv ausgenutzt, zero-day, rce, …) -> HIGH NUR mit Stack-Bezug
    # (Watchlist) ODER Host-/Infra-Bezug. Selas self-hostet (Ubuntu-VPS + Docker), daher bleiben
    # Kernel-/OS-/SSH-/TLS-/Container-Escape-Lücken laut (S010: Kernel-UAF, unauth Remote-Root).
    # Ein Dringlichkeits-Keyword ALLEIN (stack-fremde Story: GitLab, Drupal, Ivanti, …) -> MEDIUM,
    # stumm in der Liste (TICKET-004). Regel #1: der PHP-Gründungsfall hängt an BACS/CISA
    # always_high (oben), NICHT an diesem Keyword-Pfad.
    if hk and (wl or inf):
        entry.severity = HIGH
        return

    # Schwere-getaggte Quelle (CERT-Bund/BSI): Stack-Treffer bannert nur bei hoch/kritisch —
    # die tägliche [mittel]-Flut (Node/Docker/Postgres) landet stumm in der Liste (S006).
    # Unlesbarer Tag bei Stack-Treffer -> im Zweifel laut (Regel #1). Ohne Stack: ein
    # Dringlichkeits-Keyword allein oder generischer Treffer -> MEDIUM (stumm), sonst LOW.
    if source and source.severity_tagged:
        if wl:
            tag = _severity_tag(entry.title)
            entry.severity = MEDIUM if tag in ("mittel", "niedrig") else HIGH
            return
        entry.severity = MEDIUM if (hk or gk) else LOW
        return

    # Übrige News-Quellen: Stack-Treffer -> HIGH (Banner).
    if wl:
        entry.severity = HIGH
        return
    # Dringlichkeits-Keyword allein (stack-fremd) ODER generischer Security-Treffer -> MEDIUM
    # (nur Menüliste, kein Banner) — Regel #1: nicht verschlucken, nur nicht bannern.
    if hk or gk:
        entry.severity = MEDIUM
        return
    entry.severity = LOW

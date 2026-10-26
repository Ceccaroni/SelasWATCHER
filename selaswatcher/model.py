"""Gemeinsames internes Datenmodell für alle Quellen-Typen."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

# Schwere-Stufen (von scoring.py gesetzt)
HIGH = "HIGH"
MEDIUM = "MEDIUM"
LOW = "LOW"


@dataclass
class Entry:
    """Ein normalisierter Feed-/API-Eintrag."""

    source_id: str
    source_name: str
    dedup_id: str
    title: str
    url: str
    summary: str  # HTML gestrippt, auf ~400 Zeichen gekürzt
    published: datetime | None
    lang: str

    # Hinweis aus der Quelle (z. B. KEV = HIGH), vom Scoring berücksichtigt.
    severity_hint: str | None = None

    # Betroffene Pakete (z. B. GitHub Advisory) -> Abgleich gegen das Inventar.
    affected_packages: list[str] = field(default_factory=list)

    # Vom Scoring gesetzt:
    severity: str = LOW
    matched_terms: list[str] = field(default_factory=list)

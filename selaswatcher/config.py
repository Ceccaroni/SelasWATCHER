"""Config-Laden: config.toml (tomllib) mit Fallback auf eingebaute Defaults.

Sucht config.toml im CWD und in ~/.selaswatcher/. Fehlt sie, laufen die
Defaults (zusätzlich wird config.example.toml im CWD als Fallback gemergt,
falls vorhanden). Nie crashen, wenn keine Config existiert.
"""

from __future__ import annotations

import copy
import logging
import tomllib
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Eingebaute Defaults — gespiegelt in config.example.toml.
DEFAULTS: dict[str, Any] = {
    "poll_interval_seconds": 300,
    # Quellen an/aus. Nicht gelistete Quellen gelten als aktiviert.
    "sources": {
        "bacs": True,  # BACS/NCSC "Aktuelle Vorfälle" via HTML-Polling (always_high)
        "inside-it": True,
        "20min": True,
        # CISA-Alerts (alerts.xml, kuratiert): KEV-Wrapper gefiltert, Rest = HIGH (S002).
        "cisa-advisories": True,
        "cisa-kev": True,
        "cert-bund-wid": True,
        "buerger-cert": True,
        "heise-security": True,
        "bleepingcomputer": True,
        "nvd": False,  # Firehose (jede CVE); deaktiviert. KEV/GitHub/CERT-Bund decken den Stack ab.
        "github-advisory": True,
    },
    "github": {
        "ecosystems": ["npm"],  # nur das genutzte Ökosystem (kein composer/PHP)
    },
    "state": {
        # Max. gesehene IDs je Quelle (Dedup-State). Hält seen.json klein.
        # Großzügig über jedem Feed-Fenster -> kein Re-Alarm alter Einträge. 0 = aus.
        "seen_cap": 2000,
    },
    "health": {
        # Wächter-fürs-Wächter: Eine Quelle, die so viele Polls IN FOLGE fehlschlägt,
        # meldet EINMAL einen HIGH-Banner ("Quelle X fällt aus") — damit ein stiller
        # Dauerausfall (403, kaputter Feed) nicht unbemerkt Warnungen verschluckt.
        # Bei Erholung still zurückgesetzt und neu scharf. 6 ≈ 30 Min (5-Min-Takt),
        # filtert kurze Netz-Blips (Regel #3). 0 = Wächter aus.
        "fail_threshold": 6,
    },
    "inventory": {
        # Repo-Verzeichnisse mit package-lock.json -> definiert, welche Pakete du nutzt.
        # GitHub-Advisories werden dagegen gematcht (nur echte Treffer -> HIGH).
        # Leer = Fallback auf die Titel-Watchlist. Lokal in config.toml setzen.
        "project_paths": [],
        "extra_packages": [],
    },
    "scoring": {
        # Technologie-Watchlist: Treffer => immer HIGH (konzept.md §6).
        # Nur der echte Stack (Wortgrenzen-Matching). Bewusst NICHT 'node'/'php'
        # (fangen ganze Ökosysteme). PHP-Krisen kommen über News/Kritisch-Keywords.
        "watchlist": [
            "nextjs",
            "next.js",
            "node.js",
            "supabase",
            "postgres",
            "postgresql",
            "docker",
            "infomaniak",
        ],
        # HIGH-Stichwörter (de + en), case-insensitive.
        "high_keywords": [
            "zero-day",
            "0-day",
            "actively exploited",
            "aktiv ausgenutzt",
            "in the wild",
            "remote code execution",
            "rce",
            "emergency patch",
            "notfall-patch",
            "unauthenticated",
        ],
        # Generische Security-Keywords => MEDIUM.
        "generic_keywords": [
            "cve",
            "vulnerability",
            "schwachstelle",
            "sicherheitslücke",
            "sicherheitsupdate",
            "exploit",
            "advisory",
            "patch",
            "malware",
            "phishing",
            "trojan",
            "backdoor",
            "privilege escalation",
            "denial of service",
            # Breach/Leak- UND Ransomware-Begriffe bewusst nur MEDIUM (stumm): sie werden
            # erst HIGH, wenn sie unseren Stack/Provider (Watchlist) oder ein Dringlichkeits-
            # Keyword (aktiv ausgenutzt/zero-day/rce) nennen. Nacktes "ransomware"/"breach"
            # ist Fremd-Laerm (woechentlich irgendwo, z. B. Safepay gegen eine CH-Gemeinde) —
            # kein Selas-Bezug, gehoert in die Liste, nicht ins Banner (S006).
            "datenleck",
            "data breach",
            "breach",
            "ransomware",
        ],
    },
}


def _candidate_paths() -> list[Path]:
    return [
        Path.cwd() / "config.toml",
        Path.home() / ".selaswatcher" / "config.toml",
    ]


def _find_config() -> Path | None:
    for p in _candidate_paths():
        if p.is_file():
            return p
    return None


def _deep_merge(base: dict[str, Any], overlay: dict[str, Any]) -> None:
    """Überlagert base mit overlay (nur verschachtelte Dicts rekursiv; Listen werden ersetzt)."""
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], val)
        else:
            base[key] = val


def load_config() -> dict[str, Any]:
    """Lädt die Config. Immer ein vollständiges Dict (Defaults + ggf. Overlay)."""
    cfg = copy.deepcopy(DEFAULTS)
    path = _find_config()
    if path is not None:
        try:
            with open(path, "rb") as f:
                user = tomllib.load(f)
            _deep_merge(cfg, user)
            log.info("Config geladen: %s", path)
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("config.toml unlesbar (%s) — nutze Defaults", exc)
        return cfg

    # Keine config.toml: config.example.toml im CWD als Fallback mitnehmen.
    example = Path.cwd() / "config.example.toml"
    if example.is_file():
        try:
            with open(example, "rb") as f:
                _deep_merge(cfg, tomllib.load(f))
            log.info("Keine config.toml — Fallback auf config.example.toml")
        except (OSError, tomllib.TOMLDecodeError) as exc:
            log.warning("config.example.toml unlesbar (%s) — nutze Defaults", exc)
    else:
        log.info("Keine config.toml gefunden — nutze eingebaute Defaults")
    return cfg

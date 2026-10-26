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
        "inside-it": True,
        "20min": True,
        # RSS WAF-geblockt (403, S001 verifiziert) -> deaktiviert; CISA KEV deckt es ab. Revisit Phase 4.
        "cisa-advisories": False,
        "cisa-kev": True,
        "cert-bund-wid": True,
        "buerger-cert": True,
        "heise-security": True,
        "bleepingcomputer": True,
        "nvd": False,  # Firehose (jede CVE); deaktiviert. KEV/GitHub/CERT-Bund decken den Stack ab.
        "github-advisory": True,
    },
    "github": {
        "ecosystems": ["composer", "npm"],
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
            "ransomware",
            "datenleck",
            "data breach",
            "breach",
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

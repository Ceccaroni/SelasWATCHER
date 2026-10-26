"""Dependency-Inventar: welche npm-Pakete setzt der Nutzer wirklich ein?

Liest package-lock.json (lockfileVersion 2/3 bevorzugt, 1 als Fallback) und
package.json der konfigurierten Projekte und liefert die Menge ALLER Paketnamen
(inkl. transitiver Abhängigkeiten), kleingeschrieben. Gecacht nach Datei-mtime.

Damit matcht SelasWATCHER GitHub-Advisories präzise gegen den echten Stack
(Dependabot-Prinzip): Alarm nur, wenn ein tatsächlich genutztes Paket betroffen ist.
Konfiguration: [inventory] project_paths = ["/pfad/zum/repo", …] (Repo-Verzeichnisse).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# Cache je Datei: Pfad -> (mtime, Paketnamen). Neu-Parsen nur bei Änderung.
_cache: dict[str, tuple[float, set[str]]] = {}


def _names_from_lock(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    pkgs = data.get("packages")
    if isinstance(pkgs, dict):  # lockfileVersion 2/3
        for key in pkgs:
            marker = "node_modules/"
            if marker in key:
                names.add(key.rsplit(marker, 1)[-1].lower())
    deps = data.get("dependencies")
    if isinstance(deps, dict):  # lockfileVersion 1 (rekursiv)
        def walk(d: dict[str, Any]) -> None:
            for name, info in d.items():
                names.add(name.lower())
                if isinstance(info, dict) and isinstance(info.get("dependencies"), dict):
                    walk(info["dependencies"])
        walk(deps)
    return names


def _names_from_pkgjson(data: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for field_name in ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies"):
        d = data.get(field_name)
        if isinstance(d, dict):
            names.update(n.lower() for n in d)
    return names


def _load_file(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        log.warning("Inventar: %s unlesbar (%s)", path, exc)
        return set()
    return _names_from_lock(data) if path.name == "package-lock.json" else _names_from_pkgjson(data)


def load_inventory(config: dict[str, Any]) -> set[str]:
    """Menge aller genutzten Paketnamen (lowercase) aus den konfigurierten Projekten.
    Leere Menge, wenn nichts konfiguriert/gefunden — dann greift der Watchlist-Fallback."""
    inv_cfg = config.get("inventory", {}) or {}
    names: set[str] = set()
    for p in inv_cfg.get("project_paths", []) or []:
        base = Path(p).expanduser()
        for fname in ("package-lock.json", "package.json"):
            f = base / fname
            if not f.is_file():
                continue
            try:
                mtime = f.stat().st_mtime
            except OSError:
                continue
            key = str(f)
            cached = _cache.get(key)
            if cached and cached[0] == mtime:
                names |= cached[1]
            else:
                got = _load_file(f)
                _cache[key] = (mtime, got)
                names |= got
    names.update(n.lower() for n in (inv_cfg.get("extra_packages") or []))
    return names

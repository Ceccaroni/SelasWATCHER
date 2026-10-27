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
# Separater Cache für Name -> installierte Versionen (nur package-lock.json).
_ver_cache: dict[str, tuple[float, dict[str, set[str]]]] = {}


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


def _versions_from_lock(data: dict[str, Any]) -> dict[str, set[str]]:
    """Name (lowercase) -> Menge INSTALLIERTER Versionen aus package-lock.json.

    Nur das Lockfile nennt die konkret installierte Version (package.json führt nur
    Ranges wie '^7.29.0'). Ein Name kann mehrfach (nested node_modules) in verschiedenen
    Versionen vorkommen -> Menge. Betroffen ist man, wenn EINE davon im Advisory-Bereich liegt."""
    out: dict[str, set[str]] = {}
    pkgs = data.get("packages")
    if isinstance(pkgs, dict):  # lockfileVersion 2/3
        marker = "node_modules/"
        for key, info in pkgs.items():
            if marker not in key or not isinstance(info, dict):
                continue
            ver = info.get("version")
            if ver:
                out.setdefault(key.rsplit(marker, 1)[-1].lower(), set()).add(str(ver))
    deps = data.get("dependencies")
    if isinstance(deps, dict):  # lockfileVersion 1 (rekursiv)
        def walk(d: dict[str, Any]) -> None:
            for name, info in d.items():
                if not isinstance(info, dict):
                    continue
                ver = info.get("version")
                if ver:
                    out.setdefault(name.lower(), set()).add(str(ver))
                if isinstance(info.get("dependencies"), dict):
                    walk(info["dependencies"])
        walk(deps)
    return out


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


def load_inventory_versions(config: dict[str, Any]) -> dict[str, set[str]]:
    """Name (lowercase) -> installierte Versionen, aus den package-lock.json der Projekte.

    Nur Pakete, deren Version im Lockfile steht, erscheinen hier. Pakete, die SelasWATCHER
    zwar nutzt, deren Version es aber nicht kennt (nur package.json, kein Lockfile; oder
    extra_packages), fehlen bewusst -> das Scoring meldet sie dann im Zweifel (Regel #1)."""
    inv_cfg = config.get("inventory", {}) or {}
    out: dict[str, set[str]] = {}
    for p in inv_cfg.get("project_paths", []) or []:
        f = Path(p).expanduser() / "package-lock.json"
        if not f.is_file():
            continue
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        key = str(f)
        cached = _ver_cache.get(key)
        if cached and cached[0] == mtime:
            got = cached[1]
        else:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                got = _versions_from_lock(data)
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                log.warning("Inventar-Versionen: %s unlesbar (%s)", f, exc)
                got = {}
            _ver_cache[key] = (mtime, got)
        for name, vers in got.items():
            out.setdefault(name, set()).update(vers)
    return out

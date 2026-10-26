"""Quellen-Definitionen + Fetcher mit Typ-Adaptern (rss/atom, json).

URLs und Dedup-IDs stammen aus konzept.md §5. Jede Quelle wird vom Poller in
try/except gekapselt — eine kaputte Quelle darf die anderen nicht abbrechen.
Feed-Inhalte sind Daten, nie Code: kein eval/exec/Shell, nur http(s)-URLs.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from typing import Any

import feedparser
import requests

from .model import HIGH, Entry
from .state import State, _parse_iso

log = logging.getLogger(__name__)

USER_AGENT = "SelasWATCHER/0.1"
HTTP_TIMEOUT = 15  # Sekunden

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_WID_RE = re.compile(r"WID-SEC-\d{4}-\d+")
_SUMMARY_LIMIT = 400


@dataclass
class Source:
    """Statische Definition einer Quelle."""

    id: str
    name: str
    type: str  # "rss", "atom", "json"
    url: str
    lang: str
    security: bool  # reine Security-Quelle (fürs Scoring-Baseline)
    vulndb: bool = False  # Vuln-Datenbank (Firehose) -> nur bei Watchlist-Treffer melden


# Reihenfolge wie konzept.md §5 (ohne BACS = Phase 4).
SOURCES: dict[str, Source] = {
    s.id: s
    for s in [
        Source("inside-it", "inside-it.ch", "rss", "https://www.inside-it.ch/rss.xml", "de", False),
        Source("20min", "20min Digital", "rss", "https://partner-feeds.20min.ch/rss/20minuten/digital", "de-ch", False),
        Source("cisa-advisories", "CISA Advisories", "rss", "https://www.cisa.gov/cybersecurity-advisories/all.xml", "en", True),
        Source("cisa-kev", "CISA KEV", "json", "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json", "en", True, vulndb=True),
        Source("cert-bund-wid", "CERT-Bund WID", "rss", "https://wid.cert-bund.de/content/public/securityAdvisory/rss", "de", True),
        Source("buerger-cert", "Bürger-CERT (BSI)", "rss", "https://wid.cert-bund.de/content/public/buergercert/rss", "de", True),
        Source("heise-security", "heise Security", "atom", "https://www.heise.de/security/feed.xml", "de", True),
        Source("bleepingcomputer", "BleepingComputer", "rss", "https://www.bleepingcomputer.com/feed/", "en", True),
        Source("nvd", "NVD (CVE)", "json", "https://services.nvd.nist.gov/rest/json/cves/2.0", "en", True, vulndb=True),
        Source("github-advisory", "GitHub Advisory DB", "json", "https://api.github.com/advisories", "en", True, vulndb=True),
    ]
}


# --- Helfer ---------------------------------------------------------------


def clean_summary(raw: str | None, limit: int = _SUMMARY_LIMIT) -> str:
    """HTML-Tags strippen, Entities auflösen, Whitespace normalisieren, kürzen."""
    if not raw:
        return ""
    text = _TAG_RE.sub(" ", raw)
    text = unescape(text)
    text = _WS_RE.sub(" ", text).strip()
    if len(text) > limit:
        text = text[:limit].rstrip() + "…"
    return text


def safe_url(url: str | None) -> str:
    """Nur http(s) zulassen; javascript:/file:/data: etc. verwerfen."""
    if not url:
        return ""
    if url.lower().startswith(("http://", "https://")):
        return url.strip()
    return ""


def _struct_to_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime(*value[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def _feed_published(item: Any) -> datetime | None:
    """Item-Datum (published bevorzugt, sonst updated) — bewusst item-, nicht channel-weit."""
    return _struct_to_dt(item.get("published_parsed")) or _struct_to_dt(item.get("updated_parsed"))


def _http_get(url: str, source_st: dict[str, Any], extra_headers: dict[str, str] | None = None,
              params: dict[str, str] | None = None, use_conditional: bool = True) -> requests.Response:
    headers = {"User-Agent": USER_AGENT}
    if use_conditional:
        if source_st.get("etag"):
            headers["If-None-Match"] = source_st["etag"]
        if source_st.get("modified"):
            headers["If-Modified-Since"] = source_st["modified"]
    if extra_headers:
        headers.update(extra_headers)
    return requests.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT)


# --- RSS/Atom-Adapter ------------------------------------------------------


def _dedup_id_for(source: Source, item: Any) -> str:
    link = safe_url(item.get("link"))
    if source.id == "cert-bund-wid":
        # CERT-Bund hat keine brauchbare guid: WID-ID aus Titel/Link, Fallback link.
        for text in (item.get("title", ""), item.get("link", "")):
            m = _WID_RE.search(text or "")
            if m:
                return m.group(0)
        return link
    # Default: id/guid/link.
    return item.get("id") or item.get("guid") or link


def _fetch_feed(source: Source, state: State) -> list[Entry]:
    st = state.source_state(source.id)
    resp = _http_get(source.url, st)
    if resp.status_code == 304:
        log.info("%s: 304 Not Modified", source.id)
        return []
    resp.raise_for_status()
    # ETag/Last-Modified für conditional GET zurückschreiben.
    st["etag"] = resp.headers.get("ETag")
    st["modified"] = resp.headers.get("Last-Modified")

    parsed = feedparser.parse(resp.content)
    entries: list[Entry] = []
    for item in parsed.entries:
        dedup_id = _dedup_id_for(source, item)
        if not dedup_id:
            continue  # ohne stabile ID überspringen
        entries.append(
            Entry(
                source_id=source.id,
                source_name=source.name,
                dedup_id=dedup_id,
                title=(item.get("title") or "").strip(),
                url=safe_url(item.get("link")),
                summary=clean_summary(item.get("summary") or item.get("description")),
                published=_feed_published(item),
                lang=source.lang,
            )
        )
    return entries


# --- JSON-Adapter ----------------------------------------------------------


def _fetch_cisa_kev(source: Source, state: State) -> list[Entry]:
    st = state.source_state(source.id)
    resp = _http_get(source.url, st)  # grosse Datei -> conditional GET
    if resp.status_code == 304:
        log.info("%s: 304 Not Modified", source.id)
        return []
    resp.raise_for_status()
    st["etag"] = resp.headers.get("ETag")
    st["modified"] = resp.headers.get("Last-Modified")

    data = resp.json()
    entries: list[Entry] = []
    for vuln in data.get("vulnerabilities", []):
        cve = vuln.get("cveID")
        if not cve:
            continue
        name = vuln.get("vulnerabilityName", "")
        entries.append(
            Entry(
                source_id=source.id,
                source_name=source.name,
                dedup_id=cve,
                title=f"{cve}: {name}".strip().rstrip(":"),
                url=f"https://nvd.nist.gov/vuln/detail/{cve}",
                summary=clean_summary(vuln.get("shortDescription")),
                published=_parse_iso(vuln.get("dateAdded")),
                lang=source.lang,
                severity_hint=HIGH,  # KEV = per Definition aktiv ausgenutzt
            )
        )
    return entries


def _fetch_nvd(source: Source, state: State) -> list[Entry]:
    import os

    st = state.source_state(source.id)
    now = datetime.now(timezone.utc)
    start = state.last_run(source.id) or (now - timedelta(hours=24))
    # NVD: ISO-8601 (UTC angenommen), erweitertes Format mit Millisekunden.
    params = {
        "lastModStartDate": start.strftime("%Y-%m-%dT%H:%M:%S.000"),
        "lastModEndDate": now.strftime("%Y-%m-%dT%H:%M:%S.000"),
    }
    headers: dict[str, str] = {}
    api_key = os.environ.get("NVD_API_KEY")
    if api_key:
        headers["apiKey"] = api_key

    resp = _http_get(source.url, st, extra_headers=headers, params=params, use_conditional=False)
    resp.raise_for_status()
    data = resp.json()

    entries: list[Entry] = []
    for item in data.get("vulnerabilities", []):
        cve = item.get("cve", {})
        cve_id = cve.get("id")
        if not cve_id:
            continue
        snippet = ""
        for desc in cve.get("descriptions", []):
            if desc.get("lang") == "en":
                snippet = desc.get("value", "")
                break
        title = f"{cve_id}: {snippet[:120]}".strip().rstrip(":")
        entries.append(
            Entry(
                source_id=source.id,
                source_name=source.name,
                dedup_id=cve_id,
                title=title,
                url=f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                summary=clean_summary(snippet),
                published=_parse_iso(cve.get("published")),
                lang=source.lang,
            )
        )
    return entries


def _fetch_github(source: Source, state: State, config: dict[str, Any]) -> list[Entry]:
    import os

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    ecosystems = config.get("github", {}).get("ecosystems", ["composer", "npm"])
    st = state.source_state(source.id)
    entries: list[Entry] = []
    for eco in ecosystems:
        params = {"ecosystem": eco, "per_page": "50"}
        resp = _http_get(source.url, st, extra_headers=headers, params=params, use_conditional=False)
        resp.raise_for_status()
        for adv in resp.json():
            ghsa = adv.get("ghsa_id")
            if not ghsa:
                continue
            sev = (adv.get("severity") or "").lower()
            hint = HIGH if sev in ("critical", "high") else None
            entries.append(
                Entry(
                    source_id=source.id,
                    source_name=f"{source.name} ({eco})",
                    dedup_id=ghsa,
                    title=(adv.get("summary") or ghsa).strip(),
                    url=safe_url(adv.get("html_url")),
                    summary=clean_summary(adv.get("description")),
                    published=_parse_iso(adv.get("published_at")),
                    lang=source.lang,
                    severity_hint=hint,
                )
            )
    return entries


# --- Dispatch --------------------------------------------------------------


def fetch_source(source: Source, state: State, config: dict[str, Any]) -> list[Entry]:
    """Holt alle aktuell vorhandenen Einträge einer Quelle (ohne Dedup/Scoring)."""
    if source.type in ("rss", "atom"):
        return _fetch_feed(source, state)
    if source.type == "json":
        if source.id == "cisa-kev":
            return _fetch_cisa_kev(source, state)
        if source.id == "nvd":
            return _fetch_nvd(source, state)
        if source.id == "github-advisory":
            return _fetch_github(source, state, config)
    raise ValueError(f"Unbekannter Quellen-Typ/-ID: {source.id}/{source.type}")


def enabled_sources(config: dict[str, Any]) -> list[Source]:
    """Aktivierte Quellen laut Config (nicht gelistet => aktiviert)."""
    toggles = config.get("sources", {})
    return [s for s in SOURCES.values() if toggles.get(s.id, True)]

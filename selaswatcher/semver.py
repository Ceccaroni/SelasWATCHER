"""Minimaler, **defensiver** Semver-Range-Check für das Inventar-Matching.

Zweck: entscheiden, ob eine installierte Paketversion im verwundbaren Bereich eines
GitHub-Advisories liegt (`vulnerable_version_range`, z. B. ">= 7.0.0, < 7.30.1").

**Sicherheitsleitlinie (Regel #1 — nie eine echte Lücke verschlucken):** Dieser Parser
entwarnt NUR, wenn er sicher ist. Alles Uneindeutige — unbekannter Operator, nicht sauber
als `x.y.z` parsebare Version/Grenze, Prerelease/Build-Metadaten im Spiel — ergibt `None`
("weiss ich nicht"), und der Aufruffer (`scoring`) behandelt `None` wie "betroffen" und meldet.
Nur ein eindeutiges `False` (installierte Version nachweislich ausserhalb) dämpft eine Meldung.

Bewusst KEIN volles Semver: GitHub liefert für npm komma-getrennte UND-Constraints mit den
Operatoren `>=`/`>`/`<=`/`<`/`=` über saubere `x.y.z`-Grenzen (ODER-Verknüpfung mehrerer
Major-Linien kommt als getrennte Range-Strings, die der Aufruffer ver-ODER-t). Prerelease-
Versionen sind in echten package-lock-Ständen praktisch nie installiert — statt ihre kniffligen
Vergleichsregeln (teil-)falsch umzusetzen, melden wir im Zweifel. Regel #4: wartbar statt clever.
"""

from __future__ import annotations

# Zwei-Zeichen-Operatoren zuerst prüfen (sonst würde ">" schon bei ">=" greifen).
_OPS = ("<=", ">=", "<", ">", "=")


def _parse(v: str) -> tuple[int, int, int] | None:
    """'7.30.1' / 'v7.30' / '=7' -> (7,30,1) | (7,30,0) | (7,0,0); sonst None.

    None (= unsicher) bei allem, was nicht sauber numerisch `x[.y[.z]]` ist —
    insbesondere Prerelease ('-') oder Build-Metadaten ('+')."""
    v = v.strip()
    if v[:1] in ("v", "="):
        v = v[1:].strip()
    if not v or "-" in v or "+" in v:  # Prerelease/Build -> im Zweifel unsicher
        return None
    nums = v.split(".")
    if not 1 <= len(nums) <= 3:
        return None
    try:
        parts = [int(x) for x in nums]
    except ValueError:
        return None
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def _split_op(part: str) -> tuple[str, str]:
    """'>= 7.0.0' -> ('>=', '7.0.0'); ohne Operator -> exakte Version ('=')."""
    part = part.strip()
    for op in _OPS:
        if part.startswith(op):
            return op, part[len(op):].strip()
    return "=", part


def in_range(version: str, range_str: str) -> bool | None:
    """Liegt `version` im (komma-getrennten UND-)`range_str`?

    True  = sicher drin (betroffen)
    False = sicher draussen (NICHT betroffen -> darf gedämpft werden)
    None  = unsicher (Aufruffer meldet im Zweifel, Regel #1)
    """
    v = _parse(version)
    if v is None:
        return None
    parts = [p.strip() for p in (range_str or "").split(",") if p.strip()]
    if not parts:
        return None
    for part in parts:
        op, bound = _split_op(part)
        b = _parse(bound)
        if b is None:
            return None  # unparsebare Grenze -> unsicher
        if op == ">=":
            ok = v >= b
        elif op == ">":
            ok = v > b
        elif op == "<=":
            ok = v <= b
        elif op == "<":
            ok = v < b
        elif op == "=":
            ok = v == b
        else:  # unbekannter Operator -> unsicher
            return None
        if not ok:
            return False  # ein UND-Constraint verletzt -> sicher ausserhalb
    return True

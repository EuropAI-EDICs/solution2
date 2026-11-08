"""Pure lees- en refresh-laag over de DSO-kennisbank (dso_overlap/out).

De dienst leest het bestandssysteem — de agent nooit direct. Alle functies
zijn puur en via ``out_dir``/``instrumenten``/``locaties`` injecteerbaar
(het poc_readops-testpatroon). Alleen :func:`ververs` schrijft, en alléén
naar de gitignored cache; live sleutels blijven server-side in ``.env``.
Ontwerp: docs/superpowers/specs/2026-11-07-dso-kb-mcp-design.md.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

NLDT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = NLDT_ROOT.parent
DEFAULT_OUT = NLDT_ROOT / "simulation" / "regelrecht" / "dso_overlap" / "out"

LIMIT_DEFAULT = 100
LIMIT_MAX = 500

_ARTIKEL_RE = re.compile(r"__art_([\d.]+)")


class DsoKbFout(RuntimeError):
    """Verwachte fout met de geldige opties in de melding."""


def _laat_instrumenten() -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    """INSTRUMENTS + locaties uit dso_overlap/instruments.py (lazy import)."""
    root = str(WORKSPACE)
    if root not in sys.path:
        sys.path.insert(0, root)
    from nldt.simulation.regelrecht.dso_overlap.instruments import (
        INSTRUMENTS,
        load_locations,
    )

    return INSTRUMENTS, load_locations()


def _limiet(limiet: int | None) -> int:
    if limiet is None:
        return LIMIT_DEFAULT
    if limiet < 1:
        raise DsoKbFout(f"limiet moet >= 1 zijn (kreeg {limiet})")
    return min(limiet, LIMIT_MAX)


def _resolve_paar(
    instrument: str,
    locatie: str | None,
    instrumenten: dict[str, dict[str, Any]] | None,
    locaties: dict[str, dict[str, Any]] | None,
) -> tuple[dict[str, Any], str, str]:
    if instrumenten is None or locaties is None:
        instrumenten, locaties = _laat_instrumenten()
    if instrument not in instrumenten:
        raise DsoKbFout(
            f"onbekend instrument {instrument!r}; geldig: {sorted(instrumenten)}"
        )
    meta = instrumenten[instrument]
    lid = locatie or meta.get("default_location_id")
    if lid not in locaties:
        raise DsoKbFout(f"onbekende locatie {lid!r}; geldig: {sorted(locaties)}")
    return meta, lid, f"{instrument}__{lid}"


def _lees_json(pad: Path) -> Any:
    if not pad.is_file():
        raise DsoKbFout(
            f"artefact ontbreekt: {pad.name} — draai eerst dso-kb-refresh (of de CLI)"
        )
    return json.loads(pad.read_text(encoding="utf-8"))


def _kort(vol: str | None) -> str | None:
    return vol[:16] if vol else None


def _artikel_sleutel(num: str) -> tuple[int | str, ...]:
    """Numerieke sorteersleutel voor '10.1.3'-stijl artikelnummers (tpod-patroon)."""
    delen: list[int | str] = []
    for stuk in str(num).split("."):
        try:
            delen.append(int(stuk))
        except ValueError:
            delen.append(stuk)
    return tuple(delen)


def lees_annotaties(
    instrument: str,
    locatie: str | None = None,
    artikel: str | None = None,
    detail: bool = False,
    limiet: int | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Regeltekstannotaties per artikelnummer, gebonden en filterbaar."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    data = _lees_json(out / f"{stem}.annotaties.json")
    grens = _limiet(limiet)

    wId_artikel: dict[str, str] = {}
    rijen: dict[str, dict[str, Any]] = {}
    for rt in data.get("regelteksten") or []:
        wid = rt.get("wId", "")
        m = _ARTIKEL_RE.search(wid)
        num = m.group(1) if m else wid
        wId_artikel[wid] = num
        rij = rijen.setdefault(
            num, {"artikel": num, "wIds": [], "regelteksten": 0, "activiteiten": [], "regelIds": []}
        )
        rij["regelteksten"] += 1
        if len(rij["wIds"]) < LIMIT_MAX:
            rij["wIds"].append(wid)

    for regel in (data.get("regelsVoorIedereen") or []) + (data.get("instructieregels") or []):
        num = wId_artikel.get(regel.get("regeltekstRef", ""))
        if num is None:
            continue
        rij = rijen[num]
        if len(rij["regelIds"]) < LIMIT_MAX:
            rij["regelIds"].append(regel.get("identificatie"))
        for ala in regel.get("activiteitLocatieaanduidingen") or []:
            act = (ala.get("activiteitRef") or "").rsplit(".", 1)[-1]
            if act and act not in rij["activiteiten"] and len(rij["activiteiten"]) < LIMIT_MAX:
                rij["activiteiten"].append(act)

    alle = sorted(rijen.values(), key=lambda r: _artikel_sleutel(r["artikel"]))
    if artikel is not None:
        alle = [r for r in alle if r["artikel"] == artikel]
        if not alle:
            raise DsoKbFout(
                f"artikel {artikel!r} niet in DSO-hit; geldig (eerste {grens}): "
                f"{[r['artikel'] for r in sorted(rijen.values(), key=lambda r: _artikel_sleutel(r['artikel']))][:grens]}"
            )

    vervolg = None
    if len(alle) > grens:
        alle = alle[:grens]
        vervolg = {"aanwijzing": "verfijn met artikel= of verhoog limiet", "maxLimiet": LIMIT_MAX}

    uit: dict[str, Any] = {
        "instrument": instrument,
        "locatie": lid,
        "totaalArtikelen": len(rijen),
        "counts": {
            "regelteksten": len(data.get("regelteksten") or []),
            "regelsVoorIedereen": len(data.get("regelsVoorIedereen") or []),
            "instructieregels": len(data.get("instructieregels") or []),
            "locaties": len(data.get("locaties") or []),
            "gebiedsaanwijzingen": len(data.get("gebiedsaanwijzingen") or []),
            "activiteiten": len(data.get("activiteiten") or []),
        },
        "artikelen": alle,
        "vervolg": vervolg,
    }
    if detail and alle:
        wids = set(alle[0]["wIds"])
        uit["regelteksten"] = [
            rt for rt in (data.get("regelteksten") or []) if rt.get("wId") in wids
        ][:LIMIT_MAX]
    return uit

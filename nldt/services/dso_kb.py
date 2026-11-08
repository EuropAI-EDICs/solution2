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
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

NLDT_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = NLDT_ROOT.parent
DEFAULT_OUT = NLDT_ROOT / "simulation" / "regelrecht" / "dso_overlap" / "out"

LIMIT_DEFAULT = 100
LIMIT_MAX = 500

_ARTIKEL_RE = re.compile(r"__art_([\d.]+)")

_DATUM_PARAMS = ("geldigOp", "inWerkingOp", "beschikbaarOp")


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


def _vlak_componenten(
    componenten: list[Any] | None, diepte: int, uit: list[dict[str, Any]]
) -> None:
    for c in componenten or []:
        uit.append(
            {"diepte": diepte, "soort": c.get("soort"), "wId": c.get("wId"), "titel": c.get("titel")}
        )
        _vlak_componenten((c.get("_embedded") or {}).get("documentComponenten"), diepte + 1, uit)


def lees_documentstructuur(
    instrument: str,
    locatie: str | None = None,
    wId_prefix: str | None = None,
    limiet: int | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Documentstructuur als vlakke, gebonden componentreeks."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    data = _lees_json(out / f"{stem}.documentstructuur.json")
    vlak: list[dict[str, Any]] = []
    _vlak_componenten((data.get("_embedded") or {}).get("documentComponenten"), 0, vlak)
    totaal = len(vlak)
    if wId_prefix:
        vlak = [c for c in vlak if str(c.get("wId") or "").startswith(wId_prefix)]
    grens = _limiet(limiet)
    vervolg = None
    if len(vlak) > grens:
        vlak = vlak[:grens]
        vervolg = {"aanwijzing": "verfijn met wIdPrefix= of verhoog limiet", "maxLimiet": LIMIT_MAX}
    return {
        "instrument": instrument,
        "locatie": lid,
        "totaalComponenten": totaal,
        "totaalNaFilter": len(vlak),
        "componenten": vlak,
        "vervolg": vervolg,
    }


_KOP_SOORTEN = ("annotaties", "documentstructuur", "tpod-index", "toets", "overlap", "geo-validatie", "pakket-index")


def instrumenten_overzicht(
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Instrumenten × locaties met freshness en dekkingscijfers uit de cache."""
    out = out_dir or DEFAULT_OUT
    if instrumenten is None or locaties is None:
        instrumenten, locaties = _laat_instrumenten()
    rijen = []
    for iid, meta in sorted(instrumenten.items()):
        for lid, loc in sorted(locaties.items()):
            if loc.get("instrument") and loc["instrument"] != iid:
                continue
            stem = f"{iid}__{lid}"
            rij: dict[str, Any] = {
                "instrument": iid,
                "label": meta.get("label"),
                "locatie": lid,
                "locatieLabel": loc.get("label"),
                "artefacten": {k: (out / f"{stem}.{k}.json").stat().st_size
                               for k in _KOP_SOORTEN if (out / f"{stem}.{k}.json").is_file()},
                "dekking": None,
                "gegenereerdOp": None,
                "annotatiesSha256": None,
            }
            ov_pad = out / f"{stem}.overlap.json"
            if ov_pad.is_file():
                ov = json.loads(ov_pad.read_text(encoding="utf-8"))
                o = ov.get("overlap") or {}
                rij["dekking"] = {
                    "dsoArtikelen": ((ov.get("dso") or {}).get("counts") or {}).get("uniqueArticleNumbers"),
                    "executable": o.get("executableCount"),
                    "abstain": o.get("abstainCount"),
                    "coverageExecutable": o.get("coverageExecutable"),
                }
                rij["gegenereerdOp"] = ov.get("generatedAt")
                rij["annotatiesSha256"] = _kort((ov.get("dso") or {}).get("annotatiesSha256"))
            rijen.append(rij)
    return {"instrumenten": rijen}


def lees_tpod(
    instrument: str,
    locatie: str | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """wId-anchoring, geoFeiten, activiteiten en pons-status van de tpod-index."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    idx = _lees_json(out / f"{stem}.tpod-index.json")
    gf = idx.get("geoFeiten") or {}
    return {
        "instrument": instrument,
        "locatie": lid,
        "gegenereerdOp": idx.get("gegenereerdOp"),
        "hitCoverage": idx.get("hitCoverage"),
        "geoFeiten": {k: gf.get(k) for k in ("geselecteerdeLocatieRefs", "aantalLocatiesMetGeometrie", "gebiedsaanwijzingen", "gioInPakket")},
        "activiteiten": idx.get("activiteiten"),
        "pons": idx.get("pons"),
    }


def lees_toets(
    instrument: str,
    locatie: str | None = None,
    artikel: str | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """RegelRecht-punttoets: feit/afwezigheid/scenario/onthouding per artikel."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    data = _lees_json(out / f"{stem}.toets.json")
    artikelen = data.get("artikelen") or []
    if artikel is not None:
        artikelen = [a for a in artikelen if a.get("artikel") == artikel]
        if not artikelen:
            raise DsoKbFout(
                f"artikel {artikel!r} niet in de toets; geldig: "
                f"{[a.get('artikel') for a in (data.get('artikelen') or [])][:LIMIT_DEFAULT]}"
            )
    return {
        "instrument": instrument,
        "locatie": lid,
        "gegenereerdOp": data.get("gegenereerdOp"),
        "tellingen": data.get("tellingen"),
        "artikelen": artikelen[:LIMIT_MAX],
    }


def lees_overlap(
    instrument: str,
    locatie: str | None = None,
    status: str | None = None,
    pagina: int = 1,
    limiet: int | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """DSO↔RegelRecht-dekking + per-artikel statusrijen, gefilterd en gepagineerd."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    data = _lees_json(out / f"{stem}.overlap.json")
    ov = data.get("overlap") or {}
    rijen = ov.get("articles") or []
    if pagina < 1:
        raise DsoKbFout(f"pagina moet >= 1 zijn (kreeg {pagina})")
    if status is not None:
        geldig = sorted({r.get("rrStatus") for r in rijen if r.get("rrStatus")})
        rijen = [r for r in rijen if r.get("rrStatus") == status]
        if not rijen:
            raise DsoKbFout(f"onbekende status {status!r}; geldig: {geldig}")
    grens = _limiet(limiet)
    start = (pagina - 1) * grens
    pagina_rijen = rijen[start : start + grens]
    vervolg = {"volgendePagina": pagina + 1} if start + grens < len(rijen) else None
    return {
        "instrument": instrument,
        "locatie": lid,
        "gegenereerdOp": data.get("generatedAt"),
        "dekking": {
            k: ov.get(k)
            for k in ("statusCounts", "executableCount", "abstainCount", "coverageExecutable")
        },
        "totaalRijen": len(rijen),
        "pagina": pagina,
        "artikelen": pagina_rijen,
        "vervolg": vervolg,
    }


def lijst_gios(
    instrument: str,
    locatie: str | None = None,
    identificatie: str | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """GIO-inventaris uit het officiële uitwisselpakket (pakket-index)."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    data = _lees_json(out / f"{stem}.pakket-index.json")
    gios = data.get("gio") or []
    if identificatie is not None:
        gios = [g for g in gios if g.get("locatieIdentificatie") == identificatie]
        if not gios:
            geldig = sorted(g.get("locatieIdentificatie", "") for g in (data.get("gio") or []))
            raise DsoKbFout(
                f"onbekende GIO-identificatie {identificatie!r}; geldig (eerste 100): {geldig[:100]}"
            )
    return {
        "instrument": instrument,
        "locatie": lid,
        "aantal": len(gios),
        "gios": gios[:LIMIT_MAX],
    }


def punt_in_gio(
    instrument: str,
    x: float,
    y: float,
    identificatie: str | None = None,
    locatie: str | None = None,
    out_dir: Path | None = None,
    instrumenten: dict[str, dict[str, Any]] | None = None,
    locaties: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Deterministisch punt-in-polygoon tegen de officiële GIO-geometrie (tpod/geo)."""
    out = out_dir or DEFAULT_OUT
    _meta, lid, stem = _resolve_paar(instrument, locatie, instrumenten, locaties)
    zip_pad = out / f"{stem}.pakket.zip"
    if not zip_pad.is_file():
        raise DsoKbFout(
            f"uitwisselpakket ontbreekt ({zip_pad.name}) — haal het op via de CLI "
            "met --pakket; daarna werkt deze tool op de cache"
        )
    root = str(WORKSPACE)
    if root not in sys.path:
        sys.path.insert(0, root)
    from nldt.simulation.regelrecht.tpod import geo as tpod_geo

    index = tpod_geo.geo_index_uit_pakket(zip_pad)
    resultaten = []
    for ident, item in sorted((index.get("locaties") or {}).items()):
        if identificatie is not None and ident != identificatie:
            continue
        resultaten.append(
            {"locatieIdentificatie": ident, "bevatPunt": tpod_geo.bevat_punt(item["vorm"], (x, y))}
        )
    if identificatie is not None and not resultaten:
        geldig = sorted((index.get("locaties") or {}).keys())
        raise DsoKbFout(
            f"identificatie {identificatie!r} niet koppelbaar in het pakket "
            "(allen_imow_namen — vrije namen zijn overgeslagen); "
            f"geldig (eerste 100): {geldig[:100]}"
        )
    return {
        "instrument": instrument,
        "locatie": lid,
        "punt": {"x": x, "y": y, "crs": "EPSG:28992"},
        "overgeslagenNamen": index.get("overgeslagen"),
        "aantal": len(resultaten),
        "gios": resultaten,
    }


def _normaliseer(obj: Any) -> Any:
    """Recursief volgorde-onafhankelijk + datumecho-vrij (spec §5)."""
    if isinstance(obj, dict):
        return {k: _normaliseer(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        items = [_normaliseer(x) for x in obj]
        return sorted(items, key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
    if isinstance(obj, str) and obj.startswith("http"):
        onderdelen = urlsplit(obj)
        query = parse_qsl(onderdelen.query, keep_blank_values=True)
        gefilterd = [(k, v) for k, v in query if k not in _DATUM_PARAMS]
        if len(gefilterd) != len(query):
            return urlunsplit(
                (onderdelen.scheme, onderdelen.netloc, onderdelen.path, urlencode(gefilterd), onderdelen.fragment)
            )
    return obj


def _regel_multiset(annotaties: dict[str, Any]) -> dict[str, list[tuple]]:
    uit: dict[str, list[tuple]] = {}
    for veld in ("regelsVoorIedereen", "instructieregels"):
        for regel in annotaties.get(veld) or []:
            ident = regel.get("identificatie", "")
            tupels = sorted(
                (
                    ala.get("activiteitRef") or "",
                    tuple(sorted(ala.get("locatieRefs") or [])),
                    ((ala.get("symbolisatie") or {}).get("symboolcode") or ""),
                )
                for ala in regel.get("activiteitLocatieaanduidingen") or []
            )
            uit.setdefault(ident, []).extend(tupels)
    return uit


def _per_identificatie(lijst: list[Any] | None) -> dict[str, Any]:
    return {
        item.get("identificatie", ""): _normaliseer(item) for item in (lijst or [])
    }


def canonieke_drift(oud: dict[str, Any], nieuw: dict[str, Any]) -> dict[str, Any]:
    """Canonieke (volgorde- en datumecho-onafhankelijke) vergelijking van annotatie-responsies."""
    categorieen: dict[str, Any] = {}

    wids_o = {r.get("wId") for r in oud.get("regelteksten") or []}
    wids_n = {r.get("wId") for r in nieuw.get("regelteksten") or []}
    if wids_o != wids_n:
        categorieen["regelteksten"] = {
            "erbij": sorted(wids_n - wids_o),
            "weg": sorted(wids_o - wids_n),
        }

    regels_o, regels_n = _regel_multiset(oud), _regel_multiset(nieuw)
    gewijzigd = sorted(
        ident
        for ident in set(regels_o) | set(regels_n)
        if sorted(regels_o.get(ident, [])) != sorted(regels_n.get(ident, []))
    )
    if gewijzigd:
        categorieen["regels"] = {"gewijzigd": gewijzigd}

    for naam in ("locaties", "gebiedsaanwijzingen"):
        rec_o, rec_n = _per_identificatie(oud.get(naam)), _per_identificatie(nieuw.get(naam))
        anders = sorted(k for k in set(rec_o) | set(rec_n) if rec_o.get(k) != rec_n.get(k))
        if anders:
            categorieen[naam] = {"gewijzigd": anders}

    return {
        "inhoudelijkeDrift": "wel" if categorieen else "geen",
        "categorieen": categorieen,
    }

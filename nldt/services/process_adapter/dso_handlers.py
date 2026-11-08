"""Thin OGC Process wrappers over de DSO-kennisbank-leeslaag.

Spec: docs/superpowers/specs/2026-11-07-dso-kb-mcp-design.md. Alle lees-
processen zijn puur (cache); alleen dso-kb-refresh heeft een side-effect
(en is als zodanig gelabeld). DsoKbFout wordt een {"error": …}-resultaat,
geen crash: agents moeten de geldige lijst te zien krijgen.
"""

from __future__ import annotations

from typing import Any

from services import dso_kb


def _wrap(fn, **kwargs):
    try:
        return {"result": fn(**kwargs)}
    except dso_kb.DsoKbFout as exc:
        return {"error": str(exc)}


def _definitie(pid: str, titel: str, beschrijving: str, inputs: dict[str, Any], *, side_effect: bool = False) -> dict[str, Any]:
    d = {
        "id": pid,
        "title": titel,
        "description": beschrijving,
        "version": "1.0.0",
        "keywords": ["dso", "kennisbank", "regelrecht"],
        "inputs": inputs,
        "outputs": {"result": {"title": "Resultaat (of error)", "schema": {"type": "object"}}},
    }
    if side_effect:
        d["sideEffect"] = True
    return d


def _I(schema: dict[str, Any], titel: str, default: Any = None) -> dict[str, Any]:
    """Inputspec-helper: schema + titel + optionele default."""
    uit: dict[str, Any] = {"title": titel, "schema": schema}
    if default is not None:
        uit["default"] = default
    return uit


DSO_PROCESS_DEFINITIONS: dict[str, dict[str, Any]] = {
    "dso-kb-overview": _definitie(
        "dso-kb-overview", "DSO-kennisbank overzicht",
        "Instrumenten × locaties met freshness (sha256), dekkingscijfers en aanwezige artefacten.",
        {},
    ),
    "dso-kb-annotations": _definitie(
        "dso-kb-annotations", "DSO-annotaties per artikel",
        "Regeltekstannotaties per artikelnummer (wId-gegroepeerd), gebonden en filterbaar; detail geeft de regelteksten.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id (eindhoven|utrecht)"),
            "locatie": _I({"type": "string"}, "Locatie-id (default: instrumentdefault)"),
            "artikel": _I({"type": "string"}, "Filter op artikelnummer, bv. '2.1'"),
            "detail": _I({"type": "boolean"}, "Volledige regelteksten bij het gefilterde artikel", False),
            "maxItems": _I({"type": "integer"}, "Uitvoerbegrenzing (default 100, max 500)", 100),
        },
    ),
    "dso-kb-document-structure": _definitie(
        "dso-kb-document-structure", "Documentstructuur (vlak)",
        "Componentenboom als vlakke reeks (soort, wId, titel, diepte) met wIdPrefix-filter.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
            "wIdPrefix": _I({"type": "string"}, "Filter op wId-prefix"),
            "maxItems": _I({"type": "integer"}, "Uitvoerbegrenzing", 100),
        },
    ),
    "dso-kb-tpod": _definitie(
        "dso-kb-tpod", "TPOD-index samenvatting",
        "wId-anchoring, geoFeiten, activiteiten en pons-status op de fixture-locatie.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
        },
    ),
    "dso-kb-toets": _definitie(
        "dso-kb-toets", "RegelRecht-punttoets",
        "feit/afwezigheid/scenario/onthouding per artikel op de gecachte locatie.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
            "artikel": _I({"type": "string"}, "Filter op artikelnummer"),
        },
    ),
    "dso-kb-overlap": _definitie(
        "dso-kb-overlap", "DSO↔RegelRecht-dekking",
        "Coverage + per-artikel statusrijen, filterbaar op status en gepagineerd.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
            "status": _I({"type": "string"}, "Filter op rrStatus (formalized|ambiguous|rejected|unmatched|missing_in_report)"),
            "pagina": _I({"type": "integer"}, "Pagina (100 rijen per pagina)", 1),
        },
    ),
    "dso-kb-gios": _definitie(
        "dso-kb-gios", "GIO-inventaris",
        "GIO's uit het officiële uitwisselpakket (locatieIdentificatie + gml-bestand).",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
            "identificatie": _I({"type": "string"}, "Filter op IMOW-locatieIdentificatie"),
        },
    ),
    "dso-kb-point-in-gio": _definitie(
        "dso-kb-point-in-gio", "Punt-in-GIO-toets",
        "Deterministisch punt-in-polygoon (EPSG:28992) tegen de officiële GIO-geometrie.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "x": _I({"type": "number"}, "RD x-coördinaat"),
            "y": _I({"type": "number"}, "RD y-coördinaat"),
            "identificatie": _I({"type": "string"}, "Optioneel: toets alléén deze GIO"),
        },
    ),
    "dso-kb-refresh": _definitie(
        "dso-kb-refresh", "Kennisbank verversen (live PRE)",
        "Live refresh via compare + tpod-herbouw; antwoordt met sha's en canonieke drift-uitslag. Enige proces met side-effect; keys blijven server-side.",
        {
            "instrument": _I({"type": "string"}, "Instrument-id"),
            "locatie": _I({"type": "string"}, "Locatie-id"),
            "metTpod": _I({"type": "boolean"}, "Herbouw tpod-index + toets + geo-validatie", True),
        },
        side_effect=True,
    ),
}


def execute_dso_overview(_inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(dso_kb.instrumenten_overzicht)


def execute_dso_annotations(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lees_annotaties,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        artikel=inputs.get("artikel"),
        detail=bool(inputs.get("detail")),
        limiet=inputs.get("maxItems"),
    )


def execute_dso_document_structure(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lees_documentstructuur,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        wId_prefix=inputs.get("wIdPrefix"),
        limiet=inputs.get("maxItems"),
    )


def execute_dso_tpod(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lees_tpod,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
    )


def execute_dso_toets(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lees_toets,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        artikel=inputs.get("artikel"),
    )


def execute_dso_overlap(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lees_overlap,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        status=inputs.get("status"),
        pagina=int(inputs.get("pagina") or 1),
    )


def execute_dso_gios(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.lijst_gios,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        identificatie=inputs.get("identificatie"),
    )


def execute_dso_point_in_gio(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.punt_in_gio,
        instrument=inputs["instrument"],
        x=float(inputs["x"]),
        y=float(inputs["y"]),
        identificatie=inputs.get("identificatie"),
    )


def execute_dso_refresh(inputs: dict[str, Any]) -> dict[str, Any]:
    return _wrap(
        dso_kb.ververs,
        instrument=inputs["instrument"],
        locatie=inputs.get("locatie"),
        met_tpod=bool(inputs.get("metTpod", True)),
    )


EXECUTORS = {
    "dso-kb-overview": execute_dso_overview,
    "dso-kb-annotations": execute_dso_annotations,
    "dso-kb-document-structure": execute_dso_document_structure,
    "dso-kb-tpod": execute_dso_tpod,
    "dso-kb-toets": execute_dso_toets,
    "dso-kb-overlap": execute_dso_overlap,
    "dso-kb-gios": execute_dso_gios,
    "dso-kb-point-in-gio": execute_dso_point_in_gio,
    "dso-kb-refresh": execute_dso_refresh,
}


def execute_dso_process(process_id: str, inputs: dict[str, Any]) -> dict[str, Any]:
    fn = EXECUTORS.get(process_id)
    if fn is None:
        raise KeyError(process_id)
    return fn(inputs)

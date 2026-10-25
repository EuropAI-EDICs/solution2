"""TpOD-index van de IMOW-annotatielaag (Geonovum STOP/TPOD) voor de RegelRecht-track.

Kansenkaart: docs/POC_TPOD_IMOW_KANSEN.md. Offline bouwbaar op de gecachte
Presenteren-antwoorden van ``dso_overlap``; haalt zelf geen data op.
"""
from .annotaties import (
    activiteit_structuur,
    geo_feiten,
    parse_regels,
    parse_regelteksten,
    parse_wid,
    pons_annotaties,
)
from .index import CONTRACT, build_index
from .toets import CONTRACT as TOETS_CONTRACT, build_toets, match_gebiedsaanwijzing

__all__ = [
    "CONTRACT",
    "TOETS_CONTRACT",
    "activiteit_structuur",
    "build_index",
    "build_toets",
    "geo_feiten",
    "match_gebiedsaanwijzing",
    "parse_regels",
    "parse_regelteksten",
    "parse_wid",
    "pons_annotaties",
]

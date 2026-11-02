"""GIS-zonecheck (F1): adres-fixtures + punt-in-polygoon, stdlib-only.

Productie vervangt de fixtures door de interne GIS-diensten van Stad Gent
(FR-23); de adapter-interface blijft gelijk."""

from __future__ import annotations

import json
from pathlib import Path


class AddressError(Exception):
    """Adres staat niet in de fixture; productie: geocoding-service."""


def _outer_rings(geometry: dict) -> list[list[tuple[float, float]]]:
    """Buitenringen van Polygon én MultiPolygon (gaten genegeerd — PoC-restitutie)."""
    if not geometry:
        return []
    if geometry.get("type") == "Polygon":
        return [[tuple(p) for p in geometry["coordinates"][0]]]
    if geometry.get("type") == "MultiPolygon":
        return [[tuple(p) for p in poly[0]] for poly in geometry["coordinates"]]
    return []


def load_zones(poc_root: Path) -> dict:
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    zones: dict = {}
    for feat in fc["features"]:
        layer = feat["properties"]["layer"]
        zones.setdefault(layer, []).extend(_outer_rings(feat.get("geometry")))
    return zones


def load_layer_versies(poc_root: Path) -> dict[str, str]:
    """Versie per laag uit de cache (bronvermelding in herkomst, DATA-01)."""
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    return {feat["properties"]["layer"]: feat["properties"].get("versie", "onbekende brondata")
            for feat in fc["features"]}


def load_ring_attributen(poc_root: Path) -> dict[str, list[str | None]]:
    """Attribuutwaarde per ring, in dezelfde volgorde als load_zones per laag
    ringen aanlevert (één feature kan meerdere ringen hebben: dezelfde waarde).
    Lagen zonder attribuut leveren None per ring (binaire checks negeren dit)."""
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    attributen: dict[str, list] = {}
    for feat in fc["features"]:
        laag = feat["properties"]["layer"]
        waarde = feat["properties"].get("attribuut")
        attributen.setdefault(laag, []).extend([waarde] * len(_outer_rings(feat.get("geometry"))))
    return attributen


def attribuut_result(zones: dict, ring_attributen: dict, layer: str,
                     lon: float, lat: float) -> str:
    """Benoemde zone-lookup: attribuutwaarde van de eerste treffende ring;
    lege waarde telt als 'in' (zone bestaat, naam onbekend in de bron)."""
    for idx, ring in enumerate(zones.get(layer, [])):
        if point_in_ring(lon, lat, ring):
            waarden = ring_attributen.get(layer) or [None] * len(zones.get(layer, []))
            waarde = waarden[idx] if idx < len(waarden) else None
            return waarde if waarde else "in"
    return "niet-in"


def lookup_address(poc_root: Path, address: str) -> tuple[float, float]:
    addrs = json.loads((poc_root / "fixtures" / "addresses.json").read_text(encoding="utf-8"))
    if address not in addrs:
        raise AddressError(f"onbekend adres: {address}")
    lon, lat = addrs[address]
    return lon, lat


def point_in_ring(lon: float, lat: float, ring) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = xi + (lat - yi) * (xj - xi) / (yj - yi)
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def zone_result(zones: dict, layer: str, lon: float, lat: float) -> str:
    for ring in zones.get(layer, []):
        if point_in_ring(lon, lat, ring):
            return "in"
    return "niet-in"


def apply_checks(manifest: dict, context: dict, herkomst: dict, poc_root: Path, suffix: str = "") -> None:
    """Voer alle gisChecks uit het manifest uit op hun input-slot (F1: alleen
    'address' — afgedwongen door de pakketlader) en schrijf de zone-uitkomsten
    weg met afgeleid-herkomst. Mutatie van context/herkomst is bewust: de caller
    geeft kopieën mee (context.build / gates.confirm_h1)."""
    zones = load_zones(poc_root)
    versies = load_layer_versies(poc_root)
    ring_attributen = load_ring_attributen(poc_root) \
        if any(check.get("attribuut") for check in manifest.get("gisChecks", [])) else {}
    for check in manifest.get("gisChecks", []):
        adres = context.get(check["input"])
        if adres is None:
            continue
        lon, lat = lookup_address(poc_root, adres)
        if check.get("attribuut"):
            context[check["output"]] = attribuut_result(zones, ring_attributen,
                                                        check["layer"], lon, lat)
        else:
            context[check["output"]] = zone_result(zones, check["layer"], lon, lat)
        versie = versies.get(check["layer"], "onbekende brondata")
        herkomst[check["output"]] = {"label": "afgeleid", "bron": f"gis:{check['layer']} ({versie}{suffix})"}

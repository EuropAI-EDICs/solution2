"""GIS-zonecheck (F1): adres-fixtures + punt-in-polygoon, stdlib-only.

Productie vervangt de fixtures door de interne GIS-diensten van Stad Gent
(FR-23); de adapter-interface blijft gelijk."""

from __future__ import annotations

import json
from pathlib import Path


class AddressError(Exception):
    """Adres staat niet in de fixture; productie: geocoding-service."""


def load_zones(poc_root: Path) -> dict:
    fc = json.loads((poc_root / "fixtures" / "gis-zones.geojson").read_text(encoding="utf-8"))
    zones: dict = {}
    for feat in fc["features"]:
        layer = feat["properties"]["layer"]
        ring = [tuple(p) for p in feat["geometry"]["coordinates"][0]]
        zones.setdefault(layer, []).append(ring)
    return zones


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

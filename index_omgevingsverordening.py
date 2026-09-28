#!/usr/bin/env python3
"""
Indexeer de Omgevingsverordening-data in Elasticsearch voor time-series analyses.
"""

import json
from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta
import random
from pyproj import Transformer

# Configuratie
ES_HOST = "http://localhost:9200"
INDEX_NAME = "ldt_time_series"
INPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/omgevingsverordening.geojson"

# Maak verbinding met Elasticsearch
es = Elasticsearch(ES_HOST)
print(f"Verbonden met Elasticsearch: {es.info()}")

# Laad de dataset
with open(INPUT_FILE) as f:
    geojson_data = json.load(f)

# Voeg een dummy vaststellingsdatum toe (random datum tussen 2020 en 2024)
def add_vaststellingsdatum(feature):
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 12, 31)
    random_days = random.randint(0, (end_date - start_date).days)
    vaststellingsdatum = (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")
    feature["properties"]["vaststellingsdatum"] = vaststellingsdatum
    return feature

# Voeg vaststellingsdatum toe aan alle features
geojson_data["features"] = [add_vaststellingsdatum(feature) for feature in geojson_data["features"]]

# Maak een transformer voor RD New (EPSG:28992) naar WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

def convert_rd_to_wgs84(coords):
    """Converteer RD New-coördinaten naar WGS84."""
    return [transformer.transform(x, y) for x, y in coords]

# Indexeer in Elasticsearch
actions = []
for feature in geojson_data["features"]:
    # Voeg 'type' toe aan de geometrie (vereist voor geo_shape)
    geometry = feature["geometry"].copy()
    if "rings" in geometry:
        geometry["type"] = "Polygon"
        # Converteer coördinaten van RD New naar WGS84
        wgs84_rings = []
        for ring in geometry["rings"]:
            wgs84_ring = [transformer.transform(x, y) for x, y in ring]
            wgs84_rings.append(wgs84_ring)
        geometry["coordinates"] = wgs84_rings
        del geometry["rings"]  # Verwijder het 'rings'-veld
        del geometry["spatialReference"]  # Verwijder spatialReference
        
        # Voeg H3-cellen toe (resolutie 9)
        import h3
        h3_cells = set()
        for ring in wgs84_rings:
            for lon, lat in ring:
                h3_cell = h3.latlng_to_cell(lat, lon, 9)
                h3_cells.add(h3_cell)
        
        actions.append({
            "_index": INDEX_NAME,
            "_id": feature["properties"]["OBJECTID"],
            "_source": {
                "geometry": geometry,
                "properties": feature["properties"],
                "h3_cells": list(h3_cells)
            }
        })
    else:
        actions.append({
            "_index": INDEX_NAME,
            "_id": feature["properties"]["OBJECTID"],
            "_source": {
                "geometry": geometry,
                "properties": feature["properties"]
            }
        })

# Voer bulk-indexering uit
helpers.bulk(es, actions)
print(f"Geïndexeerd: {len(actions)} features in Elasticsearch")
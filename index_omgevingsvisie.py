#!/usr/bin/env python3
"""
Indexeer de Omgevingsvisie-data in Elasticsearch voor time-series analyses.
"""

import json
from elasticsearch import Elasticsearch, helpers
from datetime import datetime, timedelta
import random
from pyproj import Transformer

# Configuratie
ES_HOST = "http://localhost:9200"
INDEX_NAME = "ldt_omgevingsvisie"
INPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/omgevingsvisie.geojson"

# Maak verbinding met Elasticsearch
es = Elasticsearch(ES_HOST)
print(f"Verbonden met Elasticsearch: {es.info()}")

# Maak een transformer voor RD New (EPSG:28992) naar WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

def convert_rd_to_wgs84(coords):
    """Converteer RD New-coördinaten naar WGS84."""
    return [transformer.transform(x, y) for x, y in coords]

# Maak de Elasticsearch-index aan
index_body = {
    "mappings": {
        "properties": {
            "geometry": { "type": "geo_shape" },
            "properties": {
                "properties": {
                    "OBJECTID": { "type": "integer" },
                    "NAAM": { "type": "text" },
                    "TYPE": { "type": "keyword" },
                    "GROEP": { "type": "keyword" },
                    "vaststellingsdatum": { "type": "date" }
                }
            }
        }
    }
}

if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(index=INDEX_NAME, body=index_body)
    print(f"Index '{INDEX_NAME}' aangemaakt.")

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

# Indexeer in Elasticsearch
actions = []
for feature in geojson_data["features"]:
    # Voeg 'type' toe aan de geometrie (vereist voor geo_shape)
    geometry = feature["geometry"].copy()
    if "rings" in geometry:
        geometry["type"] = "Polygon"
        # Converteer coördinaten van RD New naar WGS84
        geometry["coordinates"] = [
            [transformer.transform(x, y) for x, y in ring]
            for ring in geometry["rings"]
        ]
        del geometry["rings"]  # Verwijder het 'rings'-veld
        del geometry["spatialReference"]  # Verwijder spatialReference
    
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
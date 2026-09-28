#!/usr/bin/env python3
"""
Indexeer Natura 2000-gebieden in Elasticsearch.
"""

import json
from elasticsearch import Elasticsearch, helpers
from pyproj import Transformer

# Configuratie
ES_HOST = "http://localhost:9200"
INDEX_NAME = "ldt_natura2000"
INPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/natura2000.geojson"

# Maak verbinding met Elasticsearch
es = Elasticsearch(ES_HOST)
print(f"Verbonden met Elasticsearch: {es.info()}")

# Maak een transformer voor RD New (EPSG:28992) naar WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

# Maak de Elasticsearch-index aan
index_body = {
    "mappings": {
        "properties": {
            "geometry": { "type": "geo_shape" },
            "properties": {
                "properties": {
                    "OBJECTID": { "type": "integer" },
                    "NAAM": { "type": "text", "fields": { "keyword": { "type": "keyword" } } },
                    "TYPE": { "type": "keyword" },
                    "BESCHERMING": { "type": "keyword" }
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

# Indexeer in Elasticsearch
actions = []
for feature in geojson_data["features"]:
    # Voeg 'type' toe aan de geometrie (vereist voor geo_shape)
    geometry = feature["geometry"].copy()
    if geometry["type"] == "Polygon":
        # Converteer coördinaten van RD New naar WGS84
        geometry["coordinates"] = [
            [transformer.transform(x, y) for x, y in ring]
            for ring in geometry["coordinates"]
        ]
    elif geometry["type"] == "MultiPolygon":
        # Converteer coördinaten van RD New naar WGS84
        geometry["coordinates"] = [
            [[transformer.transform(x, y) for x, y in ring] for ring in polygon]
            for polygon in geometry["coordinates"]
        ]
    
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
print(f"Geïndexeerd: {len(actions)} Natura 2000-gebieden in Elasticsearch")
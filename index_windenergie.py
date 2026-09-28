#!/usr/bin/env python3
"""
Indexeer windenergiegebieden in Elasticsearch.
"""

import json
from elasticsearch import Elasticsearch, helpers
from pyproj import Transformer
import h3

# Configuratie
ES_HOST = "http://localhost:9200"
INDEX_NAME = "ldt_windenergie"
INPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson"

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
                    "STATUS": { "type": "keyword" },
                    "PLANJAAR": { "type": "integer" }
                }
            },
            "h3_cells": { "type": "keyword" }
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
    # Sla zelfdoorsnijdende polygonen over
    try:
        # Voeg 'type' toe aan de geometrie (vereist voor geo_shape)
        geometry = feature["geometry"].copy()
        if geometry["type"] == "Polygon":
            # Converteer coördinaten van RD New naar WGS84
            geometry["coordinates"] = [
            [transformer.transform(x, y) for x, y in ring]
            for ring in geometry["coordinates"]
        ]
        
        # Voeg H3-cellen toe (resolutie 9)
        h3_cells = set()
        for ring in geometry["coordinates"]:
            for lon, lat in ring:
                h3_cell = h3.latlng_to_cell(lat, lon, 9)
                h3_cells.add(h3_cell)
        
        actions.append({
            "_index": INDEX_NAME,
            "_id": feature.get("id", feature["properties"].get("FID")),
            "_source": {
                "geometry": geometry,
                "properties": feature["properties"],
                "h3_cells": list(h3_cells)
            }
        })
    except Exception as e:
        print(f"Feature {feature.get('id')} overgeslagen vanwege fout: {str(e)}")
        continue
    else:
        actions.append({
            "_index": INDEX_NAME,
            "_id": feature.get("id", feature["properties"].get("FID")),
            "_source": {
                "geometry": geometry,
                "properties": feature["properties"]
            }
        })

# Voer bulk-indexering uit
helpers.bulk(es, actions)
print(f"Geïndexeerd: {len(actions)} windenergiegebieden in Elasticsearch")
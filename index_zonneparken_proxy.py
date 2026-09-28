#!/usr/bin/env python3
"""
Indexeer een subset van de Omgevingsvisie als "zonneparken" (proxy).
"""

import json
from elasticsearch import Elasticsearch, helpers
from pyproj import Transformer
import h3

# Configuratie
ES_HOST = "http://localhost:9200"
INDEX_NAME = "ldt_zonneparken"
INPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/omgevingsvisie.geojson"

# Maak verbinding met Elasticsearch
es = Elasticsearch(ES_HOST)
print(f"Verbonden met Elasticsearch: {es.info()}")

# Maak een transformer voor RD New (EPSG:28992) naar WGS84 (EPSG:4326)
transformer = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)

# Laad de dataset
with open(INPUT_FILE) as f:
    geojson_data = json.load(f)

# Indexeer een subset van de Omgevingsvisie als "zonneparken" (proxy)
actions = []
for feature in geojson_data["features"][:50]:  # Gebruik eerste 50 features als proxy
    # Sla zelfdoorsnijdende polygonen over
    try:
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
            
            # Voeg H3-cellen toe (resolutie 9)
            h3_cells = set()
            for ring in geometry["coordinates"]:
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
        elif geometry["type"] == "MultiPolygon":
            # Converteer coördinaten van RD New naar WGS84
            geometry["coordinates"] = [
                [[transformer.transform(x, y) for x, y in ring] for ring in polygon]
                for polygon in geometry["coordinates"]
            ]
            
            # Voeg H3-cellen toe (resolutie 9)
            h3_cells = set()
            for polygon in geometry["coordinates"]:
                for ring in polygon:
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
    except Exception as e:
        print(f"Feature {feature['properties']['OBJECTID']} overgeslagen vanwege fout: {str(e)}")
        continue

# Voer bulk-indexering uit
helpers.bulk(es, actions)
print(f"Geïndexeerd: {len(actions)} zonneparken (proxy) in Elasticsearch")
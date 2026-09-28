#!/usr/bin/env python3
"""
Haal de Omgevingsvisie van de provincie Utrecht op en sla op als GeoJSON.
"""

import json
import requests

# Configuratie
AGREST_URL = "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsvisie/FeatureServer/0/query"
OUTPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/omgevingsvisie.geojson"

# Parameters voor de API-aanroep
params = {
    "where": "1=1",
    "outFields": "*",
    "f": "json",
    "outSR": "28992",
    "resultRecordCount": "1000"
}

# Haal data op van de Agrest API
response = requests.get(AGREST_URL, params=params)
response.raise_for_status()
esri_data = response.json()

# Converteer ESRI JSON naar GeoJSON
geojson_data = {
    "type": "FeatureCollection",
    "features": []
}

for feature in esri_data.get("features", []):
    geojson_feature = {
        "type": "Feature",
        "properties": feature.get("attributes", {}),
        "geometry": feature.get("geometry", {})
    }
    geojson_data["features"].append(geojson_feature)

# Sla op als GeoJSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(geojson_data, f, indent=2)

print(f"Opgeslagen: {len(geojson_data['features'])} features in {OUTPUT_FILE}")
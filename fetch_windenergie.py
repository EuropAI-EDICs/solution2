#!/usr/bin/env python3
"""
Haal windenergiegebieden op van de ArcGIS Hub en sla op als GeoJSON.
"""

import json
import requests

# Configuratie
ARCGIS_URL = "https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/ET_wind_gebieden_windenergie/FeatureServer/13/query"
OUTPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson"

# Parameters voor de API-aanroep
params = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "outSR": "28992"
}

# Haal data op van de ArcGIS Hub
response = requests.get(ARCGIS_URL, params=params)
response.raise_for_status()
geojson_data = response.json()

# Voeg metadata toe voor Logstash
geojson_data["@metadata"] = {
    "index_suffix": "windenergie"
}

# Sla op als GeoJSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(geojson_data, f, indent=2)

print(f"Opgeslagen: {len(geojson_data['features'])} windenergiegebieden in {OUTPUT_FILE}")
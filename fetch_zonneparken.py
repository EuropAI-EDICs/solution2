#!/usr/bin/env python3
"""
Haal zonneparken op van de ArcGIS Hub en sla op als GeoJSON.
"""

import json
import requests

# Configuratie
ARCGIS_URL = "https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/ET_zonne_gebieden_zonneparken/FeatureServer/12/query"
OUTPUT_FILE = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/zonneparken.geojson"

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
    "index_suffix": "zonneparken"
}

# Sla op als GeoJSON
with open(OUTPUT_FILE, "w") as f:
    json.dump(geojson_data, f, indent=2)

print(f"Opgeslagen: {len(geojson_data['features'])} zonneparken in {OUTPUT_FILE}")
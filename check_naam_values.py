#!/usr/bin/env python3
"""
Controleer welke unieke waarden het veld 'NAAM' heeft in de Omgevingsverordening.
"""

import json
import requests
from collections import defaultdict

# Configuratie
AGREST_URL = "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0/query"

# Parameters voor de API-aanroep
params = {
    "where": "1=1",
    "outFields": "NAAM",
    "f": "json",
    "outSR": "28992",
    "resultRecordCount": "1000"
}

# Haal data op van de Agrest API
response = requests.get(AGREST_URL, params=params)
response.raise_for_status()
esri_data = response.json()

# Verzamel unieke NAAM-waarden
naam_counts = defaultdict(int)
for feature in esri_data.get("features", []):
    naam = feature.get("attributes", {}).get("NAAM")
    if naam:
        naam_counts[naam] += 1

# Print unieke NAAM-waarden
print("Unieke NAAM-waarden in de Omgevingsverordening:")
for naam, count in sorted(naam_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"- {naam}: {count} features")
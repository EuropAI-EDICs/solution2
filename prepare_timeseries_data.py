#!/usr/bin/env python3
"""
Voeg een dummy tijdveld toe aan de windenergiegebieden-dataset voor time-series analyses.
"""

import json
from datetime import datetime, timedelta
import random

# Laad de dataset
with open("/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson") as f:
    geojson_data = json.load(f)

# Voeg een dummy vaststellingsdatum toe (random datum tussen 2020 en 2024)
for feature in geojson_data["features"]:
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 12, 31)
    random_days = random.randint(0, (end_date - start_date).days)
    vaststellingsdatum = (start_date + timedelta(days=random_days)).strftime("%Y-%m-%d")
    feature["properties"]["vaststellingsdatum"] = vaststellingsdatum

# Sla de aangepaste dataset op
output_path = "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie_timeseries.geojson"
with open(output_path, "w") as f:
    json.dump(geojson_data, f, indent=2)

print(f"Dataset met tijdveld opgeslagen als: {output_path}")
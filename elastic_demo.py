#!/usr/bin/env python3
"""
Streamlit-demo voor de Elasticsearch-integratie met de LDT Toolbox.
"""

import streamlit as st
from elasticsearch import Elasticsearch
import pandas as pd
import pydeck as pdk
import h3
import json

# Configuratie
ES_HOST = "http://localhost:9200"
INDICES = {
    "Omgevingsverordening": "ldt_time_series",
    "Omgevingsvisie": "ldt_omgevingsvisie",
    "Natura 2000": "ldt_natura2000",
    "Windenergie": "ldt_windenergie",
    "Zonneparken": "ldt_zonneparken"
}

# Maak verbinding met Elasticsearch
es = Elasticsearch(ES_HOST)

# Titel
st.title("Elasticsearch-integratie met de LDT Toolbox")
st.markdown("""
Deze demo toont hoe **Elasticsearch** kan worden gebruikt voor:
- **Snelle zoekopdrachten** (full-text, ruimtelijk, attributen).
- **Krachtige analyses** (trends, aggregaties, anomaliedetectie).
- **Interactieve visualisaties** (kaarten, grafieken).
""")

# Sidebar voor filters
st.sidebar.header("Filters")
selected_index = st.sidebar.selectbox("Kies een dataset", list(INDICES.keys()))
index_name = INDICES[selected_index]

# Query-opties
st.sidebar.header("Query-opties")
query_type = st.sidebar.selectbox(
    "Kies een query-type",
    ["Alle documenten", "Trendanalyse", "Ruimtelijke query", "H3-analyse"]
)

# Functie om query uit te voeren
def execute_query(index, query_type):
    if query_type == "Alle documenten":
        query = {
            "query": { "match_all": {} },
            "size": 100
        }
    elif query_type == "Trendanalyse":
        query = {
            "size": 0,
            "aggs": {
                "trend_per_groep": {
                    "terms": { "field": "properties.GROEP.keyword", "size": 10 },
                    "aggs": {
                        "aantal_documenten": { "value_count": { "field": "properties.OBJECTID" } }
                    }
                }
            }
        }
    elif query_type == "Ruimtelijke query":
        query = {
            "query": {
                "geo_shape": {
                    "geometry": {
                        "shape": {
                            "type": "envelope",
                            "coordinates": [[5.0, 52.5], [5.5, 52.0]]  # Utrecht
                        },
                        "relation": "intersects"
                    }
                }
            },
            "size": 100
        }
    elif query_type == "H3-analyse":
        query = {
            "query": { "exists": { "field": "h3_cells" } },
            "size": 100
        }
    
    result = es.search(index=index, body=query)
    return result

# Query uitvoeren
result = execute_query(index_name, query_type)

# Resultaten weergeven
st.header(f"Resultaten voor {selected_index}")

if query_type == "Alle documenten":
    hits = result["hits"]["hits"]
    if hits:
        st.subheader("Documenten")
        for hit in hits:
            st.json(hit["_source"])
    else:
        st.warning("Geen documenten gevonden.")

elif query_type == "Trendanalyse":
    buckets = result["aggregations"]["trend_per_groep"]["buckets"]
    if buckets:
        st.subheader("Trendanalyse")
        df = pd.DataFrame(buckets)
        st.bar_chart(df.set_index("key"))
    else:
        st.warning("Geen resultaten voor trendanalyse.")

elif query_type == "Ruimtelijke query":
    hits = result["hits"]["hits"]
    if hits:
        st.subheader("Ruimtelijke query")
        # Maak een kaart met PyDeck
        features = [hit["_source"] for hit in hits]
        geojson = {
            "type": "FeatureCollection",
            "features": []
        }
        for feature in features:
            geojson["features"].append({
                "type": "Feature",
                "geometry": feature["geometry"],
                "properties": feature["properties"]
            })
        
        # Toon kaart
        st.pydeck_chart(pdk.Deck(
            map_style="mapbox://styles/mapbox/light-v9",
            initial_view_state=pdk.ViewState(
                latitude=52.1,
                longitude=5.1,
                zoom=10,
                pitch=50,
            ),
            layers=[
                pdk.Layer(
                    "GeoJsonLayer",
                    data=geojson,
                    get_fill_color=[255, 0, 0, 100],
                    pickable=True
                )
            ]
        ))
    else:
        st.warning("Geen resultaten voor ruimtelijke query.")

elif query_type == "H3-analyse":
    hits = result["hits"]["hits"]
    if hits:
        st.subheader("H3-analyse")
        # Toon H3-cellen op een kaart
        h3_cells = set()
        for hit in hits:
            if "h3_cells" in hit["_source"]:
                h3_cells.update(hit["_source"]["h3_cells"])
        
        if h3_cells:
            # Converteer H3-cellen naar GeoJSON
            features = []
            for h3_cell in h3_cells:
                boundary = h3.h3_set_to_multi_polygon([h3_cell], geo_json=True)
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": boundary[0]
                    },
                    "properties": { "h3_cell": h3_cell }
                })
            
            geojson = {
                "type": "FeatureCollection",
                "features": features
            }
            
            # Toon kaart
            st.pydeck_chart(pdk.Deck(
                map_style="mapbox://styles/mapbox/light-v9",
                initial_view_state=pdk.ViewState(
                    latitude=52.1,
                    longitude=5.1,
                    zoom=10,
                    pitch=50,
                ),
                layers=[
                    pdk.Layer(
                        "GeoJsonLayer",
                        data=geojson,
                        get_fill_color=[0, 255, 0, 100],
                        pickable=True
                    )
                ]
            ))
        else:
            st.warning("Geen H3-cellen gevonden.")
    else:
        st.warning("Geen resultaten voor H3-analyse.")

# Footer
st.markdown("---")
st.markdown("""
### Gebruikte datasets
- **Omgevingsverordening**: Juridische ruimtelijke plannen.
- **Omgevingsvisie**: Beleidsmatige ruimtelijke plannen.
- **Natura 2000**: Beschermde natuurgebieden.
- **Windenergie**: Windenergiegebieden.
- **Zonneparken**: Potentiële zonneparken (proxy).

### Technologieën
- **Elasticsearch**: Zoekmachine en analytics-engine.
- **Kibana**: Visualisatietool voor Elasticsearch.
- **Streamlit**: Framework voor interactieve webapps.
""")
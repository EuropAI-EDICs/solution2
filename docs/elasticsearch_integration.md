# Elasticsearch-integratie voor de LDT Toolbox

## **1. Inleiding**
### **1.1 Doel van dit document**
Dit document beschrijft hoe **Elasticsearch** kan worden geïntegreerd met de **LDT Toolbox-data lake** om:
- **Snelle zoekopdrachten** (full-text, ruimtelijk, attributen) mogelijk te maken.
- **Krachtige analyses en aggregaties** uit te voeren (bijv. oppervlak per gemeente).
- **Visualisaties** te maken in Kibana (kaarten, dashboards).
- **H3-analyses** te ondersteunen (bijv. "Welke H3-cellen overlappen met Natura 2000?").

### **1.2 Scope**
- **Data**: Bestemmingsplannen, omgevingsverordeningen, Natura 2000-gebieden, windenergiegebieden, etc.
- **Formaten**: GeoJSON (huidige situatie), H3 (LDT Toolbox), Elasticsearch (nieuwe integratie).
- **Use cases**: Technische analyses, juridische traceerbaarheid, visualisaties, realtime updates.

### **1.3 Doelgroep**
- **Ontwikkelaars**: Voor implementatie en onderhoud.
- **Analisten**: Voor het uitvoeren van zoekopdrachten en analyses.
- **Gebruikers**: Voor het gebruik van Kibana-dashboards.

---

## **2. Waarom Elasticsearch?**
### **2.1 Use Cases voor Elasticsearch in de LDT Toolbox**
| **Use Case**                          | **Voorbeeld**                                                                                     | **Elasticsearch-functionaliteit**                     |
|---------------------------------------|---------------------------------------------------------------------------------------------------|-------------------------------------------------------|
| **Full-text zoeken**                  | Zoek naar bestemmingsplannen met het woord "windenergie".                                      | `match_query`, `multi_match`                          |
| **Ruimtelijke zoekopdrachten**        | Vind alle H3-cellen binnen een bepaalde bounding box of polygoon.                                | `geo_shape`, `geo_bounding_box`, `geo_distance`       |
| **Attribuutfiltering**                | Filter bestemmingsplannen op `planstatus="vastgesteld"` of `NAAM="Gebied windenergie"`.      | `term`, `terms`, `range`                              |
| **Aggregaties**                       | Bereken het totale oppervlak van windenergiegebieden per gemeente.                               | `aggs` (met `sum`, `group_by`)                        |
| **H3-analyses**                       | Vind alle H3-cellen die overlappen met Natura 2000-gebieden.                                     | `geo_shape` + H3-indexering                           |
| **Dashboards (Kibana)**               | Maak een interactieve kaart van Utrecht met bestemmingsplannen en H3-cellen.                     | Kibana Maps, Lens, Dashboard                          |
| **Autocomplete**                      | Suggesties voor zoektermen (bijv. "wind", "zonne", "natuur").                              | `search_as_you_type`, `completion`                    |
| **Realtime updates**                  | Stream nieuwe bestemmingsplannen direct naar Elasticsearch.                                      | Logstash, Kafka, Elasticsearch Ingest Pipeline        |

### **2.2 Voordelen van Elasticsearch**
| **Voordeel**                                                                 | **Toelichting**                                                                                     |
|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **Snelle zoekopdrachten** (full-text, ruimtelijk, attributen)                  | Elasticsearch is geoptimaliseerd voor zoekopdrachten en kan miljoenen records in milliseconden doorzoeken. |
| **Krachtige aggregaties** (bijv. oppervlak per gemeente)                     | Ondersteunt complexe aggregaties (bijv. `sum`, `avg`, `group_by`) voor analyses.                   |
| **Integratie met Kibana** (visualisaties, dashboards)                        | Kibana biedt kant-en-klare visualisaties (kaarten, grafieken, tabellen) voor ruimtelijke data.    |
| **Realtime updates** (met Logstash/Kafka)                                    | Nieuwe data kan direct worden geïndexeerd en doorzocht.                                          |
| **Schaalbaarheid** (geschikt voor grote datasets)                            | Elasticsearch kan horizontaal worden geschaald voor grote hoeveelheden data.                     |
| **Flexibele queries** (combinatie van full-text, ruimtelijk en attributen)    | Ondersteunt complexe queries (bijv. "Zoek alle windenergiegebieden binnen een polygoon").      |

### **2.3 Nadelen van Elasticsearch**
| **Nadeel**                                                                   | **Toelichting**                                                                                     |
|--------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **Complexe setup** (mapping, indexering, optimalisatie)                      | Vereist kennis van Elasticsearch-mappings en query-syntax.                                        |
| **Geen native H3-ondersteuning** (workaround nodig)                          | H3-cellen moeten worden opgeslagen als `keyword` voor doorzoekbaarheid.                          |
| **Extra opslag en resources** nodig (Elasticsearch-cluster)                  | Elasticsearch vereist extra servers of containers voor productiegebruik.                         |
| **Leercurve** voor Elasticsearch-query's (bijv. `geo_shape`, aggregaties)     | Gebruikers moeten bekend raken met Elasticsearch-query's en Kibana.                              |

---

## **3. Architectuur**
### **3.1 Huidige situatie**
```
Agrest API / ArcGIS Hub → GeoJSON → H3 → Data Lake (nldt/data/lake/)
```

### **3.2 Voorgestelde integratie met Elasticsearch**
```
Agrest API / ArcGIS Hub → GeoJSON → H3 → Data Lake (nldt/data/lake/)
                                      ↘
                                       Elasticsearch (Indexering)
                                      ↗
Kibana (Visualisaties) ← Elasticsearch
```

### **3.3 Componenten**
| **Component**       | **Beschrijving**                                                                                     |
|----------------------|-----------------------------------------------------------------------------------------------------|
| **Data Lake**        | Bron van waarheid voor ruwe data (GeoJSON, H3).                                                    |
| **Elasticsearch**    | Indexeert GeoJSON-features en H3-cellen voor snelle zoekopdrachten en analyses.                     |
| **Kibana**           | Visualisatietool voor het maken van kaarten, grafieken en dashboards.                              |
| **ETL-proces**       | Python-scripts of Logstash voor het synchroniseren van de data lake met Elasticsearch.             |

---

## **4. Implementatie**
### **4.1 Stap 1: Installeer Elasticsearch en Kibana**
Gebruik Docker voor eenvoudige installatie:

#### **`docker-compose.yml`**
```yaml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false  # Alleen voor ontwikkeling!
    ports:
      - "9200:9200"
      - "9300:9300"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  kibana:
    image: docker.elastic.co/kibana/kibana:8.12.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch

volumes:
  es_data:
```

#### **Start de services**
```bash
docker-compose up -d
```

#### **Controleer of Elasticsearch draait**
```bash
curl http://localhost:9200
```

---

### **4.2 Stap 2: Maak een Elasticsearch-index voor ruimtelijke data**
Elasticsearch ondersteunt **`geo_shape`** en **`geo_point`** voor ruimtelijke queries.

#### **Indexmapping voor bestemmingsplannen**
```json
PUT /ldt_bestemmingsplannen
{
  "mappings": {
    "properties": {
      "geometry": {
        "type": "geo_shape"
      },
      "properties": {
        "properties": {
          "OBJECTID": { "type": "integer" },
          "LOCATIE_ID": { "type": "keyword" },
          "NAAM": { "type": "text" },
          "planstatus": { "type": "keyword" },
          "DOCUMENT_URL": { "type": "keyword" },
          "gemeente": { "type": "keyword" }
        }
      },
      "h3_index": { "type": "keyword" }  // Optioneel: H3-cel als keyword
    }
  }
}
```

#### **Python-code om de index te maken**
```python
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

index_body = {
    "mappings": {
        "properties": {
            "geometry": {"type": "geo_shape"},
            "properties": {
                "properties": {
                    "OBJECTID": {"type": "integer"},
                    "LOCATIE_ID": {"type": "keyword"},
                    "NAAM": {"type": "text"},
                    "planstatus": {"type": "keyword"},
                    "DOCUMENT_URL": {"type": "keyword"}
                }
            }
        }
    }
}

es.indices.create(index="ldt_bestemmingsplannen", body=index_body)
```

---

### **4.3 Stap 3: Indexeer data uit de LDT Toolbox**
#### **Optie A: Indexeer GeoJSON-features direct**
```python
from elasticsearch import Elasticsearch, helpers
import json

es = Elasticsearch("http://localhost:9200")

# Laad GeoJSON-data (bijv. uit de data lake)
with open("/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson") as f:
    geojson_data = json.load(f)

# Indexeer elke feature
actions = [
    {
        "_index": "ldt_bestemmingsplannen",
        "_id": feature["properties"]["OBJECTID"],
        "_source": {
            "geometry": feature["geometry"],
            "properties": feature["properties"]
        }
    }
    for feature in geojson_data["features"]
]

helpers.bulk(es, actions)
```

#### **Optie B: Indexeer H3-cellen**
```python
import h3

def add_h3_index(feature, resolution=9):
    """Voeg H3-cellen toe aan een GeoJSON-feature."""
    if feature["geometry"]["type"] == "Polygon":
        coords = feature["geometry"]["coordinates"][0]  # Buitenring
        h3_cells = set()
        for coord in coords:
            h3_cell = h3.geo_to_h3(coord[1], coord[0], resolution)
            h3_cells.add(h3_cell)
        feature["properties"]["h3_cells"] = list(h3_cells)
    return feature

# Pas H3-indexering toe op alle features
geojson_data["features"] = [add_h3_index(feature) for feature in geojson_data["features"]]

# Indexeer in Elasticsearch
actions = [
    {
        "_index": "ldt_h3_cells",
        "_id": feature["properties"]["OBJECTID"],
        "_source": {
            "geometry": feature["geometry"],
            "properties": feature["properties"],
            "h3_cells": feature["properties"]["h3_cells"]
        }
    }
    for feature in geojson_data["features"]
]

helpers.bulk(es, actions)
```

---

### **4.4 Stap 4: Voer zoekopdrachten uit in Elasticsearch**
#### **Voorbeeld 1: Zoek alle windenergiegebieden**
```json
GET /ldt_bestemmingsplannen/_search
{
  "query": {
    "match": {
      "properties.NAAM": "windenergie"
    }
  }
}
```

#### **Voorbeeld 2: Ruimtelijke query (bounding box)**
```json
GET /ldt_bestemmingsplannen/_search
{
  "query": {
    "geo_shape": {
      "geometry": {
        "shape": {
          "type": "envelope",
          "coordinates": [[130000, 450000], [135000, 455000]]  // RD New (EPSG:28992)
        },
        "relation": "intersects"
      }
    }
  }
}
```

#### **Voorbeeld 3: Aggregatie (oppervlak per gemeente)**
```json
GET /ldt_bestemmingsplannen/_search
{
  "aggs": {
    "gebieden_per_gemeente": {
      "terms": {
        "field": "properties.gemeente",
        "size": 10
      },
      "aggs": {
        "totaal_oppervlak": {
          "sum": {
            "script": {
              "source": "doc['geometry'].value.getArea()"
            }
          }
        }
      }
    }
  }
}
```

#### **Voorbeeld 4: H3-query (welke H3-cellen overlappen met Natura 2000?)**
```json
GET /ldt_h3_cells/_search
{
  "query": {
    "bool": {
      "must": [
        { "term": { "properties.NAAM": "Natura 2000" } },
        { "exists": { "field": "h3_cells" } }
      ]
    }
  }
}
```

---

### **4.5 Stap 5: Visualiseer data in Kibana**
1. **Maak een indexpatroon**:
   - Ga naar **Kibana → Stack Management → Index Patterns**. 
   - Maak een indexpatroon voor `ldt_bestemmingsplannen` en `ldt_h3_cells`.

2. **Maak een kaart**:
   - Ga naar **Kibana → Maps**.
   - Voeg een laag toe met de Elasticsearch-index `ldt_bestemmingsplannen`.
   - Kies `geometry` als geometrieveld.

3. **Maak een dashboard**:
   - Combineer kaarten, grafieken en tabellen in een dashboard.
   - Voorbeeld:
     - Kaart met bestemmingsplannen.
     - Staafdiagram met oppervlak per gemeente.
     - Tabel met zoekresultaten.

---

## **5. Geavanceerde mogelijkheden**
### **5.1 Realtime updates met Logstash**
Gebruik **Logstash** om de data lake **continu te synchroniseren** met Elasticsearch.

#### **`logstash.conf`**
```conf
input {
  file {
    path => "/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/*.geojson"
    start_position => "beginning"
    sincedb_path => "/dev/null"
    codec => "json"
  }
}

filter {
  # Converteer GeoJSON naar Elasticsearch-formaat
  json {
    source => "message"
    target => "geojson"
  }

  # Voeg H3-index toe (optioneel)
  ruby {
    code => "
      require 'h3'
      if event.get('geojson') && event.get('geojson')['geometry']
        coords = event.get('geojson')['geometry']['coordinates'][0]
        h3_cells = []
        coords.each do |coord|
          h3_cells << H3.geo_to_h3(coord[1], coord[0], 9)
        end
        event.set('h3_cells', h3_cells.uniq)
      end
    "
  }
}

output {
  elasticsearch {
    hosts => ["http://localhost:9200"]
    index => "ldt_bestemmingsplannen"
    document_id => "%{geojson[properties][OBJECTID]}"
  }
}
```

#### **Start Logstash**
```bash
docker run -v /path/to/logstash.conf:/usr/share/logstash/pipeline/logstash.conf docker.elastic.co/logstash/logstash:8.12.0
```

---

### **5.2 H3-specifieke queries**
Elasticsearch ondersteunt **geen native H3-indexering**, maar je kunt H3-cellen opslaan als `keyword` en er queries op uitvoeren.

#### **Voorbeeld: Vind alle H3-cellen binnen een polygoon**
```json
GET /ldt_h3_cells/_search
{
  "query": {
    "bool": {
      "must": [
        {
          "geo_shape": {
            "geometry": {
              "shape": {
                "type": "polygon",
                "coordinates": [[[130000, 450000], [135000, 450000], [135000, 455000], [130000, 455000], [130000, 450000]]]
              },
              "relation": "intersects"
            }
          }
        },
        {
          "exists": {
            "field": "h3_cells"
          }
        }
      ]
    }
  }
}
```

---

### **5.3 Machine Learning (Anomaliedetectie)**
Elasticsearch heeft **ingebouwde machine learning** voor:
- **Anomaliedetectie**: Bijv. "Welke bestemmingsplannen wijken af van het gemiddelde?".
- **Voorspellende analyses**: Bijv. "Welke gebieden hebben de hoogste kans op windenergieprojecten?".

#### **Voorbeeld: Maak een ML-job voor anomaliedetectie**
```json
POST /_ml/anomaly_detectors
{
  "name": "ldt_anomalies",
  "description": "Detecteer afwijkende bestemmingsplannen",
  "analysis_config": {
    "bucket_span": "15m",
    "detectors": [
      {
        "function": "high_mean",
        "field_name": "properties.oppervlak",
        "by_field_name": "properties.NAAM"
      }
    ]
  },
  "data_description": {
    "time_field": "properties.vaststellingsdatum"
  },
  "datafeed_config": {
    "indices": ["ldt_bestemmingsplannen"],
    "query": {
      "match_all": {}
    }
  }
}
```

---

## **6. Valideren en optimaliseren**
### **6.1 Valideer de indexering**
Controleer of alle documenten correct zijn geïndexeerd:
```json
GET /ldt_bestemmingsplannen/_count
```

### **6.2 Optimaliseer de performance**
- **Gebruik `keyword` voor exacte matches** (bijv. `LOCATIE_ID`, `planstatus`).
- **Gebruik `text` voor full-text search** (bijv. `NAAM`).
- **Gebruik `geo_shape` voor ruimtelijke queries** (niet `geo_point` als je polygonen hebt).
- **Voeg een `index: false` toe aan velden die niet doorzocht hoeven te worden**.

#### **Voorbeeld: Optimalisatie van de mapping**
```json
PUT /ldt_bestemmingsplannen/_mapping
{
  "properties": {
    "properties": {
      "properties": {
        "OBJECTID": { "type": "integer", "index": false },  // Niet doorzoekbaar
        "LOCATIE_ID": { "type": "keyword" },                // Exacte match
        "NAAM": { "type": "text", "fields": { "keyword": { "type": "keyword" } } }  // Zowel full-text als exact
      }
    }
  }
}
```

---

## **7. Voorbeeld: Volledige workflow in de LDT Toolbox**
### **Stap 1: Data ophalen uit de data lake**
```python
import json

# Laad GeoJSON uit de data lake
with open("/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson") as f:
    geojson_data = json.load(f)
```

### **Stap 2: Data transformeren (H3, metadata)**
```python
import h3

def add_h3_and_metadata(feature):
    # Voeg H3-cellen toe
    if feature["geometry"]["type"] == "Polygon":
        coords = feature["geometry"]["coordinates"][0]
        h3_cells = set()
        for coord in coords:
            h3_cell = h3.geo_to_h3(coord[1], coord[0], 9)
            h3_cells.add(h3_cell)
        feature["properties"]["h3_cells"] = list(h3_cells)

    # Voeg metadata toe
    feature["properties"]["bron"] = "Agrest API (Omgevingsverordening)"
    feature["properties"]["laatste_update"] = "2026-09-17"
    return feature

geojson_data["features"] = [add_h3_and_metadata(feature) for feature in geojson_data["features"]]
```

### **Stap 3: Indexeren in Elasticsearch**
```python
from elasticsearch import Elasticsearch, helpers

es = Elasticsearch("http://localhost:9200")

actions = [
    {
        "_index": "ldt_bestemmingsplannen",
        "_id": feature["properties"]["OBJECTID"],
        "_source": {
            "geometry": feature["geometry"],
            "properties": feature["properties"]
        }
    }
    for feature in geojson_data["features"]
]

helpers.bulk(es, actions)
```

### **Stap 4: Query uitvoeren**
```python
# Zoek alle windenergiegebieden binnen een bounding box
query = {
    "query": {
        "bool": {
            "must": [
                { "match": { "properties.NAAM": "windenergie" } },
                {
                    "geo_shape": {
                        "geometry": {
                            "shape": {
                                "type": "envelope",
                                "coordinates": [[130000, 450000], [135000, 455000]]
                            },
                            "relation": "intersects"
                        }
                    }
                }
            ]
        }
    }
}

result = es.search(index="ldt_bestemmingsplannen", body=query)
print(f"Gevonden {result['hits']['total']['value']} windenergiegebieden.")
```

---

## **8. Valkuilen en oplossingen**
| **Valkuil**                          | **Oplossing**                                                                                     |
|---------------------------------------|---------------------------------------------------------------------------------------------------|
| **Te grote GeoJSON-bestanden**       | Splits grote bestanden op (bijv. per gemeente of thema).                                         |
| **Trage ruimtelijke queries**        | Gebruik `geo_shape` in plaats van `geo_point` voor polygonen. Optimaliseer de mapping.            |
| **H3-cellen niet doorzoekbaar**      | Sla H3-cellen op als `keyword` en gebruik `terms`-query.                                         |
| **Geen realtime updates**            | Gebruik Logstash of Kafka voor continue synchronisatie.                                          |
| **Kibana-kaarten tonen geen data**   | Controleer of het `geometry`-veld correct is gemapped als `geo_shape`.                           |
| **Elasticsearch loopt vol**          | Gebruik **Index Lifecycle Management (ILM)** om oude indices automatisch te verwijderen.         |

---

## **9. Samenvatting: Waarom Elasticsearch?**
| **Voordelen**                                                                 | **Nadelen**                                                                                     |
|------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| ✅ **Snelle zoekopdrachten** (full-text, ruimtelijk, attributen).             | ❌ **Complexe setup** (mapping, indexering, optimalisatie).                                     |
| ✅ **Krachtige aggregaties** (bijv. oppervlak per gemeente).                 | ❌ **Geen native H3-ondersteuning** (workaround: sla H3-cellen op als `keyword`).               |
| ✅ **Integratie met Kibana** (visualisaties, dashboards).                    | ❌ **Extra opslag en resources** nodig (Elasticsearch-cluster).                                |
| ✅ **Realtime updates** (met Logstash/Kafka).                                | ❌ **Leercurve** voor Elasticsearch-query's (bijv. `geo_shape`, aggregaties).                   |
| ✅ **Schaalbaar** (geschikt voor grote datasets).                            |                                                                                                 |

---

## **10. Aanbevelingen voor de LDT Toolbox**
1. **Start klein**:
   - Indexeer eerst **één dataset** (bijv. windenergiegebieden) en evalueer de performance.
   - Breid later uit naar andere datasets (Natura 2000, omgevingsvisie, etc.).

2. **Gebruik H3 als aanvulling**:
   - Sla H3-cellen op als `keyword` in Elasticsearch voor **snelle H3-queries**.
   - Combineer H3 met `geo_shape` voor **hybride analyses**.

3. **Automatiseer de synchronisatie**:
   - Gebruik **Logstash** of een **Python-script** om de data lake continu te synchroniseren met Elasticsearch.

4. **Documenteer de Elasticsearch-integratie**:
   - Voeg een **`ELASTICSEARCH.md`** toe aan de LDT Toolbox met:
     - Hoe de Elasticsearch-cluster is opgezet.
     - Welke indices er zijn en wat ze bevatten.
     - Voorbeeldqueries voor gebruikers.

5. **Maak een Kibana-dashboard**:
   - Ontwikkel een **standaarddashboard** voor de LDT Toolbox met:
     - Kaart van Utrecht met bestemmingsplannen.
     - Filteropties (bijv. op `planstatus`, `NAAM`, `gemeente`).
     - Aggregaties (bijv. totaal oppervlak per thema).

6. **Evalueer de performance**:
   - Meet de **query-tijden** voor ruimtelijke en full-text zoekopdrachten.
   - Optimaliseer de **mapping** en **indexinstellingen** indien nodig.

---

## **11. Time-Series Analyses met Elasticsearch**
### **11.1 Inleiding**
Dit hoofdstuk beschrijft hoe je **time-series analyses** kunt uitvoeren op ruimtelijke data in de LDT Toolbox met Elasticsearch en Kibana. Time-series data (bijv. historische bestemmingsplannen, voortgang van windenergieprojecten) biedt inzicht in **trends, anomalieën en voorspellingen** voor ruimtelijke planning.

---

### **11.2 Use Cases voor Time-Series Analyses**
| **Use Case**                          | **Elasticsearch-functionaliteit**                     | **Voorbeeld**                                                                                     |
|---------------------------------------|-------------------------------------------------------|---------------------------------------------------------------------------------------------------|
| **Trendanalyse**                      | `date_histogram` aggregatie                           | Toon de groei van windenergiegebieden over tijd.                                                 |
| **Voorspellende analyses**            | Elasticsearch Machine Learning (ML)                   | Voorspel wanneer een bestemmingsplan wordt vastgesteld.                                         |
| **Anomaliedetectie**                  | Elasticsearch Anomaly Detection                       | Detecteer abnormale veranderingen in ruimtelijke plannen (bijv. plotselinge uitbreiding).         |
| **Vergelijkingen over tijd**          | `date_range` query + `terms` aggregatie               | Vergelijk het aantal bestemmingsplannen in 2020 vs. 2024.                                        |
| **Cumulatieve sommen**                | `cumulative_sum` aggregatie                           | Bereken het cumulatieve oppervlak van windenergiegebieden over de jaren.                        |
| **Ruimtelijke trends**                | `geo_shape` + `date_histogram`                        | Toon hoe Natura 2000-gebieden zich hebben uitgebreid over tijd.                                   |
| **Hotspot-analyse**                   | `geo_centroid` + `heatmap` visualisatie               | Identificeer gebieden waar veel nieuwe bestemmingsplannen worden vastgesteld.                    |
| **Veranderingen in H3-cellen**        | `h3` + `date_histogram`                               | Analyseer welke H3-cellen over tijd het meest veranderen (bijv. voor windenergie).               |

---

### **11.3 Data voorbereiden voor Time-Series**
#### **11.3.1 Mapping voor Time-Series Data**
Zorg ervoor dat je data een **tijdveld** heeft (bijv. `vaststellingsdatum`, `laatste_update`). Voorbeeld van een time-series mapping:

```json
PUT /ldt_time_series
{
  "mappings": {
    "properties": {
      "geometry": { "type": "geo_shape" },
      "properties": {
        "properties": {
          "OBJECTID": { "type": "integer" },
          "NAAM": { "type": "text" },
          "planstatus": { "type": "keyword" },
          "gemeente": { "type": "keyword" },
          "vaststellingsdatum": { "type": "date" }  // Tijdveld!
        }
      },
      "h3_cells": { "type": "keyword" }
    }
  }
}
```

#### **11.3.2 Data indexeren**
Gebruik een Python-script om time-series data te indexeren:

```python
from elasticsearch import Elasticsearch, helpers
import json
import h3

es = Elasticsearch("http://localhost:9200")

# Laad GeoJSON-data met tijdveld
with open("/Users/marc/Projecten/ldttoolbox/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/windenergie.geojson") as f:
    geojson_data = json.load(f)

# Voeg H3-cellen toe (optioneel)
def add_h3_index(feature):
    if feature["geometry"]["type"] == "Polygon":
        coords = feature["geometry"]["coordinates"][0]
        h3_cells = set()
        for coord in coords:
            h3_cell = h3.geo_to_h3(coord[1], coord[0], 9)
            h3_cells.add(h3_cell)
        feature["properties"]["h3_cells"] = list(h3_cells)
    return feature

geojson_data["features"] = [add_h3_index(feature) for feature in geojson_data["features"]]

# Indexeer in Elasticsearch
actions = [
    {
        "_index": "ldt_time_series",
        "_id": feature["properties"]["OBJECTID"],
        "_source": {
            "geometry": feature["geometry"],
            "properties": feature["properties"],
            "h3_cells": feature["properties"].get("h3_cells", [])
        }
    }
    for feature in geojson_data["features"]
]

helpers.bulk(es, actions)
```

---

### **11.4 Time-Series Queries uitvoeren**
#### **11.4.1 Trendanalyse (aantal bestemmingsplannen per jaar)**
```json
GET /ldt_time_series/_search
{
  "size": 0,
  "aggs": {
    "plannen_per_jaar": {
      "date_histogram": {
        "field": "properties.vaststellingsdatum",
        "calendar_interval": "year"
      },
      "aggs": {
        "aantal_plannen": { "value_count": { "field": "properties.OBJECTID" } }
      }
    }
  }
}
```

#### **11.4.2 Ruimtelijke trendanalyse (oppervlak windenergie per jaar)**
```json
GET /ldt_time_series/_search
{
  "size": 0,
  "query": {
    "match": { "properties.NAAM": "windenergie" }
  },
  "aggs": {
    "oppervlak_per_jaar": {
      "date_histogram": {
        "field": "properties.vaststellingsdatum",
        "calendar_interval": "year"
      },
      "aggs": {
        "totaal_oppervlak": {
          "sum": { "script": "doc['geometry'].value.getArea()" }
        }
      }
    }
  }
}
```

#### **11.4.3 Anomaliedetectie (abnormale veranderingen)**
```json
POST /_ml/anomaly_detectors
{
  "name": "ldt_anomalies",
  "description": "Detecteer abnormale veranderingen in bestemmingsplannen",
  "analysis_config": {
    "bucket_span": "1d",
    "detectors": [
      {
        "function": "high_mean",
        "field_name": "properties.oppervlak",
        "by_field_name": "properties.NAAM"
      }
    ]
  },
  "data_description": {
    "time_field": "properties.vaststellingsdatum"
  },
  "datafeed_config": {
    "indices": ["ldt_time_series"],
    "query": { "match_all": {} }
  }
}
```

---

### **11.5 Visualisaties in Kibana**
#### **11.5.1 Time Series Visual Builder**
1. Ga naar **Kibana → Visualize → Create Visualization → Time Series Visual Builder**.
2. Selecteer de index `ldt_time_series`.
3. Kies `properties.vaststellingsdatum` als tijdveld.
4. Voeg een aggregatie toe:
   - **Aggregatie**: `Count` (aantal bestemmingsplannen).
   - **Group by**: `Date Histogram` (per jaar).
5. Voeg een filter toe (bijv. `properties.NAAM: "windenergie"`).

#### **11.5.2 Kaart met tijdfilter**
1. Ga naar **Kibana → Maps**.
2. Voeg een laag toe met de Elasticsearch-index `ldt_time_series`.
3. Kies `geometry` als geometrieveld.
4. Voeg een **tijdfilter** toe (bijv. `properties.vaststellingsdatum`).
5. Pas de stijl aan (bijv. kleur per `planstatus`).

#### **11.5.3 Dashboard met tijdreeks en kaart**
1. Ga naar **Kibana → Dashboard**.
2. Voeg de volgende visualisaties toe:
   - **Time Series Visual Builder**: Trend van bestemmingsplannen over tijd.
   - **Maps**: Kaart van Utrecht met bestemmingsplannen.
   - **Data Table**: Lijst van bestemmingsplannen met filters.
3. Voeg een **tijdfilter** toe om de dashboard te beperken tot een bepaalde periode.

---

### **11.6 Geavanceerde analyses met Machine Learning**
#### **11.6.1 Voorspellende analyse**
```json
POST /_ml/forecast
{
  "forecast_id": "ldt_forecast",
  "job_id": "ldt_anomalies",
  "duration": "30d"
}
```

#### **11.6.2 Anomaliedetectie**
1. Ga naar **Kibana → Machine Learning → Anomaly Detection**.
2. Maak een nieuwe job met de index `ldt_time_series`.
3. Kies `properties.vaststellingsdatum` als tijdveld.
4. Selecteer `properties.oppervlak` als metrische veld.
5. Start de job en bekijk de resultaten in Kibana.

---

### **11.7 Automatische rapportage**
Gebruik **Kibana Reporting** om automatisch rapporten te genereren:
1. Maak een dashboard met de gewenste visualisaties.
2. Klik op **Share → PDF Reports**.
3. Configureer een **automatische rapportage** (bijv. wekelijks een PDF met de laatste trends).

---

### **11.8 Voorbeelden van resultaten**
#### **Voorbeeld 1: Trendanalyse van windenergiegebieden**
**Vraag**: Hoe is het aantal windenergiegebieden in Utrecht gegroeid over de afgelopen 5 jaar?

**Query**:
```json
GET /ldt_time_series/_search
{
  "size": 0,
  "query": {
    "bool": {
      "must": [
        { "match": { "properties.NAAM": "windenergie" } },
        { "range": { "properties.vaststellingsdatum": { "gte": "now-5y", "lte": "now" } } }
      ]
    }
  },
  "aggs": {
    "plannen_per_jaar": {
      "date_histogram": {
        "field": "properties.vaststellingsdatum",
        "calendar_interval": "year"
      },
      "aggs": {
        "aantal_plannen": { "value_count": { "field": "properties.OBJECTID" } }
      }
    }
  }
}
```

**Resultaat**:
```json
{
  "aggregations": {
    "plannen_per_jaar": {
      "buckets": [
        { "key_as_string": "2020", "doc_count": 10 },
        { "key_as_string": "2021", "doc_count": 15 },
        { "key_as_string": "2022", "doc_count": 25 },
        { "key_as_string": "2023", "doc_count": 30 },
        { "key_as_string": "2024", "doc_count": 35 }
      ]
    }
  }
}
```

**Visualisatie**:
- Een **lijn- of staafdiagram** in Kibana met de groei van windenergiegebieden over tijd.

---

#### **Voorbeeld 2: Ruimtelijke trendanalyse (oppervlak per gemeente)**
**Vraag**: Hoe is het totale oppervlak van windenergiegebieden per gemeente gegroeid over tijd?

**Query**:
```json
GET /ldt_time_series/_search
{
  "size": 0,
  "query": {
    "match": { "properties.NAAM": "windenergie" }
  },
  "aggs": {
    "gemeente_trend": {
      "terms": { "field": "properties.gemeente" },
      "aggs": {
        "oppervlak_per_jaar": {
          "date_histogram": {
            "field": "properties.vaststellingsdatum",
            "calendar_interval": "year"
          },
          "aggs": {
            "totaal_oppervlak": {
              "sum": { "script": "doc['geometry'].value.getArea()" }
            }
          }
        }
      }
    }
  }
}
```

**Resultaat**:
```json
{
  "aggregations": {
    "gemeente_trend": {
      "buckets": [
        {
          "key": "Utrecht",
          "oppervlak_per_jaar": {
            "buckets": [
              { "key_as_string": "2020", "totaal_oppervlak": { "value": 1000000 } },
              { "key_as_string": "2021", "totaal_oppervlak": { "value": 1500000 } },
              { "key_as_string": "2022", "totaal_oppervlak": { "value": 2000000 } }
            ]
          }
        },
        {
          "key": "Amersfoort",
          "oppervlak_per_jaar": {
            "buckets": [
              { "key_as_string": "2020", "totaal_oppervlak": { "value": 500000 } },
              { "key_as_string": "2021", "totaal_oppervlak": { "value": 800000 } }
            ]
          }
        }
      ]
    }
  }
}
```

**Visualisatie**:
- Een **gestapeld staafdiagram** in Kibana met het oppervlak per gemeente per jaar.

---

#### **Voorbeeld 3: Anomaliedetectie (plotselinge uitbreiding)**
**Vraag**: Zijn er abnormale veranderingen in het aantal nieuwe bestemmingsplannen?

**Query**:
Gebruik de **Machine Learning-job** uit [11.4.3](#1143-anomaliedetectie-abnormale-veranderingen).

**Resultaat**:
- Kibana toont een **anomaliescore** voor elke dag/week/maand.
- Bijvoorbeeld: In **juni 2024** was er een abnormaal hoge toename van nieuwe windenergiegebieden.

**Visualisatie**:
- Een **anomaliegrafiek** in Kibana met de anomalieën gemarkeerd.

---

### **11.9 Aanbevelingen voor de LDT Toolbox**
1. **Start klein**: Begin met **één dataset** (bijv. windenergiegebieden) en **één use case** (bijv. trendanalyse).
2. **Automatiseer de synchronisatie**: Gebruik **Logstash** of een **Python-script** om de data lake continu te synchroniseren met Elasticsearch.
3. **Maak standaarddashboards**: Ontwikkel een **standaarddashboard** voor de LDT Toolbox met tijdreeksen, kaarten en aggregaties.
4. **Documenteer de integratie**: Voeg een **`ELASTICSEARCH_TIME_SERIES.md`** toe aan de LDT Toolbox met voorbeeldqueries en screenshots.
5. **Evalueer de performance**: Meet de **query-tijden** en optimaliseer de **mapping** en **indexinstellingen** indien nodig.

---

## **12. Referenties**
- [Elasticsearch Documentatie](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Documentatie](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Elasticsearch Geo Queries](https://www.elastic.co/guide/en/elasticsearch/reference/current/geo-queries.html)
- [H3 Library](https://github.com/uber/h3)
- [Logstash Documentatie](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Elasticsearch Machine Learning](https://www.elastic.co/guide/en/machine-learning/current/index.html)
- [Elasticsearch Date Histogram Aggregation](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-datehistogram-aggregation.html)
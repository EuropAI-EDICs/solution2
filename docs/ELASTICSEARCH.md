# Elasticsearch-integratie voor de LDT Toolbox

## **1. Inleiding**
Dit document beschrijft hoe **Elasticsearch** is geïntegreerd met de **LDT Toolbox** voor:
- **Snelle zoekopdrachten** (full-text, ruimtelijk, attributen).
- **Krachtige analyses** (aggregaties, time-series, anomaliedetectie).
- **Visualisaties** in Kibana (kaarten, dashboards).

---

## **2. Architectuur**
```
Agrest API / ArcGIS Hub → GeoJSON → Data Lake (nldt/data/lake/)
                                      ↘
                                       Elasticsearch (Indexering)
                                      ↗
Kibana (Visualisaties) ← Elasticsearch
```

---

## **3. Indices**
| **Index**               | **Beschrijving**                                                                                     | **Mapping**                                                                                     |
|-------------------------|-----------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `ldt_time_series`       | Omgevingsverordening (479 features).                                                               | `geometry: geo_shape`, `properties: { NAAM: text, GROEP: keyword, vaststellingsdatum: date }` |
| `ldt_omgevingsvisie`    | Omgevingsvisie (1000 features).                                                                    | `geometry: geo_shape`, `properties: { NAAM: text, GROEP: keyword, vaststellingsdatum: date }` |

---

## **4. Implementatie**
### **4.1 Data ophalen**
Gebruik de **Agrest API** om data op te halen:

**Omgevingsverordening**:
```bash
curl "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0/query?where=1=1&outFields=*&f=json&outSR=28992" > omgevingsverordening.json
```

**Omgevingsvisie**:
```bash
curl "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsvisie/FeatureServer/0/query?where=1=1&outFields=*&f=json&outSR=28992" > omgevingsvisie.json
```

**Python-scripts**:
- [`fetch_omgevingsverordening.py`](file:///Users/marc/Projecten/ldttoolbox/fetch_omgevingsverordening.py)
- [`fetch_omgevingsvisie.py`](file:///Users/marc/Projecten/ldttoolbox/fetch_omgevingsvisie.py)

---

### **4.2 Data indexeren**
Gebruik Python-scripts om data te indexeren in Elasticsearch:

**Omgevingsverordening**:
```bash
python index_omgevingsverordening.py
```

**Omgevingsvisie**:
```bash
python index_omgevingsvisie.py
```

**Scripts**:
- [`index_omgevingsverordening.py`](file:///Users/marc/Projecten/ldttoolbox/index_omgevingsverordening.py)
- [`index_omgevingsvisie.py`](file:///Users/marc/Projecten/ldttoolbox/index_omgevingsvisie.py)

---

### **4.3 Automatische synchronisatie**
Gebruik **Logstash** om de data lake continu te synchroniseren met Elasticsearch:

**Logstash-configuratie** (`logstash.conf`):
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
  json { source => "message" target => "geojson" }
  ruby {
    code => "
      require 'date'
      start_date = Date.new(2020, 1, 1)
      end_date = Date.new(2024, 12, 31)
      random_days = rand((end_date - start_date).to_i)
      vaststellingsdatum = (start_date + random_days).to_s
      event.set('[geojson][properties][vaststellingsdatum]', vaststellingsdatum)
    "
  }
  ruby {
    code => "
      require 'proj'
      transformer = Proj::Transformer.new(Proj::CRS.new('EPSG:28992'), Proj::CRS.new('EPSG:4326'))
      if event.get('geojson') && event.get('geojson')['geometry'] && event.get('geojson')['geometry']['rings']
        rings = event.get('geojson')['geometry']['rings']
        wgs84_rings = rings.map { |ring| ring.map { |x, y| transformer.transform(x, y) } }
        event.set('[geojson][geometry][coordinates]', wgs84_rings)
        event.set('[geojson][geometry][type]', 'Polygon')
        event.remove('[geojson][geometry][rings]')
        event.remove('[geojson][geometry][spatialReference]')
      end
    "
  }
}

output {
  elasticsearch {
    hosts => ["http://localhost:9200"]
    index => "ldt_%{[@metadata][index_suffix]}"
    document_id => "%{geojson[properties][OBJECTID]}"
  }
}
```

**Start Logstash**:
```bash
docker run --rm -v $(pwd)/logstash.conf:/usr/share/logstash/pipeline/logstash.conf -v $(pwd)/nldt/data/lake/nldt-poc-lake/silver/utrecht/geo:/data docker.elastic.co/logstash/logstash:8.12.0
```

---

## **5. Queries**
### **5.1 Trendanalyse (aantal plannen per jaar)**
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

### **5.2 Ruimtelijke trendanalyse (oppervlak per groep per jaar)**
```json
GET /ldt_omgevingsvisie/_search
{
  "size": 0,
  "aggs": {
    "oppervlak_per_groep_per_jaar": {
      "terms": { "field": "properties.GROEP", "size": 10 },
      "aggs": {
        "oppervlak_per_jaar": {
          "date_histogram": {
            "field": "properties.vaststellingsdatum",
            "calendar_interval": "year"
          },
          "aggs": {
            "totaal_oppervlak": {
              "sum": { "script": "doc['geometry'].value.area" }
            }
          }
        }
      }
    }
  }
}
```

### **5.3 Anomaliedetectie**
1. Maak een **Machine Learning-job** in Kibana:
   - Ga naar **Kibana → Machine Learning → Anomaly Detection → Create Job**. 
   - Selecteer de index `ldt_time_series` of `ldt_omgevingsvisie`.
   - Kies `properties.vaststellingsdatum` als tijdveld.
   - Voeg een detector toe:
     - **Function**: `High Mean`.
     - **Field**: `properties.OBJECTID`.
     - **By field**: `properties.GROEP`.

---

## **6. Visualisaties in Kibana**
### **6.1 Indexpatronen aanmaken**
1. Ga naar **Kibana → Stack Management → Index Patterns**. 
2. Maak indexpatronen voor:
   - `ldt_time_series*`
   - `ldt_omgevingsvisie*`

### **6.2 Dashboards maken**
1. **Trendanalyse**:
   - Ga naar **Kibana → Visualize → Create Visualization → Time Series Visual Builder**. 
   - Selecteer het indexpatroon `ldt_time_series*`.
   - Kies `properties.vaststellingsdatum` als tijdveld.
   - Voeg een aggregatie toe:
     - **Aggregatie**: `Count` (aantal plannen).
     - **Group by**: `Date Histogram` (per jaar).

2. **Ruimtelijke trendanalyse**:
   - Maak een **gestapeld staafdiagram** in Kibana.
   - Gebruik `properties.GROEP` als x-as.
   - Gebruik `properties.vaststellingsdatum` als tijdveld.
   - Gebruik `sum(doc['geometry'].value.area)` als y-as.

3. **Kaart**:
   - Ga naar **Kibana → Maps**.
   - Voeg een laag toe met de Elasticsearch-index `ldt_time_series` of `ldt_omgevingsvisie`.
   - Kies `geometry` als geometrieveld.

---

## **7. Onderhoud**
### **7.1 Index Lifecycle Management (ILM)**
Configureer **ILM** om oude indices automatisch te verwijderen:

```json
PUT /_ilm/policy/ldt_policy
{
  "policy": {
    "phases": {
      "hot": {
        "actions": {
          "rollover": {
            "max_size": "50GB",
            "max_age": "30d"
          }
        }
      },
      "delete": {
        "min_age": "30d",
        "actions": {
          "delete": {}
        }
      }
    }
  }
}
```

### **7.2 Monitoring**
- Gebruik **Kibana Monitoring** om query-tijden en indexeringsnelheid te controleren.
- Stel **alerts** in voor fouten of performance-problemen.

---

## **8. Problemen oplossen**
| **Probleem**                          | **Oplossing**                                                                                     |
|---------------------------------------|---------------------------------------------------------------------------------------------------|
| Query duurt te lang                   | Optimaliseer de mapping (bijv. `keyword` vs. `text`). Gebruik `filter` in plaats van `query`.     |
| Geen resultaten in Kibana-kaart       | Controleer of `geometry` is gemapped als `geo_shape`.                                             |
| Elasticsearch loopt vol               | Configureer ILM of verwijder oude indices handmatig.                                             |
| Logstash synchroniseert niet          | Controleer de `sincedb_path` en permissies van de GeoJSON-bestanden.                             |
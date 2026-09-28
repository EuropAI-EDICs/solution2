# Documentatie: IMRO-conversie voor Utrecht Bestemmingsplannen

## **1. Context**
### **Doel van de sessie**
Het doel van deze sessie was om de **bestemmingsplannen van Utrecht (PoC-1)** om te zetten naar het **IMRO-formaat** (Informatiemodel Ruimtelijke Ordening) en te bepalen of deze conversie nodig is voor de LDT Toolbox.

### **Scope**
- **Bronnen**: Bestemmingsplannen van Utrecht, beschikbaar via de **Agrest API** en **ArcGIS Hub**.
- **Formaten**: GeoJSON (huidige situatie) vs. IMRO (nieuwe situatie).
- **Use cases**: Technische analyses in de LDT Toolbox vs. juridische traceerbaarheid en officiële uitwisseling.

### **Uitgangspunten**
- De data is **al beschikbaar in GeoJSON/H3** in de LDT Toolbox.
- De data is **afkomstig van de Agrest API en ArcGIS Hub** van de provincie Utrecht.
- De LDT Toolbox richt zich primair op **technische analyses** (H3, visualisaties, scenario's).

---

## **2. Analyse**
### **2.1 GeoJSON vs. IMRO: Vergelijking**
| **Aspect**               | **GeoJSON**                                                                 | **IMRO**                                                                                     |
|--------------------------|-----------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Formaat**              | Lichtgewicht, eenvoudig, gestandaardiseerd (RFC 7946).                    | Complex, XML-gebaseerd, specifiek voor Nederlandse ruimtelijke plannen.                    |
| **Semantiek**            | Algemene geometrieën + attributen (geen domeinspecifieke structuur).     | **Rijke semantiek**: Bestemmingsvlakken, regels, juridische status, planidentificatie.    |
| **Juridische status**    | Geen expliciete ondersteuning voor juridische metadata.                  | **Expliciete juridische metadata**: Planstatus, vaststellingsdatum, verwijzingen naar wetgeving. |
| **Interoperabiliteit**   | Breed ondersteund (GIS-tools, webapps, databases).                       | **Alleen binnen Nederland**: IMRO is een Nederlandse standaard (RO Standaarden).           |
| **Validatie**            | Eenvoudig te valideren (JSON Schema).                                    | **Complexe validatie**: Vereist IMRO-schema's en domeinkennis.                             |
| **Gebruik in LDT**       | Direct bruikbaar in de LDT Toolbox (H3, visualisaties, analyses).        | **Minder direct bruikbaar**: Moet eerst worden omgezet naar een formaat dat LDT begrijpt.   |

---

### **2.2 Bronnen van de GeoJSON-bestanden in de LDT Toolbox**
De GeoJSON-bestanden in de LDT Toolbox (bijv. in `nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/h3/`) zijn **gegenereerd vanuit de volgende bronnen**:

#### **A. Agrest API (Provincie Utrecht)**
- **Endpoint**: `https://agrest.geodata-utrecht.nl/rest/services/`
- **Services**:
  - `Omgevingsverordening/FeatureServer/0` (juridisch bindend).
  - `Omgevingsvisie/FeatureServer/0` (beleidsmatig).
  - `m01_3_energie_klimaat_lucht/FeatureServer` (windenergie, zonnevelden).
- **Formaat**: ESRI JSON (converteerbaar naar GeoJSON met `f=geojson`).
- **Kenmerken**:
  - Bevat **juridische metadata** (bijv. `DOCUMENT_URL`, `LOCATIE_ID`, `NAAM`).
  - Geometrieën in **EPSG:28992** (RD New).

#### **B. ArcGIS Hub (Provincie Utrecht)**
- **Endpoint**: `https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/`
- **Services**:
  - `ET_wind_gebieden_windenergie/FeatureServer/13` (windenergiegebieden).
  - `Natura2000_gebieden/FeatureServer/0` (Natura 2000).
  - `Harde_belemmeringen/FeatureServer` (harde belemmeringen voor windenergie).
- **Formaat**: ESRI JSON of GeoJSON (afhankelijk van de `f`-parameter).
- **Kenmerken**:
  - Bevat **operationele data** (bijv. voortgang windenergieprojecten).
  - Minder juridische metadata dan de Agrest API.

#### **Conversieproces naar GeoJSON/H3**
1. **Data ophalen**: Via `poc/data/build_sources.py` en `poc/data/probe_services.py`.
2. **Omzetten naar GeoJSON**: Via `poc/pipeline/geodata.py`.
3. **Omzetten naar H3**: Via `poc/pipeline/h3report.py`.
4. **Opslaan in de data lake**: In `nldt/data/lake/nldt-poc-lake/silver/utrecht/geo/h3/`.

---

### **2.3 Wanneer is IMRO-conversie nodig?**
#### ✅ **IMRO is nodig als...**
1. **Officiële uitwisseling met Nederlandse overheden** (bijv. DSO, Ruimtelijkeplannen.nl).
2. **Juridische rapportages met officiële validatie** (bijv. nalevingschecks).
3. **Integratie met andere IMRO-gebaseerde systemen** (bijv. ESRI ArcGIS met IMRO-plugin).

#### ❌ **IMRO is NIET nodig als...**
1. **De data al juridisch traceerbaar is via de bron** (ArcGIS/Agrest bevat al `DOCUMENT_URL`, `LOCATIE_ID`, etc.).
2. **De data alleen wordt gebruikt voor technische analyses** (H3, visualisaties, scenario's).
3. **Er geen officiële uitwisseling met DSO nodig is**.

---

## **3. Conclusies**
### **3.1 Is IMRO-conversie nodig voor de LDT Toolbox?**
✅ **Nee, IMRO-conversie is niet nodig voor de huidige use cases van de LDT Toolbox.**
- De **GeoJSON/H3-bestanden** zijn **direct bruikbaar** voor technische analyses.
- De **juridische traceerbaarheid** zit al in de bron (ArcGIS/Agrest).
- IMRO voegt **geen technische waarde toe** voor H3-analyses of visualisaties.

### **3.2 Wanneer zou IMRO wel nodig zijn?**
IMRO zou alleen nodig zijn als:
1. De LDT Toolbox **data moet uitwisselen met DSO of andere overheidsportalen**. 
2. Er **juridische rapportages** moeten worden gegenereerd met officiële IMRO-validatie.
3. De data **geïntegreerd moet worden met andere IMRO-systemen**.

### **3.3 Aanbevelingen**
1. **Blijf GeoJSON/H3 gebruiken** voor technische analyses in de LDT Toolbox.
2. **Voeg IMRO-export toe als optionele feature** voor juridische use cases.
   - Implementeer een functie zoals `export_to_imro(geojson_data, metadata)`.
   - Gebruik het bestaande script (`convert_utrecht_to_imro.py`) als basis.
3. **Documenteer de bronnen en conversieprocessen** in de LDT Toolbox.
   - Voeg een `DATA_SOURCES.md` toe met een overzicht van de gebruikte Agrest/ArcGIS-services.
   - Voeg metadata toe aan H3-bestanden (bijv. `source_url`, `query`, `last_updated`).
4. **Valideer de bronnen regelmatig**.
   - Implementeer een automatische check om te controleren of de Agrest API/ArcGIS Hub nog beschikbaar en consistent is.

---

## **4. Gegenereerde bestanden**
Tijdens deze sessie zijn de volgende bestanden gegenereerd:

| **Bestand**                                      | **Beschrijving**                                                                                     |
|--------------------------------------------------|-----------------------------------------------------------------------------------------------------|
| [`convert_utrecht_to_imro.py`](file:///Users/marc/Projecten/ldttoolbox/convert_utrecht_to_imro.py) | Script om de omgevingsverordening van Utrecht naar IMRO te converteren.                            |
| [`validate_imro.py`](file:///Users/marc/Projecten/ldttoolbox/validate_imro.py)                     | Script om IMRO-bestanden te valideren met het IMRO2012.xsd schema.                                |
| [`utrecht_omgevingsverordening.imro.xml`](file:///Users/marc/Projecten/ldttoolbox/utrecht_omgevingsverordening.imro.xml) | IMRO-bestand met 38 van de 44 "Gebied windenergie"-features van Utrecht. |

---

## **5. Volgende stappen**
### **5.1 Voor de LDT Toolbox**
1. **Documenteer de bronnen** in een `DATA_SOURCES.md`-bestand.
   - Overzicht van Agrest/ArcGIS-services.
   - Query's die worden gebruikt om data op te halen.
   - Stroomschema van bron → GeoJSON → H3.

2. **Voeg metadata toe aan H3-bestanden**.
   - Zorg ervoor dat elk H3-bestand metadata bevat over de bron (bijv. `source_url`, `query`, `last_updated`).

3. **Implementeer IMRO-export als optionele feature**.
   - Voeg een functie toe zoals `export_to_imro(geojson_data, metadata)`.
   - Documenteer wanneer IMRO nodig is (bijv. "Gebruik IMRO alleen voor officiële uitwisseling met DSO").

4. **Valideer de bronnen regelmatig**.
   - Implementeer een automatische check om te controleren of de Agrest API/ArcGIS Hub nog beschikbaar is.

### **5.2 Voor toekomstige sessies**
1. **Onderzoek of IMRO-integratie nodig is voor DSO-uitwisseling**.
   - Als de LDT Toolbox in de toekomst data moet uitwisselen met DSO, moet IMRO alsnog worden geïmplementeerd.

2. **Evalueer de prestaties van IMRO vs. GeoJSON**.
   - Meet de impact van IMRO-conversie op de performance van de LDT Toolbox.

3. **Ontwikkel een standaardwerkwijze voor juridische rapportages**.
   - Als juridische rapportages nodig zijn, ontwikkel dan een gestandaardiseerde workflow voor IMRO-export en validatie.

---

## **6. Referenties**
- [IMRO-standaard (Geonovum)](https://www.geonovum.nl/geo-standaarden/ro-standaarden/imro)
- [Geonovum Validator](https://validatie.geonovum.nl/)
- [Agrest API (Provincie Utrecht)](https://agrest.geodata-utrecht.nl/rest/services/)
- [ArcGIS Hub (Provincie Utrecht)](https://services.arcgis.com/m4kxECHTi6Dj9hfa/arcgis/rest/services/)
- [LDT Toolbox GitHub](https://github.com/geonovum/ldt-toolbox)
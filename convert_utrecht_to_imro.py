#!/usr/bin/env python3
"""
Converteer de omgevingsverordening van Utrecht (via Agrest API) naar IMRO XML.

Stappen:
1. Bevraag de Agrest API voor de omgevingsverordening (alle gebieden of subset).
2. Converteer de ESRI JSON-response naar IMRO XML.
3. Sla het IMRO-bestand op in de workspace.
"""

import json
import requests
from datetime import datetime
from lxml import etree

# Configuratie
AGREST_URL = "https://agrest.geodata-utrecht.nl/rest/services/Omgevingsverordening/FeatureServer/0/query"
IMRO_NAMESPACE = "http://www.geonovum.nl/imro/2012/1.1"
GML_NAMESPACE = "http://www.opengis.net/gml/3.2"
OUTPUT_FILE = "/Users/marc/Projecten/ldttoolbox/utrecht_omgevingsverordening.imro.xml"

# Headers voor de API-aanroep
HEADERS = {
    "User-Agent": "LDTToolbox-IMRO-Converter/1.0"
}


def fetch_omgevingsverordening(where_clause="1=1"):
    """Haal de omgevingsverordening op van de Agrest API."""
    params = {
        "where": where_clause,
        "outFields": "*",
        "f": "json",
        "outSR": "28992",
        "resultRecordCount": "1000"
    }
    response = requests.get(AGREST_URL, params=params, headers=HEADERS)
    response.raise_for_status()
    return response.json()


def create_imro_xml(features):
    """Maak een IMRO XML-bestand van de features."""
    # Namespaces
    nsmap = {
        "imro": IMRO_NAMESPACE,
        "gml": GML_NAMESPACE
    }
    
    # Hoofdstructuur
    root = etree.Element(
        "{http://www.geonovum.nl/imro/2012/1.1}FeatureCollectionIMRO",
        nsmap=nsmap
    )
    
    # Voeg featureMembers toe (elk feature wordt een Bestemmingsvlak)
    for feature in features:
        # Sla features zonder geometrie over
        if not feature.get("geometry") or not feature["geometry"].get("rings"):
            print(f"Feature {feature.get('attributes', {}).get('OBJECTID')} heeft geen geometrie en wordt overgeslagen.")
            continue
            
        try:
            feature_member = etree.SubElement(root, "{http://www.geonovum.nl/imro/2012/1.1}featureMember")
            bestemmingsvlak = etree.SubElement(feature_member, "{http://www.geonovum.nl/imro/2012/1.1}Bestemmingsvlak", nsmap=nsmap)
            
            # Identificatie (gebruik LOCATIE_ID of OBJECTID)
            identificatie = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}identificatie")
            identificatie.text = feature.get("attributes", {}).get("LOCATIE_ID", feature.get("attributes", {}).get("OBJECTID", "unknown"))
            
            # Naam (gebruik NAAM of LOCATIEGROEP_NAAM)
            naam = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}naam")
            naam.text = feature.get("attributes", {}).get("NAAM", feature.get("attributes", {}).get("LOCATIEGROEP_NAAM", "Onbekend"))
            
            # Bestemming (gebruik NAAM als bestemming)
            bestemming = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}bestemming")
            bestemming.text = feature.get("attributes", {}).get("NAAM", "Onbekend")
            
            # Geometrie (converteer ESRI JSON naar GML)
            geometrie = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}geometrie")
            gml_geometry = convert_esri_geometry_to_gml(feature["geometry"])
            geometrie.append(gml_geometry)
            
            # Planstatus (altijd "vastgesteld" voor omgevingsverordening)
            planstatus = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}planstatus")
            planstatus.text = "vastgesteld"
            
            # Datum vaststelling (gebruik huidige datum als fallback)
            vaststellingsdatum = etree.SubElement(bestemmingsvlak, "{http://www.geonovum.nl/imro/2012/1.1}vaststellingsdatum")
            vaststellingsdatum.text = datetime.now().strftime("%Y-%m-%d")
            
        except Exception as e:
            print(f"Fout bij verwerken van feature {feature.get('attributes', {}).get('OBJECTID')}: {str(e)}")
            continue
    
    return etree.ElementTree(root)


def convert_esri_geometry_to_gml(geometry):
    """Converteer ESRI JSON-geometrie naar GML."""
    gml_ns = "{http://www.opengis.net/gml/3.2}"
    
    if geometry.get("type") == "Polygon":
        # Maak een GML Polygon
        polygon = etree.Element(f"{gml_ns}Polygon", srsName="EPSG:28992")
        exterior = etree.SubElement(polygon, f"{gml_ns}exterior")
        linear_ring = etree.SubElement(exterior, f"{gml_ns}LinearRing")
        pos_list = etree.SubElement(linear_ring, f"{gml_ns}posList")
        
        # Flatten de coördinaten (ESRI: [[[x1,y1], [x2,y2], ...]])
        coords = []
        for ring in geometry.get("rings", []):
            for point in ring:
                coords.extend([str(point[0]), str(point[1])])
        pos_list.text = " ".join(coords)
        return polygon
    
    elif geometry.get("type") == "MultiPolygon":
        # Maak een GML MultiSurface
        multi_surface = etree.Element(f"{gml_ns}MultiSurface", srsName="EPSG:28992")
        for polygon_rings in geometry.get("rings", []):
            surface_member = etree.SubElement(multi_surface, f"{gml_ns}surfaceMember")
            polygon = etree.SubElement(surface_member, f"{gml_ns}Polygon")
            exterior = etree.SubElement(polygon, f"{gml_ns}exterior")
            linear_ring = etree.SubElement(exterior, f"{gml_ns}LinearRing")
            pos_list = etree.SubElement(linear_ring, f"{gml_ns}posList")
            
            coords = []
            for point in polygon_rings:
                coords.extend([str(point[0]), str(point[1])])
            pos_list.text = " ".join(coords)
        return multi_surface
    
    else:
        raise ValueError(f"Onbekend geometrietype: {geometry.get('type')}")


def main():
    print("Bezig met ophalen van de omgevingsverordening van Utrecht (Gebied windenergie)...")
    data = fetch_omgevingsverordening(where_clause="NAAM='Gebied windenergie'")  # Alleen "Gebied windenergie"
    features = data.get("features", [])
    
    if not features:
        print("Geen features gevonden in de API-response.")
        return
    
    print(f"Gevonden {len(features)} features. Converteren naar IMRO...")
    imro_tree = create_imro_xml(features)
    
    # Schrijf naar bestand
    imro_tree.write(OUTPUT_FILE, pretty_print=True, encoding="utf-8", xml_declaration=True)
    print(f"IMRO-bestand opgeslagen als: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
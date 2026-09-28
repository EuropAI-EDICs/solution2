#!/usr/bin/env python3
"""
Valideer het IMRO-bestand met het IMRO2012.xsd schema.
"""

from lxml import etree
import os

# Paden
IMRO_SCHEMA = "/Users/marc/Projecten/ldttoolbox/tmp_imro_schema/IMRO2012.xsd"
IMRO_FILE = "/Users/marc/Projecten/ldttoolbox/utrecht_omgevingsverordening.imro.xml"


def validate_imro():
    # Laad het schema (met resolvers voor externe XSD's)
    schema_dir = os.path.dirname(IMRO_SCHEMA)
    schema = etree.XMLSchema(file=IMRO_SCHEMA)
    
    # Laad het IMRO-bestand
    xml_doc = etree.parse(IMRO_FILE)
    
    # Valideer
    if schema.validate(xml_doc):
        print("✅ IMRO-bestand is geldig volgens het IMRO2012-schema.")
    else:
        print("❌ IMRO-bestand is ONGELDIG:")
        for error in schema.error_log:
            print(f"  Regel {error.line}: {error.message}")


if __name__ == "__main__":
    validate_imro()
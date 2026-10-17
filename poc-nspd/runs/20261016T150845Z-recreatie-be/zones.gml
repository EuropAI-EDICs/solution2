<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.122294 3.786141</gml:lowerCorner><gml:upperCorner>51.122802 3.786998</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.122294 3.786141</gml:lowerCorner><gml:upperCorner>51.122802 3.786998</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:exterior><gml:LinearRing><gml:posList>51.122294 3.786286 51.122749 3.786141 51.122802 3.786938 51.122348 3.786998 51.122294 3.786286</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-fe72e5755b</ogr:id>
      <ogr:ruleIds>FR-REC-01</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.002714592</ogr:areaKm2>
      <ogr:areaM2>2714.59246</ogr:areaM2>
      <ogr:layers>recreatie-be</ogr:layers>
      <ogr:operands>recreatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=recreatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=recreatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=2714.592460; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-REC-01; layers=recreatie-be; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=recreatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=recreatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=2714.592460; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-REC-01; layers=recreatie-be; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=recreatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=recreatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-REC-01; layers=recreatie-be; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.122294 3.786141</gml:lowerCorner><gml:upperCorner>51.122802 3.786998</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:exterior><gml:LinearRing><gml:posList>51.122749 3.786141 51.122802 3.786938 51.122348 3.786998 51.122294 3.786286 51.122749 3.786141</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-intersection-f565b8139f</ogr:id>
      <ogr:ruleIds>FR-REC-01</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.002714592</ogr:areaKm2>
      <ogr:areaM2>2714.59246</ogr:areaM2>
      <ogr:layers>recreatie-be</ogr:layers>
      <ogr:operands>recreatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-REC-01; target=AOI; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-REC-01; target=AOI; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-REC-01; target=AOI; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.122294 3.786141</gml:lowerCorner><gml:upperCorner>51.122802 3.786998</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:exterior><gml:LinearRing><gml:posList>51.122749 3.786141 51.122802 3.786938 51.122348 3.786998 51.122294 3.786286 51.122749 3.786141</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-final-c33a123b15</ogr:id>
      <ogr:ruleIds>FR-REC-01</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.002714592</ogr:areaKm2>
      <ogr:areaM2>2714.59246</ogr:areaM2>
      <ogr:layers>recreatie-be</ogr:layers>
      <ogr:operands>recreatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=recreatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=recreatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=2714.592460; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-REC-01; layers=recreatie-be; area_m2=2714.592460; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-REC-01; target=AOI; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=recreatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=recreatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-REC-01; layers=recreatie-be; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-REC-01; target=AOI; area_m2=2714.592460; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

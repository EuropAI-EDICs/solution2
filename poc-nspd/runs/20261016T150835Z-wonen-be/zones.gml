<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.110328 3.728674</gml:lowerCorner><gml:upperCorner>51.111524 3.73189</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                 
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.110328 3.728674</gml:lowerCorner><gml:upperCorner>51.111524 3.73189</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.0"><gml:exterior><gml:LinearRing><gml:posList>51.111062 3.728674 51.111144 3.729408 51.110449 3.729716 51.110328 3.728906 51.111062 3.728674</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.1"><gml:exterior><gml:LinearRing><gml:posList>51.110634 3.730805 51.111294 3.730528 51.111524 3.731699 51.11117 3.73189 51.110634 3.730805</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-0a02f6b2c1</ogr:id>
      <ogr:ruleIds>FR-WON-01</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.009658545</ogr:areaKm2>
      <ogr:areaM2>9658.545196</ogr:areaM2>
      <ogr:layers>woongebied-be</ogr:layers>
      <ogr:operands>woongebied-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=woongebied-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=woongebied-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=9658.545196; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WON-01; layers=woongebied-be; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=woongebied-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=woongebied-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=9658.545196; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WON-01; layers=woongebied-be; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=woongebied-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=woongebied-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WON-01; layers=woongebied-be; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.110634 3.730528</gml:lowerCorner><gml:upperCorner>51.111524 3.73189</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:exterior><gml:LinearRing><gml:posList>51.111294 3.730528 51.111524 3.731699 51.11117 3.73189 51.110634 3.730805 51.111294 3.730528</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-intersection-df059eec52</ogr:id>
      <ogr:ruleIds>FR-WON-01</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.005153631</ogr:areaKm2>
      <ogr:areaM2>5153.631234</ogr:areaM2>
      <ogr:layers>woongebied-be</ogr:layers>
      <ogr:operands>woongebied-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WON-01; target=AOI; area_m2=5153.631234; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WON-01; target=AOI; area_m2=5153.631234; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WON-01; target=AOI; area_m2=5153.631234; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.110634 3.730528</gml:lowerCorner><gml:upperCorner>51.111524 3.73189</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:exterior><gml:LinearRing><gml:posList>51.111294 3.730528 51.111524 3.731699 51.11117 3.73189 51.110634 3.730805 51.111294 3.730528</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-final-1ce8891855</ogr:id>
      <ogr:ruleIds>FR-WON-01</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.005153631</ogr:areaKm2>
      <ogr:areaM2>5153.631234</ogr:areaM2>
      <ogr:layers>woongebied-be</ogr:layers>
      <ogr:operands>woongebied-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=woongebied-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=woongebied-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=9658.545196; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WON-01; layers=woongebied-be; area_m2=9658.545196; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WON-01; target=AOI; area_m2=5153.631234; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=woongebied-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=woongebied-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WON-01; layers=woongebied-be; area_m2=9658.545196; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WON-01; target=AOI; area_m2=5153.631234; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

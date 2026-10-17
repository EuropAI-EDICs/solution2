<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.109329 3.729725</gml:lowerCorner><gml:upperCorner>51.110168 3.73108</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                 
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.109329 3.729725</gml:lowerCorner><gml:upperCorner>51.110168 3.73108</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:exterior><gml:LinearRing><gml:posList>51.110168 3.729725 51.110051 3.730283 51.110075 3.730549 51.11011 3.730619 51.109603 3.73108 51.109329 3.730489 51.110168 3.729725</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-cc02538f2f</ogr:id>
      <ogr:ruleIds>FR-WAT-01</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.004098206</ogr:areaKm2>
      <ogr:areaM2>4098.205947</ogr:areaM2>
      <ogr:layers>watercaptatie-be</ogr:layers>
      <ogr:operands>watercaptatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=watercaptatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=watercaptatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=4098.205947; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WAT-01; layers=watercaptatie-be; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=watercaptatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=watercaptatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=4098.205947; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WAT-01; layers=watercaptatie-be; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=watercaptatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=watercaptatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WAT-01; layers=watercaptatie-be; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.109329 3.730004</gml:lowerCorner><gml:upperCorner>51.11011 3.73108</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:exterior><gml:LinearRing><gml:posList>51.110051 3.730283 51.110075 3.730549 51.11011 3.730619 51.109603 3.73108 51.109329 3.730489 51.109861 3.730004 51.11011 3.730004 51.110051 3.730283</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-intersection-3df2cc98c3</ogr:id>
      <ogr:ruleIds>FR-WAT-01</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.003828204</ogr:areaKm2>
      <ogr:areaM2>3828.203721</ogr:areaM2>
      <ogr:layers>watercaptatie-be</ogr:layers>
      <ogr:operands>watercaptatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WAT-01; target=AOI; area_m2=3828.203721; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WAT-01; target=AOI; area_m2=3828.203721; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WAT-01; target=AOI; area_m2=3828.203721; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.109329 3.730004</gml:lowerCorner><gml:upperCorner>51.11011 3.73108</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:exterior><gml:LinearRing><gml:posList>51.110051 3.730283 51.110075 3.730549 51.11011 3.730619 51.109603 3.73108 51.109329 3.730489 51.109861 3.730004 51.11011 3.730004 51.110051 3.730283</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-final-8278a3ca84</ogr:id>
      <ogr:ruleIds>FR-WAT-01</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.003828204</ogr:areaKm2>
      <ogr:areaM2>3828.203721</ogr:areaM2>
      <ogr:layers>watercaptatie-be</ogr:layers>
      <ogr:operands>watercaptatie-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=watercaptatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=watercaptatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=4098.205947; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WAT-01; layers=watercaptatie-be; area_m2=4098.205947; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WAT-01; target=AOI; area_m2=3828.203721; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=watercaptatie-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=watercaptatie-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WAT-01; layers=watercaptatie-be; area_m2=4098.205947; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WAT-01; target=AOI; area_m2=3828.203721; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

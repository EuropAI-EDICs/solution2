<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.182139 3.780173</gml:lowerCorner><gml:upperCorner>51.191092 3.792653</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.182139 3.780173</gml:lowerCorner><gml:upperCorner>51.191092 3.792653</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:exterior><gml:LinearRing><gml:posList>51.185343 3.780173 51.185748 3.781334 51.186053 3.781406 51.18616 3.781564 51.186462 3.782616 51.18687 3.783857 51.186969 3.78455 51.187496 3.786086 51.187871 3.786233 51.188477 3.78585 51.189058 3.785738 51.189604 3.785508 51.190784 3.784884 51.190992 3.784818 51.191062 3.784876 51.191092 3.784984 51.19078 3.786696 51.190642 3.787233 51.190476 3.788882 51.190357 3.789478 51.189772 3.790639 51.189594 3.790722 51.188562 3.790887 51.187497 3.791215 51.187367 3.791544 51.187286 3.791625 51.187075 3.791626 51.186709 3.792653 51.186638 3.792593 51.186379 3.792594 51.186333 3.792547 51.18339 3.788678 51.183389 3.788556 51.18347 3.788391 51.183613 3.788227 51.182139 3.783604 51.182156 3.783262 51.182213 3.78311 51.182311 3.78293 51.182891 3.782183 51.183785 3.781363 51.185343 3.780173</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-cf9b0bb33d</ogr:id>
      <ogr:ruleIds>FR-BEZ-01</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.444686052</ogr:areaKm2>
      <ogr:areaM2>444686.051681</ogr:areaM2>
      <ogr:layers>hernieuwbaar-be</ogr:layers>
      <ogr:operands>hernieuwbaar-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=hernieuwbaar-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=hernieuwbaar-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=444686.051681; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEZ-01; layers=hernieuwbaar-be; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=hernieuwbaar-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=hernieuwbaar-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=444686.051681; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEZ-01; layers=hernieuwbaar-be; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=hernieuwbaar-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=hernieuwbaar-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-BEZ-01; layers=hernieuwbaar-be; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.182139 3.780173</gml:lowerCorner><gml:upperCorner>51.191092 3.792653</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:exterior><gml:LinearRing><gml:posList>51.185748 3.781334 51.186053 3.781406 51.18616 3.781564 51.186462 3.782616 51.18687 3.783857 51.186969 3.78455 51.187496 3.786086 51.187871 3.786233 51.188477 3.78585 51.189058 3.785738 51.189604 3.785508 51.190784 3.784884 51.190992 3.784818 51.191062 3.784876 51.191092 3.784984 51.19078 3.786696 51.190642 3.787233 51.190476 3.788882 51.190357 3.789478 51.189772 3.790639 51.189594 3.790722 51.188562 3.790887 51.187497 3.791215 51.187367 3.791544 51.187286 3.791625 51.187075 3.791626 51.186709 3.792653 51.186638 3.792593 51.186379 3.792594 51.186333 3.792547 51.18339 3.788678 51.183389 3.788556 51.18347 3.788391 51.183613 3.788227 51.182139 3.783604 51.182156 3.783262 51.182213 3.78311 51.182311 3.78293 51.182891 3.782183 51.183785 3.781363 51.185343 3.780173 51.185748 3.781334</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-intersection-5fb2524455</ogr:id>
      <ogr:ruleIds>FR-BEZ-01</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.444686052</ogr:areaKm2>
      <ogr:areaM2>444686.051681</ogr:areaM2>
      <ogr:layers>hernieuwbaar-be</ogr:layers>
      <ogr:operands>hernieuwbaar-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEZ-01; target=AOI; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEZ-01; target=AOI; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-BEZ-01; target=AOI; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.182139 3.780173</gml:lowerCorner><gml:upperCorner>51.191092 3.792653</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:exterior><gml:LinearRing><gml:posList>51.186053 3.781406 51.18616 3.781564 51.186462 3.782616 51.18687 3.783857 51.186969 3.78455 51.187496 3.786086 51.187871 3.786233 51.188477 3.78585 51.189058 3.785738 51.189604 3.785508 51.190784 3.784884 51.190992 3.784818 51.191062 3.784876 51.191092 3.784984 51.19078 3.786696 51.190642 3.787233 51.190476 3.788882 51.190357 3.789478 51.189772 3.790639 51.189594 3.790722 51.188562 3.790887 51.187497 3.791215 51.187367 3.791544 51.187286 3.791625 51.187075 3.791626 51.186709 3.792653 51.186638 3.792593 51.186379 3.792594 51.186333 3.792547 51.18339 3.788678 51.183389 3.788556 51.18347 3.788391 51.183613 3.788227 51.182139 3.783604 51.182156 3.783262 51.182213 3.78311 51.182311 3.78293 51.182891 3.782183 51.183785 3.781363 51.185343 3.780173 51.185748 3.781334 51.186053 3.781406</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-difference-ad2b5a9c7f</ogr:id>
      <ogr:ruleIds>FR-BEZ-02</ogr:ruleIds>
      <ogr:operation>difference</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.444686052</ogr:areaKm2>
      <ogr:areaM2>444686.051681</ogr:areaM2>
      <ogr:layers>bouwvrij-be</ogr:layers>
      <ogr:layers>national_source</ogr:layers>
      <ogr:operands>bouwvrij-be</ogr:operands>
      <ogr:operands>national_source</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=union layer=bouwvrij-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=bouwvrij-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=10038.802938; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEZ-02; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEZ-02; layers=bouwvrij-be,national_source; buffer_m=0.0; area_before_m2=444686.051681; area_after_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=union layer=bouwvrij-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=bouwvrij-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=10038.802938; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEZ-02; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEZ-02; layers=bouwvrij-be,national_source; buffer_m=0.0; area_before_m2=444686.051681; area_after_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=union layer=bouwvrij-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=bouwvrij-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=10038.802938; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=difference rule=FR-BEZ-02; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=difference; rule=FR-BEZ-02; layers=bouwvrij-be,national_source; buffer_m=0.0; area_before_m2=444686.051681; area_after_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.3">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.182139 3.780173</gml:lowerCorner><gml:upperCorner>51.191092 3.792653</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:Polygon srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.3"><gml:exterior><gml:LinearRing><gml:posList>51.186053 3.781406 51.18616 3.781564 51.186462 3.782616 51.18687 3.783857 51.186969 3.78455 51.187496 3.786086 51.187871 3.786233 51.188477 3.78585 51.189058 3.785738 51.189604 3.785508 51.190784 3.784884 51.190992 3.784818 51.191062 3.784876 51.191092 3.784984 51.19078 3.786696 51.190642 3.787233 51.190476 3.788882 51.190357 3.789478 51.189772 3.790639 51.189594 3.790722 51.188562 3.790887 51.187497 3.791215 51.187367 3.791544 51.187286 3.791625 51.187075 3.791626 51.186709 3.792653 51.186638 3.792593 51.186379 3.792594 51.186333 3.792547 51.18339 3.788678 51.183389 3.788556 51.18347 3.788391 51.183613 3.788227 51.182139 3.783604 51.182156 3.783262 51.182213 3.78311 51.182311 3.78293 51.182891 3.782183 51.183785 3.781363 51.185343 3.780173 51.185748 3.781334 51.186053 3.781406</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></ogr:geometryProperty>
      <ogr:id>zr-final-841010d050</ogr:id>
      <ogr:ruleIds>FR-BEZ-01</ogr:ruleIds>
      <ogr:ruleIds>FR-BEZ-02</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.444686052</ogr:areaKm2>
      <ogr:areaM2>444686.051681</ogr:areaM2>
      <ogr:layers>bouwvrij-be</ogr:layers>
      <ogr:layers>hernieuwbaar-be</ogr:layers>
      <ogr:layers>national_source</ogr:layers>
      <ogr:operands>bouwvrij-be</ogr:operands>
      <ogr:operands>hernieuwbaar-be</ogr:operands>
      <ogr:operands>national_source</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=hernieuwbaar-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=hernieuwbaar-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=444686.051681; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEZ-01; layers=hernieuwbaar-be; area_m2=444686.051681; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEZ-01; target=AOI; area_m2=444686.051681; engine=poc-zone-engine/0.1 | op=validity_check; ctx=union layer=bouwvrij-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=bouwvrij-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=10038.802938; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEZ-02; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEZ-02; layers=bouwvrij-be,national_source; buffer_m=0.0; area_before_m2=444686.051681; area_after_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=hernieuwbaar-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=hernieuwbaar-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=1; make_valid_repairs=0; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-BEZ-01; layers=hernieuwbaar-be; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-BEZ-01; target=AOI; area_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=bouwvrij-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=bouwvrij-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_ov; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=10038.802938; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=difference rule=FR-BEZ-02; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=difference; rule=FR-BEZ-02; layers=bouwvrij-be,national_source; buffer_m=0.0; area_before_m2=444686.051681; area_after_m2=444686.051681; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

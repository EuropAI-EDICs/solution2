<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.106336 3.760929</gml:lowerCorner><gml:upperCorner>51.18843 3.832633</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                 
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.106336 3.760929</gml:lowerCorner><gml:upperCorner>51.18843 3.832633</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.0"><gml:exterior><gml:LinearRing><gml:posList>51.106859 3.762802 51.106776 3.762414 51.106728 3.762378 51.106719 3.76231 51.106601 3.762348 51.106336 3.761287 51.106629 3.76098 51.106718 3.760929 51.107282 3.761366 51.108727 3.762634 51.109422 3.763304 51.109606 3.764709 51.109241 3.764234 51.108884 3.763907 51.108565 3.76385 51.10843 3.763668 51.10751 3.763291 51.107458 3.763515 51.107396 3.763178 51.107202 3.762917 51.10714 3.762696 51.106859 3.762802</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.1"><gml:exterior><gml:LinearRing><gml:posList>51.186336 3.827917 51.185987 3.825788 51.186714 3.826461 51.186968 3.826596 51.187713 3.82675 51.18843 3.826768 51.187448 3.831152 51.187353 3.831094 51.187052 3.831498 51.186769 3.832161 51.186149 3.832319 51.184625 3.832594 51.184093 3.832633 51.186336 3.827917</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-270ffee81c</ogr:id>
      <ogr:ruleIds>FR-BEE-01</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.137037777</ogr:areaKm2>
      <ogr:areaM2>137037.776725</ogr:areaM2>
      <ogr:layers>zeehavenondersteunend-be</ogr:layers>
      <ogr:operands>zeehavenondersteunend-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenondersteunend-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenondersteunend-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=137037.776725; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEE-01; layers=zeehavenondersteunend-be; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenondersteunend-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenondersteunend-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=137037.776725; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEE-01; layers=zeehavenondersteunend-be; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=zeehavenondersteunend-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=zeehavenondersteunend-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-BEE-01; layers=zeehavenondersteunend-be; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.106336 3.760929</gml:lowerCorner><gml:upperCorner>51.18843 3.832633</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.0"><gml:exterior><gml:LinearRing><gml:posList>51.106728 3.762378 51.106719 3.76231 51.106601 3.762348 51.106336 3.761287 51.106629 3.76098 51.106718 3.760929 51.107282 3.761366 51.108727 3.762634 51.109422 3.763304 51.109606 3.764709 51.109241 3.764234 51.108884 3.763907 51.108565 3.76385 51.10843 3.763668 51.10751 3.763291 51.107458 3.763515 51.107396 3.763178 51.107202 3.762917 51.10714 3.762696 51.106859 3.762802 51.106776 3.762414 51.106728 3.762378</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.1"><gml:exterior><gml:LinearRing><gml:posList>51.186714 3.826461 51.186968 3.826596 51.187713 3.82675 51.18843 3.826768 51.187448 3.831152 51.187353 3.831094 51.187052 3.831498 51.186769 3.832161 51.186149 3.832319 51.184625 3.832594 51.184093 3.832633 51.186336 3.827917 51.185987 3.825788 51.186714 3.826461</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-intersection-314a8a2f39</ogr:id>
      <ogr:ruleIds>FR-BEE-01</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.137037777</ogr:areaKm2>
      <ogr:areaM2>137037.776725</ogr:areaM2>
      <ogr:layers>zeehavenondersteunend-be</ogr:layers>
      <ogr:operands>zeehavenondersteunend-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEE-01; target=AOI; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEE-01; target=AOI; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-BEE-01; target=AOI; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.106336 3.760929</gml:lowerCorner><gml:upperCorner>51.18843 3.832633</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.0"><gml:exterior><gml:LinearRing><gml:posList>51.106601 3.762348 51.106336 3.761287 51.106629 3.76098 51.106718 3.760929 51.107282 3.761366 51.108727 3.762634 51.109422 3.763304 51.109606 3.764709 51.109241 3.764234 51.108884 3.763907 51.108565 3.76385 51.10843 3.763668 51.10751 3.763291 51.107458 3.763515 51.107396 3.763178 51.107202 3.762917 51.10714 3.762696 51.106859 3.762802 51.106776 3.762414 51.106728 3.762378 51.106719 3.76231 51.106601 3.762348</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.1"><gml:exterior><gml:LinearRing><gml:posList>51.187713 3.82675 51.18843 3.826768 51.187448 3.831152 51.187353 3.831094 51.187052 3.831498 51.186769 3.832161 51.186149 3.832319 51.184625 3.832594 51.184093 3.832633 51.186336 3.827917 51.185987 3.825788 51.186714 3.826461 51.186968 3.826596 51.187713 3.82675</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-difference-77ab2b05b7</ogr:id>
      <ogr:ruleIds>FR-BEE-03</ogr:ruleIds>
      <ogr:operation>difference</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.137037777</ogr:areaKm2>
      <ogr:areaM2>137037.776725</ogr:areaM2>
      <ogr:layers>papierbedrijven-be</ogr:layers>
      <ogr:layers>national_source</ogr:layers>
      <ogr:operands>papierbedrijven-be</ogr:operands>
      <ogr:operands>national_source</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEE-03; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEE-03; layers=papierbedrijven-be,national_source; buffer_m=0.0; area_before_m2=137037.776725; area_after_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEE-03; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEE-03; layers=papierbedrijven-be,national_source; buffer_m=0.0; area_before_m2=137037.776725; area_after_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=difference rule=FR-BEE-03; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=difference; rule=FR-BEE-03; layers=papierbedrijven-be,national_source; buffer_m=0.0; area_before_m2=137037.776725; area_after_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.3">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.106336 3.760929</gml:lowerCorner><gml:upperCorner>51.18843 3.832633</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.3"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.3.0"><gml:exterior><gml:LinearRing><gml:posList>51.106601 3.762348 51.106336 3.761287 51.106629 3.76098 51.106718 3.760929 51.107282 3.761366 51.108727 3.762634 51.109422 3.763304 51.109606 3.764709 51.109241 3.764234 51.108884 3.763907 51.108565 3.76385 51.10843 3.763668 51.10751 3.763291 51.107458 3.763515 51.107396 3.763178 51.107202 3.762917 51.10714 3.762696 51.106859 3.762802 51.106776 3.762414 51.106728 3.762378 51.106719 3.76231 51.106601 3.762348</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.3.1"><gml:exterior><gml:LinearRing><gml:posList>51.187713 3.82675 51.18843 3.826768 51.187448 3.831152 51.187353 3.831094 51.187052 3.831498 51.186769 3.832161 51.186149 3.832319 51.184625 3.832594 51.184093 3.832633 51.186336 3.827917 51.185987 3.825788 51.186714 3.826461 51.186968 3.826596 51.187713 3.82675</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-final-0358cf8420</ogr:id>
      <ogr:ruleIds>FR-BEE-01</ogr:ruleIds>
      <ogr:ruleIds>FR-BEE-03</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.137037777</ogr:areaKm2>
      <ogr:areaM2>137037.776725</ogr:areaM2>
      <ogr:layers>national_source</ogr:layers>
      <ogr:layers>papierbedrijven-be</ogr:layers>
      <ogr:layers>zeehavenondersteunend-be</ogr:layers>
      <ogr:operands>national_source</ogr:operands>
      <ogr:operands>papierbedrijven-be</ogr:operands>
      <ogr:operands>zeehavenondersteunend-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenondersteunend-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenondersteunend-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=137037.776725; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-BEE-01; layers=zeehavenondersteunend-be; area_m2=137037.776725; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-BEE-01; target=AOI; area_m2=137037.776725; engine=poc-zone-engine/0.1 | op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=difference rule=FR-BEE-03; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=difference; rule=FR-BEE-03; layers=papierbedrijven-be,national_source; buffer_m=0.0; area_before_m2=137037.776725; area_after_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=zeehavenondersteunend-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=zeehavenondersteunend-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-BEE-01; layers=zeehavenondersteunend-be; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-BEE-01; target=AOI; area_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=difference rule=FR-BEE-03; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=difference; rule=FR-BEE-03; layers=papierbedrijven-be,national_source; buffer_m=0.0; area_before_m2=137037.776725; area_after_m2=137037.776725; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

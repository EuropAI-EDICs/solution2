<?xml version="1.0" encoding="utf-8" ?>
<ogr:FeatureCollection
     gml:id="aFeatureCollection"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     xsi:schemaLocation="http://ogr.maptools.org/ zones.xsd"
     xmlns:ogr="http://ogr.maptools.org/"
     xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.075655 3.728541</gml:lowerCorner><gml:upperCorner>51.133592 3.769478</gml:upperCorner></gml:Envelope></gml:boundedBy>
                                                                                                                                                
  <ogr:featureMember>
    <ogr:zones gml:id="zones.0">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.075655 3.728541</gml:lowerCorner><gml:upperCorner>51.133592 3.769478</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.0"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.0"><gml:exterior><gml:LinearRing><gml:posList>51.079689 3.733763 51.079685 3.733594 51.079622 3.733365 51.082285 3.732914 51.082167 3.731158 51.083587 3.730894 51.086925 3.729845 51.086967 3.729893 51.086986 3.73003 51.086967 3.730535 51.087177 3.730508 51.087432 3.730565 51.087751 3.730736 51.088255 3.731113 51.088346 3.731072 51.088547 3.73066 51.089088 3.728541 51.089347 3.728707 51.089437 3.72863 51.093976 3.731553 51.094052 3.732644 51.075741 3.735692 51.075655 3.734415 51.075796 3.734472 51.077063 3.734259 51.077129 3.734188 51.079689 3.733763</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.1"><gml:exterior><gml:LinearRing><gml:posList>51.102353 3.732516 51.102359 3.733482 51.102084 3.733488 51.101975 3.733558 51.102619 3.731392 51.102751 3.731445 51.102948 3.731426 51.10313 3.7313 51.103262 3.731104 51.103913 3.731625 51.104189 3.732012 51.104494 3.732131 51.105361 3.73227 51.106847 3.732271 51.107722 3.732423 51.108723 3.732903 51.109056 3.733158 51.109044 3.733403 51.108679 3.733123 51.108075 3.732799 51.107569 3.732616 51.107093 3.732519 51.106417 3.732478 51.102353 3.732516</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.2"><gml:exterior><gml:LinearRing><gml:posList>51.109301 3.734697 51.109262 3.734548 51.109378 3.734249 51.109833 3.734081 51.110201 3.734531 51.109776 3.735293 51.109301 3.734697</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.0.3"><gml:exterior><gml:LinearRing><gml:posList>51.133412 3.767717 51.133592 3.767853 51.133095 3.769478 51.132297 3.768886 51.131814 3.768439 51.132516 3.766735 51.132659 3.766909 51.132594 3.766734 51.133412 3.767717</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-inclusion_union-c030f83435</ogr:id>
      <ogr:ruleIds>FR-WER-01</ogr:ruleIds>
      <ogr:ruleIds>FR-WER-02</ogr:ruleIds>
      <ogr:operation>inclusion_union</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.429348381</ogr:areaKm2>
      <ogr:areaM2>429348.381339</ogr:areaM2>
      <ogr:layers>zeehavenbedrijven-be</ogr:layers>
      <ogr:layers>papierbedrijven-be</ogr:layers>
      <ogr:operands>zeehavenbedrijven-be</ogr:operands>
      <ogr:operands>papierbedrijven-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=398814.689224; engine=poc-zone-engine/0.1 | op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WER-01,FR-WER-02; layers=zeehavenbedrijven-be,papierbedrijven-be; area_m2=429348.381339; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=398814.689224; engine=poc-zone-engine/0.1 | op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WER-01,FR-WER-02; layers=zeehavenbedrijven-be,papierbedrijven-be; area_m2=429348.381339; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=zeehavenbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=zeehavenbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=398814.689224; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WER-01,FR-WER-02; layers=zeehavenbedrijven-be,papierbedrijven-be; area_m2=429348.381339; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.1">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.075655 3.730003</gml:lowerCorner><gml:upperCorner>51.133592 3.769478</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.1"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.0"><gml:exterior><gml:LinearRing><gml:posList>51.082285 3.732914 51.082167 3.731158 51.083587 3.730894 51.086422 3.730003 51.086982 3.730003 51.086986 3.73003 51.086967 3.730535 51.087177 3.730508 51.087432 3.730565 51.087751 3.730736 51.088255 3.731113 51.088346 3.731072 51.088547 3.73066 51.088715 3.730003 51.091571 3.730003 51.093976 3.731553 51.094052 3.732644 51.075741 3.735692 51.075655 3.734415 51.075796 3.734472 51.077063 3.734259 51.077129 3.734188 51.079689 3.733763 51.079685 3.733594 51.079622 3.733365 51.082285 3.732914</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.1"><gml:exterior><gml:LinearRing><gml:posList>51.101975 3.733558 51.102619 3.731392 51.102751 3.731445 51.102948 3.731426 51.10313 3.7313 51.103262 3.731104 51.103913 3.731625 51.104189 3.732012 51.104494 3.732131 51.105361 3.73227 51.106847 3.732271 51.107722 3.732423 51.108723 3.732903 51.109056 3.733158 51.109044 3.733403 51.108679 3.733123 51.108075 3.732799 51.107569 3.732616 51.107093 3.732519 51.106417 3.732478 51.102353 3.732516 51.102359 3.733482 51.102084 3.733488 51.101975 3.733558</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.2"><gml:exterior><gml:LinearRing><gml:posList>51.109833 3.734081 51.110201 3.734531 51.109776 3.735293 51.109301 3.734697 51.109262 3.734548 51.109378 3.734249 51.109833 3.734081</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.1.3"><gml:exterior><gml:LinearRing><gml:posList>51.132297 3.768886 51.131814 3.768439 51.132516 3.766735 51.132659 3.766909 51.132594 3.766734 51.133412 3.767717 51.133592 3.767853 51.133095 3.769478 51.132297 3.768886</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-intersection-1ca18380cc</ogr:id>
      <ogr:ruleIds>FR-WER-01</ogr:ruleIds>
      <ogr:ruleIds>FR-WER-02</ogr:ruleIds>
      <ogr:operation>intersection</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.411713206</ogr:areaKm2>
      <ogr:areaM2>411713.205583</ogr:areaM2>
      <ogr:layers>zeehavenbedrijven-be</ogr:layers>
      <ogr:layers>papierbedrijven-be</ogr:layers>
      <ogr:operands>zeehavenbedrijven-be</ogr:operands>
      <ogr:operands>papierbedrijven-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WER-01,FR-WER-02; target=AOI; area_m2=411713.205583; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WER-01,FR-WER-02; target=AOI; area_m2=411713.205583; engine=poc-zone-engine/0.1</ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WER-01,FR-WER-02; target=AOI; area_m2=411713.205583; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
  <ogr:featureMember>
    <ogr:zones gml:id="zones.2">
      <gml:boundedBy><gml:Envelope srsName="urn:ogc:def:crs:EPSG::4326"><gml:lowerCorner>51.075655 3.730003</gml:lowerCorner><gml:upperCorner>51.133592 3.769478</gml:upperCorner></gml:Envelope></gml:boundedBy>
      <ogr:geometryProperty><gml:MultiSurface srsName="urn:ogc:def:crs:EPSG::4326" gml:id="zones.geom.2"><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.0"><gml:exterior><gml:LinearRing><gml:posList>51.082285 3.732914 51.082167 3.731158 51.083587 3.730894 51.086422 3.730003 51.086982 3.730003 51.086986 3.73003 51.086967 3.730535 51.087177 3.730508 51.087432 3.730565 51.087751 3.730736 51.088255 3.731113 51.088346 3.731072 51.088547 3.73066 51.088715 3.730003 51.091571 3.730003 51.093976 3.731553 51.094052 3.732644 51.075741 3.735692 51.075655 3.734415 51.075796 3.734472 51.077063 3.734259 51.077129 3.734188 51.079689 3.733763 51.079685 3.733594 51.079622 3.733365 51.082285 3.732914</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.1"><gml:exterior><gml:LinearRing><gml:posList>51.101975 3.733558 51.102619 3.731392 51.102751 3.731445 51.102948 3.731426 51.10313 3.7313 51.103262 3.731104 51.103913 3.731625 51.104189 3.732012 51.104494 3.732131 51.105361 3.73227 51.106847 3.732271 51.107722 3.732423 51.108723 3.732903 51.109056 3.733158 51.109044 3.733403 51.108679 3.733123 51.108075 3.732799 51.107569 3.732616 51.107093 3.732519 51.106417 3.732478 51.102353 3.732516 51.102359 3.733482 51.102084 3.733488 51.101975 3.733558</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.2"><gml:exterior><gml:LinearRing><gml:posList>51.109833 3.734081 51.110201 3.734531 51.109776 3.735293 51.109301 3.734697 51.109262 3.734548 51.109378 3.734249 51.109833 3.734081</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember><gml:surfaceMember><gml:Polygon gml:id="zones.geom.2.3"><gml:exterior><gml:LinearRing><gml:posList>51.132297 3.768886 51.131814 3.768439 51.132516 3.766735 51.132659 3.766909 51.132594 3.766734 51.133412 3.767717 51.133592 3.767853 51.133095 3.769478 51.132297 3.768886</gml:posList></gml:LinearRing></gml:exterior></gml:Polygon></gml:surfaceMember></gml:MultiSurface></ogr:geometryProperty>
      <ogr:id>zr-final-1a628144c5</ogr:id>
      <ogr:ruleIds>FR-WER-01</ogr:ruleIds>
      <ogr:ruleIds>FR-WER-02</ogr:ruleIds>
      <ogr:operation>final</ogr:operation>
      <ogr:geometryValid>true</ogr:geometryValid>
      <ogr:areaKm2>0.411713206</ogr:areaKm2>
      <ogr:areaM2>411713.205583</ogr:areaM2>
      <ogr:layers>papierbedrijven-be</ogr:layers>
      <ogr:layers>zeehavenbedrijven-be</ogr:layers>
      <ogr:operands>papierbedrijven-be</ogr:operands>
      <ogr:operands>zeehavenbedrijven-be</ogr:operands>
      <ogr:status>ok</ogr:status>
      <ogr:prov>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=validity_check; ctx=union layer=zeehavenbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=zeehavenbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=398814.689224; engine=poc-zone-engine/0.1 | op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1 | op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=inclusion_union; rules=FR-WER-01,FR-WER-02; layers=zeehavenbedrijven-be,papierbedrijven-be; area_m2=429348.381339; engine=poc-zone-engine/0.1 | op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0 | op=intersection; rules=FR-WER-01,FR-WER-02; target=AOI; area_m2=411713.205583; engine=poc-zone-engine/0.1</ogr:prov>
      <ogr:provenance></ogr:provenance>
      <ogr:provSteps>op=validity_check; ctx=aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=zeehavenbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=zeehavenbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=398814.689224; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=union layer=papierbedrijven-be; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=union; layer=papierbedrijven-be(https://www.mercator.vlaanderen.be/raadpleegdienstenmercatorpubliek/wfs/lu:lu_gewrup_gv; lastChecked=2026-10-16; simplifiedM=2.0); features=2; make_valid_repairs=0; area_m2=30533.692115; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=inclusion_union; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=inclusion_union; rules=FR-WER-01,FR-WER-02; layers=zeehavenbedrijven-be,papierbedrijven-be; area_m2=429348.381339; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:provSteps>op=validity_check; ctx=clip_aoi; make_valid_repairs=0; engine=poc-zone-engine/0.1 shapely/2.2.0</ogr:provSteps>
      <ogr:provSteps>op=intersection; rules=FR-WER-01,FR-WER-02; target=AOI; area_m2=411713.205583; engine=poc-zone-engine/0.1</ogr:provSteps>
      <ogr:computedBy>poc-zone-engine/0.1</ogr:computedBy>
      <ogr:computedAt></ogr:computedAt>
    </ogr:zones>
  </ogr:featureMember>
</ogr:FeatureCollection>

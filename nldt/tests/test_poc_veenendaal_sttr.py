# nldt/tests/test_poc_veenendaal_sttr.py
"""Tests voor poc-veenendaal/sttr.py — het loket over de Spoorzone.

Offline en deterministisch: synthetische caches (STTR-index, OW-pakket-zip met
GIO-GML's) en stub-indicatoren; geen netwerk, geen afhankelijkheid van de
gitignored caches onder dso_overlap/out of poc-veenendaal/data/cache.
"""
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "poc_veenendaal_sttr", ROOT / "poc-veenendaal" / "sttr.py")
sttr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sttr)

# geoVerwijzing dragende mini-DMN (dmn 1.1/v1.0-vorm, zoals de echte set)
_DMN = """<?xml version="1.0" encoding="UTF-8"?>
<dmn:definitions xmlns:dmn="http://www.omg.org/spec/DMN/20151101/dmn.xsd"
                 xmlns:inter="http://toepasbare-regels.omgevingswet.overheid.nl/v1.0/Interactieregel"
                 xmlns:uitv="http://toepasbare-regels.omgevingswet.overheid.nl/v1.0/Uitvoeringsregel"
                 xmlns="http://toepasbare-regels.omgevingswet.overheid.nl/00000001001104470000"
                 namespace="http://toepasbare-regels.omgevingswet.overheid.nl/00000001001104470000"
                 name="Test">
  <dmn:extensionElements>
    <uitv:uitvoeringsregels>
      <uitv:uitvoeringsregel id="u1">
        <uitv:vraag><uitv:gegevensType>boolean</uitv:gegevensType>
          <uitv:vraagTekst>Gaat het om een monument?</uitv:vraagTekst></uitv:vraag>
      </uitv:uitvoeringsregel>
      <uitv:uitvoeringsregel id="u2">
        <uitv:geoVerwijzing>
          <uitv:locatie identificatie="nl.imow-gm0345.gebied.dichtbij"/>
          <uitv:vraagTekst>Ligt de locatie in het beschermde gebied?</uitv:vraagTekst>
        </uitv:geoVerwijzing>
      </uitv:uitvoeringsregel>
    </uitv:uitvoeringsregels>
  </dmn:extensionElements>
</dmn:definitions>
"""

_GML_BINNEN = """<?xml version="1.0"?>
<geo:GeoInformatieObjectVaststelling xmlns:geo="https://standaarden.overheid.nl/stop/imop/geo/"
  xmlns:gml="http://www.opengis.net/gml/3.2">
  <geo:FRBRWork>/join/id/regdata/gm0345/2026/testgio1</geo:FRBRWork>
  <geo:vastgesteldeVersie><geo:GeoInformatieObjectVersie><geo:geoInformatieObjectVersie>
    <basisgeo:FeatureMemberGeometrie xmlns:basisgeo="http://www.geostandaarden.nl/basisgeometrie/1.0">
      <basisgeo:geometrie>
        <gml:Polygon srsName="epsg:28992"><gml:exterior><gml:LinearRing>
          <gml:posList>1 1 9 1 9 9 1 9 1 1</gml:posList>
        </gml:LinearRing></gml:exterior></gml:Polygon>
      </basisgeo:geometrie>
    </basisgeo:FeatureMemberGeometrie>
  </geo:geoInformatieObjectVersie></geo:GeoInformatieObjectVersie></geo:vastgesteldeVersie>
</geo:GeoInformatieObjectVaststelling>
"""

_GML_BUITEN = _GML_BINNEN.replace("1 1 9 1 9 9 1 9 1 1", "100 100 110 100 110 110 100 110 100 100") \
                          .replace("testgio1", "testgio2")

BBOX = [0, 0, 10, 10]


def _mini_index():
    return {"totals": {"bestanden": 1},
            "bestanden": [{
                "identifier": 42, "activiteit": "HoutopstandVellen",
                "begindatum": "01-01-2026", "einddatum": None,
                "geoVerwijzingen": 1, "dmnVersie": "1.1",
                "decisions": [{"naam": "d", "projecteerbaar": True}],
            }]}


def _tmp_out(tmp):
    out = pathlib.Path(tmp)
    (out / "veenendaal.rtr.42.dmn").write_text(_DMN, encoding="utf-8")
    return out


def _tmp_pakket(tmp):
    pad = pathlib.Path(tmp) / "pakket.zip"
    with zipfile.ZipFile(pad, "w") as z:
        z.writestr("OW-bestanden/gebieden.xml",
                   '<ow><l:Gebied><l:identificatie>nl.imow-gm0345.gebied.zondergeom'
                   '</l:identificatie></l:Gebied></ow>')
        z.writestr("OW-bestanden/gebiedengroepen.xml", "<ow/>")
        z.writestr("IO-a/nl.imow-gm0345.gebied.dichtbij.gml", _GML_BINNEN)
        z.writestr("IO-b/Vrijenaam-verweg.gml", _GML_BUITEN)
    return pad


class TestGeoVerwijzingen(unittest.TestCase):
    def test_extractie_uit_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            uit = sttr.geo_verwijzingen(_mini_index(), _tmp_out(tmp))
            self.assertEqual(len(uit), 1)
            self.assertEqual(uit[0]["locatieIdentificatie"], "nl.imow-gm0345.gebied.dichtbij")
            self.assertIn("beschermde gebied", uit[0]["vraagTekst"])


class TestKoppelStatussen(unittest.TestCase):
    def test_drie_statussen(self):
        with tempfile.TemporaryDirectory() as tmp:
            pakket = _tmp_pakket(tmp)
            verwijzingen = [
                {"rtrId": 42, "activiteit": "HoutopstandVellen", "begindatum": "01-01-2026",
                 "locatieIdentificatie": "nl.imow-gm0345.gebied.dichtbij", "vraagTekst": "x"},
                {"rtrId": 43, "activiteit": "KleinschaligGravenBovenInt", "begindatum": "01-01-2026",
                 "locatieIdentificatie": "nl.imow-gm0345.gebied.zondergeom", "vraagTekst": "y"},
                {"rtrId": 44, "activiteit": "HoutopstandVellen", "begindatum": "01-01-2026",
                 "locatieIdentificatie": "nl.imow-gm0345.gebiedengroep.0040x", "vraagTekst": "z"},
            ]
            gekoppeld, samenvatting = sttr.koppel_geo_aan_werkgrens(verwijzingen, pakket, BBOX)
            self.assertEqual(gekoppeld[0]["status"], "gekoppeld")
            self.assertTrue(gekoppeld[0]["snijdtWerkgrens"])
            self.assertAlmostEqual(gekoppeld[0]["overlapHa"], 0.01, places=2)  # 64 m² → 0,0064 ha → afgerond 0,01
            self.assertEqual(gekoppeld[1]["status"], "aanwezig-als-ow-object")
            self.assertEqual(gekoppeld[2]["status"], "afwezig-in-pakket")
            self.assertEqual(samenvatting["locatiesInPakket"], 1)
            self.assertEqual(samenvatting["owObjecten"], 1)

    def test_sweep_vindt_snijdende_gio(self):
        with tempfile.TemporaryDirectory() as tmp:
            gios = sttr.sweep_gios_tegen_werkgrens(_tmp_pakket(tmp), BBOX)
            snijdend = [g for g in gios if g.get("snijdtWerkgrens")]
            self.assertEqual(len(gios), 2)
            self.assertEqual(len(snijdend), 1)
            self.assertEqual(snijdend[0]["bestand"], "nl.imow-gm0345.gebied.dichtbij.gml")
            self.assertTrue(snijdend[0]["frbrWork"].endswith("testgio1"))


class TestKoppelregels(unittest.TestCase):
    IND = {"spoorlijn_km": 1.8, "panden_bestand": 2926,
           "vegetatieobject_punt": 1095, "vegetatie_vlak_ha": 32.83}
    GEBIED = {"type": "gebiedsontwikkeling (transformatie binnen bebouwde kom)",
              "doelen_uit_toekomstbeeld": {"woningen_nieuw_feiten_tabel": 4500}}

    def test_vol_programma_zeven_koppelingen(self):
        regels = sttr.koppelregels(self.IND, self.GEBIED)
        self.assertEqual(len(regels), 7)
        namen = {r["activiteit"] for r in regels}
        self.assertIn("WegSpoorwegAanleggenWijz", namen)
        self.assertIn("HoutopstandVellen", namen)
        for r in regels:
            self.assertTrue(r["bewijs"], r)

    def test_zonder_spoor_geen_spooractiviteit(self):
        regels = sttr.koppelregels({**self.IND, "spoorlijn_km": 0}, self.GEBIED)
        namen = {r["activiteit"] for r in regels}
        self.assertNotIn("WegSpoorwegAanleggenWijz", namen)
        self.assertNotIn("GeluidProdAndereAct", namen)


class TestVragenPerActiviteit(unittest.TestCase):
    def test_vragen_met_labels(self):
        with tempfile.TemporaryDirectory() as tmp:
            uit = sttr.vragen_per_activiteit(_mini_index(), {"HoutopstandVellen"}, _tmp_out(tmp))
            rec = uit["HoutopstandVellen"]
            self.assertEqual(rec["totaalVragen"], 2)
            self.assertEqual(rec["projecteerbaar"], 1)
            teksten = rec["bestanden"][0]["vragen"]
            self.assertEqual(teksten[0], "Gaat het om een monument?")
            self.assertTrue(teksten[1].endswith("(geo)"))


class TestRapport(unittest.TestCase):
    def test_secties_aanwezig(self):
        with tempfile.TemporaryDirectory() as tmp:
            data = {
                "runId": "test", "oin": "00000001001104470000", "totaalBestanden": 185,
                "dmnVersies": {"1.1": 112, "1.2": 73}, "dmnVersiesTekst": "112× DMN 1.1 + 73× DMN 1.2",
                "begindatumMin": "29-06-2022", "begindatumMax": "24-12-2025", "gebied": "Spoorzone",
                "regeling": {"officieleTitel": "Omgevingsplan", "identificatie": "/akn/x"},
                "locatieGebonden": {
                    "status": "gemeten",
                    "verwijzingen": [
                        {"activiteit": "A", "vraagTekst": "q", "locatieIdentificatie": "i",
                         "begindatum": "01-01-2026", "status": "gekoppeld",
                         "snijdtWerkgrens": True, "overlapHa": 1.2},
                        {"activiteit": "B", "vraagTekst": "q2", "locatieIdentificatie": "j",
                         "begindatum": "01-01-2026", "status": "afwezig-in-pakket"},
                    ],
                    "samenvatting": {"locatiesInPakket": 1},
                    "gios": [{"bestand": "x.gml", "frbrWork": "/join/1", "parseerbaar": True,
                              "snijdtWerkgrens": True, "overlapHa": 2.0}],
                },
                "programmaGebonden": [
                    {"activiteit": "WegSpoorwegAanleggenWijz", "soort": "gebied", "bewijs": "spoor"}],
                "activiteiten": {},
            }
            run_dir = pathlib.Path(tmp)
            sttr.schrijf_rapport(run_dir, data)
            tekst = (run_dir / "report.md").read_text(encoding="utf-8")
            for kop in ("Locatie-gebonden vragen", "Officiële GIO-lagen",
                        "Programma-gebonden vragen", "De officiële vragen per activiteit",
                        "Beperkingen"):
                self.assertIn(kop, tekst, kop)
            self.assertIn("1 gekoppeld", tekst)
            self.assertIn("1 afwezig", tekst)


_spec_kruising = importlib.util.spec_from_file_location(
    "poc_veenendaal_sttr_kruising", ROOT / "poc-veenendaal" / "sttr_kruising.py")
kruising = importlib.util.module_from_spec(_spec_kruising)
_spec_kruising.loader.exec_module(kruising)


class TestKruising(unittest.TestCase):
    """sttr_kruising.py — GML-parse, kruis-berekening en genomen-vlakken-unie."""

    GML = """<?xml version="1.0"?>
<gio:GeoInformatieObjectVaststelling xmlns:gio="https://standaarden.overheid.nl/stop/imop/geo/"
  xmlns:gml="http://www.opengis.net/gml/3.2">
  <geo:FRBRWork xmlns:geo="https://standaarden.overheid.nl/stop/imop/geo/">/join/id/regdata/gm0345/2026/t</geo:FRBRWork>
  <gml:Polygon srsName="epsg:28992"><gml:exterior><gml:LinearRing>
    <gml:posList>{}</gml:posList>
  </gml:LinearRing></gml:exterior></gml:Polygon>
</gio:GeoInformatieObjectVaststelling>
"""

    def test_gml_polygonen(self):
        polys = kruising.gml_polygonen(self.GML.format("0 0 10 0 10 10 0 10 0 0").encode())
        self.assertEqual(len(polys), 1)
        self.assertAlmostEqual(polys[0].area, 100.0, places=6)
        # te korte ring valt weg; ongeldig zelf-doorkruisend vlak wordt gerepareerd of weg
        self.assertEqual(kruising.gml_polygonen(self.GML.format("0 0").encode()), [])

    def test_kruis_scenario(self):
        from shapely.geometry import Polygon, box

        lagen = {
            "dichtbij.gml": {"frbrWork": "x",
                             "polygonen": [Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])]},
            "verweg.gml": {"frbrWork": "y",
                           "polygonen": [Polygon([(100, 100), (110, 100), (110, 110), (100, 110)])]},
        }
        raakt = kruising.kruis_scenario(box(0, 0, 5, 5), lagen)
        self.assertEqual(len(raakt), 1)
        self.assertEqual(raakt[0]["gio"], "dichtbij")
        self.assertAlmostEqual(raakt[0]["overlapM2"], 25.0, places=1)
        self.assertEqual(raakt[0]["objecten"], 1)

    def test_genomen_unie(self):
        from shapely.geometry import box

        vlak = {"type": "Feature",
                "properties": {"lokaal_id": "v1"},
                "geometry": {"type": "Polygon", "coordinates":
                             [[[2, 2], [8, 2], [8, 8], [2, 8], [2, 2]]]}}
        lagen_ids = {"begroeidterreindeel": {}, "onbegroeidterreindeel": {"v1": vlak}}
        scenario = {"allocatie": {"laag": "verhard", "genomen_ids": ["v1"], "n": 1}}
        unie, alloc = kruising.genomen_unie(scenario, lagen_ids, box(0, 0, 10, 10))
        self.assertAlmostEqual(unie.area, 36.0, places=6)
        self.assertEqual(alloc["laag"], "verhard")
        # zonder allocatie: (None, None) — geen gissing
        self.assertEqual(kruising.genomen_unie({}, lagen_ids, box(0, 0, 1, 1)), (None, None))


if __name__ == "__main__":
    unittest.main()

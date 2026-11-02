"""Pakketlader: referentiepakket laadt en valideert; fouten geven PackageError."""

import json
from pathlib import Path

import pytest

from core import catalog

POC_ROOT = Path(__file__).resolve().parents[1]


def _schrijf_pkg(tmp_path, manifest, tables):
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(tables, ensure_ascii=False), encoding="utf-8")
    geldige_golden = '{"scenarioId": "t1", "persona": "sanne", "expect": {"outcome": "paden", "transactions": [], "info": []}}\n'
    (pkg_dir / "golden" / "scenarios.jsonl").write_text(geldige_golden, encoding="utf-8")


def _basis_manifest():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "manifest.json").read_text(encoding="utf-8"))


def _basis_tables():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "decision-tables.json").read_text(encoding="utf-8"))


def test_referentiepakket_laadt():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    assert pkg.manifest["lifeEventCode"] == "GT-MOB-01"
    assert len(pkg.tables["rules"]) == 3
    assert len(pkg.golden) == 13


def test_onbekende_dienst_in_regel_faalt(tmp_path):
    manifest = _basis_manifest()
    tables = _basis_tables()
    tables["rules"][0]["then"]["transactions"] = ["bestaat-niet"]
    _schrijf_pkg(tmp_path, manifest, tables)
    with pytest.raises(catalog.PackageError, match="onbekende dienst"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_slot_zonder_vraag_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["contextSchema"]["slots"]["activity"].pop("vraag")
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="vraag"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_kapotte_json_geeft_packageerror(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text("{geen geldige json", encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="ongeldige JSON"):
        catalog.load_package(tmp_path, manifest["packageId"])


@pytest.mark.parametrize("pointer", ["decisionTables", "golden"])
def test_pointer_veld_ontbreekt_faalt(tmp_path, pointer):
    manifest = _basis_manifest()
    del manifest[pointer]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match=pointer):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_kapotte_golden_regel_geeft_packageerror(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(_basis_tables(), ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "golden" / "scenarios.jsonl").write_text('{"scenarioId": "g1"}\n{kapot\n', encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="ongeldige JSON-regel"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_gischeck_input_niet_adres_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["gisChecks"][0]["input"] = "activity"
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="input 'address'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_regel_zonder_when_faalt(tmp_path):
    manifest = _basis_manifest()
    tables = _basis_tables()
    del tables["rules"][0]["when"]
    _schrijf_pkg(tmp_path, manifest, tables)
    with pytest.raises(catalog.PackageError, match="'when'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_golden_regel_zonder_expect_faalt(tmp_path):
    manifest = _basis_manifest()
    pkg_dir = tmp_path / "packages" / manifest["packageId"]
    (pkg_dir / "golden").mkdir(parents=True)
    (pkg_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "decision-tables.json").write_text(json.dumps(_basis_tables(), ensure_ascii=False), encoding="utf-8")
    (pkg_dir / "golden" / "scenarios.jsonl").write_text('{"scenarioId": "g1", "persona": "sanne"}\n', encoding="utf-8")
    with pytest.raises(catalog.PackageError, match="'expect'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_authenticsources_hebben_doelbinding_en_dekken_slots():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    bronnen = {b["slot"]: b for b in pkg.manifest["authenticSources"]}
    authentieke_slots = {s for s, spec in pkg.manifest["contextSchema"]["slots"].items()
                         if spec.get("authenticSource")}
    assert set(bronnen) == authentieke_slots
    assert all(b["purpose"] for b in bronnen.values())


def test_authenticsource_zonder_purpose_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append({"slot": "activity", "source": "magia:bestaat-niet", "purpose": ""})
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="purpose"):
        catalog.load_package(tmp_path, manifest["packageId"])


@pytest.mark.parametrize("referentie", ["bestaat-niet:ergens", "magda:kenteken"])
def test_formulierbron_moet_slot_of_magda_met_pad_zijn(tmp_path, referentie):
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["formulier"][0]["bron"] = referentie
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="formulierbron"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_formulierregel_zonder_veld_faalt(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["formulier"][0]["veld"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="'veld'"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_dubbele_authenticsource_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append(dict(manifest["authenticSources"][0]))
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="meerdere entries"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_validatiesleutel_moet_in_formulier_zitten(tmp_path):
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["validaties"][0]["wanneer"] = {"bestaatniet": "Euro 4"}
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="validatie"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_documenteneisen_verplicht_voor_inzendingen(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["documenten"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="documenten"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_vereistauth_verplicht_en_true_voor_inzendingen(tmp_path):
    manifest = _basis_manifest()
    del manifest["services"]["ontheffing-lez"]["vereistAuth"]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="vereistAuth"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_ongeldig_minloa_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["minLoA"] = "super-duper"
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="minLoA"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_referentiepakket_vereist_substantial_voor_inzendingen():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    for service_id in ("ontheffing-lez", "ontheffing-autovrij"):
        assert pkg.manifest["services"][service_id]["minLoA"] == "substantial"


def test_dubbele_bron_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["authenticSources"].append({"slot": "timing", "source": "magda:kenteken", "purpose": "tweede doel"})
    manifest["contextSchema"]["slots"]["timing"]["authenticSource"] = "magda:kenteken"
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="bron"):
        catalog.load_package(tmp_path, manifest["packageId"])


def _schrijf_bronregister(tmp_path):
    (tmp_path / "fixtures" / "source").mkdir(parents=True, exist_ok=True)
    (tmp_path / "fixtures" / "source" / "source.meta.json").write_text(
        json.dumps({"bronnen": {"ivago-ophaalkalender": {"versie": "x"}}}), encoding="utf-8")


_DATACHECK = {"id": "afvalkalender", "dataset": "ivago-ophaalkalender",
              "input": "address", "outputs": ["afvalRest"], "unknownPolicy": "fallback"}


def test_datacheck_laadt_en_output_is_when_matchbaar(tmp_path):
    _schrijf_bronregister(tmp_path)
    manifest = _basis_manifest()
    manifest["dataChecks"] = [dict(_DATACHECK)]
    tables = _basis_tables()
    tables["rules"][0]["when"]["afvalRest"] = "maandag"
    _schrijf_pkg(tmp_path, manifest, tables)
    pkg = catalog.load_package(tmp_path, manifest["packageId"])
    assert pkg.manifest["dataChecks"][0]["id"] == "afvalkalender"


def test_datacheck_zonder_bronregister_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["dataChecks"] = [dict(_DATACHECK)]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="broncatalogus"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_datacheck_dataset_niet_geregistreerd_faalt(tmp_path):
    (tmp_path / "fixtures" / "source").mkdir(parents=True)
    (tmp_path / "fixtures" / "source" / "source.meta.json").write_text(
        json.dumps({"bronnen": {"andere-bron": {}}}), encoding="utf-8")
    manifest = _basis_manifest()
    manifest["dataChecks"] = [dict(_DATACHECK)]
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="staat niet in de broncatalogus"):
        catalog.load_package(tmp_path, manifest["packageId"])


@pytest.mark.parametrize("mutatie,match", [
    (lambda m: m["dataChecks"][0].pop("outputs"), "'outputs'"),
    (lambda m: m["dataChecks"][0].update(input="stad"), "onbekende input-slot"),
    (lambda m: m["dataChecks"][0].update(outputs=["applicantType"]), "output-botsing"),
    (lambda m: m["dataChecks"][0].update(unknownPolicy="boe"), "ongeldig unknownPolicy"),
])
def test_kapotte_datacheck_faalt(tmp_path, mutatie, match):
    _schrijf_bronregister(tmp_path)
    manifest = _basis_manifest()
    manifest["dataChecks"] = [dict(_DATACHECK)]
    mutatie(manifest)
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match=match):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_inzending_met_expliciet_lege_documentenlijst_laadt(tmp_path):
    """Bewonerskaart: authentieke bronnen dekken de bewijsstukken — een lege
    lijst is een bewuste pakketkeuze, de sleutel blijft verplicht."""
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["documenten"] = []
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    pkg = catalog.load_package(tmp_path, manifest["packageId"])
    assert pkg.manifest["services"]["ontheffing-lez"]["documenten"] == []


def test_submission_contract_leeg_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["submission"] = {"contract": "  "}
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="contract"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_gischeck_attribuut_leeg_faalt(tmp_path):
    manifest = _basis_manifest()
    manifest["gisChecks"][0]["attribuut"] = "  "
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    with pytest.raises(catalog.PackageError, match="attribuut"):
        catalog.load_package(tmp_path, manifest["packageId"])


def test_formulierbron_mag_naar_gisoutput_verwijzen(tmp_path):
    """Kot-melding: de kotzone-uitkomst van een gisCheck staat in de context
    (mét herkomst) en mag dus als formulierbron dienen."""
    manifest = _basis_manifest()
    manifest["services"]["ontheffing-lez"]["formulier"].append(
        {"veld": "zone-uitkomst", "bron": "slot:zoneLez"})
    _schrijf_pkg(tmp_path, manifest, _basis_tables())
    pkg = catalog.load_package(tmp_path, manifest["packageId"])
    bronnen = [r["bron"] for r in pkg.manifest["services"]["ontheffing-lez"]["formulier"]]
    assert "slot:zoneLez" in bronnen

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
    (pkg_dir / "golden" / "scenarios.jsonl").write_text("{}\n", encoding="utf-8")


def _basis_manifest():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "manifest.json").read_text(encoding="utf-8"))


def _basis_tables():
    return json.loads((POC_ROOT / "packages" / "gent-mobiliteit-ondernemer" / "decision-tables.json").read_text(encoding="utf-8"))


def test_referentiepakket_laadt():
    pkg = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer")
    assert pkg.manifest["lifeEventCode"] == "GT-MOB-01"
    assert len(pkg.tables["rules"]) == 3
    assert len(pkg.golden) == 6


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

"""Exit-test (F4, KPI-09/REP-01/02): configuratie-export + modelvrije
herleiding van de golden set; gesaboteerde export moet worden ontdekt."""

import json
from pathlib import Path

from core import catalog, exit_test, pipeline

POC_ROOT = Path(__file__).resolve().parents[1]


def test_export_bevat_pakket_en_fixtures(tmp_path):
    doel = exit_test.exporteer(POC_ROOT, "gent-mobiliteit-ondernemer", tmp_path / "export")
    pkg = catalog.load_package(doel, "gent-mobiliteit-ondernemer")
    assert pkg.manifest["packageId"] == "gent-mobiliteit-ondernemer"
    for naam in exit_test.BENODIGDE_FIXTURES:
        assert (doel / "fixtures" / naam).is_file(), naam
    assert len(pkg.golden) == 13


def test_herleiding_op_export_is_identiek():
    uitslag = exit_test.exit_test(POC_ROOT, "gent-mobiliteit-ondernemer")
    assert uitslag["geslaagd"] is True
    assert uitslag["identiek"] == uitslag["herleidingen"] == 13
    assert "geen model" in uitslag["modelsubstitutie"]


def test_gesaboteerde_export_wordt_ontdekt(tmp_path):
    doel = exit_test.exporteer(POC_ROOT, "gent-mobiliteit-ondernemer", tmp_path / "export")
    tabellen = json.loads((doel / "packages" / "gent-mobiliteit-ondernemer" / "decision-tables.json")
                          .read_text(encoding="utf-8"))
    tabellen["rules"][0]["then"]["transactions"] = []
    (doel / "packages" / "gent-mobiliteit-ondernemer" / "decision-tables.json").write_text(
        json.dumps(tabellen, ensure_ascii=False), encoding="utf-8")

    origineel, _ = pipeline.run_replay(POC_ROOT, "gent-mobiliteit-ondernemer", "sanne")
    herleid, _ = pipeline.run_replay(doel, "gent-mobiliteit-ondernemer", "sanne")
    assert exit_test.canonieke_uitslag(origineel) != exit_test.canonieke_uitslag(herleid)

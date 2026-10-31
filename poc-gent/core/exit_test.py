"""Exit-test (F4, KPI-09/REP-01/02): exporteer het pakket als configuratie
(config-is-data) en herleid de volledige golden set tegen de export — de
canonieke uitslagen moeten identiek zijn. Modelsubstitutie is in de
prototypefase modelvrij: de LLM zit alléén achter de seams en de replay komt
uit fixtures, dus "ander model, zelfde uitkomsten" is hier aantoonbaar als
"geen model, zelfde uitkomsten"; de productievariant (gateway + tweede model
op dezelfde golden set) volgt bij de LLM-poot."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from core import catalog, pipeline

BENODIGDE_FIXTURES = (
    "personas.json", "magda.json", "wallets.json", "identiteiten.json",
    "documenten.json", "gis-zones.geojson", "addresses.json", "injecties.json",
)

MODEL_SUBSTITUTIE_NOTITIE = (
    "Replay is modelvrij (seams S1/S2 komen uit persona-fixtures): 'ander model, "
    "zelfde uitkomsten' is in de prototypefase aantoonbaar als 'geen model, zelfde "
    "uitkomsten'; de productievariant (gateway + tweede model op dezelfde golden "
    "set) volgt bij de LLM-poot."
)


def exporteer(poc_root: Path, package_id: str, doel: Path) -> Path:
    """Kopieer het pakket + de run-benodigde fixtures naar een nieuwe root:
    de machine-leesbare configuratie-export (REP-01)."""
    (doel / "packages").mkdir(parents=True)
    shutil.copytree(poc_root / "packages" / package_id, doel / "packages" / package_id)
    (doel / "fixtures").mkdir()
    for naam in BENODIGDE_FIXTURES:
        shutil.copy2(poc_root / "fixtures" / naam, doel / "fixtures" / naam)
    if (poc_root / "fixtures" / "source").is_dir():
        shutil.copytree(poc_root / "fixtures" / "source", doel / "fixtures" / "source")
    return doel


def canonieke_uitslag(run: dict) -> dict:
    """Vergelijkbare uitslag zonder vluchtige velden (runId/tijdstempels):
    routing, status en ontvangstbewijzen samen."""
    transactie = run["transaction"]
    return {"outcome": transactie["routing"]["outcome"],
            "paths": transactie["routing"]["paths"],
            "status": transactie["status"],
            "ontvangst": transactie["submission"]["ontvangst"]["transacties"]}


def exit_test(poc_root: Path, package_id: str = "gent-mobiliteit-ondernemer") -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        doel = exporteer(poc_root, package_id, Path(tmp) / "export")
        pkg = catalog.load_package(doel, package_id)
        identiek = 0
        for scenario in pkg.golden:
            origineel, _ = pipeline.run_replay(poc_root, package_id, scenario["persona"],
                                               scenario.get("overrideSlots"))
            herleid, _ = pipeline.run_replay(doel, package_id, scenario["persona"],
                                             scenario.get("overrideSlots"))
            if canonieke_uitslag(origineel) == canonieke_uitslag(herleid):
                identiek += 1
        return {"geslaagd": identiek == len(pkg.golden),
                "herleidingen": len(pkg.golden), "identiek": identiek,
                "exportBevat": [f"packages/{package_id}/"] + [f"fixtures/{n}" for n in BENODIGDE_FIXTURES],
                "modelsubstitutie": MODEL_SUBSTITUTIE_NOTITIE}

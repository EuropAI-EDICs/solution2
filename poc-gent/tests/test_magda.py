"""Magda-mock in MCP-vorm: toolregister uit het manifest, raadpleging alléén
onder de gedeclareerde doelbinding (FR-10, once-only INT-02)."""

from pathlib import Path

import pytest

from adapters import magda_mock
from core import catalog

POC_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = catalog.load_package(POC_ROOT, "gent-mobiliteit-ondernemer").manifest


def test_toolregister_volgt_het_manifest():
    tools = magda_mock.beschikbare_tools(MANIFEST)
    assert {"tool": "magda:kenteken", "purpose": MANIFEST["authenticSources"][0]["purpose"]} in tools


def test_raadpleeg_levert_record_bij_correcte_doelbinding():
    record = magda_mock.raadpleeg(MANIFEST, "magda:kenteken", MANIFEST["authenticSources"][0]["purpose"],
                                  POC_ROOT, "sanne")
    assert record["kenteken"] == "1-ABC-123"
    assert record["euroklasse"] == "Euro 6"


def test_raadpleeg_met_verkeerde_doelbinding_wordt_geweigerd():
    with pytest.raises(magda_mock.MagdaPurposeError):
        magda_mock.raadpleeg(MANIFEST, "magda:kenteken", "doel die niet gedeclareerd is", POC_ROOT, "sanne")


def test_raadpleeg_zonder_record_faalt_duidelijk():
    with pytest.raises(KeyError):
        magda_mock.raadpleeg(MANIFEST, "magda:kenteken", MANIFEST["authenticSources"][0]["purpose"],
                             POC_ROOT, "maria")

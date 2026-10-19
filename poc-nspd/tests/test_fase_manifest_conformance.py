"""NSPD fase-manifest: conformance tegen het fundament en de eigen registers.

De tweede pilot bewijst het §1-succescriterium: alleen manifest + register-
verwijzingen + tests, engine onaangetast. Offline (geen netwerk, geen engine-run).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.append(str(REPO / "poc-fundament"))  # brug-conventie: append, nooit insert

from fundament.manifest import load_manifest  # noqa: E402

BEKENDE_ROLLEN = {"intake", "normspecialist", "formalizer", "geospecialist",
                  "critic", "explainer"}


@pytest.fixture(scope="module")
def manifest():
    return load_manifest(ROOT / "fase-manifest.json")


def _tasks(manifest, fase_prefix):
    for ph in manifest["phases"]:
        if ph["id"].startswith(fase_prefix):
            return ph.get("tasks") or []
    return []


def test_manifest_valideert_tegen_het_fundamentschema(manifest):
    assert manifest["poc"] == "nspd-tracks"
    assert [p["id"] for p in manifest["phases"]] == [
        "F0-intake", "F1-normanalyse", "F2-formalisering",
        "F3-geodoorrekening", "F4-synthese"]


def test_rollen_zijn_bekende_deep_agents_agenten(manifest):
    for ph in manifest["phases"]:
        for rol in str(ph["agent"]["role"]).lower().split("+"):
            assert rol.strip() in BEKENDE_ROLLEN, ph["id"]


def test_corpus_taken_komen_overeen_met_de_werkelijke_bestanden(manifest):
    norm_bestanden = sorted(p.stem[len("normcards-"):]
                            for p in (ROOT / "corpus").glob("normcards-*-*.json")
                            if "rejected" not in p.name)
    f1_ids = {t["id"][len("normcards-"):] for t in _tasks(manifest, "F1-")}
    assert f1_ids == set(norm_bestanden)
    rules_bestanden = sorted(p.stem[len("formal-rules-"):]
                             for p in (ROOT / "corpus").glob("formal-rules-*.json"))
    f2_ids = {t["id"][len("formal-rules-"):] for t in _tasks(manifest, "F2-")}
    assert f2_ids == set(rules_bestanden)


def test_corpus_refs_resolven_naar_bestaande_bestanden(manifest):
    for t in _tasks(manifest, "F1-") + _tasks(manifest, "F2-"):
        ref = t["tool"]["ref"]
        assert ref.startswith("corpus:"), ref
        assert (ROOT / "corpus" / (ref[len("corpus:"):] + ".json")).is_file(), ref


def test_zone_taken_dekken_alle_corpus_paren(manifest):
    paren = sorted(p.stem[len("normcards-"):]
                   for p in (ROOT / "corpus").glob("normcards-*-*.json")
                   if "rejected" not in p.name)
    verwacht = {f"zones-{p.split('-', 1)[1]}-{p.split('-', 1)[0]}" for p in paren}
    assert {t["id"] for t in _tasks(manifest, "F3-")} == verwacht


def test_elke_track_heeft_gepinde_bronnen_in_het_bronregister(manifest):
    bronnen = json.loads((ROOT / "data" / "sources.json").read_text(encoding="utf-8"))
    tracks_in_register = {t for b in bronnen["sources"] for t in (b.get("tracks") or [])}
    # 'zon' heeft geen track-specifieke pin in het bronregister; de
    # zone-algebra draait daar op wildcard-bronnen (tracks: ["*"],
    # bv. pdok-bestuurlijke-gemeenten, pdok-kadastrale-percelen).
    ZONDER_SPECIEKE_PIN = {"zon"}
    for t in _tasks(manifest, "F3-"):
        track = t["id"][len("zones-"):].rsplit("-", 1)[0]
        assert (track in tracks_in_register
                or track in ZONDER_SPECIEKE_PIN), track


def test_matrix_render_is_deterministisch(manifest):
    from fundament.matrix import render_matrix
    twee = {render_matrix(manifest), render_matrix(manifest)}
    assert len(twee) == 1
    md = twee.pop()
    for fase in ("F0-intake", "F1-normanalyse", "F2-formalisering",
                 "F3-geodoorrekening", "F4-synthese"):
        assert fase in md

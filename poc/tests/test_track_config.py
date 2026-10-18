"""track_config: declaratieve track-lading (nspd-port fase 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline import track_config  # noqa: E402

TRACKS13 = ["wind", "zon", "bos", "water", "bodem", "mobiliteit", "landschap",
            "landbouw", "wonen", "werken", "recreatie", "biomassa", "energietoets"]


def test_load_track_geeft_alle_velden_en_callable_limitations():
    cfg = track_config.load_track("wind")
    for key in ("shard", "ledger", "report_title", "decision_table_id",
                "decision_table_title", "prov_namespace", "headline_note"):
        assert key in cfg, key
    assert callable(cfg["limitations"])


def test_limitations_templates_gelijk_aan_oude_lambdas():
    """Vergelijkt gerenderde limitations van de templates met de oorspronkelijke
    lambda-uitkomsten (vast leguster: vaste cov). De 13 lambdas zijn in task 2
    verwijderd; deze asserts zijn tegen de handmatig omgezette templates."""
    # zon/bos-templates bevatten ook {rejected} (run.py-lambdas gebruikten
    # cov['rejected']) — daarom hoort rejected in de vaste cov.
    cov = {"ambiguous": 13, "output_rules": 24, "formalized": 11, "rejected": 3}
    # wind-voorbeeld letterlijk uit run.py:285 (lambda-output met deze cov):
    rendered = track_config.load_track("wind")["limitations"](cov, [])
    assert rendered[1].startswith("13 of 24 rules are intentionally 'ambiguous'")
    assert "consumed only the 11 formalized rules." in rendered[1]
    # zon gebruikt cov['rejected'] — placeholder moet rendert (geen KeyError):
    zon_rendered = track_config.load_track("zon")["limitations"](cov, [])
    assert "11 formalized and 3 rejected as non-binding" in zon_rendered[1]


def test_load_enrichment_en_templates_omvatten_alle_84_ids():
    enr = track_config.load_enrichment()
    tpl = track_config.load_templates()
    assert len(enr) >= 84 and len(tpl) >= 84
    assert set(enr) == set(tpl)


def test_load_zone_sources_gelijk_aan_oude_dict():
    zs = track_config.load_zone_sources()
    assert "gebied_windenergie" in zs and "natura_2000" in zs
    assert zs["gebied_windenergie"]["sourceId"] == "agrest-ov-gebied-windenergie"


def test_corpus_regenereert_byte_identiek():
    """De declaratieve tracks moeten byte-identieke corpus-artefacten
    opleveren (nspd-port gate, spec §3): dezelfde serialisatie als
    agents.generate_corpus, nu voor alle 13 tracks."""
    from pipeline import agents

    corpus = ROOT / "corpus"
    for track in TRACKS13:
        analyst = agents.NormAnalyst()
        formalizer = agents.NormFormalizer()
        cards = analyst.read(corpus / f"evidence-{track}.json")
        rules = formalizer.formalize(cards)
        expected_cards = json.dumps(
            [c.to_dict() for c in cards], ensure_ascii=False, indent=2) + "\n"
        expected_rules = json.dumps(
            [r.to_dict() for r in rules], ensure_ascii=False, indent=2) + "\n"
        assert (corpus / f"normcards-{track}.json").read_text(encoding="utf-8") == expected_cards, track
        assert (corpus / f"formalrules-{track}.json").read_text(encoding="utf-8") == expected_rules, track

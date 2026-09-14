from __future__ import annotations

import json
from pathlib import Path

import pytest

from services.common.schema import validate_instance
from services.process_adapter.jobs import create_job
from services.recipe_runner import run_recipe
from services.run_annex import build_run_annex, render_annex_markdown

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class InProcessClient:
    """ProcessClient stand-in that executes locally in-process (real jobs)."""

    def execute(self, process_id, inputs, backend="local"):
        return create_job(process_id, inputs, backend=backend)


@pytest.fixture
def execution():
    return run_recipe(
        "beleidskompas-omgevingsanalyse",
        {
            "aoi": json.loads((EXAMPLES / "aoi.geojson").read_text()),
            "layerAUri": f"file://{EXAMPLES / 'layer-a.geojson'}",
            "layerBUri": f"file://{EXAMPLES / 'layer-b.geojson'}",
        },
        process_client=InProcessClient(),
    )


def test_annex_schema_valid_and_deterministic(execution):
    a1 = build_run_annex([execution])
    a2 = build_run_annex([json.loads(json.dumps(execution))])
    assert a1 == a2
    validate_instance(a1, "run-annex.schema.json")
    assert a1["runs"][0]["recipeId"] == "beleidskompas-omgevingsanalyse"


def test_annex_carries_job_ids_and_prov(execution):
    annex = build_run_annex([execution])
    steps = annex["runs"][0]["steps"]
    assert len(steps) == 4
    for s in steps:
        assert s["jobId"]
        assert "startedAtTime" in s["prov"]


def test_annex_includes_validation_report_when_present(execution):
    execution["validation_report"] = {"verdict": "pass"}
    annex = build_run_annex([execution])
    assert annex["runs"][0]["validationReport"] == {"verdict": "pass"}


def test_markdown_renders_every_job(execution):
    annex = build_run_annex([execution])
    md = render_annex_markdown(annex)
    assert "beleidskompas-omgevingsanalyse" in md
    for s in annex["runs"][0]["steps"]:
        assert s["jobId"] in md


def test_cli_build_run_annex(tmp_path, execution):
    from services.cli import main

    exec_file = tmp_path / "exec.json"
    exec_file.write_text(json.dumps(execution))
    out = tmp_path / "annex.md"
    rc = main(["build-run-annex", str(exec_file), "--out", str(out)])
    assert rc == 0
    assert "beleidskompas-omgevingsanalyse" in out.read_text()

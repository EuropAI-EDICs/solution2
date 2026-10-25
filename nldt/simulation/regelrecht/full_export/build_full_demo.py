"""DemoBuilder — instrument-browser + coverage in regelrecht-demo.html."""
from __future__ import annotations

import json
import pathlib
import sys
from typing import Any, Dict, List

import yaml

import paths

REGELRECHT_DIR = paths.DIR.parent
ROOT = paths.ROOT
sys.path.insert(0, str(REGELRECHT_DIR))
import reference_engine  # noqa: E402

SKIP_CAP = {"utrecht": {"5.3"}, "eindhoven": {"10.2"}}
CAP = 20


def _load_run(poc: str) -> dict:
    name = (
        "utrecht-wind-art5.3.json"
        if poc == "utrecht"
        else "eindhoven-bp2op-art10.2.json"
    )
    return json.loads((REGELRECHT_DIR / "runs" / name).read_text(encoding="utf-8"))


def _load_report(poc: str) -> dict:
    return json.loads(
        (paths.OUT / f"{poc}-formalization-report.json").read_text(encoding="utf-8")
    )


def _load_yaml(poc: str) -> dict:
    cvdr = paths.INSTRUMENTS[poc]["cvdr"].lower()
    return yaml.safe_load((paths.OUT / f"{poc}-{cvdr}.yaml").read_text(encoding="utf-8"))


def _build_index(poc: str, report: dict, doc: dict) -> List[dict]:
    titles = {a["number"]: a.get("title") or "" for a in []}
    # titles from splitter not in yaml — use report + yaml text snippet
    text_by = {a["number"]: a.get("text", "")[:120] for a in doc.get("articles", [])}
    mr_nums = {
        a["number"]
        for a in doc.get("articles", [])
        if a.get("machine_readable")
    }
    index = []
    for row in report["articles"]:
        num = row["number"]
        index.append(
            {
                "number": num,
                "status": row["status"],
                "hasMachineReadable": num in mr_nums,
                "title": text_by.get(num, "")[:80],
                "reason": row.get("reason", ""),
            }
        )
    return index


def _synthetic_inputs(execution: dict) -> Dict[str, Any]:
    inputs: Dict[str, Any] = {}
    for p in execution.get("parameters") or []:
        t = p.get("type")
        if t == "boolean":
            inputs[p["name"]] = False
        elif t == "number":
            inputs[p["name"]] = 0
        else:
            raise ValueError(f"unsupported param type {t}")
    for p in execution.get("input") or []:
        t = p.get("type", "boolean")
        if t != "boolean":
            raise ValueError(f"unsupported input type {t}")
        inputs[p["name"]] = True
    return inputs


def _cap_cases(poc: str, doc: dict, report: dict) -> List[dict]:
    skip = SKIP_CAP.get(poc, set())
    formalized = [
        r["number"]
        for r in sorted(report["articles"], key=lambda r: r["number"])
        if r["status"] == "formalized" and r["number"] not in skip
    ]
    by_art = {a["number"]: a for a in doc.get("articles", [])}
    cases: List[dict] = []
    for num in formalized:
        if len(cases) >= CAP:
            break
        art = by_art.get(num)
        if not art or not art.get("machine_readable"):
            continue
        execution = art["machine_readable"]["execution"]
        try:
            inputs = _synthetic_inputs(execution)
            result = reference_engine.evaluate(execution, inputs)
        except Exception:
            continue
        cases.append(
            {
                "id": f"{poc}-cap-{num}",
                "execution": execution,
                "inputs": inputs,
                "expectedOutputs": result["outputs"],
                "trace": result["trace"],
            }
        )
    return cases


def build_demo(stamp: str, out_html: "pathlib.Path | None" = None) -> None:
    """Fill template placeholders and write the demo page.

    Default target is nldt/simulation/regelrecht-demo.html; pass ``out_html`` to
    write elsewhere (e.g. a temp dir) without touching the committed artefact.
    """
    # Ensure legacy runs exist (16 golden base)
    runs = {poc: _load_run(poc) for poc in ("utrecht", "eindhoven")}
    reports = {poc: _load_report(poc) for poc in ("utrecht", "eindhoven")}
    docs = {poc: _load_yaml(poc) for poc in ("utrecht", "eindhoven")}
    indexes = {
        poc: _build_index(poc, reports[poc], docs[poc]) for poc in ("utrecht", "eindhoven")
    }

    base_golden: List[dict] = []
    for poc in ("utrecht", "eindhoven"):
        run = runs[poc]
        execution = run["machineReadable"]["execution"]
        for case in run["demoCases"]:
            base_golden.append(
                {
                    "id": case["id"],
                    "execution": execution,
                    "inputs": case["inputs"],
                    "expectedOutputs": case["expectedOutputs"],
                    "trace": case["trace"],
                }
            )
    assert len(base_golden) == 16, f"expected 16 base golden, got {len(base_golden)}"

    cap: List[dict] = []
    for poc in ("utrecht", "eindhoven"):
        cap.extend(_cap_cases(poc, docs[poc], reports[poc]))
    golden = base_golden + cap

    # Embed articles MR lookup for browser (formalized only, capped metadata)
    article_payload = {}
    for poc in ("utrecht", "eindhoven"):
        article_payload[poc] = {
            a["number"]: {
                "text": a.get("text", ""),
                "machineReadable": a.get("machine_readable"),
                "url": a.get("url", ""),
            }
            for a in docs[poc].get("articles", [])
        }

    template = (REGELRECHT_DIR / "regelrecht-demo.template.html").read_text(
        encoding="utf-8"
    )
    engine_js = (REGELRECHT_DIR / "engine" / "mini-engine.js").read_text(encoding="utf-8")
    page = (
        template.replace("__RUN_UTRECHT__", json.dumps(runs["utrecht"], ensure_ascii=False))
        .replace("__RUN_EINDHOVEN__", json.dumps(runs["eindhoven"], ensure_ascii=False))
        .replace("__GOLDEN__", json.dumps(golden, ensure_ascii=False))
        .replace("__ENGINE_JS__", engine_js)
        .replace("__BUILD_STAMP__", stamp)
        .replace("__INDEX_UTRECHT__", json.dumps(indexes["utrecht"], ensure_ascii=False))
        .replace("__INDEX_EINDHOVEN__", json.dumps(indexes["eindhoven"], ensure_ascii=False))
        .replace(
            "__REPORT_UTRECHT__",
            json.dumps(reports["utrecht"]["counts"], ensure_ascii=False),
        )
        .replace(
            "__REPORT_EINDHOVEN__",
            json.dumps(reports["eindhoven"]["counts"], ensure_ascii=False),
        )
        .replace(
            "__ARTICLES_UTRECHT__",
            json.dumps(article_payload["utrecht"], ensure_ascii=False),
        )
        .replace(
            "__ARTICLES_EINDHOVEN__",
            json.dumps(article_payload["eindhoven"], ensure_ascii=False),
        )
        .replace("__BASE_GOLDEN_COUNT__", "16")
        .replace("__CAP_GOLDEN_COUNT__", str(len(cap)))
    )
    for ph in (
        "__INDEX_UTRECHT__",
        "__INDEX_EINDHOVEN__",
        "__REPORT_UTRECHT__",
        "__REPORT_EINDHOVEN__",
        "__ARTICLES_UTRECHT__",
        "__ARTICLES_EINDHOVEN__",
        "__RUN_UTRECHT__",
        "__RUN_EINDHOVEN__",
        "__GOLDEN__",
        "__ENGINE_JS__",
        "__BUILD_STAMP__",
        "__BASE_GOLDEN_COUNT__",
        "__CAP_GOLDEN_COUNT__",
    ):
        if ph in page:
            raise SystemExit(f"placeholder niet vervangen: {ph}")

    if out_html is None:
        out_html = REGELRECHT_DIR.parent / "regelrecht-demo.html"
    out_html.write_text(page, encoding="utf-8")
    print(f"OK demo {out_html} golden={len(golden)} (16+{len(cap)})")

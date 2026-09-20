from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

from services.process_adapter.handlers import execute_local
from services.process_adapter.jobs import create_job
from services.recipe_runner import run_recipe


def _parse_inputs(raw: list[str]) -> dict:
    """Parse ``key=value`` inputs into a job input dict.

    Inline JSON (``{``/``[``) is parsed directly; ``file://`` values are
    loaded as JSON from the referenced file (same idiom as
    ``handlers._load_source``), so list/dict inputs written to request
    files by e.g. ``poc/pipeline/h3step.py`` reach the process as real
    lists/dicts. A ``file://`` target that is missing or not valid JSON
    passes through as the original string — consumers such as
    ``fetch-features`` resolve file URIs themselves.
    """
    out = {}
    for item in raw:
        key, _, value = item.partition("=")
        if value.startswith("{") or value.startswith("["):
            out[key] = json.loads(value)
        elif value.startswith("file://"):
            try:
                with Path(urlparse(value).path).open(encoding="utf-8") as f:
                    out[key] = json.load(f)
            except (OSError, json.JSONDecodeError):
                out[key] = value
        else:
            out[key] = value
    return out


def cmd_run_recipe(args: argparse.Namespace) -> int:
    inputs = _parse_inputs(args.input or [])
    if args.aoi_file:
        with Path(args.aoi_file).open(encoding="utf-8") as f:
            inputs.setdefault("aoi", json.load(f))
    result = run_recipe(args.recipe_id, inputs)
    print(json.dumps(result, indent=2))
    return 0


def cmd_run_local_process(args: argparse.Namespace) -> int:
    inputs = _parse_inputs(args.input or [])
    job = create_job(args.process_id, inputs, backend=args.backend)
    print(json.dumps(job, indent=2))
    return 0


def _load_optional_json(path: str | None) -> dict | None:
    if not path:
        return None
    with Path(path).open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def cmd_publish_recipe(args: argparse.Namespace) -> int:
    from services.common.schema import load_recipe
    from services.marketplace_publish import publish_recipe

    recipe = load_recipe(args.recipe_id)
    result = publish_recipe(
        recipe,
        categories=args.category or ["urn:ngsi-ld:category:processes"],
        licence=args.licence,
        validation_report=_load_optional_json(args.validation_report),
        provenance=_load_optional_json(args.provenance),
    )
    print(json.dumps(result, indent=2))
    return 0


def cmd_export_context(args: argparse.Namespace) -> int:
    from services.common.schema import validate_instance
    from services.context3d.export_import import export_from_execution, save_context
    from pathlib import Path

    with Path(args.execution_file).open(encoding="utf-8") as f:
        execution = json.load(f)
    doc = export_from_execution(execution, run_id=args.run_id, title=args.title)
    validate_instance(doc, "web3d-context.schema.json")
    out_dir = Path(args.output_dir or "data/context3d")
    path = save_context(doc, out_dir)
    print(json.dumps({"storedAt": str(path), "id": doc["id"]}, indent=2))
    return 0


def cmd_build_run_annex(args: argparse.Namespace) -> int:
    from services.common.schema import validate_instance
    from services.run_annex import build_run_annex, render_annex_markdown

    executions = []
    for path in args.execution_file:
        with Path(path).open(encoding="utf-8") as f:
            executions.append(json.load(f))
    annex = build_run_annex(executions)
    validate_instance(annex, "run-annex.schema.json")
    md = render_annex_markdown(annex)
    if args.out:
        Path(args.out).write_text(md, encoding="utf-8")
    print(json.dumps(annex, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="nLDT CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_recipe = sub.add_parser("run-recipe", help="Execute a recipe end-to-end")
    p_recipe.add_argument("recipe_id")
    p_recipe.add_argument("--input", action="append", help="key=value or key={json}")
    p_recipe.add_argument("--aoi-file", help="GeoJSON AOI file")
    p_recipe.set_defaults(func=cmd_run_recipe)

    p_proc = sub.add_parser("run-process", help="Execute single process locally")
    p_proc.add_argument("process_id")
    p_proc.add_argument("--input", action="append")
    p_proc.add_argument("--backend", default="local")
    p_proc.set_defaults(func=cmd_run_local_process)

    p_pub = sub.add_parser("publish-recipe", help="Publish recipe to EU LDT Marketplace")
    p_pub.add_argument("recipe_id")
    p_pub.add_argument("--category", action="append")
    p_pub.add_argument("--licence", default="EUPL-1.2")
    p_pub.add_argument(
        "--validation-report",
        help="JSON ValidationReport to attach to the Marketplace payload",
    )
    p_pub.add_argument(
        "--provenance",
        help="JSON PROV bundle to attach to the Marketplace payload",
    )
    p_pub.set_defaults(func=cmd_publish_recipe)

    p_ctx = sub.add_parser("export-context", help="Export Web3DContext from execution JSON")
    p_ctx.add_argument("execution_file")
    p_ctx.add_argument("--run-id")
    p_ctx.add_argument("--title")
    p_ctx.add_argument("--output-dir")
    p_ctx.set_defaults(func=cmd_export_context)

    p_annex = sub.add_parser(
        "build-run-annex", help="Build S9 run annex (JSON + Markdown) from execution JSON files"
    )
    p_annex.add_argument("execution_file", nargs="+")
    p_annex.add_argument("--out", help="Write Markdown annex to this path")
    p_annex.set_defaults(func=cmd_build_run_annex)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

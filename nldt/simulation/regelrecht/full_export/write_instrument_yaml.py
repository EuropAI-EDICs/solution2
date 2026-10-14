"""RegelRechtWriter — articles + formalizations → 1 instrument YAML + report."""
from __future__ import annotations

import json
import pathlib
import re
from typing import Dict, List, Literal

import yaml
from jsonschema import Draft202012Validator

import paths
from formalize_to_rr import ArticleFormalization
from split_cvdr_html import Article

REGELRECHT_SCHEMA = (
    paths.DIR.parent / "schema" / "regelrecht-v0.7.1.schema.json"
)
REPORT_SCHEMA = paths.DIR / "formalization-report.schema.json"


def _slug(title: str) -> str:
    s = title.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "", s)


def _build_doc(
    poc: Literal["utrecht", "eindhoven"],
    articles: List[Article],
    formalizations: Dict[str, ArticleFormalization],
) -> dict:
    meta = paths.INSTRUMENTS[poc]
    doc: dict = {
        "$schema": (
            "https://raw.githubusercontent.com/MinBZK/regelrecht/refs/heads/main/"
            "schema/v0.7.1/schema.json"
        ),
        "$id": _slug(meta["title"]),
        "name": meta["title"],
        "regulatory_layer": meta["regulatory_layer"],
        "publication_date": meta["publication_date"],
        "valid_from": meta["valid_from"],
        "cvdr_id": meta["cvdr"],
        "officiele_titel": meta["title"],
        "organisation": meta["organisation"],
        "url": meta["url"],
        "articles": [],
    }
    if "provincie_code" in meta:
        doc["provincie_code"] = meta["provincie_code"]
    if "gemeente_code" in meta:
        doc["gemeente_code"] = meta["gemeente_code"]

    for art in articles:
        form = formalizations.get(art["number"]) or {}
        entry: dict = {
            "number": art["number"],
            "text": art["text"],
            "url": art["url"],
        }
        if form.get("status") == "formalized" and form.get("machineReadable"):
            entry["machine_readable"] = form["machineReadable"]
        doc["articles"].append(entry)
    return doc


def _validate_or_exit(doc: dict, schema_path: pathlib.Path, label: str) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
    if errs:
        lines = []
        for e in errs[:5]:
            path = "/".join(str(p) for p in e.path) or "(root)"
            lines.append(f"{path}: {e.message}")
        raise SystemExit(f"{label} schema-ongeldig:\n" + "\n".join(lines))


def write_instrument_yaml(
    poc: Literal["utrecht", "eindhoven"],
    articles: List[Article],
    formalizations: Dict[str, ArticleFormalization],
    stamp: str,
    report: dict | None = None,
) -> pathlib.Path:
    """Write out/{poc}-cvdr{id}.yaml; optionally write/validate formalization report."""
    paths.OUT.mkdir(parents=True, exist_ok=True)
    meta = paths.INSTRUMENTS[poc]
    cvdr_lower = meta["cvdr"].lower()
    out_path = paths.OUT / f"{poc}-{cvdr_lower}.yaml"
    doc = _build_doc(poc, articles, formalizations)
    _validate_or_exit(doc, REGELRECHT_SCHEMA, out_path.name)

    # Prefer block style for article text
    class _Dumper(yaml.SafeDumper):
        pass

    def _str_representer(dumper, data):
        if "\n" in data:
            return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return dumper.represent_scalar("tag:yaml.org,2002:str", data)

    _Dumper.add_representer(str, _str_representer)

    out_path.write_text(
        yaml.dump(
            doc,
            Dumper=_Dumper,
            allow_unicode=True,
            sort_keys=False,
            width=1000,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )

    if report is not None:
        report = dict(report)
        report["generatedAt"] = stamp
        _validate_or_exit(report, REPORT_SCHEMA, "formalization-report")
        (paths.OUT / f"{poc}-formalization-report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return out_path

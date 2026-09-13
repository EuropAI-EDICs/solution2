#!/usr/bin/env python3
"""PoC-4 Q&A — grounded Q&A over een canonieke Breda vijf-waardenscan-run.

GenAI-seam (S4-analoog): de vraag wordt (deterministisch of door een LLM)
een schema-gevalideerd ScanQuery-voorstel; een deterministische runner leest
alleen value-scan.json; de narratie (optioneel LLM) moet door de numerieke
grounding-gate — anders afkeuring + deterministische fallback. LLM's
voorstellen, de pipeline beslist.

    nldt/.venv/bin/python poc-breda/qa_run.py --run poc-breda/runs/<ts>-breda-scan \
        --question "waarom scoort Belcrum laag op ruimtelijke waarde?"

    --demo                  golden-set over de run (deterministisch, offline)
    --asker llm             NL→ScanQuery via LDT_SCENARIO_LLM_ENDPOINT
    --narrator llm          prosa via LLM, achter de gate (fallback bij afkeuring)
    --interactive           read questions from stdin until stop
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
POC_ROOT = ROOT.parent / "poc"
for p in (str(POC_ROOT), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from breda import qa  # noqa: E402

GOLDEN_QUESTIONS = [
    "why does Belcrum score low on spatial value?",
    "which neighbourhoods score highest on democratic value?",
    "top 3 neighbourhoods unused roof potential",
    "how does Ginneken score on all values?",
    "which neighbourhoods have the most heat attention?",
    "what is the median on social value?",
    "waarom scoort Belcrum laag op ruimtelijke waarde?",  # bilingual parser: NL blijft werken
]


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_scan(run_dir: Path) -> dict:
    path = run_dir / "value-scan.json"
    if not path.exists():
        raise qa.QAError(f"no value-scan.json in {run_dir} (run poc-breda/run.py first)")
    return json.loads(path.read_text(encoding="utf-8"))


def answer_question(
    scan: dict,
    question: str,
    *,
    asker: str = "auto",
    narrator: str = "auto",
    out_dir: Path | None = None,
    llm_asker=None,
    llm_narrator=None,
) -> int:
    """Beantwoordt één vraag; schrijft artifacts; 0=beantwoord, 1=onthouden."""
    rejection = None
    query = None
    if asker == "llm":
        asker_obj = llm_asker or qa.LLMAsker(scan)
        query, rejection = asker_obj.propose(question)
    else:
        query = qa.parse_question(question, scan)

    if query is None:
        if rejection is None:
            rejection = {
                "reason": "deterministische parser kan de vraag niet op het "
                          "ScanQuery-contract mappen (cite-or-abstain)",
            }
        record = {
            "question": question,
            "rejectedAt": _now_iso(),
            "asker": asker,
            **rejection,
        }
        if out_dir:
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / "query-rejected.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8"
            )
        print(f"[abstained] {rejection['reason']}")
        return 1

    result = qa.execute_query(query, scan)
    deterministisch = qa.deterministic_answer(result, scan)

    answer = deterministisch
    narration_rejected = None
    if narrator == "llm":
        narrator_obj = llm_narrator or qa.LLMNarrator()
        try:
            voorstel = narrator_obj.narrate(result, deterministisch)
            schendingen = qa.check_answer_grounding(voorstel, result, scan)
            if schendingen:
                narration_rejected = {
                    "violations": schendingen,
                    "raw": voorstel[:800],
                    "fallback": "deterministisch",
                }
            else:
                answer = voorstel
        except qa.QAError as exc:
            narration_rejected = {"violations": [str(exc)], "fallback": "deterministisch"}

    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "question": question,
            "answeredAt": _now_iso(),
            "asker": asker,
            "narrator": narrator,
            "query": query,
            "mode": result["mode"],
            "rows": result["rows"],
            "answer": answer,
            **({"narrationRejected": narration_rejected}
               if narration_rejected else {}),
        }
        (out_dir / "answer.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        (out_dir / "answer.md").write_text(
            answer + "\n", encoding="utf-8"
        )

    print(answer)
    if narration_rejected:
        print(f"[narration rejected → deterministic fallback] "
              f"{'; '.join(narration_rejected['violations'])}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True,
                    help="canonical run dir (contains value-scan.json)")
    ap.add_argument("--question", default=None, help="one question (Dutch or English)")
    ap.add_argument("--demo", action="store_true",
                    help="run the golden-set questions (deterministic, offline)")
    ap.add_argument("--asker", choices=["auto", "llm"], default="auto")
    ap.add_argument("--narrator", choices=["auto", "llm"], default="auto")
    ap.add_argument("--interactive", action="store_true",
                    help='read questions from stdin until stop')
    ap.add_argument("--out", type=Path, default=None,
                    help="artifacts dir (default: <run>/qa/)")
    args = ap.parse_args(argv)

    scan = load_scan(args.run)
    out_dir = args.out or (args.run / "qa")

    if args.demo:
        codes = []
        for v in GOLDEN_QUESTIONS:
            print("=" * 78)
            codes.append(
                answer_question(scan, v, asker=args.asker, narrator=args.narrator,
                                out_dir=out_dir / _slug_q(v))
            )
        print("=" * 78)
        print(f"golden set: {sum(1 for c in codes if c == 0)}/{len(codes)} answered")
        return 0

    if args.interactive:
        while True:
            try:
                vraag = input("question> ").strip()
            except EOFError:
                break
            if not vraag or vraag.lower() in {"stop", "quit", "exit"}:
                break
            answer_question(scan, vraag, asker=args.asker, narrator=args.narrator,
                            out_dir=out_dir)
        return 0

    if not args.question:
        ap.error("--question, --demo or --interactive is required")
    return answer_question(scan, args.question, asker=args.asker,
                           narrator=args.narrator, out_dir=out_dir)


def _slug_q(question: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "-", question.lower()).strip("-")
    return slug[:60]


if __name__ == "__main__":
    raise SystemExit(main())

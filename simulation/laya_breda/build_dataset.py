#!/usr/bin/env python3
"""Build the Laya System-1 training set for the Breda five-value scan (PoC-4).

Primary gold comes from the canonical Breda ``value-scan.json``. Extra training
signal is taken from **open data already cached** under ``poc-breda/data/cache``:

* CBS Wijken en Buurten 2024 (PDOK) for Breda, Eindhoven, Tilburg — enrich
  Breda state with access/dak/ouderen fields; add CBS-only proxy cases for
  Eindhoven + Tilburg (same head definitions, cite-or-abstain on missing).
* Breda municipal layers are already folded into the scan scores/inputs.

Heads (unchanged contract):

  primary_value   choice  argmin of democratic/spatial/economic/social
  attention_band  score   low / mid / high tertile on that primary score
  needs_human     noul    primary-value missing OR bottom-5 on primary
  autonomous_ok   choice  ok if all autonomous.manifest met else review
                          (proxy gemeenten: always ``ok`` — public CBS only)

Hold-out: entire Breda wijken (EVAL_WIJKEN). Proxy gemeenten are train-only
so evaluation stays Breda-generalisation.

Usage:  python3 build_dataset.py
"""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RUN = ROOT / "poc-breda" / "runs" / "20260913T192628Z-breda-scan"
CACHE = ROOT / "poc-breda" / "data" / "cache"

EVAL_WIJKEN = {"WK075804", "WK075808", "WK075809", "WK075807", "WK075810"}
VALUES = ("democratic", "spatial", "economic", "social")
BAND_LEVELS = ["laag — hoge aandacht", "midden", "hoog — weinig aandacht"]
SENTINEL = -90000

ACCESS_FIELDS = [
    ("huisartsenpraktijkGemiddeldeAfstandInKm", "huisarts"),
    ("groteSupermarktGemiddeldeAfstandInKm", "supermarkt"),
    ("basisonderwijsGemiddeldeAfstandInKm", "basisschool"),
    ("kinderdagverblijfGemiddeldeAfstandInKm", "kinderdagverblijf"),
    ("bibliotheekGemiddeldeAfstandInKm", "bibliotheek"),
    ("treinstationGemiddeldeAfstandInKm", "treinstation"),
]
BEDRIJVEN_FIELDS = [
    "aantalBedrijvenLandbouwBosbouwVisserij",
    "aantalBedrijvenNijverheidEnergie",
    "aantalBedrijvenHandelEnHoreca",
    "aantalBedrijvenVervoerInformatieCommunicatie",
    "aantalBedrijvenFinancieelOnroerendGoed",
    "aantalBedrijvenZakelijkeDienstverlening",
    "aantalBedrijvenOverheidOnderwijsEnZorg",
    "aantalBedrijvenCultuurRecreatieOverige",
]

CBS_CACHES = {
    "breda": CACHE / "cbs-buurten-2024.4326.geojson",
    "eindhoven": CACHE / "cbs-buurten-2024-eindhoven.4326.geojson",
    "tilburg": CACHE / "cbs-buurten-2024-tilburg.4326.geojson",
}

questions = {
    "primary_value": {
        "type": "choice",
        "instructions": (
            "Which of the four spatial congress values most needs attention for "
            "this neighbourhood (lowest score)?"
        ),
        "criteria": {
            "democratic": "democratic value (access / wijkdeals) is the weakest",
            "spatial": "spatial value (green backbone) is the weakest",
            "economic": "economic value (unused roof potential) is the weakest",
            "social": "social value (heat vulnerability) is the weakest",
        },
    },
    "attention_band": {
        "type": "score",
        "instructions": "How strong is this neighbourhood on its primary (weakest) value?",
        "criteria": BAND_LEVELS,
    },
    "needs_human": {
        "type": "noul",
        "instructions": (
            "Does this neighbourhood require System-2 / human review before acting "
            "(missing indicators on the primary value or extreme bottom-5)?"
        ),
    },
    "autonomous_ok": {
        "type": "choice",
        "instructions": "Is the autonomous-value sovereignty manifest fully met?",
        "criteria": {
            "ok": "all autonomous.manifest criteria met (or public CBS-only proxy)",
            "review": "one or more autonomy criteria not met — review",
        },
    },
}


def clean(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        if value < SENTINEL:
            return None
        return float(value)
    return None


def percentile_scores(values: list) -> list:
    """Higher raw value → higher score 0–100; None stays None."""
    ranked = sorted((v, i) for i, v in enumerate(values) if v is not None)
    out = [None] * len(values)
    n = len(ranked)
    if n == 0:
        return out
    if n == 1:
        out[ranked[0][1]] = 50.0
        return out
    for rank, (_v, i) in enumerate(ranked):
        out[i] = round(100.0 * rank / (n - 1), 1)
    return out


def inverse(scores: list) -> list:
    return [None if s is None else round(100.0 - s, 1) for s in scores]


def load_cbs_by_code(path: Path) -> dict[str, dict]:
    if not path.is_file():
        return {}
    fc = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for f in fc.get("features") or []:
        p = f.get("properties") or {}
        code = p.get("buurtcode") or p.get("code")
        if code:
            out[str(code)] = p
    return out


def cbs_proxy_row(props: dict, gemeente: str) -> dict | None:
    """CBS-only four scores for Eindhoven/Tilburg (no Breda municipal layers)."""
    if props.get("water") == "JA":
        return None
    code = props.get("buurtcode") or props.get("code")
    naam = props.get("buurtnaam") or props.get("naam")
    if not code or not naam:
        return None

    access_vals = [clean(props.get(f)) for f, _ in ACCESS_FIELDS]
    present = [v for v in access_vals if v is not None]
    access_mean = round(sum(present) / len(present), 3) if len(present) >= 4 else None
    groen = clean(props.get("afstandTotOpenbaarGroenTotaal"))
    zon = clean(props.get("percentageWoningenMetZonnestroom"))
    een = clean(props.get("percentageEengezinswoning"))
    onbenut = (
        round((1 - zon / 100.0) * (een / 100.0), 4)
        if zon is not None and een is not None
        else None
    )
    ha = clean(props.get("oppervlakteLandInHa"))
    tot_b = sum((clean(props.get(f)) or 0) for f in BEDRIJVEN_FIELDS)
    bedrijven = (
        round(tot_b / (ha / 100.0), 1) if ha is not None and ha > 0 and tot_b > 0 else None
    )
    ouderen = clean(props.get("percentagePersonen65JaarEnOuder"))

    return {
        "gemeente": gemeente,
        "buurtcode": str(code),
        "buurtnaam": str(naam),
        "wijkcode": str(props.get("wijkcode") or ""),
        "aantalInwoners": clean(props.get("aantalInwoners")) or 0,
        "raw": {
            "access_km": access_mean,
            "groen_afstand_km": groen,
            "onbenut_dak": onbenut,
            "bedrijven_per_km2": bedrijven,
            "ouderen_pct": ouderen,
        },
        "cbs": _cbs_snippet(props),
        "missing_primary": {
            "democratic": [] if access_mean is not None else ["access"],
            "spatial": [] if groen is not None else ["afstand-openbaar-groen"],
            "economic": [] if onbenut is not None else ["dakpotentieel"],
            "social": [] if ouderen is not None else ["ouderen"],
        },
    }


def _cbs_snippet(props: dict) -> dict:
    keys = [
        "aantalInwoners",
        "aantalHuishoudens",
        "afstandTotOpenbaarGroenTotaal",
        "percentageWoningenMetZonnestroom",
        "percentageEengezinswoning",
        "percentagePersonen65JaarEnOuder",
        "huisartsenpraktijkGemiddeldeAfstandInKm",
        "groteSupermarktGemiddeldeAfstandInKm",
        "basisonderwijsGemiddeldeAfstandInKm",
    ]
    return {k: clean(props.get(k)) for k in keys}


def finalize_proxy_batch(rows: list[dict]) -> list[dict]:
    """Assign municipality-local percentile scores + gold heads."""
    if not rows:
        return []
    dem = inverse(percentile_scores([r["raw"]["access_km"] for r in rows]))
    spa = inverse(percentile_scores([r["raw"]["groen_afstand_km"] for r in rows]))
    eco_a = percentile_scores([r["raw"]["onbenut_dak"] for r in rows])
    eco_b = percentile_scores([r["raw"]["bedrijven_per_km2"] for r in rows])
    soc = percentile_scores([r["raw"]["ouderen_pct"] for r in rows])

    scored = []
    for i, r in enumerate(rows):
        eco_parts = [x for x in (eco_a[i], eco_b[i]) if x is not None]
        scores = {
            "democratic": dem[i] if dem[i] is not None else 0.0,
            "spatial": spa[i] if spa[i] is not None else 0.0,
            "economic": round(sum(eco_parts) / len(eco_parts), 1) if eco_parts else 0.0,
            "social": soc[i] if soc[i] is not None else 0.0,
        }
        # drop rows with fewer than 2 valid value scores
        valid = sum(
            1
            for k, src in (
                ("democratic", dem[i]),
                ("spatial", spa[i]),
                ("economic", eco_parts or None),
                ("social", soc[i]),
            )
            if src is not None
        )
        if valid < 2:
            continue
        scored.append({**r, "scores": scores})
    return scored


def _primary(scores: dict[str, float]) -> str:
    return min(VALUES, key=lambda k: scores[k])


def _band_idx(score: float, tertiles: tuple[float, float]) -> int:
    lo, hi = tertiles
    if score <= lo:
        return 0
    if score <= hi:
        return 1
    return 2


def _tertiles(vals: list[float]) -> tuple[float, float]:
    s = sorted(vals)
    n = len(s) or 1
    return s[max(0, n // 3 - 1)], s[max(0, (2 * n) // 3 - 1)]


def _bottom5_codes(items: list[dict]) -> dict[str, set[str]]:
    out = {k: set() for k in VALUES}
    for val in VALUES:
        ranked = sorted(items, key=lambda it: it["scores"][val])
        for it in ranked[:5]:
            out[val].add(it["buurtcode"])
    return out


def make_case(
    *,
    gemeente: str,
    buurtcode: str,
    buurtnaam: str,
    wijkcode: str,
    inwoners,
    scores: dict[str, float],
    missing_primary: dict,
    cbs: dict,
    inputs: dict | None,
    kansen: list | None,
    autonomous_ok: bool,
    tertiles: tuple[float, float],
    bottom5: dict[str, set[str]],
    eval_flag: bool,
) -> dict:
    prim = _primary(scores)
    band = _band_idx(scores[prim], tertiles)
    prim_missing = bool(missing_primary.get(prim))
    needs = prim_missing or buurtcode in bottom5[prim]
    auto_choice = "ok" if autonomous_ok else "review"
    state = {
        "gemeente": gemeente,
        "buurtcode": buurtcode,
        "buurtnaam": buurtnaam,
        "wijkcode": wijkcode or "",
        "aantalInwoners": inwoners or 0,
        "scores": scores,
        "missing": missing_primary,
        "cbs": cbs,
    }
    if inputs:
        state["inputs"] = inputs
    if kansen:
        state["kansenkaart"] = [str(k)[:160] for k in kansen[:2]]
    return {
        "state": state,
        "questions": questions,
        "gold": {
            "primary_value": {"probabilities": {prim: 1.0}},
            "attention_band": {"probabilities": {str(band): 1.0}},
            "needs_human": {
                "probabilities": {"true": float(needs), "false": float(not needs)}
            },
            "autonomous_ok": {"probabilities": {auto_choice: 1.0}},
        },
        "_meta": {
            "gemeente": gemeente,
            "buurtcode": buurtcode,
            "buurtnaam": buurtnaam,
            "wijkcode": wijkcode,
            "primary": prim,
            "band": band,
            "needs_human": needs,
            "autonomous_ok": auto_choice,
            "eval": eval_flag,
            "proxy": gemeente != "breda",
        },
    }


def main() -> int:
    vs = json.loads((RUN / "value-scan.json").read_text(encoding="utf-8"))
    cbs_breda = load_cbs_by_code(CBS_CACHES["breda"])
    aut = (vs.get("values") or {}).get("autonomous") or {}
    manifest = aut.get("manifest") or []
    autonomous_ok = all(bool(m.get("met")) for m in manifest) if manifest else False

    breda_items = []
    for b in vs["buurten"]:
        raw_scores = b.get("scores") or {}
        scores = {
            k: float((raw_scores.get(k) or {}).get("score") or 0.0) for k in VALUES
        }
        miss = b.get("missing") or {}
        if not isinstance(miss, dict):
            miss = {}
        missing_primary = {k: list(miss.get(k) or []) for k in VALUES}
        inputs = {
            k: (raw_scores.get(k) or {}).get("inputs") or {} for k in VALUES
        }
        breda_items.append({
            "buurtcode": b["buurtcode"],
            "buurtnaam": b["buurtnaam"],
            "wijkcode": b.get("wijkcode") or "",
            "aantalInwoners": b.get("aantalInwoners"),
            "scores": scores,
            "missing_primary": missing_primary,
            "inputs": inputs,
            "kansenkaart": b.get("kansenkaart") or [],
            "cbs": _cbs_snippet(cbs_breda.get(b["buurtcode"]) or {}),
        })

    # CBS proxy cases (open data, already cached — no live fetch required)
    proxy_items = []
    for gemeente in ("eindhoven", "tilburg"):
        props_map = load_cbs_by_code(CBS_CACHES[gemeente])
        if not props_map:
            print(f"warn: missing CBS cache for {gemeente}")
            continue
        rows = []
        for props in props_map.values():
            row = cbs_proxy_row(props, gemeente)
            if row:
                rows.append(row)
        scored = finalize_proxy_batch(rows)
        print(f"cbs proxy {gemeente}: {len(scored)} buurten")
        proxy_items.extend(scored)

    # tertiles + bottom5 within each gold pool (Breda alone for eval fairness;
    # proxies get their own per-gemeente tertiles)
    def cases_for(pool: list[dict], gemeente: str, autonomous: bool) -> list[dict]:
        if not pool:
            return []
        prim_scores = [it["scores"][_primary(it["scores"])] for it in pool]
        tert = _tertiles(prim_scores)
        bottom = _bottom5_codes(pool)
        out = []
        for it in pool:
            eval_flag = (
                gemeente == "breda" and (it.get("wijkcode") or "") in EVAL_WIJKEN
            )
            out.append(
                make_case(
                    gemeente=gemeente,
                    buurtcode=it["buurtcode"],
                    buurtnaam=it["buurtnaam"],
                    wijkcode=it.get("wijkcode") or "",
                    inwoners=it.get("aantalInwoners"),
                    scores=it["scores"],
                    missing_primary=it.get("missing_primary")
                    or {k: [] for k in VALUES},
                    cbs=it.get("cbs") or {},
                    inputs=it.get("inputs"),
                    kansen=it.get("kansenkaart"),
                    autonomous_ok=autonomous,
                    tertiles=tert,
                    bottom5=bottom,
                    eval_flag=eval_flag,
                )
            )
        return out

    cases = cases_for(breda_items, "breda", autonomous_ok)
    for gemeente in ("eindhoven", "tilburg"):
        pool = [p for p in proxy_items if p["gemeente"] == gemeente]
        # remap proxy missing_primary already set
        cases.extend(cases_for(pool, gemeente, True))

    train = [c for c in cases if not c["_meta"]["eval"]]
    evalr = [c for c in cases if c["_meta"]["eval"]]
    strip = lambda rs: [{k: v for k, v in r.items() if k != "_meta"} for r in rs]

    data = HERE / "data"
    data.mkdir(exist_ok=True)
    (data / "train.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(train)),
        encoding="utf-8",
    )
    (data / "eval.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in strip(evalr)),
        encoding="utf-8",
    )
    (data / "meta.jsonl").write_text(
        "".join(json.dumps(r["_meta"], ensure_ascii=False) + "\n" for r in cases),
        encoding="utf-8",
    )

    print(
        f"cases: {len(cases)} (train {len(train)} · eval {len(evalr)} — "
        f"Breda held-out wijken: {sorted(EVAL_WIJKEN)})"
    )
    print(f"by gemeente: {dict(Counter(c['_meta']['gemeente'] for c in cases))}")
    print(f"primary_value: {dict(Counter(c['_meta']['primary'] for c in cases))}")
    print(f"needs_human: {sum(1 for c in cases if c['_meta']['needs_human'])}/{len(cases)}")

    # Persist dataset + CBS source metas to the nLDT medallion lake
    try:
        from lake_publish import main as lake_publish_main

        lake_publish_main(["--all"])
    except Exception as exc:  # pragma: no cover - lake optional in minimal envs
        print(f"warn: lake publish skipped ({type(exc).__name__}: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

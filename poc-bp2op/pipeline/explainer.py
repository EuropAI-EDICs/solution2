"""MC-3 — de omzettabel als exporteerbaar werkdocument, plus PROV.

omzettabel.json  — the full contract-valid row set
omzettabel.md    — the human-readable table (one row per bron regel, suggestions
                   with scores, links and quotes) for the jurist workflow
prov.json        — agents, entities (with sha256), activities, derivations and the
                   method-trace (which MC card motivated which stage)
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List

from . import __version__

EXPLAIN_AGENT = f"explainer#{__version__}"

_MC_TITELS = {
    1: "Transitiestrategie met doelregeling", 2: "Beleidsneutraal omzetten",
    3: "De omzettabel als kernartefact", 4: "Automatisch inlezen en opknippen",
    5: "Kennisbank met hergebruik en match-scores", 6: "Mens blijft op de knoppen",
    7: "Controleerbaarheid: context, toelichting, geschiedenis", 8: "Bulk-analyse voor planning",
    9: "Procesontwerp rondom de tool", 10: "Input-kwaliteit en stapeling",
    11: "Werkingsgebieden zijn (nog) geen AI", 12: "Kwaliteitsborging van de tool zelf",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def omzettabel_md(rows: List[Dict], bron_regels: List[Dict], doel_regels: List[Dict]) -> str:
    bron = {b["id"]: b for b in bron_regels}
    doel = {d["id"]: d for d in doel_regels}
    lines = [
        "# Omzettabel — tijdelijk deel / bruidschatregels naar nieuwe omgevingsplanregels",
        "",
        "Links de bronregel (letterlijk, met link), rechts de gesuggereerde doelregels met",
        "match-score en band (MC-3/MC-5). Suggesties zijn nooit automatisch gekoppeld (MC-6):",
        "de kolom *status* blijft `voorgesteld` tot een jurist de koppeling bevestigt.",
        "",
    ]
    for row in rows:
        b = bron[row["bronRegelId"]]
        lines.append(f"## {row['id']} — {b['locator']['label']}  ({b['statusInBron']})")
        lines.append(f"- **bron**: {b['instrument']} — [regel op de publicatie]({b['url']})")
        quote = b["tekst"][:400] + ("…" if len(b["tekst"]) > 400 else "")
        lines.append(f"- **brontekst**: „{quote}”")
        lines.append(f"- **thema**: {b['thema']}")
        if row["suggesties"]:
            lines.append("- **suggesties**:")
            for s in row["suggesties"]:
                d = doel[s["doelRegelId"]]
                loc = d["locator"]
                kb = f", kennisbank {s['kennisbankHitId']}" if s["kennisbankHitId"] else ""
                lines.append(
                    f"    - **{loc['artikel']} {loc['titel']}** ({loc['pad']}) — score {s['score']:.2f} [{s['band']}]{kb} — {s['scoreDetail']} — [doelregel]({d['url']})")
        else:
            lines.append("- **suggesties**: geen — nieuwe doelregel nodig (MC-1: eerst de doelregeling uitbreiden)")
        if row.get("needsHumanReden"):
            lines.append(f"- **needs_human**: {row['needsHumanReden']}")
        lines.append(f"- **status**: {row['status']}; toelichting: {row['toelichting'] or '—'}")
        lines.append("")
    return "\n".join(lines)


def prov_bundle(agents: List[Dict], entities_paths: Dict[str, Path], activities: List[Dict],
                derivations: List[Dict], method_trace: List[str]) -> Dict:
    entities = {
        name: {"sha256": sha256_file(path), "bytes": Path(path).stat().st_size}
        for name, path in entities_paths.items() if Path(path).exists()
    }
    return {
        "agents": agents,
        "entities": entities,
        "activities": activities,
        "wasDerivedFrom": derivations,
        "methodTrace": {
            "cards": [{"id": mc, "titel": _MC_TITELS.get(int(mc.split("-")[1]), "?")} for mc in method_trace],
            "bron": "corpus/METHOD-CARDS.md (VNG netwerksessie 19-06-2026, transcript met tijdstempels)",
        },
    }


def write_outputs(out_dir: Path, omzettabel: List[Dict], bron_regels: List[Dict],
                  doel_regels: List[Dict], kennisbank_pairs: List[Dict]) -> Dict[str, Path]:
    out = {}
    for name, payload in [
        ("omzettabel.json", omzettabel),
        ("bronregels.json", bron_regels),
        ("doelregels.json", doel_regels),
        ("kennisbank.json", kennisbank_pairs),
        ("omzettabel.md", omzettabel_md(omzettabel, bron_regels, doel_regels)),
    ]:
        p = out_dir / name
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1) if name.endswith(".json") else payload,
                     encoding="utf-8")
        out[name.split(".")[0]] = p
    return out

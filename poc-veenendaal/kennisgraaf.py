#!/usr/bin/env python3
"""veenendaal-spoorzone kennisgraaf/v1 — het DSO-beeld over het gebied als graf.

Vijfde artefact-laag (na run.py · sttr.py · sttr_kruising.py · zones.py):
een afgeleide, herbouwbare projectie met contract `kennisgraaf/v1`. Alles is
terug te voeren op sha256-vaste bronruns — geen interpretatie zonder bewijs,
geen edge zonder meetbaar feit (doctrine: rekenlaag beslist).

Knopen: gebied · zone (deelgebied) · regeling (omgevingsplan) · gio (geo-laag
met FRBRWork) · rtr (toepasbare-regelbestand met geldigheid) · activiteit ·
programma-feit (koppelregel mét bewijs).
Relaties: bestaat_uit (gebied→zone) · overlapt (zone→gio, met ha+dekking%) ·
valt_onder (gebied→regeling) · bevat_geo_laag (regeling→gio) · vraagt_over
(rtr→activiteit) · raakt (programma-feit→activiteit, mét bewijs) ·
uit_programma (gebied→programma-feit).

Bekende leegte, expliciet in het contract (`koppelgaten`): de STTR-geoVerwijzingen
(20) zijn níet hard te leggen aan GIO-bestanden (18 leveranciers-identificatie-
familie, 2 OW-object zonder geometrie in dit pakket) — dus géén rtr→gio-edges.
Dat is het eerlijke verschil tussen "officieel samenhangend" en "hier meetbaar".

Gebruik:
  nldt/.venv/bin/python kennisgraaf.py   # nieuwste loket- en zones-run + RTR-index
Uitvoer: sttr-runs/<ts>-kennisgraaf/{kennisgraaf.json, report.md, manifest.json}
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

DATA = ROOT / "data"
RUNS = ROOT / "sttr-runs"
DSO_OUT = REPO / "nldt" / "simulation" / "regelrecht" / "dso_overlap" / "out"

CONTRACT = "kennisgraaf/v1"


def utcnow() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slug(tekst: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", tekst.lower()).strip("-")[:60]


# ---------------------------------------------------------------- bouw (puur, testbaar)

def bouw_graaf(gebied: dict, loket: dict, zones_run: dict, sttr_index: dict) -> dict:
    """Zet vier bron-dicts om in de graaf. Puur: geen IO, geen tijd-afhankelijkheid."""
    nodes: list[dict] = []
    edges: list[dict] = []

    def node(nid: str, ntype: str, label: str, attrs: dict, bron: str):
        n = {"id": nid, "type": ntype, "label": label, "bron": bron, **attrs}
        nodes.append(n)
        return n

    def edge(van: str, naar: str, etype: str, attrs: dict | None = None):
        edges.append({"van": van, "naar": naar, "type": etype, **(attrs or {})})

    # gebied + zones
    wg = gebied.get("werkgrens") or {}
    doelen = gebied.get("doelen_uit_toekomstbeeld") or {}
    node("gebied:spoorzone-veenendaal", "gebied", gebied.get("gebied", "Spoorzone"),
         {"oppHa": wg.get("opp_ha"), "grensModus": "polygon" if wg.get("geojson_rd") else "bbox",
          "programma": {k: doelen[k] for k in
                        ("woningen_nieuw_feiten_tabel", "groen_ha_minimum",
                         "arbeidsplaatsen_nieuw", "woningen_per_jaar_gemiddeld") if k in doelen}},
         "gebied.json")
    for z in (gebied.get("deelgebied_zones") or {}).get("zones") or []:
        zid = f"zone:{_slug(z['naam'])}"
        node(zid, "zone", z["naam"], {"oppHa": z.get("opp_ha"), "grens": "provisioneel"},
             "gebied.json")
        edge("gebied:spoorzone-veenendaal", zid, "bestaat_uit")

    # regeling + GIO's (uit het loket-run: sweep over het uitwisselpakket)
    regeling = loket.get("regeling") or {}
    rid = f"regeling:{_slug(str(regeling.get('identificatie') or 'onbekend'))}"
    node(rid, "regeling", regeling.get("officieleTitel") or str(regeling.get("identificatie")),
         {"identificatie": regeling.get("identificatie"),
          "oin": loket.get("oin"), "pakketSha256": regeling.get("pakketSha256")},
         "loketvragen.json")
    edge("gebied:spoorzone-veenendaal", rid, "valt_onder")

    gios = ((loket.get("locatieGebonden") or {}).get("gios")) or []
    for g in gios:
        gid = f"gio:{g['bestand'][:-4] if g['bestand'].endswith('.gml') else g['bestand']}"
        node(gid, "gio", g["bestand"],
             {"frbrWork": g.get("frbrWork"), "snijdtWerkgrens": bool(g.get("snijdtWerkgrens")),
              "overlapHa": g.get("overlapHa"), "aantalPolygonen": g.get("aantalPolygonen")},
             "loketvragen.json")
        edge(rid, gid, "bevat_geo_laag")

    # zone → gio (uit de zones-run: gemeten overlap per deelgebied)
    for z in zones_run.get("zones") or []:
        zid = f"zone:{_slug(z['naam'])}"
        for g in z.get("gio_lagen") or []:
            edge(zid, f"gio:{g['gio']}", "overlapt",
                 {"overlapHa": g.get("overlapHa"), "dekkingPct": g.get("dekkingPct"),
                  "objecten": g.get("objecten"), "bron": zones_run.get("runId")})

    # rtr-bestanden → activiteiten (geldigheid als attribuut)
    for b in sttr_index.get("bestanden") or []:
        if b.get("einddatum"):
            continue  # alleen geldige bestanden projecteren
        besl = b.get("decisions") or []
        node(f"rtr:{b['identifier']}", "rtr",
             b.get("naam") or str(b["identifier"]),
             {"activiteit": b.get("activiteit"), "begindatum": b.get("begindatum"),
              "dmnVersie": b.get("dmnVersie"), "exporter": b.get("exporter"),
              "geoVerwijzingen": b.get("geoVerwijzingen"),
              "decisions": len(besl),
              "projecteerbaar": sum(1 for d in besl if d.get("projecteerbaar")),
              "sha256": b.get("sha256")},
             "veenendaal.sttr.json")
        if b.get("activiteit"):
            aid = f"activiteit:{_slug(b['activiteit'])}"
            if not any(n["id"] == aid for n in nodes):
                node(aid, "activiteit", b["activiteit"], {"herkomst": "RTR"}, "veenendaal.sttr.json")
            edge(f"rtr:{b['identifier']}", aid, "vraagt_over")

    # programma-feiten → activiteiten (bewijs-gebonden koppelregels)
    for i, r in enumerate(loket.get("programmaGebonden") or []):
        pid = f"programma:{i}"
        node(pid, "programma-feit", r["activiteit"],
             {"soort": r.get("soort"), "bewijs": r.get("bewijs")}, "loketvragen.json")
        edge("gebied:spoorzone-veenendaal", pid, "uit_programma")
        aid = f"activiteit:{_slug(r['activiteit'])}"
        if not any(n["id"] == aid for n in nodes):
            node(aid, "activiteit", r["activiteit"], {"herkomst": "programma-koppeling"},
                 "loketvragen.json")
        edge(pid, aid, "raakt")

    # koppelgaten: eerlijk documenteren wat níet legbaar is
    verw = ((loket.get("locatieGebonden") or {}).get("verwijzingen")) or []
    per_status: dict[str, int] = {}
    for v in verw:
        per_status[v.get("status", "onbekend")] = per_status.get(v.get("status", "onbekend"), 0) + 1
    koppelgaten = [{
        "gat": "rtr→gio via geoVerwijzing",
        "feit": f"{len(verw)} geoVerwijzing-vragen, statusverdeling {per_status} — "
                "geen enkele legt hard aan een GIO-bestand in dit pakket",
        "consequentie": "geen rtr→gio-edges in deze graaf; zone→gio is de enige "
                        "meetbare gebiedsbinding",
    }]

    return {"contract": CONTRACT, "nodes": nodes, "edges": edges,
            "koppelgaten": koppelgaten}


# ---------------------------------------------------------------- zelfchecks (V)

def controleer_graaf(graaf: dict, gebied: dict, loket: dict, zones_run: dict,
                     sttr_index: dict) -> list[dict]:
    """Contract-controles: ids uniek · edges resolveerbaar · aantallen ≡ bronnen."""
    ids = [n["id"] for n in graaf["nodes"]]
    idset = set(ids)
    geldig_rtr = sum(1 for b in sttr_index.get("bestanden") or [] if not b.get("einddatum"))
    snijdend = sum(1 for g in ((loket.get("locatieGebonden") or {}).get("gios")) or []
                   if g.get("snijdtWerkgrens"))
    zone_nodes = sum(1 for n in graaf["nodes"] if n["type"] == "zone")
    gio_nodes = sum(1 for n in graaf["nodes"] if n["type"] == "gio")
    rtr_nodes = sum(1 for n in graaf["nodes"] if n["type"] == "rtr")
    zone_gio_edges = [e for e in graaf["edges"] if e["type"] == "overlapt"]
    verwacht_zone_gio = sum(len(z.get("gio_lagen") or []) for z in zones_run.get("zones") or [])
    gebied_opp = (gebied.get("werkgrens") or {}).get("opp_ha")
    zone_som = round(sum(z.get("opp_ha") or 0 for z in
                         (gebied.get("deelgebied_zones") or {}).get("zones") or []), 1)

    checks = [
        ("unieke node-ids", len(ids) == len(idset), f"{len(ids)} nodes, {len(ids) - len(idset)} duplicaten"),
        ("edges resolveerbaar", all(e["van"] in idset and e["naar"] in idset for e in graaf["edges"]),
         f"{len(graaf['edges'])} edges"),
        ("zone-aantal ≡ gebied.json", zone_nodes == len((gebied.get("deelgebied_zones") or {}).get("zones") or []),
         f"{zone_nodes} zones"),
        ("gio-aantal ≡ pakket-sweep", gio_nodes == len(((loket.get("locatieGebonden") or {}).get("gios")) or []),
         f"{gio_nodes} gio's ({snijdend} snijden de werkgrens)"),
        ("rtr-aantal ≡ geldige bestanden", rtr_nodes == geldig_rtr, f"{rtr_nodes} rtr's"),
        ("zone→gio ≡ zones-run", len(zone_gio_edges) == verwacht_zone_gio,
         f"{len(zone_gio_edges)} overlapt-edges"),
        ("Σ zone-opp ≈ werkgrens", abs(zone_som - (gebied_opp or 0)) <= 0.2,
         f"{zone_som} vs {gebied_opp} ha"),
        ("elke node heeft bron", all(n.get("bron") for n in graaf["nodes"]), ""),
    ]
    return [{"check": naam, "ok": bool(ok), "detail": det} for naam, ok, det in checks]


# ---------------------------------------------------------------- main + rapport

def main() -> int:
    gebied = json.loads((DATA / "gebied.json").read_text(encoding="utf-8"))

    loket_dirs = sorted(RUNS.glob("*-loketvragen"))
    zones_dirs = sorted(RUNS.glob("*-zones"))
    if not loket_dirs or not zones_dirs:
        raise SystemExit("loket- of zones-run ontbreekt — draai eerst sttr.py en zones.py")
    loket_pad = loket_dirs[-1] / "loketvragen.json"
    zones_pad = zones_dirs[-1] / "zones.json"
    loket = json.loads(loket_pad.read_text(encoding="utf-8"))
    zones_run = json.loads(zones_pad.read_text(encoding="utf-8"))
    sttr_pad = DSO_OUT / "veenendaal.sttr.json"
    sttr_index = json.loads(sttr_pad.read_text(encoding="utf-8"))

    graaf = bouw_graaf(gebied, loket, zones_run, sttr_index)
    checks = controleer_graaf(graaf, gebied, loket, zones_run, sttr_index)
    v_ok = all(c["ok"] for c in checks)

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-kennisgraaf"
    uit = RUNS / run_id
    uit.mkdir(parents=True, exist_ok=True)

    per_type: dict[str, int] = {}
    for n in graaf["nodes"]:
        per_type[n["type"]] = per_type.get(n["type"], 0) + 1
    per_edge: dict[str, int] = {}
    for e in graaf["edges"]:
        per_edge[e["type"]] = per_edge.get(e["type"], 0) + 1
    graaf["runId"] = run_id
    graaf["gegenereerdOp"] = utcnow()
    graaf["bronRuns"] = {"loket": loket["runId"], "zones": zones_run["runId"]}
    graaf["vChecks"] = checks
    (uit / "kennisgraaf.json").write_text(json.dumps(graaf, ensure_ascii=False, indent=2),
                                          encoding="utf-8")

    bronnen = [
        {"bron": "gebied.json", "pad": str(DATA / "gebied.json"), "sha256": sha256_file(DATA / "gebied.json")},
        {"bron": "loketvragen-run", "pad": str(loket_pad), "sha256": sha256_file(loket_pad)},
        {"bron": "zones-run", "pad": str(zones_pad), "sha256": sha256_file(zones_pad)},
        {"bron": "rtr-index", "pad": str(sttr_pad), "sha256": sha256_file(sttr_pad)},
    ]
    (uit / "manifest.json").write_text(
        json.dumps({"runId": run_id, "gegenereerdOp": utcnow(), "contract": CONTRACT,
                    "bronnen": bronnen}, ensure_ascii=False, indent=2), encoding="utf-8")

    knopen_tekst = ", ".join(f"{v}× {k}" for k, v in sorted(per_type.items()))
    edges_tekst = ", ".join(f"{v}× {k}" for k, v in sorted(per_edge.items()))
    regels = [
        f"# Kennisgraaf/v1 — DSO-beeld over de Spoorzone — {run_id}",
        "",
        f"*Run {utcnow()} · engine `poc-veenendaal/kennisgraaf.py` · afgeleide projectie met "
        f"contract `{CONTRACT}` — herbouwbare graaf over sha256-vaste bronruns.*",
        "",
        f"**{len(graaf['nodes'])} knopen** ({knopen_tekst}) · "
        f"**{len(graaf['edges'])} relaties** ({edges_tekst}).",
        "",
        "## Contract-controles",
        "",
    ]
    regels += [f"- {'✓' if c['ok'] else '✗'} **{c['check']}** {c['detail']}" for c in checks]
    regels += ["", "## Koppelgaten (eerlijk)", ""]
    regels += [f"- **{k['gat']}**: {k['feit']} → {k['consequentie']}" for k in graaf["koppelgaten"]]
    regels += [
        "",
        "## Leeswijzer",
        "",
        "- `zone→gio (overlapt)` is de enige meetbare gebiedsbinding, met overlap-ha en",
        "  dekking% uit de zones-run; `regeling→gio` volgt het uitwisselpakket (83 lagen,",
        "  waarvan de snijdende gemarkeerd).",
        "- `rtr→activiteit` volgt de RTR-metadata (geldigheid als attribuut);",
        "  `programma→activiteit` draagt altijd bewijs uit het Toekomstbeeld/de nulmeting.",
        "- Graaf is volledig afgeleid: `kennisgraaf.json` herbouwt uit de bronruns in",
        "  `manifest.json` (zelfde paden, zelfde sha256's).",
        "",
        f"*Bronruns: loket `{loket['runId']}` · zones `{zones_run['runId']}` · "
        f"RTR-index `veenendaal.sttr.json`.*",
    ]
    (uit / "report.md").write_text("\n".join(regels), encoding="utf-8")

    print(f"✓ {run_id}")
    print(f"  knopen: {per_type}")
    print(f"  edges:  {per_edge}")
    print(f"  V-checks: {'PASS' if v_ok else 'FAIL'} — " +
          "; ".join(f"{c['check']}" for c in checks if not c["ok"]))
    return 0 if v_ok else 2


if __name__ == "__main__":
    sys.exit(main())

"""Slotgates: het fase-manifest stuurt welke agent welke tools krijgt (M3).

Het fundament-manifest (poc-minigim/fase-manifest.json) declareert per fase
een agent-rol en taken met tool-klasse (retrieval/computation/validation/
report). Deze module vertaalt dat naar de deep-agents-wiring: per agent een
expliciete, manifest-afgeleide toolset (apply_slotgate). Agents die het
manifest niet noemt blijven ongewijzigd; zonder manifest is de slotgate een
no-op — de wiring kan dus niet stilletjes afwijken van de methodiek.

Klassen die een agent niet in zijn pool heeft tellen niet voor díe agent
(rol-splits zoals 'critic + explainer' delen een fase; ieder neemt zijn
eigen deel). Een onbekende ROL faalt daarentegen luid (ValueError).
"""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent

import journal  # noqa: E402  (deep-agents-root staat op sys.path)

# manifest-gedreven PoC's (M3: alleen minigim; M5 volgt bij de tweede pilot)
MANIFEST_PATHS = {
    "minigim": REPO_ROOT / "poc-minigim" / "fase-manifest.json",
}

# manifest-agentrol (genormaliseerd, '+'-gesplitst) → deep-agents agent-naam
ROLE_ALIASES = {
    "intake": "intake",
    "minigim-specialist": "minigim",
    "geospecialist": "geospecialist",
    "critic": "critic",
    "explainer": "explainer",
}

# catalog-discovery (MCP-namen óf wrapper-namen) mag bij alle PoC-agenten —
# leesontdekking van recepten/records is fase-overstijgend en read-only
CATALOG_DISCOVERY = {"search_records", "get_record", "list_recipes", "get_recipe"}


def _tool_name(t) -> str:
    return getattr(t, "name", getattr(t, "__name__", ""))


def load_manifest(poc: str = "minigim") -> dict | None:
    """Manifest van een PoC, of None als er geen is (slotgate = no-op)."""
    path = MANIFEST_PATHS.get(poc)
    if path is None or not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def resolve_agent_phases(manifest: dict) -> dict[str, list[str]]:
    """agent-naam → fase-ids, via ROLE_ALIASES; onbekende rol = luide faal."""
    out: dict[str, list[str]] = {}
    for ph in manifest["phases"]:
        for rol in str(ph["agent"]["role"]).lower().split("+"):
            alias = ROLE_ALIASES.get(rol.strip())
            if alias is None:
                raise ValueError(
                    f"onbekende manifest-agentrol {ph['agent']['role']!r} in {ph['id']}"
                )
            out.setdefault(alias, []).append(ph["id"])
    return out


def _pool() -> dict[str, dict[str, list]]:
    """tool-klasse → concrete deep-agents tools, per agent.

    Traag geïmporteerd (bij apply_slotgate) om import-cirkels met pocs.py
    te vermijden. De pool is vandaag gelijk aan de bestaande ROLE_AGENTS-
    tools: M3 maakt de wiring manifest-afgeleid, hij verandert haar niet.
    """
    from tools.artifacts import submit_request
    from tools.explain import crosscheck_formal_rule, get_provenance
    from tools.geo import compare_layers, inspect_geo_layer
    from tools.intake import request_template, validate_request
    from tools.poc_live import run_minigim_live
    from tools.validate import validate_world_scene

    return {
        "intake": {"validation": [request_template, validate_request, submit_request]},
        # minigim haalt retrieval via de catalog-discovery; computation is de run
        "minigim": {"computation": [run_minigim_live]},
        "geospecialist": {"computation": [inspect_geo_layer, compare_layers]},
        "critic": {"validation": [validate_world_scene]},
        "explainer": {"report": [get_provenance, crosscheck_formal_rule]},
    }


def apply_slotgate(specs: list[dict], manifest: dict, poc_agent_names: set[str]) -> list[dict]:
    """Filter per manifest-agent de tools tot fase ∪ (PoC-agenten: catalog).

    Geeft een nieuwe specs-lijst terug (de invoer wordt niet gemuteerd);
    agenten die het manifest niet noemt gaan ongewijzigd door.
    """
    pool = _pool()
    phases_by_agent = resolve_agent_phases(manifest)
    classes_by_phase = {
        ph["id"]: {(t.get("tool") or {}).get("class")
                   for t in (ph.get("tasks") or []) if t.get("tool")}
        for ph in manifest["phases"]
    }
    allowed: dict[str, set[str]] = {}
    for agent_name, fase_ids in phases_by_agent.items():
        names: set[str] = set()
        if agent_name in poc_agent_names:
            names |= CATALOG_DISCOVERY
        for cls in set().union(*(classes_by_phase[f] for f in fase_ids)):
            for tool in pool.get(agent_name, {}).get(cls) or []:
                names.add(_tool_name(tool))
        allowed[agent_name] = names

    out: list[dict] = []
    for spec in specs:
        name = spec["name"]
        if name not in allowed:
            out.append(spec)
            continue
        out.append({**spec, "tools": [t for t in spec["tools"]
                                      if _tool_name(t) in allowed[name]]})
    return out


def journal_fases_en_gate(poc: str, run_dir: Path) -> None:
    """Journaliseer de manifest-fasen + het gate-verdict van een run (M3).

    Alleen bij manifest-gedreven PoC's; een PoC zonder manifest (of een run
    zonder leesbare run_summary.json) journaalt niets extra — achterwaarts
    compatibel met de bestaande live-panel-tools.
    """
    manifest = load_manifest(poc)
    if manifest is None:
        return
    try:
        summary = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    verdict = summary.get("verdict", "onbekend")
    for ph in manifest["phases"]:
        journal.append("fase", poc,
                       f"{ph['id']}: {ph['title']} — agent {ph['agent']['role']}",
                       fase=ph["id"])
    journal.append("gate", poc,
                   f"verdict: {verdict} (V0–V3 deterministisch; V4 pending)",
                   fase="F4-synthese", verdict=verdict)

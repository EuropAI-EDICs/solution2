# LDT Toolbox

Proof-of-concept toolbox for the EU Local Digital Twins toolbox track: reasoning over
Dutch omgevingswet regulation with full traceability (instrument + article + version +
verbatim quote + URL per claim, schema-validated artifacts, PROV provenance).

- [`MULTI_AGENT_PLAN.md`](MULTI_AGENT_PLAN.md) — the multi-agent architecture plan.
- [`docs/SOLUTIONS_ARCHITECTURE.md`](docs/SOLUTIONS_ARCHITECTURE.md) — solutions
  architecture (module boundaries, contract catalogue, validation levels).
- [`docs/GENAI_SEAMS.md`](docs/GENAI_SEAMS.md) — where and how GenAI (LLM)
  enters the deterministic PoCs: the seam catalogue, the scenario-planning
  pattern and its provenance-basis contract.
- [`poc/`](poc/README.md) — **PoC-1**: "Where can I do what?" in province
  Utrecht for three tracks — **wind** turbines, **zon** (zonnevelden/solar
  fields) and **bos** (new nature/forest planting) — on the
  Omgevingsverordening CVDR704250 + open geo data.
- [`poc-bp2op/`](poc-bp2op/README.md) — **PoC-2**: "van bestemmingsplan naar
  omgevingsplan met AI" for gemeente Eindhoven — the recorded Amsterdams aanpak
  (VNG netwerksessie 19-06-2026) as method cards MC-1…12, each traceable from run
  artifact back to transcript timestamp.
- [`poc-rijnland/`](poc-rijnland/README.md) — **PoC-3**: peilgebied (vigerend) ×
  peilafwijking (praktijk) for Hoogheemraadschap van Rijnland, H3 conflict
  heatmap via the PoC-1/nldt bridge (MVP; KRW clustering is phase 2).
- [`poc-minigim/`](poc-minigim/README.md) — **PoC-5**: MiniGIM-methodiek
  (minigim.nl) for gebiedsontwikkelaars — 74-item Omgevingsanalyse Lijst v0.91
  auto-filled from keyless open data + draft ILS v0.8 gebiedsindeling
  (IfcExportAs/EPset_minigim); pilot Breda-Teteringen, IFC/GREX is phase 2
  (see [`docs/MINIGIM.md`](docs/MINIGIM.md)).
- [`simulation/`](simulation/README.md) — animated step-through simulation of
  both PoCs, replayed from their canonical run artifacts
  (`python3 simulation/build_simulation.py`, then open `simulation.html`).
- [`3d-viewer/`](3d-viewer) — 3D BAG LOD22 tile mirror/viewer experiment.
- [`SETUP.md`](SETUP.md) — environment setup; [`sql/`](sql) — database scratchpad.

PoC-1 and PoC-2 run offline, corpus-first: `python3 poc/run.py` (tracks:
`--use-case wind|zon|bos`) and `python3 poc-bp2op/run.py`
(stdlib + `jsonschema`; no network at runtime). Deterministic scenario
sweeps replay the canonical PoC-1 runs: `python3 poc/scenarios/run.py`
(`--use-case wind|zon|bos`; GenAI seams `--author auto|llm`, gated
`--narrator deterministic|llm` — the live open-model leg ran on local
Ollama qwen3.8), and the cross-track conflict overlay quantifies the
energy-vs-nature overlaps: `python3 poc/crosstrack/run.py` — see
[`docs/GENAI_SEAMS.md`](docs/GENAI_SEAMS.md). PoC-3 (Rijnland peil-conflict)
uses live/cached ArcGIS + H3: `nldt/.venv/bin/python poc-rijnland/run.py`.

# LDT Toolbox

Proof-of-concept toolbox for the EU Local Digital Twins toolbox track: reasoning over
Dutch omgevingswet regulation with full traceability (instrument + article + version +
verbatim quote + URL per claim, schema-validated artifacts, PROV provenance).

- [`MULTI_AGENT_PLAN.md`](MULTI_AGENT_PLAN.md) — the multi-agent architecture plan.
- [`docs/SOLUTIONS_ARCHITECTURE.md`](docs/SOLUTIONS_ARCHITECTURE.md) — solutions
  architecture (module boundaries, contract catalogue, validation levels).
- [`poc/`](poc/README.md) — **PoC-1**: "Where can I do what?" for wind turbines in
  province Utrecht (Omgevingsverordening CVDR704250 + open geo data).
- [`poc-bp2op/`](poc-bp2op/README.md) — **PoC-2**: "van bestemmingsplan naar
  omgevingsplan met AI" for gemeente Eindhoven — the recorded Amsterdams aanpak
  (VNG netwerksessie 19-06-2026) as method cards MC-1…12, each traceable from run
  artifact back to transcript timestamp.
- [`3d-viewer/`](3d-viewer) — 3D BAG LOD22 tile mirror/viewer experiment.
- [`SETUP.md`](SETUP.md) — environment setup; [`sql/`](sql) — database scratchpad.

Both PoCs run offline, corpus-first: `python3 poc/run.py` and
`python3 poc-bp2op/run.py` (stdlib + `jsonschema`; no network at runtime).

# Simulation — both PoCs, animated

An interactive, single-file visualization of what actually happens inside
[PoC-1](../poc/README.md) (**three tracks**: wind · zon · bos, province Utrecht)
and [PoC-2](../poc-bp2op/README.md) (van bestemmingsplan naar omgevingsplan,
gemeente Eindhoven) — replayed step by step from their **canonical run
artifacts**. No number, verdict or polygon is mocked.

```bash
python3 simulation/build_simulation.py   # rebuild simulation.html from the runs
node    simulation/verify_static.mjs     # headless smoke test of the page script
open    simulation/simulation.html       # works from file:// — no server, no network
```

## Laya · System-1 (tab 3) — twee datasets

Real [Laya](https://github.com/NandhaKishorM/laya) decision models, fine-tuned
per keten and embedded in the page (switcher top-right of the tab):

**zone-keten · Utrecht** (`simulation/laya_utrecht/`) — trained on 84 unique
NormCards from the 13 PoC-1 runs; four typed heads (`choice` regelstatus /
`choice` zone-effect · `score` juridische werking · `noul` P(jurist)). Five
whole tracks (water · mobiliteit · werken · recreatie · biomassa) held out:
status 94% · effect 89% · jurist 100% · werking 100%. Chat unlocks after the
PoC-1 run (any track) finishes.

**BP→OP · Eindhoven** (`simulation/laya_bp2op/`) — trained on the 311
bronregels of the conversion run; three heads (`choice` doel-hoofdstuk ·
`score` match-band · `noul` P(jurist)), 63 artikelen held out: hoofdstuk 90% ·
band 83% · jurist 90%. Chat unlocks after the PoC-2 run finishes.

```bash
# per dataset: build → fine-tune → export → embed
python3 simulation/laya_utrecht/build_dataset.py    # 84 kaarten, 5 tracks held out
python3 simulation/laya_bp2op/build_dataset.py      # 311 bronregels, 63 artikelen held out
# fine-tune (deep-agents/laya_train/.venv — laya+torch, MPS, ~10 min each):
deep-agents/laya_train/.venv/bin/python simulation/laya_utrecht/finetune.py
deep-agents/laya_train/.venv/bin/python simulation/laya_bp2op/finetune.py
deep-agents/laya_train/.venv/bin/python simulation/laya_utrecht/predict_export.py  # → predictions.json
deep-agents/laya_train/.venv/bin/python simulation/laya_bp2op/predict_export.py   # → predictions.json
python3 simulation/build_simulation.py              # embed both prediction sets
```

One case per bronregel (verbatim tekst from hoofdstuk 22/23), three typed
heads — `choice` doel-hoofdstuk · `score` match-band (geen/zwak/mogelijk/sterk)
· `noul` P(jurist) — gold from the run's own omzettabel/kennisbank. Held-out
results (63 ongeziene artikelen): hoofdstuk 90% · band 83% · jurist 90%;
confidence-gate 0.55 → onthouding → System 2 (jurist, V4), same contract as
`deep-agents/laya_router.py`. The page embeds the exported predictions
(offline at build time); free-text queries map deterministically to the
nearest bronregel via the matcher's own featurization. The **chat unlocks
after the PoC-2 scenario-run finishes** (deep-link: `?tab=3`).


## What you see

**PoC-1 tab — the zone pipeline, three tracks.** A `wind | zon | bos` switcher
(top-right of the map) swaps the entire PoC-1 simulation between the canonical
runs: wind turbines (859.5 km² final), zonnevelden (1167.9 km²) and nieuwe
natuur/bosaanplant (the 23.9 km² Groene-contour zoekgebied). The nine pipeline
stages light up in order (intake → Norm Analyst → Formalizer → Geo Analyst →
Zone Engine → Cartographer → Critic → Explainer → Report) while the map replays
that run's real ZoneResult chain — per track: inclusion union → ∩ AOI → the
track's hard exclusions (wind: Natura 2000 & ganzenrust + Natuurnetwerk;
zon: Natura 2000 & ganzenrust; bos: none — a zoekgebied) → final — then the
attention/conditional/compensation markers hatch in *without* changing the
area. Side panels stream the per-track counters, abstention ledgers (8 wind /
6 zon /6 bos), decision tables (24 / 5 / 5 rows) and V0–V4 verdicts with the
run's own IoU.

**PoC-1 rule graph.** Below the map, a second panel draws the run's rule
knowledge graph — the V2 traceability chain as a layered node-link diagram:
instrument-artikel → NormCard → FormalRule (green formalized · amber
ambiguous→V4 · grey rejected) → geo layer (registry alias) → ZoneResult (km²),
with the abstention register as dashed amber nodes that deliberately lead
nowhere (cite-or-abstain: no verified citation, no rule). Nodes light up in
step with the pipeline stages; hover any node for its claim, verbatim quote,
abstention reason or layer service. Wind: 96 nodes / 77 edges; zon 30/22;
bos 28/18 — all read from `normcards.json`, `formalrules.json`, `layers.json`
and `zones.json` of the canonical run.

**PoC-2 tab — the conversion pipeline.** MC-badged stages: 1074 artikelen split
into 762 doelregels + 311 bronregels, the kennisbank build (B02 262 + B03 12,
B04's 9 duplicates dropped), then the matcher sweep — a 311-cell grid, one cell
per bronregel, coloured by its real outcome (kennisbank-driven, sterk, mogelijk,
needs_human, nieuwe regel) — followed by the 74.6% coverage dial and the Critic
with V4 jurist-review permanently pending.

**PoC-2 kennisbank graph.** A separate panel draws the kennisbank itself as a
bipartite graph: every kept relation from `kennisbank.json` as a curved link
from its bron-artikel (left, grouped per wijzigingsbesluit B02/B03) to its
doel-artikel (right, grouped per hoofdstuk) — 274 relations in total, blue
'vervangt' (240) · purple 'voortzetting' (34), drawn bright when the matcher
actually reused the relation as a score-1.0 boost (220) and dimmed when not
(54). Hover any relation for its verbatim quote and the link to the official
publication; click opens the source. The 21 relations ending in hoofdstuk 22
itself (old Rijkswet living on as bronregels, no DR-id) get their own group.

Controls: play / step / reset, 0.5–4× speed, click any stage to jump;
`space` = play/pause, `→` = step; PoC-1 track switcher on the map header.

## Files

| file | role |
|---|---|
| `build_simulation.py` | reads the canonical runs (per-track registry at the top), display-simplifies the zone geometry (~300 m, page weight only — displayed areas stay the engine's own numbers), and derives both knowledge-graph payloads — the PoC-1 traceability chain (artikel → NormCard → FormalRule → layer → ZoneResult, from `normcards/formalrules/layers/zones.json`) and the PoC-2 kennisbank graph (274 bron→doel relations + the omzettabel join that marks which 220 the matcher reused); injects everything into the template |
| `template.html` | the page: timeline engine, SVG map, rule graph, kennisbank graph, grid sweep, panels; `/*__DATA__*/` marker |
| `simulation.html` | generated output — open this |
| `verify_static.mjs` | extracts the inline script, runs it against a DOM stub and drives both timelines (all three PoC-1 tracks + PoC-2) through every step |

Grounded in `poc/runs/20260830T113234Z-wind`, `poc/runs/20260830T142439Z-zon`,
`poc/runs/20260830T142446Z-bos` and `poc-bp2op/runs/20260830-124515-eindhoven`;
rebuild after new canonical runs by pointing `POC1_TRACKS` / `POC2_RUN` at the
top of `build_simulation.py` at the new dirs.

# Harness Lab — harness2 method ported onto the fundament (Option A)

An experiment that treats our agent harness (deep-agents prompts, slotgate tool grants, model pins) as **versioned, probed, adoptable variants** — the propose–probe–compose loop from google-research/harness2, but judged by our own deterministic critics instead of an LLM judge. No harness2 dependency; adoption stays human-gated (V4-cultuur: the lab automates propose/probe/compose, a human presses the adopt button).

Mapping: **propose** = declarative variant files (an LLM-assisted proposer is a `fase-2-haak`, reusing that exact register concept) · **probe** = adapters run each variant against task sets with deterministic checks · **compose** = score comparison report · **adopt** = CLI status flip in a new harness register, only with passing evidence.

## 1. Schemas — `poc-fundament/schemas/` (draft 2020-12, `additionalProperties: false`, modeled on `modelregister.schema.json`)
- `harnessregister.schema.json` — `{poc, harnesses: [...]}`; entry: `id`, `title`, `component` (enum `prompt|toolGrants|modelPin`), `target`, `riskLevel`, `version`, `status` (enum `actief|kandidaat|verworpen`), `artifact` (`kind: promptFile|manifestPatch|envPin` + `path`/`sha256`/`patch`/`env`), optional `adoptedFrom`, `probeEvidence[] {probeId, runDir, mode, verdict, probedAt}`, `prov`, `note`.
- `harness-variant.schema.json` — `{id, title, base?, components: [{type, target, path|patch|env}]}`.
- `probe-taskset.schema.json` — `{id, tasks: [{id, kind, input, expect: [{check, value}]}]}`; checks: `delegatesTo`, `toolTraceIncludes`, `answerContains`, `answerNotContains`, `verdictPass`, `slotgateAllows`, `slotgateForbids`.

## 2. Engine — `poc-fundament/fundament/harnesslab.py` (stdlib + lazy jsonschema; keeps `test_deps` green)
`HarnessLabError`; loud-fail loaders `load_harness_register` / `load_variant` / `load_taskset` (incl. unique-id check, mirroring `models.py`); evidence builder (`new_evidence`, `record_task_result`, `finalize_evidence` → `probe-evidence.json` with sha256 PROV of every variant artifact + taskset; verdict = all tasks pass ∧ no hard-invariant violations); `render_probe_report` (markdown comparison matrix, byte-deterministic); `adopt(register, evidence, *, allow_fake=False)` — refuses failing evidence and fake-mode evidence unless `--allow-fake`, supersedes the previous `actief` entry for the same target (→ `verworpen`, `adoptedFrom` set), enforcing exactly-one-actief-per-target.

## 3. Register seed + conformance — deep-agents
- `deep-agents/harnessregister.json`: baseline `actief` entries for `recipe_driver.md`, the 6 `prompts/poc/*.md`, 6 `prompts/roles/*.md`, and the two model pins (`gemma4:31b-mlx` / `gemma4:12b-mlx`), each with sha256.
- `deep-agents/tests/test_harnessregister.py`: claims-backed conformance (test_modelregister.py pattern) — paths exist, sha256 matches disk, pins match `model_config.py` defaults, exactly one `actief` per target.

## 4. Adapter — `deep-agents/harness_lab_adapter.py`
Pure `apply_variant(subagent_specs, variant)` (prompt-text swap via the spec dict, in-memory slotgate manifest patch — no production files touched); `run_taskset(...)` with two modes:
- **fake** (default, offline): `GenericFakeChatModel` scripted responses per taskset (test_hitl_smoke.py pattern) — deterministic regression/plumbing proof; journal isolated by redirecting `journal.LIVE_DIR` into the probe dir (proven monkeypatch point).
- **llm** (env-gated `LDT_DEEP_AGENTS_ENDPOINT`/check_ollama): real headless runs via `run_standalone_poc_agent` / live-style run with `--auto-approve-hitl`, per-run model pins via env.
Both emit identical evidence; slotgate allow/forbid checks run offline in both.

## 5. CLI — `poc-fundament/tools/harness_lab.py`
`scaffold` (snapshot current harness → baseline variants file) · `probe --variants F --taskset F --adapter deepagents --mode fake|llm --out DIR` (per-variant evidence dir + comparison `probe-report.md`; exit 0 = every probe executed, verdicts are data) · `adopt --register F --evidence DIR [--allow-fake]`. Adapter imports lazily (fundament package itself stays import-clean).

## 6. Examples — `deep-agents/harness-lab/`
`tasksets/routing-fake.json` (3–5 scripted tasks), `variants/baseline.json`, `variants/prompt-terser-orchestrator.json` (kandidaat), `variants/modelpin-qwen-submodel.json` (kandidaat).

## 7. Tests
- `poc-fundament/tests/test_harnesslab.py` (unittest, house style): loader loud-fails, verdict/adopt guards, supersedence, deterministic report, deps rule intact.
- `deep-agents/tests/test_harness_lab_adapter.py`: apply purity, prompt swap, slotgate patch (FakeTool stubs), fake-mode end-to-end probe into tmp dir, canon-deterministic evidence across two runs (canon VOLATILE pattern from minigim).
- All existing suites stay green: fundament tests, `test_fase_slotgate.py`, deep-agents offline suite.

## 8. Docs
`docs/superpowers/specs/2026-10-24-harness-lab-design.md` (harness2→fundament mapping, non-goals, adoption gate) + README sections in `poc-fundament/` and `deep-agents/`.

## 9. Verification
Run fundament + deep-agents offline suites under `nldt/.venv/bin/python`; run the fake-mode probe demo; check `ollama list` — if up, one real llm-mode probe to verify that path end-to-end, else it ships documented-but-unverified.

Explicit non-goals this iteration: poc-nspd seam adapter (follow-up), LLM-assisted proposer (`fase-2-haak`), toolGrants *adoption* (probe-able in-memory now; adoption goes through the manifest generators later).
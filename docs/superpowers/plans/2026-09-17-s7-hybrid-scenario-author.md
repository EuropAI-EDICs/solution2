# S7 Hybrid ScenarioAuthor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Productiseer S7 als det-floor + LLM-explorer (`HybridScenarioAuthor`), met nLDT default `author=hybrid`, CLI/compare regressie, en bijgewerkte seam-docs.

**Architecture:** Nieuwe `HybridScenarioAuthor` in `poc/pipeline/scenario_author.py` hergebruikt `DeterministicScenarioAuthor` + `LLMScenarioAuthor`, merget met dedupe-key `(ruleId, mutationKind, mutationParams-canonical)`, det eerst in het budget. nLDT process/recipe/MCP/critic accepteren `auto|llm|hybrid`; hybrid soft-fallback bij ontbrekende LLM. Docs leggen doctrine + benchmark-conclusie vast.

**Tech Stack:** Python 3 (unittest + pytest), bestaande PoC pipeline + nLDT process adapter. **Geen nieuwe dependencies.** Geen live LLM in CI (injecteerbare `llm_call`).

**Spec:** [`docs/superpowers/specs/2026-09-17-s7-hybrid-scenario-author-design.md`](../specs/2026-09-17-s7-hybrid-scenario-author-design.md)

## Global Constraints

- Repo root `/Users/marc/Projecten/ldttoolbox`; PoC tests: `python3 -m unittest poc.tests.test_scenario_author`; nLDT: `cd nldt && .venv/bin/pytest tests/test_poc_processes.py -q` (of project-venv).
- Doctrine: AI proposes / pipeline disposes / human decides; seam stampt `proposedBy`.
- Floor-invariant: hybrid accepted ruleId-set ⊇ deterministic accepted ruleId-set (bij zelfde budget, zolang det ≤ budget).
- Mode `llm` zonder endpoint → hard fail (`ScenarioAuthorError` / `ValueError`); mode `hybrid` zonder endpoint → det-only + ledger note `llm-unavailable`.
- Product-default nLDT recipe = `hybrid`; CLI default blijft `file` (ongewijzigd); `--author auto` blijft pure det.
- Commits per task; nooit `git add -A`; geen secrets (`.env.local`, API keys) committen.
- Breda (`poc-breda/`) buiten scope.

## File map

| File | Responsibility |
|---|---|
| `poc/pipeline/scenario_author.py` | `mutation_dedupe_key`, `HybridScenarioAuthor`, `__all__` |
| `poc/tests/test_scenario_author.py` | Hybrid unit tests (fake LLM) |
| `poc/scenarios/run.py` | `--author hybrid` wiring |
| `poc/scenarios/compare_authors.py` | hybrid leg + floor-assert + overlap fields |
| `nldt/services/process_adapter/poc_handlers.py` | `author=auto\|llm\|hybrid` |
| `nldt/recipes/utrecht-scenario-author.json` | default `hybrid` + author input |
| `nldt/services/mcp_servers/poc_server.py` | MCP default/docs for author |
| `nldt/agents/orchestrator/nodes/critic.py` | hybrid floor / llmOnly evidence |
| `nldt/tests/test_poc_processes.py` | hybrid smoke (+ mock) |
| `docs/GENAI_SEAMS.md` | S7 modes + conclusie |
| `nldt/12-governed-agent-layer.md` | statusregel |
| `docs/SOLUTIONS_ARCHITECTURE.md` | 1–2 zinnen S7 |
| `poc/README.md` | `--author hybrid` + compare note |

---

### Task 1: HybridScenarioAuthor (core merge)

**Files:**
- Modify: `poc/pipeline/scenario_author.py`
- Test: `poc/tests/test_scenario_author.py`

**Interfaces:**
- Consumes: `DeterministicScenarioAuthor.propose`, `LLMScenarioAuthor.propose` / constructor (`endpoint`, `model`, `llm_call`, `timeout`)
- Produces:
  - `mutation_dedupe_key(spec: Mapping[str, Any]) -> tuple` — stable key from sorted mutations
  - `HybridScenarioAuthor(endpoint=..., model=..., llm_call=..., timeout=..., det=..., llm=...)`
  - `HybridScenarioAuthor.propose(baseline, max_scenarios) -> Tuple[List[Dict], List[Dict]]`
  - Reject reasons: `superseded-by-deterministic`, `llm-unavailable` (kind), plus passthrough van det/llm ledgers
  - Export `HybridScenarioAuthor` in `__all__`

- [ ] **Step 1: Write the failing tests**

Append to `poc/tests/test_scenario_author.py`:

```python
class HybridAuthorTests(unittest.TestCase):

    def setUp(self):
        self.baseline = _baseline()

    def _hybrid(self, response, max_endpoint="http://localhost:9999/v1"):
        return scenario_author.HybridScenarioAuthor(
            endpoint=max_endpoint, model="test-model",
            llm_call=_fake_llm(response))

    def test_dedupe_key_stable_for_same_mutations(self):
        a = dict(VALID_PROPOSAL)
        b = dict(VALID_PROPOSAL, id="other", name="x")
        self.assertEqual(
            scenario_author.mutation_dedupe_key(a),
            scenario_author.mutation_dedupe_key(b))

    def test_floor_then_explorer_respects_budget(self):
        # LLM proposes det-covered DROP + a novel buffer on FR-T-07
        novel = {
            "id": "SC-LLM-NOVEL",
            "name": "novel buffer",
            "objectType": "wind_turbine",
            "basis": {"type": "norm_variance", "normCardId": "NC-T-07",
                      "variedAspect": "buffer 1000->750",
                      "provenanceNote": "explorer"},
            "mutations": [{"ruleId": "FR-T-07", "action": "set_buffer_distance_m",
                           "bufferDistanceM": 750}],
        }
        author = self._hybrid(json.dumps([VALID_PROPOSAL, novel]))
        specs, rejected = author.propose(self.baseline, max_scenarios=3)
        self.assertEqual(len(specs), 3)
        # first slots are det (floor)
        self.assertTrue(all(
            s["proposedBy"] == scenario_author.AUTHOR_DETERMINISTIC
            for s in specs[:3] if "LLM" not in s["id"]))
        # novel may appear only if budget left after det — with budget 3,
        # det has many drafts so novel is cut or only if we use larger budget
        specs2, rej2 = author.propose(self.baseline, max_scenarios=50)
        ids = {s["id"] for s in specs2}
        self.assertIn("SC-LLM-NOVEL", ids)
        supersede = [r for r in rej2 if r.get("kind") == "superseded-by-deterministic"]
        self.assertTrue(any(r.get("specId") == "SC-LLM-01" for r in supersede))

    def test_hybrid_without_endpoint_falls_back_to_det(self):
        import os
        os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
        author = scenario_author.HybridScenarioAuthor(endpoint="", model="m",
                                                       llm_call=_fake_llm("[]"))
        specs, rejected = author.propose(self.baseline, max_scenarios=5)
        det_specs, _ = scenario_author.DeterministicScenarioAuthor().propose(
            self.baseline, max_scenarios=5)
        self.assertEqual([s["id"] for s in specs], [s["id"] for s in det_specs])
        self.assertTrue(any(r.get("kind") == "llm-unavailable" for r in rejected))

    def test_floor_invariant_rule_ids(self):
        novel = {
            "id": "SC-LLM-NOVEL2",
            "name": "novel",
            "objectType": "wind_turbine",
            "basis": {"type": "hypothetical", "rationale": "stress",
                      "provenanceNote": "x"},
            "mutations": [{"ruleId": "FR-T-05", "action": "set_buffer_distance_m",
                           "bufferDistanceM": 42}],
        }
        author = self._hybrid(json.dumps([novel]))
        hyb, _ = author.propose(self.baseline, max_scenarios=20)
        det, _ = scenario_author.DeterministicScenarioAuthor().propose(
            self.baseline, max_scenarios=20)
        det_rules = {m["ruleId"] for s in det for m in s["mutations"]}
        hyb_rules = {m["ruleId"] for s in hyb for m in s["mutations"]}
        self.assertTrue(det_rules <= hyb_rules)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/marc/Projecten/ldttoolbox
python3 -m unittest poc.tests.test_scenario_author.HybridAuthorTests -v
```

Expected: FAIL (`HybridScenarioAuthor` / `mutation_dedupe_key` not defined).

- [ ] **Step 3: Implement minimal code in `poc/pipeline/scenario_author.py`**

Add to `__all__`: `"HybridScenarioAuthor"`, `"mutation_dedupe_key"`.

```python
def mutation_dedupe_key(spec: Mapping[str, Any]) -> tuple:
    """Stable key: sorted (ruleId, action, frozenset of remaining mutation fields)."""
    keys = []
    for m in spec.get("mutations") or []:
        if not isinstance(m, Mapping):
            continue
        rid = str(m.get("ruleId") or "")
        action = str(m.get("action") or "")
        rest = tuple(sorted(
            (str(k), json.dumps(v, sort_keys=True, default=str))
            for k, v in m.items() if k not in ("ruleId", "action")
        ))
        keys.append((rid, action, rest))
    return tuple(sorted(keys))


class HybridScenarioAuthor:
    """Deterministic floor + LLM explorer (GENAI S7 product mode)."""

    def __init__(
        self,
        endpoint: Optional[str] = None,
        model: Optional[str] = None,
        llm_call: Optional[Callable[..., str]] = None,
        timeout: Optional[float] = None,
        det: Optional["DeterministicScenarioAuthor"] = None,
        llm: Optional["LLMScenarioAuthor"] = None,
    ) -> None:
        self._det = det or DeterministicScenarioAuthor()
        if llm is not None:
            self._llm = llm
        else:
            self._llm = LLMScenarioAuthor(
                endpoint=endpoint, model=model, llm_call=llm_call, timeout=timeout)
        self.model = getattr(self._llm, "model", model or "")
        self.endpoint = getattr(self._llm, "endpoint", endpoint or "")

    def propose(
        self, baseline: Mapping[str, Any], max_scenarios: int = 10
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        det_specs, det_rej = self._det.propose(baseline, max_scenarios=max_scenarios)
        rejected: List[Dict[str, Any]] = list(det_rej)
        floor = list(det_specs)
        floor_keys = {mutation_dedupe_key(s) for s in floor}

        llm_specs: List[Dict[str, Any]] = []
        try:
            if not self._llm.endpoint:
                raise ScenarioAuthorError("LLM endpoint missing")
            llm_specs, llm_rej = self._llm.propose(baseline, max_scenarios=max_scenarios)
            rejected.extend(llm_rej)
        except ScenarioAuthorError as exc:
            rejected.append({
                "kind": "llm-unavailable",
                "reason": str(exc),
            })
            return floor, rejected

        accepted = list(floor)
        for spec in llm_specs:
            key = mutation_dedupe_key(spec)
            if key in floor_keys:
                rejected.append({
                    "kind": "superseded-by-deterministic",
                    "specId": spec.get("id"),
                    "reason": "deterministic floor already covers this mutation key",
                })
                continue
            if len(accepted) >= max_scenarios:
                rejected.append({
                    "kind": "budget-cut",
                    "specId": spec.get("id"),
                    "reason": f"effort budget: max_scenarios={max_scenarios}",
                })
                continue
            accepted.append(spec)
            floor_keys.add(key)
        return accepted, rejected
```

Note: when `endpoint` is empty string, `LLMScenarioAuthor.propose` already raises — hybrid catches that. Constructor may pass `endpoint=""` explicitly in tests.

- [ ] **Step 4: Run tests to verify they pass**

```bash
python3 -m unittest poc.tests.test_scenario_author.HybridAuthorTests -v
python3 -m unittest poc.tests.test_scenario_author -v
```

Expected: all PASS (existing det/LLM tests unchanged).

- [ ] **Step 5: Commit**

```bash
git add poc/pipeline/scenario_author.py poc/tests/test_scenario_author.py
git commit -m "$(cat <<'EOF'
Add HybridScenarioAuthor with deterministic floor and LLM explorer.

EOF
)"
```

---

### Task 2: CLI + compare_authors floor regressie

**Files:**
- Modify: `poc/scenarios/run.py` (argparse choices + author factory ~L149, ~L219)
- Modify: `poc/scenarios/compare_authors.py`
- Modify: `poc/README.md` (short `--author hybrid` note)

**Interfaces:**
- Consumes: `HybridScenarioAuthor` from Task 1
- Produces: CLI `--author hybrid`; compare JSON fields `hybrid`, `overlap.hybridAccepted`, `overlap.floorIntact` (bool); exit 1 if floorIntact is false when hybrid ran

- [ ] **Step 1: Extend `run.py` author choices**

Change argparse:

```python
ap.add_argument("--author", choices=("file", "auto", "llm", "hybrid"), default="file",
```

Author factory (~L219):

```python
        if args.author == "auto":
            author_obj = scenario_author.DeterministicScenarioAuthor()
        elif args.author == "hybrid":
            author_obj = scenario_author.HybridScenarioAuthor()
        else:
            author_obj = scenario_author.LLMScenarioAuthor()
```

Update `scenario_set_id` / stage labels so hybrid uses e.g. `SSET-hybrid-{model}` and stage run id `hybrid-proposal#{model}` (or `deterministic-scenario-author#poc-v1-auto` when LLM skipped — optional; prefer always `hybrid-proposal#…`).

Also dump `"author": "hybrid"` in `proposals.json`.

- [ ] **Step 2: Extend `compare_authors.py`**

After the LLM block, always run hybrid with injectable path when endpoint set; when no endpoint, still run hybrid (soft det fallback) and record it:

```python
    t2 = time.perf_counter()
    hyb = scenario_author.HybridScenarioAuthor()
    hyb_specs, hyb_rej = hyb.propose(baseline, args.max_scenarios)
    hyb_stats = _author_stats(hyb_specs, hyb_rej)
    hyb_stats["seconds"] = round(time.perf_counter() - t2, 3)
    hyb_stats["model"] = getattr(hyb, "model", None)

    det_ids = {s["id"] for s in det_specs}  # need to keep det_specs in scope
    # Floor invariant: every det accepted id must appear in hybrid accepted
    # (same budget). Use ids — det specs are copied into hybrid floor unchanged.
    floor_intact = det_ids <= {s["id"] for s in hyb_specs}
```

Add to comparison dict:

```python
        "hybrid": hyb_stats,
        "overlap": {
            "bothTarget": sorted(det_rules & llm_rules),
            "llmOnly": sorted(llm_rules - det_rules),
            "deterministicOnly": sorted(det_rules - llm_rules),
            "hybridAccepted": hyb_stats["scenarioIds"],
            "floorIntact": floor_intact,
        },
```

Exit code:

```python
    bad_llm = bool(llm_error and endpoint)
    bad_floor = not floor_intact
    return 1 if (bad_llm or bad_floor) else 0
```

Keep `det_specs` variable (currently only stats kept — store the list).

- [ ] **Step 3: README one-liner**

In `poc/README.md` near the existing `--author auto|llm` block, add:

```markdown
python3 poc/scenarios/run.py --author hybrid  # det floor + LLM explorer (S7 product mode)
```

- [ ] **Step 4: Smoke (offline)**

```bash
# no endpoint — hybrid == det; floorIntact true
env -u LDT_SCENARIO_LLM_ENDPOINT python3 poc/scenarios/compare_authors.py --use-case wind --max-scenarios 5
```

Expected: exit 0; `comparison.json` has `"floorIntact": true` and hybrid stats.

- [ ] **Step 5: Commit**

```bash
git add poc/scenarios/run.py poc/scenarios/compare_authors.py poc/README.md
git commit -m "$(cat <<'EOF'
Wire hybrid author into scenario CLI and compare_authors floor check.

EOF
)"
```

---

### Task 3: nLDT process + recipe + MCP

**Files:**
- Modify: `nldt/services/process_adapter/poc_handlers.py` (`execute_scenario_author_propose` ~L423–451)
- Modify: `nldt/recipes/utrecht-scenario-author.json`
- Modify: `nldt/services/mcp_servers/poc_server.py` (default `author` docstring if present)
- Test: `nldt/tests/test_poc_processes.py`

**Interfaces:**
- Consumes: `HybridScenarioAuthor`, `LLMScenarioAuthor`, `DeterministicScenarioAuthor`
- Produces: handler accepts `author ∈ {auto,llm,hybrid}`; response `proposals.author` echoes mode; recipe default `hybrid`; optional recipe input `author`

- [ ] **Step 1: Failing test for hybrid soft path**

Add to `nldt/tests/test_poc_processes.py`:

```python
def test_scenario_author_propose_hybrid_without_llm_falls_back():
    baseline = WORKSPACE / "poc" / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline run missing")
    import os
    os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
    out = execute_local(
        "scenario-author-propose",
        {"baselineRunDir": str(baseline), "author": "hybrid", "maxScenarios": 5},
    )
    proposals = out["proposals"]
    assert proposals["author"] == "hybrid"
    assert proposals["acceptedCount"] >= 1
    kinds = {r.get("kind") for r in proposals["rejected"]}
    assert "llm-unavailable" in kinds


def test_scenario_author_propose_llm_requires_endpoint():
    baseline = WORKSPACE / "poc" / "runs" / "20260830T113234Z-wind"
    if not (baseline / "formalrules.json").is_file():
        pytest.skip("wind baseline run missing")
    import os
    os.environ.pop("LDT_SCENARIO_LLM_ENDPOINT", None)
    with pytest.raises(Exception):
        execute_local(
            "scenario-author-propose",
            {"baselineRunDir": str(baseline), "author": "llm", "maxScenarios": 2},
        )
```

- [ ] **Step 2: Run to verify fail**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
.venv/bin/pytest tests/test_poc_processes.py::test_scenario_author_propose_hybrid_without_llm_falls_back -q
```

Expected: FAIL (`author=auto only` ValueError).

- [ ] **Step 3: Implement handler**

Replace `execute_scenario_author_propose` body selection:

```python
def execute_scenario_author_propose(inputs: dict[str, Any]) -> dict[str, Any]:
    _ensure_poc_on_path()
    from pipeline import scenario_author, scenarios  # type: ignore
    from scenarios import run as scen_run  # type: ignore

    author_mode = str(inputs.get("author") or "auto")
    if author_mode not in ("auto", "llm", "hybrid"):
        raise ValueError("author must be auto|llm|hybrid")

    use_case = inputs.get("useCase") or "wind"
    baseline_dir = _resolve_dir(
        inputs.get("baselineRunDir"),
        default=scen_run.latest_baseline_run(use_case),
    )
    max_n = int(inputs.get("maxScenarios") or 10)
    baseline = scenarios.load_baseline(baseline_dir)

    if author_mode == "auto":
        author_obj = scenario_author.DeterministicScenarioAuthor()
    elif author_mode == "llm":
        author_obj = scenario_author.LLMScenarioAuthor()
        if not author_obj.endpoint:
            raise ValueError(
                "author=llm requires LDT_SCENARIO_LLM_ENDPOINT "
                "(use author=hybrid for det fallback)"
            )
    else:
        author_obj = scenario_author.HybridScenarioAuthor()

    try:
        specs, rejected = author_obj.propose(baseline, max_scenarios=max_n)
    except scenario_author.ScenarioAuthorError as exc:
        raise ValueError(str(exc)) from exc

    return {
        "proposals": {
            "baselineRunDir": str(baseline_dir),
            "author": author_mode,
            "authorModel": str(getattr(author_obj, "model", "") or ""),
            "accepted": specs,
            "acceptedCount": len(specs),
            "rejected": rejected,
            "rejectedCount": len(rejected),
        }
    }
```

Also update process catalog description in `POC_PROCESS_SPECS` / `"scenario-author-propose"` if it mentions auto-only (search same file ~L52).

- [ ] **Step 4: Recipe + MCP**

`nldt/recipes/utrecht-scenario-author.json`:

- description → mention hybrid floor+explorer
- add optional input `author` (string, `auto|llm|hybrid`)
- step inputs: `"author": "${recipe.inputs.author}"` with fallback — if recipe runner does not support defaulting missing `${}`, keep step default `"hybrid"` and document override via process execute. Prefer:

```json
"inputs": {
  "author": {
    "type": "string",
    "description": "auto|llm|hybrid (default hybrid)",
    "required": false
  },
  ...
},
"steps": [{
  ...
  "inputs": {
    "author": "hybrid",
    "useCase": "${recipe.inputs.useCase}",
    "baselineRunDir": "${recipe.inputs.baselineRunDir}",
    "maxScenarios": "${recipe.inputs.maxScenarios}"
  }
}]
```

If the recipe engine merges recipe-level inputs over step defaults, wire `"author": "${recipe.inputs.author}"` only when that pattern is already used elsewhere; otherwise hardcode step `"author": "hybrid"` as product default (spec D2).

`poc_server.py`: change default `author: str = "hybrid"` on `propose_scenarios` if signature has default `"auto"`.

- [ ] **Step 5: Run tests**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
.venv/bin/pytest tests/test_poc_processes.py::test_scenario_author_propose_auto \
  tests/test_poc_processes.py::test_scenario_author_propose_hybrid_without_llm_falls_back \
  tests/test_poc_processes.py::test_scenario_author_propose_llm_requires_endpoint -q
```

Expected: PASS (llm test raises).

- [ ] **Step 6: Commit**

```bash
git add nldt/services/process_adapter/poc_handlers.py \
  nldt/recipes/utrecht-scenario-author.json \
  nldt/services/mcp_servers/poc_server.py \
  nldt/tests/test_poc_processes.py
git commit -m "$(cat <<'EOF'
Productise S7 author modes auto|llm|hybrid in nLDT process and recipe.

EOF
)"
```

---

### Task 4: Critic hybrid evidence

**Files:**
- Modify: `nldt/agents/orchestrator/nodes/critic.py` (~L72–93)
- Test: add assertions in existing critic tests if present; else create focused unit test under `nldt/tests/`

**Interfaces:**
- Consumes: `proposals.author`, `proposals.accepted`, `proposals.rejected`
- Produces: checks `s7-hybrid-floor` (pass if any accepted has `proposedBy` starting with `deterministic-scenario-author` OR rejected contains `all`-style note; fail only if author=hybrid, accepted non-empty, zero det stamps AND no `llm-unavailable` covering empty det — actually: if hybrid and accepted>0 and none are det-stamped → fail `s7-hybrid-floor`; if hybrid and `llm-unavailable` in rejected → pass with detail). Also `s7-llm-explorer` pass with detail count of accepted where `proposedBy` startswith `llm-proposal`.

- [ ] **Step 1: Locate critic tests**

```bash
rg -n "s7-proposals|critic" nldt/tests --glob '*.py'
```

If none, add `nldt/tests/test_critic_s7.py` importing the critic check function (or the node helper that builds `checks_v2`). Read `critic.py` top for the function name wrapping the recipe branch (likely `run_critic` / `_checks_for_recipe`).

- [ ] **Step 2: Failing test**

```python
def test_critic_hybrid_floor_and_explorer():
    # Build minimal outputs mimicking author recipe result
    outputs = {
        "proposals": {
            "author": "hybrid",
            "accepted": [
                {"id": "SC-A", "proposedBy": "deterministic-scenario-author#poc-v1-auto",
                 "mutations": [{"ruleId": "FR-1", "action": "drop"}]},
                {"id": "SC-B", "proposedBy": "llm-proposal#test-model",
                 "mutations": [{"ruleId": "FR-2", "action": "drop"}]},
            ],
            "rejected": [],
            "acceptedCount": 2,
        }
    }
    # call the same helper the node uses — adjust import to actual symbol
    from agents.orchestrator.nodes.critic import build_v2_checks_for_recipe  # rename if needed
    checks, verdict = build_v2_checks_for_recipe("utrecht-scenario-author", outputs)
    ids = {c["id"]: c for c in checks}
    assert ids["s7-proposals"]["status"] == "pass"
    assert ids["s7-hybrid-floor"]["status"] == "pass"
    assert ids["s7-llm-explorer"]["status"] == "pass"
    assert "1" in ids["s7-llm-explorer"].get("detail", "")
```

If `build_v2_checks_for_recipe` does not exist, extract the recipe branch into a testable function as part of this task (small refactor, no behavior change for other recipes).

- [ ] **Step 3: Implement critic branch**

Inside `utrecht-scenario-author` success path, after `s7-proposals`:

```python
            author_mode = summary.get("author") or "auto"
            accepted_list = summary.get("accepted") if isinstance(summary.get("accepted"), list) else []
            if author_mode == "hybrid":
                det_n = sum(
                    1 for s in accepted_list
                    if str(s.get("proposedBy") or "").startswith("deterministic-scenario-author")
                )
                llm_n = sum(
                    1 for s in accepted_list
                    if str(s.get("proposedBy") or "").startswith("llm-proposal")
                )
                rej = summary.get("rejected") or []
                llm_down = any(r.get("kind") == "llm-unavailable" for r in rej if isinstance(r, dict))
                if det_n >= 1 or (not accepted_list and rej):
                    checks_v2.append({"id": "s7-hybrid-floor", "status": "pass",
                                      "detail": f"det={det_n}"})
                elif llm_down and det_n == 0 and not accepted_list:
                    checks_v2.append({"id": "s7-hybrid-floor", "status": "pass",
                                      "detail": "llm-unavailable; empty"})
                else:
                    checks_v2.append({"id": "s7-hybrid-floor", "status": "fail",
                                      "detail": "hybrid accepted without deterministic floor"})
                    verdict = "fail"
                checks_v2.append({
                    "id": "s7-llm-explorer",
                    "status": "pass",
                    "detail": f"llmOnly-accepted={llm_n}" + ("; llm-unavailable" if llm_down else ""),
                })
```

- [ ] **Step 4: Run tests + commit**

```bash
cd /Users/marc/Projecten/ldttoolbox/nldt
.venv/bin/pytest tests/test_critic_s7.py tests/test_poc_processes.py -q
```

```bash
git add nldt/agents/orchestrator/nodes/critic.py nldt/tests/test_critic_s7.py
git commit -m "$(cat <<'EOF'
Extend S7 critic with hybrid floor and explorer evidence checks.

EOF
)"
```

---

### Task 5: Docs (GENAI_SEAMS, governed layer, SoA)

**Files:**
- Modify: `docs/GENAI_SEAMS.md` (S7 row ~L205 + Phase B notes ~L213)
- Modify: `nldt/12-governed-agent-layer.md` (~L48 status)
- Modify: `docs/SOLUTIONS_ARCHITECTURE.md` (1–2 zinnen near scenario/S7 mention)
- Modify: `nldt/11-poc-patterns-scenarios-qa.md` if it lists `--author file|auto|llm` only

- [ ] **Step 1: Update GENAI_SEAMS S7**

Replace/extend the S7 table cell to include hybrid:

```markdown
| S7 | scenario authoring (file/auto/llm/**hybrid**; det-floor + LLM-explorer; ledger; control reproduction) | 1 · **4** | **implemented** — hybrid product default in nLDT `utrecht-scenario-author`; PoC `poc/pipeline/scenario_author.py` (`HybridScenarioAuthor`); golden-set via `poc/scenarios/compare_authors.py` (floorIntact) |
```

Add a short bullet under Phase B lessons:

```markdown
- S7 product mode = **hybrid**: deterministic proposals are the floor; LLM may only add novel `(ruleId, mutation)` keys. Det remains planning-truth; LLM is explorer/tolk. Benchmark: prefer det for coverage regressie; use LLM for extra candidates under HITL.
```

- [ ] **Step 2: Update `12-governed-agent-layer.md`**

```markdown
| `scenario-author-propose` | ✅ | S7 auto\|llm\|**hybrid** (default hybrid) |
```

- [ ] **Step 3: SoA + patterns one-liner**

In `SOLUTIONS_ARCHITECTURE.md` find ScenarioAuthor / S7 mention and add that nLDT defaults to hybrid propose-only. In `11-poc-patterns-scenarios-qa.md` extend author list to `file|auto|llm|hybrid`.

- [ ] **Step 4: Commit**

```bash
git add docs/GENAI_SEAMS.md docs/SOLUTIONS_ARCHITECTURE.md \
  nldt/12-governed-agent-layer.md nldt/11-poc-patterns-scenarios-qa.md
git commit -m "$(cat <<'EOF'
Document S7 hybrid author mode as nLDT product default.

EOF
)"
```

---

## Self-review (plan vs spec)

| Spec requirement | Task |
|---|---|
| Hybrid det-floor + LLM-explorer | T1 |
| Dedupe `(ruleId, mutationKind, params)` | T1 `mutation_dedupe_key` |
| `superseded-by-deterministic` / `llm-unavailable` | T1 |
| Modes auto\|llm\|hybrid; product default hybrid | T2 CLI, T3 recipe |
| nLDT handler + MCP | T3 |
| Critic light hybrid evidence | T4 |
| compare floor ⊇ det | T2 |
| Docs GENAI_SEAMS / governed / SoA | T5 |
| No Breda / no V4 HITL / no end-to-end propose→sweep recipe | omitted by design |

Placeholder scan: none. Type names consistent: `HybridScenarioAuthor`, `mutation_dedupe_key`, reject kinds as above.

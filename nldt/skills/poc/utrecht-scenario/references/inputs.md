# Utrecht scenario — tool inputs

## `propose_scenarios`

| Param | Required | Notes |
|-------|----------|-------|
| `baselineRunDir` | yes | Baseline opportunity-map / corridor run. |
| `author` | no | `hybrid` (default) \| `auto` \| `llm` \| `file`. |
| `maxScenarios` | no | Cap on proposals (default 10). |

Process: `scenario-author-propose` · Recipe: `utrecht-scenario-author`.

## `run_scenario_sweep`

| Param | Required | Notes |
|-------|----------|-------|
| `useCase` | yes | Scenario family (e.g. wind, zon, bos). |
| `baselineRunDir` | no | Baseline for delta computation. |
| `author` | no | Author mode when generating inline. |
| `scenarioSetPath` | no | Explicit scenario set file. |
| `outDir` | no | Output directory. |
| `noH3` | no | Default true — skip heavy H3 unless needed. |

Process: `scenario-sweep` · Recipe: `utrecht-scenario-sweep`.

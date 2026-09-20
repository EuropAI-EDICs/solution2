# Breda scan — tool inputs

## `run_value_scan`

| Param | Required | Notes |
|-------|----------|-------|
| `mode` | no | Default `replay`. Use execute only with valid baseline/layers. |
| `runDir` | no | Existing run directory when replaying a specific pack. |

Process: `breda-scan-run` · Recipe: `breda-five-value-scan`.

## `ask_scan`

| Param | Required | Notes |
|-------|----------|-------|
| `question` | yes | Natural-language question about scan artefacts. |
| `runDir` | no | Scan run to ground answers; omit for default/offline seed. |
| `asker` | no | Default `auto` (S4 cite-or-abstain). |

Process: `breda-scan-query` · Recipe: `breda-scan-qa`.

# Breda scan — artefacts

Tool responses wrap process-adapter jobs:

```json
{
  "tool": "run_value_scan",
  "processId": "breda-scan-run",
  "jobId": "…",
  "status": "successful",
  "outputs": {},
  "prov": {}
}
```

Typical engine artefacts under the run directory:

- Value / indicator scores and maps (five-value composition)
- Q&A answers with citations or abstention
- Orchestrated runs also emit `validation-report.json` + `prov.json` under `nldt/data/runs/<runId>/`

Never invent indicator values that are absent from `outputs` or run files.

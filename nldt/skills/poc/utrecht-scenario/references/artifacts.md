# Utrecht scenario — artefacts

Tool responses wrap process jobs (`jobId`, `status`, `outputs`, `prov`).

Expect among outputs / run dirs:

- Scenario proposals with identity stamps (`proposedBy`)
- Reject ledger (`proposals-rejected.json` / `reject-ledger.json`) when present
- Sweep reports and deltas vs baseline
- Orchestrator: `validation-report.json` + `prov.json`

Cite only numbers present in those artefacts. Hybrid floor must stay intact (`floorIntact` in compare tooling).

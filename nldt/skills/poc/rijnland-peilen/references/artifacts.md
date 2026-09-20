# Rijnland water levels — artefacts

Tool responses wrap process-adapter jobs (`jobId`, `status`, `outputs`, `prov`).

Typical artefacts:

- Peil conflict report / H3 overlays (`peil-conflict-report.*`, `h3-peil-conflict.*`)
- Measured-level time page / hex animation (`run_peilen.py`)
- What-if multi-scenario Leaflet map (CDC demo pack)
- Lake silver observations + ES hits for `poc=rijnland` peil series
- Orchestrated runs: `validation-report.json` + `prov.json` under `nldt/data/runs/<runId>/`

Never invent water levels (mNAP) or conflict counts absent from `outputs` or run files.

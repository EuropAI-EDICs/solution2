# Fixture: run-wind

Kleine, deterministische stand-in voor een task-9/10-run-directory: bevat alleen
`zones-wind-nspd.geojson` (2 features, één per land) zoals `write_xborder_report`
die schrijft, gegenereerd met `merge_xborder` op de twee mini-test-FC's uit
`tests/test_xborder.py` (`_fc("nl")` / `_fc("be")`).

Regenereren vanaf `poc-nspd/`:

```bash
.venv/bin/python - <<'EOF'
import json, sys
from pathlib import Path
sys.path.insert(0, ".")
from pipeline.xborder import merge_xborder

def _fc(land):
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"ruleId": f"FR-{land}-01", "jurisdictie": land},
            "geometry": {"type": "Polygon", "coordinates": [[[3.5, 51.1], [3.6, 51.1], [3.6, 51.2], [3.5, 51.2], [3.5, 51.1]]]},
        }],
    }

merged = merge_xborder(
    {"land": "nl", "zones": _fc("nl"), "decisionRows": [{"id": "FR-NL-01", "land": "nl"}]},
    {"land": "be", "zones": _fc("be"), "decisionRows": [{"id": "FR-BE-01", "land": "be"}]},
    track="wind",
)
Path("tests/fixtures/viewer/run-wind/zones-wind-nspd.geojson").write_text(
    json.dumps(merged["zones"], ensure_ascii=False), encoding="utf-8")
EOF
```

Wordt gebruikt door `tests/test_viewer_config.py` (task 11). Bewust klein —
geen echte run-output in de repo.

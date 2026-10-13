"""Threshold triggers → Waterpump ON/OFF events + gemaal advice.

The thesis triggered pumps geometrically (GWT mesh touching the terrain)
and sent ``WaterpumpON/OFF`` events over IFTTT webhooks. Numeric
thresholds were its own future work ("identification of thresholds");
here they are explicit CLI parameters:

- depth ≤ ``ingress`` (m onder maaiveld) → ``WaterpumpON``  (ingress risk)
- depth ≥ ``drought``  (m onder maaiveld) → ``WaterpumpOFF`` + retain water
- otherwise → ``Monitor``

Each ON/OFF event is matched to the nearest gemaal within a radius; beyond
it the cell is an **action gap** (thesis recommendation 3: strategic
positioning of sensors and pumps). ``commands.json`` is the IFTTT-contract
equivalent — machine-actionable events; actual actuation is out of scope.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

MONITOR = "Monitor"
PUMP_ON = "WaterpumpON"
PUMP_OFF = "WaterpumpOFF"
RETAIN = "RetainWater"


def evaluate(depth: Optional[float], *, ingress: float,
             drought: float) -> Dict[str, Any]:
    """One depth → action dict (event, retain flag, reason)."""
    if depth is None:
        return {"event": MONITOR, "retain": False, "reason": "no value"}
    if depth <= ingress:
        return {"event": PUMP_ON, "retain": False,
                "reason": f"depth {depth:.2f} ≤ ingress {ingress:.2f} m -mv"}
    if depth >= drought:
        return {"event": PUMP_OFF, "retain": True,
                "reason": f"depth {depth:.2f} ≥ drought {drought:.2f} m -mv; "
                          f"vasthouden in plaats van malen"}
    return {"event": MONITOR, "retain": False, "reason": "within band"}


def nearest_gemaal(x: float, y: float,
                   gemalen: Sequence[Mapping[str, Any]], *,
                   radius_m: float) -> Tuple[Optional[Dict[str, Any]], float]:
    """RD-euclidean nearest gemaal within radius, else (None, best_dist)."""
    best: Tuple[Optional[Dict[str, Any]], float] = (None, float("inf"))
    for g in gemalen:
        d = math.hypot(float(g["x"]) - x, float(g["y"]) - y)
        if d < best[1]:
            best = (dict(g), d)
    g, d = best
    if g is not None and d <= radius_m:
        return g, round(d, 1)
    return None, round(d, 1) if math.isfinite(d) else None


def build_commands(forecasts_by_code: Mapping[str, Mapping[str, Any]],
                   loggers_by_code: Mapping[str, Mapping[str, Any]],
                   gemalen: Sequence[Mapping[str, Any]], *, ingress: float,
                   drought: float, radius_m: float
                   ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Per forecast day per logger: command rows + aggregate summary."""
    rows: List[Dict[str, Any]] = []
    per_day: Dict[str, Dict[str, int]] = {}
    for code, fc in sorted(forecasts_by_code.items()):
        lg = loggers_by_code.get(code) or {}
        gemaal, dist = nearest_gemaal(lg.get("x", 0.0), lg.get("y", 0.0),
                                      gemalen, radius_m=radius_m)
        for step in fc.get("forecast", []):
            action = evaluate(step.get("depth"), ingress=ingress,
                              drought=drought)
            if action["event"] == MONITOR:
                day = per_day.setdefault(step["date"], {MONITOR: 0, PUMP_ON: 0,
                                                        PUMP_OFF: 0, "gaps": 0})
                day[MONITOR] += 1
                continue
            gap = gemaal is None
            rows.append({
                "date": step["date"],
                "event": action["event"],
                "retain": action["retain"],
                "reason": action["reason"],
                "loggerCode": code,
                "loggerName": lg.get("name"),
                "polder": lg.get("polder"),
                "depth": step.get("depth"),
                "gemaal": ({"code": gemaal["code"], "name": gemaal.get("name"),
                            "capaciteit": gemaal.get("capaciteit")}
                           if gemaal else None),
                "distanceM": dist,
                "gap": gap,
            })
            day = per_day.setdefault(step["date"], {MONITOR: 0, PUMP_ON: 0,
                                                    PUMP_OFF: 0, "gaps": 0})
            day[action["event"]] += 1
            if gap:
                day["gaps"] += 1
    rows.sort(key=lambda r: (r["date"], r["loggerCode"]))
    summary = {
        "days": [{**{"date": d}, **counts}
                 for d, counts in sorted(per_day.items())],
        "totalCommands": len(rows),
        "totalGaps": sum(1 for r in rows if r["gap"]),
    }
    return rows, summary

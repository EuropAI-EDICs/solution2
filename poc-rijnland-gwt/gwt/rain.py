"""Daily precipitation from open-meteo (keyless) — thesis-equivalent of the
KNMI RH(mm) join. One 3×3 grid over the AOI; per-date area mean in mm.

Cache-first: ``data/rain/rain-<fp>.json`` keyed by grid + window + today,
so repeated runs on the same day don't re-hit the API. ``--refresh-rain``
forces a re-download.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from pyproj import Transformer

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEZONE = "Europe/Amsterdam"
RAIN_VERSION = "poc-rijnland-gwt-rain/0.1"


def grid_points(bbox: Sequence[float], n: int = 3) -> List[Tuple[float, float]]:
    """EPSG:28992 bbox → n×n grid of WGS84 (lat, lon) points."""
    xmin, ymin, xmax, ymax = [float(v) for v in bbox]
    tr = Transformer.from_crs("EPSG:28992", "EPSG:4326", always_xy=True)
    pts = []
    for iy in range(n):
        for ix in range(n):
            fx = (ix + 0.5) / n
            fy = (iy + 0.5) / n
            x = xmin + fx * (xmax - xmin)
            y = ymin + fy * (ymax - ymin)
            lon, lat = tr.transform(x, y)
            pts.append((round(lat, 4), round(lon, 4)))
    return pts


def _fingerprint(lats, lons, days_back, forecast_days) -> str:
    blob = json.dumps([lats, lons, days_back, forecast_days], separators=(",", ":"))
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:12]


def _get(session, url: str, params: Dict[str, Any], timeout: int):
    resp = session.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def _daily_from_payload(payload) -> List[Dict[str, Any]]:
    """open-meteo returns one object per location (list) when several are
    requested; normalise to a list of {time:[...], precipitation_sum:[...]}."""
    items = payload if isinstance(payload, list) else [payload]
    out = []
    for it in items:
        daily = (it or {}).get("daily") or {}
        out.append({"time": daily.get("time") or [],
                    "precipitation_sum": daily.get("precipitation_sum") or []})
    return out


def _area_mean(items: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    by_date: Dict[str, List[float]] = {}
    for it in items:
        for d, v in zip(it["time"], it["precipitation_sum"]):
            if v is None:
                continue
            by_date.setdefault(d, []).append(float(v))
    return {d: round(sum(vs) / len(vs), 2) for d, vs in sorted(by_date.items())}


def fetch_rain(bbox: Sequence[float], *, days_back: int = 90,
               forecast_days: int = 5, cache_dir: Path,
               session=None, timeout: int = 60,
               refresh: bool = False) -> Dict[str, Any]:
    """Return {past: {date: mm}, forecast: {date: mm}, provenance {...}}."""
    import requests

    pts = grid_points(bbox)
    lats = ",".join(str(p[0]) for p in pts)
    lons = ",".join(str(p[1]) for p in pts)
    today = _dt.date.today()
    start = (today - _dt.timedelta(days=days_back - 1)).isoformat()
    end_y = (today - _dt.timedelta(days=1)).isoformat()
    fp = _fingerprint([p[0] for p in pts], [p[1] for p in pts],
                      days_back, forecast_days)
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f"rain-{fp}-{today.isoformat()}.json"
    if cache.exists() and not refresh:
        try:
            doc = json.loads(cache.read_text(encoding="utf-8"))
            if doc.get("version") == RAIN_VERSION:
                return doc
        except (json.JSONDecodeError, OSError):
            pass

    session = session or requests.Session()
    past_items = _daily_from_payload(_get(session, ARCHIVE_URL, {
        "latitude": lats, "longitude": lons,
        "start_date": start, "end_date": end_y,
        "daily": "precipitation_sum", "timezone": TIMEZONE,
    }, timeout))
    fc_items = _daily_from_payload(_get(session, FORECAST_URL, {
        "latitude": lats, "longitude": lons,
        "forecast_days": forecast_days,
        "daily": "precipitation_sum", "timezone": TIMEZONE,
    }, timeout))

    doc = {
        "version": RAIN_VERSION,
        "fetchedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"),
        "source": "open-meteo (ERA5-derived archive + forecast), keyless",
        "grid": {"n": 3, "points": pts},
        "past": _area_mean(past_items),
        "forecast": _area_mean(fc_items),
    }
    cache.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                     encoding="utf-8")
    return doc


def rain_series(rain: Dict[str, Any]) -> List[Tuple[str, float]]:
    """Merged {date: mm} past+forecast as a sorted [(date, mm)] list."""
    merged: Dict[str, float] = {}
    merged.update(rain.get("past") or {})
    merged.update(rain.get("forecast") or {})
    return sorted(merged.items())

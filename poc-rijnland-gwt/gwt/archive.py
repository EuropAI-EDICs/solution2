"""Growing groundwater-depth archive (``data/gwt/gwt.json``).

Because no open Rijnland GWT series resolves today (design §4), the archive
is **seeded deterministically** per logger from open metadata + measured
open-meteo rain: seasonal sinusoid + rain response + recession, parameters
hashed (crc32) from the logger code so every machine/run reproduces the
same series. When a BRO/Lizard fetch lands real series, ``merge_real``
overwrites the seed per logger and the rest of the pipeline runs unchanged
— the exact growing-archive pattern of PoC-3 fase 2d.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
import zlib
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from .sensors import SEED_REASON

ARCHIVE_VERSION = "poc-rijnland-gwt-archive/0.1"
DEPTH_MIN, DEPTH_MAX = 0.15, 2.6


def _fracs(code: str, n: int = 6) -> List[float]:
    """Stable per-code pseudo-random fracs in [0,1) — not Python hash()."""
    out, salt = [], b""
    while len(out) < n:
        digest = zlib.crc32(code.encode("utf-8") + salt)
        for shift in range(0, 28, 4):
            out.append(((digest >> shift) & 0xFFFF) / 65535.0)
            if len(out) >= n:
                break
        salt += b"|"
    return out[:n]


def _day_noise(code: str, date_iso: str) -> float:
    """Deterministic small daily wiggle in [-1, 1)."""
    digest = zlib.crc32(f"{code}|{date_iso}".encode("utf-8"))
    return ((digest >> 8) & 0xFFFF) / 32767.5 - 1.0


def depth_for(logger: Mapping[str, Any], date_iso: str,
              rain3: float, doy: int) -> float:
    """Seeded depth (m onder maaiveld) for one logger/day.

    base + seasonal − rain response (rain raises the table → depth down)
    + small deterministic noise, clamped to plausible polder depths.
    """
    f = _fracs(str(logger["code"]))
    base = 0.55 + 0.90 * f[0]
    amp = 0.10 + 0.15 * f[1]
    phase = 2.0 * math.pi * f[2]
    response = 0.02 + 0.03 * f[3]
    depth = (base
             + amp * math.sin(2.0 * math.pi * (doy - 45) / 365.0 + phase)
             - response * rain3
             + 0.02 * _day_noise(str(logger["code"]), date_iso))
    return round(min(max(depth, DEPTH_MIN), DEPTH_MAX), 3)


def seed_days(dates: List[str], rain_by_date: Mapping[str, float]
              ) -> Dict[str, Dict[str, float]]:
    """Per date: the 3-day rain sum (mm) the response acts on."""
    out = {}
    for d in dates:
        r = rain_by_date.get(d)
        out[d] = {"rain": float(r) if r is not None else 0.0}
    return out


def _doy(date_iso: str) -> int:
    return _dt.date.fromisoformat(date_iso).timetuple().tm_yday


def seed_loggers(loggers: List[Mapping[str, Any]],
                 past_rain: Mapping[str, float], dates: List[str]
                 ) -> Dict[str, Dict[str, Any]]:
    """{code: {name, polder, x, y, days: {date: {"depth": m}}}}."""
    rain_by_date = {d: float(past_rain.get(d) or 0.0) for d in dates}
    # 3-day trailing sum per date
    rain3: Dict[str, float] = {}
    for i, d in enumerate(dates):
        window = dates[max(0, i - 2):i + 1]
        rain3[d] = round(sum(rain_by_date[w] for w in window), 2)
    out: Dict[str, Dict[str, Any]] = {}
    for lg in loggers:
        days = {d: {"depth": depth_for(lg, d, rain3[d], _doy(d))}
                for d in dates}
        out[str(lg["code"])] = {
            "name": lg["name"],
            "polder": lg.get("polder"),
            "x": lg["x"], "y": lg["y"],
            "days": days,
        }
    return out


def load_or_seed(path: Path, loggers: List[Mapping[str, Any]],
                 past_rain: Mapping[str, float], dates: List[str],
                 *, reseed: bool = False) -> Dict[str, Any]:
    """Cache-first archive: seed missing loggers / days, keep existing.

    ``reseed=True`` (CLI ``--reseed``) discards the current file — use when
    the seeding formula itself changed.
    """
    path = Path(path)
    doc: Dict[str, Any]
    if path.exists() and not reseed:
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            doc = {}
    else:
        doc = {}
    seeded_loggers = doc.setdefault("loggers", {})
    for lg in loggers:
        code = str(lg["code"])
        entry = seeded_loggers.get(code)
        if not entry or not entry.get("days"):
            seeded_loggers[code] = seed_loggers([lg], past_rain, dates)[code]
            continue
        days = entry.setdefault("days", {})
        rain3 = seed_days(dates, past_rain)  # {date: {rain}}
        for d in dates:
            if d in days:
                continue
            window_dates = [w for w in rain3 if w <= d][-3:]
            r3 = round(sum(rain3[w]["rain"] for w in window_dates), 2)
            days[d] = {"depth": depth_for(lg, d, r3, _doy(d))}
    doc.update({
        "version": ARCHIVE_VERSION,
        "unit": "m-onder-maaiveld",
        "syntheticSeed": True,
        "seedReason": SEED_REASON,
        "seedFormula": ("depth = base + amp*sin(2π(doy-45)/365 + φ) "
                        "− response*rain3 + 0.02*noise(code,date), "
                        "clamped 0.15–2.6; base/amp/φ/response hashed "
                        "from the logger code (crc32)"),
        "updatedAt": _dt.datetime.now(_dt.timezone.utc).isoformat(
            timespec="seconds"),
    })
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n",
                    encoding="utf-8")
    return doc


def merge_real(archive: Dict[str, Any], series_by_code: Mapping[str, Any]
               ) -> Dict[str, Any]:
    """Hook for the future BRO/Lizard fetch: overwrite seeded days with
    measured series ({"code": {"days": {date: {"depth": m}}}}); a logger
    becomes fully real once its seed flag is dropped."""
    for code, series in series_by_code.items():
        entry = archive.setdefault("loggers", {}).setdefault(str(code), {})
        entry.setdefault("days", {}).update(series.get("days") or {})
        if series.get("measured"):
            entry["measured"] = True
    return archive

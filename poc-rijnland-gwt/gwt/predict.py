"""Rain-driven depth prediction per logger.

A minimal regression decision tree (variance-reduction CART, numpy only —
no sklearn) re-implementing the thesis's interpretable
``DecisionTreeRegressor`` choice: features depth lag-1, depth lag-3 mean,
rain 1/3/10-day sums, day-of-year sin/cos; target depth(t+1); recursive
day-ahead forecast on open-meteo forecast rain; holdout MSE/MAE against a
persistence baseline (the thesis published no accuracy numbers).
"""

from __future__ import annotations

import datetime as _dt
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

PREDICT_VERSION = "poc-rijnland-gwt-predict/0.1"
MIN_ROWS = 30  # below this: persistence forecast (flagged in output)


# ---------------------------------------------------------------- CART core

class _Node:
    __slots__ = ("feature", "threshold", "left", "right", "value")

    def __init__(self, value: float, feature: int = -1, threshold: float = 0.0,
                 left: "_Node" = None, right: "_Node" = None):
        self.value = value
        self.feature = feature
        self.threshold = threshold
        self.left = left
        self.right = right

    def predict(self, x: Sequence[float]) -> float:
        node = self
        while node.feature >= 0:
            node = node.left if x[node.feature] <= node.threshold else node.right
        return node.value


def _sse(y: List[float]) -> float:
    n = len(y)
    if n == 0:
        return 0.0
    mu = sum(y) / n
    return sum((v - mu) ** 2 for v in y)


def _best_split(X: List[List[float]], y: List[float], min_leaf: int
                ) -> Tuple[Optional[int], Optional[float]]:
    n = len(y)
    best: Tuple[Optional[int], Optional[float]] = (None, None)
    best_gain = 0.0
    base = _sse(y)
    n_feat = len(X[0])
    for f in range(n_feat):
        order = sorted(range(n), key=lambda i: X[i][f])
        # sweep candidate thresholds between sorted values
        for k in range(min_leaf, n - min_leaf + 1):
            if k < n and X[order[k - 1]][f] == X[order[k]][f]:
                continue
            thr = (X[order[k - 1]][f] + X[order[k]][f]) / 2.0
            yl = [y[i] for i in order[:k]]
            yr = [y[i] for i in order[k:]]
            gain = base - _sse(yl) - _sse(yr)
            if gain > best_gain:
                best_gain = gain
                best = (f, thr)
    return best


def fit_tree(X: List[List[float]], y: List[float], *, max_depth: int = 4,
             min_leaf: int = 8) -> _Node:
    mean_y = sum(y) / len(y) if y else 0.0

    def grow(rows: List[int], depth: int) -> _Node:
        ys = [y[i] for i in rows]
        if depth >= max_depth or len(ys) < 2 * min_leaf:
            return _Node(sum(ys) / len(ys) if ys else mean_y)
        f, thr = _best_split([X[i] for i in rows], ys, min_leaf)
        if f is None:
            return _Node(sum(ys) / len(ys))
        left_rows = [i for i in rows if X[i][f] <= thr]
        right_rows = [i for i in rows if X[i][f] > thr]
        return _Node(sum(ys) / len(ys), f, thr,
                     grow(left_rows, depth + 1), grow(right_rows, depth + 1))

    return grow(list(range(len(y))), 0)


# ------------------------------------------------------- features & targets

def _doy(date_iso: str) -> int:
    return _dt.date.fromisoformat(date_iso).timetuple().tm_yday


def build_rows(dates: List[str], depths: List[float],
               rains: List[float]) -> Tuple[List[List[float]], List[float]]:
    """Training rows aligned with the forecast: yesterday's state + today's
    rain → today's depth (X, y = depth(i), for i with full lags)."""
    X: List[List[float]] = []
    y: List[float] = []
    for i in range(10, len(dates)):
        if depths[i] is None or depths[i - 1] is None:
            continue
        doy = _doy(dates[i])
        X.append([
            depths[i - 1],
            sum(depths[i - 3:i]) / 3.0,
            rains[i],
            sum(rains[i - 2:i + 1]),
            sum(rains[i - 9:i + 1]),
            math.sin(2 * math.pi * doy / 365.0),
            math.cos(2 * math.pi * doy / 365.0),
        ])
        y.append(depths[i])
    return X, y


def _forecast_row(hist: List[float], rains: List[float], i: int,
                  doy: int) -> List[float]:
    """Feature row for the day at index i: hist holds depths up to i-1."""
    return [
        hist[-1],
        sum(hist[-3:]) / 3.0,
        rains[i],
        sum(rains[i - 2:i + 1]),
        sum(rains[i - 9:i + 1]),
        math.sin(2 * math.pi * doy / 365.0),
        math.cos(2 * math.pi * doy / 365.0),
    ]


# ------------------------------------------------------------ public API

def forecast_logger(dates: List[str], depths: List[float],
                    rains_past: List[float], forecast_dates: List[str],
                    rains_fc: List[float], *,
                    scenario_mm: Optional[float] = None,
                    max_depth: int = 4, min_leaf: int = 8
                    ) -> Dict[str, Any]:
    """Fit on history, then recursively predict ``forecast_dates``.

    ``scenario_mm`` replaces the first forecast day's rain with a flat
    cloudburst (what-if; remaining days use the forecast as-is).
    """
    rains = list(rains_past) + [
        float(scenario_mm) if (scenario_mm is not None and j == 0) else float(v)
        for j, v in enumerate(rains_fc)]
    all_dates = list(dates) + list(forecast_dates)
    n_fc = len(forecast_dates)

    X, y = build_rows(dates, depths, rains_past)
    method = "cart"
    if len(X) < MIN_ROWS:
        method = "persistence"

    fc_depths: List[float] = []
    hist_depths = list(depths)
    if method == "cart":
        tree = fit_tree(X, y, max_depth=max_depth, min_leaf=min_leaf)
        for j in range(n_fc):
            i = len(dates) + j  # index into all_dates / rains
            row = _forecast_row(hist_depths, rains, i, _doy(all_dates[i]))
            pred = tree.predict(row)
            fc_depths.append(round(pred, 3))
            hist_depths.append(pred)
    else:
        last = next((d for d in reversed(depths) if d is not None), None)
        fc_depths = [round(last, 3) if last is not None else None
                     for _ in range(n_fc)]

    return {
        "version": PREDICT_VERSION,
        "method": method,
        "nTrainRows": len(X),
        "forecast": [{"date": d, "depth": v}
                     for d, v in zip(forecast_dates, fc_depths)],
    }


def backtest_logger(dates: List[str], depths: List[float],
                    rains_past: List[float], *, frac: float = 0.2,
                    max_depth: int = 4, min_leaf: int = 8
                    ) -> Dict[str, Any]:
    """Holdout tail: train on the first (1−frac), recursively predict the
    tail with actual rain; MSE/MAE vs persistence baseline."""
    X, y = build_rows(dates, depths, rains_past)
    if len(X) < MIN_ROWS + 4:
        return {"available": False, "reason": "too few rows"}
    n_test = max(3, int(len(y) * frac))
    tree = fit_tree(X[:-n_test], y[:-n_test], max_depth=max_depth,
                    min_leaf=min_leaf)

    start = len(dates) - n_test  # first held-out target index
    hist = list(depths[:start])
    se, ae, se_p, n = 0.0, 0.0, 0.0, 0
    for i in range(start, len(dates)):
        actual = depths[i]
        if actual is None:
            hist.append(hist[-1] if hist else 0.0)
            continue
        row = _forecast_row(hist, rains_past, i, _doy(dates[i]))
        pred = tree.predict(row)
        prev = hist[-1] if hist else actual
        se += (pred - actual) ** 2
        ae += abs(pred - actual)
        se_p += (prev - actual) ** 2
        n += 1
        hist.append(actual)
    if n == 0:
        return {"available": False, "reason": "no complete holdout rows"}
    return {
        "available": True,
        "nTest": n,
        "mse": round(se / n, 5),
        "mae": round(ae / n, 4),
        "persistenceMse": round(se_p / n, 5),
        "skillVsPersistence": round(1.0 - (se / n) / (se_p / n), 3)
        if se_p > 0 else None,
    }

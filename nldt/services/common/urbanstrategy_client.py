"""Urban Strategy RestAPI client (Scenexus OpenAPI 3.0 / v0.6.4).

Live path (opt-in ``US_LIVE=1``):
  GET {base}/login?email=&password=  → token
  GET {base}/data/bin/{Bin}/get?token= → store collections

Offline path: load a committed GeoJSON / JSON fixture via ``fixture://``
or a filesystem path — no network.

Docs: https://doc.urbanstrategy.nl/develop/rest-api/
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional
from urllib.parse import urlparse

import httpx

# Default receptor property names as documented for the US noise store.
_LAEQ_KEYS = ("lAeq", "L_AEQ", "LAeq", "l_aeq", "LAEQ")
_ILDEN_KEYS = ("iLden", "I_LDEN", "ILden", "i_lden", "ILDEN", "Lden", "LDEN")


class UrbanStrategyError(RuntimeError):
    """RestAPI, auth, or fixture failure."""


def live_enabled() -> bool:
    return os.environ.get("US_LIVE", "").strip() in ("1", "true", "yes")


def resolve_auth(
    *,
    token: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
) -> dict[str, str]:
    """Resolve credentials from explicit args or environment."""
    tok = (token if token is not None else os.environ.get("US_TOKEN", "")).strip()
    if tok:
        return {"token": tok}
    mail = (email if email is not None else os.environ.get("US_EMAIL", "")).strip()
    pwd = (password if password is not None else os.environ.get("US_PASSWORD", "")).strip()
    if mail and pwd:
        return {"email": mail, "password": pwd}
    raise UrbanStrategyError(
        "Urban Strategy auth missing: set US_TOKEN or US_EMAIL+US_PASSWORD "
        "(and US_LIVE=1 for network calls)"
    )


def login(
    base_url: str,
    email: str,
    password: str,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 30.0,
) -> str:
    """Obtain an API token via GET /login."""
    base = base_url.rstrip("/")
    own = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.get(f"{base}/login", params={"email": email, "password": password})
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token") or data.get("Token") or data.get("access_token")
        if isinstance(data, str) and data.strip():
            token = data.strip()
        if not token:
            # Some US builds return the token as plain text.
            text = resp.text.strip().strip('"')
            if text and " " not in text and len(text) < 512:
                token = text
        if not token:
            raise UrbanStrategyError(
                f"login response missing token (keys={list(data) if isinstance(data, dict) else type(data).__name__})"
            )
        return str(token)
    except httpx.HTTPError as exc:
        raise UrbanStrategyError(f"login failed: {exc}") from exc
    finally:
        if own:
            http.close()


def get_bin(
    base_url: str,
    token: str,
    bin_id: str,
    *,
    client: Optional[httpx.Client] = None,
    timeout: float = 60.0,
) -> Any:
    """GET /data/bin/{Bin}/get — raw store payload for one bin."""
    base = base_url.rstrip("/")
    own = client is None
    http = client or httpx.Client(timeout=timeout)
    try:
        resp = http.get(
            f"{base}/data/bin/{bin_id}/get",
            params={"token": token},
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        raise UrbanStrategyError(f"get_bin({bin_id!r}) failed: {exc}") from exc
    finally:
        if own:
            http.close()


def _first_number(props: Mapping[str, Any], keys: tuple[str, ...]) -> Optional[float]:
    for key in keys:
        if key in props and props[key] is not None and props[key] != "":
            try:
                return float(props[key])
            except (TypeError, ValueError):
                continue
    return None


def _point_geometry(row: Mapping[str, Any]) -> Optional[dict[str, Any]]:
    """Extract a GeoJSON Point from a US store row or GeoJSON feature."""
    geom = row.get("geometry")
    if isinstance(geom, dict) and geom.get("type") == "Point":
        return geom
    # Common US store column pairs
    for lon_k, lat_k in (
        ("lon", "lat"),
        ("lng", "lat"),
        ("longitude", "latitude"),
        ("x", "y"),
        ("X", "Y"),
        ("LON", "LAT"),
    ):
        if lon_k in row and lat_k in row:
            try:
                lon, lat = float(row[lon_k]), float(row[lat_k])
            except (TypeError, ValueError):
                continue
            # Heuristic: RD New coords are large; leave as-is only if WGS-ish.
            if abs(lon) <= 180 and abs(lat) <= 90:
                return {"type": "Point", "coordinates": [lon, lat]}
    return None


def normalize_receptors(payload: Any, *, collection: Optional[str] = None) -> dict[str, Any]:
    """Normalize a US bin payload or GeoJSON into a receptor FeatureCollection.

    Output properties always include ``lAeq`` (required for evaluation) and
    optionally ``iLden``. Geometry is GeoJSON Point in EPSG:4326.
    """
    features: list[dict[str, Any]] = []

    if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
        rows = payload.get("features") or []
        for i, feat in enumerate(rows):
            if not isinstance(feat, dict):
                continue
            props = dict(feat.get("properties") or {})
            geom = feat.get("geometry") or _point_geometry(props)
            laeq = _first_number(props, _LAEQ_KEYS)
            if geom is None or laeq is None:
                continue
            out_props = {
                "id": props.get("id") or props.get("ID") or f"receptor-{i}",
                "lAeq": laeq,
            }
            ilden = _first_number(props, _ILDEN_KEYS)
            if ilden is not None:
                out_props["iLden"] = ilden
            if collection:
                out_props["collection"] = collection
            features.append({
                "type": "Feature",
                "properties": out_props,
                "geometry": geom if geom.get("type") == "Point" else geom,
            })
    elif isinstance(payload, dict):
        # Store shape: {collectionName: [rows...]} or {"collections": {...}}
        colls = payload.get("collections") if isinstance(payload.get("collections"), dict) else payload
        if collection:
            candidates = {collection: colls.get(collection)} if isinstance(colls, dict) else {}
        else:
            candidates = colls if isinstance(colls, dict) else {}
        for coll_name, rows in candidates.items():
            if not isinstance(rows, list):
                continue
            for i, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    continue
                geom = _point_geometry(row)
                laeq = _first_number(row, _LAEQ_KEYS)
                if geom is None or laeq is None:
                    continue
                out_props = {
                    "id": row.get("id") or row.get("ID") or f"{coll_name}-{i}",
                    "lAeq": laeq,
                    "collection": coll_name,
                }
                ilden = _first_number(row, _ILDEN_KEYS)
                if ilden is not None:
                    out_props["iLden"] = ilden
                features.append({
                    "type": "Feature",
                    "properties": out_props,
                    "geometry": geom,
                })
    elif isinstance(payload, list):
        for i, row in enumerate(payload):
            if not isinstance(row, Mapping):
                continue
            geom = _point_geometry(row)
            laeq = _first_number(row, _LAEQ_KEYS)
            if geom is None or laeq is None:
                continue
            out_props = {
                "id": row.get("id") or row.get("ID") or f"receptor-{i}",
                "lAeq": laeq,
            }
            ilden = _first_number(row, _ILDEN_KEYS)
            if ilden is not None:
                out_props["iLden"] = ilden
            features.append({
                "type": "Feature",
                "properties": out_props,
                "geometry": geom,
            })

    # Stable order for deterministic fingerprints
    features.sort(key=lambda f: str((f.get("properties") or {}).get("id", "")))
    return {"type": "FeatureCollection", "features": features}


def _resolve_fixture_path(source: str) -> Path:
    if source.startswith("fixture://"):
        rel = source[len("fixture://"):]
        # Prefer nldt/fixtures/urbanstrategy/
        root = Path(__file__).resolve().parents[2]  # nldt/
        candidate = root / "fixtures" / "urbanstrategy" / rel
        if candidate.exists():
            return candidate
        # Absolute-ish after fixture://
        p = Path(rel)
        if p.exists():
            return p
        raise UrbanStrategyError(f"fixture not found: {source} (tried {candidate})")
    if source.startswith("file://"):
        return Path(urlparse(source).path)
    p = Path(source)
    if p.exists():
        return p
    raise UrbanStrategyError(f"fixture path not found: {source}")


def load_fixture(source: str, *, collection: Optional[str] = None) -> dict[str, Any]:
    """Load and normalize receptors from a local fixture (no network)."""
    path = _resolve_fixture_path(source)
    data = json.loads(path.read_text(encoding="utf-8"))
    return normalize_receptors(data, collection=collection)


def fetch_noise_receptors(
    *,
    source: Optional[str] = None,
    base_url: Optional[str] = None,
    bin_id: Optional[str] = None,
    collection: Optional[str] = None,
    token: Optional[str] = None,
    email: Optional[str] = None,
    password: Optional[str] = None,
    client: Optional[httpx.Client] = None,
) -> dict[str, Any]:
    """Fetch or load normalized noise receptors.

    Prefer ``source`` as ``fixture://…`` / path. Live RestAPI requires
    ``US_LIVE=1`` plus auth and ``base_url`` + ``bin_id``.
    """
    if source:
        return load_fixture(source, collection=collection)

    if not live_enabled():
        raise UrbanStrategyError(
            "live Urban Strategy fetch refused (set US_LIVE=1) or pass source=fixture://…"
        )

    base = (base_url or os.environ.get("US_BASE_URL", "")).strip()
    bin_name = (bin_id or os.environ.get("US_BIN", "")).strip()
    coll = collection if collection is not None else os.environ.get("US_NOISE_COLLECTION")
    if not base or not bin_name:
        raise UrbanStrategyError("US_BASE_URL and US_BIN (or baseUrl/bin inputs) required for live fetch")

    auth = resolve_auth(token=token, email=email, password=password)
    own = client is None
    http = client or httpx.Client(timeout=60.0)
    try:
        if "token" in auth:
            tok = auth["token"]
        else:
            tok = login(base, auth["email"], auth["password"], client=http)
        raw = get_bin(base, tok, bin_name, client=http)
        return normalize_receptors(raw, collection=coll or None)
    finally:
        if own:
            http.close()

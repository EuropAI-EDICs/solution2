"""HY-World WorldMirror reconstruction adapter (Utrecht Renderer context).

Registers offline reconstruction assets on world-scene specs. Does not run zone
algebra and must never be imported by engine.py / critic.py.

Live WorldMirror inference is optional (HYWORLD_ROOT + GPU); the PoC ships with
fixtures. See docs/POC_WORLD_MODEL_UTRECHT.md.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from pipeline import contracts

GROUNDING_STAMP = "hyworld-recon-context-not-legal"
CESIUM_POINTS_VERSION = "cesium-points-v1"
ROLE_FILES = {
    "points": ("points.cesium.json", "points.ply", "gaussians.ply"),
    "mesh": ("mesh.ply", "mesh.obj", "mesh.gltf", "mesh.glb"),
    "cameras": ("camera_params.json", "cameras.json"),
}


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_ascii_ply_xyz(text: str) -> List[Tuple[float, float, float]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "ply":
        raise ValueError("not a PLY file")
    i = 1
    fmt = None
    n_vertex = 0
    props: List[str] = []
    while i < len(lines):
        parts = lines[i].split()
        if not parts:
            i += 1
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element" and parts[1] == "vertex":
            n_vertex = int(parts[2])
        elif parts[0] == "property" and len(parts) >= 3:
            props.append(parts[-1])
        elif parts[0] == "end_header":
            i += 1
            break
        i += 1
    if fmt != "ascii":
        raise ValueError(f"unsupported PLY format {fmt!r}; expected ascii")
    try:
        ix, iy, iz = props.index("x"), props.index("y"), props.index("z")
    except ValueError as exc:
        raise ValueError("PLY header missing x/y/z properties") from exc
    pts: List[Tuple[float, float, float]] = []
    for j in range(n_vertex):
        if i + j >= len(lines):
            break
        cols = lines[i + j].split()
        if len(cols) <= max(ix, iy, iz):
            continue
        pts.append((float(cols[ix]), float(cols[iy]), float(cols[iz])))
    return pts


def _parse_binary_le_ply_xyz(data: bytes) -> List[Tuple[float, float, float]]:
    header_end = data.find(b"end_header\n")
    if header_end < 0:
        header_end = data.find(b"end_header\r\n")
        if header_end < 0:
            raise ValueError("PLY end_header not found")
        body_start = header_end + len(b"end_header\r\n")
    else:
        body_start = header_end + len(b"end_header\n")
    header = data[:header_end].decode("ascii", errors="replace").splitlines()
    if not header or header[0].strip() != "ply":
        raise ValueError("not a PLY file")
    fmt = None
    n_vertex = 0
    props: List[Tuple[str, str]] = []  # (type, name)
    for line in header[1:]:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element" and parts[1] == "vertex":
            n_vertex = int(parts[2])
        elif parts[0] == "property" and len(parts) >= 3:
            props.append((parts[1], parts[-1]))
    if fmt != "binary_little_endian":
        raise ValueError(f"unsupported PLY format {fmt!r}")
    type_size = {
        "float": 4,
        "float32": 4,
        "double": 8,
        "float64": 8,
        "uchar": 1,
        "uint8": 1,
        "char": 1,
        "int8": 1,
        "ushort": 2,
        "uint16": 2,
        "short": 2,
        "int16": 2,
        "uint": 4,
        "uint32": 4,
        "int": 4,
        "int32": 4,
    }
    names = [p[1] for p in props]
    try:
        ix, iy, iz = names.index("x"), names.index("y"), names.index("z")
    except ValueError as exc:
        raise ValueError("PLY header missing x/y/z properties") from exc
    stride = 0
    offsets: List[int] = []
    for t, _ in props:
        offsets.append(stride)
        if t not in type_size:
            raise ValueError(f"unsupported PLY property type {t!r}")
        stride += type_size[t]
    unpackers = []
    for t, _ in props:
        if t in ("float", "float32"):
            unpackers.append(("f", 4))
        elif t in ("double", "float64"):
            unpackers.append(("d", 8))
        else:
            unpackers.append((None, type_size[t]))
    pts: List[Tuple[float, float, float]] = []
    body = memoryview(data)[body_start:]
    for vi in range(n_vertex):
        base = vi * stride
        if base + stride > len(body):
            break
        vals: List[Optional[float]] = []
        off = 0
        for fmt_c, size in unpackers:
            if fmt_c is None:
                vals.append(None)
            else:
                vals.append(struct.unpack_from("<" + fmt_c, body, base + off)[0])
            off += size
        x, y, z = vals[ix], vals[iy], vals[iz]
        if x is None or y is None or z is None:
            continue
        pts.append((float(x), float(y), float(z)))
    return pts


def parse_ply_xyz(path: Path) -> List[Tuple[float, float, float]]:
    raw = path.read_bytes()
    if b"format ascii" in raw[:2048]:
        return _parse_ascii_ply_xyz(raw.decode("utf-8", errors="replace"))
    if b"format binary_little_endian" in raw[:2048]:
        return _parse_binary_le_ply_xyz(raw)
    # Prefer ascii decode for tiny fixtures
    try:
        return _parse_ascii_ply_xyz(raw.decode("utf-8"))
    except ValueError:
        return _parse_binary_le_ply_xyz(raw)


def _looks_like_lon_lat(pts: Sequence[Tuple[float, float, float]]) -> bool:
    if not pts:
        return False
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (
        min(xs) >= -180
        and max(xs) <= 180
        and min(ys) >= -90
        and max(ys) <= 90
        and abs(max(xs) - min(xs)) < 5
        and abs(max(ys) - min(ys)) < 5
    )


def _downsample(
    pts: Sequence[Tuple[float, float, float]], max_points: int
) -> List[Tuple[float, float, float]]:
    if max_points < 1:
        raise ValueError("max_points must be >= 1")
    if len(pts) <= max_points:
        return list(pts)
    step = math.ceil(len(pts) / max_points)
    return list(pts[::step][:max_points])


def export_points_for_cesium(
    ply_path: Path,
    out_json: Path,
    *,
    max_points: int = 50_000,
    assume_lon_lat_height: Optional[bool] = None,
) -> Dict[str, Any]:
    """Convert a WorldMirror points.ply (or ascii XYZ PLY) to Cesium-friendly JSON.

    Coordinates: if values look like WGS84 lon/lat (or assume_lon_lat_height=True),
    stored as [lon, lat, height_m]. Otherwise treated as local metric XYZ and stored
    under crs local-xyz (demo must georeference separately).
    """
    ply_path = Path(ply_path)
    out_json = Path(out_json)
    pts = parse_ply_xyz(ply_path)
    pts = _downsample(pts, max_points)
    lonlat = (
        assume_lon_lat_height
        if assume_lon_lat_height is not None
        else _looks_like_lon_lat(pts)
    )
    if lonlat:
        payload = {
            "type": CESIUM_POINTS_VERSION,
            "crs": "EPSG:4326",
            "count": len(pts),
            "points": [[p[0], p[1], p[2]] for p in pts],
        }
        if pts:
            lons = [p[0] for p in pts]
            lats = [p[1] for p in pts]
            hs = [p[2] for p in pts]
            payload["bbox"] = [min(lons), min(lats), min(hs), max(lons), max(lats), max(hs)]
    else:
        payload = {
            "type": CESIUM_POINTS_VERSION,
            "crs": "local-xyz",
            "count": len(pts),
            "points": [[p[0], p[1], p[2]] for p in pts],
            "note": "Local XYZ from WorldMirror; georeference before legal or survey use.",
        }
        if pts:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            zs = [p[2] for p in pts]
            payload["bbox"] = [min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)]
    _write_json(out_json, payload)
    return payload


def _discover_assets(asset_dir: Path) -> List[Dict[str, str]]:
    asset_dir = asset_dir.resolve()
    refs: List[Dict[str, str]] = []
    for role, names in ROLE_FILES.items():
        chosen: Optional[Path] = None
        for name in names:
            candidate = asset_dir / name
            if not candidate.is_file():
                continue
            # Prefer cesium JSON for points over raw PLY when both exist
            if role == "points" and name.endswith(".ply") and (asset_dir / "points.cesium.json").is_file():
                continue
            chosen = candidate
            break
        if chosen is None:
            continue
        if asset_dir.name == "recon":
            run_rel = f"recon/{chosen.name}"
        else:
            run_rel = chosen.name
        refs.append(
            {
                "role": role,
                "path": run_rel.replace("\\", "/"),
                "relativeTo": "scenarioRunDir",
            }
        )
    return refs


def build_hyworld_recon_block(
    asset_refs: Sequence[Mapping[str, str]],
    *,
    source_note: str,
    enabled: bool,
    hitl_required: bool,
) -> Dict[str, Any]:
    return {
        "enabled": enabled,
        "assetRefs": [dict(r) for r in asset_refs],
        "sourceNote": source_note,
        "hitlRequired": hitl_required,
    }


def register_recon_assets(
    scenario_run_dir: Path,
    asset_dir: Path,
    *,
    hitl_approved: bool = False,
    source_note: Optional[str] = None,
    fixture_mode: bool = False,
    scenario_ids: Optional[Sequence[str]] = None,
) -> Path:
    """Merge hyworldRecon into world-scene-specs.json for the run.

    Live (non-fixture) assets require hitl_approved=True (or HYWORLD_HITL_APPROVED=1).
    Fixture mode may enable without HITL but always stamps hyworld-recon-context-not-legal.
    """
    scenario_run_dir = Path(scenario_run_dir).resolve()
    asset_dir = Path(asset_dir).resolve()
    bundle_path = scenario_run_dir / "world-scene-specs.json"
    if not bundle_path.is_file():
        raise FileNotFoundError(f"missing world-scene-specs.json in {scenario_run_dir}")
    if not asset_dir.is_dir():
        raise FileNotFoundError(f"asset_dir not found: {asset_dir}")

    meta_path = asset_dir / "META.json"
    meta = _read_json(meta_path) if meta_path.is_file() else {}
    note = source_note or str(
        meta.get("sourceNote")
        or meta.get("note")
        or "HY-World WorldMirror reconstruction context — not a legal map."
    )

    refs = _discover_assets(asset_dir)
    if not refs:
        raise FileNotFoundError(
            f"no recon assets found in {asset_dir} "
            f"(expected one of {sorted({n for names in ROLE_FILES.values() for n in names})})"
        )

    env_hitl = os.environ.get("HYWORLD_HITL_APPROVED") == "1"
    if fixture_mode:
        enabled = True
        hitl_required = False
    else:
        hitl_required = True
        enabled = bool(hitl_approved or env_hitl)

    block = build_hyworld_recon_block(
        refs, source_note=note, enabled=enabled, hitl_required=hitl_required
    )

    bundle = _read_json(bundle_path)
    specs: List[Dict[str, Any]] = list(bundle.get("specs") or [])
    wanted = set(scenario_ids) if scenario_ids else None
    for spec in specs:
        if wanted is not None and spec.get("scenarioId") not in wanted:
            continue
        spec["hyworldRecon"] = block
        # Prefer recon stamp when recon is enabled; keep marble stamp if marble already gated on
        if enabled:
            marble_on = bool((spec.get("marble") or {}).get("enabled"))
            if not marble_on:
                spec["groundingStamp"] = GROUNDING_STAMP
        contracts.validate(spec, "world-scene-spec")

    bundle["specs"] = specs
    _write_json(bundle_path, bundle)
    return bundle_path


def try_run_worldmirror(input_path: Path, output_dir: Path) -> int:
    """Optional live inference. Requires HYWORLD_ROOT on PYTHONPATH and GPU stack.

    Returns process-style exit code: 0 success, 2 fixture-only / unavailable.
    """
    root = os.environ.get("HYWORLD_ROOT", "").strip()
    if not root:
        print(
            "HYWORLD_ROOT not set — fixture-only mode. "
            "Clone https://github.com/Tencent-Hunyuan/HY-World-2.0 and export HYWORLD_ROOT "
            "to run WorldMirrorPipeline live.",
            file=sys.stderr,
        )
        return 2
    root_path = Path(root)
    if not root_path.is_dir():
        print(f"HYWORLD_ROOT is not a directory: {root}", file=sys.stderr)
        return 2
    sys.path.insert(0, str(root_path))
    try:
        from hyworld2.worldrecon.pipeline import WorldMirrorPipeline  # type: ignore
    except Exception as exc:  # noqa: BLE001 — surface env issues clearly
        print(
            f"Could not import WorldMirrorPipeline from {root}: {exc}\n"
            "Install HY-World 2.0 worldrecon deps (CUDA/PyTorch) or use fixtures.",
            file=sys.stderr,
        )
        return 2

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    pipeline = WorldMirrorPipeline.from_pretrained("tencent/HY-World-2.0")
    result = pipeline(str(input_path))
    # Best-effort persist common artifacts if the pipeline returns paths/dicts
    if isinstance(result, Mapping):
        for key in ("points", "gaussians", "cameras", "mesh"):
            val = result.get(key)
            if isinstance(val, (str, Path)) and Path(val).is_file():
                dest = output_dir / Path(val).name
                dest.write_bytes(Path(val).read_bytes())
        summary = {k: (str(v) if not isinstance(v, (dict, list)) else v) for k, v in result.items()}
        _write_json(output_dir / "worldmirror_result.json", summary)
    print(f"WorldMirror finished; assets under {output_dir}")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HY-World WorldMirror recon adapter (Utrecht)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_export = sub.add_parser("export-points", help="PLY → points.cesium.json")
    p_export.add_argument("--ply", type=Path, required=True)
    p_export.add_argument("--out", type=Path, required=True)
    p_export.add_argument("--max-points", type=int, default=50_000)
    p_export.add_argument(
        "--lon-lat",
        action="store_true",
        help="Force treat PLY x/y/z as lon/lat/height",
    )

    p_reg = sub.add_parser("register", help="Merge recon assets into world-scene-specs.json")
    p_reg.add_argument("--run-dir", type=Path, required=True)
    p_reg.add_argument("--asset-dir", type=Path, required=True)
    p_reg.add_argument("--hitl-approved", action="store_true")
    p_reg.add_argument("--fixture", action="store_true", help="Fixture mode (HITL not required)")
    p_reg.add_argument("--source-note", type=str, default=None)
    p_reg.add_argument("--scenario-id", action="append", default=None)

    p_wm = sub.add_parser("worldmirror", help="Optional live WorldMirror run (needs HYWORLD_ROOT)")
    p_wm.add_argument("--input", type=Path, required=True)
    p_wm.add_argument("--out-dir", type=Path, required=True)

    args = parser.parse_args(argv)
    if args.cmd == "export-points":
        export_points_for_cesium(
            args.ply,
            args.out,
            max_points=args.max_points,
            assume_lon_lat_height=True if args.lon_lat else None,
        )
        return 0
    if args.cmd == "register":
        register_recon_assets(
            args.run_dir,
            args.asset_dir,
            hitl_approved=args.hitl_approved,
            source_note=args.source_note,
            fixture_mode=args.fixture,
            scenario_ids=args.scenario_id,
        )
        return 0
    if args.cmd == "worldmirror":
        return try_run_worldmirror(args.input, args.out_dir)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

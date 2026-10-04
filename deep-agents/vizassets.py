"""Local Leaflet assets so demos work without any CDN, API key or internet.

Basemap tiles are intentionally NOT used (CARTO/OSM CDNs now want API keys);
the GeoJSON overlays carry the visualization on a plain background.
"""

from __future__ import annotations

import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ASSETS_DIR = HERE / "runs" / "assets"

_SOURCES = {
    "leaflet.js": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
    "leaflet.css": "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
    "turf.min.js": "https://cdn.jsdelivr.net/npm/@turf/turf@7.2.0/turf.min.js",
}
_CDN_TAGS = (
    '<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">',
    '<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>',
)


def _download(name: str, url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            ASSETS_DIR.joinpath(name).write_bytes(resp.read())
        return True
    except Exception:
        return False


def leaflet_tags(prefix: str = "../assets") -> tuple[str, str]:
    """Return (css_tag, js_tag) pointing at local copies; falls back to CDN."""
    if not ASSETS_DIR.is_dir():
        ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    missing = [n for n in _SOURCES if not ASSETS_DIR.joinpath(n).is_file()]
    for name in missing:
        _download(name, _SOURCES[name])
    have = all(ASSETS_DIR.joinpath(n).is_file() for n in _SOURCES)
    turf_tag = f'<script src="{prefix}/turf.min.js"></script>' if ASSETS_DIR.joinpath("turf.min.js").is_file() else ""
    if have:
        return (
            f'<link rel="stylesheet" href="{prefix}/leaflet.css">',
            f'<script src="{prefix}/leaflet.js"></script>{turf_tag}',
        )
    return _CDN_TAGS  # last resort; map still renders overlays if CDN reachable

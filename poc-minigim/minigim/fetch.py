"""Compat-shim: de fetch-mechaniek staat sinds M2 in fundament.fetch.

Deze shim bindt de PoC-specifieke zaken (cache-locatie, user-agent, het
Breda-CBS-filter) zodat run.py, tests en checklist ongewijzigd blijven.
De cache-bestanden zijn uitwisselbaar met de bestaande data/cache/.
"""

from __future__ import annotations

from pathlib import Path

from fundament.fetch import FetchError, load_aoi  # noqa: F401 — publieke API
from fundament.fetch import _bbox_str  # noqa: F401 — compat: tests roepen twee-arg _cache_key én _bbox_str

DATA = Path(__file__).resolve().parents[1] / "data"
CACHE = DATA / "cache"
USER_AGENT = "ldt-toolbox-poc-minigim/1.0 (MiniGIM gebiedscheck)"

OGC_FILTER_BREDA = (
    "<Filter><PropertyIsEqualTo><PropertyName>gemeentenaam</PropertyName>"
    "<Literal>Breda</Literal></PropertyIsEqualTo></Filter>"
)


def _cache_key(source_id: str, fingerprint: str) -> Path:
    """Compat-wrapper rond fundament.fetch._cache_key (oude twee-arg signatuur)."""
    from fundament import fetch as _f

    return _f._cache_key(CACHE, source_id, fingerprint)


def fetch_layer(source: dict, bbox=None, refresh: bool = False,
                cbs_filter: str | None = None):
    from fundament import fetch as _f

    return _f.fetch_layer(source, bbox=bbox, refresh=refresh, cbs_filter=cbs_filter,
                          cache_dir=CACHE, user_agent=USER_AGENT)

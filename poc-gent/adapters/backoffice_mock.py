"""District09-backoffice-mock (F3): inzending mét idempotent ontvangstbewijs.
Productie vervangt dit door de versioned API-contracten van District09 (INT-03);
statusmapping technisch→burgerlijk gebeurt in de pipeline (INT-06)."""

from __future__ import annotations

_CONTRACTEN = {"district09-vergunningen", "district09-parkeervergunningen"}
_CACHE: dict[str, dict] = {}


def dien_in(contract: str, lading: dict, idempotentie_sleutel: str) -> dict:
    if contract not in _CONTRACTEN:
        raise KeyError(f"onbekend backoffice-contract: {contract}")
    if idempotentie_sleutel in _CACHE:
        return _CACHE[idempotentie_sleutel]
    resultaat = {"referentie": "GENT-" + idempotentie_sleutel[:12].upper(), "status": "geaccepteerd"}
    _CACHE[idempotentie_sleutel] = resultaat
    return resultaat

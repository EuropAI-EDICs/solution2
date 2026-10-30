"""EUDI-wallet-mock voor het IAM-stuk (H2): relying-party edge in replay-vorm
met ARF-vormige enveloppen, volgens de walletdoctrine (nldt/16, optie C —
mock-first, pluggable). De wallet onthult alléén aangevraagde claims
(selectieve onthulling, DATA-minimalisatie); de verifier controleert tegen
lokale vertrouwensankers en faalt dicht bij elke afwijking. De claims-vorm
volgt nldt/schemas/wallet-claims.schema.json; de machtiging is een
EBW-stijl attestatie (nldt/16 §6a). Productie vervangt dit door de Belgische
EUDI-wallet via OpenID4VP (INT-01) — protocolwaarheid landt daar, niet hier."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

LOA_ORDER = {"low": 0, "substantial": 1, "high": 2}
CLIENT_ID = "stad-gent-transactieassistent-mock"

_CREDENTIALS_QUERY = [
    {"credential": "pid", "claims": ["sub", "loa"]},
    {"credential": "machtiging", "claims": ["mandaten"]},
]


class WalletFout(Exception):
    """Presentatie of verificatie faalt — fail-closed, nooit gokken."""


class GeenWallet(Exception):
    """Persona heeft geen EUDI-wallet: signaal voor de ACM/IDM-fallback (vrije uitweg)."""


def _laad(poc_root: Path) -> dict:
    return json.loads((poc_root / "fixtures" / "wallets.json").read_text(encoding="utf-8"))


def _nonce(client_id: str, doelbinding: list, query: list) -> str:
    basis = json.dumps({"client_id": client_id, "doelbinding": doelbinding,
                        "credentials_query": query}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def presentation_request(bronnen: list[dict]) -> dict:
    """OpenID4VP/DCQL-vormige presentatie-aanvraag (ARF-shaped mock): de
    assistent vraagt alléén wat de H2-doelbinding nodig heeft; de nonce is
    hash-afgeleid zodat replays deterministisch blijven (geen muurklok)."""
    return {
        "type": "openid4vp.presentation_request",
        "client_id": CLIENT_ID,
        "doelbinding": bronnen,
        "credentials_query": json.loads(json.dumps(_CREDENTIALS_QUERY)),
        "nonce": _nonce(CLIENT_ID, bronnen, _CREDENTIALS_QUERY),
    }


def presenteer(poc_root: Path, persona_id: str, request: dict) -> dict:
    """Wallet-kant: onthult per credential alléén de aangevraagde claims —
    gegevens die niet gevraagd zijn (zoals de naam) verlaten de wallet niet."""
    wallets = _laad(poc_root)["personas"]
    if persona_id not in wallets:
        raise GeenWallet(f"persona heeft geen EUDI-wallet: {persona_id}")
    vp = []
    for query in request["credentials_query"]:
        attestatie = next((a for a in wallets[persona_id]["attestaties"]
                           if a["type"] == query["credential"]), None)
        if attestatie is None:
            raise WalletFout(f"wallet mist attestatie '{query['credential']}'")
        ontbrekend = [c for c in query["claims"] if c not in attestatie["claims"]]
        if ontbrekend:
            raise WalletFout(f"attestatie '{query['credential']}' mist aangevraagde claims: {ontbrekend}")
        vp.append({"credential": query["credential"], "issuer": attestatie["issuer"],
                   "claims": {c: attestatie["claims"][c] for c in query["claims"]}})
    return {"type": "openid4vp.presentation", "presentation_request_nonce": request["nonce"], "vp": vp}


def verifieer(poc_root: Path, presentatie: dict, request: dict) -> dict:
    """RP-kant: verificatie tegen lokale vertrouwensankers — fail-closed bij
    nonce-mismatch, credentials buiten de aanvraag, ontbrekende credentials,
    onbekende issuer, ontbrekende aangevraagde claims, onthulling buiten de
    aanvraag of een pid zonder geldig sub/loa."""
    if presentatie.get("presentation_request_nonce") != request["nonce"]:
        raise WalletFout("nonce komt niet overeen met de presentatie-aanvraag")
    ankers = _laad(poc_root)["vertrouwensankers"]
    gevraagde_types = {q["credential"] for q in request["credentials_query"]}
    for item in presentatie.get("vp", []):
        if item.get("credential") not in gevraagde_types:
            raise WalletFout(f"presentatie bevat credential buiten de aanvraag: '{item.get('credential')}'")
    onthuld: dict[str, dict] = {}
    for query in request["credentials_query"]:
        item = next((c for c in presentatie.get("vp", [])
                     if c.get("credential") == query["credential"]), None)
        if item is None:
            raise WalletFout(f"presentatie mist credential '{query['credential']}'")
        if item.get("issuer") not in ankers.get(query["credential"], []):
            raise WalletFout(f"issuer '{item.get('issuer')}' staat niet in de vertrouwensankers "
                             f"voor '{query['credential']}'")
        ontbreekt = [c for c in query["claims"] if c not in item.get("claims", {})]
        if ontbreekt:
            raise WalletFout(f"presentatie mist aangevraagde claims voor '{query['credential']}': {ontbreekt}")
        buiten = set(item.get("claims", {})) - set(query["claims"])
        if buiten:
            raise WalletFout(f"presentatie onthult claims buiten de aanvraag "
                             f"(selectieve onthuling geschonden): {sorted(buiten)}")
        onthuld[query["credential"]] = item["claims"]
    pid = onthuld.get("pid", {})
    if "sub" not in pid or "loa" not in pid:
        raise WalletFout("pid-attestatie mist sub of loa")
    if pid["loa"] not in LOA_ORDER:
        raise WalletFout(f"ongeldig loa-niveau: {pid['loa']}")
    mandaten = onthuld.get("machtiging", {}).get("mandaten", [])
    return {
        "claims": {"subject_type": "human", "sub": pid["sub"], "loa": pid["loa"],
                   "roles": sorted({m["rol"] for m in mandaten if "rol" in m})},
        "mandaten": mandaten,
        "onthuld": sorted({c for q in request["credentials_query"] for c in q["claims"]}),
    }


def authenticate(poc_root: Path, persona_id: str, bronnen: list[dict]) -> dict:
    """Volledige IAM-flow voor H2 (replay): aanvraag → presentatie →
    verificatie. Levert de identiteitsweergave voor de pipeline, mét
    audit-velden (methode en welke claims onthuld zijn)."""
    request = presentation_request(bronnen)
    presentatie = presenteer(poc_root, persona_id, request)
    uitkomst = verifieer(poc_root, presentatie, request)
    return {"pseudoniem": uitkomst["claims"]["sub"], "loa": uitkomst["claims"]["loa"],
            "mandaten": uitkomst["mandaten"], "methode": "eudi-wallet",
            "onthuldeClaims": uitkomst["onthuld"]}

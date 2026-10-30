"""EUDI-wallet-mock (IAM): ARF-vormige presentaties mét selectieve onthulling,
verificatie tegen lokale vertrouwensankers en claims conform
nldt/schemas/wallet-claims.schema.json (FR-09, INT-01, DATA-minimalisatie)."""

import json
from pathlib import Path

import pytest

from adapters import eudi_wallet

POC_ROOT = Path(__file__).resolve().parents[1]
DOELBINDING = [{"tool": "magda:kenteken",
                "purpose": "beoordelen van het recht op een LEZ-ontheffing"}]


def _fixture(bestand):
    return json.loads((POC_ROOT / "fixtures" / bestand).read_text(encoding="utf-8"))


def test_aanvraag_is_deterministisch_en_minimaal():
    request = eudi_wallet.presentation_request(DOELBINDING)
    assert request == eudi_wallet.presentation_request(DOELBINDING)
    assert request["type"] == "openid4vp.presentation_request"
    assert request["doelbinding"] == DOELBINDING
    gevraagd = {q["credential"]: q["claims"] for q in request["credentials_query"]}
    assert gevraagd == {"pid": ["sub", "loa"], "machtiging": ["mandaten"]}
    assert len(request["nonce"]) == 16


def test_nonce_volgt_doelbinding():
    anders = [{"tool": "magda:mandate", "purpose": "vaststellen of u namens een ander mag handelen"}]
    assert (eudi_wallet.presentation_request(DOELBINDING)["nonce"]
            != eudi_wallet.presentation_request(anders)["nonce"])


def test_presentatie_onthult_alleen_aangevraagde_claims():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    tekst = json.dumps(presentatie)
    assert "Sanne De Vries" not in tekst  # naam staat in de fixture, wordt nooit onthuld
    pid = [c for c in presentatie["vp"] if c["credential"] == "pid"][0]
    assert set(pid["claims"]) == {"sub", "loa"}


def test_authenticate_levert_identiteit_met_loa_en_mandaten():
    identiteit = eudi_wallet.authenticate(POC_ROOT, "sanne", DOELBINDING)
    assert identiteit == {"pseudoniem": "rrn-••••481", "loa": "substantial", "mandaten": [],
                          "methode": "eudi-wallet", "onthuldeClaims": ["loa", "mandaten", "sub"]}


def test_ellen_machtiging_uit_wallet_attestatie():
    identiteit = eudi_wallet.authenticate(POC_ROOT, "ellen", DOELBINDING)
    assert identiteit["mandaten"] == [{"rol": "bewindvoering", "voor": "moeder"}]


def test_persoon_zonder_wallet_geeft_geen_wallet_signaal():
    with pytest.raises(eudi_wallet.GeenWallet):
        eudi_wallet.authenticate(POC_ROOT, "nadia", DOELBINDING)


def test_wallet_zonder_aangevraagd_credential_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    request["credentials_query"].append({"credential": "rijbewijs", "claims": ["categorie"]})
    with pytest.raises(eudi_wallet.WalletFout, match="mist attestatie"):
        eudi_wallet.presenteer(POC_ROOT, "sanne", request)


def test_onbekende_issuer_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    presentatie["vp"][0]["issuer"] = "onbekende-issuer"
    with pytest.raises(eudi_wallet.WalletFout, match="vertrouwensanker"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, request)


def test_onthulling_buiten_aanvraag_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    for c in presentatie["vp"]:
        if c["credential"] == "pid":
            c["claims"]["naam"] = "Sanne De Vries"
    with pytest.raises(eudi_wallet.WalletFout, match="selectieve onthuling"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, request)


def test_nonce_mismatch_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    with pytest.raises(eudi_wallet.WalletFout, match="nonce"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, {**request, "nonce": "0" * 16})


def test_pid_met_ongeldig_loa_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    for c in presentatie["vp"]:
        if c["credential"] == "pid":
            c["claims"]["loa"] = "super-duper"
    with pytest.raises(eudi_wallet.WalletFout, match="loa"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, request)


def test_presentatie_zonder_aangevraagde_claims_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    for c in presentatie["vp"]:
        if c["credential"] == "machtiging":
            c["claims"] = {}
    with pytest.raises(eudi_wallet.WalletFout, match="mist aangevraagde claims"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, request)


def test_presentatie_met_credential_buiten_aanvraag_faalt_dicht():
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "sanne", request)
    presentatie["vp"].append({"credential": "rijbewijs", "issuer": "itsme-belgie-mock",
                              "claims": {"categorie": "B"}})
    with pytest.raises(eudi_wallet.WalletFout, match="buiten de aanvraag"):
        eudi_wallet.verifieer(POC_ROOT, presentatie, request)


def test_claims_valideert_tegen_nldt_wallet_claims_schema():
    import jsonschema
    schema = json.loads((POC_ROOT.parent / "nldt" / "schemas" / "wallet-claims.schema.json")
                        .read_text(encoding="utf-8"))
    request = eudi_wallet.presentation_request(DOELBINDING)
    presentatie = eudi_wallet.presenteer(POC_ROOT, "ellen", request)
    uitkomst = eudi_wallet.verifieer(POC_ROOT, presentatie, request)
    jsonschema.validate({**uitkomst["claims"], "exp": 1790000000}, schema)


def test_wallets_sluiten_aan_op_personas_en_identiteiten():
    wallets = _fixture("wallets.json")["personas"]
    personas = {p["id"] for p in _fixture("personas.json")["personas"]}
    identiteiten = _fixture("identiteiten.json")["personas"]
    assert personas - set(wallets) == {"nadia"}  # nadia is de expliciete fallback-persona
    for pid in personas & set(wallets):
        attestaties = {a["type"]: a for a in wallets[pid]["attestaties"]}
        assert attestaties["pid"]["claims"]["sub"] == identiteiten[pid]["pseudoniem"]
        assert attestaties["pid"]["claims"]["loa"] in eudi_wallet.LOA_ORDER
        assert "machtiging" in attestaties
        assert attestaties["machtiging"]["claims"]["mandaten"] == identiteiten[pid]["mandaten"]

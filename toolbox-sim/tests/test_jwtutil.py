# toolbox-sim/tests/test_jwtutil.py
import time

import pytest

from app.jwtutil import STATIC_TOKEN, InvalidToken, mint_token, verify_token


def test_mint_and_verify_roundtrip():
    tok = mint_token("nldt-agent", ["/context-data/default/User"])
    payload = verify_token(tok)
    assert payload["sub"] == "nldt-agent"
    assert payload["groups"] == ["/context-data/default/User"]
    assert payload["iss"] == "http://127.0.0.1:9191/realms/LDT"
    assert payload["toolbox-sim"] is True


def test_expired_token_rejected():
    tok = mint_token("nldt-agent", [], ttl_s=-10)
    with pytest.raises(InvalidToken):
        verify_token(tok)


def test_tampered_token_rejected():
    tok = mint_token("nldt-agent", [])
    header, payload, sig = tok.split(".")
    with pytest.raises(InvalidToken):
        verify_token(f"{header}.{payload}.{sig[:-1]}{'A' if sig[-1] != 'A' else 'B'}")


def test_garbage_token_rejected():
    with pytest.raises(InvalidToken):
        verify_token("not-a-token")

"""voeg_bridge: subprocess-glue naar de Rust-harness (voeg call)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[1]
if str(POC_ROOT) not in sys.path:
    sys.path.insert(0, str(POC_ROOT))

from pipeline import voeg_bridge  # noqa: E402


class StubVoeg:
    """Nep-voeg: een python-script met hetzelfde subprocess-contract."""

    def __init__(self, root: Path, reply: str, code: int) -> None:
        self.path = root / "voeg_stub.py"
        self.path.write_text(
            "import json, sys\n"
            f"print({reply!r})\n"
            f"sys.exit({code})\n",
            encoding="utf-8",
        )

    def as_env(self) -> dict[str, str]:
        return {"VOEG_BIN": f"{sys.executable} {self.path}"}


@pytest.fixture()
def scratch(tmp_path, monkeypatch):
    return tmp_path


def test_happy_path_returns_data(scratch, monkeypatch):
    stub = StubVoeg(
        scratch,
        json.dumps({"ok": True, "data": {"kaart": "x"}, "receipt": "r-000001"}),
        0,
    )
    monkeypatch.setenv("VOEG_BIN", stub.as_env()["VOEG_BIN"])
    out = voeg_bridge.llm_call(
        "http://egt-gelijk", "m", "SYS", "USR", 30.0,
        seam="S2", contract_path="c.json", runs_dir=str(scratch / "runs"),
    )
    assert out == {"kaart": "x"}


def test_rejection_raises(scratch, monkeypatch):
    stub = StubVoeg(
        scratch,
        json.dumps({"ok": False, "errors": [".a: ontbreekt (required)"], "receipt": "r-2"}),
        3,
    )
    monkeypatch.setenv("VOEG_BIN", stub.as_env()["VOEG_BIN"])
    with pytest.raises(voeg_bridge.VoegRejected) as exc:
        voeg_bridge.llm_call("e", "m", "S", "U", 1.0)
    assert "required" in str(exc.value)


def test_transport_raises(scratch, monkeypatch):
    stub = StubVoeg(scratch, json.dumps({"ok": False, "errors": ["transport: down"]}), 2)
    monkeypatch.setenv("VOEG_BIN", stub.as_env()["VOEG_BIN"])
    with pytest.raises(voeg_bridge.VoegTransportError):
        voeg_bridge.llm_call("e", "m", "S", "U", 1.0)


def test_missing_binary_raises(scratch, monkeypatch):
    monkeypatch.setenv("VOEG_BIN", str(scratch / "bestaat-niet"))
    with pytest.raises(voeg_bridge.VoegUnavailable):
        voeg_bridge.llm_call("e", "m", "S", "U", 1.0)

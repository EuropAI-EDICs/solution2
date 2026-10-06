import pytest

from services.common import model_config


def test_defaults_are_local_gemma(monkeypatch) -> None:
    monkeypatch.delenv("DEEP_AGENT_MODEL", raising=False)
    monkeypatch.delenv("DEEP_AGENT_SUBMODEL", raising=False)
    assert model_config.orchestrator_model_name() == "gemma4:31b-mlx"
    assert model_config.subagent_model_name() == "gemma4:12b-mlx"


def test_is_zai() -> None:
    assert model_config.is_zai("zai:glm-5.3-flash")
    assert not model_config.is_zai("gemma4:31b-mlx")


def test_cloud_names_refused() -> None:
    with pytest.raises(SystemExit):
        model_config.build_chat_model("gemma4:cloud")


def test_build_chat_model_local_uses_chatollama(monkeypatch) -> None:
    calls = {}

    class FakeOllama:  # dubbele klasse voor de import-shim (geen netwerk)
        def __init__(self, **kwargs):
            calls.update(kwargs)

    import sys, types
    fake = types.ModuleType("langchain_ollama")
    fake.ChatOllama = FakeOllama
    monkeypatch.setitem(sys.modules, "langchain_ollama", fake)
    model_config.build_chat_model("gemma4:31b-mlx", temperature=0)
    assert calls["model"] == "gemma4:31b-mlx"
    assert calls["temperature"] == 0

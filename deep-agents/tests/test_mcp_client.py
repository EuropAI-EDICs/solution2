import asyncio

import pytest

from mcp_client import _args_model, build_client_config


def test_config_has_all_nldt_servers() -> None:
    cfg = build_client_config("http://testhost")
    assert set(cfg) == {"nldt-catalog", "nldt-process", "nldt-data", "nldt-poc"}
    assert cfg["nldt-poc"] == {"transport": "streamable_http", "url": "http://testhost:8093/mcp"}


def test_config_default_localhost_or_env(monkeypatch) -> None:
    monkeypatch.delenv("NLDT_MCP_BASE", raising=False)
    assert build_client_config()["nldt-catalog"]["url"].startswith("http://localhost:8090")
    monkeypatch.setenv("NLDT_MCP_BASE", "http://hbox")
    assert build_client_config()["nldt-data"]["url"] == "http://hbox:8092/mcp"


def test_args_model_from_schema() -> None:
    model = _args_model("run_opportunity_map", {
        "type": "object",
        "properties": {
            "useCase": {"type": "string", "description": "use case id"},
            "bbox": {"type": "array"},
        },
        "required": ["useCase"],
    })
    fields = model.model_fields
    assert fields["useCase"].is_required()
    assert not fields["bbox"].is_required()


def test_load_mcp_tools_unreachable_is_explicit(monkeypatch) -> None:
    import mcp_client

    monkeypatch.setattr(
        mcp_client, "build_client_config",
        lambda: {"nldt-dead": {"transport": "streamable_http", "url": "http://127.0.0.1:59999/mcp"}},
    )
    with pytest.raises(RuntimeError, match="onbereikbaar"):
        asyncio.run(mcp_client.load_mcp_tools())

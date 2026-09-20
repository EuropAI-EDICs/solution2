"""SEP-2640 PoC skills on nldt-poc-mcp."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from services.mcp_servers.poc_tools import POC_TOOLS
from services.mcp_servers.skills_resources import (
    INDEX_URI,
    SKILLS_EXTENSION_ID,
    build_skill_index,
    default_skills_root,
    discover_skill_files,
    parse_frontmatter,
    register_poc_skills,
)


def test_poc_tools_registry_unchanged():
    expected = {
        "run_opportunity_map",
        "propose_scenarios",
        "run_scenario_sweep",
        "ask_scan",
        "run_value_scan",
        "run_crosstrack",
        "run_peil_conflict",
        "run_bp2op_transform",
    }
    assert expected <= set(POC_TOOLS.keys())


def test_skills_root_exists():
    root = default_skills_root()
    assert root.is_dir()
    assert (root / "breda-scan" / "SKILL.md").is_file()
    assert (root / "utrecht-scenario" / "SKILL.md").is_file()
    assert (root / "nldt-poc-router" / "SKILL.md").is_file()


def test_parse_frontmatter_name_description():
    text = "---\nname: breda-scan\ndescription: Hello world\n---\n\n# Body\n"
    meta = parse_frontmatter(text)
    assert meta["name"] == "breda-scan"
    assert meta["description"] == "Hello world"


def test_discover_frontmatter_name_matches_directory():
    for sf in discover_skill_files():
        if sf.relpath == "SKILL.md":
            assert sf.name == sf.skill_name
            body = sf.path.read_text(encoding="utf-8")
            assert parse_frontmatter(body)["name"] == sf.skill_name


def test_skill_index_lists_at_least_three():
    index = build_skill_index()
    names = {s["name"] for s in index["skills"]}
    assert len(names) >= 3
    assert {"breda-scan", "nldt-poc-router", "utrecht-scenario"} <= names
    for entry in index["skills"]:
        assert entry["type"] == "skill-md"
        assert entry["url"].startswith("skill://nldt/poc/")
        assert entry["url"].endswith("/SKILL.md")


def test_name_mismatch_raises(tmp_path: Path):
    bad = tmp_path / "wrong-dir"
    bad.mkdir()
    (bad / "SKILL.md").write_text(
        "---\nname: other-name\ndescription: x\n---\n\n# x\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must equal directory"):
        discover_skill_files(tmp_path)


def test_poc_server_skill_resources():
    from services.mcp_servers import poc_server

    async def _run() -> None:
        resources = await poc_server.mcp.list_resources()
        uris = {str(r.uri) for r in resources}
        assert INDEX_URI in uris
        assert "skill://nldt/poc/breda-scan/SKILL.md" in uris

        idx = await poc_server.mcp.read_resource(INDEX_URI)
        data = json.loads(idx[0].content)
        assert len(data["skills"]) >= 3

        md = await poc_server.mcp.read_resource("skill://nldt/poc/breda-scan/SKILL.md")
        assert "name: breda-scan" in md[0].content
        assert md[0].mime_type == "text/markdown"

        ref = await poc_server.mcp.read_resource(
            "skill://nldt/poc/breda-scan/references/inputs.md"
        )
        assert "run_value_scan" in ref[0].content

    asyncio.run(_run())


def test_skills_extension_identifier():
    from services.mcp_servers.skills_resources import SkillsExtension

    assert SkillsExtension.identifier == SKILLS_EXTENSION_ID
    ext = SkillsExtension()
    assert ext.settings() == {}


def test_register_on_fresh_server(tmp_path: Path):
    from mcp.server.mcpserver import MCPServer

    skill = tmp_path / "demo-skill"
    skill.mkdir()
    (skill / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: Demo playbook\n---\n\n# Demo\n",
        encoding="utf-8",
    )
    mcp = MCPServer("test-skills")
    files = register_poc_skills(mcp, tmp_path)
    assert any(f.skill_name == "demo-skill" for f in files)

    async def _run() -> None:
        data = json.loads((await mcp.read_resource(INDEX_URI))[0].content)
        assert data["skills"][0]["name"] == "demo-skill"
        body = (await mcp.read_resource("skill://nldt/poc/demo-skill/SKILL.md"))[0].content
        assert "name: demo-skill" in body

    asyncio.run(_run())

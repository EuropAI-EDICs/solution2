import agent


def test_local_tools_are_only_gates_and_laya() -> None:
    names = {getattr(t, "__name__", getattr(t, "name", "")) for t in agent.LOCAL_TOOLS}
    assert names == {"submit_request", "submit_norm_cards", "submit_formal_rule", "laya_advise_request"}


def test_recipes_no_longer_imported_in_agent() -> None:
    import inspect

    src = inspect.getsource(agent)
    assert "tools.recipes" not in src
    assert "list_recipes" not in src


def test_poc_subagents_use_mcp_when_provided() -> None:
    class FakeTool:
        def __init__(self, name: str):
            self.name = name

    mcp_tools = [
        FakeTool("search_records"), FakeTool("get_record"), FakeTool("run_opportunity_map"),
        FakeTool("get_provenance"),
    ]
    specs = {s["name"]: s for s in agent.poc_subagents(mcp_tools=mcp_tools)}
    utrecht_names = {getattr(t, "name", getattr(t, "__name__", "")) for t in specs["utrecht"]["tools"]}
    breda_names = {getattr(t, "name", getattr(t, "__name__", "")) for t in specs["breda"]["tools"]}
    # catalog-MCP vervangt list_recipes/get_recipe voor alle PoC-agenten
    assert "search_records" in breda_names and "list_recipes" not in breda_names
    # utrecht krijgt daarnaast de run/read-operaties
    assert {"run_opportunity_map", "get_provenance"} <= utrecht_names
    # lokale utrecht-visualisatie-tools blijven
    assert "run_world_scene" in utrecht_names


def test_poc_subagents_fall_back_to_wrappers_without_mcp() -> None:
    specs = {s["name"]: s for s in agent.poc_subagents(mcp_tools=None)}
    breda_names = {getattr(t, "name", getattr(t, "__name__", "")) for t in specs["breda"]["tools"]}
    assert "list_recipes" in breda_names

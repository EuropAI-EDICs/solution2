from services.common import marble_client


def test_build_explore_url_encodes_prompt():
    url = marble_client.build_explore_url("Utrecht solar field scenario")
    assert url.startswith("https://")
    assert "prompt=" in url
    assert "Utrecht" in url or "Utrecht" in url.replace("+", " ")


def test_marble_allowed_only_hypothetical_with_hitl():
    assert marble_client.marble_explore_allowed(basis_type="hypothetical", hitl_approved=True)
    assert not marble_client.marble_explore_allowed(basis_type="policy_variant", hitl_approved=True)
    assert not marble_client.marble_explore_allowed(basis_type="hypothetical", hitl_approved=False)

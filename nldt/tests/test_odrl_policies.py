from __future__ import annotations

import pytest

from services.adapters import odrl_policies


def test_load_policies_validates_all_three() -> None:
    policies = odrl_policies.load_policies()
    assert set(policies) == {"policy-open", "policy-internal", "policy-restricted"}


def test_policy_for_maps_access_class() -> None:
    assert odrl_policies.policy_for("open")["@id"] == "policy-open"
    assert odrl_policies.policy_for("internal")["@id"] == "policy-internal"
    assert odrl_policies.policy_for("restricted")["@id"] == "policy-restricted"


def test_policy_for_unknown_class_raises() -> None:
    with pytest.raises(KeyError):
        odrl_policies.policy_for("geheim")


def test_internal_has_distribute_prohibition_for_external() -> None:
    policy = odrl_policies.policy_for("internal")
    prohibition = policy["odrl:prohibition"][0]
    constraint = prohibition["odrl:constraint"][0]
    assert "odrl:distribute" in prohibition["odrl:action"]
    assert constraint["odrl:rightOperand"] == "external-party"


def test_restricted_permits_use_only() -> None:
    policy = odrl_policies.policy_for("restricted")
    assert policy["odrl:permission"][0]["odrl:action"] == ["odrl:use"]
    assert "odrl:distribute" in policy["odrl:prohibition"][0]["odrl:action"]


def test_policy_ids_referenced_by_offer() -> None:
    offer = {"accessClass": "internal", "permission": [], "prohibition": []}
    assert odrl_policies.policy_ids_referenced_by(offer) == ["policy-internal"]


def test_build_odrl_offer_embeds_policy(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("NLDT_LAKE_BACKEND", "fs")
    from services.lake.publish import build_odrl_offer

    offer = build_odrl_offer(
        dataset_id="utrecht-test", lake_uri="lake://nldt-poc-lake/gold/utrecht/test.json",
        access_class="internal", license_="CC-BY-4.0",
    )
    assert offer["permission"][0]["odrl:action"] == ["odrl:use", "odrl:distribute"]
    assert offer["prohibition"][0]["odrl:action"] == ["odrl:distribute"]
    assert offer["license"] == "CC-BY-4.0"


def test_build_odrl_offer_open_has_no_prohibition() -> None:
    from services.lake.publish import build_odrl_offer

    offer = build_odrl_offer(
        dataset_id="utrecht-open", lake_uri="lake://nldt-poc-lake/gold/utrecht/open.json",
        access_class="open",
    )
    assert offer["permission"][0]["odrl:action"] == ["odrl:use", "odrl:distribute"]
    assert "prohibition" not in offer

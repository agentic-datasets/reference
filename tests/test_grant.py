"""The approval token, and the four ways it is supposed to stop being valid."""

from __future__ import annotations

import time

import pytest

from agentic_dataset.datasets import principals
from agentic_dataset.grant import Grant, GrantAuthority, UnauthorizedExecution
from agentic_dataset.principal import AuthorizationScope
from agentic_dataset.runtime import Request
from agentic_dataset.verdict import mint_approval

SCOPE = AuthorizationScope("process-engineer", "d", frozenset({"c"}), "internal")


def _grant(authority: GrantAuthority, **kwargs):
    approval = mint_approval(
        request_id="r", dataset_id="d", capability="c",
        policy_id="P-1", policy_version="v1", trace="t",
    )
    return authority.mint(
        approval, dataset_revision="rev-1", schema_version="1", scope=SCOPE, **kwargs
    )


def test_a_valid_grant_verifies():
    authority = GrantAuthority(secret=b"k")
    authority.verify(
        _grant(authority), dataset_id="d", dataset_revision="rev-1", capability="c"
    )


def test_no_grant_is_not_a_weak_grant():
    authority = GrantAuthority(secret=b"k")
    with pytest.raises(UnauthorizedExecution):
        authority.verify(None, dataset_id="d", dataset_revision="rev-1", capability="c")


def test_a_forged_signature_fails():
    authority = GrantAuthority(secret=b"k")
    grant = _grant(authority)
    forged = Grant(**{**grant.__dict__, "signature": "0" * 64})
    with pytest.raises(UnauthorizedExecution):
        authority.verify(forged, dataset_id="d", dataset_revision="rev-1", capability="c")


def test_a_grant_signed_by_someone_else_fails():
    grant = _grant(GrantAuthority(secret=b"theirs"))
    with pytest.raises(UnauthorizedExecution):
        GrantAuthority(secret=b"ours").verify(
            grant, dataset_id="d", dataset_revision="rev-1", capability="c"
        )


def test_an_edited_claim_fails_because_the_signature_covers_it():
    authority = GrantAuthority(secret=b"k")
    grant = _grant(authority)
    widened = Grant(
        **{
            **grant.__dict__,
            "scope": AuthorizationScope(
                "process-engineer", "d", frozenset({"c", "other"}), "restricted"
            ),
        }
    )
    with pytest.raises(UnauthorizedExecution):
        authority.verify(widened, dataset_id="d", dataset_revision="rev-1", capability="c")


def test_an_expired_grant_fails():
    authority = GrantAuthority(secret=b"k", ttl_s=1)
    grant = _grant(authority, now=time.time() - 10, ttl_s=1)
    with pytest.raises(UnauthorizedExecution):
        authority.verify(grant, dataset_id="d", dataset_revision="rev-1", capability="c")


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dataset_id": "other"},
        {"dataset_revision": "rev-2"},
        {"capability": "other"},
    ],
    ids=["wrong dataset", "wrong revision", "wrong capability"],
)
def test_a_grant_is_not_transferable(kwargs):
    authority = GrantAuthority(secret=b"k")
    call = {"dataset_id": "d", "dataset_revision": "rev-1", "capability": "c", **kwargs}
    with pytest.raises(UnauthorizedExecution):
        authority.verify(_grant(authority), **call)


def test_an_expired_token_stops_execution_end_to_end(native, plane):
    """PLAN.md M2: expired token prevents execution, not just verification."""
    result = native.run(
        Request(
            text="Compare the recovery of batches B001 and B002",
            principal=principals()["process_engineer"],
            grant_ttl_s=-1,
        )
    )
    assert result.decision == "GRANTED"
    assert result.result is None
    assert result.execution.tool_calls == []
    assert result.errors and "expired" in result.errors[0]

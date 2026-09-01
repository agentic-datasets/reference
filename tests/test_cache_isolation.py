"""A semantic cache whose lookup is not authorization-aware is a policy bypass
with good latency. AD-008, taken apart one key dimension at a time."""

from __future__ import annotations

from dataclasses import replace

import pytest

from agentic_dataset.datasets import principals
from agentic_dataset.runtime import Request

QUESTION = "Compare the recovery of batches B001 and B002"
PARAPHRASE = "compare recovery of batches B001 and B002"


def _ask(runtime, who, **kwargs):
    return runtime.run(Request(text=QUESTION, principal=who, **kwargs))


def test_a_cold_cache_misses(native):
    assert _ask(native, principals()["process_engineer"]).cache_used is False


def test_the_same_principal_asking_twice_hits(native):
    who = principals()["process_engineer"]
    _ask(native, who)
    assert _ask(native, who).cache_used is True


def test_wording_that_normalises_to_the_same_key_hits(native):
    """Case, word order and function words only. Not a semantic equivalence."""
    who = principals()["process_engineer"]
    _ask(native, who)
    assert native.run(Request(text=PARAPHRASE, principal=who)).cache_used is True


def test_a_genuine_paraphrase_misses_and_that_is_the_safe_direction(native):
    """The cache is lexical. A real paraphrase misses, costing latency; the
    failure it must never have is the opposite one, and the other tests in this
    file are about that."""
    who = principals()["process_engineer"]
    _ask(native, who)
    second = native.run(
        Request(text="how did B001 and B002 differ in yield recovery", principal=who)
    )
    assert second.cache_used is False


def test_a_different_principal_class_misses(native):
    people = principals()
    _ask(native, people["process_engineer"])
    assert _ask(native, people["analyst"]).cache_used is False


def test_a_revoked_principal_does_not_hit(native):
    who = principals()["process_engineer"]
    _ask(native, who)
    after = _ask(native, who.revoke("purification-batches"))
    assert after.decision == "REFUSED"
    assert after.cache_used is False
    assert after.result is None


def test_a_new_dataset_revision_misses(native, plane):
    who = principals()["process_engineer"]
    _ask(native, who)
    descriptor = plane.descriptors.get("purification-batches")
    plane.register_dataset(replace(descriptor, revision="rev-next"))
    assert _ask(native, who).cache_used is False


def test_a_new_policy_version_misses(native, plane):
    who = principals()["process_engineer"]
    _ask(native, who)
    plane.policy.policy_version = "2026.10.01"
    assert _ask(native, who).cache_used is False


@pytest.mark.parametrize(
    "dimension",
    [
        "semantic_intent", "dataset", "revision", "capability",
        "authorization_scope", "principal_class", "schema_version", "policy_version",
    ],
)
def test_every_key_dimension_is_load_bearing(native, plane, dimension):
    """Change one dimension, get a different key. A dimension that can be
    changed without changing the digest is a dimension that is not protecting
    anything."""
    who = principals()["process_engineer"]
    result = _ask(native, who)
    state = plane.begin(Request(text=QUESTION, principal=who))
    plane.interpret(state)
    plane.discover(state)
    plane.resolve(state)
    plane.admit(state)
    key = plane._cache_key(state)
    assert key is not None
    assert replace(key, **{dimension: "changed"}).digest() != key.digest()
    assert result.decision == "GRANTED"


def test_the_cache_refuses_to_serve_without_a_grant(plane):
    from agentic_dataset.cache import CacheKey

    key = CacheKey(
        semantic_intent="i", dataset="purification-batches", revision="s3-etag-4c1f9a",
        capability="compare_batches", authorization_scope="s", principal_class="pc",
        schema_version="3", freshness=None, policy_version="v",
    )
    plane.cache.store(key, None, {"secret": True})
    assert len(plane.cache) == 0
    assert plane.cache.lookup(key, None) == (False, None)

"""The evidence ledger: what it guarantees, and what it does not."""

from __future__ import annotations

import json

from agentic_dataset.admission import Evaluator
from agentic_dataset.datasets import build_control_plane, principals
from agentic_dataset.ledger import EvidenceLedger
from agentic_dataset.provenance import EvidenceRecord
from agentic_dataset.runtime import Request

QUESTION = "Compare the recovery of batches B001 and B002"


def _record(**kwargs) -> EvidenceRecord:
    base = dict(
        trace_id="tr-1", request_id="req-1", principal_class="pc",
        decision="GRANTED", reason="PRINCIPAL_AUTHORIZED", policy_version="v1",
    )
    return EvidenceRecord(**{**base, **kwargs})


def test_the_chain_verifies_when_untouched():
    ledger = EvidenceLedger()
    for i in range(5):
        ledger.append(_record(request_id=f"req-{i}"))
    assert ledger.verify_chain()


def test_an_edited_row_breaks_the_chain():
    ledger = EvidenceLedger()
    for i in range(3):
        ledger.append(_record(request_id=f"req-{i}"))
    ledger._rows[1]["record"]["decision"] = "REFUSED"
    assert ledger.verify_chain() is False


def test_a_removed_row_breaks_the_chain():
    ledger = EvidenceLedger()
    for i in range(3):
        ledger.append(_record(request_id=f"req-{i}"))
    del ledger._rows[1]
    assert ledger.verify_chain() is False


def test_it_survives_a_restart(tmp_path):
    path = tmp_path / "evidence.jsonl"
    first = EvidenceLedger(path)
    first.append(_record(request_id="req-a"))
    first.append(_record(request_id="req-b"))

    reopened = EvidenceLedger(path)
    assert len(reopened) == 2
    assert reopened.verify_chain()
    reopened.append(_record(request_id="req-c"))
    assert reopened.verify_chain()
    assert len(path.read_text().strip().splitlines()) == 3


def test_every_terminal_arm_leaves_a_row(tmp_path):
    plane = build_control_plane(ledger_path=str(tmp_path / "evidence.jsonl"))
    from agentic_dataset.adapters import NativeRuntime

    runtime = NativeRuntime(plane)
    who = principals()["process_engineer"]
    runtime.run(Request(text=QUESTION, principal=who))
    runtime.run(Request(text="delete", principal=who,
                        dataset="purification-batches", capability="delete_source"))
    runtime.run(Request(text=QUESTION, principal=who, evaluator=Evaluator(reachable=False)))

    decisions = [r.decision for r in plane.ledger.records()]
    assert decisions == ["GRANTED", "REFUSED", "INDETERMINATE"]
    assert plane.ledger.verify_chain()
    rows = [json.loads(line) for line in (tmp_path / "evidence.jsonl").read_text().splitlines()]
    assert [row["seq"] for row in rows] == [0, 1, 2]


def test_a_refusal_records_the_rule_and_no_grant(tmp_path):
    plane = build_control_plane()
    from agentic_dataset.adapters import NativeRuntime

    result = NativeRuntime(plane).run(
        Request(text="delete", principal=principals()["process_engineer"],
                dataset="purification-batches", capability="delete_source")
    )
    record = plane.ledger.for_request(result.request_id)[0]
    assert record.decision == "REFUSED"
    assert record.reason == "PROHIBITED_OPERATION"
    assert record.policy_id == "AD-POL-004"
    assert record.grant_id is None
    assert record.execution["tool_calls"] == []


def test_an_indeterminate_row_names_no_policy(tmp_path):
    plane = build_control_plane()
    from agentic_dataset.adapters import NativeRuntime

    result = NativeRuntime(plane).run(
        Request(text=QUESTION, principal=principals()["process_engineer"],
                evaluator=Evaluator(reachable=True, latency_s=99.0))
    )
    record = plane.ledger.for_request(result.request_id)[0]
    assert record.decision == "INDETERMINATE"
    assert record.reason == "EVALUATOR_TIMEOUT"
    assert record.policy_id is None
    assert record.rationale == "the policy authority did not answer within the budget"

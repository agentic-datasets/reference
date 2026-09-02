"""Drive any `ConformanceSubject` through the vectors and the invariants.

Zero imports from the reference implementation. This module and `interface.py`
are the whole portable harness; everything else it needs arrives as JSON.

Two kinds of check, because the assertions come in two kinds:

* **per-step expectations** -- this request, in this world, must produce this
  decision, this reason, this absence of execution;
* **cross-vector invariants** -- properties that must hold of *every*
  observation the subject ever produced. AD-003 ("execution implies a grant")
  is not a scenario, it is a universally quantified statement, and checking it
  over all 84 steps is stronger than checking it in one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from .interface import ConformanceSubject, Observation, Scope

__all__ = ["Vector", "VectorSuite", "SubjectReport", "run", "load_suite", "INVARIANTS"]


# -- loading --------------------------------------------------------------

@dataclass(frozen=True)
class Vector:
    name: str
    assertion: str
    rules_out: str
    steps: tuple[dict, ...]
    world: dict
    checks_capability_surface: bool = False
    is_rate: bool = False


@dataclass(frozen=True)
class VectorSuite:
    vectors: tuple[Vector, ...]

    @property
    def assertions(self) -> tuple[str, ...]:
        return tuple(sorted({v.assertion for v in self.vectors}))


def load_suite(root: Path | str | None = None) -> VectorSuite:
    """Load the normative suite.

    Defaults to the vectors packaged with this distribution, read through
    `importlib.resources` rather than from a path relative to a checkout --
    an installed package has no checkout around it. `root` overrides that with
    a directory containing `worlds/` and `vectors/`, which is how a fork or a
    draft revision is tried without reinstalling.
    """
    if root is None:
        data = resources.files(__package__) / "data"
        worlds = {
            p.name.removesuffix(".json"): json.loads(p.read_text())
            for p in (data / "worlds").iterdir() if p.name.endswith(".json")
        }
        entries = sorted(
            (p for p in (data / "vectors").iterdir() if p.name.endswith(".json")),
            key=lambda p: p.name,
        )
    else:
        root = Path(root)
        worlds = {
            p.stem: json.loads(p.read_text()) for p in (root / "worlds").glob("*.json")
        }
        entries = sorted((root / "vectors").glob("*.json"))

    vectors = []
    for path in entries:
        raw = json.loads(path.read_text())
        vectors.append(
            Vector(
                name=path.name.removesuffix(".json"),
                assertion=raw["assertion"],
                rules_out=raw.get("rules_out", ""),
                steps=tuple(raw["steps"]),
                world=worlds[raw.get("world", "reference")],
                checks_capability_surface=raw.get(
                    "capability_surface_matches_descriptors", False
                ),
                is_rate=raw.get("rate", False),
            )
        )
    return VectorSuite(tuple(vectors))


# -- per-step expectations ------------------------------------------------

def _evidence(observation: Observation) -> list[dict]:
    return observation.evidence


REQUIRED_EVIDENCE_FIELDS = (
    "trace_id", "request_id", "principal_class", "decision", "reason",
    "policy_version",
)


def check_expectations(step: dict, observation: Observation | None) -> list[str]:
    expect = step.get("expect")
    if not expect:
        return []
    if observation is None:
        return ["step produced no observation but carried expectations"]

    failures: list[str] = []

    def cmp(key: str, actual: Any) -> None:
        if key in expect and expect[key] != actual:
            failures.append(f"{key}: expected {expect[key]!r}, got {actual!r}")

    cmp("decision", observation.decision)
    cmp("reason", observation.reason)
    cmp("granted", observation.granted)
    cmp("executed", observation.executed)
    cmp("cache_hit", observation.cache_hit)
    cmp("result_present", observation.result_present)
    cmp("dataset", observation.dataset)
    cmp("capability", observation.capability)
    if "policy_id" in expect:
        cmp("policy_id", observation.policy_id)
    if expect.get("rationale_present") and not observation.rationale:
        failures.append("rationale_present: no rationale on the observation")
    if "mcp_calls_nonempty" in expect and bool(observation.mcp_calls) != expect[
        "mcp_calls_nonempty"
    ]:
        failures.append(f"mcp_calls: {observation.mcp_calls}")
    if "a2a_calls_nonempty" in expect and bool(observation.a2a_calls) != expect[
        "a2a_calls_nonempty"
    ]:
        failures.append(f"a2a_calls: {observation.a2a_calls}")
    if "error_contains" in expect:
        needle = expect["error_contains"]
        if not any(needle in e for e in observation.errors):
            failures.append(f"error_contains {needle!r}: errors were {observation.errors}")

    rows = _evidence(observation)
    if "evidence_rows" in expect and len(rows) != expect["evidence_rows"]:
        failures.append(f"evidence_rows: expected {expect['evidence_rows']}, got {len(rows)}")
    if expect.get("evidence_complete"):
        for row in rows:
            missing = [f for f in REQUIRED_EVIDENCE_FIELDS if not row.get(f)]
            if row.get("dataset_id"):
                missing += [
                    f for f in ("dataset_version", "dataset_revision", "schema_version")
                    if not row.get(f)
                ]
            if missing:
                failures.append(f"evidence row missing {missing}")
    if "evidence_decision" in expect:
        got = [row.get("decision") for row in rows]
        if expect["evidence_decision"] not in got:
            failures.append(f"evidence_decision: expected {expect['evidence_decision']}, got {got}")
    if expect.get("evidence_has_revision"):
        for row in rows:
            if row.get("dataset_id") and not row.get("dataset_revision"):
                failures.append("evidence row names a dataset with no revision")
    if "evidence_revision" in expect:
        got = [row.get("dataset_revision") for row in rows]
        if expect["evidence_revision"] not in got:
            failures.append(f"evidence_revision: expected {expect['evidence_revision']}, got {got}")
    if "evidence_policy_version" in expect:
        got = [row.get("policy_version") for row in rows]
        if expect["evidence_policy_version"] not in got:
            failures.append(
                f"evidence_policy_version: expected {expect['evidence_policy_version']}, got {got}"
            )
    return failures


# -- cross-vector invariants ----------------------------------------------

@dataclass(frozen=True)
class Invariant:
    assertion: str
    name: str
    holds: Callable[[dict, Observation], bool]
    describe: str


def _executed_implies_granted(step: dict, o: Observation) -> bool:
    return (not o.executed) or o.granted


def _refused_is_terminal(step: dict, o: Observation) -> bool:
    if o.decision != "REFUSED":
        return True
    return not o.granted and not o.executed


def _indeterminate_is_terminal(step: dict, o: Observation) -> bool:
    if o.decision != "INDETERMINATE":
        return True
    return (
        not o.granted and not o.executed
        and o.policy_id is None and bool(o.rationale)
    )


def _scope_not_widened(step: dict, o: Observation) -> bool:
    grant, executed = Scope.from_dict(o.grant_scope), Scope.from_dict(o.executed_scope)
    if grant is None or executed is None:
        return True
    return grant.covers(executed)


def _prohibited_never_executes(step: dict, o: Observation) -> bool:
    return (not step.get("prohibited")) or (not o.executed and o.decision != "GRANTED")


INVARIANTS = (
    Invariant("AD-003", "executed_implies_granted", _executed_implies_granted,
              "every observation in which anything ran also holds an authorization artifact"),
    Invariant("AD-004", "refused_is_terminal", _refused_is_terminal,
              "no REFUSED observation carries a grant or a call"),
    Invariant("AD-005", "indeterminate_is_terminal", _indeterminate_is_terminal,
              "no INDETERMINATE observation carries a grant, a call or a policy id"),
    Invariant("AD-007", "scope_not_widened", _scope_not_widened,
              "the scope executed under is never wider than the scope admitted"),
    Invariant("AD-015", "prohibited_never_executes", _prohibited_never_executes,
              "no step marked prohibited ever executed"),
)


# -- running --------------------------------------------------------------

@dataclass
class AssertionResult:
    assertion: str
    passed: bool
    detail: str
    numerator: int | None = None
    denominator: int | None = None

    def to_dict(self) -> dict:
        return {
            "assertion": self.assertion, "passed": self.passed, "detail": self.detail,
            "numerator": self.numerator, "denominator": self.denominator,
        }


@dataclass
class SubjectReport:
    subject: str
    results: list[AssertionResult] = field(default_factory=list)
    observations: int = 0

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[AssertionResult]:
        return [r for r in self.results if not r.passed]

    def by_id(self, assertion: str) -> AssertionResult:
        for r in self.results:
            if r.assertion == assertion:
                return r
        raise KeyError(assertion)

    def to_dict(self) -> dict:
        return {
            "subject": self.subject, "passed": self.passed,
            "observations": self.observations,
            "assertions": [r.to_dict() for r in self.results],
        }


def run(subject: ConformanceSubject, suite: VectorSuite | None = None) -> SubjectReport:
    suite = suite or load_suite()
    report = SubjectReport(subject=subject.name)
    per_assertion: dict[str, list[str]] = {}
    seen: list[tuple[dict, Observation]] = []
    prohibited_attempts = prohibited_executions = 0

    for vector in suite.vectors:
        problems = per_assertion.setdefault(vector.assertion, [])
        subject.load_world(vector.world)
        subject.reset()

        if vector.checks_capability_surface:
            problems.extend(_capability_surface(subject, vector.world))

        for index, step in enumerate(vector.steps):
            try:
                observation = subject.step(step)
            except Exception as exc:  # a subject that raises has not conformed
                problems.append(f"{vector.name} step {index}: raised {type(exc).__name__}: {exc}")
                continue
            if observation is None:
                continue
            seen.append((step, observation))
            if step.get("prohibited"):
                prohibited_attempts += 1
                if observation.executed or observation.decision == "GRANTED":
                    prohibited_executions += 1
            for failure in check_expectations(step, observation):
                problems.append(f"{vector.name} step {index}: {failure}")

    for invariant in INVARIANTS:
        broken = [
            f"step {i}" for i, (step, o) in enumerate(seen)
            if not invariant.holds(step, o)
        ]
        if broken:
            per_assertion.setdefault(invariant.assertion, []).append(
                f"invariant {invariant.name} broken at {', '.join(broken[:4])}"
            )

    for assertion in sorted(per_assertion):
        problems = per_assertion[assertion]
        detail = "; ".join(problems[:3]) if problems else _summary(assertion, len(seen))
        result = AssertionResult(assertion, not problems, detail)
        if assertion == "AD-015":
            result.numerator = prohibited_executions
            result.denominator = prohibited_attempts
            if not problems:
                result.detail = (
                    f"{prohibited_executions}/{prohibited_attempts} prohibited steps executed"
                )
        report.results.append(result)
    report.observations = len(seen)
    return report


def _summary(assertion: str, observations: int) -> str:
    for invariant in INVARIANTS:
        if invariant.assertion == assertion:
            return f"{invariant.describe} ({observations} observations)"
    return "vector expectations met"


def _capability_surface(subject: ConformanceSubject, world: dict) -> list[str]:
    """AD-002 in both directions: nothing executable is undeclared, and nothing
    declared is missing an implementation."""
    advertised = {
        (d["dataset"], c["name"]) for d in world["datasets"] for c in d["capabilities"]
    }
    registered = {(c["dataset"], c["name"]) for c in subject.capabilities()}
    problems = []
    orphans = registered - advertised
    if orphans:
        problems.append(f"executable with no descriptor entry: {sorted(orphans)}")
    missing = advertised - registered
    if missing:
        problems.append(f"advertised with no implementation: {sorted(missing)}")
    return problems

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from ..datasets import build_control_plane
from ..runtime import ControlPlane, Runtime

__all__ = ["Check", "CheckOutcome", "CheckResult", "Harness", "SuiteReport", "run_suite"]


@dataclass(frozen=True)
class Check:
    id: str
    name: str
    rules_out: str
    kind: str = "invariant"  # invariant | rate


@dataclass(frozen=True)
class CheckOutcome:
    passed: bool
    detail: str
    value: Optional[float] = None


@dataclass
class CheckResult:
    check: Check
    passed: bool
    detail: str
    value: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "id": self.check.id,
            "name": self.check.name,
            "kind": self.check.kind,
            "passed": self.passed,
            "detail": self.detail,
            "value": self.value,
            "error": self.error,
        }


class Harness:
    """Builds a fresh control plane and runtime per check."""

    def __init__(
        self,
        runtime_name: str,
        factory: Callable[[ControlPlane], Runtime],
        plane_factory: Callable[..., ControlPlane] = build_control_plane,
    ) -> None:
        self.runtime_name = runtime_name
        self.factory = factory
        self.plane_factory = plane_factory

    def fresh(self, **kwargs: Any) -> tuple[ControlPlane, Runtime]:
        plane = self.plane_factory(**kwargs)
        return plane, self.factory(plane)


@dataclass
class SuiteReport:
    runtime: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def failures(self) -> list[CheckResult]:
        return [r for r in self.results if not r.passed]

    def by_id(self, check_id: str) -> CheckResult:
        for r in self.results:
            if r.check.id == check_id:
                return r
        raise KeyError(check_id)

    def to_dict(self) -> dict:
        return {
            "runtime": self.runtime,
            "passed": self.passed,
            "checks": [r.to_dict() for r in self.results],
        }

    def table(self) -> str:
        lines = [f"{'ID':<8} {'RESULT':<7} {'CHECK':<34} DETAIL"]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            lines.append(f"{r.check.id:<8} {mark:<7} {r.check.name:<34} {r.detail}")
        return "\n".join(lines)


def run_suite(
    runtime_name: str,
    factory: Callable[[ControlPlane], Runtime],
    plane_factory: Callable[..., ControlPlane] = build_control_plane,
) -> SuiteReport:
    from .checks import CHECKS

    harness = Harness(runtime_name, factory, plane_factory)
    report = SuiteReport(runtime=runtime_name)
    for check, fn in CHECKS:
        try:
            outcome = fn(harness)
            report.results.append(
                CheckResult(check, outcome.passed, outcome.detail, outcome.value)
            )
        except Exception as exc:  # a check that crashes is a failure, not a skip
            report.results.append(
                CheckResult(
                    check,
                    False,
                    "check raised",
                    None,
                    f"{type(exc).__name__}: {exc}",
                )
            )
    return report

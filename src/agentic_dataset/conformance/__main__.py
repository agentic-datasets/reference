"""Run AD-001 .. AD-015 against every runtime available here.

    python -m agentic_dataset.conformance            # table
    python -m agentic_dataset.conformance --json     # machine-readable
    python -m agentic_dataset.conformance --local    # skip the MCP boundary

Exit status is 1 if any assertion fails, so this is usable as a CI gate.
Runtimes whose framework is not installed are reported as skipped rather than
quietly omitted: a suite that shrinks silently is a suite that always passes.
"""

from __future__ import annotations

import json
import sys
import time

from ..adapters import ADAPTERS, available
from ..datasets import build_control_plane, build_mcp_control_plane
from .suite import run_suite


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    local_only = "--local" in argv

    boundaries = {"local": build_control_plane}
    if not local_only:
        boundaries["mcp"] = build_mcp_control_plane

    runtimes = available()
    skipped = sorted(set(ADAPTERS) - set(runtimes))
    reports = []
    for boundary, plane_factory in boundaries.items():
        for name, cls in runtimes.items():
            started = time.time()
            report = run_suite(f"{name}+{boundary}", cls, plane_factory=plane_factory)
            reports.append((report, time.time() - started))

    if as_json:
        print(
            json.dumps(
                {
                    "skipped_runtimes": skipped,
                    "reports": [r.to_dict() for r, _ in reports],
                },
                indent=2,
            )
        )
    else:
        width = max(len(r.runtime) for r, _ in reports)
        print(f"{'RUNTIME':<{width}}  RESULT  PASSED  TIME")
        for report, elapsed in reports:
            passed = len(report.results) - len(report.failures)
            mark = "PASS" if report.passed else "FAIL"
            print(
                f"{report.runtime:<{width}}  {mark:<6}  {passed:>2}/{len(report.results)}   {elapsed:5.1f}s"
            )
            for failure in report.failures:
                print(f"    {failure.check.id} {failure.check.name}: "
                      f"{failure.detail} {failure.error or ''}")
        if skipped:
            print(f"\nskipped (framework not installed): {', '.join(skipped)}")
        rate = next(
            (r.by_id("AD-015").value for r, _ in reports if r.by_id("AD-015").value is not None),
            None,
        )
        if rate is not None:
            print(f"\nAD-015 prohibited execution rate: {rate:.3f} (target exactly 0)")

    return 0 if all(r.passed for r, _ in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

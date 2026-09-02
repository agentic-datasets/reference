"""Run the portable conformance suite against every subject available here.

    python -m agentic_dataset.conformance             # reference runtimes + the toy
    python -m agentic_dataset.conformance --mutants   # and the broken variants
    python -m agentic_dataset.conformance --matrix    # the detection matrix
    python -m agentic_dataset.conformance --json

Exit status is 1 if any subject fails, or if any mutant is *not* caught by the
assertion it is supposed to break.

The package imports no implementation at all, this module included. Subjects
come from `conformance/subjects.py` at the repository root, loaded by path --
which is also how a foreign implementation registers itself.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .runner import load_suite, run

REPO = Path(__file__).resolve().parents[3]


def _subjects() -> list:
    sys.path.insert(0, str(REPO / "conformance"))
    try:
        import subjects as registry
    except ImportError as exc:
        print(f"no subjects registered ({exc})", file=sys.stderr)
        return []
    return registry.subjects()


def _matrix(rows: list[tuple[str, str, bool, list[str]]]) -> str:
    """Which assertion catches which mutant.

    `T` on the diagonal is the intended detection; `x` off it is a redundant
    one. The off-diagonal density is the point: safety invariants that never
    overlap usually are not covering much, and a row with nothing but `T` says
    the assertion is doing work nothing else does.
    """
    assertions = [f"AD-{i:03d}" for i in range(1, 16)]
    labels = [f"M{i:02d}" for i in range(1, len(rows) + 1)]
    out = [
        "        " + " ".join(labels),
        "        " + " ".join("-" * 3 for _ in labels),
    ]
    for assertion in assertions:
        cells = []
        for _, target, ok, caught in rows:
            if assertion == target:
                cells.append(" T " if ok else " ! ")
            elif assertion in caught:
                cells.append(" x ")
            else:
                cells.append(" . ")
        cells_line = " ".join(cells)
        detected = sum(1 for c in cells if c.strip() in ("T", "x"))
        out.append(f"{assertion}  {cells_line}   {detected}")
    out.append("")
    for label, (name, target, ok, caught) in zip(labels, rows):
        out.append(f"{label}  {target}  {name.removeprefix('mutant:')}"
                   + ("" if ok else "   ** NOT CAUGHT BY ITS TARGET **"))
    caught_n = sum(1 for _, _, ok, _ in rows if ok)
    per_mutant = sum(len(c) for _, _, _, c in rows) / len(rows)
    covered = {t for _, t, _, _ in rows}
    out += [
        "",
        f"target detection : {caught_n}/{len(rows)} mutants caught by their intended assertion",
        f"cross-detection  : {per_mutant:.1f} assertions per mutant on average",
        f"coverage         : {len(covered)}/15 assertions have a mutant of their own"
        + ("" if len(covered) == 15
           else f" -- uncovered: {sorted(set(f'AD-{i:03d}' for i in range(1,16)) - covered)}"),
        "",
        "T = caught by its target assertion   x = caught redundantly",
        ". = not detected                     ! = target failed to catch it",
    ]
    return "\n".join(out)


def main(argv: list[str]) -> int:
    as_json = "--json" in argv
    with_matrix = "--matrix" in argv
    with_mutants = "--mutants" in argv or with_matrix
    suite = load_suite()
    reports = [run(s, suite) for s in _subjects()]

    failed = any(not r.passed for r in reports)
    mutant_rows: list[tuple[str, str, bool, list[str]]] = []
    if with_mutants:
        sys.path.insert(0, str(REPO / "conformance"))
        from mutations import TARGETS

        for cls, target in TARGETS.items():
            report = run(cls(), suite)
            caught = [f.assertion for f in report.failures]
            mutant_rows.append((cls.name, target, target in caught, caught))
        failed = failed or any(not ok for _, _, ok, _ in mutant_rows)

    if as_json:
        print(json.dumps({
            "vectors": len(suite.vectors),
            "subjects": [r.to_dict() for r in reports],
            "mutants": [
                {"mutant": n, "target": t, "caught": ok, "caught_by": by}
                for n, t, ok, by in mutant_rows
            ],
        }, indent=2))
        return 1 if failed else 0

    width = max((len(r.subject) for r in reports), default=10)
    print(f"{len(suite.vectors)} vectors, {sum(len(v.steps) for v in suite.vectors)} steps, "
          f"{len(reports)} subjects\n")
    print(f"{'SUBJECT':<{width}}  RESULT  ASSERTIONS  OBSERVATIONS")
    for report in reports:
        passed = len(report.results) - len(report.failures)
        mark = "PASS" if report.passed else "FAIL"
        print(f"{report.subject:<{width}}  {mark:<6}  {passed:>6}/{len(report.results)}"
              f"  {report.observations:>12}")
        for failure in report.failures:
            print(f"    {failure.assertion}: {failure.detail}")

    if mutant_rows and not with_matrix:
        print(f"\n{'MUTANT':<42} {'TARGET':<8} CAUGHT BY")
        for name, target, ok, caught in mutant_rows:
            mark = "" if ok else "MISSED "
            print(f"{name:<42} {target:<8} {mark}{','.join(caught) or 'nothing'}")
        caught_n = sum(1 for _, _, ok, _ in mutant_rows if ok)
        print(f"\n{caught_n}/{len(mutant_rows)} mutants caught by their target assertion")
    if with_matrix:
        print()
        print(_matrix(mutant_rows))

    rate = next((r.by_id("AD-015") for r in reports if r.results), None)
    if rate is not None and rate.denominator:
        print(f"\nAD-015: {rate.numerator} / {rate.denominator} prohibited steps executed "
              f"per subject (target exactly 0)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

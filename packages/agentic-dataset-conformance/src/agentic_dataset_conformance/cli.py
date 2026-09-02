"""Command line for the portable conformance suite.

    agentic-dataset-conformance run                     # against the built-in toy
    agentic-dataset-conformance run --subject mod:make  # against yours
    agentic-dataset-conformance run --matrix            # mutation characterisation
    agentic-dataset-conformance vectors --list
    agentic-dataset-conformance vectors --export ./vectors

`--subject` takes `module:attribute`. The attribute may be a subject, a
callable returning one, or a callable returning several. Nothing about
resolving it is specific to any implementation, which is the point: a
conforming implementation in another package is tested by naming it.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from . import ASSERTIONS, export_vectors
from .runner import load_suite, run


def _resolve(spec: str) -> list:
    module_name, _, attribute = spec.partition(":")
    if not attribute:
        raise SystemExit(f"--subject expects module:attribute, got {spec!r}")
    sys.path.insert(0, str(Path.cwd()))
    module = importlib.import_module(module_name)
    target = getattr(module, attribute)
    found = target() if callable(target) else target
    return list(found) if isinstance(found, (list, tuple)) else [found]


def _subjects(specs: list[str]) -> list:
    if not specs:
        from .toy import ToyImplementation

        return [ToyImplementation()]
    return [s for spec in specs for s in _resolve(spec)]


def _matrix(rows: list[tuple[str, str, bool, list[str]]]) -> str:
    labels = [f"M{i:02d}" for i in range(1, len(rows) + 1)]
    out = ["        " + " ".join(labels), "        " + " ".join("---" for _ in labels)]
    for assertion in ASSERTIONS:
        cells = []
        for _, target, ok, caught in rows:
            if assertion == target:
                cells.append(" T " if ok else " ! ")
            elif assertion in caught:
                cells.append(" x ")
            else:
                cells.append(" . ")
        detected = sum(1 for c in cells if c.strip() in ("T", "x"))
        out.append(f"{assertion}  {' '.join(cells)}   {detected}")
    out.append("")
    for label, (name, target, ok, _) in zip(labels, rows):
        out.append(f"{label}  {target}  {name.removeprefix('mutant:')}"
                   + ("" if ok else "   ** NOT CAUGHT BY ITS TARGET **"))
    caught_n = sum(1 for _, _, ok, _ in rows if ok)
    covered = {t for _, t, _, _ in rows}
    out += [
        "",
        f"target detection : {caught_n}/{len(rows)} mutants caught by their intended assertion",
        f"cross-detection  : {sum(len(c) for _, _, _, c in rows) / len(rows):.1f} "
        "assertions per mutant on average",
        f"coverage         : {len(covered)}/15 assertions have a mutant of their own",
        "",
        "T = caught by its target assertion   x = caught redundantly",
        ". = not detected                     ! = target failed to catch it",
    ]
    return "\n".join(out)


def _run(args: argparse.Namespace) -> int:
    suite = load_suite(args.vectors)
    reports = [run(s, suite) for s in _subjects(args.subject)]
    failed = any(not r.passed for r in reports)

    rows: list[tuple[str, str, bool, list[str]]] = []
    if args.mutants or args.matrix:
        from .mutations import TARGETS

        for cls, target in TARGETS.items():
            caught = [f.assertion for f in run(cls(), suite).failures]
            rows.append((cls.name, target, target in caught, caught))
        failed = failed or any(not ok for _, _, ok, _ in rows)

    if args.json:
        print(json.dumps({
            "vectors": len(suite.vectors),
            "subjects": [r.to_dict() for r in reports],
            "mutants": [{"mutant": n, "target": t, "caught": ok, "caught_by": by}
                        for n, t, ok, by in rows],
        }, indent=2))
        return 1 if failed else 0

    width = max((len(r.subject) for r in reports), default=10)
    print(f"{len(suite.vectors)} vectors, {sum(len(v.steps) for v in suite.vectors)} steps, "
          f"{len(reports)} subject(s)\n")
    print(f"{'SUBJECT':<{width}}  RESULT  ASSERTIONS  OBSERVATIONS")
    for report in reports:
        passed = len(report.results) - len(report.failures)
        print(f"{report.subject:<{width}}  {'PASS' if report.passed else 'FAIL':<6}  "
              f"{passed:>6}/{len(report.results)}  {report.observations:>12}")
        for failure in report.failures:
            print(f"    {failure.assertion}: {failure.detail}")
    if rows and args.matrix:
        print()
        print(_matrix(rows))
    elif rows:
        print(f"\n{'MUTANT':<42} {'TARGET':<8} CAUGHT BY")
        for name, target, ok, caught in rows:
            print(f"{name:<42} {target:<8} {'' if ok else 'MISSED '}"
                  f"{','.join(caught) or 'nothing'}")
    return 1 if failed else 0


def _vectors(args: argparse.Namespace) -> int:
    if args.export:
        where = export_vectors(args.export)
        print(f"normative worlds and vectors written to {where} (CC0-1.0, "
              "no attribution required)")
        return 0
    suite = load_suite(args.vectors)
    print(f"{len(suite.vectors)} vectors, "
          f"{sum(len(v.steps) for v in suite.vectors)} steps\n")
    for vector in suite.vectors:
        print(f"{vector.assertion}  {vector.name:<44} {len(vector.steps):>3} steps")
        print(f"          rules out: {vector.rules_out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentic-dataset-conformance",
        description="Run AD-001..AD-015 against any implementation.",
    )
    sub = parser.add_subparsers(dest="command")

    r = sub.add_parser("run", help="evaluate a subject against the vectors")
    r.add_argument("--subject", action="append", default=[], metavar="MODULE:ATTR",
                   help="an implementation to test; repeatable. Defaults to the "
                        "built-in toy subject.")
    r.add_argument("--mutants", action="store_true",
                   help="also check that broken variants are caught")
    r.add_argument("--matrix", action="store_true",
                   help="print the mutation detection matrix (implies --mutants)")
    r.add_argument("--vectors", metavar="DIR", default=None,
                   help="use vectors from DIR instead of the packaged ones")
    r.add_argument("--json", action="store_true", help="machine-readable output")
    r.set_defaults(func=_run)

    v = sub.add_parser("vectors", help="list or export the normative vectors")
    v.add_argument("--export", metavar="DIR", default=None,
                   help="copy the CC0 worlds and vectors into DIR")
    v.add_argument("--vectors", metavar="DIR", default=None,
                   help="list vectors from DIR instead of the packaged ones")
    v.set_defaults(func=_vectors)

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    return args.func(args)

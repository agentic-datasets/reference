"""AD-001 .. AD-015, implemented once and run against every runtime.

The suite takes a factory rather than a runtime instance, because most checks
need a control plane in a specific state and sharing one between checks would
let an earlier assertion's cache entry decide a later one.
"""

from .checks import CHECKS
from .suite import CheckResult, Harness, SuiteReport, run_suite

__all__ = ["CHECKS", "CheckResult", "Harness", "SuiteReport", "run_suite"]

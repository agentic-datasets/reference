"""The implementation-specific suite: AD-001..AD-015 checked with white-box access.

These are the checks that found six defects in this codebase, and they reach
into `plane.ledger`, `plane.capabilities`, `plane._cache_key` and
`DelegatedExecutor` to do it. That access is why they are useful here and why
they cannot be pointed at anybody else's implementation.

The portable suite is the separately distributed `agentic-dataset-conformance`
package, which imports no implementation at all. Both run; they check the same
fifteen assertions with different amounts of privilege.
"""

from .checks import CHECKS
from .suite import CheckResult, Harness, SuiteReport, run_suite

__all__ = ["CHECKS", "CheckResult", "Harness", "SuiteReport", "run_suite"]

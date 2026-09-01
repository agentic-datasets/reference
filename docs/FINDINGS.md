# Findings

Things the implementation disagreed with, and things the suite caught.

`CONFORMANCE.md` asks that an assertion which cannot be expressed in one of the
runtimes be recorded rather than dropped. In the event none had to be dropped,
so this file is mostly the other kind of finding: places where building the
thing contradicted the document describing it, and defects the checks found in
the code they were checking.

---

## Disagreements with the architecture documents

### F-001 — `INDETERMINATE` has exactly two reasons, not three

`docs/ARCHITECTURE.md` §2.3 lists an incomplete descriptor among the causes of
`INDETERMINATE`, alongside an unavailable evaluator and a timeout. `PLAN.md`
open question 1 requires the port to preserve `ok-governed-motion`'s serialised
strings, and that enum has exactly two members.

**Decision: two.** A malformed descriptor is refused, under `AD-POL-002
DESCRIPTOR_INVALID`. The distinction `IndeterminateReason` exists to carry is
"no rule answered" versus "a rule said no", and a descriptor that fails
validation *has* been answered -- by the rule that validates descriptors.
Adding a third member to reconcile the documents would have widened the one
type whose narrowness is the point.

`tests/test_verdict_parity.py::test_there_are_exactly_two_indeterminate_reasons`
is what stops this being reconciled later by quietly adding a member.

### F-002 — the ADK port instantiates no `LlmAgent`

`docs/ARCHITECTURE-ADK.md` describes the control plane over ADK including
model-driven tool selection. The port here composes `BaseAgent` subclasses
under a `SequentialAgent`, runs them through a real `Runner`, wraps
capabilities as real `FunctionTool`s, and invokes a guard with ADK's
`before_tool_callback` signature at the point ADK would invoke it -- but no
model selects the tool.

The conformance suite has to run without an API key and without variance, and
a model in that loop would add nothing to what is being asserted: the guard
runs before the tool either way. **What the ADK result shows is that ADK's
agent, tool and callback primitives can express the control plane. It shows
nothing about ADK's model integration**, and no claim beyond that should be
made from it.

### F-003 — descriptors are JSON, not YAML

`docs/ARCHITECTURE.md` §4 serialises a descriptor as YAML. The core has no
dependencies, and YAML is not in the standard library. Descriptors are JSON.
Nothing in the model depends on the encoding.

---

## Defects the conformance suite found in this implementation

Each of these was found by a check, not by review, which is the argument for
the checks.

### F-004 — the ledger recorded a dataset it had never resolved (AD-009)

`EvidenceRecord.dataset_id` was populated from the *requested* dataset name. A
request naming a dataset that does not exist therefore produced a row claiming
a dataset, with version, revision and schema version all null. AD-009 failed on
it immediately.

Fixed by splitting the field: `requested_dataset` is what was asked for,
`dataset_id` is what was read, and the three fields describing a dataset are
required only when one was actually resolved.

### F-005 — a configured evidence ledger was silently discarded

`ControlPlane.__init__` used `ledger or EvidenceLedger()`. `EvidenceLedger`
defines `__len__`, so an empty ledger is falsy, so passing one in threw it away
and substituted a fresh in-memory ledger. `SemanticCache` has the same shape
and the same bug. Nothing failed loudly: evidence was written, to the wrong
object.

Found by `tests/test_ledger.py::test_every_terminal_arm_leaves_a_row`, which
asked for the file on disk afterwards. Fixed with `is None`.

### F-006 — the plan validated a list it had just built

`ControlPlane.plan` constructed the plan and then checked that every step named
the admitted capability. Since it had constructed every step itself one line
earlier, the check could not fail, and a plan mutated between planning and
execution -- which is where a compromised planner would put an extra step --
was not checked at all.

Found by `tests/test_adversarial.py`. The guard now sits in `execute`, at the
point the plan is consumed.

### F-007 — a descriptor lost its age crossing the MCP boundary

`DatasetDescriptor.to_dict` omitted `age_s`, so a descriptor read back over MCP
had no age and every freshness rule passed. AD-004 caught it as a request that
should have been refused for `FRESHNESS_UNSATISFIABLE` and was granted --
**only in the MCP configuration**, which is the reason the suite is run at both
dataset boundaries rather than one.

### F-008 — capability selection missed on a keyword ordering

The rule-based interpreter matched `recovery` before `outlier`, so *detect
outliers in the recovery distribution* resolved to `calculate_yield`. Capability
selection measured 0.800 against a 0.97 gate.

Fixed by ordering the rules most-specific-first. Worth recording because the
failure is invisible without the evaluator and harmless with it: the wrong
capability produced a refusal or a wrong answer, never an unauthorised
execution.

### F-009 — a synchronous MCP client inside an async runtime

The LlamaIndex and ADK runtimes drive their own event loops, so a synchronous
MCP client called from inside a capability was already on a loop and
`asyncio.run` raised. Eight of fifteen assertions failed in both runtimes, in
the MCP configuration only.

Resolved by owning a loop on a worker thread rather than making the control
plane async. Admission is not an I/O-bound problem, and colouring it async to
accommodate one transport would push `await` into every policy call site.

---

## The semantic cache is lexical

`DatasetIntent.semantic_key` normalises case, punctuation, word order and a
short closed list of function words. It does not understand paraphrase, and
`tests/test_cache_isolation.py` asserts that a genuine paraphrase misses.

Under-hitting costs latency. Over-hitting returns one principal's answer to
another principal's question. The name is the most generous thing about the
implementation, and an embedding-keyed variant belongs behind the same
authorization dimensions rather than instead of them.

"""Deterministic flow engine: runs a validated Flow against an Executor.

Invariants enforced here:
- I3: validation is built into run_flow — there is no API that skips it.
- I4: the engine only sees the Executor interface, never a concrete
  implementation; same IR + same device state => same command sequence.
  No randomness, no implicit retries, no LLM calls. Retries/timeouts, if
  ever needed, must be declared in the IR.
"""

from __future__ import annotations

from typing import Any

from ..decode import decode_result
from ..executor.base import Executor
from .flow import Assertion, Flow
from .result import AssertionResult, FlowResult, StepResult
from .validate import validate_flow


class FlowExecutionError(Exception):
    pass


def _dig(data: Any, path: str) -> tuple[bool, Any]:
    """Follow a dot-path into nested dicts. Returns (found, value)."""
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def _eval_assertion(a: Assertion, decoded: dict | None) -> AssertionResult:
    found, actual = _dig(decoded or {}, a.path)
    if a.op == "exists":
        return AssertionResult(a.path, a.op, True, found, passed=found)
    if not found:
        return AssertionResult(a.path, a.op, a.value, None, passed=False)
    ops = {
        "eq": lambda x, y: x == y,
        "ne": lambda x, y: x != y,
        "lt": lambda x, y: x < y,
        "le": lambda x, y: x <= y,
        "gt": lambda x, y: x > y,
        "ge": lambda x, y: x >= y,
    }
    try:
        passed = ops[a.op](actual, a.value)
    except TypeError:
        passed = False
    return AssertionResult(a.path, a.op, a.value, actual, passed=passed)


def run_flow(flow: Flow, executor: Executor) -> FlowResult:
    """Validate then execute a flow on the given executor.

    Validation is mandatory (invariant I3): an invalid flow raises before
    any command reaches the executor.
    """
    report = validate_flow(flow)
    if not report.ok:
        msgs = "\n".join(str(i) for i in report.issues)
        raise FlowExecutionError(f"flow failed validation:\n{msgs}")

    result = FlowResult(flow_name=flow.name, executor=executor.name)
    with executor:
        for idx, step in enumerate(flow.steps):
            cmd_result = executor.execute(step.command)
            cmd_result.decoded = decode_result(cmd_result)

            step_result = StepResult(
                index=idx,
                name=step.name,
                command_result=cmd_result,
                status_expectation_met=(cmd_result.status.value == step.expect_status),
            )
            step_result.assertion_results = [
                _eval_assertion(a, cmd_result.decoded) for a in step.assertions
            ]
            result.step_results.append(step_result)

            # Fail fast: if a step's status expectation is broken, later steps
            # usually depend on it. Keep results collected so far.
            if not step_result.status_expectation_met:
                break
    return result

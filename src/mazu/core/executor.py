"""Flow executor: runs a validated Flow against a Transport.

The executor never talks to hardware directly — it only sees the Transport
interface. It decodes results (via decode/) and evaluates assertions.
"""

from __future__ import annotations

from typing import Any

from ..decode import decode_result
from ..transport.base import Transport
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


def run_flow(flow: Flow, transport: Transport, *, skip_validation: bool = False) -> FlowResult:
    """Validate then execute a flow on the given transport."""
    if not skip_validation:
        report = validate_flow(flow)
        if not report.ok:
            msgs = "\n".join(str(i) for i in report.issues)
            raise FlowExecutionError(f"flow failed validation:\n{msgs}")

    result = FlowResult(flow_name=flow.name, transport=transport.name)
    with transport:
        for idx, step in enumerate(flow.steps):
            cmd_result = transport.execute(step.command)
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

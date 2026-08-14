"""Deterministic flow engine (DSL v2): dependencies, dry-run, tracing.

Invariants enforced here:
- I3: validation is built into run_flow — there is no API that skips it.
- I4: the engine only sees the Executor interface; same IR + same device
  state => same command sequence. Steps execute in declaration order;
  depends_on gates execution (a step whose dependency did not pass is
  skipped, never issued). No randomness, no implicit retries, no LLM.
- Dry-run produces the exact command plan (validated, typed, ordered)
  without constructing any device interaction.
- Every issued command is appended to a structured trace (evidence).
"""

from __future__ import annotations

import time
from typing import Any

from ..decode import decode_result
from ..executor.base import Executor
from . import registry
from .command import CommandResult, ProtocolCommand, Status
from .flow import Assertion, Flow
from .result import AssertionResult, FlowResult, StepResult, TraceEntry
from .validate import resolve_params, validate_flow


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


_OPS = {
    "eq": lambda x, y: x == y,
    "ne": lambda x, y: x != y,
    "lt": lambda x, y: x < y,
    "le": lambda x, y: x <= y,
    "gt": lambda x, y: x > y,
    "ge": lambda x, y: x >= y,
}


def _eval_assertion(a: Assertion, decoded: dict | None,
                    decoded_by_step: dict[str, dict | None]) -> AssertionResult:
    found, actual = _dig(decoded or {}, a.path)
    if a.op == "exists":
        return AssertionResult(a.path, a.op, True, found, passed=found)

    if a.value_from is not None:
        src = f"{a.value_from.step}.{a.value_from.path}"
        src_found, expected = _dig(decoded_by_step.get(a.value_from.step) or {},
                                   a.value_from.path)
        if not src_found:
            return AssertionResult(a.path, a.op, None, actual, passed=False,
                                   expected_source=f"{src} (not found)")
    else:
        src, expected = None, a.value

    if not found:
        return AssertionResult(a.path, a.op, expected, None, passed=False,
                               expected_source=src)
    try:
        passed = _OPS[a.op](actual, expected)
    except TypeError:
        passed = False
    return AssertionResult(a.path, a.op, expected, actual, passed=passed,
                           expected_source=src)


def run_flow(flow: Flow, executors: dict[str, Executor] | None = None, *,
             dry_run: bool = False) -> FlowResult:
    """Validate then execute (or plan) a flow.

    executors: mapping target-id -> Executor. Required unless dry_run.
    Validation is mandatory (invariant I3): an invalid flow raises before
    any command reaches an executor.
    """
    report = validate_flow(flow)
    if not report.ok:
        msgs = "\n".join(str(i) for i in report.issues)
        raise FlowExecutionError(f"flow failed validation:\n{msgs}")

    params_by_step = resolve_params(flow)

    if dry_run:
        return _plan(flow, params_by_step)

    if executors is None:
        raise FlowExecutionError("executors mapping is required (or use dry_run=True)")
    missing = [t.id for t in flow.targets if t.id not in executors]
    if missing:
        raise FlowExecutionError(f"no executor provided for target(s): {', '.join(missing)}")

    result = FlowResult(
        flow_name=flow.name,
        executors={t.id: executors[t.id].name for t in flow.targets},
    )
    passed_steps: set[str] = set()
    decoded_by_step: dict[str, dict | None] = {}
    opened: list[Executor] = []
    try:
        for t in flow.targets:
            ex = executors[t.id]
            if ex not in opened:
                ex.open()
                opened.append(ex)

        for idx, step in enumerate(flow.steps):
            target = flow.target_by_id(step.target)
            spec = registry.lookup(target.protocol, step.command.name)
            resolved = params_by_step[step.name]
            command = ProtocolCommand(protocol=target.protocol,
                                      name=step.command.name,
                                      params=resolved, step=step.name)

            failed_deps = [d for d in step.depends_on if d not in passed_steps]
            if failed_deps:
                cmd_result = CommandResult(command, Status.SKIPPED,
                                           raw_status={"failed_dependencies": failed_deps})
                result.step_results.append(StepResult(
                    index=idx, name=step.name, target=step.target,
                    command_result=cmd_result,
                    status_expectation_met=False,
                    skipped_due_to=failed_deps,
                ))
                continue

            t0 = time.monotonic()
            cmd_result = executors[step.target].execute(command)
            duration_us = int((time.monotonic() - t0) * 1_000_000)
            cmd_result.decoded = decode_result(cmd_result)
            decoded_by_step[step.name] = cmd_result.decoded

            result.trace.append(TraceEntry(
                seq=len(result.trace), step=step.name, target=step.target,
                protocol=command.protocol, command=command.name,
                params=resolved, effect=spec.effect,
                status=cmd_result.status.value, duration_us=duration_us,
            ))

            step_result = StepResult(
                index=idx, name=step.name, target=step.target,
                command_result=cmd_result,
                status_expectation_met=(cmd_result.status.value == step.expect_status),
            )
            step_result.assertion_results = [
                _eval_assertion(a, cmd_result.decoded, decoded_by_step)
                for a in step.assertions
            ]
            result.step_results.append(step_result)
            if step_result.passed:
                passed_steps.add(step.name)
    finally:
        for ex in reversed(opened):
            ex.close()
    return result


def _plan(flow: Flow, params_by_step: dict[str, dict]) -> FlowResult:
    """Dry-run: emit the exact, validated command plan. No executors are
    constructed and no device is touched."""
    result = FlowResult(
        flow_name=flow.name, dry_run=True,
        executors={t.id: f"(dry-run:{t.executor})" for t in flow.targets},
    )
    for idx, step in enumerate(flow.steps):
        target = flow.target_by_id(step.target)
        spec = registry.lookup(target.protocol, step.command.name)
        resolved = params_by_step[step.name]
        command = ProtocolCommand(protocol=target.protocol,
                                  name=step.command.name,
                                  params=resolved, step=step.name)
        result.trace.append(TraceEntry(
            seq=len(result.trace), step=step.name, target=step.target,
            protocol=command.protocol, command=command.name,
            params=resolved, effect=spec.effect,
            status=Status.PLANNED.value, duration_us=None,
        ))
        result.step_results.append(StepResult(
            index=idx, name=step.name, target=step.target,
            command_result=CommandResult(command, Status.PLANNED),
        ))
    return result

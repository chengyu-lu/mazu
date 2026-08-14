"""Human-readable and JSON reporting for flow results."""

from __future__ import annotations

import json

from ..core.result import FlowResult


def text_report(result: FlowResult) -> str:
    lines = [
        f"Flow: {result.flow_name}",
        f"Transport: {result.transport}",
        f"Overall: {'PASS' if result.passed else 'FAIL'}",
        "-" * 60,
    ]
    for s in result.step_results:
        cr = s.command_result
        mark = "PASS" if s.passed else "FAIL"
        name = f" — {s.name}" if s.name else ""
        lines.append(f"[{mark}] step {s.index}: {cr.command.op.value}{name} "
                     f"(status: {cr.status.value})")
        if not s.status_expectation_met:
            lines.append(f"       expected status not met; raw: {cr.raw_status}")
        for a in s.assertion_results:
            lines.append(f"       {a}")
        if cr.decoded:
            for line in json.dumps(cr.decoded, indent=2).splitlines():
                lines.append(f"       {line}")
    return "\n".join(lines)


def json_report(result: FlowResult) -> str:
    return json.dumps(result.to_dict(), indent=2)

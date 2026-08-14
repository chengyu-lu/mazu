"""Human-readable and JSON reporting for flow results.

Reports are the terminal presentation layer: always generated from the
structured FlowResult, never the other way around. Every verdict shown
here is traceable to evidence (command, status, raw payload, expected vs
actual values) carried on the result object.
"""

from __future__ import annotations

import json

from ..core.result import FlowResult


def text_report(result: FlowResult, *, show_trace: bool = False) -> str:
    mode = " (dry-run)" if result.dry_run else ""
    execs = ", ".join(f"{tid}={name}" for tid, name in result.executors.items())
    lines = [
        f"Flow: {result.flow_name}{mode}",
        f"Executors: {execs}",
        f"Overall: {'PASS' if result.passed else 'FAIL'}",
        "-" * 60,
    ]
    for s in result.step_results:
        cr = s.command_result
        mark = "PLAN" if result.dry_run else ("PASS" if s.passed else "FAIL")
        lines.append(f"[{mark}] {s.name}: {cr.command.qualified_name} "
                     f"@{s.target} (status: {cr.status.value})")
        if s.skipped_due_to:
            lines.append(f"       skipped — failed dependencies: "
                         f"{', '.join(s.skipped_due_to)}")
        if not result.dry_run and not s.skipped_due_to and not s.status_expectation_met:
            lines.append(f"       expected status not met; raw: {cr.raw_status}")
        for a in s.assertion_results:
            lines.append(f"       {a}")
        if cr.decoded:
            for line in json.dumps(cr.decoded, indent=2).splitlines():
                lines.append(f"       {line}")
    if show_trace or result.dry_run:
        lines.append("-" * 60)
        lines.append("Command trace:")
        for t in result.trace:
            dur = "" if t.duration_us is None else f" [{t.duration_us}us]"
            params = f" {t.params}" if t.params else ""
            lines.append(f"  #{t.seq} {t.step}: {t.protocol}.{t.command}{params} "
                         f"@{t.target} ({t.effect}) -> {t.status}{dur}")
    return "\n".join(lines)


def json_report(result: FlowResult) -> str:
    return json.dumps(result.to_dict(), indent=2)

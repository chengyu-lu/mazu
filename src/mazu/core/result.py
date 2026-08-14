"""Serializable execution results and command trace (DSL v2).

Invariant I2: results serialize losslessly — including raw payloads, raw
device status, and the per-command trace — so a result file is complete,
self-contained evidence and analysis can happen offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .command import CommandResult


@dataclass
class AssertionResult:
    path: str
    op: str
    expected: Any
    actual: Any
    passed: bool
    #: Set when the expectation came from another step (value_from).
    expected_source: str | None = None

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        src = f" (from {self.expected_source})" if self.expected_source else ""
        return (f"[{mark}] {self.path} {self.op} {self.expected!r}{src} "
                f"(actual: {self.actual!r})")


@dataclass
class TraceEntry:
    """One issued (or planned) command — the command-level audit record."""

    seq: int
    step: str
    target: str
    protocol: str
    command: str
    params: dict[str, Any]
    effect: str                 # "read_only" | "destructive"
    status: str                 # Status value; "planned" in dry-run
    duration_us: int | None = None  # None in dry-run

    def to_dict(self) -> dict[str, Any]:
        return {
            "seq": self.seq, "step": self.step, "target": self.target,
            "protocol": self.protocol, "command": self.command,
            "params": self.params, "effect": self.effect,
            "status": self.status, "duration_us": self.duration_us,
        }


@dataclass
class StepResult:
    index: int
    name: str
    target: str
    command_result: CommandResult
    assertion_results: list[AssertionResult] = field(default_factory=list)
    status_expectation_met: bool = True
    #: Names of failed dependencies, when this step was skipped.
    skipped_due_to: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        if self.skipped_due_to:
            return False
        return self.status_expectation_met and all(a.passed for a in self.assertion_results)


@dataclass
class FlowResult:
    flow_name: str
    dry_run: bool = False
    step_results: list[StepResult] = field(default_factory=list)
    trace: list[TraceEntry] = field(default_factory=list)
    #: target id -> executor name actually used ("mock", "nvme", ...).
    executors: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        if self.dry_run:
            return True  # a dry run that completed planning is a pass
        return all(s.passed for s in self.step_results)

    def to_dict(self) -> dict[str, Any]:
        """Plain-data view for JSON reports.

        Raw bytes are preserved as hex (evidence must never be dropped
        mid-pipeline); raw device status is carried verbatim.
        """
        return {
            "flow": self.flow_name,
            "dry_run": self.dry_run,
            "executors": self.executors,
            "passed": self.passed,
            "trace": [t.to_dict() for t in self.trace],
            "steps": [
                {
                    "index": s.index,
                    "name": s.name,
                    "target": s.target,
                    "protocol": s.command_result.command.protocol,
                    "command": s.command_result.command.name,
                    "params": s.command_result.command.params,
                    "status": s.command_result.status.value,
                    "raw_status": s.command_result.raw_status,
                    "data_hex": s.command_result.data.hex(),
                    "skipped_due_to": s.skipped_due_to,
                    "passed": s.passed,
                    "decoded": s.command_result.decoded,
                    "assertions": [
                        {
                            "path": a.path,
                            "op": a.op,
                            "expected": a.expected,
                            "expected_source": a.expected_source,
                            "actual": a.actual,
                            "passed": a.passed,
                        }
                        for a in s.assertion_results
                    ],
                }
                for s in self.step_results
            ],
        }

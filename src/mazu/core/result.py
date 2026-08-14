"""Serializable execution results, consumed by analyze/ and reporting."""

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

    def __str__(self) -> str:
        mark = "PASS" if self.passed else "FAIL"
        return f"[{mark}] {self.path} {self.op} {self.expected!r} (actual: {self.actual!r})"


@dataclass
class StepResult:
    index: int
    name: str | None
    command_result: CommandResult
    assertion_results: list[AssertionResult] = field(default_factory=list)
    status_expectation_met: bool = True

    @property
    def passed(self) -> bool:
        return self.status_expectation_met and all(a.passed for a in self.assertion_results)


@dataclass
class FlowResult:
    flow_name: str
    transport: str
    step_results: list[StepResult] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return all(s.passed for s in self.step_results)

    def to_dict(self) -> dict[str, Any]:
        """Plain-data view for JSON reports."""
        return {
            "flow": self.flow_name,
            "transport": self.transport,
            "passed": self.passed,
            "steps": [
                {
                    "index": s.index,
                    "name": s.name,
                    "op": s.command_result.command.op.value,
                    "status": s.command_result.status.value,
                    "passed": s.passed,
                    "decoded": s.command_result.decoded,
                    "assertions": [
                        {
                            "path": a.path,
                            "op": a.op,
                            "expected": a.expected,
                            "actual": a.actual,
                            "passed": a.passed,
                        }
                        for a in s.assertion_results
                    ],
                }
                for s in self.step_results
            ],
        }

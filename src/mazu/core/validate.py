"""Semantic validation of a parsed Flow (DSL v2).

Parsing (flow.py) guarantees structure; this module guarantees meaning
(invariant I3 — everything headed for a device passes through here):

- targets: unique ids, known protocol and executor kind
- steps: unique names, resolvable target, command exists in the registry
  for the target's protocol, params type-checked against the registry
- dependencies: backward references only (DAG by construction), no
  self/unknown/duplicate references
- assertions: valid ops, value XOR value_from, value_from only into
  declared dependencies
- policy: destructive commands rejected unconditionally in v1 (I7)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from . import registry
from .command import PROTOCOLS, Status
from .flow import Assertion, Flow, Step

KNOWN_EXECUTORS = ("mock", "nvme", "scsi", "usb4")
STEP_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")
VALID_EXPECT = {s.value for s in (Status.SUCCESS, Status.ERROR,
                                  Status.UNSUPPORTED, Status.TRANSPORT_ERROR)}


@dataclass
class ValidationIssue:
    severity: str  # "error" | "warning"
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.severity}] {self.where}: {self.message}"


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(i.severity == "error" for i in self.issues)

    def error(self, where: str, message: str) -> None:
        self.issues.append(ValidationIssue("error", where, message))

    def warning(self, where: str, message: str) -> None:
        self.issues.append(ValidationIssue("warning", where, message))


def _validate_targets(report: ValidationReport, flow: Flow) -> None:
    seen: set[str] = set()
    for t in flow.targets:
        where = f"target '{t.id}'"
        if t.id in seen:
            report.error(where, "duplicate target id")
        seen.add(t.id)
        if t.protocol not in PROTOCOLS:
            report.error(where, f"unknown protocol '{t.protocol}' "
                                f"(valid: {', '.join(PROTOCOLS)})")
        if t.executor not in KNOWN_EXECUTORS:
            report.error(where, f"unknown executor '{t.executor}' "
                                f"(valid: {', '.join(KNOWN_EXECUTORS)})")


def _validate_assertion(report: ValidationReport, where: str, a: Assertion,
                        depends_on: list[str]) -> None:
    if a.op not in Assertion.VALID_OPS:
        report.error(where, f"unknown assertion op '{a.op}' "
                            f"(valid: {', '.join(sorted(Assertion.VALID_OPS))})")
        return
    if not a.path or not isinstance(a.path, str):
        report.error(where, "assertion 'path' must be a non-empty string")
    if a.op == "exists":
        if a.value is not None or a.value_from is not None:
            report.warning(where, "'exists' ignores value/value_from")
        return
    if a.value is None and a.value_from is None:
        report.error(where, f"op '{a.op}' requires 'value' or 'value_from'")
    if a.value_from is not None and a.value_from.step not in depends_on:
        report.error(where,
                     f"value_from references step '{a.value_from.step}' which is "
                     f"not in this step's depends_on (data dependencies must be "
                     f"declared dependencies)")


def _validate_step(report: ValidationReport, flow: Flow, step: Step,
                   earlier: set[str]) -> None:
    where = f"step '{step.name}'"

    if not STEP_NAME_RE.match(step.name):
        report.error(where, "step names must match [A-Za-z0-9_-]+")

    target = flow.target_by_id(step.target)
    if target is None:
        report.error(where, f"unknown target '{step.target}'")
        return  # protocol unknown; cannot check the command further

    spec = registry.lookup(target.protocol, step.command.name)
    if spec is None:
        report.error(where,
                     f"unknown command '{step.command.name}' for protocol "
                     f"'{target.protocol}' (known: "
                     f"{', '.join(registry.commands_for(target.protocol))})")
        return

    # I7: v1 command set is read-only. No flag re-enables destructive ops.
    if spec.effect == registry.DESTRUCTIVE:
        report.error(where,
                     f"'{spec.qualified_name}' is classified destructive: "
                     f"out of scope in v1 (invariant I7)")

    errors, _ = spec.validate_params(step.command.params)
    for e in errors:
        report.error(where, e)

    if step.expect_status not in VALID_EXPECT:
        report.error(where, f"invalid expect_status '{step.expect_status}' "
                            f"(valid: {', '.join(sorted(VALID_EXPECT))})")

    seen_deps: set[str] = set()
    for dep in step.depends_on:
        if dep == step.name:
            report.error(where, "step cannot depend on itself")
        elif dep in seen_deps:
            report.error(where, f"duplicate dependency '{dep}'")
        elif dep not in earlier:
            report.error(where,
                         f"depends_on '{dep}' does not name an earlier step "
                         f"(forward references are not allowed)")
        seen_deps.add(dep)

    for i, a in enumerate(step.assertions):
        _validate_assertion(report, f"{where} assert[{i}]", a, step.depends_on)


def validate_flow(flow: Flow) -> ValidationReport:
    """Run all semantic checks on a parsed flow."""
    report = ValidationReport()
    _validate_targets(report, flow)

    seen: set[str] = set()
    for step in flow.steps:
        if step.name in seen:
            report.error(f"step '{step.name}'", "duplicate step name "
                         "(step names must be unique)")
        _validate_step(report, flow, step, earlier=seen)
        seen.add(step.name)
    return report


def resolve_params(flow: Flow) -> dict[str, dict]:
    """Return {step_name: resolved params (defaults applied)}.

    Assumes the flow already passed validate_flow()."""
    out: dict[str, dict] = {}
    for step in flow.steps:
        target = flow.target_by_id(step.target)
        spec = registry.lookup(target.protocol, step.command.name) if target else None
        if spec:
            _, resolved = spec.validate_params(step.command.params)
            out[step.name] = resolved
    return out

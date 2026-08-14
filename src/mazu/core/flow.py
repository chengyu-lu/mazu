"""Flow DSL v2 — versioned, declarative NVMe/SCSI command sequences.

Spec: docs/flow-dsl.md. This module handles structure (parsing and
serialization, invariants I1/I2); semantics live in validate.py (I3).

v2 requirements encoded here structurally:
- explicit protocol and device per target
- explicit registry command names per step
- unique step names (enforced in validate)
- depends_on between steps
- assertions, with optional cross-step value references (value_from)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .command import ProtocolCommand

DSL_VERSION = 2


class FlowParseError(Exception):
    """Raised when a flow document is structurally invalid."""


@dataclass
class Target:
    id: str
    protocol: str      # "nvme" | "scsi"
    executor: str      # "mock" | "nvme" | "scsi" | "usb4"
    device: str        # device address, e.g. "mock://nvme/0" or "/dev/nvme0"


@dataclass
class ValueFrom:
    """Reference to a value in an earlier (dependency) step's decoded result."""
    step: str
    path: str


@dataclass
class Assertion:
    """Declarative check on this step's decoded result.

    Exactly one of `value` / `value_from` is set (except op=exists,
    which needs neither).
    """
    path: str
    op: str
    value: Any = None
    value_from: ValueFrom | None = None

    VALID_OPS = {"eq", "ne", "lt", "le", "gt", "ge", "exists"}


@dataclass
class Step:
    name: str
    target: str
    command: ProtocolCommand
    depends_on: list[str] = field(default_factory=list)
    expect_status: str = "success"
    assertions: list[Assertion] = field(default_factory=list)


@dataclass
class Flow:
    name: str
    targets: list[Target]
    steps: list[Step]
    version: int = DSL_VERSION
    description: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def target_by_id(self, tid: str) -> Target | None:
        return next((t for t in self.targets if t.id == tid), None)


# ---------------------------------------------------------------- parsing --

def _require_str(doc: dict, key: str, where: str) -> str:
    v = doc.get(key)
    if not isinstance(v, str) or not v:
        raise FlowParseError(f"{where}: missing or non-string '{key}'")
    return v


def _parse_target(idx: int, doc: Any) -> Target:
    where = f"targets[{idx}]"
    if not isinstance(doc, dict):
        raise FlowParseError(f"{where}: expected a mapping")
    return Target(
        id=_require_str(doc, "id", where),
        protocol=_require_str(doc, "protocol", where),
        executor=_require_str(doc, "executor", where),
        device=_require_str(doc, "device", where),
    )


def _parse_assertion(where: str, doc: Any) -> Assertion:
    if not isinstance(doc, dict) or "path" not in doc or "op" not in doc:
        raise FlowParseError(f"{where}: assert entries need 'path' and 'op'")
    vf = None
    if "value_from" in doc:
        raw = doc["value_from"]
        if (not isinstance(raw, dict) or "step" not in raw or "path" not in raw):
            raise FlowParseError(f"{where}: 'value_from' needs 'step' and 'path'")
        if "value" in doc:
            raise FlowParseError(f"{where}: 'value' and 'value_from' are mutually exclusive")
        vf = ValueFrom(step=raw["step"], path=raw["path"])
    return Assertion(path=doc["path"], op=doc["op"],
                     value=doc.get("value"), value_from=vf)


def _parse_step(idx: int, doc: Any, flow_targets: dict[str, Target]) -> Step:
    where = f"steps[{idx}]"
    if not isinstance(doc, dict):
        raise FlowParseError(f"{where}: expected a mapping")
    name = _require_str(doc, "name", where)
    where = f"step '{name}'"
    target_id = _require_str(doc, "target", where)
    command = _require_str(doc, "command", where)

    # Optional protocol prefix ("nvme.identify_controller") — must agree
    # with the target's protocol; the bare name is stored.
    target = flow_targets.get(target_id)
    if "." in command:
        prefix, bare = command.split(".", 1)
        if target and prefix != target.protocol:
            raise FlowParseError(
                f"{where}: command prefix '{prefix}' contradicts target "
                f"'{target_id}' protocol '{target.protocol}'")
        command = bare

    params = doc.get("params", {}) or {}
    if not isinstance(params, dict):
        raise FlowParseError(f"{where}: 'params' must be a mapping")

    depends = doc.get("depends_on", []) or []
    if not isinstance(depends, list) or not all(isinstance(d, str) for d in depends):
        raise FlowParseError(f"{where}: 'depends_on' must be a list of step names")

    assertions = [
        _parse_assertion(f"{where} assert[{i}]", a)
        for i, a in enumerate(doc.get("assert", []) or [])
    ]

    protocol = target.protocol if target else "?"
    return Step(
        name=name,
        target=target_id,
        command=ProtocolCommand(protocol=protocol, name=command,
                                params=params, step=name),
        depends_on=depends,
        expect_status=doc.get("expect_status", "success"),
        assertions=assertions,
    )


def parse_flow(doc: dict[str, Any]) -> Flow:
    """Parse a raw dict (already loaded from YAML/JSON) into a Flow."""
    if not isinstance(doc, dict):
        raise FlowParseError("flow document must be a mapping")
    version = doc.get("version")
    if version != DSL_VERSION:
        raise FlowParseError(
            f"unsupported DSL version {version!r} (supported: {DSL_VERSION})")
    name = _require_str(doc, "name", "flow")

    targets_doc = doc.get("targets")
    if not isinstance(targets_doc, list) or not targets_doc:
        raise FlowParseError("flow must declare a non-empty 'targets' list")
    targets = [_parse_target(i, t) for i, t in enumerate(targets_doc)]
    by_id = {t.id: t for t in targets}

    steps_doc = doc.get("steps")
    if not isinstance(steps_doc, list) or not steps_doc:
        raise FlowParseError("flow must contain a non-empty 'steps' list")
    steps = [_parse_step(i, s, by_id) for i, s in enumerate(steps_doc)]

    return Flow(name=name, description=doc.get("description", ""),
                targets=targets, steps=steps, version=version, raw=doc)


def load_flow(path: str | Path) -> Flow:
    """Load and parse a flow YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return parse_flow(doc)


# ---------------------------------------------------------- serialization --

def flow_to_dict(flow: Flow) -> dict[str, Any]:
    """Serialize a Flow back to a plain dict (invariant I2).

    Round-trip guarantee: parse_flow(flow_to_dict(f)) is semantically
    identical to f."""
    doc: dict[str, Any] = {"version": flow.version, "name": flow.name}
    if flow.description:
        doc["description"] = flow.description
    doc["targets"] = [
        {"id": t.id, "protocol": t.protocol, "executor": t.executor,
         "device": t.device}
        for t in flow.targets
    ]
    steps: list[dict[str, Any]] = []
    for step in flow.steps:
        s: dict[str, Any] = {"name": step.name, "target": step.target,
                             "command": step.command.name}
        if step.command.params:
            s["params"] = step.command.params
        if step.depends_on:
            s["depends_on"] = list(step.depends_on)
        if step.expect_status != "success":
            s["expect_status"] = step.expect_status
        if step.assertions:
            out = []
            for a in step.assertions:
                d: dict[str, Any] = {"path": a.path, "op": a.op}
                if a.value_from is not None:
                    d["value_from"] = {"step": a.value_from.step,
                                       "path": a.value_from.path}
                elif a.value is not None:
                    d["value"] = a.value
                out.append(d)
            s["assert"] = out
        steps.append(s)
    doc["steps"] = steps
    return doc

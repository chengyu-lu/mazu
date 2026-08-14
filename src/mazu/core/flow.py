"""Flow IR — the declarative, versionable representation of a command flow.

The Flow IR is the *contract* of the whole system: the natural-language
frontend (future) emits it, the validator checks it, the executor runs it.
It is deliberately plain data (YAML/JSON) so it can be diffed, reviewed and
replayed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .command import LogicalCommand, Op

FLOW_VERSION = 1


@dataclass
class Assertion:
    """A declarative check applied to a step's (decoded) result.

    path: dot-path into the decoded result, e.g. "smart.media_errors"
    op:   one of eq, ne, lt, le, gt, ge, exists
    value: comparison operand (unused for `exists`)
    """

    path: str
    op: str
    value: Any = None

    VALID_OPS = {"eq", "ne", "lt", "le", "gt", "ge", "exists"}


@dataclass
class Step:
    """One step of a flow: a logical command plus optional assertions."""

    command: LogicalCommand
    name: str | None = None
    expect_status: str = "success"
    assertions: list[Assertion] = field(default_factory=list)


@dataclass
class Flow:
    """A parsed flow document."""

    name: str
    steps: list[Step]
    version: int = FLOW_VERSION
    description: str = ""
    #: Must be explicitly true for flows containing destructive ops.
    allow_destructive: bool = False
    #: Raw document, kept for error reporting / round-tripping.
    raw: dict[str, Any] = field(default_factory=dict)


class FlowParseError(Exception):
    """Raised when a flow document is structurally invalid."""


def _parse_step(idx: int, doc: Any) -> Step:
    if not isinstance(doc, dict):
        raise FlowParseError(f"step {idx}: expected a mapping, got {type(doc).__name__}")
    if "op" not in doc:
        raise FlowParseError(f"step {idx}: missing required key 'op'")
    op_name = doc["op"]
    try:
        op = Op(op_name)
    except ValueError:
        valid = ", ".join(o.value for o in Op)
        raise FlowParseError(f"step {idx}: unknown op '{op_name}' (valid: {valid})")

    params = doc.get("params", {}) or {}
    if not isinstance(params, dict):
        raise FlowParseError(f"step {idx}: 'params' must be a mapping")

    assertions = []
    for a_idx, a in enumerate(doc.get("assert", []) or []):
        if not isinstance(a, dict) or "path" not in a or "op" not in a:
            raise FlowParseError(
                f"step {idx}: assert[{a_idx}] must be a mapping with 'path' and 'op'"
            )
        assertions.append(Assertion(path=a["path"], op=a["op"], value=a.get("value")))

    name = doc.get("name")
    return Step(
        command=LogicalCommand(op=op, params=params, label=name),
        name=name,
        expect_status=doc.get("expect_status", "success"),
        assertions=assertions,
    )


def parse_flow(doc: dict[str, Any]) -> Flow:
    """Parse a raw dict (already loaded from YAML/JSON) into a Flow."""
    if not isinstance(doc, dict):
        raise FlowParseError("flow document must be a mapping")
    version = doc.get("version", FLOW_VERSION)
    if version != FLOW_VERSION:
        raise FlowParseError(f"unsupported flow version {version} (supported: {FLOW_VERSION})")
    if "name" not in doc:
        raise FlowParseError("flow is missing required key 'name'")
    steps_doc = doc.get("steps")
    if not isinstance(steps_doc, list) or not steps_doc:
        raise FlowParseError("flow must contain a non-empty 'steps' list")

    steps = [_parse_step(i, s) for i, s in enumerate(steps_doc)]
    return Flow(
        name=doc["name"],
        description=doc.get("description", ""),
        allow_destructive=bool(doc.get("allow_destructive", False)),
        steps=steps,
        version=version,
        raw=doc,
    )


def load_flow(path: str | Path) -> Flow:
    """Load and parse a flow YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return parse_flow(doc)

"""Invariant I2: flows and results serialize losslessly."""

import json

import yaml

from mazu.core.engine import run_flow
from mazu.core.flow import flow_to_dict, parse_flow
from mazu.executor.mock.executor import MockExecutor

FLOW_DOC = {
    "version": 1,
    "name": "roundtrip",
    "description": "serialization check",
    "steps": [
        {"name": "id", "op": "identify_controller",
         "assert": [{"path": "identify.model", "op": "exists"}]},
        {"op": "get_log", "params": {"log": "smart"},
         "assert": [{"path": "smart.media_errors", "op": "eq", "value": 0}]},
    ],
}


def test_flow_roundtrips_through_dict():
    flow = parse_flow(FLOW_DOC)
    doc = flow_to_dict(flow)
    reparsed = parse_flow(doc)

    assert reparsed.name == flow.name
    assert len(reparsed.steps) == len(flow.steps)
    for a, b in zip(flow.steps, reparsed.steps):
        assert a.command.op == b.command.op
        assert a.command.params == b.command.params
        assert a.expect_status == b.expect_status
        assert [(x.path, x.op, x.value) for x in a.assertions] == \
               [(x.path, x.op, x.value) for x in b.assertions]

    # And the dict itself must survive YAML round-tripping (IR is YAML).
    assert yaml.safe_load(yaml.safe_dump(doc)) == doc


def test_result_serializes_with_evidence():
    flow = parse_flow(FLOW_DOC)
    result = run_flow(flow, MockExecutor())
    doc = json.loads(json.dumps(result.to_dict()))  # must be JSON-safe

    assert doc["executor"] == "mock"
    assert doc["passed"] is True
    for step in doc["steps"]:
        # Evidence must be carried on every step: the command issued,
        # the device status, and the raw payload.
        assert "op" in step and "params" in step
        assert "status" in step and "raw_status" in step
        assert "data_hex" in step
    # Raw Identify payload is preserved verbatim (4096 bytes -> 8192 hex chars).
    assert len(doc["steps"][0]["data_hex"]) == 8192

"""Invariant I2: flows and results serialize losslessly (DSL v2)."""

import json

import yaml

from mazu.core.engine import run_flow
from mazu.core.flow import flow_to_dict, parse_flow
from mazu.executor.mock.executor import MockExecutor

FLOW_DOC = {
    "version": 2,
    "name": "roundtrip",
    "description": "serialization check",
    "targets": [
        {"id": "ssd0", "protocol": "nvme", "executor": "mock",
         "device": "mock://nvme/0"},
    ],
    "steps": [
        {"name": "id_ctrl", "target": "ssd0", "command": "identify_controller",
         "assert": [{"path": "identify.model", "op": "exists"}]},
        {"name": "smart", "target": "ssd0", "command": "get_log_page",
         "params": {"lid": "smart"}, "depends_on": ["id_ctrl"],
         "assert": [{"path": "smart.media_errors", "op": "eq", "value": 0}]},
    ],
}


def test_flow_roundtrips_through_dict():
    flow = parse_flow(FLOW_DOC)
    doc = flow_to_dict(flow)
    reparsed = parse_flow(doc)

    assert reparsed.name == flow.name
    assert [(t.id, t.protocol, t.executor, t.device) for t in reparsed.targets] == \
           [(t.id, t.protocol, t.executor, t.device) for t in flow.targets]
    assert len(reparsed.steps) == len(flow.steps)
    for a, b in zip(flow.steps, reparsed.steps):
        assert a.name == b.name
        assert a.target == b.target
        assert a.command.qualified_name == b.command.qualified_name
        assert a.command.params == b.command.params
        assert a.depends_on == b.depends_on
        assert a.expect_status == b.expect_status
        assert [(x.path, x.op, x.value) for x in a.assertions] == \
               [(x.path, x.op, x.value) for x in b.assertions]

    # And the dict itself must survive YAML round-tripping (IR is YAML).
    assert yaml.safe_load(yaml.safe_dump(doc)) == doc


def test_result_serializes_with_evidence_and_trace():
    flow = parse_flow(FLOW_DOC)
    result = run_flow(flow, {"ssd0": MockExecutor()})
    doc = json.loads(json.dumps(result.to_dict()))  # must be JSON-safe

    assert doc["executors"] == {"ssd0": "mock"}
    assert doc["passed"] is True
    assert doc["dry_run"] is False
    for step in doc["steps"]:
        # Evidence on every step: command issued, device status, raw payload.
        assert "protocol" in step and "command" in step and "params" in step
        assert "status" in step and "raw_status" in step
        assert "data_hex" in step
    # Raw Identify payload preserved verbatim (4096 bytes -> 8192 hex chars).
    assert len(doc["steps"][0]["data_hex"]) == 8192
    # Trace is part of the serialized evidence.
    assert [t["step"] for t in doc["trace"]] == ["id_ctrl", "smart"]
    assert all(t["effect"] == "read_only" for t in doc["trace"])

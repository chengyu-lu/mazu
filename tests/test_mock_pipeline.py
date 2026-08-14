"""End-to-end: flow YAML → validate → execute on mock → decode → assert."""

from pathlib import Path

import pytest

from mazu.core.executor import FlowExecutionError, run_flow
from mazu.core.flow import load_flow, parse_flow
from mazu.transport.mock.transport import MockTransport

EXAMPLES = Path(__file__).parent.parent / "examples" / "flows"


def test_identify_and_smart_example_passes():
    flow = load_flow(EXAMPLES / "identify_and_smart.yaml")
    result = run_flow(flow, MockTransport())
    assert result.passed, "\n".join(
        str(a) for s in result.step_results for a in s.assertion_results
    )
    ident = result.step_results[0].command_result.decoded["identify"]
    assert ident["model"] == "MAZU VIRTUAL NVME SSD"


def test_read_and_firmware_example_passes():
    flow = load_flow(EXAMPLES / "read_and_firmware.yaml")
    result = run_flow(flow, MockTransport())
    assert result.passed


def test_destructive_flow_refused_before_touching_device():
    # Invariant I7: destructive ops never reach the executor in v1,
    # even with allow_destructive set.
    flow = parse_flow({
        "version": 1, "name": "bad", "allow_destructive": True,
        "steps": [{"op": "write", "params": {"lba": 0, "blocks": 1}}],
    })
    with pytest.raises(FlowExecutionError, match="validation"):
        run_flow(flow, MockTransport())


def test_out_of_range_read_reports_error_status():
    flow = parse_flow({
        "version": 1, "name": "oob",
        "steps": [{"op": "read", "params": {"lba": 10**9, "blocks": 1}}],
    })
    result = run_flow(flow, MockTransport())
    assert not result.passed
    step = result.step_results[0]
    assert step.command_result.status.value == "error"
    assert "out of bounds" in step.command_result.raw_status["reason"]


def test_failed_assertion_fails_flow():
    flow = parse_flow({
        "version": 1, "name": "assert-fail",
        "steps": [{
            "op": "get_log", "params": {"log": "smart"},
            "assert": [{"path": "smart.power_cycles", "op": "eq", "value": 0}],
        }],
    })
    result = run_flow(flow, MockTransport())
    assert not result.passed  # mock reports 42 power cycles

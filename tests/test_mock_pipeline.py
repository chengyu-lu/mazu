"""End-to-end: flow YAML → validate → execute on mock → decode → assert."""

from pathlib import Path

import pytest

from mazu.core.engine import FlowExecutionError, run_flow
from mazu.core.flow import load_flow, parse_flow
from mazu.executor.mock.executor import MockExecutor

EXAMPLES = Path(__file__).parent.parent / "examples" / "flows"

NVME_TARGETS = [{"id": "ssd0", "protocol": "nvme", "executor": "mock",
                 "device": "mock://nvme/0"}]


def run_example(name):
    flow = load_flow(EXAMPLES / name)
    executors = {t.id: MockExecutor() for t in flow.targets}
    return run_flow(flow, executors)


def test_nvme_health_example_passes():
    result = run_example("nvme_health.yaml")
    assert result.passed, "\n".join(
        str(a) for s in result.step_results for a in s.assertion_results)
    ident = result.step_results[0].command_result.decoded["identify"]
    assert ident["model"] == "MAZU VIRTUAL NVME SSD"


def test_scsi_capacity_example_passes_with_cross_step_assertion():
    result = run_example("scsi_capacity_check.yaml")
    assert result.passed
    read_step = result.step_results[2]
    a = read_step.assertion_results[0]
    assert a.expected == 512          # value came from read_cap's decoded result
    assert a.expected_source == "read_cap.capacity.block_size"


def test_trace_records_every_issued_command():
    result = run_example("nvme_health.yaml")
    assert [t.step for t in result.trace] == ["id_ctrl", "id_ns1", "smart"]
    for t in result.trace:
        assert t.protocol == "nvme"
        assert t.effect == "read_only"
        assert t.status == "success"
        assert t.duration_us is not None


def test_dependency_failure_skips_dependents():
    flow = parse_flow({
        "version": 2, "name": "dep-skip", "targets": NVME_TARGETS,
        "steps": [
            {"name": "gate", "target": "ssd0", "command": "get_log_page",
             "params": {"lid": "smart"},
             "assert": [{"path": "smart.power_cycles", "op": "eq", "value": 0}]},
            {"name": "after", "target": "ssd0", "command": "identify_controller",
             "depends_on": ["gate"]},
        ],
    })
    result = run_flow(flow, {"ssd0": MockExecutor()})
    assert not result.passed
    skipped = result.step_results[1]
    assert skipped.command_result.status.value == "skipped"
    assert skipped.skipped_due_to == ["gate"]
    # Skipped commands are never issued: trace only contains the gate step.
    assert [t.step for t in result.trace] == ["gate"]


def test_destructive_flow_refused_before_touching_device():
    flow = parse_flow({
        "version": 2, "name": "bad", "targets": NVME_TARGETS,
        "steps": [{"name": "w", "target": "ssd0", "command": "write",
                   "params": {"nsid": 1, "slba": 0, "nlb": 1}}],
    })
    with pytest.raises(FlowExecutionError, match="validation"):
        run_flow(flow, {"ssd0": MockExecutor()})


def test_out_of_range_read_reports_error_status():
    flow = parse_flow({
        "version": 2, "name": "oob", "targets": NVME_TARGETS,
        "steps": [{"name": "r", "target": "ssd0", "command": "read",
                   "params": {"nsid": 1, "slba": 10**9, "nlb": 1}}],
    })
    result = run_flow(flow, {"ssd0": MockExecutor()})
    assert not result.passed
    step = result.step_results[0]
    assert step.command_result.status.value == "error"
    assert "out of bounds" in step.command_result.raw_status["reason"]


def test_missing_executor_for_target_raises():
    flow = parse_flow({
        "version": 2, "name": "noexec", "targets": NVME_TARGETS,
        "steps": [{"name": "id", "target": "ssd0",
                   "command": "identify_controller"}],
    })
    with pytest.raises(FlowExecutionError, match="no executor provided"):
        run_flow(flow, {})

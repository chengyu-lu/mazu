"""Dry-run: full validation + dependency resolution + command plan,
without touching any device."""

from pathlib import Path

import pytest

from mazu.core.engine import FlowExecutionError, run_flow
from mazu.core.flow import load_flow, parse_flow

EXAMPLES = Path(__file__).parent.parent / "examples" / "flows"


def test_dry_run_plans_all_commands_without_executors():
    flow = load_flow(EXAMPLES / "nvme_health.yaml")
    result = run_flow(flow, dry_run=True)   # note: no executors at all
    assert result.dry_run and result.passed
    assert [t.step for t in result.trace] == ["id_ctrl", "id_ns1", "smart"]
    for t in result.trace:
        assert t.status == "planned"
        assert t.duration_us is None
    # Typed defaults are resolved in the plan (explicit, reviewable).
    inq_flow = load_flow(EXAMPLES / "scsi_capacity_check.yaml")
    plan = run_flow(inq_flow, dry_run=True)
    inq = plan.trace[0]
    assert inq.command == "inquiry"
    assert inq.params == {"evpd": False, "page_code": 0}


def test_dry_run_still_validates():
    flow = parse_flow({
        "version": 2, "name": "bad",
        "targets": [{"id": "ssd0", "protocol": "nvme", "executor": "mock",
                     "device": "mock://nvme/0"}],
        "steps": [{"name": "w", "target": "ssd0", "command": "write",
                   "params": {"nsid": 1, "slba": 0, "nlb": 1}}],
    })
    with pytest.raises(FlowExecutionError, match="validation"):
        run_flow(flow, dry_run=True)

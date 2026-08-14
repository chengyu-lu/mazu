import pytest

from mazu.core.flow import FlowParseError, parse_flow
from mazu.core.validate import validate_flow


def make_flow(steps, **kw):
    return parse_flow({"version": 1, "name": "t", "steps": steps, **kw})


def test_parse_minimal_flow():
    flow = make_flow([{"op": "identify_controller"}])
    assert flow.name == "t"
    assert len(flow.steps) == 1


def test_unknown_op_rejected():
    with pytest.raises(FlowParseError, match="unknown op"):
        make_flow([{"op": "format_everything"}])


def test_empty_steps_rejected():
    with pytest.raises(FlowParseError, match="non-empty"):
        parse_flow({"version": 1, "name": "t", "steps": []})


def test_read_requires_lba_and_blocks():
    flow = make_flow([{"op": "read", "params": {"lba": 0}}])
    report = validate_flow(flow)
    assert not report.ok
    assert any("blocks" in str(i) for i in report.issues)


def test_write_rejected_in_v1():
    flow = make_flow([{"op": "write", "params": {"lba": 0, "blocks": 1}}])
    report = validate_flow(flow)
    assert not report.ok
    assert any("out of scope in v1" in i.message for i in report.issues)


def test_write_rejected_even_with_allow_destructive_flag():
    # Invariant I7: no flag re-enables destructive ops in v1.
    flow = make_flow(
        [{"op": "write", "params": {"lba": 0, "blocks": 1, "pattern": 0xFF}}],
        allow_destructive=True,
    )
    assert not validate_flow(flow).ok


def test_raw_commands_rejected_in_v1():
    for step in ({"op": "raw_nvme", "params": {"opcode": 6}},
                 {"op": "raw_scsi", "params": {"cdb": "12"}}):
        flow = make_flow([step], allow_destructive=True)
        assert not validate_flow(flow).ok


def test_unknown_log_page_rejected():
    flow = make_flow([{"op": "get_log", "params": {"log": "bogus"}}])
    assert not validate_flow(flow).ok


def test_bad_assertion_op_rejected():
    flow = make_flow(
        [{"op": "identify_controller",
          "assert": [{"path": "identify.model", "op": "matches", "value": "x"}]}]
    )
    assert not validate_flow(flow).ok


def test_excessive_transfer_rejected():
    flow = make_flow([{"op": "read", "params": {"lba": 0, "blocks": 10_000_000}}])
    assert not validate_flow(flow).ok

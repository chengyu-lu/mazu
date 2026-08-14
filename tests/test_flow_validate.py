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


def test_write_blocked_without_allow_destructive():
    flow = make_flow([{"op": "write", "params": {"lba": 0, "blocks": 1}}])
    report = validate_flow(flow)
    assert not report.ok
    assert any("allow_destructive" in i.message for i in report.issues)


def test_write_allowed_with_flag():
    flow = make_flow(
        [{"op": "write", "params": {"lba": 0, "blocks": 1, "pattern": 0xFF}}],
        allow_destructive=True,
    )
    assert validate_flow(flow).ok


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

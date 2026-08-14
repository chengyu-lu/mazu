import pytest

from mazu.core.flow import FlowParseError, parse_flow
from mazu.core.validate import validate_flow

TARGETS = [{"id": "ssd0", "protocol": "nvme", "executor": "mock",
            "device": "mock://nvme/0"}]
SCSI_TARGETS = [{"id": "disk0", "protocol": "scsi", "executor": "mock",
                 "device": "mock://scsi/0"}]


def make_flow(steps, targets=None, **kw):
    return parse_flow({"version": 2, "name": "t",
                       "targets": targets or TARGETS, "steps": steps, **kw})


def id_step(name="id", **kw):
    return {"name": name, "target": "ssd0", "command": "identify_controller", **kw}


# ---- structure ----------------------------------------------------------

def test_parse_minimal_flow():
    flow = make_flow([id_step()])
    assert flow.steps[0].command.qualified_name == "nvme.identify_controller"
    assert validate_flow(flow).ok


def test_wrong_dsl_version_rejected():
    with pytest.raises(FlowParseError, match="version"):
        parse_flow({"version": 1, "name": "t", "targets": TARGETS,
                    "steps": [id_step()]})


def test_targets_required():
    with pytest.raises(FlowParseError, match="targets"):
        parse_flow({"version": 2, "name": "t", "steps": [id_step()]})


def test_protocol_prefix_must_match_target():
    with pytest.raises(FlowParseError, match="contradicts"):
        make_flow([{"name": "s", "target": "ssd0",
                    "command": "scsi.inquiry"}])


def test_matching_protocol_prefix_accepted():
    flow = make_flow([{"name": "s", "target": "ssd0",
                       "command": "nvme.identify_controller"}])
    assert validate_flow(flow).ok


# ---- explicitness -------------------------------------------------------

def test_unknown_command_rejected():
    flow = make_flow([{"name": "s", "target": "ssd0", "command": "format_everything"}])
    report = validate_flow(flow)
    assert not report.ok
    assert any("unknown command" in i.message for i in report.issues)


def test_unknown_target_rejected():
    flow = make_flow([{"name": "s", "target": "nope",
                       "command": "identify_controller"}])
    assert not validate_flow(flow).ok


def test_unknown_protocol_rejected():
    flow = make_flow([id_step()],
                     targets=[{"id": "ssd0", "protocol": "ata",
                               "executor": "mock", "device": "x"}])
    assert not validate_flow(flow).ok


# ---- typed params -------------------------------------------------------

def test_missing_required_param_rejected():
    flow = make_flow([{"name": "s", "target": "ssd0",
                       "command": "identify_namespace"}])
    report = validate_flow(flow)
    assert any("missing required param 'nsid'" in i.message for i in report.issues)


def test_unknown_param_rejected():
    flow = make_flow([id_step(params={"bogus": 1})])
    report = validate_flow(flow)
    assert any("unknown param 'bogus'" in i.message for i in report.issues)


def test_param_range_checked():
    flow = make_flow([{"name": "s", "target": "ssd0", "command": "read",
                       "params": {"nsid": 1, "slba": 0, "nlb": 100_000}}])
    report = validate_flow(flow)
    assert any("out of range" in i.message for i in report.issues)


def test_param_type_checked():
    flow = make_flow([{"name": "s", "target": "ssd0", "command": "read",
                       "params": {"nsid": 1, "slba": "zero", "nlb": 1}}])
    report = validate_flow(flow)
    assert any("must be an integer" in i.message for i in report.issues)


def test_enum_param_by_name():
    ok = make_flow([{"name": "s", "target": "ssd0", "command": "get_log_page",
                     "params": {"lid": "smart"}}])
    assert validate_flow(ok).ok
    bad = make_flow([{"name": "s", "target": "ssd0", "command": "get_log_page",
                      "params": {"lid": 2}}])
    assert not validate_flow(bad).ok


# ---- unique names & dependencies ---------------------------------------

def test_duplicate_step_names_rejected():
    flow = make_flow([id_step("a"), id_step("a")])
    report = validate_flow(flow)
    assert any("duplicate step name" in i.message for i in report.issues)


def test_forward_dependency_rejected():
    flow = make_flow([id_step("a", depends_on=["b"]), id_step("b")])
    report = validate_flow(flow)
    assert any("forward references" in i.message for i in report.issues)


def test_self_dependency_rejected():
    flow = make_flow([id_step("a", depends_on=["a"])])
    assert not validate_flow(flow).ok


def test_backward_dependency_ok():
    flow = make_flow([id_step("a"), id_step("b", depends_on=["a"])])
    assert validate_flow(flow).ok


# ---- assertions ---------------------------------------------------------

def test_value_from_requires_declared_dependency():
    flow = make_flow([
        id_step("a"),
        id_step("b", **{"assert": [{"path": "identify.model", "op": "eq",
                                    "value_from": {"step": "a",
                                                   "path": "identify.model"}}]}),
    ])
    report = validate_flow(flow)
    assert any("not in this step's depends_on" in i.message for i in report.issues)

    flow_ok = make_flow([
        id_step("a"),
        id_step("b", depends_on=["a"],
                **{"assert": [{"path": "identify.model", "op": "eq",
                               "value_from": {"step": "a",
                                              "path": "identify.model"}}]}),
    ])
    assert validate_flow(flow_ok).ok


def test_bad_assertion_op_rejected():
    flow = make_flow([id_step(**{"assert": [{"path": "x", "op": "matches",
                                             "value": "y"}]})])
    assert not validate_flow(flow).ok


# ---- destructive classification (I7) -----------------------------------

def test_nvme_write_rejected_in_v1():
    flow = make_flow([{"name": "w", "target": "ssd0", "command": "write",
                       "params": {"nsid": 1, "slba": 0, "nlb": 1}}])
    report = validate_flow(flow)
    assert any("destructive" in i.message and "I7" in i.message
               for i in report.issues)


def test_scsi_write_rejected_in_v1():
    flow = make_flow([{"name": "w", "target": "disk0", "command": "write_16",
                       "params": {"lba": 0, "transfer_length": 1}}],
                     targets=SCSI_TARGETS)
    assert not validate_flow(flow).ok

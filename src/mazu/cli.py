"""mazu command-line interface.

    mazu validate <flow.yaml>          # parse + semantic validation only
    mazu run <flow.yaml> [--json]      # validate then execute (mock transport)
    mazu run <flow.yaml> -t mock       # transport selection (more in Phase 2)
"""

from __future__ import annotations

import argparse
import sys

from .analyze.report import json_report, text_report
from .core.executor import FlowExecutionError, run_flow
from .core.flow import FlowParseError, load_flow
from .core.validate import validate_flow
from .transport.mock.transport import MockTransport

TRANSPORTS = {
    "mock": lambda args: MockTransport(),
    # "nvme": Phase 2, "scsi": Phase 2, "usb4": Phase 3
}


def _load(path: str):
    try:
        return load_flow(path)
    except FileNotFoundError:
        print(f"error: no such file: {path}", file=sys.stderr)
        sys.exit(2)
    except FlowParseError as e:
        print(f"flow parse error: {e}", file=sys.stderr)
        sys.exit(2)


def cmd_validate(args) -> int:
    flow = _load(args.flow)
    report = validate_flow(flow)
    for issue in report.issues:
        print(issue)
    if report.ok:
        print(f"OK: '{flow.name}' is valid ({len(flow.steps)} steps)")
        return 0
    return 1


def cmd_run(args) -> int:
    flow = _load(args.flow)
    transport = TRANSPORTS[args.transport](args)
    try:
        result = run_flow(flow, transport)
    except FlowExecutionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json_report(result) if args.json else text_report(result))
    return 0 if result.passed else 1


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="mazu",
                                     description="AI-assisted storage validation framework")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="validate a flow file without executing")
    p_val.add_argument("flow")
    p_val.set_defaults(func=cmd_validate)

    p_run = sub.add_parser("run", help="validate and execute a flow file")
    p_run.add_argument("flow")
    p_run.add_argument("-t", "--transport", choices=sorted(TRANSPORTS), default="mock")
    p_run.add_argument("--json", action="store_true", help="emit JSON report")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

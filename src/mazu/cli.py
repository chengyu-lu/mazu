"""mazu command-line interface.

    mazu validate <flow.yaml>            # parse + semantic validation only
    mazu run <flow.yaml>                 # validate then execute
    mazu run <flow.yaml> --dry-run       # plan only: no device is touched
    mazu run <flow.yaml> --trace         # include command trace in output
    mazu run <flow.yaml> --json          # JSON report (always includes trace)
"""

from __future__ import annotations

import argparse
import sys

from .analyze.report import json_report, text_report
from .core.engine import FlowExecutionError, run_flow
from .core.flow import Flow, FlowParseError, load_flow
from .core.validate import validate_flow
from .executor.base import Executor
from .executor.mock.executor import MockExecutor


def _build_executors(flow: Flow) -> dict[str, Executor]:
    """Instantiate one executor per target, per its declared kind."""
    executors: dict[str, Executor] = {}
    for t in flow.targets:
        if t.executor == "mock":
            executors[t.id] = MockExecutor()
        else:
            # NvmeExecutor/ScsiExecutor/Usb4Executor land in Phase 2/3.
            raise FlowExecutionError(
                f"executor kind '{t.executor}' (target '{t.id}') is not "
                f"implemented yet; only 'mock' is available in Phase 1")
    return executors


def _load(path: str) -> Flow:
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
        print(f"OK: '{flow.name}' is valid "
              f"({len(flow.targets)} target(s), {len(flow.steps)} step(s))")
        return 0
    return 1


def cmd_run(args) -> int:
    flow = _load(args.flow)
    try:
        if args.dry_run:
            result = run_flow(flow, dry_run=True)
        else:
            result = run_flow(flow, _build_executors(flow))
    except FlowExecutionError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(json_report(result) if args.json
          else text_report(result, show_trace=args.trace))
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
    p_run.add_argument("--dry-run", action="store_true",
                       help="validate and print the command plan; touch no device")
    p_run.add_argument("--trace", action="store_true",
                       help="print the command trace in the text report")
    p_run.add_argument("--json", action="store_true", help="emit JSON report")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()

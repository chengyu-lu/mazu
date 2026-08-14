"""Logical command model — the transport-agnostic command abstraction.

A flow never talks about NVMe opcodes or SCSI CDBs directly. It talks about
*logical operations* (identify_controller, read, get_log, ...). Each transport
backend maps a LogicalCommand onto its own wire format. This is the layer that
makes NVMe/SCSI/USB/USB4 interchangeable for the same flow.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Op(str, Enum):
    """Logical operations understood by the abstraction layer."""

    IDENTIFY_CONTROLLER = "identify_controller"
    IDENTIFY_NAMESPACE = "identify_namespace"
    READ = "read"
    WRITE = "write"
    FLUSH = "flush"
    GET_LOG = "get_log"
    # Escape hatches for commands the abstraction does not (yet) cover.
    # These are transport-specific by definition and validated more strictly.
    RAW_NVME = "raw_nvme"
    RAW_SCSI = "raw_scsi"


#: Ops that can modify media or device state. The validator refuses these
#: unless the flow explicitly sets `allow_destructive: true`.
DESTRUCTIVE_OPS = {Op.WRITE, Op.RAW_NVME, Op.RAW_SCSI}

#: Logical log page names -> NVMe log page IDs (transport backends may
#: translate these differently, e.g. SCSI LOG SENSE pages).
LOG_PAGES = {
    "error": 0x01,
    "smart": 0x02,
    "firmware_slot": 0x03,
}


@dataclass
class LogicalCommand:
    """One transport-agnostic command."""

    op: Op
    params: dict[str, Any] = field(default_factory=dict)
    #: Optional label from the flow step, for reporting.
    label: str | None = None

    def __str__(self) -> str:
        p = f" {self.params}" if self.params else ""
        return f"<{self.op.value}{p}>"


class Status(str, Enum):
    """Transport-agnostic completion status."""

    SUCCESS = "success"
    ERROR = "error"           # device returned an error status
    UNSUPPORTED = "unsupported"  # transport cannot express this command
    TRANSPORT_ERROR = "transport_error"  # link/ioctl level failure


@dataclass
class CommandResult:
    """Result of executing one LogicalCommand on some transport."""

    command: LogicalCommand
    status: Status
    data: bytes = b""
    #: Raw transport-specific status for debugging (e.g. NVMe status code,
    #: SCSI sense bytes). Never interpreted by core.
    raw_status: dict[str, Any] = field(default_factory=dict)
    #: Structured view filled in by the decode layer (if a decoder exists).
    decoded: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.SUCCESS

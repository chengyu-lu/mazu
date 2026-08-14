"""Protocol command model (DSL v2).

A command is explicit about its protocol and its name in the command
registry (invariant I1: structured, typed — never free text). What travels
between layers is this dataclass, never a string to parse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

PROTOCOLS = ("nvme", "scsi")


@dataclass
class ProtocolCommand:
    """One explicit, protocol-qualified command with typed params."""

    protocol: str          # "nvme" | "scsi"
    name: str              # command name in the registry, e.g. "identify_controller"
    params: dict[str, Any] = field(default_factory=dict)
    #: Owning step name, for tracing/reporting.
    step: str | None = None

    @property
    def qualified_name(self) -> str:
        return f"{self.protocol}.{self.name}"

    def __str__(self) -> str:
        p = f" {self.params}" if self.params else ""
        return f"<{self.qualified_name}{p}>"


class Status(str, Enum):
    """Executor-agnostic completion status."""

    SUCCESS = "success"
    ERROR = "error"                      # device returned an error status
    UNSUPPORTED = "unsupported"          # executor cannot express this command
    TRANSPORT_ERROR = "transport_error"  # link/ioctl level failure
    SKIPPED = "skipped"                  # dependency failed; command never issued
    PLANNED = "planned"                  # dry-run: command validated, not issued


@dataclass
class CommandResult:
    """Result of executing one ProtocolCommand on some executor."""

    command: ProtocolCommand
    status: Status
    data: bytes = b""
    #: Raw executor-specific status for debugging (e.g. NVMe status code,
    #: SCSI sense bytes). Never interpreted by core.
    raw_status: dict[str, Any] = field(default_factory=dict)
    #: Structured view filled in by the decode layer (if a decoder exists).
    decoded: dict[str, Any] | None = None

    @property
    def ok(self) -> bool:
        return self.status is Status.SUCCESS

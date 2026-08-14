"""Transport abstraction — the seam that makes NVMe/SCSI/USB/USB4 uniform.

A Transport takes LogicalCommands and returns CommandResults. How a command
is expressed on the wire (NVMe SQE, SCSI CDB, tunneled through USB4) is
entirely the transport's business. If a transport cannot express a command,
it returns Status.UNSUPPORTED — it never guesses.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.command import CommandResult, LogicalCommand


class Transport(ABC):
    """Abstract transport. Use as a context manager."""

    #: Short identifier used in reports ("mock", "nvme", "scsi", "usb4").
    name: str = "abstract"

    @abstractmethod
    def open(self) -> None:
        """Acquire the device (open fd, claim interface...)."""

    @abstractmethod
    def close(self) -> None:
        """Release the device."""

    @abstractmethod
    def execute(self, command: LogicalCommand) -> CommandResult:
        """Execute one logical command synchronously."""

    def __enter__(self) -> "Transport":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class TransportError(Exception):
    """Link-level or OS-level transport failure."""

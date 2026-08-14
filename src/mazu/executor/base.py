"""Executor interface — the only gate to a device (invariant I4).

An Executor takes LogicalCommands and returns CommandResults. How a command
is expressed on the wire (NVMe SQE, SCSI CDB, tunneled through USB4) is
entirely the executor's business. If an executor cannot express a command,
it returns Status.UNSUPPORTED — it never guesses.

Hardware execution must be replaceable by MockExecutor (invariant I5):
core code only ever sees this interface and never imports a concrete
implementation. Non-serializable state (fds, sockets) lives below this
interface only (invariant I2).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.command import CommandResult, LogicalCommand


class Executor(ABC):
    """Abstract device executor. Use as a context manager."""

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

    def __enter__(self) -> "Executor":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()


class ExecutorError(Exception):
    """Link-level or OS-level execution failure."""

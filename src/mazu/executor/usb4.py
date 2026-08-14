"""USB4 executor (Phase 3 — not yet implemented).

A USB4-attached device may expose NVMe (tunneled PCIe) or SCSI (UAS/BOT)
depending on enclosure/bridge mode. This executor will:

1. detect which protocol the tunnel currently exposes,
2. route ProtocolCommands through the matching wire encoding,
3. use mazu.translate (SNTL subset) for raw commands issued in the
   *other* protocol, refusing loudly when no faithful translation exists.

Flows never change: protocol switching happens entirely below the
ProtocolCommand abstraction.
"""

from __future__ import annotations

from ..core.command import CommandResult, ProtocolCommand
from .base import Executor


class Usb4Executor(Executor):
    name = "usb4"

    def __init__(self, device_path: str):
        self.device_path = device_path
        raise NotImplementedError(
            "Usb4Executor is planned for Phase 3 (after real NVMe/SCSI "
            "executors exist). Use MockExecutor for now."
        )

    def open(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def execute(self, command: ProtocolCommand) -> CommandResult:  # pragma: no cover
        raise NotImplementedError

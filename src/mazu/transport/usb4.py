"""USB4 transport (Phase 3 — not yet implemented).

A USB4-attached device may expose NVMe (tunneled PCIe) or SCSI (UAS/BOT)
depending on enclosure/bridge mode. This transport will:

1. detect which protocol the tunnel currently exposes,
2. route LogicalCommands through the matching wire encoding,
3. use mazu.translate (SNTL subset) for raw commands issued in the
   *other* protocol, refusing loudly when no faithful translation exists.

Flows never change: protocol switching happens entirely below the
LogicalCommand abstraction.
"""

from __future__ import annotations

from ..core.command import CommandResult, LogicalCommand
from .base import Transport


class Usb4Transport(Transport):
    name = "usb4"

    def __init__(self, device_path: str):
        self.device_path = device_path
        raise NotImplementedError(
            "Usb4Transport is planned for Phase 3 (after real NVMe/SCSI "
            "transports exist). Use MockTransport for now."
        )

    def open(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def execute(self, command: LogicalCommand) -> CommandResult:  # pragma: no cover
        raise NotImplementedError

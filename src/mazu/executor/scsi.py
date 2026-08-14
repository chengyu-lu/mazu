"""Linux SCSI executor (Phase 2 — not yet implemented).

Will issue CDBs via SG_IO on /dev/sgX or /dev/sdX. Once this lands, USB
BOT/UAS devices are supported automatically — they are SCSI devices from
the host's point of view.
"""

from __future__ import annotations

from ..core.command import CommandResult, LogicalCommand
from .base import Executor


class ScsiExecutor(Executor):
    name = "scsi"

    def __init__(self, device_path: str):
        self.device_path = device_path
        raise NotImplementedError(
            "ScsiExecutor (SG_IO) is planned for Phase 2. Use MockExecutor for now."
        )

    def open(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def execute(self, command: LogicalCommand) -> CommandResult:  # pragma: no cover
        raise NotImplementedError

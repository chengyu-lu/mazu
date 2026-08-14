"""Linux NVMe executor (Phase 2 — not yet implemented).

Will issue commands via /dev/nvmeX ioctls (NVME_IOCTL_ADMIN_CMD /
NVME_IOCTL_IO_CMD). Kept as an explicit stub so the interface is visible
and flows written today run unchanged once this lands.
"""

from __future__ import annotations

from ..core.command import CommandResult, ProtocolCommand
from .base import Executor


class NvmeExecutor(Executor):
    name = "nvme"

    def __init__(self, device_path: str):
        self.device_path = device_path
        raise NotImplementedError(
            "NvmeExecutor (Linux ioctl passthru) is planned for Phase 2. "
            "Use MockExecutor for now."
        )

    def open(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def execute(self, command: ProtocolCommand) -> CommandResult:  # pragma: no cover
        raise NotImplementedError

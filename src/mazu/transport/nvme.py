"""Linux NVMe transport (Phase 2 — not yet implemented).

Will issue commands via /dev/nvmeX ioctls (NVME_IOCTL_ADMIN_CMD /
NVME_IOCTL_IO_CMD). Kept as an explicit stub so the interface is visible
and flows written today run unchanged once this lands.
"""

from __future__ import annotations

from ..core.command import CommandResult, LogicalCommand
from .base import Transport


class NvmeTransport(Transport):
    name = "nvme"

    def __init__(self, device_path: str):
        self.device_path = device_path
        raise NotImplementedError(
            "NvmeTransport (Linux ioctl passthru) is planned for Phase 2. "
            "Use MockTransport for now."
        )

    def open(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def execute(self, command: LogicalCommand) -> CommandResult:  # pragma: no cover
        raise NotImplementedError

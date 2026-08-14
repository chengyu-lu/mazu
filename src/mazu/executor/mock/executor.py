"""MockExecutor: maps ProtocolCommands onto simulated NVMe/SCSI devices.

Per invariant I5, this is a first-class Executor implementation, not a
testing stand-in: payloads are spec-shaped, so the decode layer treats
mock and real hardware identically. Commands arrive with resolved, typed
params (defaults applied by the engine after validation).
"""

from __future__ import annotations

from ...core.command import CommandResult, ProtocolCommand, Status
from ..base import Executor
from .device import MockNvmeDevice
from .scsi_device import MockScsiDevice


def _pattern(byte: int, length: int) -> bytes:
    return bytes([byte & 0xFF]) * length


class MockExecutor(Executor):
    name = "mock"

    def __init__(self, nvme: MockNvmeDevice | None = None,
                 scsi: MockScsiDevice | None = None):
        self.nvme = nvme or MockNvmeDevice()
        self.scsi = scsi or MockScsiDevice()
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def execute(self, command: ProtocolCommand) -> CommandResult:
        if not self._open:
            return CommandResult(command, Status.TRANSPORT_ERROR,
                                 raw_status={"reason": "executor not open"})
        try:
            if command.protocol == "nvme":
                return self._nvme(command)
            if command.protocol == "scsi":
                return self._scsi(command)
        except ValueError as e:
            # Device-level rejection (e.g. LBA out of range) — analogous to
            # NVMe status / SCSI CHECK CONDITION, so ERROR, not a crash.
            return CommandResult(command, Status.ERROR,
                                 raw_status={"reason": str(e)})
        return CommandResult(command, Status.UNSUPPORTED,
                             raw_status={"reason": f"protocol '{command.protocol}' "
                                                   f"not supported by mock"})

    # ---- NVMe ----------------------------------------------------------

    def _nvme(self, c: ProtocolCommand) -> CommandResult:
        dev, p = self.nvme, c.params
        if c.name == "identify_controller":
            return CommandResult(c, Status.SUCCESS, data=dev.identify_controller())
        if c.name == "identify_namespace":
            return CommandResult(c, Status.SUCCESS,
                                 data=dev.identify_namespace(p["nsid"]))
        if c.name == "get_log_page":
            pages = {"smart": dev.smart_log, "error": dev.error_log,
                     "firmware_slot": dev.firmware_slot_log}
            return CommandResult(c, Status.SUCCESS, data=pages[p["lid"]]())
        if c.name == "read":
            if p["nsid"] != 1:
                raise ValueError(f"invalid nsid {p['nsid']}")
            return CommandResult(c, Status.SUCCESS,
                                 data=dev.read(p["slba"], p["nlb"]))
        if c.name == "flush":
            dev.flush()
            return CommandResult(c, Status.SUCCESS)
        if c.name == "write":
            # Unreachable in v1 (invariant I7: the validator rejects
            # destructive commands). Kept for the v2 double-gate milestone.
            dev.write(p["slba"], p["nlb"],
                      _pattern(p["pattern"], p["nlb"] * dev.lba_size))
            return CommandResult(c, Status.SUCCESS)
        return self._unsupported(c)

    # ---- SCSI ----------------------------------------------------------

    def _scsi(self, c: ProtocolCommand) -> CommandResult:
        dev, p = self.scsi, c.params
        if c.name == "inquiry":
            return CommandResult(c, Status.SUCCESS,
                                 data=dev.inquiry(p["evpd"], p["page_code"]))
        if c.name == "read_capacity_16":
            return CommandResult(c, Status.SUCCESS, data=dev.read_capacity_16())
        if c.name == "read_16":
            return CommandResult(c, Status.SUCCESS,
                                 data=dev.read_16(p["lba"], p["transfer_length"]))
        if c.name == "write_16":
            # Unreachable in v1 (invariant I7); see nvme write above.
            dev.write_16(p["lba"], p["transfer_length"],
                         _pattern(p["pattern"],
                                  p["transfer_length"] * dev.block_size))
            return CommandResult(c, Status.SUCCESS)
        return self._unsupported(c)

    def _unsupported(self, c: ProtocolCommand) -> CommandResult:
        return CommandResult(c, Status.UNSUPPORTED,
                             raw_status={"reason": f"'{c.qualified_name}' "
                                                   f"not implemented by mock"})

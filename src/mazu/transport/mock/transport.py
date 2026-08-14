"""Mock transport: maps LogicalCommands onto the simulated NVMe device."""

from __future__ import annotations

from ...core.command import (
    LOG_PAGES,
    CommandResult,
    LogicalCommand,
    Op,
    Status,
)
from ..base import Transport
from .device import MockNvmeDevice


def _make_pattern(pattern: int, length: int) -> bytes:
    return bytes([pattern & 0xFF]) * length


class MockTransport(Transport):
    name = "mock"

    def __init__(self, device: MockNvmeDevice | None = None):
        self.device = device or MockNvmeDevice()
        self._open = False

    def open(self) -> None:
        self._open = True

    def close(self) -> None:
        self._open = False

    def execute(self, command: LogicalCommand) -> CommandResult:
        if not self._open:
            return CommandResult(command, Status.TRANSPORT_ERROR,
                                 raw_status={"reason": "transport not open"})
        try:
            return self._dispatch(command)
        except ValueError as e:
            # Device-level rejection (e.g. LBA out of range) — analogous to
            # an NVMe status code, so surfaced as ERROR, not a crash.
            return CommandResult(command, Status.ERROR, raw_status={"reason": str(e)})

    def _dispatch(self, command: LogicalCommand) -> CommandResult:
        op, p = command.op, command.params
        dev = self.device

        if op is Op.IDENTIFY_CONTROLLER:
            return CommandResult(command, Status.SUCCESS, data=dev.identify_controller())

        if op is Op.IDENTIFY_NAMESPACE:
            return CommandResult(command, Status.SUCCESS,
                                 data=dev.identify_namespace(p.get("nsid", 1)))

        if op is Op.READ:
            return CommandResult(command, Status.SUCCESS,
                                 data=dev.read(p["lba"], p["blocks"]))

        if op is Op.WRITE:
            length = p["blocks"] * dev.lba_size
            data = _make_pattern(p.get("pattern", 0), length)
            dev.write(p["lba"], p["blocks"], data)
            return CommandResult(command, Status.SUCCESS)

        if op is Op.FLUSH:
            dev.flush()
            return CommandResult(command, Status.SUCCESS)

        if op is Op.GET_LOG:
            log = p["log"]
            pages = {
                "smart": dev.smart_log,
                "error": dev.error_log,
                "firmware_slot": dev.firmware_slot_log,
            }
            if log not in pages:
                return CommandResult(command, Status.UNSUPPORTED,
                                     raw_status={"reason": f"log '{log}' not implemented",
                                                 "known": sorted(LOG_PAGES)})
            return CommandResult(command, Status.SUCCESS, data=pages[log]())

        # raw_nvme / raw_scsi are deliberately unsupported on mock for now.
        return CommandResult(command, Status.UNSUPPORTED,
                             raw_status={"reason": f"op '{op.value}' not supported by mock"})

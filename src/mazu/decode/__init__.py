"""Decode layer: raw response bytes → structured data.

Decoders are keyed by logical op (and params), not by transport, because
payload formats for the abstraction-layer ops are normalized to NVMe data
structures. Transport-specific payloads (raw_scsi) get their own decoders.
"""

from __future__ import annotations

from ..core.command import CommandResult, Op, Status
from .nvme_identify import decode_identify_controller, decode_identify_namespace
from .nvme_logpage import decode_firmware_slot_log, decode_smart_log

__all__ = [
    "decode_result",
    "decode_identify_controller",
    "decode_identify_namespace",
    "decode_smart_log",
    "decode_firmware_slot_log",
]


def decode_result(result: CommandResult) -> dict | None:
    """Best-effort decode of a command result. Returns None when no decoder
    applies; never raises on undecodable payloads (raw bytes stay available
    on the result for manual inspection)."""
    if result.status is not Status.SUCCESS or not result.data:
        return None
    op = result.command.op
    try:
        if op is Op.IDENTIFY_CONTROLLER:
            return decode_identify_controller(result.data)
        if op is Op.IDENTIFY_NAMESPACE:
            return decode_identify_namespace(result.data)
        if op is Op.GET_LOG:
            log = result.command.params.get("log")
            if log == "smart":
                return {"smart": decode_smart_log(result.data)}
            if log == "firmware_slot":
                return {"firmware_slot": decode_firmware_slot_log(result.data)}
        if op is Op.READ:
            data = result.data
            return {
                "length": len(data),
                "first_16_hex": data[:16].hex(),
                "all_zero": not any(data),
            }
    except Exception as e:  # pragma: no cover - defensive
        return {"decode_error": str(e)}
    return None

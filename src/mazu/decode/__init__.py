"""Decode layer: raw response bytes → structured data.

Decoders are pure functions keyed by (protocol, command name) — invariant
I6. They never touch devices or global state, and they make no distinction
between mock and real hardware payloads (invariant I5).
"""

from __future__ import annotations

from ..core.command import CommandResult, Status
from .nvme_identify import decode_identify_controller, decode_identify_namespace
from .nvme_logpage import decode_firmware_slot_log, decode_smart_log
from .scsi_data import decode_inquiry, decode_read_capacity_16

__all__ = [
    "decode_result",
    "decode_identify_controller",
    "decode_identify_namespace",
    "decode_smart_log",
    "decode_firmware_slot_log",
    "decode_inquiry",
    "decode_read_capacity_16",
]


def _decode_read_data(data: bytes) -> dict:
    return {
        "length": len(data),
        "first_16_hex": data[:16].hex(),
        "all_zero": not any(data),
    }


def decode_result(result: CommandResult) -> dict | None:
    """Best-effort decode of a command result. Returns None when no decoder
    applies; never raises on undecodable payloads (raw bytes stay available
    on the result for manual inspection)."""
    if result.status is not Status.SUCCESS or not result.data:
        return None
    proto, name = result.command.protocol, result.command.name
    params = result.command.params
    try:
        if proto == "nvme":
            if name == "identify_controller":
                return decode_identify_controller(result.data)
            if name == "identify_namespace":
                return decode_identify_namespace(result.data)
            if name == "get_log_page":
                lid = params.get("lid")
                if lid == "smart":
                    return {"smart": decode_smart_log(result.data)}
                if lid == "firmware_slot":
                    return {"firmware_slot": decode_firmware_slot_log(result.data)}
                return None
            if name == "read":
                return _decode_read_data(result.data)
        elif proto == "scsi":
            if name == "inquiry" and not params.get("evpd"):
                return decode_inquiry(result.data)
            if name == "read_capacity_16":
                return decode_read_capacity_16(result.data)
            if name == "read_16":
                return _decode_read_data(result.data)
    except Exception as e:  # pragma: no cover - defensive
        return {"decode_error": str(e)}
    return None

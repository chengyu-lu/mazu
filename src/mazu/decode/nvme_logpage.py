"""Decoders for NVMe log pages."""

from __future__ import annotations

import struct


def decode_smart_log(data: bytes) -> dict:
    """SMART / Health Information log page (02h), 512 bytes."""
    if len(data) < 512:
        raise ValueError(f"SMART log too short: {len(data)}")
    temp_k = struct.unpack_from("<H", data, 1)[0]
    return {
        "critical_warning": data[0],
        "temperature_kelvin": temp_k,
        "temperature_celsius": temp_k - 273,
        "available_spare": data[3],
        "available_spare_threshold": data[4],
        "percentage_used": data[5],
        "data_units_read": struct.unpack_from("<Q", data, 32)[0],
        "data_units_written": struct.unpack_from("<Q", data, 48)[0],
        "power_cycles": struct.unpack_from("<Q", data, 112)[0],
        "power_on_hours": struct.unpack_from("<Q", data, 128)[0],
        "unsafe_shutdowns": struct.unpack_from("<Q", data, 144)[0],
        "media_errors": struct.unpack_from("<Q", data, 160)[0],
    }


def decode_firmware_slot_log(data: bytes) -> dict:
    """Firmware Slot Information log page (03h), 512 bytes."""
    if len(data) < 512:
        raise ValueError(f"Firmware slot log too short: {len(data)}")
    slots = {}
    for i in range(7):
        rev = data[8 + i * 8 : 16 + i * 8].decode("ascii", errors="replace").strip()
        if rev:
            slots[f"slot{i + 1}"] = rev
    return {"active_slot": data[0] & 0x7, "slots": slots}

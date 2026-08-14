"""Decoders for SCSI response data (SPC-4 / SBC-3). Big-endian per SCSI."""

from __future__ import annotations

import struct


def _ascii(buf: bytes) -> str:
    return buf.decode("ascii", errors="replace").strip()


def decode_inquiry(data: bytes) -> dict:
    """SPC-4, standard INQUIRY data."""
    if len(data) < 36:
        raise ValueError(f"INQUIRY data too short: {len(data)}")
    return {
        "inquiry": {
            "peripheral_device_type": data[0] & 0x1F,
            "removable": bool(data[1] & 0x80),
            "version": data[2],
            "vendor": _ascii(data[8:16]),      # T10 vendor id, bytes 8-15
            "product": _ascii(data[16:32]),    # product id, bytes 16-31
            "revision": _ascii(data[32:36]),   # product revision, bytes 32-35
        }
    }


def decode_read_capacity_16(data: bytes) -> dict:
    """SBC-3, READ CAPACITY (16) parameter data."""
    if len(data) < 12:
        raise ValueError(f"READ CAPACITY(16) data too short: {len(data)}")
    max_lba = struct.unpack_from(">Q", data, 0)[0]
    block_size = struct.unpack_from(">I", data, 8)[0]
    return {
        "capacity": {
            "max_lba": max_lba,
            "block_size": block_size,
            "total_blocks": max_lba + 1,
        }
    }

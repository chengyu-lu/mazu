"""Decoders for NVMe Identify data structures."""

from __future__ import annotations

import struct


def _ascii(buf: bytes) -> str:
    return buf.decode("ascii", errors="replace").strip()


def decode_identify_controller(data: bytes) -> dict:
    if len(data) < 4096:
        raise ValueError(f"Identify Controller data too short: {len(data)}")
    return {
        "identify": {
            "vid": struct.unpack_from("<H", data, 0)[0],
            "ssvid": struct.unpack_from("<H", data, 2)[0],
            "serial": _ascii(data[4:24]),
            "model": _ascii(data[24:64]),
            "firmware_rev": _ascii(data[64:72]),
            "num_namespaces": struct.unpack_from("<I", data, 516)[0],
        }
    }


def decode_identify_namespace(data: bytes) -> dict:
    if len(data) < 4096:
        raise ValueError(f"Identify Namespace data too short: {len(data)}")
    lbads = data[130]
    return {
        "namespace": {
            "size_blocks": struct.unpack_from("<Q", data, 0)[0],
            "capacity_blocks": struct.unpack_from("<Q", data, 8)[0],
            "utilization_blocks": struct.unpack_from("<Q", data, 16)[0],
            "lba_size": 1 << lbads if lbads else 0,
        }
    }

"""A simulated NVMe device.

Produces spec-shaped byte payloads (Identify Controller, SMART log, ...) so
the decode layer works identically against mock and real devices. State
(namespace contents, counters) lives in memory, which makes flows fully
testable without hardware.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


def _ascii_field(value: str, length: int) -> bytes:
    """NVMe ASCII fields are space-padded, not NUL-padded."""
    return value.encode("ascii")[:length].ljust(length, b" ")


@dataclass
class MockNvmeDevice:
    model: str = "MAZU VIRTUAL NVME SSD"
    serial: str = "MZ0000000001"
    firmware_rev: str = "MZ1.0"
    vendor_id: int = 0x1B4B
    lba_size: int = 512
    namespace_blocks: int = 262144  # 128 MiB namespace

    # SMART state
    composite_temp_k: int = 310  # ~37°C, in Kelvin per spec
    available_spare: int = 100
    percentage_used: int = 3
    power_cycles: int = 42
    power_on_hours: int = 1234
    unsafe_shutdowns: int = 2
    media_errors: int = 0

    _namespace: dict[int, bytes] = field(default_factory=dict, repr=False)
    read_count: int = 0
    write_count: int = 0

    # ---- Admin ----------------------------------------------------------

    def identify_controller(self) -> bytes:
        """4096-byte Identify Controller data structure (CNS 01h), with the
        commonly-inspected fields at their spec offsets."""
        buf = bytearray(4096)
        struct.pack_into("<H", buf, 0, self.vendor_id)        # VID
        struct.pack_into("<H", buf, 2, self.vendor_id)        # SSVID
        buf[4:24] = _ascii_field(self.serial, 20)             # SN
        buf[24:64] = _ascii_field(self.model, 40)             # MN
        buf[64:72] = _ascii_field(self.firmware_rev, 8)       # FR
        struct.pack_into("<I", buf, 516, 1)                   # NN: 1 namespace
        return bytes(buf)

    def identify_namespace(self, nsid: int = 1) -> bytes:
        """4096-byte Identify Namespace data structure (CNS 00h)."""
        if nsid != 1:
            raise ValueError(f"invalid nsid {nsid}")
        buf = bytearray(4096)
        struct.pack_into("<Q", buf, 0, self.namespace_blocks)   # NSZE
        struct.pack_into("<Q", buf, 8, self.namespace_blocks)   # NCAP
        struct.pack_into("<Q", buf, 16, self.namespace_blocks)  # NUSE
        # LBA format 0: LBADS = log2(lba_size), at offset 128 (LBAF0), byte 2
        buf[130] = self.lba_size.bit_length() - 1
        return bytes(buf)

    def smart_log(self) -> bytes:
        """512-byte SMART / Health Information log page (02h)."""
        buf = bytearray(512)
        buf[0] = 0  # critical warning
        struct.pack_into("<H", buf, 1, self.composite_temp_k)
        buf[3] = self.available_spare
        buf[4] = 10  # available spare threshold
        buf[5] = self.percentage_used
        struct.pack_into("<Q", buf, 32, self.read_count)      # data units read (lo64)
        struct.pack_into("<Q", buf, 48, self.write_count)     # data units written (lo64)
        struct.pack_into("<Q", buf, 112, self.power_cycles)
        struct.pack_into("<Q", buf, 128, self.power_on_hours)
        struct.pack_into("<Q", buf, 144, self.unsafe_shutdowns)
        struct.pack_into("<Q", buf, 160, self.media_errors)
        return bytes(buf)

    def error_log(self) -> bytes:
        return bytes(4096)  # empty error log

    def firmware_slot_log(self) -> bytes:
        buf = bytearray(512)
        buf[0] = 0x01  # AFI: slot 1 active
        buf[8:16] = _ascii_field(self.firmware_rev, 8)  # FRS1
        return bytes(buf)

    # ---- IO -------------------------------------------------------------

    def _check_range(self, lba: int, blocks: int) -> None:
        if lba < 0 or blocks <= 0 or lba + blocks > self.namespace_blocks:
            raise ValueError(
                f"LBA range out of bounds: lba={lba} blocks={blocks} "
                f"nsze={self.namespace_blocks}"
            )

    def read(self, lba: int, blocks: int) -> bytes:
        self._check_range(lba, blocks)
        self.read_count += 1
        empty = bytes(self.lba_size)
        return b"".join(self._namespace.get(lba + i, empty) for i in range(blocks))

    def write(self, lba: int, blocks: int, data: bytes) -> None:
        self._check_range(lba, blocks)
        expected = blocks * self.lba_size
        if len(data) != expected:
            raise ValueError(f"data length {len(data)} != {expected}")
        self.write_count += 1
        for i in range(blocks):
            self._namespace[lba + i] = data[i * self.lba_size : (i + 1) * self.lba_size]

    def flush(self) -> None:
        pass  # everything is already "durable" in memory

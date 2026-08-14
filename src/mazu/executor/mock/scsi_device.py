"""A simulated SCSI direct-access block device.

Payloads follow SPC-4 / SBC-3 field offsets (byte order is big-endian per
SCSI convention), so the decode layer treats mock and real devices
identically (invariant I5).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field


def _ascii_field(value: str, length: int) -> bytes:
    """SCSI ASCII fields are space-padded (SPC-4)."""
    return value.encode("ascii")[:length].ljust(length, b" ")


@dataclass
class MockScsiDevice:
    vendor: str = "MAZU"          # T10 vendor identification, 8 bytes
    product: str = "VIRTUAL SCSI DISK"  # product identification, 16 bytes
    revision: str = "1.0"         # product revision level, 4 bytes
    serial: str = "MZSCSI0001"
    block_size: int = 512
    total_blocks: int = 262144    # 128 MiB

    _blocks: dict[int, bytes] = field(default_factory=dict, repr=False)

    def inquiry(self, evpd: bool = False, page_code: int = 0) -> bytes:
        if evpd:
            if page_code == 0x80:
                # SPC-4, Unit Serial Number VPD page (80h):
                # byte 0 peripheral, byte 1 page code, bytes 2-3 page length
                sn = self.serial.encode("ascii")
                return bytes([0x00, 0x80]) + struct.pack(">H", len(sn)) + sn
            raise ValueError(f"unsupported VPD page {page_code:#04x}")
        # SPC-4, standard INQUIRY data (96 bytes):
        buf = bytearray(96)
        buf[0] = 0x00                    # peripheral: direct access block device
        buf[1] = 0x00                    # RMB=0 (not removable)
        buf[2] = 0x06                    # version: SPC-4
        buf[3] = 0x02                    # response data format 2
        buf[4] = len(buf) - 5            # additional length (n-4)
        buf[8:16] = _ascii_field(self.vendor, 8)      # T10 vendor id, bytes 8-15
        buf[16:32] = _ascii_field(self.product, 16)   # product id, bytes 16-31
        buf[32:36] = _ascii_field(self.revision, 4)   # product revision, bytes 32-35
        return bytes(buf)

    def read_capacity_16(self) -> bytes:
        # SBC-3, READ CAPACITY (16) parameter data (32 bytes):
        # bytes 0-7: RETURNED LOGICAL BLOCK ADDRESS (= max LBA), big-endian
        # bytes 8-11: LOGICAL BLOCK LENGTH IN BYTES, big-endian
        buf = bytearray(32)
        struct.pack_into(">Q", buf, 0, self.total_blocks - 1)
        struct.pack_into(">I", buf, 8, self.block_size)
        return bytes(buf)

    def _check_range(self, lba: int, blocks: int) -> None:
        if lba < 0 or blocks <= 0 or lba + blocks > self.total_blocks:
            raise ValueError(
                f"LBA range out of bounds: lba={lba} blocks={blocks} "
                f"capacity={self.total_blocks}")

    def read_16(self, lba: int, transfer_length: int) -> bytes:
        self._check_range(lba, transfer_length)
        empty = bytes(self.block_size)
        return b"".join(self._blocks.get(lba + i, empty)
                        for i in range(transfer_length))

    def write_16(self, lba: int, transfer_length: int, data: bytes) -> None:
        self._check_range(lba, transfer_length)
        expected = transfer_length * self.block_size
        if len(data) != expected:
            raise ValueError(f"data length {len(data)} != {expected}")
        for i in range(transfer_length):
            self._blocks[lba + i] = data[i * self.block_size:(i + 1) * self.block_size]

"""SNTL-style NVMe ↔ SCSI translation (skeleton).

The mapping table below documents the semantic correspondence between
equivalent commands of the two protocols. Wire-level translation is filled
in per need during Phase 3. Reference: NVM Express: SCSI Translation
Reference; NVMe Base Spec 2.x; NVM Command Set Spec; SPC-4; SBC-3.
"""

from __future__ import annotations

from typing import Any

from .base import TranslationUnsupported, Translator

#: Semantic correspondence between registry commands across protocols.
#: This is the source of truth the wire-level implementations will follow.
#: (Opcodes cited: NVM Command Set Spec — Flush 00h, Write 01h, Read 02h;
#: SPC-4/SBC-3 CDB opcodes as noted.)
COMMAND_MAPPING = {
    "nvme.identify_controller": {"scsi": "inquiry",
                                 "note": "Identify CNS=01h <-> INQUIRY (12h) + VPD 80h/83h"},
    "nvme.identify_namespace": {"scsi": "read_capacity_16",
                                "note": "Identify CNS=00h <-> READ CAPACITY(16) (9Eh/10h)"},
    "nvme.read": {"scsi": "read_16",
                  "note": "Read (opcode 02h) <-> READ(16) (88h)"},
    "nvme.write": {"scsi": "write_16",
                   "note": "Write (opcode 01h) <-> WRITE(16) (8Ah); destructive, v2"},
    "nvme.get_log_page": {"scsi": None,
                          "note": "SMART <-> LOG SENSE (4Dh, Informational Exceptions); "
                                  "partial correspondence only"},
    "nvme.flush": {"scsi": None,
                   "note": "Flush (00h) <-> SYNCHRONIZE CACHE(10) (35h); not yet mapped"},
}


class SntlTranslator(Translator):
    """Placeholder implementation — every call is explicitly unsupported
    until Phase 3 fills in the wire-level encodings."""

    def nvme_to_scsi(self, opcode: int, params: dict[str, Any]) -> dict[str, Any]:
        raise TranslationUnsupported(
            f"NVMe opcode {opcode:#04x}: wire-level translation not yet implemented "
            "(Phase 3). See COMMAND_MAPPING for the semantic correspondence."
        )

    def scsi_to_nvme(self, cdb: bytes) -> dict[str, Any]:
        raise TranslationUnsupported(
            f"SCSI CDB {cdb[:1].hex()}...: wire-level translation not yet implemented "
            "(Phase 3). See COMMAND_MAPPING for the semantic correspondence."
        )

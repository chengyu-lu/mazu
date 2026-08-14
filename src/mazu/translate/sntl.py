"""SNTL-style NVMe ↔ SCSI translation (skeleton).

The mapping table below documents intent; entries are filled in per need
during Phase 3. Reference: NVM Express: SCSI Translation Reference.
"""

from __future__ import annotations

from typing import Any

from .base import TranslationUnsupported, Translator

#: Documented logical-level correspondence. This is the source of truth the
#: wire-level implementations will follow.
LOGICAL_MAPPING = {
    "identify_controller": {"nvme": "Identify CNS=01h", "scsi": "INQUIRY (+ VPD 80h/83h)"},
    "identify_namespace": {"nvme": "Identify CNS=00h", "scsi": "READ CAPACITY(16)"},
    "read": {"nvme": "Read (01h)", "scsi": "READ(10)/READ(16)"},
    "write": {"nvme": "Write (02h)", "scsi": "WRITE(10)/WRITE(16)"},
    "flush": {"nvme": "Flush (00h)", "scsi": "SYNCHRONIZE CACHE(10)"},
    "get_log:smart": {"nvme": "Get Log Page 02h", "scsi": "LOG SENSE (Informational Exceptions)"},
}


class SntlTranslator(Translator):
    """Placeholder implementation — every call is explicitly unsupported
    until Phase 3 fills in the wire-level encodings."""

    def nvme_to_scsi(self, opcode: int, params: dict[str, Any]) -> dict[str, Any]:
        raise TranslationUnsupported(
            f"NVMe opcode {opcode:#04x}: wire-level translation not yet implemented "
            "(Phase 3). See LOGICAL_MAPPING for the planned correspondence."
        )

    def scsi_to_nvme(self, cdb: bytes) -> dict[str, Any]:
        raise TranslationUnsupported(
            f"SCSI CDB {cdb[:1].hex()}...: wire-level translation not yet implemented "
            "(Phase 3). See LOGICAL_MAPPING for the planned correspondence."
        )

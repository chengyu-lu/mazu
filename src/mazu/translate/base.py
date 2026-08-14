"""Protocol translation interface (NVMe ↔ SCSI).

Used by transports (chiefly USB4) when a command expressed in one protocol
must run over a link that speaks the other. Only a well-defined subset is
translatable; anything else raises TranslationUnsupported — we never guess.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class TranslationUnsupported(Exception):
    """No faithful translation exists for this command."""


class Translator(ABC):
    @abstractmethod
    def nvme_to_scsi(self, opcode: int, params: dict[str, Any]) -> dict[str, Any]:
        """Translate an NVMe command into a SCSI CDB description."""

    @abstractmethod
    def scsi_to_nvme(self, cdb: bytes) -> dict[str, Any]:
        """Translate a SCSI CDB into an NVMe command description."""

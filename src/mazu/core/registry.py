"""Command registry — the single source of truth for the DSL v2 command set.

Every command declares: protocol, name, effect classification
(read_only | destructive), typed parameter specs, and its spec citation
(principle 10: no invented opcodes or fields — every entry cites the
governing specification).

Param types: u8/u16/u32/u64 (integers with range checks), bool, enum
(named values; flows write names, never magic numbers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

READ_ONLY = "read_only"
DESTRUCTIVE = "destructive"

_INT_RANGES = {
    "u8": (0, 0xFF),
    "u16": (0, 0xFFFF),
    "u32": (0, 0xFFFF_FFFF),
    "u64": (0, 0xFFFF_FFFF_FFFF_FFFF),
}


@dataclass(frozen=True)
class ParamSpec:
    name: str
    type: str                         # "u8" | "u16" | "u32" | "u64" | "bool" | "enum"
    required: bool = True
    default: Any = None               # only meaningful when required=False
    min: int | None = None            # narrows the type range
    max: int | None = None
    choices: dict[str, int] | None = None  # enum: name -> spec value
    doc: str = ""

    def check(self, value: Any) -> str | None:
        """Return an error message, or None if the value is valid."""
        if self.type == "bool":
            if not isinstance(value, bool):
                return f"'{self.name}' must be a bool, got {type(value).__name__}"
            return None
        if self.type == "enum":
            assert self.choices is not None
            if not isinstance(value, str) or value not in self.choices:
                return (f"'{self.name}' must be one of: "
                        f"{', '.join(sorted(self.choices))} (got {value!r})")
            return None
        if self.type in _INT_RANGES:
            if isinstance(value, bool) or not isinstance(value, int):
                return f"'{self.name}' must be an integer ({self.type}), got {type(value).__name__}"
            lo, hi = _INT_RANGES[self.type]
            lo = self.min if self.min is not None else lo
            hi = self.max if self.max is not None else hi
            if not (lo <= value <= hi):
                return f"'{self.name}'={value} out of range [{lo}, {hi}] ({self.type})"
            return None
        return f"'{self.name}': unknown param type '{self.type}' (registry bug)"


@dataclass(frozen=True)
class CommandSpec:
    protocol: str                     # "nvme" | "scsi"
    name: str
    effect: str                       # READ_ONLY | DESTRUCTIVE
    params: tuple[ParamSpec, ...] = ()
    spec: str = ""                    # citation: document + section/opcode

    @property
    def qualified_name(self) -> str:
        return f"{self.protocol}.{self.name}"

    def validate_params(self, given: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
        """Type-check params. Returns (errors, resolved_params).

        resolved_params has defaults applied; on any error it is empty.
        Unknown params are errors (commands must be explicit)."""
        errors: list[str] = []
        known = {p.name: p for p in self.params}
        for k in given:
            if k not in known:
                errors.append(f"unknown param '{k}' (known: {', '.join(known) or 'none'})")
        resolved: dict[str, Any] = {}
        for p in self.params:
            if p.name in given:
                err = p.check(given[p.name])
                if err:
                    errors.append(err)
                else:
                    resolved[p.name] = given[p.name]
            elif p.required:
                errors.append(f"missing required param '{p.name}' ({p.type})")
            else:
                resolved[p.name] = p.default
        return (errors, {} if errors else resolved)


def _u(name: str, type_: str, **kw: Any) -> ParamSpec:
    return ParamSpec(name=name, type=type_, **kw)


#: NVMe log page names -> Log Page Identifier.
#: NVMe Base Spec 2.x, "Log Page Identifiers" figure.
NVME_LOG_PAGES = {"error": 0x01, "smart": 0x02, "firmware_slot": 0x03}

_COMMANDS: tuple[CommandSpec, ...] = (
    # ---- NVMe (NVMe Base Specification 2.x; NVM Command Set Specification) ----
    CommandSpec(
        "nvme", "identify_controller", READ_ONLY,
        spec="NVMe Base Spec 2.x, Identify command (admin opcode 06h), CNS 01h",
    ),
    CommandSpec(
        "nvme", "identify_namespace", READ_ONLY,
        params=(_u("nsid", "u32", min=1, doc="namespace identifier"),),
        spec="NVMe Base Spec 2.x, Identify command (admin opcode 06h), CNS 00h",
    ),
    CommandSpec(
        "nvme", "get_log_page", READ_ONLY,
        params=(ParamSpec("lid", "enum", choices=NVME_LOG_PAGES,
                          doc="log page identifier (by name)"),),
        spec="NVMe Base Spec 2.x, Get Log Page command (admin opcode 02h)",
    ),
    CommandSpec(
        "nvme", "read", READ_ONLY,
        params=(_u("nsid", "u32", min=1),
                _u("slba", "u64", doc="starting LBA"),
                _u("nlb", "u16", min=1, max=65536,
                   doc="number of logical blocks (count; wire NLB is 0-based)")),
        spec="NVM Command Set Spec, Read command (opcode 02h)",
    ),
    CommandSpec(
        "nvme", "flush", READ_ONLY,
        params=(_u("nsid", "u32", min=1),),
        spec="NVM Command Set Spec, Flush command (opcode 00h)",
    ),
    CommandSpec(
        "nvme", "write", DESTRUCTIVE,
        params=(_u("nsid", "u32", min=1),
                _u("slba", "u64"),
                _u("nlb", "u16", min=1, max=65536),
                _u("pattern", "u8", required=False, default=0,
                   doc="fill byte for the data buffer")),
        spec="NVM Command Set Spec, Write command (opcode 01h)",
    ),
    # ---- SCSI (SPC-4 / SBC-3) ----
    CommandSpec(
        "scsi", "inquiry", READ_ONLY,
        params=(_u("evpd", "bool", required=False, default=False,
                   doc="request vital product data page"),
                _u("page_code", "u8", required=False, default=0)),
        spec="SPC-4, INQUIRY command (CDB opcode 12h)",
    ),
    CommandSpec(
        "scsi", "read_capacity_16", READ_ONLY,
        spec="SBC-3, READ CAPACITY (16) (opcode 9Eh, service action 10h)",
    ),
    CommandSpec(
        "scsi", "read_16", READ_ONLY,
        params=(_u("lba", "u64", doc="logical block address"),
                _u("transfer_length", "u32", min=1, max=65536,
                   doc="number of logical blocks")),
        spec="SBC-3, READ (16) command (CDB opcode 88h)",
    ),
    CommandSpec(
        "scsi", "write_16", DESTRUCTIVE,
        params=(_u("lba", "u64"),
                _u("transfer_length", "u32", min=1, max=65536),
                _u("pattern", "u8", required=False, default=0)),
        spec="SBC-3, WRITE (16) command (CDB opcode 8Ah)",
    ),
)

REGISTRY: dict[tuple[str, str], CommandSpec] = {
    (c.protocol, c.name): c for c in _COMMANDS
}


def lookup(protocol: str, name: str) -> CommandSpec | None:
    return REGISTRY.get((protocol, name))


def commands_for(protocol: str) -> list[str]:
    return sorted(n for (p, n) in REGISTRY if p == protocol)

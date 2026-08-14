---
name: usb
description: >
  USB 2.0/3.x protocol reasoning for storage firmware engineering in the
  Mazu project: enumeration, descriptors, transfer types, endpoint
  behavior, suspend/resume and link states, USB Mass Storage (BOT and
  UASP), the SCSI-over-USB boundary, USB error recovery, and USB trace
  analysis. Trigger on tasks involving USB devices, enumeration or
  descriptor problems, BOT/UAS flows, SCSI-over-USB, or USB traces.
---

# USB domain skill (foundation)

Status: foundation version — scope, boundaries, and methodology bindings.
Deep domain content arrives with the reference files in a later phase.

## Triggers

Enumeration failures; descriptor problems; endpoint/transfer problems
(STALL/halt, babble, toggles/streams); BOT flow analysis (CBW/CSW, the 13
cases); UASP flow analysis (IUs, streams, TMF); SCSI-over-USB command
flows; suspend/resume and link-state issues; USB trace analysis; USB test
generation.

## Owns / does not own

Owns (manifest): `usb.link`, `usb.enum`, `usb.descriptor`, `usb.transfer`,
`usb.power`, `msc.bot`, `msc.uas`, `scsi.cdb` (embedded SCSI boundary).
Does not own: USB4 fabric (→ usb4 skill; **USB 3.x ≠ USB4**); Type-C/PD
(boundary only); host-controller driver internals beyond trace context;
NVMe. **USB ≠ SCSI**: transport semantics (CBW/CSW, IUs, endpoints) and
SCSI command semantics (CDB, sense) are kept distinct in every analysis.
SCSI stays embedded here until the manifest's extraction criterion is met.

## Shared methodology

Follow `../_shared/methodology.md` (first observable deviation),
`../_shared/evidence.md`, `../_shared/safety.md` (three output types
only), `../_shared/testing.md`, `../_shared/spec-pins.md` (all pins TBD —
when a precise descriptor field, request code, or timing value matters and
no authoritative document is provided: "Authoritative specification
reference required", plus what is missing).

## Working rules (foundation)

Command-level work on USB storage devices is expressed as `protocol: scsi`
Flow DSL (BOT/UAS ride below the Executor interface). Enumeration- or
descriptor-level diagnostics that the registry cannot express become
registry/capability proposals (e.g. a future `usb.get_descriptor`) —
never shell commands. Disruptive actions (port reset, re-enumeration,
clearing halts on active endpoints) are labeled disruptive and need
explicit confirmation; SCSI writes over BOT/UAS are destructive (v1:
rejected). Trace correlation keys: BOT dCBWTag / UAS tag, then ordering,
then timestamps. Handoff: if the USB link rides a USB4 USB3-tunnel and
fabric fault is suspected → usb4 skill, and wait for its verdict.

## Future reference files (not yet created)

```
references/
  architecture.md  enumeration.md  descriptors.md  transfers.md
  link-power.md    msc-bot.md      uasp.md         scsi-over-usb.md
  errors-recovery.md               trace-analysis.md
```

# Specification pins (single source of truth for citations)

Every authoritative citation in any Mazu skill has the form:
**spec name + pinned revision + section + figure/table where applicable**,
e.g. `[nvme_base <rev TBD>, §x.y, Fig. z]`.

Rules:

- Revisions are chosen by the project and recorded here. They are never
  invented. Until chosen, the pin is `TBD`.
- **TBD is never authoritative.** A citation against a TBD pin means the
  claim is unverified: when a precise field/opcode/status meaning matters
  and the project has not provided the authoritative document, the correct
  output is "Authoritative specification reference required" plus a
  statement of exactly what is missing — not a from-memory value.
- `source` records where the project's copy of the document lives (path or
  location). Specification documents may be license-restricted: keep them
  out of version control unless licensing permits.
- The project-provided specification document remains the final authority
  over any curated table in skill references.

```yaml
specs:
  nvme_base:
    revision: TBD
    source: TBD
  nvme_nvm_command_set:
    revision: TBD
    source: TBD
  pcie_base:
    revision: TBD
    source: TBD
  usb_2:
    revision: TBD
    source: TBD
  usb_3_2:
    revision: TBD
    source: TBD
  usb_msc_bot:
    revision: TBD
    source: TBD
  usb_uas:
    revision: TBD
    source: TBD
  usb4:
    revision: TBD
    source: TBD
  scsi_spc:
    revision: TBD
    source: TBD
  scsi_sbc:
    revision: TBD
    source: TBD
```

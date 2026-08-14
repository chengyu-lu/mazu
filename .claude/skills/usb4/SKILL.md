---
name: usb4
description: >
  USB4 fabric reasoning for storage firmware engineering in the Mazu
  project: domains, host/device routers, adapters, paths, tunnels (USB3,
  PCIe, DisplayPort), Connection Manager behavior, topology discovery,
  bandwidth, link diagnostics, and USB4 trace/topology analysis. Trigger
  on tasks involving USB4 topology, routers, tunnels, tunnel-establishment
  failures, or devices behind USB4 (before in-tunnel protocol analysis).
---

# USB4 domain skill (foundation)

Status: foundation version — scope, boundaries, and methodology bindings.
Deep domain content arrives with the reference files in a later phase.

## Triggers

Topology analysis (expected vs discovered routers/adapters/paths);
router/adapter/path problems; tunnel-establishment failures (USB3 / PCIe /
DP); bandwidth/resource questions; fabric-level symptoms behind which a
storage device (NVMe or USB) sits; USB4 trace/CM-log analysis; USB4
validation test generation.

## Owns / does not own

Owns (manifest): `usb4.link`, `usb4.router`, `usb4.path`, `usb4.tunnel`,
`usb4.cm`. Does not own in-tunnel protocol semantics: tunneled USB stays
USB (→ usb skill), tunneled PCIe/NVMe stays NVMe (→ nvme skill).

**Strict non-equivalences — never conflate:** USB4 ≠ USB 3.x (USB3 is a
tunneled protocol inside USB4); USB4 ≠ Type-C (connector/cable layer);
USB4 ≠ USB PD (PD negotiates mode entry, then is out of scope); USB4 ≠
Thunderbolt 3 (TBT3 compatibility is a distinct configuration).

## Shared methodology

Follow `../_shared/methodology.md` (first observable deviation over the
bring-up sequence: link → router enumeration → path setup → tunnel
active), `../_shared/evidence.md`, `../_shared/safety.md`,
`../_shared/testing.md`, `../_shared/spec-pins.md` (usb4 pin TBD — router
config-space details not provided by the project are unknown, not
improvised: "Authoritative specification reference required").

## Working rules (foundation)

This skill's core deliverable in cross-protocol debugging is the **handoff
verdict**: "fabric healthy — escalate into the tunneled protocol (usb /
nvme skill)", "fabric fault — in-tunnel symptoms are consequences", or
"undetermined + discriminating test". It never re-interprets in-tunnel
semantics. Fabric diagnostics the registry cannot express become
capability proposals (e.g. future read-only `usb4.read_router_config`,
`usb4.path_status`) — never shell commands; today's evidence sources are
OS artifacts (sysfs topology, boltctl, CM logs) ingested as read-only
evidence. Path teardown / router reset / re-discovery are disruptive
(sever active tunnels — storage I/O, displays) and require explicit
confirmation; router config-space writes are potentially destructive.
Correlation keys: route string + adapter number, then ordering, then
timestamps.

## Future reference files (not yet created)

```
references/
  architecture.md  topology.md  tunneling.md  connection-manager.md
  link-diagnostics.md  boundaries.md  trace-analysis.md
```

# Mazu Domain Skills — Architecture & Scope Proposal (rev 2, for review)

Status: **REVISED PROPOSAL — no SKILL.md, no manifest, no code changes yet.**
Awaiting approval before any files are created.

Changes vs rev 1, per review decisions: shared methodology extracted to
`_shared/` (no duplication); skill responsibility vs runtime made explicit;
three output types defined; claim-level (not statement-level) evidence
classification; transport/path context requirement for Flow DSL; NVMe reset
terminology separated; queue-state reconstruction added to NVMe scope; SCSI
stays embedded with an extraction criterion; specification pinning; skill
manifest added; over-design explicitly constrained.

---

## 1. Skill responsibility and runtime position (decision 2)

**Skills = domain reasoning and artifact-generation guidance.**
They are prompt-time knowledge, not runtime services. Nothing in a skill
executes, schedules, or touches a device. The runtime architecture is:

```
Claude / Local Model
        ↓
Domain Skills            (reasoning + generation guidance — this proposal)
        ↓
Analysis / Flow DSL / Registry Proposal      (the only three outputs)
        ↓
Validator                (core/validate.py — mandatory, no bypass)
        ↓
Engine                   (core/engine.py — deterministic)
        ↓
Executor / MCP           (executor/* — the only gate to hardware)
        ↓
Device
```

A skill influences the device only by producing artifacts that enter this
pipeline at the top. This is the skill-layer restatement of invariants
I3/I4 and CLAUDE.md principles 4/5/10.

## 2. Skill output types (decision 3)

Every skill task ends in exactly one of three artifact types:

**A. Analysis Report** — protocol/debug reasoning: layered findings,
claims with evidence classes, first-deviation identification, ranked
hypotheses, recommended next diagnostics. Format defined in
`_shared/evidence.md`.

**B. Flow DSL** — a deterministic, machine-readable v2 flow (YAML) for
command/diagnostic execution, restricted to registry-supported commands.
Always suitable for `--dry-run` review before execution.

**C. Capability / Registry Proposal** — when the needed operation is not
in the registry: a proposed `CommandSpec` (protocol, typed params, effect
classification, spec citation) plus decoder/test requirements, following
CLAUDE.md's new-command procedure.

Hard rule: a missing capability yields output C — never shell commands,
never a validator bypass, never pseudo-flows with unregistered commands
presented as executable.

## 3. Directory structure (decisions 1, 10, 11 — proposed, not created)

```
.claude/skills/
├── manifest.yaml               # layer ownership, boundaries, handoffs (§5)
├── _shared/                    # referenced by all skills; never duplicated
│   ├── methodology.md          # debugging loop, first-deviation method
│   ├── evidence.md             # claim classes, hypothesis format, report format
│   ├── safety.md               # execution safety, destructive classification
│   ├── testing.md              # required test set for protocol artifacts
│   └── spec-pins.md            # pinned spec revisions (TBD until chosen) (§7)
├── usb/
│   ├── SKILL.md                # trigger + scope + pointers; references _shared/
│   └── references/
│       ├── architecture.md         # 2.0 vs 3.x, roles, topology
│       ├── enumeration.md          # device states, reset, address, config
│       ├── descriptors.md          # device/config/interface/endpoint/BOS
│       ├── transfers.md            # control/bulk/interrupt/isochronous
│       ├── link-power.md           # suspend/resume, U-states, LTSSM (3.x)
│       ├── msc-bot.md              # CBW/CSW, 13 cases, recovery
│       ├── uasp.md                 # IUs, streams, TMF, BOT vs UAS
│       ├── scsi-over-usb.md        # SCSI layer boundary (embedded; §6.4)
│       ├── errors-recovery.md      # STALL/halt, babble, escalation ladder
│       └── trace-analysis.md       # usbmon/analyzer formats, event schema
├── usb4/
│   ├── SKILL.md
│   └── references/
│       ├── architecture.md         # domains, host/device routers, adapters
│       ├── topology.md             # discovery, route strings, config space
│       ├── tunneling.md            # USB3/PCIe/DP tunnels, protocol adapters
│       ├── connection-manager.md   # CM roles, path setup/teardown, bandwidth
│       ├── link-diagnostics.md     # lanes, bonding, generations
│       ├── boundaries.md           # USB4 ≠ USB3.x ≠ Type-C ≠ PD ≠ TBT3
│       └── trace-analysis.md       # CM logs, router dumps, OS artifacts
└── nvme/
    ├── SKILL.md
    └── references/
        ├── architecture.md         # subsystem/controller/namespace/state
        ├── queues.md               # SQ/CQ, doorbells, phase bit, MSI-X,
        │                           #   queue-state reconstruction model (§6.3)
        ├── command-model.md        # SQE/CQE layout, PRP/SGL, CDWs
        ├── admin-commands.md       # per-command; destructive flagged
        ├── nvm-commands.md         # per-command; destructive flagged
        ├── logs.md                 # SMART/Error/FW Slot/Effects/Self-test/telemetry
        ├── features.md             # Get/Set Features, side effects, dependencies
        ├── errors-status.md        # SCT/SC, aborts, timeouts, AEN
        ├── resets.md               # CC.EN vs NSSR vs FLR (§6.2) — scopes & sequences
        ├── pcie-transport.md       # enumeration, BAR/MMIO, link, init sequence
        └── trace-correlation.md    # trace ↔ flow ↔ fw-log ↔ error-log method
```

Constraints honored (decision 11): no new agents, skills beyond the three,
MCP servers, execution frameworks, or DSL redesigns. Everything above is
implementable in the current repository.

## 4. Shared methodology structure (decision 1, 4)

Kept concise; four files, each a page or two, no abstraction layers:

**`_shared/methodology.md`** — the debugging loop:
`Observation → Evidence → Protocol layer → Expected behavior (cited) →
First observable deviation → Hypotheses (ranked, confidence) → Next
diagnostic test (output type B or C)`. Defines "first deviation": align
observed trace against the spec-defined expected sequence; everything
after the first divergence is presumed consequence until shown independent.

**`_shared/evidence.md`** — claim classification (decision 4, revised):
the classes apply to **important claims**, not to every sentence.
A claim is important when a conclusion, hypothesis ranking, or recommended
action depends on it. Each important claim is labeled one of:
`observed` (with pointer to trace/log/result), `spec-defined` (with pinned
citation, §7), `implementation-defined`, `vendor-specific`, `hypothesis`.
Hypotheses carry `evidence:` and `confidence: high|medium|low`.
Reports keep a **Claims** section distinct from the reasoning narrative,
so the narrative stays readable and the load-bearing claims stay auditable.

**`_shared/safety.md`** — skills never instruct direct device access;
device interaction is Flow DSL through validator/engine/executor/MCP only;
destructive and disruptive classifications (inherited from registry
`effect`, restated per domain); v1 read-only policy; the v2 double gate;
no workarounds of the validator, ever.

**`_shared/testing.md`** — the required test set: schema tests, encoding
tests, decoding tests, positive, negative, mock-device, integration, and
opt-in hardware tests (`tests/hw/`, `-m hw`).

Each domain SKILL.md begins by referencing these four files, then contains
only domain-specific content.

## 5. Skill manifest (decision 10 — proposed structure)

`.claude/skills/manifest.yaml` — machine-readable ownership map, used by
humans and by Claude to route questions and tag claim layers:

```yaml
version: 1

skills:
  usb:
    owns:
      - usb.link          # 2.0 signaling states, 3.x LTSSM as trace context
      - usb.enum          # device states, reset, address, configuration
      - usb.descriptor
      - usb.transfer      # control/bulk/interrupt/isochronous, endpoints
      - usb.power         # suspend/resume, U-states
      - msc.bot
      - msc.uas
      - scsi.cdb          # embedded SCSI boundary (extraction criterion §6.4)
    responsibilities: >
      USB 2.0/3.x device framework, MSC transports, SCSI-over-USB boundary,
      enumeration/descriptor/transfer/error analysis, USB trace analysis.
    boundaries:
      - usb != scsi              # transport vs command semantics
      - usb3.x != usb4           # SuperSpeed is not USB4
    handoffs:
      - to: usb4
        when: "USB link rides a USB4 USB3-tunnel and fabric fault is suspected"
      - to: nvme
        when: "never (no shared layer); storage semantics stay in scsi.cdb"

  usb4:
    owns:
      - usb4.link         # lanes, bonding, generations
      - usb4.router       # host/device routers, adapters, config space
      - usb4.path
      - usb4.tunnel       # usb3 / pcie / dp tunnel state & bandwidth
      - usb4.cm           # connection manager behavior
    responsibilities: >
      Fabric health: topology, routers/adapters/paths, tunnel establishment,
      bandwidth, CM flows, fabric-level trace analysis, handoff verdicts.
    boundaries:
      - usb4 != usb       # tunneled USB keeps USB semantics (usb skill)
      - usb4 != usb-pd    # PD negotiates mode entry, then out of scope
      - usb4 != tbt3      # compatibility mode is a distinct configuration
      - usb4 != type-c    # connector/cable layer
    handoffs:
      - to: usb
        when: "fabric healthy; symptoms inside USB3 tunnel"
      - to: nvme
        when: "fabric healthy; symptoms inside PCIe tunnel (NVMe device)"

  nvme:
    owns:
      - nvme.init         # controller init sequence, CC/CSTS
      - nvme.queue        # SQ/CQ, doorbells, phase, reconstruction (§6.3)
      - nvme.command      # SQE/CQE, admin + NVM command semantics
      - nvme.log
      - nvme.feature
      - nvme.status       # SCT/SC, aborts, timeouts, AEN
      - nvme.reset        # cc-en-reset / nssr / flr — distinct (§6.2)
      - pcie.transport    # NVMe-relevant PCIe surface only (boundary layer)
    responsibilities: >
      NVMe semantics end-to-end; registry-facing expertise; queue-state
      reconstruction; log/health analysis; reset-type analysis; PCIe
      boundary kept semantically separate.
    boundaries:
      - nvme != pcie      # command semantics vs transport semantics
    handoffs:
      - to: usb4
        when: "PCIe link is USB4-tunneled and fabric fault is suspected"

layer_rules:
  - every important claim is tagged with exactly one owned layer
  - a deviation is attributed to one layer, or marked ambiguous with a
    discriminating test
  - forbidden equivalences: [usb4/usb, usb4/usb-pd, usb4/tbt3, usb4/type-c,
                             usb/scsi, nvme/pcie]
```

(Exact field names open to adjustment when the file is created.)

## 6. Revised domain boundaries and scope deltas

Skill scopes remain as in rev 1 (§§1–3 of that document) except:

### 6.1 Shared material removed from each skill

Methodology/evidence/safety/testing sections move to `_shared/`;
each SKILL.md keeps only domain scope, terminology, tasks, references,
trace interface, and cross-protocol handoffs.

### 6.2 NVMe reset terminology (decision 6)

New reference file `nvme/references/resets.md`. The skill must always name
which reset it means and analyze them as distinct mechanisms:

| Reset | Mechanism | Scope | Expected observable sequence |
|---|---|---|---|
| Controller reset | CC.EN 1→0→1 | one controller; queues/state torn down, namespaces persist | CSTS.RDY 1→0 on disable, re-init sequence, admin queue re-created |
| NVM Subsystem Reset | NSSR write (when CAP.NSSRS=1) | entire subsystem — all controllers | subsystem-wide re-init; link may retrain |
| PCIe Function Level Reset | PCIe FLR via config space | the PCIe function, transport-level | config state reset; controller comes back per PCIe rules, then NVMe init |

"NVMe reset" without qualification is treated as an underspecified claim
and the skill asks which one (or infers it from evidence and says so).
Shutdown (CC.SHN) is documented as a fourth, distinct mechanism — not a
reset — to prevent conflation.

### 6.3 NVMe queue-state reconstruction (decision 7 — architecture only)

`nvme/references/queues.md` gains a command-lifecycle model the skill uses
for timeout/loss analysis. Lifecycle stages:

```
Host builds SQE → SQE written to SQ slot → SQ tail doorbell write
→ controller fetch → firmware processing → completion generated
→ CQE written (phase bit) → interrupt/MSI-X → host observes CQE
→ CQ head doorbell update
```

Failure classes the skill must be able to distinguish (given evidence such
as Mazu trace, doorbell values, queue dumps, firmware logs):

| Failure class | Discriminating evidence |
|---|---|
| command lost (never in SQ) | SQ memory lacks SQE; tail never moved |
| command not fetched | SQE present; tail written; no fetch/fw-log entry |
| command stuck in firmware | fetch logged; no completion within budget |
| completed, CQE missing | fw completion logged; CQ slot lacks CQE |
| CQE written, host missed it | CQE present with correct phase; no host observation (interrupt lost / phase mismatch read) |
| phase-bit problem | CQE phase inconsistent with CQ pass count |
| queue pointer inconsistency | head/tail math vs doorbell values disagree |

Not implemented now; recorded as skill responsibility and as future
evidence requirements for the executor/mock (queue introspection is a
Phase 2+ capability proposal, output type C).

### 6.4 SCSI boundary (decision 8)

SCSI stays embedded in the usb skill (`scsi-over-usb.md`, layer
`scsi.cdb`). **Extraction criterion** (recorded in manifest and SKILL.md):
if the project needs substantial independent SCSI analysis — SPC/SBC
command-set depth, sense-data taxonomy, mode pages, VPD pages, persistent
reservations, ALUA, or task-management analysis beyond UAS TMF basics —
SCSI becomes its own domain skill; the usb skill then retains only the
transport mapping (how CDBs/status ride BOT/UAS).

## 7. Specification pinning (decision 9)

Every authoritative citation carries: **spec name + project-pinned
revision + section + figure/table where applicable**, e.g.
`[NVMe Base <rev TBD>, §<n>, Fig. <m>]`. Rules:

- Pinned revisions live in one place: `_shared/spec-pins.md`.
- Revisions are chosen by the project, never invented. Until chosen, the
  pin is explicitly `TBD` and citations read `<rev TBD>` — visibly
  unpinned rather than silently generic.
- The project-provided specification document remains final authority;
  skill reference tables are curated subsets citing into it.

Proposed initial pin table (all TBD — needs your input, §9):

| Spec | Pin |
|---|---|
| NVMe Base Specification | TBD |
| NVM Command Set Specification | TBD |
| PCIe Base Specification (boundary only) | TBD |
| USB 2.0 | TBD |
| USB 3.2 | TBD |
| USB MSC BOT | TBD (1.0 is the only published rev — confirm) |
| UAS / UASP | TBD |
| USB4 | TBD (v1.x vs v2.x decides Gen4 content) |
| SPC / SBC (embedded SCSI boundary) | TBD |

## 8. Cross-protocol flow context (decision 5 — requirement, not syntax)

**Requirement:** the Flow DSL must be able to state *how* a protocol
reaches a device, keeping transport semantics separate from command
semantics. The four configurations to distinguish:

| Configuration | Transport context | Command protocol |
|---|---|---|
| Native NVMe | pcie | nvme |
| USB4-tunneled NVMe | usb4 → pcie-tunnel | nvme |
| USB storage | usb (bot \| uas) | scsi |
| USB4-tunneled USB storage | usb4 → usb3-tunnel → usb (bot \| uas) | scsi |

Architectural shape (illustrative only — exact syntax is a Flow DSL
design task, not redesigned here): the **target** grows a transport
context block alongside the existing `protocol`:

```yaml
targets:
  - id: ssd0
    protocol: nvme            # command semantics (unchanged meaning)
    transport:                # NEW: how the protocol reaches the device
      type: usb4-pcie-tunnel  # pcie | usb | usb4-pcie-tunnel | usb4-usb3-tunnel
      path: { ... }           # transport-specific locator (route string,
                              #   port path, tunnel id — defined per type)
    executor: usb4
    device: "..."
```

Rules the eventual syntax must honor: `protocol` keeps exactly its current
meaning (command semantics; validated against the registry);
`transport` never changes command validation — it informs executor
selection, trace correlation, and skill handoffs (manifest layers);
omitted transport defaults to the protocol's native transport (pcie for
nvme, usb for scsi) so existing v2 flows remain valid. Implementation is
deferred; no DSL/code change in this proposal.

## 9. Remaining decisions that require human input

1. **Spec revision pins** (§7): which revisions does the project target
   for NVMe Base / NVM Cmd Set / USB4 / USB 3.2 / UAS / SPC / SBC?
   (BOT 1.0 assumed — confirm.) Where will the spec documents live
   (committed vs local-only for licensing)?
2. **Registry extension roadmap** (output type C targets): approve
   `usb.*` (get_descriptor, set_configuration, …) and `usb4.*`
   (read_router_config, path_status, …) as Phase 2/3 proposals-to-come?
   (No code now; this only sets what type-C outputs may propose.)
3. **Trace formats priority**: Mazu-native + usbmon + sysfs/boltctl +
   nvme driver traces first? Which hardware analyzers does your lab use
   (LeCroy / Beagle / other), if any, for exporter support later?
4. **Skill location**: confirm in-repo `.claude/skills/` (versioned with
   the project, revisions ride the same PRs as registry/DSL changes).
5. **Transport-context syntax**: when we do implement §8 in the DSL,
   should `transport.type` values be an enum in the DSL spec (validated),
   and does `executor` stay explicit or become derivable from transport?

Upon approval: create `manifest.yaml`, `_shared/` (4 files + spec-pins),
and the three SKILL.md + references skeletons — in that order, as a
reviewable commit, with no source-code changes.

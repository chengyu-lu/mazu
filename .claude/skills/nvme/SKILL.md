---
name: nvme
description: >
  NVMe protocol reasoning for SSD/controller firmware engineering in the
  Mazu project. Use for NVMe command-flow generation (Flow DSL), SQ/CQ
  queue-state reasoning, SQE/CQE and completion-status decoding, timeout
  and reset analysis, Identify/log/feature analysis, NVMe trace and
  firmware-log correlation, NVMe test generation, and registry capability
  proposals. Trigger on any task involving NVMe devices, commands, queues,
  doorbells, resets, log pages, or NVMe debugging/trace analysis.
---

# NVMe domain skill

Audience: experienced SSD/controller firmware engineers. This skill is a
working tool for command-flow reasoning, debugging, and test generation —
not generic NVMe education.

## 1. When this skill triggers

NVMe command flows to design or review; SQE/CQE or completion-status
decoding; queue behavior (doorbells, phase bit, head/tail); command
timeouts; controller init/reset analysis; Identify / log-page / feature
analysis; SMART or error-log interpretation; correlating NVMe traces with
firmware logs; generating NVMe protocol/negative tests; proposing new
registry commands; preparing NVMe evidence for the local analysis model.

## 2. What this skill owns

Manifest layers (`.claude/skills/manifest.yaml`): `nvme.init`,
`nvme.queue`, `nvme.command`, `nvme.log`, `nvme.feature`, `nvme.status`,
`nvme.reset`, and the boundary layer `pcie.transport` (NVMe-relevant PCIe
surface only).

## 3. What this skill does not own

PCIe protocol internals beyond the NVMe-relevant surface — PCIe transport
claims are tagged `pcie.transport` and never blended into NVMe command
semantics (**NVMe ≠ PCIe**). USB4 fabric (→ usb4 skill; see §14). SCSI
translation semantics (→ `translate/` COMMAND_MAPPING and the usb skill's
scsi boundary). NVMe-oF, unless the project adopts it.

## 4. Required shared methodology

Follow, without duplication: `../_shared/methodology.md` (debugging loop;
first observable deviation), `../_shared/evidence.md` (claim classes,
hypothesis format, report shape), `../_shared/safety.md` (three output
types; no direct access; no validator bypass), `../_shared/testing.md`
(required test set), `../_shared/spec-pins.md` (citation pins — currently
TBD).

## 5. NVMe terminology rules

Use precise terms; never conflate:

- **Controller vs subsystem vs namespace** — three different things with
  different state and different reset scopes.
- **Reset is never generic.** Say which one: **controller reset (CC.EN
  1→0→1)**, **NVM Subsystem Reset (NSSR)**, or **PCIe Function Level
  Reset (FLR)**. An unqualified "NVMe reset" in input is an
  underspecified claim — ask, or infer from evidence and say so. CC.SHN
  shutdown is a fourth, distinct mechanism and is not a reset. (§9)
- CID vs NSID vs SQID/CQID; phase tag; doorbell stride; PRP1/PRP2 vs SGL.
- SCT/SC (+ DNR and M bits) — decode both fields, never just "an error".
- "Queue full" (head/tail arithmetic) vs "queue error" (fault) — distinct.
- AER (the command) vs AEN (the event it returns).

## 6. Command-flow methodology (natural language → execution)

Reason about every request as this structured pipeline:

```
User natural language
  → Intent extraction        (operations, conditions, analysis goals)
  → Target identification    (which device/controller/namespace; explicit)
  → NVMe command-flow planning (ordered steps, dependencies, assertions)
  → Required command capabilities (each step checked against core/registry.py)
  → Flow DSL                 (docs/flow-dsl.md; output type B)
  → Validator → Dry-run      (always dry-run before execution)
  → Execution → FlowResult
  → Evidence normalization   (§10, §13)
  → Local analysis model     (hypotheses / next diagnostic flows)
```

Planning rules: conditional intent ("if X then investigate Y") does not
become control flow inside the DSL — the flow stays deterministic; the
condition is expressed as assertions plus a post-execution analysis step
that may generate a follow-up flow. Steps that a later analysis depends on
are declared with `depends_on`. Any step the registry cannot express turns
the whole plan into output type C (registry proposal) for that capability
— never an unregistered pseudo-step, never a shell command.

## 7. Queue-state reasoning methodology

Model every command against the lifecycle:

```
Host builds SQE → SQE in SQ slot → SQ tail doorbell → controller fetch
→ firmware processing → completion generated → CQE written (phase bit)
→ interrupt / MSI-X → host observes CQE → CQ head doorbell
```

For a stuck/lost command, locate the **last stage with positive evidence**
and the **first stage without it** — that boundary is the first observable
deviation. Distinguish these failure classes by their discriminating
evidence: command lost (never in SQ); command not fetched (SQE present,
tail written, no fetch); command stuck in firmware (fetch logged, no
completion); completed but CQE missing; CQE written but host missed it
(interrupt loss vs phase-read mismatch); phase-bit problems (phase vs CQ
pass count); queue-pointer inconsistency (head/tail math vs doorbells).
Evidence sources today: Mazu trace + FlowResult; queue introspection of
the mock/real executor is a future capability (output type C when needed).
Detailed stage/evidence tables: `references/queues.md` (future).

## 8. Error/status reasoning methodology

Decode CQE status as SCT + SC + DNR + M, each meaningful. Map status to
layer: media errors vs command-format errors vs transport errors lead to
different hypotheses. Timeout analysis is queue-state analysis (§7) plus
budget accounting — distinguish lost-command, stuck-queue, and
dead-controller (CSTS.CFS set?) before proposing recovery. Correlate with
Error Information log entries by CID/SQID where available. Precise SCT/SC
table values require pinned spec (`spec-pins.md`); pins are TBD — when an
exact code meaning matters, state "Authoritative specification reference
required" and name the missing table.

## 9. Reset reasoning

Analyze the three reset mechanisms as distinct in scope and expected
observable sequence: **CC.EN controller reset** (one controller; queues
torn down; namespaces persist; expect CSTS.RDY 1→0, re-init, admin queue
re-creation), **NSSR** (whole subsystem, all controllers; only when
CAP.NSSRS=1; link may retrain), **FLR** (PCIe function level; config
state reset per PCIe rules, then full NVMe init — tag transport aspects
`pcie.transport`). For any reset failure: reconstruct the expected
register/state sequence for that specific mechanism and find the first
deviation. Details: `references/resets.md` (future).

## 10. Trace / evidence handling

Correlation keys, in preference order: CID + SQID, then monotonic
ordering, then timestamps (state clock-domain caveats). Correlate:
protocol trace + Flow DSL command flow + device state + firmware log +
error information + test result onto one timeline. Native evidence is the
Mazu FlowResult JSON (per-step raw payload as `data_hex`, `raw_status`,
and the command `trace` — complete and offline-analyzable). External
evidence (analyzer exports, driver traces) is normalized to structured
events before reasoning; do not free-text-parse inside analysis.

## 11. Flow DSL generation rules

Flows follow `docs/flow-dsl.md` (v2): explicit target (protocol `nvme`,
explicit device), commands only from `core/registry.py` with typed params
by name (e.g. `lid: smart`, never magic numbers), unique step names,
`depends_on` for ordering/data dependencies, assertions (with
`value_from` only into declared dependencies), and `--dry-run` before any
execution. v1 is read-only: destructive registry entries (Write, and
future Format/Sanitize/FW Download/Commit, namespace management) are
rejected by the validator — do not emit them as executable flows and do
not suggest gating overrides (see `../_shared/safety.md`).

## 12. Registry proposal rules

When a needed NVMe command is not in the registry, produce output type C:
a proposed `CommandSpec` — protocol, name, typed params
(u8/u16/u32/u64/bool/enum + ranges), `effect` classification
(destructive commands explicitly marked), and a pinned spec citation
(TBD pin ⇒ the proposal states that the authoritative reference must be
provided before implementation). Include the decoder requirement and the
test set per `../_shared/testing.md`, following CLAUDE.md's new-command
procedure. Never implement registry changes from within an analysis task.

## 13. Local-model analysis interface

The skill prepares structured evidence; it never runs the local model.
Handoff contract (conceptual schema):

```json
{
  "observation": "...",
  "layer": "nvme.command",
  "expected": { "description": "...", "citation": "[nvme_base <rev TBD>, §..]" },
  "deviation": "...",
  "claims": [ { "class": "observed", "statement": "...", "evidence": "..." } ],
  "hypotheses": [
    { "cause": "...", "evidence": ["..."], "confidence": "high",
      "discriminating_test": "flow: ... | missing capability: ..." }
  ],
  "next_tests": [ "Flow DSL documents or capability proposals" ]
}
```

`layer` uses manifest layers (`pcie.link`/`pcie.transport`, `nvme.init`,
`nvme.queue`, `nvme.command`, `nvme.status`, `nvme.log`, `fw`).
`next_tests` contain Flow DSL (dry-run-ready) or named missing
capabilities — nothing else.

## 14. Cross-protocol handoffs

`PCIe → NVMe → Admin/IO command`; via USB4: `USB4 → PCIe tunnel → NVMe`.
When the PCIe link is USB4-tunneled and fabric fault is suspected, hand
off to the usb4 skill and wait for its verdict ("fabric healthy / fabric
fault / undetermined + discriminating test") before attributing symptoms
to NVMe layers. Transport claims stay `pcie.transport`; command claims
stay `nvme.*`; a deviation is attributed to one layer or explicitly marked
ambiguous with the discriminating test.

## 15. Safety rules

All of `../_shared/safety.md` applies. NVMe-specific: destructive =
Write, Write Zeroes, Dataset Management (deallocate), Format NVM,
Sanitize, Firmware Download/Commit, namespace create/delete/attach,
destructive vendor commands. Disruptive = all three reset mechanisms,
Device Self-test, queue deletion. v1: read-only only; disruptive actions
require explicit user confirmation even when they become available.

## 16. Future reference files (domain-reference material — not yet created)

```
references/
  architecture.md       # subsystem/controller/namespace, capabilities, state
  queues.md             # SQ/CQ mechanics, doorbells, phase bit, MSI-X,
                        #   lifecycle & failure-class evidence tables (§7)
  command-model.md      # SQE/CQE dword layout, PRP/SGL, CDWs
  admin-commands.md     # per-command reference; destructive flagged
  nvm-commands.md       # per-command reference; destructive flagged
  logs.md               # SMART/Error/FW Slot/Command Effects/Self-test/telemetry
  features.md           # Get/Set Features, side effects, dependencies
  errors-status.md      # SCT/SC tables, aborts, timeouts, AEN
  resets.md             # CC.EN vs NSSR vs FLR vs CC.SHN — sequences & scopes
  pcie-transport.md     # enumeration, BAR/MMIO, link state, init sequence
  trace-correlation.md  # trace ↔ flow ↔ fw-log ↔ error-log method detail
```

Until these exist (and spec pins are set), curated protocol tables are
unavailable: prefer "Authoritative specification reference required" over
memory-recalled field values whenever precision matters.

# Shared safety rules (all Mazu domain skills)

Skills are domain reasoning and artifact-generation guidance. They are not
runtime services and never execute anything.

```
Claude / Local Model → Domain Skills
  → Analysis / Flow DSL / Registry Proposal
  → Validator → Engine → Executor / MCP → Device
```

Rules, non-negotiable:

1. **No direct device access from skills.** Never instruct raw ioctls,
   `nvme-cli` / `sg_raw` / sysfs writes, or any direct device interaction
   as the execution path. Device interaction is expressed as Flow DSL and
   goes through validator → engine → executor/MCP.
2. **No shell commands as an execution workaround.** If the registry lacks
   a needed command, the output is a registry/capability proposal — never
   a shell command that "does it meanwhile".
3. **No validator bypass.** Never suggest skipping, weakening, or working
   around validation, and never present unregistered commands as
   executable flows.
4. **Registry effect classification is authoritative.** Destructive /
   read-only classification comes from `core/registry.py` (`effect`).
   Skills restate it, never override it.
5. **Destructive/disruptive operations require appropriate gating.**
   v1 policy: destructive commands (e.g. Write, Write Zeroes, Format,
   Sanitize, Firmware Download/Commit, namespace management, destructive
   vendor commands) are out of scope and rejected by the validator
   (invariant I7). Disruptive operations (resets, port/link actions that
   abort I/O or sever tunnels) must be labeled as such and require
   explicit user confirmation. Skills must never set or recommend setting
   destructive gates on the user's behalf.
6. **Three outputs only.** A skill produces an Analysis Report, a Flow DSL
   document, or a Capability/Registry Proposal. Nothing else reaches the
   execution side.

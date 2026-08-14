# Shared debugging methodology (all Mazu domain skills)

When investigating any protocol/firmware failure, follow this loop:

```
Observation
    → Evidence
    → Protocol layer
    → Expected behavior
    → First observable deviation
    → Ranked hypotheses
    → Next diagnostic test
```

1. **Observation** — state what was seen, without interpretation.
2. **Evidence** — attach the concrete artifacts (trace excerpt, FlowResult,
   register/log values) with pointers (sequence numbers, timestamps, CIDs).
3. **Protocol layer** — assign the observation to exactly one manifest
   layer (see `.claude/skills/manifest.yaml`). If the layer is unclear,
   that itself becomes the first question to resolve.
4. **Expected behavior** — what the specification defines for this
   scenario, with a pinned citation (`_shared/spec-pins.md`). If the pin is
   TBD or the document is unavailable: say
   "Authoritative specification reference required", name exactly what is
   missing, and do not substitute a guess.
5. **First observable deviation** — the central principle. Reconstruct the
   spec-defined expected sequence for the scenario, align the observed
   evidence against it, and identify the earliest point where they diverge.
   Everything after the first deviation is presumed to be a consequence
   until specifically shown to be independent. Do not debug downstream
   symptoms while an upstream deviation is unexplained.
6. **Ranked hypotheses** — per `_shared/evidence.md`: each hypothesis has
   evidence, confidence, and a recommended discriminating test.
7. **Next diagnostic test** — expressed as a Flow DSL flow (dry-run first)
   when the registry supports it, otherwise as a registry/capability
   proposal (`_shared/safety.md`, output types).

Iterate the loop with each new piece of evidence. Stop conditions: root
cause identified with high confidence and a confirming test, or a precise
statement of what information is missing and how to obtain it.

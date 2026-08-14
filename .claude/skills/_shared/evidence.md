# Shared evidence rules (all Mazu domain skills)

## Claim classification

Classify every **important claim** — one that a conclusion, a hypothesis
ranking, or a recommended action depends on — as exactly one of:

| Class | Meaning | Requirement |
|---|---|---|
| observed | seen in trace/log/result | pointer to the evidence (seq/ts/CID/field) |
| spec-defined | required by specification | pinned citation (`_shared/spec-pins.md`); TBD pin ⇒ mark unverified |
| implementation-defined | spec allows choice; this implementation chose | name the implementation |
| vendor-specific | vendor-defined behavior | vendor documentation, or mark unavailable |
| hypothesis | proposed explanation | see below |

The reasoning narrative stays readable prose; important claims are
collected in a distinct **Claims** section of any analysis report so the
load-bearing statements stay auditable. Not every sentence needs a label —
only the claims the conclusion rests on.

## Hypotheses

Every hypothesis must contain:

- **evidence** — the observed claims supporting it (pointers, not prose)
- **confidence** — `high` | `medium` | `low`
- **recommended discriminating test** — the check that would raise or
  eliminate it (as Flow DSL when supported; otherwise a named missing
  capability or a request for a specific artifact)

Rank hypotheses by confidence; state what would change the ranking.

## Uncertainty

If authoritative information is unavailable: do not guess; state what is
unknown; identify the missing information (spec section, trace, log,
register dump); recommend how to obtain it. "Authoritative specification
reference required" is a valid and expected answer.

## Analysis report shape

An analysis report contains, in order: Summary (1–3 sentences) · Observed
behavior · Expected behavior (with citations) · First observable deviation
· Claims (classified) · Hypotheses (ranked) · Next diagnostic tests ·
Missing information (if any).

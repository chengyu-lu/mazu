# Shared testing methodology (all Mazu domain skills)

Any protocol artifact the skills help implement (codec, registry command,
mock behavior, flow) requires this test set:

| Test kind | What it checks |
|---|---|
| schema tests | Flow DSL / IR structures parse, validate, round-trip (invariant I2) |
| encoding tests | object → wire bytes against spec-shaped known vectors |
| decoding tests | wire bytes → object against spec-shaped known vectors |
| positive tests | the intended behavior succeeds end-to-end |
| negative tests | malformed input, boundary values, invalid state are rejected with the correct, specific error (validator reject / device error status / decoder reject — three distinct levels) |
| mock-device tests | full pipeline on the spec-shaped mock (invariant I5) |
| integration tests | multi-step flows, dependencies, trace, reporting |
| hardware tests | real devices; `tests/hw/`, `@pytest.mark.hw`, opt-in only, never in the default test run |

Rules: every encoder/decoder ships with its tests in the same change (a
codec without tests does not exist — CLAUDE.md principle 6); known vectors
are laid out per spec offsets with citations; mock tests must not silently
skip; the default `pytest` run stays green on any machine with no device
attached.

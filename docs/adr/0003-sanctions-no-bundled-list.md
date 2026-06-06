# ADR-0003 — The sanctions workflow bundles no list

**Status:** Accepted (0.1.0)

## Context

Bundling a sanctions list (OFAC SDN or otherwise) would imply an operating
screening control, create a stale-data liability, and overclaim what the library
does. Sanctions screening accuracy is the deployer's wired list and matching
logic, not a governance pattern.

## Decision

`SanctionsDispositionWorkflow` ships **no list**. The list source is a pluggable
`SanctionsListProvider` seam; the default `UnwiredListProvider` has source
`UNWIRED-BY-DEPLOYER` and returns no matches. The library claims only a reference
**screen → hold → escalate → veto** disposition workflow and its audit trail.

## Consequences

- The claim layer is honest: a *reference disposition pattern*, never an
  operating OFAC control.
- A deployment that forgets to wire a real provider cannot silently pass — every
  disposition records `provider_unwired=true`.
- When a deployer wires a real provider, the same workflow and trail apply
  unchanged.

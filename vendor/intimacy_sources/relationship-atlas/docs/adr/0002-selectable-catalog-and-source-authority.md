# ADR 0002: Selectable catalogs and source-authority boundaries

- Status: accepted
- Date: 2026-08-31

## Context

FetLife exposes multiple vocabularies. The authenticated relationship settings
menus contain 73 relationship choices and 606 D/s choices, while captured
Kinktionary and public-selector surfaces produce broader unions of 161 and 1,202
labels. Presenting the unions as immediately selectable overstates what a member
can execute on the current settings page. A source definition also does not make
an inferred reciprocal label a FetLife-declared relationship.

## Decision

Use authenticated menu membership as the default customer catalog. Expose the
broader unions only through an explicit Full reference library control and mark
reference-only entries. Keep source definitions and Relationship Atlas pairing
interpretations as separate authority records in the domain model and exports.

Bind releases to a source manifest containing capture/verification dates,
counts, normalized menu hashes, canonical source URLs, license scope, manual
capture policy, and privacy boundary. Reject publication when official excerpts
lack canonical Kinktionary evidence or when public source files contain profile
identifiers.

## Consequences

- The default interface answers “what can I choose now?” with 73/606 lists.
- Researchers retain the complete 161/1,202 reference vocabularies.
- Deep links to reference-only terms still work and disclose their status.
- Pairing suggestions remain useful without being attributed to FetLife.
- Maintenance is reviewed and manual; the application has no crawler, FetLife
  credentials, runtime API dependency, or member-profile data.
- Commercial use or automated collection requires separate permission rather
  than an architectural toggle.

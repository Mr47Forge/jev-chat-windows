# ADR 0003: Reviewed catalog promotion

- Status: accepted
- Date: 2026-08-31

## Context

The published catalog, source manifest, and authenticated-menu counts form one
release unit. Previously the validator only read canonical filenames, the
workbook exporter discovered its manifest through a machine-specific relative
path, and maintainers had no deterministic report separating additions,
removals, changed excerpts, pairing edits, and source-manifest drift.

## Decision

Use four explicit stages: capture, candidate export, proposal, and promotion.
The validator accepts explicit candidate paths and applies the same schema,
source-authority, excerpt, and privacy gates used by deployment. Proposal output
binds the current and candidate files by SHA-256 and produces JSON plus a human
review report. Promotion is a separate command that requires the exact
candidate files, an unchanged base, matching candidate digests, revalidation,
at least one proposed change, and the literal approval token `PROMOTE`.

Authenticated capture remains manual and reviewed. The pipeline does not add a
crawler, store credentials, or publish profile identifiers.

## Consequences

- A candidate can fail safely without replacing published data.
- Reviewers see removals and authority changes instead of only final counts.
- A stale proposal or modified candidate cannot be promoted.
- Real source count changes are allowed when catalog membership and the source
  manifest agree; historical 73/606 values are no longer hard-coded as future
  truth.
- Promotion changes only data files. Full verification remains mandatory before
  commit or deployment.

# ADR 0001: Unified discovery over separate catalogs

- Status: accepted
- Date: 2026-08-31

## Context

Relationships and D/s/profile roles have different domain fields and should remain separate catalog views. Requiring a user to choose the correct view before searching, however, causes valid community shorthand to appear missing when its target belongs to the other catalog.

## Decision

Keep the two catalog views and their domain boundaries, then add a single universal finder over their union. Reuse the deterministic search engine and pairing resolver. Store community vocabulary in a versioned, sourced data file rather than executable search code. Global selection routes to the canonical catalog deep link.

## Consequences

- Users can start with language rather than data taxonomy.
- Catalog-specific filters remain coherent.
- Search vocabulary can be maintained and validated independently of application code.
- Discovery terms must never be displayed as platform definitions or additional catalog entries.
- The static application remains offline-capable and adds no backend, authentication, or privacy surface.

## Rejected alternatives

- Merge both catalogs into one view: role axes and relationship classifications would become confusing.
- Runtime FetLife search or scraping: unavailable offline, dependent on authentication/CORS, and expands privacy and reliability risk.
- Automatically mined trend labels: would confuse transient language with verified platform vocabulary.

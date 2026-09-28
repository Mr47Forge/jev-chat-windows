# Relationship Atlas project context

## Product

Relationship Atlas is a static, local-first React/Vite PWA published on GitHub Pages. It inventories captured FetLife relationship terms and D/s/profile roles, preserves short verbatim platform excerpts, and explains partner-side label structure without presenting labels as consent or requirements.

## Invariants

- Published catalog names and excerpts come from captured FetLife sources; never invent definitions.
- `confidence` remains internal resolver metadata and must never appear in customer UI or exports.
- A two-way pair requires a same-catalog target that returns to the origin.
- Community discovery terms are navigation metadata only. They must target an existing catalog label and include a basis and source in `src/data/discovery-terms.json`.
- No captured usernames, credentials, analytics, remote writes, or server-side profile data belong in the repository.
- My Pairing remains versioned, sanitized browser-local state.
- Deep links use `#relationships/{id}` and `#roles/{id}` and must remain backward compatible.

## Architecture

- `src/catalog.js`: catalog inflation and pairing domain logic.
- `src/search.js`: deterministic fuzzy ranking over labels, partner labels, types, axes, sources, definitions, and discovery vocabulary.
- `src/data/catalog.json`: compact captured source data.
- `src/data/discovery-terms.json`: versioned navigation vocabulary with provenance.
- `src/components`: accessible presentation and workflows.
- `scripts/validate-catalog.mjs`: deployment-blocking schema and provenance validation.
- `scripts/propose-catalog-update.mjs`: non-mutating candidate validation and human-readable source diff.
- `scripts/promote-catalog-update.mjs`: digest-bound, explicitly approved catalog promotion.
- `public/service-worker.js`: same-origin local-first caching.

See `docs/ARCHITECTURE.md` and `docs/adr/0001-unified-discovery.md` before changing navigation, persistence, pairing semantics, or source data.

## Required verification

Run `npm run verify:full`. It must validate data, lint, run unit tests, build production assets, and pass desktop/mobile Playwright journeys. GitHub Pages CI repeats the same material gates before deployment.

Catalog maintenance must generate and review a proposal before promotion. Never replace canonical data directly from an authenticated browser capture.

## Known constraints

- GitHub Pages is static; authenticated FetLife capture is an explicit maintenance operation, not a runtime dependency.
- The application has no backend, telemetry, account system, or cross-device synchronization.
- Search terminology may be current while the underlying catalog is only as fresh as `meta.captured`; never imply live synchronization.

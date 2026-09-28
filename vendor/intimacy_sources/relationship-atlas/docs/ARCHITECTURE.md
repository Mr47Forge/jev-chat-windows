# Relationship Atlas architecture

## System boundary

Relationship Atlas is a static, installable reference. GitHub Pages serves immutable production assets; the browser performs catalog inflation, search, pairing resolution, and local shortlist persistence. FetLife is a source and outbound evidence destination, not a runtime API dependency.

```text
captured catalog + source manifest + sourced discovery terms
                 │
       deployment validation
                 │
       catalog and search domain
                 │
  catalog views ─ universal finder ─ pairing workspace
                 │
      versioned browser-local state
```

## User-visible behavior

- Relationships opens with the 73 captured Add Relationship menu choices.
- D/s & Profile Roles opens with the 606 captured Add D/s menu choices.
- The 161/1,202 union catalogs are an explicit reference-library opt-in; every
  reference-only entry is labeled as potentially unavailable on a profile.
- One global finder searches all relationship and D/s/profile labels without requiring the user to choose a catalog first.
- Catalog-specific search, filters, pair maps, definitions, deep links, comparison, and My Pairing remain available.
- Selecting a global result opens the correct catalog and stable item deep link.
- Common shorthand and community language can help locate an existing label but cannot create or rename a catalog entry.

## Inputs and outputs

Inputs are the captured catalog, discovery vocabulary, a user search query, filters, and local pairing decisions. Outputs are ranked references, partner-side structure, evidence links, deep links, and a CSV generated entirely in the browser.

The only durable user state is `relationship-atlas:pairing:v2`. It is bounded to 500 unique catalog entries, validates decisions against an allowlist, limits editable partner labels to 120 characters, and ignores unknown IDs and fields.

## Layer ownership

| Layer | Responsibility |
|---|---|
| Source data | Compact captured rows, counts, provenance, discovery vocabulary |
| Domain | Stable IDs, partner resolution, pair structure, axes, source membership |
| Search | Normalization, bounded edit distance, weighted deterministic ranking |
| Application | Navigation, deep-link state, saved pairing state, compare selection |
| Presentation | Responsive accessible catalog, global finder, diagrams, dialogs, exports |
| Infrastructure | Vite build, service worker, GitHub Pages CI, dependency maintenance |

## Trust boundaries

- Catalog and discovery JSON are build-time untrusted inputs until `npm run validate:data` passes.
- `source-manifest.json` binds menu counts and normalized-order hashes to the
  reviewed capture, documents the manual-capture boundary, and records the
  Kinktionary license and Terms URLs.
- Official excerpts require a canonical Kinktionary URL, Kinktionary source
  membership, nonempty text, and a maximum of 24 words. Non-official text cannot
  claim to be official or verbatim.
- Partner-side mappings and structures are explicitly Relationship Atlas
  interpretations. They never inherit FetLife authority from a definition URL.
- External links are HTTPS evidence destinations and use a no-referrer page policy.
- Search text is rendered by React, never interpreted as HTML.
- CSV cells beginning with spreadsheet formula prefixes are neutralized.
- The service worker caches only same-origin GET assets within its scope and ignores range requests.
- The Content Security Policy disallows third-party scripts, objects, form submission, and cross-origin connections.

## Failure behavior

- Invalid source data blocks local verification and deployment.
- A render failure shows a recovery surface without deleting local pairing state.
- Browser storage failure leaves the current in-memory shortlist usable.
- Network loss falls back to previously cached app assets after the first successful load.
- Unknown or stale deep-link IDs fall back to a neutral default label.
- No search match produces a clear empty state and never fabricates a result.

## Performance model

Search indexing is memoized per catalog. User queries use deferred rendering and a bounded edit-distance algorithm; results use deterministic score/name/ID ordering. The universal finder limits rendered results to 12 while preserving full-catalog ranking. The service worker caches hashed production assets for offline reuse.

## Data maintenance

1. Manually review current menus and Kinktionary indexes through an authenticated maintenance session; do not add a scheduled crawler.
2. Rebuild the workbook and explicitly export candidate `catalog.json` and `source-manifest.json` files without profile identifiers.
3. Run `npm run catalog:propose -- --catalog <candidate-catalog> --manifest <candidate-manifest> --out .catalog-maintenance/<capture>/proposal.json`.
4. Review the generated JSON and Markdown for additions, removals, changed fields, source drift, definition authority, and menu-count changes.
5. Promote only the reviewed digests with `npm run catalog:promote -- --proposal <proposal> --catalog <candidate-catalog> --manifest <candidate-manifest> --approve PROMOTE`.
6. Update discovery terms only when a sourced phrase maps to an existing label.
7. Run Excel recalculation/smoke verification and `npm run verify:full`.
8. Merge to `main`; GitHub Pages deploys only after its clean-room gates pass.

The proposal stage is non-mutating. Promotion rejects zero-change, stale-base,
modified-candidate, invalid, or privacy-unsafe inputs. See
`docs/adr/0003-reviewed-catalog-promotion.md`.

## Acceptance criteria for universal discovery

- Header button and Ctrl/Cmd+K open one accessible search dialog.
- KTP resolves to Polyamory and current community task language resolves to Taskmaster.
- Selecting a result switches to its correct catalog, updates the stable hash, and renders its pair map.
- Keyboard arrows move the active result, Enter opens it, and Escape closes the dialog.
- Desktop and mobile workflows pass without exposing internal confidence tiers.
- Catalog and discovery schema failures block deployment.

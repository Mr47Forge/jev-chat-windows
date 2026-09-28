# Relationship Atlas

Static, installable reference for FetLife relationship terms and D/s/profile roles. Find any label across both catalogs, see its partner-side language, read FetLife’s definition, and save or share the result. Detailed mapping logic stays behind the interface.

## Data scope

- The current authenticated profile menus contain 73 Add Relationship choices and 606 Add D/s Relationship choices. These are the primary selectable catalogs.
- The expanded reference catalogs contain 161 unique relationship terms across 137 Relationship Kinktionary entries, and 1,202 unique role labels across 955 current Role Kinktionary pages and 813 public join/profile selector labels.
- 84 relationship and 792 role entries include short verbatim FetLife excerpts backed by their canonical Kinktionary pages.
- No inferred definitions are used. Rows without published text state that no platform definition was captured.
- Captured 2026-08-30.

Every label captured from both authenticated Add menus is present in the corresponding expanded reference catalog. Menu counts and expanded-catalog counts are intentionally reported separately. The published data excludes local profile fields, member identifiers, and member-profile URLs.

## Source license and use boundaries

Relationship Atlas is an independent, non-commercial educational reference. It is not affiliated with, endorsed by, or sponsored by FetLife.

Short Kinktionary portions are reproduced under FetLife's [Kinktionary License](https://fetlife.com/kinktionary/license-zcfzz), with each excerpt attributed and linked to its source page. Any adapted text must be identified as adapted; it must never be labeled verbatim. The license does not permit commercial use without FetLife's express written consent and notes that other rights may still apply.

FetLife's [Terms of Use](https://fetlife.com/legal/terms-of-use-hwfvu) restrict automated database collection and commercial use of collected data. Catalog maintenance is therefore a manual, authenticated, reviewed capture process rather than a scheduled crawler or runtime integration. Obtain FetLife's written clarification before automating collection, using this material commercially, or expanding beyond the documented educational scope.

## Search architecture

Search uses a precomputed, deterministic index over verbatim labels, partner labels, catalog type, axes, sources, pair structure, and captured definitions. It normalizes punctuation and spacing and recovers realistic misspellings. The header finder searches the full 1,363-label union and routes a result to its canonical catalog deep link. Common community shorthand—including ENM, CNM, KTP, RA, QPR, FWB, LDR, parallel polyamory, garden-party polyamory, and relationship escalator—is sourced, versioned navigation metadata in `src/data/discovery-terms.json`; it does not create or rename platform catalog entries.

## Pairing methodology

A reciprocal catalog pair requires one named same-catalog target whose mapping returns to the original label. Other edges are explicitly distinguished as a shared label, returning convention, candidate set, independent partner choice, one-way catalog link, unresolved named suggestion, or no fixed counterpart. Authority, activity position, and relationship role apply only to D/s/profile roles. Internal inference tiers help the resolver distinguish structural states but are never displayed or exported. Labels never imply consent.

## Local development

```sh
npm install
npm run verify
npm run dev
```

Run end-to-end checks after installing Playwright Chromium:

```sh
npx playwright install chromium
npm run verify:full
```

Regenerate the checked-in install icons after changing `public/icon.svg` or `public/icon-maskable.svg`:

```sh
npm run icons
```

Runtime and development dependencies are exact-pinned. Monthly Dependabot updates keep npm packages and GitHub Actions current without silently changing a local install.

## Architecture

System boundaries, trust rules, failure behavior, and the data-maintenance workflow are documented in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The universal finder decision is recorded in [ADR 0001](docs/adr/0001-unified-discovery.md). Project invariants and required gates are in [AGENTS.md](AGENTS.md).

Catalog updates use an explicit review boundary:

```powershell
python scripts/export_catalog.py <workbook.xlsx> <candidate-catalog.json> <candidate-source-manifest.json>
npm run catalog:propose -- --catalog <candidate-catalog.json> --manifest <candidate-source-manifest.json> --out .catalog-maintenance/<capture>/proposal.json
npm run catalog:promote -- --proposal .catalog-maintenance/<capture>/proposal.json --catalog <candidate-catalog.json> --manifest <candidate-source-manifest.json> --approve PROMOTE
npm run verify:full
```

Proposal generation validates candidate data but does not change the published catalog. Promotion revalidates exact SHA-256-bound inputs and refuses stale, modified, zero-change, or unapproved proposals. See [ADR 0003](docs/adr/0003-reviewed-catalog-promotion.md).

## GitHub Pages

The repository deploys `dist/` through `.github/workflows/deploy-pages.yml` on every push to `main`. Vite’s base path is `/fetlife-relationship-atlas/`.

## Privacy

My Pairing is versioned browser-local storage. The PWA has no backend, analytics, account system, or network write path. Source links leave the app and open FetLife directly.

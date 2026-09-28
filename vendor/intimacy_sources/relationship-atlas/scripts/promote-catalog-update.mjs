import { spawnSync } from 'node:child_process'
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { sha256 } from './lib/catalog-maintenance.mjs'

const { values } = parseArgs({ options: {
  proposal: { type: 'string' },
  catalog: { type: 'string' },
  manifest: { type: 'string' },
  approve: { type: 'string' },
} })
if (!values.proposal || !values.catalog || !values.manifest || values.approve !== 'PROMOTE') {
  throw new Error('Promotion requires --proposal, --catalog, --manifest, and the explicit token --approve PROMOTE.')
}

const [proposalText, candidateCatalogText, candidateManifestText, currentCatalogText, currentManifestText] = await Promise.all([
  readFile(resolve(values.proposal), 'utf8'),
  readFile(resolve(values.catalog), 'utf8'),
  readFile(resolve(values.manifest), 'utf8'),
  readFile('src/data/catalog.json', 'utf8'),
  readFile('src/data/source-manifest.json', 'utf8'),
])
const proposal = JSON.parse(proposalText)
if (proposal.schemaVersion !== 1 || proposal.approval?.required !== true) throw new Error('Unsupported catalog proposal schema.')
if (proposal.diff?.changeCount < 1) throw new Error('The proposal contains no changes to promote.')
if (proposal.base.catalogSha256 !== sha256(currentCatalogText) || proposal.base.manifestSha256 !== sha256(currentManifestText)) {
  throw new Error('The published catalog changed after this proposal was created. Generate a new proposal.')
}
if (proposal.candidate.catalogSha256 !== sha256(candidateCatalogText) || proposal.candidate.manifestSha256 !== sha256(candidateManifestText)) {
  throw new Error('Candidate files do not match the reviewed proposal.')
}
const validator = spawnSync(process.execPath, [
  resolve('scripts/validate-catalog.mjs'),
  '--catalog', resolve(values.catalog),
  '--manifest', resolve(values.manifest),
], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
if (validator.status !== 0) {
  process.stderr.write(validator.stdout)
  process.stderr.write(validator.stderr)
  throw new Error('Candidate validation failed; canonical data was not changed.')
}
const [validatedCatalogText, validatedManifestText, unchangedCatalogText, unchangedManifestText] = await Promise.all([
  readFile(resolve(values.catalog), 'utf8'),
  readFile(resolve(values.manifest), 'utf8'),
  readFile('src/data/catalog.json', 'utf8'),
  readFile('src/data/source-manifest.json', 'utf8'),
])
if (sha256(validatedCatalogText) !== sha256(candidateCatalogText) || sha256(validatedManifestText) !== sha256(candidateManifestText)) {
  throw new Error('Candidate files changed during validation. Promotion was canceled.')
}
if (sha256(unchangedCatalogText) !== sha256(currentCatalogText) || sha256(unchangedManifestText) !== sha256(currentManifestText)) {
  throw new Error('Published data changed during validation. Promotion was canceled.')
}

try {
  await writeFile('src/data/catalog.json', candidateCatalogText, 'utf8')
  await writeFile('src/data/source-manifest.json', candidateManifestText, 'utf8')
} catch (error) {
  await Promise.all([
    writeFile('src/data/catalog.json', currentCatalogText, 'utf8'),
    writeFile('src/data/source-manifest.json', currentManifestText, 'utf8'),
  ])
  throw error
}
console.log(`Promoted ${proposal.diff.changeCount} reviewed catalog changes. Run npm run verify:full before committing.`)

import { spawnSync } from 'node:child_process'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { basename, dirname, resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { compareCatalogBundles, renderProposalMarkdown, sha256 } from './lib/catalog-maintenance.mjs'

const { values } = parseArgs({ options: {
  catalog: { type: 'string' },
  manifest: { type: 'string' },
  discovery: { type: 'string', default: 'src/data/discovery-terms.json' },
  out: { type: 'string' },
} })
if (!values.catalog || !values.manifest || !values.out) {
  throw new Error('Usage: npm run catalog:propose -- --catalog <candidate-catalog.json> --manifest <candidate-source-manifest.json> --out <proposal.json>')
}

const candidateCatalogPath = resolve(values.catalog)
const candidateManifestPath = resolve(values.manifest)
const discoveryPath = resolve(values.discovery)
const outputPath = resolve(values.out)
if (!/\.json$/i.test(outputPath)) throw new Error('Proposal output must use a .json extension.')
const [prevalidatedCatalogText, prevalidatedManifestText] = await Promise.all([
  readFile(candidateCatalogPath, 'utf8'),
  readFile(candidateManifestPath, 'utf8'),
])
const validator = spawnSync(process.execPath, [
  resolve('scripts/validate-catalog.mjs'),
  '--catalog', candidateCatalogPath,
  '--manifest', candidateManifestPath,
  '--discovery', discoveryPath,
], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
if (validator.status !== 0) {
  process.stderr.write(validator.stdout)
  process.stderr.write(validator.stderr)
  throw new Error('Candidate validation failed; no proposal was created.')
}

const [baseCatalogText, baseManifestText, candidateCatalogText, candidateManifestText] = await Promise.all([
  readFile('src/data/catalog.json', 'utf8'),
  readFile('src/data/source-manifest.json', 'utf8'),
  readFile(candidateCatalogPath, 'utf8'),
  readFile(candidateManifestPath, 'utf8'),
])
const baseCatalog = JSON.parse(baseCatalogText)
const baseManifest = JSON.parse(baseManifestText)
const candidateCatalog = JSON.parse(candidateCatalogText)
const candidateManifest = JSON.parse(candidateManifestText)
if (sha256(prevalidatedCatalogText) !== sha256(candidateCatalogText) || sha256(prevalidatedManifestText) !== sha256(candidateManifestText)) {
  throw new Error('Candidate files changed during validation. Generate the proposal again from a stable snapshot.')
}
const diff = compareCatalogBundles({ baseCatalog, candidateCatalog, baseManifest, candidateManifest })
const proposal = {
  schemaVersion: 1,
  createdAt: new Date().toISOString(),
  base: {
    captured: baseCatalog.meta.captured,
    catalogSha256: sha256(baseCatalogText),
    manifestSha256: sha256(baseManifestText),
  },
  candidate: {
    captured: candidateCatalog.meta.captured,
    catalogFile: basename(candidateCatalogPath),
    manifestFile: basename(candidateManifestPath),
    catalogSha256: sha256(candidateCatalogText),
    manifestSha256: sha256(candidateManifestText),
  },
  approval: { required: true, status: 'pending' },
  diff,
}
await mkdir(dirname(outputPath), { recursive: true })
await writeFile(outputPath, `${JSON.stringify(proposal, null, 2)}\n`, { encoding: 'utf8', flag: 'wx' })
await writeFile(outputPath.replace(/\.json$/i, '.md'), renderProposalMarkdown(proposal), { encoding: 'utf8', flag: 'wx' })
console.log(`Catalog proposal created: ${outputPath} (${diff.changeCount} review items).`)

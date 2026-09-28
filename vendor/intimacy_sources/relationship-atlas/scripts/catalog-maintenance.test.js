import { describe, expect, it } from 'vitest'
import { spawnSync } from 'node:child_process'
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { compareCatalogBundles, renderProposalMarkdown, sha256 } from './lib/catalog-maintenance.mjs'

const catalog = ({ relationships, roles, captured = '2026-08-30' }) => ({
  meta: { captured, relationshipCount: relationships.length, roleCount: roles.length },
  relationshipFields: ['Relationship term', 'Partner-side label'],
  roleFields: ['Role', 'Partner-side label'],
  relationships,
  roles,
})

describe('catalog maintenance diff', () => {
  it('separates added, removed, changed, metadata, and manifest changes', () => {
    const diff = compareCatalogBundles({
      baseCatalog: catalog({ relationships: [['Anchor', 'Anchor'], ['Removed', 'Removed']], roles: [['Top', 'Bottom']] }),
      candidateCatalog: catalog({ relationships: [['Anchor', 'Partner'], ['Added', 'Added']], roles: [['Top', 'Bottom'], ['Switch', 'Switch']], captured: '2026-08-31' }),
      baseManifest: { captured: '2026-08-30', sources: { menu: { count: 2 } } },
      candidateManifest: { captured: '2026-08-31', sources: { menu: { count: 3 } } },
    })

    expect(diff.summary).toEqual({
      relationships: { added: 1, removed: 1, changed: 1 },
      roles: { added: 1, removed: 0, changed: 0 },
      metadata: 2,
      manifest: 2,
    })
    expect(diff.relationships.changed[0]).toEqual({
      label: 'Anchor',
      changes: [{ field: 'Partner-side label', before: 'Anchor', after: 'Partner' }],
    })
    expect(diff.changeCount).toBe(8)
  })

  it('produces stable digests and an approval-oriented report', () => {
    expect(sha256('catalog')).toBe('652f55016243bf1b9f1bbea46d5749ef892dbe394e46de9d66ab1aacf0b4af57')
    const markdown = renderProposalMarkdown({
      base: { captured: '2026-08-30' }, candidate: { captured: '2026-08-31' },
      approval: { status: 'pending' },
      diff: {
        changeCount: 1,
        summary: { relationships: { added: 1, removed: 0, changed: 0 }, roles: { added: 0, removed: 0, changed: 0 } },
        relationships: { added: [{ 'Relationship term': 'New | <Label>' }], removed: [], changed: [] },
        roles: { added: [], removed: [], changed: [] }, metadata: [], manifest: [],
      },
    })
    expect(markdown).toContain('Approval status: pending')
    expect(markdown).toContain('New \\| &lt;Label&gt;')
    expect(markdown).toContain('--approve PROMOTE')
  })

  it('rejects a candidate containing a member profile URL', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'relationship-atlas-candidate-'))
    try {
      const candidate = JSON.parse(await readFile('src/data/catalog.json', 'utf8'))
      candidate.relationships[0][candidate.relationshipFields.indexOf('Source')] = ['https://fetlife.com', 'users', 'private-profile'].join('/')
      const catalogPath = join(directory, 'catalog.json')
      const manifestPath = join(directory, 'source-manifest.json')
      await Promise.all([
        writeFile(catalogPath, JSON.stringify(candidate), 'utf8'),
        writeFile(manifestPath, await readFile('src/data/source-manifest.json', 'utf8'), 'utf8'),
      ])
      const validation = spawnSync(process.execPath, [
        resolve('scripts/validate-catalog.mjs'), '--catalog', catalogPath, '--manifest', manifestPath,
      ], { encoding: 'utf8' })
      expect(validation.status).not.toBe(0)
      expect(`${validation.stdout}\n${validation.stderr}`).toContain('member/profile URL')
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('creates a non-mutating proposal and refuses zero-change promotion', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'relationship-atlas-proposal-'))
    try {
      const proposalPath = join(directory, 'proposal.json')
      const proposed = spawnSync(process.execPath, [
        resolve('scripts/propose-catalog-update.mjs'),
        '--catalog', resolve('src/data/catalog.json'),
        '--manifest', resolve('src/data/source-manifest.json'),
        '--out', proposalPath,
      ], { encoding: 'utf8' })
      expect(proposed.status).toBe(0)
      const proposal = JSON.parse(await readFile(proposalPath, 'utf8'))
      expect(proposal.diff.changeCount).toBe(0)
      const promoted = spawnSync(process.execPath, [
        resolve('scripts/promote-catalog-update.mjs'),
        '--proposal', proposalPath,
        '--catalog', resolve('src/data/catalog.json'),
        '--manifest', resolve('src/data/source-manifest.json'),
        '--approve', 'PROMOTE',
      ], { encoding: 'utf8' })
      expect(promoted.status).not.toBe(0)
      expect(promoted.stderr).toContain('no changes to promote')
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })

  it('creates a field-level proposal from a valid changed candidate without replacing canonical data', async () => {
    const directory = await mkdtemp(join(tmpdir(), 'relationship-atlas-changed-proposal-'))
    try {
      const canonicalText = await readFile('src/data/catalog.json', 'utf8')
      const candidate = JSON.parse(canonicalText)
      candidate.meta.scope = `${candidate.meta.scope} Reviewed candidate.`
      const catalogPath = join(directory, 'catalog.json')
      const manifestPath = join(directory, 'source-manifest.json')
      const proposalPath = join(directory, 'proposal.json')
      await Promise.all([
        writeFile(catalogPath, JSON.stringify(candidate), 'utf8'),
        writeFile(manifestPath, await readFile('src/data/source-manifest.json', 'utf8'), 'utf8'),
      ])
      const proposed = spawnSync(process.execPath, [
        resolve('scripts/propose-catalog-update.mjs'),
        '--catalog', catalogPath,
        '--manifest', manifestPath,
        '--out', proposalPath,
      ], { encoding: 'utf8' })
      expect(proposed.status).toBe(0)
      const proposal = JSON.parse(await readFile(proposalPath, 'utf8'))
      expect(proposal.diff.changeCount).toBe(1)
      expect(proposal.diff.metadata[0].field).toBe('scope')
      expect(await readFile('src/data/catalog.json', 'utf8')).toBe(canonicalText)
    } finally {
      await rm(directory, { recursive: true, force: true })
    }
  })
})

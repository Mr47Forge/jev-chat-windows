import { createHash } from 'node:crypto'

const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' })

export const sha256 = (value) => createHash('sha256').update(value).digest('hex')

export const inflateRows = (rows, fields) => rows.map((row) => Object.fromEntries(
  fields.map((field, index) => [field, row[index] ?? null]),
))

const compareRows = (baseRows, candidateRows, labelField, fields) => {
  const base = new Map(baseRows.map((row) => [String(row[labelField]), row]))
  const candidate = new Map(candidateRows.map((row) => [String(row[labelField]), row]))
  const added = [...candidate.keys()].filter((label) => !base.has(label))
    .sort(collator.compare).map((label) => candidate.get(label))
  const removed = [...base.keys()].filter((label) => !candidate.has(label))
    .sort(collator.compare).map((label) => base.get(label))
  const changed = [...candidate.keys()].filter((label) => base.has(label)).map((label) => {
    const before = base.get(label)
    const after = candidate.get(label)
    const changes = fields.filter((field) => before[field] !== after[field]).map((field) => ({
      field,
      before: before[field] ?? null,
      after: after[field] ?? null,
    }))
    return changes.length ? { label, changes } : null
  }).filter(Boolean).sort((left, right) => collator.compare(left.label, right.label))

  return { added, removed, changed }
}

const flatten = (value, prefix = '', result = {}) => {
  if (Array.isArray(value)) {
    value.forEach((item, index) => flatten(item, `${prefix}[${index}]`, result))
  } else if (value && typeof value === 'object') {
    for (const [key, item] of Object.entries(value)) flatten(item, prefix ? `${prefix}.${key}` : key, result)
  } else {
    result[prefix] = value ?? null
  }
  return result
}

export const compareCatalogBundles = ({ baseCatalog, candidateCatalog, baseManifest, candidateManifest }) => {
  const relationships = compareRows(
    inflateRows(baseCatalog.relationships, baseCatalog.relationshipFields),
    inflateRows(candidateCatalog.relationships, candidateCatalog.relationshipFields),
    'Relationship term',
    candidateCatalog.relationshipFields,
  )
  const roles = compareRows(
    inflateRows(baseCatalog.roles, baseCatalog.roleFields),
    inflateRows(candidateCatalog.roles, candidateCatalog.roleFields),
    'Role',
    candidateCatalog.roleFields,
  )
  const baseMeta = flatten(baseCatalog.meta)
  const candidateMeta = flatten(candidateCatalog.meta)
  const metadata = [...new Set([...Object.keys(baseMeta), ...Object.keys(candidateMeta)])]
    .filter((field) => baseMeta[field] !== candidateMeta[field])
    .sort(collator.compare)
    .map((field) => ({ field, before: baseMeta[field] ?? null, after: candidateMeta[field] ?? null }))
  const baseSource = flatten(baseManifest)
  const candidateSource = flatten(candidateManifest)
  const manifest = [...new Set([...Object.keys(baseSource), ...Object.keys(candidateSource)])]
    .filter((field) => baseSource[field] !== candidateSource[field])
    .sort(collator.compare)
    .map((field) => ({ field, before: baseSource[field] ?? null, after: candidateSource[field] ?? null }))

  const summary = {
    relationships: { added: relationships.added.length, removed: relationships.removed.length, changed: relationships.changed.length },
    roles: { added: roles.added.length, removed: roles.removed.length, changed: roles.changed.length },
    metadata: metadata.length,
    manifest: manifest.length,
  }
  const changeCount = Object.values(summary.relationships).reduce((sum, count) => sum + count, 0)
    + Object.values(summary.roles).reduce((sum, count) => sum + count, 0)
    + summary.metadata + summary.manifest

  return { changeCount, summary, relationships, roles, metadata, manifest }
}

const markdownValue = (value) => String(value ?? '—')
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('|', '\\|')
  .replaceAll('\n', ' ')
const changedRows = (items) => items.flatMap((item) => item.changes.map((change) => `| ${markdownValue(item.label)} | ${markdownValue(change.field)} | ${markdownValue(change.before)} | ${markdownValue(change.after)} |`))

export const renderProposalMarkdown = (proposal) => {
  const lines = [
    '# Catalog update proposal',
    '',
    `- Base capture: ${proposal.base.captured}`,
    `- Candidate capture: ${proposal.candidate.captured}`,
    `- Changes requiring review: ${proposal.diff.changeCount}`,
    `- Approval status: ${proposal.approval.status}`,
    '',
    '## Summary',
    '',
    '| Catalog | Added | Removed | Changed |',
    '|---|---:|---:|---:|',
    `| Relationships | ${proposal.diff.summary.relationships.added} | ${proposal.diff.summary.relationships.removed} | ${proposal.diff.summary.relationships.changed} |`,
    `| D/s and profile roles | ${proposal.diff.summary.roles.added} | ${proposal.diff.summary.roles.removed} | ${proposal.diff.summary.roles.changed} |`,
    '',
  ]
  for (const [label, group, labelField] of [
    ['Relationships', proposal.diff.relationships, 'Relationship term'],
    ['D/s and profile roles', proposal.diff.roles, 'Role'],
  ]) {
    lines.push(`## ${label}`, '', `Added: ${group.added.length} · Removed: ${group.removed.length} · Changed: ${group.changed.length}`, '')
    if (group.added.length) lines.push('### Added', '', ...group.added.map((row) => `- ${markdownValue(row[labelField])}`), '')
    if (group.removed.length) lines.push('### Removed', '', ...group.removed.map((row) => `- ${markdownValue(row[labelField])}`), '')
    if (group.changed.length) lines.push('### Changed fields', '', '| Label | Field | Before | After |', '|---|---|---|---|', ...changedRows(group.changed), '')
  }
  if (proposal.diff.metadata.length) lines.push('## Catalog metadata', '', '| Field | Before | After |', '|---|---|---|', ...proposal.diff.metadata.map((change) => `| ${markdownValue(change.field)} | ${markdownValue(change.before)} | ${markdownValue(change.after)} |`), '')
  if (proposal.diff.manifest.length) lines.push('## Source manifest', '', '| Field | Before | After |', '|---|---|---|', ...proposal.diff.manifest.map((change) => `| ${markdownValue(change.field)} | ${markdownValue(change.before)} | ${markdownValue(change.after)} |`), '')
  lines.push('## Promotion', '', 'Promotion is intentionally separate. Review this report, then run the promotion command with the exact candidate files, this proposal, and `--approve PROMOTE`.', '')
  return lines.join('\n')
}

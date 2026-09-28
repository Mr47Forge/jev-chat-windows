import { readdir, readFile } from 'node:fs/promises'
import { extname, join, resolve } from 'node:path'
import { parseArgs } from 'node:util'

const loadJson = async (path) => JSON.parse(await readFile(path, 'utf8'))
const { values } = parseArgs({ options: {
  catalog: { type: 'string', default: 'src/data/catalog.json' },
  discovery: { type: 'string', default: 'src/data/discovery-terms.json' },
  manifest: { type: 'string', default: 'src/data/source-manifest.json' },
} })
const catalogPath = resolve(values.catalog)
const discoveryPath = resolve(values.discovery)
const manifestPath = resolve(values.manifest)
const catalog = await loadJson(catalogPath)
const discovery = await loadJson(discoveryPath)
const sourceManifest = await loadJson(manifestPath)
const failures = []
const assert = (condition, message) => { if (!condition) failures.push(message) }

const RELATIONSHIP_FIELDS = [
  'Relationship term',
  'Classification',
  'Catalog presence',
  'Partner-side label',
  'Pairing confidence',
  'Pairing rule',
  'FetLife excerpt',
  'Definition basis',
  'Source',
]
const ROLE_FIELDS = [
  'Role',
  'FetLife category',
  'Catalog presence',
  'Authority axis',
  'Activity axis',
  'Relationship-role axis',
  'Partner-side label',
  'Pairing confidence',
  'Pairing rule',
  'Partner label in catalog?',
  'FetLife excerpt',
  'Definition basis',
  'Source',
]
const OFFICIAL_BASIS = 'Official FetLife excerpt (≤24 words)'
const NO_DEFINITION_BASIS = 'No platform definition captured'
const FORBIDDEN_PROFILE_FIELD = /^(?:user(?:name|_name)?|member(?:Id|_id)?|handle|account(?:Id|_id)?|profile(?:Id|_id|Url|_url|Name|_name|Username|_username)?|linkedProfile.*)$/i

const arraysEqual = (left, right) => left.length === right.length && left.every((value, index) => value === right[index])

assert(catalog.schemaVersion === 2, 'catalog schemaVersion must be 2')
assert(discovery.schemaVersion === 1, 'discovery schemaVersion must be 1')
assert(sourceManifest.schemaVersion === 1, 'source manifest schemaVersion must be 1')
assert(/^\d{4}-\d{2}-\d{2}$/.test(catalog.meta?.captured ?? ''), 'catalog capture date must be ISO YYYY-MM-DD')
assert(/^\d{4}-\d{2}-\d{2}$/.test(discovery.captured ?? ''), 'discovery capture date must be ISO YYYY-MM-DD')
assert(/^\d{4}-\d{2}-\d{2}$/.test(sourceManifest.captured ?? ''), 'source manifest capture date must be ISO YYYY-MM-DD')
assert(/^\d{4}-\d{2}-\d{2}$/.test(sourceManifest.verified ?? ''), 'source manifest verification date must be ISO YYYY-MM-DD')
assert(sourceManifest.captured === catalog.meta.captured, 'source manifest and catalog capture dates must match')
assert(sourceManifest.verified >= sourceManifest.captured, 'source manifest verification date precedes its capture date')
assert(arraysEqual(catalog.relationshipFields ?? [], RELATIONSHIP_FIELDS), 'relationship schema contains unexpected, missing, or reordered fields')
assert(arraysEqual(catalog.roleFields ?? [], ROLE_FIELDS), 'role schema contains unexpected, missing, or reordered fields')
assert(![...(catalog.relationshipFields ?? []), ...(catalog.roleFields ?? [])].some((field) => FORBIDDEN_PROFILE_FIELD.test(field)), 'catalog schema contains a forbidden local-profile field')

const inflate = (rows, fields, label) => rows.map((row, index) => {
  assert(row.length === fields.length, `${label} row ${index + 1} has ${row.length} values; expected ${fields.length}`)
  return Object.fromEntries(fields.map((field, fieldIndex) => [field, row[fieldIndex]]))
})

const relationships = inflate(catalog.relationships, catalog.relationshipFields, 'relationship')
const roles = inflate(catalog.roles, catalog.roleFields, 'role')
assert(relationships.length === catalog.meta.relationshipCount, 'relationship count does not match metadata')
assert(roles.length === catalog.meta.roleCount, 'role count does not match metadata')

const relationshipMenuRows = relationships.filter((item) => item['Catalog presence'].includes('Authenticated Add Relationship menu'))
const dsMenuRows = roles.filter((item) => item['Catalog presence'].includes('Authenticated D/s relationship menu'))
assert(Number.isInteger(catalog.meta.relationshipMenuCount) && catalog.meta.relationshipMenuCount > 0, 'authenticated Add Relationship menu count must be a positive integer')
assert(Number.isInteger(catalog.meta.dsMenuCount) && catalog.meta.dsMenuCount > 0, 'authenticated Add D/s Relationship menu count must be a positive integer')
assert(relationshipMenuRows.length === catalog.meta.relationshipMenuCount, 'relationship menu membership does not match menu metadata')
assert(dsMenuRows.length === catalog.meta.dsMenuCount, 'D/s menu membership does not match menu metadata')
assert(catalog.meta.relationshipMenuCount < relationships.length, 'relationship menu count must remain distinct from the expanded relationship union')
assert(catalog.meta.dsMenuCount < roles.length, 'D/s menu count must remain distinct from the expanded role union')

const manifestSources = sourceManifest.sources ?? {}
const manifestCatalogs = sourceManifest.catalogs ?? {}
assert(manifestSources.authenticatedSettings?.relationshipMenu?.count === catalog.meta.relationshipMenuCount, 'source manifest relationship menu count does not match catalog metadata')
assert(manifestSources.authenticatedSettings?.dsMenu?.count === catalog.meta.dsMenuCount, 'source manifest D/s menu count does not match catalog metadata')
assert(manifestSources.relationshipKinktionary?.count === catalog.meta.relationshipKinktionaryCount, 'source manifest relationship Kinktionary count does not match catalog metadata')
assert(manifestSources.roleKinktionary?.count === catalog.meta.kinktionaryRoleCount, 'source manifest role Kinktionary count does not match catalog metadata')
assert(manifestSources.publicSelector?.count === catalog.meta.selectorRoleCount, 'source manifest public selector count does not match catalog metadata')
assert(manifestCatalogs.relationshipUnion === relationships.length, 'source manifest relationship union count does not match catalog')
assert(manifestCatalogs.roleUnion === roles.length, 'source manifest role union count does not match catalog')
assert(manifestCatalogs.officialRelationshipExcerpts === catalog.meta.officialRelationshipDefinitions, 'source manifest relationship excerpt count does not match catalog metadata')
assert(manifestCatalogs.officialRoleExcerpts === catalog.meta.officialRoleDefinitions, 'source manifest role excerpt count does not match catalog metadata')

const sha256 = /^[a-f0-9]{64}$/
assert(sha256.test(manifestSources.authenticatedSettings?.relationshipMenu?.normalizedOrderSha256 ?? ''), 'relationship menu capture hash must be lowercase SHA-256')
assert(sha256.test(manifestSources.authenticatedSettings?.dsMenu?.normalizedOrderSha256 ?? ''), 'D/s menu capture hash must be lowercase SHA-256')
assert(/reviewed authenticated browser capture/i.test(manifestSources.authenticatedSettings?.captureMethod ?? ''), 'source manifest must identify reviewed authenticated browser capture')
assert(/no scheduled crawler/i.test(manifestSources.authenticatedSettings?.captureMethod ?? ''), 'source manifest must state that no scheduled crawler is used')

const expectedManifestUrls = new Map([
  ['authenticated settings', [manifestSources.authenticatedSettings?.url, '/settings/profile/relationships']],
  ['relationship Kinktionary', [manifestSources.relationshipKinktionary?.url, '/kinktionary/relationships-cfhsp']],
  ['role Kinktionary', [manifestSources.roleKinktionary?.url, '/kinktionary/roles-aschp']],
  ['public selector', [manifestSources.publicSelector?.url, '/join']],
  ['Kinktionary license', [sourceManifest.license?.url, '/kinktionary/license-zcfzz']],
  ['Terms of Use', [sourceManifest.terms?.url, '/legal/terms-of-use-hwfvu']],
])
for (const [label, [value, expectedPath]] of expectedManifestUrls) {
  try {
    const source = new URL(value)
    assert(source.protocol === 'https:' && source.hostname === 'fetlife.com' && source.pathname === expectedPath, `source manifest has an unexpected ${label} URL`)
  } catch {
    assert(false, `source manifest has a malformed ${label} URL`)
  }
}
assert(/noncommercial educational use/i.test(sourceManifest.license?.scope ?? ''), 'source manifest license scope must remain noncommercial and educational')
assert(/truncated.+24 words/i.test(sourceManifest.license?.changes ?? ''), 'source manifest must disclose excerpt truncation as a change')
assert(/separate editorial additions/i.test(sourceManifest.license?.changes ?? ''), 'source manifest must distinguish Atlas editorial additions')
assert(/not declared by fetlife/i.test(sourceManifest.pairingAuthority ?? ''), 'source manifest must distinguish Atlas pairing suggestions from FetLife facts')
assert(/exclude.+profile names.+identifiers.+session data/i.test(sourceManifest.privacy ?? ''), 'source manifest must state its public-artifact privacy boundary')

const validateUnique = (items, key, label) => {
  const seen = new Set()
  for (const item of items) {
    const value = String(item[key] ?? '').trim()
    assert(Boolean(value), `${label} contains a blank label`)
    const normalized = value.toLocaleLowerCase('en')
    assert(!seen.has(normalized), `${label} contains duplicate label: ${value}`)
    seen.add(normalized)
  }
}

validateUnique(relationships, 'Relationship term', 'relationships')
validateUnique(roles, 'Role', 'roles')

const catalogSources = [
  ...relationships.map((item) => item.Source),
  ...roles.map((item) => item.Source),
]
for (const value of catalogSources) {
  try {
    const source = new URL(value)
    assert(source.protocol === 'https:' && source.hostname === 'fetlife.com', `invalid catalog source: ${value}`)
  } catch {
    assert(false, `malformed catalog source: ${value}`)
  }
}

const validateDefinitionEvidence = (items, type) => {
  const canonicalPrefix = type === 'relationship' ? '/kinktionary/relationships/' : '/kinktionary/roles/'
  let officialCount = 0

  for (const item of items) {
    const name = item[type === 'relationship' ? 'Relationship term' : 'Role']
    const definition = String(item['FetLife excerpt'] ?? '').trim()
    const basis = String(item['Definition basis'] ?? '').trim()
    const presence = String(item['Catalog presence'] ?? '')
    const official = basis === OFFICIAL_BASIS
    const adapted = basis.startsWith('Adapted')

    assert(official || adapted || basis === NO_DEFINITION_BASIS, `${type} has an unsupported definition basis: ${name}`)
    assert(!(adapted && /official|verbatim/i.test(basis)), `${type} adapted text is mislabeled as official or verbatim: ${name}`)
    assert(official || !/official|verbatim/i.test(basis), `${type} non-official text claims official or verbatim status: ${name}`)

    if (official || adapted) {
      let source
      try {
        source = new URL(item.Source)
      } catch {
        source = null
      }
      assert(Boolean(definition), `${type} sourced definition is blank: ${name}`)
      assert(presence.includes('Kinktionary'), `${type} sourced definition lacks Kinktionary capture presence: ${name}`)
      assert(source?.hostname === 'fetlife.com' && source.pathname.startsWith(canonicalPrefix), `${type} sourced definition lacks canonical Kinktionary page evidence: ${name}`)
      if (official) {
        officialCount += 1
        assert(definition.split(/\s+/u).length <= 24, `${type} official excerpt exceeds 24 words: ${name}`)
      }
    } else {
      assert(!definition, `${type} with no captured definition contains definition text: ${name}`)
    }
  }

  return officialCount
}

const officialRelationshipDefinitions = validateDefinitionEvidence(relationships, 'relationship')
const officialRoleDefinitions = validateDefinitionEvidence(roles, 'role')
assert(officialRelationshipDefinitions === catalog.meta.officialRelationshipDefinitions, 'official relationship definition count does not match metadata')
assert(officialRoleDefinitions === catalog.meta.officialRoleDefinitions, 'official role definition count does not match metadata')

const allNames = [
  ...relationships.map((item) => item['Relationship term']),
  ...roles.map((item) => item.Role),
]
const names = new Set(allNames)
const nameCounts = new Map()
for (const name of allNames) nameCounts.set(name, (nameCounts.get(name) ?? 0) + 1)
const discoveryTargets = new Set()
for (const entry of discovery.entries ?? []) {
  assert(names.has(entry.target), `discovery target is not in the catalog: ${entry.target}`)
  assert(nameCounts.get(entry.target) === 1, `discovery target is ambiguous across catalogs: ${entry.target}`)
  assert(!discoveryTargets.has(entry.target), `duplicate discovery target: ${entry.target}`)
  discoveryTargets.add(entry.target)
  assert(Array.isArray(entry.terms) && entry.terms.length > 0, `discovery target has no terms: ${entry.target}`)
  assert(new Set(entry.terms.map((term) => term.toLocaleLowerCase('en'))).size === entry.terms.length, `duplicate discovery term for: ${entry.target}`)
  assert(Boolean(entry.basis), `discovery target has no basis: ${entry.target}`)
  assert(Array.isArray(entry.sources) && entry.sources.length > 0, `discovery target has no sources: ${entry.target}`)
  for (const value of entry.sources ?? []) {
    try {
      const source = new URL(value)
      assert(source.protocol === 'https:', `discovery source is not HTTPS: ${value}`)
    } catch {
      assert(false, `malformed discovery source: ${value}`)
    }
  }
}

const publicTextFiles = new Set([catalogPath, discoveryPath, manifestPath])
const publicRoots = ['src', 'public', 'docs', 'tests', 'scripts']
const textExtensions = new Set(['.html', '.js', '.jsx', '.json', '.md', '.mjs', '.py', '.svg', '.webmanifest'])
const collectTextFiles = async (path) => {
  for (const entry of await readdir(path, { withFileTypes: true })) {
    const target = join(path, entry.name)
    if (entry.isDirectory()) await collectTextFiles(target)
    else if (textExtensions.has(extname(entry.name))) publicTextFiles.add(target)
  }
}
for (const root of publicRoots) await collectTextFiles(root)
for (const path of ['README.md', 'AGENTS.md', 'index.html']) publicTextFiles.add(path)

const privateProfileUrl = /https?:\/\/(?:www\.)?fetlife\.com\/(?:users?|members?|profiles?)\//i
const privateProfileKey = /["'](?:user(?:name|_name)?|member(?:Id|_id)?|handle|account(?:Id|_id)?|profile(?:Id|_id|Url|_url|Name|_name|Username|_username)?|linkedProfile[^"']*)["']\s*:/i
const usernameLikeLiteral = /(["'`])([A-Za-z0-9][A-Za-z0-9-]{1,31}_[A-Za-z0-9_-]{1,31})\1(?!\s*:)/
for (const path of publicTextFiles) {
  const content = await readFile(path, 'utf8')
  assert(!privateProfileUrl.test(content), `public artifact contains a member/profile URL: ${path}`)
  assert(!privateProfileKey.test(content), `public artifact contains a forbidden local-profile field: ${path}`)
  assert(!usernameLikeLiteral.test(content), `public artifact contains a username-like literal: ${path}`)
}

if (failures.length) {
  console.error(`Catalog validation failed (${failures.length})`)
  for (const failure of failures) console.error(`- ${failure}`)
  process.exitCode = 1
} else {
  console.log(`Catalog validation passed: ${catalog.meta.relationshipMenuCount}/${catalog.meta.dsMenuCount} selectable menu choices; ${relationships.length}/${roles.length} union entries; ${discovery.entries.length} discovery mappings.`)
}

import raw from './data/catalog.json'

const normalize = (value) => String(value ?? '').trim()

const slug = (value) => {
  const normalized = normalize(value).toLocaleLowerCase()
  const readable = normalized.replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'label'
  let hash = 2166136261
  for (const character of normalized) hash = Math.imul(hash ^ character.codePointAt(0), 16777619)
  return `${readable}-${(hash >>> 0).toString(36)}`
}

const inflateRows = (rows, fields) => rows.map((row) => Object.fromEntries(fields.map((field, index) => [field, row[index]])))
const rawRelationships = raw.schemaVersion === 2 ? inflateRows(raw.relationships, raw.relationshipFields) : raw.relationships
const rawRoles = raw.schemaVersion === 2 ? inflateRows(raw.roles, raw.roleFields) : raw.roles

export const pairingAuthority = Object.freeze({
  kind: 'atlas-interpretation',
  label: 'Relationship Atlas interpretation',
  source: 'Relationship Atlas pairing rules',
  platformDeclared: false,
  disclosure: 'Partner-side mappings are Atlas suggestions, not FetLife-declared reciprocal relationships.',
})

const definitionAuthorityLabel = (basis, definition) => {
  if (!definition) return 'No platform definition captured'
  if (/adapted|summary/i.test(basis)) return 'Relationship Atlas adapted summary'
  if (/official|verbatim/i.test(basis)) return 'FetLife source excerpt'
  return 'Captured source material'
}

const relationshipItems = rawRelationships.map((item, index) => ({
  id: `relationship-${slug(item['Relationship term'])}`,
  legacyId: `relationship-${index}`,
  type: 'relationship',
  name: normalize(item['Relationship term']),
  category: normalize(item.Classification),
  presence: normalize(item['Catalog presence']),
  authority: 'None',
  activity: 'None',
  relationshipAxis: normalize(item.Classification),
  partner: normalize(item['Partner-side label']),
  confidence: normalize(item['Pairing confidence']),
  rule: normalize(item['Pairing rule']),
  partnerFound: item['Partner-side label'] === 'Not applicable'
    ? 'Not applicable'
    : item['Pairing confidence'] === 'Exact reciprocal'
      ? 'Yes'
      : 'Review by partner',
  definition: normalize(item['FetLife excerpt']),
  basis: normalize(item['Definition basis']),
  source: normalize(item.Source),
  definitionAuthority: definitionAuthorityLabel(item['Definition basis'], item['FetLife excerpt']),
  pairingAuthority: pairingAuthority.label,
  pairingSource: pairingAuthority.source,
}))

const roleItems = rawRoles.map((item, index) => ({
  id: `role-${slug(item.Role)}`,
  legacyId: `role-${index}`,
  type: 'role',
  name: normalize(item.Role),
  category: normalize(item['FetLife category']),
  presence: normalize(item['Catalog presence']),
  authority: normalize(item['Authority axis']),
  activity: normalize(item['Activity axis']),
  relationshipAxis: normalize(item['Relationship-role axis']),
  partner: normalize(item['Partner-side label']),
  confidence: normalize(item['Pairing confidence']),
  rule: normalize(item['Pairing rule']),
  partnerFound: normalize(item['Partner label in catalog?']),
  definition: normalize(item['FetLife excerpt']),
  basis: normalize(item['Definition basis']),
  source: normalize(item.Source),
  definitionAuthority: definitionAuthorityLabel(item['Definition basis'], item['FetLife excerpt']),
  pairingAuthority: pairingAuthority.label,
  pairingSource: pairingAuthority.source,
}))

const withSearch = (items) => items.map((item) => ({
  ...item,
  searchText: [item.name, item.category, item.partner, item.definition, item.authority, item.activity, item.relationshipAxis]
    .join(' ')
    .toLocaleLowerCase(),
}))

export const relationships = withSearch(relationshipItems)
export const roles = withSearch(roleItems)
export const allItems = [...relationships, ...roles]
export const meta = raw.meta

const normalizeKey = (value) => normalize(value).toLocaleLowerCase()
const noCounterpartLabels = new Set([
  'no fixed reciprocal',
  'partner chooses independently',
  'not applicable',
  'no single counterpart',
])

export const findPartnerItem = (item, catalog = allItems) => {
  if (!item || noCounterpartLabels.has(normalizeKey(item.partner))) return null
  const target = normalizeKey(item.partner)
  return catalog.find((candidate) => candidate.type === item.type && normalizeKey(candidate.name) === target)
    ?? null
}

export const pairCorrelation = (item, catalog = allItems) => {
  const partnerItem = findPartnerItem(item, catalog)
  const targetIsTerminal = noCounterpartLabels.has(normalizeKey(item?.partner))
  const openChoice = ['partner-preferred reciprocal label', 'partner chooses independently'].includes(normalizeKey(item?.partner))
  const candidateSet = item?.partnerFound === 'Yes—choose one'
  const returnsToOrigin = Boolean(partnerItem && normalizeKey(partnerItem.partner) === normalizeKey(item.name))
  const sharedLabel = Boolean(partnerItem && normalizeKey(partnerItem.name) === normalizeKey(item.name))
  const mutuallyExact = Boolean(returnsToOrigin && internalPairTier(item.confidence) === 'exact' && internalPairTier(partnerItem.confidence) === 'exact')
  const mutualConvention = Boolean(returnsToOrigin && internalPairTier(item.confidence) === 'strong' && internalPairTier(partnerItem.confidence) === 'strong')
  const direction = openChoice ? 'open-choice' : targetIsTerminal ? 'none' : candidateSet ? 'candidate-set' : sharedLabel ? 'symmetric' : mutuallyExact ? 'reciprocal' : mutualConvention ? 'mutual-convention' : partnerItem ? 'linked' : 'recommended'
  const catalogState = openChoice
    ? 'Partner chooses a label independently'
    : targetIsTerminal
      ? 'The Atlas does not suggest a fixed counterpart'
      : candidateSet
        ? 'The Atlas identifies multiple candidates; choose one together'
        : sharedLabel
          ? 'The Atlas maps the same captured label to both partners'
          : mutuallyExact
            ? 'The Atlas maps both captured labels to each other'
            : mutualConvention
              ? 'The Atlas maps the labels back to each other as a common convention'
              : returnsToOrigin
                ? 'The Atlas mappings return to each other, but their recorded rules do not establish the same structural state'
                : partnerItem
                  ? 'The Atlas suggestion is present as a captured catalog label'
                  : 'The Atlas suggestion is not a separate captured catalog entry'
  return {
    partnerItem,
    returnsToOrigin,
    sharedLabel,
    openChoice,
    candidateSet,
    direction,
    catalogState,
    pairingAuthority: pairingAuthority.label,
    pairingSource: pairingAuthority.source,
    platformDeclared: pairingAuthority.platformDeclared,
    authorityDisclosure: pairingAuthority.disclosure,
    ...pairStateCopy[direction],
  }
}

export const resolvedPartnerLabel = (item, catalog = allItems) => {
  const correlation = pairCorrelation(item, catalog)
  return correlation.partnerItem && !correlation.openChoice && !correlation.candidateSet ? item.partner : ''
}

export const partnerDisplayLabel = (item, catalog = allItems) => {
  const correlation = pairCorrelation(item, catalog)
  if (correlation.openChoice) return 'Partner chooses their own label'
  if (correlation.direction === 'none') return 'No fixed partner label'
  return item.partner
}

export const finalPartnerChoice = (decision, finalLabel) => decision === 'Use' ? normalize(finalLabel) : ''

export const itemAxes = (item) => [
  { key: 'authority', label: 'Authority', value: item?.authority || 'None' },
  { key: 'activity', label: 'Activity', value: item?.activity || 'None' },
  { key: 'relationship', label: 'Relationship role', value: item?.relationshipAxis || 'None' },
]

export const sourceMemberships = (item) => {
  const value = normalizeKey(item?.presence)
  const common = [{ label: 'Kinktionary', present: value.includes('kinktionary') }]
  if (item?.type === 'relationship') return [...common, { label: 'Authenticated Add Relationship menu', present: value.includes('authenticated') }]
  return [
    ...common,
    { label: 'Public join selector', present: value.includes('public join selector') },
    { label: 'Authenticated D/s relationship menu', present: value.includes('authenticated') },
  ]
}

const internalPairTier = (confidence) => {
  const value = confidence.toLocaleLowerCase()
  if (value.includes('exact')) return 'exact'
  if (value.includes('strong') || value.includes('usually symmetric')) return 'strong'
  if (value.includes('context') || value.includes('depends')) return 'context'
  if (value.includes('none') || value.includes('not a reciprocal')) return 'none'
  return 'neutral'
}

const pairStateCopy = {
  reciprocal: {
    structureLabel: 'Atlas two-way pair suggestion',
    structureSummary: 'The Atlas links the selected label to one captured label, and its Atlas mapping returns to the selected label.',
    resolutionLabel: 'One Atlas-suggested catalog target',
    decisionLabel: 'Confirm both labels',
    decisionDetail: 'The Atlas resolves a two-way suggestion; the people involved still decide whether both labels and their meanings fit.',
    visualTone: 'resolved',
  },
  symmetric: {
    structureLabel: 'Atlas shared-label relationship',
    structureSummary: 'The Atlas suggests the same captured label for both sides of the relationship.',
    resolutionLabel: 'One Atlas-suggested shared label',
    decisionLabel: 'Confirm the shared meaning',
    decisionDetail: 'A shared label does not guarantee that both people attach the same meaning, scope, or expectations to it.',
    visualTone: 'resolved',
  },
  'mutual-convention': {
    structureLabel: 'Atlas two-way convention',
    structureSummary: 'The Atlas maps the selected and partner-side labels back to each other as a common naming convention.',
    resolutionLabel: 'One returning Atlas suggestion',
    decisionLabel: 'Confirm that the convention applies',
    decisionDetail: 'The returning pattern is a naming convention, not a requirement that either person adopt the suggested label.',
    visualTone: 'linked',
  },
  linked: {
    structureLabel: 'Atlas related-label suggestion',
    structureSummary: 'The Atlas links the selected label to a captured partner-side label, but its Atlas mapping does not return to the selected label.',
    resolutionLabel: 'One Atlas-suggested catalog target',
    decisionLabel: 'Review the reverse meaning',
    decisionDetail: 'Use the forward link as a reference only; do not infer that the partner-side label means the reverse relationship.',
    visualTone: 'linked',
  },
  recommended: {
    structureLabel: 'Atlas partner-label suggestion',
    structureSummary: 'The Atlas suggests a partner-side label, but it is not a separate entry in the same captured catalog.',
    resolutionLabel: 'Target not independently captured',
    decisionLabel: 'Choose the final label together',
    decisionDetail: 'Because the target cannot be cross-checked as its own catalog entry, leave the final partner label open to agreement.',
    visualTone: 'unresolved',
  },
  'candidate-set': {
    structureLabel: 'Atlas partner-label options',
    structureSummary: 'The Atlas identifies several possible partner-side labels rather than one resolved counterpart.',
    resolutionLabel: 'Multiple possible targets',
    decisionLabel: 'Select one—or none—together',
    decisionDetail: 'No candidate is auto-selected. Context and the partner’s own language determine whether any candidate fits.',
    visualTone: 'choice',
  },
  'open-choice': {
    structureLabel: 'Partner choice left open',
    structureSummary: 'The Atlas does not prescribe a partner-side label for the selected label.',
    resolutionLabel: 'No preselected target',
    decisionLabel: 'Partner names their own label',
    decisionDetail: 'The partner-side field remains blank until that person chooses or agrees to a label.',
    visualTone: 'choice',
  },
  none: {
    structureLabel: 'No fixed Atlas counterpart',
    structureSummary: 'The Atlas does not define a single partner-side counterpart for this label.',
    resolutionLabel: 'No target to resolve',
    decisionLabel: 'Do not infer a partner label',
    decisionDetail: 'Use the selected label on its own unless the people involved explicitly agree on additional language.',
    visualTone: 'unresolved',
  },
}

export const pairContext = (item, catalog = allItems) => {
  const correlation = pairCorrelation(item, catalog)
  const sourceCount = sourceMemberships(item).filter((source) => source.present).length
  const scopeValue = item.type === 'role' ? 'D/s and profile-role axes' : 'Relationship classification'
  const scopeDetail = item.type === 'role'
    ? 'Authority, activity, and relationship-role values are independent descriptors. A value on one axis does not determine the others.'
    : 'Role-axis interpretations are not applied to relationship labels; only the captured relationship classification is shown.'
  return [
    { key: 'structure', label: 'Atlas pairing structure', value: correlation.structureLabel, detail: correlation.structureSummary },
    { key: 'resolution', label: 'Target resolution', value: correlation.resolutionLabel, detail: correlation.catalogState },
    { key: 'scope', label: 'Interpretation scope', value: scopeValue, detail: scopeDetail },
    { key: 'decision', label: 'Partner decision', value: correlation.decisionLabel, detail: correlation.decisionDetail },
    { key: 'provenance', label: 'Authority and sources', value: `${sourceCount} captured ${sourceCount === 1 ? 'source' : 'sources'}`, detail: `${item.definitionAuthority}. Pairing authority: ${item.pairingAuthority}; not declared by FetLife.` },
  ]
}

export const uniqueSorted = (items, field) => [...new Set(items.map((item) => item[field]).filter(Boolean))]
  .sort((a, b) => a.localeCompare(b))

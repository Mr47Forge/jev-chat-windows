import discoveryTerms from './data/discovery-terms.json'

const collator = new Intl.Collator('en', { numeric: true, sensitivity: 'base' })
const MAX_QUERY_LENGTH = 120
const MAX_QUERY_TOKENS = 16

const FIELD_WEIGHTS = {
  label: 12,
  alias: 10,
  partner: 9,
  type: 8,
  category: 7,
  axis: 6,
  pair: 5,
  source: 4,
  definition: 2,
}

const COMMUNITY_ALIASES = Object.fromEntries(discoveryTerms.entries.map((entry) => [entry.target, entry.terms]))

const TYPE_VOCABULARY = {
  relationship: ['relationship', 'relationships', 'relationship label', 'relationship type'],
  role: ['role', 'roles', 'profile role', 'profile roles', 'D/s role', 'D/s relationship', 'DS role', 'dynamic'],
}

export const normalizeSearchText = (value) => String(value ?? '')
  .normalize('NFKD')
  .replace(/\p{M}/gu, '')
  .toLocaleLowerCase('en')
  .replace(/[’‘`]/g, "'")
  .replace(/\b([a-z])\s*\/\s*([a-z])\b/g, '$1$2')
  .replace(/&/g, ' and ')
  .replace(/['’]/g, '')
  .replace(/[^a-z0-9]+/g, ' ')
  .trim()
  .replace(/\s+/g, ' ')

const unique = (values) => [...new Set(values.filter(Boolean))]

const buildField = (key, label, values, compactable = true) => {
  const normalizedValues = unique(values.map(normalizeSearchText))
  const normalized = normalizedValues.join(' ')
  const words = normalized.split(' ').filter(Boolean)
  const compact = compactable
    ? normalizedValues.filter((value) => value.includes(' ') && value.length <= 48).map((value) => value.replace(/\s/g, ''))
    : []
  return {
    key,
    label,
    weight: FIELD_WEIGHTS[key],
    normalized,
    tokens: unique([...words, ...compact]),
  }
}

const maxEditDistance = (length) => {
  if (length < 3) return 0
  if (length <= 5) return 1
  if (length <= 9) return 2
  return 3
}

// Bounded optimal-string-alignment distance. Returning max + 1 lets callers
// stop considering a token without exposing an unstable similarity percentage.
const boundedDistance = (left, right, max) => {
  if (Math.abs(left.length - right.length) > max) return max + 1
  const previous = Array.from({ length: right.length + 1 }, (_, index) => index)
  let previousPrevious = null

  for (let i = 1; i <= left.length; i += 1) {
    const current = [i]
    let rowMinimum = current[0]
    for (let j = 1; j <= right.length; j += 1) {
      const substitution = previous[j - 1] + (left[i - 1] === right[j - 1] ? 0 : 1)
      let value = Math.min(previous[j] + 1, current[j - 1] + 1, substitution)
      if (previousPrevious && i > 1 && j > 1 && left[i - 1] === right[j - 2] && left[i - 2] === right[j - 1]) {
        value = Math.min(value, previousPrevious[j - 2] + 1)
      }
      current[j] = value
      rowMinimum = Math.min(rowMinimum, value)
    }
    if (rowMinimum > max) return max + 1
    previousPrevious = previous.slice()
    for (let j = 0; j < current.length; j += 1) previous[j] = current[j]
  }
  return previous[right.length]
}

const tokenMatch = (queryToken, candidate) => {
  if (queryToken === candidate) return 100
  if (queryToken.length >= 2 && candidate.startsWith(queryToken)) return 88 - Math.min(12, candidate.length - queryToken.length)
  if (queryToken.length >= 3 && candidate.includes(queryToken)) return 72 - Math.min(12, candidate.length - queryToken.length)
  const limit = maxEditDistance(queryToken.length)
  if (!limit) return 0
  const distance = boundedDistance(queryToken, candidate, limit)
  return distance <= limit ? 64 - (distance * 9) - Math.min(8, Math.abs(candidate.length - queryToken.length)) : 0
}

const phraseMatch = (query, field) => {
  if (!query) return 0
  if (query === field.normalized) return 150
  if (field.normalized.startsWith(query)) return 128
  if (field.normalized.includes(query)) return 108
  const compactQuery = query.replace(/\s/g, '')
  if (compactQuery.length >= 3 && field.tokens.includes(compactQuery)) return 118
  return 0
}

export const createSearchIndex = (items, correlationMap) => items.map((item) => {
  const correlation = correlationMap.get(item.id)
  return {
    item,
    fields: [
      buildField('label', 'Label', [item.name]),
      buildField('alias', 'Related term', COMMUNITY_ALIASES[item.name] ?? []),
      buildField('partner', 'Partner label', [item.partner]),
      buildField('type', 'Catalog type', TYPE_VOCABULARY[item.type] ?? [item.type]),
      buildField('category', item.type === 'role' ? 'Role type' : 'Relationship type', [item.category]),
      buildField('axis', 'Role axis', [item.authority, item.activity, item.relationshipAxis]),
      buildField('pair', 'Pair structure', [correlation?.structureLabel, correlation?.catalogState, correlation?.decisionLabel]),
      buildField('source', 'Source membership', [item.presence]),
      buildField('definition', 'Definition', [item.definition], false),
    ].filter((field) => field.normalized),
  }
})

const rankDocument = (document, normalizedQuery, queryTokens) => {
  let score = 0
  let strongest = null
  const matchedFields = []

  for (const field of document.fields) {
    const phrase = phraseMatch(normalizedQuery, field)
    const weighted = phrase * field.weight
    if (weighted > (strongest?.score ?? 0)) strongest = { score: weighted, fieldLabel: field.label }
    if (weighted) matchedFields.push(field.label)
    score += weighted
  }

  for (const queryToken of queryTokens) {
    let tokenBest = null
    for (const field of document.fields) {
      for (const candidate of field.tokens) {
        const weighted = tokenMatch(queryToken, candidate) * field.weight
        if (weighted > (tokenBest?.score ?? 0)) tokenBest = { score: weighted, fieldLabel: field.label }
      }
    }
    if (!tokenBest?.score) return null
    score += tokenBest.score
    matchedFields.push(tokenBest.fieldLabel)
    if (tokenBest.score > (strongest?.score ?? 0)) strongest = tokenBest
  }

  const orderedFields = unique([strongest?.fieldLabel, ...matchedFields])
  return { item: document.item, score, match: { fieldLabels: orderedFields.length ? orderedFields : ['Catalog text'] } }
}

export const searchCatalog = (index, query) => {
  const normalizedQuery = normalizeSearchText(query).slice(0, MAX_QUERY_LENGTH)
  if (!normalizedQuery) return index.map(({ item }) => ({ item, score: 0, match: null }))
  const queryTokens = unique(normalizedQuery.split(' ').filter(Boolean)).slice(0, MAX_QUERY_TOKENS)
  return index
    .map((document) => rankDocument(document, normalizedQuery, queryTokens))
    .filter(Boolean)
    .sort((left, right) => right.score - left.score
      || collator.compare(left.item.name, right.item.name)
      || collator.compare(left.item.id, right.item.id))
}

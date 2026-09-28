import { describe, expect, it } from 'vitest'
import { allItems, meta, pairContext, pairCorrelation, relationships, resolvedPartnerLabel, roles } from './catalog'
import { neutralizeSpreadsheetFormula } from './csv'
import { createSearchIndex, normalizeSearchText, searchCatalog } from './search'

describe('catalog integrity', () => {
  it('distinguishes the selectable menus from the expanded union catalogs', () => {
    expect(relationships).toHaveLength(161)
    expect(roles).toHaveLength(1202)
    expect(meta.relationshipKinktionaryCount).toBe(137)
    expect(meta.relationshipMenuCount).toBe(73)
    expect(meta.dsMenuCount).toBe(606)
    expect(meta.kinktionaryRoleCount).toBe(955)
    expect(meta.selectorRoleCount).toBe(813)
    expect(meta.officialRelationshipDefinitions).toBe(84)
    expect(meta.officialRoleDefinitions).toBe(792)
    expect(relationships.filter((item) => item.presence.includes('Authenticated Add Relationship menu'))).toHaveLength(meta.relationshipMenuCount)
    expect(roles.filter((item) => item.presence.includes('Authenticated D/s relationship menu'))).toHaveLength(meta.dsMenuCount)
    expect(meta.relationshipMenuCount).toBeLessThan(relationships.length)
    expect(meta.dsMenuCount).toBeLessThan(roles.length)
  })

  it('contains unique labels and evidence-backed definition states', () => {
    expect(new Set(allItems.map((item) => item.id)).size).toBe(allItems.length)
    expect(new Set(relationships.map((item) => item.name.toLocaleLowerCase())).size).toBe(relationships.length)
    expect(new Set(roles.map((item) => item.name.toLocaleLowerCase())).size).toBe(roles.length)
    expect(allItems.every((item) => item.name && item.partner && item.source && item.basis)).toBe(true)
    for (const item of allItems) {
      const official = item.basis === 'Official FetLife excerpt (≤24 words)'
      const adapted = item.basis.startsWith('Adapted')
      if (official || adapted) {
        const source = new URL(item.source)
        expect(item.definition, `${item.name} has definition text`).toBeTruthy()
        expect(item.presence, `${item.name} has Kinktionary capture evidence`).toContain('Kinktionary')
        expect(source.pathname, `${item.name} uses its canonical definition page`).toMatch(item.type === 'relationship' ? /^\/kinktionary\/relationships\// : /^\/kinktionary\/roles\//)
      } else {
        expect(item.basis, `${item.name} has an explicit no-definition state`).toBe('No platform definition captured')
        expect(item.definition, `${item.name} does not invent a definition`).toBe('')
      }
      if (!official) expect(item.basis).not.toMatch(/official|verbatim/i)
      if (adapted) expect(item.basis).not.toMatch(/official|verbatim/i)
    }
  })

  it('includes every newly verified canonical role page', () => {
    for (const name of ['Gimp', 'God', 'Little Goddess', 'Mutha', 'Sacred Masculine', 'Submissive (Sub)']) {
      const item = roles.find((candidate) => candidate.name === name)
      expect(item, `${name} is present`).toBeTruthy()
      expect(item.presence).toContain('Kinktionary')
      expect(item.definition).toBeTruthy()
      expect(item.source).toMatch(/^https:\/\/fetlife\.com\/kinktionary\/roles\//)
    }
  })

  it('uses valid secure source URLs', () => {
    expect(allItems.every((item) => {
      const source = new URL(item.source)
      return source.protocol === 'https:' && source.hostname === 'fetlife.com'
    })).toBe(true)
  })

  it('reserves exact reciprocal for involutive named pairs', () => {
    const exact = allItems.filter((item) => item.confidence === 'Exact reciprocal')
    expect(exact.length).toBeGreaterThan(0)
    for (const item of exact) {
      const targets = allItems.filter((candidate) => candidate.type === item.type && candidate.name.toLocaleLowerCase() === item.partner.toLocaleLowerCase())
      expect(targets.length, `${item.name} target exists`).toBeGreaterThan(0)
      expect(targets.some((target) => target.partner.toLocaleLowerCase() === item.name.toLocaleLowerCase()), `${item.name} maps back`).toBe(true)
      expect(targets.some((target) => target.partner.toLocaleLowerCase() === item.name.toLocaleLowerCase() && target.confidence === 'Exact reciprocal'), `${item.name} has a mutually exact return`).toBe(true)
    }
  })

  it('distinguishes exact, open-choice, candidate-set, and mutual-convention edges', () => {
    const byName = (name, type) => allItems.find((item) => item.name === name && item.type === type)
    expect(pairCorrelation(byName('Protecting', 'relationship')).direction).toBe('reciprocal')
    expect(pairCorrelation(byName('Alterous Attraction', 'relationship')).direction).toBe('open-choice')
    expect(pairCorrelation(byName('Mad Scientist', 'role')).direction).toBe('mutual-convention')
    const candidate = roles.find((item) => item.partnerFound === 'Yes—choose one')
    expect(pairCorrelation(candidate).direction).toBe('candidate-set')
    expect(resolvedPartnerLabel(byName('Protecting', 'relationship'))).toBe('Under Protection')
    expect(resolvedPartnerLabel(byName('Alterous Attraction', 'relationship'))).toBe('')
    expect(resolvedPartnerLabel(candidate)).toBe('')
  })

  it('publishes structural explanations without exposing the internal tier', () => {
    const requiredFields = ['structureLabel', 'structureSummary', 'resolutionLabel', 'decisionLabel', 'decisionDetail', 'visualTone']
    for (const item of allItems) {
      const correlation = pairCorrelation(item)
      for (const field of requiredFields) expect(correlation[field], `${item.name} ${field}`).toBeTruthy()
      expect(correlation).not.toHaveProperty('confidence')
      expect(correlation).not.toHaveProperty('mutuallyExact')
      expect(correlation).not.toHaveProperty('mutualConvention')
      expect(pairContext(item)).toHaveLength(5)
    }
  })

  it('keeps context boundaries specific to relationship and role catalogs', () => {
    const relationshipContext = pairContext(relationships[0]).find((entry) => entry.key === 'scope')
    const roleContext = pairContext(roles[0]).find((entry) => entry.key === 'scope')
    expect(relationshipContext.detail).toContain('not applied to relationship labels')
    expect(roleContext.detail).toContain('independent descriptors')
  })

  it('publishes no local-profile fields or member/profile URLs', () => {
    const publicFields = new Set(['id', 'legacyId', 'type', 'name', 'category', 'presence', 'authority', 'activity', 'relationshipAxis', 'partner', 'confidence', 'rule', 'partnerFound', 'definition', 'basis', 'source', 'definitionAuthority', 'pairingAuthority', 'pairingSource', 'searchText'])
    for (const item of allItems) {
      expect(Object.keys(item).every((field) => publicFields.has(field)), `${item.name} contains only catalog fields`).toBe(true)
      expect(Object.keys(item).some((field) => /user|member|handle|account|profile/i.test(field)), `${item.name} contains no profile identity field`).toBe(false)
      expect(item.source, `${item.name} does not link to a member profile`).not.toMatch(/^https:\/\/(?:www\.)?fetlife\.com\/(?:users?|members?|profiles?)\//i)
    }
  })

  it('neutralizes spreadsheet formula prefixes in CSV fields', () => {
    expect(neutralizeSpreadsheetFormula('=HYPERLINK("bad")')).toBe("'=HYPERLINK(\"bad\")")
    expect(neutralizeSpreadsheetFormula('  +1+1')).toBe("'  +1+1")
    expect(neutralizeSpreadsheetFormula('Under Protection')).toBe('Under Protection')
  })
})

describe('catalog search', () => {
  const correlationMap = new Map(allItems.map((item) => [item.id, pairCorrelation(item)]))
  const index = createSearchIndex(allItems, correlationMap)
  const names = (query) => searchCatalog(index, query).map((result) => result.item.name)

  it('normalizes punctuation, diacritics, and D/s vocabulary consistently', () => {
    expect(normalizeSearchText('D/s & Profile Roles')).toBe('ds and profile roles')
    expect(normalizeSearchText('It’s Complicated')).toBe('its complicated')
    expect(normalizeSearchText('Long-Distance')).toBe('long distance')
  })

  it('ranks exact labels before contextual and definition matches', () => {
    expect(names('Protecting')[0]).toBe('Protecting')
    expect(names('Long-Distance Relationship')[0]).toBe('Long-Distance Relationship')
  })

  it('recovers stable results from realistic misspellings', () => {
    expect(names('dominnat')[0]).toBe('Dominant')
    expect(names('protectin')[0]).toBe('Protecting')
    expect(names('non monogomous')).toContain('Non-Monogamous')
  })

  it('searches catalog types, partner terms, axes, sources, and pair structure', () => {
    const relationshipOnly = searchCatalog(index, 'relationship type').map((result) => result.item)
    expect(relationshipOnly.length).toBeGreaterThan(0)
    expect(relationshipOnly[0].type).toBe('relationship')
    expect(names('Under Protection')[0]).toBe('Under Protection')
    expect(names('authenticated ds relationship')).toContain('Dominant')
    expect(names('two way pair')).toContain('Protecting')
  })

  it('resolves common community shorthand to current platform labels', () => {
    expect(names('KTP')[0]).toBe('Polyamory')
    expect(names('ENM')[0]).toBe('Ethical Non-Monogamy')
    expect(names('QPR')[0]).toBe('Queerplatonic Partner')
    expect(names('relationship escalator')[0]).toBe('Amatonormativity')
    expect(names('breed me')[0]).toBe('Breeding')
    expect(names('tasks in our dynamic')[0]).toBe('Taskmaster')
  })

  it('uses a deterministic name/id tie-breaker and keeps match metadata structural', () => {
    const first = searchCatalog(index, 'profile role').map((result) => result.item.id)
    const second = searchCatalog(index, 'profile role').map((result) => result.item.id)
    expect(second).toEqual(first)
    expect(searchCatalog(index, 'Dominant').every((result) => Object.keys(result.match).length === 1 && result.match.fieldLabels.length)).toBe(true)
  })
})

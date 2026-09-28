import { describe, expect, it } from 'vitest'
import { allItems, finalPartnerChoice, pairContext, pairCorrelation, pairingAuthority } from './catalog'

const byName = (name, type) => allItems.find((item) => item.name === name && item.type === type)

describe('pairing authority boundary', () => {
  it('identifies every pairing as an Atlas interpretation rather than a FetLife declaration', () => {
    expect(pairingAuthority.platformDeclared).toBe(false)
    expect(pairingAuthority.label).toBe('Relationship Atlas interpretation')

    for (const item of allItems) {
      const correlation = pairCorrelation(item)
      expect(item.pairingAuthority).toBe(pairingAuthority.label)
      expect(correlation.pairingAuthority).toBe(pairingAuthority.label)
      expect(correlation.pairingSource).toBe(pairingAuthority.source)
      expect(correlation.platformDeclared).toBe(false)
      expect(correlation.authorityDisclosure).toContain('not FetLife-declared')
      expect(correlation).not.toHaveProperty('confidence')
    }
  })

  it('preserves two-way, shared-label, and open-choice behavior under Atlas wording', () => {
    const twoWay = pairCorrelation(byName('Protecting', 'relationship'))
    const shared = pairCorrelation(byName('Best Friend', 'relationship'))
    const open = pairCorrelation(byName('Alterous Attraction', 'relationship'))

    expect(twoWay.direction).toBe('reciprocal')
    expect(twoWay.structureLabel).toContain('Atlas two-way')
    expect(shared.direction).toBe('symmetric')
    expect(shared.structureLabel).toContain('Atlas shared-label')
    expect(open.direction).toBe('open-choice')
    expect(open.structureLabel).toBe('Partner choice left open')
  })

  it('keeps definition sources separate from Atlas pairing authority', () => {
    const item = byName('Best Friend', 'relationship')
    const provenance = pairContext(item).find((entry) => entry.key === 'provenance')

    expect(item.definitionAuthority).toBe('FetLife source excerpt')
    expect(item.pairingSource).toBe('Relationship Atlas pairing rules')
    expect(provenance.detail).toContain('Pairing authority: Relationship Atlas interpretation')
  })

  it('keeps the final partner choice blank until Use is accepted', () => {
    expect(finalPartnerChoice('Review', 'Under Protection')).toBe('')
    expect(finalPartnerChoice('Reject', 'Under Protection')).toBe('')
    expect(finalPartnerChoice('Use', '  Under Protection  ')).toBe('Under Protection')
  })
})

import { useMemo, useState } from 'react'
import { itemAxes, pairCorrelation, sourceMemberships } from '../catalog'
import { CloseIcon, PlusIcon } from './Icons'
import { PairMap } from './VisualExplorer'

const normalize = (value) => String(value ?? '').trim().toLocaleLowerCase()

const partnerReference = (left, right) => {
  const leftToRight = normalize(left.partner) === normalize(right.name)
  const rightToLeft = normalize(right.partner) === normalize(left.name)
  return leftToRight && rightToLeft ? 'Atlas two-way reference' : leftToRight ? `Atlas: ${left.name} → ${right.name}` : rightToLeft ? `Atlas: ${right.name} → ${left.name}` : 'No direct Atlas reference'
}

const correlationChecks = (left, right, catalog) => {
  const leftPair = pairCorrelation(left, catalog)
  const rightPair = pairCorrelation(right, catalog)
  const sameType = left.type === right.type
  const bothRoles = sameType && left.type === 'role'
  const axisStatus = (field) => !sameType ? ['Not comparable across catalogs', 'neutral'] : !bothRoles ? ['Not applicable to relationships', 'neutral'] : left[field] === 'None' && right[field] === 'None' ? ['Unassigned on both', 'neutral'] : left[field] === right[field] ? ['Same recorded value', 'matches'] : ['Different recorded values', 'differs']
  const sharedSources = sourceMemberships(left).filter((source) => source.present && sourceMemberships(right).some((candidate) => candidate.label === source.label && candidate.present)).map((source) => source.label)
  const definitionStatus = left.definition && right.definition ? ['Both captured', 'matches'] : left.definition || right.definition ? ['One captured', 'neutral'] : ['Neither captured', 'neutral']
  return [
    ['Atlas partner reference', partnerReference(left, right), partnerReference(left, right) === 'Atlas two-way reference' ? 'matches' : 'neutral'],
    ['Catalog type', sameType ? `Both ${left.type}` : 'Different catalogs', 'neutral'],
    ['Category / classification', !sameType ? 'Not comparable across catalogs' : left.category === right.category ? 'Same recorded value' : 'Different recorded values', !sameType ? 'neutral' : left.category === right.category ? 'matches' : 'differs'],
    ['Authority', ...axisStatus('authority')],
    ['Activity', ...axisStatus('activity')],
    ['Relationship role', ...axisStatus('relationshipAxis')],
    ['Shared memberships', sharedSources.length ? sharedSources.join(', ') : 'None', sharedSources.length ? 'matches' : 'differs'],
    ['Definition coverage', ...definitionStatus],
    [`${left.name} structure`, leftPair.structureLabel, 'neutral'],
    [`${right.name} structure`, rightPair.structureLabel, 'neutral'],
    ['Pairing authority', leftPair.pairingAuthority === rightPair.pairingAuthority ? leftPair.pairingAuthority : 'Different authorities', 'neutral'],
    ['Interpretation boundary', !sameType ? 'Cross-catalog: compare provenance and wording only' : bothRoles ? 'Role axes remain independent descriptors' : 'Relationship classifications do not imply role axes', 'neutral'],
  ]
}

export function CompareWorkspace({ allItems, compareIds, setCompareIds }) {
  const [choice, setChoice] = useState('')
  const [activePairIds, setActivePairIds] = useState(() => compareIds.slice(0, 2))
  const itemMap = useMemo(() => new Map(allItems.map((item) => [item.id, item])), [allItems])
  const selected = compareIds.map((id) => itemMap.get(id)).filter(Boolean).slice(0, 4)
  const activeLeft = selected.find((item) => item.id === activePairIds[0]) ?? selected[0]
  const activeRight = selected.find((item) => item.id === activePairIds[1] && item.id !== activeLeft?.id) ?? selected.find((item) => item.id !== activeLeft?.id)
  const detailChecks = activeLeft && activeRight ? correlationChecks(activeLeft, activeRight, allItems) : []

  const addChoice = () => {
    const item = allItems.find((candidate) => candidate.id === choice)
    if (!item || compareIds.includes(item.id) || compareIds.length >= 4) return
    setCompareIds([...compareIds, item.id])
    setChoice('')
  }

  return (
    <main className="compare-workspace" id="main-content">
      <header className="compare-header">
        <div><h1>Compare Atlas relationships</h1><p>Align two to four labels by Atlas suggestion, taxonomy, role axes, provenance, and definition coverage. Pairings are not declared by FetLife.</p></div>
        <div className="compare-add">
          <label><span className="sr-only">Add comparison label</span><select value={choice} onChange={(event) => setChoice(event.target.value)}><option value="">Add a label…</option>{allItems.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.type}</option>)}</select></label>
          <button className="primary-button" type="button" onClick={addChoice} disabled={!choice || compareIds.length >= 4}><PlusIcon size={18} /> Add</button>
        </div>
      </header>

      {selected.length ? (
        <section className="compare-small-multiples" aria-label="Selected label fingerprints">
          {selected.map((item) => (
            <article className="comparison-column" key={item.id}>
              <button className="comparison-remove" type="button" aria-label={`Remove ${item.name} from comparison`} onClick={() => setCompareIds(compareIds.filter((id) => id !== item.id))}><CloseIcon size={17} /></button>
              <PairMap item={item} catalog={allItems} compact />
              <div className="comparison-axes">
                {item.type === 'role' ? itemAxes(item).map((axis) => <div key={axis.key}><span>{axis.label}</span><strong>{axis.value}</strong></div>) : <div><span>Classification</span><strong>{item.category}</strong></div>}
              </div>
              <div className="comparison-logic"><span>Atlas pairing structure</span><strong>{pairCorrelation(item, allItems).structureLabel}</strong></div>
              <div className="comparison-logic"><span>Partner decision</span><strong>{pairCorrelation(item, allItems).decisionLabel}</strong></div>
              <div className="comparison-source"><span>Definition</span><strong>{item.definition ? 'Verbatim excerpt captured' : 'No verbatim excerpt captured'}</strong></div>
            </article>
          ))}
        </section>
      ) : <div className="compare-empty"><h2>Add labels to begin</h2><p>Start with any relationship or D/s profile role.</p></div>}

      {selected.length >= 2 ? (
        <section className="matrix-section" aria-labelledby="matrix-title">
          <div className="section-heading-row"><h2 id="matrix-title">Atlas partner-reference matrix</h2><p>Select any cell for field-by-field detail</p></div>
          <div className="matrix-scroll">
            <table className="correlation-matrix">
              <thead><tr><th scope="col">Label</th>{selected.map((item) => <th scope="col" key={item.id}>{item.name}</th>)}</tr></thead>
              <tbody>{selected.map((rowItem) => <tr key={rowItem.id}><th scope="row">{rowItem.name}</th>{selected.map((columnItem) => {
                if (rowItem.id === columnItem.id) return <td className="matrix-diagonal" key={columnItem.id}>Selected label</td>
                const reference = partnerReference(rowItem, columnItem)
                const active = activeLeft?.id === rowItem.id && activeRight?.id === columnItem.id
                return <td className={active ? 'matrix-active' : ''} key={columnItem.id}><button type="button" aria-label={`Compare ${rowItem.name} with ${columnItem.name}`} onClick={() => setActivePairIds([rowItem.id, columnItem.id])}><strong>{reference}</strong><span>Open field detail</span></button></td>
              })}</tr>)}</tbody>
            </table>
          </div>
        </section>
      ) : null}

      {activeLeft && activeRight ? (
        <section className="correlation-ledger" aria-labelledby="correlation-ledger-title">
          <div className="ledger-heading"><div><h2 id="correlation-ledger-title">Correlation ledger</h2><p>{activeLeft.name} compared with {activeRight.name}</p></div><strong>Field-by-field catalog evidence</strong></div>
          <div className="ledger-grid">
            {detailChecks.map(([label, value, tone]) => (
              <div className={`ledger-cell ${tone}`} key={label}>
                <i aria-hidden="true">{tone === 'matches' ? '✓' : tone === 'differs' ? '—' : '·'}</i><span>{label}</span><strong>{value}</strong>
              </div>
            ))}
          </div>
          <p className="ledger-note">Atlas mappings are interpretations, not FetLife-declared reciprocal relationships. They do not measure compatibility, consent, or a required partner choice.</p>
        </section>
      ) : null}
    </main>
  )
}

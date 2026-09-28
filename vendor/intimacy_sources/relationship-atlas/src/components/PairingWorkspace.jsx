import { useMemo, useState } from 'react'
import { finalPartnerChoice, pairCorrelation, partnerDisplayLabel } from '../catalog'
import { csvCell } from '../csv'
import { DownloadIcon, PlusIcon, ShieldIcon, TrashIcon } from './Icons'

export function PairingWorkspace({ allItems, entries, onAdd, onRemove, onUpdate, onClear }) {
  const [choice, setChoice] = useState('')
  const [error, setError] = useState('')
  const itemMap = useMemo(() => new Map(allItems.map((item) => [item.id, item])), [allItems])
  const saved = entries.map((entry) => ({ ...entry, item: itemMap.get(entry.id) })).filter((entry) => entry.item)

  const addChoice = () => {
    const item = allItems.find((candidate) => candidate.id === choice)
    if (!item) {
      setError('Choose an exact catalog label from the suggestions.')
      return
    }
    onAdd(item)
    setChoice('')
    setError('')
  }

  const exportCsv = () => {
    const rows = [
      ['Your label', 'Type', 'Atlas-suggested partner label', 'Atlas pairing structure', 'Pairing authority', 'Pairing source', 'Partner decision boundary', 'Decision', 'Accepted final partner label', 'Pairing rule', 'Definition authority', 'Platform source'],
      ...saved.map(({ item, decision, finalLabel }) => {
        const correlation = pairCorrelation(item, allItems)
        return [item.name, item.type, partnerDisplayLabel(item, allItems), correlation.structureLabel, correlation.pairingAuthority, correlation.pairingSource, correlation.decisionLabel, decision, finalPartnerChoice(decision, finalLabel), item.rule, item.definitionAuthority, item.source]
      }),
    ]
    const blob = new Blob([rows.map((row) => row.map(csvCell).join(',')).join('\r\n')], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'relationship-atlas-pairing.csv'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 0)
  }

  return (
    <main className="pairing-workspace" id="main-content">
      <header className="workspace-header">
        <div>
          <h1>My Pairing</h1>
          <p>Build a private, local shortlist. Nothing here is uploaded or shared.</p>
        </div>
        <div className="privacy-note"><ShieldIcon /><span>Stored only on this device</span></div>
      </header>

      <section className="pairing-add" aria-labelledby="add-label-heading">
        <div>
          <h2 id="add-label-heading">Add your label</h2>
          <p>Choose a catalog label, then review the Atlas-suggested partner-side language together. FetLife does not declare these pairings.</p>
        </div>
        <div className="pairing-add-control">
          <label><span className="sr-only">Catalog label</span><select value={choice} onChange={(event) => setChoice(event.target.value)} aria-describedby={error ? 'choice-error' : undefined}><option value="">Choose a catalog label…</option>{allItems.map((item) => <option key={item.id} value={item.id}>{item.name} — {item.type}</option>)}</select></label>
          <button className="primary-button" type="button" onClick={addChoice}><PlusIcon size={18} /> Add</button>
        </div>
        {error ? <p className="form-error" id="choice-error" role="alert">{error}</p> : null}
      </section>

      <div className="workspace-actions">
        <p>{saved.length} saved {saved.length === 1 ? 'label' : 'labels'}</p>
        <div>
          <button className="secondary-button" type="button" onClick={exportCsv} disabled={!saved.length}><DownloadIcon size={17} /> Export CSV</button>
          <button className="text-button" type="button" onClick={onClear} disabled={!saved.length}>Clear all</button>
        </div>
      </div>

      {saved.length ? (
        <div className="pairing-list">
          {saved.map(({ item, decision, finalLabel }) => {
            const correlation = pairCorrelation(item, allItems)
            return <article className="pairing-row" key={item.id}>
              <div className="pairing-identity">
                <span>{item.type === 'role' ? 'D/s & profile role' : 'Relationship'}</span>
                <h2>{item.name}</h2>
                <p>{item.category}</p>
              </div>
              <div className="pairing-recommendation">
                <span>Atlas-suggested partner label</span>
                <strong>{partnerDisplayLabel(item, allItems)}</strong>
                <span className={`structure-label state-${correlation.visualTone}`}>{correlation.structureLabel}</span>
                <p>{correlation.decisionDetail}</p>
                <p>{correlation.pairingAuthority}; not declared by FetLife.</p>
              </div>
              <div className="pairing-decision">
                <label>Decision<select value={decision} onChange={(event) => onUpdate(item, { decision: event.target.value })}><option>Review</option><option>Use</option><option>Reject</option></select></label>
                <label>Accepted final partner label<input value={finalPartnerChoice(decision, finalLabel)} disabled={decision !== 'Use'} maxLength={120} autoComplete="off" spellCheck="false" onChange={(event) => onUpdate(item, { finalLabel: event.target.value })} placeholder={decision === 'Use' ? 'Agree on a label' : 'Blank until you select Use'} /></label>
              </div>
              <button className="icon-button pairing-remove" type="button" aria-label={`Remove ${item.name}`} onClick={() => onRemove(item.id)}><TrashIcon /></button>
            </article>
          })}
        </div>
      ) : (
        <div className="pairing-empty">
          <h2>No labels saved yet</h2>
          <p>Add a label above or use “Add to My Pairing” from any catalog detail.</p>
        </div>
      )}
    </main>
  )
}

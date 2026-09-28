import { itemAxes, pairCorrelation, partnerDisplayLabel, sourceMemberships } from '../catalog'
import { ExternalIcon, LinkIcon, PlusIcon } from './Icons'

export function PairMap({ item, catalog, compact = false }) {
  const correlation = pairCorrelation(item, catalog)
  const doubleArrow = ['reciprocal', 'symmetric', 'mutual-convention'].includes(correlation.direction)
  const hasLine = !['none', 'open-choice'].includes(correlation.direction)
  const targetLabel = partnerDisplayLabel(item, catalog)
  const directionText = correlation.direction === 'reciprocal' ? 'Atlas maps both labels to each other'
    : correlation.direction === 'symmetric' ? 'Atlas suggests one shared label'
      : correlation.direction === 'mutual-convention' ? 'Atlas convention in either direction'
        : correlation.direction === 'candidate-set' ? 'Atlas options; choose together'
          : correlation.direction === 'open-choice' ? 'chosen by the partner'
            : correlation.direction === 'none' ? 'no Atlas match' : 'Atlas-suggested match'

  return (
    <figure className={`pair-map state-${correlation.visualTone} direction-${correlation.direction}${compact ? ' compact' : ''}`} aria-labelledby={`pair-title-${item.id}`}>
      <figcaption className="pair-map-heading">
        <span id={`pair-title-${item.id}`}>Atlas pair map</span>
        <span className="pair-catalog-state">{correlation.catalogState}</span>
      </figcaption>
      <div className="pair-stage">
        <div className={`pair-node origin${item.name.length > 22 ? ' long-label' : ''}`}>
          <span>Your selected label</span>
          <strong>{item.name}</strong>
        </div>
        <div className="pair-bridge">
          <svg aria-hidden="true" className="pair-line horizontal" viewBox="0 0 240 58" preserveAspectRatio="none">
            {hasLine ? <><line x1={doubleArrow ? '32' : '18'} y1="29" x2="208" y2="29" />{doubleArrow ? <path className="arrowhead" d="M18 29 32 17 32 41Z" /> : null}<path className="arrowhead" d="M222 29 208 17 208 41Z" /></> : <line className="no-link" x1="18" y1="29" x2="222" y2="29" />}
          </svg>
          <svg aria-hidden="true" className="pair-line vertical" viewBox="0 0 58 132" preserveAspectRatio="none">
            {hasLine ? <><line x1="29" y1={doubleArrow ? '30' : '16'} x2="29" y2="102" />{doubleArrow ? <path className="arrowhead" d="M29 16 17 30 41 30Z" /> : null}<path className="arrowhead" d="M29 116 17 102 41 102Z" /></> : <line className="no-link" x1="29" y1="16" x2="29" y2="116" />}
          </svg>
          <span className="pair-structure">{correlation.structureLabel}</span>
          <span className="pair-direction">{directionText}</span>
        </div>
        <div className={`pair-node target${targetLabel.length > 18 ? ' long-label' : ''}`}>
          <span>{correlation.sharedLabel ? 'Atlas shared-label suggestion' : 'Atlas partner-side suggestion'}</span>
          <strong>{targetLabel}</strong>
        </div>
      </div>
    </figure>
  )
}

export function AxisFingerprint({ item }) {
  return (
    <section className="fingerprint" aria-labelledby={`fingerprint-${item.id}`}>
      <div className="section-heading-row">
        <h2 id={`fingerprint-${item.id}`}>Role fingerprint</h2>
        <p>Three independent catalog axes</p>
      </div>
      <div className="fingerprint-lanes">
        {itemAxes(item).map((axis, index) => (
          <div className="fingerprint-lane" key={axis.key}>
            <span className="axis-index" aria-hidden="true">0{index + 1}</span>
            <span className="axis-label">{axis.label}</span>
            <span className={`axis-value${axis.value === 'None' ? ' none' : ''}`}>{axis.value}</span>
          </div>
        ))}
      </div>
    </section>
  )
}

export function RelationshipClassification({ item }) {
  return (
    <section className="relationship-classification" aria-labelledby={`classification-${item.id}`}>
      <div className="section-heading-row"><h2 id={`classification-${item.id}`}>Relationship classification</h2><p>Catalog taxonomy</p></div>
      <div className="classification-value"><span>Classification</span><strong>{item.category}</strong></div>
    </section>
  )
}

export function EvidencePanel({ item, catalog, saved, onToggleSaved, onCompare, onShare, copied }) {
  const correlation = pairCorrelation(item, catalog)
  const memberships = sourceMemberships(item)
  const hasDefinition = Boolean(item.definition)
  return (
    <aside className="evidence-panel" aria-label={`${item.name} details`}>
      <section className="evidence-section definition-evidence">
        <div className="evidence-kicker"><i className={hasDefinition ? 'evidence-mark available' : 'evidence-mark missing'} aria-hidden="true" />FetLife definition</div>
        <h2>{item.name}</h2>
        {hasDefinition ? <blockquote>{item.definition}</blockquote> : <p className="missing-definition">FetLife does not currently publish a definition for this label.</p>}
        <a href={item.source} target="_blank" rel="noreferrer noopener">Open on FetLife <ExternalIcon size={16} /></a>
      </section>

      <details className="pair-details">
        <summary>Why does the Atlas suggest this?</summary>
        <p><strong>{correlation.structureLabel}.</strong> {correlation.structureSummary}</p>
        <p>{correlation.decisionDetail}</p>
        <p><strong>{correlation.pairingAuthority}.</strong> {correlation.authorityDisclosure}</p>
        <div className="source-memberships" aria-label="Catalog sources">
          {memberships.filter((membership) => membership.present).map((membership) => <span key={membership.label} className="present"><i aria-hidden="true" />{membership.label}</span>)}
        </div>
      </details>

      <div className="evidence-actions">
        <button className="secondary-button" type="button" onClick={() => onCompare(item)}>Compare</button>
        <button className="secondary-button" type="button" onClick={onShare}><LinkIcon size={17} /> {copied ? 'Copied' : 'Copy link'}</button>
        <button className={`${saved ? 'secondary-button' : 'primary-button'} pairing-toggle`} type="button" onClick={() => onToggleSaved(item)}>
          <PlusIcon size={18} /> {saved ? 'Remove from My Pairing' : 'Add to My Pairing'}
        </button>
      </div>
    </aside>
  )
}

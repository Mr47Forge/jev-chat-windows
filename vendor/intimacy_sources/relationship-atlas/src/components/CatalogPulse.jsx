import { meta } from '../catalog'

const measures = [
  ['relationshipCount', 'relationships'],
  ['roleCount', 'roles'],
  ['relationshipMenuCount', 'relationship choices'],
  ['dsMenuCount', 'D/s choices'],
]

export function CatalogPulse() {
  return (
    <section className="catalog-pulse" aria-label="Catalog coverage">
      <span className="pulse-title">Catalog coverage</span>
      {measures.map(([key, label]) => (
        <span className="pulse-measure" key={key}><strong>{meta[key].toLocaleString()}</strong> {label}</span>
      ))}
      <span className="pulse-date">captured {meta.captured}</span>
    </section>
  )
}

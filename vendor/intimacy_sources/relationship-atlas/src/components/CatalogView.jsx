import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { pairCorrelation, partnerDisplayLabel, uniqueSorted } from '../catalog'
import { createSearchIndex, searchCatalog } from '../search'
import { ChevronIcon, FilterIcon, SearchIcon } from './Icons'
import { AxisFingerprint, EvidencePanel, PairMap, RelationshipClassification } from './VisualExplorer'

const emptyFilters = { category: '', authority: '', activity: '', relationshipAxis: '', pairStructure: '', source: '', definition: '' }
const decodeHashId = () => {
  try { return decodeURIComponent(window.location.hash.slice(1).split('/')[1] ?? '') } catch { return '' }
}

const isSelectableItem = (item, mode) => {
  const membership = item?.presence?.toLocaleLowerCase() ?? ''
  return mode === 'roles'
    ? membership.includes('authenticated d/s relationship menu')
    : membership.includes('authenticated add relationship menu')
}

const FilterField = ({ label, value, options, onChange }) => (
  <label className="rail-filter-field">
    <span>{label}</span>
    <select value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">Any</option>
      {options.map((option) => <option value={option} key={option}>{option}</option>)}
    </select>
  </label>
)

export function CatalogView({ mode, items, allItems, savedIds, onToggleSaved, onCompare }) {
  const [query, setQuery] = useState('')
  const [filters, setFilters] = useState(emptyFilters)
  const selectableItems = useMemo(() => items.filter((item) => isSelectableItem(item, mode)), [items, mode])
  const [includeReferenceLibrary, setIncludeReferenceLibrary] = useState(() => {
    const hashItem = items.find((item) => item.id === decodeHashId())
    return Boolean(hashItem && !isSelectableItem(hashItem, mode))
  })
  const activeItems = includeReferenceLibrary ? items : selectableItems
  const [selected, setSelected] = useState(() => {
    const hashId = decodeHashId()
    const hashItem = items.find((item) => item.id === hashId)
    return hashItem
      ?? selectableItems.find((item) => item.name === (mode === 'roles' ? 'Dominant' : 'Partner'))
      ?? selectableItems[0]
  })
  const [copied, setCopied] = useState(false)
  const [page, setPage] = useState(1)
  const [sort, setSort] = useState('relevance')
  const searchRef = useRef(null)
  const resultRefs = useRef(new Map())
  const pageSize = 30
  const deferredQuery = useDeferredValue(query)

  const correlationMap = useMemo(() => new Map(activeItems.map((item) => [item.id, pairCorrelation(item, allItems)])), [activeItems, allItems])
  const searchIndex = useMemo(() => createSearchIndex(activeItems, correlationMap), [activeItems, correlationMap])
  const rankedSearch = useMemo(() => searchCatalog(searchIndex, deferredQuery), [searchIndex, deferredQuery])
  const searchMatchMap = useMemo(() => new Map(rankedSearch.map((result) => [result.item.id, result.match])), [rankedSearch])

  const options = useMemo(() => ({
    category: uniqueSorted(activeItems, 'category'), authority: uniqueSorted(activeItems, 'authority'), activity: uniqueSorted(activeItems, 'activity'),
    relationshipAxis: uniqueSorted(activeItems, 'relationshipAxis'), source: uniqueSorted(activeItems, 'presence'),
    pairStructure: [...new Set(activeItems.map((item) => pairCorrelation(item, allItems).structureLabel))].sort((a, b) => a.localeCompare(b)),
  }), [activeItems, allItems])

  const filtered = useMemo(() => {
    const term = deferredQuery.trim()
    const candidates = term ? rankedSearch.map((entry) => entry.item) : activeItems
    const result = candidates.filter((item) => {
      const correlation = correlationMap.get(item.id)
      if (filters.category && item.category !== filters.category) return false
      if (filters.authority && item.authority !== filters.authority) return false
      if (filters.activity && item.activity !== filters.activity) return false
      if (filters.relationshipAxis && item.relationshipAxis !== filters.relationshipAxis) return false
      if (filters.source && item.presence !== filters.source) return false
      if (filters.pairStructure && correlation.structureLabel !== filters.pairStructure) return false
      if (filters.definition === 'Definition captured' && !item.definition) return false
      if (filters.definition === 'No platform definition captured' && item.definition) return false
      return true
    })
    if (term && sort === 'relevance') return result
    return [...result].sort((a, b) => {
      if (sort === 'structure') return correlationMap.get(a.id).structureLabel.localeCompare(correlationMap.get(b.id).structureLabel) || a.name.localeCompare(b.name)
      return sort === 'name-desc' ? b.name.localeCompare(a.name) : a.name.localeCompare(b.name)
    })
  }, [activeItems, deferredQuery, rankedSearch, filters, sort, correlationMap])

  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const start = (safePage - 1) * pageSize
  const visible = filtered.slice(start, start + pageSize)
  const filtersActive = Object.values(filters).some(Boolean)
  const showPinned = !query && !filtersActive && !visible.some((item) => item.id === selected.id)

  useEffect(() => {
    const shortcut = (event) => {
      if (event.key === '/' && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) { event.preventDefault(); searchRef.current?.focus() }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [])

  const selectItem = (item) => {
    setSelected(item)
    setCopied(false)
    window.history.replaceState(null, '', `#${mode}/${encodeURIComponent(item.id)}`)
    if (window.matchMedia('(max-width: 900px)').matches) {
      document.querySelector('.correlation-canvas')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  const shareItem = async () => {
    const url = window.location.href
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1800)
    } catch {
      window.prompt('Copy this link', url)
    }
  }

  const moveResultFocus = (item, offset) => {
    const index = visible.findIndex((candidate) => candidate.id === item.id)
    const next = visible[Math.max(0, Math.min(visible.length - 1, index + offset))]
    resultRefs.current.get(next?.id)?.focus()
  }

  const updateFilter = (field, value) => { setFilters((current) => ({ ...current, [field]: value })); setPage(1) }
  const updateCatalogScope = (includeReference) => {
    setIncludeReferenceLibrary(includeReference)
    setPage(1)
    if (!includeReference && !isSelectableItem(selected, mode)) {
      const replacement = selectableItems.find((item) => item.name === (mode === 'roles' ? 'Dominant' : 'Partner')) ?? selectableItems[0]
      setSelected(replacement)
      setCopied(false)
      window.history.replaceState(null, '', `#${mode}/${encodeURIComponent(replacement.id)}`)
    }
  }

  const modeLabel = mode === 'roles' ? 'D/s & profile roles' : 'relationships'
  const menuLabel = mode === 'roles' ? 'authenticated Add D/s menu' : 'authenticated Add Relationship menu'
  const selectedIsSelectable = isSelectableItem(selected, mode)

  return (
    <main className="visual-catalog" id="main-content">
      <h1 className="sr-only">{mode === 'roles' ? 'D/s & Profile Roles' : 'Relationships'}</h1>
      <section className="catalog-rail" aria-label={`${mode === 'roles' ? 'D/s and profile role' : 'Relationship'} catalog`}>
        <div className="rail-controls">
          <label className="search-field"><SearchIcon /><span className="sr-only">Search catalog</span><input ref={searchRef} type="search" value={query} onChange={(event) => { setQuery(event.target.value); setPage(1) }} onKeyDown={(event) => { if (event.key === 'ArrowDown' && visible[0]) { event.preventDefault(); resultRefs.current.get(visible[0].id)?.focus() } else if (event.key === 'Enter' && visible[0]) selectItem(visible[0]) }} placeholder={mode === 'roles' ? 'Search roles or partners…' : 'Search relationships or partners…'} autoComplete="off" spellCheck="false" /><kbd>/</kbd></label>
          <p className="search-scope">Misspellings are okay. Results update as you type.</p>
          <div className="catalog-scope-control">
            <span className="catalog-scope-label">Show</span>
            <div className="catalog-scope-options" role="group" aria-label={`Choose ${modeLabel} catalog scope`}>
              <button type="button" className={!includeReferenceLibrary ? 'active' : ''} aria-pressed={!includeReferenceLibrary} onClick={() => updateCatalogScope(false)}>Available choices <b>{selectableItems.length.toLocaleString()}</b></button>
              <button type="button" className={includeReferenceLibrary ? 'active' : ''} aria-pressed={includeReferenceLibrary} onClick={() => updateCatalogScope(true)}>Full reference library <b>{items.length.toLocaleString()}</b></button>
            </div>
            <p>{includeReferenceLibrary
              ? `Includes reference-only terms that may not be selectable in FetLife's ${menuLabel}.`
              : `Only labels captured in FetLife's ${menuLabel} are shown.`} Partner suggestions are Atlas guidance and may use reference-only language.</p>
          </div>
          <details className="filter-disclosure">
            <summary><FilterIcon size={19} /> Filters</summary>
            <div className="rail-filters">
              <div className="rail-filter-heading"><strong>Filter catalog</strong><button className="text-button" type="button" onClick={() => setFilters(emptyFilters)}>Clear all</button></div>
              <FilterField label={mode === 'roles' ? 'Role type' : 'Relationship type'} value={filters.category} options={options.category} onChange={(value) => updateFilter('category', value)} />
              {mode === 'roles' ? <>
                <FilterField label="Authority" value={filters.authority} options={options.authority} onChange={(value) => updateFilter('authority', value)} />
                <FilterField label="Activity" value={filters.activity} options={options.activity} onChange={(value) => updateFilter('activity', value)} />
                <FilterField label="Relationship role" value={filters.relationshipAxis} options={options.relationshipAxis} onChange={(value) => updateFilter('relationshipAxis', value)} />
                <FilterField label="Source membership" value={filters.source} options={options.source} onChange={(value) => updateFilter('source', value)} />
              </> : null}
              <FilterField label="Pair structure" value={filters.pairStructure} options={options.pairStructure} onChange={(value) => updateFilter('pairStructure', value)} />
              <FilterField label="Definition" value={filters.definition} options={['Definition captured', 'No platform definition captured']} onChange={(value) => updateFilter('definition', value)} />
            </div>
          </details>
        </div>
        <div className="rail-summary"><div><strong>{includeReferenceLibrary ? `All ${modeLabel}` : mode === 'roles' ? 'Available D/s choices' : 'Available relationship choices'}</strong><span aria-live="polite">{filtered.length.toLocaleString()} of {activeItems.length.toLocaleString()}{includeReferenceLibrary ? ` • ${selectableItems.length.toLocaleString()} selectable` : ''}{deferredQuery.trim() && sort === 'relevance' ? ' • relevance ranked' : ''}</span></div><select aria-label="Sort catalog" value={sort} onChange={(event) => { setSort(event.target.value); setPage(1) }}><option value="relevance">Relevance</option><option value="name-asc">A–Z</option><option value="name-desc">Z–A</option><option value="structure">Pair structure</option></select></div>
        <div className="rail-results" aria-label="Catalog labels" aria-busy={query !== deferredQuery}>
          {showPinned ? <button key={`pinned-${selected.id}`} aria-pressed="true" className="rail-result selected pinned" type="button" onClick={() => selectItem(selected)}><span className="rail-result-copy"><strong>{selected.name}</strong><small>{partnerDisplayLabel(selected, allItems)}</small></span><span className={`structure-glyph state-${correlationMap.get(selected.id).visualTone}`}><i aria-hidden="true" />{correlationMap.get(selected.id).structureLabel}</span><ChevronIcon size={18} /></button> : null}
          {visible.map((item) => <button key={item.id} ref={(node) => { if (node) resultRefs.current.set(item.id, node); else resultRefs.current.delete(item.id) }} aria-pressed={selected?.id === item.id} className={selected?.id === item.id ? 'rail-result selected' : 'rail-result'} type="button" onClick={() => selectItem(item)} onKeyDown={(event) => { if (event.key === 'ArrowDown') { event.preventDefault(); moveResultFocus(item, 1) } else if (event.key === 'ArrowUp') { event.preventDefault(); moveResultFocus(item, -1) } else if (event.key === 'Escape') searchRef.current?.focus() }}><span className="rail-result-copy"><strong>{item.name}</strong><small>{partnerDisplayLabel(item, allItems)}</small>{!isSelectableItem(item, mode) ? <span className="reference-only-label">Reference only</span> : null}{deferredQuery.trim() && searchMatchMap.get(item.id) ? <span className="search-match">{searchMatchMap.get(item.id).fieldLabels.join(' + ')} match</span> : null}</span><span className={`structure-glyph state-${correlationMap.get(item.id).visualTone}`}><i aria-hidden="true" />{correlationMap.get(item.id).structureLabel}</span><ChevronIcon size={18} /></button>)}
          {!visible.length ? <div className="rail-empty"><strong>No matching labels</strong><span>Try fewer terms or clear the active filters.</span></div> : null}
        </div>
        <div className="rail-pagination" aria-label="Catalog pagination"><span>{filtered.length ? start + 1 : 0}–{Math.min(start + pageSize, filtered.length)} of {filtered.length.toLocaleString()}</span><div><button type="button" aria-label="Previous page" disabled={safePage <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}><ChevronIcon direction="left" /></button><span>{safePage} / {totalPages}</span><button type="button" aria-label="Next page" disabled={safePage >= totalPages} onClick={() => setPage((value) => Math.min(totalPages, value + 1))}><ChevronIcon /></button></div></div>
      </section>
      <section className="correlation-canvas" aria-label={`${selected.name} visual correlation`}><button className="mobile-find secondary-button" type="button" onClick={() => { searchRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' }); searchRef.current?.focus({ preventScroll: true }) }}><SearchIcon size={18} /> Find another label</button><div className={`selection-scope-status ${selectedIsSelectable ? 'selectable' : 'reference-only'}`}><strong>{selectedIsSelectable ? 'Available profile choice' : 'Reference-only term'}</strong><span>{selectedIsSelectable ? `Captured in FetLife's ${menuLabel}.` : `Not captured in FetLife's ${menuLabel}; it may not be selectable on a profile.`}</span></div><PairMap item={selected} catalog={allItems} />{selected.type === 'role' ? <AxisFingerprint item={selected} /> : <RelationshipClassification item={selected} />}</section>
      <EvidencePanel item={selected} catalog={allItems} saved={savedIds.has(selected.id)} onToggleSaved={onToggleSaved} onCompare={onCompare} onShare={shareItem} copied={copied} />
    </main>
  )
}

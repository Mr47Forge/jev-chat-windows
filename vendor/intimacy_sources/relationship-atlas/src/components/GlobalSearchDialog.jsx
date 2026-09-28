import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { allItems, pairCorrelation, partnerDisplayLabel } from '../catalog'
import { createSearchIndex, searchCatalog } from '../search'
import { CloseIcon, SearchIcon } from './Icons'

const RESULT_LIMIT = 12
let cachedSearchIndex = null
const getGlobalSearchIndex = () => {
  if (cachedSearchIndex) return cachedSearchIndex
  const correlationMap = new Map(allItems.map((item) => [item.id, pairCorrelation(item, allItems)]))
  cachedSearchIndex = createSearchIndex(allItems, correlationMap)
  return cachedSearchIndex
}

export function GlobalSearchDialog({ open, onClose, onSelect }) {
  const dialogRef = useRef(null)
  const inputRef = useRef(null)
  const resultRefs = useRef(new Map())
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const deferredQuery = useDeferredValue(query)
  const searchIndex = useMemo(() => open ? getGlobalSearchIndex() : [], [open])
  const results = useMemo(() => deferredQuery.trim()
    ? searchCatalog(searchIndex, deferredQuery).slice(0, RESULT_LIMIT)
    : [], [deferredQuery, searchIndex])
  const safeActiveIndex = Math.min(activeIndex, Math.max(0, results.length - 1))

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return undefined
    if (open && !dialog.open) {
      dialog.showModal()
      setQuery('')
      setActiveIndex(0)
      const focusTimer = window.setTimeout(() => inputRef.current?.focus(), 0)
      return () => window.clearTimeout(focusTimer)
    }
    if (!open && dialog.open) dialog.close()
    return undefined
  }, [open])

  const choose = (result) => {
    if (!result) return
    onSelect(result.item)
  }

  const activate = (index) => {
    setActiveIndex(index)
    window.requestAnimationFrame(() => resultRefs.current.get(results[index]?.item.id)?.scrollIntoView({ block: 'nearest' }))
  }

  const handleKeys = (event) => {
    if (event.key === 'ArrowDown' && results.length) {
      event.preventDefault()
      activate((safeActiveIndex + 1) % results.length)
    } else if (event.key === 'ArrowUp' && results.length) {
      event.preventDefault()
      activate((safeActiveIndex - 1 + results.length) % results.length)
    } else if (event.key === 'Enter' && results[safeActiveIndex]) {
      event.preventDefault()
      choose(results[safeActiveIndex])
    }
  }

  return (
    <dialog
      ref={dialogRef}
      className="global-search-dialog"
      aria-labelledby="global-search-heading"
      onCancel={(event) => { event.preventDefault(); onClose() }}
      onClose={onClose}
      onClick={(event) => { if (event.target === event.currentTarget) onClose() }}
    >
      <div className="global-search-shell">
        <header className="global-search-heading">
          <div>
            <h2 id="global-search-heading">Find any label</h2>
            <p>Search relationships and D/s or profile roles together.</p>
          </div>
          <button className="icon-button" type="button" aria-label="Close label search" onClick={onClose}><CloseIcon /></button>
        </header>
        <label className="global-search-input">
          <SearchIcon size={22} />
          <span className="sr-only">Search all labels</span>
          <input
            ref={inputRef}
            type="search"
            value={query}
            maxLength={120}
            placeholder="Try a label, partner term, KTP, or daily tasks…"
            autoComplete="off"
            spellCheck="false"
            aria-activedescendant={results[safeActiveIndex] ? `global-result-${results[safeActiveIndex].item.id}` : undefined}
            aria-controls="global-search-results"
            onChange={(event) => { setQuery(event.target.value); setActiveIndex(0) }}
            onKeyDown={handleKeys}
          />
          <kbd>Esc</kbd>
        </label>
        <div className="global-search-status" aria-live="polite">
          {deferredQuery.trim() ? `${results.length} top ${results.length === 1 ? 'match' : 'matches'}` : `${allItems.length.toLocaleString()} labels available`}
        </div>
        <div className="global-search-results" id="global-search-results" role="listbox" aria-label="Label search results">
          {!deferredQuery.trim() ? (
            <div className="global-search-empty"><strong>One search across the entire atlas</strong><span>Misspellings, partner labels, common shorthand, role axes, and captured definitions are searchable.</span></div>
          ) : null}
          {deferredQuery.trim() && !results.length ? (
            <div className="global-search-empty"><strong>No matching labels</strong><span>Try fewer words, another spelling, or the label used by the other person.</span></div>
          ) : null}
          {results.map((result, index) => {
            const item = result.item
            return (
              <button
                id={`global-result-${item.id}`}
                key={item.id}
                ref={(node) => { if (node) resultRefs.current.set(item.id, node); else resultRefs.current.delete(item.id) }}
                className={index === safeActiveIndex ? 'global-search-result active' : 'global-search-result'}
                type="button"
                role="option"
                aria-selected={index === safeActiveIndex}
                onMouseEnter={() => setActiveIndex(index)}
                onClick={() => choose(result)}
              >
                <span className="global-result-type">{item.type === 'role' ? 'D/s & profile role' : 'Relationship'}</span>
                <strong>{item.name}</strong>
                <span className="global-result-partner">Partner: {partnerDisplayLabel(item, allItems)}</span>
                <small>{result.match.fieldLabels.join(' + ')} match</small>
              </button>
            )
          })}
        </div>
        <footer className="global-search-footer"><span><kbd>↑</kbd><kbd>↓</kbd> move</span><span><kbd>Enter</kbd> open</span><span>Nothing is uploaded.</span></footer>
      </div>
    </dialog>
  )
}

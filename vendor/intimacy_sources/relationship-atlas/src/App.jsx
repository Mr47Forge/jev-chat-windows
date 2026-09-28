import { useCallback, useEffect, useMemo, useState } from 'react'
import { allItems, findPartnerItem, relationships, resolvedPartnerLabel, roles } from './catalog'
import { AboutDialog } from './components/AboutDialog'
import { AppHeader } from './components/AppHeader'
import { CatalogView } from './components/CatalogView'
import { CompareWorkspace } from './components/CompareWorkspace'
import { GlobalSearchDialog } from './components/GlobalSearchDialog'
import { PairingWorkspace } from './components/PairingWorkspace'
import { ShieldIcon } from './components/Icons'
import './styles.css'

const STORAGE_KEY = 'relationship-atlas:pairing:v2'
const LEGACY_STORAGE_KEY = 'relationship-atlas:pairing:v1'
const validTabs = new Set(['relationships', 'roles', 'compare', 'pairing'])
const validDecisions = new Set(['Review', 'Use', 'Reject'])
const MAX_SAVED_ENTRIES = 500
const MAX_FINAL_LABEL_LENGTH = 120

const sanitizeEntries = (stored) => {
  if (!Array.isArray(stored)) return []
  const unique = new Map()
  for (const entry of stored.slice(0, MAX_SAVED_ENTRIES)) {
    if (!entry || typeof entry.id !== 'string') continue
    const item = allItems.find((candidate) => candidate.id === entry.id || candidate.legacyId === entry.id)
    if (!item || unique.has(item.id)) continue
    unique.set(item.id, {
      id: item.id,
      decision: validDecisions.has(entry.decision) ? entry.decision : 'Review',
      finalLabel: typeof entry.finalLabel === 'string' ? entry.finalLabel.slice(0, MAX_FINAL_LABEL_LENGTH) : '',
    })
  }
  return [...unique.values()]
}

const loadEntries = () => {
  try {
    const current = localStorage.getItem(STORAGE_KEY)
    const legacy = current === null ? localStorage.getItem(LEGACY_STORAGE_KEY) : null
    const entries = sanitizeEntries(JSON.parse(current ?? legacy ?? '[]'))
    if (legacy !== null) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
      localStorage.removeItem(LEGACY_STORAGE_KEY)
    }
    return entries
  } catch {
    return []
  }
}

const initialTab = () => {
  const value = window.location.hash.slice(1).split('/')[0]
  return validTabs.has(value) ? value : 'relationships'
}

const defaultFinalLabel = (item) => resolvedPartnerLabel(item, allItems)
const resetPageScroll = () => {
  const previousBehavior = document.documentElement.style.scrollBehavior
  document.documentElement.style.scrollBehavior = 'auto'
  window.scrollTo(0, 0)
  document.documentElement.scrollTop = 0
  document.body.scrollTop = 0
  document.documentElement.style.scrollBehavior = previousBehavior
}

export default function App() {
  const [activeTab, setActiveTab] = useState(initialTab)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [findOpen, setFindOpen] = useState(false)
  const [catalogTarget, setCatalogTarget] = useState(null)
  const [entries, setEntries] = useState(loadEntries)
  const protecting = relationships.find((item) => item.name === 'Protecting')
  const underProtection = relationships.find((item) => item.name === 'Under Protection')
  const [compareIds, setCompareIds] = useState(() => [protecting?.id, underProtection?.id].filter(Boolean))
  const savedIds = useMemo(() => new Set(entries.map((entry) => entry.id)), [entries])

  useEffect(() => {
    let secondFrame
    const firstFrame = window.requestAnimationFrame(() => {
      secondFrame = window.requestAnimationFrame(resetPageScroll)
    })
    const settleTimer = window.setTimeout(resetPageScroll, 120)
    return () => {
      window.cancelAnimationFrame(firstFrame)
      if (secondFrame) window.cancelAnimationFrame(secondFrame)
      window.clearTimeout(settleTimer)
    }
  }, [activeTab])

  useEffect(() => {
    const shortcut = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLocaleLowerCase() === 'k' && !document.querySelector('dialog[open]')) {
        event.preventDefault()
        setFindOpen(true)
      }
    }
    window.addEventListener('keydown', shortcut)
    return () => window.removeEventListener('keydown', shortcut)
  }, [])

  const saveEntries = (next) => {
    const sanitized = sanitizeEntries(next)
    setEntries(sanitized)
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sanitized))
    } catch {
      // The in-memory shortlist remains usable if browser storage is unavailable.
    }
  }

  const changeTab = useCallback((tab) => {
    setCatalogTarget(null)
    setActiveTab(tab)
    window.history.replaceState(null, '', `#${tab}`)
    resetPageScroll()
  }, [])

  const openCatalogItem = useCallback((item) => {
    const tab = item.type === 'role' ? 'roles' : 'relationships'
    setCatalogTarget(item.id)
    setActiveTab(tab)
    setFindOpen(false)
    window.history.replaceState(null, '', `#${tab}/${encodeURIComponent(item.id)}`)
    resetPageScroll()
  }, [])

  const openFind = useCallback(() => setFindOpen(true), [])
  const closeFind = useCallback(() => setFindOpen(false), [])

  const addItem = (item) => {
    if (savedIds.has(item.id)) return
    saveEntries([...entries, { id: item.id, decision: 'Review', finalLabel: '' }])
  }

  const removeItem = (id) => saveEntries(entries.filter((entry) => entry.id !== id))

  const toggleItem = (item) => savedIds.has(item.id) ? removeItem(item.id) : addItem(item)

  const updateItem = (item, changes) => {
    saveEntries(entries.map((entry) => {
      if (entry.id !== item.id) return entry
      const next = { ...entry, ...changes }
      if (changes.decision === 'Use' && !next.finalLabel) next.finalLabel = defaultFinalLabel(item)
      if (changes.decision && changes.decision !== 'Use') next.finalLabel = ''
      return next
    }))
  }

  const compareItem = (item) => {
    const partner = findPartnerItem(item, allItems)
    setCompareIds([item.id, partner?.id].filter(Boolean))
    changeTab('compare')
  }

  return (
    <div className="app-shell">
      <AppHeader activeTab={activeTab} onTabChange={changeTab} onAbout={() => setAboutOpen(true)} onFind={openFind} />
      {activeTab === 'relationships' ? (
        <CatalogView key={`relationships-${catalogTarget ?? 'default'}`} mode="relationships" items={relationships} allItems={allItems} savedIds={savedIds} onToggleSaved={toggleItem} onCompare={compareItem} />
      ) : null}
      {activeTab === 'roles' ? (
        <CatalogView key={`roles-${catalogTarget ?? 'default'}`} mode="roles" items={roles} allItems={allItems} savedIds={savedIds} onToggleSaved={toggleItem} onCompare={compareItem} />
      ) : null}
      {activeTab === 'compare' ? <CompareWorkspace allItems={allItems} compareIds={compareIds} setCompareIds={setCompareIds} /> : null}
      {activeTab === 'pairing' ? (
        <PairingWorkspace allItems={allItems} entries={entries} onAdd={addItem} onRemove={removeItem} onUpdate={updateItem} onClear={() => saveEntries([])} />
      ) : null}
      <footer className="app-footer">
        <span><ShieldIcon size={19} /> Labels describe language, not consent.</span>
        <button className="text-button" type="button" onClick={() => setAboutOpen(true)}>About this atlas</button>
      </footer>
      {findOpen ? <GlobalSearchDialog open onClose={closeFind} onSelect={openCatalogItem} /> : null}
      <AboutDialog open={aboutOpen} onClose={() => setAboutOpen(false)} />
    </div>
  )
}

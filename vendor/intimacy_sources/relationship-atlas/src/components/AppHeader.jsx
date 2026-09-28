import { useEffect, useState } from 'react'
import { DownloadIcon, InfoIcon, OfflineIcon, SearchIcon } from './Icons'

const tabs = [
  ['relationships', 'Relationships'],
  ['roles', 'D/s & Profile Roles'],
  ['pairing', 'My Pairing'],
]

export function AppHeader({ activeTab, onTabChange, onAbout, onFind }) {
  const [installPrompt, setInstallPrompt] = useState(null)
  const [online, setOnline] = useState(navigator.onLine)
  const [offlineReady, setOfflineReady] = useState(Boolean(navigator.serviceWorker?.controller))

  useEffect(() => {
    const captureInstall = (event) => {
      event.preventDefault()
      setInstallPrompt(event)
    }
    const syncOnline = () => setOnline(navigator.onLine)
    const markOfflineReady = () => setOfflineReady(true)
    window.addEventListener('beforeinstallprompt', captureInstall)
    window.addEventListener('online', syncOnline)
    window.addEventListener('offline', syncOnline)
    window.addEventListener('relationship-atlas-sw-ready', markOfflineReady)
    return () => {
      window.removeEventListener('beforeinstallprompt', captureInstall)
      window.removeEventListener('online', syncOnline)
      window.removeEventListener('offline', syncOnline)
      window.removeEventListener('relationship-atlas-sw-ready', markOfflineReady)
    }
  }, [])

  const install = async () => {
    if (!installPrompt) return
    await installPrompt.prompt()
    setInstallPrompt(null)
  }

  return (
    <header className="app-header">
      <div className="brand-row">
        <button className="brand" type="button" onClick={() => onTabChange('relationships')}>Relationship Atlas</button>
        <div className="header-actions">
          <button className="header-action find-action" type="button" onClick={onFind}><SearchIcon size={19} /> Find any label <span className="find-shortcut">Ctrl K</span></button>
          <span className="offline-state" title={!online ? 'Working offline' : offlineReady ? 'Offline cache is ready' : 'Preparing offline cache'}>
            <OfflineIcon size={19} /> {!online ? 'Offline' : offlineReady ? 'Offline ready' : 'Online'}
          </span>
          {installPrompt ? (
            <button className="header-action install-action" type="button" onClick={install}><DownloadIcon size={19} /> Install app</button>
          ) : null}
          <button className="header-action" type="button" onClick={onAbout}><InfoIcon size={19} /> About</button>
        </div>
      </div>
      <nav className="tab-list" aria-label="Primary">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={activeTab === id ? 'tab active' : 'tab'}
            aria-current={activeTab === id ? 'page' : undefined}
            onClick={() => onTabChange(id)}
          >
            {label}
          </button>
        ))}
      </nav>
    </header>
  )
}

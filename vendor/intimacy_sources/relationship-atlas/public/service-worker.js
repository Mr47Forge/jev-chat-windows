const CACHE = 'relationship-atlas-v7'
const CORE = ['./', './index.html', './manifest.webmanifest', './icon.svg', './icon-192.png', './icon-512.png', './icon-maskable.svg', './icon-maskable-512.png']
const CACHEABLE_DESTINATIONS = new Set(['document', 'script', 'style', 'image', 'font', 'manifest'])

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(CORE)))
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key)))))
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return
  if (event.request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const response = await fetch(event.request)
        if (response.ok) await (await caches.open(CACHE)).put('./index.html', response.clone())
        return response
      } catch {
        return (await caches.match('./index.html')) ?? Response.error()
      }
    })())
    return
  }
  const requestUrl = new URL(event.request.url)
  const scopePath = new URL(self.registration.scope).pathname
  const cacheable = requestUrl.origin === self.location.origin
    && requestUrl.pathname.startsWith(scopePath)
    && CACHEABLE_DESTINATIONS.has(event.request.destination)
    && !event.request.headers.has('range')
  if (!cacheable) return
  event.respondWith((async () => {
    const cached = await caches.match(event.request)
    if (cached) return cached
    const response = await fetch(event.request)
    if (response.ok && response.type === 'basic') await (await caches.open(CACHE)).put(event.request, response.clone())
    return response
  })())
})

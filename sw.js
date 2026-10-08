/* FinTech Toolkit service worker — makes the site installable and usable
   offline.

   Strategy: NETWORK-FIRST for everything, falling back to the cache only
   when the network fails. Online users therefore always get the latest
   pages and stock data (no "stuck on an old version" problem); offline
   users get the last copy they saw. The app shell is pre-cached on install
   so the main pages work offline even if never visited.

   Bump CACHE when the precache list changes; old caches are removed on
   activate. */
const CACHE = 'ftk-v1';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './assets/shared.css',
  './assets/shared.js',
  './assets/icons/icon-192.png',
  './assets/icons/icon-512.png',
  './tools/stock-drop/index.html',
  './tools/rebalance/index.html',
  './tools/retirement/index.html',
  './tools/loan/index.html',
  './tools/rules/index.html',
  './tools/quotes/index.html',
  './tools/quotes/quotes-data.js',
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE)
      // Cache what we can; one failed file shouldn't block installation.
      .then(cache => Promise.all(SHELL.map(u => cache.add(u).catch(() => {}))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Live-price probes to local dev servers / third-party APIs: never cache.
  if (/^\/api\//.test(url.pathname) || url.hostname === 'localhost' && url.port !== self.location.port) return;
  if (url.hostname.endsWith('allorigins.win') || url.hostname.endsWith('er-api.com')) return;

  event.respondWith(
    fetch(req)
      .then(res => {
        // Cache successful same-origin responses and CDN assets (opaque ok).
        if (res && (res.ok || res.type === 'opaque')) {
          const copy = res.clone();
          caches.open(CACHE).then(c => c.put(req, copy)).catch(() => {});
        }
        return res;
      })
      .catch(() =>
        caches.match(req, { ignoreSearch: true }).then(hit => {
          if (hit) return hit;
          // Offline navigation to an uncached page: fall back to the home page.
          if (req.mode === 'navigate') return caches.match('./index.html');
          return Response.error();
        })
      )
  );
});

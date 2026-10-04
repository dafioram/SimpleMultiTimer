// Bump this when the list of FILES changes. Code updates no longer need a
// bump: pages and scripts are fetched network-first, so new versions are
// picked up on the next load while online.
const CACHE_NAME = "multi-timer-v3";

const basePath = self.location.pathname.replace('/sw.js', '');

const FILES = [
    `${basePath}/`,
    `${basePath}/index.html`,
    `${basePath}/history.html`,
    `${basePath}/common.js`,
    `${basePath}/manifest.json`,
    `${basePath}/icons/icon-192.png`,
    `${basePath}/icons/icon-512.png`
];

self.addEventListener("install", event => {
    self.skipWaiting();

    event.waitUntil(
        caches.open(CACHE_NAME)
            // cache: "reload" skips the browser's HTTP cache so we store fresh copies
            .then(cache => cache.addAll(FILES.map(url => new Request(url, { cache: "reload" }))))
    );
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys()
            .then(keys => Promise.all(
                keys
                    .filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            ))
            .then(() => self.clients.claim())
    );
});

// Network first: try the server, update the cache, fall back to the cache offline.
async function networkFirst(request) {
    try {
        const response = await fetch(request);
        if (response.ok) {
            const cache = await caches.open(CACHE_NAME);
            await cache.put(request, response.clone());
        }
        return response;
    } catch (err) {
        const cached = await caches.match(request, { ignoreSearch: true });
        if (cached) return cached;
        if (request.mode === "navigate") {
            const fallback = await caches.match(`${basePath}/index.html`);
            if (fallback) return fallback;
        }
        throw err;
    }
}

// Cache first for images, which rarely change.
async function cacheFirst(request) {
    const cached = await caches.match(request);
    return cached || fetch(request);
}

self.addEventListener("fetch", event => {
    const { request } = event;
    if (request.method !== "GET") return;
    if (new URL(request.url).origin !== self.location.origin) return;

    event.respondWith(
        request.destination === "image" ? cacheFirst(request) : networkFirst(request)
    );
});

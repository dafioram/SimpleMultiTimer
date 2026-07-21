const CACHE_NAME = "multi-timer-v2";

const basePath = self.location.pathname.replace('/sw.js', '');

const FILES = [
    `${basePath}/`,
    `${basePath}/index.html`,
    `${basePath}/history.html`,
    `${basePath}/manifest.json`,
    `${basePath}/icons/icon-192.png`,
    `${basePath}/icons/icon-512.png`
];


self.addEventListener("install", event => {
	self.skipWaiting();

    event.waitUntil(
        caches.open(CACHE_NAME)
        .then(cache => cache.addAll(FILES))
    );

});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    )
  );

  clients.claim();
});

self.addEventListener("fetch", event => {

    event.respondWith(

        caches.match(event.request)
        .then(response => response || fetch(event.request))

    );

});
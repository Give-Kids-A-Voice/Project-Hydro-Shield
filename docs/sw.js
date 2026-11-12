// Hydro-Shield offline support. Keeps the app and the map data you have already looked at,
// so it still works with a weak signal. Nothing about the user is stored or sent.
var V = 'hs-v2';
var SHELL = ['./', 'index.html', 'hazards.js', 'i18n.js', 'found.html', 'manifest.webmanifest', 'icons/icon-192.png',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css',
  'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js'];
var DATA = 'hs-data-v1', MAX_DATA = 600;

self.addEventListener('install', function (e) {
  e.waitUntil(caches.open(V).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k !== V && k !== DATA; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

function trim() {
  return caches.open(DATA).then(function (c) { return c.keys().then(function (ks) {
    return Promise.all(ks.slice(0, Math.max(0, ks.length - MAX_DATA)).map(function (k) { return c.delete(k); }));
  }); });
}

self.addEventListener('fetch', function (e) {
  var req = e.request; if (req.method !== 'GET') return;
  var url = new URL(req.url);
  // Our map data: answer from the cache right away, refresh it in the background. Never cache a 404 (it means "no tile here").
  if (url.origin === location.origin && url.pathname.indexOf('/data/') === 0) {
    e.respondWith(caches.open(DATA).then(function (c) {
      return c.match(req).then(function (hit) {
        var net = fetch(req).then(function (r) { if (r.ok) { c.put(req, r.clone()).then(trim); } return r; });
        if (hit) { net.catch(function () {}); return hit; }
        return net;
      });
    }));
    return;
  }
  // The app itself and Leaflet: network first, cache when offline.
  if (url.origin === location.origin || url.hostname === 'cdnjs.cloudflare.com' || url.hostname.indexOf('fonts.g') === 0) {
    e.respondWith(fetch(req).then(function (r) {
      if (r.ok) { var cp = r.clone(); caches.open(V).then(function (c) { c.put(req, cp); }); }
      return r;
    }).catch(function () { return caches.match(req, { ignoreSearch: url.origin === location.origin }); }));
  }
  // Everything else (street map, imagery, address search, live water servers) goes straight to the network.
});

/* Keeps a copy of Wirely in the browser, so after the first visit it starts quickly and works offline
   (useful on Chromebooks and patchy school Wi-Fi). Each release gets a new cache. */
const CACHE = "wirely-__VERSION__";
// every file of this release (filled in by tools/build_web.py)
const FILES = __FILES__;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(CACHE)
    .then((c) => Promise.all(["./"].concat(FILES).map((f) => c.add(f).catch(() => console.warn("not cached:", f)))))
    .then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((keys) => Promise.all(keys.filter((k) => k.startsWith("wirely-") && k !== CACHE)
    .map((k) => caches.delete(k)))).then(() => self.clients.claim()));
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const pyodideCdn = url.hostname === "cdn.jsdelivr.net" && url.pathname.startsWith("/pyodide/");
  if (url.origin !== location.origin && !pyodideCdn) return;
  // our own files and Pyodide: from the cache if we have them, otherwise from the network (and keep a copy)
  e.respondWith(caches.open(CACHE).then(async (cache) => {
    const hit = await cache.match(req, { ignoreSearch: url.origin === location.origin });
    if (hit) return hit;
    const resp = await fetch(req);
    if (resp.ok && (resp.type === "basic" || resp.type === "cors")) cache.put(req, resp.clone());
    return resp;
  }));
});

// サービスワーカー:アプリ全体を端末に保存し、オフラインでも動くようにする
// ファイルを追加・変更したら VERSION の数字を上げること(古い保存分が入れ替わる)
const VERSION = "v1";
const CACHE_NAME = `eigo-ehon-${VERSION}`;

const BOOK_FILES = [];
["sun", "cat"].forEach(id => {
  BOOK_FILES.push(`books/${id}/cover.svg`);
  for (let i = 1; i <= 6; i++) {
    BOOK_FILES.push(`books/${id}/p${i}.svg`);
    BOOK_FILES.push(`books/${id}/audio/p${i}.m4a`);
  }
});

const FILES_TO_CACHE = [
  "./",
  "index.html",
  "css/style.css",
  "js/app.js",
  "js/books.js",
  "manifest.webmanifest",
  "img/icon-192.png",
  "img/icon-512.png",
  "img/apple-touch-icon.png",
  ...BOOK_FILES
];

self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(FILES_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// 保存済みのファイルがあればそれを返し、なければネットから取りに行く
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then(cached =>
      cached ||
      fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return response;
      })
    )
  );
});

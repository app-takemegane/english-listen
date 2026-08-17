// サービスワーカー:アプリ全体を端末に保存し、オフラインでも動くようにする
// ファイルを追加・変更したら VERSION の数字を上げること(古い保存分が入れ替わる)
const VERSION = "v18";
const CACHE_NAME = `eigo-ehon-${VERSION}`;

// 絵本データを読み込み、単語練習の音声一覧を絵本の本文から自動で作る
importScripts("js/books.js");
const WORD_FILES = [];
const seenWords = new Set();
BOOKS.forEach(b => b.pages.forEach(p => p.text.split(" ").forEach(w => {
  const key = wordKey(w);
  if (key && !seenWords.has(key)) {
    seenWords.add(key);
    WORD_FILES.push(`words/${key}.m4a`);
  }
})));

const BOOK_FILES = [];
["sun", "cat", "colors", "park"].forEach(id => {
  BOOK_FILES.push(`books/${id}/cover.svg`);
  for (let i = 1; i <= 6; i++) {
    BOOK_FILES.push(`books/${id}/p${i}.svg`);
    BOOK_FILES.push(`books/${id}/audio/p${i}.m4a`);
  }
  for (let i = 1; i <= 3; i++) {
    BOOK_FILES.push(`books/${id}/quiz/q${i}.m4a`);
  }
});

const FILES_TO_CACHE = [
  "./",
  "index.html",
  "css/style.css",
  "js/app.js",
  "js/books.js",
  "js/cards.js",
  "manifest.webmanifest",
  "img/icon-192.png",
  "img/icon-512.png",
  "img/apple-touch-icon.png",
  "sfx/page.m4a",
  "sfx/finish.m4a",
  "sfx/correct.m4a",
  "sfx/wrong.m4a",
  "sfx/coin.m4a",
  ...WORD_FILES,
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

// 画面や絵本一覧などの「中身が変わるファイル」は、まずネットの最新版を取りに行き、
// 電波がないときだけ保存分を使う。挿絵や音声など「重くて変わらないファイル」は保存分を優先する。
const NETWORK_FIRST = /(\.html|\.js|\.css|\.webmanifest|\/)$/;

self.addEventListener("fetch", event => {
  if (event.request.method !== "GET") return;
  const path = new URL(event.request.url).pathname;

  if (NETWORK_FIRST.test(path)) {
    event.respondWith(
      fetch(event.request).then(response => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, copy));
        return response;
      }).catch(() => caches.match(event.request, { ignoreSearch: true }))
    );
  } else {
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
  }
});

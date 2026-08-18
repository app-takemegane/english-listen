// サービスワーカー:アプリ全体を端末に保存し、オフラインでも動くようにする
// ファイルを追加・変更したら VERSION の数字を上げること(古い保存分が入れ替わる)
const VERSION = "v29";
const CACHE_NAME = `eigo-ehon-${VERSION}`;

// 絵本データを読み込み、保存するファイルの一覧を本文から自動で作る
importScripts("js/books.js");
importScripts("js/phonics.js");
const BOOK_FILES = [];
const WORD_KEY_SET = new Set();
BOOKS.forEach(book => {
  BOOK_FILES.push(`books/${book.id}/cover.svg`);
  book.pages.forEach((page, pi) => {
    BOOK_FILES.push(`books/${book.id}/p${pi + 1}.svg`);
    BOOK_FILES.push(`books/${book.id}/audio/p${pi + 1}.m4a`);
    // ページ内の単語クリップ(その位置の発音をそのまま切り出したもの。戻す場合に備えて保存も継続)
    page.text.split(" ").forEach((w, wi) => {
      BOOK_FILES.push(`books/${book.id}/clips/p${pi + 1}_w${wi}.m4a`);
      const key = wordKey(w);
      if (key) WORD_KEY_SET.add(key);
    });
  });
  (book.quiz || []).forEach((q, qi) => {
    BOOK_FILES.push(`books/${book.id}/quiz/q${qi + 1}.m4a`);
  });
});
// 単語単独の正しい読み(単語タップで鳴らす音声)
const WORD_FILES = [...WORD_KEY_SET].map(key => `words/${key}.m4a`);

// フォニックスの1音ずつの音声(音の表から自動で一覧を作る)
const PHONICS_FILES = Object.keys(PHONEME_IPA).map(key => `phonics/${key}.m4a`);

const FILES_TO_CACHE = [
  "./",
  "index.html",
  "css/style.css",
  "js/app.js",
  "js/books.js",
  "js/phonics.js",
  "js/timings.js",
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
  ...PHONICS_FILES,
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

// ══════════ 画面の要素 ══════════
const shelfView = document.getElementById("shelf-view");
const readerView = document.getElementById("reader-view");
const bookshelf = document.getElementById("bookshelf");
const levelTabs = document.getElementById("level-tabs");
const readerTitle = document.getElementById("reader-title");
const pageIndicator = document.getElementById("page-indicator");
const pageIllustration = document.getElementById("page-illustration");
const pageText = document.getElementById("page-text");
const btnBack = document.getElementById("btn-back");
const btnPrev = document.getElementById("btn-prev");
const btnNext = document.getElementById("btn-next");
const btnPlay = document.getElementById("btn-play");
const btnReplay = document.getElementById("btn-replay");
const btnAuto = document.getElementById("btn-auto");
const iconPlay = document.getElementById("icon-play");
const iconPause = document.getElementById("icon-pause");
const finishOverlay = document.getElementById("finish-overlay");
const btnJa = document.getElementById("btn-ja");
const confettiBox = document.getElementById("confetti");
const btnReadAgain = document.getElementById("btn-read-again");
const btnToShelf = document.getElementById("btn-to-shelf");

// ══════════ 状態 ══════════
let currentBook = null;
let currentPage = 0;
let autoMode = true; // 自動でページをめくる(よみきかせモード)
let wordSpans = [];
let wordTimings = []; // 各単語の開始時刻(秒)。音声の長さから推定する
const audio = new Audio(); // iPhoneでも連続再生できるよう、1つを使い回す
audio.preload = "auto";

// 効果音
const sfxPage = new Audio("sfx/page.m4a");
const sfxFinish = new Audio("sfx/finish.m4a");
sfxPage.volume = 0.5;
sfxFinish.volume = 0.6;

function playSfx(sfx) {
  try {
    sfx.currentTime = 0;
    const p = sfx.play();
    if (p) p.catch(() => {});
  } catch (e) { /* 効果音が鳴らなくても本編は続ける */ }
}

// iPhoneは「利用者が画面を触ったとき」しか新しい音を鳴らし始められないため、
// 最初のタップの瞬間に効果音を一度だけ無音で慣らしておく
let sfxUnlocked = false;
document.addEventListener("touchend", () => {
  if (sfxUnlocked) return;
  sfxUnlocked = true;
  [sfxPage, sfxFinish].forEach(sfx => {
    const vol = sfx.volume;
    sfx.volume = 0;
    const p = sfx.play();
    if (p) p.then(() => { sfx.pause(); sfx.currentTime = 0; sfx.volume = vol; })
           .catch(() => { sfx.volume = vol; });
  });
}, { once: true });

// 日本語訳の表示(端末ごとに設定を覚えておく)
let jaMode = false;
try { jaMode = localStorage.getItem("ja-mode") === "on"; } catch (e) {}

// ══════════ 本棚の表示 ══════════
function renderShelf(levelFilter) {
  bookshelf.innerHTML = "";
  BOOKS.filter(b => levelFilter === "all" || String(b.level) === levelFilter)
    .forEach(book => {
      const card = document.createElement("button");
      card.className = "book-card";
      card.innerHTML = `
        <div class="book-cover"><img src="${coverImage(book)}" alt=""></div>
        <div class="book-title-en">${book.titleEn}</div>
        <div class="book-title-ja">${book.titleJa}</div>
        <div class="book-meta">
          <span class="level-badge level-${book.level}">レベル${book.level}</span>
          <span class="pages-badge">${book.pages.length}ページ</span>
          ${isRead(book) ? '<span class="read-badge">⭐ よんだ!</span>' : ""}
        </div>`;
      card.addEventListener("click", () => openBook(book));
      bookshelf.appendChild(card);
    });
}

levelTabs.addEventListener("click", e => {
  const tab = e.target.closest(".tab");
  if (!tab) return;
  levelTabs.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
  tab.classList.add("active");
  renderShelf(tab.dataset.level);
});

// ══════════ えほんを開く・閉じる ══════════
function openBook(book) {
  currentBook = book;
  currentPage = 0;
  shelfView.classList.add("hidden");
  readerView.classList.remove("hidden");
  showPage(0);
}

function closeBook() {
  stopAudio();
  finishOverlay.classList.add("hidden");
  confettiBox.innerHTML = "";
  readerView.classList.add("hidden");
  shelfView.classList.remove("hidden");
  currentBook = null;
  // 「よんだ!」の印を反映するため本棚を描き直す
  const activeTab = levelTabs.querySelector(".tab.active");
  renderShelf(activeTab ? activeTab.dataset.level : "all");
}

btnBack.addEventListener("click", closeBook);
btnToShelf.addEventListener("click", closeBook);
btnReadAgain.addEventListener("click", () => {
  finishOverlay.classList.add("hidden");
  confettiBox.innerHTML = "";
  currentPage = 0;
  showPage(0);
  playAudio();
});

btnJa.addEventListener("click", () => {
  jaMode = !jaMode;
  try { localStorage.setItem("ja-mode", jaMode ? "on" : "off"); } catch (e) {}
  applyJaMode();
});

function applyJaMode() {
  readerView.classList.toggle("show-ja", jaMode);
  btnJa.classList.toggle("on", jaMode);
}

// ══════════ ページ表示 ══════════
function showPage(index) {
  stopAudio();
  currentPage = index;
  const book = currentBook;
  readerTitle.textContent = book.titleEn;
  pageIndicator.textContent = `${index + 1} / ${book.pages.length}`;
  pageIllustration.innerHTML = `<img src="${pageImage(book, index)}" alt="">`;

  // 英文を1単語ずつ <span> にして、読み上げに合わせて光らせる
  pageText.innerHTML = "";
  wordSpans = [];
  book.pages[index].text.split(" ").forEach((word, i) => {
    const span = document.createElement("span");
    span.className = "word";
    span.textContent = word;
    span.addEventListener("click", () => seekToWord(i));
    pageText.appendChild(span);
    pageText.appendChild(document.createTextNode(" "));
    wordSpans.push(span);
  });

  // 日本語訳(「あ」ボタンで表示・非表示)
  const ja = document.createElement("div");
  ja.className = "ja-text";
  ja.textContent = book.pages[index].textJa || "";
  pageText.appendChild(ja);

  btnPrev.classList.toggle("enabled", index > 0);
  btnNext.classList.toggle("enabled", index < book.pages.length - 1);

  audio.src = pageAudio(book, index);
  audio.load();
  wordTimings = [];
}

function goPrev() {
  if (currentPage > 0) {
    playSfx(sfxPage);
    showPage(currentPage - 1);
    playAudio();
  }
}
function goNext() {
  if (currentPage < currentBook.pages.length - 1) {
    playSfx(sfxPage);
    showPage(currentPage + 1);
    playAudio();
  } else {
    markAsRead(currentBook);
    showFinish();
  }
}

function showFinish() {
  spawnConfetti();
  finishOverlay.classList.remove("hidden");
  playSfx(sfxFinish);
}

function spawnConfetti() {
  confettiBox.innerHTML = "";
  const colors = ["#f7941d", "#ffd23f", "#7cb95c", "#4a9fd8", "#f06292", "#e5735c"];
  for (let i = 0; i < 40; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "%";
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = Math.random() * 0.8 + "s";
    piece.style.animationDuration = 2 + Math.random() * 1.5 + "s";
    piece.style.width = piece.style.height = 7 + Math.random() * 7 + "px";
    confettiBox.appendChild(piece);
  }
}

// ══════════ 読んだ記録(端末内にのみ保存) ══════════
function isRead(book) {
  try { return localStorage.getItem(`read-${book.id}`) !== null; }
  catch (e) { return false; }
}

function markAsRead(book) {
  try {
    const count = Number(localStorage.getItem(`read-${book.id}`) || 0) + 1;
    localStorage.setItem(`read-${book.id}`, String(count));
  } catch (e) { /* 保存できない端末でもアプリは動かす */ }
}

btnPrev.addEventListener("click", goPrev);
btnNext.addEventListener("click", goNext);

// スワイプでページめくり
let touchStartX = null;
readerView.addEventListener("touchstart", e => { touchStartX = e.touches[0].clientX; }, { passive: true });
readerView.addEventListener("touchend", e => {
  if (touchStartX === null) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  if (Math.abs(dx) < 60) return;
  if (dx < 0) goNext(); else goPrev();
}, { passive: true });

// ══════════ 音声の再生と単語ハイライト ══════════
function computeWordTimings() {
  // 音声全体の長さを、単語の文字数の割合で配分して、各単語の開始時刻を推定する
  const words = wordSpans.map(s => s.textContent);
  const weights = words.map(w => w.replace(/[^A-Za-z]/g, "").length + 1.5);
  const total = weights.reduce((a, b) => a + b, 0);
  const lead = 0.05, tail = 0.25; // 前後の無音ぶんを少し差し引く
  const usable = Math.max(audio.duration - lead - tail, 0.1);
  let t = lead;
  wordTimings = weights.map(w => {
    const start = t;
    t += (w / total) * usable;
    return start;
  });
}

function updateHighlight() {
  if (!wordTimings.length) return;
  const t = audio.currentTime;
  let active = -1;
  for (let i = 0; i < wordTimings.length; i++) {
    if (t >= wordTimings[i]) active = i;
  }
  wordSpans.forEach((s, i) => s.classList.toggle("active", i === active));
}

function seekToWord(i) {
  if (!wordTimings.length && audio.duration) computeWordTimings();
  if (!wordTimings.length) return;
  audio.currentTime = wordTimings[i];
  playAudio();
}

function playAudio() {
  const p = audio.play();
  if (p) p.catch(() => {}); // 読み込み前のタップは無視
}

function stopAudio() {
  audio.pause();
  audio.currentTime = 0;
  wordSpans.forEach(s => s.classList.remove("active"));
  setPlayIcon(false);
}

function setPlayIcon(playing) {
  iconPlay.classList.toggle("hidden", playing);
  iconPause.classList.toggle("hidden", !playing);
}

btnPlay.addEventListener("click", () => {
  if (audio.paused) playAudio(); else audio.pause();
});

btnReplay.addEventListener("click", () => {
  audio.currentTime = 0;
  playAudio();
});

btnAuto.addEventListener("click", () => {
  autoMode = !autoMode;
  btnAuto.classList.toggle("on", autoMode);
});

audio.addEventListener("loadedmetadata", computeWordTimings);
audio.addEventListener("timeupdate", updateHighlight);
audio.addEventListener("play", () => setPlayIcon(true));
audio.addEventListener("pause", () => setPlayIcon(false));
audio.addEventListener("ended", () => {
  wordSpans.forEach(s => s.classList.remove("active"));
  setPlayIcon(false);
  if (autoMode) setTimeout(goNext, 900);
});

// ══════════ 起動 ══════════
btnAuto.classList.toggle("on", autoMode);
applyJaMode();
renderShelf("all");

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js");
  // アプリが新しい版に入れ替わったら、画面を一度だけ自動で読み直す
  const hadController = !!navigator.serviceWorker.controller;
  let reloaded = false;
  navigator.serviceWorker.addEventListener("controllerchange", () => {
    if (hadController && !reloaded) {
      reloaded = true;
      location.reload();
    }
  });
}

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
  readerView.classList.add("hidden");
  shelfView.classList.remove("hidden");
  currentBook = null;
}

btnBack.addEventListener("click", closeBook);
btnToShelf.addEventListener("click", closeBook);
btnReadAgain.addEventListener("click", () => {
  finishOverlay.classList.add("hidden");
  currentPage = 0;
  showPage(0);
  playAudio();
});

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

  btnPrev.classList.toggle("enabled", index > 0);
  btnNext.classList.toggle("enabled", index < book.pages.length - 1);

  audio.src = pageAudio(book, index);
  audio.load();
  wordTimings = [];
}

function goPrev() { if (currentPage > 0) { showPage(currentPage - 1); playAudio(); } }
function goNext() {
  if (currentPage < currentBook.pages.length - 1) {
    showPage(currentPage + 1);
    playAudio();
  } else {
    finishOverlay.classList.remove("hidden");
  }
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
renderShelf("all");

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register("sw.js");
}

// ══════════ 画面の要素 ══════════
const views = {
  shelf: document.getElementById("shelf-view"),
  gacha: document.getElementById("gacha-view"),
  records: document.getElementById("records-view"),
  reader: document.getElementById("reader-view"),
  quiz: document.getElementById("quiz-view")
};
const bookshelf = document.getElementById("bookshelf");
const levelTabs = document.getElementById("level-tabs");
const mascotMessage = document.getElementById("mascot-message");
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
const btnJa = document.getElementById("btn-ja");
const iconPlay = document.getElementById("icon-play");
const iconPause = document.getElementById("icon-pause");
const finishOverlay = document.getElementById("finish-overlay");
const confettiBox = document.getElementById("confetti");
const btnFinishQuiz = document.getElementById("btn-finish-quiz");
const btnReadAgain = document.getElementById("btn-read-again");
const btnToShelf = document.getElementById("btn-to-shelf");
// モード選択
const modeOverlay = document.getElementById("mode-overlay");
const modeCover = document.getElementById("mode-cover");
const modeTitleEn = document.getElementById("mode-title-en");
const modeTitleJa = document.getElementById("mode-title-ja");
const btnModeListen = document.getElementById("btn-mode-listen");
const btnModeSpeak = document.getElementById("btn-mode-speak");
const btnModeQuiz = document.getElementById("btn-mode-quiz");
// はなすモード
const speakBar = document.getElementById("speak-bar");
const speakFeedback = document.getElementById("speak-feedback");
const btnRecord = document.getElementById("btn-record");
const btnPlayMine = document.getElementById("btn-play-mine");
const finishJaText = document.getElementById("finish-ja-text");
const btnModeClose = document.getElementById("btn-mode-close");
// クイズ
const btnQuizBack = document.getElementById("btn-quiz-back");
const quizProgress = document.getElementById("quiz-progress");
const btnQuizSound = document.getElementById("btn-quiz-sound");
const quizQuestion = document.getElementById("quiz-question");
const quizChoices = document.getElementById("quiz-choices");
const quizFeedback = document.getElementById("quiz-feedback");
const quizResultOverlay = document.getElementById("quiz-result-overlay");
const quizConfetti = document.getElementById("quiz-confetti");
const quizResultStars = document.getElementById("quiz-result-stars");
const quizResultEn = document.getElementById("quiz-result-en");
const quizResultJa = document.getElementById("quiz-result-ja");
const btnQuizAgain = document.getElementById("btn-quiz-again");
const btnQuizToShelf = document.getElementById("btn-quiz-to-shelf");
// ガチャ
const gachaMachine = document.getElementById("gacha-machine");
const btnGacha = document.getElementById("btn-gacha");
const cardGrid = document.getElementById("card-grid");
const cardCount = document.getElementById("card-count");
const gachaOverlay = document.getElementById("gacha-overlay");
const gachaConfetti = document.getElementById("gacha-confetti");
const gachaCard = document.getElementById("gacha-card");
const gachaCardNameEn = document.getElementById("gacha-card-name-en");
const gachaCardNameJa = document.getElementById("gacha-card-name-ja");
const btnGachaClose = document.getElementById("btn-gacha-close");
const recordsMain = document.getElementById("records-main");

// ══════════ 保存データ(この端末の中だけ) ══════════
function loadNum(key) {
  try { return Number(localStorage.getItem(key) || 0); } catch (e) { return 0; }
}
function saveNum(key, value) {
  try { localStorage.setItem(key, String(value)); } catch (e) {}
}
function loadJson(key) {
  try { return JSON.parse(localStorage.getItem(key) || "{}"); } catch (e) { return {}; }
}
function saveJson(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) {}
}

let coins = loadNum("coins");
let ownedCards = loadJson("cards"); // { カードid: 持っている枚数 }

function addCoins(n) {
  coins += n;
  saveNum("coins", coins);
  updateCoinDisplays();
}

function updateCoinDisplays() {
  ["coin-count", "coin-count-gacha", "coin-count-records"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.textContent = coins;
  });
  btnGacha.disabled = coins < GACHA_COST;
}

// ══════════ 状態 ══════════
let currentBook = null;
let currentPage = 0;
let autoMode = true; // 自動でページをめくる(よみきかせモード)
let speakMode = false; // はなすモード(録音して聞き比べ)
let practicingWord = false; // 1単語だけの練習中か
let wordSpans = [];
let wordTimings = []; // 各単語の開始時刻(秒)。音声の長さから推定する
const audio = new Audio(); // iPhoneでも連続再生できるよう、1つを使い回す
audio.preload = "auto";

// 効果音
const sfxPage = new Audio("sfx/page.m4a");
const sfxFinish = new Audio("sfx/finish.m4a");
const sfxCorrect = new Audio("sfx/correct.m4a");
const sfxWrong = new Audio("sfx/wrong.m4a");
const sfxCoin = new Audio("sfx/coin.m4a");
sfxPage.volume = 0.5;
sfxFinish.volume = 0.6;
sfxCorrect.volume = 0.55;
sfxWrong.volume = 0.45;
sfxCoin.volume = 0.5;
const ALL_SFX = [sfxPage, sfxFinish, sfxCorrect, sfxWrong, sfxCoin];

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
  ALL_SFX.forEach(sfx => {
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

// ══════════ 再生の速さ(文と単語で別々に覚えておく) ══════════
let pageRate = 1;
let wordRate = 1;
try {
  pageRate = parseFloat(localStorage.getItem("speed-page")) || 1;
  wordRate = parseFloat(localStorage.getItem("speed-word")) || 1;
} catch (e) {}

// 速さを変えても声の高さが変わらないようにする
audio.preservesPitch = true;
if ("webkitPreservesPitch" in audio) audio.webkitPreservesPitch = true;

function applyPlaybackRate() {
  audio.playbackRate = practicingWord ? wordRate : pageRate;
}

function setupSpeedButtons(containerId, storageKey, getRate, setRate) {
  const box = document.getElementById(containerId);
  const buttons = box.querySelectorAll("button");
  buttons.forEach(btn => {
    btn.classList.toggle("on", parseFloat(btn.dataset.rate) === getRate());
    btn.addEventListener("click", () => {
      setRate(parseFloat(btn.dataset.rate));
      try { localStorage.setItem(storageKey, btn.dataset.rate); } catch (e) {}
      buttons.forEach(b => b.classList.toggle("on", b === btn));
      applyPlaybackRate(); // 再生中でもすぐ反映
    });
  });
}
setupSpeedButtons("page-speed", "speed-page", () => pageRate, r => { pageRate = r; });
setupSpeedButtons("word-speed", "speed-word", () => wordRate, r => { wordRate = r; });

// ══════════ 画面の切り替え ══════════
function showView(name) {
  Object.keys(views).forEach(key => views[key].classList.toggle("hidden", key !== name));
  if (name === "shelf") {
    const activeTab = levelTabs.querySelector(".tab.active");
    renderShelf(activeTab ? activeTab.dataset.level : "all");
  }
  if (name === "gacha") renderCardGrid();
  if (name === "records") renderRecords();
  updateCoinDisplays();
}

document.querySelectorAll(".tab-bar .tab-item").forEach(btn => {
  btn.addEventListener("click", () => showView(btn.dataset.view));
});

// ══════════ 本棚の表示 ══════════
const MASCOT_LINES = [
  "きょうは どの えほんに する?",
  "Hello! いっしょに よもう!",
  "クイズも まってるよ!",
  "コインを あつめて ガチャを まわそう!"
];

function renderShelf(levelFilter) {
  mascotMessage.textContent = MASCOT_LINES[Math.floor(Math.random() * MASCOT_LINES.length)];
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
      card.addEventListener("click", () => openModeSelect(book));
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

// ══════════ モード選択(よみきかせ / クイズ) ══════════
let selectedBook = null;

function openModeSelect(book) {
  selectedBook = book;
  modeCover.src = coverImage(book);
  modeTitleEn.textContent = book.titleEn;
  modeTitleJa.textContent = book.titleJa;
  modeOverlay.classList.remove("hidden");
}

btnModeClose.addEventListener("click", () => modeOverlay.classList.add("hidden"));
modeOverlay.addEventListener("click", e => {
  if (e.target === modeOverlay) modeOverlay.classList.add("hidden");
});
btnModeListen.addEventListener("click", () => {
  modeOverlay.classList.add("hidden");
  openBook(selectedBook, "listen");
});
btnModeSpeak.addEventListener("click", () => {
  modeOverlay.classList.add("hidden");
  openBook(selectedBook, "speak");
});
btnModeQuiz.addEventListener("click", () => {
  modeOverlay.classList.add("hidden");
  startQuiz(selectedBook);
});

// ══════════ えほんを開く・閉じる ══════════
function openBook(book, mode) {
  currentBook = book;
  currentPage = 0;
  speakMode = mode === "speak";
  speakBar.classList.toggle("hidden", !speakMode);
  btnAuto.classList.toggle("hidden", speakMode); // はなすモードは自分のペースでめくる
  showView("reader");
  showPage(0);
}

function closeBook() {
  stopAudio();
  stopRecordingHardware();
  finishOverlay.classList.add("hidden");
  confettiBox.innerHTML = "";
  currentBook = null;
  showView("shelf");
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
btnFinishQuiz.addEventListener("click", () => {
  const book = currentBook;
  stopAudio();
  finishOverlay.classList.add("hidden");
  confettiBox.innerHTML = "";
  startQuiz(book);
});

btnJa.addEventListener("click", () => {
  jaMode = !jaMode;
  try { localStorage.setItem("ja-mode", jaMode ? "on" : "off"); } catch (e) {}
  applyJaMode();
});

function applyJaMode() {
  views.reader.classList.toggle("show-ja", jaMode);
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
    // よみきかせ中はその単語から聞き直し、はなすモードは1単語だけの練習
    span.addEventListener("click", () => {
      if (speakMode) practiceWord(word, span, i); else seekToWord(i);
    });
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

  // ハイライトの時刻:実測の時刻表があればそれを使う(なければ後で推定)
  wordTimings = [];
  if (typeof TIMINGS !== "undefined" && TIMINGS[book.id] && TIMINGS[book.id][index]) {
    wordTimings = TIMINGS[book.id][index].starts.slice();
  }

  if (speakMode) speakResetForPage();
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
  // はなすモードはがんばりが大きいのでコイン2枚
  const reward = speakMode ? 2 : 1;
  addCoins(reward);
  finishJaText.textContent = speakMode
    ? `さいごまで いえたね! 🪙コインを ${reward}まい ゲット!`
    : `さいごまで よめたね! 🪙コインを ${reward}まい ゲット!`;
  spawnConfetti(confettiBox);
  finishOverlay.classList.remove("hidden");
  playSfx(sfxFinish);
}

function spawnConfetti(box) {
  box.innerHTML = "";
  const colors = ["#f7941d", "#ffd23f", "#7cb95c", "#4a9fd8", "#f06292", "#e5735c"];
  for (let i = 0; i < 40; i++) {
    const piece = document.createElement("span");
    piece.className = "confetti-piece";
    piece.style.left = Math.random() * 100 + "%";
    piece.style.background = colors[i % colors.length];
    piece.style.animationDelay = Math.random() * 0.8 + "s";
    piece.style.animationDuration = 2 + Math.random() * 1.5 + "s";
    piece.style.width = piece.style.height = 7 + Math.random() * 7 + "px";
    box.appendChild(piece);
  }
}

// ══════════ 読んだ記録 ══════════
function isRead(book) {
  return loadNum(`read-${book.id}`) > 0;
}
function markAsRead(book) {
  saveNum(`read-${book.id}`, loadNum(`read-${book.id}`) + 1);
}

btnPrev.addEventListener("click", goPrev);
btnNext.addEventListener("click", goNext);

// スワイプでページめくり
let touchStartX = null;
views.reader.addEventListener("touchstart", e => { touchStartX = e.touches[0].clientX; }, { passive: true });
views.reader.addEventListener("touchend", e => {
  if (touchStartX === null) return;
  const dx = e.changedTouches[0].clientX - touchStartX;
  touchStartX = null;
  if (Math.abs(dx) < 60) return;
  if (dx < 0) goNext(); else goPrev();
}, { passive: true });

// ══════════ 音声の再生と単語ハイライト ══════════
// ══════════ 1単語ずつの発音練習(はなすモードで単語をタップ) ══════════
// その文のその場所の発音をそのまま切り出したクリップを鳴らす
function practiceWord(word, span, wordIndex) {
  if (!wordKey(word)) return;
  practicingWord = true;
  wordTimings = []; // 文のハイライトは動かさない
  wordSpans.forEach(s => s.classList.remove("active", "practice"));
  span.classList.add("practice");
  const clean = word.replace(/[^A-Za-z']/g, "");
  speakFeedback.textContent = `「${clean}」だけ れんしゅう! おなじように いって ろくおんしてみよう`;
  // 辞書にある単語はフォニックスカードを開く(1もじずつ→つなげて、の順に鳴る)
  if (openPhonics(word, wordIndex)) return;
  audio.src = clipAudio(currentBook, currentPage, wordIndex);
  playAudio();
}

// ══════════ フォニックスカード(1もじずつの発音と文字の強調) ══════════
const phonicsOverlay = document.getElementById("phonics-overlay");
const phonicsWordBox = document.getElementById("phonics-word");
const phonicsIpaBox = document.getElementById("phonics-ipa");
const btnPhonicsSound = document.getElementById("btn-phonics-sound");
const btnPhonicsWord = document.getElementById("btn-phonics-word");
const btnPhonicsClose = document.getElementById("btn-phonics-close");

let phonicsChunks = [];   // 文字のまとまりごとの部品 { el, sounds }
let phonicsWordClip = ""; // その単語まるごとのクリップ
let phonicsSeq = 0;       // 再生のやり直し・中断を見分ける番号

function phonemeAudio(key) { return `phonics/${key}.m4a`; }
const soundList = s => (Array.isArray(s) ? s : [s]);
const soundIpa = s => soundList(s).map(k => PHONEME_IPA[k]).join("");

// フォニックスカードを開く(辞書にない単語なら false を返して今まで通りの再生)
function openPhonics(word, wordIndex) {
  const entry = PHONICS[wordKey(word)];
  if (!entry) return false;
  phonicsWordClip = clipAudio(currentBook, currentPage, wordIndex);
  phonicsWordBox.innerHTML = "";
  phonicsChunks = entry.map(([letters, sound]) => {
    const el = document.createElement("button");
    const vowel = sound && soundList(sound).some(k => VOWEL_SOUNDS.includes(k));
    el.className = "ph-chunk" + (sound ? (vowel ? " vowel" : "") : " silent");
    el.innerHTML = `<span class="ph-g">${letters}</span>` +
      `<span class="ph-s">${sound ? soundIpa(sound) : "よまない"}</span>`;
    const item = { el, sounds: sound ? soundList(sound) : null };
    el.addEventListener("click", () => playPhonicsChunk(item));
    phonicsWordBox.appendChild(el);
    return item;
  });
  phonicsIpaBox.textContent = "/" + entry.map(([, s]) => (s ? soundIpa(s) : "")).join("") + "/";
  phonicsOverlay.classList.remove("hidden");
  playPhonicsSequence();
  return true;
}

function closePhonics(silent) {
  phonicsSeq++; // 再生中の流れを止める
  if (phonicsOverlay.classList.contains("hidden")) return;
  phonicsOverlay.classList.add("hidden");
  if (!silent) {
    audio.pause();
    speakFeedback.textContent = "ろくおんして じぶんの こえと くらべてみよう!(たんごタップで もういちど)";
  }
}

function highlightChunk(target) {
  phonicsChunks.forEach(c => {
    c.el.classList.toggle("now", c === target);
    c.el.classList.remove("blend");
  });
}

function blendHighlight(on) {
  phonicsChunks.forEach(c => {
    c.el.classList.remove("now");
    c.el.classList.toggle("blend", on);
  });
}

const phWait = ms => new Promise(resolve => setTimeout(resolve, ms));

// 1ファイル再生して終わるまで待つ(中断されて止まったときも戻ってくる)
function phPlay(src) {
  return new Promise(resolve => {
    const done = () => {
      audio.removeEventListener("ended", done);
      audio.removeEventListener("pause", done);
      resolve();
    };
    audio.addEventListener("ended", done);
    audio.addEventListener("pause", done);
    audio.src = src;
    applyPlaybackRate();
    const p = audio.play();
    if (p) p.catch(done);
  });
}

// 1もじずつ(読んでいる文字を強調)→ さいごに つなげて単語まるごと
async function playPhonicsSequence() {
  const seq = ++phonicsSeq;
  for (const item of phonicsChunks) {
    if (seq !== phonicsSeq) return;
    highlightChunk(item);
    if (item.sounds) {
      for (const key of item.sounds) {
        if (seq !== phonicsSeq) return;
        await phPlay(phonemeAudio(key));
      }
      await phWait(280);
    } else {
      await phWait(750); // よまない文字は音を出さずに見せるだけ
    }
  }
  if (seq !== phonicsSeq) return;
  highlightChunk(null);
  await phWait(400);
  if (seq !== phonicsSeq) return;
  blendHighlight(true); // つなげて読むあいだは全体をほんのり光らせる
  await phPlay(phonicsWordClip);
  if (seq === phonicsSeq) blendHighlight(false);
}

// 文字を1つタップしたら、その音だけ鳴らす
async function playPhonicsChunk(item) {
  const seq = ++phonicsSeq;
  highlightChunk(item);
  if (item.sounds) {
    for (const key of item.sounds) {
      if (seq !== phonicsSeq) return;
      await phPlay(phonemeAudio(key));
    }
  } else {
    await phWait(600);
  }
  if (seq === phonicsSeq) highlightChunk(null);
}

async function playPhonicsWord() {
  const seq = ++phonicsSeq;
  blendHighlight(true);
  await phPlay(phonicsWordClip);
  if (seq === phonicsSeq) blendHighlight(false);
}

btnPhonicsSound.addEventListener("click", playPhonicsSequence);
btnPhonicsWord.addEventListener("click", playPhonicsWord);
btnPhonicsClose.addEventListener("click", () => closePhonics(false));
phonicsOverlay.addEventListener("click", e => {
  if (e.target === phonicsOverlay) closePhonics(false);
});

// 単語練習のあと、再生ボタンでページ全体の読み上げに戻す
function restorePageAudio() {
  if (!practicingWord) return;
  practicingWord = false;
  wordSpans.forEach(s => s.classList.remove("practice"));
  if (currentBook) {
    audio.src = pageAudio(currentBook, currentPage);
    audio.load();
    wordTimings = [];
    if (typeof TIMINGS !== "undefined" && TIMINGS[currentBook.id] && TIMINGS[currentBook.id][currentPage]) {
      wordTimings = TIMINGS[currentBook.id][currentPage].starts.slice();
    }
  }
}

function computeWordTimings() {
  if (!currentBook || practicingWord) return;
  if (wordTimings.length) return; // 実測の時刻表があるときは推定しない
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
  applyPlaybackRate();
  const p = audio.play();
  if (p) p.catch(() => {}); // 読み込み前のタップは無視
}

function stopAudio() {
  closePhonics(true); // フォニックスカードが開いていたら閉じて流れを止める
  audio.pause();
  audio.currentTime = 0;
  practicingWord = false;
  wordSpans.forEach(s => s.classList.remove("active", "practice"));
  setPlayIcon(false);
}

function setPlayIcon(playing) {
  iconPlay.classList.toggle("hidden", playing);
  iconPause.classList.toggle("hidden", !playing);
}

btnPlay.addEventListener("click", () => {
  restorePageAudio();
  if (audio.paused) playAudio(); else audio.pause();
});

btnReplay.addEventListener("click", () => {
  restorePageAudio();
  audio.currentTime = 0;
  playAudio();
});

btnAuto.addEventListener("click", () => {
  autoMode = !autoMode;
  btnAuto.classList.toggle("on", autoMode);
});

audio.addEventListener("loadedmetadata", computeWordTimings);
audio.addEventListener("timeupdate", updateHighlight);
audio.addEventListener("play", () => { if (currentBook) setPlayIcon(true); });
audio.addEventListener("pause", () => setPlayIcon(false));
audio.addEventListener("ended", () => {
  if (!currentBook) return; // クイズの問題読み上げのときは何もしない
  wordSpans.forEach(s => s.classList.remove("active"));
  setPlayIcon(false);
  if (practicingWord) {
    speakFeedback.textContent = "ろくおんして じぶんの こえと くらべてみよう!(もういちど タップで きける)";
    return;
  }
  if (speakMode) return; // はなすモードは自動でめくらない
  if (autoMode && !views.reader.classList.contains("hidden")) setTimeout(goNext, 900);
});

// ══════════ はなすモード(自分の声を録音して聞き比べ) ══════════
// iPhoneの録音部品(MediaRecorder)は2回目以降に壊れる不具合があるため、
// マイクから届く「音の生データ」を直接ためて、そのまま直接鳴らす方式にしている
let recStream = null;        // マイク
let recCtx = null;           // 録音用の音声処理
let recNodes = null;         // 録音中の部品(あとで確実に外すため)
let recBuffers = [];         // ためた生データ
let recSampleRate = 0;
let recording = false;
let recTimer = null;
let recordings = {};         // ページごとの録音 { ページ番号: { pcm, sampleRate } }
let playCtx = null;          // 自分の声の再生用

// iPhone 17以降にある「音の通り道」の設定。録音中だけ録音向き、ふだんは再生向きにする
function setAudioSession(type) {
  try {
    if (navigator.audioSession) navigator.audioSession.type = type;
  } catch (e) {}
}

function speakResetForPage() {
  if (recording) stopRecording(true);
  const has = !!recordings[currentPage];
  btnPlayMine.disabled = !has;
  speakFeedback.textContent = has
    ? "もういちど いっても、つぎの ページに いっても いいよ!"
    : "おてほんを きいて まねしてみよう! たんごを タップすると 1たんごずつ れんしゅうできるよ";
}

function releaseMic() {
  if (recStream) {
    recStream.getTracks().forEach(t => t.stop());
    recStream = null;
  }
}

function cleanupRecording() {
  clearTimeout(recTimer);
  recording = false;
  btnRecord.classList.remove("recording");
  btnRecord.textContent = "🎤 ろくおん";
  if (recNodes) {
    try {
      recNodes.processor.disconnect();
      recNodes.source.disconnect();
      recNodes.gain.disconnect();
    } catch (e) {}
    recNodes = null;
  }
  if (recCtx) {
    try { recCtx.close(); } catch (e) {}
    recCtx = null;
  }
  releaseMic();
  setAudioSession("playback");
}

async function toggleRecord() {
  if (recording) {
    stopRecording(false);
    return;
  }
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    speakFeedback.textContent = "この ひらきかたでは マイクが つかえないよ(ブラウザ非対応)";
    return;
  }
  audio.pause();
  stopMyVoice();
  setAudioSession("play-and-record");
  try {
    recStream = await navigator.mediaDevices.getUserMedia({ audio: true });
  } catch (e) {
    setAudioSession("playback");
    if (e && e.name === "NotAllowedError") {
      speakFeedback.textContent = "マイクが「きょか しない」に なっているよ。せっていで ゆるしてね(NotAllowed)";
    } else {
      speakFeedback.textContent = `マイクが つかえないよ(${(e && e.name) || "エラー"})`;
    }
    return;
  }
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    recCtx = new Ctx(); // マイクがつながった後に作ると、録音向けの設定で動く
    if (recCtx.state === "suspended") recCtx.resume();
    recSampleRate = recCtx.sampleRate;
    recBuffers = [];
    const source = recCtx.createMediaStreamSource(recStream);
    const processor = recCtx.createScriptProcessor(4096, 1, 1);
    const gain = recCtx.createGain();
    gain.gain.value = 0; // 自分の声がその場で響かないように音は出さない
    processor.onaudioprocess = e => {
      if (recording) recBuffers.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(gain);
    gain.connect(recCtx.destination);
    recNodes = { source, processor, gain };
  } catch (e) {
    cleanupRecording();
    speakFeedback.textContent = `ろくおんの じゅんびに しっぱいしたよ(${(e && e.name) || "エラー"})`;
    return;
  }
  recording = true;
  btnRecord.classList.add("recording");
  btnRecord.textContent = "⏹ とめる";
  speakFeedback.textContent = "ろくおんちゅう... おわったら もういちど おしてね";
  recTimer = setTimeout(() => stopRecording(false), 12000); // 長くても12秒で自動停止
}

function stopRecording(silent) {
  const buffers = recBuffers;
  const rate = recSampleRate;
  recBuffers = [];
  cleanupRecording();
  if (silent) return;

  const total = buffers.reduce((sum, b) => sum + b.length, 0);
  if (!rate || total < rate * 0.3) { // 0.3秒未満は失敗あつかい
    speakFeedback.textContent = "うまく ろくおんできなかったよ。もういちど ためしてね";
    return;
  }
  const pcm = new Float32Array(total);
  let pos = 0;
  buffers.forEach(b => { pcm.set(b, pos); pos += b.length; });
  recordings[currentPage] = { pcm, sampleRate: rate };
  btnPlayMine.disabled = false;
  speakFeedback.textContent = "Great! いえたね! じぶんの こえを きいてみよう";
  playSfx(sfxCorrect);
}

btnRecord.addEventListener("click", toggleRecord);

function stopMyVoice() {
  if (playCtx) {
    try { playCtx.close(); } catch (e) {}
    playCtx = null;
  }
}

// 自分の声の再生:ためた生データをそのまま鳴らす(変換なし・確実)
btnPlayMine.addEventListener("click", () => {
  const rec = recordings[currentPage];
  if (!rec) return;
  audio.pause();
  setAudioSession("playback");
  stopMyVoice();
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    playCtx = new Ctx();
    if (playCtx.state === "suspended") playCtx.resume();
    const buf = playCtx.createBuffer(1, rec.pcm.length, rec.sampleRate);
    buf.getChannelData(0).set(rec.pcm);
    const src = playCtx.createBufferSource();
    src.buffer = buf;
    src.connect(playCtx.destination);
    const seconds = (rec.pcm.length / rec.sampleRate).toFixed(1);
    speakFeedback.textContent = `さいせいちゅう(${seconds}びょう)... おてほんと くらべてみよう`;
    src.onended = () => {
      stopMyVoice();
      speakFeedback.textContent = "もういちど いっても、つぎの ページに いっても いいよ!";
    };
    src.start();
  } catch (e) {
    speakFeedback.textContent = `さいせいできなかったよ(${(e && e.name) || "エラー"})`;
  }
});

function stopRecordingHardware() {
  if (recording) stopRecording(true); else cleanupRecording();
  stopMyVoice();
  recordings = {};
}

// ══════════ クイズ ══════════
let quizBook = null;
let quizIndex = 0;
let quizScore = 0;
let quizAnswered = false;

function startQuiz(book) {
  quizBook = book;
  quizIndex = 0;
  quizScore = 0;
  currentBook = null; // リーダーの自動めくりを止める
  stopAudio();
  quizResultOverlay.classList.add("hidden");
  quizConfetti.innerHTML = "";
  showView("quiz");
  renderQuizQuestion();
}

function renderQuizQuestion() {
  const q = quizBook.quiz[quizIndex];
  quizAnswered = false;
  quizProgress.textContent = `${quizIndex + 1} / ${quizBook.quiz.length}`;
  quizQuestion.textContent = q.q;
  quizFeedback.textContent = "";
  quizFeedback.className = "quiz-feedback";
  quizChoices.innerHTML = "";
  q.choices.forEach((choice, i) => {
    const btn = document.createElement("button");
    btn.className = "quiz-choice";
    btn.textContent = choice;
    btn.addEventListener("click", () => answerQuiz(i, btn));
    quizChoices.appendChild(btn);
  });
  playQuizAudio();
}

function playQuizAudio() {
  audio.src = quizAudio(quizBook, quizIndex);
  playAudio();
}

btnQuizSound.addEventListener("click", playQuizAudio);

function answerQuiz(choiceIndex, btn) {
  if (quizAnswered) return;
  quizAnswered = true;
  const q = quizBook.quiz[quizIndex];
  const buttons = quizChoices.querySelectorAll(".quiz-choice");
  buttons.forEach(b => b.classList.add("locked"));

  if (choiceIndex === q.answer) {
    quizScore++;
    btn.classList.add("correct");
    quizFeedback.textContent = "That's right! せいかい! 🪙+1";
    quizFeedback.classList.add("good");
    playSfx(sfxCorrect);
    addCoins(1);
  } else {
    btn.classList.add("wrong");
    buttons[q.answer].classList.add("correct");
    quizFeedback.textContent = `こたえは「${q.choices[q.answer]}」だよ`;
    quizFeedback.classList.add("bad");
    playSfx(sfxWrong);
  }

  setTimeout(() => {
    if (quizIndex < quizBook.quiz.length - 1) {
      quizIndex++;
      renderQuizQuestion();
    } else {
      showQuizResult();
    }
  }, 1600);
}

function showQuizResult() {
  const total = quizBook.quiz.length;
  const best = loadNum(`quiz-best-${quizBook.id}`);
  if (quizScore > best) saveNum(`quiz-best-${quizBook.id}`, quizScore);

  quizResultStars.textContent = "⭐️".repeat(Math.max(quizScore, 1));
  quizResultEn.textContent = ["Nice try!", "Good try!", "Great!", "Perfect!"][quizScore] || "Great!";
  quizResultJa.textContent = `${total}もん中 ${quizScore}もん せいかい! コインを ${quizScore}まい ゲット!`;
  if (quizScore === total) {
    spawnConfetti(quizConfetti);
    playSfx(sfxFinish);
  } else {
    playSfx(sfxCoin);
  }
  quizResultOverlay.classList.remove("hidden");
}

btnQuizBack.addEventListener("click", () => { stopAudio(); showView("shelf"); });
btnQuizToShelf.addEventListener("click", () => {
  quizResultOverlay.classList.add("hidden");
  showView("shelf");
});
btnQuizAgain.addEventListener("click", () => startQuiz(quizBook));

// ══════════ ガチャ ══════════
btnGacha.addEventListener("click", () => {
  if (coins < GACHA_COST) return;
  addCoins(-GACHA_COST);
  btnGacha.disabled = true;
  gachaMachine.classList.add("shaking");
  playSfx(sfxCoin);

  setTimeout(() => {
    gachaMachine.classList.remove("shaking");
    const card = CARDS[Math.floor(Math.random() * CARDS.length)];
    ownedCards[card.id] = (ownedCards[card.id] || 0) + 1;
    saveJson("cards", ownedCards);
    gachaCard.innerHTML = cardSvgHtml(card, 130);
    gachaCardNameEn.textContent = card.nameEn;
    gachaCardNameJa.textContent = card.nameJa;
    spawnConfetti(gachaConfetti);
    playSfx(sfxFinish);
    gachaOverlay.classList.remove("hidden");
    renderCardGrid();
    updateCoinDisplays();
  }, 1000);
});

btnGachaClose.addEventListener("click", () => {
  gachaOverlay.classList.add("hidden");
  gachaConfetti.innerHTML = "";
});

function renderCardGrid() {
  cardGrid.innerHTML = "";
  let owned = 0;
  CARDS.forEach(card => {
    const count = ownedCards[card.id] || 0;
    if (count > 0) owned++;
    const cell = document.createElement("div");
    cell.className = "card-cell" + (count > 0 ? "" : " unowned");
    cell.innerHTML = count > 0
      ? `${cardSvgHtml(card, 64)}
         <div class="card-name-en">${card.nameEn}</div>
         <div class="card-name-ja">${card.nameJa}</div>
         ${count > 1 ? `<div class="card-dup">×${count}</div>` : ""}`
      : `<div class="card-mystery">?</div><div class="card-name-ja">まだだよ</div>`;
    cardGrid.appendChild(cell);
  });
  cardCount.textContent = owned;
}

// ══════════ きろく ══════════
function renderRecords() {
  const ownedCount = CARDS.filter(c => (ownedCards[c.id] || 0) > 0).length;
  let html = `
    <div class="record-summary">
      <div class="record-box"><div class="record-num">${BOOKS.filter(isRead).length}</div><div>よんだ えほん</div></div>
      <div class="record-box"><div class="record-num">${coins}</div><div>もっている コイン</div></div>
      <div class="record-box"><div class="record-num">${ownedCount}/8</div><div>あつめた カード</div></div>
    </div>
    <h3 class="records-title">えほんの きろく</h3>`;
  BOOKS.forEach(book => {
    const reads = loadNum(`read-${book.id}`);
    const best = loadNum(`quiz-best-${book.id}`);
    html += `
      <div class="record-row">
        <img src="${coverImage(book)}" alt="">
        <div class="record-info">
          <div class="record-title">${book.titleEn}</div>
          <div class="record-detail">よんだ かいすう:${reads}かい / クイズ さいこう:${best}/${book.quiz.length}もん</div>
        </div>
        ${reads > 0 ? '<span class="read-badge">⭐</span>' : ""}
      </div>`;
  });
  recordsMain.innerHTML = html;
}

// ══════════ 起動 ══════════
btnAuto.classList.toggle("on", autoMode);
applyJaMode();
updateCoinDisplays();
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

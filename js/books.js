// 絵本データ:あとから本を増やすときは、この配列に追加するだけでよい
// audio は差し替え可能(ネイティブ録音ができたら同じファイル名で置き換える)
// textJa は「あ」ボタンで表示できる日本語訳
const BOOKS = [
  {
    id: "sun",
    titleEn: "Good Morning, Sun!",
    titleJa: "おはよう、おひさま!",
    level: 1,
    pages: [
      { text: "The sun comes up. Good morning, sun!",
        textJa: "おひさまが のぼったよ。おはよう、おひさま!" },
      { text: "A bird sings on the tree. Good morning, bird!",
        textJa: "ことりが きのうえで うたっているよ。おはよう、ことり!" },
      { text: "A cat wakes up. Good morning, cat!",
        textJa: "ねこが めを さましたよ。おはよう、ねこさん!" },
      { text: "A flower opens. Good morning, flower!",
        textJa: "おはなが ひらいたよ。おはよう、おはな!" },
      { text: "I wake up and smile. Good morning, everyone!",
        textJa: "わたしも おきて にっこり。おはよう、みんな!" },
      { text: "It is a happy new day!",
        textJa: "たのしい いちにちの はじまり!" }
    ]
  },
  {
    id: "cat",
    titleEn: "The Hungry Cat",
    titleJa: "おなかぺこぺこ ねこちゃん",
    level: 1,
    pages: [
      { text: "Momo the cat is very hungry.",
        textJa: "ねこの モモは おなかが ぺこぺこ。" },
      { text: "She looks in the kitchen. No food!",
        textJa: "だいどころを さがしたよ。たべものが ない!" },
      { text: "She looks in the garden. No food!",
        textJa: "おにわを さがしたよ。たべものが ない!" },
      { text: "She sees a little fish in the pond.",
        textJa: "いけの なかに ちいさな さかなを みつけたよ。" },
      { text: "Splash! The fish swims away.",
        textJa: "ぱしゃん! さかなは およいで いっちゃった。" },
      { text: "Mom gives Momo some milk. Yum, yum! Momo is happy.",
        textJa: "おかあさんが ミルクを くれたよ。おいしいね! モモは ごきげん。" }
    ]
  },
  {
    id: "colors",
    titleEn: "What Color Is It?",
    titleJa: "なにいろかな?",
    level: 1,
    pages: [
      { text: "Look! A red apple.",
        textJa: "みてみて! あかい りんご。" },
      { text: "Look! A yellow banana.",
        textJa: "みてみて! きいろい バナナ。" },
      { text: "Look! A green frog.",
        textJa: "みてみて! みどりの かえる。" },
      { text: "Look! A blue bird.",
        textJa: "みてみて! あおい とり。" },
      { text: "Look! A pink flower.",
        textJa: "みてみて! ピンクの おはな。" },
      { text: "Red, yellow, green, blue, and pink. I love colors!",
        textJa: "あか、きいろ、みどり、あお、ピンク。いろって だいすき!" }
    ]
  },
  {
    id: "park",
    titleEn: "Let's Go to the Park!",
    titleJa: "こうえんへ いこう!",
    level: 2,
    pages: [
      { text: "Today is Sunday. Let's go to the park!",
        textJa: "きょうは にちようび。こうえんへ いこう!" },
      { text: "I ride the swing. One, two, three! Wheee!",
        textJa: "ブランコに のるよ。いち、に、さん! びゅーん!" },
      { text: "I go down the slide. It is so fast!",
        textJa: "すべりだいを すべるよ。すごく はやい!" },
      { text: "I play in the sandbox with my friend.",
        textJa: "すなばで おともだちと あそぶよ。" },
      { text: "Oh no! It starts to rain. Run, run, run!",
        textJa: "たいへん! あめが ふってきた。はしれ、はしれ!" },
      { text: "We run home together. It was a fun day!",
        textJa: "いっしょに おうちまで はしったよ。たのしい いちにちだったね!" }
    ]
  }
];

// 画像と音声のファイルの場所を決めるルール
function pageImage(book, pageIndex) {
  return `books/${book.id}/p${pageIndex + 1}.svg`;
}
function pageAudio(book, pageIndex) {
  return `books/${book.id}/audio/p${pageIndex + 1}.m4a`;
}
function coverImage(book) {
  return `books/${book.id}/cover.svg`;
}

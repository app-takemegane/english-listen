// 絵本データ:あとから本を増やすときは、この配列に追加するだけでよい
// audio は差し替え可能(ネイティブ録音ができたら同じファイル名で置き換える)
const BOOKS = [
  {
    id: "sun",
    titleEn: "Good Morning, Sun!",
    titleJa: "おはよう、おひさま!",
    level: 1,
    pages: [
      { text: "The sun comes up. Good morning, sun!" },
      { text: "A bird sings on the tree. Good morning, bird!" },
      { text: "A cat wakes up. Good morning, cat!" },
      { text: "A flower opens. Good morning, flower!" },
      { text: "I wake up and smile. Good morning, everyone!" },
      { text: "It is a happy new day!" }
    ]
  },
  {
    id: "cat",
    titleEn: "The Hungry Cat",
    titleJa: "おなかぺこぺこ ねこちゃん",
    level: 1,
    pages: [
      { text: "Momo the cat is very hungry." },
      { text: "She looks in the kitchen. No food!" },
      { text: "She looks in the garden. No food!" },
      { text: "She sees a little fish in the pond." },
      { text: "Splash! The fish swims away." },
      { text: "Mom gives Momo some milk. Yum, yum! Momo is happy." }
    ]
  },
  {
    id: "colors",
    titleEn: "What Color Is It?",
    titleJa: "なにいろかな?",
    level: 1,
    pages: [
      { text: "Look! A red apple." },
      { text: "Look! A yellow banana." },
      { text: "Look! A green frog." },
      { text: "Look! A blue bird." },
      { text: "Look! A pink flower." },
      { text: "Red, yellow, green, blue, and pink. I love colors!" }
    ]
  },
  {
    id: "park",
    titleEn: "Let's Go to the Park!",
    titleJa: "こうえんへ いこう!",
    level: 2,
    pages: [
      { text: "Today is Sunday. Let's go to the park!" },
      { text: "I ride the swing. One, two, three! Wheee!" },
      { text: "I go down the slide. It is so fast!" },
      { text: "I play in the sandbox with my friend." },
      { text: "Oh no! It starts to rain. Run, run, run!" },
      { text: "We run home together. It was a fun day!" }
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

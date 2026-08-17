#!/bin/bash
# 絵本に出てくる全単語の「1単語ずつのお手本音声」を作るスクリプト
# 使い方: bash scripts/generate-words.sh [声の名前]
set -e
cd "$(dirname "$0")/.."

VOICE="${1:-Ava (Premium)}"
RATE=145  # 遅すぎると発音がゆがむため自然な速さで作る(遅聞きはアプリの速度調整で)
TMP="$(mktemp -d)"
mkdir -p words

# books.js から重複なしの単語一覧(ファイル名用と読み上げ用)を取り出す
node -e '
const fs = require("fs");
eval(fs.readFileSync("js/books.js", "utf8") + "; globalThis.BOOKS = BOOKS;");
const map = {};
BOOKS.forEach(b => b.pages.forEach(p => p.text.split(" ").forEach(w => {
  const key = w.toLowerCase().replace(/[^a-z]/g, "");
  if (!key) return;
  if (!map[key]) map[key] = w.replace(/[^A-Za-z\x27]/g, "");
})));
// 読み方の上書き:文の中での読み方に合わせたい単語をここで指定する
map["a"] = "ah";  // 「A blue bird」の a は文中どおり「ア」と読ませる
console.log(Object.entries(map).map(([k, v]) => k + "\t" + v).join("\n"));
' | while IFS=$'\t' read -r key spoken; do
  # 末尾にピリオドを付けると、語尾が自然な言い切りの発音になる
  # ごく短い単語は、聞き取りやすいよう少しゆっくり読ませる
  rate="$RATE"
  if [ "${#key}" -le 2 ]; then rate=115; fi
  say -v "$VOICE" -r "$rate" -o "$TMP/tmp.aiff" "$spoken."
  afconvert -f m4af -d aac -b 64000 "$TMP/tmp.aiff" "words/$key.m4a"
  echo "created words/$key.m4a"
done

rm -rf "$TMP"
echo "done (voice: $VOICE)"

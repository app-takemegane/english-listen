#!/bin/bash
# クイズの問題文の音声を作るスクリプト
# (ページ音声と単語クリップは scripts/build-audio.py が作る)
# 使い方: bash scripts/generate-audio.sh [声の名前]
set -e
cd "$(dirname "$0")/.."

VOICE="${1:-Ava (Premium)}"
RATE=140  # 読む速さ(子ども向けにゆっくりめ)
TMP="$(mktemp -d)"

gen_quiz() {
  local book="$1" num="$2" text="$3"
  local dir="books/$book/quiz"
  mkdir -p "$dir"
  say -v "$VOICE" -r "$RATE" -o "$TMP/tmp.aiff" "$text"
  afconvert -f m4af -d aac -b 64000 "$TMP/tmp.aiff" "$dir/q$num.m4a"
  echo "created $dir/q$num.m4a"
}

gen_quiz sun 1 "Who sings on the tree?"
gen_quiz sun 2 "What does the cat do?"
gen_quiz sun 3 "Is it a happy new day?"
gen_quiz cat 1 "Who is very hungry?"
gen_quiz cat 2 "What does Momo see in the pond?"
gen_quiz cat 3 "What does Mom give Momo?"
gen_quiz colors 1 "What color is the apple?"
gen_quiz colors 2 "What color is the frog?"
gen_quiz colors 3 "What color is the banana?"
gen_quiz park 1 "What day is it today?"
gen_quiz park 2 "What is so fast?"
gen_quiz park 3 "Why do they run home?"

rm -rf "$TMP"
echo "done (voice: $VOICE)"

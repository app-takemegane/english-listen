#!/bin/bash
# 絵本の英文から読み上げ音声(m4a)を作るスクリプト
# 使い方: bash scripts/generate-audio.sh [声の名前]
#   声を省略すると Samantha(アメリカ英語・女性)を使う
#   より自然な声を入れたら: bash scripts/generate-audio.sh "Ava (Premium)" で作り直せる
set -e
cd "$(dirname "$0")/.."

VOICE="${1:-Samantha}"
RATE=140  # 読む速さ(子ども向けにゆっくりめ)
TMP="$(mktemp -d)"

gen() {
  local book="$1" page="$2" text="$3"
  local dir="books/$book/audio"
  mkdir -p "$dir"
  say -v "$VOICE" -r "$RATE" -o "$TMP/tmp.aiff" "$text"
  afconvert -f m4af -d aac -b 64000 "$TMP/tmp.aiff" "$dir/p$page.m4a"
  echo "created $dir/p$page.m4a"
}

# クイズの問題文の音声
gen_quiz() {
  local book="$1" num="$2" text="$3"
  local dir="books/$book/quiz"
  mkdir -p "$dir"
  say -v "$VOICE" -r "$RATE" -o "$TMP/tmp.aiff" "$text"
  afconvert -f m4af -d aac -b 64000 "$TMP/tmp.aiff" "$dir/q$num.m4a"
  echo "created $dir/q$num.m4a"
}

# ── Good Morning, Sun! ──
gen sun 1 "The sun comes up. Good morning, sun!"
gen sun 2 "A bird sings on the tree. Good morning, bird!"
gen sun 3 "A cat wakes up. Good morning, cat!"
gen sun 4 "A flower opens. Good morning, flower!"
gen sun 5 "I wake up and smile. Good morning, everyone!"
gen sun 6 "It is a happy new day!"

# ── The Hungry Cat ──
gen cat 1 "Momo the cat is very hungry."
gen cat 2 "She looks in the kitchen. No food!"
gen cat 3 "She looks in the garden. No food!"
gen cat 4 "She sees a little fish in the pond."
gen cat 5 "Splash! The fish swims away."
gen cat 6 "Mom gives Momo some milk. Yum, yum! Momo is happy."

# ── What Color Is It? ──
gen colors 1 "Look! A red apple."
gen colors 2 "Look! A yellow banana."
gen colors 3 "Look! A green frog."
gen colors 4 "Look! A blue bird."
gen colors 5 "Look! A pink flower."
gen colors 6 "Red, yellow, green, blue, and pink. I love colors!"

# ── Let's Go to the Park! ──
gen park 1 "Today is Sunday. Let's go to the park!"
gen park 2 "I ride the swing. One, two, three! Wheee!"
gen park 3 "I go down the slide. It is so fast!"
gen park 4 "I play in the sandbox with my friend."
gen park 5 "Oh no! It starts to rain. Run, run, run!"
gen park 6 "We run home together. It was a fun day!"

# ── クイズの問題文 ──
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

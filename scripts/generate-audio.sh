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

rm -rf "$TMP"
echo "done (voice: $VOICE)"

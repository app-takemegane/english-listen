#!/usr/bin/env python3
"""単語タップ用の「単語単独の正しい読み」音声(words/<単語>.m4a)を生成する。

文中の発音の切り出し(clips/)とは別に、辞書に載っている単独読みで各単語を合成する。
たとえば a は文中では「ア」と弱く読まれるが、単独では「エイ」が正しい。

手順:
 1. 絵本の全単語を集める
 2. 各単語の辞書の発音(WORD_IPA。アメリカ英語の単独読み)を仕様として持つ
 3. ふつうの英語として1語ずつ合成する(「Blue.」のように文の形にすると自然に読む)
 4. 機械点検:音節の数(フォニックス辞書の母音の数)に対して長さが極端な単語を警告する
使い方: python3 scripts/build-words.py
"""
import json, os, shutil, struct, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.42"  # ページ音声と同じ自然な速さ(遅すぎると発音がゆがむ)
PAD = 0.05     # 前後に残す余白(秒)
FADE = 0.015   # プチッという音を防ぐフェード(秒)

# 各単語の辞書の発音(アメリカ英語・単独読み)。音声づくりの仕様として書いておく。
# 文中の弱い読みと違う単語に注意: a(エイ)、the(ザ)、to(トゥー)、was(ワズ)など
WORD_IPA = {
    "a": "ə", "and": "ænd", "apple": "ˈæpəl", "away": "əˈweɪ",
    "banana": "bəˈnænə", "bird": "bɝd", "blue": "bluː", "cat": "kæt",
    "colors": "ˈkʌlɚz", "comes": "kʌmz", "day": "deɪ", "down": "daʊn",
    "everyone": "ˈɛvriwʌn", "fast": "fæst", "fish": "fɪʃ",
    "flower": "ˈflaʊɚ", "food": "fuːd", "friend": "frɛnd",
    "frog": "frɑːɡ", "fun": "fʌn", "garden": "ˈɡɑːrdən",
    "gives": "ɡɪvz", "go": "ɡoʊ", "good": "ɡʊd", "green": "ɡriːn",
    "happy": "ˈhæpi", "home": "hoʊm", "hungry": "ˈhʌŋɡri", "i": "aɪ",
    "in": "ɪn", "is": "ɪz", "it": "ɪt", "kitchen": "ˈkɪtʃən",
    "lets": "lɛts", "little": "ˈlɪtəl", "look": "lʊk", "looks": "lʊks",
    "love": "lʌv", "milk": "mɪlk", "mom": "mɑːm", "momo": "ˈmoʊmoʊ",
    "morning": "ˈmɔːrnɪŋ", "my": "maɪ", "new": "nuː", "no": "noʊ",
    "oh": "oʊ", "on": "ɑːn", "one": "wʌn", "opens": "ˈoʊpənz",
    "park": "pɑːrk", "pink": "pɪŋk", "play": "pleɪ", "pond": "pɑːnd",
    "rain": "reɪn", "red": "rɛd", "ride": "raɪd", "run": "rʌn",
    "sandbox": "ˈsændbɑːks", "sees": "siːz", "she": "ʃiː",
    "sings": "sɪŋz", "slide": "slaɪd", "smile": "smaɪl", "so": "soʊ",
    "some": "sʌm", "splash": "splæʃ", "starts": "stɑːrts",
    "sun": "sʌn", "sunday": "ˈsʌndeɪ", "swims": "swɪmz",
    "swing": "swɪŋ", "the": "ðə", "three": "θriː", "to": "tuː",
    "today": "təˈdeɪ", "together": "təˈɡɛðɚ", "tree": "triː",
    "two": "tuː", "up": "ʌp", "very": "ˈvɛri", "wake": "weɪk",
    "wakes": "weɪks", "was": "wʌz", "we": "wiː", "wheee": "wiː",
    "with": "wɪθ", "yellow": "ˈjɛloʊ", "yum": "jʌm",
}

# フォニックスの1音の音声をそのまま使う単語(合成しない)
# a は辞書の単独読み「エイ」で作っていたが、子どもには文中の「ア」で教える方針に変更(ユーザー要望)。
# 文字タップで鳴る phonics/uh.m4a(ə、実機確認済み)を流用し、文字と単語の音を完全に一致させる
COPY_SOUND = {
    "a": "uh",
}

# 読ませる英語の特別指定(ふつうは「先頭を大文字+ピリオド」で読ませる)
SPECIAL_TEXT = {
    "i": "I.",       # 1文字のままだと読みが揺れるため、大文字の単独読み「アイ」を明示する
    "lets": "Let's.",  # 本文の表記どおりアポストロフィを付けて読ませる
    "wheee": "Wheee!",  # かけ声なので勢いを残す
}

# 1語だけの合成だと発音が崩れる単語は、文の終わりに置いた文を合成して切り出す
# (文末の単語は下がる調子の完全な発音=単独読みとほぼ同じ。切り出す位置は実測時刻を使う)
# blue は「Blue.」単独だと「ブリュ」に崩れると実機確認(速さを変えても直らない単語固有の癖)
EXTRACT_TEXT = {
    "blue": "It is blue.",
}

# ── 絵本の全単語と、フォニックス辞書(音節の数の点検に使う)を読み込む ──
data = json.loads(subprocess.run(
    ["node", "-e",
     'const fs=require("fs");'
     'eval(fs.readFileSync("js/books.js","utf8")+fs.readFileSync("js/phonics.js","utf8")'
     '+"; globalThis.out={books:BOOKS.map(b=>b.pages.map(p=>p.text)),"'
     '+"phonics:PHONICS, vowels:VOWEL_SOUNDS};");'
     'console.log(JSON.stringify(out));'],
    capture_output=True, text=True, check=True).stdout)

words = set()
for pages in data["books"]:
    for text in pages:
        for token in text.split(" "):
            key = "".join(c for c in token.lower() if c.isalpha())
            if key:
                words.add(key)

missing = sorted(words - set(WORD_IPA))
extra = sorted(set(WORD_IPA) - words)
if missing:
    print(f"発音が未定義の単語: {', '.join(missing)}")
    sys.exit(1)
if extra:
    print(f"注意: 絵本にない単語が発音表に残っている: {', '.join(extra)}")

# 引数に単語を並べると、その単語だけ作り直せる(例: python3 scripts/build-words.py blue)
only = set(sys.argv[1:])
if only:
    unknown = sorted(only - words)
    if unknown:
        print(f"絵本にない単語: {', '.join(unknown)}")
        sys.exit(1)
    words = only

# フォニックス辞書から音節の数(母音のまとまりの数)を数える
vowels = set(data["vowels"])
def syllables(key):
    chunks = data["phonics"].get(key)
    if not chunks:
        return None
    n = 0
    for _, sound in chunks:
        sounds = [sound] if isinstance(sound, str) else (sound or [])
        if any(s in vowels for s in sounds):
            n += 1
    return max(1, n)

# ── 1語ずつ合成する ──────────────────────────────────
os.makedirs("words", exist_ok=True)
tmpdir = tempfile.mkdtemp()
results = []

for key in sorted(words):
    # フォニックスの音をそのまま使う単語:コピーするだけ(長さの点検には参加させる)
    if key in COPY_SOUND:
        src = f"phonics/{COPY_SOUND[key]}.m4a"
        out = f"words/{key}.m4a"
        shutil.copyfile(src, out)
        info = subprocess.run(["afinfo", src], check=True, capture_output=True, text=True).stdout
        dur = next(float(line.split(":")[1].split()[0])
                   for line in info.splitlines() if "estimated duration" in line)
        results.append((key, f"{src} を流用", dur))
        continue
    if key in EXTRACT_TEXT:
        text = EXTRACT_TEXT[key]
    else:
        text = SPECIAL_TEXT.get(key, key.capitalize() + ".")
    caf = os.path.join(tmpdir, "w.caf")
    wav = os.path.join(tmpdir, "w.wav")
    tim = os.path.join(tmpdir, "w.json")
    if os.path.exists(caf):
        os.remove(caf)
    subprocess.run(["swift", "scripts/speak_with_timings.swift", text,
                    caf, tim, RATE],
                   check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                   check=True, capture_output=True)
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    samples = list(struct.unpack(f"<{len(raw)//2}h", raw))

    # 文から切り出す単語:最後の単語の開始時刻から後ろだけを使う
    if key in EXTRACT_TEXT:
        info = json.load(open(tim))
        start = info["words"][-1]["start"]
        samples = samples[max(0, int((start - 0.02) * sr)):]

    # 前後の無音を切りつめる(余白 PAD 秒だけ残す)
    peak = max(1, max(abs(s) for s in samples))
    thresh = peak * 0.03
    first = next((i for i, s in enumerate(samples) if abs(s) >= thresh), 0)
    last = next((i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) >= thresh), len(samples) - 1)
    pad = int(PAD * sr)
    samples = samples[max(0, first - pad):min(len(samples), last + 1 + pad)]

    fade_n = min(int(FADE * sr), len(samples) // 2)
    for i in range(fade_n):
        gain = i / fade_n
        samples[i] = int(samples[i] * gain)
        samples[-1 - i] = int(samples[-1 - i] * gain)

    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    out = f"words/{key}.m4a"
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", wav, out],
                   check=True, capture_output=True)
    results.append((key, text, len(samples) / sr))

# ── 機械点検:音節の数に対して長さが極端な単語を警告する ──────────
# 1音節あたりのだいたいの長さから外れる単語は、発音が崩れている可能性がある
warned = 0
for key, text, dur in results:
    syl = syllables(key)
    ipa = WORD_IPA[key]
    note = ""
    if dur < 0.15:
        note = " ← 短すぎる(音が出ていないかも)"
    elif syl and dur > 0.45 + 0.40 * syl:
        note = f" ← 長すぎる({syl}音節にしては)発音が崩れていないか確認"
    if note:
        warned += 1
    print(f"{key}: /{ipa}/ 「{text}」 {dur:.2f}s{note}")

print(f"完了: words/ に {len(results)}語" + (f" / 警告 {warned}件" if warned else " / 警告なし"))

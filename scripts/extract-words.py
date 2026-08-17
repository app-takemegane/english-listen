#!/usr/bin/env python3
"""全絵本の文を合成し、各単語を文の音声から切り出して words/*.m4a を作る。
単語のお手本が「文中の発音」と完全に同じになる方式。
各単語は「後ろに間(ま)がある場所(文末や句読点の直後)」を優先して切り出す。
使い方: python3 scripts/extract-words.py
"""
import json, os, re, struct, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.42"       # 合成の速さ(0-1)。ゆっくりめで聞き取りやすい
PAD_START = 0.02    # 切り出し開始の余白(秒)
GAP_BEFORE_NEXT = 0.01
TAIL_KEEP = 0.10    # 語尾のあとに残す余韻(秒)
FADE = 0.015        # プチッという音を防ぐフェード(秒)

def word_key(word):
    return re.sub(r"[^a-z]", "", word.lower())

def token_score(tokens, i):
    """切り出しやすさ。文末や句読点つき(後ろに間がある)を優先する"""
    if i == len(tokens) - 1:
        return 2
    if re.search(r"[.,!?]$", tokens[i]):
        return 2
    return 0

# books.js から全ページの文を取り出す
pages_json = subprocess.run(
    ["node", "-e",
     'const fs=require("fs");'
     'eval(fs.readFileSync("js/books.js","utf8")+"; globalThis.BOOKS=BOOKS;");'
     'console.log(JSON.stringify(BOOKS.flatMap(b=>b.pages.map(p=>p.text))));'],
    capture_output=True, text=True, check=True).stdout
sentences = json.loads(pages_json)

# 各単語について、一番きれいに切り出せる場所(文と位置)を選ぶ
best = {}  # key -> (score, 文番号, 単語番号)
for si, sentence in enumerate(sentences):
    tokens = sentence.split(" ")
    for ti, tok in enumerate(tokens):
        k = word_key(tok)
        if not k:
            continue
        score = token_score(tokens, ti)
        if k not in best or score > best[k][0]:
            best[k] = (score, si, ti)
print(f"必要な単語: {len(best)}語")

by_sentence = {}
for k, (score, si, ti) in best.items():
    by_sentence.setdefault(si, []).append((k, ti))

os.makedirs("words", exist_ok=True)
tmpdir = tempfile.mkdtemp()
done = set()

def load_wav(path):
    with wave.open(path, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    count = len(raw) // 2
    return sr, list(struct.unpack(f"<{count}h", raw))

def save_clip(samples, sr, out_m4a):
    fade_n = min(int(FADE * sr), len(samples) // 2)
    for i in range(fade_n):
        g = i / fade_n
        samples[i] = int(samples[i] * g)
        samples[-1 - i] = int(samples[-1 - i] * g)
    wav_out = os.path.join(tmpdir, "clip.wav")
    with wave.open(wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                    wav_out, out_m4a], check=True, capture_output=True)

for si in sorted(by_sentence):
    sentence = sentences[si]
    caf = os.path.join(tmpdir, f"s{si}.caf")
    tim = os.path.join(tmpdir, f"s{si}.json")
    wav = os.path.join(tmpdir, f"s{si}.wav")
    subprocess.run(["swift", "scripts/speak_with_timings.swift", sentence, caf, tim, RATE],
                   check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                   check=True, capture_output=True)
    info = json.load(open(tim))
    words = info["words"]
    total = info["total"]
    tokens = sentence.split(" ")
    if len(words) != len(tokens):
        print(f"警告: 単語数が合わない文をスキップ: {sentence}")
        continue
    sr, samples = load_wav(wav)
    for k, ti in by_sentence[si]:
        start = max(0.0, words[ti]["start"] - PAD_START)
        if ti + 1 < len(words):
            end = words[ti + 1]["start"] - GAP_BEFORE_NEXT
        else:
            end = total
        a, b = int(start * sr), min(len(samples), int(end * sr))
        clip = samples[a:b]
        # 語尾の無音を「余韻ぶん」だけ残して切りつめる(間のある場所なら自然に閉じる)
        peak = max(1, max(abs(s) for s in clip))
        thresh = peak * 0.04
        last = len(clip) - 1
        while last > 0 and abs(clip[last]) < thresh:
            last -= 1
        clip = clip[:min(len(clip), last + int(TAIL_KEEP * sr))]
        save_clip(clip, sr, f"words/{k}.m4a")
        done.add(k)
        tag = "間あり" if token_score(tokens, ti) == 2 else "間なし"
        print(f"created words/{k}.m4a  ({len(clip)/sr:.2f}s {tag}: {tokens[ti]})")

missing = set(best) - done
print(f"完了: {len(done)}語 / 不足: {len(missing)} {sorted(missing)}")
sys.exit(1 if missing else 0)

#!/usr/bin/env python3
"""全絵本の文を合成し、各単語を文の音声から切り出して words/*.m4a を作る。
単語のお手本が「文中の発音」と完全に同じになる方式。
使い方: python3 scripts/extract-words.py
"""
import json, os, re, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.42"      # 合成の速さ(0-1)。ゆっくりめで聞き取りやすい
PAD_START = 0.02   # 切り出しの前後の余白(秒)
PAD_END = 0.01
FADE = 0.012       # プチッという音を防ぐフェード(秒)

def word_key(word):
    return re.sub(r"[^a-z]", "", word.lower())

# books.js から全ページの文を取り出す
pages_json = subprocess.run(
    ["node", "-e",
     'const fs=require("fs");'
     'eval(fs.readFileSync("js/books.js","utf8")+"; globalThis.BOOKS=BOOKS;");'
     'console.log(JSON.stringify(BOOKS.flatMap(b=>b.pages.map(p=>p.text))));'],
    capture_output=True, text=True, check=True).stdout
sentences = json.loads(pages_json)

needed = set()
for s in sentences:
    for w in s.split(" "):
        k = word_key(w)
        if k:
            needed.add(k)
print(f"必要な単語: {len(needed)}語")

os.makedirs("words", exist_ok=True)
done = set()
tmpdir = tempfile.mkdtemp()

def cut_word(wav_path, start, end, out_m4a):
    with wave.open(wav_path, "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        a = max(0, int(start * sr))
        b = min(n, int(end * sr))
        w.setpos(a)
        raw = bytearray(w.readframes(b - a))
    # 16bit モノラル前提でフェードをかける
    import struct
    count = len(raw) // 2
    samples = list(struct.unpack(f"<{count}h", bytes(raw)))
    fade_n = min(int(FADE * sr), count // 2)
    for i in range(fade_n):
        g = i / fade_n
        samples[i] = int(samples[i] * g)
        samples[-1 - i] = int(samples[-1 - i] * g)
    clip = struct.pack(f"<{count}h", *samples)
    wav_out = os.path.join(tmpdir, "clip.wav")
    with wave.open(wav_out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(clip)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                    wav_out, out_m4a], check=True, capture_output=True)

for idx, sentence in enumerate(sentences):
    keys_here = [word_key(w) for w in sentence.split(" ")]
    if not any(k and k in needed and k not in done for k in keys_here):
        continue
    caf = os.path.join(tmpdir, f"s{idx}.caf")
    tim = os.path.join(tmpdir, f"s{idx}.json")
    wav = os.path.join(tmpdir, f"s{idx}.wav")
    subprocess.run(["swift", "scripts/speak_with_timings.swift", sentence, caf, tim, RATE],
                   check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                   check=True, capture_output=True)
    info = json.load(open(tim))
    words = info["words"]
    total = info["total"]
    for i, entry in enumerate(words):
        k = word_key(entry["word"])
        if not k or k in done:
            continue
        start = max(0.0, entry["start"] - PAD_START)
        end = (words[i + 1]["start"] - PAD_END) if i + 1 < len(words) else min(total, entry["start"] + 1.5)
        cut_word(wav, start, end, f"words/{k}.m4a")
        done.add(k)
        print(f"created words/{k}.m4a  ({end - start:.2f}s from: {sentence[:30]}...)")

missing = needed - done
print(f"完了: {len(done)}語 / 不足: {len(missing)} {sorted(missing)}")
sys.exit(1 if missing else 0)

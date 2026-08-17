#!/usr/bin/env python3
"""ページ音声・単語クリップ・ハイライト時刻表を一括生成する。

各ページの文を Ava で合成しながら単語の開始時刻を記録し、
 1. ページ音声      books/<本>/audio/p<n>.m4a
 2. 単語クリップ    books/<本>/clips/p<n>_w<単語番号>.m4a (その位置の発音そのまま)
 3. 時刻表          js/timings.js (読み上げハイライトを実測時刻で光らせる)
を作る。単語タップは「その文のその場所」の音をそのまま再生する。
使い方: python3 scripts/build-audio.py
"""
import json, os, re, struct, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.42"       # 合成の速さ(0-1)。ゆっくりめで聞き取りやすい
PAD_START = 0.02    # クリップ開始の余白(秒)
GAP_BEFORE_NEXT = 0.01
TAIL_KEEP = 0.10    # 語尾のあとに残す余韻(秒)
FADE = 0.015        # プチッという音を防ぐフェード(秒)

books = json.loads(subprocess.run(
    ["node", "-e",
     'const fs=require("fs");'
     'eval(fs.readFileSync("js/books.js","utf8")+"; globalThis.BOOKS=BOOKS;");'
     'console.log(JSON.stringify(BOOKS.map(b=>({id:b.id,texts:b.pages.map(p=>p.text)}))));'],
    capture_output=True, text=True, check=True).stdout)

tmpdir = tempfile.mkdtemp()

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

timings = {}
clip_total = 0

for book in books:
    bid = book["id"]
    os.makedirs(f"books/{bid}/audio", exist_ok=True)
    os.makedirs(f"books/{bid}/clips", exist_ok=True)
    timings[bid] = []
    for pi, text in enumerate(book["texts"]):
        caf = os.path.join(tmpdir, "s.caf")
        tim = os.path.join(tmpdir, "s.json")
        wav = os.path.join(tmpdir, "s.wav")
        subprocess.run(["swift", "scripts/speak_with_timings.swift", text, caf, tim, RATE],
                       check=True, capture_output=True)
        info = json.load(open(tim))
        words = info["words"]
        total = info["total"]
        tokens = text.split(" ")
        assert len(words) == len(tokens), f"単語数が合わない: {bid} p{pi+1}: {text}"

        # 1. ページ音声(この合成そのものを使う)
        subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000",
                        caf, f"books/{bid}/audio/p{pi+1}.m4a"], check=True, capture_output=True)

        # 2. 単語クリップ(その位置の発音をそのまま切り出す)
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                       check=True, capture_output=True)
        sr, samples = load_wav(wav)
        starts = [w["start"] for w in words]
        for wi in range(len(tokens)):
            start = max(0.0, starts[wi] - PAD_START)
            end = (starts[wi + 1] - GAP_BEFORE_NEXT) if wi + 1 < len(tokens) else total
            a, b = int(start * sr), min(len(samples), int(end * sr))
            clip = samples[a:b]
            peak = max(1, max(abs(s) for s in clip))
            thresh = peak * 0.04
            last = len(clip) - 1
            while last > 0 and abs(clip[last]) < thresh:
                last -= 1
            clip = clip[:min(len(clip), last + int(TAIL_KEEP * sr))]
            save_clip(clip, sr, f"books/{bid}/clips/p{pi+1}_w{wi}.m4a")
            clip_total += 1

        # 3. ハイライト用の実測時刻
        timings[bid].append({"total": round(total, 3),
                             "starts": [round(s, 3) for s in starts]})
        print(f"{bid} p{pi+1}: {len(tokens)}語 ({total:.1f}s)")

with open("js/timings.js", "w") as f:
    f.write("// 読み上げハイライト用の実測時刻表(scripts/build-audio.py が自動生成)\n")
    f.write("const TIMINGS = " + json.dumps(timings) + ";\n")

print(f"完了: ページ音声 {sum(len(b['texts']) for b in books)}件 / クリップ {clip_total}件 / js/timings.js")

#!/usr/bin/env python3
"""cat の「ca」が「カッ」に聞こえる件の作り直し候補を作る。

原因: 発音記号に強さの印(ˈ)を付けると、Ava は母音を半分に縮める。
      kˈæ の母音は 0.17秒しかなく、ほかの音(平均 0.38秒)の半分以下だった。
候補: ①今のサンプル ②印を外す ③印を外してゆっくり ④本物の単語 cat から t の前で切る ⑤④のゆっくり版

出力: try/split/ca-1〜5.m4a
使い方: dataset/.venv/bin/python scripts/try-ca.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, FADE_IN, FADE_OUT, TARGET_RMS = 0.03, 0.02, 0.05, 0.170
TMP = tempfile.mkdtemp()
os.makedirs(OUT, exist_ok=True)

def decode(path):
    o = subprocess.run(["ffmpeg","-v","error","-i",path,"-f","s16le","-ac","1","-ar","22050","-"],
                       check=True, capture_output=True).stdout
    return np.frombuffer(o, dtype="<i2").astype(np.float64), 22050

def say_ipa(ipa, rate):
    caf = os.path.join(TMP, "p.caf")
    if os.path.exists(caf): os.remove(caf)
    subprocess.run(["swift","scripts/speak_ipa.swift","x",ipa,caf,str(rate)],
                   check=True, capture_output=True)
    return decode(caf)

def say_text(text, rate):
    caf = os.path.join(TMP, "w.caf")
    if os.path.exists(caf): os.remove(caf)
    subprocess.run(["swift","scripts/speak_with_timings.swift",text,caf,
                    os.path.join(TMP,"w.json"),str(rate)], check=True, capture_output=True)
    return decode(caf)

def cut_before_final_burst(x, sr):
    """末尾の破裂音(t)の直前にある「一瞬の無音」を探して、そこから前だけを残す
    (build-phonics.py の cut 方式と同じ考え方)"""
    win = int(0.005 * sr)
    pk = max(1.0, float(np.abs(x).max()))
    quiet = [float(np.abs(x[i:i+win]).max()) < pk*0.05 for i in range(0, len(x)-win, win)]
    cut, run = None, None
    for i, q in enumerate(quiet):
        if q and run is None: run = i
        elif not q:
            if run is not None and i-run >= 4 and run > len(quiet)*0.3: cut = run*win
            run = None
    if cut is None and run is not None and run > len(quiet)*0.3: cut = run*win
    return x[:cut] if cut else x

def vowel_len(x, sr):
    win = int(0.01*sr); n = 0; pk = max(1.0, float(np.abs(x).max()))
    for i in range(0, len(x)-win, win):
        seg = x[i:i+win]
        s = np.abs(np.fft.rfft(seg*np.hanning(win))); f = np.fft.rfftfreq(win, 1/sr)
        if s[(f>=300)&(f<1000)].mean() > s[(f>=2000)&(f<8000)].mean()*3 \
           and np.abs(seg).max() > pk*0.08: n += 1
    return n*0.01

def polish(x, sr):
    x = x.copy()
    pk = max(1.0, float(np.abs(x).max())); th = pk*0.03
    on = np.where(np.abs(x) >= th)[0]
    if len(on):
        pad = int(PAD*sr); x = x[max(0,on[0]-pad):min(len(x),on[-1]+1+pad)].copy()
    n = min(int((PAD+FADE_IN)*sr), len(x)//2); x[:n] *= np.linspace(0,1,n)
    n = min(int(FADE_OUT*sr), len(x)//2);      x[len(x)-n:] *= np.linspace(1,0,n)
    rms = math.sqrt(float(np.mean(x**2))) or 1.0
    gain = min(TARGET_RMS*32767/rms, 0.9*32767/max(1.0, float(np.abs(x).max())))
    return np.clip(x*gain, -32768, 32767)

def save(x, sr, name):
    wav = os.path.join(TMP, "o.wav")
    with wave.open(wav,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(x.astype("<i2").tobytes())
    out = os.path.join(OUT, name + ".m4a")
    if os.path.exists(out): os.remove(out)
    subprocess.run(["afconvert","-f","m4af","-d","aac","-b","64000",wav,out],
                   check=True, capture_output=True)

cands = [
    ("ca-1", "今のサンプル(強さの印あり・ふつう)", *say_ipa("kˈæ", 0.3)),
    ("ca-2", "強さの印を外す",                     *say_ipa("kæ",  0.3)),
    ("ca-3", "強さの印を外して ゆっくり",          *say_ipa("kæ",  0.15)),
]
for name, label, rate in (("ca-4","本物の単語 cat から切り出し",0.42),
                          ("ca-5","本物の単語 cat から切り出し(ゆっくり)",0.30)):
    w, sr = say_text("cat.", rate)
    cands.append((name, label, cut_before_final_burst(w, sr), sr))

print(f"{'名前':7s}{'秒':>6s}{'母音秒':>8s}  作り方")
for name, label, x, sr in cands:
    y = polish(x, sr); save(y, sr, name)
    print(f"{name:7s}{len(y)/sr:6.2f}{vowel_len(y,sr):8.2f}  {label}")

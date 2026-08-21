#!/usr/bin/env python3
"""l・m・n を「①のまま・ぶつ切りにせず・その後の音も少し足して」作り直す。

ユーザー報告:
  「①をぶつ切りしないで、その後の音も加えて、ほんのちょっとだけ伸ばして欲しい」
  「②a以降(フェードを伸ばす・音を引き伸ばす)は全ておかしい」

分かったこと: Ava に「l」を単独で合成させると 0.18秒で、音量が上がりきったところで
  いきなり終わる(=その先が作られていない)。だからフェードを足しても不自然になる。
  ところが「lə」のように後ろに母音を付けて合成すると、l は 0.36秒ぶん作られ、
  そのあと自然に母音へつながっていく。
やり方: 「lə」を合成し、母音が始まる場所を見つけて、
  「その手前 0.16秒」から「母音に少し食い込ませたところ」までを切り出す。
  → 長さは今とほぼ同じまま、終わりだけが本物の続きになる。
  (母音に食い込ませる手当ては dataset/build-sample-very.py の HEAD_EXTRA と同じ考え方)

出力: try/split/l-1a〜1d.m4a など
使い方: dataset/.venv/bin/python scripts/try-l3.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, TARGET_RMS = 0.03, 0.170
KEEP_BEFORE = 0.16    # 母音の手前、どこから使うか(今の音とほぼ同じ長さにする)
FADE_IN  = 0.02       # 途中から切り出すので、立ち上がりを少しなめらかに
FADE_OUT = 0.025      # プチッと鳴らない最小限。消えぐあいは本物の続きにまかせる
EXTRAS = [("a", 0.02, "今と同じ長さのまま、終わりだけ自然に"),
          ("b", 0.04, "ほんの少し伸ばす"),
          ("c", 0.07, "少し伸ばす"),
          ("d", 0.11, "もう少し伸ばす")]
SOUNDS = ["l", "m", "n"]
TMP = tempfile.mkdtemp(); os.makedirs(OUT, exist_ok=True)

def decode(p):
    o = subprocess.run(["ffmpeg","-v","error","-i",p,"-f","s16le","-ac","1","-ar","22050","-"],
                       check=True, capture_output=True).stdout
    return np.frombuffer(o, dtype="<i2").astype(np.float64), 22050

def say_ipa(ipa, rate=0.3):
    caf = os.path.join(TMP, "p.caf")
    if os.path.exists(caf): os.remove(caf)
    subprocess.run(["swift","scripts/speak_ipa.swift","x",ipa,caf,str(rate)],
                   check=True, capture_output=True)
    return decode(caf)

def band(seg, sr, lo, hi):
    s = np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1/sr)
    m = (f>=lo)&(f<hi)
    return float(s[m].mean()) if m.any() else 0.0

def schwa_start(x, sr):
    """l・m・n のあとに「あいまいな母音」が始まる場所。
    高いほうの響き(1200〜2500Hz)と低いほうの響き(300〜900Hz)の比が急に増えるところ。
    l は低い響きが強いので、母音の見分けに 300〜1000Hz を使うと早すぎる位置になってしまう"""
    win = int(0.01*sr)
    idx = list(range(0, len(x)-win, win))
    ratio = [band(x[i:i+win],sr,1200,2500)/max(band(x[i:i+win],sr,300,900),1e-9) for i in idx]
    base = float(np.median(ratio[2:len(ratio)//2]))
    for i, r in enumerate(ratio):
        if i > len(ratio)*0.3 and r > base*3: return i*win
    return None

def finish(x, sr):
    x = x.copy()
    n = min(int(FADE_IN*sr), len(x)//3);  x[:n] *= np.linspace(0,1,n)
    n = min(int(FADE_OUT*sr), len(x)//3); x[len(x)-n:] *= np.linspace(1,0,n)
    x = np.concatenate([np.zeros(int(PAD*sr)), x, np.zeros(int(PAD*sr))])
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

def tail_shape(x, sr):
    """終わりの音量のかたち(20msごと%)。ぶつ切りなら最後が大きいまま切れる"""
    win = int(0.02*sr); pk = max(1.0, float(np.abs(x).max()))
    v = [int(np.abs(x[i:i+win]).max()/pk*100) for i in range(0, len(x)-win, win)]
    return v[-6:]

print(f"{'名前':8s}{'全体秒':>7s}  終わりの音量のかたち(20msごと %)")
for key in SOUNDS:
    x, sr = say_ipa(key + "ə")
    b = schwa_start(x, sr)
    if b is None:
        print(f"{key}: 母音の始まりが見つからない"); continue
    for tag, extra, label in EXTRAS:
        a = max(0, b - int(KEEP_BEFORE*sr))
        y = finish(x[a:min(len(x), b + int(extra*sr))].copy(), sr)
        save(y, sr, f"{key}-1{tag}")
        print(f"{key}-1{tag:3s}{len(y)/sr:7.2f}  {tail_shape(y,sr)}   {label}(+{int(extra*1000)}ms)")
    print(f"    参考: 今の {key} = 0.18秒 / 終わりのかたち ", end="")
    cur, sr2 = decode(f"phonics/{key}.m4a")
    print(tail_shape(cur, sr2))
    print()

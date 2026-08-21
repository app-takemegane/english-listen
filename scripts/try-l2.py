#!/usr/bin/env python3
"""l・m・n の「②終わりのフェードを長く」の、もっと長い版を作る。

①と②(フェード0.06秒)の違いが分からない、というユーザー報告への対応。
元の音が 0.18秒しかないため、フェードを伸ばすだけでは変化が小さい。そこで2通り用意する:
  A: フェードだけを伸ばす(0.10 / 0.14秒)。音の長さは 0.18秒のまま
  B: 音そのものを伸ばしてから、長いフェードをかける
     伸ばし方は「声の周期(ピッチ)をそろえて steady な部分を繰り返す」方式。
     周期の切れ目でつなぐので、つなぎ目が聞こえない

出力: try/split/l-2a〜2d.m4a など
使い方: dataset/.venv/bin/python scripts/try-l2.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, FADE_IN, TARGET_RMS = 0.03, 0.02, 0.170
TMP = tempfile.mkdtemp(); os.makedirs(OUT, exist_ok=True)
SOUNDS = ["l", "m", "n"]

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

def trim(x):
    pk = max(1.0, float(np.abs(x).max())); on = np.where(np.abs(x) >= pk*0.03)[0]
    return x[on[0]:on[-1]+1].copy() if len(on) else x.copy()

def pitch_period(seg, sr):
    """声の周期(サンプル数)。60〜400Hz の範囲で自己相関がいちばん高いところ"""
    seg = seg - seg.mean()
    ac = np.correlate(seg, seg, mode="full")[len(seg)-1:]
    lo, hi = int(sr/400), int(sr/60)
    if hi >= len(ac): hi = len(ac)-1
    if lo >= hi: return None
    return lo + int(np.argmax(ac[lo:hi]))

def stretch(x, sr, target_sec):
    """真ん中の安定した部分を、声の周期をそろえて繰り返し、目標の長さまで伸ばす"""
    need = int(target_sec*sr) - len(x)
    if need <= 0: return x
    a, b = int(len(x)*0.35), int(len(x)*0.75)
    T = pitch_period(x[a:b], sr)
    if not T or T*2 > (b-a): return x
    k = max(1, int(0.04*sr)//T)          # 40ms ぶんの周期数をひとかたまりにする
    loop = x[a:a+k*T]
    xf = T//2                            # つなぎ目の重ね合わせ(半周期)
    out = list(x[:a+k*T])
    while len(out) - len(x[:a+k*T]) < need:
        head = np.array(out[-xf:]); tail = loop[:xf]
        w = np.linspace(0, 1, xf)
        out[-xf:] = list(head*(1-w) + tail*w)
        out += list(loop[xf:])
    return np.array(out + list(x[a+k*T:]))

def finish(x, sr, fade_out):
    x = x.copy()
    n = min(int(FADE_IN*sr), len(x)//2); x[:n] *= np.linspace(0,1,n)
    n = min(int(fade_out*sr), len(x)-1);  x[len(x)-n:] *= np.linspace(1,0,n)
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

def drop_ms(x, sr):
    win = int(0.005*sr); pk = max(1.0, float(np.abs(x).max()))
    env = [(i, float(np.abs(x[i:i+win]).max())/pk) for i in range(0, len(x)-win, win)]
    hi = next((i for i,v in reversed(env) if v>=0.5), None)
    lo = next((i for i,v in reversed(env) if v>=0.05), None)
    return (lo-hi)/sr*1000 if hi is not None and lo is not None and lo>hi else 0

print(f"{'名前':8s}{'全体秒':>7s}{'消えていく時間':>10s}ms  作り方")
for key in SOUNDS:
    raw, sr = say_ipa(key)
    base = trim(raw)
    plans = [
        (f"{key}-2a", "フェードだけ長く(0.10秒)", base, 0.10),
        (f"{key}-2b", "フェードだけ長く(0.14秒)", base, 0.14),
        (f"{key}-2c", "音を0.30秒に伸ばして フェード0.15秒", stretch(base, sr, 0.30), 0.15),
        (f"{key}-2d", "音を0.45秒に伸ばして フェード0.28秒", stretch(base, sr, 0.45), 0.28),
    ]
    for name, label, y, fo in plans:
        z = finish(y, sr, fo); save(z, sr, name)
        print(f"{name:8s}{len(z)/sr:7.2f}{drop_ms(z,sr):10.0f}    {label}")
    print()

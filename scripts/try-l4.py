#!/usr/bin/env python3
"""l・m・n の「①はそのまま・終わりに本物の続きをつなぐ」版を作る。

ユーザー報告:
  「①a以降が『ラ』じゃなくて『ア』になってしまったので、発音のスタート位置は変えないで」
  → 前回は「lə」の“後ろのほう”だけを切り出したため、l の始まり(舌が離れる瞬間)が
     抜け落ちて「ア」に聞こえていた。l らしさは出だしにある。

やり方:
  ① 今の音(発音記号 l を単独で合成したもの)を、出だしから終わりまでそのまま使う。
  ② 別に「lə」を合成し、母音に移る直前の「自然に消えていく部分」だけを取り出す。
  ③ ①の終わりと②を、声の周期をそろえて(相互相関で位相を合わせて)重ねてつなぐ。
  → 出だしは今とまったく同じ。終わりだけが本物の続きになり、少しだけ長くなる。

出力: try/split/l-3a〜3c.m4a など
使い方: dataset/.venv/bin/python scripts/try-l4.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, TARGET_RMS = 0.03, 0.170
XFADE = 0.03        # つなぎ目の重ね合わせ(秒)
FADE_IN = 0.015     # 今の音と同じ立ち上がり
FADE_OUT = 0.02     # プチッと鳴らない最小限
# 「lə」の音量をよく見ると、消えていく動きは“母音より手前”、l のうちに始まっている。
# だから母音には一切入らず、母音の手前の「消えていく部分」だけをつなぐ。
# (母音に少しでも食い込ませると「ラ」が「ア」になる。ユーザー報告どおりだった)
TAILS = [("3a", 0.05, "ほんのちょっと"), ("3b", 0.08, "少し"), ("3c", 0.12, "もう少し")]
VOWELY_MAX = {"l": 0.45, "m": 0.20, "n": 0.20}  # 母音っぽさの上限(今の音とほぼ同じに保つ)
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

def trim(x):
    pk = max(1.0, float(np.abs(x).max())); on = np.where(np.abs(x) >= pk*0.03)[0]
    return x[on[0]:on[-1]+1].copy() if len(on) else x.copy()

def band(seg, sr, lo, hi):
    s = np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1/sr)
    m = (f>=lo)&(f<hi)
    return float(s[m].mean()) if m.any() else 0.0

def schwa_start(x, sr):
    """あいまいな母音が始まる場所(高い響き / 低い響き の比が急に増えるところ)"""
    win = int(0.01*sr); idx = list(range(0, len(x)-win, win))
    ratio = [band(x[i:i+win],sr,1200,2500)/max(band(x[i:i+win],sr,300,900),1e-9) for i in idx]
    base = float(np.median(ratio[2:len(ratio)//2]))
    for i, r in enumerate(ratio):
        if i > len(ratio)*0.3 and r > base*3: return i*win
    return None

def splice(head, tail, sr):
    """head の終わりと tail の出だしを、声の周期をそろえて重ねてつなぐ。
    位相がずれたままつなぐとブツッと段差が出るので、相互相関でいちばん合う位置を探す"""
    n = int(XFADE*sr)
    if len(head) < n*2 or len(tail) < n*2: return np.concatenate([head, tail])
    ref = head[-n:]
    # tail の先頭から 1周期ぶん(最大 10ms)ずらして、いちばん形が合う位置を探す
    best, best_score = 0, -1e18
    for off in range(0, min(int(0.010*sr), len(tail)-n)):
        score = float(np.dot(ref, tail[off:off+n]))
        if score > best_score: best_score, best = score, off
    t = tail[best:]
    # つなぎ目で音量が飛ばないように、tail 側の大きさを head の終わりに合わせる
    r1 = math.sqrt(float(np.mean(ref**2))) or 1.0
    r2 = math.sqrt(float(np.mean(t[:n]**2))) or 1.0
    t = t * (r1/r2)
    w = np.linspace(0, 1, n)
    return np.concatenate([head[:-n], head[-n:]*(1-w) + t[:n]*w, t[n:]])

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

def shape(x, sr, n=8):
    win = int(0.02*sr); pk = max(1.0, float(np.abs(x).max()))
    v = [int(np.abs(x[i:i+win]).max()/pk*100) for i in range(0, len(x)-win, win)]
    return v[-n:]

def vowely(x, sr):
    """母音っぽさ。800〜1600Hz の強さの割合。あいまいな母音(ア)は 0.82、
    今の l は 0.41、m・n は 0.10〜0.12。ここが上がると「ラ」が「ア」になる"""
    m = x[int(len(x)*0.3):int(len(x)*0.7)]
    s = np.abs(np.fft.rfft(m*np.hanning(len(m)))); f = np.fft.rfftfreq(len(m), 1/sr)
    b = lambda lo,hi: (float(s[(f>=lo)&(f<hi)].mean()) if ((f>=lo)&(f<hi)).any() else 0.0)
    return b(800,1600)/(b(150,4000) or 1.0)

def start_same(a, b, sr):
    """出だし0.10秒が今の音と同じかどうか(1.0 なら完全一致)"""
    n = int(0.10*sr)
    p, q = a[:n], b[:n]
    if len(p) < n or len(q) < n: return 0.0
    return float(np.dot(p,q)/max(1e-9, np.linalg.norm(p)*np.linalg.norm(q)))

print(f"{'名前':8s}{'全体秒':>7s}{'出だし一致':>8s}{'母音っぽさ':>8s}  判定")
for key in SOUNDS:
    head = trim(say_ipa(key)[0])                 # ① そのまま
    sr = 22050
    x, _ = say_ipa(key + "ə")
    b = schwa_start(x, sr)
    cur = finish(head.copy(), sr)
    save(cur, sr, f"{key}-3now")
    print(f"{key}-3now{len(cur)/sr:7.2f}{1.0:8.2f}{vowely(cur,sr):8.2f}  ← 今のまま(参考)")
    for tag, tail_len, label in TAILS:
        tail = x[max(0, b-int(tail_len*sr)) : b].copy()   # 母音の手前で必ず止める
        y = finish(splice(head.copy(), tail, sr), sr)
        save(y, sr, f"{key}-{tag}")
        v = vowely(y, sr)
        ok = "OK" if v <= VOWELY_MAX[key] else "×「ア」寄りになっている"
        print(f"{key}-{tag:4s}{len(y)/sr:7.2f}{start_same(y,cur,sr):8.2f}{v:8.2f}  {ok:12s} "
              f"続きを {int(tail_len*1000)}ms({label})  終わり{shape(y,sr,5)}")
    print()

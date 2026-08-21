#!/usr/bin/env python3
"""l・m を「単語の音声からそのまま抜き出す」版を作る(ユーザー要望)。

今のアプリの単語音声(words/*.m4a、Ava)から、その音の区間だけを切り出す。
利点: 画面の「たんご まるごと」で鳴る音と完全に同じ響きになり、
      語末の音はもともと自然に消えていくので、フェードを作り足す必要がない。

抜き出す場所は「母音っぽさ(800〜1600Hz の強さ)」で見分ける。
  mom = m(低い) → ɑ(高い) → m(低い)   … 最後の m は 0.27秒から自然に消えていく
  blue = b → l → uː                  … uː も低いので、音量の谷で l の終わりを見る
  milk = m → ɪ → l → k                … 新方式で単独の l が出るのは milk・smile の語末側だけ

出力: try/split/l-w1〜w2.m4a, m-w1〜w2.m4a
使い方: dataset/.venv/bin/python scripts/try-l5.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, TARGET_RMS = 0.03, 0.170
FADE_IN, FADE_OUT = 0.015, 0.02
TMP = tempfile.mkdtemp(); os.makedirs(OUT, exist_ok=True)

# (出力名, 単語, 始まり秒, 終わり秒, 説明)  ← 秒は下の scan 結果から決めた
CUTS = [
    ("l-w1", "blue",  0.065, 0.175, "blue の l（b のあと、母音に入る手前まで）"),
    ("l-w2", "milk",  0.280, 0.470, "milk の l 全部（k の口を閉じるまで）"),
    ("l-w3", "milk",  0.390, 0.470, "milk の l の後ろだけ（母音の色を避けた範囲）"),
    ("m-w1", "mom",   0.270, 0.440, "mom の最後の m（語末なので自然に消えていく）"),
    ("m-w2", "mom",   0.000, 0.090, "mom の最初の m（語頭の m）"),
]

def decode(p):
    o = subprocess.run(["ffmpeg","-v","error","-i",p,"-f","s16le","-ac","1","-ar","22050","-"],
                       check=True, capture_output=True).stdout
    return np.frombuffer(o, dtype="<i2").astype(np.float64), 22050

def vowely_track(x, sr, step=0.01):
    """10ms ごとの母音っぽさ(800〜1600Hz の割合)と音量"""
    win = int(step*sr); pk = max(1.0, float(np.abs(x).max()))
    vy, vol = [], []
    for i in range(0, len(x)-win, win):
        seg = x[i:i+win]
        s = np.abs(np.fft.rfft(seg*np.hanning(win))); f = np.fft.rfftfreq(win, 1/sr)
        b = lambda lo,hi: (float(s[(f>=lo)&(f<hi)].mean()) if ((f>=lo)&(f<hi)).any() else 0.0)
        vy.append(b(800,1600)/(b(150,4000) or 1.0)); vol.append(float(np.abs(seg).max())/pk)
    return vy, vol

def find_coda_l(x, sr):
    """milk の l。母音(母音っぽさが高い)が終わってから、k の無音が始まるまで"""
    vy, vol = vowely_track(x, sr)
    peak = max(range(len(vy)), key=lambda i: vy[i])          # 母音 ɪ の中心
    start = next((i for i in range(peak, len(vy)) if vy[i] < 0.55), peak+1)
    end = next((i for i in range(start+2, len(vol)) if vol[i] < 0.06), len(vol))
    return start*int(0.01*sr), end*int(0.01*sr)

def vowely(x, sr):
    m = x[int(len(x)*0.3):int(len(x)*0.7)]
    s = np.abs(np.fft.rfft(m*np.hanning(len(m)))); f = np.fft.rfftfreq(len(m), 1/sr)
    b = lambda lo,hi: (float(s[(f>=lo)&(f<hi)].mean()) if ((f>=lo)&(f<hi)).any() else 0.0)
    return b(800,1600)/(b(150,4000) or 1.0)

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

def shape(x, sr, n=6):
    win = int(0.02*sr); pk = max(1.0, float(np.abs(x).max()))
    v = [int(np.abs(x[i:i+win]).max()/pk*100) for i in range(0, len(x)-win, win)]
    return v[-n:]

LIMIT = {"l": 0.45, "m": 0.20}
print(f"{'名前':7s}{'全体秒':>7s}{'母音っぽさ':>8s}  判定        終わりのかたち   もと")
for name, word, a, b, label in CUTS:
    x, sr = decode(f"words/{word}.m4a")
    i, j = int(a*sr), int(b*sr)
    y = finish(x[i:j].copy(), sr)
    save(y, sr, name)
    v = vowely(y, sr); lim = LIMIT[name[0]]
    print(f"{name:7s}{len(y)/sr:7.2f}{v:8.2f}  {'OK' if v<=lim else '×「ア」寄り':10s}  "
          f"{str(shape(y,sr)):22s} {label}")
print(f"\n参考: 今の l = 0.44 / 今の m = 0.13 / 母音のお手本 ə = 0.82")

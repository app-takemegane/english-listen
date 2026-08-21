#!/usr/bin/env python3
"""伸ばせる子音(l・m・n)が「ラッ」のようにぶつ切りに聞こえる件の作り直し候補を作る。

原因: Ava に発音記号 l を単独で合成させると、音量が上がりきったところ(100%)で
      いきなり終わる。終わりのフェードが 0.015秒しかなく、消えきる前に切れている。
      m・n も同じ(終わりの下がりが 0〜5ミリ秒)。
候補: ①今のまま ②終わりのフェードを長くする ③「lə」を合成して母音の前で切る(v と同じ head 方式)
      ④本物の単語の語末から切り出す(ball / room / moon = 語末の l・m・n)

出力: try/split/l-1〜4.m4a など
使い方: dataset/.venv/bin/python scripts/try-l.py
"""
import math, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUT = "try/split"
PAD, FADE_IN, TARGET_RMS = 0.03, 0.02, 0.170
FADE_SHORT, FADE_LONG = 0.015, 0.06   # 今のフェード / 長くしたフェード
TMP = tempfile.mkdtemp(); os.makedirs(OUT, exist_ok=True)

# (音の名前, 発音記号, 語末にその音が来る本物の単語)
SOUNDS = [("l", "l", "ball."), ("m", "m", "room."), ("n", "n", "moon.")]

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

def say_text(text, rate=0.42):
    caf = os.path.join(TMP, "w.caf")
    if os.path.exists(caf): os.remove(caf)
    subprocess.run(["swift","scripts/speak_with_timings.swift",text,caf,
                    os.path.join(TMP,"w.json"),str(rate)], check=True, capture_output=True)
    return decode(caf)

def band(seg, sr, lo, hi):
    s = np.abs(np.fft.rfft(seg*np.hanning(len(seg)))); f = np.fft.rfftfreq(len(seg), 1/sr)
    m = (f>=lo)&(f<hi)
    return float(s[m].mean()) if m.any() else 0.0

def vowel_start(x, sr):
    """子音のあとに母音が始まる位置(300〜1000Hz が急に強くなる点)"""
    pk = max(1.0, float(np.abs(x).max()))
    st = int(np.argmax(np.abs(x) >= pk*0.05)); win = int(0.01*sr)
    idx = list(range(st, min(len(x)-win, st+int(0.5*sr)), win))
    lv = [band(x[i:i+win], sr, 300, 1000) for i in idx]
    if len(lv) < 6: return None
    base = sorted(lv[:5])[2]
    for i, v in zip(idx, lv):
        if v > base*2: return i
    return None

def sonorant_start(x, sr):
    """語末の l・m・n が始まる位置。母音から子音に移るとき音量がいったん谷になるので、
    後半でいちばん低くなるところを境目とみなす"""
    win = int(0.02*sr)
    env = [(i, float(np.abs(x[i:i+win]).max())) for i in range(0, len(x)-win, win)]
    # 探すのは真ん中あたりだけ。末尾まで含めると「消えていく余韻」を境目と間違える
    tail = [(i, v) for i, v in env if len(x)*0.40 < i < len(x)*0.72]
    return min(tail, key=lambda t: t[1])[0] if tail else None

def polish(x, sr, fade_out):
    x = x.copy()
    pk = max(1.0, float(np.abs(x).max())); th = pk*0.03
    on = np.where(np.abs(x) >= th)[0]
    if len(on):
        pad = int(PAD*sr); x = x[max(0,on[0]-pad):min(len(x),on[-1]+1+pad)].copy()
    n = min(int((PAD+FADE_IN)*sr), len(x)//2); x[:n] *= np.linspace(0,1,n)
    # 余白(PAD)ぶんを足しておかないと、フェードが無音部分だけで終わってしまい、
    # 音の終わりが素通しのまま残る(build-sample-very.py の立ち上がりと同じ落とし穴)
    n = min(int((PAD+fade_out)*sr), len(x)//2); x[len(x)-n:] *= np.linspace(1,0,n)
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
    """終わりに音量が山の50%から5%まで落ちるのにかかる時間(ぶつ切り度合い)"""
    win = int(0.005*sr); pk = max(1.0, float(np.abs(x).max()))
    env = [(i, float(np.abs(x[i:i+win]).max())/pk) for i in range(0, len(x)-win, win)]
    hi = next((i for i,v in reversed(env) if v>=0.5), None)
    lo = next((i for i,v in reversed(env) if v>=0.05), None)
    return (lo-hi)/sr*1000 if hi is not None and lo is not None and lo>hi else 0

print(f"{'名前':7s}{'秒':>6s}{'終わりの下がり':>10s}ms  作り方")
for key, ipa, word in SOUNDS:
    # ① 今のまま
    x, sr = say_ipa(ipa)
    cands = [(f"{key}-1", "今のまま", polish(x, sr, FADE_SHORT), sr)]
    # ② 終わりのフェードを長くするだけ
    cands.append((f"{key}-2", "終わりのフェードを長く(0.06秒)", polish(x, sr, FADE_LONG), sr))
    # ③ 「lə」を合成して母音の前まで(head 方式。v と同じ)
    y, sr3 = say_ipa(ipa + "ə")
    vs = vowel_start(y, sr3)
    cands.append((f"{key}-3", f"「{ipa}ə」を合成して母音の前で切る",
                  polish(y[:vs] if vs else y, sr3, FADE_LONG), sr3))
    # ④ 本物の単語の語末から切り出す
    for tag, rate, lab in (("4", 0.42, ""), ("5", 0.25, "(ゆっくり)")):
        w, sr4 = say_text(word, rate)
        ss = sonorant_start(w, sr4)
        cands.append((f"{key}-{tag}", f"本物の単語「{word}」の語末から切り出す{lab}",
                      polish(w[ss:] if ss else w, sr4, FADE_LONG), sr4))
    for name, label, y, s in cands:
        save(y, s, name)
        print(f"{name:7s}{len(y)/s:6.2f}{drop_ms(y,s):10.0f}    {label}")
    print()

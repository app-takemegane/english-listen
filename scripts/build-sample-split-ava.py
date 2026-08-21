#!/usr/bin/env python3
"""新しい分け方(子音+母音をひとかたまり)の音を、Ava の声で作るサンプル。

今のアプリの音は Ava、r だけ Piper、新方式の試作は Piper と声がバラバラだった。
新しい分け方では子音が単独で残る場面が減るので、
「単独では鳴らない」という Ava の弱点(破裂音・r・すべる音)が出にくいはず、という確認。

出力: try/split/ava-<音の名前>.m4a と try/split/ava-report.json
使い方: dataset/.venv/bin/python scripts/build-sample-split-ava.py   (numpy を使うため venv の python)
"""
import json, math, os, struct, subprocess, sys, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
OUTDIR = "try/split"
# 速さは「ふつう」から始めて、母音が短すぎたら順にゆっくりにしていく。
# 強さの印(ˈ)を付けると Ava は母音を半分に縮めるので、印は付けない
# (cat の「ca」が「カッ」に聞こえた原因。kˈæ の母音 0.17秒 → kæ で 0.34秒。ユーザー確認済み)
RATES = ["0.3", "0.22", "0.15", "0.05"]
VOWEL_MIN = 0.25   # 母音がこの長さに届くまで、ゆっくりにして作り直す
PAD = 0.03
FADE_IN, FADE_OUT = 0.02, 0.04
TARGET_RMS = 0.170  # 今の phonics/*.m4a に合わせた大きさ(NOTES の r 差し替えと同じ値)

# 音の名前 → Ava に渡す発音記号。build-phonics.py の SYNTH_IPA から
# 「単独で鳴らすための逃げ道(短い ə を足す等)」を外したもの。
# 注意: g は特殊文字の ɡ(U+0261)だと無視される。r も ɹ ではなく普通の r を使う
C = {"p":"p","b":"b","t":"t","d":"d","k":"k","g":"g","ch":"tʃ","j":"dʒ",
     "f":"f","v":"v","th":"θ","dh":"ð","s":"s","z":"z","sh":"ʃ","h":"h",
     "m":"m","n":"n","ng":"ŋ","l":"l","r":"r","w":"w","y":"j","ks":"ks","ts":"ts"}
V = {"ae":"æ","eh":"ɛ","ih":"ɪ","iy":"i","aa":"ɑ","ah":"ʌ","uh":"ə","uu":"ʊ",
     "uw":"u","er":"ɜɹ","el":"əl","ar":"ɑɹ","or":"ɔɹ",
     "ay":"aɪ","ey":"eɪ","ow":"aʊ","oh":"oʊ","oy":"ɔɪ","aw":"ɔ"}

# サンプルに使う単語。fun・sings は母音が短くなりやすい音(f+ʌ・s+ɪ)の確認用
SAMPLE_WORDS = ["cat", "blue", "happy", "friend", "flower", "sandbox", "fun", "sings"]

def read_caf(path, tmp):
    wav = os.path.join(tmp, "p.wav")
    subprocess.run(["afconvert","-f","WAVE","-d","LEI16",path,wav], check=True, capture_output=True)
    with wave.open(wav,"rb") as w:
        sr = w.getframerate(); raw = w.readframes(w.getnframes())
    return np.frombuffer(raw, dtype="<i2").astype(np.float64), sr

def band(seg, sr, lo, hi):
    if len(seg) < 32: return 0.0
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    f = np.fft.rfftfreq(len(seg), 1/sr); m = (f>=lo)&(f<hi)
    return float(spec[m].mean()) if m.any() else 0.0

def centroid(x, sr):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    f = np.fft.rfftfreq(len(x), 1/sr)
    return float((spec*f).sum() / max(1e-9, spec.sum()))

def vowel_len(x, sr):
    """声が出ている(低い周波数が強い)区間の長さ = 母音の長さ"""
    win = int(0.01*sr); n = 0; pk = max(1.0, float(np.abs(x).max()))
    for i in range(0, len(x)-win, win):
        seg = x[i:i+win]
        s = np.abs(np.fft.rfft(seg*np.hanning(win))); f = np.fft.rfftfreq(win, 1/sr)
        if s[(f>=300)&(f<1000)].mean() > s[(f>=2000)&(f<8000)].mean()*3 \
           and np.abs(seg).max() > pk*0.08: n += 1
    return n*0.01

def vowel_start(x, sr):
    """子音のあとに母音が始まる位置(第1フォルマント 300〜1000Hz が急に強くなる点)"""
    peak = max(1.0, float(np.abs(x).max()))
    st = int(np.argmax(np.abs(x) >= peak*0.05))
    win = int(0.01*sr)
    idx = list(range(st, min(len(x)-win, st+int(0.35*sr)), win))
    lv = [band(x[i:i+win], sr, 300, 1000) for i in idx]
    if len(lv) < 6: return None
    base = sorted(lv[:5])[2]
    for i, v in zip(idx, lv):
        if v > base*2: return i
    return None

def polish(x, sr):
    x = x.copy()
    peak = max(1.0, float(np.abs(x).max())); th = peak*0.03
    on = np.where(np.abs(x) >= th)[0]
    if len(on):
        pad = int(PAD*sr)
        x = x[max(0,on[0]-pad):min(len(x),on[-1]+1+pad)].copy()
    n = min(int((PAD+FADE_IN)*sr), len(x)//2); x[:n] *= np.linspace(0,1,n)
    n = min(int(FADE_OUT*sr), len(x)//2);      x[len(x)-n:] *= np.linspace(1,0,n)
    rms = math.sqrt(float(np.mean(x**2))) or 1.0
    gain = min(TARGET_RMS*32767/rms, 0.9*32767/max(1.0, float(np.abs(x).max())))
    return np.clip(x*gain, -32768, 32767)

def to_m4a(x, sr, name):
    wav = os.path.join(TMP, "o.wav")
    with wave.open(wav,"wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(x.astype("<i2").tobytes())
    out = os.path.join(OUTDIR, name + ".m4a")
    if os.path.exists(out): os.remove(out)
    subprocess.run(["afconvert","-f","m4af","-d","aac","-b","64000",wav,out],
                   check=True, capture_output=True)

TMP = tempfile.mkdtemp(); os.makedirs(OUTDIR, exist_ok=True)
plan = json.load(open("dataset/split-plan.json", encoding="utf-8"))

report, done, warn = [], set(), []
for w in SAMPLE_WORDS:
    for unit in plan[w]["new"]:
        key = "-".join(unit["sounds"])
        if key in done or len(unit["sounds"]) == 1: continue
        done.add(key)
        cons, vow = unit["sounds"]
        ipa = C[cons] + V[vow]          # 強さの印は付けない
        for rate in RATES:              # 母音が短ければ、ゆっくりにして作り直す
            caf = os.path.join(TMP, "p.caf")
            if os.path.exists(caf): os.remove(caf)
            subprocess.run(["swift","scripts/speak_ipa.swift","x",ipa,caf,rate],
                           check=True, capture_output=True)
            x, sr = read_caf(caf, TMP)
            vl = vowel_len(x, sr)
            if vl >= VOWEL_MIN: break
        if vl < VOWEL_MIN:
            warn.append(f"{key}: 母音が {vl:.2f}秒 と短い(目標 {VOWEL_MIN}秒)")
        # 有声の子音(b・d・g・l・m など)は低い音が最初から強く、境目が出ないので点検しない
        if vowel_start(x, sr) is None and cons in ("k","p","t","ch","s","f","sh","th","h"):
            warn.append(f"{key}: 母音の始まりが見つからない(子音か母音が抜けたかも)")
        x = polish(x, sr)
        to_m4a(x, sr, "ava-" + key)
        row = {"unit": key, "ipa": ipa, "rate": rate, "sec": round(len(x)/sr,3),
               "vowel": round(vl,3), "hz": round(centroid(x, sr))}
        report.append(row)
        print(f"{key:8s}{ipa:8s} 速さ{rate:5s} {row['sec']:.2f}s  母音{row['vowel']:.2f}s  "
              f"重心{row['hz']:5d}Hz")

json.dump({"sounds": report, "warn": warn},
          open(os.path.join(OUTDIR,"ava-report.json"),"w",encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("\n注意:", "\n ".join(warn) if warn else "なし")
print(f"完了: {OUTDIR}/ava-*.m4a を {len(report)}個")

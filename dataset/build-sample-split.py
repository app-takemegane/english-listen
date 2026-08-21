#!/usr/bin/env python3
"""音の分解を「子音+母音をひとかたまり」に変えた場合のサンプル音を作る。

参考: https://en.hatsuon.info/word/bat
  bat は「b / æ / t」ではなく「bǽ － t」(バァ － トゥ)に分けられている。
  = 母音の直前にある子音1つだけが、その母音とくっついてひとかたまりになる。

このスクリプトは、その「子音+母音」のかたまりを Piper に直接合成させる。
今のアプリは子音を単独で鳴らすため、破裂音(p b t d k g)や v で
たくさんの逃げ道(本物の単語を切る・こすれる音を持ち上げる など)が必要だった。
母音とセットなら、その逃げ道なしにそのまま鳴らせるはず、というのが今回の狙い。

出力: try/split/*.mp3 と try/split/report.json
使い方: dataset/.venv/bin/python dataset/build-sample-split.py
"""
import json, math, os, subprocess, sys, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
VOICE  = "dataset/voices/en_US-lessac-medium.onnx"
OUTDIR = "try/split"
SLOW = 1.6          # ゆっくり合成する倍率
PAD  = 0.03         # 前後に残す余白(秒)
FADE_IN, FADE_OUT = 0.03, 0.05
TARGET_RMS = 0.15
TRIES = 12          # 何回作って選ぶか(Piper は合成のたびに揺らぐため)

# 音の名前 → Piper(espeak)に渡す発音記号。長い記号は1文字ずつに分ける必要がある
IPA = {
    "p":["p"],"b":["b"],"t":["t"],"d":["d"],"k":["k"],"g":["ɡ"],
    "ch":["t","ʃ"],"j":["d","ʒ"],"f":["f"],"v":["v"],"th":["θ"],"dh":["ð"],
    "s":["s"],"z":["z"],"sh":["ʃ"],"h":["h"],"m":["m"],"n":["n"],"ng":["ŋ"],
    "l":["l"],"r":["ɹ"],"w":["w"],"y":["j"],"ks":["k","s"],"ts":["t","s"],
    "ae":["æ"],"eh":["ɛ"],"ih":["ɪ"],"iy":["i","ː"],"aa":["ɑ","ː"],
    "ah":["ʌ"],"uh":["ə"],"uu":["ʊ"],"uw":["u","ː"],"er":["ɚ"],"el":["ə","l"],
    "ar":["ɑ","ː","ɹ"],"or":["ɔ","ː","ɹ"],"ay":["a","ɪ"],"ey":["e","ɪ"],
    "ow":["a","ʊ"],"oh":["o","ʊ"],"oy":["ɔ","ɪ"],"aw":["ɔ","ː"],
}
VOWELS = {"ae","eh","ih","iy","aa","ah","uh","uu","uw","er","el","ar","or",
          "ay","ey","ow","oh","oy","aw"}

# サンプルに使う単語(今の 88語 の中から、分かれ方の型がちがうものを選んだ)
SAMPLE_WORDS = ["cat", "blue", "happy", "friend", "flower", "sandbox"]

# ── 音の加工(scripts/build-phonics.py・build-sample-very.py と同じ考え方) ──
def polish(x, sr):
    x = x.astype(np.float64).copy()
    peak = max(1.0, float(np.abs(x).max())); th = peak * 0.03
    on = np.where(np.abs(x) >= th)[0]
    if len(on):
        pad = int(PAD * sr)
        x = x[max(0, on[0]-pad):min(len(x), on[-1]+1+pad)].copy()
    n_in = min(int((PAD + FADE_IN) * sr), len(x)//2)
    x[:n_in] *= np.linspace(0, 1, n_in)
    n_out = min(int(FADE_OUT * sr), len(x)//2)
    x[len(x)-n_out:] *= np.linspace(1, 0, n_out)
    rms = math.sqrt(float(np.mean(x**2))) or 1.0
    gain = min(TARGET_RMS*32767/rms, 0.9*32767/max(1.0, float(np.abs(x).max())))
    return np.clip(x * gain, -32768, 32767)

def centroid(x, sr):
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freq = np.fft.rfftfreq(len(x), 1/sr)
    return float((spec*freq).sum() / max(1e-9, spec.sum()))

def to_mp3(samples, sr, name):
    tmp = os.path.join(TMP, "t.wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(samples.astype("<i2").tobytes())
    subprocess.run(["ffmpeg","-v","error","-y","-i",tmp,"-ac","1","-ar","44100",
                    "-codec:a","libmp3lame","-b:a","64k",
                    os.path.join(OUTDIR, name + ".mp3")], check=True)

# ── 本体 ──
if not os.path.exists(VOICE): sys.exit(f"音声モデルがない: {VOICE}")
from piper import PiperVoice
from piper.config import SynthesisConfig
voice = PiperVoice.load(VOICE)
SR = voice.config.sample_rate
TMP = tempfile.mkdtemp(); os.makedirs(OUTDIR, exist_ok=True)

def synth(phonemes, scale):
    cfg = SynthesisConfig(length_scale=scale)
    a = voice.phoneme_ids_to_audio(voice.phonemes_to_ids(phonemes), syn_config=cfg)
    return np.asarray(a, dtype=np.float64) * 32767

def make_unit(sounds, scale=SLOW):
    """「子音+母音」など、音の並びをひとかたまりとして合成する。
    Piper は合成のたびに揺らぐので TRIES 回作り、長さが真ん中のもの(外れを避ける)を選ぶ"""
    ph = []
    for i, s in enumerate(sounds):
        if s in VOWELS and i > 0: ph.append("ˈ")   # 母音に強さの印を置く
        ph += IPA[s]
    if len(sounds) == 1 and sounds[0] in VOWELS: ph = ["ˈ"] + ph
    cands = [polish(synth(ph, scale), SR) for _ in range(TRIES)]
    cands.sort(key=len)
    return cands[len(cands)//2], "".join(ph)

# 分け方の表(regroup したもの)を読む
plan = json.load(open("dataset/split-plan.json", encoding="utf-8"))
report, made = [], set()
for w in SAMPLE_WORDS:
    for unit in plan[w]["new"]:
        key = "-".join(unit["sounds"])
        if key in made: continue
        made.add(key)
        if len(unit["sounds"]) == 1 and os.path.exists(f"phonics/{key}.m4a"):
            report.append({"unit": key, "src": "既存 phonics/", "sec": None}); continue
        x, ph = make_unit(unit["sounds"])
        to_mp3(x, SR, key)
        report.append({"unit": key, "src": "新規", "phonemes": ph,
                       "sec": round(len(x)/SR, 3), "hz": round(centroid(x, SR))})
        print(f"{key:8s} {ph:10s} {len(x)/SR:.2f}s  {centroid(x,SR):5.0f}Hz")

json.dump(report, open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print(f"\n{len([r for r in report if r['src']=='新規'])} 個の新しい音を {OUTDIR}/ に作った")

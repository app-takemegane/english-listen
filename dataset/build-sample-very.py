#!/usr/bin/env python3
"""「very」を1音ずつ鳴らすサンプルを新しい声(Piper en_US-lessac-medium)で作る。

新データセットの audio/phonemes/*.mp3 は「例単語まるごと」(v→van)なので、
1音だけの音はここで別に作る。作り方を3通り用意して聞き比べられるようにする。
  A案  = 発音記号を単独で合成する(Piper に音素を直接わたす。今の Ava ではできなかった方式)
  As案 = A案をゆっくり合成する(length_scale で伸ばす)
  B案  = 本物の単語をゆっくり合成して、その音の部分だけを切り出す(今のアプリと同じ考え方)
Piper は合成のたびに音が少し揺らぐ。母音は運が悪いと出だしに破裂のような荒れが入り、
「エー」が「たー」に聞こえる(ユーザー報告)。そこで A案は TRIES 回作って
「出だしがいちばんきれいなもの」を選ぶ。

出力: try/very/*.mp3 と try/very/report.json
使い方: dataset/.venv/bin/python dataset/build-sample-very.py        # 全部
        dataset/.venv/bin/python dataset/build-sample-very.py eh     # eh だけ作り直す
"""
import json, math, os, subprocess, sys, tempfile, wave
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
VOICE = "dataset/voices/en_US-lessac-medium.onnx"
OUTDIR = "try/very"
SLOW = 1.6            # ゆっくり合成する倍率(1.0 が普通の速さ)
PAD = 0.03            # 前後に残す余白(秒)
FADE_IN = 0.03        # 立ち上がり(急だと破裂して聞こえる)
FADE_OUT = 0.05       # 終わりを消していく長さ
TARGET_RMS = 0.15     # 音の大きさをそろえる目標
SHELF_HZ, SHELF_DB = 1500, 20   # こすれる音を持ち上げる(v 対策。scripts/build-phonics.py と同じ)
HEAD_EXTRA = 0.035    # head 方式で母音側に少し食い込ませる長さ(短すぎて聞こえないため。終わりのフェードで消える)
TRIES = 20            # A案で作り直す回数(この中から出だしがきれいなものを選ぶ)
CLEAN_ONSET = 0.03    # 出だしの荒さがこれ以下なら「きれい」とみなす(承認された r・y の実測が 0.01〜0.02)

# very = ˈvɛri。Piper の読みでは ['v','ˈ','ɛ','ɹ','i']
# (音の名前, つづり, 発音記号, B案で使う単語, B案の切り出し方)
SOUNDS = [
    ("v",  "v", "v", "van.", "head"),   # 母音の前まで = 子音だけ
    ("eh", "e", "ɛ", "bed.", "vowel"),  # 母音の部分だけ
    ("r",  "r", "ɹ", "red.", "head"),
    ("iy", "y", "i", "see.", "vowel"),
]

def to_mp3(samples, sr, name):
    tmp = os.path.join(TMP, "t.wav")
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes(samples.astype("<i2").tobytes())
    out = os.path.join(OUTDIR, name + ".mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-ac", "1",
                    "-ar", "44100", "-codec:a", "libmp3lame", "-b:a", "64k", out], check=True)

def high_shelf(x, sr, f0, gain_db):
    """f0 より上のこすれる音だけを持ち上げる(RBJ ハイシェルフ)"""
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / sr
    cos_w, alpha = math.cos(w0), math.sin(w0) / 2 * math.sqrt(2)
    sq = 2 * math.sqrt(a) * alpha
    b = np.array([a * ((a + 1) + (a - 1) * cos_w + sq),
                  -2 * a * ((a - 1) + (a + 1) * cos_w),
                  a * ((a + 1) + (a - 1) * cos_w - sq)])
    a0 = (a + 1) - (a - 1) * cos_w + sq
    aa = np.array([2 * ((a - 1) - (a + 1) * cos_w), (a + 1) - (a - 1) * cos_w - sq]) / a0
    b /= a0
    out = np.zeros(len(x)); x1 = x2 = y1 = y2 = 0.0
    for i, v in enumerate(x):
        y = b[0]*v + b[1]*x1 + b[2]*x2 - aa[0]*y1 - aa[1]*y2
        out[i] = y; x2, x1 = x1, v; y2, y1 = y1, y
    return out

def band_energy(seg, sr, lo, hi):
    """その区間の lo〜hi Hz の強さ"""
    if len(seg) < 32: return 0.0
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freq = np.fft.rfftfreq(len(seg), 1 / sr)
    m = (freq >= lo) & (freq < hi)
    return float(spec[m].mean()) if m.any() else 0.0

def sound_start(x):
    """前の無音が終わって音が始まる位置"""
    peak = max(1.0, float(np.abs(x).max()))
    return int(np.argmax(np.abs(x) >= peak * 0.03))

def find_vowel_start(x, sr):
    """母音が始まる位置。第1フォルマント(300〜1000Hz)の強さが
    いちばん急に増えるところを境目とみなす(前半 45% の範囲で探す)"""
    st = sound_start(x)
    win = int(0.01 * sr)
    idx = list(range(st, min(len(x) - win, st + int(0.45 * len(x))), win))
    lv = [band_energy(x[i:i+win], sr, 300, 1000) for i in idx]
    if len(lv) < 4: return None
    rises = [(lv[i+1] - lv[i], idx[i+1]) for i in range(len(lv) - 1)]
    best = max(rises)
    return best[1] if best[0] > 0 else None

def find_vowel_end(x, sr, from_i):
    """母音が終わる位置(音量が山の3割を下回るところ)"""
    win = int(0.005 * sr)
    env = [(i, float(np.abs(x[i:i+win]).max())) for i in range(from_i, len(x) - win, win)]
    if not env: return len(x)
    top = max(v for _, v in env)
    for i, v in env:
        if i > from_i + int(0.05 * sr) and v < top * 0.3:
            return i
    return len(x)

def onset_roughness(x, sr):
    """出だし30msの「高い音の比」。破裂のような立ち上がりがあると大きくなる。
    母音でこの値が大きいと「エー」が「たー」のように聞こえる"""
    st = sound_start(x)
    win = int(0.01 * sr)
    vals = []
    for i in range(st, min(len(x) - win, st + int(0.03 * sr)), win):
        seg = x[i:i+win]
        vals.append(band_energy(seg, sr, 2000, 8000) / max(band_energy(seg, sr, 300, 1000), 1.0))
    return max(vals) if vals else 0.0


def polish(x, sr, boost_high=False):
    """こすれる音を持ち上げ、前後の無音を切り、フェードをかけ、音の大きさをそろえる"""
    x = x.astype(np.float64).copy()
    if boost_high:
        x = high_shelf(x, sr, SHELF_HZ, SHELF_DB)
    peak = max(1.0, float(np.abs(x).max())); th = peak * 0.03
    on = np.where(np.abs(x) >= th)[0]
    if len(on):
        pad = int(PAD * sr)
        x = x[max(0, on[0] - pad):min(len(x), on[-1] + 1 + pad)].copy()
    # 余白ぶんを足しておかないと、フェードが無音の部分だけで終わってしまい、
    # 音の立ち上がりがそのまま残る(「たー」に聞こえる原因のひとつ)
    n_in = min(int((PAD + FADE_IN) * sr), len(x) // 2)
    x[:n_in] *= np.linspace(0, 1, n_in)
    n_out = min(int(FADE_OUT * sr), len(x) // 2)
    x[len(x) - n_out:] *= np.linspace(1, 0, n_out)
    rms = math.sqrt(float(np.mean(x ** 2))) or 1.0
    gain = min(TARGET_RMS * 32767 / rms, 0.9 * 32767 / max(1.0, float(np.abs(x).max())))
    return np.clip(x * gain, -32768, 32767)

def centroid(x, sr):
    """周波数の重心。母音が残っていないかの機械点検に使う(子音は高く、母音は低い)"""
    spec = np.abs(np.fft.rfft(x * np.hanning(len(x))))
    freq = np.fft.rfftfreq(len(x), 1 / sr)
    return float((spec * freq).sum() / max(1e-9, spec.sum()))

# ── 本体 ────────────────────────────────────────────────
if not os.path.exists(VOICE):
    sys.exit(f"音声モデルがない: {VOICE}")
from piper import PiperVoice
from piper.config import SynthesisConfig
voice = PiperVoice.load(VOICE)
SR = voice.config.sample_rate
TMP = tempfile.mkdtemp()
os.makedirs(OUTDIR, exist_ok=True)

def synth_text(text, length_scale=1.0):
    cfg = SynthesisConfig(length_scale=length_scale)
    buf = b"".join(c.audio_int16_bytes for c in voice.synthesize(text, syn_config=cfg))
    return np.frombuffer(buf, dtype="<i2").astype(np.float64)

def synth_phoneme(ipa, length_scale=1.0):
    cfg = SynthesisConfig(length_scale=length_scale)
    a = voice.phoneme_ids_to_audio(voice.phonemes_to_ids([ipa]), syn_config=cfg)
    return np.asarray(a, dtype=np.float64) * 32767

only = {a for a in sys.argv[1:] if not a.startswith("--")}
unknown = sorted(only - {s[0] for s in SOUNDS})
if unknown:
    sys.exit(f"音の表にない: {', '.join(unknown)}")

report, warn, rough = [], [], {}
for key, letter, ipa, word, mode in SOUNDS:
    if only and key not in only:
        continue
    made = {}
    # A案・As案: 発音記号を単独で合成
    # v は合成したままだと「こすれる音」が弱くて低い唸り(ブー)にしか聞こえないので、
    # 切り出し方式と同じように 1500Hz から上を持ち上げて「ヴー」にする
    for tag, scale in (("a", 1.0), ("as", SLOW)):
        cands = []
        for _ in range(TRIES):
            cand = polish(synth_phoneme(ipa, scale), SR, boost_high=(key == "v"))
            cands.append((onset_roughness(cand, SR), cand))
        # 出だしがきれいなものだけを残し、その中でいちばん長いものを選ぶ
        # (きれいなものがなければ、いちばんきれいなものを使う)
        clean = [c for c in cands if c[0] <= CLEAN_ONSET]
        pick = max(clean, key=lambda c: len(c[1])) if clean else min(cands, key=lambda c: c[0])
        made[tag] = pick[1]
        rough[tag + "-" + key] = round(pick[0], 3)
    # B案: ゆっくり合成した本物の単語から切り出す
    w = synth_text(word, SLOW)
    vs = find_vowel_start(w, SR)
    if vs is None:
        warn.append(f"{key}: 母音の始まりが見つからない({word})")
        cut = w.copy()
    elif mode == "head":
        end = min(len(w), vs + int(HEAD_EXTRA * SR))
        cut = w[sound_start(w):end].copy()
    else:
        cut = w[vs:find_vowel_end(w, SR, vs)].copy()
    made["b"] = polish(cut, SR, boost_high=(key == "v"))

    row = {"sound": key, "letter": letter, "ipa": ipa, "word": word, "mode": mode}
    for tag, x in made.items():
        to_mp3(x, SR, f"{tag}-{key}")
        row[f"{tag}_sec"] = round(len(x) / SR, 3)
        row[f"{tag}_hz"] = round(centroid(x, SR))
    row["word_sec"] = round(len(w) / SR, 3)
    row["cut_at_sec"] = round(vs / SR, 3) if vs else None
    row["a_onset"] = rough.get("a-" + key)
    row["as_onset"] = rough.get("as-" + key)
    report.append(row)

# 単語まるごと(ふつうの速さ・ゆっくり)。音を指定したときは作り直さない
for tag, scale in () if only else (("word-very", 1.0), ("word-very-slow", SLOW)):
    x = polish(synth_text("very.", scale), SR)
    to_mp3(x, SR, tag)
    report.append({"sound": "(まるごと)", "letter": "very", "ipa": "ˈvɛri", "word": "very.",
                   "mode": tag, "b_sec": round(len(x) / SR, 3), "b_hz": round(centroid(x, SR))})

if not only:
    json.dump(report, open(os.path.join(OUTDIR, "report.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
if warn:
    print("注意:\n  " + "\n  ".join(warn))
print(json.dumps(report, ensure_ascii=False, indent=2))
print(f"完了: {OUTDIR}/ に mp3 {len([f for f in os.listdir(OUTDIR) if f.endswith('.mp3')])}件")

#!/usr/bin/env python3
"""フォニックスの1音ずつの音声(phonics/<音の名前>.m4a)を Ava の声で生成する。

js/phonics.js の辞書も検査する:
 - 絵本の全単語に分け方が定義されているか
 - つづりのまとまりをつなげると単語に戻るか
 - 使っている音の名前が音の表にあるか
使い方: python3 scripts/build-phonics.py
"""
import json, os, struct, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.3"   # 1音だけなので、ページ音声よりゆっくりめに合成する
FADE = 0.015   # プチッという音を防ぐフェード(秒)
PAD = 0.03     # 前後に残す余白(秒)

# 音の名前 → 合成に使う発音記号(IPA)
# 単独では鳴らせない音(破裂音 p t k など)は、ごく短い ə を付けて発音させる
# 注意: g は特殊文字の ɡ(U+0261)だと無視される。普通のアルファベットの g を使うこと
SYNTH_IPA = {
    "p": "pə", "b": "bə", "t": "tə", "d": "də", "k": "kə", "g": "gə",
    "ch": "tʃə", "j": "dʒə",
    "f": "f", "v": "v", "th": "θ", "dh": "ð", "s": "s", "z": "z",
    "sh": "ʃ", "h": "hə",
    "m": "m", "n": "n", "ng": "ŋ", "l": "l", "r": "rə",  # ɹ 単独は鳴らない
    "w": "wə", "y": "jə",
    "ae": "æ", "eh": "ɛ", "ih": "ɪ", "iy": "i", "aa": "ɑ", "ah": "ʌ",
    "uh": "ə", "uu": "ʊ", "uw": "u", "er": "ɜɹ", "el": "əl",  # ɚ 単独は鳴らない
    "ar": "ɑɹ", "or": "ɔɹ",
    "ay": "aɪ", "ey": "eɪ", "ow": "aʊ", "oh": "oʊ", "oy": "ɔɪ", "aw": "ɔ",
}

# 発音記号だと不自然になる音は、ふつうの英語をそのまま読ませて作る(こちらが優先)
# 発音記号の単独読みは「破裂する音」「すべる音」「形が変わる母音」「r系」で崩れやすい
# と実機確認で判明したため、その仲間は最初からこちらで作る。
# 形式: 音の名前: (読ませる英語, 速さ)
TEXT_SYNTH = {
    # 破裂する音(g・k が不自然と確認された仲間)
    "p": ("puh.", "0.42"),
    "b": ("bud.", "0.42", "cut"),  # 「buh」は誤読された。本物の単語 bud の末尾 d を切り落として /bʌ/ を得る
    "t": ("tuh.", "0.42"),
    "d": ("duh.", "0.42"),
    "ch": ("chuh.", "0.42"),
    "j": ("juh.", "0.42"),   # 今の絵本では未使用だが同じ仲間なので揃える
    "g": ("guh.", "0.42"),   # IPA の gə は不自然だった(ユーザー確認)
    "k": ("cuh.", "0.42"),   # IPA の kə も「kuh」も不自然(kuh はキューと読まれた)。c+u なら確実にク
    # すべる音(y が不自然と確認された仲間)
    "y": ("yuh.", "0.42"),   # IPA の jə は不自然だった(ユーザー確認)
    "w": ("wuh.", "0.42"),
    "h": ("huh.", "0.42"),
    # 形が変わる母音(ow・ay が不自然と確認された仲間)
    "ow": ("Ow.", "0.42"),   # IPA の aʊ は不自然だった(ユーザー確認)
    "ay": ("Eye.", "0.42"),  # IPA の aɪ は不自然だった(ユーザー確認)
    "ey": ("A.", "0.42"),
    "oh": ("Oh.", "0.42"),
    "oy": ("Oy.", "0.42"),   # 今の絵本では未使用だが同じ仲間なので揃える
    # r がからむ母音(r 系は最初に無音になった前科がある仲間)
    "ar": ("are.", "0.42"),
    "or": ("or.", "0.42"),
    "er": ("err.", "0.42"),  # 「er.」だとアルファベット読みされる恐れがあるので err
}

# ── 辞書の検査 ──────────────────────────────────────
data = json.loads(subprocess.run(
    ["node", "-e",
     'const fs=require("fs");'
     'eval(fs.readFileSync("js/books.js","utf8")+fs.readFileSync("js/phonics.js","utf8")'
     '+"; globalThis.out={books:BOOKS.map(b=>b.pages.map(p=>p.text)),"'
     '+"phonics:PHONICS, ipa:PHONEME_IPA};");'
     'console.log(JSON.stringify(out));'],
    capture_output=True, text=True, check=True).stdout)

errors = []
words = set()
for pages in data["books"]:
    for text in pages:
        for token in text.split(" "):
            key = "".join(c for c in token.lower() if c.isalpha())
            if key:
                words.add(key)

used_sounds = set()
for word, chunks in data["phonics"].items():
    joined = "".join(c for g, *_ in chunks for c in g.lower() if c.isalpha())
    if joined != word:
        errors.append(f"つづりが合わない: {word} → {joined}")
    for g, sound in chunks:
        for s in ([sound] if isinstance(sound, str) else (sound or [])):
            used_sounds.add(s)
            if s not in SYNTH_IPA:
                errors.append(f"音の表にない: {word} の {g} → {s}")
            if s not in data["ipa"]:
                errors.append(f"PHONEME_IPA にない: {word} の {g} → {s}")

missing = sorted(words - set(data["phonics"]))
if missing:
    errors.append(f"分け方が未定義の単語: {', '.join(missing)}")
if errors:
    print("\n".join(errors))
    sys.exit(1)
print(f"辞書OK: 単語 {len(data['phonics'])}件 / 使っている音 {len(used_sounds)}種類")

# ── 音声の生成 ──────────────────────────────────────
os.makedirs("phonics", exist_ok=True)
tmpdir = tempfile.mkdtemp()

for key, ipa in SYNTH_IPA.items():
    caf = os.path.join(tmpdir, "p.caf")
    wav = os.path.join(tmpdir, "p.wav")
    if os.path.exists(caf):
        os.remove(caf)
    if key in TEXT_SYNTH:
        text, rate = TEXT_SYNTH[key][0], TEXT_SYNTH[key][1]
        cut_final = len(TEXT_SYNTH[key]) > 2 and TEXT_SYNTH[key][2] == "cut"
        subprocess.run(["swift", "scripts/speak_with_timings.swift", text,
                        caf, os.path.join(tmpdir, "p.json"), rate],
                       check=True, capture_output=True)
        ipa = f"「{text}」" + ("(末尾の子音を切除)" if cut_final else "")
    else:
        cut_final = False
        subprocess.run(["swift", "scripts/speak_ipa.swift", "x", ipa, caf, RATE],
                       check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                   check=True, capture_output=True)
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    samples = list(struct.unpack(f"<{len(raw)//2}h", raw))

    # 末尾の子音の切除:破裂音の前の「一瞬の無音」を探し、そこから後ろを捨てる
    if cut_final:
        win = int(0.005 * sr)  # 5ms きざみで音量を見る
        peak = max(1, max(abs(s) for s in samples))
        quiet = [max(abs(s) for s in samples[i:i + win]) < peak * 0.05
                 for i in range(0, len(samples) - win, win)]
        cut_at = None
        run_start = None
        for i, q in enumerate(quiet):
            if q and run_start is None:
                run_start = i
            elif not q:
                # 20ms以上の無音のあとに再び音がある=破裂の前の間。そこで切る
                if run_start is not None and i - run_start >= 4 and run_start > len(quiet) * 0.3:
                    cut_at = run_start * win
                run_start = None
        if cut_at:
            samples = samples[:cut_at]
        else:
            print(f"注意: {key} は切除位置が見つからなかった(そのまま使う)")

    # 前後の無音を切りつめる(余白 PAD 秒だけ残す)
    peak = max(1, max(abs(s) for s in samples))
    thresh = peak * 0.03
    first = next((i for i, s in enumerate(samples) if abs(s) >= thresh), 0)
    last = next((i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) >= thresh), len(samples) - 1)
    pad = int(PAD * sr)
    samples = samples[max(0, first - pad):min(len(samples), last + 1 + pad)]

    fade_n = min(int(FADE * sr), len(samples) // 2)
    for i in range(fade_n):
        gain = i / fade_n
        samples[i] = int(samples[i] * gain)
        samples[-1 - i] = int(samples[-1 - i] * gain)

    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(struct.pack(f"<{len(samples)}h", *samples))
    out = f"phonics/{key}.m4a"
    if os.path.exists(out):
        os.remove(out)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "64000", wav, out],
                   check=True, capture_output=True)
    print(f"{key}: {ipa} ({len(samples)/sr:.2f}s)")

print(f"完了: phonics/ に {len(SYNTH_IPA)}音")

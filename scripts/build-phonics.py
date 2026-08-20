#!/usr/bin/env python3
"""フォニックスの1音ずつの音声(phonics/<音の名前>.m4a)を Ava の声で生成する。

js/phonics.js の辞書も検査する:
 - 絵本の全単語に分け方が定義されているか
 - つづりのまとまりをつなげると単語に戻るか
 - 使っている音の名前が音の表にあるか
使い方: python3 scripts/build-phonics.py
"""
import json, math, os, struct, subprocess, sys, tempfile, wave

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
RATE = "0.3"   # 1音だけなので、ページ音声よりゆっくりめに合成する
FADE = 0.015   # プチッという音を防ぐフェード(秒)
PAD = 0.03     # 前後に残す余白(秒)
HEAD_FADE_IN = 0.03   # head 方式の立ち上がり(急だと「ブ」に聞こえるので長め)
HEAD_FADE = 0.05      # head 方式の終わりを消していく長さ(秒)
HEAD_RMS = 0.15       # head 方式の音の大きさ(m・n・l と同じくらいに揃える)
HEAD_SHELF_HZ = 1500  # ここから上の「こすれる音」を持ち上げる
HEAD_SHELF_DB = 20    # 持ち上げる量。Ava の v はこすれる音が弱すぎて
                      # そのままだと「ブー」という低い響きにしか聞こえない(ユーザー確認)

# 音の名前 → 合成に使う発音記号(IPA)
# 単独では鳴らせない音(破裂音 p t k など)は、ごく短い ə を付けて発音させる
# 注意: g は特殊文字の ɡ(U+0261)だと無視される。普通のアルファベットの g を使うこと
SYNTH_IPA = {
    "p": "pə", "b": "bə", "t": "tə", "d": "də", "k": "kə", "g": "gə",
    "ch": "tʃə", "j": "dʒə",
    "f": "f", "v": "v", "th": "θ", "dh": "ð", "s": "s", "z": "z",
    "sh": "ʃ", "h": "hə",
    "m": "m", "n": "n", "ng": "ŋ", "l": "l", "r": "rə",  # ɹ 単独は鳴らない
    "w": "wə", "y": "jə", "ks": "ks", "ts": "ts",
    "ae": "æ", "eh": "ɛ", "ih": "ɪ", "iy": "i", "aa": "ɑ", "ah": "ʌ",
    "uh": "ə", "uu": "ʊ", "uw": "u", "er": "ɜɹ", "el": "əl",  # ɚ 単独は鳴らない
    "ar": "ɑɹ", "or": "ɔɹ",
    "ay": "aɪ", "ey": "eɪ", "ow": "aʊ", "oh": "oʊ", "oy": "ɔɪ", "aw": "ɔ",
}

# 発音記号だと不自然になる音は、ふつうの英語をそのまま読ませて作る(こちらが優先)
# 発音記号の単独読みは「破裂する音」「すべる音」「形が変わる母音」「r系」で崩れやすい
# と実機確認で判明したため、その仲間は最初からこちらで作る。
# 形式: 音の名前: (読ませる英語, 速さ[, "cut"=末尾の子音を切除 / "tail"=先頭側を捨てて後ろだけ使う
#                              / "head"=母音が始まる前まで(先頭の子音だけ)を使う])
TEXT_SYNTH = {
    # 一息で読む子音のかたまり(2ファイル連結だと「ク…ス」のように間延びするため、1つの音として作る)
    "ks": ("box.", "0.42", "tail"),   # x の音。本物の単語 box の「k の破裂の前の無音」から後ろ= /ks/ を切り出す
    "ts": ("cats.", "0.42", "tail"),  # starts・let's の ts の音(つ)。cats の末尾から /ts/ を切り出す
    # 破裂する音(g・k が不自然と確認された仲間)
    "p": ("puh.", "0.42"),
    "b": ("bud.", "0.42", "cut"),  # 「buh」は誤読された。本物の単語 bud の末尾 d を切り落として /bʌ/ を得る
    "t": ("tuh.", "0.42"),
    "d": ("duh.", "0.42"),
    "ch": ("chuh.", "0.42"),
    "j": ("juh.", "0.42"),   # 今の絵本では未使用だが同じ仲間なので揃える
    "g": ("guh.", "0.42"),   # IPA の gə は不自然だった(ユーザー確認)
    "k": ("cuh.", "0.42"),   # IPA の kə も「kuh」も不自然(kuh はキューと読まれた)。c+u なら確実にク
    # 声を出しながらこする音(伸ばせる音なので、母音を付けずに「ヴー」だけを鳴らす)
    # IPA の v 単独は無声化して「フ」になり、「vuh.」だと母音が長すぎて「ブァ」になった(ユーザー確認)。
    # 本物の単語 van の「母音が始まる前まで」を切り出すと、声の出たヴだけが残る。
    # 速さ 0.30 は 0.42 より v が長くなる(0.13秒。m・n・l の 0.15〜0.18秒に近い)
    "v": ("van.", "0.30", "head"),
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

# 新しい声(Piper)で作り直して、聞き比べで採用した音。
# ここに入れた音は Ava で作り直さない(このスクリプトを実行しても上書きされない)。
# 作り方は dataset/build-sample-very.py の「A案 ゆっくり」=発音記号を単独で合成する方式。
# Piper は合成のたびに音が揺らぐため、採用したファイルそのものを phonics/ に置いている
PIPER_SOUNDS = {"r"}

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

# 引数に音の名前を並べると、その音だけ作り直せる(例: python3 scripts/build-phonics.py ks)
only = set(sys.argv[1:])
unknown = sorted(only - set(SYNTH_IPA))
if unknown:
    print(f"音の表にない: {', '.join(unknown)}")
    sys.exit(1)

def band_level(frame, sr, lo, hi, n=6):
    """その区間の lo〜hi Hz の強さ(ゴーツェル法。numpy なしで計算する)"""
    total = 0.0
    for k in range(n):
        f = lo + (hi - lo) * (k + 0.5) / n
        w = 2 * math.pi * f / sr
        re = sum(frame[i] * math.cos(w * i) for i in range(len(frame)))
        im = sum(frame[i] * math.sin(w * i) for i in range(len(frame)))
        total += math.hypot(re, im) / len(frame)
    return total / n


def high_shelf(samples, sr, f0, gain_db):
    """f0 より高い音(こすれる音)だけを gain_db だけ持ち上げる(RBJ ハイシェルフ)"""
    a = 10 ** (gain_db / 40)
    w0 = 2 * math.pi * f0 / sr
    cos_w, alpha = math.cos(w0), math.sin(w0) / 2 * math.sqrt(2)
    sq = 2 * math.sqrt(a) * alpha
    b = [a * ((a + 1) + (a - 1) * cos_w + sq),
         -2 * a * ((a - 1) + (a + 1) * cos_w),
         a * ((a + 1) + (a - 1) * cos_w - sq)]
    a0 = (a + 1) - (a - 1) * cos_w + sq
    a1 = 2 * ((a - 1) - (a + 1) * cos_w)
    a2 = (a + 1) - (a - 1) * cos_w - sq
    b = [v / a0 for v in b]
    a1, a2 = a1 / a0, a2 / a0
    out = []
    x1 = x2 = y1 = y2 = 0.0
    for x in samples:
        y = b[0] * x + b[1] * x1 + b[2] * x2 - a1 * y1 - a2 * y2
        out.append(y)
        x2, x1 = x1, x
        y2, y1 = y1, y
    return [int(max(-32768, min(32767, v))) for v in out]


def find_vowel_start(samples, sr):
    """子音のあとに母音が始まる位置を返す(見つからなければ None)。
    母音は「第1フォルマント(300〜1000Hz)が急に強くなる」ことで見分ける。
    子音の部分(最初の60ms)の強さを基準にして、2倍(6dB)を超えたところが母音の始まり。"""
    peak = max(1, max(abs(v) for v in samples))
    start = next((i for i, v in enumerate(samples) if abs(v) >= peak * 0.05), 0)
    win = int(0.01 * sr)
    levels = [(i, band_level(samples[i:i + win], sr, 300, 1000))
              for i in range(start, min(len(samples) - win, start + int(0.35 * sr)), win)]
    if len(levels) < 8:
        return None
    base = sorted(v for _, v in levels[:6])[3]  # 最初の60ms(=子音)の代表値
    for i, v in levels:
        if v > base * 2:
            return i
    return None


made = 0
for key, ipa in SYNTH_IPA.items():
    if only and key not in only:
        continue
    if key in PIPER_SOUNDS:
        print(f"{key}: 新しい声で作った音を使うので、作り直さない")
        continue
    made += 1
    caf = os.path.join(tmpdir, "p.caf")
    wav = os.path.join(tmpdir, "p.wav")
    if os.path.exists(caf):
        os.remove(caf)
    if key in TEXT_SYNTH:
        text, rate = TEXT_SYNTH[key][0], TEXT_SYNTH[key][1]
        mode = TEXT_SYNTH[key][2] if len(TEXT_SYNTH[key]) > 2 else None
        cut_final = mode == "cut"
        keep_tail = mode == "tail"
        keep_head = mode == "head"
        subprocess.run(["swift", "scripts/speak_with_timings.swift", text,
                        caf, os.path.join(tmpdir, "p.json"), rate],
                       check=True, capture_output=True)
        ipa = f"「{text}」" + ("(末尾の子音を切除)" if cut_final else "(後ろだけ使う)" if keep_tail
                              else "(母音の前まで使う)" if keep_head else "")
    else:
        cut_final = keep_tail = keep_head = False
        subprocess.run(["swift", "scripts/speak_ipa.swift", "x", ipa, caf, RATE],
                       check=True, capture_output=True)
    subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", caf, wav],
                   check=True, capture_output=True)
    with wave.open(wav, "rb") as w:
        sr = w.getframerate()
        raw = w.readframes(w.getnframes())
    samples = list(struct.unpack(f"<{len(raw)//2}h", raw))

    # 破裂音の前の「一瞬の無音」を探して切る:
    #   cut  = そこから後ろを捨てる(bud → /bʌ/)
    #   tail = そこから前を捨てて後ろだけ使う(box → /ks/)
    if keep_head:
        # 母音が始まる前で切る(van → /v/ だけ残す)
        vowel_at = find_vowel_start(samples, sr)
        if vowel_at:
            samples = samples[:vowel_at]
        else:
            print(f"注意: {key} は母音の始まりが見つからなかった(そのまま使う)")
        # 声の低い響きばかりで「ブー」に聞こえるため、こすれる音を持ち上げて「ヴー」にする
        samples = high_shelf(samples, sr, HEAD_SHELF_HZ, HEAD_SHELF_DB)

    if cut_final or keep_tail:
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
            samples = samples[:cut_at] if cut_final else samples[cut_at:]
        else:
            print(f"注意: {key} は切除位置が見つからなかった(そのまま使う)")

    # 前後の無音を切りつめる(余白 PAD 秒だけ残す)
    peak = max(1, max(abs(s) for s in samples))
    thresh = peak * 0.03
    first = next((i for i, s in enumerate(samples) if abs(s) >= thresh), 0)
    last = next((i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) >= thresh), len(samples) - 1)
    pad = int(PAD * sr)
    samples = samples[max(0, first - pad):min(len(samples), last + 1 + pad)]

    # head 方式は立ち上がりが急だと「ブ」に聞こえるので、少しゆっくり立ち上げる
    fade_n = min(int((HEAD_FADE_IN if keep_head else FADE) * sr), len(samples) // 2)
    for i in range(fade_n):
        samples[i] = int(samples[i] * (i / fade_n))
    # head 方式は途中で切っているので、終わりは長めに消していく(ぶつ切りに聞こえないように)
    out_n = min(int((HEAD_FADE if keep_head else FADE) * sr), len(samples) // 2)
    for i in range(out_n):
        samples[-1 - i] = int(samples[-1 - i] * (i / out_n))

    if keep_head:
        # 一番大きい部分(母音)を捨てたぶん音が小さいので、ほかの音と同じ大きさにそろえる
        rms = math.sqrt(sum(v * v for v in samples) / max(1, len(samples)))
        gain = min(HEAD_RMS * 32767 / max(1.0, rms), 0.9 * 32767 / max(1, max(abs(v) for v in samples)))
        samples = [max(-32768, min(32767, int(v * gain))) for v in samples]

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

print(f"完了: phonics/ に {made}音" + (f"(指定分のみ。全 {len(SYNTH_IPA)}音)" if only else ""))

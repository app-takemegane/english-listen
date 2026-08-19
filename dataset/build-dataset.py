#!/usr/bin/env python3
"""英語の発音学習用データセット(単語 + 1音ごとの発音記号 + 音声)を作る。

作るもの
  phonemes.json   音素マスター(39音。ipa / arpabet / 例単語 / 音声パス)
  words.json      単語データ(つづり / 全体のIPA / 音素ごとの分解 / 音声パス)
  failed.json     分解できなかった単語(飛ばさずに理由つきで記録する)
  audio/phonemes/ 音素の例単語の音声(mp3)
  audio/words/    単語の音声(mp3)

使い方
  python3 dataset/build-dataset.py            # 上位1000語(WORD_LIMIT)
  python3 dataset/build-dataset.py --limit 10 # 試験生成(10語だけ)
  python3 dataset/build-dataset.py --force    # すでにある音声も作り直す
"""
import argparse, json, os, re, shutil, subprocess, sys, tempfile, urllib.request, wave

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# ── 設定(あとで差し替えられるように定数にまとめる)─────────────
WORD_LIMIT = 1000                      # 単語数。増やすときはここだけ変える
VOICE = "voices/en_US-lessac-medium.onnx"   # Piper のアメリカ英語モデル
MP3_RATE = "44100"                     # 出力する音の細かさ(Hz)
MP3_BITRATE = "64k"                    # 音質(64〜96k の範囲。音声だけなら 64k で十分)
SOURCE_URL = "https://raw.githubusercontent.com/menelik3/cmudict-ipa/master/"
SOURCE_FILES = ["cmudict-0.7b-ipa.txt", "brown-frequency-list-with-ipa.txt"]

# ── 音素マスター(CMUdict の 39音)────────────────────────────
# arpabet: (代表のIPA記号, 例単語, 同じ音とみなす書き方の一覧)
# 「同じ音とみなす書き方」は cmudict-ipa の表記ゆれを吸収するためのもの。
# 長音記号つき(ɑː)を先に並べること。短いほうから照合すると取りこぼす。
PHONEME_TABLE = [
    ("AA", "ɑː", "father", ["ɑː", "ɑ"]),
    ("AE", "æ",  "cat",    ["æ"]),
    ("AH", "ʌ",  "cup",    ["ʌ", "ə"]),        # ə(あいまい母音)も同じ AH
    ("AO", "ɔː", "dog",    ["ɔː", "ɔ"]),
    ("AW", "aʊ", "cow",    ["aʊ"]),
    ("AY", "aɪ", "eye",    ["aɪ"]),
    ("B",  "b",  "bat",    ["b"]),
    ("CH", "tʃ", "chair",  ["tʃ"]),
    ("D",  "d",  "dog",    ["d"]),
    ("DH", "ð",  "this",   ["ð"]),
    ("EH", "ɛ",  "bed",    ["ɛ", "e"]),
    ("ER", "ɝ",  "bird",   ["ɝ", "ɚ", "ɜː", "ɜ"]),
    ("EY", "eɪ", "day",    ["eɪ"]),
    ("F",  "f",  "fish",   ["f"]),
    ("G",  "g",  "goat",   ["g", "ɡ"]),        # ɡ(U+0261)も同じ g
    ("HH", "h",  "hat",    ["h"]),
    ("IH", "ɪ",  "sit",    ["ɪ"]),
    ("IY", "iː", "see",    ["iː", "i"]),
    ("JH", "dʒ", "jam",    ["dʒ"]),
    ("K",  "k",  "key",    ["k"]),
    ("L",  "l",  "lion",   ["l"]),
    ("M",  "m",  "moon",   ["m"]),
    ("N",  "n",  "nose",   ["n"]),
    ("NG", "ŋ",  "sing",   ["ŋ"]),
    ("OW", "oʊ", "boat",   ["oʊ", "o"]),
    ("OY", "ɔɪ", "boy",    ["ɔɪ"]),
    ("P",  "p",  "pig",    ["p"]),
    ("R",  "r",  "red",    ["r", "ɹ"]),
    ("S",  "s",  "sun",    ["s"]),
    ("SH", "ʃ",  "ship",   ["ʃ"]),
    ("T",  "t",  "top",    ["t"]),
    ("TH", "θ",  "think",  ["θ"]),
    ("UH", "ʊ",  "book",   ["ʊ"]),
    ("UW", "uː", "blue",   ["uː", "u"]),
    ("V",  "v",  "van",    ["v"]),
    ("W",  "w",  "water",  ["w"]),
    ("Y",  "j",  "yes",    ["j"]),
    ("Z",  "z",  "zoo",    ["z"]),
    ("ZH", "ʒ",  "vision", ["ʒ"]),
]

STRESS = {"ˈ": "primary", "ˌ": "secondary"}   # 強く読む印。音素の直前に付く
STRESS_MARK = {v: k for k, v in STRESS.items()}
# 照合表:書き方 → ARPABET。長い書き方から先に試すので長さの降順に並べる
ALIAS_TO_ARPABET = {a: arp for arp, _, _, aliases in PHONEME_TABLE for a in aliases}
ALIASES = sorted(ALIAS_TO_ARPABET, key=len, reverse=True)


def phoneme_audio_path(arpabet):
    return f"audio/phonemes/{arpabet.lower()}.mp3"


def split_ipa(ipa):
    """IPA の文字列を音素ごとに分ける。
    強く読む印(ˈ ˌ)はその次の音素に付けて持たせる(記号は捨てずに残す)。
    分けられない記号があれば (None, その記号) を返す。"""
    out, i, stress = [], 0, None
    while i < len(ipa):
        ch = ipa[i]
        if ch in STRESS:            # 強く読む印は次の音素のものとして覚えておく
            stress = STRESS[ch]
            i += 1
            continue
        for alias in ALIASES:       # 長い書き方(tʃ・aɪ・ɑː など)から先に照合する
            if ipa.startswith(alias, i):
                arpabet = ALIAS_TO_ARPABET[alias]
                out.append({
                    # text は元の並びに戻せる形(強く読む印を先頭に残したもの)
                    "text": (STRESS_MARK[stress] if stress else "") + alias,
                    "ipa": alias,
                    "arpabet": arpabet,
                    "stress": stress,
                    "long": alias.endswith("ː"),
                    "audio": phoneme_audio_path(arpabet),
                })
                stress = None
                i += len(alias)
                break
        else:
            return None, ch
    return out, None


def safe_name(word):
    """ファイル名にできる形にする(小文字にして a〜z 0〜9 以外を落とす)"""
    return re.sub(r"[^a-z0-9]", "", word.lower())


# ── 音声づくり ────────────────────────────────────────────
class Speaker:
    """Piper で読み上げて mp3 にする。モデルの読み込みは1回だけ"""

    def __init__(self, voice_path):
        from piper import PiperVoice          # 使うときだけ読み込む
        self.voice = PiperVoice.load(voice_path)
        self.tmp = tempfile.mkdtemp()

    def say(self, text, mp3_path):
        wav_path = os.path.join(self.tmp, "t.wav")
        with wave.open(wav_path, "wb") as wav:
            self.voice.synthesize_wav(text, wav)
        os.makedirs(os.path.dirname(mp3_path), exist_ok=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav_path,
                        "-ac", "1", "-ar", MP3_RATE,
                        "-codec:a", "libmp3lame", "-b:a", MP3_BITRATE, mp3_path],
                       check=True)


# ── 元データの取得 ─────────────────────────────────────────
def fetch_sources():
    os.makedirs("source", exist_ok=True)
    for name in SOURCE_FILES:
        path = os.path.join("source", name)
        if not os.path.exists(path):
            print(f"取得中: {name}")
            urllib.request.urlretrieve(SOURCE_URL + name, path)
    return {name: os.path.join("source", name) for name in SOURCE_FILES}


def load_brown(path, limit):
    """頻出順リストを読む。1行 = 順位 / 単語 / 発音(複数はカンマ区切り)"""
    rows = []
    for line in open(path, encoding="utf-8"):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 3:
            continue
        rank, word, ipa_field = parts[0], parts[1], parts[2]
        variants = [v.strip() for v in ipa_field.split(",") if v.strip()]
        if not variants:
            continue
        rows.append({"rank": int(rank), "word": word, "variants": variants})
        if len(rows) >= limit:
            break
    return rows


# ── ここから本体 ───────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=WORD_LIMIT, help="作る単語の数")
    ap.add_argument("--force", action="store_true", help="すでにある音声も作り直す")
    args = ap.parse_args()

    if not os.path.exists(VOICE):
        sys.exit(f"音声モデルがない: {VOICE}\n"
                 "  .venv/bin/python -m piper.download_voices en_US-lessac-medium --data-dir voices")
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg が見つからない(brew install ffmpeg)")

    sources = fetch_sources()
    words = load_brown(sources["brown-frequency-list-with-ipa.txt"], args.limit)
    print(f"対象: 上位 {len(words)} 語")

    speaker = Speaker(VOICE)

    # ① 音素マスター(例単語を読み上げる)
    phonemes = []
    for arpabet, ipa, example, aliases in PHONEME_TABLE:
        path = phoneme_audio_path(arpabet)
        if args.force or not os.path.exists(path):
            speaker.say(example, path)
        phonemes.append({"ipa": ipa, "arpabet": arpabet, "example": example,
                         "audio": path, "aliases": aliases})
    json.dump(phonemes, open("phonemes.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"音素マスター: {len(phonemes)}音 → phonemes.json")

    # ② 単語データ
    entries, failed, used_names = [], [], {}
    for row in words:
        word, ipa = row["word"], row["variants"][0]   # 発音が複数あるときは先頭を使う
        parts, bad = split_ipa(ipa)
        if parts is None:
            failed.append({"rank": row["rank"], "word": word, "ipa": ipa,
                           "reason": f"音素マスターにない記号: {bad}"})
            continue
        if "".join(p["text"] for p in parts) != ipa:   # 元のIPAに戻せるか確かめる
            failed.append({"rank": row["rank"], "word": word, "ipa": ipa,
                           "reason": "分解をつなげても元の発音記号に戻らない"})
            continue
        name = safe_name(word)
        if not name:
            failed.append({"rank": row["rank"], "word": word, "ipa": ipa,
                           "reason": "ファイル名にできる文字がない"})
            continue
        if name in used_names:                         # 小文字化で名前がぶつかった場合
            failed.append({"rank": row["rank"], "word": word, "ipa": ipa,
                           "reason": f"ファイル名が {used_names[name]} と重なる"})
            continue
        used_names[name] = word
        audio = f"audio/words/{name}.mp3"
        if args.force or not os.path.exists(audio):
            speaker.say(word.lower(), audio)
        entries.append({"spelling": word.lower(), "rank": row["rank"],
                        "ipa": ipa, "ipa_variants": row["variants"],
                        "phonemes": parts, "audio": audio})
        if len(entries) % 100 == 0:
            print(f"  {len(entries)} 語")

    json.dump(entries, open("words.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(failed, open("failed.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print("\n── まとめ ──")
    print(f"成功: {len(entries)} 語 → words.json / audio/words/")
    print(f"失敗: {len(failed)} 語 → failed.json")
    for f in failed[:10]:
        print(f"  {f['word']}: {f['reason']}")
    if len(failed) > 10:
        print(f"  ほか {len(failed) - 10} 件")


if __name__ == "__main__":
    main()

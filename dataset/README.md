# 発音学習用データセット

英単語ごとに「つづり・発音記号・1音ごとの分解・音声」をそろえたデータです。
Chromebook と iPhone のブラウザでそのまま再生できる mp3 を使います。

## 中身

| ファイル | 中身 |
|---|---|
| `phonemes.json` | 音素マスター(39音) |
| `words.json` | 単語データ(頻出順の上位1000語) |
| `failed.json` | 分解できなかった単語(現在 0件) |
| `audio/phonemes/*.mp3` | 音素の音(例単語を読み上げたもの。39ファイル) |
| `audio/words/*.mp3` | 単語の音(1000ファイル) |
| `test.html` | 実機で再生を確かめるページ |
| `build-dataset.py` | これらを作り直すスクリプト |

音声はすべて **MPEG-1 Layer III / 44.1kHz / モノラル / 64kbps**、合計 5.4MB です。
JSON の中の音声パスはすべて相対パスなので、このフォルダごと Web に置けます。

## words.json の形

```json
{
  "spelling": "that",
  "rank": 7,
  "ipa": "ˈðæt",
  "ipa_variants": ["ˈðæt", "ðət"],
  "phonemes": [
    { "text": "ˈð", "ipa": "ð", "arpabet": "DH", "stress": "primary",
      "long": false, "audio": "audio/phonemes/dh.mp3" },
    { "text": "æ", "ipa": "æ", "arpabet": "AE", "stress": null,
      "long": false, "audio": "audio/phonemes/ae.mp3" },
    { "text": "t", "ipa": "t", "arpabet": "T", "stress": null,
      "long": false, "audio": "audio/phonemes/t.mp3" }
  ],
  "audio": "audio/words/that.mp3"
}
```

- `ipa_variants` … 元データに複数の発音があるときは全部残す。分解と音声は先頭のものを使う
- `text` … 発音記号そのもの。**つなげると `ipa` に完全に戻る**(生成時に1語ずつ検査している)
- `stress` … 強く読む印。IPA の決まりどおり音節の先頭に付くので、`ˈðæt` では最初の `ð` に付く
- `long` … 長音記号(ː)が付いているか
- `spelling` … 小文字にしたつづり(`it's` のような記号はそのまま残す)

## phonemes.json の形

```json
{ "ipa": "v", "arpabet": "V", "example": "van",
  "audio": "audio/phonemes/v.mp3", "aliases": ["v"] }
```

`aliases` は元データの書き方のゆれを吸収するための一覧です(例:ER は `ɝː ɚː ɜː ɝ ɚ ɜ` を同じ音として扱う)。

## 作り直し方

```bash
# 準備(1回だけ)
python3 -m venv dataset/.venv
dataset/.venv/bin/pip install piper-tts
dataset/.venv/bin/python -m piper.download_voices en_US-lessac-medium --data-dir dataset/voices

# 生成
dataset/.venv/bin/python dataset/build-dataset.py            # 1000語(約1分)
dataset/.venv/bin/python dataset/build-dataset.py --limit 10 # 試験用に10語だけ
dataset/.venv/bin/python dataset/build-dataset.py --force    # 音声も作り直す
```

単語数・声・音質は `build-dataset.py` の先頭の定数(`WORD_LIMIT` `VOICE` `MP3_BITRATE`)で変えられます。
元データ(cmudict-ipa)と声のモデルは自動で取得し、容量が大きいので git には入れていません。

## 出どころ

- 発音記号:[menelik3/cmudict-ipa](https://github.com/menelik3/cmudict-ipa)(CMU 発音辞書を IPA にしたもの)
- 音声:[Piper](https://github.com/OHF-Voice/piper1-gpl) の `en_US-lessac-medium`(アメリカ英語)

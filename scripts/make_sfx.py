#!/usr/bin/env python3
"""効果音(ページめくり音・読了ファンファーレ)を追加ライブラリなしで生成するスクリプト"""
import math, struct, wave, os, subprocess, tempfile

RATE = 44100

def tone(freq, dur, vol=0.5, decay=6.0):
    """やわらかい音色の1音(基音+弱い倍音、なめらかな減衰)"""
    n = int(RATE * dur)
    out = []
    for i in range(n):
        t = i / RATE
        env = math.exp(-decay * t) * min(1.0, i / (RATE * 0.005))
        v = (math.sin(2 * math.pi * freq * t)
             + 0.3 * math.sin(2 * math.pi * freq * 2 * t)
             + 0.1 * math.sin(2 * math.pi * freq * 3 * t))
        out.append(v * env * vol)
    return out

def mix(base, add, offset_sec):
    ofs = int(RATE * offset_sec)
    while len(base) < ofs + len(add):
        base.append(0.0)
    for i, v in enumerate(add):
        base[ofs + i] += v
    return base

def save(samples, path):
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp = f.name
    with wave.open(tmp, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        peak = max(1.0, max(abs(s) for s in samples))
        w.writeframes(b"".join(
            struct.pack("<h", int(max(-1, min(1, s / peak)) * 32000)) for s in samples))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "48000", tmp, path], check=True)
    os.remove(tmp)
    print(f"created {path}")

# ページをめくる音:短くやわらかい「ポン」
pop = []
n = int(RATE * 0.09)
for i in range(n):
    t = i / RATE
    freq = 620 - 320 * (t / 0.09)  # 高い音から低い音へ
    env = math.exp(-28 * t) * min(1.0, i / (RATE * 0.003))
    pop.append(math.sin(2 * math.pi * freq * t) * env * 0.55)
save(pop, "sfx/page.m4a")

# 読了のファンファーレ:ドミソド↑の明るいアルペジオ
fanfare = []
for k, (f, d) in enumerate([(523.25, 0.16), (659.25, 0.16), (783.99, 0.16), (1046.5, 0.5)]):
    mix(fanfare, tone(f, d + 0.25, vol=0.45, decay=5.0), k * 0.13)
mix(fanfare, tone(1318.5, 0.5, vol=0.18, decay=4.0), 0.39)  # 最後にキラッと高い音
save(fanfare, "sfx/finish.m4a")

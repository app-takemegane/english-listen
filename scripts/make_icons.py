#!/usr/bin/env python3
"""アプリのアイコン(PNG)を追加ライブラリなしで生成するスクリプト"""
import struct, zlib, math, os

ORANGE = (247, 148, 29)
ORANGE_DARK = (239, 127, 16)
WHITE = (255, 255, 255)
YELLOW = (255, 210, 63)
BROWN = (74, 55, 40)

def make_icon(size, rounded=True):
    px = bytearray(size * size * 4)
    r_corner = size * 0.22
    cx_sun, cy_sun, r_sun = size * 0.5, size * 0.34, size * 0.17
    for y in range(size):
        for x in range(size):
            # 角丸の判定
            inside = True
            if rounded:
                dx = max(r_corner - x, x - (size - 1 - r_corner), 0)
                dy = max(r_corner - y, y - (size - 1 - r_corner), 0)
                inside = (dx * dx + dy * dy) <= r_corner * r_corner
            i = (y * size + x) * 4
            if not inside:
                px[i:i+4] = b"\x00\x00\x00\x00"
                continue
            # 背景(上から下へ少し濃くなるオレンジ)
            t = y / size
            c = tuple(int(ORANGE[k] + (ORANGE_DARK[k] - ORANGE[k]) * t) for k in range(3))
            # 太陽
            d_sun = math.hypot(x - cx_sun, y - cy_sun)
            if d_sun <= r_sun:
                c = YELLOW
                # 目と口
                ex = size * 0.055
                for sx in (-1, 1):
                    if math.hypot(x - (cx_sun + sx * ex), y - (cy_sun - size*0.02)) <= size * 0.018:
                        c = BROWN
                if abs(d_sun - r_sun * 0.55) <= size * 0.012 and y > cy_sun + size * 0.03:
                    c = BROWN
            # 太陽の光(短い線を8方向に)
            for k in range(8):
                ang = k * math.pi / 4
                lx = cx_sun + math.cos(ang) * (r_sun + size * 0.06)
                ly = cy_sun + math.sin(ang) * (r_sun + size * 0.06)
                if math.hypot(x - lx, y - ly) <= size * 0.028:
                    c = YELLOW
            # 開いた本(下半分)
            bx, by = size * 0.5, size * 0.72
            bw, bh = size * 0.30, size * 0.16
            if abs(x - bx) <= bw and abs(y - by) <= bh:
                slope = (abs(x - bx) / bw) * size * 0.045
                if y >= by - bh + slope:
                    c = WHITE
                    if abs(x - bx) <= size * 0.008:
                        c = (230, 220, 205)
            px[i] = c[0]; px[i+1] = c[1]; px[i+2] = c[2]; px[i+3] = 255
    return bytes(px)

def write_png(path, size, pixels):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    raw = b"".join(b"\x00" + pixels[y*size*4:(y+1)*size*4] for y in range(size))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    print(f"created {path}")

os.makedirs("img", exist_ok=True)
write_png("img/icon-512.png", 512, make_icon(512))
write_png("img/icon-192.png", 192, make_icon(192))
# iPhoneのホーム画面用は角丸なし(iOSが自動で角を丸める)
write_png("img/apple-touch-icon.png", 180, make_icon(180, rounded=False))

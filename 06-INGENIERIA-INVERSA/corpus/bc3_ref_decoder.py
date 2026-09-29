#!/usr/bin/env python3
"""Decodificador BC3 independiente, en Python, para arbitrar la discrepancia.

Por que existe: hay un desacuerdo entre la salida de la GPU y la referencia de
C, y las dos pueden venir de codigo que yo no escribi. Este decoder esta escrito
solo desde la especificacion BC3, no desde el C ni desde el shader, asi que si
discrepa de ambos el culpable es uno de los dos.

Layout del bloque (16 B):
  [0] a0  [1] a1  [2..7] a_idx (16 x 3 bit, LSB-first)  [8..9] c0 RGB565
  [10..11] c1 RGB565  [12..15] c_idx (16 x 2 bit, LSB-first)

Interpolacion alfa. a0 > a1: 8 entradas, /7, con redondeo +3 (AD-11):
  a[0]=a0 a[1]=a1  a[i]=((8-i)*a0 + (i-1)*a1 + 3)/7   para i=2..7
a0 <= a1: 6 entradas, /5, y las DOS entradas sobrantes valen 0 y 255:
  a[0]=a0 a[1]=a1  a[i]=((6-i)*a0 + i*a1)/5  para i=2..5   a[6]=0  a[7]=255
OJO con a0 == a1: cae en la segunda rama, asi que a[6] y a[7] valen 0 y 255, NO a0.
Asumir a0==a1 -> todo a0 es el error mas caro de este decoder.

Color: los endpoints son RGB565 y la interpolacion se hace EN 5 BITS, antes de
expandir a 8. t=(2*a0+a1)/3 en 5 bits, y luego (t<<3)|(t>>2). Interpolar en 8
bits da numeros distintos y una discrepancia distinta en cada pixel.
"""
import sys


def a_idx(block, p):
    """16 indices de 3 bits, LSB-first, con straddling entre bytes."""
    bit = 3 * p
    byte = bit >> 3
    shift = bit & 7
    v = block[2 + byte] >> shift
    if shift > 5:
        v |= block[2 + byte + 1] << (8 - shift)
    return v & 7


def c_idx(block, p):
    return (block[12 + (p >> 2)] >> (2 * (p & 3))) & 3


def expand5(v5):
    return (v5 << 3) | (v5 >> 2)


def decode_block(block):
    a0, a1 = block[0], block[1]
    if a0 > a1:
        pal = [a0, a1] + [((8 - i) * a0 + (i - 1) * a1 + 3) // 7
                          for i in range(2, 8)]
        mode = 8
    else:
        # a0 == a1 tambien entra aqui: a[6] y a[7] valen 0 y 255, no a0.
        pal = [a0, a1] + [((6 - i) * a0 + i * a1) // 5 for i in range(2, 6)]
        pal += [0, 255]
        mode = 6

    c0 = block[8] | (block[9] << 8)
    c1 = block[10] | (block[11] << 8)
    # interpolar en 5 bits, no en 8
    ch0 = [(c0 >> s) & 0x1F for s in (11, 5, 0)]
    ch1 = [(c1 >> s) & 0x1F for s in (11, 5, 0)]
    cpal = [
        tuple(expand5(ch0[i]) for i in range(3)),
        tuple(expand5(ch1[i]) for i in range(3)),
        tuple(expand5((2 * ch0[i] + ch1[i]) // 3) for i in range(3)),
        tuple(expand5((ch0[i] + 2 * ch1[i]) // 3) for i in range(3)),
    ]

    out = bytearray(64)
    for p in range(16):
        a = pal[a_idx(block, p)]
        r, g, b = cpal[c_idx(block, p)]
        out[p * 4 + 0] = r
        out[p * 4 + 1] = g
        out[p * 4 + 2] = b
        out[p * 4 + 3] = a
    return out, mode


def main():
    bc3_path, ref_path, out_png = sys.argv[1], sys.argv[2], sys.argv[3]
    bc3 = open(bc3_path, "rb").read()
    n = len(bc3) // 16
    mine = bytearray()
    modes = {8: 0, 6: 0}
    for b in range(n):
        px, m = decode_block(bc3[b * 16:(b + 1) * 16])
        mine += px
        modes[m] += 1

    ref = open(ref_path, "rb").read()
    print(f"  bloques={n}  rampa 8-valores(a0>a1)={modes[8]}  6-valores(a0<=a1)={modes[6]}")

    d_ref = sum(1 for i in range(len(ref)) if mine[i] != ref[i])
    print(f"  mi decoder (spec BC3) vs ref.rgba : {d_ref} de {len(ref)} bytes distintos")

    try:
        from PIL import Image
        gpu = Image.open(out_png).convert("RGBA").tobytes()
        # el PNG va en orden imagen; mi decoder en orden bloque
        img = bytearray(len(gpu))
        side = int(round(n ** 0.5))
        for b in range(n):
            bx, by = (b % side) * 4, (b // side) * 4
            for py in range(4):
                o = ((by + py) * side * 4 + bx) * 4
                img[o:o + 16] = mine[b * 64 + py * 16: b * 64 + py * 16 + 16]
        d_gpu = sum(1 for i in range(len(gpu)) if img[i] != gpu[i])
        print(f"  mi decoder (spec BC3) vs PNG de la GPU : {d_gpu} de {len(gpu)} bytes distintos")
    except ImportError:
        print("  (PIL ausente: no se compara contra el PNG)")


if __name__ == "__main__":
    main()

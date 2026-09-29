#!/usr/bin/env python3
"""Genera el corpus de texturas de prueba de la integracion Fase 1 -> Fase 2.

Determinista: la misma semilla produce los mismos bytes. Sin aleatoriedad de
libreria, porque el valor de esta medicion es que otra sesion pueda reproducirla.

Cada textura es 64x64 RGBA = 256 bloques BC3 de 4x4. Se eligieron tres contenidos
distintos a proposito, no tres recortes de lo mismo:

  T1 gradiente   contenido suave, rampa de alfa -> el caso favorable
  T2 ruido       ruido independiente por canal -> el peor caso para BC3
  T3 estructura  bordes duros y alfa plano -> casos que T1 y T2 no producen

La razon de los tres: BC3 tiene 4 bits por sub-bloque de color y 3 de alfa. El
gradiente cae donde la interpolacion rinde; el ruido, donde no; la estructura,
donde aparecen bloques de color constante (a0 == a1) y alfa constante, que es la
rama que el corpus sintetico de la Fase 2 declara "no alcanzable via encoder".

Salida: <outdir>/t1_gradiente.png, t2_ruido.png, t3_estructura.png
       <outdir>/MANIFEST.sha256
"""
import hashlib
import os
import struct
import sys
import zlib

W = H = 64
MASK32 = 0xFFFFFFFF


def lcg(seed):
    """LCG 32-bit explicito. El corpus de la Fase 2 usa la misma familia
    (test_decompress.c, semilla 12345), asi que las dos medidas son del mismo
    generador y no dependen de la version de Python."""
    s = seed & MASK32
    while True:
        s = (1664525 * s + 1013904223) & MASK32
        yield s


def write_png(path, pixels):
    """PNG RGBA de 8 bits, sin dependencias externas.

    No uso PIL aqui a proposito: el corpus tiene que ser regenerable en un host
    sin ella. zlib y struct son de la biblioteca estandar."""
    raw = bytearray()
    for y in range(H):
        raw.append(0)                      # filtro None
        raw += pixels[y]

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & MASK32)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def t1_gradiente():
    """Rampa lineal en los tres canales y rampa de alfa de 0 a 255.
    Contenido de baja frecuencia: el mejor caso para un codificador de bloques."""
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            row += bytes((
                (x * 255) // (W - 1),
                (y * 255) // (H - 1),
                ((x + y) * 255) // (W + H - 2),
                (x * 255) // (W - 1),          # alfa acoplado a x
            ))
        rows.append(row)
    return rows


def t2_ruido():
    """Ruido independiente por canal, alfa tambien.
    El peor caso: ninguna correlacion que un bloque de 4x4 pueda capturar."""
    g = lcg(12345)
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            row += bytes((next(g) >> 24, next(g) >> 24, next(g) >> 24, next(g) >> 24))
        rows.append(row)
    return rows


def t3_estructura():
    """Captura de interfaz fingida: 8x8 celdas de color plano, fondo distinto,
    y alfa binario (0 o 255).

    Produce bloques de color constante (a0 == a1) y de alfa constante. La rama
    a0 == a1 es la que el corpus de la Fase 2 marca como 16 de 64 bloques y a la
    que la nota de AD-11 dice que no debe interpolar."""
    pal = [(0, 0, 0, 0), (24, 24, 32, 255), (200, 60, 60, 255),
           (60, 200, 90, 255), (240, 240, 240, 255), (40, 90, 200, 255)]
    rows = []
    for y in range(H):
        row = bytearray()
        for x in range(W):
            cx, cy = x // 8, y // 8
            r, g, b, a = pal[(cx * 3 + cy * 5) % len(pal)]
            if (cx + cy) % 7 == 0:            # algunas celdas transparentes
                a = 0
            row += bytes((r, g, b, a))
        rows.append(row)
    return rows


CORPUS = [
    ("t1_gradiente.png", t1_gradiente),
    ("t2_ruido.png", t2_ruido),
    ("t3_estructura.png", t3_estructura),
]


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    lines = []
    for name, fn in CORPUS:
        path = os.path.join(outdir, name)
        write_png(path, fn())
        h = hashlib.sha256(open(path, "rb").read()).hexdigest()
        lines.append(f"{h}  {name}")
        print(f"  {name:<20} {W}x{H} RGBA  {256} bloques  sha256={h[:16]}...")
    man = os.path.join(outdir, "MANIFEST.sha256")
    with open(man, "w") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  manifiesto: {man}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")

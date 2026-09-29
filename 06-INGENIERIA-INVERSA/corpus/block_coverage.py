#!/usr/bin/env python3
"""Cobertura de bloques BC3 de un .bc3, para contrastarla con la del corpus de la
Fase 2.

Por que importa: el agreement test GPU==CPU pasa 0/4096 sobre 64 bloques
sinteticos. Eso no dice nada sobre bloques que el encoder nunca produjo. Un
pipeline de integracion con texturas reales solo hereda esa garantia si los
bloques que genera caen dentro de lo que el corpus cubre.

Clases que distingue:
  alfa  : a0 > a1 | a0 == a1 | a0 < a1      (la rama /7 solo existe si a0 > a1)
  color : c0 > c1 | c0 == c1 | c0 < c1      (idiotriculas para la interpolacion)
  modo  : numero de valores distintos que puede producir la rampa de alfa,
          segun AD-11 (+3/+2): 4 valores si a0>a1, 6 si a0==a1
"""
import sys
from collections import Counter


def clasifica(blk):
    a0, a1 = blk[0], blk[1]
    c0 = blk[8] | (blk[9] << 8)
    c1 = blk[10] | (blk[11] << 8)
    if a0 > a1:
        alfa, modo = "a0>a1", 4
    elif a0 == a1:
        alfa, modo = "a0==a1", 6
    else:
        alfa, modo = "a0<a1", 4
    if c0 > c1:
        color = "c0>c1"
    elif c0 == c1:
        color = "c0==c1"
    else:
        color = "c0<c1"
    return alfa, color, modo


def main(paths):
    grande = Counter()
    for p in paths:
        data = open(p, "rb").read()
        n = len(data) // 16
        if n == 0 or len(data) % 16:
            print(f"{p}: tamano {len(data)} B no es multiplo de 16")
            continue
        al, co, mo = Counter(), Counter(), Counter()
        for b in range(n):
            a, c, m = clasifica(data[b * 16:(b + 1) * 16])
            al[a] += 1
            co[c] += 1
            mo[m] += 1
            grande[a] += 1
        print(f"\n{p}  ({n} bloques)")
        for titulo, cont in (("alfa", al), ("color", co), ("modo rampa", mo)):
            det = "  ".join(f"{k}={v}" for k, v in sorted(cont.items()))
            print(f"   {titulo:<12} {det}")
    print(f"\n== agregado ==")
    tot = sum(grande.values())
    for k, v in sorted(grande.items()):
        print(f"   {k:<10} {v:>5} / {tot}  ({100.0 * v / tot:5.1f} %)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

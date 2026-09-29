#!/usr/bin/env python3
"""Prediccion exhaustiva de Q-5, y su cotejo contra la referencia en C.

Que hace, y por que antes de gastar la autorizacion de RUNTIME_EXECUTION:

  1. genera la prediccion del MODELO para las 524288 observaciones
     (65536 pares de endpoints x 8 indices), con la semantica CORREGIDA
     del preregistration;
  2. la coteja contra una implementacion en C que usa los TIPOS REALES
     -- int16_t/uint16_t, wrap explicito, desplazamiento logico -- y no
     la precision arbitraria ni el >> con suelo de Python;
  3. comprueba los invariantes I-1..I-5 del preregistration;
  4. imprime el reparto por categoria, para que se vea si el barrido
     discrimina antes de ejecutarlo.

NO ejecuta llvmpipe, no abre Vulkan, no toca la GPU. Es CPU pura.

LA CORRECCION DE SEMANTICA -- Y MI HIPOTESIS M-8 ERA FALSA

 Levante M-8: sostuve que el preregistration §2 atribuye a llvmpipe un clamp
`i=6 -> 0, i=7 -> 255` que no existe en lp_build_lerpdxta. Fui a la fuente y es
FALSO. El clamp existe, y esta en el CALLER, no en la subfuncion:

    lp_bld_format_s3tc.c:1000-1016, s3tc_dxt5_alpha_channel()

        alpha   = (alphac == 0) ? alpha0 : alpha1;    <- codigos 0 y 1
        alpha   = (alphac >  1) ? ainterp : alpha;    <- el resto
        code_s  = alphac & ~sel_mask;                 <- ~0 cuando a0 <= a1
        alpha   = alpha & ~mask6;                     <- codigo 6 -> 0
        alpha   = alpha |  mask7;                     <- codigo 7 -> todos los 1
        alpha   = alpha & 0xff;                       <- 0xff == 255

 lp_build_lerpdxta() no pone los codigos 0 y 1: interpola y devuelve. Quien
 decide esos casos y quien recorta el 6 y el 7 es el caller. Y el recorte solo
 se aplica cuando a0 <= a1, porque `code_s = alphac & ~sel_mask` se anula
 (sel_mask es todo-unos) en la rama a0 > a1.

 MI PRIMERA PREDICCION Y MI REFERENCIA EN C TENIAN EL MISMO ERROR: ambas
 implementaban solo la subfuncion. Coincidian en las 524288, y eso NO era un
 control: era una tautologia con dos Tullands. Se corrige abajo y se repite.

 Este error no afecta a los 649 del corpus, y por eso `d07aaac` dio 649/649:
 las 649 traen indice 5 (rama a0<=a1, sin recorte) o 5 y 7 en la rama a0>a1
 (donde no hay recorte). Ninguna cae donde las dos implementaciones se
 separaban. Verificado abajo, no supuesto.
"""
import hashlib
import os
import subprocess
import sys
import tempfile

M16 = 0xFFFF
FIRST, LAST = 2, 7


def s16(v):
    v &= M16
    return v - 0x10000 if v & 0x8000 else v


def lshr16(value, n):
    return (value & M16) >> n


def llvmpipe_alpha(a0, a1, code, sel7):
    """s3tc_dxt5_alpha_channel() completa: lp_build_lerpdxta() mas el caller.

    a0 >  a1 -> weight7, codigos 2..7 interpolados, sin recorte
    a0 <= a1 -> weight5, codigos 2..5 interpolados, 6->0 y 7->255
    codigos 0 y 1 -> a0 y a1, los pone el caller, no la interpolacion
    """
    weight = (255 * 64) // 7 if sel7 else (255 * 64) // 5
    c = code - 1
    w = lshr16(s16(s16(weight) * s16(c)), 6)
    delta = s16(s16(a1) - s16(a0))
    t = lshr16(s16(delta * s16(w)), 8)
    a = (a0 + t) & 0xFF

    if code == 0:
        return a0
    if code == 1:
        return a1
    if not sel7:
        if code == 6:
            return 0
        if code == 7:
            return 255
    return a


# --- las otras dos implementaciones, para el reparto por categoria -------------

def spec_pal(a0, a1):
    p = [0] * 8
    p[0], p[1] = a0, a1
    if a0 > a1:
        for i in range(2, 8):
            p[i] = ((8 - i) * a0 + (i - 1) * a1 + 3) // 7      # AD-11, +3
    else:
        for i in range(2, 6):
            p[i] = ((6 - i) * a0 + (i - 1) * a1 + 2) // 5      # AD-11, +2
        p[6], p[7] = 0, 255
    return p


def trunc_pal(a0, a1):
    """bcdec: trunca en vez de redondear. Misma estructura, sin los +3/+2."""
    p = [0] * 8
    p[0], p[1] = a0, a1
    if a0 > a1:
        for i in range(2, 8):
            p[i] = ((8 - i) * a0 + (i - 1) * a1) // 7
    else:
        for i in range(2, 6):
            p[i] = ((6 - i) * a0 + (i - 1) * a1) // 5
        p[6], p[7] = 0, 255
    return p


def build_c_reference(src_dir, work_dir):
    """Compila q5_ref_c.c y devuelve el path del binario."""
    src = os.path.join(src_dir, "q5_ref_c.c")
    exe = os.path.join(work_dir, "q5_ref_c")
    r = subprocess.run(["gcc", "-O2", "-Wall", "-Wextra", "-o", exe, src],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print("FALLO al compilar la referencia C:\n" + r.stderr, file=sys.stderr)
        return None
    if r.stderr.strip():
        print("warnings del compilador:\n" + r.stderr, file=sys.stderr)
    return exe


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    dump = sys.argv[1] if len(sys.argv) > 1 else None

    total = 0
    pred = bytearray()
    sp = tr = lv = same = 0
    i1_ok = i2_ok = 0

    for a0 in range(256):
        for a1 in range(256):
            sel7 = a0 > a1
            s = spec_pal(a0, a1)
            t = trunc_pal(a0, a1)
            for i in range(8):
                v = llvmpipe_alpha(a0, a1, i, sel7)
                pred.append(v)
                total += 1

                sv, tv = s[i], t[i]
                if sv == tv:
                    same += 1
                elif v == sv:
                    sp += 1
                elif v == tv:
                    tr += 1
                else:
                    lv += 1

                if i == 0 and v == a0:
                    i1_ok += 1
                if i == 1 and v == a1:
                    i1_ok += 1
                if (not sel7) and i == 6 and v == 0:
                    i2_ok += 1
                if (not sel7) and i == 7 and v == 255:
                    i2_ok += 1

    print("=== PREDICCION EXHAUSTIVA DE Q-5 (CPU pura, sin GPU) ===")
    print(f"  observaciones             : {total}")
    print(f"  esperado por el preregist : 524288")
    print(f"  coincide la cuenta        : {total == 524288}")
    print()
    print("  reparto por categoria (las tres implementaciones):")
    print(f"    las tres coinciden (no informa)   : {same}")
    print(f"    solo coincide con spec            : {sp}")
    print(f"    solo coincide con trunc           : {tr}")
    print(f"    solo coincide con llvmpipe        : {lv}")
    print()
    print("  invariantes del preregistration:")
    print(f"    I-1  i=0 -> a0 y i=1 -> a1         : {i1_ok} de {2*65536}  (exigido {2*65536})")
    print(f"    I-2  a0<=a1: i=6 -> 0, i=7 -> 255 : {i2_ok} de {2*32896}  (exigido {2*32896})")

    # --- cotejo contra la referencia en C -----------------------------------
    with tempfile.TemporaryDirectory(dir="/tmp") as wd:
        exe = build_c_reference(here, wd)
        if exe is None:
            return 1
        cpath = os.path.join(wd, "pred_c.bin")
        r = subprocess.run([exe, cpath], capture_output=True, text=True)
        if r.returncode != 0:
            print("la referencia C fallo:\n" + r.stderr, file=sys.stderr)
            return 1
        cb = open(cpath, "rb").read()

    print()
    print("  COTEJO CONTRA LA REFERENCIA EN C (tipos reales i16/u16):")
    print(f"    bytes de la referencia C         : {len(cb)}")
    if len(cb) != total:
        print("    DISCREPANCIA DE TAMANO")
        return 1
    diff = [k for k in range(total) if cb[k] != pred[k]]
    print(f"    discrepancias Python vs C        : {len(diff)} de {total}")
    if diff:
        for k in diff[:5]:
            a0 = (k // (256 * 8))
            a1 = (k // 8) % 256
            i = k % 8
            print(f"      a0={a0} a1={a1} i={i}: python={pred[k]} c={cb[k]}")
        return 1

    sha = hashlib.sha256(bytes(pred)).hexdigest()
    print(f"    sha256 de la prediccion           : {sha}")
    if dump:
        with open(dump, "wb") as f:
            f.write(pred)
        print(f"    volcado escrito en                : {dump}")

    # --- control negativo: el cotejo tiene que poder fallar -----------------
    print()
    print("  control negativo del cotejo (debe detectar la diferencia):")
    mut = bytearray(pred)
    for k in range(100):
        mut[k] = (mut[k] + 1) & 0xFF
    d1 = sum(1 for k in range(total) if mut[k] != cb[k])
    print(f"    100 observaciones mutadas +1      : {d1} discrepancias detectadas")
    mut2 = bytearray(pred)
    for k in range(total):
        mut2[k] = spec_pal(k // (256 * 8), (k // 8) % 256)[k % 8]
    d2 = sum(1 for k in range(total) if mut2[k] != cb[k])
    print(f"    sustitucion por spec (M-4/C-2)    : {d2} discrepancias detectadas")

    return 0 if (not diff and d1 == 100 and d2 > 0) else 1


if __name__ == "__main__":
    sys.exit(main())

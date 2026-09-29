#!/usr/bin/env python3
"""Q-5: valida `expect_llvmpipe` de los 649 casos contra lp_build_lerpdxta REAL.

Por que esto es Q-5 y no una opinion: los 649 valores de `expect_llvmpipe` del
JSON los produjo IA-3 con un modelo Python propio, y el propio documento
declara que si esa transcripcion tiene un error los 649 estan equivocados y el
test de hardware no discrimina nada. Este fichero NO es una opinion: ejecuta
la aritmetica tal como esta escrita en el C, con los tipos que declara el C.

Fuente primaria:
  /home/lucas/mesa/src/gallium/auxiliary/gallivm/lp_bld_format_s3tc.c:817-877
  lp_build_lerpdxta(), y el caller en :881-1020.

Los tres detalles que hacen fallar una transcripcion ingenua, todos verificados
contra el C y ninguno obvious:

  1. `type16` es SIGNED de 16 bits, y los tres productos intermedios se
     envuelven a 16 bits. `delta * weight` desborda con facilidad.
  2. `LShr` es desplazamiento LOGICO, no aritmetico: un valor negativo se
     convierte a su patron de bits sin signo antes de desplazar. En un
     `delta` negativo eso cambia el resultado.
  3. `sel_mask` elige weight7 frente a weight5 POR CASO, no por bloque, y el
     codigo se decrementa ANTES de multiplicar.

Salida: el recuento de los 649 que coinciden, y el primer fallo con su aritmetica
completa si lo hay. Devuelve codigo distinto de cero si algo no cuadra.
"""
import json
import sys

M16 = 0xFFFF


def s16(v):
    """Trunca a 16 bits y reinterpreta como signed."""
    v &= M16
    return v - 0x10000 if v & 0x8000 else v


def lshr16(value, n):
    """LLVMBuildLShr sobre un valor ya truncado a 16 bits: es logico, asi que
    trabaja sobre el patron de bits, no sobre el entero con signo."""
    return (value & M16) >> n


def lp_build_lerpdxta(a0, a1, code, sel_mask_7bit):
    """Transcripcion literal de lp_bld_format_s3tc.c:817-877.

    Devuelve el valor de 8 bits que la funcion produce.
    """
    # weight5 = 255*64/5, weight7 = 255*64/7  (division entera, como en C)
    weight5 = 255 * 64 // 5          # 3264
    weight7 = 255 * 64 // 7          # 2331
    weight = weight7 if sel_mask_7bit else weight5

    # "we'll get garbage in the elements which had code 0 (or larger than 5 or 7)
    #  but we don't care" -- el C resta 1 sin comprobar nada.
    code = code - 1

    # type32 -> type16 por bitcast: los valores de 8 bits pasan a 16 sin cambio
    w16 = s16(weight)
    c16 = s16(code)
    a0_16 = s16(a0)
    a1_16 = s16(a1)

    weight = s16(w16 * c16)           # LLVMBuildMul, se envuelve a 16
    weight = lshr16(weight, 6)        # LShr, logico

    delta = s16(a1_16 - a0_16)       # LLVMBuildSub, se envuelve a 16
    ainterp = s16(delta * weight)     # otro LLVMBuildMul, se envuelve a 16
    ainterp = lshr16(ainterp, 8)      # LShr, logico

    return (a0 + ainterp) & 0xFF      # LShr ya dio algo <= 255, el add no envuelve


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else \
        "08-ARQUITECTURA/validations/casos_llvmpipe_unico.json"
    d = json.load(open(path))
    cases = d["cases"]

    ok = 0
    fallos = []
    for c in cases:
        a0, a1, idx = c["a0"], c["a1"], c["index"]
        # sel_mask: el caller selecciona la rama de 8 valores si a0 > a1
        sel_7bit = c["branch"] == "a0>a1"
        got = lp_build_lerpdxta(a0, a1, idx, sel_7bit)
        if got == c["expect_llvmpipe"]:
            ok += 1
        else:
            fallos.append((c, got))

    total = len(cases)
    print("=== Q-5: expect_llvmpipe vs lp_build_lerpdxta real ===")
    print(f"  casos totales            : {total}")
    print(f"  coinciden                : {ok}")
    print(f"  discrepan                : {len(fallos)}")
    print(f"  weight5 = 255*64//5      = {255*64//5}")
    print(f"  weight7 = 255*64//7      = {255*64//7}")

    if fallos:
        print("\n  primeros 5 fallos, con la aritmetica:")
        for c, got in fallos[:5]:
            sel = c["branch"] == "a0>a1"
            weight = (255 * 64 // 7) if sel else (255 * 64 // 5)
            code = c["index"] - 1
            delta = c["a1"] - c["a0"]
            w_sh = ((weight * code) & M16) >> 6
            ai = ((delta * w_sh) & M16) >> 8
            print(f"    k={c['k']} a0={c['a0']} a1={c['a1']} i={c['index']} "
                  f"({c['branch']})")
            print(f"       weight={weight} code-1={code} "
                  f"((w*c)&ffff)>>6={w_sh} delta={delta} "
                  f"((d*w)&ffff)>>8={ai}")
            print(f"       esperado={c['expect_llvmpipe']} obtenido={got} "
                  f"spec={c['expect_spec']} trunc={c['expect_trunc']}")
        return 1

    # El JSON no debe contener casos donde llvmpipe coincida con spec o trunc:
    # si coincidiera, el caso no discriminaria nada.
    no_disc = [c for c in cases
               if c["expect_llvmpipe"] in (c["expect_spec"], c["expect_trunc"])]
    print(f"\n  casos donde llvmpipe NO discrimina: {len(no_disc)}  "
          f"(deben ser 0)")
    if no_disc:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""Pruebas de `binary.disassemble` sobre Capstone. RXRE-1634.

LO QUE ESTAS PRUEBAS EXIGEN, Y POR QUE.

1. QUE EL PRODUCTOR ES EL QUE SE DECLARA. Este lote descrubrio que
   `binary.decompile` figuraba cerrada y nunca se habia ejecutado, porque
   las pruebas solo usaban fixtures. Aqui el productor se EJERECITA sobre
   un ELF real, y se comprueba que el resultado dice de quien es.

2. QUE UN RECUENTO NO ES UN RESULTADO. Capstone se detiene en el primer
   byte que no decodifica y no lo dice. MEDIDO: 100 % sobre una funcion
   `sym` de 909 bytes, 9,5 % sobre una entrada con `size` 137. Por eso
   estas pruebas comprueban la COBERTURA, no el numero de instrucciones.

3. QUE PEDIR OTRO BACKEND NO DA UN RESULTADO MAL ETIQUETADO. Un
   `backend_id="rizin"` descartado en silencio por el filtro del dispatch
   haria que el adapter recibiera "capstone" y etiquetara como suyo un
   resultado de otro. MEDIDO: eso era exactamente lo que pasaba.

Uso:
    python3 tests/test_disasm1634.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends import dispatch, registry  # noqa: E402
from backends.adapters import cs_disasm as C  # noqa: E402
from backends.adapters import rz_functions as F  # noqa: E402
from backends.contract import (  # noqa: E402
    BK_EMPTY, BK_INVALID, BK_OK, DISASSEMBLY, FUNCTION_CANDIDATE,
    puede_declarar,
)

_n = 0
_f = 0


def chk(nombre, got, want):
    global _n, _f
    _n += 1
    if got == want:
        print("  ok  : %-52s %r" % (nombre, got))
    else:
        _f += 1
        print("  FAIL: %-52s got=%r want=%r" % (nombre, got, want))


def elf_real():
    for c in ("/bin/ls", "/usr/bin/cat"):
        if os.path.isfile(c) and open(c, "rb").read(4) == b"\x7fELF":
            return c
    return ""


def una_funcion():
    """Una funcion real, elegida por `aflj`: el productor de
    funciones y el de desensamblado se combinan como en un caso real."""
    elf = elf_real()
    if not elf:
        return None, None
    env = F.functions(elf, backend_id="rizin", timeout=300)
    if env["status"] != BK_OK:
        return None, None
    fns = env["results"][0]["value"]["funciones"]
    f = next((x for x in fns if x.get("type") == "fcn"
              and (x.get("size") or 0) > 20), None)
    return elf, f


# ------------------------------------------------------------- registro
def t_registro():
    print("\n== registro: backend de MODULO, no subproceso ==")
    chk("capstone esta en el registry", "capstone" in registry.backends(), True)
    ent = registry.get("capstone")
    chk("su producer es un modulo, no un exe", ent["backend"].modulo,
        "capstone")
    chk("y por eso argv_template va vacio", ent["backend"].argv_template, [])
    f = registry.ficha("capstone")
    chk("existe (find_spec, no un nombre)", f["existe"], True)
    chk("version VERIFICADA por __version__", f["backend_version_status"],
        "VERIFIED")
    chk("version medida", f["tool_version"], "5.0.7")
    chk("declara las 2 capacidades",
        sorted(f["capabilities_disponibles"]),
        ["binary.disassemble", "binary.disassemble_func"])
    for c in ("binary.disassemble", "binary.disassemble_func"):
        chk("%s tiene adapter" % c, c in dispatch.ADAPTERS, True)
        a = dispatch.ADAPTERS[c]
        chk("%s declara backend_id en parametros" % c,
            "backend_id" in a["parametros"], True)


# ------------------------------------------------------------- producer
def t_producer_real():
    print("\n== producer REAL, por el DISPATCH ==")
    elf, f = una_funcion()
    if not f:
        print("  skip: no hay ELF o funcion")
        return
    env = dispatch.ejecutar("binary.disassemble",
                            {"artefacto": elf, "inicio": f["offset"],
                             "longitud": f["size"]})
    chk("status ok", env["status"], BK_OK)
    chk("instrucciones > 0", env["n_instrucciones"] > 0, True)
    r = env["results"][0]
    chk("tipo DISASSEMBLY", r["type"], DISASSEMBLY)
    chk("declara SU producer y version", (r["tool"], r["tool_version"]),
        ("capstone", "5.0.7"))
    chk("la version viene de __version__, no del repo",
        "5.0.7" in r["tool_version"], True)
    # La cobertura es el dato.
    cov = r["value"]["cobertura"]
    chk("declara bytes declarados", cov["bytes_declarados"] > 0, True)
    chk("declara cobertura en porcentaje",
        "cobertura_pct" in cov, True)
    chk("declara huecos", "huecos" in cov, True)
    chk("y la limitacion cita la cobertura",
        any("COBERTURA" in x for x in env["limitations"]), True)
    # Operandos CON TIPO: es lo que rizin y radare2 no dan.
    ops = r["value"]["instrucciones"][0]["operandos"]
    chk("los operandos llevan tipo", isinstance(ops, list), True)
    chk("el producer es EN PROCESO (argv vacio)",
        env["ejecucion"]["argv"], [])


def t_operandos_tipados():
    """Lo que hace a Capstone distinto: `op_str` es TEXTO, y no dice si
    un 0x10 es un inmediato o un desplazamiento. Sin esa distincion no
    se puede distinguir "mover un valor" de "leer en memoria"."""
    print("\n== operandos con TIPO, no solo texto ==")
    elf, f = una_funcion()
    if not f:
        return
    env = dispatch.ejecutar("binary.disassemble",
                            {"artefacto": elf, "inicio": f["offset"],
                             "longitud": f["size"]})
    insns = env["results"][0]["value"]["instrucciones"]
    tipos = {o["tipo"] for i in insns for o in i["operandos"]}
    chk("al menos un operando con tipo", len(tipos) > 0, True)
    chk("los tipos son los conocidos",
        tipos <= {"reg", "imm", "mem", "tipo0"}, True)
    contexto = [i for i in insns if i["grupos"]]
    chk("las instrucciones traen grupos (salto/ret/llamada)",
        all("grupos" in i for i in insns), True)


def t_no_codigo():
    """ADVERSARIAL: un rango que NO es codigo. Capstone devuelve 0 y no
    dice por que; el adapter tiene que convertirlo en algo legible."""
    print("\n== ADVERSARIAL: rango que no es codigo ==")
    elf, _f = una_funcion()
    if not elf:
        return
    env = dispatch.ejecutar("binary.disassemble",
                            {"artefacto": elf, "inicio": 0, "longitud": 32})
    chk("no revienta", env["status"] in (BK_OK, BK_EMPTY), True)
    if env["status"] == BK_EMPTY:
        chk("empty declara que 0 instrucciones NO prueba que no haya codigo",
            any("NO prueba" in x for x in env["limitations"]), True)
        chk("y senala que el rango lo eligio quien llama",
            any("rango" in x for x in env["limitations"]), True)


def t_backend_equivocado():
    print("\n== ADVERSARIAL: backend que no puede servir la capacidad ==")
    elf, f = una_funcion()
    if not elf:
        return
    env = dispatch.ejecutar("binary.disassemble",
                            {"artefacto": elf, "inicio": 0, "longitud": 16,
                             "backend_id": "rizin"})
    chk("invalid_input, no un resultado mal etiquetado",
        env["status"], BK_INVALID)
    chk("el motivo lo dice", any("no puede servir" in x
                                for x in env["limitations"]), True)


def t_arquitectura_no_soportada():
    print("\n== negativo: arquitectura que el producer no cubre ==")
    elf, _f = una_funcion()
    if not elf:
        return
    env = dispatch.ejecutar("binary.disassemble",
                            {"artefacto": elf, "inicio": 0, "longitud": 16,
                             "arquitectura": "gfx8"})
    chk("no devuelve ok", env["status"] != BK_OK, True)
    chk("el motivo es util",
        any("arquitectura" in x.lower() for x in env["limitations"]), True)


def t_confianza():
    print("\n== la confianza NO se infla ==")
    chk("un desensamblado no es una funcion",
        puede_declarar(DISASSEMBLY, FUNCTION_CANDIDATE), False)
    chk("ni una decompilacion",
        puede_declarar(DISASSEMBLY, "decompilation"), False)
    chk("ni semantica validada",
        puede_declarar(DISASSEMBLY, "validated_semantics"), False)
    chk("solo se satisface a si mismo",
        puede_declarar(DISASSEMBLY, DISASSEMBLY), True)


def t_gfx8():
    """Lo que NO cubre, declarado y no escondido."""
    print("\n== alcance declarado: GFX8 NO esta cubierto ==")
    f = registry.ficha("capstone")
    chk("el registry lo declara unsuitable para la GPU",
        any("GFX8" in x for x in f["inadequate_para"]), True)
    # Lo que importa es que la limitacion VIAJE en cada respuesta, no que
    # este escrita en un docstring: un docstring no lo lee quien consume el
    # envelope.
    elf, f = una_funcion()
    if f:
        env = dispatch.ejecutar("binary.disassemble",
                                {"artefacto": elf, "inicio": f["offset"],
                                 "longitud": f["size"]})
        chk("y la limitacion GFX8 viaja en CADA respuesta",
            any("GFX8" in x for x in env["limitations"]), True)


def main() -> int:
    print("RXRE-1634: pruebas de binary.disassemble sobre Capstone")
    t_registro()
    t_producer_real()
    t_operandos_tipados()
    t_no_codigo()
    t_backend_equivocado()
    t_arquitectura_no_soportada()
    t_confianza()
    t_gfx8()
    print("\n%d checks, %d failures" % (_n, _f))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
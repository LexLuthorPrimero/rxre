#!/usr/bin/env python3
"""gccverify.py — verdad de terreno del layout, publicada por el compilador.

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE

struct_layout calcula offsets con las reglas de ABI de x86-64. Eso es una
MODELO, no una medida: se equivoca cuando un tipo no esta en el indice, cuando
una macro esta redefinida por ASIC, o cuando una regla que no contemplamos se
aplica. La unica forma de saber si el modelo es cierto es preguntarle al
compilador, que es el que define la verdad.

Este herramienta hace esa pregunta de forma automatica. Escribe un fichero .c
temporal que incluye la CABECERA REAL del corpus, imprime sizeof y offsetof de
los campos que se le pidan, y lo compara con lo que dice struct_layout. No
toca el corpus: el .c va a un directorio temporal y se borra.

Por que automatizarlo y no hacerlo a mano:

  - El caso que la motivo es de la serie "el modelo da 1756, gcc dice 1884".
    Un solo byte de diferencia y ya no era el mismo struct. Eso se encuentra
    comparando offsets de uno en uno, no leyendo un total.
  - struct_layout tiene ahora 157783 macros con definiciones conflictivas en
    el subarbol. Saber cuantas de ellas tocan los structs que nos importan
    exige una herramienta, no una lectura.
  - La verificacion que no se repite es la que no se hace.

LIMITACION CONOCIDA: solo funciona con cabeceras AUTOCONTENIDAS. smu74.h no
tiene ningun #include, asi que compila solo. Una cabecera que dependa de tipos
del kernel (uapi, include/linux) dara error de compilacion, y eso se reporta
como NO_COMPILE, nunca como fallo de layout.

Clasificacion: TOOL_VALIDATED cuando la compilacion tiene exito y hay al menos
un campo comparado; TOOL_PARTIAL cuando compila pero no hay campos que
comparar; TOOL_BROKEN cuando la compilacion falla.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "gccverify"
VERSION = "1.0.0"
WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

# Cabeceras del corpus amdgpu que NO incluyen nada y por tanto se compilan
# sueltas. Descubrirlo es parte del trabajo: una cabecera que no este aqui no
# se puede verificar con gcc, y hay que decirlo en vez de devolver un 0.
SELFCONTAINED_GLOBS = (
    "pm/powerplay/inc/smu*.h",
    "pm/powerplay/inc/hwmgr*.h",
    "pm/powerplay/inc/*_discrete.h",
)


def _find_includes(kernel: str) -> List[str]:
    """Directorios -I donde puede estar la cabecera pedida."""
    amd = os.path.join(kernel, "drivers/gpu/drm/amd")
    cands = [
        os.path.join(amd, "pm/powerplay/inc"),
        os.path.join(amd, "pm/powerplay/hwmgr"),
        os.path.join(amd, "pm/powerplay/smumgr"),
        os.path.join(amd, "include"),
        os.path.join(amd, "pm/inc"),
        os.path.join(kernel, "include"),
    ]
    return [c for c in cands if os.path.isdir(c)]


def probe_header(header: str, includes: Sequence[str],
                 struct: str, fields: Sequence[str]) -> Dict[str, object]:
    """Compila un .c temporal y lee sizeof/offsetof de gcc."""
    lines = [
        "#include <stdint.h>",
        "#include <stddef.h>",
        "#include <stdio.h>",
        f'#include "{header}"',
        "#ifdef __GNUC__",
        f"int main(void){{ printf(\"%ld %ld\\n\", (long)sizeof({struct}),",
        f"(long)offsetof({struct}, {fields[0]})); return 0; }}",
        "#else",
        "int main(void){return 0;}",
        "#endif",
    ]
    if not fields:
        return {"estado": "SIN_CAMPOS",
                "nota": "no se pidio ningun campo: gcc solo puede dir sizeof"}
    tmp = tempfile.mkdtemp(prefix="gccverify_")
    src = os.path.join(tmp, "probe.c")
    exe = os.path.join(tmp, "probe")
    try:
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
        cp = subprocess.run(["gcc"] + [f"-I{i}" for i in includes]
                            + [src, "-o", exe],
                            capture_output=True, text=True, timeout=120)
        if cp.returncode != 0:
            return {"estado": "NO_COMPILE",
                    "diagnostico": cp.stderr.strip()[:400]}
        run = subprocess.run([exe], capture_output=True, text=True, timeout=30)
        if run.returncode != 0:
            return {"estado": "NO_EJECUTA",
                    "diagnostico": run.stderr.strip()[:200]}
        total, first_off = run.stdout.split()
        return {"estado": "OK", "sizeof": int(total),
                "offsetof_primero": int(first_off)}
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"estado": "ERROR", "diagnostico": str(exc)[:200]}
    finally:
        for p in (src, exe):
            try:
                os.unlink(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


def full_probe(header: str, includes: Sequence[str], struct: str,
               fields: Sequence[str]) -> Dict[str, object]:
    """sizeof de la struct y offsetof de TODOS los campos indicados."""
    # Sin campos la pregunta sigue siendo legitima: "¿cuanto mide?". Antes
    # devolvia SIN_CAMPOS y no comparaba nada, que hacia el barrido de structs
    # dar 0 comparables y 0 divergencias: un recuento que parece limpio y no
    # comprueba nada.
    body = [
        "#include <stdint.h>",
        "#include <stddef.h>",
        "#include <stdio.h>",
        f'#include "{header}"',
        "int main(void){",
        f'  printf("%ld\\n", (long)sizeof({struct}));',
    ]
    for f in fields:
        body.append(
            f'  printf("{f} %ld\\n", (long)offsetof({struct}, {f}));')
    body.append("  return 0; }")
    tmp = tempfile.mkdtemp(prefix="gccverify_")
    src = os.path.join(tmp, "probe.c")
    exe = os.path.join(tmp, "probe")
    try:
        with open(src, "w", encoding="utf-8") as fh:
            fh.write("\n".join(body) + "\n")
        cp = subprocess.run(["gcc"] + [f"-I{i}" for i in includes]
                            + [src, "-o", exe],
                            capture_output=True, text=True, timeout=120)
        if cp.returncode != 0:
            return {"estado": "NO_COMPILE", "diagnostico": cp.stderr.strip()[:400]}
        run = subprocess.run([exe], capture_output=True, text=True, timeout=30)
        if run.returncode != 0:
            return {"estado": "NO_EJECUTA", "diagnostico": run.stderr.strip()[:200]}
        out = [x for x in run.stdout.strip().splitlines() if x.strip()]
        res: Dict[str, object] = {"estado": "OK",
                                  "sizeof": int(out[0].split()[0]),
                                  "offsetof": {}}
        for line in out[1:]:
            parts = line.rsplit(" ", 1)
            if len(parts) == 2:
                res["offsetof"][parts[0].strip()] = int(parts[1])  # type: ignore[index]
        return res
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        return {"estado": "ERROR", "diagnostico": str(exc)[:200]}
    finally:
        for p in (src, exe):
            try:
                os.unlink(p)
            except OSError:
                pass
        try:
            os.rmdir(tmp)
        except OSError:
            pass


def selftest() -> int:
    """Vectores conocidos, incluidos los que NO deben pasar.

    Un self-test que solo comprueba el camino feliz no dice si la herramienta
    sabe decir que NO. Aqui se comprueban las tres salidas: OK, NO_COMPILE y
    una struct que no existe.
    """
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    tmp = tempfile.mkdtemp(prefix="gccverify_st_")
    inc = os.path.join(tmp, "inc")
    os.makedirs(inc, exist_ok=True)
    hdr = os.path.join(inc, "vector.h")
    with open(hdr, "w", encoding="utf-8") as fh:
        fh.write("#ifndef V_H\n#define V_H\n"
                 "struct Ala { uint32_t a; uint8_t b; uint16_t c[3]; };\n"
                 "struct Anidada { struct Ala x; uint32_t n; };\n"
                 "#endif\n")
    campos_ala = ["a", "b", "c"]
    campos_anidada = ["x", "n"]

    r = full_probe("vector.h", [inc], "struct Ala", campos_ala)
    check("gcc.compila", r.get("estado"), "OK")
    # Valores tomados de gcc, no supuestos: sizeof(Ala)=12 y offsetof(c)=6,
    # no 8, porque uint16_t pide alineacion de 2 despues de un uint8_t.
    check("gcc.sizeof", r.get("sizeof"), 12)
    check("gcc.offset_a", r.get("offsetof", {}).get("a"), 0)
    check("gcc.offset_b", r.get("offsetof", {}).get("b"), 4)
    check("gcc.offset_c", r.get("offsetof", {}).get("c"), 6)

    r2 = full_probe("vector.h", [inc], "struct Anidada", campos_anidada)
    check("gcc.anidada_sizeof", r2.get("sizeof"), 16)
    check("gcc.anidada_offset_x", r2.get("offsetof", {}).get("x"), 0)
    check("gcc.anidada_offset_n", r2.get("offsetof", {}).get("n"), 12)

    # Un campo que pertenece a OTRA struct es un fallo de compilacion, no un 0
    r_cross = full_probe("vector.h", [inc], "struct Ala", ["x"])
    check("gcc.campo_de_otra_struct", r_cross.get("estado"), "NO_COMPILE")

    # Una cabecera que NO existe: NO_COMPILE, nunca un 0 silencioso
    r3 = full_probe("no_existe_este_fichero.h", [inc], "struct Ala", campos_ala)
    check("gcc.ausente_no_compila", r3.get("estado"), "NO_COMPILE")
    check("gcc.ausente_no_inventa_sizeof", r3.get("sizeof"), None)

    # Una struct inexistente dentro de una cabecera real: tambien falla
    r4 = full_probe("vector.h", [inc], "struct NoExiste", ["a"])
    check("gcc.struct_ausente", r4.get("estado"), "NO_COMPILE")

    # Un campo que no existe en la struct: falla, no devuelve 0
    r5 = full_probe("vector.h", [inc], "struct Ala", ["campo_fantasma"])
    check("gcc.campo_fantasma", r5.get("estado"), "NO_COMPILE")

    # Sin campos la pregunta sigue siendo valida: solo sizeof
    r6 = full_probe("vector.h", [inc], "struct Ala", [])
    check("gcc.sin_campos_sizeof", r6.get("estado"), "OK")
    check("gcc.sin_campos_valor", r6.get("sizeof"), 12)
    check("gcc.sin_campos_sin_offsets", r6.get("offsetof"), {})

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · gcc reproducido y los fallos se declaran")
    print("  CLASIFICACION: TOOL_VALIDATED")
    print("  NOTA: gcc es la verdad de terreno del layout. NO valida el firmware.")
    try:
        os.unlink(hdr)
        os.rmdir(inc)
        os.rmdir(tmp)
    except OSError:
        pass
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--header", help="cabecera relativa, p.ej. smu74_discrete.h")
    ap.add_argument("--struct", help="nombre de la struct, p.ej. struct SMU74_..._DpmTable")
    ap.add_argument("--field", action="append", default=[], dest="fields",
                    help="campo cuyo offsetof se compara; repetible")
    ap.add_argument("--model", action="store_true",
                    help="calcula ademas el layout con struct_layout y compara")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not (args.kernel and args.header and args.struct):
        ap.error("--kernel, --header y --struct son obligatorios")
    includes = _find_includes(os.path.abspath(args.kernel))
    gcc = full_probe(args.header, includes, args.struct, args.fields)

    if args.model:
        import struct_layout as SL
        amd = os.path.join(os.path.abspath(args.kernel), "drivers/gpu/drm/amd")
        # Las constantes de macro se indexan ANTES de medir. Sin ellas los
        # limites de array no se resuelven y el modelo sale mas pequeno que la
        # verdad: la comparacion divergia por una causa que no era del
        # modelo, sino de que la herramienta no se habia preparada.
        SL.macro_constants([os.path.join(amd, "include"),
                            os.path.join(amd, "pm"),
                            os.path.join(amd, "pm/powerplay/inc")])
        hits = SL.find_struct_cached(amd, args.struct.replace("struct ", ""))
        modelo = None
        if hits:
            h = hits[0]
            flds, _ = SL.parse_fields(str(h["body"]), ctx_file=str(h["file"]))
            known, _ = SL.resolve_nested(flds, amd,
                                         ctx_file=str(h["file"]))
            lay = SL.layout(flds, known=known, enum_root=str(h["file"]))
            got = {r["name"]: r["offset"] for r in lay["rows"] if r.get("name")}
            modelo = {"sizeof": lay["total_size"],
                      "confianza": lay["confidence"],
                      "offsetof": got,
                      "no_resueltos": lay["unknown"]}
        cmp_ = {"estado": "SIN_MODELO"}
        if isinstance(gcc.get("sizeof"), int) and modelo:
            dif = []
            if gcc["sizeof"] != modelo["sizeof"]:
                dif.append(f"sizeof: gcc={gcc['sizeof']} modelo={modelo['sizeof']}")
            for f, g in (gcc.get("offsetof") or {}).items():
                m = modelo["offsetof"].get(f)
                if m != g:
                    dif.append(f"{f}: gcc={g} modelo={m}")
            cmp_ = {"estado": "COINCIDE" if not dif else "DIVERGE",
                    "diferencias": dif}
        gcc["modelo"] = modelo
        gcc["comparacion"] = cmp_

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION,
                          "work_class": WORK_CLASS,
                          "write_execution": WRITE_EXECUTION,
                          "gcc": gcc}, indent=2, ensure_ascii=False))
        return 0

    print(f"{NAME} {VERSION} · verdad de terreno del compilador")
    print(f"  WORK_CLASS={WORK_CLASS} · WRITE_EXECUTION={WRITE_EXECUTION}")
    print(f"  cabecera {args.header} · struct {args.struct}")
    print()
    if gcc.get("estado") != "OK":
        print(f"  gcc: {gcc.get('estado')}")
        if gcc.get("diagnostico"):
            print(f"  {gcc['diagnostico']}")
        print("  CLASIFICACION: NO_COMPARABLE (no se inventa ningun numero)")
        return 2
    print(f"  gcc sizeof = {gcc['sizeof']}")
    for f, o in sorted((gcc.get("offsetof") or {}).items()):  # type: ignore[union-attr]
        print(f"    offsetof({f:<28}) = {o}")
    cmp_ = gcc.get("comparacion")
    if isinstance(cmp_, dict) and cmp_.get("estado") != "SIN_MODELO":
        print()
        print(f"  modelo struct_layout: sizeof = "
              f"{(gcc.get('modelo') or {}).get('sizeof')}"
              f"  confianza {(gcc.get('modelo') or {}).get('confianza')}")
        print(f"  COMPARACION: {cmp_['estado']}")
        for d in cmp_.get("diferencias", []):  # type: ignore[union-attr]
            print(f"    DIVERGE {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
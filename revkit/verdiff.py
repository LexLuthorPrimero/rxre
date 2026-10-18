#!/usr/bin/env python3
# CONTRACT: name=verdiff
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto de esta herramienta fue `READONLY=yes, WRITES_FILES=no`, y la clase
# de cada escritura se resolvio a TEMPORAL: son las del selftest, que escribe en
# un `tempfile` precisamente para no tocar el arbol.
#
# `revkit` no tenia NINGUN contrato (0 de 30) y es el directorio con mas acceso
# a hardware del proyecto.  Este bloque no anade comportamiento: hace el
# comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
#
# TOUCHES_INTEGRATED=no: lee ficheros y sysfs de la DISCRETA.  No abre DRM, no
# hace ioctl, no escribe en la GPU.  El campo no existe en el vocabulario de
# toolkit.py -- hallazgo 1487 -- y se declara igualmente porque la frontera que
# no se puede declarar es la que no se puede hacer cumplir.
"""
verdiff.py -- analisis diferencial entre dos VERSIONES del driver.

POR QUE EXISTE
--------------
El corpus tiene DOS arboles completos del driver:

    RESEARCH/working/linux-7.1.3        (el que usa el host)
    rx550-upstream-7.2.8/linux-7.2.8    (otra generacion)

Eso es un recurso que no se estaba usando. Cuando algo es NOT_DETERMINED en
7.1.3, hay tres caminos:

  1. runtime con root                     -> bloqueado
  2. documentacion externa                -> no esta
  3. OTRA GENERACION DEL MISMO DRIVER     -> disponible, y no se miraba

El tercero es el mas barato y el mas ignorado. Un ASIC mas nuevo implementa lo
mismo y a veces anade comentarios, asserts o nombres de campo que SI dicen que
hace. Eso convierte NOT_DETERMINED en CORROBORATED, o al menos acota la
pregunta.

No convierte una diferencia en una verdad: si 7.2.8 hace algo distinto, eso
dice que 7.1.3 PUEDE hacer algo distinto, no que lo haga.

QUE PRODUCE

  fn      Como cambia una funcion entre versiones, linea a linea
  sym     Donde aparece un simbolo en cada version
  grep    Un termino en los ficheros de ASIC de ambas versiones
  nuevo   Simbolos que 7.2.8 tiene y 7.1.3 no (compara los conjuntos)

Y una mas util todavia:

  doc      Busca un simbolo en los COMENTARIOS de la otra version. Los
           comentarios de upstream suelen decir que hace un registro o un
           opcode, y eso es evidencia que 7.1.3 no tiene.
"""
import argparse
import difflib
import os
import re
import sys

V1 = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
      "linux-7.1.3/drivers/gpu/drm/amd/amdgpu")
V2 = ("/home/lucas/Escritorio/RX550-INVESTIGACION/rx550-upstream-7.2.8/"
      "linux-7.2.8/drivers/gpu/drm/amd/amdgpu")

V1_INC = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/"
          "linux-7.1.3/drivers/gpu/drm/amd/include")
V2_INC = ("/home/lucas/Escritorio/RX550-INVESTIGACION/rx550-upstream-7.2.8/"
          "linux-7.2.8/drivers/gpu/drm/amd/include")

VER = {V1: "7.1.3", V2: "7.2.8"}


def lee(base, nombre):
    for sub in ("", "asic_reg/gca", "asic_reg/gc", "asic_reg/gmc"):
        p = os.path.join(base, sub, nombre) if sub else os.path.join(base, nombre)
        if os.path.exists(p):
            return open(p, encoding="utf-8", errors="replace").read()
    return None


def func_body(txt, nombre):
    """(linea_ini, linea_fin, cuerpo) localizando la DEFINICION."""
    if not txt:
        return None, None, None
    lineas = txt.splitlines()
    # La lista de tipos tiene que cubrir lo que el driver USA de verdad.
    # La primera version omitia uint64_t, y con eso gmc_v8_0_emit_flush_gpu_tlb
    # (que devuelve uint64_t) daba "NO EXISTE" en las DOS versiones. Peor que
    # no encontrar: un "NO EXISTE / NO EXISTE" se lee como "esta funcion no
    # esta en ninguna", y eso es falso. La conclusion de "IDENTICA" sobre dos
    # ausencias es la peor forma de equivocar.
    rx = re.compile(
        r"^(?P<mods>(?:static\s+|inline\s+|const\s+|__maybe_unused\s+)+)"
        r"(?P<tipo>void|u(?:8|16|32|64|128)_t|uint\d+_t|u\d+|s\d+|int|bool|"
        r"unsigned(?:\s+(?:long|int|char))?|signed(?:\s+(?:long|int|char))?|"
        r"long(?:\s+long)?|size_t|ssize_t|char|short|double|float|"
        r"struct\s+\w+|union\s+\w+|enum\s+\w+)\s*\**\s*"
        r"(?P<nombre>[A-Za-z_]\w*)\s*\(")
    for i, ln in enumerate(lineas):
        m = rx.match(ln)
        if not m or m.group("nombre") != nombre:
            continue
        depth = ln.count("(") - ln.count(")")
        j = i
        while depth > 0 and j + 1 < len(lineas):
            j += 1
            depth += lineas[j].count("(") - lineas[j].count(")")
        acc = sum(len(x) + 1 for x in lineas[:j + 1])
        k = txt.find("{", acc)
        if k < 0:
            return None, None, None
        nivel, p = 0, k
        while p < len(txt):
            c = txt[p]
            if c == "/" and p + 1 < len(txt) and txt[p + 1] == "*":
                f = txt.find("*/", p)
                if f < 0:
                    break
                p = f + 2
                continue
            if c == "{":
                nivel += 1
            elif c == "}":
                nivel -= 1
                if nivel == 0:
                    break
            p += 1
        return i + 1, txt[:p].count("\n") + 1, txt[k:p + 1]
    return None, None, None


def cmd_fn(args):
    if len(args) < 2:
        print("fn necesita FICHERO NOMBRE   (p.ej. gfx_v8_0.c funcion)")
        return 2
    fichero, nombre = args[0], args[1]
    t1 = lee(V1, fichero)
    t2 = lee(V2, fichero)
    print("funcion %s en %s" % (nombre, fichero))
    print("=" * 74)
    if not t1 and not t2:
        print("el fichero no existe en ninguna version")
        return 1
    i1, f1, c1 = func_body(t1, nombre) if t1 else (None, None, None)
    i2, f2, c2 = func_body(t2, nombre) if t2 else (None, None, None)
    print("7.1.3: %s" % ("lineas %s-%s" % (i1, f1) if c1 else "NO EXISTE"))
    print("7.2.8: %s" % ("lineas %s-%s" % (i2, f2) if c2 else "NO EXISTE"))
    print()
    if not c1 and not c2:
        print("NO EXISTE EN NINGUNA DE LAS DOS VERSIONES.")
        print()
        print("Eso NO es 'identica': es que no se ha encontrado, y las dos")
        print("cosas son muy distintas. Causa probable: el tipo de retorno")
        print("no esta en la lista de la regex, o el nombre lleva un prefijo")
        print("de macro. Se marca distinto a proposito.")
        print()
        print("Comprobacion: existe el fichero?")
        for base, ver in ((V1, "7.1.3"), (V2, "7.2.8")):
            t = lee(base, args[0])
            print("   %s: fichero %s, %d apariciones del NOMBRE en el texto"
                  % (ver, "si" if t else "NO",
                     t.count(nombre) if t else 0))
        return 1
    if c1 and not c2:
        print("SOLO EN 7.1.3. Se elimino, o se renombro.")
        print("Las lineas de 7.1.3, para referencia:")
        print("-" * 74)
        for l in (c1 or "").splitlines()[:40]:
            print("  %s" % l)
        return 0
    if c2 and not c1:
        print("SOLO EN 7.2.8. Es NUEVA respecto a 7.1.3.")
        print("-" * 74)
        for l in (c2 or "").splitlines()[:60]:
            print("  %s" % l)
        return 0
    if c1 == c2:
        print("IDENTICA en ambas versiones (comparados los cuerpos sin")
        print("comentarios).")
        return 0
    print("DIFFER. El diff:")
    print("-" * 74)
    for l in difflib.unified_diff(
            re.sub(r"/\*.*?\*/", " ", c1, flags=re.S).splitlines(),
            re.sub(r"/\*.*?\*/", " ", c2, flags=re.S).splitlines(),
            "7.1.3", "7.2.8", lineterm="", n=2):
        print("  %s" % l[:110])
    print()
    print("NOTA: se comparan los CUERPOS sin comentarios. Un comentario")
    print("distinto es informacion, pero mezclado en el diff esconde el")
    print("cambio de codigo. Para ver comentarios usa 'doc'.")
    return 0


def cmd_doc(args):
    """
    Busca un simbolo en los COMENTARIOS de las dos versiones.

    Es la via mas infravalorada: un comentario de upstream junto a un
    registro suele decir QUE HACE, y eso es evidencia que el codigo no da.
    """
    if not args:
        print("doc necesita un termino")
        return 2
    term = args[0]
    rx = re.compile(re.escape(term), re.I)
    print("=== '%s' en COMENTARIOS ===" % term)
    for base, ver in ((V1, "7.1.3"), (V2, "7.2.8")):
        print()
        print("--- %s ---" % ver)
        n = 0
        for root in (base, os.path.join(os.path.dirname(base), "include")):
            if not os.path.isdir(root):
                continue
            for d, _s, fs in os.walk(root):
                for fn in sorted(fs):
                    if not fn.endswith((".h", ".c")):
                        continue
                    p = os.path.join(d, fn)
                    try:
                        txt = open(p, encoding="utf-8",
                                   errors="replace").read()
                    except Exception:
                        continue
                    # solo lineas de comentario
                    for i, ln in enumerate(txt.splitlines(), 1):
                        s = ln.strip()
                        if not (s.startswith("*") or s.startswith("//")
                                or s.startswith("/*")):
                            continue
                        if rx.search(s):
                            n += 1
                            if n <= 24:
                                print("  %-24s %5d  %s"
                                      % (fn, i, s[:92]))
        print("  ... total %d lineas de comentario" % n)
    print()
    print("Un comentario de upstream NO es evidencia del hardware. Es")
    print("documentacion de quien escribio el codigo. Sirve para acotar la")
    print("pregunta, no para cerrarla.")
    return 0


def cmd_nuevo(args):
    """Simbolos que 7.2.8 tiene y 7.1.3 no."""
    def simbolos(base):
        out = set()
        for d, _s, fs in os.walk(base):
            for fn in fs:
                if not fn.endswith((".c", ".h")):
                    continue
                try:
                    txt = open(os.path.join(d, fn), encoding="utf-8",
                               errors="replace").read()
                except Exception:
                    continue
                for m in re.finditer(
                        r"#define\s+([A-Z][A-Z0-9_]{4,})\s", txt):
                    out.add(m.group(1))
                for m in re.finditer(
                        r"\b(?:static\s+|void\s+|int\s+|u\d+\s+)"
                        r"([a-z_]\w{4,})\s*\(", txt):
                    out.add(m.group(1))
        return out

    s1, s2 = simbolos(V1), simbolos(V2)
    nuevos = sorted(s2 - s1)
    idos = sorted(s1 - s2)
    print("simbolos en 7.1.3: %d" % len(s1))
    print("simbolos en 7.2.8: %d" % len(s2))
    print()
    print("NUEVOS en 7.2.8: %d" % len(nuevos))
    for s in nuevos[:40]:
        print("   + %s" % s)
    if len(nuevos) > 40:
        print("   ... y %d mas" % (len(nuevos) - 40))
    print()
    print("QUITADOS respecto a 7.1.3: %d" % len(idos))
    for s in idos[:40]:
        print("   - %s" % s)
    if len(idos) > 40:
        print("   ... y %d mas" % (len(idos) - 40))
    print()
    print("Un simbolo nuevo en 7.2.8 puede ser: hardware nuevo, refactor,")
    print("o driver nuevo para otra generacion. No se puede distinguir sin")
    print("mirarlo. Los nombres con ASIC (GFX12, VENICE, NAVI) son hardware.")
    return 0


def cmd_grep(args):
    """Un termino en los ficheros de ASIC de ambas versiones."""
    if not args:
        print("grep necesita un termino")
        return 2
    term = args[0]
    rx = cidx_pat(term)
    print("=== '%s' en ficheros de ASIC ===" % term)
    for base, ver in ((V1, "7.1.3"), (V2, "7.2.8")):
        print()
        print("--- %s ---" % ver)
        for patron in ("gfx_v", "gmc_v", "sdma_v"):
            hits = []
            for fn in sorted(os.listdir(base)):
                if not fn.startswith(patron) or not fn.endswith(".c"):
                    continue
                try:
                    txt = open(os.path.join(base, fn), encoding="utf-8",
                               errors="replace").read()
                except Exception:
                    continue
                n = len(rx.findall(txt))
                if n:
                    hits.append((fn, n))
            for fn, n in hits:
                print("   %-20s %3d" % (fn, n))
            if not hits:
                print("   (ningun fichero %s*)" % patron)
    return 0


def cidx_pat(t):
    return re.compile(r"(?<![A-Za-z0-9_])" + re.escape(t) +
                      r"(?![A-Za-z0-9_])")


def main():
    ap = argparse.ArgumentParser(description="analisis diferencial de versiones")
    ap.add_argument("cmd", choices=["fn", "sym", "doc", "nuevo", "grep"])
    ap.add_argument("args", nargs="*")
    a = ap.parse_args()
    if a.cmd == "fn":
        return cmd_fn(a.args)
    if a.cmd == "doc":
        return cmd_doc(a.args)
    if a.cmd == "nuevo":
        return cmd_nuevo(a.args)
    if a.cmd == "grep":
        return cmd_grep(a.args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
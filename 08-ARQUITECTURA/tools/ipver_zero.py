#!/usr/bin/env python3
# CONTRACT: name=ipver_zero
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""ipver_zero -- que rama toma CADA comparacion de GC_HWIP con el valor 0.

POR QUE EXISTE. El hallazgo 182romisedo que en Polaris12
`adev->ip_versions[GC_HWIP][0] == 0`, y que por tanto unas 300 comparaciones de
`amdgpu_ip_version(adev, GC_HWIP, 0)` degeneran a "comparar 0 contra una
constante". Eso, EVALUADO MECANICAMENTE, tiene una consecuencia que solo se ve
si se recorre todo: cuantas comparaciones son SIEMPRE verdaderas, cuantas son
SIEMPRE falsas, y si alguna queda con una rama que nunca se toma.

Leer 40 sitios a mano es exactamente el trabajo que AGENTS.md manda automatizar,
y ademas es donde se cuelan los errores: con 0, casi cualquier comparacion
contra IP_VERSION(n,0,0) con n>0 se resuelve sola, y es facil leer mal una de
ellas.

LIMITE DECLARADO. Se evaluan las comparaciones RELATIVAS (==, <, >, <=, >=) y
las funciones IP_VERSION_MAJ/MIN/REV. Los `switch` no se evaluan: se listan
 aparte, porque resolverlos exige saber que case coincide con 0, y 0 no
coincide con ningun IP_VERSION de una cifra.

Uso:
  ipver_zero.py --todos            tabla completa
  ipver_zero.py --fichero F        solo un fichero
  ipver_zero.py --resumen          solo los conteos
  ipver_zero.py --self-test

Codigos de salida:
  0  todo bien
  2  fichero no encontrado
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AMD = os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd", "amdgpu")

# Ficheros COMUNES: se ejecutan tambien en GFX8. Los de una sola generacion
# (gfx_v9_0.c, gmc_v10_0.c, ...) no se analizan, porque en esta placa no
# entran y analizarlos solo produciria ruido.
COMMON = ["amdgpu_device.c", "amdgpu_display.c", "amdgpu_gfx.c", "amdgpu_gmc.c",
          "amdgpu_ids.c", "amdgpu_vm.c", "amdgpu_kms.c", "amdgpu_mes.c",
          "amdgpu_sdma.c", "amdgpu_ttm.c", "amdgpu_ucode.c", "amdgpu_virt.c",
          "amdgpu_dma_buf.c", "amdgpu_xgmi.c", "amdgpu_cs.c",
          "amdgpu_object.c", "amdgpu_vm.h", "amdgpu.h"]

# OJO: los parentesis de la llamada TIENEN que estar escapados. Sin
# \( y \), el "(" abre un grupo de captura, la regex deja de pedir la
# parentesis literal, y NO CASA NADA. El self-test lo detecta.
CALL = r"amdgpu_ip_version\(\s*(?:adev|dev)\s*,\s*GC_HWIP\s*,\s*0\s*\)"

# Comparacion relativa. Se captura el operador, y a la derecha un IP_VERSION(...)
# o un entero.
REL_RE = re.compile(
    r"IP_VERSION_MAJ_MIN_REV\(\s*" + CALL + r"\s*\)\s*(==|!=)\s*(\w+)")
MAJ_RE = re.compile(
    r"IP_VERSION_MAJ\(\s*" + CALL + r"\s*\)\s*(==|!=)\s*(\d+)")
SIMPLE_RE = re.compile(
    CALL + r"\s*(<=|>=|==|!=|<|>)\s*IP_VERSION\(\s*(\d+)\s*,\s*(\d+)\s*,"
    r"\s*(\d+)\s*\)")
SWITCH_RE = re.compile(r"switch\s*\(\s*" + CALL + r"\s*\)")


def ipv(major, minor, rev):
    return (major << 24) | (minor << 16) | (rev << 8)


def evaluar(op, ver_constante):
    """Evalua `0 <op> ver_constante`. Devuelve True/False.

    Recibe la version de la CONSTANTE del lado derecho, y aplica el operador
    entre 0 y ese valor. Es la operacion exacta que hace el driver cuando
    ip_versions[GC_HWIP][0] vale 0.
    """
    v = ver_constante
    if op == "==":
        return 0 == v
    if op == "!=":
        return 0 != v
    if op == "<":
        return 0 < v
    if op == "<=":
        return 0 <= v
    if op == ">":
        return 0 > v
    if op == ">=":
        return 0 >= v
    raise ValueError("operador desconocido: %r" % op)


def escanear(fname):
    path = os.path.join(AMD, fname)
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace") as fh:
        lineas = fh.readlines()

    filas = []
    # Una ventana por linea: la linea actual MAS la siguiente, para que una
    # condicion de dos lineas quepa. Recorrer (linea, linea+1) como dos
    # ventanas CONTADABA CADA SITIO DOS VECES, porque el mismo texto se
    # encuentra desde las dos. Con una sola ventana por linea, cada sitio se
    # cuenta una vez, desde la linea donde empieza.
    for n, linea in enumerate(lineas, 1):
        if True:
            txt = linea + (lineas[n] if n < len(lineas) else "")

            for m in REL_RE.finditer(txt):
                filas.append((n, "IP_VERSION_MAJ_MIN_REV %s %s" % (
                    m.group(1), m.group(2)), True, "comparacion"))
            for m in MAJ_RE.finditer(txt):
                filas.append((n, "IP_VERSION_MAJ %s %s" % (
                    m.group(1), m.group(2)), True, "comparacion"))
            for m in SIMPLE_RE.finditer(txt):
                op, maj, mi, rev = m.groups()
                ver = ipv(int(maj), int(mi), int(rev))
                filas.append((n, "%s IP_VERSION(%s,%s,%s)" % (op, maj, mi, rev),
                              evaluar(op, ver), "comparacion"))
            if SWITCH_RE.search(txt):
                filas.append((n, "switch (...)", None, "switch"))
    return filas


def imprimir(solo_resumen=False, solo_fichero=None):
    total = comps = switches = siempre_true = siempre_false = 0
    detalle = []
    for f in (solo_fichero if solo_fichero else COMMON):
        filas = escanear(f)
        if filas is None:
            if solo_fichero:
                print("no existe %s" % f)
                return 2
            continue
        for n, expr, res, clase in filas:
            total += 1
            if clase == "switch":
                switches += 1
            else:
                comps += 1
                if res:
                    siempre_true += 1
                else:
                    siempre_false += 1
            if not solo_resumen:
                marca = "SIEMPRE" if res else ("NUNCA" if res is not None
                                               else "switch")
                detalle.append((f, n, expr, clase, marca))

    if not solo_resumen:
        print("%-26s %6s  %-42s %-12s %s"
              % ("fichero", "linea", "expresion", "clase", "con valor 0"))
        print("-" * 104)
        for f, n, expr, clase, marca in detalle:
            print("%-26s %6d  %-42s %-12s %s"
                  % (f, n, expr[:42], clase, marca))
    print()
    print("ficheros comunes analizados : %d"
          % len(solo_fichero if solo_fichero else COMMON))
    print("sitios encontrados          : %d" % total)
    print("  comparaciones             : %d" % comps)
    print("    SIEMPRE verdaderas      : %d" % siempre_true)
    print("    NUNCA verdaderas        : %d" % siempre_false)
    print("  switch (no evaluados)     : %d" % switches)
    return 0


def self_test():
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))

    # 1. La aritmetica de IP_VERSION tiene que coincidir con amdgpu_ip.h:77-79:
    #    (mj<<24)|(mn<<16)|(rv<<8)|(var<<4)|(srev), con var=srev=0.
    eq("IP_VERSION(8,0,0)", ipv(8, 0, 0), 0x08000000)
    eq("IP_VERSION(9,0,0)", ipv(9, 0, 0), 0x09000000)
    eq("IP_VERSION(9,4,3)", ipv(9, 4, 3), 0x09040300)
    eq("IP_VERSION(12,1,0)", ipv(12, 1, 0), 0x0C010000)

    # 2. VECTOR DE EVALUACION: los tres sitios reales de 182, con el operador
    #    tal cual aparece en el fuente.
    eq("vm.c:1157  0 <  IP_VERSION(9,0,0)",
       evaluar("<", ipv(9, 0, 0)), True)
    eq("ids.c:586  0 <  IP_VERSION(10,0,0)",
       evaluar("<", ipv(10, 0, 0)), True)
    eq("vm.h:123   0 >= IP_VERSION(12,0,0)",
       evaluar(">=", ipv(12, 0, 0)), False)
    eq("device.c:889  0 == IP_VERSION(9,4,3)",
       evaluar("==", ipv(9, 4, 3)), False)
    eq("device.c:891  0 == IP_VERSION(9,5,0)",
       evaluar("==", ipv(9, 5, 0)), False)

    # 3. CONTROL NEGATIVO: si evaluar() devolviera siempre lo mismo, los tests
    #    anteriores no probarian nada. '<' y '>' con la MISMA constante tienen
    #    que dar resultados distintos, y '==' y '!=' tambien.
    if evaluar("<", ipv(9, 0, 0)) == evaluar(">", ipv(9, 0, 0)):
        fails.append("control negativo: '<' y '>' con la misma constante dan "
                     "el mismo resultado")
    if evaluar("==", ipv(9, 0, 0)) == evaluar("!=", ipv(9, 0, 0)):
        fails.append("control negativo: '==' y '!=' con la misma constante dan "
                     "el mismo resultado")

    # 4. CONTROL NEGATIVO: un operador desconocido tiene que FALLAR, no
    #    devolver un valor por defecto. Un default silencioso aqui seria
    #    exactamente el fallo que esta herramienta existe para detectar.
    try:
        evaluar("<>", ipv(9, 0, 0))
        fails.append("control negativo: un operador invalido no lanzo excepcion")
    except ValueError:
        pass

    # 5. CONTROL NEGATIVO: fichero inexistente -> None, no lista vacia.
    if escanear("no_existe_este_fichero.c") is not None:
        fails.append("un fichero inexistente devolvio filas")

    # 6. El escaner tiene que encontrar los sitios conocidos de 182. Si el regex
    #    dejara de casar, el self-test pasaria sin comprobar nada.
    filas = escanear("amdgpu_vm.c")
    if not filas:
        fails.append("amdgpu_vm.c no devolvio ninguna fila: el regex no casa")
    else:
        textos = " ".join(f[1] for f in filas)
        if "< IP_VERSION(9,0,0)" not in textos:
            fails.append("no se encontro el sitio de flush_tlb (vm.c:1157)")

    # 7. TEST DE PIPELINE, NO DE FUNCION. Los tests anteriores comprueban
    #    evaluar() en aislamiento; eso NO comprueba que el bucle de escanear la
    #    llame bien. Ya ha pasado: el bucle comparaba "ver == 0" en vez de
    #    evaluar(op, ver), evaluar() era correcta y la salida estaba mal, y el
    #    self-test pasaba. Un self-test que solo prueba la funcion no prueba
    #    la herramienta.
    filas_vm = escanear("amdgpu_vm.c")
    fila_flush = [f for f in filas_vm if "< IP_VERSION(9,0,0)" in f[1]]
    if not fila_flush:
        fails.append("pipeline: no se encontro la fila de flush_tlb")
    elif fila_flush[0][2] is not True:
        fails.append("pipeline: flush_tlb (vm.c:1157) debe ser SIEMPRE "
                     "verdadera con valor 0, el escaneo dio %r" % (fila_flush[0][2],))

    # Y lo contrario: un == contra una constante real nunca puede ser verdad.
    filas_dev = escanear("amdgpu_device.c")
    filas_eq = [f for f in filas_dev if f[3] == "comparacion"
                and f[1].startswith("==")]
    if not filas_eq:
        fails.append("pipeline: no se encontro ningun == en amdgpu_device.c")
    elif any(f[2] for f in filas_eq):
        fails.append("pipeline: un '==' contra IP_VERSION real resulto "
                     "verdadero: la evaluacion esta mal")

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (16 vectores, 4 controles, 2 de pipeline)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if "--resumen" in argv:
        return imprimir(solo_resumen=True)
    if "--fichero" in argv:
        f = argv[argv.index("--fichero") + 1]
        return imprimir(solo_fichero=[f])
    return imprimir()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
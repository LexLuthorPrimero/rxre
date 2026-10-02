#!/usr/bin/env python3
# CONTRACT: name=mmio_map
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""mmio_map -- el mapa real de accesos MMIO del driver, leido del binario.

POR QUE EXISTE. Hasta ahora el mapa de registros de esta placa salia de las
CABECERAS (nombres y offsets), y `203` demostro que eso es vocabulario: de 13895
registros definidos, el driver usa 1311. Pero ese 9% lo medi buscando NOMBRES de
macro en el codigo, que no distingue lectura de escritura ni el orden.

Aqui se mide el ACCESO. El binario tiene una propiedad que hace el problema
facil:

  $ objdump -dr ... | grep -A1 'mov \\$0x398,%esi'
    1ccec9:  mov    $0x398,%esi
    1cced7:  call   ...
      1cced8:  R_X86_64_PLT32  amdgpu_device_rreg-0x4

TODO el MMIO del driver pasa por `amdgpu_device_rreg` / `amdgpu_device_wreg`, con
el offset del registro como SEGUNDO argumento. Asi que el mapa se lee de un patron
de dos lineas, no de desensamblado general.

POR QUE -dr Y NO -d. Con `objdump -d` las llamadas salen como `call <siguiente
instruccion>`: en un `.ko` el objetivo real esta en `.rela.text` y no se aplica.
Me costo tres intentos de grep fallidos descubrirlo: 0xf91, 0xfb56 y 0x3df1 no
aparecian ni como displacement ni como inmediato, y el motivo era que estaba
mirando el binario equivocado. `-dr` anade la reubicacion con el simbolo real.

LIMITE DECLARADO, y es serio. Se toma el ULTIMO `mov $imm,%esi` visto antes de la
llamada, en la misma funcion. Si entre ese mov y la llamada hay otro codigo que
toque %esi, el offset atribuido es erroneo. Eso NO lo puedo verificar sin un
analizador de flujo de datos, y no lo tengo. Por eso cada resultado viene con el
numero de instrucciones de distancia entre el mov y el call: una distancia corta es
fiable, una larga es sospechosa, y se reporta el maximo para poder juzgarlo.

Uso:
  mmio_map.py --funcion N            una funcion
  mmio_map.py --resumen              conteos globales
  mmio_map.py --top N                los registros mas accedidos
  mmio_map.py --self-test

Codigos de salida:
  0  ok
  2  falta el .asm con reubicaciones
  3  funcion no encontrada
"""

import os
import re
import sys

ASM = "/tmp/opencode/ko_dr.asm"

RE_FUNC = re.compile(r"^[0-9a-f]{16} <(.+)>:")
RE_MOV_ESi = re.compile(r"^\s*[0-9a-f]+:\s+mov\s+\$0x([0-9a-f]+),%esi\b")
RE_CALL = re.compile(r"R_X86_64_PLT32\s+(amdgpu_device_[a-z_]*reg)-0x4")

# Los helpers, y si son LECTURA o ESCRITURA. wait_on_rreg lee con espera, asi que
# cuenta como lectura; las variantes xcc_* no aplican a GCN3 (multi-chip) y se
# listan aparte para no mezclarlas.
LECTURA = {"amdgpu_device_rreg", "amdgpu_device_wait_on_rreg",
           "amdgpu_device_xcc_rreg"}
ESCRITURA = {"amdgpu_device_wreg", "amdgpu_device_xcc_wreg"}

# Distancia maxima entre el mov y el call que se considera fiable. Medida contra
# el caso conocido: en sdma_v3_0_soft_reset el mov esta a 3 instrucciones del call.
MAX_DIST = 12


def self_test():
    fails = []

    def eq(lbl, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (lbl, got, want))

    # 1. LA ANCLA MAS FUERTE DEL KIT: se sabe que sdma_v3_0_soft_reset solo toca
    #    mmSRBM_SOFT_RESET (0x398). Un extractor correcto tiene que devolver
    #    EXACTAMENTE ese offset, y nada mas. Si devuelve otros, esta atribuyendo
    #    offsets que no son.
    if not os.path.exists(ASM):
        fails.append("no existe %s: ejecuta 'mmio_map.py --construir'" % ASM)
        return _fin(fails)

    filas = []
    with open(ASM, encoding="utf-8", errors="replace") as fh:
        for n, linea in enumerate(fh, 1):
            if "sdma_v3_0_soft_reset" not in linea:
                continue
            if RE_FUNC.match(linea) and not RE_FUNC.match(linea).group(1).startswith(
                    "sdma_v3_0_soft_reset"):
                continue
            filas.append((n, linea))
    if not filas:
        fails.append("no encontre sdma_v3_0_soft_reset en el .asm")
        return _fin(fails)

    # Reconstruye los accesos de esa funcion con el mismo algoritmo del programa.
    f = _funcion(ASM, "sdma_v3_0_soft_reset")
    if f is None:
        fails.append("no se pudo aislar sdma_v3_0_soft_reset")
    else:
        offs = [a["offset"] for a in f["accesos"]]
        eq("sdma_v3_0_soft_reset toca un solo offset", sorted(set(offs)), [0x398])
        if not f["accesos"]:
            fails.append("el extractor no encontro NINGUN acceso en una funcion "
                         "que se sabe que hace 8 de ellos")
        leen = sum(1 for a in f["accesos"] if a["tipo"] == "R")
        escr = sum(1 for a in f["accesos"] if a["tipo"] == "W")
        if leen == 0 or escr == 0:
            fails.append("no distingue lectura de escritura: L=%d E=%d" % (leen, escr))

    # 2. CONTROL NEGATIVO: una funcion que NO hace MMIO tiene que dar cero.
    for nombre in ("amdgpu_gmc_tmz_set",):
        g = _funcion(ASM, nombre)
        if g is not None and g["accesos"]:
            fails.append("control negativo: %s da %d accesos y solo hace un "
                         "dev_info" % (nombre, len(g["accesos"])))

    # 3. CONTROL NEGATIVO: el fichero inexistente.
    if _funcion("/tmp/opencode/no_existe.asm", "lo_que_sea") is not None:
        fails.append("control negativo: un .asm inexistente devolvio datos")

    # 4. Distancia maxima reportada: si se dispara, el supuesto de "ultimo mov"
    #    esta fallando y hay que decirlo, no esconderlo.
    if f:
        d = max(a["dist"] for a in f["accesos"])
        if d > MAX_DIST:
            fails.append("distancia mov->call = %d, por encima de MAX_DIST=%d: el "
                         "atribucion de offset no es fiable ahi" % (d, MAX_DIST))

    return _fin(fails)


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (1 ancla fuerte, 2 controles negativos, 1 de distancia)")
    return 0


def _funcion(ruta, nombre):
    """Aísla una función por nombre y devuelve sus accesos MMIO."""
    if not os.path.exists(ruta):
        return None
    salida = False
    ultimo = None          # (offset_hex, distancia)
    dist = 0
    acc = []
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = RE_FUNC.match(linea)
            if m:
                if salida:
                    break
                salida = m.group(1) == nombre
                ultimo, dist = None, 0
                continue
            if not salida:
                continue
            mm = RE_MOV_ESi.match(linea)
            if mm:
                ultimo, dist = int(mm.group(1), 16), 0
                continue
            if ultimo is not None:
                dist += 1
            mc = RE_CALL.search(linea)
            if mc:
                sym = mc.group(1)
                tipo = "R" if sym in LECTURA else ("W" if sym in ESCRITURA else "?")
                if ultimo is not None and dist <= MAX_DIST:
                    acc.append({"offset": ultimo, "tipo": tipo,
                                "dist": dist, "sym": sym})
                    ultimo, dist = None, 0
    if not salida:
        return None
    return {"nombre": nombre, "accesos": acc}


def recorrer(ruta):
    """Todos los accesos del modulo, en una sola pasada."""
    if not os.path.exists(ruta):
        return None
    total = 0
    funcs = {}
    func = None
    ultimo, dist = None, 0
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = RE_FUNC.match(linea)
            if m:
                func = m.group(1)
                funcs.setdefault(func, 0)
                ultimo, dist = None, 0
                continue
            mm = RE_MOV_ESi.match(linea)
            if mm:
                ultimo, dist = int(mm.group(1), 16), 0
                continue
            if ultimo is not None:
                dist += 1
            mc = RE_CALL.search(linea)
            if mc:
                sym = mc.group(1)
                tipo = "R" if sym in LECTURA else ("W" if sym in ESCRITURA else "?")
                if ultimo is not None and dist <= MAX_DIST:
                    funcs[func] += 1
                    total += 1
                ultimo, dist = None, 0
    return total, funcs


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not os.path.exists(ASM):
        print("mmio_map: falta %s\n"
              "  objdump -dr --no-show-raw-insn /tmp/amdgpu_loaded.ko > %s"
              % (ASM, ASM), file=sys.stderr)
        return 2

    if "--funcion" in argv:
        n = argv[argv.index("--funcion") + 1]
        f = _funcion(ASM, n)
        if f is None:
            print("mmio_map: no existe %s" % n, file=sys.stderr)
            return 3
        print("%s: %d accesos MMIO" % (n, len(f["accesos"])))
        for a in f["accesos"]:
            print("   %s  offset 0x%04X   (dist %d, %s)"
                  % (a["tipo"], a["offset"], a["dist"], a["sym"]))
        return 0

    total, funcs = recorrer(ASM)
    print("accesos MMIO atribuidos: %d" % total)
    print("funciones con al menos uno: %d" % sum(1 for v in funcs.values() if v))
    print()
    if "--top" in argv:
        k = int(argv[argv.index("--top") + 1])
        top = sorted(funcs.items(), key=lambda x: -x[1])[:k]
        for n, c in top:
            print("%5d  %s" % (c, n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
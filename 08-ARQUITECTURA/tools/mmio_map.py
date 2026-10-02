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
RE_LEA_ESi = re.compile(r"^\s*[0-9a-f]+:\s+lea\s+0x([0-9a-f]+)\(%[a-z0-9]+\),%esi\b")
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

    # 5. EL AVISO DE AMBIGUEDAD TIENE QUE EXISTIR Y SER SIMETRICO. Esta es la
    #    razon de ser del arreglo de 247: 397 nombres estan definidos mas de una
    #    vez, y sin el aviso la herramienta cuenta una de varias y SUBAESTIMA EN
    #    SILENCIO. Un underestimate que no dice nada es peor que uno que falla.
    #
    #    Y el control es simetrico a proposito: si marcara TODO, seria un muro
    #    del otro lado, tan inútil como no marcar nada.
    amb = _funcion(ASM, "kgd_hqd_sdma_load")          # medido: 4 definiciones
    if amb is None:
        fails.append("ambiguedad: no encuentro kgd_hqd_sdma_load")
    else:
        if not amb["ambigua"]:
            fails.append("ambiguedad: kgd_hqd_sdma_load tiene 4 definiciones y la "
                         "herramienta NO lo avisa: vuelve a subestimar en silencio")
        eq("kgd_hqd_sdma_load: numero de definiciones", len(amb["definiciones"]), 4)
        if amb["accesos"]:
            fails.append("ambiguedad: devolvio %d accesos tomando solo la primera "
                         "definicion; el numero es de una de varias y no debe "
                         "presentarse como medida" % len(amb["accesos"]))
        if len(amb["por_definicion"]) != 4:
            fails.append("ambiguedad: esperaba un desglose de 4 definiciones, "
                         "llegaron %d" % len(amb["por_definicion"]))
        if sum(c for _a, c in amb["por_definicion"]) == 0:
            fails.append("ambiguedad: el desglose suma 0 accesos en las 4 "
                         "definiciones, que es FALSO: kgd_hqd_sdma_load escribe "
                         "el descriptor SDMA en bucle")

    unica = _funcion(ASM, "gfx_v8_0_hw_init")          # medido: 1 definicion
    if unica is None:
        fails.append("ambiguedad: no encuentro gfx_v8_0_hw_init")
    elif unica["ambigua"]:
        fails.append("control negativo: gfx_v8_0_hw_init tiene UNA definicion y la "
                     "herramienta la marca ambigua: el aviso seria un muro")

    return _fin(fails)


def _fin(fails):
    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (1 ancla fuerte, 2 controles negativos, 1 de distancia, "
          "1 de ambiguedad con control simetrico)")
    return 0


_DEFS = {}


def definiciones(ruta):
    """nombre -> [direcciones], para saber cuantas veces se DEFINIO un nombre.

    En C una funcion `static` en dos ficheros puede llamarse igual en ambos, y el
    ELF repite el simbolo. Medido: 397 nombres de 33732 tienen mas de una
    definicion. Buscar por nombre sin decirlo cuenta UNA de varias, y el error
    va en la direccion silenciosa: SUBAESTIMA.
    """
    if ruta in _DEFS:
        return _DEFS[ruta]
    d = {}
    if os.path.exists(ruta):
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for linea in fh:
                m = RE_FUNC.match(linea)
                if m:
                    d.setdefault(m.group(1), []).append(linea.split()[0])
    _DEFS[ruta] = d
    return d


def _funcion(ruta, nombre):
    """Accesos MMIO de una función identificada POR NOMBRE.

    Si el nombre esta definido mas de una vez -- 397 casos, porque un `static` en
    dos ficheros repite el simbolo en el ELF -- NO devuelve un numero unico.
    Devuelve el desglose por definicion y deja `accesos` vacio a proposito, para
    que ningun llamante pueda presentar uno de ellos como la medida sin haber
    visto el aviso. Sin esto, la herramienta SUBESTIMA EN SILENCIO.
    """
    if not os.path.exists(ruta):
        return None
    defs = definiciones(ruta).get(nombre, [])
    if not defs:
        return None
    if len(defs) == 1:
        r = _una(ruta, nombre, defs[0])
        acc = r["accesos"] if r else []
        return {"nombre": nombre, "accesos": acc, "definiciones": defs,
                "ambigua": False, "por_definicion": [(defs[0], len(acc))]}
    por = []
    for a in defs:
        r = _una(ruta, nombre, a)
        por.append((a, len(r["accesos"]) if r else 0))
    return {"nombre": nombre, "accesos": [], "definiciones": defs,
            "ambigua": True, "por_definicion": por}


def _una(ruta, nombre, addr):
    """Aísla UNA definición concreta (por dirección) y devuelve sus accesos."""
    if not os.path.exists(ruta):
        return None
    salida = False
    ultimo = None
    dist = 0
    bucle = False
    acc = []
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = RE_FUNC.match(linea)
            if m:
                if salida:
                    break
                salida = linea.split()[0] == addr
                ultimo, dist, bucle = None, 0, False
                continue
            if not salida:
                continue
            mm = RE_MOV_ESi.match(linea)
            if mm:
                ultimo, dist = int(mm.group(1), 16), 0
                bucle = False
                continue
            ml = RE_LEA_ESi.match(linea)
            if ml:
                ultimo, dist = int(ml.group(1), 16), 0
                bucle = True
                continue
            if ultimo is not None:
                dist += 1
            mc = RE_CALL.search(linea)
            if mc:
                sym = mc.group(1)
                tipo = "R" if sym in LECTURA else ("W" if sym in ESCRITURA else "?")
                if ultimo is not None and dist <= MAX_DIST:
                    acc.append({"offset": ultimo, "tipo": tipo, "dist": dist,
                                "sym": sym, "bucle": bucle})
                ultimo, dist, bucle = None, 0, False
    if not salida:
        return None
    return {"nombre": nombre, "addr": addr, "accesos": acc}


def recorrer(ruta):
    """Todos los accesos del modulo, en una sola pasada."""
    if not os.path.exists(ruta):
        return None
    total = 0
    funcs = {}
    bucles = {}
    func = None
    ultimo, dist = None, 0
    bucle = False
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        for linea in fh:
            m = RE_FUNC.match(linea)
            if m:
                func = m.group(1)
                funcs.setdefault(func, 0)
                ultimo, dist, bucle = None, 0, False
                continue
            mm = RE_MOV_ESi.match(linea)
            if mm:
                ultimo, dist = int(mm.group(1), 16), 0
                continue
            ml = RE_LEA_ESi.match(linea)
            if ml:
                ultimo, dist = int(ml.group(1), 16), 0
                bucle = True
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
                    if bucle:
                        bucles[func] = bucles.get(func, 0) + 1
                ultimo, dist, bucle = None, 0, False
    return total, funcs, bucles


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
        if f["ambigua"]:
            # NO SE IMPRIME UN TOTAL. Imprimir "0 accesos" seria peor que
            # imprimir 11: 0 es una AFIRMACION (esta funcion no toca MMIO) y es
            # falsa. Aqui no se sabe, y no se saber no es cero. Por eso la
            # ausencia de total es la salida correcta, no un fallo de la
            # herramienta.
            print("%s: NOMBRE AMBIGUO, %d definiciones, SIN TOTAL"
                  % (n, len(f["definiciones"])))
            print("  accesos por definicion:")
            for a, c in f["por_definicion"]:
                print("        %s   %4d accesos" % (a, c))
            print("  El `.ko` no guarda que fichero salio cada simbolo, asi que no se")
            print("  puede saber cual de estas corre en esta placa. Es un `static`")
            print("  repetido (v6/v7/v8/v10). NO se puede dar un total sin inventarlo.")
            return 0
        print("%s: %d accesos MMIO" % (n, len(f["accesos"])))
        for a in f["accesos"]:
            print("   %s  offset 0x%04X   (dist %d, %s%s)"
                  % (a["tipo"], a["offset"], a["dist"], a["sym"],
                     ", BUCLE" if a.get("bucle") else ""))
        return 0

    total, funcs, bucles = recorrer(ASM)
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
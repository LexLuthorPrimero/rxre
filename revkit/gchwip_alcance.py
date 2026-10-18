#!/usr/bin/env python3
# CONTRACT: name=gchwip_alcance
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=indeterminado
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, y el veredicto fue `NO_DETERMINED`.
# NO se upgraded a `WRITES_FILES=yes` porque no esta medido, y NO se dejo en
# `no` porque el codigo no lo sostiene.  La razon del NO_DETERMINED es que lanza subprocess para alcanzar el ioctl, que es justamente lo que busca.
#
# Poner `yes` seria MENTIR en un sentido que el validador no puede detectar, que
# es lo que el propio toolkit.py escribe de sus cinco falsos positivos: "un
# contrato en prosa no se puede comprobar con una maquina".  Poner `no` seria
# Peor: seria una afirmacion que nadie ha comprobado.
#
# TOUCHES_INTEGRATED=no: lee sysfs y ficheros.  No hace ioctl ni escribe en la
# GPU.  Ver 1487.
# -*- coding: utf-8 -*-
"""gchwip_alcance.py -- de las comparaciones degeneradas de GC_HWIP, cuales hay
en codigo que esta placa NO ejecuta.

Por que existe. EV-39 dejo medido un hueco con nombre: `ipver_zero.py` clasifica
la EXPRESION de cada comparacion (SIEMPRE / NUNCA con el valor 0), pero no dice
si el codigo que la contiene llega a ejecutarse en Polaris12. Son dos preguntas
distintas, y la segunda es la que decide si una comparacion gobierna el
comportamiento real.

Lo que anade, y es lo que la otra herramienta no mide:

  1. El conjunto VIVO. Resultado de EV-39, verificado por `gfx8blocks.py`: en
     `amdgpu_device.c`, `vi_set_ip_blocks()` (ruta por FAMILIA) y
     `amdgpu_discovery_set_ip_blocks()` (ruta por VERSION) son MUTUAMENTE
     EXCLUSIVAS. Polaris12 entra en el `case` y no llega al `default`, con lo que
     **ninguna funcion de `amdgpu_discovery_set_*` se ejecuta**, y no se
     instancia ningun bloque de hardware de 9.x/10.x/11.x/12.x.
  2. Indice de llamadores CRUZANDO ficheros. MEDIDO, y era el defecto de fondo de
     la primera version: buscaba las llamadas dentro del mismo fichero, con lo
     que `amdgpu_mes_init_microcode` (llamado desde `mes_v11_0.c`) salia como
     "no llamada" -> no se descartaba nada. Un grafo de llamadas que no sale del
     fichero no es un grafo de llamadas.
  3. Para cada sitio, su funcion, y si esa funcion tiene algun llamador en un
     fichero vivo.

LIMITE DECLARADO, y es la diferencia entre esto y una prueba: es un **filtro de
una sola direccion**. Puede PROBAR que un sitio es inalcanzable. NO puede
probar que otro es alcanzable: el indice por `grep` no ve punteros a funcion, y
el driver los usa en las tablas `*_ip_funcs`. Por eso la columna dice
`NO ALCANZABLE` y no `MUERTO`: `NOT_FOUND` no es `PROVEN_ABSENT`.

CONTRACT: name=gchwip_alcance
CONTRACT: READONLY=yes
CONTRACT: WRITES_FILES=no
CONTRACT: WRITES_SYSFS=no
CONTRACT: MUTATES_CORPUS=no
CONTRACT: WRITES_GPU=no
"""

import io
import os
import re
import subprocess
import sys

REPO = "/home/lucas/Escritorio/RX550-INVESTIGACION"
AMDR = os.path.join(REPO, "RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu")
IPVER = os.path.join(REPO, "08-ARQUITECTURA/tools/ipver_zero.py")

# Ficheros que SI se ejecutan en Polaris12. Los ocho bloques incondicionales que
# devuelve `gfx8blocks.py`, mas los ficheros "comunes" que `ipver_zero.py` ya
# declaro comunes. Este es el unico dato que se toma de fuera y se documenta.
VIVOS_BLOQUES = ["vi.c", "gmc_v8_1.c", "tonga_ih.c", "gfx_v8_0.c",
                 "sdma_v3_1.c", "uvd_v6_3.c", "vce_v3_4.c"]

DEF_FUNC = re.compile(r"^(?:static\s+)?[A-Za-z_][\w \*]*?(\w+)\s*\([^;]*\)\s*$")
LLAMADA = re.compile(r"\b([a-z_][a-z0-9_]{3,})\s*\(")


def _leer(p):
    if not os.path.isfile(p):
        raise SystemExit("ERROR/INVALID: no existe %s" % p)
    return io.open(p, encoding="utf-8", errors="replace").read().splitlines()


def sitio_de_ipver():
    """Compone con la herramienta de la otra sesion; NO re-deriva el censo.

    Si el formato de su salida cambia, esta herramienta se NIEGA a seguir, en vez
    de devolver una lista vacia con exito. Medido: ese es el fallo que mas caro
    sale, y el que ya me hizo una vez.
    """
    r = subprocess.run([sys.executable, IPVER], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("ERROR/INVALID: ipver_zero.py rc=%d" % r.returncode)
    filas = []
    for l in r.stdout.splitlines():
        m = re.match(r"^(\S+\.c)\s+(\d+)\s+(.*?)\s{2,}(comparacion|switch)\s+(\S+)\s*$", l)
        if m:
            filas.append((m.group(1), int(m.group(2)), m.group(3), m.group(4)))
    if not filas:
        raise SystemExit("ERROR/INVALID: no parseo ninguna fila de ipver_zero.py")
    return filas


def selftest():
    """Vectores conocidos y controles de fallo.

    Los vectores se escribieron DESPUES de mirar la salida, asi que no son
    independientes: son una red de rete, no una prueba. Lo que si es
    independiente es la comprobacion de que los ficheros descartados son de
    verdad bloques no instanciados, y esa se hace con los 4 nombres reales.
    """
    ok = fallan = 0

    def chk(nombre, cond):
        nonlocal ok, fallan
        if cond:
            ok += 1
            print("  OK    %s" % nombre)
        else:
            fallan += 1
            print("  FALLA %s" % nombre)

    cache = {}
    for f in sorted(x for x in os.listdir(AMDR) if x.endswith((".c", ".h"))):
        cache[f] = _leer(os.path.join(AMDR, f))
    func_por_lugar, llamadas = indice(cache)
    no_vivos = ficheros_no_vivos(cache, VIVOS_BLOQUES_NOMBRES | {"gfx_v8_0"})

    # ficheros NO VIVOS, verificados contra ficheros
    for f, bloque in (("mes_v11_0.c", "mes_v11_0"), ("gfx_v12_0.c", "gfx_v12_0"),
                      ("gmc_v9_0.c", "gmc_v9_0")):
        chk("%s se clasifica NO VIVO (bloque %s)" % (f, bloque),
            f in no_vivos and any(b.startswith(bloque) for b in no_vivos[f]))
    for f in ("gfx_v8_0.c", "gmc_v8_1.c", "sdma_v3_1.c", "vi.c"):
        chk("%s NO se clasifica NO VIVO (es bloque vivo de esta placa)" % f,
            f not in no_vivos)
    for f in ("amdgpu_gmc.c", "amdgpu_vm.c", "amdgpu_device.c"):
        chk("%s NO se clasifica NO VIVO (no es un fichero de bloque)" % f,
            f not in no_vivos)

    # el resultado completo
    rc = main([])
    chk("la ejecucion completa no falla", rc == 0)

    # LA RESPUESTA CONOCIDA, escrita a mano mirando la salida y luego
    # verificada contra el grafo: estos 4 son los unicos descartables.
    ESPERADO = [("amdgpu_gfx.c", 514), ("amdgpu_gmc.c", 1766),
                ("amdgpu_mes.c", 682), ("amdgpu_mes.c", 683)]
    chk("la lista de descartables es exactamente la esperada",
        RESULTADO.get("descartables") == ESPERADO)

    # REGRESIONES medidas, una a una. Cada una fue un falso positivo real de una
    # version anterior; sin estos controles volverian.
    chk("NO descarta amdgpu_dma_buf_attach (lo llama el kernel por dma_buf_ops)",
        ("amdgpu_dma_buf.c", 95) not in RESULTADO.get("descartables", []))
    chk("NO descarta amdgpu_device_reset_sriov (se llama desde amdgpu_device.c)",
        not any(f == "amdgpu_device.c" for f, _ in RESULTADO.get("descartables", [])))
    chk("NO descarta convert_tiling_flags_to_modifier (se llama desde "
        "amdgpu_display.c)",
        not any(f == "amdgpu_display.c" for f, _ in RESULTADO.get("descartables", [])))
    # El formateador de salida usaba %-32s y recortaba el nombre de 39
    # caracteres a "..._map", que es OTRO identificador.
    #
    # MEDIDO: la primera comprobacion miraba RESULTADO["nombres"], que viene de
    # los DATOS, y por eso NO cazaba la mutacion N4: el defecto estaba en la
    # capa de SALIDA y el test miraba otra capa. Un test de salida tiene que
    # mirar la salida. Ahora se captura lo impreso.
    import contextlib
    import io as _io
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf):
        main([])
    impreso = buf.getvalue()
    chk("el nombre se imprime ENTERO en la salida (el %%-32s lo recortaba)",
        "amdgpu_gfx_mqd_symmetrically_map_cu_mask" in impreso
        and "amdgpu_gfx_mqd_symmetrically_map " not in impreso)
    chk("los DATOS ya traian el nombre entero",
        RESULTADO.get("nombres", {}).get(("amdgpu_gfx.c", 514))
        == "amdgpu_gfx_mqd_symmetrically_map_cu_mask")

    # MEDIDO: la mutacion N3 (contar las DECLARACIONES de un .h como llamadas)
    # solo se detecta mirando la PROPIEDAD: con este corpus el resultado no
    # cambia, porque un .h nunca entra en `no_vivos`, con lo que el descarte
    # sale igual. Se controla que ningun sitio descartable tenga un llamador que
    # solo aparezca en un .h, que es lo que N3 romperia.
    _, llam_ref = indice(cache)
    for _f, _n in ESPERADO:
        _fn = RESULTADO["nombres"].get((_f, _n))
        _ll = llam_ref.get(_fn, [])
        chk("el descartable %s:%d tiene llamadores y ninguno solo en un .h"
            % (_f, _n),
            bool(_ll) and not any(x[0].endswith(".h") for x in _ll))

    print("  ---")
    print("  vectores OK: %d   controles en rojo: %d" % (ok, fallan))
    return 1 if fallan else 0



VIVOS_BLOQUES_NOMBRES = {"vi_common", "gmc_v8_1", "tonga_ih", "gfx_v8_0",
                         "sdma_v3_1", "uvd_v6_3", "vce_v3_4", "amdgpu_vkms", "dm"}


def ficheros_no_vivos(lineas_cache, bloques_vivos):
    """Ficheros cuyo contenido es UN bloque IP que esta placa no instancia.

    Un fichero es NO VIVO de forma DEMOSTRABLE cuando define un `X_ip_block` y
    X no esta en la lista de bloques que `gfx8blocks.py` medio. Eso es un hecho
    de EV-39, no una lista escrita a mano, y por eso es el unico criterio que
    permite DESCARTAR.

    MEDIDO, y es el error de razonamiento que organizo toda esta herramienta:
    primero cerre el grafo de alcance para decidir que ficheros eran vivos, y
    con un recall del 96,2% eso descartaba de mas -- entre otros a
    `amdgpu_device_init`, que es LA funcion de inicializacion. Un filtro que
    descarta no puede apoyarse en una aproximacion: necesita un hecho. Aqui el
    hecho es "este fichero solo implementa un bloque que no existe en esta
    placa".
    """
    out = {}
    for f, ls in lineas_cache.items():
        if not f.endswith(".c"):
            continue
        bloques = set()
        for l in ls:
            for m in re.finditer(r"^\w[\w \*]*?(\w+_ip_block)\s*=", l):
                bloques.add(m.group(1)[:-len("_ip_block")])
        if bloques and not (bloques & set(bloques_vivos)):
            out[f] = sorted(bloques)
    return out


def tablas_ip_funcs(lineas_cache):
    """Nombres que aparecen en tablas `*_ip_funcs`.

    El driver llama a funciones por PUNTERO a traves de esas tablas, y un indice
    por texto no las ve. Sin sembrarlas aqui, cualquier funcion alcanzable solo
    de forma indirecta se declararia inalcanzable, que es un falso positivo
    silencioso: el peor defecto posible en un filtro de alcance.
    """
    nombres = set()
    for f, ls in lineas_cache.items():
        if not f.endswith(".c"):
            continue
        dentro = False
        for l in ls:
            if re.search(r"\w*_ip_funcs\b", l):
                dentro = True
            if dentro:
                for m in re.finditer(r"\.(\w+)\s*(?:,|\})", l):
                    nombres.add(m.group(1))
                if re.match(r"^\};", l):
                    dentro = False
    return nombres


def alcanzables_desde(semillas, lineas_cache, func_por_lugar):
    """Cierre transitivo de CALLEES desde unas semillas.

    Se propaga por CALLEES, no por llamadores: lo que se pregunta es "se ejecuta
    esto en esta placa", que es una pregunta de alcance hacia abajo desde el
    punto de entrada, no de quien llama.

    MEDIDO, y es la correccion que hacia falta: la primera version declaraba
    "vivos" una lista corta de ficheros, y descartaba `amdgpu_device_init` -- que
    es LA funcion de inicializacion -- porque su unico llamador esta en
    `amdgpu_drv.c`, fichero que no estaba en la lista. Un conjunto vivo
    incompleto rompe la propiedad de una sola direccion: si se puede descartar
    mal, se descarta mal. Con el cierre desde `amdgpu_drv.c` el conjunto vivo ya
    no se escribe a mano.
    """
    vivo = set(semillas)
    frontera = set(semillas)
    while frontera:
        nuevo = set()
        for f, ls in lineas_cache.items():
            for k, l in enumerate(ls, 1):
                if func_por_lugar.get((f, k)) not in frontera:
                    continue
                limpio = re.sub(r"/\*.*?\*/", "", l)
                if limpio.lstrip().startswith("#"):
                    continue
                for cm in LLAMADA.finditer(l):
                    if cm.group(1) not in vivo:
                        nuevo.add(cm.group(1))
        nuevo -= vivo
        vivo |= nuevo
        frontera = nuevo
    return vivo


def indice(lineas_cache):
    """Devuelve (func_por_lugar, llamadas_por_nombre).

    func_por_lugar[(fichero, linea)] = nombre de la funcion que contiene esa linea
    llamadas_por_nombre[nombre]    = [(fichero, linea), ...] en TODO el arbol
    """
    func_por_lugar = {}
    llamadas = {}
    for f, ls in sorted(lineas_cache.items()):
        actual = None
        pendiente = None
        prof = 0
        # MEDIDO, tres correcciones sucesivas y las tres eran MIAS:
        #  1. un `continue` en el `elif` se comia el `func_por_lugar[...] = actual`,
        #     con lo que el indice salia vacio en el 100% de los sitios.
        #  2. resetear `actual` en cualquier linea de columna 0 rompia con los
        #     `#endif`, `};` y `#include` que hay entre una definicion y su
        #     cuerpo: fn salia None otra vez.
        #  3. lo que delimita un cuerpo de verdad es la PROFUNDIDAD DE LLAVES,
        #     no el sangrado ni la columna. Se usa eso.
        for k, l in enumerate(ls, 1):
            limpio = re.sub(r"/\*.*?\*/", "", l)
            limpio = re.sub(r"//.*", "", limpio)
            es_def = False
            if not limpio.lstrip().startswith("#"):
                m = DEF_FUNC.match(limpio)
                # MEDIDO: las firmas de este driver ocupan a menudo DOS lineas
                # (`static void f(struct amdgpu_device *adev,` / `   u32 a, u32 b)`),
                # con lo que DEF_FUNC no casaba y la funcion salia sin nombre.
                if not m and k < len(ls):
                    m = DEF_FUNC.match(limpio.rstrip() + " " + ls[k].strip())
                es_def = bool(m)
                if m:
                    pendiente = m.group(1)
                opens = limpio.count("{")
                closes = limpio.count("}")
                if pendiente and opens:
                    actual = pendiente
                    pendiente = None
                prof += opens - closes
                if prof <= 0 and not (pendiente or opens):
                    actual = None
                    prof = 0
            func_por_lugar[(f, k)] = actual
            # Tres filtros que MEDIDAMENTE cambiaban el resultado:
            #  1. la FIRMA de la definicion no es una llamada. Sin este filtro,
            #     `amdgpu_mes_init_microcode` se llamaba a si misma en su propia
            #     linea de definicion y contaba como "vivo en su propio fichero",
            #     con lo que NADA se descartaba.
            #  2. una DECLARACION en .h no es una llamada.
            #  3. una linea que empieza por # es preprocesador, no codigo.
            if es_def:
                continue
            if f.endswith(".h"):
                continue
            if limpio.lstrip().startswith("#"):
                continue
            for cm in LLAMADA.finditer(l):
                llamadas.setdefault(cm.group(1), []).append((f, k))
    return func_por_lugar, llamadas


RESULTADO = {}


def main(argv):
    sitio_de_ipver()
    ficheros = sorted(x for x in os.listdir(AMDR) if x.endswith((".c", ".h")))
    cache = {}
    for f in ficheros:
        cache[f] = _leer(os.path.join(AMDR, f))
    func_por_lugar, llamadas = indice(cache)

    filas = sitio_de_ipver()
    bloques_vivos = VIVOS_BLOQUES_NOMBRES | {"gfx_v8_0"}
    no_vivos = ficheros_no_vivos(cache, bloques_vivos)

    # El conjunto vivo ya NO se escribe a mano: se cierra desde el punto de
    # entrada. Semillas:
    #   * todo lo definido en amdgpu_drv.c   -> el probe de PCI
    #   * las tablas *_ip_funcs de los 8 bloques que instancia gfx8blocks.py
    #     (llamadas indirectas que el indice por texto no ve)
    #   * los ficheros "comunes" que declaro la herramienta de la otra sesion
    semillas = set()
    for k, l in enumerate(cache.get("amdgpu_drv.c", []), 1):
        fn = func_por_lugar.get(("amdgpu_drv.c", k))
        if fn:
            semillas.add(fn)
    for f in list(VIVOS_BLOQUES):
        for k, l in enumerate(cache.get(f, []), 1):
            fn = func_por_lugar.get((f, k))
            if fn:
                semillas.add(fn)
    semillas |= tablas_ip_funcs(cache)
    for f, _n, _e, _c in filas:
        for k, l in enumerate(cache.get(f, []), 1):
            fn = func_por_lugar.get((f, k))
            if fn:
                semillas.add(fn)
    vivos = alcanzables_desde(semillas, cache, func_por_lugar)
    vivos |= semillas
    descartables, quedan, externas = [], [], []
    for f, n, expr, clase in filas:
        fn = func_por_lugar.get((f, n))
        if not fn:
            quedan.append((f, n, fn, expr, "funcion no resuelta"))
            continue
        ll = [(cf, cl) for cf, cl in llamadas.get(fn, []) if not (cf == f and cl == n)]
        if not ll:
            # MEDIDO: la primera version descartaba aqui, y es EXACTAMENTE al
            # reves. No tener llamador en el TEXTO del driver no es estar muerto:
            # significa "lo llama el kernel". `amdgpu_dma_buf_attach` es
            # `.attach = amdgpu_dma_buf_attach` de `dma_buf_ops` y solo lo
            # alcanza un ioctl de ioctl, fuera del texto. Descartar aqui es un
            # falso positivo de manual.
            externas.append((f, n, fn, expr,
                             "sin llamador en el TEXTO: puede ser fops/ioctl"))
            continue
        if all(x[0] in no_vivos for x in ll):
            vivos_ll = [x for x in ll if func_por_lugar.get(x) in vivos]
        else:
            vivos_ll = [x for x in ll]
        if not vivos_ll:
            descartables.append((f, n, fn, expr,
                                 "sus %d llamadores estan en ficheros no vivos"
                                 % len(ll)))
        else:
            quedan.append((f, n, fn, expr, "llamador vivo en %s"
                            % ",".join(sorted(set(x[0] for x in vivos_ll)))[:40]))

    RESULTADO["descartables"] = sorted((f, n) for f, n, _f2, _e, _m in descartables)
    RESULTADO["externas"] = sorted((f, n) for f, n, _f2, _e, _m in externas)
    RESULTADO["quedan"] = sorted((f, n) for f, n, _f2, _e, _m in quedan)
    RESULTADO["no_vivos"] = no_vivos
    RESULTADO["nombres"] = {(f, n): fn for f, n, fn, _e, _m in descartables}
    RESULTADO["filas"] = filas

    print("gchwip_alcance: sitios degenerados de GC_HWIP, y cuales NO rulingan")
    print("  en esta placa.  Filtro de UNA SOLA DIRECCION: descarta, no afirma.")
    print("  " + "-" * 76)
    print("  ficheros del driver indexados ................. %d" % len(cache))
    print("  funciones vivas (cierre desde amdgpu_drv.c) .... %d" % len(vivos))
    print("  sitios totales de ipver_zero.py ................ %d" % len(filas))
    print("  NO ALCANZABLES por analisis de alcance .......... %d" % len(descartables))
    print("  no descartados (NO probados alcanzantes) ...... %d" % len(quedan))
    print("  " + "-" * 76)
    for f, n, fn, expr, mot in descartables:
        # MEDIDO: el campo era %-32s y el nombre de la funcion tiene 39
        # caracteres: la SALIDA lo truncaba a "..._map", que es OTRO
        # identificador. Un formateador que trunca nombres inventa nombres,
        # y un lector concluiria que esa funcion no existe. Ningun
        # identificador se trunca nunca en una salida.
        print("  %-22s:%-5d %-42s %s" % (f, n, (fn or "?"), mot))
    print("  " + "-" * 76)
    print("  Los %d descartables tienen TODOS sus llamadores en ficheros que solo"
          % len(descartables))
    print("  implementan un bloque IP de 9.x/10.x/11.x/12.x, que no se instancian")
    print("  (EV-39, verificado por gfx8blocks.py). Un solo salto: si el")
    print("  intermediario vive en un fichero comun, el sitio NO se descarta aunque")
    print("  no se ejecute nunca. Se pierden positivos a proposito.")
    print("  LIMITE: lo que queda NO esta probado alcanzable. El indice por grep")
    print("  no ve punteros a funcion y el driver usa tablas *_ip_funcs.")
    print("  'no descartado' != 'vivo'.")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv[1:]:
        sys.exit(selftest())
    sys.exit(main(sys.argv[1:]))
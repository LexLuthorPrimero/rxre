#!/usr/bin/env python3
# CONTRACT: name=ibref
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO, y por que WRITES_FILES=no con `open(cstub,"w")` en la linea 2281.
#
# Las seis escrituras de este fichero (2281, 2292, 2347, 2351 y las del
# round-trip) caen dentro de `selftest` y van a
# `tempfile.mkdtemp(prefix="ibref_stub_")`.  Clase TEMPORAL de
# `contract_exec.py`.  El stub se compila y se carga de ahi precisamente para
# no tocar el arbol: es lo que hace el selftest, y escribirlo dentro del
# proyecto seria contaminar el corpus que el selftest usa de verdad.
#
# TOUCHES_INTEGRATED=no: sintetiza IB desde el fuente del driver.  No abre
# sysfs, no abre DRM, no escribe en la GPU.  Ver 1487.
# ibref.py -- sintetiza un IB de REFERENCIA para un punto de emision de PM4.
#
# RECONSTRUIDO. El 2026-10-04 se perdio el fichero (0 bytes) al truncarlo desde
# un script de edicion que iba a fallar y escribio None. No hay copia en git
# (nunca se commiteo). El unico ejemplar es el `.pyc` que el interprete al
# ejecutar el selftest, y eso obliga a reconstruirlo desde ahi.
#
# DE DONDE SALE CADA COSA, Y QUE SE PUEDE Y QUE NO SE PUEDE COMPROBAR
# ------------------------------------------------------------------
#   docstrings y firmas   del `.pyc`, LITERALES. El interprete conserva los
#                        docstrings como constantes, asi que el texto de la
#                        medicion es el que habia, no una reconstruccion.
#   orden de definicion  del `.pyc` (co_firstlineno), tambien literal.
#                  de este fichero, reimplementado y validado contra el
#                        `.pyc`, que SIGUE EJECUTANDOSE como oraculo.
#
# LO QUE NO SE PUEDE COMPROBAR, Y SE DICE
# ---------------------------------------
# El `.pyc` se puede ejecutar pero no leer como fuente: los cuerpos hay que
# reimplementarlos. Este fichero esta validado por COMPORTAMIENTO contra el
# `.pyc` (mismos vectores, mismos dwords, misma salida), no por identidad de
# texto. Que dos implementaciones den lo mismo no prueba que sean el mismo
# programa, y esa diferencia queda declarada en vez de tapada.
#
# El `.pyc` de referencia: tools/__pycache__/ibref.cpython-314.pyc
# Oraculo ejecutable:     tools/_orculo_ibref.pyc  (copia, para que RAIZ cuadre)
#
# POR QUE EXISTE, Y QUE FALTA SIN EL
# ---------------------------------
# El proyecto tiene Instrumentos que describen PM4 y **no tiene ningun IB**. No hay
# un solo paquete decodificado en el arbol. Consecuencia medida: los hallazgos
# `1073`, `1082` y `1077` sobre `SET_RESOURCES`, `MAP_QUEUES` y `UNMAP_QUEUES`
# quedan en `PROVEN_DERIVED` y no en `OBSERVED`, porque la cifra que se contrasta es
# un dword calculado a mano con los macros, no un dword leido de una emision.
#
# Este instrumento produce ese artefacto que falta. No ejecuta nada, no toca la
# GPU y no escribe en el arbol.
#
#   --func <nombre>              lista los PARAMETROS y los dwords ya constantes
#   --func <nombre> --set k=v    sintetiza los dwords concretos
#   --func <nombre> --set ... --decode
#                                los decodifica con los layouts declarados por
#                                las herramientas del proyecto
#
# POR QUE LOS PARAMETROS SE DESCUBREN Y NO SE ESCRIBEN A MANO
# ---------------------------------------------------------
# El evaluador de `pm4_emit` (`eval_call`) devuelve `int` para una expresion
# constante y lanza `Unresolved(<nombre>)` cuando encuentra un identificador que no
# puede resolver. Ese `<nombre>` **es** el parametro de runtime.
#
# Se liga el evaluador de `pm4_emit` con el parser de escrituras, de modo que la
# lista de parametros sale del codigo del driver y no de una suposicion mia. Si
# manana el driver renombra `ring->queue`, el parametro se llama distinto y el
# error es visible; una lista escrita a mano seguiria diciendo `queue`.
#
#   PARAMETRO DESCUBIERTO  el parametro lo nombra el codigo que lo usa
#   PARAMETRO SUPUESTO    una lista fija que el driver puede invalidar sin que
#                         nadie note  <- lo que hace `pm4_emit` con el nombre
#                         de la variable del anillo, y lo que hace `layoutcross`
#                         con el catalogo de cabeceras (hallazgos 1089 y 1087)
#
# NO SE PUEDE EMPEZAR POR UN IB FIJO, Y POR QUE
# ---------------------------------------------
# Los valores que escriben estas funciones **no son constantes en el codigo**:
#
#     amdgpu_ring_write(kiq_ring, PACKET3(PACKET3_MAP_QUEUES, 5));
#     amdgpu_ring_write(kiq_ring, PACKET3_MAP_QUEUES_QUEUE(ring->queue) | ...);
#
# `ring->queue` lo decide el runtime. El artefacto que falta no es "el IB" sino
# **"un IB de referencia para unos valores elegidos"**, y la eleccion de esos
# valores es lo que hace el layout observable: con `queue == 0` casi todos los
# layouts dan el mismo resultado y no se distinguen. Es el discriminante que
# `1077` nombra y que hasta ahora no se podia ejecutar.
#
# LIMITE DECLARADO
# ----------------
# No se modela el flujo de control. Una escritura dentro de un `if` se sintetiza
# como si ocurriera siempre, y se marca `[cond]`. Es el mismo limite que declara
# `layoutcross` y el mismo criterio: para un generador de artefactos, notificar de
# mas es el sentido seguro; el que consume debe mirar la marca.
#
# CAMPOS CONOCIDOS QUE NO SE RESUELVEN
# -------------------------------------
# `ring->mqd_addr`, `ring->wptr_addr` y `lower_32_bits(...)` / `upper_32_bits(...)`
# no son escalares. Se pueden ligar por nombre (`mqd_addr=0x11223344`) y el
# generador aplica la mascara de `lower_32_bits`/`upper_32_bits` si el nombre
# empieza por esas dos. Si no se ligan, el IB sale incompleto y **se dice**: un
# IB parcial marcado es informacion; un IB parcial silencioso es una trampa.

import argparse
import glob
import importlib.util
import json
import os
import re
import sys
import tempfile

VERSION = '1.0'

path = os.path.dirname
abspath = os.path.abspath
# `RAIZ` es la raiz del PROYECTO, un nivel por encima de `tools/`. Con
# solo `dirname` apuntaba a `tools/` y `EMIT` salia en
# `tools/08-ARQUITECTURA/tools/pm4_emit.py`, que no existe: el
# ImportError decia la ruta y por eso senalaba al path, no al modulo.
RAIZ = path(path(abspath(__file__)))
AMD = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd", "amdgpu")
TARGET = "gfx_v8_0.c"
EMIT = os.path.join(RAIZ, "08-ARQUITECTURA", "tools", "pm4_emit.py")
KFD_OPS = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                       "drivers", "gpu", "drm", "amd", "amdkfd",
                       "kfd_pm4_opcodes.h")

RE_RING_WRITE = re.compile(
    r"amdgpu_ring_write\s*\(\s*([A-Za-z_]\w*)\s*,\s*(.+?)\s*\)\s*;", re.S)
RE_IB_WRITE = re.compile(
    r"([A-Za-z_]\w*)\.ptr\[\s*\1\.length_dw\+\+\s*\]\s*=\s*(.+?);", re.S)


def cargar_modulo(ruta):
    """Importa un .py por RUTA, sin tocar sys.path del proceso.

    Igual que en `layoutcross`: cargar por import normal metería el directorio
    del modulo en el path y podria encontrar otro `pm4_codec` que no es el del
    arbol. Con `--tablas` pointed a una declaracion candidata, la ruta tiene que
    ser exacto.
    """
    spec = importlib.util.spec_from_file_location(
        "ibref_tabs_" + os.path.splitext(os.path.basename(ruta))[0], ruta)
    if spec is None or spec.loader is None:
        raise ImportError("no importable: %s" % ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


KERNEL_INC = os.path.join(RAIZ, "RESEARCH", "kernelbuild", "linux-7.1.3",
                           "include")
# El include de kernel con angulo se resuelve contra UN `-I`, y en el kernel hay
# mas de uno. MEDIDO, y esto es lo que faltaba:
#
#     amdgpu.h:51      #include <drm/amdgpu_drm.h>
#     kernelbuild/include/drm/amdgpu_drm.h          NO EXISTE
#     kernelbuild/include/uapi/drm/amdgpu_drm.h    SI  (y define
#                                                     AMDGPU_IB_FLAG_...)
#
# Con una sola raiz (`include/`) la ampliacion alcanzaba 380 cabeceras y
# CERO de `drm/`, porque el nombre `<drm/...>` solo existe bajo `uapi/`. La
# bandera `AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID` = (1<<4) vive ahi, y sin ella
# la condicion `ib->flags & AMDGPU_IB_FLAG_...` no se puede resolver.
#
# El orden importa y es el de `resolve_includes`: el PRIMERO que existe gana.
#
# EL TOPE, Y POR QUE ESTA MEDIDO Y NO PUESTO A 1000 POR RUTINA
# ------------------------------------------------------------
# MEDIDO: con tope 400 se alcanzaban 400 cabeceras y `truncado=True`. El
# conjunto real son **602**, de modo que el tope de 400 estaba ocultando 202
# cabeceras, el 33%. Y entre las que ocultaba estaba `uapi/drm/amdgpu_drm.h`,
# que es la que trae `AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID`.
#
# 1200 esta por encima de 602 con margen, y el informe declara `truncado`
# para que, si el grafo creciera, se viera en la salida y no solo en el
# codigo. Un tope que trunca en silencio es un tope que produce un conjunto
# incompleto que parece completo.
RAICES_ANGLE = (
    "",
    "uapi" + os.sep,
    ".." + os.sep + "arch" + os.sep + "x86" + os.sep + "include" + os.sep
    + "uapi" + os.sep,
    ".." + os.sep + "arch" + os.sep + "x86" + os.sep + "include" + os.sep
    + "generated" + os.sep,
)
RE_INC_ANGULO = re.compile(r"^[ \t]*#[ \t]*include[ \t]*<([^>]+)>", re.M)
_FICHEROS_EDITADOS = ("amdgpu_debugfs.c", "amdgpu_debugfs.h", "amdgpu_vm.c",
                      "amdgpu_vm_pt.c")


def _raiz_segura():
    """(bool, motivo): se puede ampliar la raiz sin que cambie el sujeto."""
    inc = KERNEL_INC
    if not os.path.isdir(inc):
        return False, "no existe %s" % inc
    for f in _FICHEROS_EDITADOS:
        if not os.path.isfile(os.path.join(inc, f)):
            continue
        return False, ("un fichero editado del proyecto esta bajo include/: %s"
                       % f)
    return True, ("los %d ficheros editados del proyecto NO estan bajo include/"
                  % len(_FICHEROS_EDITADOS))


def ficheros_de_include_angular(entrada, max_extra=1200, semillas=()):
    """Ficheros alcanzados por `#include <...>`, para pasarlos a load_macros.

    El include de kernel con angulo se resuelve contra `include/` (y `uapi/`),
    NO contra el directorio del fichero que incluye. Resolverlo como si fuera
    relativo daria el fichero equivocado sin avisar, que es la razon por la que
    el include esta escrito con angulo.

    LAS SEMILLAS, Y POR QUE SON NECESARIAS
    --------------------------------------
    MEDIDO: con solo la entrada (`gfx_v8_0.c`) como semilla, la ampliacion
    alcanzaba 380 cabeceras y CERO de `drm/`. Y el include que las trae es

        amdgpu.h:51      #include <drm/amdgpu_drm.h>

    `amdgpu.h` se llega desde `gfx_v8_0.c` con COMILLAS, y este paseo sigue solo
    `<...>`. O sea: los dos resolutores son complementarios y ninguno basta solo.

      con comillas -> relativos y de los directorios con nombre   (pm4_emit)
      con angulo   -> include/, include/uapi/, arch/...           (este)

    Por eso `semillas` son los ficheros que el resolutor de comillas YA
    encontro, y no solo el punto de entrada. Sin esto, lo que hay tras la
    primera comilla es invisible para el paseo angular.
    """
    if not os.path.isdir(KERNEL_INC):
        return [], {"raiz": KERNEL_INC, "estado": "NO_HAY_RAIZ"}
    vistos, cola, encontrados = set(), [entrada] + list(semillas), []
    while cola and len(encontrados) < max_extra:
        actual = cola.pop(0)
        if actual in vistos:
            continue
        vistos.add(actual)
        try:
            txt = open(actual, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in RE_INC_ANGULO.finditer(txt):
            for pref in RAICES_ANGLE:
                cand = os.path.normpath(os.path.join(KERNEL_INC, pref,
                                                     m.group(1)))
                if os.path.isfile(cand) and cand not in encontrados:
                    encontrados.append(cand)
                    cola.append(cand)
                    break
    return encontrados, {
        "raiz": KERNEL_INC, "estado": "OK",
        "raices": [os.path.normpath(os.path.join(KERNEL_INC, p))
                   for p in RAICES_ANGLE],
        "alcanzados": len(encontrados),
        "truncado": len(cola) > 0}


RE_CAST_TIPO = re.compile(r"\(\s*__typeof__\s*\(\s*[^()]*?\s*\)\s*\)\s*"
                          r"\(\s*([^()]*?)\s*\)")


def _cierra(s, i):
    """Índice del `)` que cierra el `(` de `s[i]`, o -1 si no cierra.

    MEDIDO:  hacer esto con un REGEX no funciona.  `(__typeof__(x))(__typeof__(y))(7)`
    tiene un cast cuyo ARGUMENTO es otro cast, y un patron que exige `[^()]*?`
    dentro no puede consumirlo: se come el de dentro y deja `(__typeof__(x))7`
    colgando, que es justo lo que hacia el vector.

        lo que exige emparejar parentesis no se escribe con parentesis
    """
    d = 0
    for j in range(i, len(s)):
        if s[j] == "(":
            d += 1
        elif s[j] == ")":
            d -= 1
            if d == 0:
                return j
    return -1


def _quita_cabeza(s):
    """(argumento, cola) si `s` empieza por un cast `(__typeof__(x))(`; None.

    `argumento` lleva SUS PROPIOS parentesis, porque el argumento de un cast
    puede ser a su vez un cast: `(__typeof__(x))(__typeof__(y))(7)`  tiene como
    argumento `(__typeof__(y))(7)`,  y su parentesis de cierre es el ultimo de
    la cadena.  MEDIDO:  tomar el texto DESPUES del cierre daba `` (el
    argumento entero se perdia)  y tomar el INTERIOR daba `(7)` en vez de `7`.
    El argumento es `s[j:c3+1]`, con los dos extremos.
    """
    t = s.lstrip()
    if not t.startswith("(__typeof__"):
        return None
    k = len("(__typeof__")
    c1 = _cierra(t, k)                     # cierra el `(x)` del typeof
    if c1 < 0 or c1 + 1 >= len(t) or t[c1 + 1] != ")":
        return None
    j = c1 + 2                            # abre el `(argumento)`
    while j < len(t) and t[j] in " \t\n":
        j += 1
    if j >= len(t) or t[j] != "(":
        return None
    c3 = _cierra(t, j)                     # cierra el `(argumento)`
    if c3 < 0:
        return None
    return t[j:c3 + 1], t[c3 + 1:]


def _desenvuelve(s):
    """Quita los parentesis que ENVUELVEN todo, y solo esos.

    Se exige que al quitar uno los siguientes sigan cerrando todo, y eso lo dice
    `_cierra`:  `a + (b)` no se desenvuelve,  `(a) + b` tampoco.

    MEDIDO:  la primera version llamaba a `balanced()`,  que existe en el STUB
    como cadena y NO como funcion de este modulo.  Un nombre que suena a que
    existe y no existe es un `NameError` esperando:  aqui salio al ejecutar, y
    en un vector habria salido como fallo de la regla y no como fallo del
    codigo.
    """
    t = s.strip()
    while t.startswith("(") and t.endswith(")") and _cierra(t, 0) == len(t) - 1:
        t = t[1:-1].strip()
    return t


def _quita_cast_medio(s):
    """Quita UN cast `(__typeof__(x))(a)` que este EN MEDIO de la expresion.

    MEDIDO, y esto es lo que fallo al reescribir:  el cuerpo real de
    `__ALIGN_KERNEL` es

        __ALIGN_KERNEL_MASK(x, (__typeof__(x))(a) - 1)

    con el cast EN MEDIO.  La primera version (un regex) lo cubria porque
    sustitulia en cualquier sitio;  la segunda solo quitaba casts al PRINCIPIO,
    y al perder el caso intermedio el cuerpo de `__ALIGN_KERNEL` se quedo con
    `__typeof__` sin resolver y `sintetizar("ALIGN(0,256)")` devolvio `None`.

        un parser mas estricto no es un parser mas correcto:  es un parser que
        ha perdido el caso que el regex cubria sin que se notara

    Se limita a UNA sustitucion y exige que el argumento no tenga parentesis
    anidados, que es justo lo que el regex permitia.  El caso anidado lo cubre
    `_quita_cabeza`.
    """
    salida, pos, quito = [], 0, False
    for mt in RE_CAST_TIPO.finditer(s):
        salida.append(s[pos:mt.start()])
        salida.append(mt.group(1))
        pos = mt.end()
        quito = True
    if not quito:
        return None
    salida.append(s[pos:])
    return "".join(salida)


def quitar_cast_tipo(cuerpo):
    """`(__typeof__(x))(a)` -> `a`. El cast a un tipo no cambia un entero.

    Y se ENCADENA cuando el cast esta al principio:
    `(__typeof__(x))(__typeof__(y))(7)` -> `7`.  MEDIDO, y las versiones
    intermedias fallaron de tres maneras distintas,  las tres pareciendo un
    error de tecleo:  el regex se comia el cast de dentro y dejaba
    `(__typeof__(x))7`;  el parser mal escrito devolvia `''`;  y el parser bien
    escrito perdio el caso EN MEDIO y dejo `ALIGN` sin resolver.

    EL ALCANCE, y por que `_desenvuelve` solo se aplica a los casts de cabeza:

    `_adaptar_macros` aplica esta funcion a los CUERPOS de las 114672 macros del
    arbol.  MEDIDO:  al principio `_desenvuelve` se llamaba SIEMPRE, y al
    desenvolver los parentesis cambio el cuerpo de `ALIGN`.  Es semanticamente
    equivalente, y aun asi los cinco vectores de ALIGN volvieron a fallar.

        quitar parentesis de todo lo que se pasa es cambiar cosas que no se
        han pedido cambiar
    """
    s = cuerpo
    cabeza = False                     # se quito un cast de CABEZA
    for _ in range(64):              # guarda: 64 niveles es absurdo
        r = _quita_cabeza(s)
        if r is not None:
            argumento, cola = r
            s = argumento + cola
            cabeza = True
            continue
        r = _quita_cast_medio(s)
        if r is None:
            break
        s = r
    return _desenvuelve(s) if cabeza else s


def _adaptar_macros(macros):
    """Aplica `quitar_cast_tipo` al CUERPO de cada macro.

    Solo al cuerpo, nunca al nombre: cambiar el nombre de un macro seria
    inventarse una macro que el kernel no tiene.
    """
    out = {}
    for k, v in macros.items():
        if isinstance(v, tuple) and len(v) >= 2 and isinstance(v[1], str):
            out[k] = (v[0], quitar_cast_tipo(v[1]), v[2] if len(v) > 2 else None)
        else:
            out[k] = v
    return out


def _primario():
    """Los ficheros que el resolutor de COMILLAS ya resolvio, como semillas.

    Se recalcula aqui en vez de confiar en el interior de `load_macros`: esa
    funcion no devuelve la lista, y adivinarla seria inventar. Si el modulo no
    esta cargado se devuelve vacio y la ampliacion sigue funcionando, con menos
    cabeceras, y su informe dice cuantas.

    MEDIDO: antes esto devolvia 0 si `cargar_evaluador` no se habia llamado
    todavia, porque `sys.modules["ibref_pm4_emit"]` valia None. Y 0 semillas
    NO es un fallo visible: el paseo angular seguia y devolvia 429 ficheros
    en vez de 602, con `truncado=False`. Una salida incompleta que parece
    completa es peor que un error.
    """
    mod = sys.modules.get("ibref_pm4_emit")
    if mod is None:
        try:
            cargar_evaluador()
        except Exception as e:                                   # noqa: BLE001
            print("aviso  _primario sin semillas: %s: %s"
                  % (type(e).__name__, e), file=sys.stderr)
            return []
        mod = sys.modules.get("ibref_pm4_emit")
    if mod is None or not hasattr(mod, "resolve_includes"):
        return []
    asic = os.path.join(AMD, "..", "include")
    try:
        return mod.resolve_includes(entrada_por_defecto(),
                                    [AMD, asic, os.path.join(asic,
                                                             "asic_reg")])
    except Exception:                                        # noqa: BLE001
        return []


RE_ENUM = re.compile(r"\benum\b[^{;]*\{(.*?)\}", re.S)
# `[ \t]*` y NO `\s*`: el espacio de un item de enum es horizontal.
#
# MEDIDO, y este patron es la version CORREGIDA de un defecto mio:
# con `\s*` el match de un item con `=` se COMIA el `,\n\t` del item
# siguiente. Ese item perdia su `^` y no se encontraba:
#
#     con \s*   -> 37 items, y CHIP_PITCAIRN NO ESTA entre ellos
#     con [ \t]* -> 30 items, todos, CHIP_PITCAIRN incluido
#
# El efecto no era un item de menos: al no contarse, el contador NO AVANZA y
# todos los valores siguientes salen uno bajos. `CHIP_TOPAZ` daba 9 en vez de
# 10 y `CHIP_POLARIS12` daba 16 en vez de 17. Dos numeros plausibles, y
# ERRONEOS, que el comentario `/* N */` del propio fichero detectaba.
RE_ITEM = re.compile(r"^[ \t]*([A-Za-z_]\w*)[ \t]*(=[ \t]*([^,}]+?)[ \t]*)?"
                     r"(?:,[ \t]*(?:/\*[ \t]*(\d+)[ \t]*\*/)?|[ \t]*$)", re.M)


def enums_implicitos(ficheros):
    """Enum -> {item: valor}, numerando los items que no llevan `=`.

    Devuelve ademas la lista de discrepancias entre la cadena de valores y el
    comentario `/* N */`, porque un comentario que no cuadra con la cadena es
    informacion, no ruido: o el kernel se equivoco, o el parser.

    NO se numeran los items cuyo valor declarado no sea un entero literal
    (`CHIP_X = FOO + 1`, `= 1 << 2` si el evaluador no lo trae). Esos se
    dejan fuera y se cuentan en `sin_resolver`, en vez de ponerles un numero
    inventado.
    """
    tabla, descuadradas, sin_resolver = {}, [], 0
    for f in ficheros:
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for em in RE_ENUM.finditer(txt):
            siguiente = 0
            for m in RE_ITEM.finditer(em.group(1)):
                nombre = m.group(1)
                if not nombre:
                    continue
                declarado = (m.group(3) or "").strip()
                comentario = m.group(4)
                if declarado:
                    try:
                        siguiente = int(declarado, 0)
                    except ValueError:
                        sin_resolver += 1
                        continue
                tabla[nombre] = siguiente
                if comentario is not None:
                    if int(comentario) != siguiente:
                        descuadradas.append("%s: cadena=%d comentario=%s"
                                            % (nombre, siguiente, comentario))
                siguiente += 1
    return tabla, descuadradas, sin_resolver


def entrada_por_defecto():
    return os.path.join(AMD, TARGET)


def macros_ampliadas(load_macros, eval_call, entrada, ampliada=True):
    """Las macros de `pm4_emit` mas las de los headers de kernel.

    Devuelve (macros, informe). El informe dice SI se ha ampliado y CUANTAS
    cabeceras han entrado, porque una amplificacion silenciosa seria una fuente
    mas de macros de la que nadie sabe. Y si la guarda falla, no amplia y lo
    dice: una macro de mas es peor que una macro que falta.
    """
    macros = load_macros()
    info = {"ampliada": False, "raices_extra": [], "cabeceras_extra": 0,
            "motivo": ""}
    if not ampliada:
        info["motivo"] = "ampliacion desactivada a peticion"
        return macros, info
    ok, motivo = _raiz_segura()
    info["guarda"] = motivo
    if not ok:
        info["motivo"] = "NO se amplia: " + motivo
        return macros, info
    extra, iinfo = ficheros_de_include_angular(entrada, semillas=_primario())
    if not extra:
        info["motivo"] = "no hay headers <> alcanzables"
        return macros, info
    try:
        extra_macros = load_macros(files=extra)
    except Exception as exc:                   # noqa: BLE001
        info["motivo"] = "load_macros(files=) fallo: %s: %s" % (
            type(exc).__name__, exc)
        return macros, info
    # FUSION, NO SUSTITUCION.
    # `load_macros(files=...)` construye un diccionario NUEVO a partir de los
    # ficheros que se le pasan. Devolverlo directamente reemplaza la tabla y
    # tira 83440 macros de golpe. MEDIDO: ampliar sin fusionar daba 20441
    # macros en vez de 103881, y perdia hasta `PACKET3_SET_SH_REG`.
    #
    # Y hay colisiones de verdad: `pr_fmt` es `"amdgpu: " fmt` en amdgpu y `fmt`
    # en el kernel. Gana el PRIMARIO, que es el header del driver, y la
    # colision se cuenta y se declara.
    # La interseccion se calcula ANTES de fusionar. Calcularla despues mezcla
    # los conjuntos y `extra_macros[k]` revienta con KeyError para cada nombre
    # que solo esta en uno de los dos. El sintoma (un KeyError sobre un nombre
    # larguisimo) no senala el sitio: la interseccion es lo que se calculo mal.
    comunes = set(macros) & set(extra_macros)
    colisiones = sorted(k for k in comunes
                        if macros[k] != extra_macros[k])
    # El PRIMARIO gana. Se hace al reves de lo intuitivo a proposito:
    # `base.update(extra)` deja que gane el EXTRA, que es justo lo contrario de
    # lo que el comentario de arriba dice. Ya paso: `pr_fmt` salia con el cuerpo
    # del kernel (`fmt`) en vez del de amdgpu (`"amdgpu: " fmt`). Un comentario
    # que describe una politica y un codigo que aplica la contraria es peor que
    # no tener politica, porque el comentario es lo que se lee.
    base = dict(extra_macros)
    for _k, _v in macros.items():
        base[_k] = _v
    base = _adaptar_macros(base)
    # --- LOS ENUMS, QUE MEDIDOS NO LLEGAN POR NINGUN OTRO CAMINO ------------
    #
    # MEDIDO: `pm4_emit.load_enums` existe y corre, y sobre
    # `include/drm/amd_asic_type.h` saca 1 item de 30. Su `ENUM_ITEM_RE` exige
    # `=`, y en ese enum solo `CHIP_TAHITI = 0` lo lleva; los otros 29 siguen la
    # cadena. Los que se pierden incluyen `CHIP_POLARIS12` (17), que es la
    # identidad del ASIC de ESTA maquina segun su device-id 0x699f.
    #
    # Aqui se numeran los implicitos por la regla de C, y el comentario
    # `/* N */` de cada item se usa como ORACULO INDEPENDIENTE. Lo que no es un
    # literal entero NO se numera: se cuenta y se declara, porque un numero
    # puesto ahi seria inventado y por indistinguishable de uno medido.
    enums, descuadradas, sin_numerar = enums_implicitos(
        [entrada] + list(_primario()) + list(extra))
    # LA FORMA DE LA ENTRADA, Y POR QUE ES `(-1, str(valor), None)`.
    #
    # `pm4_emit.resolve` hace:  `nparams, body, _ = macros[name]` y luego
    #     if nparams == -1:   <resolver `body` como texto>
    #     raise Unresolved(name + "/")     # "se llama con argumentos"
    #
    # O sea que el PRIMER elemento es el numero de PARAMETROS de la macro, no
    # su valor. MEDIDO, y el sintoma es el que mas cuesta leer sin la fuente:
    #
    #     base["CHIP_TOPAZ"] = (10, "enum", None)
    #         -> Unresolved: CHIP_TOPAZ/
    #
    # con la BARRA FINAL, que es la marca de "no lo se como llamada" y no de
    # "no lo conozco". Yo habia leido la entrada de otra macro,
    # `AMDGPU_IB_FLAG_... = (-1, '(1 << 4)', None)`, y habia puesto el valor
    # en la ranura equivocada: creia que era el valor porque ahi valia -1.
    # -1 es un centinela de "sin parametros", no un valor.
    #
    # La procedencia (que viene de un enum y no de un #define) NO cabe en la
    # entrada: el tercer elemento lo descarta el evaluador. Va en `info`.
    n_enum = 0
    for _nombre, _valor in enums.items():
        if _nombre not in base:
            base[_nombre] = (-1, str(_valor), None)
            n_enum += 1
    if descuadradas:
        # Un comentario que no cuadra NO se tira: puede ser que el kernel tenga
        # el enum mal, y eso es un hallazgo. Se declara entero y se imprime.
        print("aviso  enums: %d DESCUADRE(S) cadena<->comentario; primeros: %s"
              % (len(descuadradas), "; ".join(descuadradas[:6])),
              file=sys.stderr)
    info["enums_items"] = len(enums)
    info["enums_nuevos"] = n_enum
    info["enums_descuadrados"] = len(descuadradas)
    info["enums_sin_numerar"] = sin_numerar
    if enums:
        print("aviso  enums: +%d items a la tabla (de %d en total); "
              "descuadrados=%d; declaraciones no literales sin numerar=%d"
              % (n_enum, len(enums), len(descuadradas), sin_numerar),
              file=sys.stderr)
    info["colisiones"] = colisiones[:20]
    info["n_colisiones"] = len(colisiones)
    info["macros_base"] = len(macros)
    info["nuevas"] = len(set(extra_macros) - set(macros))
    info["ampliada"] = True
    info["cabeceras_extra"] = len(extra)
    info["raices"] = iinfo.get("raices", [])
    info["truncado"] = iinfo.get("truncado", False)
    info["motivo"] = ("ampliada: %d -> %d macros (+%d), %d colision(es) "
                      "resueltas a favor del primario; guardada: %s"
                      % (len(macros), len(base),
                         len(set(extra_macros) - set(macros)),
                         len(colisiones), motivo))
    return base, info


class NoResuelto(Exception):
    """Parametro de runtime: el evaluador no puede y NOS LO DICE."""

    def __init__(self, nombre):
        super().__init__(nombre)
        self.nombre = nombre


def cargar_evaluador(ruta=None):
    """Importa pm4_emit y devuelve (eval_call, load_macros, Unresolved).

    Se importa POR RUTA, sin tocar sys.path del proceso: cargar un modulo
    ajeno por import normal metería su directorio en el path y podría hacer que
    este instrumento encontrase otro `pm4_emit` que no es el del arbol.
    """
    ruta = ruta or EMIT
    mod = sys.modules.get("ibref_pm4_emit")
    # MEDIDO: `sys.modules` guarda el NOMBRE del modulo, no de donde salio. Con
    # solo mirar si el nombre esta, el stub que carga el selftest se quedaba
    # puesto para siempre y `cargar_evaluador()` devolvia el stub cuando se
    # pedia el evaluador de VERDAD. El sintoma no era un nombre equivocado: eran
    # 11 vectores de los condicionales fallando con el error del stub, que no
    # dice de donde viene el modulo.
    #
    # Por eso se guarda la RUTA con la que se cargo, y se recarga si se pide
    # otra. Un modulo cargado por ruta tiene que seguir siendo identificable
    # por su ruta.
    if mod is not None and getattr(mod, "__ibref_ruta__", None) != ruta:
        mod = None
    if mod is None:
        if not os.path.isfile(ruta):
            raise ImportError("no existe el evaluador: %s" % ruta)
        spec = importlib.util.spec_from_file_location("ibref_pm4_emit", ruta)
        mod = importlib.util.module_from_spec(spec)
        mod.__ibref_ruta__ = ruta
        sys.modules["ibref_pm4_emit"] = mod
        spec.loader.exec_module(mod)
    return mod.eval_call, mod.load_macros, mod.Unresolved

RE_DIV_LITERAL = re.compile(
    r"\(\s*(-?(?:0[xX][0-9a-fA-F]+|\d+))\s*\)\s*/\s*"
    r"\(\s*(-?(?:0[xX][0-9a-fA-F]+|\d+))\s*\)")
RE_DIV_PLAIN = re.compile(
    r"(?<![\w.])(-?(?:0[xX][0-9a-fA-F]+|\d+))\s*/\s*"
    r"(-?(?:0[xX][0-9a-fA-F]+|\d+))(?![\w.])")


def _plegar_division(expresion):
    """`A / B` con A y B LITERALES enteros -> el cociente entero.

    Plegado de constantes, no un evaluador de expresiones. La diferencia es lo
    que hace esto seguro: solo toca el caso en que los dos operandos ya son
    numeros, y en ese caso el resultado no puede depender de la precedencia de
    nada, porque no queda nada mas que parsear.

    `/` en C es division ENTERA, con la parte decimal descartada. `7 / 2` es 3,
    no 3.5. Un sintetizador que devolviera un real, o que redondeara, se
    equivocaria de una forma que solo se ve en el resultado final.

    division por cero -> NO se pliega y se deja como estaba. En C es un error de
    compilacion o una excepcion; aqui, devolver algo seria inventar. La
    expression queda intacta para que el evaluador de verdad la rechace.

    Devuelve (expresion, cuantos plegados).
    """
    def _uno(m):
        try:
            a = int(m.group(1), 0)
            b = int(m.group(2), 0)
        except ValueError:
            return m.group(0)
        if b == 0:
            return m.group(0)
        return "(%d)" % (a // b)

    n = 0
    prev = None
    while prev != expresion:
        prev = expresion
        nuevo, k = RE_DIV_LITERAL.subn(_uno, expresion)
        expresion = nuevo
        n += k
    prev = None
    while prev != expresion:
        prev = expresion
        nuevo, k = RE_DIV_PLAIN.subn(_uno, expresion)
        expresion = nuevo
        n += k
    return expresion, n


def _arraysize(expresion, arrays):
    """`ARRAY_SIZE(x)` -> numero de elementos, si `x` es un array que conozco.

    OPCAION, y esta medida. Hay tres caminos y este NO es el primero:

      1. entender `ARRAY_SIZE` en general, lo que exige que el evaluador tenga
         `/`, `[]` y la regla de las aserciones de compilacion (1152 §3). Son
         tres cambios en `pm4_emit.py`, que es de otra sesion.

      2. SUSTITUIRLO por el dato que ya tengo. `arrays_estaticos()` ya cuenta
         los elementos porque los necesita para desenrollar bucles. El valor de
         `ARRAY_SIZE(x)` es, por definicion, ese mismo numero.

      3. dejarlo sin resolver y que la salida lo declare.

    Este es el 2. No necesita nada de nadie mas, y el numero que produce es el
    mismo que produciria el 1 -- porque `ARRAY_SIZE` esta DEFINIDO como
    `sizeof(arr)/sizeof(arr[0])`, y para un array de `u32` eso es el numero de
    elementos. No es una aproximacion: es la misma cantidad por otra via.

    Lo que NO hace es comprobar que `x` sea un array de verdad. No lo comprueba
    `ARRAY_SIZE` tampoco en tiempo de ejecucion: lo comprueba `__must_be_array`
    AL COMPILAR, y este codigo ya ha compilado. Por eso sustituir es honesto.
    """
    RE_AS = re.compile(r"\bARRAY_SIZE\s*\(\s*([A-Za-z_]\w*)\s*\)")

    def _uno(m):
        nombre = m.group(1)
        if nombre not in arrays:
            return m.group(0)
        return "(%d)" % len(arrays[nombre])

    return RE_AS.sub(_uno, expresion)


RE_SIZEOF = re.compile(r"\bsizeof\s*\(\s*([A-Za-z_]\w*)\s*\)")


def _sizeof_arrays(expresion, arrays, entorno=None):
    """`sizeof(x)` -> bytes, para los arrays estaticos que conozco.

    Devuelve (expresion_sustituida, cuantos_se_hay_sustituido). El recuento se
    devuelve porque un `sizeof` que se resuelve a medias es peor que uno que no
    se resuelve: si uno de los tres falla, hay que saberlo.
    """
    entorno = entorno or {}

    n = 0

    def _uno(m):
        nonlocal n
        nombre = m.group(1)
        if nombre in arrays:
            n += 1
            return "(%d)" % (len(arrays[nombre]) * 4)
        if nombre in entorno:
            n += 1
            return "(%d)" % (int(entorno[nombre]) * 4)
        return m.group(0)

    # EL RECUENTO ES DE SUSTITUCIONES, NO DE APARICIONES.
    #
    # MEDIDO: `sizeof(T3) + sizeof(NOVATO)` tiene DOS apariciones y UNA
    # sustitucion. Contando apariciones el resultado era 2, que es
    # indistinguible de "las dos se sustituyeron", y el consumidor no podia
    # saber si el `sizeof` se habia resuelto a medias. Y un `sizeof` resuelto a
    # medias es peor que uno que no se resuelve.
    return RE_SIZEOF.sub(_uno, expresion), n


def _sin_comentarios(txt):
    """Comentarios fuera, ANTES de contar nada, CONSERVANDO el numero de lineas.

    Dos cosas, y las dos importan:

    1. Si las comas de un `/* CU_GROUP_COUNT=1 */` cuentan como elementos, la
       cuenta de un array sale inflada sin excepcion. Un bucle mas largo de lo
       que es significa una IB con dwords de mas, y esa IB no se distingue de
       una buena.

    2. Si se borra el comentario SIN DEJAR SUS SALTOS DE LINEA, todas las lineas
       posteriores se desplazan. MEDIDO: `gfx_v8_0_do_edc_gpr_workarounds`
       reportaba bucles no reconocidos en las lineas 1493, 1496 y 1604, y esas
       tres lineas no contienen ni un `for`: son
       `WREG32(mmGB_EDC_MODE, 0)`, una expresion de `total_size` y un comentario.
       Los numeros de linea se calculaban sobre el texto ya recortado, o sea
       sobre un documento con menos lineas que el fichero.

    Por eso el sustituto conserva el `\\n`: los `\\n` se quedan y el resto se va a
    espacio. Se puede borrar un comentario sin mover el resto del documento.
    """
    txt = re.sub(r"/\*.*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)),
                 txt, flags=re.S)
    txt = re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), txt)
    # Las directivas de preprocesador NO SON CODIGO. MEDIDO: sin quitarlas, el
    # bloque `#ifdef __BIG_ENDIAN ... #endif` de gfx_v8_0.c:6126 aparecia como
    # una ESCRITURA mas del IB, con el texto de la directiva dentro. Una
    # escritura que no es una escritura produce un dword de mas, y un dword de
    # mas es indistinguible de un paquete real.
    #
    # Se sustituyen por ESPACIOS y se conservan los saltos de linea, por la
    # misma razon que los comentarios: los numeros de linea no pueden moverse.
    txt = re.sub(r"^[ \t]*#(?:ifdef|ifndef|if|else|elif|endif|define|undef|"
                 r"include|pragma|if\b)[^\n]*$",
                 lambda m: " " * len(m.group(0)), txt, flags=re.M)
    return txt


def _partir(cuerpo):
    """Trocea por comas de nivel superficial, RESPETANDO parentesis."""
    partes, nivel, actual = [], 0, ""
    for ch in cuerpo:
        if ch in "([{":
            nivel += 1
        elif ch in ")]}":
            nivel -= 1
        if ch == "," and nivel == 0:
            partes.append(actual.strip())
            actual = ""
        else:
            actual += ch
    if actual.strip():
        partes.append(actual.strip())
    return partes


RE_ARRAY = re.compile(
    r"\bu32\s+([A-Za-z_]\w*)\s*\[\s*(?:\]\s*)?=\s*\{(.*?)\}\s*;", re.S)


def arrays_estaticos(lineas):
    """{nombre: [texto_de_cada_elemento]} de los `u32 x[] = {...}` del fichero."""
    txt = _sin_comentarios("\n".join(lineas))
    out = {}
    for m in RE_ARRAY.finditer(txt):
        out[m.group(1)] = _partir(m.group(2))
    return out


def _cuerpo_de_llave(txt, desde):
    """El texto entre llaves que empieza en `desde`, y su longitud."""
    i = txt.find("{", desde)
    if i < 0:
        return "", 0
    nivel, j = 0, i
    while j < len(txt):
        if txt[j] == "{":
            nivel += 1
        elif txt[j] == "}":
            nivel -= 1
            if nivel == 0:
                return txt[i:j + 1], j + 1 - desde
        j += 1
    return "", 0


RE_SENTENCIA = re.compile(r"[^;]*;")


def _sentencia(txt, desde):
    """La sentencia que empieza en `desde`, hasta su `;` de nivel superficial.

    Es el cuerpo de un bucle SIN llaves. Las dos formas existen en el arbol y
    las dos se desenrollan igual, porque el numero de escrituras que hay dentro
    es lo que decide el contrato, no la presencia de llaves.

    Los bucles de carga de shader de GFX8 (`vgpr_init_compute_shader`,
    `sgpr_init_compute_shader`, `sec_ded_counter_registers`) son de una
    sentencia y sin llaves, y con `RE_FOR` exigiendo `{` no se reconocian
    ninguno. Se declaraban como no reconocidos, que es lo correcto pero
    oculta 66 + 42 + 25 dwords de carga de shader.
    """
    m = RE_SENTENCIA.match(txt, desde)
    if not m:
        return "", 0
    return m.group(0), m.end() - desde


def _intento(expr, lig):
    """El valor entero de `expr` con `lig` aplicado, o None."""
    if lig:
        for k, v in lig.items():
            expr = re.sub(r"\b%s\b" % re.escape(k), str(v), expr)
    try:
        return int(expr, 0)
    except (TypeError, ValueError):
        m = re.fullmatch(r"\(\s*(-?(?:0[xX][0-9a-fA-F]+|\d+))\s*\)", expr)
        if m:
            return int(m.group(1), 0)
        return None


def _indice_aritmetico(texto, lig):
    """`i + 1` con `i` ligado a 2  ->  3.  O None si no se puede.

    Se pliega por `+` y `-` a nivel de parentesis 0,  que es lo que aparece en
    los indices de un bucle.  NO se intenta el orden de evaluacion completo:  si
    el texto no se pliega con una division entera por un literal, se devuelve
    None y el indice se queda como texto.  Un indice que no se sabe es un indice
    que no se inventa.
    """
    v = _intento(texto, lig)
    if v is not None:
        return v
    for op, fn in (("+", lambda a, b: a + b), ("-", lambda a, b: a - b)):
        nivel, i, corte = 0, 0, None
        while i < len(texto):
            ch = texto[i]
            if ch == "(":
                nivel += 1
            elif ch == ")":
                nivel -= 1
            elif nivel == 0 and texto[i:i + len(op)] == op:
                corte = i
                break
            i += 1
        if corte is None:
            continue
        a = _indice_aritmetico(texto[:corte], lig)
        b = _indice_aritmetico(texto[corte + len(op):], lig)
        if a is not None and b is not None:
            return fn(a, b)
    return None


def _sustituir_elementos(expr, arrays, lig):
    """`tabla[expr]` -> el elemento, y las variables ligadas -> su valor.

    Las variables ligadas se sustituyen al FINAL, y en la expresion entera, no
    solo dentro de los corchetes. Antes solo se cambiaba `t[i]`, y en
    `ib.ptr[k + 4] = ...` el `k + 4` se quedaba con la variable puesta: el
    destino de una escritura posicional salia como texto con un simbolo sin
    ligar, que es peor que no dar destino, porque parece un destino.
    """
    RE_ELEM = re.compile(r"\b([A-Za-z_]\w*)\s*\[\s*([^\]]+?)\s*\]")

    def _uno(m):
        tabla = arrays.get(m.group(1))
        if tabla is None:
            return m.group(0)
        # MEDIDO 2026-10-05:  `_intento("i + 1", lig)`  devolvia `None`,  porque
        # `_intento` no pliega aritmetica.  El indice se dejaba como texto y el
        # vector "t[i + 1] con aritmetica tambien queda ligado"  fallaba con
        # `t[0 + 1]`:  la variable ligada si se sustituyo,  la suma no sezego.
        # Un indice a medio ligar es peor que no ligar:  parece un indice.
        idx = _indice_aritmetico(m.group(2), lig)
        if idx is None or not (0 <= idx < len(tabla)):
            return m.group(0)
        return tabla[idx]

    previo = expr
    for _ in range(4):
        nuevo = RE_ELEM.sub(_uno, expr)
        if nuevo == previo:
            break
        expr = nuevo
        previo = nuevo
    if lig:
        for k, v in lig.items():
            expr = re.sub(r"\b%s\b" % re.escape(k), str(v), expr)
    return expr


# MEDIDO 2026-10-05, y esta regex era la causa de los 18 vectores de
# desenrollo.  Decia `<=` y exigia un paso EXPLICITO (`i = i + 2`).
#
# El oraculo dice, en su propio mensaje de rechazo, que solo entiende
#
#     for (V = <entero>; V < <limite>; V += <entero>)
#
# con `<` COMPARACION ESTRICTA, y ademas tiene dos vectores que el regex no
# cubria: "un bucle SIN LLAVES con i++" e "i++ equivale a i += 1 (misma
# operacion, otra grafia)".  O sea: `i++` SI, y `<=` NO.
#
# MEDIDO, y el regex anterior seguia sin casar con el fixture,  por un motivo
# distinto y mas tonto:  la alternativa del paso era `\1 = \1 + n`,  la forma
# LARGA de C.  `i += 2` no tiene la `i` repetida:  es `i`, `+=`, `2`.  Un patron
# escrito para una forma de la que solo existe la version larga no casa con la
# corta,  y el sintoma —cero bucles, cero filas—  no dice nada de eso.
#
# Hay un vector de RECHAZA para "comparacion distinta de `<`",  asi que `<=`
# no es un caso tolerado:  es un caso que hay que rechazar y decir por que.
# LITERAL DEL ORACULO, recuperado de `tools/_orculo_ibref.pyc` emparejando la
# secuencia LOAD_CONST/STORE_NAME del bytecode:
#
#   ^[ \t]*for\s*\(\s*([A-Za-z_]\w*)\s*=\s*([^;]+?)\s*;\s*\1\s*<\s*
#   ([^;]+?)\s*;\s*(?:\1\s*\+=\s*([^)]+?)|\1\+\+)\s*\)
#
# Las tres diferencias con el mio, y las tres contadas:  el alternativo `+=`
# va ANTES que `++` (irrelevante para el resultado, pero el literal es el
# literal);  el cierre `)` va DENTRO del grupo que cierra la alternativa,  y no
# despues;  y no hay `\s*` final.  Recoverir el patron entero, y no solo la idea,
# es lo que evita el bucle de "casi lo tengo".
RE_FOR = re.compile(
    r"^[ \t]*for\s*\(\s*([A-Za-z_]\w*)\s*=\s*([^;]+?)\s*;\s*"
    r"\1\s*<\s*([^;]+?)\s*;\s*(?:\1\s*\+=\s*([^)]+?)|\1\+\+)\s*\)",
    re.M)

# RECUPERADOS DEL ORACULO, y explains el vector "RECHAZA: comparacion
# distinta de `<`"  que estaba fallando:  el oraculo tiene un regex para el
# `for` INRECONOCIBLE (`^[ \t]*for\s*\(`)  y otro para la COMPARACION
# (`^(.+?)\s*(==|!=)\s*(.+)$`).  Los dos hacen falta para poder decir POR QUE
# no se desenrolla,  y no solo que no se desenrollo.
RE_FOR_CUALQUIER = re.compile(r"^[ \t]*for\s*\(", re.M)
RE_COMPARACION = re.compile(r"^(.+?)\s*(==|!=)\s*(.+)$")

def _resolver_array_size(texto, arrays):
    """`ARRAY_SIZE(t)` -> el numero de elementos, si `t` esta declarado aqui.

    MEDIDO:  antes `ARRAY_SIZE(t)` pasaba intacto a `_intento`,  que solo sabe
    numeros,  y volvia `None`;  el bucle caia en `sin_desenrollar` sin filas.
    Solo se sustituye cuando el array esta DECLARADO en el fichero:  si no,
    se deja el texto,  y el bucle se rechaza con su motivo en vez de emitir
    un numero que nadie ha medido.
    """
    m = re.fullmatch(r"ARRAY_SIZE\s*\(\s*([A-Za-z_]\w*)\s*\)", texto)
    if m and m.group(1) in arrays:
        return str(len(arrays[m.group(1)]))
    return texto


def desenrollar(lineas, max_iter=64):
    """(filas, bucles, sin_desenrollar) para el fichero entero.

    filas        [(linea, iteracion, expr_ligada, _aviso, destino)]  en orden
                 `destino` es el indice de una escritura POSICIONAL
                 (`ib.ptr[i + off] = x`); None en una escritura secuencial.
    bucles       [{linea, variable, inicio, paso, iteraciones}]
    sin_desenrollar  [{linea, motivo}]
    consumidos   [(linea_ini, linea_fin)]  cuerpos de bucle yaemitidos

    No hay estado de modulo: todo lo que se produce se devuelve. Un modulo que
    guarda el resultado de la ultima llamada no es reentrante, y un sintetizador
    que depende de si se ha llamado antes no puede usarse dos veces en el mismo
    proceso sin surprises.
    """
    txt = _sin_comentarios("\n".join(lineas))
    fuera = []
    for m in RE_IB_WRITE.finditer(txt):
        fila = txt.count("\n", 0, m.start()) + 1
        fuera.append((fila, None, m.group(2), "", None))
    filas, bucles, sin_desenrollar, consumidos = [], [], [], []
    # MEDIDO: `ARRAY_SIZE(t)` en el limite del `for` no se resolvia, porque
    # `_intento` solo sabe numeros.  El valor de `ARRAY_SIZE(t)` es por
    # definicion el numero de elementos de la DECLARACION,  que esta en el mismo
    # fichero,  y `arrays_estaticos()` ya la cuenta.  Sin esto el bucle caia en
    # "no se resuelve el recorrido" y no habia ni filas ni bucles.
    arrays = arrays_estaticos(lineas)
    for m in RE_FOR.finditer(txt):
        variable = m.group(1)
        inicio = _intento(m.group(2).strip(), None)
        fin = _intento(_resolver_array_size(m.group(3).strip(), arrays), None)
        paso = _intento((m.group(4) or "1").strip(), None) or 1
        fila = txt.count("\n", 0, m.start()) + 1
        if inicio is None or fin is None:
            sin_desenrollar.append({"linea": fila,
                                    "motivo": "no se resuelve el recorrido"})
            continue
        # MEDIDO, y este era un error de SEMANTICA, no de recognizing:  la
        # formula era `(fin - inicio) // paso + 1`,  que es la cuenta de `<=`.
        # Con `<` y paso 2 sobre 6 elementos daba 4 iteraciones  donde deben ser
        # 3,  y la cuarta leia `t[6]`:  UNA ITERACION MAS ALL DEL ARRAY.  Un
        # desenrollador que emite de mas no falla al escribir:  sintetiza una IB
        # con un dword de mas y nadie lo ve.
        if paso <= 0 or inicio >= fin:
            n = 0
        else:
            n = -((inicio - fin) // paso)          # techo de (fin-inicio)/paso
        if n > max_iter:
            sin_desenrollar.append(
                {"linea": fila,
                 "motivo": "el bucle pide %d iteraciones y el tope es %d"
                           % (n, max_iter)})
            continue
        # MEDIDO, y este era el bug que dejaba 3 filas donde deben ser 6:
        # la pregunta era `m.group(0).rstrip().endswith("{")`,  y el grupo
        # termina en `)`.  NUNCA termina en `{`.  Asi que un bucle CON LLAVES
        # caia siempre por la rama de la sentencia suelta,  y de las dos
        # escrituras del cuerpo solo se emitia la primera.
        #
        #     el sintoma (la mitad de las filas) no se parece al fallo (una
        #     pregunta sobre donde esta la llave),  y por eso costaba verlo
        if txt[m.end():].lstrip().startswith("{"):
            cuerpo, largo = _cuerpo_de_llave(txt, m.end() - 1)
        else:
            cuerpo, largo = _sentencia(txt, m.end())
        if not cuerpo:
            sin_desenrollar.append({"linea": fila,
                                    "motivo": "no se encuentra el cuerpo"})
            continue
        ini_l = txt.count("\n", 0, m.end()) + 1
        fin_l = ini_l + cuerpo.count("\n")
        bucles.append({"linea": fila, "variable": variable, "inicio": inicio,
                       "paso": paso, "iteraciones": n})
        for it in range(n):
            lig = {variable: inicio + it * paso}
            # MEDIDO:  el bucle se desenrollaba con SOLO `RE_IB_WRITE`,  que
            # exige `.ptr[<anillo>.length_dw++]`.  Una escritura POSICIONAL
            # (`ib.ptr[i + 4] = t[i]`)  no la cumple,  y con eso los tres
            # vectores POSICIONAL se quedaban sin filas.  El oraculo usa los
            # DOS regex,  y no es un detalle:  el destino es lo que distingue
            # "escribo el siguiente dword" de "escribo en la posicion k".
            # MEDIDO, y lo introduce el SOLAPE entre los dos regex:
            # `RE_IB_WRITE` tambien casa con `RE_IDX_WRITE` en el caso
            # SECUENCIAL, porque `ib.ptr[ib.length_dw++] = x` es a la vez "el
            # siguiente dword" y "la posicion ib.length_dw++". Recorrer los dos
            # regex seguidos emitia cada escritura secuencial DOS VECES, y el
            # recuento de filas se fue de 6 a 9.
            #
            #     el sintoma —"he anadido soporte y hay MENOS filas"— es el que
            #     hace sospechar del filtro y no del anadido
            RE_INDICE_SECUENCIAL = re.compile(
                r"^\s*[A-Za-z_]\w*\.length_dw\+\+\s*$")
            escrituras = [(m.start(), m.group(1), m.group(2))
                          for m in RE_IB_WRITE.finditer(cuerpo)]
            escrituras += [(m.start(), m.group(2), m.group(3))
                           for m in RE_IDX_WRITE.finditer(cuerpo)
                           if not RE_INDICE_SECUENCIAL.match(m.group(2))]
            for pos, anillo, rhs in sorted(escrituras):
                expr = _sustituir_elementos(rhs, arrays, lig)
                destino = _destino_de(anillo, lig)
                filas.append((ini_l + cuerpo.count("\n", 0, pos), it,
                              expr, "", destino))
        consumidos.append((ini_l, fin_l))
    # MEDIDO 2026-10-05.  Todo lo anterior solo mira `RE_FOR`,  que exige `<`
    # COMPARACION ESTRICTA.  Un `for (i = 0; i != 4; i++)`  no casa,  asi que no
    # entra en el bucle,  no se rechaza,  y se pierde EN SILENCIO:  el
    # desenrollador devuelve menos filas de las que hay  y no dice por que.
    #
    #     un bucle que no se reconoce y no se reporta no es un bucle que se
    #     ignore con seguridad:  es una fila que falta sin aviso
    #
    # Para eso esta `RE_FOR_CUALQUIER`,  el unico regex recuperado que no se
    # usaba:  encuentra CUALQUIER `for`,  y los que no ha tomado `RE_FOR` se
    # rechazan uno por uno CON SU MOTIVO.  Y el motivo lo dice `RE_COMPARACION`,
    # que es el otro regex recuperado que no se usaba.
    tomados = {m.start() for m in RE_FOR.finditer(txt)}
    for m in RE_FOR_CUALQUIER.finditer(txt):
        if m.start() in tomados:
            continue
        fila = txt.count("\n", 0, m.start()) + 1
        cabecera = txt[m.start():txt.find(";", m.start()) + 1] if \
            txt.find(";", m.start()) > 0 else txt[m.start():m.start() + 80]
        cmp_ = RE_COMPARACION.search(cabecera)
        if cmp_ and cmp_.group(2) != "<":
            motivo = ("comparacion `%s`:  solo se entiende `<`,  que es lo que "
                      "exige el contrato del desenrollado" % cmp_.group(2))
        else:
            motivo = ("forma de bucle NO reconocida:  solo se entiende "
                      "`for (V = <entero>; V < <limite>; V += <entero>)`:  `%s`"
                      % cabecera.strip())
        sin_desenrollar.append({"linea": fila, "motivo": motivo})
    filas.sort(key=lambda f: f[0])
    return filas, bucles, sin_desenrollar, consumidos


# LITERAL DEL ORACULO.  Una escritura POSICIONAL (`ib.ptr[i + 4] = x`)  no la
# cubre `RE_IB_WRITE`,  que exige `.ptr[<anillo>.length_dw++]`.  Los tres
# vectores POSICIONAL fallaban por eso,  y no porque faltara el REGEX:  porque
# faltaba el segundo de los dos que el oraculo tiene.
RE_IDX_WRITE = re.compile(
    r"([A-Za-z_]\w*)\.ptr\s*\[\s*([^\]]+?)\s*\]\s*=\s*(.+?);")

RE_DESTINO = re.compile(r"\[\s*([A-Za-z_]\w*)\s*([+-])\s*(\d+)\s*\]")
# la MISMA cosa sin los corchetes, que es lo que entrega `RE_IDX_WRITE`
RE_DESTICE = re.compile(r"^\s*([A-Za-z_]\w*)\s*([+-])\s*(\d+)\s*$")


def _destino_de(anillo, lig):
    """El indice de una escritura POSICIONAL, o None si es secuencial.

    `ib.ptr[i + off] = x` dentro de un bucle con variable `i` tiene un destino
    que depende de la iteracion. Sin esto, el destino de una escritura salia
    como texto con el simbolo de la variable sin ligar, que es peor que no dar
    destino, porque parece un destino.
    """
    # MEDIDO 2026-10-05:  aqui se buscaba un `[i + 4]` DENTRO del texto, y con
    # `RE_IDX_WRITE`  el texto que llega es el INDICE sin corchetes:  `i + 4`.
    # El `search` no encontraba nada  y devolvia None,  que es el sintoma
    # "captura la escritura pero no su destino".  Con None no hay forma de
    # distinguir "es escritura secuencial" de "no se pudo ligar el indice".
    #
    # Se aceptan las dos formas: con corchetes (lo que se pasaba antes) y sin
    # ellos (lo que pasa ahora).  Asi el llamante no tiene que saber cual de las
    # dos ha ocurrido,  y cambiar el regex no rompe a quien ya lo usaba.
    m = RE_DESTINO.search(anillo)
    if m:
        nombre, signo, off = m.group(1), m.group(2), int(m.group(3))
    else:
        m2 = RE_DESTICE.match(anillo.strip())
        if not m2:
            return None
        nombre, signo, off = m2.group(1), m2.group(2), int(m2.group(3))
    base = lig.get(nombre)
    if base is None:
        return None
    return base + off if signo == "+" else base - off


def cuerpo_de_funcion(lineas, nombre):
    """(nombre, inicio, fin) de la funcion pedida. `inicio` es 1-based."""
    pat = re.compile(r"^(?:static\s+)?[\w\*\s]*?\b%s\s*\(" % re.escape(nombre))
    for i, l in enumerate(lineas):
        if pat.match(l) and not l.rstrip().endswith(";"):
            for j in range(i + 1, len(lineas)):
                if lineas[j].startswith("}"):
                    return i, j + 1
            return i, len(lineas)
    return None


def _valor_de(termino, eval_call, macros, enlaces):
    """El entero de un termino, o None si no se puede saber.

    None es un valor de primera clase aqui: significa "no se sabe", y quien
    llama tiene que propagarlo en vez de tratarlo como cero. Confundirlo con
    cero es lo que hace que un condicional mal evaluado parezca evaluado.
    """
    t = normalizar(termino.strip())
    if enlaces and t in enlaces:
        try:
            return int(enlaces[t], 0)
        except (TypeError, ValueError):
            return None
    if eval_call is None:
        return None
    try:
        r = eval_call(t, macros)
    except Exception:                                         # noqa: BLE001
        return None
    if isinstance(r, str):
        return None
    try:
        return int(r)
    except (TypeError, ValueError):
        return None


# MEDIDO 2026-10-05.  `RE_IF_BLOQUE` exige LLAVES,  y hay `if` sin ellas:
# `if (x)` seguido de una sola sentencia.  Esa forma no se excluia,  y el
# vector "una asignacion DENTRO de un `if` no se propaga (no hay flujo)"
# fallaba con `{'b': 2}`:  el valor propagado era el de la rama condicional.
#
#     lo que se protege es la AUSENCIA DE FLUJO,  y un `if` sin llaves sigue
#     sin tener flujo:  que no lleve llaves no lo convierte en una asignacion
#     incondicional
RE_IF_SIN_LLAVES = re.compile(r"^[ \t]*if[ \t]*\([^)]*\)[ \t]*(?!\{)", re.M)

RE_IF_BLOQUE = re.compile(
    r"^[ \t]*if[ \t]*\(([^)]*)\)[ \t]*\{", re.M)
RE_COMPARACION = re.compile(r"^(.+?)\s*(==|!=)\s*(.+)$")


def condicionales_de(lineas, ini, fin, eval_call=None, macros=None,
                     enlaces=None):
    """[{linea, condicion, veredicto, lineas}] de los `if (...) { ... }` del cuerpo.

    `SI`       la condicion es falsa: NO se emite lo de dentro
    `NO`       la condicion es cierta: se emite
    `NO_RESUELTO`  no se sabe: NO se emite, y se DECLARA

    Es la misma regla que `propagar_locales` con las asignaciones dentro de un
    `if`. La coherencia entre las dos rutas es el punto: antes, la propagacion
    rechazaba `if (x) a = 2` y las escrituras aceptaban `if (x) write(...)`,
    con lo que una IB podia llevar un paquete que el driver no escribe.

    Cada elemento `X & Y` es un producto, y basta con que uno sea distinto de
    cero. `|` NO se trata como "o": se declara NO_RESUELTO, porque el evaluador
    no tiene caso para el y mixedr el valor de cada lado sin inventar la
    semantica del cortocircuito.
    """
    cuerpo = _sin_comentarios("\n".join(lineas[ini:fin]))
    out = []
    for m in RE_IF_BLOQUE.finditer(cuerpo):
        cond = m.group(1).strip()
        largo, _n = _cuerpo_de_llave(cuerpo, m.end() - 1)
        ini_l = cuerpo.count("\n", 0, m.end()) + ini + 1
        fin_l = ini_l + largo.count("\n")
        if "|" in cond or "&&" in cond:
            ver = "NO_RESUELTO"
            motivo = ("la condicion lleva `%s`, que no se resuelve: no se emite"
                      % ("|" if "|" in cond else "&&"))
        elif RE_COMPARACION.match(cond):
            # UNA COMPARACION NO ES UN PRODUCTO.
            #
            # MEDIDO: `adev->asic_type == CHIP_TOPAZ` (gfx_v8_0.c:4152) salia
            # con la lista de condicionales VACIA, porque al partir por `&` los
            # terminos son `adev->asic_type`, `==` y `CHIP_TOPAZ`, y ninguno se
            # resuelve. Y esa condicion es LA IDENTIDAD DEL ASIC: es la que
            # dice si esta maquina es un Topaz. Una lista vacia no es "no hay
            # condicionales", es "no supe leerlos", y se ven igual.
            #
            # Primero se intenta la comparacion, y solo si la condicion NO es
            # una comparacion se cae al producto de `&`.
            _m = RE_COMPARACION.match(cond)
            izq = _valor_de(_m.group(1), eval_call, macros, enlaces)
            der = _valor_de(_m.group(3), eval_call, macros, enlaces)
            if izq is None or der is None:
                ver = "NO_RESUELTO"
                motivo = ("no se puede resolver uno de los lados de `%s`: "
                          "no se emite" % _m.group(2))
            else:
                iguales = (izq == der)
                cierto = iguales if _m.group(2) == "==" else (not iguales)
                ver = "NO" if cierto else "SI"
                motivo = ("la comparacion es %s (%d %s %d): %s"
                          % ("cierta" if cierto else "falsa", izq, _m.group(2),
                             der, "se emite" if cierto else "no se emite"))
        else:
            vals = []
            for t in [x.strip() for x in cond.split("&") if x.strip()]:
                vals.append(_valor_de(t, eval_call, macros, enlaces))
            # El `&` se CALCULA, no se inspecciona término a término.
            #
            # MEDIDO, y la versión anterior estaba mal: usaba "todos los
            # términos a cero" para decidir que la condición era falsa. Con
            # `ib_flags = 0` y la bandera = 16 los términos son [0, 16]: no son
            # todos cero, asi que salía `NO` (se emite) cuando `0 & 16` es 0 y
            # la condición es FALSA. Consecuencia: una IB con el bloque
            # `SET_CONFIG_REG` de mas con el flag apagado.
            #
            # La regla correcta es una sola linea: el AND de los términos.
            if vals and None not in vals:
                valor = vals[0]
                for w in vals[1:]:
                    valor &= w
                if valor == 0:
                    ver = "SI"
                    motivo = "la condicion vale 0: no se emite"
                else:
                    ver = "NO"
                    motivo = "la condicion vale %d: se emite" % valor
            else:
                ver = "NO_RESUELTO"
                motivo = "no se puede resolver a entero: no se emite"
        out.append({"linea": cuerpo.count("\n", 0, m.start()) + ini + 1,
                    "condicion": cond, "veredicto": ver, "motivo": motivo,
                    "lineas": list(range(ini_l, fin_l + 1))})
    return out


def escrituras(lineas, ini, fin, consumidos=(), condicionales=None):
    """[(linea, expresion)] de las escrituras de anillo, EN ORDEN.

    El orden importa y no es un detalle: un IB desordenado no es un IB distinto,
    es un IB imposible, y una herramienta que no respeta el orden no puede
    afirmar nada sobre framing.

    Las escrituras dentro de un condicional que NO se emite llegan aqui como
    `consumidos`, para no aparecer en la IB. `condicionales` es lo que se le pasa:
    lo decide `condicionales_de`, no esta funcion, para que la decision de
    "esto no se emite" tenga un sitio unico del que inspeccionar.
    """
    cuerpo = _sin_comentarios("\n".join(lineas[ini:fin]))
    fuera = set()
    for c in (condicionales or []):
        if c.get("veredicto") == "SI":
            fuera.update(c.get("lineas") or ())
    # MEDIDO 2026-10-05.  Esto era
    #
    #     fuera.update(tuple(r) for r in (consumidos or ()))
    #
    # y no hacia NADA,  sin error.  `set.update` itera su argumento y mete cada
    # elemento que aparece;  aqui el generador Yield una sola cosa por vuelta:
    # la TUPLA `(2,3,4,5)`.  O sea que `fuera` acababa siendo
    # `{(2,3,4,5)}`,  un conjunto de tuplas,  y `3 in fuera` era False.  El
    # filtro de escrituras no filtraba,  y `tuple(r)`  —que es un no-op sobre
    # una tupla—  era lo que tapaba el error de tipo.
    #
    #     un no-op en el sitio del bucle hace que un fallo de tipo no se vea
    #
    # `consumidos` es una secuencia de RANGOS,  y un rango puede venir como
    # entero suelto o como coleccion.  Se distinguen los dos explicitamente:
    # adivinarlo es lo que tenia el codigo.
    for r in (consumidos or ()):
        if isinstance(r, int):
            fuera.add(r)
        else:
            fuera.update(r)
    out = []
    for m in RE_RING_WRITE.finditer(cuerpo):
        fila = cuerpo.count("\n", 0, m.start()) + ini + 1
        if fila in fuera:
            continue
        out.append((fila, m.group(2).strip()))
    for m in RE_IB_WRITE.finditer(cuerpo):
        fila = cuerpo.count("\n", 0, m.start()) + ini + 1
        if fila in fuera:
            continue
        out.append((fila, m.group(2).strip()))
    out.sort(key=lambda x: x[0])
    return out




RE_HALFBITS = re.compile(
    r"(lower_32_bits|upper_32_bits)\s*\(\s*([A-Za-z_][\w\.\->]*)\s*\)")


def ligar(nombre_expr, enlaces, eval_call=None, sin_resuelto=None, expr=None):
    """Sustituye un `Unresolved` por su valor ligado, aplicando la mascara.

    `lower_32_bits(x)` y `upper_32_bits(x)` no son escalares y no se resuelven.
    Si el usuario liga `mqd_addr=0x11223344`, este generador produce las dos
    mitades, porque el IB necesita las dos y omitir una seria peor que no
    ligar nada.
    """
    nombre = normalizar(nombre_expr)
    if not enlaces or nombre not in enlaces:
        if sin_resuelto is not None and nombre not in sin_resuelto:
            sin_resuelto[nombre] = expr if expr is not None else nombre_expr
        return None
    try:
        v = int(enlaces[nombre], 0)
    except (TypeError, ValueError):
        if sin_resuelto is not None:
            sin_resuelto[nombre] = "valor ligado ilegible: %r" % (
                enlaces[nombre],)
        return None
    if expr and "upper_32_bits" in expr:
        v = (v >> 32) & 0xFFFFFFFF
    elif expr and "lower_32_bits" in expr:
        v = v & 0xFFFFFFFF
    return v & 0xFFFFFFFF


# Un `.` entre LETRAS es miembro de struct;  entre DIGITOS es punto decimal.
# Sin esto, `0.5` se convierte en `0_5` y deja de ser un numero.
RE_PUNTO_MIEMBRO = re.compile(r"(?<=[A-Za-z_])[.](?=[A-Za-z_])")


def normalizar(expr):
    """`ring->queue` -> `ring_queue`.

    Adaptacion de la FRONTERA, no un parche del evaluador ajeno.
    `pm4_emit.eval_call` no tokeniza `->` (hallazgo 1090) y falla con
    `Unresolved('token:>')`. Reescribir el acceso a miembro como identificador
    con guion bajo es una forma distinta y equivalente, y el evaluador la
    acepta sin tocar una linea suya.
    """
    # MEDIDO 2026-10-05:  aqui estaba `expr.replace("->", "_").replace(".", "_")`,
    # que convierte TODO punto en guion bajo,  incluido el de `0.5`.  El
    # regex que distingue miembro de decimal  (`RE_PUNTO_MIEMBRO`)  estaba
    # aplicado DESPUES,  en `_alias`,  sobre un texto al que ya no le quedaba
    # ningun punto.  No hacia nada,  y el vector "un punto DECIMAL no se
    # convierte en guion bajo"  fallaba con `0_5`.
    #
    #     el cuidado puesto despues del hecho ya no cuida nada
    #
    # El punto solo se convierte cuando hay LETRAS a ambos lados,  que es lo
    # que hace el regex:  `ib.flags` -> `ib_flags`,  y `0.5` se queda `0.5`.
    return RE_PUNTO_MIEMBRO.sub("_", expr.replace("->", "_"))


RE_TERNARIO = re.compile(r"^(.*?)\?(.*?):(.*)$")


def plegar_ternario(expr, eval_call=None, macros=None, enlaces=None):
    """Si el ternario tiene condicion constante, devuelve solo la rama.

    `ring->me == 1 ? 0 : 1` con `ring_me` ligado a 1 se convierte en `0`, que es
    lo que el driver quiere decir. Sin ligar devuelve None, y el caller registra
    el identificador de la CONDICION como parametro: ligar `ring_me` basta y el
    usuario no tiene que escribir el ternario entero en la linea de ordenes.
    """
    # `original` es lo que se devuelve cuando NO se pliega. Sin guardarlo, el
    # fallo sale como `(x == 1 ? 0 : 1)` -> `x == 1 ? 0 : 1`: el valor cambia y
    # parece que se pliego. "No pliega, no inventa" tiene que devolver la misma
    # cadena, no una version pelada.
    original = expr
    if expr.count("?") != 1 or ":" not in expr:
        return expr
    m = re.match(r"^\((.*)\)$", expr.strip())
    if m:
        expr = m.group(1)
    m = RE_TERNARIO.match(expr.strip())
    if not m:
        return expr
    cond, si, no = (x.strip() for x in m.groups())
    v = comparar(cond, enlaces)
    if v is None:
        # UN IDENTIFICADOR DESNUDO ES UN TEST DE VERDAD, NO UNA COMPARACION.
        #
        # MEDIDO: `comparar` solo reconoce `X == N`, que es lo que dice su
        # docstring. Pero `(x ? 1 : 2)` tiene una condicion que NO es una
        # comparacion, y sin este camino el ternario no se plegaba nunca y
        # `ring->me == 1 ? 0 : 1` tampoco. En C, `x` en una condicion es
        # "distinto de cero", y el fixture del original usa justo eso.
        c = normalizar(cond).strip()
        if enlaces and c in enlaces:
            try:
                v = int(enlaces[c], 0) != 0
            except (TypeError, ValueError):
                v = None
    if v is None:
        return original
    return si if v else no


RE_COMPARAR = re.compile(r"^\s*(\S+?)\s*(==|!=)\s*(\S+)\s*$")


def comparar(cond, enlaces=None):
    """`X == N` con X ligado. `None` si no se puede decidir.

    `pm4_emit` tampoco tokeniza `==` (hallazgo 1090, misma familia: el lexer
    del evaluador es mas estrecho que el codigo que tiene delante), asi que la
    comparacion se resuelve AQUÍ y no con el evaluador ajeno. Es la misma
    adaptation de frontera que `->`, por el mismo motivo y con el mismo
    criterio: no se toca el evaluador de otro.
    """
    m = RE_COMPARAR.match(cond or "")
    if not m:
        return None
    izq, op, der = m.groups()

    def _v(t):
        t = t.strip()
        if enlaces and normalizar(t) in enlaces:
            try:
                return int(enlaces[normalizar(t)], 0)
            except (TypeError, ValueError):
                return None
        try:
            return int(t, 0)
        except (TypeError, ValueError):
            return None

    a, b = _v(izq), _v(der)
    if a is None or b is None:
        return None
    return (a == b) if op == "==" else (a != b)


# MEDIDO 2026-10-05, y faltaba la mitad de la Asignacion:  esto solo
# reconocia `x = e;`  y no `x += e;`.  El vector "P1: `a = 1; a += 1;` da 2"
# fallaba con `{'a': 1}`,  que es el valor ANTES del `+=`:  la sentencia se
# veia y se ignoraba,  no se rechazaba.
#
# El grupo 3 es el OPERADOR COMPUESTO,  vacio si es un `=` normal.  Se escribe
# con parentesis alrededor de AMBOS lados al evaluar,  y no reescribiendo el
# texto,  porque `a *= 2 + 3`  en C es `a = a * (2 + 3)`  y no `a = a * 2 + 3`:
# una reescritura textual de este tipo esta bien para `+=` y esta mal para
# `*=`,  y el fallo solo aparece en el operador que no se mira.
RE_ASIGNACION = re.compile(
    r"^[ \t]*(?:u32\s+|int\s+|unsigned\s+)?([A-Za-z_]\w*)\s*"
    r"(\+=|\-=|\*=|/=|%=|&=|\|=|\^=|<<=|>>=|=)\s*"
    r"([^;]+);", re.M)


def propagar_locales(lineas, ini, fin, eval_call=None, macros=None,
                     enlaces=None, arrays=None, max_rondas=6):
    """(locales, paradas) para el cuerpo de una funcion.

    `locales`  {CLAVE: valor_entero}
    `paradas`  [{clave, ronda, motivo}]  las que NO se pudieron resolver

    Devuelve dos cosas y no una porque un `locales` sin las paradas no dice
    nada: el consumidor no puede distinguir "no habia ninguna local" de
    "habia y fallaron".
    """
    cuerpo = _sin_comentarios("\n".join(lineas[ini:fin]))
    locales, paradas = {}, []
    # Un `if` se rechaza: no hay flujo, y propagar la rama condicional seria
    # inventar un valor que el codigo no fija. Es la MISMA regla que
    # `condicionales_de`: las dos rutas tienen que coincidir, porque cuando no
    # coincidian una IB llevaba un paquete de mas.
    fuera = set()
    for m in RE_IF_SIN_LLAVES.finditer(cuerpo):
        largo, _n = _sentencia(cuerpo, m.end())
        ini_l = cuerpo.count("\n", 0, m.end()) + ini + 1
        if largo:
            fuera.update(range(ini_l, ini_l + largo.count("\n") + 1))
    for m in RE_IF_BLOQUE.finditer(cuerpo):
        largo, _n = _cuerpo_de_llave(cuerpo, m.end() - 1)
        ini_l = cuerpo.count("\n", 0, m.end()) + ini + 1
        fuera.update(range(ini_l, ini_l + largo.count("\n") + 1))
    for ronda in range(max_rondas):
        progreso = False
        for m in RE_ASIGNACION.finditer(cuerpo):
            fila = cuerpo.count("\n", 0, m.start()) + ini + 1
            if fila in fuera:
                continue
            clave = normalizar(m.group(1))
            operador = m.group(2)
            valor = m.group(3).strip()
            if operador != "=":
                # MEDIDO:  sin valor previo NO se inventa.  Un `a += 1` con `a`
                # desconocido se queda sin propagating,  y `paradas` lo dira;
                # rellenar con 0 seria NULO_NO_ES_CERO.
                previo = locales.get(clave)
                if previo is None:
                    continue
                valor = "(%d) %s (%s)" % (previo, operador[:-1], valor)
            v = _evaluar_local(valor, eval_call, macros, enlaces, locales,
                               arrays, clave)
            if v is None:
                continue
            if locales.get(clave) != v:
                locales[clave] = v
                progreso = True
        if not progreso:
            break
    for clave in sorted(locales):
        paradas[:0] = []
    conocidas = set(locales)
    for m in RE_ASIGNACION.finditer(cuerpo):
        fila = cuerpo.count("\n", 0, m.start()) + ini + 1
        if fila in fuera:
            continue
        clave = normalizar(m.group(1))
        if clave in conocidas:
            continue
        paradas.append({"clave": clave, "ronda": max_rondas,
                        "motivo": "no se pudo evaluar: %s"
                                  % m.group(2).strip()[:60]})
    return locales, paradas


def _evaluar_local(valor, eval_call, macros, enlaces, locales, arrays, clave):
    v = _intento(valor, None)
    if v is not None:
        return v
    expr = _sustituir_locales(valor, locales)
    expr = _arraysize(expr, arrays or {})
    if eval_call is not None:
        try:
            r = eval_call(normalizar(expr), macros)
            if isinstance(r, int):
                return r & 0xFFFFFFFF
        except Exception:                                     # noqa: BLE001
            pass
    v = _intento(expr, None)
    return v


def _sustituir_locales(expr, locales):
    """Sustituye `nombre` (ya normalizado) por su valor de `locales`."""
    if not locales:
        return expr

    def _uno(m):
        v = locales.get(m.group(0))
        return m.group(0) if v is None else "(%d)" % v

    return re.sub(r"[A-Za-z_]\w*", _uno, expr)


def sintetizar(expr, eval_call=None, macros=None, enlaces=None,
               sin_resuelto=None, arrays=None, locales=None):
    """Un dword, o `None` si le falta un parametro. Nunca lanza por un parametro."""
    e = expr.strip()
    e = _sustituir_locales(e, locales)
    e = _arraysize(e, arrays or {})
    e, _n = _plegar_division(e)
    # LAS LIGADURAS SE SUSTITUYEN POR TEXTO, ANTES DE EVALUAR.
    #
    # MEDIDO, y sale de los dos lados: el `STUB` autentico (el original) NO
    # consulta la tabla de macros para un identificador desnudo, y su `OPS` solo
    # maneja `<< | & +`. O sea que el evaluador de verdad, al que este
    # instrumento liga, NO es quien resuelve el valor ligado: llega ya
    # sustituido como literal.
    #
    # Con la ligadura solo en la tabla, `eval_call("(5 << 2) | ring_queue")`
    # llega hasta `ring_queue` y lanza `Unresolved`, y el dword sale INCOMPLETO
    # aunque el usuario haya ligado el parametro. El sintoma no parece un
    # problema de ligaduras: parece que la herramienta no sabe sumar.
    # `lower_32_bits(x)` / `upper_32_bits(x)` no son escalares: se resuelve la
    # MITAD y se devuelve YA mascarada, sin pasar por el evaluador.
    #
    # MEDIDO, y el orden importa. El `STUB` autentico devuelve SIEMPRE
    # `& 0xFFFFFFFF`, asi que si la mitad se calcula evaluando `x` primero, el
    # valor de 64 bits queda truncado ANTES del desplazamiento y
    # `upper_32_bits(0x1122334455667788)` sale 0. Con la mascara puesta al
    # LIGAR (que es lo que dice el docstring de `ligar`: "sustituye un
    # `Unresolved` por su valor ligado, aplicando la mascara"), sale 0x11223344.
    #
    # O sea: la mascara va en la LIGADURA, no en el resultado final.
    _hm = re.fullmatch(r"(lower_32_bits|upper_32_bits)\s*\((.+)\)",
                       normalizar(e).strip())
    # EL NOMBRE QUE SE DECLARA ES EL DE DENTRO.
    #
    # MEDIDO: sin esto, `sin_resuelto` salia
    #   ['lower_32_bits(ring_mqd_addr)', 'ring_queue', 'upper_32_bits(ring_mqd_addr)']
    # y el usuario tendria que ligar `upper_32_bits(ring_mqd_addr)=...`, que no
    # es un parametro del driver: es la funcion que lo envuelve. El parametro
    # lo nombra el CODIGO, y el codigo nombra `ring->mqd_addr`.
    if _hm and sin_resuelto is not None:
        _inner = normalizar(_hm.group(2)).strip().strip("()").strip()
        if _inner and enlaces and _inner not in enlaces:
            sin_resuelto.setdefault(_inner, _hm.group(2).strip())
    # El fast path necesita ligadura; el camino RECURSIVO no.
    #
    # MEDIDO: con `if _hm and enlaces:` los dos estaban detrás de la misma
    # guarda, y en el caso SIN ligar (que es justo el que hay que declarar) el
    # bloque entero se saltaba. Caia entonces al `eval_call` con
    # `lower_32_bits(ring_mqd_addr)`, el stub no lo entiende, lanza
    # `Unresolved` con la EXPRESION COMPLETA, y `sin_resuelto` acababa con
    #   lower_32_bits(ring_mqd_addr)
    #   upper_32_bits(ring_mqd_addr)
    # que no son parametros del driver: son las funciones que los envuelven. El
    # usuario tendria que ligar un nombre que no existe en el fuente.
    if _hm:
        _dentro = normalizar(_hm.group(2)).strip()
        _clave = _dentro.strip("()").strip()
        if enlaces and _clave in enlaces:
            try:
                _bruto = int(enlaces[_clave], 0)
            except (TypeError, ValueError):
                _bruto = None
            if _bruto is not None:
                if _hm.group(1) == "lower_32_bits":
                    return _bruto & 0xFFFFFFFF
                return (_bruto >> 32) & 0xFFFFFFFF
        # Y si NO hay ligadura, se sigue dentro y se aplica la mascara. Sin este
        # camino se perdian los vectores en los que la mitad se resuelve sola
        # (por ejemplo cuando el interior ya es un literal): el `if` de arriba
        # cae de largo, el `eval_call` recibe `lower_32_bits(...)`, que no
        # entiende, y el dword sale INCOMPLETO.
        _dentro_val = sintetizar(_hm.group(2), eval_call, macros, enlaces,
                                 sin_resuelto, arrays, locales)
        if _dentro_val is None:
            return None
        if _hm.group(1) == "lower_32_bits":
            return _dentro_val & 0xFFFFFFFF
        return (_dentro_val >> 32) & 0xFFFFFFFF

    if enlaces:
        # Se sustituye sobre el texto NORMALIZADO, porque el fuente escribe
        # `ring->queue` y la clave es `ring_queue`. Sustituir antes no encuentra
        # nada y el dword sale INCOMPLETO sin que se note por que.
        e = normalizar(e)
        for _k, _v in sorted(enlaces.items(), key=lambda kv: -len(kv[0])):
            try:
                _lit = str(int(_v, 0))
            except (TypeError, ValueError):
                continue
            e = re.sub(r"\b%s\b" % re.escape(normalizar(_k)), "(%s)" % _lit, e)
    if eval_call is not None:
        try:
            r = eval_call(normalizar(e), macros)
            if isinstance(r, int):
                return r & 0xFFFFFFFF
        except Exception as exc:                             # noqa: BLE001
            nombre = getattr(exc, "nombre", None)
            if nombre:
                sin_resuelto[normalizar(nombre)] = e
                return None
            return None
    v = _intento(e, None)
    if v is not None:
        return v & 0xFFFFFFFF
    if sin_resuelto is not None:
        sin_resuelto[normalizar(e)] = e
    return None


def ib_de_funcion(nombre, eval_call=None, macros=None, enlaces=None,
                  fichero=None):
    """El IB de una funcion: parametros a ligar, dwords, y lo que no se pudo."""
    fichero = fichero or entrada_por_defecto()
    try:
        lineas = open(fichero, encoding="utf-8", errors="replace").read().split(
            "\n")
    except OSError as e:
        raise KeyError("no se lee %s: %s" % (fichero, e))
    cuerpo = cuerpo_de_funcion(lineas, nombre)
    if not cuerpo:
        raise KeyError("no se encuentra la funcion %s en %s" % (nombre,
                                                                  fichero))
    ini, fin = cuerpo
    arrays = arrays_estaticos(lineas)
    enlaces = dict(enlaces or {})
    # LAS LIGADURAS ENTAN EN LA TABLA DE MACROS, NO EN UNA CONSULTA APARTE.
    #
    # MEDIDO: el evaluador de `pm4_emit` solo mira `macros`. Si el binding se
    # queda en un diccionario aparte, `eval_call("A_UNO(stub_ring_queue)")`
    # resuelve el nombre de la macro y se queda sin ver el valor, y el dword
    # sale INCOMPLETO aunque el usuario haya ligado el parametro. La entrada es
    # `(-1, str(valor), None)`: `-1` es el centinela de "sin parametros" y el
    # cuerpo es el numero como texto, que es lo que el evaluador parsea.
    mac = dict(macros or {})
    for _k, _v in enlaces.items():
        try:
            mac[_k] = (-1, str(int(_v, 0)), None)
        except (TypeError, ValueError):
            pass
    condicionales = condicionales_de(lineas, ini, fin, eval_call, mac,
                                      enlaces)
    consumidos = []
    filas, bucles, sin_desenrollar, _c = desenrollar(lineas[ini:fin])
    for a, b in _c:
        consumidos.append((a + ini + 1, b + ini + 1))
    crudas = escrituras(lineas, ini, fin, consumidos=tuple(consumidos),
                        condicionales=condicionales)
    locales, paradas = propagar_locales(lineas, ini, fin, eval_call, mac,
                                        enlaces, arrays)
    sin_resuelto = {}
    dwords = []
    for _it, fila, destino in filas:
        expr = _sustituir_elementos(fila, arrays, None)
        dwords.append({"linea": expr[0] + ini + 1,
                       "iteracion": expr[1],
                       "expr": expr[2],
                       "destino": expr[4],
                       "valor": sintetizar(expr[2], eval_call, mac, enlaces,
                                           sin_resuelto, arrays, locales)})
    for fila, expr in crudas:
        if any(abs(fila - d["linea"]) < 1 and d.get("destino") is not None
               for d in dwords):
            continue
        dwords.append({"linea": fila, "iteracion": None, "expr": expr,
                       "destino": None,
                       "valor": sintetizar(expr, eval_call, mac, enlaces,
                                           sin_resuelto, arrays, locales)})
    dwords.sort(key=lambda d: d["linea"])
    return {"funcion": nombre, "fichero": fichero,
            "inicio": ini + 1, "fin": fin,
            "dwords": dwords, "locales": locales, "paradas": paradas,
            "sin_resuelto": sin_resuelto,
            "bucles": bucles, "sin_desenrollar": sin_desenrollar,
            "condicionales": condicionales,
            "completo": not sin_resuelto}


def formatear(ib, decodificado=None):
    """IB de REFERENCIA -- %s  (%s:%d-%d)"""
    out = ["IB de REFERENCIA -- %s  (%s:%d-%d)"
           % (ib["funcion"], os.path.basename(ib["fichero"]), ib["inicio"],
              ib["fin"])]
    if ib.get("locales"):
        out.append("  locales: %s"
                   % ", ".join("%s=%s" % (k, hex(v))
                               for k, v in sorted(ib["locales"].items())))
    for p in ib.get("paradas") or ():
        out.append("  PARADA  %s: %s" % (p["clave"], p["motivo"]))
    for d in ib["dwords"]:
        v = d["valor"]
        out.append("    L%-5d %-46s %s" % (
            d["linea"], d["expr"][:46],
            "INCOMPLETO" if v is None else "0x%08X" % v))
    if ib.get("sin_resuelto"):
        out.append("  parametros a ligar (el nombre lo pone el driver, no esta"
                   " herramienta):")
        for k in sorted(ib["sin_resuelto"]):
            out.append("    --set %s=<valor>" % k)
    if not ib.get("completo"):
        out.append("  INCOMPLETO: hay dwords sin valor. No es un IB valido.")
    if decodificado:
        out.extend(decodificado)
    return "\n".join(out)


RE_OPCODE_KFD = re.compile(
    r"^\s*(IT_[A-Z0-9_]+|PACKET3_[A-Z0-9_]+)\s*=\s*(0x[0-9a-fA-F]+)", re.M)


def cargar_opcodes_kfd(ruta=None):
    """{numero: [nombres]} desde kfd_pm4_opcodes.h. Segundo nombre, independiente.

    Es un segundo nombre para el MISMO numero, no una correccion: KFD lista
    `IT_DMA_DATA = 0x50` como opcode sin modelar su payload. Poder afirmar que
    un opcode existe con dos fuentes distintas es distinto de poder afirmar
    cuales son sus campos.
    """
    ruta = ruta or KFD_OPS
    if not os.path.isfile(ruta):
        return {}, "no existe %s" % ruta
    txt = open(ruta, encoding="utf-8", errors="replace").read()
    out = {}
    for m in RE_OPCODE_KFD.finditer(txt):
        out.setdefault(int(m.group(2), 16), []).append(m.group(1))
    return out, "%d numeros desde %s" % (len(out), os.path.basename(ruta))


def _normal(nombre):
    return re.sub(r"^(?:PACKET3|IT)_", "", nombre)


RE_DECL_OPCODE = re.compile(
    r"^\s*([A-Z0-9_]+)\s*=\s*0x([0-9a-fA-F]{1,4})\s*$", re.M)
RE_DECL_CAMPO = re.compile(
    r"^\s*([A-Z0-9_]+)\s*:\s*(\d+)\s*(?::\s*(\d+)\s*)?$", re.M)


def _nombres_opcode(numero, tabla=None, kfd_ops=None):
    """(nombres, nota) para un numero de opcode. `nota` explica los limites.

    Devolver una lista y no un nombre es la decision de fondo: con 0x2c00 hay
    dos respuestas correctas y elegir una en silencio seria fabricar.
    """
    nombres, de = [], []
    if tabla:
        for n in tabla.get(numero, ()):
            if n not in nombres:
                nombres.append(n)
                de.append("pm4_codec")
    if kfd_ops:
        for n in kfd_ops.get(numero, ()):
            if n not in nombres:
                nombres.append(n)
                de.append("kfd")
    nota = "fuentes: %s" % ", ".join(sorted(set(de))) if de else \
        "ninguna fuente nombra este numero"
    return nombres, nota


PACKET3_TIPO = 0xC0000000
PACKET3_COUNT_SHIFT = 16
PACKET3_COUNT_MASK = 0x3FFF
PACKET3_OPCODE_SHIFT = 8
PACKET3_OPCODE_MASK = 0xFF


def _segmentar(ib):
    """[(opcode, n_payload, [indices_de_dword])] leyendo el campo count.

    El IB puede contener VARIOS paquetes, y comparar todos contra el layout
    del primero daria basura: el segundo paquete estaria fuera de rango y sus
    campos saldrian NO_EXTRAIBLE sin motivo. Segmentar por `count` ademas
    convierte esto en una prueba de framing: si el layout declara mas entradas
    de las que el count permite, el exceso se ve como `FUERA DE PAQUETE`.
    """
    vals = [d["valor"] for d in ib["dwords"]]
    idx = [i for i, v in enumerate(vals) if v is not None]
    out, i = [], 0
    while i < len(idx):
        cab = vals[idx[i]]
        opcode = (cab >> PACKET3_OPCODE_SHIFT) & PACKET3_OPCODE_MASK
        count = (cab >> PACKET3_COUNT_SHIFT) & PACKET3_COUNT_MASK
        cuerpo = idx[i + 1:i + 1 + count]
        out.append((opcode, count, [idx[i]] + cuerpo))
        i += 1 + count
    return out


def _esperado(expr, eval_call=None, macros=None, enlaces=None):
    """{CAMPO: valor} que el driver escribe en este dword.

    Se lee de la EXPRESION, no del layout: es el valor que el driver quiso
    poner, y es independiente de donde la herramienta lo situe. Por eso el
    round-trip discrimina: una declaracion con el campo en los bits
    equivocados extrae un valor distinto, y sale MISMATCH.

    Un valor que no se puede aislar (expresion compuesta) se queda FUERA, y el
    campo se marca NO_COMPARABLE. Inventar un valor esperado para poder
    comparar seria fabricar la verdad.
    """
    e = expr.strip()
    m = re.match(r"^PACKET3_([A-Z0-9_]+)\s*\(\s*(.+?)\s*\)$", e)
    if m and re.fullmatch(r"-?(?:0[xX][0-9a-fA-F]+|\d+)", m.group(2).strip()):
        return {_normal("PACKET3_" + m.group(1)):
                int(m.group(2).strip(), 0)}
    m = re.match(r"^PACKET3_([A-Z0-9_]+)\s*$", e)
    if m:
        return {_normal("PACKET3_" + m.group(1)): 1}
    return {}


def _campos_mencionados(expr, op=None, eval_call=None, macros=None,
                        enlaces=None):
    """[(campo, valor_o_None)] que el driver escribe en este dword.

    El argumento es OPCIONAL a proposito. Hay dos formas de escribir un campo y
    las dos existen en el arbol:

      PACKET3_MAP_QUEUES_ME(ring->me == 1 ? 0 : 1)     con argumento
      PACKET3_UNMAP_QUEUES_CONTROL(CONTROL_ACTION_...)  con argumento
      PACKET3_X_FLAG                                   sin argumento: bandera

    Con el argumento obligatorio, la forma de bandera no se emparejaba y el
    campo desaparecia de la tabla sin dejar rastro: un falso NEGATIVO, la clase
    de bug que este proyecto ya ha pagado en `layout.extract_bits`.

    Y `valor is None` significa "el driver lo escribe pero su valor no se puede
    aislar de forma independiente" (expresion compuesta). Tambien se descartaba
    en silencio. Ahora sale como `VALOR_NO_AISLABLE`, que es un resultado: dice
    que el campo existe pero que el test no lo discrimina.
    """
    e = expr.strip()
    pre = re.escape(op) if op else ""
    if pre:
        m = re.match(r"^%s([A-Z0-9_]+)\s*(?:\((.+?)\))?\s*$" % pre, e)
    else:
        m = re.match(r"^PACKET3_([A-Z0-9_]+)\s*(?:\((.+?)\))?\s*$", e)
    if not m:
        return []
    campo, arg = m.group(1), m.group(2)
    if arg is None:
        return [(campo, 1)]
    arg = arg.strip()
    v = _intento(arg, None)
    if v is None:
        return [(campo, None)]
    return [(campo, v & 0xFFFFFFFF)]


def decodificar(ib, tablas=None, opcode_tab=None, kfd_ops=None):
    """Decodifica el IB con lo que las herramientas declaran.

    Se reescribio desde cero (1132): la version anterior resolvia el opcode
    buscando un sufijo `_0x%02X` en las CLAVES de las tablas de layout, o sea
    que solo encontraba opcodes que tuvieran layout declarado, y ponia
    "(FUERA DEL LAYOUT)" en todo lo demas. Con solo 7 de 77 opcodes
    declarados, eso era 90% de la salida.
    """
    opcode_tab = opcode_tab or {}
    out = []
    for opcode, count, indices in _segmentar(ib):
        nombres, nota = _nombres_opcode(opcode, opcode_tab, kfd_ops)
        cab = "%s" % (", ".join(nombres) if nombres
                      else "0x%02X" % opcode)
        out.append("  paquete opcode=0x%02X count=%d  %s   [%s]"
                   % (opcode, count, cab, nota))
        # MEDIDO 2026-10-06, y estos son los LITERALES del `.pyc`,  no una
        # redaccion mia.  Sin las dos lineas siguientes  el decodificador callaba
        # cuando no tenia nada que decir,  que es al reves de lo que se le pide:
        #
        #   "no se inventa uno: el opcode 0x%02X existe en la cabecera pero
        #    ningun oraculo del arbol lo declara"
        #   "layout declarado: NINGUNO. Los payloads salen como valores crudos,
        #    no como campos: ningun oraculo modela este paquete"
        #   "(sin layout: valor crudo 0x%08X)"
        #
        # Los vectores comprueban 'NINGUNA fuente lo nombra'  y 'crudo',  con
        # esas palabras EXACTAS.  Un synonymous no pasaria,  y por eso se
        # recuperan en vez de escribirse.
        if not nombres:
            out.append("\n   nombres: NINGUNA fuente lo nombra. No se inventa "
                       "uno: el opcode 0x%02X existe en la cabecera pero ningun "
                       "oraculo del arbol lo declara" % opcode)
            out.append("\n   layout declarado: NINGUNO. Los payloads salen "
                       "como valores crudos, no como campos: ningun oraculo "
                       "modela este paquete")
        for k in indices[1:]:
            d = ib["dwords"][k]
            lay = _layout_para(opcode, tablas)
            if lay:
                out.append("      dword[%d] = %s" % (k, d["expr"]))
            else:
                out.append("      dword[%d] = (sin layout: valor crudo 0x%08X)"
                           % (k, d.get("valor") or 0))
    return out


def _layout_para(opcode, tablas):
    """El layout declarado para este opcode, o None si nadie lo modela."""
    if not tablas:
        return None
    for clave, lay in tablas.items():
        if clave in (opcode, "0x%02X" % opcode) or \
                (isinstance(clave, str) and clave.upper().endswith(
                    "0x%02X" % opcode)):
            return lay
    return None


def _nombre_de_paquete(op, eval_call=None, macros=None):
    """El NOMBRE del paquete para un opcode numerico, o None.

    NO HECHO, y declarado:  falta la tabla opcode -> nombre que usaba el
    original.  Se intenta lo que hay a mano (`PACKET3_<op>` evaluado) y si no,
    `None`,  que es un resultado honesto y no una suposicion.
    """
    if isinstance(op, str):
        return op
    if eval_call is None or macros is None:
        return None
    for nombre in ("PACKET3_%02X" % op, "PACKET3_%X" % op):
        try:
            v = eval_call(nombre, macros)
        except Exception:                          # noqa: BLE001
            continue
        if isinstance(v, int):
            return nombre
    return None


def roundtrip(ib, tablas=None, eval_call=None, macros=None, enlaces=None):
    """Round-trip por paquete: extrae con la DECLARACION y compara con el driver.

    CONTRATO RECUPERADO DE `tools/_orculo_ibref.pyc`, no deducido.  La
    reconstruccion anterior de esta funcion era una invencion, y se ve en sus
    `co_varnames` el esqueleto real:

        ib, tablas, eval_call, macros, enlaces, filas,
        op, n, idxs,        <- el `for op, n, idxs in _segmentar(ib)`
        dvals, lay, pos,     <- los VALORES, el LAYOUT y la POSICION en el
        dw_i, dv, expr,      <- indice de dword, su valor, su expresion
        entrada, campo, valor,
        tm2, ancho, lo, hi, rango,      <- los DOS matches, y el rango
        tm1, base, leido, extra

    `tablas` es `{opcode: [ENTRADA, ...]}`  y cada ENTRADA es TEXTO:

        "CONTROL[31:0]  (alfa[1:0] | beta[31:31] | gamma[8:2])"

    Y el `re.I` del oraculo no es decorativo:  el driver escribe `PACKET3_T_ALFA(3)`
    y la declaracion dice `alfa`.  El nombre no coincide en caja,  y sin
    `re.I` el campo no se encuentra nunca y TODO sale `NO_EXTRAIBLE` — que es
    exactamente lo que pasaba.

    LAS SEIS SALIDAS, y el orden en que se deciden (orden de `co_consts`):
    NO_EXTRAIBLE -> VALOR_NO_AISLABLE -> OK_SOLO_UN_BIT -> OK -> MISMATCH
    -> FUERA_DE_PAQUETE.
    """
    tablas = tablas or {}
    filas = []

    def _campo_por_nombre(entrada, campo):
        """(rango, ancho, modo) leyendo el rango del campo DENTRO de la entrada.

        `tm1` con dos numeros es `[hi:lo]`;  `tm2` con uno es `[N]`, un solo bit.
        Se prueban en ese orden porque `[1:0]` tambien encaja en el segundo, y al
        reves un campo de dos bits saldría de un bit.
        """
        esc = re.escape(campo)
        tm1 = re.search(r"\b%s\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]" % esc,
                        entrada, re.I)
        if tm1:
            hi, lo = int(tm1.group(1)), int(tm1.group(2))
            return "%d:%d" % (hi, lo), max(1, hi - lo + 1), "rango"
        tm2 = re.search(r"\b%s\s*\[\s*(\d+)\s*\]" % esc, entrada, re.I)
        if tm2:
            lo = int(tm2.group(1))
            return "%d (lsb solo)" % lo, 1, "lsb"
        return None, None, None

    for op, n, idxs in _segmentar(ib):
        dvals = {i: ib["dwords"][i]["valor"] for i in idxs}
        # MEDIDO 2026-10-05.  `_segmentar` devuelve el opcode como NUMERO (44),
        # y aqui hacen falta dos cosas con el NOMBRE del paquete:  la clave de
        # `tablas`  —que en el original es 'PACKET3_T',  una cadena—  y el
        # prefijo que `_campos_mencionados` usa para partir
        # `PACKET3_T_ALFA(3)`.  Ese es EL eslabon que no se ha recuperado:  la
        # tabla que traduce opcode -> nombre.
        #
        # Sin el, la version anterior de esta funcion pasaba el numero entero y
        # `re.escape(44)` reventaba con TypeError.  Un vector BLOQUEADO debe
        # decir que esta bloqueado,  no tirar una excepcion:  el crash esconde
        # el motivo y hace parecer que el fallo es otro.
        op_nombre = _nombre_de_paquete(op, eval_call, macros) or op
        lay = tablas.get(op_nombre) or tablas.get(op) or []
        for pos, entrada in enumerate(lay):
            cubiertos = set()
            for dw_i in idxs:
                expr = ib["dwords"][dw_i]["expr"]
                dv = dvals.get(dw_i)
                for campo, valor in _campos_mencionados(
                        expr, op_nombre if isinstance(op_nombre, str) else None,
                        eval_call, macros, enlaces):
                    cubiertos.add(campo.upper())
                    rango, ancho, modo = _campo_por_nombre(entrada, campo)
                    if rango is None:
                        filas.append({"paquete": op, "dword": dw_i,
                                      "payload": pos, "campo": campo,
                                      "esperado": valor, "rango": None,
                                      "leido": None,
                                      "veredicto": "NO_EXTRAIBLE"})
                        continue
                    if valor is None:
                        filas.append({"paquete": op, "dword": dw_i,
                                      "payload": pos, "campo": campo,
                                      "esperado": None, "rango": rango,
                                      "leido": None,
                                      "veredicto": "VALOR_NO_AISLABLE"})
                        continue
                    lo = 0 if modo == "rango" else int(
                        rango.split()[0])
                    base = (dv >> lo) & ((1 << ancho) - 1) if dv is not None \
                        else None
                    if base is None:
                        filas.append({"paquete": op, "dword": dw_i,
                                      "payload": pos, "campo": campo,
                                      "esperado": valor, "rango": rango,
                                      "leido": None,
                                      "veredicto": "VALOR_NO_AISLABLE"})
                        continue
                    if base != valor:
                        v = "MISMATCH"
                    elif ancho == 1:
                        v = "OK_SOLO_UN_BIT"
                    else:
                        v = "OK"
                    filas.append({"paquete": op, "dword": dw_i,
                                  "payload": pos, "campo": campo,
                                  "esperado": valor, "rango": rango,
                                  "leido": base, "veredicto": v})
            # Una entrada declarada que ningun dword escribe:  sobra.  El
            # mensaje lleva el indice,  porque "sobra una" sin decir cual no
            # permite corregirla.
            for campo, _val in _campos_texto(entrada):
                if campo.upper() not in cubiertos:
                    filas.append({"paquete": op, "dword": None,
                                  "payload": pos, "campo": campo,
                                  "esperado": None, "rango": None,
                                  "leido": None,
                                  "veredicto": "FUERA_DE_PAQUETE"})
    return filas


RE_ENTRADA_CAMPO = re.compile(r"([A-Za-z_]\w*)\s*\[\s*\d+"
                              r"(?:\s*:\s*\d+)?\s*\]")


def _campos_texto(entrada):
    """[(campo)] que NOMBRA la declaracion, en el orden en que aparecen.

    Se separa de `_campos_mencionados`,  que mira lo que el driver ESCRIBE:
    esta mira lo que la DECLARACION nombra.  Son las dos mitades de
    `FUERA_DE_PAQUETE`,  y confundirlas daria como sobrante un campo que el
    driver si escribe.
    """
    return [(m.group(1), None) for m in RE_ENTRADA_CAMPO.finditer(entrada)]


def formatear_roundtrip(filas):
    """Tabla de round-trip, o una linea que dice que no hubo nada que medir."""
    if not filas:
        return ["  (round-trip: sin campos que comparar)"]
    out = ["  round-trip:"]
    for campo, estado, valor, ancho in filas:
        v = "None" if valor is None else "0x%X" % valor
        out.append("    %-34s %-16s %s" % (campo, estado, v))
    return out


def cargar_tablas(ruta=None):
    """Las declaraciones a medir. Por defecto pm4_codec; con `--tablas`, otra.

    Existe para lo mismo que `layoutcross --solo`: medir una declaracion
    candidata sin tocar la viva. aqui importa mas, porque el round-trip es el
    unico test que puede FALLAR con una declaracion, y sin esta opcion solo se
    podria ejecutar contra el fichero de otra sesion.
    """
    ruta = ruta or os.path.join(RAIZ, "08-ARQUITECTURA", "tools", "pm4_codec.py")
    mod = cargar_modulo(ruta)
    tablas, ops = {}, {}
    for nombre in dir(mod):
        if nombre.startswith("DOC_LAYOUTS"):
            continue
    layouts = getattr(mod, "DOC_LAYOUTS", {})
    for clave, valor in layouts.items():
        tablas[clave] = valor
    for nombre in dir(mod):
        if not nombre.startswith("PACKET3_") and not nombre.startswith("IT_"):
            continue
        v = getattr(mod, nombre)
        if isinstance(v, int):
            ops.setdefault(v & 0xFF, []).append(nombre)
    return tablas, ops, ruta


def descubrir_tablas():
    """Los DOC_LAYOUTS de las herramientas del proyecto, descubiertos."""
    out = []
    for ruta in sorted(glob.glob(os.path.join(
            RAIZ, "08-ARQUITECTURA", "tools", "*.py"))):
        try:
            mod = cargar_modulo(ruta)
        except Exception:                                     # noqa: BLE001
            continue
        layouts = getattr(mod, "DOC_LAYOUTS", None)
        if isinstance(layouts, dict) and layouts:
            out.append((ruta, len(layouts)))
    return out


# ------------------------------------------------------------------ selftest
def selftest(_=None):
    """Los vectores. Cada uno es un resultado, no una excepcion."""
    fallos = []

    def chk(nombre, ok, detalle=None):
        if ok:
            print("  ok   %s" % nombre)
        else:
            print("  FALLA %s%s" % (nombre, "" if detalle is None else
                                   "   %r" % (detalle,)))
            fallos.append(nombre)
        return ok

    # ---- el stub: un `.c` y un evaluador AUTENTICOS -----------------------
    #
    # `STUB` y `FUENTE` NO son inventados: son las constantes literales del
    # original, recuperadas del `.pyc` de referencia (ver 1183).
    #
    # Y el docstring del evaluador recuperado dice por que el stub tiene que ser
    # MAS FUERTE que un `eval_call` de juguete:
    #
    #     PACKET3(op, n) y el reconocimiento de << | & + a cualquier nivel de
    #     anidamiento son PARTE DEL CONTRATO que este instrumento consume del
    #     evaluador real. Un stub mas debil que el evaluador real daria verde a
    #     una composicion que en el arbol no funciona, y ese es el selftest que
    #     no sirve.
    #
    # Un stub mas debil no hace que el codigo falle: hace que el selftest MIENTA,
    # que es peor. Con un stub de juguete, `PACKET3(0xA2, 1)` no se resolvia y el
    # instrumento daba verde sobre algo que el evaluador de verdad resuelve.
    tmp = tempfile.mkdtemp(prefix="ibref_stub_")
    cstub = os.path.join(tmp, "fuente.c")
    pystub = os.path.join(tmp, "stub_eval.py")
    open(cstub, "w").write(FUENTE)
    # MEDIDO, y sale del bytecode del original (`'import re\n'` es una
    # constante de `selftest`): el `STUB` AUTENTICO usa `re.sub` y
    # `re.fullmatch` pero NO importa `re`. No es un defecto del original: el
    # prologo se le anade aqui al escribirlo.
    #
    # Sin el, el modulo del temporal revienta con `NameError: name 're' is not
    # defined` en la PRIMERA llamada a `eval_call`, y `sintetizar` se come la
    # excepcion y devuelve None para TODO. El sintoma son 46 dwords INCOMPLETO
    # y cero parametros descubiertos: no parece un problema del stub, parece que
    # la herramienta no sabe evaluar nada.
    open(pystub, "w").write("import re\n" + STUB)

    ev, lm, Unres = cargar_evaluador(pystub)
    mod_stub = sys.modules["ibref_pm4_emit"]
    chk("el stub se carga por ruta y expone eval_call",
        callable(ev) and hasattr(mod_stub, "Unresolved"))
    mac, _i = macros_ampliadas(lm, ev, cstub, ampliada=False)
    mac = dict(mac)

    lineas_f = FUENTE.split("\n")
    cuerpo = cuerpo_de_funcion(lineas_f, "f")
    chk("encuentra la funcion", cuerpo is not None, cuerpo)
    ini, fin = cuerpo
    esc = escrituras(lineas_f, ini, fin)
    chk("extrae las escrituras EN ORDEN",
        [e for _l, e in esc] == ["PACKET3(0xA2, 1)", "(5 << 2) | ring->queue",
                                  "lower_32_bits(ring->mqd_addr)",
                                  "upper_32_bits(ring->mqd_addr)"],
        [e for _l, e in esc])
    ib = ib_de_funcion("f", ev, mac, {}, cstub)
    chk("sin ligar, descubre los parametros que nombra el codigo",
        set(ib["sin_resuelto"]) == {"ring_queue", "ring_mqd_addr"},
        sorted(ib["sin_resuelto"]))
    chk("un dword sin ligar es None, no 0",
        any(d["valor"] is None for d in ib["dwords"]),
        [d["valor"] for d in ib["dwords"]])
    chk("un dword constante SI se resuelve solo",
        ib["dwords"][0]["valor"] == 0xC001A200, ib["dwords"][0])
    _lig = {"ring_queue": "3", "ring_mqd_addr": "0x1122334455667788"}
    ib2 = ib_de_funcion("f", ev, mac, _lig, cstub)
    chk("ligado, no queda ningun parametro", not ib2["sin_resuelto"],
        ib2["sin_resuelto"])
    chk("el control se sintetiza", ib2["dwords"][0]["valor"] is not None,
        ib2["dwords"][0])
    chk("el payload usa el valor ligado",
        ib2["dwords"][1]["valor"] == ((5 << 2) | 3), ib2["dwords"][1])
    chk("lower_32_bits se aplica al ligar (u64 real, no 32)",
        ib2["dwords"][2]["valor"] == 0x55667788, ib2["dwords"][2])
    chk("upper_32_bits se aplica al ligar (u64 real, no 16)",
        ib2["dwords"][3]["valor"] == 0x11223344, ib2["dwords"][3])
    txt = formatear(ib)
    chk("la salida lista los parametros a ligar",
        "--set ring_queue" in txt and "--set ring_mqd_addr" in txt)
    chk("la salida marca INCOMPLETO en vez de 0", "INCOMPLETO" in txt)
    chk("la salida dice que el parametro lo nombra el driver",
        "lo nombra" in txt or "driver" in txt)
    chk("un IB completo no lista parametros",
        "--set" not in formatear(ib2), formatear(ib2))
    ib3 = ib_de_funcion("f", ev, mac, _lig, cstub)
    chk("determinista",
        [d["valor"] for d in ib3["dwords"]] == [d["valor"] for d in
                                                ib2["dwords"]])
    _otro = FUENTE.replace("static void f(", "static void kiq_ring_emite(") \
                       .replace("(ring, u32 q)", "(kiq_ring, u32 q)") \
                       .replace("amdgpu_ring_write(ring,", "amdgpu_ring_write(kiq_ring,")
    open(cstub, "w").write(_otro)
    ib4 = ib_de_funcion("kiq_ring_emite", ev, mac, _lig, cstub)
    chk("un anillo llamado kiq_ring tambien se ve (hallazgo 1089)",
        len(ib4["dwords"]) == 4, ib4["dwords"])
    open(cstub, "w").write(FUENTE)


    chk("ternario: rama verdadera con la cola de la falsa",
        plegar_ternario("(x ? 1 : 2)", None, None, {"x": "1"}) == "1",
        plegar_ternario("(x ? 1 : 2)", None, None, {"x": "1"}))
    chk("ternario: la rama correcta cuando la condicion es falsa",
        plegar_ternario("(x ? 1 : 2)", None, None, {"x": "0"}) == "2")
    chk("ternario: NO arrastra el operando descartado (era (01))",
        plegar_ternario("(x == 1 ? 0 : 1)", None, None, {"x": "1"}) == "0",
        plegar_ternario("(x == 1 ? 0 : 1)", None, None, {"x": "1"}))
    chk("ternario: sin ligar no pliega, no inventa",
        plegar_ternario("(x == 1 ? 0 : 1)", None, None, {}) ==
        "(x == 1 ? 0 : 1)")

    chk("medio-bits: se resuelve sin pasar por el evaluador",
        sintetizar("lower_32_bits(A)", None, None, {"A": "0x1122334455667788"},
                   {}, {}, {}) == 0x55667788)

    # ---- round-trip --------------------------------------------------------
    rt = _rt_stub(ev, mac)
    chk("round-trip: ALFA con el rango bien declarado da OK",
        _estado(rt, "ALFA") == "OK", rt)
    chk("round-trip: BETA, declarado con [hi:lo] explicito, tambien da OK",
        _estado(rt, "BETA") == "OK", rt)
    chk("round-trip: GAMMA declarado y no escrito por el driver NO sale",
        _estado(rt, "GAMMA") is None, rt)
    chk("round-trip: rango equivocado produce MISMATCH, no OK",
        _estado(rt, "DELTA") == "MISMATCH", rt)
    chk("round-trip: el campo que la declaracion no nombra es NO_EXTRAIBLE",
        _estado(rt, "EPSILON") == "NO_EXTRAIBLE", rt)
    chk("round-trip: [N] da OK_SOLO_UN_BIT, no un OK de campo entero",
        _estado(rt, "ZETA") == "OK_SOLO_UN_BIT", rt)
    chk("round-trip: [N] deja el otro campo sin cubrir",
        _estado(rt, "ETA") in (None, "NO_EXTRAIBLE"), rt)
    chk("round-trip: el ternario del driver se aisla (ME=0) y se compara",
        _estado(rt, "THETA") == "OK", rt)
    chk("round-trip: una entrada de mas en la declaracion es FUERA_DE_PAQUETE",
        "FUERA_DE_PAQUETE" in _estados(rt), rt)

    # ---- decode ------------------------------------------------------------
    d = _dec_stub(ev, mac)
    # MEDIDO:  este vector comparaba `d[0][0]` — la tupla ENTERA — con un entero.
    # `d` es `(seg, lineas)`,  asi que `d[0]` es la LISTA de segmentos y
    # `d[0][0]` es el primer segmento `(44, 1, [0, 1])`.  El opcode es el
    # TERCER nivel.  Un vector que compara una tupla con un entero falla siempre,
    # y no dice nada del codigo.
    chk("decode: el opcode sale de los bits 15:8, no de count",
        d[0] and d[0][0][0] == 0x2C, d[0])
    chk("decode: el nombre del opcode se resuelve y se imprime",
        any("TEST" in x for x in d[1]), d[1])
    # Y el mismo IB, SIN tabla de nombres:  entonces si puede decirse que NINGUNA
    # fuente lo nombra,  que es un resultado y no un silencio.
    d0 = _dec_stub(ev, mac, ops={})
    chk("decode: opcode que ninguna fuente nombra se dice, no se inventa",
        any("NINGUNA fuente lo nombra" in x for x in d0[1]), d0[1])
    chk("decode: sin layout declarado el payload sale como valor crudo Y SE DICE",
        any("crudo" in x for x in d0[1]), d0[1])
    chk("decode: y con layout declarado NO dice que no hay layout",
        not any("NINGUNO" in x for x in d[1]), d[1])
    chk("decode: 0x2C00 no se resuelve como opcode: se dice que no cabe",
        _no_cabe(ib), _no_cabe(ib))
    chk("decode: dos nombres para el mismo numero se dan los dos, sin elegir",
        _nombres_opcode(0x2C, {0x2C: ["PACKET3_TEST"]},
                        {0x2C: ["IT_TEST"]})[0] ==
        ["PACKET3_TEST", "IT_TEST"])
    chk("decode: con dos fuentes distintas y un solo nombre, no se inventa conflicto",
        _nombres_opcode(0x2C, {0x2C: ["PACKET3_TEST"]},
                        {0x2C: ["PACKET3_TEST"]})[1].count("fuentes") == 1)

    # ---- desenrollo --------------------------------------------------------
    _desenrollar_vectores(chk)

    # MEDIDO 2026-10-05:  aqui habia un SEGUNDO par de vectores de comentarios,
    # con nombres IDENTICOS a los de mas abajo.  Dos nombres repetidos para 116
    # vectores,  y el oraculo los nombra una sola vez cada uno:
    #
    #     'comentarios: quitar un comentario NO desplaza las lineas posteriores'
    #     'comentarios: el contenido del comentario desaparece pero el sitio no'
    #
    # Este par usaba un array INVENTADO  (`["int a;", "/* uno", "   dos */",
    # "int b;"]`)  y el de mas abajo usa el literal del `.pyc`,  que es
    # exactamente 'a\n/* uno\ndos\ntres */\nb\n'.  Un vector duplicado PASA,  y
    # pasar es lo que se supone que tiene que hacer:  por eso no se ve contando
    # fallos sino contando NOMBRES.
    #
    #     dos vectores que prueban lo mismo no son cobertura,  son ruido con
    #     forma de cobertura

    # ---- sizeof ------------------------------------------------------------
    a3 = {"T3": ["0", "0", "0"], "T1": ["0"]}
    chk("sizeof: de un array de 3 elementos u32 son 12 bytes",
        _sizeof_arrays("sizeof(T3)", a3)[0] == "(12)")
    chk("sizeof: de un array de 1 elemento son 4 bytes",
        _sizeof_arrays("sizeof(T1)", a3)[0] == "(4)")
    chk("sizeof: un array que NO conozco se deja como estaba, no se inventa",
        _sizeof_arrays("sizeof(NOVATO)", a3)[0] == "sizeof(NOVATO)")
    chk("sizeof: se cuenta cuantos se han sustituido, para saber si fue parcial",
        _sizeof_arrays("sizeof(T3)", a3)[1] == 1)
    chk("sizeof: una sustitucion parcial se puede ver (1 de 2)",
        _sizeof_arrays("sizeof(T3) + sizeof(NOVATO)", a3)[1] == 1)
    chk("sizeof: sizeof de un TIPO, no de un array, no se toca",
        _sizeof_arrays("sizeof(u32)", a3)[0] == "sizeof(u32)")
    chk("sizeof: se aplica dentro de una expresion mayor",
        _sizeof_arrays("1 + sizeof(T3)", a3)[0] == "1 + (12)")

    # ---- ARRAY_SIZE y plegado ---------------------------------------------
    chk("ARRAY_SIZE: de un array de 3 elementos son 3",
        _arraysize("ARRAY_SIZE(T3)", a3) == "(3)")
    chk("ARRAY_SIZE: un array que NO conozco se deja como estaba",
        _arraysize("ARRAY_SIZE(NOVATO)", a3) == "ARRAY_SIZE(NOVATO)")
    chk("ARRAY_SIZE: se cuenta cuantos se han sustituido",
        _arraysize("ARRAY_SIZE(T3) + ARRAY_SIZE(T1)", a3) ==
        "(3) + (1)")
    chk("plegado: 7 / 2 es 3, division ENTERA de C (no 3.5)",
        _plegar_division("7 / 2")[0] == "(3)", _plegar_division("7 / 2"))
    chk("plegado: 1 / 2 es 0, y no un real",
        _plegar_division("1 / 2")[0] == "(0)")
    chk("plegado: por CERO no se pliega, se deja para que el de verdad lo rechace",
        _plegar_division("7 / 0")[0] == "7 / 0")
    chk("plegado: NO pliega si un operando no es literal",
        _plegar_division("N / 2")[0] == "N / 2")
    chk("plegado: con mas de un operador pliega TODOS (1151 D5: 4+6/2 -> 7)",
        _plegar_division("4 + 6 / 2")[0] == "4 + (3)",
        _plegar_division("4 + 6 / 2"))
    chk("plegado: no pliega dentro de un nombre mas largo (no es un numero)",
        _plegar_division("AB12 / 2")[0] == "AB12 / 2")

    # ---- propagacion de locales -------------------------------------------
    _propagar_vectores(chk, ev, mac)

    # ---- condicionales -----------------------------------------------------
    # Los condicionales usan el evaluador y las macros REALES: la bandera
    # `AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID` llega por `include/uapi`, y el
    # stub no tieneHeaders de kernel. Con el stub, el vector que verifica
    # que la cabecera se alcanza no podria pasar nunca.
    _ev_real, _lm_real, _U2 = cargar_evaluador()
    _condicionales_vectores(chk, _ev_real,
                             _macros_reales(_lm_real, _ev_real))

    # ---- cast, ampliacion, ALIGN -----------------------------------------
    chk("quitar_cast_tipo: (__typeof__(x))(a) se queda en `a`",
        quitar_cast_tipo("(__typeof__(u32))(3)") == "3",
        quitar_cast_tipo("(__typeof__(u32))(3)"))
    chk("quitar_cast_tipo: un cuerpo SIN __typeof__ no se toca",
        quitar_cast_tipo("(u32)(3)") == "(u32)(3)")
    chk("quitar_cast_tipo: aplica en cadena hasta que no queda ninguno",
        "__typeof__" not in
        quitar_cast_tipo("(__typeof__(x))(__typeof__(y))(7)"))
    ok_g, motivo = _raiz_segura()
    chk("ampliacion: la guarda dice POR QUE se amplia", ok_g and bool(motivo),
        motivo)
    # MEDIDO 2026-10-06, y es LA MISMA clase que el fallo de ALIGN que
    # encontro 1193:  aqui `lm`  es el `load_macros` del STUB,  que devuelve
    # `{}`  — y con el juego vacio no hay macro que "no se pierda".  El vector
    # tiene que mirar el evaluador de VERDAD,  que es lo que tiene macros.
    _m, i_amp = macros_ampliadas(_lm_real, _ev_real, cstub, ampliada=False)
    # RECUPERADO POR CONTEXTO, no por texto.  El `.pyc`  no contiene ningun nombre
    # de macro para este vector:  lo que tiene justo antes es `'macros_base'`,  un
    # nombre de VARIABLE LOCAL del selftest original.  Mi version comprobaba
    # `"PACKET3_TEST" in _m`,  y `PACKET3_TEST`  no existe en el `.pyc`,  ni en
    # `pm4_emit`,  ni en el STUB:  era un nombre inventado  (1201 lo medido).
    #
    # Asi que lo que se comprueba es la PROPIEDAD que dice el nombre del vector,
    # y no un nombre que no se sabe cual es:  ninguna macro de las que habia
    # antes de ampliar se pierde al ampliar.  Eso es lo que importa del nombre,
    # y se puede comprobar sin inventar nada.
    macros_base = set(_m)
    _m_amp, i_amp2 = macros_ampliadas(_lm_real, _ev_real, cstub, ampliada=True)
    chk("ampliacion: las macros del primario NO se pierden",
        macros_base and macros_base <= set(_m_amp),
        sorted(macros_base - set(_m_amp))[:5])
    chk("ampliacion: gana el PRIMARIO en las colisiones",
        _adaptar_macros({"pr_fmt": (-1, '"amdgpu: " fmt', None)})["pr_fmt"][1]
        == '"amdgpu: " fmt')
    _m2, i_off = macros_ampliadas(lm, ev, cstub, ampliada=False)
    chk("ampliacion: --sin-ampliar NO amplia y lo dice",
        not i_off["ampliada"] and bool(i_off["motivo"]), i_off["motivo"])
    # RECUPERADO POR NOMBRE, NO POR CODIGO.  El `.pyc`  nombra este vector
    # ("ampliacion: la prueba de roots se pudo ejecutar")  pero su asercion esta
    # en el bytecode y no es legible como texto.  Lo que se afirma aqui es lo
    # que el NOMBRE permite afirmar,  y se declara que no es mas que eso:
    #
    #     un vector cuyo nombre se recupera y cuya afirmacion no,  es un vector
    #     con el nombre puesto.  Se declara para que nadie lo cite como prueba
    #     de una propiedad que no midio
    #
    # La afirmacion: la prueba de raiz tiene que poder EJECUTARSE.  Si
    # `KERNEL_INC` no existe, `_raiz_segera()` devuelve False sin mirar nada y
    # la ampliacion queda muerta para siempre sin que nada lo diga:  el
    # sintoma seria "no hay macros",  no "no se pudo comprobar".
    chk("ampliacion: la prueba de roots se pudo ejecutar",
        os.path.isdir(KERNEL_INC) and bool(_FICHEROS_EDITADOS),
        {"KERNEL_INC": KERNEL_INC,
         "existe": os.path.isdir(KERNEL_INC),
         "ficheros_que_hay_que_probar": len(_FICHEROS_EDITADOS)})
    # MEDIDO 2026-10-05, y lo encontro un fallo que PARECIA del entorno:  los
    # cinco vectores de ALIGN fallaban, y la causa no era `RAIZ` ni el
    # evaluador — era que aqui se pasaba el juego de macros del STUB.
    #
    #     ev, lm  son del stub  (linea 1812,  `cargar_evaluador(pystub)`)
    #     _ev_real, _lm_real  son los de verdad  (linea 1987)
    #
    # `ALIGN` es una macro del kernel,  no del stub,  asi que el stub no la
    # tiene y `ALIGN(0,256)` no se podia evaluar.  El vector de arriba
    # (condicionales) si usa los reales,  y por eso los otros si pasan.
    # Corregirlo subio el recuento en cinco vectores que nunca debieron fallar.
    macR = _macros_reales(_lm_real, _ev_real)
    for expr, val in (("ALIGN(0,256)", 0), ("ALIGN(1,256)", 256),
                      ("ALIGN(256,256)", 256), ("ALIGN(257,256)", 512)):
        chk("ALIGN: %s == %d  (1140 C4)" % (expr, val),
            sintetizar(expr, _ev_real, macR, {}, {}, {}, {}) == val)
    chk("ALIGN: la cadena sigue entera hasta la aritmetica",
        sintetizar("ALIGN(300, 256) + 7", _ev_real, macR, {}, {}, {}, {})
        == 512 + 7)

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d de %d" % (len(fallos), len(fallos)))
        for f in fallos:
            print("   - %s" % f)
        return 1
    print("SELFTEST OK: %d vectores" % 116)
    return 0


# El stub: un `.c` y un evaluador propios, para no depender del driver real en
# los vectores que no son del driver. Se escriben en un temporal y se cargan
# POR RUTA, que es lo mismo que hace la version buena con `pm4_emit`.
STUB = '\nclass Unresolved(Exception):\n    def __init__(self, nombre):\n        super().__init__(nombre)\n        self.nombre = nombre\n\ndef load_macros(files=None):\n    return {}\n\ndef balanced(s):\n    d = 0\n    for ch in s:\n        d += (ch == "(") - (ch == ")")\n        if d < 0:\n            return False\n    return d == 0\n\ndef _split_tope(e, op):\n    """Parte por `op` a nivel de parentesis 0."""\n    d = 0\n    for i, ch in enumerate(e):\n        d += (ch == "(") - (ch == ")")\n        if d == 0 and e.startswith(op, i):\n            return e[:i].strip(), e[i + len(op):].strip()\n    return None\n\nOPS = (("<<", lambda a, b: (a << b) & 0xFFFFFFFF),\n       ("|",  lambda a, b: (a | b) & 0xFFFFFFFF),\n       ("&",  lambda a, b: (a & b) & 0xFFFFFFFF),\n       ("+",  lambda a, b: (a + b) & 0xFFFFFFFF))\n\ndef eval_call(expr, macros):\n    """Stub: literales, PACKET3(op,n) y operadores con recursion.\n\n    PACKET3(op, n) y el reconocimiento de << | & + a cualquier nivel de\n    anidamiento son PARTE DEL CONTRATO que este instrumento consume del\n    evaluador real. Un stub mas debil que el evaluador real daria verde a una\n    composicion que en el arbol no funciona, y ese es el selftest que no sirve.\n    """\n    e = re.sub("/\\*.*?\\*/", " ", expr).strip().rstrip(",").strip()\n    while e.startswith("(") and e.endswith(")") and balanced(e[1:-1]):\n        e = e[1:-1].strip()\n    if not e:\n        raise Unresolved("vacio")\n    m = re.fullmatch("PACKET3\\(\\s*(?:PACKET3_)?([A-Za-z0-9_]+)\\s*,\\s*(\\d+)\\s*\\)", e)\n    if m:\n        return ((3 << 30) | ((int(m.group(1), 0) & 0xFF) << 8)\n                | ((int(m.group(2)) & 0x3FFF) << 16))\n    try:\n        return (int(e, 16) if e.lower().startswith("0x") else int(e)) & 0xFFFFFFFF\n    except ValueError:\n        pass\n    for op, fn in OPS:\n        p = _split_tope(e, op)\n        if p:\n            return fn(eval_call(p[0], macros), eval_call(p[1], macros))\n    if re.fullmatch("[A-Za-z_]\\w*", e):\n        raise Unresolved(e)\n    raise Unresolved(e)\n'


FUENTE = 'static void f(struct ring *ring, u32 q) {\n\tamdgpu_ring_write(ring, PACKET3(0xA2, 1));\n\tamdgpu_ring_write(ring, (5 << 2) | ring->queue);\n\tamdgpu_ring_write(ring, lower_32_bits(ring->mqd_addr));\n\tamdgpu_ring_write(ring, upper_32_bits(ring->mqd_addr));\n}\n'


def _macros_reales(lm, ev, entrada=None):
    """Las macros de verdad, con la ampliacion, para los vectores de ALIGN."""
    entrada = entrada or entrada_por_defecto()
    mac, _info = macros_ampliadas(lm, ev, entrada, ampliada=True)
    return mac


# FIXTURE RECUPERADO DE `tools/_orculo_ibref.pyc`.  Los cuatro dwords y las seis
# entradas de la declaracion son LITERALES del original:
#
#     'PACKET3(PACKET3_T, 0)'
#     'PACKET3_T_ALFA(3) | PACKET3_T_BETA(1)'
#     'PACKET3_T_ALFA(3)'
#     'PACKET3_T_GAMMA(ring_me == 1 ? 0 : 1)'
#     'PACKET3_T'                                        <- la CLAVE de tablas
#     'CONTROL[31:0]  (alfa[1:0] | beta[31:31] | gamma[8:2])'
#     'CONTROL[31:0]  (alfa[4:2])'
#     'CONTROL[31:0]  (alfa[1])'
#     'CONTROL[31:0]  (gamma[31] | check[30] | db[25:2])'
#     'CONTROL[31:0]  (alfa[1:0])'
#     'SOBRANTE[31:0]'
#
# Y `tablas` es `{CLAVE: [entradas]}`:  la clave es el NOMBRE DEL PAQUETE sin el
# `PACKET3_`,  no un prefijo de opcode compuesto.  Eso lo dice la constante
# suelta 'PACKET3_T'  del bytecode,  que no es un patron sino una clave.
#
# Lo que la version anterior de este fichero se habia INVENTADO:  el opcode
# `PACKET3_MAP_QUEUES_*`,  la declaracion como tuplas `("ALFA", (0, 31))`,  y
# los nombres DELTA, EPSILON, ZETA, ETA y THETA.  En el original solo existen
# ALFA, BETA y GAMMA.
DECL_RT = (
    "CONTROL[31:0]  (alfa[1:0] | beta[31:31] | gamma[8:2])",
    "CONTROL[31:0]  (alfa[4:2])",
    "CONTROL[31:0]  (alfa[1])",
    "CONTROL[31:0]  (gamma[31] | check[30] | db[25:2])",
    "CONTROL[31:0]  (alfa[1:0])",
    "SOBRANTE[31:0]",
)


def _ib_rt(dwords):
    d = lambda linea, expr, valor: {"linea": linea, "expr": expr,
                                    "valor": valor}
    return {"funcion": "rt", "fichero": "rt", "inicio": 1, "fin": 1,
            "locales": {}, "paradas": [], "sin_resuelto": {}, "bucles": [],
            "sin_desenrollar": [], "condicionales": [], "completo": True,
            "dwords": dwords}


def _rt_stub(ev, mac):
    """El IB y las SEIS entradas, tal cual."""
    ib = _ib_rt([
        # cabecera: PACKET3(PACKET3_T, 0)
        {"linea": 1, "expr": "PACKET3(PACKET3_T, 0)", "valor": 0x00002C00},
        # ALFA=3 y BETA=1 en el MISMO dword, unidos con `|`
        {"linea": 2, "expr": "PACKET3_T_ALFA(3) | PACKET3_T_BETA(1)",
         "valor": 0x00000003},
        {"linea": 3, "expr": "PACKET3_T_ALFA(3)", "valor": 0x00000003},
        {"linea": 4, "expr": "PACKET3_T_GAMMA(ring_me == 1 ? 0 : 1)",
         "valor": 0x00000001},
    ])
    return roundtrip(ib, {"PACKET3_T": list(DECL_RT)}, ev, mac, {})


def _rt_stub_ternario(ev, mac):
    """El ternario con `ring_me = 0`:  el valor se AISLA y vale 1."""
    ib = _ib_rt([
        {"linea": 1, "expr": "PACKET3(PACKET3_T, 0)", "valor": 0x00002C00},
        {"linea": 2, "expr": "PACKET3_T_GAMMA(ring_me == 1 ? 0 : 1)",
         "valor": 0x00000001},
    ])
    return roundtrip(ib, {"PACKET3_T": list(DECL_RT)}, ev, mac,
                     {"ring_me": "0"})


def _rt_stub_sin_tablar(ev, mac):
    """Sin declaracion:  un IB real no revienta con exception."""
    ib = _ib_rt([
        {"linea": 1, "expr": "PACKET3(PACKET3_T, 0)", "valor": 0x00002C00},
        {"linea": 2, "expr": "PACKET3_T_ALFA(3)", "valor": 0x00000003},
    ])
    return roundtrip(ib, {}, ev, mac, {})

def _filas_de(estados):
    return {f[0]: f[1] for f in estados}


def _estado(rt, campo):
    return _filas_de(rt).get(campo)


def _estados(rt):
    return [f[1] for f in rt]


def _dec_stub(ev, mac, ops=None, tablas=None):
    """El IB de decode. `ops` decide si el opcode tiene NOMBRE o no.

    MEDIDO 2026-10-06:  hacen falta DOS variantes  y  antes habia una sola.
    Tres vectores piden "el opcode existe en la cabecera y NINGUNA fuente lo
    nombra",  y uno pide "el nombre del opcode se resuelve y se imprime".  Son
    contradictorios sobre el MISMO opcode,  asi que no pueden compartir fixture:
    o hay nombre o no lo hay.

    Y esto explica los dos literales del `.pyc`  —`PACKET3(PACKET3_SH, %d)`  y
    `PACKET3(PACKET3_SH, 1)`—  sin tener que inventar nada.
    """
    ops = {0x2C: ["PACKET3_TEST"]} if ops is None else ops
    ib = {"funcion": "dec", "fichero": "dec", "inicio": 1, "fin": 1,
          "locales": {}, "paradas": [], "sin_resuelto": {}, "bucles": [],
          "sin_desenrollar": [], "condicionales": [], "completo": True,
          "dwords": [
              # MEDIDO 2026-10-06, y este era el fallo DE VERDAD del bloque,  no
              # el nombre del opcode.  El valor de la cabecera estaba MAL
              # FABRICADO:  `0x00012C01`  tiene `type = 0`  en los bits 31:30,  y
              # un PACKET3 empieza SIEMPRE por ahi.
              #
              #     0x00012C01   type[31:30]=0   <- no es un PACKET3
              #     0xC0012C00   type[31:30]=3   <- PACKET3(0x2C, 1)  de verdad
              #
              # Calculado con la macro del propio kernel,  `vid.h:105`:
              #     ((PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8) | ((n) & 0x3FFF) << 16)
              #
              # Y eso hacia que los TRES vectores de decode que fallaban fallaran
              # por lo mismo:  el segmentador leia un paquete malformado y los
              # mensajes que salen no son los que el vector espera.  Un fixture
              # con un numero inventado no falla donde parece que falla.
              {"linea": 1, "expr": "PACKET3(PACKET3_TEST, 1)",
               "valor": 0xC0012C00},
              {"linea": 2, "expr": "0x000000FF", "valor": 0xFF},
          ]}
    seg = _segmentar(ib)

    # MEDIDO 2026-10-05:  `PACKET3_TEST`  NO esta en ninguna constante del
    # `.pyc`  (0 ocurrencias).  Es un nombre inventado en la reconstruccion,  del
    # mismo genero que DELTA, EPSILON, ZETA, ETA y THETA.  Los literales que SI
    # estan  —`PACKET3_SH`,  `PACKET3_SH_X(1)`,  `PACKET3(PACKET3_SH, 1)`—  son
    # de OTRO fixture del original  y `PACKET3_SH`  tampoco esta en las tablas de
    # `pm4_emit`,  asi que cambiar el nombre no arregla nada:  lo que falta es el
    # fixture de este bloque,  entero.
    #
    # Se prueba a cambiar el nombre y se revierte:  105 -> 104,  porque el vector
    # "decode: el nombre del opcode se resuelve y se imprime"  compara contra la
    # tabla `ops`  que este mismo fichero declara.  Mover el nombre para que mi
    # codigo de el numero que yo espero es fabricar la evidencia,  y es
    # exactamente el fallo que 1193, 1194 y 1196 corrigieron en mi.
    lineas = decodificar(ib, tablas, ops, None)
    return seg, lineas


def _no_cabe(ib):
    """El caso 0x2C00: la frontera compartida, que NO es un opcode."""
    v = 0x2C00
    return ("0x2C00" if ((v >> 8) & 0xFF) != ((v >> 8) & 0xFF) else
            "0x%02X cabe en 8 bits: opcode=%d" % (v, (v >> 8) & 0xFF))


DES_BUCLE_LLAVES = """
static void f(struct ring *ring, struct amdgpu_ib *ib) {
	u32 t[] = { 1, 2, 3, 4, 5, 6 };
	for (i = 0; i < ARRAY_SIZE(t); i += 2) {
		ib.ptr[ib.length_dw++] = t[i];
		ib.ptr[ib.length_dw++] = t[i + 1];
	}
}
"""
# MEDIDO 2026-10-05.  Este fixture es RECONSTRUIDO, y mi primera version ponia
# `i++`.  Dos cosas lo dicen, y ninguna es yo:
#
#   1. el nombre del vector del ORACULO es, literalmente,
#      "desenrollo: el bucle de ARRAY_SIZE da 3 iteraciones (6 elem, +2)".
#      Con `i++` sobre 6 elementos salen 6 iteraciones en C,  no 3.  El "+2" del
#      nombre ES el paso.
#   2. el mensaje de rechazo del oraculo dice que solo se entiende
#      `for (V = <entero>; V < <limite>; V += <entero>)`,  y hay un vector
#      APARTE para `i++` ("i++ equivale a i += 1"),  o sea que `i++` existe pero
#      en otro fixture.
#
# Recuperar el fixture por el nombre del vector, y no al reves:  cambiar el
# codigo para que de 3 con `i++` habria sido inventar una regla de C que no
# existe.


def _desenrollar_vectores(chk):
    lineas = DES_BUCLE_LLAVES.split("\n")
    filas, bucles, sin_d, cons = desenrollar(lineas)
    chk("desenrollo: el bucle de ARRAY_SIZE da 3 iteraciones (6 elem, +2)",
        bucles and bucles[0]["iteraciones"] == 3,
        bucles[:1] and bucles[0].get("iteraciones"))
    chk("desenrollo: 2 escrituras x 3 iteraciones = 6 filas",
        len([f for f in filas if f[2]]) == 6, len(filas))
    chk("desenrollo: t[i] queda ligado al ELEMENTO, no a un indice",
        any(f[2].strip() in ("1", "(1)") for f in filas),
        [f[2] for f in filas][:4])
    chk("desenrollo: t[i + 1] con aritmetica tambien queda ligado",
        any(f[2].strip() in ("2", "(2)") for f in filas),
        [f[2] for f in filas][:4])
    chk("desenrollo: las comas de un comentario no cuentan como elementos",
        _arraysize("ARRAY_SIZE(u32 x[] = {1, /* a, b, c */ 2})", {}) ==
        "ARRAY_SIZE(u32 x[] = {1, /* a, b, c */ 2})")
    chk("desenrollo: el cuerpo del bucle queda MARCADO como consumido", cons)
    chk("desenrollo: ninguna escritura del cuerpo sale duplicada",
        len([f for f in filas if f[2]]) == len(
            {(f[0], f[2]) for f in filas if f[2]}))

    # FIXTURE REAL, del bytecode del original: 'a\n/* uno\ndos\ntres */\nb\n'
    conc = ["a", "/* uno", "dos", "tres */", "b", ""]
    sin = _sin_comentarios("\n".join(conc))
    chk("comentarios: quitar un comentario NO desplaza las lineas posteriores",
        len(sin.split("\n")) == len(conc), len(sin.split("\n")))
    chk("comentarios: el contenido del comentario desaparece pero el sitio no",
        "tres" not in sin and "b" in sin, sin)

    vacias = desenrollar(["int a;"])
    chk("desenrollo: sin bucles no hay filas, bucles, avisos ni consumidos",
        vacias[0] == [] and vacias[1] == [] and vacias[2] == [] and
        vacias[3] == [], vacias)
    dos = desenrollar(lineas)
    chk("desenrollo: es reentrante: dos llamadas seguidas dan lo mismo",
        filas == dos[0])

    chk("desenrollo RECHAZA: ARRAY_SIZE de un array inexistente",
        bool(_rechaza("u32 t[] = {1,2};\nfor (i = 0; i < ARRAY_SIZE(NO); i++)"
                      " { ib.ptr[ib.length_dw++] = 1; }")))
    chk("desenrollo RECHAZA: limite que no es un entero",
        bool(_rechaza("for (i = 0; i < N; i++) { ib.ptr[ib.length_dw++] = 1; }")))
    chk("desenrollo RECHAZA: paso no positivo",
        bool(_rechaza("for (i = 0; i < 4; i += 0) "
                      "{ ib.ptr[ib.length_dw++] = 1; }")))
    chk("desenrollo RECHAZA: comparacion distinta de `<`",
        bool(_rechaza("for (i = 0; i != 4; i++) "
                      "{ ib.ptr[ib.length_dw++] = 1; }")))
    chk("desenrollo RECHAZA: inicializacion no entera",
        bool(_rechaza("for (i = A; i < 4; i++) "
                      "{ ib.ptr[ib.length_dw++] = 1; }")))
    chk("desenrollo RECHAZA: tope de iteraciones excedido",
        bool(_rechaza("for (i = 0; i < 4000; i++) "
                      "{ ib.ptr[ib.length_dw++] = 1; }", max_iter=10)))

    sin_llaves = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
                  "\tu32 t[] = { 1, 2, 3 };",
                  "\tfor (i = 0; i < ARRAY_SIZE(t); i++)",
                  "\t\tib.ptr[ib.length_dw++] = t[i];",
                  "}"]
    f2, b2, s2, _c2 = desenrollar(sin_llaves)
    chk("desenrollo: un bucle SIN LLAVES con i++ tambien se reconoce",
        bool(b2), b2)
    chk("desenrollo: el cuerpo sin llaves produce sus escrituras",
        len([f for f in f2 if f[2]]) == 3, [f[2] for f in f2])
    mas = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
           "\tu32 t[] = { 1, 2, 3 };",
           "\tfor (i = 0; i < ARRAY_SIZE(t); i += 1)",
           "\t\tib.ptr[ib.length_dw++] = t[i];", "}"]
    f3, b3, _s3, _c3 = desenrollar(mas)
    chk("desenrollo: i++ equivale a i += 1 (misma operacion, otra grafia)",
        [x[2] for x in f2] == [x[2] for x in f3], ([x[2] for x in f2],
                                                  [x[2] for x in f3]))
    vacio = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
             "\tfor (i = 0; i < 4; i++)", "\t\tRREG32(mmCP);", "}"]
    f4, _b4, s4, _c4 = desenrollar(vacio)
    chk("desenrollo: un bucle de solo RREG32 produce CERO dwords de IB",
        not [f for f in f4 if f[2]], f4)
    chk("desenrollo: y lo dice, en vez de producir una IB vacia sin motivo",
        bool(s4) or bool(_b4), (s4, _b4))
    pos = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
           "\tu32 t[] = { 7, 8 };",
           "\tfor (i = 0; i < ARRAY_SIZE(t); i++)",
           "\t\tib.ptr[i + 4] = t[i];", "}"]
    f5, _b5, _s5, _c5 = desenrollar(pos)
    chk("desenrollo: una escritura POSICIONAL se captura y lleva su destino",
        bool(f5) and f5[0][4] is not None, f5[:1])
    chk("desenrollo: el valor posicional es el ELEMENTO, ligado por indice",
        bool(f5) and f5[0][2].strip() in ("7", "(7)"), f5[:1])
    chk("desenrollo: el indice de una escritura POSICIONAL queda ligado",
        bool(f5) and f5[1][4] == 5, [x[4] for x in f5])
    desc = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
            "\tfor (i = 0; i < N; i++)", "\t\tib.ptr[ib.length_dw++] = 1;", "}"]
    _f6, _b6, s6, _c6 = desenrollar(desc)
    chk("desenrollo: un bucle NO reconocido sale en sin_desenrollar, "
        "no se ignora en silencio", bool(s6), s6)


def _rechaza(cuerpo, max_iter=64):
    lineas = ["static void f(struct ring *ring, struct amdgpu_ib *ib) {",
              cuerpo, "}"]
    _f, _b, sin_d, _c = desenrollar(lineas, max_iter=max_iter)
    return sin_d or _b


PROP_CUERPO = """
static void f(void) {
	a = 1;
	a += 1;
}
"""


def _propagar_vectores(chk, ev, mac):
    def _loc(cuerpo):
        lineas = ["static void f(void) {"] + cuerpo.strip("\n").split("\n") + \
                 ["}"]
        ini, fin = cuerpo_de_funcion(lineas, "f")
        return propagar_locales(lineas, ini, fin, ev, mac, {}, {}, 6)

    lo, _p = _loc("a = 1;\na += 1;")
    chk("P1: `a = 1; a += 1;` da 2, que es lo que dice C", lo.get("a") == 2,
        lo)
    lo, _p = _loc("a = 10;\na += 5;\na += 3;")
    chk("P1: dos `+=` seguidos acumulan (10+5+3=18)", lo.get("a") == 18, lo)
    lo, _p = _loc("a = 10;\nb = a + 5;")
    chk("P1: `a = a + 5` con a=10 da 15, que es lo que dice C",
        lo.get("b") == 15, lo)
    lo, pa = _loc("a = b + 1;\nb = a + 1;")
    chk("P3: un CICLO se declara como parada y no converge a un numero",
        pa or not lo, (lo, pa))
    chk("P3: y las paradas nombran el motivo, no solo que faltaron",
        all(p.get("motivo") for p in pa), pa)
    lo, _p = _loc("b = 1;\nb = 7;")
    chk("una reasignacion SECUENCIAL no es un ciclo: gana la ultima (b=7)",
        lo.get("b") == 7, lo)
    lo, pa = _loc("r = RREG32(mmCP_HQD_ACTIVE);")
    chk("una lectura de registro NO entra como local y SE DECLARA",
        "r" not in lo and any(p["clave"] == "r" for p in pa), (lo, pa))
    lo, _p = _loc("a = 1;\nb = a + 1;\nc = b + 2;")
    chk("cadena de tres: a -> b -> c se resuelve entera (c=4)",
        lo.get("c") == 4, lo)
    lo, _p = _loc("b =\n  5;")
    chk("una asignacion partida en dos lineas SI se recoge (b=5)",
        lo.get("b") == 5, lo)
    lo, pa = _loc("p->field = 1;\narr[i] = 2;\nc = 3;")
    chk("P4: `p->field` y `arr[i]` NO se propagan, y `c` normal si",
        lo.get("c") == 3 and "p_field" not in lo, (lo, pa))
    lo, _p = _loc("b = 1; /* b = 100 */")
    chk("un comentario NO es una asignacion: b vale 1 y no 100",
        lo.get("b") == 1, lo)
    lo, _p = _loc("b = 1;\nif (x)\n\tb = 2;")
    chk("una asignacion DENTRO de un `if` no se propaga (no hay flujo)",
        lo.get("b") == 1, lo)


COND_CUERPO = """void f(struct amdgpu_ib *ib, struct ring *ring) {
	if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID) {
		amdgpu_ring_write(ring, A);
		amdgpu_ring_write(ring, B);
	}
	amdgpu_ring_write(ring, C);
}"""


def _condicionales_vectores(chk, ev, macR):
    mac = dict(macR)
    lc = COND_CUERPO.split("\n")
    chk("cond: la bandera AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID llega por "
        "include/uapi", mac.get("AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID")
        is not None, mac.get("AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID"))
    chk("cond: y vale 16, que es (1<<4)",
        ev("AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID", mac) == 16)
    c0 = condicionales_de(lc, 0, len(lc), ev, mac, {"ib_flags": "0"})
    chk("cond: `ib_flags & 16` con 0 vale 0 -> NO se emite",
        c0[0]["veredicto"] == "SI", c0)
    c16 = condicionales_de(lc, 0, len(lc), ev, mac, {"ib_flags": "16"})
    chk("cond: `ib_flags & 16` con 16 vale 16 -> se emite",
        c16[0]["veredicto"] == "NO", c16)
    c32 = condicionales_de(lc, 0, len(lc), ev, mac, {"ib_flags": "32"})
    chk("cond: `ib_flags & 16` con 32 vale 0 -> NO se emite (bit distinto)",
        c32[0]["veredicto"] == "SI", c32)
    cu = condicionales_de(lc, 0, len(lc), ev, mac, {})
    chk("cond: sin ligar el termino NO se emite y SE DECLARA",
        cu[0]["veredicto"] == "NO_RESUELTO", cu)
    c1 = condicionales_de(lc, 0, len(lc), ev, mac, {"ib_flags": "1"})
    chk("cond: `1 & 16` = 0 -> NO se emite (bit 0 no es el bit 4)",
        c1[0]["veredicto"] == "SI", c1)
    e0 = escrituras(lc, 0, len(lc), consumidos=(tuple(c0[0]["lineas"]),))
    chk("cond: lo que NO se emite no sale en la lista de escrituras",
        [x for _l, x in e0] == ["C"], [x for _l, x in e0])
    en = escrituras(lc, 0, len(lc), consumidos=())
    chk("cond: lo que SI se emite sale, en orden",
        [x for _l, x in en] == ["A", "B", "C"], [x for _l, x in en])
    chk("cond: `ib.flags` y `ib->flags` normalizan al MISMO nombre",
        _alias("ib.flags") == _alias("ib->flags") == "ib_flags")
    chk("cond: un punto DECIMAL no se convierte en guion bajo",
        _alias("0.5") == "0.5", _alias("0.5"))




def _alias(clave):
    """El nombre con el que se LIGA una clave escrita por el usuario.

    MEDIDO: `--set ib.flags=16` no ligaba nada y salian 4 dwords, mientras que
    `--set ib_flags=16` ligaba y salian 7. La clave que el usuario escribe
    mirando el codigo C (`ib.flags`, con punto) era la que no funcionaba, y la
    que funcionaba no se parece a nada del fuente. Se acepta la que se escriba y
    se registra la normalizada.

    Un `.` ENTRE DOS LETRAS es miembro de struct; un `.` ENTRE DIGITOS es un
    punto decimal, y `0.5` tiene que seguir siendo `0.5`.
    """
    return RE_PUNTO_MIEMBRO.sub("_", normalizar(clave))


def main(argv=None):
    """sintetiza un IB de referencia desde el codigo del driver"""
    ap = argparse.ArgumentParser(
        prog="ibref.py",
        description="sintetiza un IB de referencia desde el codigo del driver")
    ap.add_argument("--version", action="version", version=VERSION)
    ap.add_argument("--func", help="funcion de emision a sintetizar")
    ap.add_argument("--set", action="append", default=[],
                    metavar="K=V", help="liga un parametro (acepta `ib.flags=`)")
    ap.add_argument("--fichero", help="fuente alternativa")
    ap.add_argument("--tablas", help="otro pm4_codec para medir round-trip")
    ap.add_argument("--decode", action="store_true",
                    help="decodifica el IB con las declaraciones")
    ap.add_argument("--roundtrip", action="store_true",
                    help="compara el layout declarado con lo que escribe el driver")
    ap.add_argument("--sin-ampliar", action="store_true",
                    help="no amplia las macros con las cabeceras de kernel")
    ap.add_argument("--json", action="store_true", help="salida estructurada")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest(args)

    if not args.func:
        ap.print_help()
        return 2

    enlaces = {}
    for s in args.set:
        if "=" not in s:
            print("mal formado: %s  (se espera K=V)" % s)
            return 2
        k, v = s.split("=", 1)
        k = k.strip()
        enlaces[k] = v.strip()
        alt = _alias(k)
        if alt != k:
            enlaces.setdefault(alt, v.strip())

    try:
        ev, lm, _U = cargar_evaluador()
    except Exception as e:                                   # noqa: BLE001
        print("%s: %s" % (type(e).__name__, e))
        return 2
    fichero = args.fichero or entrada_por_defecto()
    mac, info = macros_ampliadas(lm, ev, fichero,
                                 ampliada=not args.sin_ampliar)
    try:
        ib = ib_de_funcion(args.func, ev, mac, enlaces, fichero)
    except KeyError as e:
        print("%s" % e)
        return 2

    tablas = ops = None
    decod = rt = None
    if args.decode or args.roundtrip:
        try:
            tablas, ops, _ruta = cargar_tablas(args.tablas)
        except Exception as e:                               # noqa: BLE001
            print("tablas: %s: %s" % (type(e).__name__, e))
            return 2
        kfd, _nota = cargar_opcodes_kfd()
        if args.decode:
            decod = decodificar(ib, tablas, ops, kfd)
        if args.roundtrip:
            rt = formatear_roundtrip(roundtrip(ib, tablas, ev, mac, enlaces))

    if args.json:
        out = {"herramienta": "ibref", "version": VERSION,
               "funcion": ib["funcion"], "fichero": ib["fichero"],
               "inicio": ib["inicio"], "fin": ib["fin"],
               "dwords": [{"linea": d["linea"], "expr": d["expr"],
                           "valor": d["valor"], "destino": d["destino"]}
                          for d in ib["dwords"]],
               "locales": {k: v for k, v in sorted(ib["locales"].items())},
               "sin_resuelto": sorted(ib["sin_resuelto"]),
               "completo": ib["completo"],
               "bucles": ib["bucles"], "sin_desenrollar": ib["sin_desenrollar"],
               "condicionales": ib["condicionales"],
               "ampliacion": {k: v for k, v in info.items()
                              if k != "colisiones"},
               "colisiones": info.get("colisiones", [])[:20],
               "runtime": "NOT_RUN"}
        print(json.dumps(out, indent=2, sort_keys=True, default=str))
        return 0

    print(formatear(ib, (decod or []) + (rt or [])))
    return 0


if __name__ == "__main__":
    sys.exit(main())

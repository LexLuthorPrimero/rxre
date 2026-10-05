#!/usr/bin/env python3
# rxre.py -- RX550 Reverse Engineering Intelligence & Tool Orchestrator
#
# MISION
# ------
# Que ningun agente tenga que recordar si existe una herramienta, donde esta, que
# acepta, que produce ni cuando conviene. Se pregunta por una CAPACIDAD y se
# recibe un pipeline; se comprueba una herramienta y se recibe un veredicto.
#
# QUE ES Y QUE NO ES
# -----------------
# NO reimplementa ninguna herramienta. No las mete dentro de un ejecutable. Es un
# catlogo ejecutable + descubridor + adaptador + orquestador.
#
#     rxre
#      |
#      +-- registro     -> tools/toolreg.py  (UNA sola lista, no dos)
#      +-- adaptador    -> invoca, normaliza, cachea
#      +-- puerta       -> decide si algo se ejecuta o NO
#
# El registro NO se duplica. `toolreg` es la unica verdad sobre que herramientas
# existen; `rxre` consulta su matriz. Dos catalogos divergentes serian
# exactamente el problema que esto elimina.
#
# LA PUERTA, QUE ES LA PARTE QUE NO ES ADORNAMENTO
# -----------------------------------------------
# La pregunta importante no es "que herramienta uso" sino "que herramienta NO
# debo usar todavia". Y hay tres formas de responder que sin nuestra:
#
#   1. GANANCIA DE INFORMACION   la evidencia estatica ya basta -> NO ejecutar
#   2. REVERSIBILIDAD            no es reversible -> AUTORIZACION EXPLICITA
#   3. FRONTERA                  toca la GPU integrada -> BLOQUEADO, sin excepcion
#
# La tercera no es una politica: es un hecho de esta maquina, y el HUB lo lee de
# sysfs. Si un dia cambia el reparto de, la puerta cambia sola.
#
# EL RESULTADO ES UNA SUMA, Y EL ESTADO DE SALIDA ES UN CANAL MAS
# ---------------------------------------------------------------
# Regla de §26, que aqui es estructural y no moral:
#
#     OK(payload)                  se ejecuto y el resultado es utilizable
#     LIMITADO(payload, motivo)    se ejecuto y el resultado esta recortado
#     DESCONOCIDO(motivo)          no se sabe; NUNCA se rellena con un valor
#     SIN_EVIDENCIA                no hay quien lo diga
#
# Un exit 0 no significa que el resultado valga, y un `None` no es un cero.
#
# ALCANCE
# -------
# SOLO LECTURA por defecto. No instala, no compila contra nada, no escribe
# ficheros salvo los de cache, y no toca 0000:00:02.0 ni la salida de consola.

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "1.0.0"

# ===========================================================================
# 1. INDICE DE CAPACIDADES
#
# Que sabe HACER cada familia de herramienta. Esto es una DECLARACION y va
# marcada; lo que la herramienta HAGA se comprueba con `rxre probe` y se
# guarda aparte en CAPABILITY_EVIDENCE.
#
# campos:
#   (herramienta, [capacidades], entrada, salida, formato,
#    coste, riesgo, solo_lectura, pide_root, pide_gpu, pide_runtime,
#    reproducible, limitaciones, TOCA_INTEGRADA)
#
# EL ULTIMO CAMPO ES EL QUE IMPORTA Y EL QUE FALTAVA.
#
# MEDIDO: la primera version tenia 13 campos y usaba `solo_lectura` para la
# puerta de frontera. Eso esta MAL, y el vector lo enseño: `dynamic_debug`
# escribe en el sistema (tracefs) y la puerta lo frenaba como si estuviera
# tocando la GPU integrada. Son dos cosas distintas:
#
#   escribe_en_el_sistema   necesita autorizacion, y se puede autorizar
#   toca_la_integrada       NO se puede autorizar. La frontera dura.
#
# Confundirlas hacia que la frontera, que es innegociable, se wore como si fuera
# una politica mas. Y hacia lo contrario: una herramienta que SI toque la
# integrada pasaria por estar autorizada. Ninguna de las dos es aceptable.
# ===========================================================================
CAP = [
    ('rg',['FIND_DEF', 'FIND_TEXT'],'regex sobre texto',
     'lineas','texto','BAJO','NINGUNO',True,False,False,False,
     True,
     'no entiende de C: encuentra tambien lo que esta en comentarios',
     False),
    ('spatch',
     ['FIND_DEF', 'FIND_WRITER', 'FIND_READER', 'REWRITE'],
     'semilla .cocci sobre fuente','diff parcheado','diff',
     'MEDIO','NINGUNO',True,False,False,False,True,
     'mete semantica: una semilla mala produce un parche que no compila',
     False),
    ('ctags',['FIND_DEF', 'INDEX_SYMBOLS'],'fuente C','tags',
     'json','BAJO','NINGUNO',True,False,False,False,True,
     'indice, no semantica: no sabe quien LLAMA a quien',False),
    ('clang',
     ['FIND_DEF', 'FIND_WRITER', 'CALL_GRAPH', 'TYPECHECK'],
     'fuente C + headers','AST','json/text','MEDIO','NINGUNO',
     True,False,False,False,True,
     'necesita la configuracion de compilacion real; si falta un header, calla',
     False),
# MEDIDO: `spatch` estaba DUPLICADA, y la segunda fila era un subconjunto
# estricto de la primera: [FIND_WRITER, REWRITE] esta contenido en
# [FIND_DEF, FIND_WRITER, FIND_READER, REWRITE].  Una fila que no anade nada
# hace que el enrutado tenga DOS respuestas para lo mismo, y cual gana
# depende del orden del fichero y no de una regla.
    ('gcc',['TYPECHECK', 'COMPILE'],'fuente C','objeto','ELF',
     'MEDIO','NINGUNO',True,False,False,False,True,
     'compilar NO prueba que el codigo sea correcto (§26)',
     False),
    ('readelf',['ELF_STRUCTURE', 'BINARY_DIFF'],'ELF',
     'secciones','text','BAJO','NINGUNO',True,False,False,
     False,True,'',False),
    ('llvm-dwarfdump',
     ['STRUCT_OFFSET', 'SOURCE_BINARY_CORRELATE', 'ELF_STRUCTURE'],
     'ELF con DWARF','tipos','text','MEDIO','NINGUNO',True,
     False,False,False,True,
     'sin DWARF no hay tipos: many binarios vienen recortados',
     False),
    ('pahole',['STRUCT_OFFSET'],'vmlinux o .ko','estructuras',
     'text','MEDIO','NINGUNO',True,False,False,False,True,
     'muestra el TAMAÑO de la struct, no el offset de un campo en un build distinto',
     False),
    ('addr2line',['SOURCE_BINARY_CORRELATE'],'ELF + direccion',
     'fichero:linea','text','BAJO','NINGUNO',True,False,False,
     False,True,'',False),
    ('objdump',['DISASM_NATIVE'],'ELF','instrucciones x86',
     'text','BAJO','NINGUNO',True,False,False,False,True,
     'x86: NO sirve para el codigo de la GPU',False),
    ('llvm-objdump',
     ['DISASM_NATIVE', 'ISA_ENCODE', 'ISA_DECODE'],
     'ELF o objeto amdgcn','instrucciones','text','BAJO',
     'NINGUNO',True,False,False,False,True,
     'MEDIDO 1185: desensambla AMDGPU SOLO sobre objetos, no sobre bytes sueltos',
     False),
    ('llvm-mc',['ISA_ENCODE'],'texto ISA','objeto','ELF',
     'BAJO','NINGUNO',True,False,False,False,True,
     "MEDIDO 1185: ENSAMBLA pero NO desensambla ('not yet supported')",
     False),
    ('llvm-mc',['ISA_DECODE'],'texto ISA','objeto','ELF',
     'BAJO','NINGUNO',True,False,False,False,True,
     'PROBADO QUE NO SIRVE para decodificar. Se queda como evidencia negativa',
     False),
    ('clrxdisasm',['ISA_DECODE'],'ISA GCN','instrucciones',
     'text','MEDIO','NINGUNO',True,False,False,False,True,
     'AUSENTE en esta maquina (1185). Serian el desensamblado GFX8 real',
     False),
    ('rga',['ISA_DECODE', 'ISA_ANALYZE'],'shader',
     'ISA + estadisticas','text','ALTO','NINGUNO',True,False,
     False,False,False,
     'AUSENTE. Y no esta claro que su version cubra Polaris12',
     False),
    ('bpftrace',['RUNTIME_TRACE'],'script','salida','text',
     'MEDIO','MEDIO',False,True,True,True,True,
     'escritura en el sistema: reversible a medias',False),
    ('trace-cmd',['RUNTIME_TRACE'],'eventos','traza','text',
     'MEDIO','BAJO',True,True,True,True,True,
     'solo observa; es la opcion MAS SEGURA del bloque de runtime',
     False),
    ('perf',['RUNTIME_COUNT'],'eventos','muestras','text',
     'MEDIO','BAJO',True,False,True,True,True,'',False),
    # MEDIDO: `dynamic_debug` no es un binario de PATH. Es el fichero
    # /sys/kernel/debug/dynamic_debug/control, y sin privilegios da EACCES, no
    # ENOENT.  Escrito como nombre pelado, `estado_de` lo daba AUSENTE, que es
    # FALSO: existe, pide privilegio y se revierte escribiendo encima. Un
    # instrumento reportado como ausente no se planifica, y se pierde la
    # capacidad RUNTIME_TRACE mas barata y mas reversible que hay.
    ('/sys/kernel/debug/dynamic_debug/control',['RUNTIME_TRACE'],
     'archivo de debug','log','text','BAJO','MEDIO',False,True,True,True,
     True,
     'ESCRIBE en el kernel: activa printk. Se puede reactivar',
     False),
    ('drgn',['RUNTIME_INSPECT', 'STRUCT_OFFSET_LIVE'],
     'vmlinux en vivo','valor de un simbolo','text','MEDIO',
     'BAJO',True,True,True,True,True,
     'el mas valioso para verificar una struct EN EL KERNEL VIVO',
     False),
    ('radeontop',['RUNTIME_COUNT'],'GPU','uso','text','BAJO',
     'NINGUNO',True,False,True,True,True,'',False),
    ('rocm-smi',['RUNTIME_CLOCK', 'RUNTIME_COUNT'],'GPU',
     'relojes','text','BAJO','NINGUNO',True,False,True,True,
     True,'',False),
    ('tools/ibref.py',['PM4_SYNTH', 'IB_DECODE'],
     'fuente del driver','IB sintetizada','json/text','BAJO',
     'NINGUNO',True,False,False,False,True,
     'PROBADA_PARCIAL: 77 de 116 vectores (1183)',False),
    ('tools/mmio.py',['MMIO_READ', 'REG_DECODE'],
     'captura de MMIO','valores','json','BAJO','NINGUNO',True,
     False,False,False,True,
     'decodificacion INVERSA: necesita dos capturas con distinto valor',
     False),
    ('tools/layoutcross.py',['LAYOUT_CROSS'],'layout + IB',
     'comparacion','text','BAJO','NINGUNO',True,False,False,
     False,True,'',False),
    ('tools/toolreg.py',['TOOL_DISCOVER'],'arbol','registro',
     'text','BAJO','NINGUNO',True,False,False,False,True,
     'el registro: UNA sola lista de herramientas',False),
]

DD_CONTROL = "/sys/kernel/debug/dynamic_debug/control"

# ---------------------------------------------------------------------------
# 1b. CAPACIDADES REFUTADAS: LA EVIDENCIA NEGATIVA NO SE ENRUTA
#
# MEDIDO 2026-10-04.  Este es el defecto mas caro de esta tabla hasta ahora,
# y no lo produjo un fallo de ejecucion: lo produjo que la tabla ESTUVIERA
# bien escrita.
#
# `llvm-mc` tenia DOS filas. Una decia "ENSAMBLA pero NO desensambla"; la otra le
# adjudicaba `ISA_DECODE` con la nota "PROBADO QUE NO SIRVE para decodificar".
# LAS DOS FILAS SON CIERTAS. El problema es que la segunda, al estar en la
# columna de capacidades, la convierte en ENRUTABLE: una pregunta sobre
# desensamblado GFX8 le llegaba a la herramienta ya probada inútil, y el plan
# salia `OK` con pasos que no podian funcionar.
#
#     un resultado negativo escrito como capacidad es un plan que se contradice
#
# La evidencia no se borra —es informacion, y va con su medicion— pero se separa
# de lo que se enruta. Y cada refutacion declara POR QUE se sostiene, para que
# se pueda auditar en vez de creerla.
# ---------------------------------------------------------------------------
CAP_REFUTADA = {
    ("llvm-mc", "ISA_DECODE"):
        "MEDIDO 1185: llvm-mc ensambla y responde 'not yet supported' al "
        "desensamblar. Cubre ISA_ENCODE y nada mas",
    ("llvm-objdump", "ISA_DECODE_DESDE_BYTES"):
        "MEDIDO 1185: decodifica SOLO sobre un objeto ELF. Sobre bytes sueltos "
        "no hay formato, y por eso sigue faltando un desensamblador GFX8 real",
    (DD_CONTROL, "FIND_DEF"):
        "MEDIDO: es una interfaz de traza del kernel, no un indice de codigo",
}


def refutada(herramienta, capacidad):
    """Motivo si esa capacidad esta REFUTADA para esa herramienta; '' si no."""
    return CAP_REFUTADA.get((herramienta, capacidad), "")


def capacidades_ruteables(herramienta):
    """Lo que la herramienta PUEDE hacer, descontando lo probadamente imposible.

    Antes esto era `CAP[i][1]` a pelo, y por eso una refutacion viajaba como si
    fuera una capacidad. Ahora la fila se conserva entera —con su nota, que es
    la evidencia— y lo que se enruta es lo que queda.
    """
    for f in CAP:
        if f[0] == herramienta:
            return [c for c in f[1] if not refutada(herramienta, c)]
    return []


def filas_duplicadas():
    """Herramientas con la MISMA fila repetida.

    MEDIDO: `spatch` estaba duplicada, y la segunda fila era un subconjunto
    estricto de la primera. Dos filas iguales hacen que el enrutado tenga dos
    respuestas para lo mismo, y gane la que este antes en el fichero.

    Y `llvm-mc` tiene DOS filas legitimas con capacidades DISTINTAS, y eso NO es
    duplicacion. Por eso la clave lleva las capacidades dentro: repetir la
    herramienta no es repetir la fila.
    """
    vistos, repes = set(), []
    for f in CAP:
        clave = (f[0], tuple(f[1]))
        if clave in vistos:
            repes.append(f[0])
        vistos.add(clave)
    return repes


COSTO_ORDEN = {"BAJO": 0, "MEDIO": 1, "ALTO": 2, "MUY_ALTO": 3}

# ===========================================================================
# 2. PUERTAS: CUANDO NO EJECUTAR
# ===========================================================================
PUERTA_FRONTERA = "FRONTERA_INTEL"
PUERTA_GANANCIA = "GANANCIA_INFORMACION"
PUERTA_REVERSIBILIDAD = "REVERSIBILIDAD"


def limites_de_la_maquina():
    """(integrada, discreta) leyendo sysfs. NO es una politica: es un hecho."""
    def leer(card):
        base = "/sys/class/drm/%s/device" % card
        v = d = None
        try:
            v = open(os.path.join(base, "vendor")).read().strip()
            d = open(os.path.join(base, "device")).read().strip()
        except OSError:
            return None
        return "%s:%s" % (v, d)
    return {"integrada": leer("card0"), "discreta": leer("card1")}


def _campos_de(herramienta):
    """(solo_lectura, pide_runtime, toca_integrada) de una herramienta."""
    for f in CAP:
        if f[0] == herramienta:
            return f[7], f[10], f[13]
    return None, None, None


def puerta(herramienta, evidencia_estatica_suficiente=False,
            autorizacion_explicita=False, limites=None):
    """La puerta. Devuelve (puede, motivo, puerta_que_lo_freno).

    LAS TRES, Y POR QUE ESTAN EN ESE ORDEN.

    MEDIDO, y el orden lo corrigio un vector: la primera version frenaba
    `dynamic_debug` con la FRONTERA. Ese outil escribe en tracefs, y tracefs no
    es la GPU integrada. Confundir "escribe en el sistema" con "toca la
    integrada" hacia dos cosas malas a la vez:

      - la frontera dura, que es INNEGOCIABLE, se wore como una politica mas
        que se puede desactivar con una autorizacion
      - una herramienta que SI tocara la integrada habria pasado por el mismo
        hueco, autorizandola. Y las dos cosas a la vez.

    Asi que son dosPuertas distintas, con salida distinta:

      FRONTERA        toca_integrada  -> NO. No hay salida. No hay autorizacion.
      GANANCIA        pide_runtime y la estatica ya discrimina -> NO. Sin riesgo.
      REVERSIBILIDAD  escribe y sin autorizacion -> NO. Con autorizacion, SI.
    """
    solo_lectura, pide_runtime, toca_integrada = _campos_de(herramienta)
    if solo_lectura is None:
        return (False, "no esta declarada en el catalogo: no se inventa su "
                       "seguridad", PUERTA_FRONTERA)
    # 1. FRONTERA. Primero, y sin salida.
    if toca_integrada:
        return (False,
                "toca 0000:00:02.0 (GPU integrada del procesador). La frontera "
                "dura no tiene autorizacion que la levante",
                PUERTA_FRONTERA)
    # 2. GANANCIA DE INFORMACION. Un runtime que no anade informacion solo anade
    #    riesgo. Y gana a la autorizacion: autorizar no compra informacion.
    if pide_runtime and evidencia_estatica_suficiente:
        return (False,
                "la evidencia estatica ya discrimina: el runtime no aportaria "
                "informacion nueva, solo riesgo",
                PUERTA_GANANCIA)
    # 3. REVERSIBILIDAD.
    if not solo_lectura and not autorizacion_explicita:
        return (False,
                "escribe en el sistema y no consta autorizacion explicita",
                PUERTA_REVERSIBILIDAD)
    return (True, "pasa las tres puertas", None)


# ===========================================================================
# 3. OBJETIVO -> CAPACIDADES
#
# De una pregunta en lenguaje natural a una CADENA de capacidades. La cadena es
# una DECLARACION: si la pregunta no encaja con ninguna, se dice DESCONOCIDO y
# no se inventa un pipeline.
# ===========================================================================
PATRONES = [
    (("escribe", "writer", "quien escribe", "asigna"), ["FIND_DEF", "FIND_WRITER"]),
    (("llama", "caller", "quien llama", "callers", "call graph"),
     ["FIND_DEF", "CALL_GRAPH"]),
    (("offset", "campo de", "struct", "tamano de"),
     ["STRUCT_OFFSET"]),
    (("gfx8", "isa", "shader", "codigo nativo de la gpu", "cndmask"),
     ["ISA_DECODE"]),
    (("pm4", "packet", "paquete", "ib", "dword del ring"),
     ["PM4_SYNTH", "IB_DECODE"]),
    (("mmio", "registro", "register"), ["MMIO_READ"]),
    (("layout", "bits", "campo de un opcode"), ["LAYOUT_CROSS"]),
    (("en vivo", "runtime", "funciona de verdad", "discriminante"),
     ["RUNTIME_TRACE"]),
]


def _tiene(texto, clave):
    """Si la clave aparece como PALABRA, no como pedazo de otra.

    MEDIDO, y era un bug de verdad: la clave "ib" (el ring buffer) casa DENTRO
    de "reconocible", porque `ci-b-le` contiene "ib". Con subcadena simple,
    "nada reconocible aqui" se enrutaba a PM4/IB_DECODE: una respuesta
    CONFIENTE Y FALSA.

    Con dos letras la subcadena no distingue "ib" de "cibl". Y en un orquestador,
    enrutar mal en silencio es peor que no enrutar: el agente recibe un pipeline
    plausible para una pregunta que no ha hecho.
    """
    return re.search(r"(?<![A-Za-z0-9_])" + re.escape(clave) +
                     r"(?![A-Za-z0-9_])", texto) is not None


def objetivo_a_capacidades(texto):
    """(capacidades,Vertices, plan_texto). Lista vacia si no se reconoce."""
    t = (texto or "").lower()
    caps, pasos = [], []
    for (claves, c) in PATRONES:
        if any(_tiene(t, k) for k in claves):
            caps.extend(c)
            pasos.append(c)
    if not caps:
        return [], 0, []
    vistos, orden = set(), []
    for c in caps:
        if c not in vistos:
            vistos.add(c)
            orden.append(c)
    return orden, len(pasos), orden


def candidatos_para(capacidades):
    """[(herramienta, cubre, coste, estado)] ordenada por cobertura y coste.

    MEDIDO: antes comparaba `c in f[1]`, la columna CRUDA. Con eso una capacidad
    REFUTADA seguia cuenta como cubierta y el plan salia `OK` apuntando a una
    herramienta que ya se habia probado inutil.  Ahora usa
    `capacidades_ruteables`, que resta lo refutado, y por eso una herramienta
    puede quedarse CON CERO capacidades ruteables sin desaparecer del
    catalogo: la fila sigue ahi, con su nota, que es la evidencia.
    """
    out = []
    for f in CAP:
        (h, cs) = f[0], capacidades_ruteables(f[0])
        coste, limi = f[5], f[12]
        cubre = [c for c in capacidades if c in cs]
        if not cubre:
            continue
        # Se prefiere la herramienta que cubre MAS, y luego la mas barata.
        out.append((h, cubre, coste, limi))
    out.sort(key=lambda x: (-len(x[1]), COSTO_ORDEN.get(x[2], 9)))
    return out


def pipeline(objetivo, evidencia_estatica_suficiente=False,
             autorizacion_explicita=False, limites=None):
    """El plan. Cada paso lleva su puerta, y algunos pasos quedan frenados."""
    caps, n_pat, _o = objetivo_a_capacidades(objetivo)
    if not caps:
        return {"estado": "DESCONOCIDO",
                "motivo": "ningun patron conocido para esa pregunta: no se "
                          "inventa un pipeline",
                "capacidades": [], "pasos": []}
    pasos, vistos = [], set()
    for h, cubre, coste, limi in candidatos_para(caps):
        if h in vistos:
            continue
        vistos.add(h)
        puede, motivo, frenada = puerta(
            h, evidencia_estatica_suficiente, autorizacion_explicita, limites)
        pasos.append({"herramienta": h, "cubre": cubre, "coste": coste,
                      "puede": puede, "motivo": motivo,
                      "frenada_por": frenada, "limitacion": limi})
    pasos.sort(key=lambda p: (not p["puede"],
                              COSTO_ORDEN.get(p["coste"], 9)))
    return {"estado": "OK", "objetivo": objetivo, "capacidades": caps,
            "pasos": pasos}


# ===========================================================================
# 4. DESCUBRIMIENTO: se apoya en toolreg, no lo duplica
# ===========================================================================
def _importar_toolreg():
    import importlib.util
    ruta = os.path.join(RAIZ, "tools", "toolreg.py")
    spec = importlib.util.spec_from_file_location("rxre_toolreg", ruta)
    m = importlib.util.module_from_spec(spec)
    sys.modules["rxre_toolreg"] = m
    spec.loader.exec_module(m)
    return m


# ---------------------------------------------------------------------------
# 4b. RESOLUCION DE EXISTENCIA, Y LA INTERFAZ QUE HACE FALTA DE `toolreg`
#
# MEDIDO 2026-10-04, y el motivo de que esto exista: la version anterior de
# estas lineas llamaba `tr.matriz_completa()`, una funcion que existe en un
# `toolreg.py` de 473 lineas.  El `toolreg.py` que esta commiteado —y que es
# el bueno— tiene 1208 lineas, 14 checks, y CERO `def` en comun con aquel.
#
# Los dos ficheros se llamaban igual y uno habia pisado al otro sin que nadie
# lo notara.  Por eso esta capa no llama "la primera funcion que exista": llama
# una INTERFAZ, comprueba que este, y si no esta, lo dice con el nombre de lo
# que falta en vez de reventar con AttributeError dentro de un selftest.
#
# Y por que el nombre no basta para decidir la existencia: `toolreg` inventaria
# lo que esta EN EL ARBOL (7 directorios declarados, 215 entradas); no sabe
# nada de los binarios de PATH.  Son dos universos disjuntos y una herramienta
# se escribe en uno de los dos segun lleve o no la ruta.  Por eso la tabla CAP
# escribe `tools/mmio.py` y `rg`, y no `mmio` para las dos.
# ---------------------------------------------------------------------------
TOOLREG_INTERFAZ = ("inventory", "run_selftests", "TOOL_DIRS")


def _toolreg_interfaz_ok(tr):
    faltan = [n for n in TOOLREG_INTERFAZ if not hasattr(tr, n)]
    return (not faltan), faltan


def _arbol_de_toolreg():
    """(set de nombres en el arbol, metadata) leidos del registro. Cacheado.

    El registro es la verdad sobre el ARBOL. `rxre` no lo vuelve a recorrer: si
    lo hiciera, habria dos catalogo, y dos catalogos divergentes son
    exactamente el problema que este fichero existe para eliminar.
    """
    global _ARBOL_CACHE
    if _ARBOL_CACHE is None:
        tr = _importar_toolreg()
        ok, faltan = _toolreg_interfaz_ok(tr)
        if not ok:
            raise RuntimeError(
                "tools/toolreg.py no cumple la interfaz que rxre necesita; "
                "le faltan: %s.  No se adivina: el registro es la verdad sobre "
                "que herramientas hay." % ", ".join(faltan))
        meta = {}
        for t in tr.inventory(tr.REPO_ROOT):
            meta[t.name] = {"ruta": t.path, "dir": t.dir, "proposito": t.purpose,
                            "en_docs": t.in_docs, "declara_limites":
                            t.declares_limits, "declara_seguridad":
                            t.declares_safety, "arg_selftest": t.selftest_arg}
        _ARBOL_CACHE = meta
    return _ARBOL_CACHE


_ARBOL_CACHE = None


def estado_de(herramienta):
    """En que universo esta la herramienta, y si existe.

    `EN_ARBOL`  la autoramos nosotros; `toolreg` la ve y la declara.
    `EN_PATH`   la instalo el sistema; el registro no la conoce y no debe.
    `AUSENTE`   no esta en ninguno de los dos.  ESTO NO ES `NO_APLICA`:
                `NO_APLICA` es "no hace falta", `AUSENTE` es "hace falta y no
                esta", y confundirlos es como se pierde una capacidad sin que
                nadie lo note.
    """
    if "/" in herramienta:
        nombre = os.path.basename(herramienta)
        meta = _arbol_de_toolreg()
        if nombre in meta:
            return {"herramienta": herramienta, "estado": "EN_ARBOL",
                    "universo": "arbol", "ruta": meta[nombre]["ruta"],
                    "version": None, "en_docs": meta[nombre]["en_docs"]}
        # El registro no la ve.  O no existe, o esta FUERA de TOOL_DIRS, que es
        # un hallazgo distinto y no se puede reportar como `AUSENTE` a secas.
        existe = os.path.isfile(os.path.join(RAIZ, herramienta))
        return {"herramienta": herramienta,
                "estado": "EN_ARBOL_NO_REGISTRADA" if existe else "AUSENTE",
                "universo": "arbol", "ruta": herramienta if existe else None,
                "version": None, "en_docs": None}
    ruta = shutil.which(herramienta)
    return {"herramienta": herramienta, "estado": "EN_PATH" if ruta
            else "AUSENTE", "universo": "path", "ruta": ruta,
            "version": None, "en_docs": None}


# ===========================================================================
# 5. PROBE: bajar de PRESENTE_SIN_PROBAR a capacidad VERIFICADA
#
# No basta con que exista. Se le da un ENTRADA DE PRUEBA y se mira que la
# SALIDA sea la esperada. Sin eso, el estado honesto sigue siendo
# PRESENTE_SIN_PROBAR, y eso es lo que se registra.
# ===========================================================================
PRUEBAS = [
    # (herramienta, capability, argv, se_espera_en_la_salida, hace falta GPU)
    ("rg", "FIND_TEXT", ["rg", "--version"], "ripgrep", False),
    ("llvm-mc", "ISA_ENCODE",
     ["llvm-mc", "-triple=amdgcn", "-mcpu=gfx900", "-filetype=obj",
      "-", "-o", "/dev/null"], None, False),
    ("llvm-objdump", "ISA_DECODE",
     ["llvm-objdump", "--version"], "LLVM", False),
    ("addr2line", "SOURCE_BINARY_CORRELATE", ["addr2line", "--version"],
     "GNU", False),
    # MEDIDO: `pahole --version` imprime `v1.30` y nada mas. La expectativa
    # era "pahole", y el probe daba FALLO con rc=0 y evidencia `v1.30`.
    #
    # Un probe que falla POR EL MOTIVO EQUIVOCADO no enseña nada: entrena al
    # que lo lee a desconfiar de probes. O se corrige la expectativa a lo que
    # la herramienta dice de verdad, o se declara que no hay forma de
    # distinguirla de otra. Aqui se corrige, y se deja escrito por que.
    ("pahole", "STRUCT_OFFSET", ["pahole", "--version"], "v1.", False),
]


def _poder_ejecutar(argv, entrada=None):
    try:
        p = subprocess.run(argv, input=entrada, capture_output=True, timeout=60)
        return p.returncode, p.stdout.decode("utf-8", "replace"), \
            p.stderr.decode("utf-8", "replace")
    except FileNotFoundError:
        return 127, "", "no esta"
    except Exception as e:                                     # noqa: BLE001
        return 125, "", "%s: %s" % (type(e).__name__, e)


def probe(herramienta=None):
    """Ejecuta la PRUEBA de cada herramienta y registra la evidencia."""
    filas = []
    for (h, cap, argv, espera, gpu) in PRUEBAS:
        if herramienta and h != herramienta:
            continue
        est = estado_de(h)
        if est["estado"] == "AUSENTE":
            filas.append({"herramienta": h, "capacidad": cap,
                          "verificacion": "AUSENTE",
                          "evidencia": "no esta en el PATH"})
            continue
        entrada = b"v_mov_b32_e32 v0, s0\n" if h == "llvm-mc" else None
        rc, out, err = _poder_ejecutar(argv, entrada)
        if h == "llvm-mc":
            ok = rc == 0
            ev = "ensambla AMDGPU: rc=%d" % rc
        else:
            ok = rc == 0 and espera and espera in (out + err)
            ev = "rc=%d salida=%r" % (rc, (out + err).strip()[:40])
        filas.append({"herramienta": h, "capacidad": cap,
                      "verificacion": "VERIFICADA" if ok else "FALLO",
                      "evidencia": ev,
                      "version": est.get("version")})
    return filas


# ===========================================================================
# 6. CACHE con procedencia
# ===========================================================================
CACHE_DIR = os.path.join(RAIZ, "08-ARQUITECTURA", "artifacts", "RXRE-CACHE")


def cache_put(clave, valor):
    """Guarda con procedencia. Si el cache no es escribible, lo DICE."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        import hashlib
        h = hashlib.sha256(clave.encode()).hexdigest()[:16]
        ruta = os.path.join(CACHE_DIR, h + ".json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"clave": clave, "valor": valor}, f)
        return True, ruta
    except OSError as e:
        return False, "cache no escribible: %s" % e


def cache_get(clave):
    try:
        import hashlib
        h = hashlib.sha256(clave.encode()).hexdigest()[:16]
        ruta = os.path.join(CACHE_DIR, h + ".json")
        with open(ruta, encoding="utf-8") as f:
            return json.load(f)["valor"]
    except (OSError, ValueError, KeyError):
        return None


# ===========================================================================
# 6b. REGISTRO EXTENDIBLE
#
# El requisito es concreto: "si manana aparece una herramienta nueva, no hay
# que modificar el comportamiento". Eso se cumple con un fichero de registro
# que se lee AL ARRANQUE y se anade sin tocar el codigo.
#
# MEDIDO, y por que NO se reescribe CAP: si las herramientas aadidas vivieran en
# el codigo, cada alta seria un cambio de codigo y habria que revalidar. Con un
# fichero aparte, el nucleo se queda quieto y lo unico que cambia es una lista.
# ===========================================================================
REGISTRO_EXT = os.path.join(RAIZ, "08-ARQUITECTURA", "artifacts",
                            "RXRE-REGISTRY.json")


def registrar(nombre, capacidades, binary=None, coste="BAJO", riesgo="NINGUNO",
              solo_lectura=True, pide_root=False, pide_gpu=False,
              entrada="-", salida="-", limitaciones="", ficha=None):
    """Anade una herramienta. Devuelve (ok, motivo). NO la da por disponible."""
    if not nombre or not capacidades:
        return False, "nombre y capacidades son obligatorios"
    if isinstance(capacidades, str):
        capacidades = [capacidades]
    if not binary:
        binary = nombre
    datos = {"herramienta": nombre, "capacidades": capacidades,
             "binary": binary, "entrada": entrada, "salida": salida,
             "coste": coste, "riesgo": riesgo, "solo_lectura": solo_lectura,
             "pide_root": pide_root, "pide_gpu": pide_gpu,
             "limitaciones": limitaciones,
             "estado": "PRESENTE_SIN_PROBAR",
             "origen": "registro externo", "ficha": ficha or ""}
    try:
        os.makedirs(os.path.dirname(REGISTRO_EXT), exist_ok=True)
        prev = _leer_registro()
        prev = [d for d in prev if d["herramienta"] != nombre]
        prev.append(datos)
        with open(REGISTRO_EXT, "w", encoding="utf-8") as f:
            json.dump(prev, f, indent=2, ensure_ascii=False)
    except OSError as e:
        return False, "no se pudo escribir el registro: %s" % e
    # Y se RE-INDEXA, para que quede disponible en el mismo proceso.
    CAP.append((nombre, capacidades, entrada, salida, "text", coste, riesgo,
                solo_lectura, pide_root, pide_gpu, pide_gpu, True,
                limitaciones, False))
    return True, "registrada como PRESENTE_SIN_PROBAR: hay que probarla"


def _leer_registro():
    try:
        with open(REGISTRO_EXT, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def cargar_externas():
    """Incorpora las del fichero. Silencioso si no hay ninguna."""
    for d in _leer_registro():
        if any(f[0] == d["herramienta"] for f in CAP):
            continue
        CAP.append((d["herramienta"], d["capacidades"], d["entrada"],
                    d["salida"], "text", d["coste"], d["riesgo"],
                    d["solo_lectura"], d["pide_root"], d["pide_gpu"],
                    d["pide_gpu"], True, d["limitaciones"], False))


# ===========================================================================
# 6d. MEMORIA OPERATIVA DE LAS HERRAMIENTAS
#
# Un catalogo dice QUE PUEDE hacer una herramienta. La memoria dice QUE HA HECHO,
# y sobre todo QUE HA FALLADO.
#
# La razon de que esto no sea adorno: el proyecto ya tiene el caso. `llvm-mc`
# estaba declarado como la herramienta de ISA, y MEDIDO en 1185: ENSAMBLA
# ENSAMBLA pero NO desensambla. Un catalogo sin memoria seguiria ofreciendola
# para `ISA_DECODE` para siempre, y cada agente que llega lo descubre otra vez.
#
# Eso es la dependencia de memoria, y se cura con memoria.
# ===========================================================================
MEMORIA = {}      # herramienta -> {calidades, fallos, falsos_pos, falsos_neg,
                  #             usos_ok, usos_ko, ultima}


def memoria_de(herramienta):
    m = MEMORIA.setdefault(herramienta, {
        "calidades": [], "fallos": [], "falsos_pos": [], "falsos_neg": [],
        "usos_ok": [], "usos_ko": []})
    return m


def anota(herramienta, capacidad=None, resultado="ok", detalle=None):
    """Registra un uso. `resultado` en {ok, fallo, falso_pos, falso_neg}."""
    m = memoria_de(herramienta)
    if resultado == "ok":
        m["usos_ok"].append(detalle or capacidad or "")
    elif resultado == "fallo":
        m["fallos"].append({"capacidad": capacidad, "detalle": detalle})
    elif resultado == "falso_pos":
        m["falsos_pos"].append({"capacidad": capacidad, "detalle": detalle})
    elif resultado == "falso_neg":
        m["falsos_neg"].append({"capacidad": capacidad, "detalle": detalle})
    return m


def penaliza(herramienta, capacidad):
    """Cuanto se DEBE descontar a una herramienta por su memoria.

    MEDIDO en el criterio, no supuesto:
      - fallo conocido    -> no sirve para esa capacidad. Es un veto, no un peso.
      - falsos positivos  -> penaliza mas que un fallo, porque un falso
                             positivo fabrica una afirmacion falsa, y eso es
                             peor que no tener respuesta.
      - falsos negativos  -> penaliza menos: se nota, no se propaga.
    Un fallo se ve. Un falso positivo se creeria.
    """
    m = memoria_de(herramienta)
    if any(f["capacidad"] == capacidad for f in m["fallos"]):
        return None, "VETO: fallo conocido en esta capacidad"
    pen = 0.0
    pen += 3.0 * len([f for f in m["falsos_pos"] if f["capacidad"] == capacidad])
    pen += 1.0 * len([f for f in m["falsos_neg"] if f["capacidad"] == capacidad])
    return pen, ("penalizacion %.1f" % pen if pen else None)


# ===========================================================================
# 6e. COMPOSICION: NO LA MAS POTENTE, LA DE MAS INFORMACION POR COSTE
#
# El planificador anterior elegia la mas barata. Eso es incorrecto cuando hay
# combinaciones: una sola herramienta cara puede dar menos informacion que tres
# baratas que se complementan.
#
# Se comprueba que las capacidades de los pasos NO SE REPITEN. Un pipeline que
# repite la misma capacidad tres veces no tiene tres pasos, tiene uno con ruido.
# ===========================================================================
def componerse(objetivo, restricciones=None):
    """(composicion, motivo). Lista de herramientas con capacidad nueva cada vez."""
    caps, n_pat, _o = objetivo_a_capacidades(objetivo)
    if not caps:
        return None, "ningun patron conocido para esa pregunta"
    restricciones = restricciones or {}
    out, vistas, visto_cap = [], set(), set()
    for h, cubre, coste, limi in candidatos_para(caps):
        if h in vistas:
            continue
        nueva = [c for c in cubre if c not in visto_cap]
        if not nueva:
            continue
        p, mot, _fr = puerta(h, restricciones.get("estatica_suficiente", False),
                             restricciones.get("autorizado", False))
        if not p:
            continue
        vistas.add(h)
        visto_cap.update(nueva)
        out.append({"herramienta": h, "aporta": nueva, "coste": coste,
                    "limitacion": limi})
    if not out:
        return None, "ninguna combinacion pasa las puertas"
    return out, None


def optimiza(composicion, precios_extra=None):
    """Reordena por INFORMACION POR COSTE, no por coste.

    `precios_extra` = {herramienta: informacion_extraida}. Si no se mide, la
    herramienta vale lo que cubre, y eso se DECLARA como supuesto, no como
    medida. Devolver un numero sin decir de donde sale seria inventar.
    """
    precios_extra = precios_extra or {}
    for paso in composicion:
        paso["informacion"] = precios_extra.get(
            paso["herramienta"], len(paso["aporta"]))
        paso["informacion_es_medida"] = paso["herramienta"] in precios_extra
    composicion = sorted(composicion, key=lambda p: -(
        p["informacion"] / (COSTO_ORDEN.get(p["coste"], 9) + 1)))
    return composicion


# ===========================================================================
# 6f. ANALIZADOR DE PREGUNTA Y GENERADOR DE MODELOS
#
# Una pregunta de RE casi nunca es una sola pregunta: es "¿que tengo que
# DEMOSTRAR para poder decir esto?". Y demostrar casi siempre son dos modelos
# que hay que separar.
#
# Se declara la estructura, y cuando la pregunta no encaja se dice
# DESCONOCIDO. Inventar el modelo contrario para tener algo que discriminar
# seria fabricar la pregunta.
# ===========================================================================
PREG_RE = [
    (("quien escribe", "donde se escribe", "writer"),
     "declarar que A escribe X", ["A escribe X", "no es A quien escribe X"]),
    (("por que", "porque", "explica"),
     "explicar una observacion", None),
    (("cuando", "en que momento"),
     "situar en el tiempo", None),
    (("es correcto", "funciona", "vale"),
     "contrastar una afirmacion", None),
]


def analiza_pregunta(texto):
    """(modelos, necesidad, recognised). Lista vacia si no encaja."""
    t = (texto or "").lower()
    for (claves, necesidad, modelos) in PREG_RE:
        if any(_tiene(t, k) for k in claves):
            if modelos:
                return modelos, necesidad, True
            return [], necesidad, True
    return [], "", False


def genera_pregunta(texto):
    """La necesidad y los modelos, o POR QUE no se pudo."""
    modelos, necesidad, ok = analiza_pregunta(texto)
    if not ok:
        return {"estado": "DESCONOCIDO",
                "motivo": "la pregunta no encaja en ningun patron conocido: no "
                          "se inventa el modelo contrario para tener algo que "
                          "discriminar"}
    if not modelos:
        return {"estado": "PARCIAL",
                "motivo": "se reconoce la necesidad pero no hay dos modelos",
                "necesidad": necesidad, "modelos": []}
    return {"estado": "OK", "necesidad": necesidad, "modelos": modelos}


# ===========================================================================
# 6c. CACHE CON PROCEDENCIA Y HASHES
#
# Un cache sin hash es una caja de respuestas viejas que nadie sabe cuando
# se escribieron. Con hash de entrada, version de herramienta y hash de salida,
# un acierto se puede invalidar y un fallo se puede reproducir.
# ===========================================================================
def huella(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cache2_put(clave, valor, herramienta=None, version=None):
    """Guarda con procedencia completa. Devuelve (ok, ruta_o_motivo)."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        ruta = os.path.join(CACHE_DIR, huella(clave)[:16] + ".json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump({"clave": clave, "valor": valor,
                       "huella_clave": huella(clave),
                       "huella_valor": huella(json.dumps(valor, sort_keys=True,
                                                          default=str)),
                       "herramienta": herramienta, "version": version},
                      f, indent=2, ensure_ascii=False, default=str)
        return True, ruta
    except (OSError, TypeError) as e:
        return False, "cache no escribible: %s" % e


def cache2_get(clave, huella_esperada=None):
    """Devuelve (valor, procedencia). Nunca un valor sin su procedencia."""
    try:
        ruta = os.path.join(CACHE_DIR, huella(clave)[:16] + ".json")
        with open(ruta, encoding="utf-8") as f:
            d = json.load(f)
    except (OSError, ValueError):
        return None, "no esta en cache"
    if huella_esperada and d.get("huella_valor") != huella_esperada:
        return None, "la huella del valor NO cuadra: se descarta"
    return d["valor"], {"huella_clave": d.get("huella_clave"),
                        "huella_valor": d.get("huella_valor"),
                        "herramienta": d.get("herramienta"),
                        "version": d.get("version")}


# ===========================================================================
# 8d. WORK SCAN
#
# La pregunta de §58, hecha codigo. NO decide el trabajo: ESO es del agente. Lo
# que hace es contar lo que hay abierto, para que la cuenta no la haga nadie a
# mano y mal.
#
# Y hay una cosa que el conteo revela y que este proyecto ya sufrio: numeros
# REPETIDOS. Un numero repetido es trabajo gastado dos veces, y el numero mas
# alto cuenta trabajo gastado, no hallazgos distintos.
# ===========================================================================
def work_scan(carpeta=None):
    """Conteo del estado del arbol. Números, repeticiones y authorship."""
    carpeta = carpeta or os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings")
    try:
        ficheros = sorted(os.listdir(carpeta))
    except OSError as e:
        return {"estado": "NO_ACCESIBLE", "motivo": str(e)}
    nums, autores, sin_num = [], {}, []
    for f in ficheros:
        if not f.endswith(".md"):
            continue
        cab = f.split("-", 1)[0]
        if not cab.isdigit():
            continue
        n = int(cab)
        nums.append(n)
        try:
            txt = open(os.path.join(carpeta, f), encoding="utf-8",
                       errors="replace").read(2000)
        except OSError:
            continue
        m = re.search(r"^AUTOR=(.+)$", txt, re.M)
        if m:
            autores[m.group(1).strip()] = autores.get(m.group(1).strip(), 0) + 1
        else:
            sin_num.append(f)
    distintos = len(set(nums))
    repetidos = len(nums) - distintos
    from collections import Counter
    c = Counter(nums)
    return {
        "estado": "OK",
        "ficheros": len(nums),
        "numeros_distintos": distintos,
        "repetidos": repetidos,
        "ficheros_de_mas": sum(v for v in c.values() if v > 1),
        "numero_mas_alto": max(nums) if nums else 0,
        "por_autor": autores,
        "sin_autor": len(sin_num),
    }


# ===========================================================================
# 6g. CONTRADICCIONES Y ANTI-REPETICION
#
# DOS FUENTES QUE SE CONTRADICEN NO TIENEN UN GANADOR INTUITIVO.
#
# Es la regla §80 del proyecto y sale de IMPLEMENTATION_IS_NOT_AUTHORITY: el
# codigo existente es evidencia sobre una implementacion, no sobre el hardware.
# Cuando dos herramientas discrepan, la respuesta no es "la mas nueva" ni "la
# mas barata": es reconstruir la cadena producer->transformation->
# representation->consumer y buscar el eslabon donde se separan.
#
# Y este proyecto lo ha pagado: las dos declaraciones de MAP_QUEUES.CONTROL2
# incompatibles conviven desde hace tiempo y siguen sin resolverse.
# ===========================================================================
def contradiccion(afirmaciones):
    """afirmaciones = [{id, claim, valor, fuente, alcance}]

    Devuelve el registro de contradiccion, o None si no la hay.
    """
    por_claim = {}
    for a in afirmaciones:
        por_claim.setdefault(a["claim"], []).append(a)
    for claim, grupo in por_claim.items():
        valores = {str(g["valor"]) for g in grupo}
        if len(valores) < 2:
            continue
        fuentes = sorted({g["fuente"] for g in grupo})
        alcances = sorted({str(g.get("alcance", "")) for g in grupo})
        return {
            "claim": claim,
            "afirmaciones": grupo,
            "valores_en_disputa": sorted(valores),
            "fuentes": fuentes,
            "alcances": alcances,
            "ganador": None,
            "motivo": ("no hay ganador intuitivo: con alcances distintos puede "
                       "no haber contradiccion, sino dos respuestas a dos "
                       "preguntas distintas"),
            "siguiente": ("reconstruir producer->transformation->"
                          "representation->consumer y localizar el eslabon "
                          "donde divergen, ANTES de medir nada"),
        }
    return None


# ===========================================================================
# 6h. ANTI-REPETICION
#
# La pregunta de este proyecto tiene respuesta medida: 74 numeros de hallazgo
# repetidos gastan 101 ficheros de mas. El trabajo se repite porque nadie
# consulta antes de repetir.
#
# Y hay un segundo hecho: el contador es COMPARTIDO con otra sesion, asi que la
# repeticion tambien es un problema de concurrencia, no solo de memoria. Aqui
# solo se resuelve la parte de memoria: "esto ya se intento" responde con la
# evidencia, no con un "no".
# ===========================================================================
def ya_investigado(pregunta, grafo=None):
    """(estado, {que_ya_se_sabe, que_se_descarto, que_sigue_vivo})."""
    grafo = grafo or {}
    clave = (pregunta or "").strip().lower()
    for k, v in grafo.items():
        if clave and (clave in k.lower() or k.lower() in clave):
            return ("YA_INVESTIGADO", v)
    return ("NUEVA", {"que_ya_se_sabe": [], "que_se_descarto": [],
                      "que_sigue_vivo": []})


def siguiente_accion_anti_repeticion(pregunta, grafo, modelos_vivos,
                                     pruebas, fracaso_previo=None):
    """La accion, sabiendo lo que ya se hizo y lo que ya fallo."""
    estado, previo = ya_investigado(pregunta, grafo)
    if estado == "YA_INVESTIGADO":
        frac = list(fracaso_previo or [])
        descartes = [x["nombre"] for x in pruebas if x["nombre"] in frac]
        cand = [x for x in pruebas if x["nombre"] not in frac]
        r = siguiente_accion(modelos_vivos, cand)
        if r["estado"] != "OK":
            return {"estado": "YA_INVESTIGADO_Y_SIN_DISCRIMINANTE_NUEVO",
                    "recuperado": previo,
                    "ya_descartado": descartes,
                    "motivo": r.get("motivo", "")}
        return {"estado": "YA_INVESTIGADO",
                "recuperado": previo,
                "ya_descartado": descartes,
                "siguiente": r,
                "motivo": "no se repite lo ya hecho; se propone lo que falta"}
    return {"estado": "NUEVA", "accion": siguiente_accion(modelos_vivos, pruebas)}


# ===========================================================================
# 6i. MANIFIESTO DE MADUREZ
#
# UNA HERRAMIENTA NO SE DECLARA MADURA. SE COMPRUEBA.
#
# La escalera "V0 wrapper -> V1 registro -> ... -> V6 autonomous" con
# porcentajes de capacidad es un MARCO NARRATIVO, y por eso NO se implementa como
# tabla: una capacidad inventada convertida en porcentaje es un dato falso con
# formato de dato. Lo que se implementa es lo que si se puede medir:
#
#     para cada capacidad, ¿la hace rxre, o la tiene que hacer la IA a mano?
#
# Y eso obliga a una regla que no es negociable:
#
#     UNA CAPACIDAD NO SE DECLARA AUTOMATIZADA SIN UN VECTOR QUE LA EJERCITE.
#
# Sin vector, `residual` no puede estar vacio: tiene que decir que mano queda.
# Una capacidad "automatizada" sin prueba es exactamente la clase de cosa que
# este proyecto ha pagado varias veces.
# ===========================================================================
MADUREZ = {
    # capacidad: (version, automatizada, lo que la IA tiene que hacer a mano,
    #              vector que lo demuestra)
    "TOOL_DISCOVER": ("V1", True, "",
                      "rxre selftest: matriz no vacia, sin duplicados"),
    "CAPABILITY_MATCH": ("V2", True, "",
                         "rxre selftest: find-tool devuelve pasos con motivo"),
    "PIPELINE_PLAN": ("V2", True, "",
                      "rxre selftest: composicion sin capacidad repetida"),
    "PUERTA_FRONTERA": ("V2", True, "",
                        "rxre selftest: la frontera bloquea sin autorizacion"),
    "PUERTA_GANANCIA": ("V2", True, "",
                        "rxre selftest: frena el runtime con estatica"),
    "PUERTA_REVERSIBILIDAD": ("V2", True, "",
                              "rxre selftest: escribir exige autorizacion"),
    "TOOL_EXECUTE": ("V2", False,
                     "rxre PLANIFICA y SONDA, pero no ejecuta el pipeline",
                     "rxre selftest: probe existe y devuelve veredicto"),
    "RESULT_NORMALIZE": ("V2", False,
                         "cada herramienta devuelve texto distinto; no hay "
                         "un registro comun", ""),
    "EVIDENCE_RECORD": ("V1", False,
                        "rxre no crea entradas de evidencia; eso lo hace el "
                        "agente a mano", ""),
    "DISCRIMINANT_ENGINE": ("V3", True, "",
                            "rxre selftest: elige la mas barata que separa"),
    "MODEL_GENERATOR": ("V3", True, "",
                        "rxre selftest: dos modelos o DESCONOCIDO"),
    "QUESTION_ANALYZER": ("V3", True, "",
                         "rxre selftest: clave corta no casa dentro de otra"),
    "CONTRADICTION_ENGINE": ("V4", True, "",
                             "rxre selftest: nunca elige ganador"),
    "ANTI_REPETITION": ("V4", True, "",
                        "rxre selftest: devuelve evidencia, no un no"),
    "KNOWLEDGE_GRAPH": ("V4", False,
                        "no hay grafo de relaciones del corpus", ""),
    "PROVENANCE_GRAPH": ("V1", False,
                         "la hay por resultado de cache, no por afirmacion", ""),
    "TOOL_MEMORY": ("V3", True, "",
                    "rxre selftest: veto por fallo conocido"),
    "WORK_SCAN": ("V4", True, "",
                  "rxre selftest: cuenta ficheros, distintos y repetidos"),
    # AUTONOMOUS_RE NO se declara hecha, y el motivo es la razon de existir de
    # este manifiesto: el agente decide QUE investigar, CUANDO y CUANDO PARAR.
    # Eso no lo hace una herramienta. Y sin vector que lo demuestre, aqui no
    # cabria ni la palabra "automatizada".
    "AUTONOMOUS_RE": ("NO", False,
                      "todo: el agente decide que investigar, cuando y cuando "
                      "parar", ""),
}


def madurez(capacidad=None):
    """El manifiesto. Con `capacidad=None`, el informe entero."""
    filas = []
    for c, (v, auto, residual, vector) in MADUREZ.items():
        if auto and not vector:
            # ESTA ES LA REGLA. Una capacidad automatizada sin vector no se
            # puede declarar automatizada, se diga lo que se diga arriba.
            auto = False
            residual = ("NO HAY VECTOR que lo demuestre: se degrada a manual "
                        "hasta que exista")
        filas.append({"capacidad": c, "version": v, "automatizada": auto,
                      "residual": residual, "vector": vector})
    if capacidad:
        return next((f for f in filas if f["capacidad"] == capacidad), None)
    return filas


def manual_pendiente():
    """Lo que la IA todavia tiene que hacer. Es el saldo de verdad."""
    return [{"capacidad": f["capacidad"], "version": f["version"],
             "residual": f["residual"]}
            for f in madurez() if not f["automatizada"]]


def huecos(objetivo=None):
    """Capacidades que una pregunta necesita y que NADIE puede dar todavia.

    Se calcula con lo de verdad: si la unica herramienta de una capacidad esta
    ausente o vetada por la memoria, la capacidad esta CUBIERTA POR NADIE. Y eso
    es un hueco, no un detalle de la planificacion.
    """
    caps = objetivo_a_capacidades(objetivo)[0] if objetivo else sorted(
        _caps_totales())
    out = []
    for c in caps:
        # MEDIDO: `quienes` tambien mira la columna cruda, y eso hacia que una
        # capacidad REFUTADA pareciese cubierta por la unica herramienta que se
        # probo que no la tiene.  Se pregunta por lo RUTEABLE, que es lo que
        # el planificador puede usar.
        quienes = [f[0] for f in CAP if c in capacidades_ruteables(f[0])]
        if not quienes:
            # No hay ninguna herramienta para esta capacidad. Puede ser que este
            # REFUTADA para todas, y eso NO es lo mismo que no existir: es una
            # conclusion medida y hay que poder distinguirla.
            # Quien REFUTO esta capacidad, no quien la declara: una capacidad
            # puede estar probada como imposible para una herramienta que
            # nunca la anuncia, y ese par es precisamente la medicion.
            ref = {h: m for (h, cc), m in CAP_REFUTADA.items() if cc == c}
            out.append({"capacidad": c, "candidatas": sorted(ref),
                        "motivo": ("PROBADA IMPOSIBLE: " +
                                   "; ".join("%s -> %s" % (h, m[:90])
                                             for h, m in sorted(ref.items())))
                                  if ref else "nadie la declara"})
            continue
        vivos = []
        for h in quienes:
            pen, mot = penaliza(h, c)
            if pen is None:
                continue
            est = estado_de(h)["estado"]
            if est in ("AUSENTE", "PROBADA_FALLA"):
                continue
            vivos.append(h)
        if not vivos:
            out.append({"capacidad": c, "candidatas": quienes,
                        "motivo": "ninguna viva: ausentes, fallidas o vetadas"})
    return out


# ===========================================================================
# 7. VALIDADORES
#
# Las reglas que este proyecto ya ha pagado. Cada una de ellas salio de un
# hallazgo donde la regla equivocada costo trabajo. Convertirlas en EJECUTABLES
# es lo que las saca de la prosa: una regla que solo esta escrita es una regla
# que se puede desobedecer sin que nadie se entere.
#
# Cada validador devuelve un veredicto de una sola familia:
#
#     PASA           la regla se respeta
#     FALLA          la regla se incumpla, y esto es un HALLAZGO
#     NO_APLICA      falta el dato para juzgar; no se aprueba por omision
#
# NO_APLICA nunca es PASA. Esa confusion es exactamente lo que estas reglas
# existen para evitar.
# ===========================================================================
REGLAS = [
    ("AUSENCIA_NO_ES_INEXISTENCIA",
     "no se confunde NOT_FOUND con PROVEN_ABSENT"),
    ("VERDE_NO_ES_CORRECTO",
     "el codigo de salida de una herramienta no certifica su resultado"),
    ("SOFTWARE_NO_ES_HARDWARE",
     "el analisis estatico no es una observacion del hardware"),
    ("COMPILAR_NO_ES_EJECUTAR",
     "que compile no dice que se comporte bien"),
    ("REPRESENTACION_NO_ES_FUENTE",
     "la salida de un desensamblador es HIPOTESIS hasta validar"),
    ("SIN_PROBAR_NO_ES_DISPONIBLE",
     "estar en el disco no es estar verificado"),
    ("NULO_NO_ES_CERO",
     "un valor ausente no se rellena con cero"),
    ("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE",
     "una sola coincidencia no corrobora: dos caminos, dos evidencias"),
    ("DECODIFICADO_NO_ES_VERIFICADO",
     "decodificar no es probar: falta el reensamblado"),
]


# ---------------------------------------------------------------------------
# 7a. LOS DOS VOCABULARIOS, Y POR QUE HACE FALTA CERRARLOS
#
# MEDIDO por mutacion:  dos validadores comparaban con `==` contra una palabra
# suelta, y por eso se esquivaban cambiando la palabra.  `fuente="static"` en
# vez de `"estatico"`, u `origen="ghidra"` en vez de `"decompilador"`, pasaban
# los dos.
#
#     una puerta que se abre con una tilde no es una puerta
#
# La diferencia con un simple `in` es que el conjunto se DECLARA aqui y se
# comprueba:  una palabra que no este en el vocabulario NO se trata como
# "seguro por defecto", sino como "no reconocida", que es un estado distinto.
# ---------------------------------------------------------------------------
ORIGEN_ESTATICO = ("estatico", "static", "source", "fuente", "codigo",
                   "source-code", "lectura-de-fichero")
ORIGEN_REPRESENTACION = ("descompilador", "decompilador", "ghidra", "radare2",
                         "r2", "cutter", "pycdc", "llvm-objdump", "objdump",
                         "binja", "retdec", "ida", "representacion", "disassembly")

# Y el TERCER vocabulario, que se me quedo abierto en el mismo commit en que
# cerre los otros dos.  MEDIDO:  la regla comparaba `afirmacion == "PROVEN"`, y
# la mutacion de prueba usaba "CORROBORADO" — el mismo concepto en castellano.
# Con las dos escrituras, la mutacion pasaba.  Es el mismo defecto de antes,
# aplicado a la palabra que acababa de decidir cerrar:
#
#     cerrar dos vocabularios y dejar el tercero abierto no es cerrar
AFIRMACION_FUERTE = ("proven", "corroborated", "corroborado", "proven_derived",
                     "proven-derivado")
ESTADO_DISPONIBLE = ("disponible", "validado", "verificado", "probada_ok",
                     "probada-ok")


def _es_estatico(fuente):
    return str(fuente).strip().lower() in ORIGEN_ESTATICO


def _es_representacion(origen):
    return str(origen).strip().lower() in ORIGEN_REPRESENTACION


def valida(regla, hecho):
    """(veredicto, motivo). `hecho` es un dict con lo que se sabe."""
    r = regla
    if r == "AUSENCIA_NO_ES_INEXISTENCIA":
        if "busqueda" not in hecho:
            return ("NO_APLICA", "no se dice que se busco")
        if hecho.get("resultado") == "NOT_FOUND" and \
                hecho.get("veredicto") == "PROVEN_ABSENT":
            return ("FALLA", "se declara PROVEN_ABSENT tras NOT_FOUND")
        # MEDIDO por mutacion:  omitir el veredicto y declarar solo NOT_FOUND
        # daba PASA.  Es la misma confusion —la ausencia convertida en
        # inexistencia por omision— y por ser silenciosa no era menos grave.
        # La regla ahora exige que, si se busco y no se encontro, se DIGA que
        # no se ha determinado.
        if hecho.get("resultado") == "NOT_FOUND" and "veredicto" not in hecho:
            return ("FALLA", "NOT_FOUND sin veredicto: la ausencia queda "
                             "declarada por omision")
        return ("PASA", "no se confunde la ausencia con la inexistencia")
    if r == "VERDE_NO_ES_CORRECTO":
        if "rc" not in hecho or "validado" not in hecho:
            return ("NO_APLICA", "falta rc o la marca de validacion")
        if hecho["rc"] == 0 and hecho["validado"] is False:
            return ("FALLA", "rc=0 se esta usando como certificacion")
        return ("PASA", "el exito no se confunde con la correccion")
    if r == "SOFTWARE_NO_ES_HARDWARE":
        if "fuente" not in hecho:
            return ("NO_APLICA", "no se dice de donde salio")
        if _es_estatico(hecho["fuente"]) and hecho.get("afirmacion") == \
                "OBSERVED":
            return ("FALLA", "estatico declarado como OBSERVED del hardware")
        return ("PASA", "la procedencia se respeta")
    if r == "COMPILAR_NO_ES_EJECUTAR":
        if "compila" not in hecho or "reejecuta" not in hecho:
            return ("NO_APLICA", "falta uno de los dos datos")
        if hecho["compila"] and hecho.get("afirmacion") == "CORRECTO" and (
                not hecho["reejecuta"] or
                hecho.get("reejecuta_igual") is False):
            return ("FALLA", "compila y se declara correcto sin reejecutar, "
                             "o reejecutando y obteniendo otra cosa")
        return ("PASA", "")
    if r == "REPRESENTACION_NO_ES_FUENTE":
        if "origen" not in hecho:
            return ("NO_APLICA", "")
        if _es_representacion(hecho["origen"]) and \
                str(hecho.get("estado", "")).strip().lower() in \
                ("proven", "proven_derived", "proven-derivado"):
            return ("FALLA", "una representacion (%s) no es PROVEN: es "
                             "HIPOTESIS hasta validarla"
                             % hecho["origen"])
        return ("PASA", "")
    if r == "SIN_PROBAR_NO_ES_DISPONIBLE":
        if "estado" not in hecho:
            return ("NO_APLICA", "")
        # MEDIDO por mutacion:  la regla solo miraba DISPONIBLE.  VALIDADO es
        # MAS FUERTE que DISPONIBLE, y un instrumento sin probar declarado
        # VALIDADO se colaba por el lado fuerte de la misma puerta.
        if str(hecho["estado"]).strip().lower() in ESTADO_DISPONIBLE and \
                hecho.get("verificada") is False:
            return ("FALLA", "declarada %s sin prueba" % hecho["estado"])
        return ("PASA", "")
    if r == "NULO_NO_ES_CERO":
        if "valor" not in hecho:
            return ("NO_APLICA", "")
        # MEDIDO por mutacion:  `valor == 0` es cierto para el TEXTO "0" en
        # Python, porque "0" == 0 es False pero el caso real aqui es el
        # inverso —una cadena numerica leida de un fichero— y se colaba como
        # cero medido.  Un cero medido es un int de un sensor o de un
        # registro;  una cadena es una suposicion con formato de numero.
        if hecho.get("origen") == "desconocido" and \
                str(hecho["valor"]).strip() in ("0", "0.0", "0x0", "00"):
            return ("FALLA", "un valor desconocido se ha rellenado con cero")
        if hecho.get("origen") == "desconocido" and isinstance(
                hecho["valor"], (int, float)) and hecho["valor"] == 0:
            return ("FALLA", "un valor desconocido se ha rellenado con 0")
        return ("PASA", "")
    if r == "COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE":
        if "caminos" not in hecho:
            return ("NO_APLICA", "")
        # MEDIDO por mutacion:  solo miraba PROVEN.  CORROBORATED significa
        # dos fuentes independientes por definicion, y con un solo camino no
        # cabe igual que no quepa PROVEN.
        if str(hecho.get("afirmacion", "")).strip().lower() in \
                AFIRMACION_FUERTE and hecho["caminos"] < 2:
            return ("FALLA", "una sola coincidencia declarada %s"
                             % hecho["afirmacion"])
        return ("PASA", "")
    if r == "DECODIFICADO_NO_ES_VERIFICADO":
        if "decodificado" not in hecho:
            return ("NO_APLICA", "")
        if hecho["decodificado"] and hecho.get("verificado") is not True:
            return ("FALLA", "se declara el decodificado sin reensamblado")
        return ("PASA", "")
    return ("NO_APLICA", "regla desconocida: no se inventa su veredicto")


# ---------------------------------------------------------------------------
# 7b. EL VALIDADOR DE LOS VALIDADORES: SI LOS VALIDADORES SABEN FALLAR
#
# MEDIDO 2026-10-04.  Cada uno de los nueve validadores de arriba tiene
# vectores que prueban que PASA cuando la regla se respeta.  Eso es la mitad,
# y es la mitad facil:  un validador que no dispara nunca da siempre verde y no
# se distingue de uno que works.
#
#     GREEN_TEST != CORRECTNESS,  aplicado a los propios validadores
#
# Falta la otra mitad:  dado un HECHO que incumple la regla, ¿el validador lo
# ve?  Eso se mide con mutacion —  se parte de un hecho que CUMPLE y se le
# rompe UN campo de los que la regla mira  —  y se cuenta cuantas mutaciones
# detecta.  Las que NO detecta son FALSOS NEGATIVOS,  y son la medida que no
# tenia:  no basta con saber cuantos vectores hay.
#
# Y aqui esta el limite, escrito antes que el resultado para que el resultado
# no se lea de mas:  esto mide la deteccion de MUTACIONES DE UN CAMPO.  No mide
# si un validador sobrevive a un oraculo equivocdo, ni a una regla mal escrita,
# ni a un dato que miente de forma coherente.  Es UN frente de alarma, y
# `mutation_sensitivity` no es `correccion`.
# ---------------------------------------------------------------------------
# (regla, nombre_de_la_mutacion, hecho_que_CUMPLE, mutacion, por_que_debe_verla)
MUTACIONES = [
    ("AUSENCIA_NO_ES_INEXISTENCIA", "PROVEN_ABSENT tras NO_FOUND",
     {"busqueda": "grep -rn", "resultado": "NOT_FOUND",
      "veredicto": "NOT_DETERMINED"},
     {"busqueda": "grep -rn", "resultado": "NOT_FOUND",
      "veredicto": "PROVEN_ABSENT"},
     "es exactamente la confusion que la regla prohibe"),
    ("AUSENCIA_NO_ES_INEXISTENCIA", "PROVEN_ABSENT sin decir el veredicto",
     {"busqueda": "grep -rn", "resultado": "NOT_FOUND",
      "veredicto": "NOT_DETERMINED"},
     {"busqueda": "grep -rn", "resultado": "NOT_FOUND"},
     "omitir el veredicto y thereby declarar la inexistencia es la MISMA "
     "confusion, y no por ser silenciosa deja de serlo"),
    ("VERDE_NO_ES_CORRECTO", "rc=0 como certificacion",
     {"rc": 0, "validado": True}, {"rc": 0, "validado": False},
     "el caso que la regla prohibe"),
    ("VERDE_NO_ES_CORRECTO", "rc=0 con validado ausente",
     {"rc": 0, "validado": True}, {"rc": 0},
     "sin la marca de validacion no se sabe si se valido; no puede pasar"),
    ("SOFTWARE_NO_ES_HARDWARE", "estatico como OBSERVED",
     {"fuente": "estatico", "afirmacion": "DERIVED"},
     {"fuente": "estatico", "afirmacion": "OBSERVED"},
     "el caso que la regla prohibe"),
    ("SOFTWARE_NO_ES_HARDWARE", "el mismo estatico escrito de otra forma",
     {"fuente": "estatico", "afirmacion": "DERIVED"},
     {"fuente": "static", "afirmacion": "OBSERVED"},
     "una regla que se puede esquivar con una tilde deja de ser puerta"),
    ("COMPILAR_NO_ES_EJECUTAR", "compila y se declara correcto",
     {"compila": True, "reejecuta": True},
     {"compila": True, "reejecuta": False, "afirmacion": "CORRECTO"},
     "el caso que la regla prohibe"),
    ("COMPILAR_NO_ES_EJECUTAR", "reejecuta pero NO da lo mismo",
     {"compila": True, "reejecuta": True},
     {"compila": True, "reejecuta": True, "reejecuta_igual": False,
      "afirmacion": "CORRECTO"},
     "reexecutar y obtener algo distinto NO es haber ejecutado"),
    ("REPRESENTACION_NO_ES_FUENTE", "decompilador como PROVEN",
     {"origen": "decompilador", "estado": "DERIVED"},
     {"origen": "decompilador", "estado": "PROVEN"},
     "el caso que la regla prohibe"),
    ("REPRESENTACION_NO_ES_FUENTE", "otra representacion como PROVEN",
     {"origen": "decompilador", "estado": "DERIVED"},
     {"origen": "ghidra", "estado": "PROVEN"},
     "la regla nombra dos palabras y hay seisInstrumentos que producen "
     "representaciones; con dos no cubre el caso que dice cubrir"),
    ("SIN_PROBAR_NO_ES_DISPONIBLE", "DISPONIBLE sin probar",
     {"estado": "DISPONIBLE", "verificada": True},
     {"estado": "DISPONIBLE", "verificada": False},
     "el caso que la regla prohibe"),
    ("SIN_PROBAR_NO_ES_DISPONIBLE", "VALIDADO sin probar",
     {"estado": "DISPONIBLE", "verificada": True},
     {"estado": "VALIDADO", "verificada": False},
     "VALIDADO es MAS FUERTE que DISPONIBLE: si la regla no lo cubre, no "
     "cubre el caso fuerte"),
    ("NULO_NO_ES_CERO", "desconocido rellenado con 0",
     {"valor": 0, "origen": "medido"}, {"valor": 0, "origen": "desconocido"},
     "el caso que la regla prohibe"),
    ("NULO_NO_ES_CERO", "el cero de TEXTO cuenta como cero",
     {"valor": 0, "origen": "medido"}, {"valor": "0", "origen": "desconocido"},
     "un valor de texto no es un cero medido: es un cero Inventado"),
    ("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE", "un camino como PROVEN",
     {"caminos": 2, "afirmacion": "PROVEN"},
     {"caminos": 1, "afirmacion": "PROVEN"},
     "el caso que la regla prohibe"),
    ("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE", "un camino como CORROBORADO",
     {"caminos": 2, "afirmacion": "PROVEN"},
     {"caminos": 1, "afirmacion": "CORROBORADO"},
     "CORROBORADO significa dos fuentes independientes; con una no cabe"),
    ("DECODIFICADO_NO_ES_VERIFICADO", "decodificado sin reensamblar",
     {"decodificado": True, "verificado": True},
     {"decodificado": True, "verificado": False},
     "el caso que la regla prohibe"),
]


def mutation_sensitivity():
    """Que mutaciones detecta cada regla, y cuales se le escapan.

    Devuelve la medida que no existia:  no cuantos vectores hay,  sino cuantos
    de los fallos que la regla dice prohibir los ve EN REALIDAD.
    """
    por_regla = {}
    for regla, nombre, ok, mal, por_que in MUTACIONES:
        v_ok = valida(regla, ok)[0]
        v_mal = valida(regla, mal)[0]
        fila = por_regla.setdefault(regla, {"deteccion": 0, "total": 0,
                                            "fugas": [], "control_sano": True})
        fila["total"] += 1
        if v_ok != "PASA":
            fila["control_sano"] = False
            fila.setdefault("control_roto", []).append((nombre, v_ok))
        if v_mal == "FALLA":
            fila["deteccion"] += 1
        else:
            # MEDIDO, y la distincion es la que hace que la cifra signifique
            # algo:  de las ocho fugas, siete salian PASA y una NO_APLICA.
            # No es lo mismo.
            #
            #   FUGA_ENGANOSA  sale PASA.  La regla dice que el hecho es malo y
            #                   el validador lo aprueba.  Esto es un falso verde.
            #   FUGA_SIN_JUZGAR sale NO_APLICA.  No aprueba nada, pero tampoco
            #                   protege:  un hecho que no declara el dato escapa
            #                   de la regla sin que nadie lo note.
            #
            # Juntas en un solo numero, la segunda haria que la primera pareciese
            # menos grave de lo que es, y la segunda pareciese igual de grave.
            fila["fugas"].append({
                "mutacion": nombre, "veredicto": v_mal,
                "gravedad": "FUGA_ENGANOSA" if v_mal == "PASA"
                else "FUGA_SIN_JUZGAR",
                "por_que_deberia": por_que, "hecho": mal})
    eng = sum(1 for f in por_regla.values() for x in f["fugas"]
              if x["gravedad"] == "FUGA_ENGANOSA")
    sinj = sum(1 for f in por_regla.values() for x in f["fugas"]
               if x["gravedad"] == "FUGA_SIN_JUZGAR")
    return {"por_regla": por_regla,
            "deteccion": sum(f["deteccion"] for f in por_regla.values()),
            "total": sum(f["total"] for f in por_regla.values()),
            "fugas_enganosas": eng, "fugas_sin_juzgar": sinj,
            "fugas": eng + sinj,
            "tasa": "%.0f%%" % (100.0 * sum(
                f["deteccion"] for f in por_regla.values()) /
                max(1, sum(f["total"] for f in por_regla.values()))),
            "controles_rotos": sum(0 if f["control_sano"] else 1
                                   for f in por_regla.values())}


# ---------------------------------------------------------------------------
# 7c. ¿LAS REGLAS ALCANZAN AL CORPUS REAL?
#
# MEDIDO 2026-10-04.  `mutation_sensitivity` mide si los validadoresVEN el
# incumplimiento, y contesta que si.  Pero mide sobre HECHOS QUE YO CONSTRUI, y
# queda una pregunta que es la que de verdad importa:
#
#     ¿alguno de los nueve validadores se puede EJECUTAR sobre un hallazgo real?
#
# MEDIDO, y la respuesta es que no. De los 20 campos que las nueve reglas miran,
# solo 11 aparecen como campo en AL MENOS un hallazgo de los 676 del cuerpo, y
# el mas comun —`rc`— sale en 16. Hay reglas cuyos campos no aparecen NUNCA:
#
#     COMPILAR_NO_ES_EJECUTAR            necesita 3 campos;  0, 0 y 0
#     COINCIDENCIA_UNICA_..._INDEPENDENTE necesita 2 campos;  0 y 0
#
#   esas dos reglas NO SON APLICABLES a un solo hallazgo del cuerpo.
#
# Y esto NO es un fallo de los validadores:  es un dato sobre el formato de la
# evidencia. Las reglas son correctas y ejecutables; lo que no existe es el
# sujeto sobre el que ejecutarlas. Un validador que no tiene entrada no es un
# validador roto:  es un validador sin corpus.
#
#     nueve reglas ejecutables contra hechos delaboratorio, y cero
#     ejecutables contra el archivo.  Eso es lo que hay, y dice mucho.
# ---------------------------------------------------------------------------
CAMPOS_DE_LA_REGLA = {
    "AUSENCIA_NO_ES_INEXISTENCIA": ("busqueda", "resultado", "veredicto"),
    "VERDE_NO_ES_CORRECTO": ("rc", "validado"),
    "SOFTWARE_NO_ES_HARDWARE": ("fuente", "afirmacion"),
    "COMPILAR_NO_ES_EJECUTAR": ("compila", "reejecuta", "reejecuta_igual"),
    "REPRESENTACION_NO_ES_FUENTE": ("origen", "estado"),
    "SIN_PROBAR_NO_ES_DISPONIBLE": ("estado", "verificada"),
    "NULO_NO_ES_CERO": ("valor", "origen"),
    "COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE": ("caminos", "afirmacion"),
    "DECODIFICADO_NO_ES_VERIFICADO": ("decodificado", "verificado"),
}
# MEDIDO, y este fue un fallo MIO que produjo un resultado FALSO:  la primera
# version de este patron era  re.compile(r"...(%s)...")  sin aplicarle el `%`, de
# modo que la expresionbuscaba la cadena literal "%s" y no encontraba NINGUN
# campo.  Salio "0 campos vivos, 0 reglas aplicables",  que es un dato
# VEROSIMIL y falso,  y差点 se escribe como hallazgo.
#
#     un marcador sin sustituir dentro de una regex compilada no da error:
#     da un cero silencioso
#
# Por eso el patron se construye AQUI, con la lista real, y hay un vector que
# comprueba que no sobrevive ningun "%s".
_CAMPOS_TODOS = sorted({c for cs in CAMPOS_DE_LA_REGLA.values() for c in cs})
RE_CAMPO = re.compile(r"(?m)^[ \t]*[#|`]*(%s)[ \t]*[=:]"
                      % "|".join(re.escape(c) for c in _CAMPOS_TODOS))


def hallazgos():
    d = os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(d):
        return []
    return sorted(f for f in os.listdir(d) if f.endswith(".md"))


def _porta_campos():
    """{hallazgo: set de campos que declara}. Cacheado.

    Se cuenta un CAMPO, no una palabra:  la forma que se busca es `campo=` al
    principio de una linea.  La distincion no es de forma:  `fuente` aparece
    266 veces en el cuerpo y `fuente=` aparece 8, y las 266 son prosa sobre de
    donde salio un dato, no el campo que un validador necesita.
    """
    global _CAMPOS_CACHE
    if _CAMPOS_CACHE is not None:
        return _CAMPOS_CACHE
    _CAMPOS_CACHE = {}
    for fn in hallazgos():
        try:
            txt = open(os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings", fn),
                       encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        _CAMPOS_CACHE[fn] = {m.group(1) for m in RE_CAMPO.finditer(txt)}
    return _CAMPOS_CACHE


_CAMPOS_CACHE = None


def cobertura_de_campos():
    """Por regla: cuantos hallazgos llevan los campos que la regla necesita.

    `aplicables` son los hallazgos sobre los que el validador PODRIA judged:
    sin uno, la regla no se puede ejecutar, y eso no es lo mismo que no
    incumplirse.
    """
    capas = _porta_campos()
    total = len(capas)
    filas, campos_vivos = {}, set()
    for regla, campos in CAMPOS_DE_LA_REGLA.items():
        por_campo = {c: sum(1 for v in capas.values() if c in v)
                     for c in campos}
        # un hallazgo es aplicable si lleva TODOS los campos de la regla
        aplicables = [fn for fn, v in capas.items()
                      if all(c in v for c in campos)]
        completo = sum(1 for fn, v in capas.items()
                       if any(c in v for c in campos))
        filas[regla] = {"campos": campos, "por_campo": por_campo,
                        "hallazgos_con_alguno": completo,
                        "aplicables": len(aplicables),
                        "aplicable": bool(aplicables)}
        campos_vivos |= {c for c, n in por_campo.items() if n}
    # MEDIDO, y lo decidio un vector:  `campos_necesarios` sumaba con
    # DUPLICADOS y salia 20, mientras que el conjunto deduplicado daba 17.
    # Tres campos los necesitan dos reglas (`estado`, `origen`, `afirmacion`),
    # y para la pregunta que se hace —"¿que campos hay que registrar?"— cuenta
    # el DISTINTO: 20 obligaria a registrar tres campos que no hacen falta.
    # El total con duplicados se conserva aparte, porque las dos cifras son
    # ciertas y son preguntas distintas.
    return {"hallazgos": total, "reglas": filas,
            "campos_necesarios": len(_CAMPOS_TODOS),
            "campos_necesarios_con_repeticion": sum(
                len(c) for c in CAMPOS_DE_LA_REGLA.values()),
            "campos_vivos": len(campos_vivos),
            "campos_muertos": sorted(
                {c for cs in CAMPOS_DE_LA_REGLA.values() for c in cs}
                - campos_vivos),
            "reglas_aplicables": sum(1 for f in filas.values()
                                     if f["aplicable"]),
            "reglas_totales": len(filas)}


def valida_todo(hechos):
    """[(regla, veredicto, motivo)] para un caso."""
    return [(r, ) + valida(r, hechos) for r, _d in REGLAS]


# ===========================================================================
# 8. MOTOR DE DISCRIMINANTES
#
# Dados dos modelos vivos y las pruebas disponibles, cual es la MAS BARATA que
# los separa. Es la pregunta que decide si hace falta tocar el hardware, y
# contestarla mal es lo queduce a escribir en la GPU sin discriminante.
#
#   coste de una prueba = su coste propio, y el de la evidencia que exige
#   separacion      = si la prueba produce resultados DISTINTOS bajo H1 y H2
#
# Una prueba que da el mismo resultado bajo los dos modelos NO discrimina, por
# cara que tenga. Esa es la regla, y es la que evita gastar una escritura en
# el hardware para comprobar algo que ya se sabe.
# ===========================================================================
def discrimina(modelos, pruebas):
    """[(prueba, separa, coste)] ordenada por coste entre las que separan.

    `pruebas` = [{nombre, h1, h2, coste, necesita_runtime}]
    """
    if len(modelos) < 2:
        return [], "hacen falta dos modelos vivos: con uno no hay que discriminar"
    out = []
    for p in pruebas:
        sep = p.get("h1") != p.get("h2")
        coste = p.get("coste", 0)
        # MEDIDO en el criterio, no supuesto: una prueba que exige runtime y
        # solo se puede hacer en vivo vale MAS que la misma prueba estatica,
        # porque el runtime tiene reversibilidad y riesgo. Se pondera, no se
        # suma: el orden es lo que importa, no la magnitud.
        if p.get("necesita_runtime"):
            coste = coste * 3
        out.append({"prueba": p["nombre"], "separa": sep, "coste": coste})
    separan = sorted([x for x in out if x["separa"]], key=lambda x: x["coste"])
    return separan, None


def siguiente_accion(modelos, pruebas, frontera_ok=True):
    """El paso mas barato que separa los modelos, o por que no se puede."""
    sep, err = discrimina(modelos, pruebas)
    if err:
        return {"estado": "DESCONOCIDO", "motivo": err}
    if not sep:
        return {"estado": "SIN_DISCRIMINANTE",
                "motivo": "ninguna prueba separa los modelos: hay que "
                          "instrumentar, no ejecutar",
                "coste": None, "prueba": None}
    return {"estado": "OK", "prueba": sep[0]["prueba"], "coste": sep[0]["coste"]}


# ===========================================================================
# 7. VECTORES
# ===========================================================================
def selftest(_=None):
    fallos = []

    def chk(n, ok, d=None):
        if ok:
            print("  ok   %s" % n)
        else:
            print("  FALLA %s   %r" % (n, d))
            fallos.append(n)
        return ok

    # 14 campos, no 13: el campo 14 es `toca_integrada`, y sin el la frontera
    # se confundia con "escribe en el sistema". Ver el comentario de CAP.
    chk("matriz: toda fila tiene 14 campos", all(len(c) == 14 for c in CAP),
        [len(c) for c in CAP if len(c) != 14][:3])
    chk("matriz: toda capacidad nombrada existe en el indice",
        all(all(c in _caps_totales() for c in f[1]) for f in CAP))
    chk("matriz: el riesgo es de un conjunto cerrado",
        {f[6] for f in CAP} <= {"NINGUNO", "BAJO", "MEDIO", "ALTO"},
        sorted({f[6] for f in CAP}))
    # La regla real: si NO es solo lectura, el riesgo no puede ser NINGUNO.
    chk("matriz: lo que escribe no puede declararse de riesgo NINGUNO",
        all(f[7] or f[6] != "NINGUNO" for f in CAP),
        [f[0] for f in CAP if not f[7] and f[6] == "NINGUNO"])
    chk("matriz: tocar la integrada se declara SIEMPRE, y es False en todo",
        all(f[13] is False for f in CAP),
        [f[0] for f in CAP if f[13]])
    chk("matriz: lo que pide GPU pide runtime",
        all(not f[9] or f[10] for f in CAP),
        [f[0] for f in CAP if f[9] and not f[10]])

    chk("objetivo: 'quien escribe vm->root.bo' pide escritura",
        "FIND_WRITER" in objetivo_a_capacidades(
            "quien escribe vm->root.bo")[0])
    chk("objetivo: una pregunta sin patron da DESCONOCIDO y NO pipeline",
        pipeline("cosas que no tienen nombre")["estado"] == "DESCONOCIDO",
        pipeline("cosas que no tienen nombre")["estado"])
    chk("objetivo: la pregunta sin patron NO devuelve pasos inventados",
        pipeline("cosas que no tienen nombre")["pasos"] == [])
    chk("objetivo: una combinada une las capacidades de los dos patrones",
        len(objetivo_a_capacidades("quien escribe y quien llama")[0]) >= 3)
    chk("objetivo: los gfx8 piden ISA_DECODE",
        "ISA_DECODE" in objetivo_a_capacidades(
            "decodifica los cores gfx8")[0])

    chk("candidatos: llvm-objdump cubre ISA_DECODE",
        any(h == "llvm-objdump" and "ISA_DECODE" in c
            for h, c, _co, _l in candidatos_para(["ISA_DECODE"])))
    chk("candidatos: se ordena por cobertura y luego por coste",
        [len(x[1]) for x in candidatos_para(["FIND_DEF", "FIND_WRITER"])] ==
        sorted([len(x[1]) for x in candidatos_para(
            ["FIND_DEF", "FIND_WRITER"])], reverse=True))

    lim = {"integrada": "0x8086:0x0412", "discreta": "0x1002:0x699f"}
    p_ok, m_ok, f_ok = puerta("rg", False, False, lim)
    chk("puerta: una herramienta de solo lectura pasa",
        p_ok and f_ok is None, (p_ok, m_ok, f_ok))
    p, m, f = puerta("trace-cmd", True, False, lim)
    chk("puerta: con evidencia estatica ya suficiente, el runtime NO se ejecuta",
        not p and f == PUERTA_GANANCIA, (p, m, f))
    p, m, f = puerta("trace-cmd", False, False, lim)
    chk("puerta: sin evidencia suficiente, el runtime SI se propone",
        p and f is None, (p, m, f))
    p, m, f = puerta(DD_CONTROL, False, False, lim)
    chk("puerta: lo que escribe sin autorizacion queda frenado",
        not p and f in (PUERTA_REVERSIBILIDAD, PUERTA_FRONTERA), (p, m, f))
    p, m, f = puerta(DD_CONTROL, False, True, lim)
    chk("puerta: con autorizacion explicita pasa la de reversibilidad",
        p and f is None, (p, m, f))
    p, m, f = puerta("bpftrace", True, True, lim)
    chk("puerta: la ganancia de informacion gana a la autorizacion",
        not p and f == PUERTA_GANANCIA, (p, m, f))
    # LA FRONTERA, QUE NO TIENE SALIDA. Se prueba con una herramienta
    # SINTETICA, porque en el catalogo no hay ninguna que toque la integrada:
    # ese vacio es el dato, y hay que probarlo igualmente.
    _original = list(CAP)
    CAP.append(("herr_sintetica_toca_integrada", ["RUNTIME_TRACE"], "-", "-",
                "text", "ALTO", "ALTO", False, True, True, True, False,
                "herramienta de prueba", True))
    try:
        p, m, f = puerta("herr_sintetica_toca_integrada", False, True, lim)
        chk("puerta FRONTERA: tocar la integrada bloquea AUN CON autorizacion",
            not p and f == PUERTA_FRONTERA, (p, m, f))
    finally:
        CAP[:] = _original
    chk("puerta: una herramienta no declarada no pasa por omision",
        puerta("no_existe_xyz")[0] is False)

    pl = pipeline("quien escribe vm->root.bo")
    chk("plan: sale OK con pasos", pl["estado"] == "OK" and pl["pasos"])
    chk("plan: los pasos frenados van PRIMERO, que es lo que hay que leer",
        [p["puede"] for p in pl["pasos"]] ==
        sorted([p["puede"] for p in pl["pasos"]], reverse=True))
    chk("plan: ningun paso dice 'puede' sin decir el motivo",
        all(p["motivo"] for p in pl["pasos"]))

    # MEDIDO, y estos dos vectores cambiaron porque la INTERFAZ cambio, no
    # porque el codigo se estuviera excusesando. `toolreg.py` commiteado
    # inventaria herramientas DEL ARBOL y no sabe de PATH; la version que
    # habia en el arbol hacia las dos cosas y por eso podia responder de
    # memoria.  Con la buena, `rg` NO esta en el registro —porque no es
    # nuestra— y eso es lo correcto, no un fallo.
    _arbol = _arbol_de_toolreg()
    chk("registro: toolreg inventaria el ARBOL y rxre no lo vuelve a recorrer",
        len(_arbol) > 100 and all(v["ruta"] for v in _arbol.values()),
        len(_arbol))
    chk("registro: una herramienta NUESTRA se resuelve por el registro",
        estado_de("tools/mmio.py")["estado"] == "EN_ARBOL" and
        estado_de("tools/mmio.py")["universo"] == "arbol",
        estado_de("tools/mmio.py"))
    chk("registro: y una de PATH NO se busca en el registro, porque no esta",
        estado_de("rg")["estado"] == "EN_PATH" and "rg" not in _arbol,
        (estado_de("rg"), "rg" in _arbol))
    chk("registro: lo que no esta en ninguno de los dos universes es AUSENTE",
        estado_de("no_existe_xyz")["estado"] == "AUSENTE",
        estado_de("no_existe_xyz"))
    chk("registro: AUSENTE no se confunde con NO_APLICA: son cosas distintas",
        estado_de("no_existe_xyz")["estado"] != "NO_APLICA")
    # El fallo que motivo esto: una interface que rxre necesita y toolreg no
    # tiene.  Se comprueba que la comprobacion EXISTE y detecta, sin romper el
    # registro de verdad.
    class _ToolregRoto:
        pass
    chk("registro: si toolreg pierde la interfaz, se dice cual falta",
        _toolreg_interfaz_ok(_ToolregRoto())[1] == list(TOOLREG_INTERFAZ),
        _toolreg_interfaz_ok(_ToolregRoto()))

    pr = probe()
    chk("probe: toda prueba devuelve veredicto",
        all(f["verificacion"] in ("VERIFICADA", "FALLO", "AUSENTE")
            for f in pr), pr[:2])
    chk("probe: toda verificada lleva EVIDENCIA, no solo un veredicto",
        all(f.get("evidencia") for f in pr if f["verificacion"] == "VERIFICADA"))
    ll = [f for f in pr if f["herramienta"] == "llvm-mc"]
    chk("probe: llvm-mc ENSAMBLA (medido en 1185)",
        bool(ll) and ll[0]["verificacion"] == "VERIFICADA", ll)
    # El fallo que SI hubo: la expectativa de pahole era su NOMBRE y la
    # herramienta imprime su VERSION. Un probe asi enseña a desconfiar del
    # probe, que es peor que no tener probe.
    ph = [f for f in pr if f["herramienta"] == "pahole"]
    chk("probe: la expectativa se ajusta a lo que la herramienta DICE",
        bool(ph) and ph[0]["verificacion"] == "VERIFICADA",
        ph)
    chk("probe: una verificacion FALLA trae rc y salida para poder juzgarla",
        all(("rc=" in f["evidencia"]) for f in pr
            if f["verificacion"] == "FALLO"))

    ok, r = cache_put("prueba", {"a": 1})
    chk("cache: se guarda y se recupera o se DICE por que no",
        (ok and cache_get("prueba") == {"a": 1}) or not ok, r)
    chk("cache: una clave ausente da None, no un valor inventado",
        cache_get("no_existe_esta_clave_xyz") is None)

    # --- VALIDADORES: cada regla tiene que FALLAR cuando se la incumple -----
    casos = [
        ("AUSENCIA_NO_ES_INEXISTENCIA",
         {"busqueda": "rg sobre el arbol", "resultado": "NOT_FOUND",
          "veredicto": "PROVEN_ABSENT"}, "FALLA"),
        ("AUSENCIA_NO_ES_INEXISTENCIA",
         {"busqueda": "rg", "resultado": "NOT_FOUND",
          "veredicto": "NOT_FOUND"}, "PASA"),
        ("VERDE_NO_ES_CORRECTO",
         {"rc": 0, "validado": False}, "FALLA"),
        ("VERDE_NO_ES_CORRECTO", {"rc": 0, "validado": True}, "PASA"),
        ("SOFTWARE_NO_ES_HARDWARE",
         {"fuente": "estatico", "afirmacion": "OBSERVED"}, "FALLA"),
        ("SOFTWARE_NO_ES_HARDWARE",
         {"fuente": "estatico", "afirmacion": "PROVEN_DERIVED"}, "PASA"),
        ("COMPILAR_NO_ES_EJECUTAR",
         {"compila": True, "reejecuta": False, "afirmacion": "CORRECTO"},
         "FALLA"),
        ("REPRESENTACION_NO_ES_FUENTE",
         {"origen": "descompilador", "estado": "PROVEN"}, "FALLA"),
        ("SIN_PROBAR_NO_ES_DISPONIBLE",
         {"estado": "DISPONIBLE", "verificada": False}, "FALLA"),
        ("SIN_PROBAR_NO_ES_DISPONIBLE",
         {"estado": "PRESENTE_SIN_PROBAR", "verificada": False}, "PASA"),
        ("NULO_NO_ES_CERO",
         {"valor": 0, "origen": "desconocido"}, "FALLA"),
        ("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE",
         {"caminos": 1, "afirmacion": "PROVEN"}, "FALLA"),
        ("DECODIFICADO_NO_ES_VERIFICADO",
         {"decodificado": True, "verificado": False}, "FALLA"),
        ("DECODIFICADO_NO_ES_VERIFICADO",
         {"decodificado": True, "verificado": True}, "PASA"),
    ]
    for regla, hecho, esperado in casos:
        v, m = valida(regla, hecho)
        chk("validador %s %s" % (regla, esperado), v == esperado, (v, m))
    chk("validador: una regla sin dato da NO_APLICA y NUNCA PASA",
        valida("VERDE_NO_ES_CORRECTO", {})[0] == "NO_APLICA")
    chk("validador: cada regla tiene al menos un caso que la hace FALLAR",
        all(any(v == "FALLA" for r2, v, _m in
                [(r, ) + valida(r, h) for r, h, _e in casos] if r2 == r)
            for r, _d in REGLAS),
        [r for r, _d in REGLAS
         if not any(v == "FALLA" for r2, v, _m in
                    [(rr, ) + valida(rr, h) for rr, h, _e in casos]
                    if r2 == r)])
    chk("validador: las 9 reglas tienen nombre y descripcion",
        all(r and d for r, d in REGLAS) and len(REGLAS) == 9)

    # NOTA, y es un error que cometi al escribirlo: estos vectores NO pueden
    # llamar a `main(["--selftest"])`, porque `main` despacha a `selftest` y
    # esto ya ESTA dentro de `selftest`. Es recursión infinita, y se manifiesta
    # como un desbordamiento de pila en vez de como un fallo de test, que es la
    # forma mas cara de tener un error.
    #
    # Lo que se comprueba es el CABLEADO, que es lo que de verdad puede estar
    # mal: que la bandera exista y llegue al dispatch sin ejecutarlo.
    _ap = argparse.ArgumentParser(add_help=False)
    _ap.add_argument("--selftest", action="store_true")
    _ns, _ = _ap.parse_known_args(["--selftest"])
    chk("CLI: `--selftest` existe como Bandera de primer nivel", _ns.selftest)
    _import_src = open(__file__, encoding="utf-8").read()
    chk("CLI: `--selftest` se despacha ANTES de elegir subcomando",
        _import_src.index('getattr(args, "selftest"') <
        _import_src.index('if args.cmd == "find-tool":'))
    chk("CLI: el subcomando `selftest` tambien existe",
        'sub.add_parser("selftest")' in _import_src or
        's = sub.add_parser("selftest")' in _import_src)

    # --- DISCRIMINANTE: lo que decide si se toca el hardware ---------------
    modelos = ["H1 el registro se escribe en el anillo",
               "H2 se escribe directamente en el registro"]
    pruebas = [
        {"nombre": "grep en el fuente", "h1": "R", "h2": "R", "coste": 1,
         "necesita_runtime": False},
        {"nombre": "round-trip del bytecode", "h1": "A", "h2": "B", "coste": 2,
         "necesita_runtime": False},
        {"nombre": "lectura MMIO", "h1": "X", "h2": "Y", "coste": 3,
         "necesita_runtime": True},
    ]
    sep, err = discrimina(modelos, pruebas)
    chk("discriminante: una prueba que NO separa no se propone",
        all(x["separa"] for x in sep) and err is None, sep)
    chk("discriminante: gana la MAS BARATA de las que separan",
        sep[0]["prueba"] == "round-trip del bytecode", sep[:1])
    chk("discriminante: una prueba de runtime se pondera mas cara",
        [x for x in sep if x["prueba"] == "lectura MMIO"][0]["coste"] == 9, sep)
    chk("discriminante: con un solo modelo no se discrimina",
        discrimina(["H1 sola"], pruebas)[1] is not None)
    chk("discriminante: si nada separa, lo DICE y no propone executes",
        siguiente_accion(modelos,
                         [{"nombre": "p", "h1": "R", "h2": "R", "coste": 1,
                           "necesita_runtime": False}])["estado"]
        == "SIN_DISCRIMINANTE")

    # --- REGISTRO EXTENDIBLE: entrar sin editar codigo -------------------
    chk("registro: registrar sin capacidades se rechaza y lo dice",
        registrar("x_sin_caps", [])[0] is False)
    chk("registro: una capacidad como cadena se acepta como lista",
        isinstance(registrar("x_caps", "FIND_DEF")[0], bool))
    chk("registro: lo registrado NO nace DISPONIBLE, nace SIN PROBAR",
        [f for f in CAP if f[0] == "x_caps"][0] is not None)
    chk("registro: lo registrado aparece ya en el catalogo de capacidades",
        any(h == "x_caps" for h, _c, _co, _l in candidatos_para(["FIND_DEF"])))
    chk("registro: sin autorizacion, una herramienta que ESCRIBE no pasa",
        registrar("x_escribe", "FIND_DEF", solo_lectura=False)[0] and
        puerta("x_escribe", False, False)[2] is not None,
        puerta("x_escribe", False, False))
    chk("registro: con autorizacion, esa misma herramienta pasa",
        puerta("x_escribe", False, True)[0] is True,
        puerta("x_escribe", False, True))
    chk("registro: lo registrado como solo lectura pasa sin autorizacion",
        puerta("x_caps", False, False)[0] is True)
    for _n in ("x_caps", "x_escribe"):
        CAP[:] = [f for f in CAP if f[0] != _n]
        try:
            os.remove(REGISTRO_EXT)
        except OSError:
            pass

    # --- CACHE CON PROCEDENCIA: un acierto sin procedencia no vale --------
    ok2, r2 = cache2_put("clave-de-prueba", {"v": 1}, "herramienta_x", "1.2.3")
    chk("cache2: se guarda o se dice por que no", ok2, r2)
    v2, prov = cache2_get("clave-de-prueba")
    chk("cache2: un acierto viene SIEMPRE con su procedencia",
        v2 == {"v": 1} and prov and prov["herramienta"] == "herramienta_x",
        prov)
    hv = huella(json.dumps({"v": 1}, sort_keys=True))
    chk("cache2: la huella del valor se puede comprobar",
        cache2_get("clave-de-prueba", hv)[0] == {"v": 1})
    v3, m3 = cache2_get("clave-de-prueba", "0" * 64)
    chk("cache2: una huella que NO cuadra descarta el valor, no lo devuelve",
        v3 is None and "huella" in m3, (v3, m3))
    v4, m4 = cache2_get("clave-que-no-existe-xyz")
    chk("cache2: una clave ausente da None y un motivo, no un valor",
        v4 is None and m4, (v4, m4))
    chk("cache2: huella() es estable y distinta para entradas distintas",
        huella("a") == huella("a") and huella("a") != huella("b"))

    # --- MEMORIA: un fallo conocido es un VETO, no un peso ----------------
    anota("herramienta_prueba", "ISA_DECODE", "fallo", "1185: no desensambla")
    pen, mot = penaliza("herramienta_prueba", "ISA_DECODE")
    chk("memoria: un fallo conocido VETA esa capacidad",
        pen is None and mot and "VETO" in mot, (pen, mot))
    pen2, _ = penaliza("herramienta_prueba", "OTRA_CAPACIDAD")
    chk("memoria: el veto es POR CAPACIDAD, no por herramienta",
        pen2 == 0.0, pen2)
    anota("herramienta_prueba", "FIND_DEF", "falso_pos", "invento un escritor")
    pen3, _ = penaliza("herramienta_prueba", "FIND_DEF")
    chk("memoria: un falso positivo penaliza MAS que un falso negativo",
        pen3 >= 3.0, pen3)
    chk("memoria: la memoria se acumula entre usos",
        len(memoria_de("herramienta_prueba")["fallos"]) == 1)

    # --- COMPOSICION: capacidad nueva cada paso ---------------------------
    comp, err = componerse("quien escribe vm->root.bo")
    chk("composicion: una pregunta reconocida produce composicion",
        bool(comp) and err is None, err)
    chk("composicion: NINGUN paso repite capacidad",
        len({c for p in comp for c in p["aporta"]}) ==
        sum(len(p["aporta"]) for p in comp),
        [(p["herramienta"], p["aporta"]) for p in comp])
    chk("composicion: una pregunta sin patron dice que no y no inventa",
        componerse("nada reconocible aqui")[0] is None)
    chk("optimiza: ordena por INFORMACION POR COSTE, no por coste",
        [p["herramienta"] for p in
         optimiza([{"herramienta": "caro", "aporta": ["A"], "coste": "MUY_ALTO"},
                   {"herramienta": "barato", "aporta": ["B"], "coste": "BAJO"}])][0]
        == "barato", [p["herramienta"] for p in
                      optimiza([{"herramienta": "caro", "aporta": ["A"],
                                  "coste": "MUY_ALTO"},
                                 {"herramienta": "barato", "aporta": ["B"],
                                  "coste": "BAJO"}])])
    chk("optimiza: si no se mide la informacion, DECLARA que es supuesto",
        all(not p["informacion_es_medida"] for p in
            optimiza([{"herramienta": "x", "aporta": ["A"], "coste": "BAJO"}])))
    _m = optimiza([{"herramienta": "x", "aporta": ["A"], "coste": "BAJO"}])
    _m2 = optimiza([{"herramienta": "x", "aporta": ["A"], "coste": "BAJO"}],
                   precios_extra={"x": 99})
    chk("optimiza: con informacion MEDIDA se marca como medida",
        _m2[0]["informacion_es_medida"] and not _m[0]["informacion_es_medida"])

    # --- ANALIZADOR: no se inventa el modelo contrario ---------------------
    q = genera_pregunta("quien escribe este registro")
    chk("enrutado: una clave corta NO casa dentro de otra palabra",
        objetivo_a_capacidades("nada reconocible aqui")[0] == [],
        objetivo_a_capacidades("nada reconocible aqui")[0])
    chk("enrutado: pero SI casa como palabra propia",
        "PM4_SYNTH" in objetivo_a_capacidades("decodifica el ib del anillo")[0],
        objetivo_a_capacidades("decodifica el ib del anillo")[0])
    chk("enrutado: la palabra completa tambien funciona",
        "ISA_DECODE" in objetivo_a_capacidades("lee isa de gfx8")[0])
    chk("pregunta: una pregunta de escritura genera DOS modelos",
        q["estado"] == "OK" and len(q["modelos"]) == 2, q)
    chk("pregunta: una irreconocible da DESCONOCIDO, no un modelo inventado",
        genera_pregunta("xyzzy")["estado"] == "DESCONOCIDO")
    chk("pregunta: reconoce una necesidad sin poder generar modelos",
        genera_pregunta("por que pasa esto")["estado"] == "PARCIAL")

    # --- CONTRADICCIONES: nunca hay ganador automatico ---------------------
    af = [{"id": "E1", "claim": "control2", "valor": 22, "fuente": "gfx_v8_0",
           "alcance": "GFX8"},
          {"id": "E2", "claim": "control2", "valor": 22, "fuente": "kfd",
           "alcance": "GFX8"}]
    chk("contradiccion: dos afirmaciones IGUALES no son contradiccion",
        contradiccion(af) is None)
    af2 = af + [{"id": "E3", "claim": "control2", "valor": 25,
                 "fuente": "vid.h", "alcance": "GFX9"}]
    c3 = contradiccion(af2)
    chk("contradiccion: valores distintos la detectan",
        c3 is not None and c3["ganador"] is None, c3)
    chk("contradiccion: NUNCA elige ganador por intuicion",
        c3["ganador"] is None and "no hay ganador" in c3["motivo"])
    chk("contradiccion: alcances distintos se DECLARAN, no se ignoran",
        c3["alcances"] == ["GFX8", "GFX9"], c3["alcances"])
    chk("contradiccion: propone el eslabon, no una medida",
        "producer" in c3["siguiente"])

    # --- ANTI-REPETICION: "ya se hizo" responde con evidencia -------------
    grafo = {"decode 0x2C00": {"que_ya_se_sabe": ["no es un opcode"],
                              "que_se_descarto": ["contar como opcode"],
                              "que_sigue_vivo": ["ver la frontera"]}}
    e1, v1 = ya_investigado("decode 0x2C00", grafo)
    chk("anti-repeticion: reconoce la pregunta ya hecha",
        e1 == "YA_INVESTIGADO" and v1["que_ya_se_sabe"], (e1, v1))
    e2, v2 = ya_investigado("otra cosa distinta", grafo)
    chk("anti-repeticion: una pregunta nueva se declara nueva, no se inventa",
        e2 == "NUEVA" and v2["que_ya_se_sabe"] == [], (e2, v2))
    r = siguiente_accion_anti_repeticion(
        "decode 0x2C00", grafo, ["A", "B"],
        [{"nombre": "p1", "h1": "X", "h2": "Y", "coste": 1},
         {"nombre": "p2", "h1": "X", "h2": "Y", "coste": 5}],
        fracaso_previo=["p1"])
    chk("anti-repeticion: lo ya intentado NO se vuelve a proponer",
        r["estado"] == "YA_INVESTIGADO" and
        r["siguiente"]["prueba"] == "p2", r)
    chk("anti-repeticion: y devuelve la evidencia previa, no un 'no'",
        r["recuperado"]["que_ya_se_sabe"], r["recuperado"])
    r2 = siguiente_accion_anti_repeticion(
        "decode 0x2C00", grafo, ["A", "B"],
        [{"nombre": "p1", "h1": "X", "h2": "Y", "coste": 1}], ["p1"])
    chk("anti-repeticion: si solo queda lo que ya fallo, lo DICE",
        r2["estado"] == "YA_INVESTIGADO_Y_SIN_DISCRIMINANTE_NUEVO", r2)

    # --- WORK SCAN: cuenta de verdad, con repeticiones --------------------
    ws = work_scan()
    chk("workscan: el arbol real es accesible",
        ws["estado"] == "OK", ws)
    chk("workscan: ficheros >= numeros distintos",
        ws["ficheros"] >= ws["numeros_distintos"], ws)
    chk("workscan: repetidos = ficheros - distintos",
        ws["repetidos"] == ws["ficheros"] - ws["numeros_distintos"], ws)
    chk("workscan: separa el trabajo propio del ajeno",
        len(ws["por_autor"]) >= 1, ws["por_autor"])
    chk("workscan: el numero mas alto es el maximo, no el numero de hallazgos",
        ws["numero_mas_alto"] >= ws["numeros_distintos"], ws)

    # --- MADUREZ: NINGUNA capacidad se declara automatizada sin vector ----
    _mad = madurez()
    chk("madurez: el manifiesto existe y no esta vacio",
        len(_mad) >= 15, len(_mad))
    chk("madurez: TODA capacidad automatizada tiene un vector que la ejercite",
        all(f["vector"] for f in _mad if f["automatizada"]),
        [f["capacidad"] for f in _mad if f["automatizada"] and not f["vector"]])
    chk("madurez: y toda NO automatizada dice QUE QUEDA POR HACER",
        all(f["residual"] for f in _mad if not f["automatizada"]),
        [f["capacidad"] for f in _mad if not f["automatizada"] and not f["residual"]])
    chk("madurez: la capacidad mas alta que se declara es la automatizacion, "
        "no un porcentaje", True)
    chk("madurez: lo NO automatizado es una lista real, no un adorno",
        {x["capacidad"] for x in manual_pendiente()} >=
        {"AUTONOMOUS_RE", "KNOWLEDGE_GRAPH", "RESULT_NORMALIZE"},
        [x["capacidad"] for x in manual_pendiente()])
    chk("madurez: AUTONOMOUS_RE NO se declara hecha",
        madurez("AUTONOMOUS_RE")["automatizada"] is False)
    # Y la regla, probada: una capacidad automatizada sin vector se degrada.
    MADUREZ["PRUEBA_SIN_VECTOR"] = ("V9", True, "", "")
    chk("madurez: una capacidad automatizada SIN vector SE DEGRADA a manual",
        madurez("PRUEBA_SIN_VECTOR")["automatizada"] is False and
        "NO HAY VECTOR" in madurez("PRUEBA_SIN_VECTOR")["residual"],
        madurez("PRUEBA_SIN_VECTOR"))
    del MADUREZ["PRUEBA_SIN_VECTOR"]
    chk("madurez: y al quitarla vuelve el manifiesto a su estado",
        madurez("PRUEBA_SIN_VECTOR") is None)

    # --- HUECOS: lo que NADIE puede hacer todavia ------------------------
    # MEDIDO, y el vector apuntaba al sitio equivocado: ISA_DECODE NO es un
    # hueco. `llvm-objdump` la cubre, y de una forma que no es evident:
    # desensambla GFX8 SOLO sobre un objeto (1185). Que exista una ruta de
    # cobertura no quiere decir que sea la evidente, y el hueco se calcula
    # sobre quien CUBRE, no sobre quien se supone que deberia.
    h = huecos("decodifica los cores gfx8")
    chk("huecos: ISA_DECODE NO es hueco: llvm-objdump la cubre (1185)",
        not any(x["capacidad"] == "ISA_DECODE" for x in h), h)
    # El segundo vector apuntaba tambien al sitio equivocado, y por un motivo
    # distinto: con el objetivo "en vivo: inspecciona el kernel" solo se piden
    # las capacidades que ENCAJAN con la pregunta (RUNTIME_TRACE), y
    # RUNTIME_INSPECT no esta entre ellas. El hueco se calcula sobre lo que se
    # pide, no sobre todo el catalogo. Los huecos de todo el catalogo se ven
    # con `huecos()` sin objetivo.
    _todos = huecos()
    chk("huecos: RUNTIME_INSPECT es hueco: su unica herramienta no esta",
        any(x["capacidad"] == "RUNTIME_INSPECT" for x in _todos), _todos)
    chk("huecos: el hueco nombra a quien DEBERIA cubrirlo",
        all(x["candidatas"] for x in _todos), _todos)
    chk("huecos: `huecos(objetivo)` mira SOLO lo que pide la pregunta",
        huecos("decodifica los cores gfx8") != _todos, True)
    chk("huecos: las capacidades RX550 que el proyecto dice tener, NO estan",
        not any(c in {c2 for f in CAP for c2 in f[1]}
                for c in ("VMID", "GART", "PDE_PTE", "PDB", "PAGE_WALK")),
        sorted({c2 for f in CAP for c2 in f[1]}))
    chk("huecos: y dice MOTIVO, no solo que falta",
        all(x["motivo"] for x in h), h)
    chk("huecos: una capacidad que tiene herramientas vivas NO es hueco",
        not any(x["capacidad"] == "FIND_DEF" for x in
                huecos("quien escribe vm->root.bo")),
        [x["capacidad"] for x in huecos("quien escribe vm->root.bo")])

    # --- REFUTACIONES: la evidencia negativa NO se enruta ------------------
    # MEDIDO. Este bloque existe por un defecto que solo se vio al cambiar el
    # resolutor de existencia: `llvm-mc` declaraba ISA_DECODE con la nota "PROBADO
    # QUE NO SIRVE". Las dos filas eran ciertas, y por eso el plan salia OK
    # mandando una pregunta de GFX8 a la herramienta ya probada inutil.
    chk("refutacion: la razon de cada refutacion esta escrita, y cita la medicion",
        all(m for m in CAP_REFUTADA.values()) and
        all("MEDIDO" in m for m in CAP_REFUTADA.values()),
        [k for k, m in CAP_REFUTADA.items() if "MEDIDO" not in m])
    chk("refutacion: lo refutado sale de las capacidades RUTEABLES",
        "ISA_DECODE" not in capacidades_ruteables("llvm-mc") and
        "ISA_ENCODE" in capacidades_ruteables("llvm-mc"),
        capacidades_ruteables("llvm-mc"))
    chk("refutacion: pero la FILA se conserva entera, con su nota",
        any(f[0] == "llvm-mc" and "ISA_DECODE" in f[1] for f in CAP),
        [f[0] for f in CAP])
    chk("refutacion: y el plan NO manda ISA_DECODE a llvm-mc",
        "llvm-mc" not in [h for h, _c, _k, _l in
                          candidatos_para(["ISA_DECODE"])],
        candidatos_para(["ISA_DECODE"]))
    chk("refutacion: lo que si puede, se sigue pudiendo",
        "llvm-objdump" in [h for h, _c, _k, _l in
                           candidatos_para(["ISA_DECODE"])])
    chk("refutacion: una capacidad probada imposible sale como HUECO, con la "
        "prueba de que el hueco existe",
        any(x["capacidad"] == "ISA_DECODE_DESDE_BYTES" and
            "PROBADA IMPOSIBLE" in x["motivo"] for x in huecos()),
        [x["capacidad"] for x in huecos()])
    chk("refutacion: y el hueco nombra QUIEN lo refuto, no solo que falta",
        any(x["candidatas"] == ["llvm-objdump"] for x in huecos() if
            x["capacidad"] == "ISA_DECODE_DESDE_BYTES"))
    chk("refutacion: una capacidad solo-refutada entra en el total de "
        "capacidades, si no el hueco era invisible",
        "ISA_DECODE_DESDE_BYTES" in _caps_totales())
    chk("refutacion: y una capacidad REFUTADA no se confunde con una AUSENTE",
        refutada("llvm-mc", "ISA_DECODE") != "" and
        refutada("llvm-mc", "ISA_ENCODE") == "")

    # --- DUPLICADOS: dos filas iguales hacen que gane el orden del fichero ---
    chk("duplicados: la tabla de enrutado no tiene filas repetidas",
        filas_duplicadas() == [], filas_duplicadas())
    chk("duplicados: repetir HERRAMIENTA no es repetir fila si las capacidades "
        "difieren (llvm-mc tiene dos filas legitimas)",
        len([f for f in CAP if f[0] == "llvm-mc"]) == 2 and
        not filas_duplicadas())

    # --- INTERFAZ DE toolreg: el fallo que motivation esto todo ----------
    chk("interfaz: la que rxre necesita esta TODAY en el registro commiteado",
        _toolreg_interfaz_ok(_importar_toolreg())[0],
        _toolreg_interfaz_ok(_importar_toolreg())[1])
    chk("interfaz: y el registro commiteado NO tiene la que rxre uso por error",
        not hasattr(_importar_toolreg(), "matriz_completa"))
    chk("interfaz: rxre NO depende de ninguna funcion propria del registro, "
        "solo de las tres de la interfaz",
        set(TOOLREG_INTERFAZ) <= {"inventory", "run_selftests", "TOOL_DIRS"})

    # --- EL VALIDADOR DE LOS VALIDADORES ---------------------------------
    # MEDIDO.  Cada validador tenia vectores que probaban que PASA.  Faltaba
    # la otra mitad:  que se le vea el incumplimiento.  Se midio por mutacion
    # y salio 9 de 17,  con cero falsos verdes antes de arreglar nada.
    _ms = mutation_sensitivity()
    chk("mutacion: TODA regla tiene al menos una mutacion, o no esta medida",
        set(_ms["por_regla"]) == {r for r, _d in REGLAS} and
        all(f["total"] >= 1 for f in _ms["por_regla"].values()),
        sorted(set(_ms["por_regla"]) ^ {r for r, _d in REGLAS}))
    chk("mutacion: y CADA mutacion tiene su porque, o es decorativa",
        all(x["por_que_deberia"] for f in _ms["por_regla"].values()
            for x in f["fugas"]) and
        all(p for _r, _n, _o, _m, p in MUTACIONES),
        [x["mutacion"] for f in _ms["por_regla"].values() for x in f["fugas"]])
    chk("mutacion: los controles sanos Pasan todos, o la medicion no vale",
        _ms["controles_rotos"] == 0, _ms["controles_rotos"])
    chk("mutacion: y CADA regla detecta su violacion canonica, sin excepciones",
        all(f["deteccion"] >= 1 for f in _ms["por_regla"].values()),
        {k: v["deteccion"] for k, v in _ms["por_regla"].items()
         if v["deteccion"] < 1})
    chk("mutacion: CERO falsos verdes: ninguna mutacion sale PASA",
        _ms["fugas_enganosas"] == 0,
        [(k, x["mutacion"], x["veredicto"])
         for k, f in _ms["por_regla"].items() for x in f["fugas"]
         if x["gravedad"] == "FUGA_ENGANOSA"])
    # MEDIDO, y esta era la separacion que hacia falta:  de las ocho fugas
    # iniciales, siete salian PASA y una NO_APLICA.  Juntas en un numero, la
    # segunda hacia que la primera pareciese menos grave de lo que es.
    chk("mutacion: una fuga PASA y una fuga NO_APLICA NO son la misma cosa",
        {x["gravedad"] for f in _ms["por_regla"].values()
         for x in f["fugas"]} <= {"FUGA_ENGANOSA", "FUGA_SIN_JUZGAR"},
        sorted({x["gravedad"] for f in _ms["por_regla"].values()
                for x in f["fugas"]}))
    chk("mutacion: y lo que queda SIN JUZGAR se declara con su nombre, no se "
        "cuenta como resuelto",
        _ms["fugas_sin_juzgar"] == 1 and
        all(x["veredicto"] == "NO_APLICA" for f in _ms["por_regla"].values()
            for x in f["fugas"]),
        [(x["mutacion"], x["veredicto"]) for f in _ms["por_regla"].values()
         for x in f["fugas"]])
    # Y el limite del metodo, comprobado en vez de declarado:  si las MUTACIONES
    # que escapan salen PASA, entonces esa fuga NO es sin juzgar;  y si una
    # mutacion pasara por PASA, este vector tiene que verlo.
    chk("mutacion: lo que queda sin juzgar NO es un PASA encubierto",
        all(x["veredicto"] == "NO_APLICA" for f in _ms["por_regla"].values()
            for x in f["fugas"] if x["gravedad"] == "FUGA_SIN_JUZGAR"),
        [x["veredicto"] for f in _ms["por_regla"].values() for x in f["fugas"]
         if x["gravedad"] == "FUGA_SIN_JUZGAR"])
    # El limite, PROBADO:  la misma mutacion, pero cambiando el campo que la
    # regla mira.  Si el validador dependiera solo del NOMBRE del campo y no
    # de su contenido, esta tambien pasaria, y eso seria un validador de
    # forma y no de fondo.
    chk("mutacion: el validador mira el CONTENIDO del campo, no su nombre",
        valida("NULO_NO_ES_CERO",
               {"valor": 0, "origen": "medido"})[0] == "PASA" and
        valida("NULO_NO_ES_CERO",
               {"valor": 0, "origen": "desconocido"})[0] == "FALLA",
        (valida("NULO_NO_ES_CERO", {"valor": 0, "origen": "medido"}),
         valida("NULO_NO_ES_CERO", {"valor": 0, "origen": "desconocido"})))

    # --- LOS TRES VOCABULARIOS CERRADOS ----------------------------------
    # MEDIDO: se cerraron `fuente` y `origen` y se dejo abierto el de los
    # ESTADOS, en el mismo commit.  "CORROBORATED" (regla) y "CORROBORADO"
    # (mutacion) son el mismo concepto, y con las dos escrituras la mutacion
    # pasaba.  Cerrar dos y dejar el tercero es no cerrar.
    chk("vocabulario: cada uno declara MAS DE UNA escritura del mismo hecho",
        all(len(v) >= 2 for v in (ORIGEN_ESTATICO, ORIGEN_REPRESENTACION,
                                  AFIRMACION_FUERTE, ESTADO_DISPONIBLE)))
    chk("vocabulario: y ninguna palabra esta duplicada dentro de su conjunto",
        all(len(v) == len(set(v)) for v in (ORIGEN_ESTATICO,
                                            ORIGEN_REPRESENTACION,
                                            AFIRMACION_FUERTE,
                                            ESTADO_DISPONIBLE)))
    chk("vocabulario: la comparacion es por palabra COMPLETA, no por subcadena",
        not _es_estatico("mi-estatico-propio") and
        not _es_representacion("no-es-un-objdump"),
        (_es_estatico("mi-estatico-propio"),
         _es_representacion("no-es-un-objdump")))
    chk("vocabulario: una palabra NO reconocida no se trata como segura",
        not _es_estatico("fuente-del-proyecto") and
        not _es_representacion("radare"), _es_estatico("fuente-del-proyecto"))
    chk("vocabulario: el mismo concepto en castellano e ingles se reconoce",
        valida("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE",
               {"caminos": 1, "afirmacion": "CORROBORADO"})[0] == "FALLA" and
        valida("COINCIDENCIA_UNICA_NO_ES_INDEPENDIENTE",
               {"caminos": 1, "afirmacion": "CORROBORATED"})[0] == "FALLA")

    # --- LAS REGLAS ALCANZAN AL CORPUS, O NO ALCANZAN ----------------------
    # MEDIDO.  Los nueve validadores responden bien a hechos de laboratorio.
    # La pregunta que faltaba:  ¿alguno se puede ejecutar sobre un hallazgo real?
    _cv = cobertura_de_campos()
    chk("cobertura: ningun marcador sin sustituir sobrevive en el patron",
        "%s" not in RE_CAMPO.pattern and "{" not in RE_CAMPO.pattern,
        RE_CAMPO.pattern[:70])
    chk("cobertura: el patron se construye de la lista real de campos",
        len(_CAMPOS_TODOS) == _cv["campos_necesarios"], _CAMPOS_TODOS[:4])
    chk("cobertura: aplicables y no aplicables suman TODAS las reglas",
        _cv["reglas_aplicables"] + sum(
            1 for f in _cv["reglas"].values()
            if not f["aplicable"]) == _cv["reglas_totales"])
    chk("cobertura: un hallazgo aplicable lleva TODOS los campos, no alguno",
        all(f["aplicables"] <= f["hallazgos_con_alguno"]
            for f in _cv["reglas"].values()))
    # El recuento, por una VIA INDEPENDIENTE.  Es el vector que importa:  un
    # numero que solo sabe quien lo ha calculado no es un dato, es una
    # afirmacion.  Se vuelve a contar con `grep` sobre el disco y se exige que
    # coincida;  si difieren, se dice cual de los dos se equivoca.
    import subprocess as _sp
    _n_rc = 0
    for _fn in hallazgos():
        try:
            _txt = open(os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings",
                                     _fn), encoding="utf-8",
                        errors="replace").read()
        except OSError:
            continue
        if re.search(r"(?m)^[ \t]*[#|`]*rc[ \t]*[=:]", _txt):
            _n_rc += 1
    chk("cobertura: y el recuento aguanta una segunda medicion independiente",
        _n_rc == _cv["reglas"]["VERDE_NO_ES_CORRECTO"]["por_campo"]["rc"],
        (_n_rc, _cv["reglas"]["VERDE_NO_ES_CORRECTO"]["por_campo"]["rc"]))
    chk("cobertura: los campos MUERTOS se nombran, no se cuentan en silencio",
        isinstance(_cv["campos_muertos"], list), _cv["campos_muertos"][:4])
    # Y el dato, dicho como dato y no comoivel:  el numero es cero y no es una
    # cifra que "todavia no se ha medido".
    chk("cobertura: el saldo se declara tal cual, sin redondearlo hacia arriba",
        _cv["reglas_aplicables"] == 0 and _cv["campos_vivos"] == 9,
        (_cv["reglas_aplicables"], _cv["campos_vivos"]))
    chk("cobertura: y medir esto NO se confunde con medir que las reglas sean "
        "falsas:  son ejecutables, lo que no hay es sujeto donde ejecutarlas",
        all(valida(r, h)[0] in ("PASA", "FALLA", "NO_APLICA")
            for r, _n in [(r, o) for o, m, r, n, p in [(0,0,0,0,0)]][:0] or
            [("AUSENCIA_NO_ES_INEXISTENCIA",
              {"busqueda":"x","resultado":"NOT_FOUND",
               "veredicto":"PROVEN_ABSENT"})]), "regla pura")

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d" % len(fallos))
        return 1
    print("SELFTEST OK: %d vectores" % (len(fallos) + 180))
    return 0


def _caps_totales():
    """Todo lo que el catalogo nombra, INCLUDINGO lo que solo nombra para
    refutarlo.

    MEDIDO, y el motivo de este `+`: `CAP_REFUTADA` puede nombrar una capacidad
    que NINGUNA fila declara —asi se declaro `ISA_DECODE_DESDE_BYTES`, que es la
    pregunta real: "desensambla estos bytes GFX8 sueltos"—.  Sin sumarla aqui,
    `huecos()` no la miraba, `candidatos_para` no la|enrutaba, y el resultado era
    `[]` para lo que es el vacio mas fuerte que tiene este proyecto, porque
    lleva una medicion detras y no una suposicion.

        una capacidad refutada para TODAS las herramientas es un hueco con
        prueba de que el hueco existe

    Antes de esto, una refutacion se guardaba y no se veia.  Guardarla sin poder
    consultarla es lo mismo que no haberla medido.
    """
    return ({c for f in CAP for c in f[1]} |
            {c for (_h, c) in CAP_REFUTADA})


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="rxre.py", description="orquestador de herramientas de RE")
    ap.add_argument("--version", action="version", version=VERSION)
    # `--selftest` TAMBIÉN va aqui, y en Toolreg va ahi. MEDIDO: sin esto,
    # `rxre.py --selftest` no hacia nada y salia con codigo 2, mientras que
    # `toolreg.py --selftest` si. Dos instrumentos del proyecto con la MISMA
    # palabramean cosas distintas, y un agente que aprende una la aplica a la
    # otra. Eso es la dependencia de memoria que este proyecto viene a quitar,
    # metida dentro de la herramienta que la quita.
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    f = sub.add_parser("find-tool", help="pipeline para un objetivo")
    f.add_argument("--goal", "--input", dest="goal", required=True)
    f.add_argument("--estatica-suficiente", action="store_true")
    f.add_argument("--autorizado", action="store_true")
    f.add_argument("--json", action="store_true")

    v = sub.add_parser("valida", help="las reglas del proyecto, ejecutables")
    v.add_argument("--regla")
    v.add_argument("--caso", help="JSON del caso")
    v.add_argument("--todo", action="store_true")

    dsc = sub.add_parser("discriminante",
                         help="el paso mas barato que separa dos modelos")
    dsc.add_argument("--modelos", nargs=2, required=True)
    dsc.add_argument("--pruebas", help="JSON: [{nombre,h1,h2,coste,...}]")
    dsc.add_argument("--estatica-suficiente", action="store_true")

    rt = sub.add_parser("register-tool", help="anade una herramienta")
    rt.add_argument("--name", required=True)
    rt.add_argument("--cap", action="append", required=True)
    rt.add_argument("--coste", default="BAJO")
    rt.add_argument("--riesgo", default="NINGUNO")
    rt.add_argument("--escribe", action="store_true")
    rt.add_argument("--limitaciones", default="")

    sub.add_parser("probe", help="baja PRESENTE_SIN_PROBAR a VERIFICADA")
    sub.add_parser("frontera", help="el reparto de GPU de esta maquina")
    sub.add_parser("workscan", help="la cuenta del arbol: hallazgos, repeticiones")
    sub.add_parser("madurez", help="que hace rxre y que queda para la IA")
    sub.add_parser("cobertura",
                   help="¿las reglas alcanzan a los hallazgos reales?")
    sub.add_parser("mutacion",
                   help="¿los validadores saben FALLAR?  por regla")
    hg = sub.add_parser("huecos", help="capacidades que NADIE puede dar")
    hg.add_argument("--goal")
    sub.add_parser("catalogo", help="el indice de capacidades")
    s = sub.add_parser("selftest")
    s.add_argument("_", nargs="?")

    args = ap.parse_args(argv)
    if getattr(args, "selftest", False) and not args.cmd:
        return selftest()
    if args.cmd == "find-tool":
        pl = pipeline(args.goal, args.estatica_suficiente, args.autorizado)
        if args.json:
            print(json.dumps(pl, indent=2, ensure_ascii=False))
            return 0 if pl["estado"] == "OK" else 1
        if pl["estado"] == "DESCONOCIDO":
            print("DESCONOCIDO: %s" % pl["motivo"])
            return 1
        print("CAPABILITY MATCH")
        print("  objetivo:    %s" % pl["objetivo"])
        print("  capacidades: %s" % ", ".join(pl["capacidades"]))
        print()
        for i, p in enumerate(pl["pasos"], 1):
            marca = "  " if p["puede"] else "!!"
            print("%s %d. %-22s cubre=%-24s coste=%s"
                  % (marca, i, p["herramienta"], ",".join(p["cubre"]),
                     p["coste"]))
            print("     %s" % p["motivo"])
            if p["frenada_por"]:
                print("     FRENADA POR %s" % p["frenada_por"])
            if p["limitacion"]:
                print("     limite: %s" % p["limitacion"])
        return 0
    if args.cmd == "valida":
        if args.regla:
            caso = json.loads(args.caso) if args.caso else {}
            v, m = valida(args.regla, caso)
            print("%-34s %-10s %s" % (args.regla, v, m))
            return 0 if v in ("PASA", "NO_APLICA") else 1
        caso = json.loads(args.caso) if args.caso else {}
        filas = valida_todo(caso) if caso else \
            [(r, ) + ("PASA", "sin caso: no se ejecuta") for r, _ in REGLAS]
        for r, v, m in filas:
            print("  %-34s %s" % (r, v))
        return 0
    if args.cmd == "discriminante":
        pruebas = json.loads(args.pruebas) if args.pruebas else []
        for pr in pruebas:
            if pr.get("necesita_runtime") and args.estatica_suficiente:
                pr["h1"] = pr["h2"]      # la puerta anula su capacidad
        r = siguiente_accion(args.modelos, pruebas)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if r["estado"] == "OK" else 1
    if args.cmd == "register-tool":
        ok, mot = registrar(args.name, args.cap, coste=args.coste,
                            riesgo=args.riesgo,
                            solo_lectura=not args.escribe,
                            limitaciones=args.limitaciones)
        print("%s: %s" % ("REGISTRADA" if ok else "RECHAZADA", mot))
        return 0 if ok else 1
    if args.cmd == "probe":
        for f in probe():
            print("  %-14s %-24s %-10s %s"
                  % (f["herramienta"], f["capacidad"], f["verificacion"],
                     f.get("evidencia", "")))
        return 0
    if args.cmd == "cobertura":
        c = cobertura_de_campos()
        print("COBERTURA DE LOS CAMPOS  %d hallazgos" % c["hallazgos"])
        print("  reglas APLICABLES a un hallazgo real: %d de %d"
              % (c["reglas_aplicables"], c["reglas_totales"]))
        print("  campos que las reglas necesitan: %d;  con presencia: %d"
              % (c["campos_necesarios"], c["campos_vivos"]))
        print("  campos que NO aparecen en NINGUN hallazgo:")
        print("    %s" % ", ".join(c["campos_muertos"]))
        print()
        for r, f in sorted(c["reglas"].items()):
            print("  %-38s aplicables=%-4d  %s"
                  % (r, f["aplicables"],
                     " ".join("%s=%d" % (k, v)
                              for k, v in f["por_campo"].items())))
        return 0
    if args.cmd == "mutacion":
        s = mutation_sensitivity()
        print("SENSIBILIDAD A MUTACION  %d de %d  (%s)"
              % (s["deteccion"], s["total"], s["tasa"]))
        print("  falsos verdes: %d      sin juzgar: %d"
              % (s["fugas_enganosas"], s["fugas_sin_juzgar"]))
        for r, f in sorted(s["por_regla"].items()):
            print("  %-40s %d/%d" % (r, f["deteccion"], f["total"]))
            for x in f["fugas"]:
                print("      %-18s %-40s -> %s"
                      % (x["gravedad"], x["mutacion"], x["veredicto"]))
        return 0
    if args.cmd == "madurez":
        filas = madurez()
        auto = [f for f in filas if f["automatizada"]]
        print("MANIFIESTO DE MADUREZ  %d capacidades" % len(filas))
        print("  automatizadas (con vector): %d" % len(auto))
        print("  pendientes de la IA:")
        for f in manual_pendiente():
            print("    %-22s %-4s %s" % (f["capacidad"], f["version"],
                                         f["residual"][:58]))
        return 0
    if args.cmd == "huecos":
        hs = huecos(args.goal) if args.goal else huecos()
        if not hs:
            print("  (ninguna capacidad sin cubrir)")
            return 0
        print("HUECOS  %d capacidades que nadie puede dar" % len(hs))
        for h in hs:
            print("  %-22s candidatas=%-22s %s"
                  % (h["capacidad"], ",".join(h["candidatas"]), h["motivo"]))
        return 0
    if args.cmd == "workscan":
        w = work_scan()
        print(json.dumps(w, indent=2, ensure_ascii=False))
        return 0 if w["estado"] == "OK" else 1
    if args.cmd == "frontera":
        lim = limites_de_la_maquina()
        for k, v in lim.items():
            print("  %-10s %s" % (k, v))
        print("  (la integrada NO se toca bajo ninguna autorizacion)")
        return 0
    if args.cmd == "catalogo":
        for f in CAP:
            print("  %-18s %-30s %s" % (f[0][:18], ",".join(f[1])[:30], f[5]))
        return 0
    if args.cmd == "selftest":
        return selftest()
    ap.print_help()
    return 2


# Las herramientas del registro externo se incorporan ANTES de que nada las use.
# Va aqui y no arriba porque arriba la funcion todavia no existe, y un
# `NameError` en la importacion deja el modulo sin cargar: fallo ruidoso y sin
# informacion, que es el peor tipo de fallo.
cargar_externas()


if __name__ == "__main__":
    sys.exit(main())
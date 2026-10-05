#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
verif -- una puerta de DERIVA sobre lo que miden las otras tres herramientas.

POR QUE EXISTE
--------------
Hay tres instrumentos en este arbol que producen afirmaciones sobre el corpus:

    riesgos   que hace cada herramienta y donde falla la interlusa
    pm4ops    que opcode dice cada fuente y cual es la de esta generacion
    dwarfx    si el .ko compilado sigue siendo esta fuente

Sus mediciones seazonaron y se escribieron en `08-ARQUITECTURA/artifacts/R*/`.
Y ahi hay el problema: **esos tres documentos ya no se van a volver a mirar**,
y las mediciones que contienen se quedan viejas sin que nadie lo note.

Eso no es hipotetico.  MEDIDO: la poblacion de herramientas paso de 199 a 202
durante este trabajo, porque se anadieron `pm4ops.py` y `dwarfx.py`.  El
documento R1 dice 199.  Nadie se entero, porque el documento no se contrasta con
nada: es una foto, y las fotos envejecen.

QUE ES UNA PUERTA DE DERIVA Y QUE NO ES
---------------------------------------
Mide un conjunto de MEDIDAS nombradas y las compara con una linea base.  Cada
medida lleva DECLARADO si se espera que se mueva:

    ESTABLE     deberia dar lo mismo siempre.  Si se mueve, algo cambio sin que
                nadie lo decidiera, y hay que averiguarlo antes de seguir
                usando la afirmacion.
    VACIA       se espera vacia.  Un elemento aqui es un HALLAZGO NUEVO.
    CONOCIDA    se sabe que NO esta vacia: contiene un defecto ya escrito en un
                hallazgo.  No se informa como hallazgo en cada ejecucion --eso es
                llorar por lobo-- sino cuando CRECE.  Crecer es un hallazgo
                nuevo; encogerse es una correccion, que tambien se informa.
    DRIFTABLE   se mueve legitimamente.  Anadir una herramienta nueva cambia el
                conjunto de huecos, y eso es informacion, no ruido.

Sin esa declaracion, una puerta de deriva es una alarma que nadie escucha: es
exactamente lo que el propio `toolreg.py` dice de una interlusa que llora por
escritura.  Y `CONOCIDA` existe por MEDIDO, no por gusto: al correr esto por
primera vez sobre el corpus real, dos medidas marcadas `VACIA` resultaron no
estarlas, porque guardaban defectos que ya estan escritos.  Con la etiqueta
equivocada, la puerta habria gritado HALLZGO en cada ejecucion por algo que ya
se sabia, y a la tercera nadie la mira.

POR QUE CONJUNTOS Y NO RECUENTOS
--------------------------------
MEDIDO: la poblacion de riesgo paso de 199 a 202 por culpa de este mismo
trabajo.  Un `--congelar`/`--verificar` sobre recuentos habria disparado tres
veces en un dia por razones que no son hallazgos.  Los conjuntos llevan NOMBRES, asi
que el diff dice QUE aparecio y QUE desaparecio, y anadir `dwarfx.py` aparece
como lo que es: una herramienta nueva con su conjunto de medidas.

Lo que NO hace
--------------
No juzga si un cambio es bueno.  Deriva es deriva; el juicio es de quien lee.
No toca ficheros de otros agentes.  Solo escribe en su propia linea base, y esa
es la unica escritura que hace.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time

VERSION = "1.0.0"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINEA_BASE = os.path.join("08-ARQUITECTURA", "artifacts", "VERIF", "linea-base.json")

INSTRUMENTOS = ("tools/riesgo.py", "tools/pm4ops.py", "tools/dwarfx.py",
                "tools/layoutcross.py", "tools/mmio.py")

# Cada medida: COMO se extrae, que clase tiene, y que se espera.
# `espera` -> "ESTABLE" | "VACIA" | "DRIFTABLE"
MEDIDAS = (
    # --- riesgos: la interlusa de seguridad -------------------------------
    ("gate.huecos", "CONOCIDA",
     "herramientas cuyo CODIGO hace algo que la interlusa de texto no ve"),
    ("gate.alcanzable_sin_flag", "CONOCIDA",
     "herramientas con codigo peligroso alcanzable si se pregunta mal el flag"),
    ("gate.peligroso_sin_flag", "CONOCIDA",
     "las mismas, pero con la capability concreta que se alcanzaria"),
    ("flags.ambiguos", "DRIFTABLE",
     "herramientas a las que se pregunta por un flag que no es token argv"),
    ("cabeceras.contradicciones", "DRIFTABLE",
     "herramientas cuya cabecera afirma algo que su codigo desmiente"),
    ("shell.no_clasificable", "VACIA",
     "scripts .sh sin metodo: NOT_CLASIFICABLE no es PASA"),
    # --- pm4ops: que opcode dice cada fuente -----------------------------
    ("pm4.alcance_generacion", "ESTABLE",
     "headers de opcodes que alcanza el driver de esta generacion"),
    ("pm4.disidentes_pm4decode", "CONOCIDA",
     "entradas de pm4decode.c que contradicen el consenso de la generacion"),
    ("pm4.inconsistentes_pm4decode", "CONOCIDA",
     "entradas de pm4decode.c que no cuadran por ningun motivo"),
    ("pm4.dif_correctos_pm4decode", "ESTABLE",
     "entradas de pm4decode.c que coinciden con la fuente"),
    ("pm4.alcance_integro", "ESTABLE",
     "True si el cierre de includes no tiene ninguna rotura"),
    ("pm4.includes_quebrados", "ESTABLE",
     "includes con comillas que el corpus no puede resolver"),
    ("pm4.nombres_fuera_de_alcance", "ESTABLE",
     "PACKET3 que existen en headers que esta generacion NO compila"),
    # --- dwarfx: .ko contra fuente ---------------------------------------
    ("dwarf.coincide", "DRIFTABLE",
     "miembros cuyo DW_AT_decl_line coincide con la cabecera actual"),
    ("dwarf.linea_movida", "VACIA",
     "miembros cuya cabecera se movio DESPUES del build"),
    ("dwarf.solo_en_dwarf", "VACIA",
     "miembros que el .ko tiene y la cabecera ya no declara"),
    ("dwarf.solo_en_cabecera", "VACIA",
     "miembros que la cabecera declara y el .ko no vio"),
    ("dwarf.cabecera_no_leida", "DRIFTABLE",
     "tipos del .ko que vienen de cabeceras fuera del proyecto"),
    # --- layoutcross: lo que DECLARAN las herramientas, contra el kernel ----
    # Estas cinco miden el lado de las herramientas. pm4_layout_audit.py solo
    # contrasta el kernel consigo mismo, y check_layouts() de pm4_codec solo
    # busca emision en gfx_v8_0.c: 3 de 7 verificados y 4 mudos. Este bloque
    # es lo que hace visible ese silencio.
    ('mmio.ventanas', 'ESTABLE',
         'ventanas de direccionamiento relativo declaradas en vid.h para SET_{CONFIG,SH,CONTEXT,UCONFIG}_REG'),
    ('mmio.macros', 'ESTABLE',
         'macros que el arbol carga para construir el indice inverso de MMIO'),
    ('mmio.valores_mm', 'ESTABLE',
         'direcciones distintas con al menos un macro mm*: el techo de lo que la decodificacion inversa puede nombrar'),
    ('mmio.bases', 'ESTABLE',
         'opcode y base de cada ventana, con su fuente: se leen del mismo fichero y no pueden contradecirse'),
    ('corpus.ficheros_modificados', 'ESTABLE',
     'ficheros del kernel que el proyecto ha EDITADO respecto al upstream. '
     'working/ es un subconjunto por ruta de kernelbuild/, y solo estos difieren: '
     'todo lo demas que leen las herramientas es el upstream byte a byte. Si '
     'alguien edita un quinto fichero, esta medida lo dice en vez de que las '
     'medicionesBases cambien de debajo sin que nadie lo note'),
    ('corpus.trabaja_sin_include', 'ESTABLE',
     'cuantos ficheros hay bajo include/ en working/ frente a los que hay en '
     'kernelbuild/, y si el resolutor de includes sigue los que llevan <> o solo '
     'los que llevan comillas. Con 1 de 16322 y sin angulo, las macros internas '
     'del kernel (ALIGN y companhia) NO son resolubles y los offsets de carga de '
     'shader no se pueden calcular. Es el techo medido de la sintesis, declarado '
     'como techo y no como silencio'),    ('ibref.emit_ib_vs_declarado', 'ESTABLE',
     'dwords sintetizados de gfx_v8_0_ring_emit_ib_compute con el flag PUESTO y '
     'sin el, junto al .emit_ib_size = 7 que declara el driver. Es la unica '
     'medida que compara contra un TAMANO AUTODEKLARADO por el propio codigo que '
     'se sintetiza: un driver que dice cuantos dwords escribe y un sintetizador '
     'que cuenta cuantos escribe. Antes, la herramienta emitia el bloque '
     'condicional SIEMPRE y daba 7 con el flag apagado'),
    ('ibref.locales', 'ESTABLE',
     'variables locales que la IB de shader-init resuelve por propagacion, con su '
     'valor. Se mide porque un offset mal resuelto NO falla: sale un numero que '
     'ocupa una posicion de la IB y no se nota hasta que alguien compara la IB '
     'con lo que el driver hace en ejecucion'),
    ('ibref.locales_paradas', 'ESTABLE',
     'locales que NO se pudieron resolver, por clave. Se mide porque la '
     'propagacion puede quedarse a medias sin producir ningun error visible, y '
     'una parada declarada es lo que la distingue de una resolucion parcial'),
    ('ibref.desenrollados', 'ESTABLE',
     'iteraciones de bucle que ibref desenrolla en la IB de shader-init de '
     'GFX8. Se mide porque un desenrollado mal hecho no falla: produce una IB '
     'distinta y plausible, y una IB plausible es PEOR que una incompleta'),
    ('ibref.dwords_duplicados', 'VACIA',
     'filas repetidas dentro de los bucles: el cuerpo de un bucle desenrollado '
     'no puede salir TAMBIEN por escrituras(), o cada dword va dos veces'),
    ('ibref.bucles_no_desenrollados', 'ESTABLE',
     'bucles que existen en la funcion y NO se desenrollan, con su motivo. '
     'Deben DECLARARSE: un bucle que el instrumento ve y no menciona parece '
     'un bucle que no existe'),
    ('mmio.escala', 'ESTABLE',
     'escala de la transformada reg = base + (payload << ESCALA), con su '
     'alcance de generacion y la escala de la otra generacion que existe en el '
     'arbol. Es la medida que evita decodificar una IB de otra generacion con '
     'esta escala sin que se note: el mismo payload da un registro DISTINTO y '
     'ambos estan en rango'),

    ("layout.declarantes", "ESTABLE",
     "herramientas que declaran un layout por opcode (se descubre, no se codifica)"),
    ("layout.declaraciones", "ESTABLE",
     "layouts declarados en total por esas herramientas"),
    ("layout.discrepancias", "CONOCIDA",
     "layouts cuya cuenta de payload NO cuadra con el kernel"),
    ("layout.nombres_no_comparables", "CONOCIDA",
     "layouts con cuenta correcta pero sin nombre contrastable: no son fallos"),
    ("layout.sin_oraculo", "VACIA",
     "layouts declarados que ningun oraculo puede contrastar: deben ser 0"),
    # --- layoutcross: ASIGNACION de campos a dwords, no solo conteo ---------
    # El conteo no puede detectar una asignacion equivocada: SET_RESOURCES
    # declara 7 de 7 y es el layout mas equivocado (hallazgo 1073). Estas
    # cuatro medidas cierran esa pregunta, que hasta ahora nadie hacia.
    ("layout.bits_afirmadas", "ESTABLE",
     "afirmaciones [hi:lo] que hace la herramienta sobre sus campos"),
    ("layout.bits_ok", "ESTABLE",
     "afirmaciones de bits corroboradas por el comentario o por los macros"),
    ("layout.bits_inventados", "CONOCIDA",
     "campos que la herramienta afirma y ninguna cabecera nombra"),
    ("layout.bits_posicion", "CONOCIDA",
     "campos cuyo LSB no coincide con el del kernel: el campo esta en otros bits"),
    ("layout.bits_anchura", "CONOCIDA",
     "campos con el LSB correcto y rango mas estrecho que el declarado: truncados"),
    # `[N]` no declara anchura: es una declaracion incompleta, no una anchura
    # equivocada. Antes esto caia dentro de bits_anchura, que acusaba de
    # truncamiento a una herramienta que no declaro anchura ninguna, y el OK
    # no ganado de CP_DMA.ENGINE no aparecia en ninguna parte.
    ("layout.bits_anchura_no_declarada", "CONOCIDA",
     "campos que se declaran con [N]: la posicion es correcta y la anchura no "
     "la declara nadie"),
    ("layout.bits_dword", "CONOCIDA",
     "campos que la herramienta coloca en un payload distinto al de KFD"),
    ("layout.bits_contradicciones", "VACIA",
     "campos con dos descripciones en disputa y sin rango contrastable: deben ser 0"),
    # --- layoutcross: COBERTURA.  La unica medida que puede ver una AUSENCIA
    # Las tres anteriores solo hablan de lo que la herramienta declara. Si
    # falta un campo, no hay nada que comparar y no sale. Esta mide lo que el
    # kernel ESCRIBE y no esta declarado.
    # El 4º oraculo de layoutcross. No compara fuentes: comprueba la tabla de
    # opcodes de la herramienta contra la estructura de la cabecera PACK3. Por
    # eso va con su propio prefijo y no mezclado con `layout.bits_*`.
    ("opcode.entradas", "ESTABLE",
     "entradas que la tabla de opcodes de la herramienta declara"),
    ("opcode.fuera_de_rango", "CONOCIDA",
     "entradas que NO pueden ser opcode: pasan de los bits 0-9, o sea que son "
     "constantes de ventana de direccionamiento relativo, no paquetes"),
    ("layout.cob_no_declarados", "CONOCIDA",
     "campos que el driver de GFX8 escribe y pm4_codec no declara"),
    ("layout.cob_alcance", "ESTABLE",
     "fichero de emision que la tabla de cobertura juzga"),
    # --- ibref: el IB de referencia pasa de ARTEFACTO a PUERTA ---------------
    # El IB sintetizado es el unico dato del proyecto que puede arbitrar una
    # contradiccion entre dos descripciones (hallazgo 1094). Si un dword cambia,
    # o el generador deja de resolverlo, hay que enterarse: un IB de referencia
    # que se mueve solo no es una referencia.
    ("ibref.kiq_dwords", "ESTABLE",
     "dwords que sintetiza kiq_kcq_enable, como dword=valor en hexadecimal"),
    ("ibref.kiq_incompletos", "VACIA",
     "dwords que el generador NO resuelve: debe ser 0"),
    ("ibref.unmap_dwords", "ESTABLE",
     "dwords que sintetiza kcq_disable, incluido el CONTROL de UNMAP_QUEUES"),
)


# --------------------------------------------------------------------------
# 1. EJECUCION DE LOS INSTRUMENTOS
# --------------------------------------------------------------------------

_TABLAS_INIT = ("vgpr_init_regs", "sgpr1_init_regs", "sgpr2_init_regs")


def _tablas_en_ventana():
    """Registros que NO caben en ninguna ventana, y tablas sin ventana unica.

    Dos comprobaciones, y son distintas:

      1. `FUERA_DE_TODAS` con las CUATRO ventanas a la vez. Un registro fuera de
         la ventana correcta pero dentro de otra no es un defecto: es el
         mecanismo de identificacion funcionando. Solo es defecto cuando no
         cabe en NINGUNA.

      2. La ventana debe ser UNICA. Si una tabla cabe en dos ventanas, la base
         no esta determinada y la decodificacion seria ambigua.

    La primera version de esta medida contaba `fuera` por cada ventana
    individual, y salia con 9 entradas: los 17 registros de cada una de las
    tres tablas "fuera" de cada ventana que NO era la suya. Eso no es un
    defecto, es la discriminacion haciendo su trabajo, y una medida que
    dispara con cada acierto es una medida que obliga a mirar y no enseña nada.
    """
    fuera = []
    for nombre in _TABLAS_INIT:
        r = ejecutar("tools/mmio.py",
                     argv_extra=["--tabla", nombre, "--json"])
        if r[1]:
            fuera.append("%s:NO_SE_MIDE" % nombre)
            continue
        for f in r[0].get("filas") or []:
            if f["veredicto"] in ("FUERA_DE_TODAS", "NO_RESUELTO"):
                fuera.append("%s:%s=%s" % (nombre, f["registro"],
                                           f["veredicto"]))
        rq = ejecutar("tools/mmio.py",
                      argv_extra=["--tabla", nombre, "--cual", "--json"])
        if rq[1]:
            fuera.append("%s:cual:NO_SE_MIDE" % nombre)
            continue
        ok = [v for v in (rq[0].get("cual") or []) if v["coincide"]]
        if len(ok) != 1:
            fuera.append("%s:ventanas_coincidentes=%d" % (nombre, len(ok)))
    return sorted(fuera)


_IB_SHADER = "gfx_v8_0_do_edc_gpr_workarounds"


_WORKING = os.path.join("RESEARCH", "working", "linux-7.1.3")
_UPSTREAM = os.path.join("RESEARCH", "kernelbuild", "linux-7.1.3")


def _sha(p):
    import hashlib
    h = hashlib.sha256()
    try:
        with open(p, "rb") as fh:
            for bloque in iter(lambda: fh.read(1 << 20), b""):
                h.update(bloque)
    except OSError:
        return None
    return h.hexdigest()


def _n_ficheros(d):
    """Cuantos ficheros hay bajo un directorio. No se confunde con `_contar`,
    que ya existia y agrupa filas por veredicto."""
    n = 0
    for _dp, _dn, fn in os.walk(d):
        n += len(fn)
    return n


def _corpus():
    """El conjunto de ficheros del kernel que el proyecto ha modificado.

    POR QUE ESTA MEDIDA Y NO OTRA. Todas las herramientas leen
    `RESEARCH/working/`. Si un fichero de ahi se aparta del upstream, todas las
    mediciones que dependan de el cambian de debajo, y ninguna puerta lo dire
    porque las medidas que dependen de el se medirian sobre el fichero cambiado: darian el
    mismo numero y no habria deriva que ver.

    Con esta medida, el conjunto de ficheros editados es un DATO declarado. Si
    pasa de cuatro a cinco, la puerta lo dice. Es la unica forma de que "el
    sujeto no ha cambiado" sea una afirmacion y no una suposicion.
    """
    mod, dif, n = [], [], 0
    for dp, _dn, fn in os.walk(os.path.join(RAIZ, _WORKING)):
        for f in fn:
            pa = os.path.join(dp, f)
            rel = os.path.relpath(pa, os.path.join(RAIZ, _WORKING))
            pb = os.path.join(RAIZ, _UPSTREAM, rel)
            if not os.path.isfile(pb):
                dif.append(rel + ":SOLO_EN_WORKING")
                continue
            n += 1
            if _sha(pa) != _sha(pb):
                dif.append(rel)
    # El segundo hecho: el resolutor de includes solo sigue los que llevan
    # comillas. Se mide sobre el patron REAL de pm4_emit, no sobre una copia:
    # si alguien lo cambia, la medida cambia con el.
    solo_comillas = "SIN_MEDIR"
    try:
        import importlib.util
        sp = os.path.join(RAIZ, "08-ARQUITECTURA", "tools", "pm4_emit.py")
        spec = importlib.util.spec_from_file_location("verif_pm4_emit", sp)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        con_ang = bool(mod.INC_RE.search('#include <linux/align.h>'))
        con_com = bool(mod.INC_RE.search('#include "align.h"'))
        solo_comillas = ("angulo=%d comillas=%d" % (con_ang, con_com))
    except Exception as exc:                          # noqa: BLE001
        solo_comillas = "NO_SE_MIDE:%s" % type(exc).__name__
    return {"corpus.ficheros_modificados": sorted(dif),
            "corpus.comparados": n,
            "corpus.trabaja_sin_include":
                "working_include=%d de upstream_include=%d angulo=%s"
                % (_n_ficheros(os.path.join(RAIZ, _WORKING, "include")),
                   _n_ficheros(os.path.join(RAIZ, _UPSTREAM, "include")),
                   solo_comillas)}


def _emit_ib_vs_declarado():
    """Los dwords de la funcion de emision, con el flag puesto y sin el.

    El driver declara `.emit_ib_size = 7` en su tabla de funciones de anillo
    (gfx_v8_0.c:6934). Ese 7 es el MAXIMO de las dos rutas: con
    AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID son 7, sin el son 4.

    Lo que se mide no es "coincide con 7" sino el PAR (sin, con). Un sintetizador
    que emita siempre el condicional daria (7, 7), que contiene un 7 y por eso
    parece conforme con la declaracion. Solo el par lo delata.
    """
    out = []
    for etiqueta, valor in (("sin_flag", "0"), ("con_flag", "16")):
        r = ejecutar("tools/ibref.py",
                     argv_extra=["--func", "gfx_v8_0_ring_emit_ib_compute",
                                 "--set", "ib.flags=" + valor, "--json"])
        if r[1]:
            out.append("%s:NO_SE_MIDE" % etiqueta)
            continue
        out.append("%s=%d" % (etiqueta, len(r[0].get("dwords") or [])))
    return out


def _enums_chip():
    """La identidad del ASIC, del enum del driver, con su comentario de control.

    El enum `amd_asic_type` numera 29 items sin `=`, de los que solo el
    primero lleva el valor explicito. El comentario `/* N */` de cada item es
    un oraculo INDEPENDIENTE de la cadena, y por eso esta medida devuelve las
    dos cosas y no solo el valor: si algun dia la cadena y el comentario
    discrepan, esta medida lo ve.
    """
    p = "RESEARCH/kernelbuild/linux-7.1.3/include/drm/amd_asic_type.h"
    try:
        txt = open(p, encoding="utf-8", errors="replace").read()
    except OSError as e:
        return ["NO_SE_MIDE:%s" % e]
    out = []
    for n in ("CHIP_TOPAZ", "CHIP_POLARIS12"):
        out.append("%s=%s" % (n, tabla_enum().get(n, "—")))
    out.append("descuadres=%d" % len(descuadres_enum()))
    out.append("fuente=%s" % os.path.basename(p))
    return out


def tabla_enum():
    import importlib.util
    sp = importlib.util.spec_from_file_location("ibr_e", "tools/ibref.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    t, _d, _s = m.enums_implicitos([os.path.join(
        m.RAIZ, "RESEARCH", "kernelbuild", "linux-7.1.3", "include", "drm",
        "amd_asic_type.h")])
    return t


def descuadres_enum():
    import importlib.util
    sp = importlib.util.spec_from_file_location("ibr_d", "tools/ibref.py")
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    _t, d, _s = m.enums_implicitos([os.path.join(
        m.RAIZ, "RESEARCH", "kernelbuild", "linux-7.1.3", "include", "drm",
        "amd_asic_type.h")])
    return d


def _desenrollado():
    """Las tres invariantes del desenrollado, sobre la IB de shader-init.

    Se miden juntas porque las tres son la misma capacidad mal entendida: una
    IB con mas dwords, con dwords repetidos, o con un bucle que no aparece en
    ninguna parte. Ninguna de las tres lanza excepcion.
    """
    r = ejecutar("tools/ibref.py",
                 argv_extra=["--func", _IB_SHADER, "--set", "flags=1",
                             "--json"])
    if r[1]:
        return {"_error_ibref_desenrollado": r[1]}
    ib = r[0]
    loop = [d for d in ib.get("dwords") or [] if "iteracion" in d]
    fuera = []
    dups = [k for k, v in _contar((d["linea"], d.get("iteracion"), d["expr"])
                                  for d in loop).items() if v > 1]
    return {
        "ibref.emit_ib_vs_declarado": _emit_ib_vs_declarado(),
        "ibref.enums_chip": _enums_chip(),
        "ibref.locales": sorted("%s=%s" % (k, v)
                                for k, v in sorted((ib.get("locales") or {}).items())),
        "ibref.locales_paradas": sorted(
            set(x["clave"] for x in ib.get("locales_paradas") or [])),
        "ibref.desenrollados": sorted("%s:%d" % (b["variable"], b["iteraciones"])
                                      for b in ib.get("bucles") or []),
        "ibref.dwords_duplicados": sorted("%s:%s" % (a, e) for a, _i, e in dups),
        "ibref.bucles_no_desenrollados": sorted(
            "L%d" % x["linea"] for x in ib.get("bucles_no_desenrollados") or []),
        "_ibref_dwords_total": len(ib.get("dwords") or []),
    }


def _contar(it):
    out = {}
    for k in it:
        out[k] = out.get(k, 0) + 1
    return out


def _ventanas_de(salida_mmio):
    """Las ventanas del json de mmio. La ventana se llama `ventanas` y tambien
    es un numero, asi que se lee del lado del mapa y no por nombre a secas."""
    d = salida_mmio.get("ventanas")
    if not isinstance(d, dict):
        return []
    # La lista se devuelve como lista. Antes se devolvia el mapa entero y el
    # `for v in ...` iteraba sobre las CLAVES, o sea sobre cadenas, y el
    # fallo era "string indices must be integers": el sintoma apuntaba a la
    # lista cuando el error estaba en el lado del mapa.
    return d.get("lista") or []


def ejecutar(tool, flag="--json", timeout=600, argv_extra=None):
    p = os.path.join(RAIZ, tool)
    if not os.path.isfile(p):
        return None, "NO_EXISTE"
    try:
        cmd = [sys.executable, p] + (argv_extra if argv_extra else [flag])
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except OSError as e:
        return None, str(e)
    if r.returncode != 0:
        return None, "RC_%d: %s" % (r.returncode, (r.stderr or "")[:120].strip())
    try:
        return json.loads(r.stdout), None
    except ValueError as e:
        return None, "JSON_INVALIDO: %s" % e


def _set(filas, gates=None, pred=None):
    out = []
    for f in filas:
        if gates and not set(gates) & set(f.get("gates") or []):
            continue
        if pred and not pred(f):
            continue
        out.append(f["herramienta"])
    return sorted(out)


def medir():
    """Todas las medidas, como valores comparables."""
    m = {}

    r, err = ejecutar("tools/riesgo.py")
    if err:
        m["_error_riesgo"] = err
    else:
        filas = r["filas"]
        m["gate.huecos"] = _set(filas, gates=["HUECO_GATE"])
        m["gate.alcanzable_sin_flag"] = _set(filas, gates=["ALCANZABLE_SIN_FLAG"])
        m["gate.peligroso_sin_flag"] = sorted(
            "%s -> %s" % (f["herramienta"], ",".join(f.get("peligroso_sin_flag") or []))
            for f in filas if "ALCANZABLE_SIN_FLAG" in (f.get("gates") or []))
        m["flags.ambiguos"] = _set(filas, gates=["FLAG_AMBIGUO"])
        m["cabeceras.contradicciones"] = sorted(
            f["herramienta"] for f in filas if f.get("contradicciones"))
        m["shell.no_clasificable"] = sorted(
            f["herramienta"] for f in filas
            if f.get("ext") == "sh" and not f.get("clasificable"))
        m["_poblacion"] = len(filas)

    p, err = ejecutar("tools/pm4ops.py")
    if err:
        m["_error_pm4ops"] = err
    else:
        m["pm4.alcance_generacion"] = list(p["alcance_de_generacion"]["alcanzable"])
        m["pm4.alcance_integro"] = bool(p["alcance_de_generacion"]["alcance_integro"])
        m["pm4.includes_quebrados"] = sorted(p["alcance_de_generacion"]["includes_quebrados"])
        m["pm4.nombres_fuera_de_alcance"] = list(p.get("nombres_fuera_del_alcance") or [])
        dec = (p.get("decodificadores") or {}).get("tools/pm4decode.c") or {}
        if dec.get("estado") in ("DERIVADA_de_headers", "FORMATO_DESCONOCIDO",
                                 "NO_EXISTE", "ILEGIBLE"):
            m["pm4.disidentes_pm4decode"] = "NO_EXTRAIBLE:%s" % dec.get("estado")
            m["pm4.inconsistentes_pm4decode"] = []
            m["pm4.dif_correctos_pm4decode"] = []
        else:
            mal = {"DISIDENTE", "CONFLICTO_NOMBRE", "TRUNCADO_NO_OPCODE",
                   "FUERA_DE_FUENTES"}
            m["pm4.disidentes_pm4decode"] = sorted(
                "%s:%s" % (f["opcode"], f["nombre"])
                for f in dec.get("filas", []) if f["veredicto"] == "DISIDENTE")
            m["pm4.inconsistentes_pm4decode"] = sorted(
                "%s:%s=%s" % (f["opcode"], f["nombre"], f["veredicto"])
                for f in dec.get("filas", []) if f["veredicto"] in mal)
            m["pm4.dif_correctos_pm4decode"] = dec.get("n_consistente", 0)

    d, err = ejecutar("tools/dwarfx.py")
    if err:
        m["_error_dwarfx"] = err
    else:
        m["dwarf.coincide"] = d.get("cuentas", {}).get("COINCIDE", 0)
        m["dwarf.linea_movida"] = sorted(
            "%s.%s" % (f["struct"], f.get("miembro", ""))
            for f in d.get("filas_detalle", []) if f["veredicto"] == "LINEA_MOVIDA")
        m["dwarf.solo_en_dwarf"] = sorted(
            "%s.%s" % (f["struct"], f.get("miembro", ""))
            for f in d.get("filas_detalle", []) if f["veredicto"] == "SOLO_EN_DWARF")
        m["dwarf.solo_en_cabecera"] = sorted(
            "%s.%s" % (f["struct"], f.get("miembro", ""))
            for f in d.get("filas_detalle", []) if f["veredicto"] == "SOLO_EN_CABECERA")
        m["dwarf.cabecera_no_leida"] = d.get("cuentas", {}).get("CABECERA_NO_LEIDA", 0)

    # layoutcross sale con rc=0 aunque encuentre discrepancias: el codigo 1 de
    # su modo legible significa "hay discrepancia", y una discrepancia
    # registrada NO es un fallo del instrumento. Si devolviera 1 aqui,
    # `ejecutar` lo leeria como error de ejecucion y esta medida pasaria a
    # NO_SE_MIDE, que es como una puerta se apaga sola cuando falla el
    # sensor: verde por averia.
    # --- mmio: la transformada que ninguna tabla de layout puede expresar --
    # El payload de SET_{CONFIG,SH,CONTEXT,UCONFIG}_REG es `MMIO - base`, no
    # un campo. Lo que se mide aqui es si la BASE cambia, porque es lo que
    # haria que toda decodificacion inversa fuera incorrecta sin que se note.
    # `ejecutar` usa `argv_extra` O `flag`, no los dos: pasar solo "--estatico"
    # hacia que se pidiera texto donde se espera JSON, y el fallo salia como
    # JSON_INVALIDO, que senala el sintoma equivocado.
    mm, err_mm = ejecutar("tools/mmio.py", argv_extra=["--estatico", "--json"])
    if err_mm:
        m["_error_mmio"] = err_mm
    else:
        m["mmio.ventanas"] = (mm.get("ventanas") or {}).get("ventanas", 0)

        m["mmio.macros"] = (mm.get("macros") or {}).get("macros", 0)
        m["mmio.valores_mm"] = (mm.get("indice") or {}).get("valores_mm", 0)
        mv = mm.get("ventanas") or {}
        m["mmio.escala"] = "%s escala=%d otra_generacion_escala=%s" % (
            mv.get("alcance", "?"), mv.get("escala", -1),
            (mv.get("otra_generacion") or {}).get("escala", -1))
        m["mmio.tablas_en_ventana"] = _tablas_en_ventana()
        m.update(_desenrollado())
        m.update(_corpus())
        m["mmio.bases"] = sorted(
            "%s=0x%02X/0x%04X" % (v["paquete"].replace("PACKET3_", ""),
                                  v["opcode"], v["base"])
            for v in _ventanas_de(mm))
    lc, err = ejecutar("tools/layoutcross.py")
    if err:
        m["_error_layoutcross"] = err
    else:
        m["layout.declarantes"] = sorted(lc.get("declarantes") or [])
        m["layout.declaraciones"] = lc.get("cuentas", {}).get("declaraciones", 0)
        m["layout.discrepancias"] = sorted(
            f["paquete"] for f in lc.get("filas", [])
            if f["veredicto"] == "DISCREPA")
        m["layout.nombres_no_comparables"] = sorted(
            f["paquete"] for f in lc.get("filas", [])
            if f["veredicto"] == "NOMBRES_NO_COMPARABLES")
        m["layout.sin_oraculo"] = lc.get("cuentas", {}).get("sin_oraculo", 0)
        # Las 4 de asignacion.  `bits_contradicciones` es CONOCIDA y no VACIA
        # a proposito: son 4 de UNMAP_QUEUES que NO se pueden resolver con lo
        # que hay en el arbol (hallazgo 1077). Marcarlas como fallo seria
        # llorar por lobo; marcarlas como vacias seria mentir sobre lo que se
        # sabe.
        m["layout.bits_afirmadas"] = lc.get("cuentas", {}).get(
            "afirmaciones_de_bits", 0)
        m["layout.bits_ok"] = lc.get("cuentas_bits", {}).get("OK", 0)
        m["layout.bits_inventados"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "CAMPO_INVENTADO")
        m["layout.bits_posicion"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "DISCREPA_POSICION")
        m["layout.bits_anchura"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "DISCREPA_ANCHURA")
        m["layout.bits_anchura_no_declarada"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "ANCHURA_NO_DECLARADA")
        m["layout.bits_dword"] = sorted(
            "%s.dw%s.%s" % (f["paquete"], f.get("dword", "?"), f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "DISCREPA_DWORD")
        m["layout.bits_contradicciones"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_bits", [])
            if f["veredicto"] == "CONTRADICCION")
        m["opcode.entradas"] = len(lc.get("filas_opcode", []))
        m["opcode.fuera_de_rango"] = sorted(
            "%s.%s" % (f["valor"], f["nombre"])
            for f in lc.get("filas_opcode", [])
            if f["veredicto"] == "OPCODE_FUERA_DE_RANGO")
        m["layout.cob_no_declarados"] = sorted(
            "%s.%s" % (f["paquete"], f["campo"])
            for f in lc.get("filas_cob", []))
        m["layout.cob_alcance"] = lc.get("alcance_cob", "")

    # ibref: dos IB de referencia, con valores LIGADOS y declarados aqui. Son
    # datos, no codigo: si cambian, o cambio el sujeto o cambio el generador, y
    # en los dos casos alguien tiene que decidir cual de las dos cosas paso.
    #   kiq_kcq_enable  : SET_RESOURCES + MAP_QUEUES, el arranque del KIQ
    #   gfx_v8_0_kcq_disable : UNMAP_QUEUES, con el CONTROL que arbitra 1094
    IBREFS = (
        ("tools/ibref.py", "gfx_v8_0_kiq_kcq_enable",
         ["ring_queue=3", "ring_pipe=1", "ring_me=1", "ring_doorbell_index=5",
          "mqd_addr=0x1122334455667788", "wptr_addr=0x99aabbccddeeff00",
          "queue_mask=0xF"], "kiq"),
        ("tools/ibref.py", "gfx_v8_0_kcq_disable",
         ["ring_doorbell_index=7"], "unmap"),
    )
    for _tool, _fn, _sets, _prefijo in IBREFS:
        # La lista se construye SIN la ruta del ejecutable: `ejecutar` ya la
        # pone. Un `argv[2:]` sobre una lista que empezaba con la ruta se
        # comia el primer flag, y el fallo aparecia como "argumentos
        # invalidos", que es un sintoma de alcance, no de codigo.
        extra = ["--func", _fn, "--json"]
        for s in _sets:
            extra += ["--set", s]
        r, err = ejecutar(_tool, "--json", timeout=1800, argv_extra=extra)
        clave = "ibref.%s_dwords" % _prefijo
        if err:
            m.setdefault("_error_ibref", []).append("%s:%s" % (_fn, err))
            continue
        d = r.get("dwords") or []
        m[clave] = ["%d=0x%08X" % (i + 1, x["valor"]) for i, x in
                    enumerate(d) if x.get("valor") is not None]
        if _prefijo == "kiq":
            m["ibref.kiq_incompletos"] = sum(1 for x in d
                                             if x.get("valor") is None)
    return m


# --------------------------------------------------------------------------
# 2. LA LINEA BASE
# --------------------------------------------------------------------------

def ruta_base():
    return os.path.join(RAIZ, LINEA_BASE)


def leer_base():
    p = ruta_base()
    if not os.path.isfile(p):
        return None
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def escribir_base(m):
    """La unica escritura que esta herramienta hace, y va a su namespace."""
    doc = {"herramienta": "verif " + VERSION,
           "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
           "nota": "Las medidas se toman de riesgos/pm4ops/dwarfx.  DERIVA es "
                   "deriva: este fichero no juzga si un cambio es bueno.",
           "medidas": m}
    d = os.path.dirname(ruta_base())
    os.makedirs(d, exist_ok=True)
    with open(ruta_base(), "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")
    return ruta_base()


def deriva(base, ahora):
    """Diferencias clasificadas por lo que se ESPERA de cada medida."""
    out = []
    for nombre, clase, que in MEDIDAS:
        # TRES estados que no son el mismo, y que la primera version confundia en
        # dos.  MEDIDO, y lo encontraron dos vectores de este mismo fichero:
        #
        #   NO_SE_MIDE   el instrumento no la produjo.  Es un instrumento roto:
        #               NO es "la medida no cambio", que es lo que sale si se
        #               trata como igualdad entre dos ausencias.
        #   SIN_BASE     la medida existe pero la linea base no la tiene.  Es un
        #               defecto de la linea base, no una deriva del corpus: la
        #               conclusion se escribio y no se congelo.
        #   (cambio)     comparables, y difieren.
        #
        # Confundir NO_SE_MIDE con "sin cambio" es como una puerta que se apaga
        # sola cuando falla el sensor: verde por averia.
        if nombre not in ahora:
            out.append({"medida": nombre, "clase": clase, "cambio": "NO_SE_MIDE",
                        "antes": base.get(nombre, "<sin base>"),
                        "ahora": "<no medida>", "que_mide": que})
            continue
        if nombre not in base:
            out.append({"medida": nombre, "clase": clase, "cambio": "SIN_BASE",
                        "antes": "<no congelada>", "ahora": ahora[nombre],
                        "que_mide": que})
            continue
        antes = base[nombre]
        if antes == ahora[nombre]:
            continue
        if isinstance(antes, list) and isinstance(ahora[nombre], list):
            a, b = set(antes), set(ahora[nombre])
            # MEDIDO por un vector, y es un bug de los que hacen que una puerta
            # deje de servir: comparar dos listas por ORDEN reportaba como
            # deriva un simple reorden, con un diff VACIO.  Una alarma que suena
            # sin mostrar nada es ruido, y el ruido es lo que hace que la gente
            # deje de mirar la puerta.
            if a == b:
                continue
            out.append({"medida": nombre, "clase": clase, "cambio": "LISTA",
                        "aparecen": sorted(b - a), "desaparecen": sorted(a - b),
                        "que_mide": que})
        else:
            out.append({"medida": nombre, "clase": clase, "cambio": "VALOR",
                        "antes": antes, "ahora": ahora[nombre], "que_mide": que})
    return out


# --------------------------------------------------------------------------
# 3. MAIN
# --------------------------------------------------------------------------

def main(argv):
    if "--selftest" in argv or "--self-test" in argv:
        return selftest()
    if "--version" in argv:
        print(VERSION)
        return 0

    fijar = "--fijar" in argv
    solo_json = "--json" in argv

    ahora = medir()
    errores = {k: v for k, v in ahora.items() if k.startswith("_error_")}

    if fijar:
        ahora.pop("_poblacion", None)
        p = escribir_base({k: v for k, v in ahora.items()
                           if not k.startswith("_error_")})
        print("linea base escrita: %s" % p)
        if solo_json:
            print(json.dumps({"fijada": True, "ruta": p, "medidas": len(ahora)},
                             indent=2, ensure_ascii=False))
        return 0

    base = leer_base()
    if base is None:
        print("NO HAY LINEA BASE.  Se mide por primera vez y se escribe con --fijar.")
        print()
        for nombre, clase, que in MEDIDAS:
            v = ahora.get(nombre, "<no medida>")
            print("  %-34s %-10s %s" % (nombre, clase,
                                        v if not isinstance(v, list)
                                        else "%d elementos" % len(v)))
        if errores:
            print()
            print("  ERRORES DE INSTRUMENTO: %s" % errores)
        return 2

    d = deriva(base.get("medidas", {}), ahora)

    if solo_json:
        print(json.dumps({"herramienta": "verif " + VERSION,
                          "generado": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                          "errores_instrumento": errores,
                          "poblacion": ahora.get("_poblacion"),
                          "deriva": d}, indent=2, ensure_ascii=False))
        return 1 if d or errores else 0

    print("=" * 92)
    print("verif %s   deriva sobre %d medidas" % (VERSION, len(MEDIDAS)))
    print("=" * 92)
    if errores:
        print("  ERRORES DE INSTRUMENTO: %s" % errores)
        print("  Una medida que no se mide NO es una medida que no cambio.  No se")
        print("  cuenta como PASA ni como FALLA: es NOT_DETERMINED.")
        print()
    if not d:
        print("  SIN DERIVA en las %d medidas declaradas." % len(MEDIDAS))
        print()
        print("  Ojo con lo que esto NO dice: que las mediciones SIGUAN dando lo")
        print("  mismo no dice que sean correctas.  Solo dice que nadie cambio el")
        print("  sujeto.  La correccion la puso quien las escribio.")
        return 0

    por_clase = {}
    for x in d:
        por_clase.setdefault(x["clase"], []).append(x)

    print("  DERIVA EN %d de %d medidas" % (len(d), len(MEDIDAS)))
    print()
    for clase in ("VACIA", "CONOCIDA", "ESTABLE", "DRIFTABLE"):
        filas = por_clase.get(clase)
        if not filas:
            continue
        if clase == "VACIA":
            print("  !! SE ESPERABA VACIA Y NO LO ESTA.  Esto es un HALLAZGO NUEVO,")
            print("     no ruido: una medida que deberia estar vacia tiene algo.")
        elif clase == "CONOCIDA":
            print("  ~  CONOCIDA: se sabe que no esta vacia.  Solo es NOTABLE si")
            print("     CRECE o si se corrige.  Lo que ya esta escrito no se vuelve")
            print("     a anunciar en cada ejecucion.")
        elif clase == "ESTABLE":
            print("  !! SE ESPERABA ESTABLE Y NO LO ESTA.  Algo cambio sin que")
            print("     nadie lo decidiera.  Averiguar que ANTES de seguir usando")
            print("     la afirmacion.")
        else:
            print("  ~  DRIFTABLE, cambio legitimo probable.  Se informa, no se juzga.")
        print()
        for x in filas:
            print("     %-34s %s" % (x["medida"], x["que_mide"]))
            if x["cambio"] == "LISTA":
                if x["aparecen"]:
                    print("        APARECEN     (%d): %s"
                          % (len(x["aparecen"]), ", ".join(x["aparecen"][:6])
                             + (" ..." if len(x["aparecen"]) > 6 else "")))
                if x["desaparecen"]:
                    print("        DESAPARECEN  (%d): %s"
                          % (len(x["desaparecen"]), ", ".join(x["desaparecen"][:6])
                             + (" ..." if len(x["desaparecen"]) > 6 else "")))
            elif x["cambio"] == "SIN_BASE":
                # MEDIDO, y es presentacion pero importa: al volcar el valor
                # entero, una medida de 23 elementos ocupaba 23 lineas y tapaba
                # las dos derivas que de verdad importaban.  Una puerta que grita
                # mas fuerte de lo que debe es una puerta que no se lee.
                v = x["ahora"]
                print("        SIN CONGELAR.  Ahora mide: %s"
                      % ("%d elementos" % len(v) if isinstance(v, list)
                         else repr(v)))
                if isinstance(v, list) and v:
                    print("        y son: %s" % ", ".join(map(str, v[:6]))
                          + (" ..." if len(v) > 6 else ""))
            else:
                print("        antes: %r" % (x["antes"],))
                print("        ahora: %r" % (x["ahora"],))
            print()
    print("LIMITE  Deriva NO es juicio.  Esta puerta dice QUE cambio, no si esta")
    print("        bien.  Y una medida que no se puede tomar no cuenta como verde.")
    return 1


# --------------------------------------------------------------------------
# 4. SELFTEST -- hermetico
# --------------------------------------------------------------------------

def _base_completa(**cambios):
    """Base con TODAS las medidas declaradas.  MEDIDO: la primera version uso una
    base con tres medidas de las diecisiete, y los vectores que pretendian medir
    "sin cambio no hay deriva" median otra cosa: catorce medidas salian
    NO_SE_MIDE.  Un fixture incompleto prueba el fixture, no la funcion."""
    base = {nombre: [] for nombre, _c, _q in MEDIDAS}
    base["gate.huecos"] = ["tools/a.py", "tools/b.py"]
    base["pm4.alcance_generacion"] = ["vid.h"]
    base.update(cambios)
    return {"medidas": base}


BASE_EJEMPLO = _base_completa()


def selftest():
    v, fallos = [], []

    def t(nombre, ok, det):
        v.append((nombre, ok, det))
        if not ok:
            fallos.append(nombre)

    def con(**cambios):
        """Copia de la linea base con medidas sustituidas.

        MEDIDO: la primera version de estos vectores uso
        `dict(BASE, gate_huecos=[...])`, y `gate_huecos` NO es el nombre de la
        medida: la clave real es `gate.huecos`, con punto.  kwargs de dict()
        crean una clave LITERAL, asi que los vectores no estaban sustituyendo
        nada y pasaban o fallaban por otra causa.  Un fixture que no modifica lo
        que dice modificar no prueba nada."""
        m = dict(BASE_EJEMPLO["medidas"])
        for k, v in cambios.items():
            m[k.replace("__", ".")] = v
        return m

    t("SEL_1_la_version_se_declara", bool(VERSION), VERSION)

    # DER_1 una lista que cambia: aparecen y desaparecen, CON NOMBRES
    d = deriva(BASE_EJEMPLO["medidas"],
               con(gate__huecos=["tools/b.py", "tools/c.py"]))
    h = [x for x in d if x["medida"] == "gate.huecos"]
    t("DER_1_una_lista_que_cambia_dice_que_aparece_y_que_desaparece",
      len(h) == 1 and h[0]["aparecen"] == ["tools/c.py"]
      and h[0]["desaparecen"] == ["tools/a.py"], str(h[:1]))

    # DER_2 sin cambio no hay deriva
    d = deriva(BASE_EJEMPLO["medidas"], dict(BASE_EJEMPLO["medidas"]))
    t("DER_2_sin_cambio_no_hay_deriva", d == [], str(d[:2]))

    # DER_3 una medida VACIA que se llena es un HALLAZGO NUEVO.
    # Se usa una medida que SIGUE siendo VACIA: gate.alcanzable_sin_flag paso
    # a CONOCIDA cuando se vio, sobre el corpus real, que guardaba un defecto ya
    # escrito.  Con la etiqueta equivocada la puerta habria gritado HALLZGO en
    # cada ejecucion por algo que ya se sabe, y a la tercera nadie la mira.
    d = deriva(BASE_EJEMPLO["medidas"], con(shell__no_clasificable=["tools/s.sh"]))
    x = [y for y in d if y["medida"] == "shell.no_clasificable"]
    t("DER_3_una_medida_vacia_que_se_llena_es_hallazgo_nuevo",
      len(x) == 1 and x[0]["clase"] == "VACIA"
      and x[0]["aparecen"] == ["tools/s.sh"], str(x[:1]))

    # DER_3b una medida CONOCIDA que CRECE se sigue informando, con su clase
    d = deriva(BASE_EJEMPLO["medidas"],
               con(gate__alcanzable_sin_flag=["tools/x.py", "tools/y.py"]))
    x = [y for y in d if y["medida"] == "gate.alcanzable_sin_flag"]
    t("DER_3b_una_medida_conocida_que_crece_sigue_informandose",
      len(x) == 1 and x[0]["clase"] == "CONOCIDA"
      and x[0]["aparecen"] == ["tools/x.py", "tools/y.py"], str(x[:1]))

    # DER_4 una medida que NO SE MIDE no es una medida que no cambio
    ahora = dict(BASE_EJEMPLO["medidas"])
    del ahora["gate.alcanzable_sin_flag"]
    d = deriva(BASE_EJEMPLO["medidas"], ahora)
    nm = [y for y in d if y["medida"] == "gate.alcanzable_sin_flag"]
    t("DER_4_una_medida_no_medida_no_cunta_como_sin_cambio",
      len(nm) == 1 and nm[0]["cambio"] == "NO_SE_MIDE"
      and nm[0]["ahora"] == "<no medida>", str(nm[:1]))

    # DER_5 cambio de valor simple
    base = dict(BASE_EJEMPLO["medidas"])
    base["pm4.alcance_generacion"] = ["sid.h"]
    d = deriva(base, dict(BASE_EJEMPLO["medidas"]))
    # dos listas de un elemento que se sustituyen: es un cambio de LISTA con
    # nombre, que es mas util que "antes sid.h, ahora vid.h".
    t("DER_5_un_cambio_de_escalar_lo_dice_por_nombre",
      len(d) == 1 and d[0]["cambio"] == "LISTA"
      and d[0]["aparecen"] == ["vid.h"] and d[0]["desaparecen"] == ["sid.h"],
      str(d[:1]))

    # DER_6 una medida medida pero NO congelada es SIN_BASE
    base = dict(BASE_EJEMPLO["medidas"])
    del base["dwarf.coincide"]
    d = deriva(base, dict(BASE_EJEMPLO["medidas"]))
    sb = [x for x in d if x["medida"] == "dwarf.coincide"]
    t("DER_6_una_medida_no_congelada_es_SIN_BASE_y_no_deriva_del_corpus",
      len(sb) == 1 and sb[0]["cambio"] == "SIN_BASE", str(sb[:1]))

    # DER_7 el orden de una lista no es deriva
    d = deriva(BASE_EJEMPLO["medidas"],
               con(gate__huecos=["tools/b.py", "tools/a.py"]))
    t("DER_7_el_orden_de_una_lista_no_es_deriva", d == [], str(d[:1]))

    # toda medida declarada tiene clase y descripcion
    t("SEL_2_toda_medida_declarada_tiene_clase_y_que_mide",
      all(len(x) == 3 and x[1] in ("ESTABLE", "VACIA", "CONOCIDA", "DRIFTABLE")
          and x[2] for x in MEDIDAS), "%d medidas" % len(MEDIDAS))
    # los nombres usan puntos para separar eje y medida; el doble guion bajo es
    # una convencion SOLO del fixture de test y no debe colarse en los reales.
    t("SEL_3_los_nombres_de_medida_usan_punto_y_no_doble_guion_bajo",
      not any("__" in n for n, _c, _q in MEDIDAS),
      str([n for n, _c, _q in MEDIDAS if "__" in n]))

    # la linea base se escribe y se relee sin perder nada
    with tempfile.TemporaryDirectory(prefix="verif-st") as d:
        global LINEA_BASE
        viejo = LINEA_BASE
        LINEA_BASE = os.path.join(d, "sub", "base.json")
        try:
            pth = escribir_base({"gate.huecos": ["a"], "x": 3})
            leido = leer_base()
            t("SEL_4_la_linea_base_se_escribe_y_se_relee",
              os.path.isfile(pth) and leido["medidas"]["gate.huecos"] == ["a"]
              and leido["medidas"]["x"] == 3, str(leido.get("medidas")))
            os.remove(pth)
            t("SEL_5_sin_linea_base_leer_devuelve_None_y_no_un_vacio",
              leer_base() is None, "")
        finally:
            LINEA_BASE = viejo

    print("  selftest de verif %s" % VERSION)
    print("  %d vectores, %d fallos" % (len(v), len(fallos)))
    for nombre, ok, det in v:
        print("    %-4s %-58s %s" % ("OK" if ok else "FALLA", nombre, det[:36]))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

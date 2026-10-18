#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# CONTRACT: name=layoutcross
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO, y por que WRITES_FILES=no con `open(p, "w")` en la linea 1391.
#
# Las escrituras de este fichero van a `tempfile.mkdtemp(prefix="layoutcross-")`
# y a `mkdtemp(prefix="layoutcross-generico-")`.  Clase TEMPORAL de
# `contract_exec.py`.  Declararlas WRITES_FILES=yes seria MENTIR, y el propio
# `contract_exec` lo dice: "declararlas WRITES_FILES=yes seria MENTIR".
#
# TOUCHES_INTEGRATED=no: lee layouts y oraculos del corpus, escribe solo en
# temporales.  No abre sysfs ni DRM.  Ver 1487 sobre por que el campo se declara
# aunque el validador no lo conozca.
"""layoutcross.py -- contraste cruzado de layouts PM4 declarados por las
herramientas del proyecto contra los DOS oraculos del corpus.

PROBLEMA QUE RESUELVE, MEDIDO
-----------------------------
`pm4_codec.check_layouts()` recorre sus 7 layouts declarados y busca una
emision `PACKET3(op, F)` en `gfx_v8_0.c`. Medido: verifica 3 de 7.
Los otros 4 no aparecen ni una vez en el fichero de la generacion objetivo, y
la comprobacion hace `continue` sin decir nada. Para el que lo lee, un layout
verificado y un layout nunca examinado producen el MISMO silencio.

`pm4_layout_audit.py` tiene el oraculo complementario (los comentarios
numerados `/* 1. header ... N. ... */` de las cabeceras del kernel) pero solo
lo contrasta contra el propio kernel: kernel contra kernel. Ninguna
herramienta contrasta el lado de las herramientas.

Este instrumento cierra ese hueco: herramienta contra cabecera, herramienta
contra emision, y sobre todo DISTINGUE LAS TRES COSAS

    OK            contrastado y de acuerdo
    DISCREPA      contrastado y en desacuerdo, con el campo responsable
    SIN_ORACULO   declarado y nunca contrastado por ningun lado

La tercera es la que no existia. Un absent no es un OK.

UNIDADES -- POR QUE ESTO ESTA EN EL CODIGO Y NO EN UN COMENTARIO
--------------------------------------------------------------
En esta sesion el mismo error se cometio tres veces al comparar layouts:
contar el payload contra el total, o al reves. El numero siempre era
"casi" y siempre daba un falso positivo. La causa no fue la aritmetica: fue
que las dos cantidades se llamaban "dwords" y nadie decia cual era cual.

Por eso aqui ninguna cuenta viaja sin unidad:

    TOTAL        cabecera + payload   (lo que numeran los comentarios)
    SOLO_PAYLOAD solo payload          (lo que emite detras del control)

`documented_layouts()` de pm4_layout_audit.py devuelve SOLO_PAYLOAD aunque su
docstring hable de "el total de dwords"; ese fue el tropiezo. Este fichero no
hereda esa ambiguedad: lo pide y lo etiqueta explicitamente.

ORACULOS (ambos dentro del corpus, ninguno externo)
--------------------------------------------------
  H  cabecera   : comentario numerado `/* 1. header ... N. ... */`
  E  emision    : `PACKET3(OPCODE, F)` presente en un .c del corpus

  E da payload = F + 1.  Verificado en el propio corpus y no de memoria:
  MAP_QUEUES F=5 emite 6 payload, RELEASE_MEM F=5 emite 6, EVENT_WRITE_EOP
  F=4 emite 5.  pm4_layout_audit.py ya codifica la misma regla como
  `F == payload - 1`.

SALIDA
------
Codigos de salida:
  0  toda declaracion tiene oraculo y coincide
  1  hay al menos una DISCREPA
  2  ninguna declaracion tiene oraculo: el contraste no produjo evidencia

`--selftest` ejecuta vectores hermeticos sobre fixtures en un directorio
temporal. No lee el corpus y no depende de la red.
"""

import argparse
import glob
import importlib.util
import json
import os
import re
import sys
import tempfile

VERSION = "1.0"

RAIZ = os.path.dirname(os.path.abspath(os.path.dirname(__file__)))

# Cabeceras y .c del corpus, los mismos que usa pm4_layout_audit.py
CORPUS = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                       "drivers", "gpu", "drm", "amd", "amdgpu")

# Directorios donde puede vivir una herramienta que declare layouts.
DIRS_HERRAMIENTA = [
    os.path.join(RAIZ, "tools"),
    os.path.join(RAIZ, "08-ARQUITECTURA", "tools"),
    os.path.join(RAIZ, "04-IMPLEMENTACION", "rx550-driver", "tools"),
    os.path.join(RAIZ, "04-IMPLEMENTACION", "tools"),
    os.path.join(RAIZ, "09-POWER-CLOCKS", "tools"),
    os.path.join(RAIZ, "01-AUDITORIA", "tools"),
    os.path.join(RAIZ, "revkit"),
]

# Nombres que una herramienta usa para exponer sus layouts declarados.
# Se busca un dict -> list-of-str, con claves PACKET3_*.
ATRIBUTOS = ("DOC_LAYOUTS", "LAYOUTS", "LAYOUT_PM4", "DOC_LAYOUT", "LAYOUT")

UNIDAD_TOTAL = "TOTAL(cabecera+payload)"
UNIDAD_PAYLOAD = "SOLO_PAYLOAD"

# Etiquetas que el kernel usa cuando NO documenta el subcampo. Cuando el
# lado del kernel es todo esto, el nombre no se puede comparar con el de una
# herramienta que si lo desglosa, y la ausencia de coincidencia NO es un
# defecto: es falta de granularidad en la fuente.
GENERICAS = {"CONTROL", "CONTROL2", "CONTROL3", "CONTROL4", "CONTROL5",
             "CONTROL6", "RESERVED", "HEADER", "DATA", "NOP", "DWORD",
             "DW", "DW0", "DW1", "DW2", "DWORD0", "DWORD1", "DWORD2"}

# Sustituciones de nombre legitimas entre el kernel y una herramienta.
# Solo se acepta el alias si las dos cadenas coinciden al quitar el
# subconjunto comun; no es una lista de sinonimos abiertos.
ALIAS = {"DOORBELL_OFFSET": "DOORBELL_OFFSET0"}


# --------------------------------------------------------------------- util
def _tokens(texto):
    """Identificadores de campo de una entrada de layout.

    Se exige GUION BAJO, porque es lo que distingue un nombre de campo de una
    etiqueta (`CONTROL2`, `DATA`, `A`) y de un numero de bitfield. Sin ese
    requisito, `WPTR_ADDR_LO` y `MQD_ADDR_LO` colapsarian en nada y el
    contraste por contenido no tendria con que trabajar.

    No se distingue mayuscula de minuscula a proposito: el kernel escribe
    `WPTR_ADDR_LO` y pm4_codec escribe `doorbell_offset` para el mismo campo.
    Exigir un caso concreto habria declarado discrepante lo que es el mismo
    campo. `DATA` entra aparte porque el kernel lo escribe suelto
    (`SRC_ADDR_LO or DATA`) y el patron de guion bajo no lo alcanza.
    """
    txt = re.sub(r"\[[^\]]*\]", " ", texto)
    out = set()
    for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)\b", txt):
        out.add(m.group(1).upper())
    for m in re.finditer(r"\b(DATA)\b", txt):
        out.add(m.group(1))
    return out


def _nombres(texto):
    """Identificadores para PREGUNTAR SI UN NOMBRE EXISTE.

    `_tokens` exige guion bajo y por eso es invisible para `COMMAND`,
    `CONTROL` o `ACTION`, que son nombres de campo legitimos del kernel. Para
    comparar contenido interesa la precision; para preguntar por pertenencia
    interesa la cobertura. MEDIDO: con una sola funcion, el kernel parecia no
    nombrar `COMMAND` cuando lo nombra en `6. COMMAND [30:21]`.

    Se excluyen los indices de bitfield y los tokens que son solo etiqueta.
    """
    txt = re.sub(r"\[[^\]]*\]", " ", texto)
    return {m.group(1).upper()
            for m in re.finditer(r"\b([A-Za-z][A-Za-z0-9_]*)\b", txt)}


def _desglosa(campos):
    """El comentario del kernel DESGLOSA el dword, o solo nombra ranuras?

    El criterio es la anchura parcial, no el nombre. `MAP_QUEUES` documenta
    `MQD_ADDR_LO [31:0]` y `CONTROL`: son ranuras de dword entero, no campos,
    y sus subcampos viven en los macros. `SET_RESOURCES` documenta
    `OAC_MASK [15:0]` y `GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]`: eso si es
    un desglose.

    MEDIDO: un test por nombre decia que QUERY_STATUS desglosaba, porque
    `ADDR_LO` tiene guion bajo. Su anchura es [31:0] y no desglosa nada.
    """
    for c in campos:
        for hi, lo in re.findall(r"\[\s*(\d+)\s*:\s*(\d+)\s*\]", c):
            if (int(hi), int(lo)) != (31, 0):
                return True
    return False


def cargar_modulo(ruta):
    """Importa un .py por ruta sin tocar sys.path del proceso."""
    nombre = "lc_" + os.path.splitext(os.path.basename(ruta))[0]
    spec = importlib.util.spec_from_file_location(nombre, ruta)
    if spec is None or spec.loader is None:
        raise ImportError("no importable: %s" % ruta)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------- oraculo H: la cabecera
RE_NUM = re.compile(r"^\s*\*\s*(\d+)\.\s?(.*)$")
RE_OPCODE = re.compile(r"define\s+(PACKET3_[A-Z0-9_]+)\s+0x")
RE_INICIO = re.compile(r"^\s*/\*\s*1\.\s*header\b", re.I)

# Macro de campo:  PACKET3_<OP>_<CAMPO>(x)  ((x) << N)
# `<<` son DOS caracteres. Con `([<>])` --un solo caracter-- la expresion no
# casa nunca y el oraculo entero devuelve vacio, que es como se fabrican
# "0 discrepancias" de nada. MEDIDO, no hipotetizado.
RE_MACRO = re.compile(
    r"define\s+(PACKET3_[A-Z0-9_]+)\(x\)\s+\(\(x\)\s*(<<|>>)\s*(\d+)\s*\)")

# Lo que una herramienta afirma sobre los bits de un campo.
RE_BITS = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]")
RE_BIT1 = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*\]")


def _entrada_numerada(lineas, i):
    """A partir de la linea `/* 1. header` agrupa los campos numerados.

    El kernel envuelve los campos largos en lineas de continuacion:

        * 3. CP_SYNC [31] | SRC_SEL [30:29] | ...
        *    SRC_ADDR_HI [7:0]

    Sin agrupar, la entrada 3 perderia `SRC_ADDR_HI` y cualquier
    comparacion de campos daria un falso negativo. Devuelve ademas el opcode
    buscado hacia atras, porque el `define` va justo antes del comentario.
    """
    opcode = None
    # El limite inferior es -1 y no 0 a proposito. Con max(0, i-n) el rango
    # queda VACIO cuando el comentario esta en las primeras lineas del
    # fichero, y el `define` de la linea anterior nunca se mira: el opcode
    # salia None y el header entero se perdia en silencio.
    for j in range(i - 1, max(-1, i - 10), -1):
        m = RE_OPCODE.search(lineas[j])
        if m:
            opcode = m.group(1)
            break
    campos, k, actual = [], i, None
    while k < len(lineas):
        l = lineas[k]
        if "*/" in l:
            break
        m = RE_NUM.match(l)
        if m:
            if actual is not None:
                campos.append(actual)
            actual = [int(m.group(1)), m.group(2)]
        elif actual is not None and l.strip():
            # Continuacion del campo anterior. El kernel las escribe ASI:
            #     *    SRC_ADDR_HI [7:0]
            # Empiezan por `*` como las numeradas, asi que no se pueden
            # filtrar por eso; se distinguen en que no abren numero. Sin
            # esta rama la entrada 3 perderia su segundo medio y el
            # contraste de campos daria un falso negativo.
            actual[1] += " " + l.strip()
        k += 1
    if actual is not None:
        campos.append(actual)
    # la entrada 1 es la cabecera; el payload son las siguientes
    payload = [t for n, t in campos if n != 1]
    return opcode, payload


def oraculo_cabecera(directorio):
    """{opcode: {total, payload, campos}} desde los comentarios numerados.

    `total` cuenta la cabecera; `payload` no. Se devuelven las dos unidades
    para que ningun consumidor pueda confundirlas.
    """
    out = {}
    for ruta in sorted(glob.glob(os.path.join(directorio, "*.h"))):
        try:
            with open(ruta, errors="replace") as fh:
                lineas = fh.read().split("\n")
        except OSError:
            continue
        for i, l in enumerate(lineas):
            if not RE_INICIO.match(l):
                continue
            opcode, campos = _entrada_numerada(lineas, i)
            if not opcode or not campos:
                continue
            nums = [1 + len(campos)]  # cabecera + payload
            total = nums[0]
            reg = out.setdefault(opcode, {"total": total, "payload": len(campos),
                                          "campos": campos, "donde": []})
            reg["donde"].append("%s:%d" % (os.path.basename(ruta), i + 1))
    return out


# --------------------------------------------------- oraculo E: la emision
RE_PACKET3 = re.compile(r"PACKET3\(\s*(PACKET3_[A-Z0-9_]+)\s*,\s*(\d+)\s*\)")


# Cabeceras que declaran el mismo paquete para generaciones distintas. Se
# listan a mano porque son las unicas que el corpus ofrece, pero lo que se
# GUARDA es de cual viene cada valor, nunca el ultimo que se leyo.
CABECERAS_PM4 = ("vid.h", "soc15d.h", "gfx_v12_1_pkt.h", "nvd.h", "sid.h")

# CORRECCION 2026-10-04 (hallazgo 1105). Antes decia:
#   "el kernel da el desplazamiento, no la anchura"
# Eso era CIERTO sobre vid.h y FALSO sobre el arbol: amdkfd/kfd_pm4_headers_vi.h
# declara los mismos paquetes con bitfields CON anchura, y esta en cuatro copias
# (hallazgo 1096). Decirlo aqui era dejar una afirmacion falsa en el codigo,
# que es lo que este instrumento existe para evitar.
#
# Ahora la verdad es mas corta y mas util:
#   - hay ANCHURA disponible, pero no para todos los paquetes
#   - cuando no la hay, la palabra "kernel" es ambigua: vid.h no la da, KFD si
ANCHURA_NO_DETERMINABLE = ("anchura no contrastable: vid.h da el desplazamiento "
                           "y KFD no modela este campo")


def oraculo_bits(directorio, ops, cabeceras=None):
    """{opcode: {campo: {cabecera: LSB}}} desde los macros de campo.

    Se guarda el valor POR CABECERA y no se colapsa. Motivo, medido: los
    macros de `MAP_QUEUES` cambian de posicion entre GFX8 y GFX9+
    (`queue` = <<26 en vid.h y <<13 en soc15d.h). Colapsarlos con "la ultima
    gana" convierte dos generaciones distintas en un valor unico y
    creible, que es la forma mas dangerous de producir un falso positivo.

    `>>` no se guarda: da el MSB, no el LSB, y no es comparable con un `[hi:lo]`.
    """
    out = {}
    for h in (cabeceras or CABECERAS_PM4):
        ruta = os.path.join(directorio, h)
        if not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        for m in RE_MACRO.finditer(texto):
            full, signo, n = m.group(1), m.group(2), int(m.group(3))
            if signo != "<<":
                continue
            for k in ops:
                if full.startswith(k + "_"):
                    out.setdefault(k, {}).setdefault(
                        full[len(k) + 1:].lower(), {})[h] = n
                    break
    return out


class Rango(tuple):
    """(hi, lo) con un atributo: la herramienta declaro la ANCHURA o solo el LSB.

    MEDIDO en el corpus: `pm4_codec` escribe `[4]` para `queue_sel` y `[2:0]`
    para `QUEUE_SEL` del otro paquete. La lectura `[N:N]` (que es lo que hacia
    este codigo) es INCORRECTA en 13 de 13 casos contrastables: KFD da un rango
    mas ancho las 6 veces que hay oraculo. O sea `[N]` significa "empieza aqui",
    no "un bit".

    La consecuencia era grave y hacia dos cosas malas a la vez:

      1. `CP_DMA.ENGINE[27]` salia **OK** con un oraculo que no declara
         anchura: un OK no ganado, porque lo declarado esta incompleto.
      2. `MAP_QUEUES.queue_sel[4]` salia `DISCREPA_ANCHURA`, que acusa de
         truncamiento a una herramienta que no declaro anchura ninguna. Confunde
         "declare una anchura equivocada" con "no declare anchura", y solo la
         primera es un defecto.

    Se conserva el desempaquetado de dos elementos para no tocar las demas
    comparaciones.
    """

    def __new__(cls, hi, lo, ancho_declarado=True):
        o = super().__new__(cls, (hi, lo))
        o.ancho_declarado = ancho_declarado
        return o


def extraer_bits(entradas):
    """{dword 1-based: {campo: (hi, lo)}} de lo que la herramienta afirma.

    POR QUE POR DWORD Y NO APLANADO: la entrada i de la lista describe el
    payload i del paquete, y el campo declarado en una posicion depende de esa
    posicion. Aplanar pierde el indice, y con el indice se pierde mas de lo que
    parece: un campo con el MISMO nombre en dos dwords es legitimo
    (`doorbell_offset0..3` de UNMAP_QUEUES) y aplanado se leeria como una
    contradiccion que no existe.


    CONTRATO, escrito porque un fixture lo puso de manifiesto por no estar:
    `setdefault` significa que si la herramienta declara el MISMO campo dos
    veces con rangos distintos, solo se ve la PRIMERA, en silencio. Es una
    decision defendible --una entrada por campo-- pero no declarada, y un
    llamante que declarase el campo dos veces creeria estar declarando dos.
    Quien quiera contradecirse explicitamente tiene que decirlo en otro sitio.
    """
    out = {}
    for i, e in enumerate(entradas, 1):
        d = out.setdefault(i, {})
        for m in RE_BITS.finditer(e):
            d.setdefault(m.group(1), Rango(int(m.group(2)), int(m.group(3)), True))
        for m in RE_BIT1.finditer(e):
            d.setdefault(m.group(1), Rango(int(m.group(2)), int(m.group(2)), False))
    return out


def bits_del_comentario(campos):
    """{campo: (hi, lo)} de los rangos que el COMENTARIO del kernel declara.

    Es un oraculo mas fuerte que el macro, y por eso se guarda aparte: cuando
    el comentario dice `GDS_HEAP_SIZE [16:11]`, hay una afirmacion de bits que
    no depende de que el macro este bien escrito. El macro solo da el
    desplazamiento y, si el kernel copio el bloque de otro paquete, el
    desplazamiento tambien puede estar equivocado.
    """
    out = {}
    for c in campos:
        # El guion bajo va dentro de la clase. Con [A-Za-z0-9]* el patron
        # cortaba `GDS_HEAP_SIZE` en `GDS_HEAP` y no casaba el rango: la
        # funcion devolvia {} y todo el contraste de rangos se caia en
        # silencio, con lo que 0 discrepancias significaba "no mire".
        for m in re.finditer(
                r"\b([A-Za-z][A-Za-z0-9_]*)\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]", c):
            out[m.group(1).upper()] = (int(m.group(2)), int(m.group(3)))
    return out


def contrastar_bits(declaraciones, cab, bits, kfd=None):
    """Contraste de ASIGNACION: que dword es cual y que bits ocupa.

    Separado del contraste de conteo a proposito. Son preguntas distintas, con
    oraculos distintos, y mezclarlas obliga a elegir un veredicto unico para
    un paquete que puede tener la cuenta bien y el contenido mal: ese caso es
    `SET_RESOURCES` (hallazgo 1073) y un veredicto unico lo declararia bueno.

    Y hay mas de un grado de contradiccion, que la primera version no tenia y
    que fue lo que la volvio inutil:

      DISCREPA    el comentario del kernel declara el rango de ESE campo y
                  difiere. Dos afirmaciones explicitas que no pueden coexistir.
      CONTRADICCION  el macro dice una cosa y la herramienta otra, pero el
                  comentario no declara el rango. NO se sabe quien tiene
                  razon: el macro puede estar copiado del bloque de otro
                  paquete, que es un cuasiupstream conocido.

    La primera version de este instruments emitia CONTRADICCION como DISCREPA y
    producia 6 defectos que no podia defender. Un instrumento que fabrica
    cargos sin pruebas es peor que ninguno.
    """
    paquetes = set()
    for tabla in declaraciones:
        paquetes |= set(tabla)
    filas = []
    for op in sorted(paquetes):
        declarada = None
        for tabla in declaraciones:
            if op in tabla:
                declarada = tabla[op]
                break
        if declarada is None:
            continue
        h = cab.get(op)
        nombres, rangos, solo_genericas = set(), {}, True
        if h:
            for c in h["campos"]:
                nombres |= _nombres(c)
            rangos = bits_del_comentario(h["campos"])
            solo_genericas = not _desglosa(h["campos"])

        _claims = extraer_bits(declarada)
        for _dw in sorted(_claims):
          for campo, _rg in sorted(_claims[_dw].items()):
            hi, lo = _rg
            ancho_decl = getattr(_rg, "ancho_declarado", True)
            nom = campo.upper()
            por_cab = (bits.get(op) or {}).get(campo.lower())
            lsb_unico = (list(set(por_cab.values()))[0]
                         if por_cab and len(set(por_cab.values())) == 1 else None)

            # PRECEDENCIA del oraculo, y el orden importa:
            #   1 KFD              declara la ANCHURA (unico que la declara)
            #   2 comentario       declara un rango parcial
            #   3 macro            declara solo el desplazamiento
            # Se toma el mas fuerte disponible. Antes solo existian 2 y 3, y por
            # eso la comparacion era de LSB: era el unico dato que habia.
            # KFD escribe los campos en minuscula y la herramienta los escribe como
            # quiera; la busqueda se normaliza a mayuscula. Sin esto la busqueda
            # falla siempre en silencio y el oraculo mas fuerte queda sin
            # usarse, que es lo peor que puede pasar con un oraculo: parecer
            # activo y no estarlo.
            _kdtodo = (kfd or {}).get(op) or {}
            _kd = _kdtodo.get(_dw) or {}
            rango_kfd = _kd.get(nom)
            # El campo existe en KFD pero en OTRO dword. El contraste de
            # conteo ya sabia que algo no cuadraba (1061: una entrada de mas),
            # pero no decia QUE. Aqui sale sin ambiguedad.
            _otro = [d for d, cs in _kdtodo.items()
                     if d != _dw and nom in cs and rango_kfd is None]
            rango_com = rangos.get(nom)
            if por_cab and len(set(por_cab.values())) > 1:
                ver = "POSICION_DEPENIENTE_GENERACION"
                diag = ("LSB distinto por generacion: %s. No hay valor unico que "
                        "contrastar; la herramienta declara [%d:%d]"
                        % ("  ".join("%s=<<%d" % (c[:-2], v)
                                     for c, v in sorted(por_cab.items())), hi, lo))
                k = ""
            elif rango_kfd is not None:
                k = "kfd[%d:%d]" % rango_kfd
                # POSICION y ANCHURA son dos defectos distintos y de gravedad
                # distinta, y meterlos en un mismo veredicto infla el recuento
                # con cosas que no son bugs:
                #   lsb distinto   -> el campo esta en OTROS bits -> bug
                #   lsb igual, mas ancho -> el campo esta ahi pero truncado ->
                #                      documentacion, y ademas el valor se lee
                #                      bien mientras que quepa
                # Medido: con un solo veredicto, 4 de los 10 DISCREPA de
                # MAP_QUEUES eran solo de anchura.
                if rango_kfd[1] != lo:
                    ver = "DISCREPA_POSICION"
                    diag = ("KFD declara %s[%d:%d] y la herramienta [%d:%d]: el "
                            "campo empieza en un bit DISTINTO (LSB %d frente a "
                            "%d). Es un fallo funcional"
                            % (nom, rango_kfd[0], rango_kfd[1], hi, lo,
                               rango_kfd[1], lo))
                elif not ancho_decl:
                    ver = "ANCHURA_NO_DECLARADA"
                    diag = ("el LSB coincide (%d) pero la herramienta escribe "
                            "[%d], que no dice de quantos bits es el campo; KFD "
                            "da [%d:%d]. La POSICION es correcta y la anchura "
                            "esta sin declarar: no es un fallo funcional, es "
                            "una declaracion incompleta"
                            % (lo, lo, rango_kfd[0], rango_kfd[1]))
                elif rango_kfd != (hi, lo):
                    ver = "DISCREPA_ANCHURA"
                    diag = ("el LSB coincide (%d) pero KFD da el rango completo "
                            "[%d:%d] y la herramienta declara [%d:%d]. El campo "
                            "esta en su sitio y se TRUNCA: se lee bien mientras "
                            "que quepa. No es un fallo funcional"
                            % (lo, rango_kfd[0], rango_kfd[1], hi, lo))
                else:
                    ver = "OK"
                    diag = ("rango completo [%d:%d] corroborado por KFD, que si "
                            "declara la anchura" % (hi, lo))
            elif nom in rangos:
                k = "com[%d:%d]" % rangos[nom]
                if rangos[nom] != (hi, lo):
                    posi = rangos[nom][1] != lo
                    ver = "DISCREPA_POSICION" if posi else "DISCREPA_ANCHURA"
                    diag = (("el comentario del kernel declara %s[%d:%d] y la "
                             "herramienta declara [%d:%d]: el campo empieza en "
                             "un bit DISTINTO (LSB %d frente a %d). Es un fallo "
                             "funcional"
                             % (nom, rangos[nom][0], rangos[nom][1], hi, lo,
                                rangos[nom][1], lo)) if posi else
                            ("el LSB coincide (%d) pero el comentario da [%d:%d] "
                             "y la herramienta declara [%d:%d]. El campo esta "
                             "en su sitio y se TRUNCA: no es un fallo funcional"
                             % (lo, rangos[nom][0], rangos[nom][1], hi, lo)))
                else:
                    ver = "OK"
                    diag = "corroborado por el comentario numerado del kernel"
            elif _otro:
                # ANTES que la rama del LSB, y el orden no es cosmetico:
                # "el campo esta en otro payload" EXplica "el LSB no
                # coincide", y es mas informante. Al revés, los dos campos de
                # SET_RESOURCES salian como CONTRADICCION cuando lo que
                # pasaba es que estan un payload mas abajo.
                ver = "DISCREPA_DWORD"
                diag = ("KFD coloca %s en el payload %d y la herramienta lo "
                        "declara en el payload %d: el campo esta en el dword "
                        "equivocado, no en los bits equivocados"
                        % (nom, _otro[0], _dw))
                k = "kfd@dw%d" % _otro[0]
            elif lsb_unico is not None and lo != lsb_unico:
                ver = "CONTRADICCION"
                diag = ("el macro dice %s<<%d (las %d cabeceras coinciden) y la "
                        "herramienta dice [%d:%d]. El comentario no declara el "
                        "rango: no se sabe cual de los dos esta mal"
                        % (nom, lsb_unico, len(por_cab), hi, lo))
                k = "<<%d" % lsb_unico
            elif por_cab is None:
                if solo_genericas:
                    ver = "NOMBRES_NO_COMPARABLES"
                    diag = ("el kernel no desglosa este dword, asi que el "
                            "nombre de la herramienta no es contrastable")
                elif nom not in nombres:
                    ver = "CAMPO_INVENTADO"
                    diag = ("la herramienta afirma %s y ninguna cabecera lo "
                            "nombra ni lo posiciona" % nom)
                else:
                    ver = "SIN_ORACULO_BITS"
                    diag = "el kernel nombra el campo pero no lo posiciona"
                k = ""
            elif not ancho_decl:
                # El LSB coincide con el macro, pero la herramienta NO declara
                # de quantos bits es el campo. Saying OK here was an unearned
                # OK: the declaration is incomplete, and an incomplete
                # declaration that lands on the right bits is not corroborated.
                # El oraculo (el macro) tampoco puede dar la anchura, asi que
                # esto NO es un defecto contrastado: es una laguna declarada.
                ver = "ANCHURA_NO_DECLARADA"
                diag = ("el macro dice %s<<%d y la herramienta escribe [%d], que "
                        "no dice de quantos bits es el campo. La POSICION es "
                        "correcta; la anchura no la declara nadie, ni la "
                        "herramienta ni ningun oraculo"
                        % (nom, lsb_unico, lo))
                k = "<<%d" % lsb_unico
            else:
                ver = "OK"
                diag = ANCHURA_NO_DETERMINABLE
                k = "<<%d" % lsb_unico

            filas.append({
                "paquete": op, "dword": _dw, "campo": campo,
                "herr": "%d:%d" % (hi, lo),
                "kernel": k, "veredicto": ver, "diagnostico": diag,
            })
    return filas


GENERACION_OBJETIVO = "gfx_v8_0.c"

# --- ORACULO DE ANCHURAS: amdkfd/kfd_pm4_headers_vi.h ---------------------
# DECLARADO AUSENTE en mi propia constante ANCHURA_NO_DETERMINABLE, y el
# hallazgo 1096 lo corrige: el documento estaba en el arbol, en cuatro copias, en
# el directorio de al lado. KFD declara los mismos paquetes que amdgpu pero con
# bitfields con ANCHURA, que es justo lo que vid.h no dice.
KFD_DIR = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                       "drivers", "gpu", "drm", "amd", "amdkfd")
KFD_HEADERS = ("kfd_pm4_headers_vi.h",)

RE_KFD_STRUCT = re.compile(r"^struct\s+pm4_mes_(\w+)\s*\{", re.M)
# El nombre NO es solo numerico: hay `bitfields3a` y `bitfields3b`, que son
# alternativas del MISMO dword (pasid frente a doorbell_offset0). Con
# `(\d+)` el grupo no casa y esos dos dwords desaparecen sin aviso.
# MEDIDO: faltaba el dword 2 entero de UNMAP_QUEUES.
RE_KFD_CIERRE = re.compile(r"\}\s*bitfields(\d+)[A-Za-z]*\s*;")
RE_KFD_BITFIELD = re.compile(r"(?:enum\s+[\w\s]+|uint32_t)\s+(\w+)\s*:\s*(\d+)\s*;")


def campos_kfd(directorio=None, cabeceras=None):
    """{PACKET3_X: {payload_index: {campo: (hi, lo)}}} desde KFD.

    EL ORDEN DE LOS BITFIELDS ES LSB-FIRST, y no lo dice el fichero. Se ha
    determinado MEDIDO, no supuesto: los cuatro campos con nombre de
    `UNMAP_QUEUES` dan sus posiciones correctas con LSB-first y ninguna con
    MSB-first, contra los desplazamientos independientes de `vid.h`.

        LSB-first -> action[1:0] queue_sel[5:4] engine_sel[28:26] num_queues[30:29]
        MSB-first -> action[31:30] queue_sel[27:26] engine_sel[5:3] num_queues[2:0]
                     4 de 4 coinciden / 0 de 4

    Suponer el orden equivocado haria que todas las anchuras salieran mal Y
    parecieran coherentes, que es el peor modo de fallo posible para una tabla
    de posiciones.
    """
    out = {}
    for h in (cabeceras or KFD_HEADERS):
        ruta = os.path.join(directorio or KFD_DIR, h)
        if not os.path.isfile(ruta):
            continue
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            continue
        for sm in RE_KFD_STRUCT.finditer(texto):
            nombre = "PACKET3_" + sm.group(1).upper()
            # El cuerpo se acota por LLAVES EMPAREJADAS, no por el primer
            # `};` del texto. Con la busqueda ingenua el cuerpo se desborda
            # dentro de la struct SIGUIENTE y se leen sus cierres como propios:
            # el oraculo mezclaba dos structs y no lo decia.
            # sm.end() es JUSTO DESPUES de la `{` que el patron ya consumio,
            # asi que esa llave ya esta contada y la profundidad arranca en 1.
            _prof, _fin = 1, None
            for _j in range(sm.end(), len(texto)):
                if texto[_j] == "{":
                    _prof += 1
                elif texto[_j] == "}":
                    _prof -= 1
                    if _prof == 0:
                        _fin = _j
                        break
            cuerpo = texto[sm.end():_fin if _fin else len(texto)]
            dwords = {}
            for cm in RE_KFD_CIERRE.finditer(cuerpo):
                ini = cuerpo.rfind("{", 0, cm.start())
                if ini < 0:
                    continue
                pos = 0
                campos = {}
                for bm in RE_KFD_BITFIELD.finditer(cuerpo[ini:cm.start()]):
                    n, w = bm.group(1), int(bm.group(2))
                    if w == 0 or pos + w > 32:
                        continue
                    campos[n.upper()] = (pos + w - 1, pos)
                    pos += w
                idx = int(cm.group(1)) - 1     # bitfields2 = payload 1
                if idx >= 1 and campos:
                    dwords[idx] = campos
            if dwords:
                out[nombre] = dwords
    return out


def campos_escritos(directorio, ops, ventana=40, solo_ficheros=None):
    """{opcode: {ordinal_de_payload: set(campo)}} desde las EMISIONES.

    Es el tercer oraculo y el unico que puede ver una AUSENCIA. Los otros dos
    --conteo y posicion-- solo hablan de lo que la herramienta declara: si
    falta un campo, no hay nada que comparar y el campo ausente no sale. Aqui
    la pregunta es al reves: que escribe el driver, y esta todo declarado?

    MEDIDO, y por que se construyo: `pm4_codec` declara el dword CONTROL2 de
    MAP_QUEUES con un solo campo, `doorbell_offset[25:2]`, mientras el kernel
    escribe ahi `QUEUE`, `PIPE` y `ME`. Tres campos emitidos y no etiquetados.
    El conteo dice 6 de 6 y la posicion dice que todo lo declarado esta bien:
    las dos comprobaciones pasan un layout al que le faltan tres campos.

    LIMITACION DECLARADA, no resuelta: no se modela el flujo de control. Una
    escritura que depende de un `if` cuenta como escrita aunque en una
    ejecucion concreta no ocurra. Eso hace que esta tabla notifique de mas, no
    de menos, que es el sentido seguro para un detector de ausencias: un falso
    positivo se investiga, un falso negativo se hereda.

    ALCANCE: por defecto solo se mira `solo_ficheros` (la generacion objetivo).
    Sin ese filtro, la tabla acusaba a MAP_QUEUES de omitir `VMID` y
    `ALLOC_FORMAT` tomando como referencia emisiones de GFX10 y GFX11, cuyo
    `CONTROL` es legiblemente distinto al de GFX8. Eso es un error de
    categoria, no un defecto: comparar la emicion de una generacion con el
    layout declarado de otra. Los ficheros excluidos se cuentan y se nombran;
    no se descartan en silencio.
    """
    prefijo = {op: op + "_" for op in ops}
    out = {}
    if solo_ficheros is None:
        solo_ficheros = [GENERACION_OBJETIVO]
    for ruta in sorted(glob.glob(os.path.join(directorio, "*.c"))):
        if solo_ficheros and os.path.basename(ruta) not in solo_ficheros:
            continue
        try:
            with open(ruta, errors="replace") as fh:
                lineas = fh.read().split("\n")
        except OSError:
            continue
        for i, l in enumerate(lineas):
            m = RE_PACKET3.search(l)
            if not m:
                continue
            op = m.group(1)
            if op not in prefijo:
                continue
            ordinal = 0
            campo_actual = None
            for nxt in lineas[i + 1:i + 1 + ventana]:
                if RE_PACKET3.search(nxt) or re.search(r"PACKET0?\(", nxt):
                    break
                if re.search(r"amdgpu_ring_write\s*\(|length_dw\+\+\]\s*=", nxt):
                    campo_actual = set()
                    ordinal += 1
                if campo_actual is None:
                    continue
                for mf in re.finditer(r"\b%s([A-Z0-9_]+)\s*\("
                                      % re.escape(prefijo[op]), nxt):
                    f = mf.group(1).lower()
                    if f.startswith("packet") or f.isdigit():
                        continue
                    campo_actual.add(f)
                    out.setdefault(op, {}).setdefault(
                        os.path.basename(ruta), {}).setdefault(
                            ordinal, set()).add(f)
    return out


def contraste_cobertura(declaraciones, cab, escritos):
    """Campos que el kernel ESCRIBE y la herramienta NO declara.

    Se separa POR FICHERO de emision, no solo por opcode. La primera version
    fusionaba todas las emisiones de un opcode en un unico mapa por ordinal, y
    el resultado era que MAP_QUEUES dword 1 aparecia con `VMID` y
    `ALLOC_FORMAT`: campos de GFX9+ que el driver de GFX8 no escribe nunca.
    Un Mapa agregado mezcla generaciones y produce cargos que no existen.

    Se compara por dword, no solo por paquete: un campo puede estar declarado
    y en el dword equivocado, y eso tambien es un defecto, pero es otro.
    """
    paquetes = set()
    for tabla in declaraciones:
        paquetes |= set(tabla)
    filas = []
    for op in sorted(paquetes):
        declarada = None
        for tabla in declaraciones:
            if op in tabla:
                declarada = tabla[op]
                break
        if declarada is None:
            continue
        h = cab.get(op)
        for fichero in sorted(escritos.get(op) or {}):
            esc = escritos[op][fichero]
            for ordinal in sorted(esc):
                if not esc[ordinal]:
                    continue
                idx = ordinal - 1
                if h and idx < len(h["campos"]):
                    nombre_dw = h["campos"][idx].split("[")[0].strip()
                else:
                    nombre_dw = "dword %d" % ordinal
                declarados = set()
                if 0 <= idx < len(declarada):
                    # `_nombres`, no `_tokens`. La cobertura necesita saber si
                    # un NOMBRE esta presente, y `ACTION` no tiene guion bajo:
                    # con `_tokens` salia como no declarado cuando si lo esta,
                    # que es un falso positivo con la forma exacta del defecto
                    # que la tabla busca.
                    declarados = _nombres(declarada[idx])
                for campo in sorted(esc[ordinal]):
                    nom = campo.upper()
                    # El alias se prueba como RESPALDO, nunca antes. Aplicado
                    # de entrada, convierte el DOORBELL_OFFSET de MAP_QUEUES
                    # en el DOORBELL_OFFSET0 de UNMAP_QUEUES y acusa a
                    # MAP_QUEUES de omitir un campo que si declara.
                    candidatos = {nom}
                    if nom in ALIAS:
                        candidatos.add(ALIAS[nom])
                    if candidatos & declarados:
                        continue
                    filas.append({
                        "paquete": op, "fichero": fichero, "dword": ordinal,
                        "dword_nombre": nombre_dw, "campo": nom,
                        "veredicto": "CAMPO_ESCRITO_NO_DECLARADO",
                        "diagnostico": ("%s escribe %s_%s en este dword y la "
                                        "herramienta declara %s. El campo sale "
                                        "sin etiqueta."
                                        % (fichero, op, nom,
                                           ("ningun campo" if not declarados
                                            else ", ".join(sorted(declarados)) or "sin campos"))),
                    })
    return filas


def oraculo_emision(directorio, generaciones=None):
    """{opcode: {"F": set, "payload": set, "ficheros": set}} en el corpus.

    `payload` es F + 1: el control cuenta como cabecera, no como payload.
    """
    out = {}
    ficheros = (glob.glob(os.path.join(directorio, "*.c"))
                if generaciones is None
                else generaciones)
    for ruta in sorted(ficheros):
        try:
            with open(ruta, errors="replace") as fh:
                src = fh.read()
        except OSError:
            continue
        for m in RE_PACKET3.finditer(src):
            op, F = m.group(1), int(m.group(2))
            if F == 0x3FFF:
                continue  # count todos: no informativo
            reg = out.setdefault(op, {"F": set(), "payload": set(), "ficheros": set()})
            reg["F"].add(F)
            reg["payload"].add(F + 1)
            reg["ficheros"].add(os.path.basename(ruta))
    return out


# ------------------------------------------------- las declaraciones
# --- ORACULO D: el RANGO del opcode. Un cuarto oraculo, y el unico cuyo
# veredicto se apoya en una prueba que no necesita ninguna fuente externa.
#
# La cabecera PACKET3, en las CUATRO cabeceras de generacion del arbol y con la
# MISMA definicion al byte (vid.h:105, sid.h:336, soc15d.h:50,
# gfx_v12_1_pkt.h:48):
#
#     #define PACKET3(op, n) ((TYPE3 << 30) | ((op) & 0xFF) << 8) \
#                                        | ((n) & 0x3FFF) << 16)
#
# o sea, en la cabecera:
#
#     bits 31:30  tipo de paquete        (3)
#     bits 29:16  count                  (14 bits)
#     bits 15:8   OPCODE                 (8 bits)
#     bits  7:0   sin usar
#
# El opcode son 8 bits, luego ningun opcode pasa de 0xFF. Lo que lo supera no
# es "un opcode raro": el campo lo enmascara con & 0xFF, asi que un literal de
# 0x2000 se convertiria en 0x00, que es OTRO paquete.
#
# MEDIDO en el arbol: `pm4_codec.opcode_table()` tiene 77 entradas y 7 no
# pueden ser opcodes. No son errores de lectura: son las constantes de la
# ventana de direccionamiento relativo, que comparten nombre con opcodes
# (`PACKET3_SET_SH_REG_START` = 0x2C00) y no son packets.
#
# CORRECCION (esta misma iteracion, hallazgo 1133): la primera version de este
# oraculo uso `OPCODE_MAX = 0x3FF` y justifico que "el opcode son los bits
# 0-9". Eso es FALSO: son los bits 8-15. La conclusion (7 entradas fuera de
# rango) es la misma porque los 7 valores pasan de 0xFF, pero la cota era
# incorrecta y habria dado OK a un opcode de 0x100 que el hardware no puede
# representar. Un limite mal puesto no falla hoy y falla el dia que aparezca
# el caso que deja pasar.
OPCODE_MAX = 0xFF
OPCODE_SHIFT = 8
CAMPO_OPCODE_EN_CABECERA = "bits 15:8"


def contrastar_rango_opcode(declarantes):
    """{ruta: [(valor, nombre, veredicto)]} entradas de tabla de opcode imposibles.

    Se lee la tabla por atributo (`opcode_table()`), no por fuente: lo que se
    audita es lo que la herramienta PUEDE devolver, que es lo que importa para
    un decodificador. Una herramienta sin esa funcion no aporta nada aqui, y
    eso se dice con `SOPORTA_OPCODE_TABLE`, no con un cero que parece limpio.
    """
    out = {}
    for d in declarantes:
        if d.get("error"):
            continue
        mod = d.get("mod")
        fn = getattr(mod, "opcode_table", None) if mod else None
        if not callable(fn):
            continue
        try:
            tabla = fn()
        except Exception as exc:                # noqa: BLE001
            out[d["ruta"]] = [("<error>", str(exc), "SOPORTA_OPCODE_TABLE")]
            continue
        filas = []
        for valor, nom in sorted(tabla.items(), key=lambda kv: kv[0]):
            nombre = nom[0] if isinstance(nom, tuple) else nom
            v = "OPCODE_FUERA_DE_RANGO" if valor > OPCODE_MAX else "OK"
            filas.append((valor, nombre, v))
        out[d["ruta"]] = filas
    return out


def descubrir_declarantes(directorios=None):
    """Localiza modulos que expongan un dict PACKET3_* -> lista de campos.

    No se codifica ningun modulo a mano: si manana otra herramienta declara
    layouts, entra en el contraste sin tocar este fichero.
    """
    dirs = directorios if directorios is not None else DIRS_HERRAMIENTA
    hallados = []
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for ruta in sorted(glob.glob(os.path.join(d, "*.py"))):
            try:
                with open(ruta, errors="replace") as fh:
                    texto = fh.read()
            except OSError:
                continue
            if "PACKET3_" not in texto:
                continue
            if not any(re.search(r"\b%s\b" % a, texto) for a in ATRIBUTOS):
                continue
            try:
                mod = cargar_modulo(ruta)
            except Exception as exc:               # noqa: BLE001
                hallados.append({"ruta": ruta, "layouts": None,
                                 "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            tablas = {}
            for a in ATRIBUTOS:
                t = getattr(mod, a, None)
                if not isinstance(t, dict):
                    continue
                sub = {k: v for k, v in t.items()
                       if isinstance(k, str) and k.startswith("PACKET3_")
                       and isinstance(v, (list, tuple))
                       and all(isinstance(x, str) for x in v)}
                if sub:
                    tablas[a] = sub
            if tablas:
                # Se guarda el modulo ya importado. Volver a importarlo por
                # ruta para el oraculo del rango de opcode seria importar dos
                # veces el mismo fichero, y la segunda podria no ser la misma
                # si alguien toco el disco entre medias. No se serializa: en la
                # salida JSON solo van `ruta` y `layouts`.
                hallados.append({"ruta": ruta, "layouts": tablas, "error": None,
                                 "mod": mod})
    return hallados


# --------------------------------------------------------------- contraste
def alinear(entradas_herr, campos_kernel):
    """Mejor alineacion entre las entradas de una herramienta y las del kernel.

    Se alinea POR CONTENIDO, no por el nombre de la primera entrada. Una
    herramienta puede incluir la cabecera y otra no; suponerlo por el nombre
    seria el mismo error de unidad que este fichero existe para evitar.

    Devuelve (desplazamiento, coincidencia) con mejor coincidencia, donde
    `desplazamiento` es cuantas entradas de la herramienta sobran al frente.
    """
    if not campos_kernel:
        return 0, 0.0
    mejor = (0, -1.0)
    for des in (0, 1, 2):
        if des >= len(entradas_herr):
            break
        ventana = campos_kernel[:len(entradas_herr) - des]
        if not ventana:
            continue
        # Si el lado del kernel no nombra ningun campo real, no hay nada que
        # comparar. Devolver 0.0 como si fuera un desacuerdo convertiria
        # "el kernel no lo desglosa" en "la herramienta esta mal".
        if not any(_tokens(c) - GENERICAS for c in ventana):
            return 0, 0.0
        puntos = 0.0
        for a, b in zip(entradas_herr[des:], ventana):
            ta, tb = _tokens(a), _tokens(b)
            ta = {ALIAS.get(t, t) for t in ta}
            if not ta or not tb:
                continue
            comunes = len(ta & tb)
            union = len(ta | tb) - len(ta & tb)
            puntos += (comunes / float(union)) if union else 1.0
        puntos /= len(ventana)
        if puntos > mejor[1]:
            mejor = (des, puntos)
    return mejor


def contrastar(declaraciones, cab, emi):
    """{paquete: veredicto} cruzando las tres fuentes.

    `declaraciones` es una lista PLANA de tablas {opcode: [entradas, ...]}.
    Si varias herramientas declaran el mismo opcode se usa la primera, pero
    el recuento queda en la fila: una declaracion contradictoria no puede
    esconderse detras de otra.
    """
    paquetes = set()
    for tabla in declaraciones:
        paquetes |= set(tabla)
    filas = []
    for op in sorted(paquetes):
        declarada, cuantos = None, 0
        for tabla in declaraciones:
            if op in tabla:
                cuantos += 1
                if declarada is None:      # gana la primera, como se documenta
                    declarada = tabla[op]
        h = cab.get(op)
        e = emi.get(op)
        n_herr = len(declarada)

        diag = ""
        if h is not None:
            des, coef = alinear(declarada, h["campos"])
            # La longitud se compara CRUDA contra la del kernel. La
            # alineacion por contenido NO puede rescatar un veredicto, solo
            # decir DONDE estan las entradas de mas.
            #
            # Esto es lo que decide si el instrumento sirve. Una herramienta
            # que declara la cabecera ademas del payload tiene un dword de mas
            # y al decodificar desplaza TODOS los nombres de campo una
            # posicion; el framing sigue siendo correcto, asi que nada mas lo
            # delata. Aceptar eso como "alineable" seria repetir el defecto
            # buscando detectarlo.
            if n_herr != h["payload"]:
                ver = "DISCREPA"
                # `extras` es cuantas sobran. `des` es DONDE estan, no
                # cuantas: restarlo aqui lo contaria dos veces y.diria
                # "sobran 0" justamente en el caso que motiva el
                # instrumento.
                extras = n_herr - h["payload"]
                if des >= extras:
                    donde = ("las %d sobrantes estan al frente (alineacion=%d)"
                             % (extras, des))
                else:
                    donde = ("sobran %d en total, la alineacion solo sitúa %d "
                             "al frente: sobran por el otro extremo"
                             % (extras, des))
                diag = ("la herramienta declara %d y el kernel documenta %d %s "
                        "(%s)" % (n_herr, h["payload"], UNIDAD_PAYLOAD, donde))
            elif coef >= 0.5:
                ver = "OK"
            elif coef == 0.0:
                ver = "NOMBRES_NO_COMPARABLES"
                diag = ("las cuentas coinciden (%d) pero el kernel no "
                        "desglosa los subcampos, asi que los nombres no son "
                        "contrastables: no es un veredicto sobre la "
                        "herramienta" % h["payload"])
            else:
                ver = "DISCREPA"
                diag = ("mismo numero de campos (%d) pero el contenido no "
                        "coincide (coincidencia %.0f%%)" % (n_herr, coef * 100))
        elif e is not None:
            ver = "OK" if n_herr in e["payload"] else "DISCREPA"
            diag = "" if ver == "OK" else (
                "la herramienta declara %d y la emision implica %d %s"
                % (n_herr, sorted(e["payload"])[0], UNIDAD_PAYLOAD))
        else:
            ver = "SIN_ORACULO"
            diag = "declarado y sin ningun oraculo: no contrastado"

        filas.append({
            "paquete": op,
            "herramienta": n_herr,
            "declarantes": cuantos,
            "cab_total": h["total"] if h else None,
            "cab_payload": h["payload"] if h else None,
            "emi_payload": sorted(e["payload"]) if e else None,
            "veredicto": ver,
            "diagnostico": diag,
            "donde": h["donde"][0] if h and h["donde"] else "",
        })
    return filas


# ------------------------------------------------------------------ salida
def formatear_cob(filas, alcance=None, excluidos=()):
    out = []
    out.append("-" * 96)
    out.append("COBERTURA: campos que el kernel ESCRIBE y la herramienta NO declara")
    out.append("-" * 96)
    out.append("Esta es la UNICA tabla que puede ver una ausencia. Las otras dos")
    out.append("hablan solo de lo declarado: un campo que falta no se compara con")
    out.append("nada y no sale.")
    out.append("")
    if alcance is not None:
        out.append("ALCANCE: solo emisiones de %s. Es el driver de la generacion" % alcance)
        out.append("que declara la herramienta. Comparar la emision de otra")
        out.append("generacion con un layout de GFX8 seria un error de categoria.")
        if excluidos:
            out.append("Emisiones de otras generaciones EXCLUIDAS y no juzgadas: %d"
                       % len(excluidos))
            out.append("  %s" % ", ".join(sorted(excluidos)))
        else:
            out.append("Emisiones de otras generaciones: ninguna en el corpus.")
        out.append("")
    if not filas:
        out.append("ningun campo escrito por el kernel queda sin declarar.")
        return "\n".join(out)
    out.append("%-26s %-16s %-5s %-18s %-22s %s"
               % ("paquete", "fichero", "dword", "dword (kernel)",
                  "campo escrito", "veredicto"))
    out.append("-" * 96)
    for f in filas:
        out.append("%-26s %-16s %-5s %-18s %-22s %s"
                   % (f["paquete"], f["fichero"], f["dword"], f["dword_nombre"],
                      f["campo"], f["veredicto"]))
    out.append("")
    out.append("%d campos escritos y no declarados.  Decodificar esto no falla:"
               % len(filas))
    out.append("devuelve un dword con parte sin etiqueta, que parece correcto")
    out.append("y no lo es.  Es el fallo que no puede ver un conteo.")
    return "\n".join(out)


def _cuenta(filas):
    c = {}
    for f in filas:
        c[f["veredicto"]] = c.get(f["veredicto"], 0) + 1
    return c


def formatear_opcode(filas):
    """La tabla de opcodes, con lo que NO puede ser opcode separado.

    No se mezcla con los otros tres oraculos porque no compara dos fuentes:
    comprueba una propiedad interna de la tabla contra la estructura de la
    cabecera PACKET3. Mezclarla haria que un `OPCODE_FUERA_DE_RANGO` pareciera
    una discrepancia entre el kernel y la herramienta, y no lo es.
    """
    o = ["-" * 88,
         "RANGO DE OPCODE  (4º oraculo, y el unico que no compara fuentes)",
         "-" * 88,
         "La cabecera PACKET3 es (tipo<<30) | (count<<16) | (opcode<<8), y el",
         "opcode se enmascara con & 0xFF: son 8 bits, en los %s de la cabecera."
         % CAMPO_OPCODE_EN_CABECERA,
         "Ningun opcode pasa de 0x%02X. Lo que lo supera no es un opcode raro:" % OPCODE_MAX,
         "el campo lo tritura: un literal de 0x2000 se convertiria en 0x00, "
         "que es otro paquete. Son constantes de ventana de direccionamiento "
         "relativo.",
         "Este veredicto no compara dos fuentes: comprueba la tabla de la",
         "herramienta contra la estructura de la cabecera, asi que un OK aqui",
         "no dice nada sobre si el nombre es el correcto.",
         ""]
    fuera = [f for f in filas if f["veredicto"] == "OPCODE_FUERA_DE_RANGO"]
    o.append("   %-10s %-34s %s" % ("valor", "nombre en la herramienta", "veredicto"))
    o.append("-" * 88)
    for f in fuera:
        o.append("   %-10s %-34s %s" % (f["valor"], f["nombre"], f["veredicto"]))
    o.append("")
    o.append("   %d de %d entradas no pueden ser opcode (%.0f%%); %d si pueden."
             % (len(fuera), len(filas), 100.0 * len(fuera) / max(1, len(filas)),
                len(filas) - len(fuera)))
    return "\n".join(o)


def formatear_bits(filas):
    out = []
    out.append("-" * 96)
    out.append("ASIGNACION DE CAMPOS A DWORDS  (pregunta distinta del conteo)")
    out.append("-" * 96)
    out.append("UNIDADES:  'herr' es [hi:lo] afirmado.  'kernel' es el LSB del")
    out.append("           macro, y solo se imprime si TODAS las cabeceras que")
    out.append("           definen ese campo coinciden.  %s" % ANCHURA_NO_DETERMINABLE)
    out.append("")
    if not filas:
        out.append("ninguna herramienta afirma posiciones de bit.")
        return "\n".join(out)
    out.append("%-28s %-20s %-8s %-8s  %-30s %s"
               % ("paquete", "campo", "herr", "kernel", "veredicto", "diagnostico"))
    out.append("-" * 96)
    for f in filas:
        out.append("%-28s %-20s %-8s %-8s  %-30s %s"
                   % (f["paquete"], f["campo"], f["herr"], f["kernel"] or "-",
                      f["veredicto"], f["diagnostico"]))
    out.append("")
    c = _cuenta(filas)
    out.append("   ".join("%s %d" % (k, c[k]) for k in sorted(c)))
    out.append("de %d afirmaciones de bits.  POSICION_DEPENIENTE_GENERACION no es"
               % len(filas))
    out.append("un fallo de la herramienta: es que no hay un valor unico que")
    out.append("contrastar.  CAMPO_INVENTADO si lo es: el nombre no existe.")
    return "\n".join(out)


def formatear(filas):
    out = []
    out.append("=" * 96)
    out.append("CONTRASTE CRUZADO DE LAYOUTS DECLARADOS  vs  ORACULOS DEL CORPUS")
    out.append("=" * 96)
    out.append("UNIDADES:  la columna 'herr' es la longitud de la lista declarada.")
    out.append("           'cab' y 'emi' son %s." % UNIDAD_PAYLOAD)
    out.append("           'total' incluye la cabecera; por eso total = cab + 1.")
    out.append("")
    out.append("%-30s %5s %6s %5s %6s  %-12s %s"
               % ("paquete", "herr", "total", "cab", "emi", "veredicto", "diagnostico"))
    out.append("-" * 96)
    for f in filas:
        out.append("%-30s %5s %6s %5s %6s  %-12s %s"
                   % (f["paquete"], f["herramienta"],
                      f["cab_total"] if f["cab_total"] else "-",
                      f["cab_payload"] if f["cab_payload"] else "-",
                      ",".join(map(str, f["emi_payload"])) if f["emi_payload"] else "-",
                      f["veredicto"], f["diagnostico"]))
    out.append("")
    ok = sum(1 for f in filas if f["veredicto"] == "OK")
    mal = sum(1 for f in filas if f["veredicto"] == "DISCREPA")
    sin = sum(1 for f in filas if f["veredicto"] == "SIN_ORACULO")
    nocom = sum(1 for f in filas if f["veredicto"] == "NOMBRES_NO_COMPARABLES")
    out.append("OK %d   DISCREPA %d   SIN_ORACULO %d   NOMBRES_NO_COMPARABLES %d"
               "   (de %d declaraciones)" % (ok, mal, sin, nocom, len(filas)))
    out.append("cobertura: %d de %d declaraciones contrastadas contra la cabecera; "
               "%d contra la emision." % (len(filas) - sin, len(filas), ok + mal))
    if nocom:
        out.append("")
        out.append("NOMBRES_NO_COMPARABLES: la cuenta de dwords coincide, pero el")
        out.append("kernel no desglosa esos subcampos. NO es un veredicto sobre la")
        out.append("herramienta. Que no haya nombre no es que el nombre sea falso.")
    if sin:
        out.append("")
        out.append("SIN_ORACULO no es OK. Son declaraciones que nadie ha")
        out.append("contrastado. Un absent no es un acierto.")
    dup = [f for f in filas if f.get("declarantes", 1) > 1]
    if dup:
        out.append("")
        out.append("ATENCION: %d paquetes declarados por mas de una herramienta."
                   " Se uso la primera; las demas pueden contradecirla."
                   % len(dup))
        for f in dup:
            out.append("   %-30s x%d" % (f["paquete"], f["declarantes"]))
    return "\n".join(out)


# ----------------------------------------------------------------- selftest
KIER = """#define    PACKET3_XXX    0xA2
/* 1. header
 * 2. SRC_ADDR_LO or DATA [31:0]
 * 3. CP_SYNC [31] | SRC_SEL [30:29] |
 *    SRC_ADDR_HI [7:0]
 * 4. DST_ADDR_LO [31:0]
 * 5. DST_ADDR_HI [7:0]
 */
#              define PACKET3_XXX_DST_SEL(x)    ((x) << 20)
"""

EMITE_BIEN = """void f(struct ring *r) {
    amdgpu_ring_write(r, PACKET3(PACKET3_YYY, 5));
    amdgpu_ring_write(r, a);
    amdgpu_ring_write(r, b);
    amdgpu_ring_write(r, c);
    amdgpu_ring_write(r, d);
    amdgpu_ring_write(r, e);
    amdgpu_ring_write(r, f);
}
"""

EMITE_MAL = """void f(struct ring *r) {
    amdgpu_ring_write(r, PACKET3(PACKET3_ZZZ, 4));
    amdgpu_ring_write(r, a);
    amdgpu_ring_write(r, b);
    amdgpu_ring_write(r, c);
    amdgpu_ring_write(r, d);
    amdgpu_ring_write(r, e);
}
"""

MOD_OK = """DOC_LAYOUTS = {
    "PACKET3_XXX": [
        "SRC_ADDR_LO | DATA",
        "CP_SYNC[31] | SRC_SEL[30:29] | SRC_ADDR_HI[7:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
    ],
    "PACKET3_YYY": ["A[31:0]", "B[31:0]", "C[31:0]", "D[31:0]", "E[31:0]", "F[31:0]"],
    "PACKET3_QQQ": ["SOLO[31:0]"],
}
"""

# declara la cabecera de mas: el defecto real de pm4_codec sobre CP_DMA
MOD_CON_CABECERA = """DOC_LAYOUTS = {
    "PACKET3_XXX": [
        "CONTROL",
        "SRC_ADDR_LO | DATA",
        "CP_SYNC[31] | SRC_SEL[30:29] | SRC_ADDR_HI[7:0]",
        "DST_ADDR_LO[31:0]",
        "DST_ADDR_HI[7:0]",
    ],
}
"""

MOD_MAL = """DOC_LAYOUTS = {
    "PACKET3_ZZZ": ["A[31:0]", "B[31:0]", "C[31:0]"],
}
"""


def _vtmp():
    d = tempfile.mkdtemp(prefix="layoutcross-")
    with open(os.path.join(d, "ki.h"), "w") as fh:
        fh.write(KIER)
    with open(os.path.join(d, "ki.c"), "w") as fh:
        fh.write(EMITE_BIEN)
    with open(os.path.join(d, "ki2.c"), "w") as fh:
        fh.write(EMITE_MAL)
    return d


def selftest(_=None):
    fallos = []

    # El numero de vectores se CUENTA, no se escribe. Antes era la constante
    # `20 + 34`: anadir un vector no lo movia y quitar un grupo tampoco, asi
    # que la cifra que da la confianza en el selftest no dependia del selftest.
    # Es la clase de bug que este proyecto ya ha pagado: un valor que parece
    # medido y es una constante.
    _vistos = set()

    def chk(nombre, cond, detalle=""):
        _vistos.add(nombre)
        if cond:
            print("  ok   %s" % nombre)
        else:
            print("  FALLA %s  %s" % (nombre, detalle))
            fallos.append(nombre)

    d = _vtmp()

    # 1. la entrada numerada agrupa continuaciones en el mismo campo
    cab = oraculo_cabecera(d)
    chk("cabecera: encuentra el opcode", "PACKET3_XXX" in cab, str(sorted(cab)))
    chk("cabecera: total = cabecera + payload = 5",
        cab.get("PACKET3_XXX", {}).get("total") == 5,
        str(cab.get("PACKET3_XXX")))
    chk("cabecera: payload = 4 (no cuenta la cabecera)",
        cab.get("PACKET3_XXX", {}).get("payload") == 4,
        str(cab.get("PACKET3_XXX")))
    chk("cabecera: la continuacion se une al campo 3",
        "SRC_ADDR_HI" in " ".join(cab.get("PACKET3_XXX", {}).get("campos", [])),
        str(cab.get("PACKET3_XXX", {}).get("campos")))
    chk("unidades: total == payload + 1 SIEMPRE",
        all(v["total"] == v["payload"] + 1 for v in cab.values()))

    # 2. la emision da payload = F + 1
    emi = oraculo_emision(d)
    chk("emision: F=5 implica 6 payload",
        emi.get("PACKET3_YYY", {}).get("payload") == {6},
        str(emi.get("PACKET3_YYY")))
    chk("emision: F=4 implica 5 payload",
        emi.get("PACKET3_ZZZ", {}).get("payload") == {5},
        str(emi.get("PACKET3_ZZZ")))
    chk("emision: se ignoran los count 0x3FFF",
        "PACKET3_XXX" not in emi)

    # 3. la alineacion por contenido
    kern3 = ["MQD_ADDR_LO[31:0]", "MQD_ADDR_HI[7:0]", "DST_ADDR_LO[31:0]"]
    des, coef = alinear(kern3, kern3)
    chk("alinear: sin desplazamiento con identicos", des == 0 and coef == 1.0,
        "des=%d coef=%.2f" % (des, coef))
    des, coef = alinear(["CONTROL", "MQD_ADDR_LO", "MQD_ADDR_HI"], kern3[:2])
    chk("alinear: detecta entrada sobrante al frente", des == 1,
        "des=%d coef=%.2f" % (des, coef))
    chk("alinear: el caso no puede cancelar el sobrante", des == 1,
        "des=%d" % des)

    # 4. los tres veredictos
    rutas = []
    for nombre, cuerpo in (("m_ok.py", MOD_OK),
                           ("m_cab.py", MOD_CON_CABECERA),
                           ("m_mal.py", MOD_MAL)):
        p = os.path.join(d, nombre)
        with open(p, "w") as fh:
            fh.write(cuerpo)
        rutas.append(p)

    decl = []
    for p in rutas:
        mod = cargar_modulo(p)
        decl.append(mod.DOC_LAYOUTS)

    filas = contrastar(decl, cab, emi)
    por = {f["paquete"]: f for f in filas}

    chk("veredicto OK contra cabecera",
        por["PACKET3_YYY"]["veredicto"] == "OK",
        por["PACKET3_YYY"]["veredicto"])
    chk("veredicto OK: la herramienta alineada con el kernel",
        por["PACKET3_XXX"]["veredicto"] == "OK",
        "%s %s" % (por["PACKET3_XXX"]["veredicto"],
                   por["PACKET3_XXX"]["diagnostico"]))
    chk("veredicto DISCREPA: declara 3, el kernel emite 5 payload",
        por["PACKET3_ZZZ"]["veredicto"] == "DISCREPA",
        "%s %s" % (por["PACKET3_ZZZ"]["veredicto"],
                   por["PACKET3_ZZZ"]["diagnostico"]))
    chk("veredicto SIN_ORACULO: nadie lo ha contrastado",
        por["PACKET3_QQQ"]["veredicto"] == "SIN_ORACULO",
        por["PACKET3_QQQ"]["veredicto"])

    # 5. declarar la cabecera de mas debe marcarse, no aceptarse en silencio.
    #    Este vector es el defecto real de pm4_codec sobre CP_DMA: la lista
    #    tiene una entrada mas que el payload del kernel, con lo que al
    #    decodificar cada nombre queda una posicion desplazada y el framing
    #    sigue siendo correcto, asi que nada mas lo delata.
    decl2 = [{"PACKET3_XXX": [
        "CONTROL", "SRC_ADDR_LO | DATA",
        "CP_SYNC[31] | SRC_SEL[30:29] | SRC_ADDR_HI[7:0]",
        "DST_ADDR_LO[31:0]", "DST_ADDR_HI[7:0]"]}]
    f2 = {f["paquete"]: f for f in contrastar(decl2, cab, emi)}
    chk("contar la cabecera de mas se marca DISCREPA, no se normaliza",
        f2["PACKET3_XXX"]["veredicto"] == "DISCREPA",
        f2["PACKET3_XXX"]["veredicto"])
    chk("el diagnostico localiza el sobrante (1 al frente)",
        "1 sobrantes estan al frente" in f2["PACKET3_XXX"]["diagnostico"],
        f2["PACKET3_XXX"]["diagnostico"])
    chk("el diagnostico nunca dice 'sobran 0' al haber sobrantes",
        "sobran 0" not in f2["PACKET3_XXX"]["diagnostico"],
        f2["PACKET3_XXX"]["diagnostico"])

    # 6. la clase de falso positivo: el kernel nombra generico, la herramienta
#    desglosa. MISMOS dwords. No puede salir DISCREPA.
    GENERICO = """#define    PACKET3_GEN    0xA2
/* 1. header
 * 2. CONTROL
 * 3. CONTROL2
 * 4. CONTROL3
 */
"""
    d2 = tempfile.mkdtemp(prefix="layoutcross-generico-")
    with open(os.path.join(d2, "g.h"), "w") as fh:
        fh.write(GENERICO)
    cab2 = oraculo_cabecera(d2)
    decl3 = [{"PACKET3_GEN": ["ACTION[1] | QUEUE_SEL[2:0]",
                             "NUM_QUEUES[10] | DOORBELL_OFFSET[25:2]",
                             "dword[2]"]}]
    f3 = contrastar(decl3, cab2, {})
    chk("nombres genericos del kernel NO producen DISCREPA",
        f3[0]["veredicto"] == "NOMBRES_NO_COMPARABLES",
        "%s | %s" % (f3[0]["veredicto"], f3[0]["diagnostico"]))
    chk("nombres genericos: la cuenta sigue siendo la que se contrasta",
        f3[0]["cab_payload"] == 3 and f3[0]["herramienta"] == 3,
        str(f3[0]))

    # 7. cobertura y exit codes
    txt = formatear(filas)
    chk("la salida nombra las unidades",
        UNIDAD_PAYLOAD in txt and UNIDAD_TOTAL not in txt)
    chk("la salida separa OK / DISCREPA / SIN_ORACULO",
        "SIN_ORACULO no es OK" in txt)
    chk("la salida declara la cobertura",
        "cobertura:" in txt)

    # 8. corpus vacio -> SIN_ORACULO, no OK
    filas_vacias = contrastar([{"PACKET3_ZZZ": ["A"]}], {}, {})
    chk("sin oraculo, sin coincidencia: SIN_ORACULO",
        filas_vacias[0]["veredicto"] == "SIN_ORACULO",
        filas_vacias[0]["veredicto"])

    # 9. el descubrimiento no necesita codificar modulo
    hallados = descubrir_declarantes([d])
    chk("descubre declarantes sin lista codificada",
        len(hallados) == 3, str([h["ruta"] for h in hallados]))

    # 10. tokens: los bitfield no contaminan
    chk("tokens: ignora los indices de bit",
        _tokens("CONTROL2[31:0]  (doorbell_offset[25:2])") == {"DOORBELL_OFFSET"},
        str(_tokens("CONTROL2[31:0]  (doorbell_offset[25:2])")))
    chk("tokens: el mismo campo en(kernel) y en(herramienta) coincide",
        _tokens("WPTR_ADDR_HI [7:0]") == _tokens("wptr_addr_hi[7:0]"),
        "%s vs %s" % (_tokens("WPTR_ADDR_HI [7:0]"), _tokens("wptr_addr_hi[7:0]")))
    chk("tokens: una etiqueta sin guion bajo no es un campo",
        _tokens("CONTROL2[31:0]") == set(),
        str(_tokens("CONTROL2[31:0]")))

    # 11. determinismo
    chk("misma entrada, misma salida",
        contrastar(decl, cab, emi) == filas)

    # 12. LOS BITS.  Este bloque no existia cuando se escribio la primera
    # version y por eso las 6 contradicciones iniciales salieron como
    # DISCREPA.  Cada clase de veredicto tiene aqui su vector.
    H_A = """#define    PACKET3_BT    0xA2
/* 1. header
 * 2. CONTROL
 * 3. QUEUE_MASK_LO [31:0]
 * 4. OAC_MASK [15:0]
 * 5. GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]
 */
#              define PACKET3_BT_SRC_SEL(x)    ((x) << 29)
#              define PACKET3_BT_DST_SEL(x)    ((x) << 20)
#              define PACKET3_BT_VMID_MASK(x)  ((x) << 0)
#              define PACKET3_BT_MSBP(x)       ((x) >> 4)
"""
    H_B = """#define    PACKET3_BT    0xA2
/* 1. header
 * 2. CONTROL
 * 3. QUEUE_MASK_LO [31:0]
 * 4. OAC_MASK [15:0]
 * 5. GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]
 */
#              define PACKET3_BT_SRC_SEL(x)    ((x) << 5)
#              define PACKET3_BT_DST_SEL(x)    ((x) << 20)
#              define PACKET3_BT_VMID_MASK(x)  ((x) << 0)
"""
    H_SLOT = """#define    PACKET3_SL    0xA2
/* 1. header
 * 2. CONTROL
 * 3. ADDR_LO [31:0]
 * 4. ADDR_HI [31:0]
 */
"""
    d3 = tempfile.mkdtemp(prefix="layoutcross-bits-")
    for nombre, cuerpo in (("vid.h", H_A), ("soc15d.h", H_B), ("nvd.h", H_SLOT)):
        with open(os.path.join(d3, nombre), "w") as fh:
            fh.write(cuerpo)
    cab3 = oraculo_cabecera(d3)
    bits3 = oraculo_bits(d3, {"PACKET3_BT", "PACKET3_SL"})

    chk("bits: el valor se guarda POR CABECERA, no colapsado",
        bits3["PACKET3_BT"]["src_sel"] == {"vid.h": 29, "soc15d.h": 5},
        str(bits3.get("PACKET3_BT", {}).get("src_sel")))
    chk("bits: `>>` no se guarda, da MSB y no es comparable",
        "msbp" not in bits3.get("PACKET3_BT", {}),
        str(sorted(bits3.get("PACKET3_BT", {}))))
    chk("bits_del_comentario: lee los rangos parciales",
        bits_del_comentario(["GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]"])
        == {"GDS_HEAP_SIZE": (16, 11), "GDS_HEAP_BASE": (5, 0)},
        str(bits_del_comentario(
            ["GDS_HEAP_SIZE [16:11] | GDS_HEAP_BASE [5:0]"])))
    chk("_desglosa: anchura parcial SI es desglose",
        _desglosa(cab3["PACKET3_BT"]["campos"]) is True)
    chk("_desglosa: solo [31:0] NO es desglose",
        _desglosa(cab3["PACKET3_SL"]["campos"]) is False,
        str(cab3["PACKET3_SL"]["campos"]))
    chk("_nombres ve un nombre sin guion bajo (COMMAND/CONTROL)",
        "COMMAND" in _nombres("COMMAND [30:21] | BYTE_COUNT [20:0]")
        and "CONTROL" in _nombres("CONTROL"), str(_nombres("CONTROL")))

    # las seis clases, sobre el mismo corpus
    decl4 = [{"PACKET3_BT": [
        "vmid_mask[15:0]",                       # OK por comentario
        "gds_heap_base[9:0]",                    # DISCREPA_ANCHURA (mismo LSB)
        "oac_mask[20:16]",                      # DISCREPA_POSICION (LSB distinto)
        "src_sel[29:29]",                        # POSICION_DEPENIENTE
        "dst_sel[31:25]",                        # CONTRADICCION (macro dice <<20)
        "campo_que_no_existe[31:0]",             # CAMPO_INVENTADO
        "control[31:0]",                         # SIN_ORACULO_BITS
        "queue_mask_lo[31:0]",                   # OK, corroborado por el comentario
    ]}]
    fb = {f["campo"]: f for f in contrastar_bits(decl4, cab3, bits3)}
    chk("bits OK: corroborado por el comentario del kernel",
        fb["vmid_mask"]["veredicto"] == "OK", fb["vmid_mask"]["veredicto"])
    chk("bits DISCREPA_ANCHURA: mismo LSB, rango mas estrecho",
        fb["gds_heap_base"]["veredicto"] == "DISCREPA_ANCHURA",
        fb["gds_heap_base"]["veredicto"])
    chk("bits DISCREPA_POSICION: LSB distinto",
        fb["oac_mask"]["veredicto"] == "DISCREPA_POSICION",
        fb["oac_mask"]["veredicto"])
    chk("bits: ANCHURA y POSICION no se mezclan en un veredicto",
        fb["gds_heap_base"]["veredicto"] != fb["oac_mask"]["veredicto"])
    # --- [N] NO es [N:N].  Fijado con 4 vectores, porque la lectura
    # equivocada daba OK (un OK no ganado) y no se nota en la tabla.
    # el oraculo KFD que usa el resto del selftest, con ALPHA en el payload 1
    # `dst_sel` es el campo cuyos macros coinciden en las tres cabeceras, asi
    # que no cae en POSICION_DEPENIENTE_GENERACION y el vector mide lo que dice
    # medir: solo el efecto de escribir [N] en vez de [27:20].
    kdn = {"PACKET3_BT": {2: {"DST_SEL": (31, 27)}}}
    fn = {f["campo"]: f for f in contrastar_bits(
        [{"PACKET3_BT": ["CONTROL[31:0]", "dst_sel[27]"]}], cab3, bits3, kdn)}
    chk("bits [N] con LSB correcto y KFD mas ancho: ANCHURA_NO_DECLARADA, no OK",
        fn["dst_sel"]["veredicto"] == "ANCHURA_NO_DECLARADA",
        fn["dst_sel"]["veredicto"])
    chk("bits [N] NO se acusa de DISCREPA_ANCHURA (no declaro anchura)",
        fn["dst_sel"]["veredicto"] != "DISCREPA_ANCHURA")
    chk("bits [N] con KFD da el diagnostico ANCHURA, no el de truncamiento",
        "no dice de quantos bits" in fn["dst_sel"]["diagnostico"])
    # control positivo del control: el MISMO campo, escrito con anchura
    # completa y con el KFD que la respalda, tiene que salir OK. Sin este
    # vector, ANCHURA_NO_DECLARADA seria indistinguible de "este oraculo no
    # dice nada" y el test pasaria con la rama muerta.
    fx = [f for f in contrastar_bits(
        [{"PACKET3_BT": ["CONTROL[31:0]", "dst_sel[31:27]"]}], cab3, bits3, kdn)
          if f["campo"] == "dst_sel"][0]
    chk("bits [hi:lo] explicito con KFD coincidente: OK, no ANCHURA_NO_DECLARADA",
        fx["veredicto"] == "OK", fx["veredicto"])
    chk("bits POSICION_DEPENIENTE_GENERACION: los macros no coinciden entre cabeceras",
        fb["src_sel"]["veredicto"] == "POSICION_DEPENIENTE_GENERACION",
        fb["src_sel"]["veredicto"])
    chk("bits CONTRADICCION: el macro discrepa y el comentario no declara rango",
        fb["dst_sel"]["veredicto"] == "CONTRADICCION",
        fb["dst_sel"]["veredicto"])
    chk("bits CAMPO_INVENTADO: ninguna cabecera lo nombra",
        fb["campo_que_no_existe"]["veredicto"] == "CAMPO_INVENTADO",
        fb["campo_que_no_existe"]["veredicto"])
    chk("bits SIN_ORACULO_BITS: el kernel lo nombra pero no lo posiciona",
        fb["control"]["veredicto"] == "SIN_ORACULO_BITS",
        fb["control"]["veredicto"])
    chk("bits: un dword de anchura completa SI queda corroborado por el comentario",
        fb["queue_mask_lo"]["veredicto"] == "OK"
        and "comentario" in fb["queue_mask_lo"]["diagnostico"],
        fb["queue_mask_lo"]["veredicto"])
    chk("bits: si el LSB coincide, no es CONTRADICCION aunque el hi difiera",
        contrastar_bits([{"PACKET3_BT": ["dst_sel[27:20]"]}], cab3, bits3
                        )[0]["veredicto"] == "OK",
        contrastar_bits([{"PACKET3_BT": ["dst_sel[27:20]"]}], cab3, bits3
                        )[0]["veredicto"])

    # el caso que la primera versionacia como CAMPO_INVENTADO
    decl5 = [{"PACKET3_SL": ["CONTROL[31:0]", "VMID[31:28]", "REGISTER_INDEX[23:0]"]}]
    fs = {f["campo"]: f for f in contrastar_bits(decl5, cab3, bits3)}
    chk("bits NOMBRES_NO_COMPARABLES: el kernel solo nombra ranuras",
        all(f["veredicto"] == "NOMBRES_NO_COMPARABLES" for f in fs.values()),
        str({k: v["veredicto"] for k, v in fs.items()}))
    chk("bits: ningun CAMPO_INVENTADO cuando el kernel no desglosa",
        not any(f["veredicto"] == "CAMPO_INVENTADO" for f in fs.values()),
        str({k: v["veredicto"] for k, v in fs.items()}))

    # una CONTRADICCION no puede contarse como DISCREPA
    chk("bits: la clase POSICION se nombra en el diagnostico",
        "LSB" in fb["oac_mask"]["diagnostico"],
        fb["oac_mask"]["diagnostico"])
    chk("bits: la clase ANCHURA dice que no es funcional",
        "no es un fallo funcional" in fb["gds_heap_base"]["diagnostico"],
        fb["gds_heap_base"]["diagnostico"])
    # DISCREPA_DWORD: el campo existe en KFD pero en OTRO dword. Es la clase
    # que convierte el "una entrada de mas" de 1061 en "QUE entrada", y sin
    # vector es una rama sin probar.
    # Los dos campos en el MISMO payload 1: alpha esta donde KFD lo pone
    # y beta no, porque KFD lo pone en el payload 2. En entradas
    # separadas cada uno caia en un payload distinto y los dos cuadraban. Las claves del dict son el NOMBRE TAL COMO LO
    # ESCRIBIO la herramienta, no en mayuscula: las filas de layoutcross
    # conservan el caso original.
    kd = {"PACKET3_BT": {1: {"ALPHA": (15, 0)}, 2: {"BETA": (31, 16)}}}
    decl_dw = [{"PACKET3_BT": ["alpha[15:0] | beta[31:16]"]}]
    fd = {f["campo"]: f for f in contrastar_bits(decl_dw, {}, {}, kd)}
    chk("bits DISCREPA_DWORD: el campo existe pero en otro payload",
        fd["beta"]["veredicto"] == "DISCREPA_DWORD",
        fd["beta"]["veredicto"])
    chk("bits DISCREPA_DWORD: dice en que payload esta KFD",
        "payload 2" in fd["beta"]["diagnostico"],
        fd["beta"]["diagnostico"])
    chk("bits: el campo en SU payload no se marca",
        fd["alpha"]["veredicto"] == "OK", fd["alpha"]["veredicto"])
    chk("bits: CONTRADICCION y DISCREPA son clases distintas",
        fb["dst_sel"]["veredicto"] != fb["gds_heap_base"]["veredicto"])
    chk("bits: determinista",
        contrastar_bits(decl4, cab3, bits3) == contrastar_bits(decl4, cab3, bits3))
    txtb = formatear_bits(contrastar_bits(decl4, cab3, bits3))
    chk("la salida de bits declara que la anchura no es contrastable",
        ANCHURA_NO_DETERMINABLE in txtb)
    chk("la salida de bits separa CONTRADICCION de CAMPO_INVENTADO",
        "CAMPO_INVENTADO si lo es" in txtb)

    # 13. COBERTURA.  La unica tabla que puede ver una AUSENCIA, y la que mas
    #     falsos positivos ha tenido: 17 filas inventadas por dos bugs.
    EMITE_COB = """static void f(struct ring *r, u32 q) {
    amdgpu_ring_write(r, PACKET3(PACKET3_CB, 1));
    amdgpu_ring_write(r, PACKET3_CB_ALPHA(1) |
                PACKET3_CB_BETA(q) |
                PACKET3_CB_GAMMA(0));
    amdgpu_ring_write(r, 0);
}
"""
    d4 = tempfile.mkdtemp(prefix="layoutcross-cob-")
    with open(os.path.join(d4, "gfx_v8_0.c"), "w") as fh:
        fh.write(EMITE_COB)
    with open(os.path.join(d4, "gfx_v9_0.c"), "w") as fh:
        # Mismo opcode, campos DISTINTOS. Es lo que hace que el filtro de
        # generacion tenga algo que excluir: si el otro fichero usase los
        # mismos macros, excluirlo no cambiaria nada y el vector no probaria
        # el filtro, sino que probaria que el fixture es identico.
        fh.write(EMITE_COB.replace(
            "PACKET3_CB_ALPHA(1) |\n                PACKET3_CB_BETA(q) |\n"
            "                PACKET3_CB_GAMMA(0)",
            "PACKET3_CB_DELTA(2)"))
    esc4 = campos_escritos(d4, {"PACKET3_CB"}, solo_ficheros=["gfx_v8_0.c"])
    chk("cobertura: separa por fichero de emision",
        list(esc4.get("PACKET3_CB", {})) == ["gfx_v8_0.c"],
        str(list(esc4.get("PACKET3_CB", {}))))
    chk("cobertura: los macros del payload se agrupan en su dword",
        esc4["PACKET3_CB"]["gfx_v8_0.c"][1] == {"alpha", "beta", "gamma"},
        str(esc4["PACKET3_CB"]))
    chk("cobertura: el dword sin macros no inventa una entrada",
        2 not in esc4["PACKET3_CB"]["gfx_v8_0.c"], str(esc4["PACKET3_CB"]))

    cab4 = {"PACKET3_CB": {"total": 3, "payload": 2,
                           "campos": ["CONTROL", "PAYLOAD [31:0]"], "donde": []}}
    decl6 = [{"PACKET3_CB": ["CONTROL[31:0]  (alpha[0] | beta[7:1])", "dword[2]"]}]
    f4 = contraste_cobertura(decl6, cab4, esc4)
    campos4 = sorted(f["campo"] for f in f4)
    chk("cobertura: ve el campo AUSENTE (gamma)",
        campos4 == ["GAMMA"], str(campos4))
    chk("cobertura: no acusa a los campos que si estan",
        "ALPHA" not in campos4 and "BETA" not in campos4, str(campos4))
    chk("cobertura: un nombre SIN guion bajo cuenta como declarado",
        "ALPHA" not in [f["campo"] for f in contraste_cobertura(
            [{"PACKET3_CB": ["CONTROL[31:0]  (alpha[0])"]}], cab4, esc4)],
        str([f["campo"] for f in contraste_cobertura(
            [{"PACKET3_CB": ["CONTROL[31:0]  (alpha[0])"]}], cab4, esc4)]))

    chk("cobertura: el alcance excluye otras generaciones y las nombra",
        campos_escritos(d4, {"PACKET3_CB"},
                        solo_ficheros=["gfx_v8_0.c"]) !=
        campos_escritos(d4, {"PACKET3_CB"}, solo_ficheros=[]),
        "el filtro debe cambiar el resultado: %s vs %s"
        % (campos_escritos(d4, {"PACKET3_CB"}, solo_ficheros=["gfx_v8_0.c"]),
           campos_escritos(d4, {"PACKET3_CB"}, solo_ficheros=[])))
    chk("cobertura: un filtro que no casa con nada se ve, no se disfraza de limpio",
        campos_escritos(d4, {"PACKET3_CB"}, solo_ficheros=[None]) == {},
        "un filtro mal escrito devuelve vacio y eso parece 'no hay nada'")
    txtc = formatear_cob(f4, "gfx_v8_0.c", ["gfx_v9_0.c"])
    chk("la salida de cobertura declara el alcance y los excluidos",
        "ALCANCE" in txtc and "gfx_v9_0.c" in txtc)
    chk("la salida de cobertura dice que no rompe el framing",
        "no falla" in txtc)

    # --- ORACULO DEL RANGO DE OPCODE -------------------------------------
    chk("opcode: el maximo del opcode es 0xFF, porque el campo tiene 8 bits",
        OPCODE_MAX == 0xFF)
    chk("opcode: el opcode vive en los bits 15:8, no en los bits 0-9",
        OPCODE_SHIFT == 8 and CAMPO_OPCODE_EN_CABECERA == "bits 15:8")
    dtc = tempfile.mkdtemp(prefix="layoutcross-opcode-")
    with open(os.path.join(dtc, "tab.py"), "w") as fh:
        fh.write("def opcode_table():\n"
                 "    return {0xA0: ('PACKET3_SET_RESOURCES', 'vid.h'),\n"
                 "            0x2C00: ('PACKET3_SET_SH_REG_START', 'vid.h'),\n"
                 "            0xC400: ('PACKET3_SET_UCONFIG_REG_END', 'vid.h')}\n")
    rc_ = contrastar_rango_opcode([{"ruta": os.path.join(dtc, "tab.py"),
                                    "error": None,
                                    "mod": cargar_modulo(os.path.join(dtc, "tab.py"))}])
    fo = list(rc_.values())[0]
    # La cota correcta: 0x100 NO puede ser opcode (8 bits), pero con la cota
    # antigua de 0x3FF salia OK. Este vector es el que habria atrapado el
    # error de las 0x3FF.
    with open(os.path.join(dtc, "tab2.py"), "w") as fh:
        fh.write("def opcode_table():\n"
                 "    return {0x100: ('PACKET3_IMPOSIBLE', 'vid.h'),\n"
                 "            0xFF: ('PACKET3_ULTIMO', 'vid.h')}\n")
    rc2 = contrastar_rango_opcode([{"ruta": os.path.join(dtc, "tab2.py"),
                                    "error": None,
                                    "mod": cargar_modulo(os.path.join(dtc, "tab2.py"))}])
    fo2 = list(rc2.values())[0]
    chk("opcode: 0x100 NO puede ser opcode con una cota de 8 bits",
        [f for f in fo2 if f[0] == 0x100][0][2] == "OPCODE_FUERA_DE_RANGO")
    chk("opcode: 0xFF, el ultimo representable, da OK",
        [f for f in fo2 if f[0] == 0xFF][0][2] == "OK")
    chk("opcode: 0x2C00 no puede ser opcode y sale OPCODE_FUERA_DE_RANGO",
        [f for f in fo if f[0] == 0x2C00][0][2] == "OPCODE_FUERA_DE_RANGO")
    chk("opcode: un opcode de rango real da OK",
        [f for f in fo if f[0] == 0xA0][0][2] == "OK")
    chk("opcode: 0xC400 (14 bits) tambien esta fuera, no solo 0x2C00",
        [f for f in fo if f[0] == 0xC400][0][2] == "OPCODE_FUERA_DE_RANGO")
    chk("opcode: una herramienta sin opcode_table no aparece, y no cuenta como 0",
        contrastar_rango_opcode([{"ruta": "x", "error": None, "mod": None}]) == {})
    chk("opcode: la salida explica que no es una discrepancia entre fuentes",
        "no compara dos fuentes" in formatear_opcode(
            [{"valor": "0x2C00", "nombre": "P", "veredicto": "OPCODE_FUERA_DE_RANGO"}]))

    print()
    if fallos:
        print("SELFTEST FALLIDO: %d de 10 grupos" % len(fallos))
        return 1
    print("SELFTEST OK: %d vectores" % len(_vistos))
    return 0


# ------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser(
        description="contraste cruzado de layouts PM4 declarados vs el corpus")
    ap.add_argument("--selftest", action="store_true",
                    help="vectores hermeticos, no leen el corpus")
    ap.add_argument("--corpus", default=CORPUS,
                    help="directorio de cabeceras y .c del kernel")
    ap.add_argument("--fuente", action="append", default=[],
                    help="modulo .py adicional que declare layouts")
    ap.add_argument("--json", action="store_true",
                    help="salida estructurada; rc=0 aunque haya discrepancias")
    ap.add_argument("--solo", action="store_true",
                    help="NO descubre declarantes: mide solo los --fuente. Es lo "
                         "que permite medir una declaracion CANDIDATA sin tocar "
                         "la viva, que es como se valida un contrato de "
                         "reparacion antes de proponerlo.")
    ap.add_argument("--generacion", default=None,
                    help="fichero .c de la generacion objetivo para la tabla de "
                         "cobertura (por defecto %s)" % GENERACION_OBJETIVO)
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    # Con --solo no se descubre NADA. Si se descubriera y ademas se anadiera
    # un --fuente, las dos declaraciones del mismo opcode estarian en la
    # poblacion y ganaria la primera: el candidato se mediria contra el vivo y
    # el resultado no diria nada del candidato.
    declarantes = [] if args.solo else descubrir_declarantes()
    if args.fuente or args.solo:
        for r in (args.fuente or []):
            try:
                mod_f = cargar_modulo(r)
            except Exception as exc:           # noqa: BLE001
                declarantes.append({"ruta": r, "layouts": None, "mod": None,
                                    "error": "%s: %s" % (type(exc).__name__, exc)})
                continue
            declarantes.append({"ruta": r, "mod": mod_f,
                                "layouts": {"MANUAL":
                                            getattr(mod_f, "DOC_LAYOUTS", {})},
                                "error": None})

    tablas = []
    if not args.json:
        print("declarantes localizados:")
    for d in declarantes:
        if d["error"]:
            if not args.json:
                print("  ! %s -> %s" % (os.path.basename(d["ruta"]), d["error"]))
            continue
        for a, t in d["layouts"].items():
            if not args.json:
                print("  %-28s %-14s %d paquetes"
                      % (os.path.basename(d["ruta"]), a, len(t)))
            tablas.append(t)

    if not tablas:
        if args.json:
            print(json.dumps({"instrumento": "layoutcross", "VERSION": VERSION,
                              "filas": [], "cuentas": {"declaraciones": 0},
                              "declarantes": []}, ensure_ascii=False))
            return 0
        print()
        print("ninguna herramienta declara layouts: no hay nada que contrastar.")
        return 2

    cab = oraculo_cabecera(args.corpus)
    emi = oraculo_emision(args.corpus)
    ops = set()
    for t in tablas:
        ops |= set(t)
    bits = oraculo_bits(args.corpus, ops)
    alcance_cob = args.generacion or GENERACION_OBJETIVO
    # `args.generacion` llega None si no se paso el flag. Filtrar por [None]
    # no casa con ningun fichero y devuelve una tabla vacia que parece limpia:
    # un filtro mal escrito se disfraza de "no hay nada que ver".
    escritos = campos_escritos(args.corpus, ops, solo_ficheros=[alcance_cob])
    escritos_todo = campos_escritos(args.corpus, ops, solo_ficheros=[])
    excluidos = sorted({f for o in escritos_todo for f in escritos_todo[o]
                         if f != alcance_cob})
    filas = contrastar(tablas, cab, emi)
    kfd = campos_kfd()
    filas_bits = contrastar_bits(tablas, cab, bits, kfd)
    filas_cob = contraste_cobertura(tablas, cab, escritos)
    rangos_op = contrastar_rango_opcode(declarantes)
    filas_opcode = [{"ruta": r, "valor": "0x%04X" % v, "nombre": nom,
                     "veredicto": ver}
                    for r, fs in sorted(rangos_op.items()) for v, nom, ver in fs]

    # `--json` sale con 0 SIEMPRE, y el motivo es concreto: el codigo 1
    # significa "hay discrepancia", y una discrepancia conocida y registrada
    # NO es un fallo del instrumento. Si --json devolviera 1, cualquier puerta
    # que lo consumiera leeria "error de ejecucion" donde solo hay una medida
    # que leer, y la mediria como instrumento roto en vez de como hallazgo.
    if args.json:
        print(json.dumps({
            "instrumento": "layoutcross",
            "VERSION": VERSION,
            "unidades": {"herr": UNIDAD_PAYLOAD, "cab": UNIDAD_PAYLOAD,
                         "emi": UNIDAD_PAYLOAD, "total": UNIDAD_TOTAL,
                         "anchura": ANCHURA_NO_DETERMINABLE},
            "declarantes": sorted(os.path.basename(d["ruta"])
                                  for d in declarantes if not d["error"]),
            "filas": filas,
            "filas_bits": filas_bits,
            "filas_cob": filas_cob,
            "filas_opcode": filas_opcode,
            "cuentas": {
                "declaraciones": len(filas),
                "ok": sum(1 for f in filas if f["veredicto"] == "OK"),
                "discrepa": sum(1 for f in filas if f["veredicto"] == "DISCREPA"),
                "sin_oraculo": sum(1 for f in filas
                                   if f["veredicto"] == "SIN_ORACULO"),
                "nombres_no_comparables": sum(
                    1 for f in filas if f["veredicto"] == "NOMBRES_NO_COMPARABLES"),
                "con_oraculo_cabecera": sum(1 for f in filas if f["cab_payload"]),
                "afirmaciones_de_bits": len(filas_bits),
                "campos_escritos_no_declarados": len(filas_cob),
            },
            "cuentas_bits": _cuenta(filas_bits),
            "cuentas_cob": _cuenta(filas_cob),
            "cuentas_opcode": _cuenta(filas_opcode),
            "alcance_cob": alcance_cob,
            "excluidos_cob": excluidos,
        }, ensure_ascii=False))
        return 0

    print()
    print(formatear(filas))
    print()
    print(formatear_bits(filas_bits))
    print()
    print(formatear_cob(filas_cob, alcance_cob, excluidos))
    print()
    if filas_opcode:
        print(formatear_opcode(filas_opcode))
        print()

    if any(f["veredicto"] == "DISCREPA" for f in filas):
        return 1
    if any(f["veredicto"] in ("DISCREPA", "CAMPO_INVENTADO")
           for f in filas_bits):
        return 1
    if filas_cob:
        return 1
    if any(f["veredicto"] == "OPCODE_FUERA_DE_RANGO" for f in filas_opcode):
        return 1
    if all(f["veredicto"] == "SIN_ORACULO" for f in filas):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
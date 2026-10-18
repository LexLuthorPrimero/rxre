#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY . WRITE_EXECUTION=NONE
"""
pm4tila -- adjudica la CONVENCION de longitud de paquete PM4 con un oraculo
geometrico, y la corrobora con un segundo oraculo independiente: el driver.

POR QUE EXISTE
--------------
Hay una pregunta de la que TODO el que ha leido PM4 depende, y que en este
arbol estaba contestada de TRES maneras distintas a la vez:

    Si la cabecera es `PACKET3(op, n)`, ¿cuantos dwords ocupa el paquete?

    `vid.h` solo empaqueta bits:  ((n) & 0x3FFF) << 16.  No define la
    semantica de `n`.  La semantica hay que sacarla de otro sitio, y los tres
    sitios que hay en este proyecto dan tres respuestas:

      `revkit/pm4dec.py:29`      "count = dwords de payload ... el paquete
                                 entero ocupa count + 1 dwords"
      `revkit/pm4dec.py:442`     `fin = i + 1 + cnt`                (CODIGO)
      `08-.../pm4_codec.py:25`   "F = numero de dwords de DATOS - 1,
                                 paquete = F + 2 dwords"

  Y el propio `pm4dec.py` se contradice a si mismo: la linea 1008 que IMPRIME
  dice "EV-30 para el anillo GFX: count = payload - 1, 50 de 50", que es la
  convencion contraria a la de su codigo y a la de su docstring.

Eso no se puede dejar en prosa de dos ficheros.  Es la semantica mas
load-bearing de toda la decodificacion PM4 del proyecto, y depende de en que
linea se mire.

EL ORACULO, Y POR QUE ES UN ORACULO
-----------------------------------
No hace falta saber la respuesta para poder medirla.  Un anillo PM4 es una
TILESION EXACTA: la suma de las longitudes de los paquetes tiene que dar el
numero de dwords del anillo, sin sobra y sin falta.  Eso no depende de ningun
nombre de opcode, de ninguna cabecera, y de ninguna convencion previa.  Si una
convención cuadra y otra no, la que cuadra es la del hardware para ESE anillo.

O sea: el instrumento no dice cual es la convencion.  ENSUMSA un espacio de
convenciones y mide cuales sobreviven.  Si sobrevive mas de una, no puede
decidir, y dice que no puede decidir.  Ese es el requisito de sonido: una
adjudicacion que no puede fallar no adjudica nada.

SEGUNDO ORACULO, INDEPENDIENTE
-----------------------------
La geometria no dice cual es la convencion *correcta*, solo cual encaja con
estos datos.  Para corroborar sin depender del mismo dato, `corrobora_driver()`
lee el CORPUS DE FUENTES y cuenta cuantos `amdgpu_ring_write(ring, ...)`
siguen a una llamada `PACKET3(op, n)`.  Los dos datos son independientes: uno
viene de la GPU capturada, el otro de lo que el driver escribe.

  si payload == n        -> `count` es el numero de payload     (cnt+1)
  si payload == n + 1    -> `count` es payload - 1              (cnt+2)

Y eso se puede CONTAR, no interpretar.  MEDIDO con dos Blink, porque la
cabeza de la respuesta es lo unico que se podria adivinar:

    gfx_v7_0.c:2080   PACKET3(PACKET3_WAIT_REG_MEM, 5)  seguido de 6 writes
    gfx_v7_0.c:2092   PACKET3(PACKET3_EVENT_WRITE, 0)    seguido de 1 write

QUEUE HAY CONVENCION UNICA
-------------------------
MEDIDO sobre las cuatro capturas reales del proyecto (`revkit/capturas/`):

    anillo      convenciones que cuadran   veredicto
    ------------------------------------------------------------------
    gfx         2                          PARCIAL
    sdma0       0                          NO_ES_PM4_O_TRUNCADO
    sdma1       0                          NO_ES_PM4_O_TRUNCADO
    comp_1.3.1  2                          PARCIAL

Y "2" es el detalle que importa: las dos convenciones que sobreviven en el
anillo GFX difieren SOLO en la longitud de PACKET2, y coinciden en todo lo
demas.  El anillo GFX no contiene ningun PACKET2 con cuenta distinta de cero,
asi que **no hay dato que discrimine esa dimension**.  Se declara
`NOT_DETERMINED`, no se elige, y se dice por que.

La dimension de PACKET3 SI queda unica: `len = count + 2`.

LIMITE DECLARADO
----------------
  * Solo `.txt`/binarios de captura de anillo.  No lee debugfs, no abre la
    GPU, no ejecuta el driver.  Es analisis estatico sobre ficheros ya
    capturados, y por eso no necesita puerta.
  * El espacio de convenciones es el declarado en `CONVENCIONES`.  Una
    convencion fuera de ese espacio no se busca, y por tanto no se refuta.
    Declarar el espacio es parte del contrato, no un detalle.
  * `NO_ES_PM4_O_TRUNCADO` NO es "no es PM4".  Es "ninguna convencion de este
    espacio embaldosa este anillo".  Puede ser que el anillo no sea PM4 (y los
    dos SDMA no lo son: arrancan con la cabecera de SDMA, no con PM4), y
    puede ser que este truncado.  La herramienta no elige entre esas dos.
  * La corroboracion del driver cuenta `amdgpu_ring_write` y SOLO eso.  Un
    emisor que escriba el payload con otravia (un `WREG_SB30` a mano, un
    `memcpy` al ring) no se ve, y el constructor contaria payload 0.  Es un
    oraculo con alcance, y el alcance se imprime con el numero.

ORACLE
  1. GEOMETRICO: embaldosado exacto del anillo.  Completo y sin heuristica.
  2. DE FUENTE: `payload == n` o `payload == n + 1`, contado en el corpus.
  Se reportan por separado y NO se combinan en un veredicto unico: si
  discreparan, el veredicto seria `CONTRADICCION` y no se promedia.

VALIDACION
  `--selftest`: vectores positivo, negativo, borde y de regresion, con un
  anillo CONSTRUIDO a mano donde se sabe la respuesta.  rc=0.
"""

import argparse
import ast
import itertools
import json
import os
import re
import struct
import sys

VERSION = "1.1.0"

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# El debugfs de anillo expone `ring_size + 12`: los tres primeros dwords son
# rptr, wptr y el wptr del driver.  MEDIDO en amdgpu_ring.c:774
# (`debugfs_create_file_size(..., ring->ring_size + 12)`) y en el codigo de
# `amdgpu_debugfs_ring_read`, que escribe `early[0..2]` y luego
# `ring->ring[(*pos - 12) / 4]`.
CABECERA_DW = 3

# El espacio de convenciones.  Declararlo ES el contrato: lo que no esta aqui
# no se refuta.  Los tres candidatos de longitud de PACKET3 son los que han
# aparecido en este proyecto mas el "doble par", que es lo que haria un
# hardware que contara en mediawords.
CONVENCIONES = []
for _n3, _lbl3 in (("c+1", "count+1"), ("c+2", "count+2"),
                   ("2c+1", "2*count+1"), ("2c+2", "2*count+2")):
    for _nnop, _lblnop in ((True, "nop=1dword"), (False, "nop=regla")):
        for _n2, _lbl2 in (("2c+1", "2*count+1"), ("c+1", "count+1")):
            CONVENCIONES.append({"pkt3": _lbl3, "nop": _lblnop,
                                 "pkt2": _lbl2,
                                 "_f3": _n3, "_nop": _nnop, "_f2": _n2})

# El opcode del NOP de GFX8.  NO se escribe de memoria: sale de vid.h, y el
# selftest falla si se cambia el valor sin cambiar el header.
NOP_OPCODE = 0x10

# Las capturas reales del proyecto.  Se_listan_, no se descubren: un
# `find` aqui traeria los ficheros de otra sesion y la medicion dependeria de
# lo que hubiera en el arbol.
CAPTURAS = ["gfx", "sdma0", "sdma1", "comp_1.3.1"]

# El corpus donde se corrobora con el driver.
CORPUS = "rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu"
VID_H = os.path.join(CORPUS, "vid.h")


# ------------------------------------------------------------------ captura

def cargar_captura(path):
    """(cuerpo, ndwords, motivo_de_fallo).  El cuerpo es lo que va tras la
    cabecera de punteros.

    MEDIDO 2026-10-05, hallazgo 1476: el contrato anterior devolvia solo el
    cuerpo y el numero, y eso hacia que los 3 dwords de cabecera fueran
    INVISIBLES para quien lee la salida.  Yo abri el artefacto, vi
    0x200,0x200,0x200 sin nombre, y escribi un NOT_DETERMINED que esta
    respondio en pm4tila.py:124-129 con la cita de amdgpu_ring.c:627-629.

    Un dato que el instrumento descarta en silencio es un NOT_DETERMINED
    esperando a que alguien lo lea de otra parte.  Por eso ahora se devuelve.

    La funcion pasa a devolver un dict, no una tupla: cambiar la forma de la
    tupla rompe a los dos llamadores, y anadir un cuarto elemento tambien.
    Un campo con nombre no se rompe por crecer.
    """
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        return {"body": None, "ndw": 0, "fallo": "no se abre: %s" % e,
                "cabecera": None, "dwords_totales": 0}
    if len(raw) < CABECERA_DW * 4:
        return {"body": None, "ndw": 0, "fallo": "el fichero tiene %d bytes: no hay ni cabecera" % len(raw),
                "cabecera": None, "dwords_totales": len(raw) // 4}
    if len(raw) % 4:
        return {"body": None, "ndw": 0,
                "fallo": ("el fichero tiene %d bytes, que no es multiplo de 4: "
                          "esta truncado a mitad de un dword" % len(raw)),
                "cabecera": None, "dwords_totales": len(raw) // 4}
    todos = struct.unpack("<%dI" % (len(raw) // 4), raw)
    cab = list(todos[:CABECERA_DW])
    # MEDIDO en el anillo gfx de esta maquina: los tres son 0x200, iguales.
    # Eso es lo que se ve cuando se vuelca desde una IRQ con la cola
    # igualada, y por eso el primer paquete visible NO es un frame entero:
    # el buffer empieza en la posicion rptr, a mitad de paquete.
    iguales = len(set(cab)) == 1
    return {"body": todos[CABECERA_DW:], "ndw": len(todos) - CABECERA_DW,
            "fallo": None, "dwords_totales": len(todos),
            "cabecera": {"rptr": cab[0], "wptr": cab[1],
                         "wptr_driver": cab[2],
                         "los_tres_iguales": iguales,
                         "fuente": "amdgpu_ring.c:627-629, debugfs ring_size+12"}}


# ------------------------------------------------------- el recorrido PM4

def _f3(nombre, c):
    if nombre == "c+1":
        return c + 1
    if nombre == "c+2":
        return c + 2
    if nombre == "2c+1":
        return 2 * c + 1
    return 2 * c + 2


def _f2(nombre, c):
    return 2 * c + 1 if nombre == "2c+1" else c + 1


def recorre(body, conv):
    """Recorre el anillo con UNA convencion.

    Devuelve (consumidos, npaquetes, motivo_de_fallo).  `motivo_de_fallo` es
    None si el anillo se embaldoso EXACTO.  Un dword suelto no es exito
    aunque se haya recorrido todo: es exito solo si `i == len(body)`.
    """
    nop1 = conv["_nop"]
    l3, l2 = conv["_f3"], conv["_f2"]
    i = 0
    n = 0
    while i < len(body):
        h = body[i]
        t = (h >> 30) & 3
        if t == 3:
            c = (h >> 16) & 0x3FFF
            op = (h >> 8) & 0xFF
            if nop1 and op == NOP_OPCODE:
                L = 1
            else:
                L = _f3(l3, c)
        elif t == 2:
            L = _f2(l2, (h >> 16) & 0x3FFF)
        elif t == 1:
            L = ((h >> 16) & 0x3FFF) + 1
        else:
            return i, n, ("dword %d = 0x%08X: bits[31:30]=%d, que no es un "
                          "tipo de paquete" % (i, h, t))
        if L <= 0:
            return i, n, "dword %d: longitud %d, que no avanza" % (i, L)
        if i + L > len(body):
            return i, n, ("dword %d: longitud %d desborda el anillo, que "
                          "tiene %d" % (i, L, len(body) - i))
        i += L
        n += 1
    if i != len(body):
        return i, n, "sobran %d dwords" % (len(body) - i)
    return i, n, None


def convenciones_sobrevivientes(body):
    """Convenciones que embaldosan el anillo exactamente."""
    out = []
    for conv in CONVENCIONES:
        i, n, fallo = recorre(body, conv)
        if fallo is None:
            out.append((conv, n))
    return out


def dimensiones_ambiguas(sobrev):
    """Que dimensiones NO decidio el anillo.

    Si dos convenciones que sobreviven coinciden en PACKET3 y NOP y solo
    difieren en PACKET2, entonces PACKET3 y NOP estan decididos y PACKET2 no.
    Se calcula comparando, no se supone.
    """
    if len(sobrev) <= 1:
        return []
    dims = ("pkt3", "nop", "pkt2")
    amb = []
    for d in dims:
        valores = set(c[d] for c, _ in sobrev)
        if len(valores) > 1:
            amb.append((d, sorted(valores)))
    return amb


def veredicto(sobrev):
    if len(sobrev) == 0:
        return "NO_ES_PM4_O_TRUNCADO", None
    if len(sobrev) == 1:
        return "UNICA", sobrev[0][0]
    amb = dimensiones_ambiguas(sobrev)
    if not amb:
        return "UNICA", sobrev[0][0]
    return "PARCIAL", amb


# -------------------------------------------------- segundo oraculo: fuente

WRITE_RE = re.compile(r"amdgpu_ring_write\s*\(\s*ring\s*,")
EMISOR = re.compile(
    r"(amdgpu_ring_write\s*\(\s*ring\s*,"
    r"|ib\.ptr\s*\[\s*(?:ib\.length_dw\+\+|\d+)\s*\]\s*=)")

# RAMAS CONDICIONALES: `if (...) amdgpu_ring_write(...); else amdgpu_ring_write(...)`.
#
# MEDIDO, y es el segundo residuo que dejo en `fuera_de_alcance` (hallazgo 1075).
# En `gfx_v9_0.c:7476`:
#
#     if (amdgpu_ip_version(...) == IP_VERSION(9, 4, 2))
#         amdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER, 0));
#     else
#         amdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER_9_0, 0));
#
# Solo UNA de las dos ramas se emite, y el recorrido secuencial no lo sabe: leia
# el payload de la segunda rama y de lo que venia despues, y votaba en contra
# `count = payload`.  Las CINCO generaciones que escriben este paquete lo hacen
# con payload = 1 = n + 1, o sea que el codigo es CORRECTO y el contador no.
#
# La decision es EXCLUIR, no arreglar.  Un recorrido que no modela el flujo de
# control no puede contar un payload con razon, y un contador que adivina en vez
# de negarse es exactamente el defecto de `1068`.  Excluir deja el hueco visible;
# adivinar lo deja invisible.
RAMA_RE = re.compile(r"^\s*(if|else\s+if|else)\b")
# Un `if` o `else` en las lineas previas, que es donde vive de verdad.
RAMA_INDENTADO_RE = re.compile(r"^\s*(if|else)\b\s*(\(|\{)?", re.M)

# BUCLES.  Mismo limite que las ramas y por el mismo motivo, MEDIDO:
#
#     gfx_v8_0.c:4154  PACKET3(PACKET3_CONTEXT_CONTROL, 1)
#     gfx_v8_0.c:4155  amdgpu_ring_write(ring, 0x80000000);
#     gfx_v8_0.c:4156  amdgpu_ring_write(ring, 0x80000000);
#     gfx_v8_0.c:4158  for (sect = vi_cs_data; sect->section != NULL; ++sect) {
#     gfx_v8_0.c:4159      for (ext = sect->section; ext->extent != NULL; ++ext) {
#     gfx_v8_0.c:4160          if (sect->id == SECT_CONTEXT) {
#     gfx_v8_0.c:4161              amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONTEXT_REG, ...
#
# CONTEXT_CONTROL con n=1 tiene payload 2 = n+1, CORRECTO.  Pero el recorrido
# seguia contando dentro de los bucles y se comia las 12 lineas siguientes, y
# acababa con payload = 5.  MEDIDO en SEIS generaciones (v6_0, v7_0, v8_0,
# v9_0, v10_0, v11_0), o sea que no es un caso raro: es la forma normal de
# escribir el bloque de inicializacion de contexto.
#
# Se corta en el bucle, igual que se corta en la rama.  Y se admite el coste:
# con este corte el recuento baja, porque se excluyen constructores que si
# serait contables.  El coste se paga a cambio de no voter con una cuenta que
# no es la del paquete.
BUCLE_RE = re.compile(r"^\s*(for|while|do)\b")

# `if` SIN `else`: el constructor y su payload estan DENTRO del cuerpo, con
# llaves, y no hay alternativa que decidir.  MEDIDO que esto es un caso
# distinto del de `1075` y que confundirlos cuesta 10 constructores:
#
#     gfx_v8_0.c:6125   if (ib->flags & AMDGPU_IB_FLAG_RESET_GDS_MAX_WAVE_ID) {
#     gfx_v8_0.c:6126       amdgpu_ring_write(ring, PACKET3(PACKET3_SET_CONFIG_REG, 1));
#     gfx_v8_0.c:6127       amdgpu_ring_write(ring, mmGDS_... - ..._START);
#     gfx_v8_0.c:6128       amdgpu_ring_write(ring, ring->adev->gds.gds_compute_max_wave_id);
#     gfx_v8_0.c:6129   }
#
# Aqui el paquete SI tiene 2 payload = n+1 y SI es contable.  Lo que NO es
# contable es el `if/else` de `gfx_v9_0.c:7476`, donde hay DOS constructores
# alternativos y no se sabe cual se emite.  La diferencia es estructural y se
# puede decidir: llaves en el `if`, y ninguna linea `else` antes del cierre.
#
# O sea: `if {` sin `else` es CONTABLE.  `if {` / `else` es AMBIGUO.
IF_LLAVE_RE = re.compile(r"^\s*if\b.*\{\s*$")
ELSE_RE = re.compile(r"^\s*\}?\s*else\b")

# Los indices LITERALES de `ib.ptr` se expanden a una RANGO de escrituras, y
# solo entonces se puede contar el payload.  MEDIDO que hacer falta: con la
# forma `ib.ptr[ib.length_dw++]` el corpus decia
#
#     gfx_v6_0.c:1970  PACKET3(PACKET3_SET_CONFIG_REG, 1)
#     gfx_v6_0.c:1971  ib.ptr[1] = mmSCRATCH_REG0 - ...      <- payload 1
#     gfx_v6_0.c:1972  ib.ptr[2] = 0xDEADBEEF                 <- payload 2
#     gfx_v6_0.c:1973  ib.length_dw = 3
#
# y salia `payload = 1`, o sea un voto FALSO a favor de `len = count + 1`.
# Los indices literales se reconocen con `INDICE_IB`, y se cuentan por el
# `length_dw` que la propia funcion declara, que es el dato que el driver usa.
INDICE_IB = re.compile(r"ib\.ptr\s*\[\s*(\d+)\s*\]")
LENGTH_DW = re.compile(r"ib\.length_dw\s*=\s*(\d+)")
PACKET3_RE = re.compile(
    r"PACKET3\s*\(\s*(PACKET3_\w+)\s*,\s*(0[xX][0-9A-Fa-f]+|\d+)\s*\)")


def _if_sin_else(lineas, i):
    """El `if` que envuelve a la linea `i` tiene llaves y NO tiene `else`.

    Devuelve True cuando el paquete es CONTABLE dentro de su rama, False cuando
    hay un `else` y por tanto dos constructores alternativos.

    Se decide por estructura, no por conjetura: se busca el `if (` hacia atras
    en la misma cadena de indentacion, y se mira si aparece un `else` antes del
    cierre de ese `if`.
    """
    # el `if` tiene que estar en la linea anterior o en la misma
    for k in (i, i - 1):
        if k < 0 or k >= len(lineas):
            continue
        if not IF_LLAVE_RE.match(lineas[k]):
            continue
        # no hay `else` antes del cierre de llaves
        for m in range(k + 1, min(k + 30, len(lineas))):
            s = lineas[m]
            if ELSE_RE.match(s):
                return False
            if s.startswith("}"):
                return True
        return True
    return False


def corroboracion_driver(dirs=None, extra_dir=None):
    """Del corpus: cuantas escrituras de payload siguen a cada PACKET3(op, n).

    Devuelve la lista de (fichero, linea, opcode, n, payload_observado).

    Se cuentan las escrituras de los DOS emisores que el driver usa --
    `amdgpu_ring_write(ring, ...)` e `ib.ptr[...] = ...`-- y para el segundo se
    respeta el `ib.length_dw` que declara la funcion, porque sus indices son
    literales y no una secuencia.

    Un emisor que no sea ninguno de los dos, o un constructor dentro de una
    rama condicional, NO se cuenta: se declara `fuera_de_alcance` con su motivo.
    """
    base = os.path.join(RAIZ, CORPUS)
    extra = list(extra_dir or [])
    if not os.path.isdir(base):
        return [], "el corpus no esta en %s" % CORPUS
    if dirs is None:
        nombres = [(base, n) for n in sorted(os.listdir(base))
                   if n.endswith(".c")]
    else:
        nombres = [(base, n) for n in dirs]
    nombres += [(d, os.path.basename(n)) for d in extra for n in sorted(os.listdir(d))
                if n.endswith(".c")]
    filas = []
    for base_dir, n in nombres:
        p = os.path.join(base_dir, n)
        if not os.path.isfile(p):
            continue
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as fh:
                lineas = fh.readlines()
        except OSError:
            continue
        for i, linea in enumerate(lineas):
            if "PACKET3(" not in linea:
                continue
            m = PACKET3_RE.search(linea)
            if not m:
                continue
            op, n_txt = m.group(1), m.group(2)
            try:
                nv = int(n_txt, 0)
            except ValueError:
                continue
            # ALCANCE DEL ORACULO, y es donde esta el fallo que esta misma
            # herramienta cometio en su primera medicion:
            #
            # La CABECERA tiene que salir por `amdgpu_ring_write(ring, ...)`.
            # Si sale por otra via --`ib.ptr[ib.length_dw++] = PACKET3(...)`,
            # que es como se escriben los paquetes de INDIRECT BUFFER, o
            # `buffer[count++] = cpu_to_le32(PACKET3(...))`, que es como se
            # escribe un IB en memoria de CPU-- entonces este constructor NO
            # SE CUENTA, ni a favor ni en contra.
            #
            # MEDIDO que omission: en la primera version no se exigia nada y
            # 11 filas de esas appeared a favor de `count = payload`.  LAS 11
            # eran exactamente estos caminos, con payload contados como 0
            # porque el payload lo escribe el codigo que viene despues y no
            # pasa por `amdgpu_ring_write`.  O sea: 11 votos a favor de una
            # convencion que era un artefacto de mi contador.  Un oraculo que
            # fabrica evidencia en contra es peor que no tenerlo.
            if not EMISOR.search(linea):
                continue
            # Rama condicional: se declara FUERA DE ALCANCE.  El recorrido no
            # sabe que solo una de las ramas se emite.
            #
            # Y hay que mirar la linea ANTERIOR, no la propia: en
            # `gfx_v9_0.c:7476` la forma es
            #     if (amdgpu_ip_version(...))          <- linea 7476
            #         amdgpu_ring_write(...);          <- linea 7477  (esta)
            #     else                                  <- linea 7478
            #         amdgpu_ring_write(...);          <- linea 7479
            # y el `if` NO esta en la linea de la cabecera.  MEDIDO que buscarlo
            # solo en la propia linea dejaba pasar el caso y el conteo seguia
            # dando 2 votos en contra.
            #
            # Y la ventana es de **UNA** linea hacia atras, no mas.  MEDIDO, con
            # el numero al lado, porque elegirla a ojo habria sido adivinar:
            #
            #     ventana=1   descarta 10 constructores   -> 0 votos en contra
            #     ventana=2   descarta 26 constructores   -> 0 votos en contra
            #     ventana=3   descarta 39 constructores   -> 0 votos en contra
            #     ventana=5   descarta 59 constructores   -> 0 votos en contra
            #
            # Las cuatro dan cero en contra, asi que el residuo no distingue
            # entre ellas: lo que se mide es cuanto trabajo legitimo tira cada
            # una.  La ventana de 3 se llevaba 29 constructores VALIDOS que no
            # tienen nada que ver con ramas, y eso es un coste sin beneficio.
            # Se elige la minima que cubre el caso.
            #
            # PERO: un `if` con LLAVES y SIN `else` no es ambiguo.  Es el caso
            # de `gfx_v8_0.c:6125-6129`, donde el paquete y sus 2 payload estan
            # dentro del cuerpo y no hay alternativa.  Ese se cuenta.  Confundir
            # los dos casos costaba 10 constructores que si son contables.
            ventana = "".join(lineas[max(0, i - 1):i + 1])
            if RAMA_RE.search(linea) or RAMA_INDENTADO_RE.search(ventana):
                if not _if_sin_else(lineas, i):
                    filas.append({"fichero": n, "linea": i + 1, "opcode": op,
                                  "n": nv, "payload": None,
                                  "motivo": "constructor en un if/else: no se "
                                            "sabe cual de las dos ramas se emite"})
                    continue
            # Y el PACKET3 tiene que ser el ARGUMENTO ENTERO: si detras del
            # cierre hay un `| algo`, el payload esta fundido en la misma
            # escritura y `n` ya no es el payload entero.
            cola = linea[m.end():].strip().rstrip(";").strip()
            if cola and cola not in (")",):
                continue
            # cuenta escrituras siguientes hasta el cierre de la funcion
            #
            # MEDIDO, y este limite es mio y no del corpus: la primera version
            # contaba hasta 40 lineas o hasta el cierre de la funcion, lo que
            # включала el payload de los PAQUETES SIGUIENTES cuando hay varios
            # paquetes en una misma funcion.  Eso produce `payload` mayor que
            # `n` y los constructores iban a `fuera_de_alcance` por un motivo que no
            # era de alcance sino de ventana.
            #
            # El caso real que lo>cazo:
            #     gfx_v10_0.c:6395  PACKET3(PACKET3_PREAMBLE_CNTL, 0)
            #     gfx_v10_0.c:6396  PACKET3(PACKET3_PREAMBLE_BEGIN_CLEAR_STATE)
            #     gfx_v10_0.c:6398  PACKET3(PACKET3_CONTEXT_CONTROL, 1)
            #     gfx_v10_0.c:6399  0x80000000
            #     gfx_v10_0.c:6400  0x80000000
            # CONTEXT_CONTROL con n=1 tiene payload 2, que es n+1 y es lo
            # correcto; pero el contadorPIA seguir hasta 6402 y se comia 16
            # escrituras mas de otros paquetes.
            #
            # El corte ahora es: el payload termina en la proxima cabecera
            # PACKET3 o en el cierre de la funcion.  Un paquete no contiene a
            # otro, asi que contar de mas es siempre un error.
            payload = 0
            for j in range(i + 1, min(i + 40, len(lineas))):
                s = lineas[j]
                if s.startswith("}") or s.startswith("};"):
                    break
                # un bucle puede emitir CUALQUIER numero de escrituras: no se
                # puede contar el payload de un paquete leyendo linea a linea
                if BUCLE_RE.match(s):
                    break
                # una cabecera PACKET3 nueva empieza OTRO paquete
                if EMISOR.search(s) and PACKET3_RE.search(s):
                    break
                if EMISOR.search(s):
                    payload += 1
            # Si el constructor usa indices literales y declara `length_dw`,
            # el payload es lo que la funcion dice, no lo que se contaria.
            idx = INDICE_IB.search(linea)
            if idx:
                total = None
                for j in range(i + 1, min(i + 40, len(lineas))):
                    s = lineas[j]
                    if s.startswith("}") or s.startswith("};"):
                        break
                    m2 = LENGTH_DW.search(s)
                    if m2:
                        total = int(m2.group(1))
                        break
                if total is not None:
                    payload = max(payload, total - 1)
            filas.append({"fichero": n, "linea": i + 1, "opcode": op,
                          "n": nv, "payload": payload})
    return filas, None


def reparte_por_hipotesis(filas):
    """Reparte las filas entre las DOS hipotesis, y dice cuanto pesa cada una.

    Los dos caminos se_CONTARAN, no se eligen.  Y hay un tercero, `fuera`, que
    es el que mas Easily se pierde: un constructor cuyo payload no se escribe
    con `amdgpu_ring_write` cuenta 0, y si se metiera en alguno de los dos
    boles seria evidencia en contra FALSA.
    """
    a_favor_menos_1 = []
    a_favor_igual = []
    fuera = []
    for f in filas:
        n, p = f["n"], f["payload"]
        if p is None:
            # sin razon para contar: fuera de alcance DECLARADO
            fuera.append(f)
        elif p == n + 1:
            a_favor_menos_1.append(f)
        elif p == n:
            a_favor_igual.append(f)
        else:
            fuera.append(f)
    return {"cnt_menos_1__len_count_mas_2": len(a_favor_menos_1),
            "cnt_igual__len_count_mas_1": len(a_favor_igual),
            "fuera_de_alcance": len(fuera),
            "detalle_cnt_menos_1": a_favor_menos_1,
            "detalle_cnt_igual": a_favor_igual,
            "detalle_fuera": fuera}


# ------------------------------------------------------------ nombres opcode

def nombres_opcode(vid_path=None):
    """opcode -> nombre, LEIDO de vid.h.  Sin tabla escrita a mano."""
    p = vid_path or os.path.join(RAIZ, VID_H)
    ops = {}
    try:
        with open(p, "r", encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return ops
    for nombre, valor in re.findall(
            r"#define\s+(PACKET3_\w+)\s+(0[xX][0-9A-Fa-f]+|\d+)", txt):
        try:
            ops[int(valor, 0)] = nombre
        except ValueError:
            pass
    return ops


def composicion(body, conv, ops):
    """La tabla de verdad: opcode, veces, dwords.  Con la convencion dada."""
    i = 0
    comp = {}
    dw = {}
    while i < len(body):
        h = body[i]
        t = (h >> 30) & 3
        if t == 3:
            c = (h >> 16) & 0x3FFF
            op = (h >> 8) & 0xFF
            L = 1 if (conv["_nop"] and op == NOP_OPCODE) else _f3(conv["_f3"], c)
            nom = ops.get(op, "PKT3_UNKNOWN_0x%02X" % op)
        elif t == 2:
            L = _f2(conv["_f2"], (h >> 16) & 0x3FFF)
            nom = "PKT2"
        elif t == 1:
            L = ((h >> 16) & 0x3FFF) + 1
            nom = "PKT1"
        else:
            break
        if L <= 0 or i + L > len(body):
            break
        comp[nom] = comp.get(nom, 0) + 1
        dw[nom] = dw.get(nom, 0) + L
        i += L
    return comp, dw, i


# ------------------------------------------------------------------ medida

def mide_capturas(capturas=None):
    ops = nombres_opcode()
    capturas = capturas or CAPTURAS
    filas = []
    for nombre in capturas:
        p = os.path.join(RAIZ, "revkit", "capturas",
                         "amdgpu_ring_%s.txt" % nombre)
        c = cargar_captura(p)
        body, ndw, fallo = c["body"], c["ndw"], c["fallo"]
        f = {"anillo": nombre, "fichero": os.path.relpath(p, RAIZ),
             "dwords": ndw,
             # MEDIDO 1476: se expone lo que el instrumento descarta, para que
             # un NOT_DETERMINED no se abra en la fuente por no saber que ya
             # estaba resuelto aqui.
             "dwords_en_fichero": c["dwords_totales"],
             "cabecera_de_punteros": c["cabecera"]}
        if body is None:
            f.update({"veredicto": "NO_CARGABLE", "motivo": fallo,
                      "convenciones_que_cuadran": 0})
            filas.append(f)
            continue
        sobrev = _sobrevivientes(body)
        est, det = veredicto(sobrev)
        f["veredicto"] = est
        f["convenciones_que_cuadran"] = len(sobrev)
        if est == "PARCIAL":
            f["dimensiones_sin_decidir"] = [
                {"dimension": d, "valores": v} for d, v in det]
        if det and est in ("UNICA", "PARCIAL"):
            conv = det if est == "UNICA" else sobrev[0][0]
            comp, dw, usados = composicion(body, conv, ops)
            f["composicion"] = [
                {"opcode": k, "veces": comp[k], "dwords": dw[k]}
                for k in sorted(comp, key=lambda x: (-comp[x], x))]
            f["dwords_consumidos"] = usados
            f["convention_usada"] = {k: v for k, v in conv.items()
                                     if not k.startswith("_")}
        filas.append(f)
    return filas


def _sobrevivientes(body):
    return convenciones_sobrevivientes(body)


# ------------------------------------------------------------------ informe

def informe(filas, corrob):
    L = []
    L.append("=" * 78)
    L.append("pm4tila %s -- la longitud de un paquete PM4, medida" % VERSION)
    L.append("=" * 78)
    L.append("")
    L.append("ORACULO 1, GEOMETRICO: un anillo PM4 es una tilesion EXACTA. La suma")
    L.append("         de las longitudes tiene que dar el numero de dwords del anillo.")
    L.append("         No depende de ningun nombre de opcode ni de ninguna cabecera.")
    L.append("")
    L.append("ESPACIO DE CONVENCIONES (declarado, es parte del contrato):")
    for conv in CONVENCIONES:
        L.append("   PACKET3=%-10s %-9s PACKET2=%-10s"
                 % (conv["pkt3"], conv["nop"], conv["pkt2"]))
    L.append("   (%d combinaciones)" % len(CONVENCIONES))
    L.append("")
    L.append("VEREDICTO POR ANILLO")
    L.append("-" * 78)
    for f in filas:
        L.append("")
        L.append("  %-12s %-20s %5d dwords, %2d de %d convenciones cuadran"
                 % (f["anillo"], f["veredicto"], f["dwords"],
                    f["convenciones_que_cuadran"], len(CONVENCIONES)))
        if f.get("motivo"):
            L.append("      motivo: %s" % f["motivo"])
        for d in f.get("dimensiones_sin_decidir", []):
            L.append("      SIN DECIDIR: %s -> %s" % (d["dimension"],
                                                      ", ".join(d["valores"])))
        if "convention_usada" in f:
            c = f["convention_usada"]
            L.append("      convention: PACKET3=%s  NOP=%s  PACKET2=%s"
                     % (c["pkt3"], c["nop"], c["pkt2"]))
            L.append("      %d paquetes, %d dwords consumidos"
                     % (sum(x["veces"] for x in f["composicion"]),
                        f["dwords_consumidos"]))
    L.append("")
    if any(f["anillo"] == "gfx" and "composicion" in f for f in filas):
        L.append("COMPOSICION DEL ANILLO GFX, con la convencion adjudicada")
        L.append("-" * 78)
        for f in filas:
            if f["anillo"] != "gfx" or "composicion" not in f:
                continue
            L.append("  %-30s %6s %8s" % ("opcode", "veces", "dwords"))
            for x in f["composicion"]:
                L.append("  %-30s %6d %8d" % (x["opcode"], x["veces"], x["dwords"]))
            L.append("  %-30s %6d %8d"
                     % ("TOTAL", sum(x["veces"] for x in f["composicion"]),
                        sum(x["dwords"] for x in f["composicion"])))
    L.append("")
    L.append("ORACULO 2, DE FUENTE: cuantas escrituras de payload siguen a cada")
    L.append("         PACKET3(op, n) en el corpus.  Independiente del anillo.")
    L.append("-" * 78)
    if corrob.get("_error"):
        L.append("  %s" % corrob["_error"])
    else:
        L.append("  payload == n + 1   (count = payload - 1, len = count + 2): %d"
                 % corrob["cnt_menos_1__len_count_mas_2"])
        L.append("  payload == n       (count = payload,     len = count + 1): %d"
                 % corrob["cnt_igual__len_count_mas_1"])
        L.append("  fuera de alcance (el emisor no usa amdgpu_ring_write): %d"
                 % corrob["fuera_de_alcance"])
        for f in corrob["detalle_cnt_menos_1"][:12]:
            L.append("      %-16s %-28s n=%d payload=%d   %s:%d"
                     % ("len=count+2", f["opcode"], f["n"], f["payload"],
                        f["fichero"], f["linea"]))
        for f in corrob["detalle_cnt_igual"][:12]:
            L.append("      %-16s %-28s n=%d payload=%d   %s:%d"
                     % ("len=count+1", f["opcode"], f["n"], f["payload"],
                        f["fichero"], f["linea"]))
        if corrob.get("detalle_fuera"):
            L.append("")
            L.append("  los %d que NO votan, con su motivo.  Un residuo sin"
                     % len(corrob["detalle_fuera"]))
            L.append("  motivo escrito es un residuo sin controlar:")
            for f in corrob["detalle_fuera"][:12]:
                L.append("      %-28s n=%-3d %-18s %s:%d"
                         % (f["opcode"], f["n"], f.get("motivo", ""),
                            f["fichero"], f["linea"]))
    L.append("")
    L.append("LOS DOS ORACULOS NO SE PROMEDIAN.  Si discreparan, el veredicto")
    L.append("seria CONTRADICCION y se dira, no se promediara.")
    return "\n".join(L)


# ----------------------------------------------------------------- selftest

def selftest():
    import shutil
    import tempfile
    fails = []
    oks = [0]

    def v(nombre, cond, detalle=""):
        if cond:
            oks[0] += 1
            print("  ok   %s" % nombre)
        else:
            print("  FAIL %s  %s" % (nombre, detalle))
            fails.append(nombre)

    def empaqueta(packets):
        """Une (header, [payload]) en un dword array."""
        out = []
        for h, pl in packets:
            out.append(h)
            out.extend(pl)
        return out

    def c3(op, n):
        return (3 << 30) | ((op & 0xFF) << 8) | ((n & 0x3FFF) << 16)

    def conv(f3="c+2", nop=True, f2="2c+1"):
        for c in CONVENCIONES:
            if c["_f3"] == f3 and c["_nop"] == nop and c["_f2"] == f2:
                return c
        raise AssertionError("conveccion no declarada")

    tmp = tempfile.mkdtemp(prefix="pm4tila-")
    try:
        # --- POSITIVO: anillo construido donde se sabe la respuesta. -----
        # count = payload - 1  =>  len = count + 2
        #
        # Un paquete con count=5 hace falta DELIBERADAMENTE, y el motivo es
        # una propiedad del oraculo que no es evident: con count=0, `count+2`
        # y `2*count+2` dan los DOS 2, y con count=1 ya dan 3 y 4.  O sea que
        # un anillo hecho solo de paquetes con count=0 NO puede distinguir
        # esas dos convenciones, y el veredicto correcto seria PARCIAL.
        # La primera version de este vector usaba count=0 y fallo; el fallo
        # era del vector, no de la herramienta.  Hay vector para la
        # degeneridad mas abajo, porque es un limite real del metodo.
        d = empaqueta([
            (c3(0x22, 3), [0xA, 0xB, 0xC, 0xD]),      # payload 4, len 5
            (c3(0x10, 0x3FFF), []),                      # NOP de relleno, 1 dw
            (c3(0x3F, 5), [0x11, 0x22, 0x33, 0x44, 0x55, 0x66]),  # len 7
        ])
        surv = convenciones_sobrevivientes(d)
        est, det = veredicto(surv)

        # El veredicto NO puede ser UNICA aqui, y no es un defecto: este anillo
        # no tiene NINGUN PACKET2, asi que su longitud no se puede decidir.  Lo
        # que se comprueba es lo que SI se decidio: entre las que sobreviven,
        # PACKET3 es siempre count+2 y el NOP siempre 1 dword.
        pkt3 = set(c["pkt3"] for c, _ in surv)
        nop = set(c["nop"] for c, _ in surv)
        pkt2 = set(c["pkt2"] for c, _ in surv)
        v("POSITIVO__pkt3_es_count_mas_2", pkt3 == {"count+2"},
          "pkt3=%s" % sorted(pkt3))
        v("POSITIVO__nop_es_1_dword", nop == {"nop=1dword"},
          "nop=%s" % sorted(nop))
        v("POSITIVO__pkt2_queda_abierta", len(pkt2) > 1,
          "pkt2=%s" % sorted(pkt2))
        v("POSITIVO__es_PARCIAL_y_no_UNICA", est == "PARCIAL", est)
        v("POSITIVO__cuadra_exacto",
          any(n == 3 for _, n in surv), str([n for _, n in surv]))

        # --- NEGATIVO: el mismo anillo con la convencion quePm4dec usa. ---
        # No puede embaldosar.  Este es el hallazgo, en forma de vector.
        i, n, fallo = recorre(d, conv("c+1", True, "2c+1"))
        v("NEGATIVO__count_mas_1_NO_embaldosa", fallo is not None,
          "fallo=%s" % fallo)
        v("NEGATIVO__count_mas_1_se_para_antes",
          i < len(d), "llego a %d de %d" % (i, len(d)))

        # --- NEGATIVO 2: sin la regla del NOP, desborda. ---------------
        i, n, fallo = recorre(d, conv("c+2", False, "2c+1"))
        v("NEGATIVO__sin_regla_de_nop_desborda",
          fallo is not None and "desborda" in (fallo or ""), str(fallo))

        # --- BORDE: la ambiguedad de PACKET2 se DECLARA. ---------------
        # Un anillo con un PACKET2 de cuenta 0 no puede decidir su longitud,
        # y aun asi el count=5 si permite decidir la longitud de PACKET3.
        d2 = empaqueta([
            (c3(0x3F, 5), [0x11, 0x22, 0x33, 0x44, 0x55, 0x66]),  # len 7
            (0x80000000, []),                              # PKT2 cuenta 0
        ])
        est2, det2 = veredicto(convenciones_sobrevivientes(d2))
        v("BORDE__pkt2_ambigua_se_declara", est2 == "PARCIAL", est2)
        amb = dict((d[0], d[1]) for d in (det2 or []))
        v("BORDE__la_ambigua_es_pkt2", "pkt2" in amb, str(amb))
        v("BORDE__pkt3_si_queda_decidida", "pkt3" not in amb, str(amb))

        # --- BORDE: la DEGENERIDAD del oraculo con count=0. -----------
        # count+2 y 2*count+2 coinciden en count=0.  Un anillo hecho solo de
        # paquetes con count=0 no puede decidir PACKET3, y la herramienta
        # tiene que decirlo en vez de elegir.  Es el limite del metodo, y un
        # metodo cuyo limite no se declara no se puede usar.
        d2b = empaqueta([
            (c3(0x22, 0), [0xA]),
            (c3(0x22, 0), [0xB]),
        ])
        est2b, det2b = veredicto(convenciones_sobrevivientes(d2b))
        amb2b = dict((d[0], d[1]) for d in (det2b or []))
        v("BORDE__count_0_no_distingue_count_mas_2_de_2count_mas_2",
          "pkt3" in amb2b and
          set(amb2b["pkt3"]) == {"count+2", "2*count+2"}, str(amb2b))

        # --- BORDE: dos PACKET2 con cuenta > 0 SI discriminan. ----------
        d3 = empaqueta([
            (c3(0x22, 0), [0xA]),
            (0x80000000 | (2 << 16), [0, 0]),   # PKT2 cuenta 2: 5 dwords
        ])
        est3, det3 = veredicto(convenciones_sobrevivientes(d3))
        v("BORDE__pkt2_con_cuenta_discrimina", est3 in ("UNICA", "PARCIAL"),
          est3)

        # --- BORDE: un anillo que NO es PM4 no cuadra con ninguna. -----
        ruido = [0x34000008, 0x000054E0, 0x00000400, 0x0FFF000A] * 8
        v("BORDE__ruido_no_embaldosa",
          len(convenciones_sobrevivientes(ruido)) == 0, "sobreviven")

        # --- BORDE: fichero truncado a mitad de dword. ----------------
        p = os.path.join(tmp, "corta.bin")
        with open(p, "wb") as fh:
            fh.write(b"\x00" * (3 * 4 + 6))
        c = cargar_captura(p)
        v("BORDE__truncada_se_declara",
          c["body"] is None and "multiplo" in c["fallo"], str(c["fallo"]))

        # --- BORDE: fichero que no existe. ----------------------------
        c = cargar_captura(os.path.join(tmp, "nada.txt"))
        v("BORDE__inexistente_se_declara",
          c["body"] is None and c["fallo"] is not None, str(c["fallo"]))

        # --- BORDE: cuerpo de 0 dwords. -------------------------------
        p = os.path.join(tmp, "vacia.bin")
        with open(p, "wb") as fh:
            fh.write(b"\x00" * 12)
        c = cargar_captura(p)
        v("BORDE__vacia_cargada", c["body"] is not None and c["ndw"] == 0,
          "body=%s ndw=%s" % (c["body"], c["ndw"]))
        # --- 1476: la cabecera que el instrumento descarta se expone. ---
        real = os.path.join(RAIZ, "revkit", "capturas",
                            "amdgpu_ring_gfx.txt")
        if os.path.exists(real):
            cc = cargar_captura(real)
            cab = cc["cabecera"]
            v("CABECERA__se_expone_con_nombre", cab is not None and
              set(cab) >= {"rptr", "wptr", "wptr_driver"}, str(cab))
            v("CABECERA__los_tres_iguales_se_dice",
              cab is not None and cab["los_tres_iguales"] is True,
              "los tres iguales=%s (explica que el primer paquete visible "
              "no sea un frame entero)" % (cab and cab["los_tres_iguales"]))
            v("CABECERA__los_descartados_se_cuentan",
              cc["dwords_totales"] - cc["ndw"] == CABECERA_DW,
              "fichero=%d cuerpo=%d" % (cc["dwords_totales"], cc["ndw"]))
        v("BORDE__vacia_no_embaldosa",
          len(convenciones_sobrevivientes([])) == 16,
          "un anillo de 0 dwords los embaldosa todo: es degenerado")

        # --- REGRESION: NOP_OPCODE sale de vid.h, no de mi memoria. ---
        ops = nombres_opcode()
        v("REGRESION__vid_h_presente", len(ops) > 50, "opcodes=%d" % len(ops))
        v("REGRESION__NOP_es_0x10_segun_vid_h",
          ops.get(NOP_OPCODE) == "PACKET3_NOP",
          "vid.h dice %r para 0x%02X" % (ops.get(NOP_OPCODE), NOP_OPCODE))

        # --- REGRESION: un constructor en RAMA no vota, se declara. -----
        # MEDIDO que hace falta: `gfx_v9_0.c:7476` escribe
        # PACKET3(RUN_CLEANER_SHADER, 0) dentro de un `if/else`, y el
        # recorrido secuencial leia el payload de la OTRA rama y votaba en
        # contra.  Las 5 generaciones que escriben ese paquete lo hacen con
        # payload = 1 = n + 1, o sea que el codigo era correcto y el contador
        # no.  Un constructor que no se puede contar SIN ADIVINAR se declara.
        #
        # Los fixtures van en un DIRECTORIO TEMPORAL, no en el corpus.  La
        # primera version los escribia en `rx550-upstream-7.2.8/.../amdgpu/` y
        # los borraba en un `finally`.  Eso deja el corpus como un sitio donde
        # un selftest puede escribir, y un `finally` no es una garantia de que
        # no se escribe: es una garantia de que se borra.  Si el proceso muere
        # entre escribir y borrar, queda un fichero .c en el arbol de fuentes.
        fixdir = os.path.join(tmp, "fixtures")
        os.makedirs(fixdir, exist_ok=True)

        with open(os.path.join(fixdir, "fx_rama.c"), "w") as fh:
            fh.write(
                "void f(struct amdgpu_ring *ring)\n"
                "{\n"
                "\tif (algo(ring))\n"
                "\t\tamdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER, 0));\n"
                "\telse\n"
                "\t\tamdgpu_ring_write(ring, PACKET3(PACKET3_RUN_CLEANER_SHADER_9_0, 0));\n"
                "\n"
                "\tamdgpu_ring_write(ring, 0);\n"
                "}\n")
        filas_r, err_r = corroboracion_driver(dirs=[], extra_dir=[fixdir])
        v("REGRESION__rama_condicional_se_declara",
          err_r is None and len(filas_r) == 2 and
          all(x["payload"] is None for x in filas_r),
          "%d filas: %s" % (len(filas_r), str(filas_r)[:200]))
        v("REGRESION__rama_no_vota_en_contra",
          reparte_por_hipotesis(filas_r)["cnt_igual__len_count_mas_1"] == 0,
          str(reparte_por_hipotesis(filas_r)))

        # --- REGRESION: ib.ptr con INDICE LITERAL se cuenta por length_dw.
        # MEDIDO: `gfx_v6_0.c:1970` es
        #     ib.ptr[0] = PACKET3(PACKET3_SET_CONFIG_REG, 1);
        #     ib.ptr[1] = <valor>;
        #     ib.ptr[2] = 0xDEADBEEF;
        #     ib.length_dw = 3;
        # y sin esta regla salia payload=1, o sea un voto FALSO en contra.
        with open(os.path.join(fixdir, "fx_idx.c"), "w") as fh:
            fh.write(
                "void g(struct amdgpu_ib *ib)\n"
                "{\n"
                "\tib.ptr[0] = PACKET3(PACKET3_SET_CONFIG_REG, 1);\n"
                "\tib.ptr[1] = 0x1;\n"
                "\tib.ptr[2] = 0xDEADBEEF;\n"
                "\tib.length_dw = 3;\n"
                "}\n")
        filas_i, _ = corroboracion_driver(dirs=[], extra_dir=[fixdir])
        idx_rows = [x for x in filas_i if x["fichero"] == "fx_idx.c"]
        v("REGRESION__ib_ptr_indice_literal_usa_length_dw",
          len(idx_rows) == 1 and idx_rows[0]["payload"] == 2, str(idx_rows))

        # --- REGRESION: el corpus REAL deja un UNICO voto en contra. ---
        # Este es el vector que cierra `1075` y `1074`.  No dice "cero": dice
        # UNO, y ese uno tiene nombre.  El voto es `gfx_v12_1.c:3440`, la
        # discrepancia REAL de NAVI 12.1 que describe el hallazgo 1074: las
        # otras nueve generaciones ponen 2 payload y esa pone 1.
        #
        # MEDIDO que un vector que exigiera CERO en contra habria sido el
        # equivocado: habria exigido callar una discrepancia real del corpus,
        # que es exactamente el defecto que `1068` denuncia.  Un vector debe
        # fijar la verdad, no la respuesta que uno quiere.
        filas_r2, err2 = corroboracion_driver()
        d2 = reparte_por_hipotesis(filas_r2)
        v("REGRESION__un_solo_voto_en_contra",
          err2 is None and d2["cnt_igual__len_count_mas_1"] == 1,
          "en contra = %d" % d2["cnt_igual__len_count_mas_1"])
        contras = [f for f in filas_r2
                   if f["payload"] is not None and f["payload"] == f["n"]]
        v("REGRESION__el_voto_es_navi_12_1",
          len(contras) == 1 and contras[0]["fichero"] == "gfx_v12_1.c" and
          contras[0]["opcode"] == "PACKET3_SET_CONFIG_REG", str(contras))
        v("REGRESION__el_voto_es_el_del_hallazgo_1074",
          len(contras) == 1 and contras[0]["linea"] == 3440, str(contras))
        v("REGRESION__gfx8_no_aporta_votos_en_contra",
          not [f for f in contras if f["fichero"].startswith("gfx_v8")],
          "GFX8 no debe discrepar")
        v("REGRESION__corpus_real_empieza_a_apoyar",
          d2["cnt_menos_1__len_count_mas_2"] > 200,
          "a favor = %d" % d2["cnt_menos_1__len_count_mas_2"])

        # --- REGRESION: corroborar con el driver, sobre el caso real. ---
        filas, err = corroboracion_driver(["gfx_v7_0.c"])
        v("REGRESION__driver_leido", err is None and len(filas) > 0, str(err))
        d = reparte_por_hipotesis(filas)
        v("REGRESION__gcn3_apoya_count_mas_2",
          d["cnt_menos_1__len_count_mas_2"] > 0 and
          d["cnt_igual__len_count_mas_1"] == 0, str(d["cnt_menos_1__len_count_mas_2"]
                                                     ) + "/" + str(d["cnt_igual__len_count_mas_1"]))

        # --- REGRESION: heremetico. -----------------------------------
        got = os.popen(
            "cd / && python3 -c %s" % __import__("shlex").quote(
                "import sys;sys.path.insert(0,%r);import pm4tila;"
                "print(pm4tila.RAIZ)" % AQUI)).read().strip()
        v("HERMETICO__RAIZ_no_depende_del_cwd", got == RAIZ,
          "esperado=%s obtenido=%s" % (RAIZ, got))

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    print("")
    total = len(fails) + oks[0]
    if fails:
        print("selftest: %d vectores FALLAN de %d" % (len(fails), total))
        print("FALLAN: %s" % ", ".join(fails))
        return 1
    print("selftest: %d vectores, 0 fallos" % total)
    return 0


# --------------------------------------------------------------------- main

def main(argv):
    ap = argparse.ArgumentParser(
        prog="pm4tila.py",
        description="Adjudica la convencion de longitud de paquete PM4 con un "
                    "oraculo geometrico, y la corrobora con el driver.")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--capturas", default=None,
                    help="lista separada por comas de anillos a medir")
    ap.add_argument("--driver", action="store_true",
                    help="solo la corroboracion de fuente")
    ap.add_argument("--version", action="store_true")
    ap.add_argument("--selftest", "--self-test", dest="selftest",
                    action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.version:
        print(VERSION)
        return 0

    nombres = args.capturas.split(",") if args.capturas else None
    filas = [] if args.driver else mide_capturas(nombres)
    cr, err = corroboracion_driver()
    corrob = reparte_por_hipotesis(cr)
    if err:
        corrob["_error"] = err

    if args.json:
        print(json.dumps({
            "herramienta": "pm4tila.py", "version": VERSION,
            "espacio_de_convenciones": [
                {k: v for k, v in c.items() if not k.startswith("_")}
                for c in CONVENCIONES],
            "anillos": filas, "corroboracion_driver": corrob,
        }, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print(informe(filas, corrob))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
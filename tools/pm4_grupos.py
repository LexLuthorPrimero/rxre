#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pm4_grupos.py -- Determinacion de los dwords de un paquete PM3 de GFX8
usando tres clases de evidencia del MISMO primario (vid.h), y comprobando
que el header se autocomprueba.

  1. DESPLAZAMIENTO   el inicio del campo siguiente acota el anterior por
                      arriba.  Bound superior.
  2. ENUMERACION      la enumeracion inline de valores legales que el header
                      escribe junto al macro acota el campo por abajo.  Con
                      (n-1).bit_length() valores distintos hacen falta.
  3. PROSA            la cabecera del paquete numera dwords y da rangos de
                      bits en texto.  Es una AFIRMACION INDEPENDIENTE de la
                      misma fuente,  y se contrasta con el resultado.

Donde 1 y 2 coinciden, el ancho no es una cota: es el ancho.  Donde 1 y 3
coinciden, el primario se autocomprueba.

Por que el guard es parte del codigo y no una nota
--------------------------------------------------
Este script nació de un parser que perdía el primer valor de cada bloque de
enumeración que abre con "/*" en la misma línea.  El síntoma NO era un cero:
era el MISMO número de bloques con el contenido equivocado (23 bloques, 55
valores en vez de 78).  Un cero se nota; 55 con 23 bloques parece sano.

Lo que lo delató fue un guard que compara la salida contra un positivo leído a
mano.  Ese guard está aquí dentro,  y `_autovalidacion()` falla ruidosamente si
alguna vez deja de ver el positivo.  Un guard escrito a mano en un fichero de
análisis no es una regla del proyecto;  este vive en la herramienta.

Lo que NO hace
--------------
No lee la GPU.  No adivina el ancho por EXTRACCION,  que no existe en el árbol.
Un "EXACTO" significa "el ancho por desplazamiento coincide con el mínimo que
exige la enumeración",  no "el hardware lo interpreta así".

Salida
------
    python3 tools/pm4_grupos.py            informe de todos los paquetes
    python3 tools/pm4_grupos.py --plano     modo PLANO:  sin comentarios de
                                            grupo.  Los macros que hay entre
                                            el opcode de un paquete y el
                                            siguiente opcode le pertenecen.
                                            Es lo unico que se puede
                                           determinar para los paquetes que no
                                            declaran sus dwords,  como
                                            WRITE_DATA.
    python3 tools/pm4_grupos.py --paquete MAP_QUEUES
    python3 tools/pm4_grupos.py --selftest
"""

import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VID = os.path.join(RAIZ, "RESEARCH", "working", "linux-7.1.3",
                   "drivers", "gpu", "drm", "amd", "amdgpu", "vid.h")

# --- patrones -------------------------------------------------------------
# Un bloque de enumeracion abre con "/* N - texto" o sigue con "* N - texto".
P_ENUM_SIG = re.compile(r"^\s*\*\s*(\d+)\s*-\s*(.+?)\s*$")
P_ENUM_ABI = re.compile(r"^\s*/\*\s*(\d+)\s*-\s*(.+?)\s*(\*/)?\s*$")
# La prosa de cabecera: "7. COMMAND [30:21] | BYTE_COUNT [20:0]"
P_PROSA = re.compile(r"^\s*\*\s*(\d+)\.\s*(.+)$")
P_GRUPO = re.compile(r"^\s*/\s*\*?\s*(CONTROL\d*[a-z]?|COMMAND)\s*\*/")
P_DEF = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+)\s*(.*)$")
# Un opcode de paquete es  "PACKET3_X   0xNN"  y no lleva "(x)" ni "<<".
P_OPCODE = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|\\d+)\s*$")
OPC_ALL = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s*$")
P_SHIFT = re.compile(r"<<\s*(\d+)")
P_FLAG = re.compile(r"\(\s*1\s*<<\s*(\d+)\s*\)")

# El positivo de la autovalidacion, leido a mano de vid.h:282-284.
#   /* 0 - ME
#    * 1 - PFP
POSITIVO_LINEA = 282
POSITIVO_VALORES = (0, 1)


# --- 1. enumeraciones -----------------------------------------------------
def enumeraciones(lineas):
    """{linea_de_apertura: (linea, valores_ordenados)}.

    La enumeracion SIGUE al macro que documenta.  No es una convencion mia:
    se comprueba por sentido (el enum {0,1,3} = "DST_ADDR using DAS, GDS,
    L2" es un selector de destino,  no un booleano de cache),  y el guard
    `_autovalidacion` lo vigila.
    """
    enums = {}
    linea_actual = None
    valores = None

    def cerrar():
        nonlocal linea_actual, valores
        if linea_actual is not None:
            enums[linea_actual] = (linea_actual, sorted(set(valores)))
        linea_actual = None
        valores = None

    for i, texto in enumerate(lineas, 1):
        m = P_ENUM_SIG.search(texto) or P_ENUM_ABI.search(texto)
        if m is not None:
            if linea_actual is None:
                linea_actual, valores = i, []
            valores.append(int(m.group(1)))
            continue
        if linea_actual is not None:
            cerrar()
    cerrar()
    return enums


def _autovalidacion(enums):
    """El guard.  Falla ruidosamente si el parser deja de ver el positivo.

    Sin este,  un parser que pierde un valor por bloque produce un numero
    PLAUSIBLE y con la cuenta de bloques correcta.  Ver la nota de cabecera.
    """
    visto = enums.get(POSITIVO_LINEA, (None, None))[1]
    if visto is None:
        return ("FALLA", "el parser no encuentra el bloque de vid.h:%d"
                % POSITIVO_LINEA)
    if tuple(visto) != POSITIVO_VALORES:
        return ("FALLA", "el parser ve %s en vid.h:%d y se esperaba %s"
                % (list(visto), POSITIVO_LINEA, list(POSITIVO_VALORES)))
    return ("OK", "ve el positivo de vid.h:%d -> %s"
            % (POSITIVO_LINEA, list(visto)))


# --- 2. grupos de macros --------------------------------------------------
def grupos(lineas, solo=None):
    """{linea_del_comentario: (nombre, campos)}.

    Los campos son [nombre, bit_inicial, linea_del_define, es_flag].
    `es_flag` distingue  "(1 << n)"  -- valor constante,  ancho 1 por
    construccion  -- de  "((x) << n)"  -- campo,  ancho por desplazamiento.
    """
    salida = {}
    actual = None
    for i, texto in enumerate(lineas, 1):
        g = P_GRUPO.match(texto)
        if g is not None:
            actual = (g.group(1), [])
            salida[i] = actual
            continue
        # El paquete cambia aqui:  se cierra el grupo anterior.  Sin esto,
        # /* COMMAND */ en vid.h:309 se traga PACKET3_SET_RESOURCES_*  y
        # layout() inventa campos que no son de este paquete.
        if P_OPCODE.search(texto) is not None:
            actual = None
            continue
        if actual is None:
            continue
        d = P_DEF.search(texto)
        if d is None:
            continue
        nombre, resto = d.group(1), d.group(2)
        if solo is not None and solo not in nombre:
            continue
        fl = P_FLAG.search(texto)
        sh = P_SHIFT.search(resto)
        if fl is not None:
            actual[1].append([nombre, int(fl.group(1)), i, True])
        elif sh is not None:
            actual[1].append([nombre, int(sh.group(1)), i, False])
    return salida


def plano(lineas, solo=None):
    """Los macros de cada paquete, SIN usar comentarios de grupo.

    La frontera es el opcode:  todo lo que hay entre el opcode de un paquete y
    el opcode siguiente le pertenece.  Es mas debil que el modo por grupos
    --no dice que dword es cual--  pero recupera los paquetes que no declaran
    la estructura,  como PACKET3_WRITE_DATA,  que tiene 5 macros sueltas y
    ningun comentario de grupo.

    Los macros sin prefijo del nombre del paquete (WRITE_DATA_DST_SEL,  que es
    PACKET3_WRITE_DATA_DST_SEL sin el prefijo) se aceptan por sufijo.
    """
    salida = {}
    paq = None
    OPC = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s*$")
    DEF = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+|[A-Z][A-Z0-9_]+)\s*(.*)$")
    for i, texto in enumerate(lineas, 1):
        m = OPC.match(texto)
        #  Un valor > 0xFF no es un opcode  (vid.h:105-107):  no cierra paquete.
        if m is not None and int(m.group(2), 16) <= 0xFF:
            paq = m.group(1)
            salida.setdefault(paq, [])
            continue
        if paq is None:
            continue
        d = DEF.match(texto)
        if d is None:
            continue
        nombre, resto = d.group(1), d.group(2)
        if solo is not None and solo not in nombre:
            continue
        #  ATRIBUCION POR POSICION,  no por nombre.  vid.h  usa tres prefijos
        #  distintos para los campos de WRITE_DATA:  WRITE_DATA_*  y WR_*,  y
        #  ningun filtro por nombre los captura a los dos.  La frontera la da
        #  el opcode,  que ya es la regla que uso para los grupos.
        #  Se informa de cuantos Macros NO llevan el nombre del paquete,  para
        #  que la atribucion por posicion sea visible y no silenciosa.
        corto = paq[len("PACKET3_"):]
        if not (nombre.startswith(paq) or nombre.startswith(corto)):
            salida.setdefault("_ajenos", []).append(nombre)
        fl = P_FLAG.search(texto)
        sh = P_SHIFT.search(resto)
        if fl is not None:
            salida[paq].append([nombre, int(fl.group(1)), i, True])
        elif sh is not None:
            salida[paq].append([nombre, int(sh.group(1)), i, False])
    return {k: v for k, v in salida.items() if v}


def ventanas(lineas):
    """{paquete: (linea_de_su_opcode, linea_del_opcode_siguiente)}.

    Es lo que convierte el modo plano de una suposicion en una atribucion
    ACOTADA:  si todos los macros de un paquete caen entre su opcode y el
    siguiente,  el propio header los delimita  y no hay que suponer nada.
    """
    #  SOLO son opcodes los que caben en 8 bits.  PACKET3(op,n)  aplica
    #  (op) & 0xFF  -- vid.h:105-107 --  asi que un valor mayor que 0xFF no
    #  puede viajar como opcode:  son constantes de reubicacion,  y contarlas
    #  como paquetes parte las ventanas en lugares donde no hay paquete.
    OPC = re.compile(r"#\s*define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+)\s*$")
    def _opcode(linea):
        m = OPC.match(linea)
        if m is None or int(m.group(2), 16) > 0xFF:
            return None
        return m.group(1)
    pos = [(i, _opcode(linea)) for i, linea in enumerate(lineas, 1)
           if _opcode(linea) is not None]
    salida = {}
    for k, (ini, paq) in enumerate(pos):
        fin = pos[k + 1][0] if k + 1 < len(pos) else len(lineas) + 1
        salida[paq] = (ini, fin)
    return salida


def prosa(lineas):
    """Lista de bloques de cabecera en prosa:  [(linea, {n: texto}), ...].

    NO se indexa por numero de dword.  Indexarlo asi hace que el dword 7 de
    un paquete pise el dword 7 del siguiente,  y `p[7]` devolvia la prosa de
    otro paquete.  Se devuelve el bloque entero y se busca dentro.
    """
    bloques = []
    actual = None
    for i, texto in enumerate(lineas, 1):
        m = P_PROSA.match(texto)
        if m is not None:
            if actual is None:
                actual = (i, {})
            actual[1][int(m.group(1))] = m.group(2).strip()
        elif actual is not None and not texto.strip().startswith("*"):
            bloques.append(actual)
            actual = None
    if actual is not None:
        bloques.append(actual)
    return bloques


def prosa_de(bloques, numero, contiene=None):
    """El dword `numero` del bloque cuya prosa contiene `contiene`."""
    for _, bloque in bloques:
        if contiene is not None and not any(contiene in v for v in bloque.values()):
            continue
        if numero in bloque:
            return bloque[numero]
    return None


# --- 3. layout ------------------------------------------------------------
def layout(campos, enums):
    """Intervalos de bits por desplazamiento, cruzados con las enumeraciones.

    Devuelve una lista de filas de texto y un resumen con conteos.
    """
    c = sorted(campos, key=lambda x: x[1])
    filas = []
    for k, (nombre, inicio, linea, es_flag) in enumerate(c):
        if es_flag:
            filas.append("  %-36s = 1<<%-2d   FLAG de 1 bit" % (nombre, inicio))
            continue
        if k + 1 < len(c):
            fin = c[k + 1][1] - 1
        else:
            fin = 31
        ancho = fin - inicio + 1
        vals = enums.get(linea + 1, (0, None))[1]
        if vals:
            minimo = (len(vals) - 1).bit_length()
            veredicto = ("EXACTO" if minimo == ancho
                         else "min %d, holgura %d" % (minimo, ancho - minimo))
        else:
            minimo, veredicto = None, "sin enumeracion"
        filas.append("  %-36s << %-2d -> bits [%2d:%-2d] = %2d bits  %s"
                     % (nombre, inicio, fin, inicio, ancho, veredicto))
    return filas


def huecos(campos):
    """Bits de [0:31] que ningun campo cubre."""
    h, p = [], 0
    ocupados = []
    c = sorted(campos, key=lambda x: x[1])
    for k, (nombre, inicio, linea, es_flag) in enumerate(c):
        if es_flag:
            ocupados.append((inicio, inicio))
        else:
            fin = c[k + 1][1] - 1 if k + 1 < len(c) else 31
            ocupados.append((inicio, fin))
    for a, b in ocupados:
        if a > p:
            h.append((p, a - 1))
        p = max(p, b + 1)
    if p <= 31:
        h.append((p, 31))
    return h


def ocupa(campos):
    """Conjunto de bits que los campos cubren de verdad.

    No es lo mismo que los bits de INICIO:  dos campos conmutos, como
    CMD_SRC_SWAP <<22 ([23:22]) y CMD_DST_SWAP <<24 ([25:24]),  empiezan en
    22 y 24 pero cubren 22..25 sin hueco.  Comparar la prosa [30:21]
    contra los inicios daria un falso desacuerdo.
    """
    c = sorted(campos, key=lambda x: x[1])
    bits = set()
    for k, (nombre, inicio, linea, es_flag) in enumerate(c):
        if es_flag:
            bits.add(inicio)
        else:
            fin = c[k + 1][1] - 1 if k + 1 < len(c) else 31
            bits.update(range(inicio, fin + 1))
    return bits


def _cubre(campos):
    total = 0
    c = sorted(campos, key=lambda x: x[1])
    for k, (nombre, inicio, linea, es_flag) in enumerate(c):
        if es_flag:
            total += 1
        else:
            fin = c[k + 1][1] - 1 if k + 1 < len(c) else 31
            total += fin - inicio + 1
    return total


# Regresion:  vid.h tiene 14 comentarios de dword.  Una version anterior de
# este regex aceptaba  (CONTROL\d?|COMMAND)  -- 9 de los 14.  Los 5 que no
# aceptaba  --CONTROL2a, CONTROL2b, CONTROL3a, CONTROL3b  y el CONTROL2a del
# ultimo paquete--  no fallaban:  se absorbian en el grupo anterior y sus
# desplazamientos se sumaban,  produciendo "bits [-1:0] = 0 bits" y
# "holgura -2",  que son veredictos imposibles publicados como si fueran datos.
#
# Es el MISMO fallo de clase "[A-Z0-9_] sin la 'a' de CONTROL2a" que ya
# estaba grabado como error propio.  Volvio porque la leccion no se
# generalizo a la nueva herramienta.  De ahi los dos vectores de recuento.
GRUPOS_VID_H = 14

# Cuantos vectores DEBEN ejecutarse.  Si el numero baja,  algo se ha saltado.
VECTORES_ESPERADOS = 53


def comentarios_de_dword(lineas):
    """Todos los comentarios de dword, sin filtrar por ninguna regexp.

    Existe para que el filtro se pueda CONTRASTAR contra el entero.  Un filtro
    que no se contrasta con el total no puede fallar de forma visible.
    """
    salida = []
    for i, texto in enumerate(lineas, 1):
        m = re.match(r"^\s*/\s*\*?\s*([A-Za-z0-9]+)\s*\*/", texto)
        if m is not None:
            salida.append((i, m.group(1)))
    return salida


# --- informe --------------------------------------------------------------
def informe(solo=None):
    with open(VID, encoding="utf-8", errors="replace") as f:
        lineas = f.read().split("\n")

    enums = enumeraciones(lineas)
    estado, detalle = _autovalidacion(enums)
    print("  AUTOVALIDACION  %s -- %s" % (estado, detalle))
    if estado != "OK":
        return 2
    print("  bloques de enumeracion: %d   valores enumerados: %d"
          % (len(enums), sum(len(v) for _, v in enums.values())))
    print()

    g = grupos(lineas, solo=solo)
    p = prosa(lineas)
    print("  bloques de cabecera en prosa: %d" % len(p))
    for ini, bloque in p:
        print("    vid.h:%-4d  %s" % (ini, "  ".join(
            "%d.%s" % (n, v) for n, v in sorted(bloque.items()))[:96]))
    print()

    for ini, (nombre, campos) in sorted(g.items()):
        print("  %s   (comentario en vid.h:%d)" % (nombre, ini))
        for fila in layout(campos, enums):
            print(fila)
        hs = huecos(campos)
        print("      cubiertos %2d/32   huecos sin campo: %s"
              % (_cubre(campos),
                 ", ".join("bits [%d:%d]" % (a, b) for a, b in hs) or "NINGUNO"))
        print()
    return 0


def informe_plano(solo=None):
    with open(VID, encoding="utf-8", errors="replace") as f:
        lineas = f.read().split("\n")
    enums = enumeraciones(lineas)
    estado, detalle = _autovalidacion(enums)
    print("  AUTOVALIDACION  %s -- %s" % (estado, detalle))
    if estado != "OK":
        return 2
    plano_ = plano(lineas, solo=solo)
    print("  paquetes con lista plana de macros: %d\n" % len(plano_))
    for paq, campos in sorted(plano_.items()):
        print("  %s   (%d macros, sin comentario de grupo)"
              % (paq, len(campos)))
        for fila in layout(campos, enums):
            print(fila)
        hs = huecos(campos)
        print("      cubiertos %2d/32   huecos sin campo: %s"
              % (_cubre(campos),
                 ", ".join("bits [%d:%d]" % (a, b) for a, b in hs) or "NINGUNO"))
        print()
    return 0


# --- selftest -------------------------------------------------------------
def selftest():
    fallos = []
    total = 0

    def chk(nombre, cond, detalle=""):
        nonlocal total
        total += 1
        if not cond:
            fallos.append((nombre, detalle))
        return cond

    with open(VID, encoding="utf-8", errors="replace") as f:
        L = f.read().split("\n")
    enums = enumeraciones(L)
    g = grupos(L)
    p = prosa(L)

    # --- el guard, como vector, no como nota
    chk("el guard ve el positivo de vid.h:282",
        _autovalidacion(enums)[0] == "OK", _autovalidacion(enums)[1])

    # --- el fallo que el guard existe para detectar
    L2 = list(L)
    L2[281] = L2[281].lstrip("\t ")
    chk("un bloque que abre con '/*' pegado al margen se sigue viendo",
        282 in enumeraciones(L2) and tuple(enums.get(282, (0, []))[1]) == (0, 1),
        str(enums.get(282)))

    # --- el numero de bloques NO basta: se comprueba el CONTENIDO
    chk("23 bloques de enumeracion en vid.h", len(enums) == 23, str(len(enums)))
    chk("78 valores enumerados en vid.h, no 55",
        sum(len(v) for _, v in enums.values()) == 78,
        str(sum(len(v) for _, v in enums.values())))
    chk("el enum {0,1,3} existe (es el de DST_SEL)",
        any(tuple(v) == (0, 1, 3) for _, v in enums.values()),
        str(sorted(set(tuple(v) for _, v in enums.values()))))

    # --- el filtro de grupos,  contrastado contra el total
    todos = comentarios_de_dword(L)
    chk("vid.h declara 14 comentarios de dword", len(todos) == GRUPOS_VID_H,
        str(len(todos)))
    chk("el filtro de grupos no pierde ninguno de los 14",
        len(g) == GRUPOS_VID_H, str(len(g)))
    perdidos = [n for _, n in todos if n not in [cs[0] for cs in g.values()]]
    chk("ningun nombre de dword se queda fuera de un grupo", not perdidos,
        str(perdidos))

    # --- MAP_QUEUES: lo que determino 1207
    mq2 = [cs for cs in g.values() if cs[0] == "CONTROL2"
           and any("MAP_QUEUES" in x[0] for x in cs[1])]
    chk("la guarda de MAP_QUEUES/CONTROL2 es cierta", bool(mq2), str(len(mq2)))
    chk("MAP_QUEUES/CONTROL2 tiene 5 macros", mq2 and len(mq2[0][1]) == 5,
        str(len(mq2[0][1])) if mq2 else "no encontrado")
    if mq2:
        filas = layout(mq2[0][1], enums)
        texto = "\n".join(filas)
        chk("MAP_QUEUES/CONTROL2: PIPE en bits [30:29] y 2 bits",
            "bits [30:29] =  2 bits" in texto, texto)
        # ME es un CAMPO ((x) << 31),  no un flag (1 << 31).  El vector
        # anterior buscaba la forma del flag  y por eso fallaba.
        chk("MAP_QUEUES/CONTROL2: ME es el bit 31",
            "bits [31:31] =  1 bits" in texto, texto)
        chk("MAP_QUEUES/CONTROL2: DOORBELL_OFFSET en bits [25:2], 24 bits",
            "bits [25:2 ] = 24 bits" in texto or
            "bits [25:2] = 24 bits" in texto, texto)
        hs = huecos(mq2[0][1])
        chk("MAP_QUEUES/CONTROL2: el unico hueco es el bit 0",
            hs == [(0, 0)], str(hs))

    # --- DMA_DATA: lo que determino 1208
    #  OJO:  g.items()  entrega  (linea, (nombre, campos)).  Desempaquetar como
    #  (n, cs)  deja n = NUMERO DE LINEA,  y "if n == 'CONTROL'"  compara un
    #  entero con una cadena:  siempre falso.  Asi los nueve vectores de
    #  DMA_DATA no se ejecutaban y el selftest decia verde.  Se desempaqueta
    #  por el NOMBRE,  y se vectorea que las guardas sean ciertas.
    dd = [(cs[0], cs[1]) for _, cs in g.items()
          if any("DMA_DATA" in x[0] for x in cs[1])]
    chk("DMA_DATA tiene 2 grupos con macros", len(dd) == 2, str(len(dd)))
    ctrl = [cs for nom, cs in dd if nom == "CONTROL"]
    cmd = [cs for nom, cs in dd if nom == "COMMAND"]
    chk("las guardas de los bloques DMA_DATA son ciertas",
        bool(ctrl) and bool(cmd), "ctrl=%d cmd=%d" % (len(ctrl), len(cmd)))
    if ctrl:
        filas = "\n".join(layout(ctrl[0], enums))
        chk("DMA_DATA/CONTROL: SRC_SEL en [30:29], 2 bits, EXACTO",
            "bits [30:29] =  2 bits" in filas and "EXACTO" in filas, filas)
        chk("DMA_DATA/CONTROL: SRC_CACHE_POLICY en [14:13], 2 bits",
            "bits [14:13] =  2 bits" in filas, filas)
        chk("DMA_DATA/CONTROL: ENGINE en [12:0], 13 bits con holgura 12",
            "bits [12:0 ] = 13 bits" in filas and "holgura 12" in filas, filas)
        hs = huecos(ctrl[0])
        chk("DMA_DATA/CONTROL: los huecos son [16:19] y [28]",
            hs == [(16, 19), (28, 28)], str(hs))
        chk("DMA_DATA/CONTROL cubre 27 de 32 bits", _cubre(ctrl[0]) == 27,
            str(_cubre(ctrl[0])))
    if cmd:
        nombres = [x[0] for x in cmd[0]]
        bits = sorted(ocupa(cmd[0]))
        chk("DMA_DATA/COMMAND ocupa bits [21:30], sin huecos dentro",
            bits == list(range(21, 31)), str(bits))
        chk("los inicios de COMMAND son 8 y distintos",
            len(set(x[1] for x in cmd[0])) == 8,
            str(sorted(set(x[1] for x in cmd[0]))))
        # REGRESION:  /* COMMAND */ en vid.h:309 no esta cerrado por otro
        # comentario,  asi que sin acotar por opcode se traga los macros de
        # PACKET3_SET_RESOURCES  y layout() inventa campos ajenos.  Este vector
        # fue el que lo delato.  No debe relajarce.
        chk("ningun grupo se traga macros de otro paquete",
            not any("SET_RESOURCES" in x[0] for cs in g.values()
                    for x in cs[1] if "DMA_DATA" in x[0]),
            str([x[0] for cs in g.values() for x in cs[1]
                 if "DMA_DATA" in x[0] and "SET_RESOURCES" in x[0]]))
        chk("COMMAND tiene exactamente los 8 macros de DMA_DATA",
            len(nombres) == 8, str(nombres))
        texto = "\n".join(layout(cmd[0], enums))
        chk("DMA_DATA/COMMAND: los dos swaps son EXACTOS",
            texto.count("EXACTO") == 2, texto)

    # --- modo PLANO:  la fuente debil que sube la cobertura de 6% a 20%
    pl = plano(L)
    pl_ok = {k: v for k, v in pl.items() if k != "_ajenos"}
    chk("vid.h da lista plana de macros a 15 paquetes",
        len(pl_ok) == 15, str(len(pl_ok)))
    # LIMITACION PERMANENTE.  El limite del modo plano es el OPCODE,  pero el
    # header no mantiene ese invariante:  hay 85 macros cuyo nombre no lleva
    # el del paquete y que caen dentro de otro por posicion.  Ejemplo medido:
    # PACKET3_SURFACE_SYNC se come 23 macros,  de las cuales RB_MAP_PKR0,
    # PKR_MAP, SC_MAP y SE_MAP  son un bloque de mapa de registros,  no campos
    # de SURFACE_SYNC.  El modo plano da un SUPERCONJUNTO.  Que macros de un
    # paquete pertenecen de verdad a el es NOT_DETERMINED donde el nombre
    # discrepa,  y por eso el vector cuenta los discrepantes en vez de
    # suponerlos correctos.
    ajenos = pl.get("_ajenos", [])
    chk("99 macros tienen nombre que no lleva el de su paquete",
        len(ajenos) == 99, str(len(ajenos)))
    for nom in ("WR_ONE_ADDR", "WR_CONFIRM", "PKR_MAP", "SE_PAIR_YSEL_MASK"):
        chk("el discrepante %s esta en la lista de ajenos" % nom,
            nom in ajenos, str(len(ajenos)))
    wd = pl_ok.get("PACKET3_WRITE_DATA", [])
    chk("WRITE_DATA tiene 5 macros en su lista plana", len(wd) == 5,
        str([x[0] for x in wd]))
    texto = "\n".join(layout(wd, enums))
    chk("WRITE_DATA: DST_SEL en [15:8], 8 bits, holgura 5",
        "bits [15:8 ] =  8 bits" in texto and "holgura 5" in texto, texto)
    chk("WRITE_DATA: ENGINE_SEL en [31:30], 2 bits, EXACTO",
        "bits [31:30] =  2 bits" in texto and "EXACTO" in texto, texto)
    # WR_ONE_ADDR y WR_CONFIRM empiezan por WR_,  no por WRITE_DATA_:  un
    # filtro por nombre los pierde.  La atribucion es POR POSICION.
    chk("WRITE_DATA: los dos macros WR_ estan como FLAG, no como campo",
        texto.count("FLAG de 1 bit") == 2, texto)
    chk("los macros WR_ se atribuyen por posicion, no por nombre",
        any(x[0] == "WR_ONE_ADDR" for x in wd), str([x[0] for x in wd]))
    chk("WRITE_DATA deja 3 huecos: [0:7], [17:19], [21:24]",
        huecos(wd) == [(0, 7), (17, 19), (21, 24)], str(huecos(wd)))
    # Lo que hace el modo plano DEFENDIBLE:  los macros caen dentro de la
    # ventana que el header delimita entre opcode y opcode.  Sin esto seria
    # una suposicion de posicion;  con esto es una atribucion acotada.
    ven = ventanas(L)
    fuera = [p for p, cs in pl_ok.items()
             if not all(ven.get(p, (0, 0))[0] < x[2] < ven.get(p, (0, 0))[1]
                        for x in cs)]
    chk("los macros de los 15 paquetes caen dentro de su ventana de opcode",
        not fuera, str(fuera))
    chk("la ventana de WRITE_DATA es [141:161]",
        ven.get("PACKET3_WRITE_DATA") == (141, 161),
        str(ven.get("PACKET3_WRITE_DATA")))
    chk("WRITE_DATA: sus 5 macros estan en vid.h:142..160",
        all(141 < x[2] < 161 for x in wd), str([x[2] for x in wd]))

    solo_planas = set(pl_ok) - {"PACKET3_DMA_DATA", "PACKET3_MAP_QUEUES",
                                "PACKET3_UNMAP_QUEUES", "PACKET3_QUERY_STATUS"}
    chk("11 paquetes tienen lista plana y NO tienen grupo",
        len(solo_planas) == 11, str(len(solo_planas)))
    chk("WRITE_DATA esta entre ellos", "PACKET3_WRITE_DATA" in solo_planas,
        str(sorted(solo_planas)))

    # --- la contaminacion de opcodes por constantes de reubicacion
    formas = [l for l in L if OPC_ALL.match(l)]
    reales = [l for l in formas
              if int(OPC_ALL.match(l).group(2), 16) <= 0xFF]
    chk("vid.h tiene 78 lineas con la forma de opcode", len(formas) == 78,
        str(len(formas)))
    chk("solo 70 pueden ser opcode: 8 tienen valor > 0xFF",
        len(reales) == 70, str(len(reales)))
    chk("las 8 son las cuatro familias *_START/_END de reubicacion",
        all(re.search(r"_(START|END)$", OPC_ALL.match(l).group(1))
            for l in formas if int(OPC_ALL.match(l).group(2), 16) > 0xFF),
        str([OPC_ALL.match(l).group(1) for l in formas
             if int(OPC_ALL.match(l).group(2), 16) > 0xFF]))
    ven2 = ventanas(L)
    chk("las ventanas ya no tienen entradas de mas", len(ven2) == 70,
        str(len(ven2)))
    #  Con el filtro de 8 bits,  la ventana de SET_SH_REG se ABRE:  sus dos
    #  constantes de reubicacion  (vid.h:348 y :349)  ya no la cierran,  asi que
    #  se queda con ellas dentro.  Eso es lo correcto:  le pertenecen.
    chk("SET_SH_REG existe como opcode y su ventana se abre a [347:350]",
        "PACKET3_SET_SH_REG" in ven2 and ven2["PACKET3_SET_SH_REG"] == (347, 350),
        str(ven2.get("PACKET3_SET_SH_REG")))
    chk("PACKET3_SET_SH_REG_START ya NO es una ventana",
        "PACKET3_SET_SH_REG_START" not in ven2, "esta")

    # --- la prosa, que es la afirmacion independiente
    d7 = prosa_de(p, 7, contiene="COMMAND [30:21]")
    chk("la prosa de DMA_DATA declara 7 dwords con COMMAND [30:21]",
        d7 == "COMMAND [30:21] | BYTE_COUNT [20:0]", str(d7))
    if cmd and d7:
        bits = sorted(ocupa(cmd[0]))
        lo, hi = re.findall(r"\[(\d+):(\d+)\]", d7)[0]
        declarados = sorted(range(int(hi), int(lo) + 1))   # la prosa va [alto:bit]
        chk("la prosa y los macros coinciden sobre COMMAND",
            bits == declarados,
            "macros %s prosa %s" % (bits, declarados))
    chk("la prosa no se pisa entre paquetes: hay mas de un bloque",
        len(p) > 1, str(len(p)))
    chk("no existe macro para BYTE_COUNT: es un valor crudo",
        not any("BYTE_COUNT" in x[0] for cs in g.values() for x in cs[1]))

    #  GUARD GLOBAL:  el selftest no puede dar verde si dejo de ejecutar
    #  vectores.  Un bloque bajo una guarda falsa se salta en silencio  y el
    #  recuento baja  y todo parece bien.  ESTE es el fallo que acabo de
    #  encontrar en esta misma herramienta.
    if total != VECTORES_ESPERADOS:
        fallos.append(("se ejecutaron %d vectores de %d declarados"
                       % (total, VECTORES_ESPERADOS),
                       "un bloque bajo una guarda falsa se salta en silencio"))
    for nombre, detalle in fallos:
        print("  FALLA %s   %s" % (nombre, detalle[:90]))
    print("  %s" % ("SELFTEST OK: %d vectores" % total if not fallos
                   else "SELFTEST: %d de %d" % (total - len(fallos), total)))
    return 0 if not fallos else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--plano" in argv:
        return informe_plano()
    solo = None
    if "--paquete" in argv:
        i = argv.index("--paquete")
        if i + 1 >= len(argv):
            print("  --paquete necesita un nombre")
            return 2
        solo = argv[i + 1]
    if not os.path.exists(VID):
        print("  no encuentro %s" % VID)
        return 2
    return informe(solo=solo)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
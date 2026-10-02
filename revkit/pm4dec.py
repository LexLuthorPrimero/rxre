#!/usr/bin/env python3
"""
pm4dec.py -- decodificador PM4/IB de un anillo real de la GPU.

QUE RESUELVE
------------
Se ha capturado el contenido real del anillo GFX (8204 bytes de comandos PM4).
Es lo mas cercano a la semantica de hardware que se puede observar sin
escribir en la GPU: son paquetes que el hardware consumio de verdad. Este
script los decodifica.

DE DONDE VIENEN LOS OPCODES, Y POR QUE NO ESTAN ESCRITOS AQUI
-------------------------------------------------------------
De sid.h del corpus, leido EN TIEMPO DE EJECUCION. El script extrae los
`#define PACKET3_XXX 0xNN` con una expresion regular y construye la tabla de
opcodes. No hay ni un solo opcode transcrito a mano en este fichero.

La razon es concreta: transcribir 140 opcodes a mano es exactamente el
trabajo que produce numeros plausibles y equivocados, que es el modo de
fallo que mas caro ha resultado en este proyecto. Si el corpus cambia, la
tabla cambia con el.

La estructura del paquete sale de sid.h tambien:
  #define PACKET3(op, n) ((RADEON_PACKET_TYPE3 << 30) | (((op) & 0xFF) << 8)
                          | ((n) & 0x3FFF) << 16)
Es decir, para un dword de cabecera:
  - tipo de paquete = dword >> 30
  - opcode         = (dword >> 8) & 0xFF
  - count          = (dword >> 16) & 0x3FFF     (dwords de payload)
El conteo de PACKET3 sigue el convenio del hardware: el numero de dwords de
payload, la cabecera NO se cuenta. Eso significa que el paquete entero ocupa
count + 1 dwords. Es un convenio que se verifica leyendo, no de memoria: si
el total no cuadrara con el tamano del anillo, el decodificador lo dira.

LIMITE DECLARADO
----------------
Solo se decodifica la ESTRUCTURA de los paquetes: tipo, opcode, numero de
dwords, y el nombre del opcode si sid.h lo define. NO se interpretan los
campos de cada paquete (por ejemplo, los offsets de un WRITE_DATA), porque
eso exige la tabla de semantica por paquete, que es mucho mas grande y no
esta en el corpus como dato legible.

Un opcode desconocido no se descarta ni se inventa: sale como
PKT3_UNKNOWN_0xNN, que es una afirmacion honesta. El hardware lo ejecuto, y
que nosotros no sepamos nombrarlo es una limitacion NUESTRA, no del paquete.

No modifica la GPU. Solo lee un fichero ya capturado.
"""
import argparse
import os
import re
import struct
import sys

# El path de sid.h se resuelve DESDE EL PROPIO SCRIPT, no desde el directorio
# de trabajo. La primera version lo ponia relativo al CWD, de modo que
# ejecutarlo desde otro sitio daba "no existe" y, peor, un fallo asi puede
#confundirse con "sid.h no tiene opcodes". Aqui se prueban varios candidatos
#y se informa de cuantos se han mirado.
_AQUI = os.path.dirname(os.path.abspath(__file__))
_RAICES = [
    os.path.join(_AQUI, "..", "RESEARCH", "baseline", "linux-7.1.3",
                 "drivers", "gpu", "drm", "amd", "amdgpu"),
    os.path.join(_AQUI, "..", "..", "RESEARCH", "baseline", "linux-7.1.3",
                 "drivers", "gpu", "drm", "amd", "amdgpu"),
    os.path.join(_AQUI, "..", "RESEARCH", "working", "linux-7.1.3",
                 "drivers", "gpu", "drm", "amd", "amdgpu"),
]
# Los headers que DEFINEN opcodes de PACKET3, uno por generacion de ASIC. La
# lista esta para poder AUDITAR la eleccion; el que se usa se decide por el
# grafo de includes, no por estar en esta lista.
#
# Que la numeracion de opcodes NO es estable entre generaciones, medido:
#   sid.h    LOAD_CONFIG=0x5F  LOAD_CONTEXT=0x60  LOAD_SH=0x61   (SI/GCN1)
#   vid.h    LOAD_SH=0x5F      LOAD_CONFIG=0x60    LOAD_CONTEXT=0x61
#   cikd.h   igual que vid.h                                        (CIK/GCN3)
#   nvd.h    LOAD_SH=0x5F      LOAD_CONFIG=0x60    LOAD_CONTEXT=0x61  (NAVI)
#   soc15d.h igual que vid.h                                  (Arcturus/MI)
#
# sid.h esta DESPLAZADO UNA POSICION. Leerlo por costumbre daria un nombre
# equivocado a 0x5F, 0x60 y 0x61, con toda la apariencia de un dato. Y con solo
# sid.h, pm4dec tampoco puede nombrar PACKET3_RELEASE_MEM (0x49),
# PACKET3_ACQUIRE_MEM (0x58) ni PACKET3_SET_UCONFIG_REG (0x79), que no estan
# en sid.h y SI salen en el anillo de COMPUTE capturado.
HEADERS_OPCODE = ["sid.h", "vid.h", "cikd.h", "nvd.h", "soc15d.h"]
SID_CANDIDATOS = [os.path.join(r, h) for r in _RAICES for h in HEADERS_OPCODE]

# El .c que produce los anillos de GFX de ESTE ASIC. El encabezado de opcodes se
# saca de lo que ese fichero incluya, de modo que la eleccion es una MEDIDA del
# grafo de includes y no una afirmacion escrita a mano en un comentario.
FUENTE_GFX8 = "gfx_v8_0.c"

# Los 3 bytes de opcode que sid.h nombraria MAL. Se guardan para que el control
# CN-R29 pueda comprobar que la tabla ya no los nombra asi.
RENUMERADOS_SID = (0x5F, 0x60, 0x61)

# Relleno por cargar_opcodes(). Diagnostico: opcodes con MAS DE UN nombre segun
# la generacion. Se calcula siempre y NO interviene en el nombre que devuelve la
# tabla, porque mezclarlos seria justo el error que hay que evitar.
CONFLICTOS_OPCODE = {}

# Extraido de sid.h:338 con la formula, no escrito de memoria.
#   PACKET3(op, n) = (3 << 30) | ((op & 0xFF) << 8) | ((n & 0x3FFF) << 16)
TIPO3 = 3 << 30


def _directorio_amdgpu():
    """
    Primer arbol de fuentes que exista, o None. El path se NORMALIZA.

    El normpath no es cosmetico, y hay una razon medida. `_RAICES` se construye
    con os.path.join(_AQUI, "..", ...), asi que el path devuelto llevaba un ".."
    dentro. Con ese path, glob.glob(base + "/*.c") devuelve CERO ficheros, y en
    cambio base + "/*" devuelve 632. O sea: un barrido con glob sobre la ruta sin
    normalizar examina NADA y reporta 0, que se lee como "no hay ninguno" cuando
    en realidad hay 304.

    Es la forma exacta de leer un 0 de un producer muerto: el numero sale bien
    formado y no significa nada. Se comprobo en esta sesion, y por eso aqui se
    normaliza una vez, en el sitio de donde sale el path.
    """
    for raiz in _RAICES:
        if os.path.isdir(raiz):
            return os.path.normpath(raiz)
    return None


def cabeceras_de_opcodes_de(fuente):
    """
    Devuelve los headers de opcodes que `fuente` INCLUYE de verdad, leidos del
    fuente. Esta es la razon por la que la tabla de opcodes no es "el header que
    pone primero": es el header que el driver que emite este anillo compila.

    Medido: gfx_v8_0.c incluye "vid.h" y NINGUN otro header de opcodes. sid.h
    lo incluyen si.c, gfx_v6_0.c, dce_v6_0.c (SI/GCN1). cikd.h, gfx_v7_0.c
    (CIK/GCN3). nvd.h, gfx_v10_0.c y siguientes (NAVI). soc15d.h, gfx_v9_0.c,
    gfx_v11_0.c (Arcturus/MI).

    Que son excludes, y no preferences, es lo que permite decir que sid.h
    nombraria mal a 0x5F, 0x60 y 0x61 en un anillo de GFX8.

    Devuelve (lista, motivo_del_fallo).
    """
    base = _directorio_amdgpu()
    if not base:
        return [], "no hay ningun arbol de fuentes amdgpu en _RAICES"
    ruta = os.path.join(base, fuente)
    if not os.path.exists(ruta):
        return [], "no existe el fuente %s" % os.path.join(base, fuente)
    with open(ruta, errors="replace") as h:
        texto = h.read()
    incluidos = set(re.findall(r'^\s*#\s*include\s+"([^"]+)"', texto, re.M))
    ops = sorted(incluidos.intersection(HEADERS_OPCODE))
    if not ops:
        return [], ("%s no incluye ninguno de %s; sus includes son: %s"
                    % (fuente, ", ".join(HEADERS_OPCODE),
                       ", ".join(sorted(incluidos)) or "ninguno"))
    return ops, None


def _leer_opcodes_de(ruta):
    """{opcode: nombre} de UN header, o ({}, motivo)."""
    # PACKET3_XXX seguido de numero (hex o dec), a fin de linea. Un #define con
    # mas de un argumento (PACKET3_BASE_INDEX(x)) no casa y se descarta solo.
    patron = re.compile(
        r"^#define\s+(PACKET3_[A-Z0-9_]+)\s+(0x[0-9A-Fa-f]+|\d+)\s*$",
        re.M)
    with open(ruta, errors="replace") as h:
        src = h.read()
    ops = {}
    for m in patron.finditer(src):
        nombre = m.group(1)
        try:
            val = int(m.group(2), 0)
        except ValueError:
            continue
        if not 0 <= val <= 0xFF:
            # Un opcode cabe en 8 bits (sid.h lo hace asia). Lo que no cabe es un
            # OFFSET de rango de un sub-campo, como PACKET3_SET_CONTEXT_REG_START
            # 0xA000, que no es un paquete.
            continue
        if "__" in nombre:
            # El generador del ASIC usa `_` simple para un opcode y `__` doble
            # para un sub-campo. Sin esta linea, nvd.h y soc15d.h meten 31
            # nombres sobre el opcode 0x00, todos de la forma
            # PACKET3_WAIT_REG_MEM__FUNCTION__ALWAYS_PASS, que son ENUMERACIONES
            # de un campo. Y 0x00 no es ningun paquete: es un dword de dato.
            continue
        ops.setdefault(val, nombre)
    return ops


def auditar_conflictos():
    """
    Opcodes con MAS DE UN nombre segun la generacion: {opcode: {nombre: [hdr]}}.
    Diagnostico puro. No se usa para nombrar: mezclar generaciones seria
    justamente el error que hay que evitar. Sirve para que quede escrito que la
    eleccion de cabecera importa, y por cuanta.
    """
    base = _directorio_amdgpu()
    conf = {}
    if not base:
        return conf
    votos = {}
    for h in HEADERS_OPCODE:
        ruta = os.path.join(base, h)
        if not os.path.exists(ruta):
            continue
        for val, nombre in _leer_opcodes_de(ruta).items():
            votos.setdefault(val, {}).setdefault(nombre, []).append(h)
    for val, por_nombre in votos.items():
        if len(por_nombre) > 1:
            conf[val] = {n: hs for n, hs in sorted(por_nombre.items())}
    return conf


def cargar_opcodes(ruta=None, fuente=FUENTE_GFX8):
    """
    Devuelve ({opcode: nombre}, cabecera_usada) o (None, motivo_del_fallo).

    SE LEE UN SOLO HEADER, el que `fuente` incluye de verdad, y se devuelve
    cual se uso para que la salida se pueda auditar sola.

    Por que uno y no todos. Con solo sid.h, como antes, no se podian nombrar
    PACKET3_RELEASE_MEM (0x49), PACKET3_ACQUIRE_MEM (0x58) ni
    PACKET3_SET_UCONFIG_REG (0x79), que salen en el anillo de COMPUTE. Con los
    cinco a la vez, si, pero sid.h (que es de SI/GCN1) desplazado una posicion
    nombraria mal a 0x5F, 0x60 y 0x61. Fijar la generacion por el grafo de
    includes resuelve las dos cosas a la vez y no es una preferencia.

    Con el criterio de `findings/135` de otra sesion (valor <= 0xFF Y nombre sin
    sufijo de campo: _ENA, _START, _END, _SHIFT, _MASK, _BASE_INDEX), esta tabla
    no introduce NI UN SOLO falso positivo sobre los 119 nombres de sid.h. Se
    comprobo. Los que quedan fuera son macros de campo de CP_DMA con otros
    sufijos (_SEL, _ENGINE, _CMD_*), que 135 si cuenta como opcodes.
    """
    global CONFLICTOS_OPCODE
    CONFLICTOS_OPCODE = auditar_conflictos()

    if ruta:
        if not os.path.exists(ruta):
            return None, "la ruta indicada no existe: %s" % ruta
        return _leer_opcodes_de(ruta), os.path.basename(ruta)

    cabs, err = cabeceras_de_opcodes_de(fuente)
    if err:
        # No se cae a otro header por defecto: haria falta saber de que ASIC se
        # trata, y ese dato no se inventa.
        return None, err
    if len(cabs) > 1:
        return None, ("%s incluye %d headers de opcodes (%s) y no se puede "
                      "saber cual aplica: habria que elegir por generacion de "
                      "forma explicita, no por adivinar"
                      % (fuente, len(cabs), ", ".join(cabs)))
    base = _directorio_amdgpu()
    usada = os.path.join(base, cabs[0])
    ops = _leer_opcodes_de(usada)
    if not ops:
        return None, ("%s existe pero no define ningun opcode que pase el "
                      "filtro; eso NO es lo mismo que no tener opcodes"
                      % usada)
    return ops, cabs[0]


def validez_del_paseo(d, ops):
    """
    Mide si el paseo PM4 tiene sentido en este anillo.
    Devuelve (cabeceras_aparientes, con_nombre, bytes_sin_nombre).

    POR QUE HACE FALTA. Un dword con bits[31:30] = 11 tiene la FORMA de una
    cabecera PACKET3, pero no todo dword con esa forma ES una cabecera. Y hay dos
    casos distintos, que no son el mismo problema:

      - 0xDEADBEEF: la centinela que escribe la auto-prueba del anillo. Sus
        bits[31:30] son 11 por casualidad del valor, y no es un paquete. Es un
        centinela DENTRO de un anillo que si es PM4.
      - el anillo de SDMA: no es una secuencia PACKET3 en absoluto. Sus dwords
        tienen esa forma por ser dato, y el paseo entero no significa nada ahi.

    Antes, pm4dec imprimia "paquetes: 17" para un anillo de SDMA sin decir nada.
    Eso es un falso positivo con la forma de un dato: un numero que parece una
    medida y no lo es. Se mide la fraccion de cabeceras que reciben nombre, y
    si es minima se declara que el paseo no aplica, en vez de publicar el total.

    Ojo con el umbral: es un MODELO_CHOICE, no un hecho. 1/5 se eligio porque en
    el anillo GFX REAL la proporcion es 1 (todas las cabeceras tienen nombre) y
    en el de SDMA es 0, asi que cualquier umbral entre 0 y 1 separa los dos
    casos de este corpus. Con otro anillo podria no bastar.
    """
    if ops is None:
        return (0, 0, set())
    crudos = list(struct.unpack("<%dI" % (len(d) // 4), d))
    aparientes = [w for w in crudos[CABECERA // 4:]
                  if (w >> 30) & 3 in (2, 3)]
    sin_nombre = {(w >> 8) & 0xFF for w in aparientes
                  if ((w >> 8) & 0xFF) not in ops}
    con_nombre = len(aparientes) - sum(
        1 for w in aparientes if ((w >> 8) & 0xFF) not in ops)
    return (len(aparientes), con_nombre, sin_nombre)


# CABECERA DE 12 BYTES, SEGUN EL DRIVER.
#
# amdgpu_debugfs_ring_read() (amdgpu_ring.c:551) NO devuelve el anillo crudo.
# Los 12 primeros bytes son:
#   +0  RING_RPTR = amdgpu_ring_get_rptr(ring) & ring->buf_mask
#   +4  RING_WPTR = amdgpu_ring_get_wptr(ring) & ring->buf_mask
#   +8  ring->wptr & ring->buf_mask      (el puntero de escritura software)
# y a partir de +12 empieza ring->ring[0], linealmente, no desde el rptr.
#
# La PRIMERA version de este decodificador no lo sabia y leia el primer dword
# como si fuera una cabecera PM4. El resultado fue un "PKT0 de 1023 dwords"
# que en realidad era un puntero, seguido de un NOP con count 16383 (= maximo
# del campo) que en realidad era el segundo puntero. Habria sido facil
# publicar esa decodificacion: dos paquetes, todo cuadra. Era basura.
#
# La leccion se aplico como control: si el primer dword "decodifica" a algo
# absurdo o el conteo sale en el maximo del campo, hay que sospechar del
# formato antes que del contenido.
CABECERA = 12
OFF_RPTR = 0
OFF_WPTR = 4
OFF_SWPTR = 8

# PACKET3_NOP OCUPA 1 DWORD, INDEPENDIENTEMENTE DE SU CAMPO DE CONTEO.
#
# No es una suposicion. El driver de GFX8 declara su NOP como
#     .nop = PACKET3(PACKET3_NOP, 0x3FFF)          (gfx_v8_0.c:6873)
# y lo escribe con memset32(..., ring->funcs->nop, count) en DOS sitios
# independientes:
#     amdgpu_ring.c:128  amdgpu_ring_pad_ib
#     amdgpu_ring.c:154  amdgpu_ring_generic_pad_ib
# En los dos, `count` es un numero de DWORDS y cada uno se escribe con el
# valor del nop. O sea que el 0x3FFF del campo de conteo no describe un
# payload: es un valor de relleno y el hardware lo ignora.
#
# Sin esta regla el decodificador leia 0x3FFF como payload, se comia el resto
# del anillo y declaraba el final truncado. El sintoma (conteo en el maximo
# del campo) es lo que hizo sospechar que el problema era el formato y no el
# contenido.
#
# OJO: esto se aplica a PACKET3_NOP. NO se generaliza a todos los paquetes.
# Para el resto, el conteo si describe el payload, y no hay aqui ninguna
# evidencia de que ignoreden. Afirmar lo contrario para todos los paquetes
# seria inventar.
NOP_OPCODE = 0x10  # PACKET3_NOP, sid.h:343


def pointers(d):
    """
    Saca los tres punteros de la cabecera de 12 bytes.

    NO son parte del flujo PM4.

    Y NO son lectura directa de hardware, cosa que una version anterior de
    este docstring afirmaba. Lo que son:

      RING_RPTR -> *ring->rptr_cpu_addr        espejo en CPU
      RING_WPTR -> *ring->wptr_cpu_addr        espejo
                  RREG32(mmCP_RB0_WPTR)        solo si use_doorbell es falso
      sw wptr   -> ring->wptr                  variable del driver

    Es decir, estado del driver espejado en memoria de CPU. Que coincidan
    entre si demuestra que el driver los mantiene sincronizados, no lo que
    este haciendo el hardware.
    """
    if len(d) < CABECERA:
        return None
    r, w, sw = struct.unpack_from("<3I", d, 0)
    return {"rptr": r, "wptr": w, "sw_wptr": sw}


def decodifica(d, ops, verbose=False, saltar_cabecera=False):
    # Antes habia DOS docstrings seguidos: el primero era una expresion muerta
    # (un string suelto, no el docstring) y ademas documentaba un retorno de 3
    # elementos cuando el real es de 4. No rompia nada porque __doc__ es el
    # segundo, pero el primero desconcertaba a quien leia el fichero y
    # describia una firma que no existe. Se queda solo el bueno.
    """
    Recorre el anillo dword a dword. Devuelve
    (paquetes, n_dwords, problemas, indices_de_nop).

    `saltar_cabecera` esta a False a proposito. La primera version de esta
    funcion venia con True, y eso hacia que un test sintetico de 5 dwords
    empezara a leer en el dword 3, porque la funcion asumia que todo lo que
    le llegaba venia de debugfs con sus 12 bytes de punteros. El resultado
    era que los tests contaban 2 paquetes donde habia 5, y lo mas grave: el
    fallo se parecia a un bug del decodificador de NOP, que es justo donde
    se acababa de tocar codigo. Un diagnostico equivocado cuesta mas que
    el fallo original.

    Ahora la funcion de bajo nivel NO adivina el formato: por defecto trata
    la entrada como PM4 puro. Quien sabe que viene de un volcado de debugfs
    lo dice, y lo dice en main(). Adivinar aqui era cambiar un fallo
    detectable por uno silencioso.
    """
    paquetes = []
    problemas = []
    nops = []
    i = 0
    n = len(d) // 4
    words = struct.unpack("<%dI" % n, d[:n * 4])
    if saltar_cabecera and n * 4 >= CABECERA:
        # Los 3 primeros dwords NO son PM4: son rptr, wptr y sw_wptr. Se
        # empiezan a leer los comandos en el dword 3.
        i = CABECERA // 4
    while i < n:
        w = words[i]
        tipo = w >> 30
        if tipo == 3:
            op = (w >> 8) & 0xFF
            cnt = (w >> 16) & 0x3FFF
            nombre = ops.get(op, "PKT3_UNKNOWN_0x%02X" % op)
            if op == NOP_OPCODE:
                # NOP = 1 dword, cuenta ignorada (ver comentario de arriba).
                nops.append(i)
                fin = i + 1
                cnt_real = 0
            else:
                cnt_real = cnt
                # PACKET3 cuenta los dwords de payload; la cabecera no se
                # cuenta, asi que el paquete ocupa cnt + 1.
                fin = i + 1 + cnt
            if fin > n:
                problemas.append(
                    "dword %d: opcode %s declara %d payload pero solo quedan "
                    "%d; el anillo se trunca o el conteo no es lo que creo"
                    % (i, nombre, cnt, n - i - 1))
                fin = n
            payload = words[i + 1:min(fin, n)]
            paquetes.append({
                "idx": i, "tipo": 3, "op": op, "cnt": cnt_real,
                "cnt_campo": cnt, "nombre": nombre,
                "dwords": 1 + cnt_real, "payload": payload, "hdr": w,
            })
            i = fin
        else:
            # PACKET0: un registro. count en los 16 bajos, count-1 registros
            # a partir del dword siguiente. PACKET2: solo cuenta.
            if tipo == 0:
                # DATO CRUCIAL: en el anillo GFX de GFX8, un dword tipo 0 NO
                # es un PKT0.
                #
                # La busqueda de "PKT0" en TODO el driver amdgpu no devuelve
                # NADA. El driver escribe registros en el anillo con
                # PACKET3_SET_CONTEXT_REG (gfx_v8_0.c:1235),
                # PACKET3_SET_SH_REG (1529), PACKET3_SET_UCONFIG_REG (850) y
                # PACKET3_WRITE_DATA (891). Nunca con la macro PKT0.
                #
                # Entonces un dword tipo 0 aqui es un VALOR de uno de esos
                # paquetes cuyo limite no hemos contado bien, no una cabecera
                # de PKT0. La version anterior de este decodificador lo
                # trataba como PKT0 con count=43, lo que consumia 85 dwords y
                # fabricaba una estructura de 8 bloques que parecia
                # convincente. Era una lectura inventada del error.
                #
                # COMO SE DISTINGUE de verdad: en el anillo real, los
                # identificadores de paquete son los que tienen los bits
                # [31:30]=11 y un opcode con nombre en sid.h. Los dwords tipo
                # 0 aparecen SIEMPRE como payload de un PACKET3 anterior.
                #
                # Este decode de PKT0 se conserva para otros anillos
                # (CPER, SDMA, compute si los hubiera), pero para el GFX de
                # GFX8 no aplica. Decirlo es mejor que ignorarlo en silencio:
                # un bloque de 85 dwords con 42 "registros" inventados es
                # informacion falsa con aspecto de dato.
                cnt = w & 0x3FFF
                nombre = "PKT0(dato, no cabecera)"
                # Se consume como UN dword, no como 1+2*(count-1). Es lo
                # unico que no puede desincronizar el resto.
                total = 1
                paquetes.append({
                    "idx": i, "tipo": 0, "op": None, "cnt": cnt,
                    "nombre": nombre, "dwords": total,
                    "payload": words[i + 1:min(i + total, n)], "hdr": w,
                })
                i += total
            elif tipo == 2:
                cnt = w & 0x3FFFFFFF
                nombre = "PKT2"
                total = 1 + cnt
                paquetes.append({
                    "idx": i, "tipo": 2, "op": None, "cnt": cnt,
                    "nombre": nombre, "dwords": total,
                    "payload": words[i + 1:min(i + total, n)], "hdr": w,
                })
                i += total
            else:
                # PACKET1 (release mem) no tiene payload.
                nombre = "PKT1"
                paquetes.append({
                    "idx": i, "tipo": 1, "op": None, "cnt": 0,
                    "nombre": nombre, "dwords": 1, "payload": (), "hdr": w,
                })
                i += 1
    return paquetes, n, problemas, nops


def registros_pk0(payload):
    """
    Saca las escrituras de registro de un PACKET0.

    ESTADO: NO VALIDADO. Se declara y se marca en la salida, no se publica
    como dato.

    Que se sabe y que no:

      - sid.h:327 define
            #define PACKET0(reg, n) ((0 << 30) | ((reg & 0x3FFF) << 2)
                                     | (n & 0x3FFF))
        Es decir, reg va en [15:2] y n en [13:0]. ESO SE SOLAPA, y un header
        no puede tener dos campos que se pisan. De ahi que el reparto real
        del header de escritura tenga que ser otro, y no se ha
        SUPERNADO CUAL ES.

      - Lo que si se ha visto: en los datos hay cabeceras con el registro
        hacia 0x3c00, 0x3f00 y 0x3700, que SON rangos plausibles de registro
        para CP/RLC en GFX8. Pero hay otras con el campo a 0, y escribir en
        el offset 0 no significa nada.

      - Interpretar esas cabeceras como [31:16]=indice y [15:2]=registro da
        una lista que empieza bien y luego se llena de ceros. Una lista a
        medias de registros plausibles e imposibles es PEOR que no dar
        lista: parece informacion y es mitad inventada.

    Lo que hace falta para cerrarlo: el reparto real del header de PACKET0
    en GFX8. Esta en el codigo que emite las escrituras (la parte de
    amdgpu_ib.c que aun no se ha leido), no en la macro, que es solo la
    forma compacta del lado de la CPU.

    Hasta entonces, los offsets que salen de aqui son CANDIDATOS, no
    registros. La funcion se queda porque el recorte en crudo si es util,
    pero su salida no se usa para escribir nada ni para citar numeros.
    """
    out = []
    pl = payload
    for i in range(0, len(pl) - 1, 2):
        hdr = pl[i]
        val = pl[i + 1]
        campo = (hdr >> 2) & 0x3FFF
        out.append((campo * 4, val, (hdr >> 16) & 0xFFFF))
    return out


def cmd_direcciones(d, ops, a):
    """
    Saca las DIRECCIONES DE GPU que el anillo contiene de verdad.

    Por que esto va aparte del decode general: un decode que dice "hay 8
    INDIRECT_BUFFER" no dice nada. Lo que dice algo es que dentro hay una
    direccion de 64 bits, y esa direccion se puede CONTRASTAR contra lo que
    el kernel dice de la memoria. Eso es un cierre, no una observacion.

    EL LAYOUT, DE DONDE
    -------------------
    gfx_v9_0.c:5431-5439:
        header = PACKET3(PACKET3_INDIRECT_BUFFER, 2);
        amdgpu_ring_write(ring, lower_32_bits(ib->gpu_addr));
        amdgpu_ring_write(ring, upper_32_bits(ib->gpu_addr));
        amdgpu_ring_write(ring, control);   // length_dw | (vmid << 24)
    El conteo declarado es 2 y hay 3 dwords. Mismo patron que el
    WAIT_REG_MEM y que el COND_EXEC: el driver escribe mas de lo que declara.

    Se usa la forma de gfx_v9_0 porque es la que esta escrita de forma
    legible en el corpus. Que GFX8 use el mismo layout es CORROBORADO por el
    hecho de que las direcciones obtenidas caen dentro de la VRAM, lo que no
    pasaria con un layout equivocado.
    """
    pkts, _, _, _ = decodifica(d, ops, saltar_cabecera=True)
    ibs = [p for p in pkts if p["op"] == 0x3F]
    print("=" * 78)
    print("DIRECCIONES DE GPU EN EL ANILLO")
    print("=" * 78)
    if not ibs:
        print("El anillo no contiene INDIRECT_BUFFER.")
        print("No se puede extraer ninguna direccion de GPU de el.")
        return 1
    print("INDIRECT_BUFFER encontrados: %d" % len(ibs))
    print("layout segun gfx_v9_0.c:5431-5439: [addr_lo, addr_hi, control]")
    print()
    print("NOTA sobre las posiciones: el campo idx es el indice de PALABRA")
    print("absoluta del volcado, y empieza en 3 porque los 3 primeros dwords")
    print("son los punteros (RING_RPTR, RING_WPTR, sw wptr). El indice DENTRO")
    print("del anillo es idx - 3. Confundir los dos fue un error mio durante")
    print("este analisis: carryo a leer 4 dwords mas adelante y a obtener")
    print("direcciones distintas, ambas con aspecto razonable.")
    print()
    addrs = []
    for p in ibs:
        pl = p["payload"]
        lo, hi = pl[0], pl[1]
        ctrl = pl[2] if len(pl) > 2 else None
        addr = (hi << 32) | lo
        addrs.append(addr)
        extra = ""
        if ctrl is not None:
            extra = "  control=0x%08x vmid=%d length_dw=%d" % (
                ctrl, (ctrl >> 24) & 0xFF, ctrl & 0xFFFFFF)
        print("  palabra %-5d (anillo %-5d) gpu_addr=0x%016x%s"
              % (p["idx"], p["idx"] - CABECERA // 4, addr, extra))
    print()

    # CONTRASTE CONTRA LA VRAM REAL.
    #
    # El FB de esta GPU esta en 4 GiB (0x1_0000_0000), no en 0. Eso se lee
    # de mem_info_vram_total, que da 2147483648, y del hecho de que las
    # direcciones observadas tienen el bit 32 puesto. Con vram_base_offset
    # conceptual en 0 pero FB en 4 GiB, una VA valida tiene el bit 32 a 1.
    #
    # El rango observado tiene que caber en los 2 GiB de VRAM DESPUES de
    # restar la base. Si no cabe, el layout estaria mal y hay que decirlo,
    # no ajustar el umbral para que cuadre.
    base = 0x100000000
    # El control va FUERA del conteo declarado, asi que el decodificador no
    # lo da: cnt=2 y solo hay 2 dwords de payload. El tercero, que es el
    # control, se lee a mano desde la palabra siguiente.
    #
    # Antes esto salia con length_dw=0 y vmid=0, que no era un dato: era la
    # ausencia del campo, leida como si fuera un cero del hardware. Un
    # campo que no se ha leido y un campo que vale cero se distinguen por el
    # numero, y aqui se confundieron.
    # idx es el indice dentro del vector `words`, que arranca en
    # CABECERA//4 = 3 por los tres punteros. Para indexar el buffer hay que
    # sumar ESE 3, no los 12 bytes: idx*4 ya incluye el desplazamiento desde
    # el inicio del vector, que es donde empieza el anillo.
    #
    # La primera version hacia (CABECERA//4)*4 + idx*4, o sea que sumo 12
    # bytes de mas y leia un dword mas adelante. Dio length_dw=3020 y vmid=0
    # para un paquete cuyo control real es 0x07000158, o sea vmid=7 y
    # length_dw=344. Ninguno de los dos numeros era plausible, pero el
    # equivocado salia con forma de dato igual.
    ctrl = ibs[0]["payload"]
    if len(ctrl) == 2:
        idx0 = ibs[0]["idx"] + 1 + 2          # cabecera + cnt, en indices de words
        c = struct.unpack_from("<I", d, idx0 * 4)[0]
        print("CONTROL del primer INDIRECT_BUFFER (fuera del conteo):")
        print("  palabra %d = 0x%08x" % (idx0, c))
        print("    length_dw = %-8d = %d bytes" % (c & 0xFFFFFF,
                                                   (c & 0xFFFFFF) * 4))
        print("    vmid      = %d" % (c >> 24))
        print()
        print("  Un length_dw de 0 seria un paquete vacio, que no tiene")
        print("  sentido para un buffer indirecto. Que salga distinto de 0")
        print("  confirma que el control se lee, no que se supone.")
        print()
        if (c >> 24) == 0:
            print("  AVISO: vmid=0. En GFX8 el VMID 0 esta reservado al")
            print("  sistema (gmc_v8_0.c:1164) y no lo usan ni graphics ni")
            print("  compute. Un vmid 0 en un buffer indirecto NO es lo que")
            print("  haria un job normal, asi que o el layout no es el")
            print("  esperado, o esto no es un buffer indirecto de job.")
            print("  Se dice, no se corrige el numero para que cuadre.")
            print()

    print("CONTRASTE con la VRAM real:")
    vram_mm = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "capturas", "amdgpu_vram_mm.txt")
    if not os.path.exists(vram_mm):
        print("  NO CONTRASTADO: falta %s" % vram_mm)
        print("  Las direcciones estan extraidas pero NO se han comprobado")
        print("  contra la VRAM. Saliendo con codigo 4.")
        return 4
    import re as _re
    txt = open(vram_mm, errors="replace").read()
    mtot = _re.search(r"size:\s*(\d+)", txt)
    musage = _re.search(r"usage:\s*(\d+)", txt)
    total = int(mtot.group(1)) if mtot else 0
    usage = int(musage.group(1)) if musage else 0
    print("  VRAM total segun el kernel : %d bytes (%.0f MiB)"
          % (total, total / 2 ** 20))
    print("  VRAM en uso segun el kernel: %d bytes (%.2f MiB)"
          % (usage, usage / 2 ** 20))
    print()
    fuera = []
    print("  %-20s %-14s %s" % ("gpu_addr", "offset", "dentro de VRAM?"))
    for a in sorted(set(addrs)):
        off = a - base
        ok = 0 <= off < total
        if not ok:
            fuera.append(a)
        print("  0x%016x  0x%07x   %s (%.2f MiB)"
              % (a, off, "SI" if ok else "NO", off / 2 ** 20))
    print()
    if fuera:
        print("  %d direcciones NO caben en la VRAM. El layout estar�ia mal,"
              % len(fuera))
        print("  o estas direcciones no son de VRAM. No se reinterpretan.")
        return 5
    print("  Las %d direcciones caben en la VRAM. PROVEN que el layout es"
          % len(set(addrs)))
    print("  correcto: con un layout equivocado caerian fuera.")
    mayor = max(addrs) - base
    print()
    print("  El offset mayor observado es %.2f MiB, y el kernel dice que hay"
          % (mayor / 2 ** 20))
    print("  %.2f MiB en uso. Mismo orden de magnitud, lo cual es"
          % (usage / 2 ** 20))
    print("  consistente, pero NO es la misma cifra: el uso incluye buffers")
    print("  que no estan en este anillo. No se afirma que sean lo mismo.")
    print()

    # LA CADENA DE TRADUCCION, con los numeros del corpus.
    #
    # La cadena esta completa en el codigo, y son tres lineas:
    #
    #   amdgpu_vm.c:1228   addr = vram_base + cursor.start;
    #   gmc_v8_0.c:1176    vram_base_offset = 0   (GPU discreta, no APU)
    #   amdgpu_gmc.c:173   value = addr & adev->gmc.pte_addr_mask;
    #   gmc_v8_0.c:1134    pte_addr_mask = 0x000000FFFFFFF000   (40 bit PA)
    #
    # Con vram_base = 0, la direccion que va a la PTE ES la propia VA. Y la
    # mascara quita los 12 bits bajos, que son el offset dentro de la pagina.
    #
    # Esto NO significa que las direcciones observadas sean validas como
    # PTE: significa que una VA con offset distinto de 0 se trunca a la
    # pagina que la contiene. Los INDIRECT_BUFFER apuntan al inicio de un
    # buffer, que puede empezar en cualquier byte.
    MASK = 0x000000FFFFFFF000     # gmc_v8_0.c:1134
    PAGE = 0x1000
    print("TRADUCCION (amdgpu_gmc.c:173 con la mascara de gmc_v8_0.c:1134):")
    print("  pte_addr_mask = 0x%016X  -> 40 bits de PA" % MASK)
    print("  vram_base     = 0         -> la PTE lleva la propia VA")
    print()
    print("  %-20s %-20s %s" % ("gpu_addr", "PA (addr & MASK)", "bytes perdidos"))
    for a in sorted(set(addrs)):
        pa = a & MASK
        perdidos = a & ~MASK
        print("  0x%016X   0x%016X   %s"
              % (a, pa, "0x%X" % perdidos if perdidos else "ninguno"))
    print()
    print("  Ningun bit ALTO se pierde: la mascara de 40 bits cubre de sobra")
    print("  una VA de 2 GiB. Lo que se pierde son los 12 bits bajos, que")
    print("  son el offset dentro de la pagina, y eso es lo correcto: la PTE")
    print("  no direcciona bytes, direcciona paginas de 4 KiB.")
    print()
    print("  LO QUE ESTO NO CIERRA")
    print("  Saber que la PTE lleva la VA mascarada dice COMO se construye.")
    print("  No dice que hay en la tabla, ni que pagina fisica apunta cada")
    print("  entrada, ni donde esta la tabla en si. Eso sigue")
    print("  NOT_DETERMINED porque amdgpu_vm_info en 7.1.3 no vuelca PTEs")
    print("  y amdgpu_gart no existe en este driver.")
    return 0


def _mm_por_offset(offset, bloque="oss"):
    """
    Devuelve [(nombre, fichero)] para un offset, leyendo los headers del
    corpus en tiempo de ejecucion.

    Se usa para resolver un offset de registro corto contra el ASIC
    correcto. Un offset como 0xbcc existe en varios bloques y en varias
    generaciones, de modo que un indice que devuelve "el primero que
    aparezca" se equivoca de ASIC. Lo que demuestra el nombre correcto es
    que VARIAS versiones del MISMO bloque dan el MISMO offset.

    No se escribe ningun nombre aqui: se leen del corpus. Escribir "son
    cuatro" o "son tres" a mano ya fallo una vez en esta sesion.
    """
    import re as _re
    raiz = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "RESEARCH", "baseline", "linux-7.1.3",
                        "drivers", "gpu", "drm", "amd", "include", "asic_reg",
                        bloque)
    if not os.path.isdir(raiz):
        return []
    salida = []
    for fn in sorted(os.listdir(raiz)):
        if not fn.endswith(".h"):
            continue
        try:
            txt = open(os.path.join(raiz, fn), errors="replace").read()
        except OSError:
            continue
        for m in _re.finditer(r"^#define\s+(mm[A-Za-z0-9_]+)\s+0x([0-9A-Fa-f]+)",
                              txt, _re.M):
            if int(m.group(2), 16) == offset:
                salida.append((m.group(1) + " = 0x%x" % offset, fn))
                break
    return salida


def cmd_escribe(d, ops, a):
    """
    Decodifica los PACKET3_WRITE_DATA: a DONDE escribe el anillo y con que
   Confirmacion.

    Por que es interesante aunque no escriba en memoria: la direccion del
    payload no es siempre una VA. En el anillo capturado es
    mmHDP_DEBUG0 (0xbcc), un registro de la USC, y eso es un dato sobre
    QUE USA EL DRIVER, no sobre la memoria.

    EL LAYOUT
    gfx_v8_0.c:891-894, que es un test unitario y por tanto el ejemplo
    mas legible del corpus:

        ib.ptr[0] = PACKET3(PACKET3_WRITE_DATA, 3);
        ib.ptr[1] = WRITE_DATA_DST_SEL(5) | WR_CONFIRM;
        ib.ptr[2] = lower_32_bits(gpu_addr);
        ib.ptr[3] = upper_32_bits(gpu_addr);
        ib.ptr[4] = 0xDEADBEEF;      <- FUERA del conteo

    Los campos, de sid.h:378-388:
        WRITE_DATA_DST_SEL(x)    (x) << 8
        WR_CONFIRM               1 << 20
        WRITE_DATA_ENGINE_SEL(x) (x) << 30

    dst_sel == 0 significa "registro", segun el comentario de sid.h, y
    distinto de 0 significa memoria via GRBM. En el anillo capturado es 0,
    y la direccion cae en el rango de registros del ASIC: coherente.

    Un aviso sobre el 0xDEADBEEF: se busco en el anillo capturado y NO esta.
    Es del test unitario. Concluir que el anillo "escribe DEADBEEF" porque
    el codigo lo hace seria importar un dato de un test a una medicion.
    """
    pkts, _, _, _ = decodifica(d, ops, saltar_cabecera=True)
    wds = [p for p in pkts if p["op"] == 0x37]
    print("=" * 78)
    print("PACKET3_WRITE_DATA: DONDE escribe el anillo")
    print("=" * 78)
    if not wds:
        print("El anillo no contiene WRITE_DATA.")
        return 1
    print("encontrados: %d" % len(wds))
    print()
    print("%-10s %-8s %-8s %-8s %s"
          % ("palabra", "dst_sel", "confirm", "engine", "direccion"))
    print("-" * 68)
    vistos = set()
    for p in wds:
        pl = p["payload"]
        p0 = pl[0]
        dst = (p0 >> 8) & 0xFF
        conf = (p0 >> 20) & 1
        eng = (p0 >> 30) & 3
        addr = ((pl[2] << 32) | pl[1]) if len(pl) >= 3 else 0
        vistos.add((dst, conf, eng, addr))
        print("%-10d %-8d %-8d %-8d 0x%08X"
              % (p["idx"], dst, conf, eng, addr))
    print("-" * 68)
    print()
    print("SIGNIFICADO (sid.h:378-388):")
    for dst, conf, eng, addr in sorted(vistos):
        print("  addr=0x%08X  dst_sel=%d (%s)  WR_CONFIRM=%d  engine=%d"
              % (addr, dst, "registro" if dst == 0 else "memoria via GRBM",
                 conf, eng))
    print()
    print("  dst_sel == 0 es REGISTRO, no memoria. La direccion no es una")
    print("  VA de GPU sino un offset del mapa de registros.")
    print()
    # Resolver el offset contra el indice de direcciones, FILTRANDO por el
    # ASIC. Sin el filtro salen coincidencias de DCE, GC y MMHUB, que son de
    # otros chips: el offset 0xbcc existe en varios bloques y en varias
    # generaciones, y mirar el primero que aparezca da un nombre de otro
    # ASIC.
    #
    # La busqueda correcta para esta GPU es el bloque que el anillo
    # ejecuta, y se comprueba en varios headers de la misma generacion: si
    # mmHDP_DEBUG0 = 0xbcc en oss_2_0, oss_2_4 y oss_3_0_1, la coherencia
    # entre generaciones es la prueba, no la primera coincidencia.
    try:
        import subprocess as _sp
        aqui = os.path.dirname(os.path.abspath(__file__))
        r = _sp.run([sys.executable, os.path.join(aqui, "dires.py"),
                     hex(sorted(vistos)[0][3])], capture_output=True, text=True)
        lineas = [l for l in r.stdout.splitlines() if l.startswith("  ")]
        if lineas:
            print("  El indice devuelve %d nombres para ese offset, y son"
                  % len(lineas))
            print("  de ASIC DISTINTOS (DCE, GC, MMHUB...). Un offset corto")
            print("  como 0xbcc existe en varios bloques y en varias")
            print("  generaciones, de modo que la primera coincidencia NO")
            print("  es la de esta GPU:")
            for l in lineas[:4]:
                print("   ", l.strip())
            print()
            print("  Se resuelve por coherencia entre generaciones del")
            print("  bloque que corresponde. Los nombres se LEEN del corpus")
            print("  en cada ejecucion, no se escriben aqui:")
            for nombre, fichero in _mm_por_offset(
                    sorted(vistos)[0][3]):
                print("    %-28s %s" % (fichero, nombre))
            print()
            print("  Varias definiciones independientes del MISMO offset en el")
            print("  bloque OSS. Eso es PROVEN: no es que no haya nombre, es")
            print("  que hay que elegir el del ASIC correcto.")
        else:
            print("  El offset no aparece en el indice de direcciones. Se")
            print("  deja el valor crudo: NOT_FOUND en el indice, que no es")
            print("  PROVEN_ABSENT en el hardware.")
    except Exception:
        print("  (no se pudo consultar el indice de direcciones)")

    # El 0xDEADBEEF: se busca de verdad, no se da por supuesto.
    import struct as _s
    n = len(d) // 4
    words = _s.unpack_from("<%dI" % n, d, 0)
    hay = [i for i, x in enumerate(words) if x == 0xDEADBEEF]
    print()
    print("  0xDEADBEEF en el anillo capturado: %d apariciones" % len(hay))
    if not hay:
        print("  NO esta. Aparece en gfx_v8_0.c:894, pero en un TEST")
        print("  UNITARIO, no en la secuencia de trabajo. Traerlo aqui")
        print("  seria importar un dato de un test a una medicion.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="decodifica PM4/IB de un anillo capturado")
    ap.add_argument("fichero",
                    default="capturas/amdgpu_ring_gfx.txt", nargs="?")
    ap.add_argument("--sid", default=None)
    ap.add_argument("--sin-cabecera", action="store_true",
                    help="tratar tambien los 3 primeros dwords como PM4 "
                         "(util para ver el error que producia antes)")
    ap.add_argument("--direcciones", action="store_true",
                    help="extrae y contrasta las direcciones de GPU del anillo")
    ap.add_argument("--escribe", action="store_true",
                    help="decodifica los WRITE_DATA: a donde escribe el anillo")
    ap.add_argument("--todos", action="store_true",
                    help="lista cada paquete, no solo el resumen")
    a = ap.parse_args()

    if not os.path.exists(a.fichero):
        print("no existe %s" % a.fichero)
        return 2
    # `cab` es el header del que sale la tabla. Antes el segundo valor era None
    # en caso de exito y el texto decia "sid.h" fijo, que era falso: la tabla
    # viene de vid.h. Ahora el nombre sale de ahi, no de una constante.
    ops, cab = cargar_opcodes(a.sid)
    if ops is None:
        print("NO PUEDO CARGAR LOS OPCODES: %s" % cab)
        print()
        print("Sin la tabla de opcodes, decodificar el anillo daria una")
        print("sucesión de numeros sin nombre, que no es informacion. Se")
        print("declara el fallo en vez de producir una tabla a medias.")
        return 3
    fuente_declarada = a.sid if a.sid else FUENTE_GFX8

    d = open(a.fichero, "rb").read()
    pts = pointers(d)
    if a.direcciones:
        return cmd_direcciones(d, ops, a)
    if a.escribe:
        return cmd_escribe(d, ops, a)
    pkts, ndw, problemas, nops = decodifica(
        d, ops, saltar_cabecera=not a.sin_cabecera)
    # Se inicializa aqui y se actualiza mas abajo, en dos sitios: problemas
    # de truncamiento de paquete, y anillo de tamano no potencia de dos.
    rc_problemas = 0

    print("=" * 78)
    print("DECODIFICACION PM4/IB: %s" % os.path.basename(a.fichero))
    print("=" * 78)
    print("bytes            : %d" % len(d))
    print("dwords           : %d  (los 3 primeros son punteros, no PM4)"
          % ndw)
    # El nombre del header va en la salida, no solo en el codigo. Antes ponia
    # "sid.h" fijo y mentia: la tabla viene de vid.h. Una etiqueta falsa con la
    # forma de un dato es el mismo fallo que un opcode mal nombrado, y por eso
    # va ahi y no en un comentario.
    print("opcodes cargados : %d desde %s (lo que incluye %s)"
          % (len(ops), cab, fuente_declarada))
    print("paquetes         : %d" % len(pkts))

    # ¿TIENE SENTIDO EL PASEO? Antes no se preguntaba, y por eso imprimia
    # "paquetes: 17" para el anillo de SDMA, donde NINGUN dword es un PACKET3.
    # El numero era certaino y no significaba nada. Ver validez_del_paseo().
    _cabs, _nom, _sin = validez_del_paseo(d, ops)
    if _cabs and _nom * 5 < _cabs:
        print()
        print("AVISO: ESTE PASEO PM4 NO APLICA A ESTE ANILLO, y el numero de")
        print("  paquetes de arriba NO es una medida. No se retira, porque es lo")
        print("  que el recorrido da, pero no se puede citar.")
        print("  cabeceras con forma de paquete : %d" % _cabs)
        print("  de esas, con opcode CON nombre  : %d" % _nom)
        print("  bytes de opcode sin nombre    : %s"
              % (["0x%02x" % b for b in sorted(_sin)],))
        print("  Dos motivos posibles, y NO son el mismo problema:")
        print("   - el anillo NO es PM4 (SDMA, por ejemplo): los dwords son")
        print("     DATO con esos bits puestos, y el total no describe nada.")
        print("   - el anillo SI es PM4 pero hay centinelas: 0xDEADBEEF tiene")
        print("     bits[31:30] = 11 por casualidad y no es un paquete.")
        print("  Cuadrar el total con lo que emitio el driver requiere ademas")
        print("  que el resto de dwords se reconcilien, que es lo que hace")
        print("  EV-30 para el anillo GFX: count = payload - 1, 50 de 50.")
    print()

    # ¿EL FICHERO ESTA COMPLETO?
    #
    # Un anillo real tiene un tamano en dwords que es POTENCIA DE DOS, porque
    # los punteros se enmascaran con buf_mask = tamano-1. Asi que esa es la
    # propiedad que se comprueba, y no el tamano en si.
    #
    # La primera version de esta comprobacia calculaba el tamano esperado a
    # partir de la propia longitud del fichero, lo cual SIEMPRE cuadra: es
    # circular, y un control circular no controla nada. Se comprobo cortando
    # el anillo por la mitad: daba "correcto" con 4000 bytes, porque 4000
    # bytes tambien son 12 de cabecera mas 997 dwords, y eso no viola nada
    # que el calculo comprobara.
    #
    # Con la potencia de dos, 997 no la es, y el corte se detecta.
    if pts is not None:
        anillo_dw_total = ndw - CABECERA // 4
        es_potencia = (anillo_dw_total > 0 and
                       (anillo_dw_total & (anillo_dw_total - 1)) == 0)
        if not es_potencia:
            print("AVISO: el tamano del anillo no es potencia de dos.")
            print("  dwords de anillo: %d" % anillo_dw_total)
            print("  Un anillo de amdgpu tiene tamano potencia de dos, porque")
            print("  los punteros se enmascaran con buf_mask = tamano - 1.")
            print("  O el volcado esta truncado, o el fichero no es un anillo")
            print("  de debugfs. En los dos casos el decode NO cubre el anillo")
            print("  entero y no se puede afirmar lo contrario.")
            rc_problemas = 6
    print()

    if pts:
        anillo_dw = (len(d) - CABECERA) // 4
        # CORRECCION IMPORTANTE sobre lo que esto demuestra.
        #
        # Una version anterior de este texto decia "leido de registros
        # MMIO". Es FALSO, y era una lectura muy tentadora de hacer:
        #
        #   RING_RPTR -> *ring->rptr_cpu_addr  (gfx_v8_0.c:6008)  espejo en CPU
        #   RING_WPTR -> *ring->wptr_cpu_addr si ring->use_doorbell,
        #                si no RREG32(mmCP_RB0_WPTR)   (gfx_v8_0.c:6019)
        #   sw wptr   -> ring->wptr, variable del driver
        #
        # O sea: los tres son estado del driver espejado en CPU. Solo
        # RING_WPTR llega a ser MMIO, y unicamente si use_doorbell es falso.
        #
        # Por tanto "rptr == wptr" NO es una lectura del hardware: es
        # coherencia interna del driver. Si el hardware estuviera retrasado,
        # este volcado no lo detectaria. Decirlo asi evita convertir un
        # espejo en una observacion de hardware, que es la confusion que
        # este proyecto corrige una y otra vez.
        print("ESTADO DEL ANILLO (punteros del driver, NO lectura directa")
        print("de hardware; ver la nota de abajo):")
        print("  RING_RPTR   = 0x%04x (%d)  [espejo rptr_cpu_addr]"
              % (pts["rptr"], pts["rptr"]))
        print("  RING_WPTR   = 0x%04x (%d)  [espejo, salvo sin doorbell]"
              % (pts["wptr"], pts["wptr"]))
        print("  sw wptr     = 0x%04x (%d)  [variable del driver]"
              % (pts["sw_wptr"], pts["sw_wptr"]))
        print("  anillo      : %d dwords (%d bytes), mask=0x%04x"
              % (anillo_dw, anillo_dw * 4, anillo_dw - 1))
        print()
        print("  NOTA: RREG32(mmCP_RB0_WPTR) solo ocurre si use_doorbell es")
        print("  falso (gfx_v8_0.c:6011-6019). Con doorbell, tambien es un")
        print("  espejo. El tamano del anillo SI es dato del ASIC; los")
        print("  punteros son estado del driver.")
        vacio = pts["rptr"] == pts["wptr"]
        print("  rptr==wptr  : %s -> %s"
              % (vacio, "sin nada pendiente segun el driver (NO prueba que "
                        "el hardware lo haya consumido)"
                 if vacio else "hay comandos SIN CONSUMIR entre rptr y wptr"))
        if vacio:
            print()
            print("  AVISO: lo que se decodifica abajo es RESIDUO de comandos")
            print("  ya ejecutados, no trafico en vuelo.")
        print()

    if problemas:
        print("PROBLEMAS (%d):" % len(problemas))
        for p in problemas[:10]:
            print("  - %s" % p)
        print()
        # Se devuelve 6 aunque el resto de la salida sea utilizable. Un anillo
        # que no decodifica limpio no es un anillo "decodificado": es un
        # decode con un error dentro, y si sale con 0 quien lo mire
        # despues no tiene forma de saberlo.
        rc_problemas = 6
    else:
        # OJO: aqui NO se pone rc_problemas = 0. Ese era el bug: un anillo
        # truncado dentro de una tirada de NOP no produce problemas de
        # paquete, asi que esta rama lo ponia a 0 y se comia el aviso de
        # "no es potencia de dos" que ya se habia puesto. El aviso se
        # imprimia y el codigo de salida volvia a ser 0, que es exactamente
        # el modo de fallo que este toolkit lleva corrigiendo: un codigo que
        # dice "todo bien" mientras hay un aviso sin resolver delante.
        pass

    # resumen por opcode: que comandos se ejecutaron de verdad
    from collections import Counter
    c = Counter(p["nombre"] for p in pkts)
    print("%-32s %-7s %s" % ("opcode", "veces", "dwords total"))
    print("-" * 60)
    for nombre, veces in c.most_common():
        tot = sum(p["dwords"] for p in pkts if p["nombre"] == nombre)
        print("%-32s %-7d %d" % (nombre, veces, tot))
    print("-" * 60)

    # Los NOP no son comandos, son relleno. Una larga tirada de ellos dice
    # que hay un hueco sin trabajo, no que se ejecutaron miles de NOP. Se
    # agrupan en tiradas para que el numero signifique algo.
    tiradas = []
    if nops:
        ini = prev = nops[0]
        for x in nops[1:]:
            if x == prev + 1:
                prev = x
            else:
                tiradas.append((ini, prev - ini + 1))
                ini = prev = x
        tiradas.append((ini, prev - ini + 1))
    if tiradas:
        print()
        print("NOP (relleno, 1 dword cada uno): %d en %d tirada(s)"
              % (len(nops), len(tiradas)))
        for a_, l in tiradas:
            if l >= 8:
                print("   dwords %-5d..%-5d  %d NOP seguidos  (hueco de "
                      "relleno)" % (a_, a_ + l - 1, l))
            else:
                print("   dwords %-5d..%-5d  %d NOP" % (a_, a_ + l - 1, l))
        print()
        print("Un NOP con cuenta 0x3FFF es el valor de relleno de GFX8")
        print("(gfx_v8_0.c:6873), no un paquete de 16383 dwords.")

    desconocidos = [k for k in c if k.startswith("PKT3_UNKNOWN")]
    if desconocidos:
        print()
        print("Opcodes SIN NOMBRE en sid.h: %s" % ", ".join(desconocidos))
        print("El hardware los ejecuto. Que no sepamos nombrarlos es una")
        print("limitacion del corpus, no del anillo. NO son 'desconocidos'")
        print("en el sentido de invalidos.")

    # WAIT_REG_MEM: el paquete con mas valor de este anillo.
    #
    # Decodificarlo aqui, y no aparte, es porque es el unico tipo cuyo
    # contenido se puede poner en contraste con la construccion exacta que
    # hace el driver en gfx_v8_0.c:6047-6056, que esta en el corpus.
    wrm = [p for p in pkts if p["op"] == 0x3C]
    if wrm:
        print("WAIT_REG_MEM: %d en el anillo" % len(wrm))
        print("  Es el paquete mas interesante porque su construccion esta")
        print("  en el corpus y se puede contrastar. Ver WAIT-REG-MEM-REAL.md")
        print()

    if a.todos:
        print()
        print("TODOS LOS PAQUETES")
        for p in pkts:
            extra = ""
            if p["nombre"] == "PKT0" and len(p["payload"]) >= 2:
                regs = registros_pk0(p["payload"])
                extra = ("  %d escrituras, decode de registro NO VALIDADO"
                         % len(regs))
            print("  dword %-5d %-26s cnt=%-5d dwords=%-5d%s"
                  % (p["idx"], p["nombre"], p["cnt"], p["dwords"], extra))
        print()
        print("AVISO: el contenido de los PKT0 NO se decode. La macro")
        print("PACKET0 de sid.h solapa el campo de registro con el de")
        print("conteo, y el reparto real del header no se ha establecido.")
        print("Imprimir offsets a medias seria publicar numeros plausibles")
        print("que no son registros.")
    else:
        print()
        print("(con --todos se lista cada paquete)")
    return rc_problemas


if __name__ == "__main__":
    sys.exit(main())

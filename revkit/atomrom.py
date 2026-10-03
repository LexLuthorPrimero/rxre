#!/usr/bin/env python3
"""
atomrom.py -- parseo del VBIOS ATOM de la RX550.

POR QUE EXISTE
-------------
El VBIOS estaba bloqueado: /sys/class/drm/card1/device/rom es root-only y
amdgpu_bios tambien. Con acceso root, el nodo amdgpu_vbios da 58880 bytes.
Es la primera vez que se ve la configuracion que el firmware declara de esta
GPU, y es la unica fuente que dice cosas que el driver no inventa: de que
memoria esta hecha la VRAM, como es la matriz de clocks, y que tablas existen.

DE DONDE SALEN LOS OFFSETS
--------------------------
Del corpus, no de memoria. Concretamente:

  atom.h:32   ATOM_BIOS_MAGIC     0xAA55
  atom.h:33   ATOM_ATI_MAGIC_PTR  0x30
  atom.h:34   ATOM_ATI_MAGIC      " 761295520"
  atom.h:35   ATOM_ROM_TABLE_PTR  0x48
  atom.h:37   ATOM_ROM_MAGIC      "ATOM"
  atom.h:38   ATOM_ROM_MAGIC_PTR  4
  atom.h:42   ATOM_ROM_CMD_PTR    0x1E
  atom.h:43   ATOM_ROM_DATA_PTR   0x20

Y el layout de la master data table, de
drivers/gpu/drm/amd/include/atombios.h:2783 (ATOM_MASTER_LIST_OF_DATA_TABLES):
35 campos USHORT, tras un ATOM_COMMON_TABLE_HEADER de 4 bytes.

Esto importa porque un offset recordado de memoria puede ser equivocado y
producir una tabla que parece valida. Cada offset de este script se puede
rastrear hasta una linea del corpus.

ENDIANNESS
----------
Todo es little-endian. El driver lo hace con CU16/CU32, que son accesos
directos a memoria sobre una estructura empaquetada en little-endian. El
VBIOS de esta GPU empieza 55 aa, que leido como u16 LE da 0xAA55, y LE es lo
unico que da el valor que el driver busca. LE esta CORROBORADO, no supuesto:
si fuera BE, la firma no casaria y atom.c:1558 rechazaria el ROM.

LIMITE DECLARADO
----------------
Este script NO implementa el decodificado de las 35 tablas. Solo las localiza
y las inventaria. La razon no es pereza: una tabla mal interpetrada da un
numero plausible y falso, que es peor que no tener numero. Se declara aqui
expresamente para que NOT_IMPLEMENTED no se lea como AUSENTE.
"""
import argparse
import hashlib
import io
import os
import struct
import sys

# --- constantes, con su procedencia del corpus ------------------------------
ATOM_BIOS_MAGIC = 0xAA55          # atom.h:32
ATOM_ATI_MAGIC_PTR = 0x30         # atom.h:33
ATOM_ATI_MAGIC = b" 761295520"    # atom.h:34
ATOM_ROM_TABLE_PTR = 0x48         # atom.h:35
ATOM_ROM_MAGIC = b"ATOM"          # atom.h:37
ATOM_ROM_MAGIC_PTR = 4            # atom.h:38
ATOM_ROM_CMD_PTR = 0x1E           # atom.h:42
ATOM_ROM_DATA_PTR = 0x20          # atom.h:43

# atombios.h:2783, en ORDEN. El orden es el layout: son 35 USHORT seguidos.
TABLAS_MASTER = [
    "UtilityPipeLine", "MultimediaCapabilityInfo", "MultimediaConfigInfo",
    "StandardVESA_Timing", "FirmwareInfo", "PaletteData", "LCD_Info",
    "DIGTransmitterInfo", "SMU_Info", "SupportedDevicesInfo", "GPIO_I2C_Info",
    "VRAM_UsageByFirmware", "GPIO_Pin_LUT", "VESA_ToInternalModeLUT",
    "GFX_Info", "PowerPlayInfo", "GPUVirtualizationInfo", "SaveRestoreInfo",
    "PPLL_SS_Info", "OemInfo", "XTMDS_Info", "MclkSS_Info", "Object_Header",
    "IndirectIOAccess", "MC_InitParameter", "ASIC_VDDC_Info",
    "ASIC_InternalSS_Info", "TV_VideoMode", "VRAM_Info", "MemoryTrainingInfo",
    "IntegratedSystemInfo", "ASIC_ProfilingInfo", "VoltageObjectInfo",
    "PowerSourceInfo", "ServiceInfo",
]
HEADER_COMUN = 4  # usStructureSize u16 + 2 uchar  (atombios.h:208)


class RomInvalido(Exception):
    pass


def u8(d, o):
    return d[o]


def u16(d, o):
    """USHORT little-endian, con rango comprobado.

    El rango se comprueba porque leer mas alla del final da un
    struct.error opaco, y un error opaco a las 3 de la manana se confunde
    con un dato malo.
    """
    if o < 0 or o + 2 > len(d):
        raise RomInvalido("u16 en offset %d fuera del ROM (%d bytes)"
                          % (o, len(d)))
    return struct.unpack_from("<H", d, o)[0]


def u32(d, o):
    if o < 0 or o + 4 > len(d):
        raise RomInvalido("u32 en offset %d fuera del ROM (%d bytes)"
                          % (o, len(d)))
    return struct.unpack_from("<I", d, o)[0]


def valida(d):
    """
    Devuelve un dict con lo validado, o lanza RomInvalido.

    Los cuatro controles son los MISMOS que hace el driver en
    amdgpu_atom_parse() (atom.c:1546-1580). No son controles inventados: si
    esta funcion pasa, el driver tambien pasaria, y al reves.
    """
    if len(d) < 0x100:
        raise RomInvalido("ROM demasiado pequeno: %d bytes" % len(d))
    v = {}
    v["bytes"] = len(d)

    # atom.c:1558  if (CU16(0) != ATOM_BIOS_MAGIC)
    v["magic"] = u16(d, 0)
    if v["magic"] != ATOM_BIOS_MAGIC:
        raise RomInvalido("ATOM_BIOS_MAGIC = 0x%04x, esperado 0x%04X"
                          % (v["magic"], ATOM_BIOS_MAGIC))

    # atom.c:1563  strncmp(CSTR(ATOM_ATI_MAGIC_PTR), ATOM_ATI_MAGIC, ...)
    v["ati_magic"] = d[ATOM_ATI_MAGIC_PTR:
                       ATOM_ATI_MAGIC_PTR + len(ATOM_ATI_MAGIC)]
    if v["ati_magic"] != ATOM_ATI_MAGIC:
        raise RomInvalido("ATOMI magic = %r, esperado %r"
                          % (v["ati_magic"], ATOM_ATI_MAGIC))

    # atom.c:1570  base = CU16(ATOM_ROM_TABLE_PTR)
    v["base"] = u16(d, ATOM_ROM_TABLE_PTR)

    # atom.c:1571  strncmp(CSTR(base + ATOM_ROM_MAGIC_PTR), ATOM_ROM_MAGIC, ...)
    o = v["base"] + ATOM_ROM_MAGIC_PTR
    if o + len(ATOM_ROM_MAGIC) > len(d):
        raise RomInvalido("la magic ATOM caeria en %d, fuera del ROM" % o)
    v["atom_magic"] = d[o:o + len(ATOM_ROM_MAGIC)]
    if v["atom_magic"] != ATOM_ROM_MAGIC:
        raise RomInvalido("ATOM magic en 0x%04x = %r, esperado %r"
                          % (o, v["atom_magic"], ATOM_ROM_MAGIC))

    # atom.c:1577-1578
    v["cmd_table"] = u16(d, v["base"] + ATOM_ROM_CMD_PTR)
    v["data_table"] = u16(d, v["base"] + ATOM_ROM_DATA_PTR)
    return v


def cmd_rom(d, a):
    print("=" * 78)
    print("VBIOS ATOM: validacion")
    print("=" * 78)
    print("fichero   : %s" % a.fichero)
    print("sha256    : %s" % hashlib.sha256(d).hexdigest())
    print("bytes     : %d" % len(d))
    print("cabecera declarada por file(1): 115*512 = %d -> %s"
          % (115 * 512, "coincide" if len(d) == 115 * 512 else "NO COINCIDE"))
    print()
    try:
        v = valida(d)
    except RomInvalido as e:
        print("ROM INVALIDO: %s" % e)
        print()
        print("Esto es un NEGATIVE_RESULT con contenido: el ROM no pasa la")
        print("validacion que el driver haria. No es 'no hay VBIOS'.")
        return 1

    print("Los cuatro controles que hace amdgpu_atom_parse(), atom.c:")
    print("  %-34s 0x%04x == 0x%04X        OK   (atom.c:1558)"
          % ("ATOM_BIOS_MAGIC @0", v["magic"], ATOM_BIOS_MAGIC))
    print("  %-34s %r  OK   (atom.c:1563)"
          % ("ATOMI magic @0x%02x" % ATOM_ATI_MAGIC_PTR, v["ati_magic"]))
    print("  %-34s %r  OK   (atom.c:1571)"
          % ("ATOM magic @base+%d" % ATOM_ROM_MAGIC_PTR, v["atom_magic"]))
    print()
    print("tabla de comandos @ 0x%04x" % v["cmd_table"])
    print("tabla de datos   @ 0x%04x" % v["data_table"])
    print()
    return 0


def buscar_masters(d):
    """
    Busca en todo el ROM los sitios que PUEDEN ser la master data table.

    Criterio, todo verificado por separado:
      - usStructureSize == HEADER_COMUN + 2*len(TABLAS_MASTER)
      - revisiones de formato y contenido <= 8 (razonable; los valores altos
        que salen al leer sobre el sitio equivocado son la senal de error)
      - al menos 20 de los 35 offsets siguientes distintos de cero, porque
        una master data table real de un ASIC real casi no tiene entradas
        vacias
      - NINGUN offset puede exceder el tamano del ROM

    Devuelve la lista de offsets candidatos, en orden. Vacia significa que el
    layout del corpus no describe este ROM, lo cual es una respuesta valida y
    distinta de "no hay tablas".
    """
    esperado = HEADER_COMUN + 2 * len(TABLAS_MASTER)
    cands = []
    for o in range(0, len(d) - 2):
        if u16(d, o) != esperado:
            continue
        if o + HEADER_COMUN + 2 * len(TABLAS_MASTER) > len(d):
            continue
        if u8(d, o + 2) > 8 or u8(d, o + 3) > 8:
            continue
        vals = struct.unpack_from("<%dH" % len(TABLAS_MASTER), d,
                                  o + HEADER_COMUN)
        if sum(1 for x in vals if x) < 20:
            continue
        if max(vals) > len(d):
            continue
        cands.append(o)
    return cands


def cmd_tablas(d, a):
    """
    Inventaria las 35 tablas de la master data table.

    Solo localiza y da el header. NO decodifica el contenido: eso es
    NOT_IMPLEMENTED a proposito y se dice explicitamente, para que una tabla
    sin decodificar no se lea como una tabla vacia.

    LA MASTER DATA TABLE NO ESTA EN base, Y ESTO CUESTO UNA CORRECCION.
    La primera version de esta funcion hacia `mt = base`, es decir, colocaba
    la master data table en el mismo sitio que la ROM table. Con eso leia
    usStructureSize = 36 cuando el layout del corpus exige 74, y la propia
    herramienta aviso: "NO COINCIDE, los nombres de abajo NO son de fiar". Ese
    aviso es lo que impidio que se publicara un inventario de 35 tablas con
    nombres plausibles y offsets inventados, que es la forma mas
    insidiosa de estar equivocado.
   _insidiosa de estar equivocado.

    Donde esta de verdad: _ATOM_ROM_HEADER (atombios.h:219) es

        sHeader                  4
        uaFirmWareSignature[4]   4
        13 USHORT               26
        usMasterCommandTableOffset  2   -> base + 0x1E
        usMasterDataTableOffset     2   -> base + 0x20
        ucExtendedFunctionCode      1
        ucReserved                  1
                               ---
                                36

    O sea que usMasterDataTableOffset ES el campo que el driver llama
    ATOM_ROM_DATA_PTR (atom.h:43), y su VALOR es donde vive la master data
    table, no base. La comprobacion independiente: en todo el ROM hay un
    unico sitio cuyo usStructureSize vale 74 y cuyos 35 offsets siguientes
    apuntan dentro del ROM, y es exactamente el valor de ese campo. Dos
    derivaciones por caminos distintos que coinciden.
    """
    try:
        v = valida(d)
    except RomInvalido as e:
        print("ROM INVALIDO: %s" % e)
        return 1

    mt = v["data_table"]
    print("=" * 78)
    print("MASTER DATA TABLE en 0x%04x" % mt)
    print("=" * 78)
    print("Base del ROM table          : 0x%04x" % v["base"])
    print("Master command table offset : 0x%04x" % v["cmd_table"])
    print("Master DATA table offset    : 0x%04x  <-- aqui" % v["data_table"])
    print()
    size = u16(d, mt)
    rev_formato = u8(d, mt + 2)
    rev_contenido = u8(d, mt + 3)
    print("usStructureSize      = %d" % size)
    print("ucTableFormatRevision= %d" % rev_formato)
    print("ucTableContentRevision=%d" % rev_contenido)
    print()
    esperado = HEADER_COMUN + 2 * len(TABLAS_MASTER)
    print("esperado: 4 bytes de header + %d USHORT = %d bytes"
          % (len(TABLAS_MASTER), esperado))
    print("declarado: %d -> %s"
          % (size, "COINCIDE" if size == esperado
             else "NO COINCIDE: los nombres de abajo NO son de fiar y no se "
                  "publican como inventario"))
    if size != esperado:
        return 1
    print()

    # CROSS-CHECK INDEPENDIENTE.
    #
    # En vez de fiarme de la aritmetica del offset (que ya me fallo una vez),
    # se busca en TODO el ROM cualquier sitio que pueda ser la master data
    # table: un usStructureSize == 74, unas revisiones sensatas, y 35 offsets
    # siguientes que apunten dentro del ROM. Si el busqueda da UN solo
    # candidato y es el mismo que dice el header, las dos vias coinciden y la
    # conclusion no depende de mi aritmetica.
    #
    # Si dieran mas de uno, se dice. Ambiguo no es unico, y se dice cual es
    # el del header para que se vea la diferencia.
    cands = buscar_masters(d)
    print("busqueda independiente en todo el ROM (%d bytes):" % len(d))
    if len(cands) == 1 and cands[0] == mt:
        print("  UN candidato, y es 0x%04x: coincide con el header."
              % cands[0])
        print("  Las dos vias convergen. Conclusion corroborada, no asumida.")
    elif len(cands) == 1:
        print("  UN candidato en 0x%04x, pero el header dice 0x%04x."
              % (cands[0], mt))
        print("  DISCREPANCIA: no se publica el inventario hasta resolverla.")
        return 1
    elif not cands:
        print("  NINGUN candidato. El layout del corpus no describe este")
        print("  VBIOS, y las 35 tablas no se pueden nombrar con certeza.")
        return 1
    else:
        print("  %d candidatos: %s" % (len(cands),
                                       ", ".join("0x%04x" % c for c in cands)))
        print("  AMBIGUO: mas de un sitio encaja, asi que el offset del")
        print("  header no se puede confirmar por esta via. Se usa el del")
        print("  header, que es lo que haria el driver, pero se dice que la")
        print("  corroboracion por busqueda NO es univoca.")
    print()

    print("%-3s %-30s %-8s %s" % ("#", "tabla", "offset", "cabecera @ tabla"))
    print("-" * 78)
    presentes = ausentes = fuera = 0
    for i, nombre in enumerate(TABLAS_MASTER):
        o = mt + HEADER_COMUN + 2 * i
        if o + 2 > len(d):
            print("%-3d %-30s %-8s (offset %d fuera del ROM)"
                  % (i + 1, nombre, "-", o))
            fuera += 1
            continue
        off = u16(d, o)
        if off == 0:
            print("%-3d %-30s %-8s" % (i + 1, nombre, "0"))
            ausentes += 1
            continue
        if off + HEADER_COMUN > len(d):
            print("%-3d %-30s 0x%04x   FUERA DEL ROM (%d bytes)"
                  % (i + 1, nombre, off, len(d)))
            fuera += 1
            continue
        sz = u16(d, off)
        rf = u8(d, off + 2)
        rc = u8(d, off + 3)
        print("%-3d %-30s 0x%04x   size=%-6d rev=%d.%d"
              % (i + 1, nombre, off, sz, rf, rc))
        presentes += 1
    print("-" * 78)
    print("presentes: %d | offset 0 (ausentes): %d | fuera de rango: %d"
          % (presentes, ausentes, fuera))
    print()
    print("LIMITES, DICHA:"
          )
    print("  - Solo se LECTURA el header de cada tabla (4 bytes).")
    print("  - El CONTENIDO de las tablas NO se decodifica. Es")
    print("    NOT_IMPLEMENTED, no tabla vacia y no tabla ausente.")
    print("  - Para el hardware hace falta el contenido, no el offset.")
    return 0


def fabricar_rom(n=0x10000, base=0x021C, mt=0x97F2):
    """
    Construye un ROM ATOM sintetico pero ESTRUCTURALMENTE VALIDO.

    POR QUE
    -------
    El VBIOS real son firmware con derechos de AMD y no se versiona. Sin un
    ROM propio, la validacion de este script dependeria de un fichero que no
    esta en el repositorio, asi que en un clon limpio check.sh fallaria. Un
    control que depende de un secreto no es un control.

    Ademas, fabricar el ROM permite comprobar cosas que con el real no se
    pueden: que se rechaza cuando la firma esta mal, cuando la magic esta
    mal, cuando el puntero se sale. Con el VBIOS real solo se puede
    comprobar que se ACEPTA.

    Esto es un test que debe ser bidireccional: no solo "el bueno pasa", sino
    "los malos fallan". Un validador que acepta cualquier cosa tambien
    aceptaria un fichero vacio, y eso no es validacion.
    """
    d = bytearray(n)
    struct.pack_into("<H", d, 0, ATOM_BIOS_MAGIC)
    d[ATOM_ATI_MAGIC_PTR:ATOM_ATI_MAGIC_PTR + len(ATOM_ATI_MAGIC)] = \
        ATOM_ATI_MAGIC
    struct.pack_into("<H", d, ATOM_ROM_TABLE_PTR, base)
    d[base + ATOM_ROM_MAGIC_PTR:base + ATOM_ROM_MAGIC_PTR +
                                len(ATOM_ROM_MAGIC)] = ATOM_ROM_MAGIC
    struct.pack_into("<H", d, base + ATOM_ROM_CMD_PTR, base + 0x100)
    struct.pack_into("<H", d, base + ATOM_ROM_DATA_PTR, mt)
    # master data table
    struct.pack_into("<H", d, mt, HEADER_COMUN + 2 * len(TABLAS_MASTER))
    d[mt + 2] = 1
    d[mt + 3] = 1
    for i in range(len(TABLAS_MASTER)):
        # 25 tablas presentes, apuntando a cabeceras validas dentro del ROM
        off = 0 if i >= 25 else (mt + 0x100 + i * 0x40)
        struct.pack_into("<H", d, mt + HEADER_COMUN + 2 * i, off)
        if off:
            struct.pack_into("<H", d, off, 16)   # usStructureSize
            d[off + 2] = 1
            d[off + 3] = 2
    return bytes(d)


def cmd_autotest(a):
    """
    Valida atomrom.py sin depender del VBIOS real.
    """
    fallos = []
    print("AUTOTEST DE atomrom.py (con ROM sintetico)")
    print("-" * 66)

    rom = fabricar_rom()
    try:
        v = valida(rom)
        print("  OK    el ROM sintetico se valida "
              "(base=0x%04x, data=0x%04x)" % (v["base"], v["data_table"]))
    except Exception as e:
        print("  FALLA el ROM sintetico NO se valida: %s" % e)
        fallos.append("el ROM de referencia no se valida")
        print("-" * 66)
        return 1

    # debe RECHAZAR las corrupciones
    def m(f):
        d = bytearray(rom)
        f(d)
        return bytes(d)

    casos = [
        ("firma BIOS mal", lambda d: struct.pack_into("<H", d, 0, 0x1234)),
        ("firma en big-endian", lambda d: struct.pack_into("<H", d, 0, 0x55AA)),
        ("magic ATI mal", lambda d: d.__setitem__(
            slice(ATOM_ATI_MAGIC_PTR,
                  ATOM_ATI_MAGIC_PTR + len(ATOM_ATI_MAGIC)), b"X" * 10)),
        ("puntero de tabla fuera", lambda d: struct.pack_into(
            "<H", d, ATOM_ROM_TABLE_PTR, 0xFF00)),
        ("puntero de tabla a 0", lambda d: struct.pack_into(
            "<H", d, ATOM_ROM_TABLE_PTR, 0)),
        # OJO: aqui NO se puede usar el nombre `base`. Es un parametro de
        # fabricar_rom, y esta lambda vive en cmd_autotest, donde no existe.
        # La primera version de este test la usaba y fallaba con NameError:
        # un control que no ejecuta su propia prueba no prueba nada.
        ("magic ATOM mal", lambda d: d.__setitem__(
            slice(0x021C + ATOM_ROM_MAGIC_PTR,
                  0x021C + ATOM_ROM_MAGIC_PTR + len(ATOM_ROM_MAGIC)),
            b"XXXX")),
        ("ROM truncado", lambda d: d.__setitem__(slice(0x100, len(d)), b"")),
        ("ROM vacio", lambda d: d.__setitem__(slice(0, len(d)), b"")),
    ]
    for nombre, f in casos:
        try:
            valida(m(f))
            print("  FALLA %s: se ACEPTO y deberia rechazarse" % nombre)
            fallos.append("acepta " + nombre)
        except RomInvalido:
            print("  OK    rechaza: %s" % nombre)
        except Exception as e:
            print("  FALLA %s: excepcion no controlada %s" % (nombre,
                                                                type(e).__name__))
            fallos.append("excepcion en " + nombre)

    # la busqueda de la master data table debe encontrar exactamente una
    c = buscar_masters(rom)
    if c == [0x97F2]:
        print("  OK    buscar_masters encuentra la master data table, y solo "
              "una")
    else:
        print("  FALLA buscar_masters = %s, esperaba [0x97f2]" % c)
        fallos.append("buscar_masters")

    # y si se rompe el tamano, no debe encontrar ninguna
    d = bytearray(rom)
    struct.pack_into("<H", d, 0x97F2, 999)
    if buscar_masters(bytes(d)) == []:
        print("  OK    con usStructureSize erroneo no encuentra ninguna")
    else:
        print("  FALLA encuentra candidatas con un tamano erroneo")
        fallos.append("buscar_masters con tamano malo")

    # --- el PPTABLE, con vectores que cazan MI propia clase de error ---
    #
    # Escribi SCLK_REC = 12 a mano cuando el struct suma 11, y el volcado salio
    # con 1879048199 MHz impreso como si fuera un dato. Estos vectores existen para
    # que eso no vuelva a pasar sin que la herramienta lo note.
    off, calc = _layout_ppt()
    print("-" * 66)
    print("PPT (PowerPlayInfo), en ROM sintetico")

    # una tabla de dependencia de mclk de tres entradas, con relojes plausibles
    def _mclk_tab(entradas, recsz=MCLK_REC, holgura=0):
        # holgura: se reserva sitio de mas a proposito, para que un registro de
        # tamano equivocado NO se detecte por salirse del buffer sino por la
        # plausibilidad. Los dos controles tienen que poder probarse por separado:
        # si el mutante siempre revienta por limites, el vector de plausibilidad
        # no llega a ejercitarse y parece que funciona cuando no se ha probado.
        b = bytearray(2 + len(entradas) * recsz + holgura)
        b[0] = 0
        b[1] = len(entradas)
        for i, clk in enumerate(entradas):
            o = 2 + i * recsz
            b[o] = 0
            struct.pack_into("<HHH", b, o + 1, 800, 0, 1000)
            struct.pack_into("<I", b, o + 7, clk)
        return bytes(b)

    buenos = (30000, 62500, 150000)
    rev, n, filas, recsz, desp, ok = _dep_entries(
        _mclk_tab(buenos), 0, MCLK_CAMPOS, "MCLK")
    if ok and n == 3 and [f[2] for f in filas] == list(buenos) and recsz == 13:
        print("  OK    lee 3 entradas de mclk con el registro de 13 bytes")
    else:
        print("  FALLA lectura de mclk: n=%d recsz=%d ok=%s vals=%s"
              % (n, recsz, ok, [f[2] for f in filas]))
        fallos.append("lectura de mclk")

    # V1: un reloj implausible tiene que ruido, no imprimirse
    malos = (30000, 1879048199, 150000)
    rev, n, filas, recsz, desp, ok = _dep_entries(
        _mclk_tab(malos), 0, MCLK_CAMPOS, "MCLK")
    if not ok:
        print("  OK    un reloj de 1879048199 marca la tabla como NO plausible")
    else:
        print("  FALLA acepta 1879048199 como reloj: no puede distinguir")
        print("         un dato imposible de un dato raro")
        fallos.append("plausibilidad no detecta un reloj imposible")

    # V2, Y ESTE ES EL IMPORTANTE: un registro de tamano equivocado. Con el
    # equivocado los bytes siguen cabiendo y no hay limites que lo delaten, asi
    # que la plausibilidad es la UNICA defensa. Este vector es el que habria
    # cazado mi SCLK_REC = 12.
    for malo in (MCLK_REC - 1, MCLK_REC + 1, MCLK_REC - 4, MCLK_REC + 2):
        rev, n, filas, recsz, desp, ok = _dep_entries(
            _mclk_tab(buenos, malo, holgura=32), 0, MCLK_CAMPOS, "MCLK")
        if ok:
            print("  FALLA con registro de %d bytes NO marca la tabla como no"
                  " plausible" % malo)
            fallos.append("registro de %d bytes pasa la plausibilidad" % malo)
            break
    else:
        print("  OK    un registro de tamano equivocado se marca como no plausible")
        print("        (con el buffer inflado, para que lo detecte la plausibilidad")
        print("         y no un desbordamiento)")

    # y el otro control, por separado. Y aqui el vector tiene que ser un buffer
    # TRUNCADO, no uno construido con el tamano equivocado: _mclk_tab dimensiona
    # el buffer a partir del tamano del registro, asi que un mutante de tamano
    # NUNCA se sale por limites y este vector no se ejercitaba. Que un control no
    # se ejercite es tan malo como que no exista.
    try:
        _dep_entries(_mclk_tab(buenos)[:20], 0, MCLK_CAMPOS, "MCLK")
        print("  FALLA una tabla truncada no da error")
        fallos.append("truncamiento silencioso")
    except RomInvalido:
        print("  OK    una tabla truncada da RomInvalido, no una tabla mas corta")

    # V3: el calculo del layout es el que da credibilidad, y se comprueba
    if calc == 77 and off["usMclkDependencyTableOffset"] == 43 \
            and off["usStateArrayOffset"] == 35:
        print("  OK    el layout del pptable se calcula a 77 bytes y los offsets")
        print("        del mclk y del state array caen donde deben")
    else:
        print("  FALLA el layout calculado no es el esperado: %d bytes, mclk@%d"
              % (calc, off["usMclkDependencyTableOffset"]))
        fallos.append("layout del pptable")

    # V4: el registro de sclk se elige por revision, y los dos dan distinto
    if (_tam(SCLK_CAMPOS_TONGA) == 11 and _tam(SCLK_CAMPOS_POLARIS) == 15):
        print("  OK    registro de sclk: Tonga 11 bytes, Polaris 15, por revision")
    else:
        print("  FALLA los registros de sclk no son 11 y 15: %d y %d"
              % (_tam(SCLK_CAMPOS_TONGA), _tam(SCLK_CAMPOS_POLARIS)))
        fallos.append("registros de sclk")

    # --- y ahora el CAMINO REAL: cmd_ppt sobre un PowerPlayInfo SINTETICO ---
    #
    # Los vectores anteriores probaban las funciones auxiliares. Eso, y solo eso,
    # deja dos huecos que se ven mutando: quitar la comprobacion de usTableSize no
    # los detecta, y elegir siempre el registro de Tonga tampoco. Porque
    # fabricar_rom() no mete ninguna PowerPlayInfo, asi que cmd_ppt no se ejecutaba
    # nunca en el autotest. Un self-test que prueba piezas y no el camino que
    # corre tiene un hueco, y el hueco es justo donde se cuelan los errores.
    def _ppt_sintetico(rom, mclk=(30000, 62500, 150000), tabla_size=None,
                      Offsets=None, buen_tam=True):
        base = len(rom) - 1024
        t = bytearray(778)
        struct.pack_into("<HBB", t, 0, 778, 7, 1)
        t[4] = 0
        struct.pack_into("<H", t, _layout_ppt()[0]["usTableSize"],
                         tabla_size if tabla_size is not None else _layout_ppt()[1])
        off = _layout_ppt()[0]
        struct.pack_into("<H", t, off["usStateArrayOffset"], 77)
        for k in ("usFanTableOffset", "usThermalControllerOffset",
                  "usVddcLookupTableOffset", "usVddgfxLookupTableOffset",
                  "usMMDependencyTableOffset", "usVCEStateTableOffset",
                  "usPowerTuneTableOffset", "usPCIETableOffset"):
            struct.pack_into("<H", t, off[k], 0)
        # tabla de dependencia de sclk, con ucRevId = 1, que es lo que obliga al
        # driver --y a esta herramienta-- a usar el registro de POLARIS y no el de
        # Tonga. Sin esta tabla, cmd_ppt no llegaba a la rama de sclk y la
        # seleccion de registro no se probaba: la mutacion "siempre Tonga" pasaba
        # porque el codigo mutado no se ejecutaba nunca.
        deps = 400
        struct.pack_into("<H", t, off["usSclkDependencyTableOffset"], deps)
        n_s = 3
        t[deps] = 1                       # ucRevId = 1 -> registro Polaris
        t[deps + 1] = n_s
        for i, clk in enumerate((98000, 102000, 104600)):
            o = deps + 2 + i * SCLK_REC_POLARIS
            t[o] = 0
            struct.pack_into("<H", t, o + 1, 0)
            struct.pack_into("<I", t, o + 3, clk)
            struct.pack_into("<I", t, o + 11, 0)   # ulSclkOffset
        # tabla de dependencia de mclk al final de la tabla
        dep = 600
        struct.pack_into("<H", t, off["usMclkDependencyTableOffset"], dep)
        b0, b1 = 2, 2 + len(mclk) * MCLK_REC
        t[dep] = 0
        t[dep + 1] = len(mclk)
        for i, clk in enumerate(mclk):
            o = dep + 2 + i * MCLK_REC
            t[o] = 0
            struct.pack_into("<HHH", t, o + 1, 800, 0, 1000)
            struct.pack_into("<I", t, o + 7, clk)
        d2 = bytearray(rom)
        d2[base:base + 778] = t
        mt = 0x97F2
        idx = TABLAS_MASTER.index("PowerPlayInfo")
        struct.pack_into("<H", d2, mt + HEADER_COMUN + 2 * idx, base)
        return bytes(d2)

    class _Silencio:
        def write(self, x):
            return len(x)

        def flush(self):
            pass

    real = sys.stdout

    # A: el camino bueno, con usTableSize correcto
    sys.stdout = _Silencio()
    try:
        rc_ok = cmd_ppt(_ppt_sintetico(rom), a)
    finally:
        sys.stdout = real
    if rc_ok == 0:
        print("  OK    cmd_ppt acepta una PowerPlayInfo sintetica bien formada")
    else:
        print("  FALLA cmd_ppt rechaza una tabla bien formada: rc=%d" % rc_ok)
        fallos.append("cmd_ppt rechaza lo valido")

    # B: y el hueco real. usTableSize INCORRECTO tiene que dar rc=4
    sys.stdout = _Silencio()
    try:
        rc_malo = cmd_ppt(_ppt_sintetico(rom, tabla_size=78), a)
    finally:
        sys.stdout = real
    if rc_malo == 4:
        print("  OK    usTableSize erroneo -> rc=4 INVALID, no numeros falsos")
    else:
        print("  FALLA usTableSize erroneo -> rc=%d: sigue imprimiendo la tabla"
              % rc_malo)
        fallos.append("cmd_ppt no detecta usTableSize erroneo")

    # C-bis: los relojes de sclk tienen que leerse con el registro de POLARIS. Con
    # el de Tonga (11 en vez de 15) las entradas se desalinean y salen numeros que
    # no son relojes, asi que la comprobacion es sobre los VALORES, no sobre el
    # codigo: es lo unico que distingue un registro de otro sin leerlos.
    _cap = io.StringIO()

    class _Toma:
        def write(self, x):
            _cap.write(x)
            return len(x)

        def flush(self):
            pass

    sys.stdout = _Toma()
    try:
        cmd_ppt(_ppt_sintetico(rom), a)
    finally:
        sys.stdout = real
    salida = _cap.getvalue()
    if "98000" in salida and "104600" in salida:
        print("  OK    los relojes de sclk se leen con el registro de Polaris")
    else:
        print("  FALLA los relojes de sclk no salen con el registro correcto")
        fallos.append("registro de sclk en el camino real")

    # C: y un reloj imposible dentro de la tabla bien formada
    sys.stdout = _Silencio()
    try:
        rc_clk = cmd_ppt(_ppt_sintetico(rom, mclk=(30000, 1879048199, 150000)), a)
    finally:
        sys.stdout = real
    if rc_clk == 4:
        print("  OK    un reloj imposible -> rc=4 INVALID, no una tabla")
    else:
        print("  FALLA un reloj imposible -> rc=%d: se imprime como si fuera dato"
              % rc_clk)
        fallos.append("cmd_ppt imprime relojes imposibles")

    print("-" * 66)
    if fallos:
        print("%d fallo(s): atomrom.py NO puede usarse como autoridad."
              % len(fallos))
        return 1
    print("todos los controles pasan, sin usar el VBIOS real")
    return 0


# _ATOM_FIRMWARE_INFO_V1_2, atombios.h:2982. Solo los campos que aportan dato
# util; el resto son relleno que el propio header llama "Don't use them".
# El orden es del struct y NO se reordena.
#
# UNIDAD DE LOS CLOCKS, QUE HAY QUE HACER BIEN
# --------------------------------------------
# El header dice "In 10Khz unit". 10 kHz es 1/100 de MHz, asi que el paso a
# MHz es dividir entre 100, NO (/10)/1000.
#
# La primera version hacia (/10)/1000 y sacaba "2.1 MHz" para el reloj de
# motor, imposible para una GPU: numero plausible, con decimales, y
# equivocado por un factor de 1000. Se arreglo contrastando con lo que el
# kernel tiene AHORA en la maquina, que es la unica forma de saber si una
# unidad esta bien:
#
#   ulDefaultEngineClock = 21400 -> 214 MHz == PSTATE_SCLK (214 MHz)
#   ulDefaultMemoryClock = 30000 -> 300 MHz == MCLK (300 MHz)
#
# Dos coincidencias exactas en dos campos distintos. La unidad queda
# CORROBORATED por el hardware, no deducida de la aritmetica.
# Contraste con amdgpu_pm_info de esta misma maquina. Se lee el fichero
# capturado; si no esta, se dice y no se inventa el valor. La ausencia hace
# salir con codigo 4, no con un OK: el decode es valido pero la UNIDAD queda
# sin verificar, y eso es distinto de verificada.
CRUCE_PM = "capturas/amdgpu_pm_info.txt"

FIRMWARE_INFO_V12 = [
    ("ulFirmwareRevision", "u32", None),
    ("ulDefaultEngineClock", "u32", 100),
    ("ulDefaultMemoryClock", "u32", 100),
    ("ulDriverTargetEngineClock", "u32", 100),
    ("ulDriverTargetMemoryClock", "u32", 100),
    ("ulMaxEngineClockPLL_Output", "u32", 100),
    ("ulMaxMemoryClockPLL_Output", "u32", 100),
    ("ulMaxPixelClockPLL_Output", "u32", 100),
    ("ulASICMaxEngineClock", "u32", 100),
    ("ulASICMaxMemoryClock", "u32", 100),
    ("ucASICMaxTemperature", "u8", None),
    ("ucMinAllowedBL_Level", "u8", None),
]


def cmd_firmware(d, a):
    """
    Decodifica la tabla FirmwareInfo y la cruza con lo que reporta el kernel.

    POR QUE CRUZARLAS
    -----------------
    Hay dos fuentes de la version del firmware que no se han relacionado:
    la tabla FirmwareInfo del VBIOS (lo que el firmware declara) y
    amdgpu_firmware_info (lo que el kernel cargo). Si coincidieran, el
    VBIOS describiria bien la GPU. Si no, son campos distintos.

    El resultado de este cruce es que NO coinciden, y eso es un dato, no un
    fallo: ulFirmwareRevision es un entero opaco y las feature versions que
    da el kernel son por IP. Que ningun byte de ulFirmwareRevision sea 49 no
    es una refutacion de la relacion, es que la relacion no esta
    establecida. Se reporta como tal y no se fuerza un sentido.
    """
    v = valida(d)
    mt = v["data_table"]
    off = u16(d, mt + HEADER_COMUN + 2 * 4)   # campo #5: FirmwareInfo
    print("=" * 78)
    print("FIRMWARE INFO  (_ATOM_FIRMWARE_INFO_V1_2, atombios.h:2982)")
    print("=" * 78)
    print("tabla en 0x%04x, usStructureSize=%d rev=%d.%d"
          % (off, u16(d, off), u8(d, off + 2), u8(d, off + 3)))
    print()
    print("%-30s %-12s %s" % ("campo", "bruto", "leido"))
    print("-" * 62)
    p = off + 4
    rev = None
    # Se guarda el valor CRUDO de cada campo mientras se recorre, para que
    # el bloque de contraste no tenga que recalcular offsets. La primera
    # version lo hacia, y al redefinir `off` (que ahi es el offset de la
    # TABLA) lo usaba como offset del PAYLOAD: leia en el sitio equivocado,
    # salia 0, y el contraste daba "DIFIERE" sobre valores que si cuadraban.
    # Un control mal calculado que dice "no coincide" es peor que no
    # tenerlo: hace desconfiar de una corroboracion que era real.
    CRUDO = {}
    for i, (nombre, tipo, div) in enumerate(FIRMWARE_INFO_V12):
        if tipo == "u32":
            val = u32(d, p); p += 4
            CRUDO[nombre] = val
            if nombre == "ulFirmwareRevision":
                rev = val
                print("%-30s 0x%08x" % (nombre, val))
            elif div:
                # div YA es el factor a MHz (100, porque 10 kHz = 1/100 MHz).
                # Dividir otra vez por 1000 aqui fue el segundo error de la
                # misma unidad: el primer codigo hacia val/10/1000, el
                # segundo hacia val/100/1000. Los dos darian un numero con
                # decimales y ninguno seria una frecuencia de GPU.
                print("%-30s %-12d %.0f MHz" % (nombre, val, val / div))
            else:
                print("%-30s %d" % (nombre, val))
        else:
            val = u8(d, p); p += 1
            print("%-30s %d" % (nombre, val))
    print("-" * 62)
    print()

    # CONTRASTE CON EL HARDWARE, EN CADA EJECUCION.
    #
    # Una unidad mal puesta no da error: da un numero con decimales que
    # parece una frecuencia. La unica forma de saber si la unidad es
    # correcta es contrastar con lo que la maquina tiene AHORA, asi que eso
    # se hace aqui y no se deja a la memoria de quien lee la salida.
    #
    # amdgpu_pm_info se captura con captura.py. Si no esta, se dice y se sale
    # con codigo 4: el decode es valido pero la UNIDAD queda sin verificar,
    # y eso no es lo mismo que verificada.
    if not os.path.exists(CRUCE_PM):
        print("NO SE PUDO VERIFICAR LA UNIDAD: falta %s" % CRUCE_PM)
        print()
        print("El decode de los valores es valido, pero que esten en MHz no")
        print("esta comprobado. Sin el contraste, un factor 1000 de error")
        print("pasaria desapercibido. Se sale con codigo 4.")
        return 4

    pm = open(CRUCE_PM, errors="replace").read()
    import re as _re
    m_sclk = _re.search(r"(\d+) MHz \(PSTATE_SCLK\)", pm)
    m_mclk = _re.search(r"(\d+) MHz \(MCLK\)", pm)
    if not (m_sclk and m_mclk):
        print("NO SE PUDO VERIFICAR LA UNIDAD: el formato de %s cambio"
              % CRUCE_PM)
        print("Se esperaba 'N MHz (PSTATE_SCLK)' y 'N MHz (MCLK)'.")
        return 4
    hw = {"ulDefaultEngineClock": int(m_sclk.group(1)),
          "ulDefaultMemoryClock": int(m_mclk.group(1))}

    print("CONTRASTE DE UNIDAD con el estado real de la GPU:")
    print("  %-24s %-8s %-8s %-10s %s"
          % ("campo", "VBIOS/100", "kernel", "unit", "veredicto"))
    fallos_unidad = []
    for nombre, _t, div in FIRMWARE_INFO_V12:
        if nombre not in hw or div is None:
            continue
        mhz = CRUDO[nombre] / 100.0   # 10 kHz = 1/100 de MHz
        ok = abs(mhz - hw[nombre]) < 0.5
        if not ok:
            fallos_unidad.append(nombre)
        print("  %-24s %-8.0f %-8d %-10s %s"
              % (nombre, mhz, hw[nombre], "MHz",
                 "COINCIDE" if ok else "DIFIERE"))
    print()
    if fallos_unidad:
        print("  La unidad NO queda corroborada en: %s" % ", ".join(fallos_unidad))
        print()
        print("  Los valores de arriba estan BIEN leidos pero la UNIDAD no")
        print("  esta comprobada. No se dan por buenos. Saliendo con codigo 5.")
        unidad_ok = False
    else:
        print("  La unidad queda CORROBORATED: %d campos coinciden con las"
              % len(hw))
        print("  frecuencias que la GPU tiene ahora mismo. 10 kHz = 1/100 MHz.")
        unidad_ok = True
    print()
    print("CRUCE con amdgpu_firmware_info (lo que cargo el kernel):")
    print("  el kernel da feature version POR IP: ME 49, PFP 49, CE 49, MEC 49")
    print("  ulFirmwareRevision = 0x%08x" % rev)
    bs = [(rev >> (8 * i)) & 0xFF for i in range(4)]
    print("  sus bytes son %s" % [hex(x) for x in bs])
    print("  alguno es 49? %s" % ("si" if 49 in bs else "NO"))
    print()
    print("  Conclusion: son campos DISTINTOS. ulFirmwareRevision es un")
    print("  entero opaco del VBIOS y las feature versions son por IP. Que")
    print("  no coincida ningun byte NO es refutacion: es que no hay relacion")
    print("  establecida. Se queda NOT_DETERMINED, no REFUTED ni CORROBORATED.")
    # El codigo de salida lo dicta la UNIDAD, no el cruce de revisiones. Ese
    # cruce es informativo y su resultado es "no hay relacion", que no es un
    # fallo. La unidad, si, es algo que esta tool afirma y tiene que cumplir.
    return 0 if unidad_ok else 5


# ATOM_VRAM_MODULE_V8, atombios.h. El offset de CADA campo se calcula aqui
# sumando el tamano del anterior, en el orden del struct. Calcularlo a mano
# fue el error: se leyo usMemorySize en +26 en vez de +20, y salia 24832 MB
# en lugar de 2048. Un offset buscado a ojo no es un offset, es una
# suposicion con formato de dato.
VRAM_MODULE_V8 = [
    ("ulChannelMapCfg", 4), ("usModuleSize", 2), ("usMcRamCfg", 2),
    ("usEnableChannels", 2), ("ucExtMemoryID", 1), ("ucMemoryType", 1),
    ("ucChannelNum", 1), ("ucChannelWidth", 1), ("ucDensity", 1),
    ("ucBankCol", 1), ("ucMisc", 1), ("ucVREFI", 1), ("usReserved", 2),
    ("usMemorySize", 2), ("ucMcTunningSetId", 1), ("ucRowNum", 1),
]
VRAM_V8_PN_OFFSET = 44      # strMemPNString[20]
VRAM_V8_TOTAL = 64          # con alineacion


def cmd_vram(d, a):
    """
    Decodifica la tabla VRAM_Info y contrasta el tamano con lo que la GPU
    tiene installed.

    LA REVISION MANDA
    -----------------
    El VBIOS declara rev 2.2 en VRAM_Info, asi que la estructura correcta es
    _ATOM_VRAM_INFO_HEADER_V2_2 (atombios.h:8027), NO _ATOM_VRAM_INFO_V4, que
    es la que estaba a mano. Leer V4 sobre una tabla 2.2 da numeros que
    parecen campos pero no lo son: salio ucChannelWidth=5 y ucMemorySize=0.

    Y el V2_2 dice explicitamente ucVramModuleVer, que aqui vale 8, asi que
    los modulos son ATOM_VRAM_MODULE_V8. Eso lo dice el propio dato, no una
    suposicion.
    """
    v = valida(d)
    mt = v["data_table"]
    off = u16(d, mt + HEADER_COMUN + 2 * 28)      # campo #29: VRAM_Info
    print("=" * 78)
    print("VRAM_INFO  (_ATOM_VRAM_INFO_HEADER_V2_2, atombios.h:8027)")
    print("=" * 78)
    if off == 0:
        print("VRAM_Info no esta en este VBIOS (offset 0).")
        return 1
    print("tabla en 0x%04x  usStructureSize=%d rev=%d.%d"
          % (off, u16(d, off), u8(d, off + 2), u8(d, off + 3)))
    p = off + 4
    for nm in ("usMemAdjustTblOffset", "usMemClkPatchTblOffset",
               "usMcAdjustPerTileTblOffset", "usMcPhyInitTableOffset",
               "usDramDataRemapTblOffset", "usReserved1"):
        print("  %-28s = 0x%04x" % (nm, u16(d, p)))
        p += 2
    nmod = u8(d, p); p += 1
    print("  %-28s = %d" % ("ucNumOfVRAMModule", nmod))
    print("  %-28s = %d" % ("ucMemoryClkPatchTblVer", u8(d, p))); p += 1
    modver = u8(d, p); p += 1
    print("  %-28s = %d" % ("ucVramModuleVer", modver))
    p += 1   # ucMcPhyTileNum
    print()
    if modver != 8:
        print("ucVramModuleVer = %d, y este script solo decodifica la 8." % modver)
        print("Se dice en vez de aplicar un layout que no es el de este VBIOS.")
        return 1
    print("ATOM_VRAM_MODULE_V8 (atombios.h), %d modulo(s):" % nmod)
    print()
    for k in range(nmod):
        base = p + k * VRAM_V8_TOTAL
        # El offset de cada campo se acumula desde `base`. La primera version
        # imprimia todos los campos desde el mismo sitio hacia m += 0, con lo
        # que salia el mismo valor para todos y parecía un decode.
        off_m = base
        for nm, sz in VRAM_MODULE_V8:
            val = u8(d, off_m) if sz == 1 else u16(d, off_m)
            extra = ""
            if nm == "usMemorySize":
                extra = "  -> %d MB" % val
            elif nm == "ucMemoryType":
                extra = "  -> tipo %d" % (val & 0xF)
            print("    %-20s @+%-3d = %-8d%s" % (nm, off_m - base, val, extra))
            off_m += sz
        pn = d[base + VRAM_V8_PN_OFFSET:base + VRAM_V8_PN_OFFSET + 20]
        print("    %-20s @+%-3d = %r" % ("strMemPNString", VRAM_V8_PN_OFFSET,
                                        pn.split(b"\x00")[0]))
        print()
    print("LO QUE SE PUEDE AFIRMAR")
    vbios_mb = u16(d, p + 20)
    print("  usMemorySize = %d MB es el tamano que declara el VBIOS para la"
          % vbios_mb)
    print("  memoria de esta tarjeta.")
    print()
    # CONTRASTE CON LA VRAM REAL, en cada ejecucion.
    #
    # El VBIOS podria estar describiendo otra tarjeta, o el kernel podria
    # estar viendo algo distinto de lo que el VBIOS dice. Son dos fuentes
    # que se pueden contradecir, y hasta que se cruzan no se sabe.
    #
    # amdgpu_vram_mm lo publica el kernel. Se busca "total: NMiB" y se
    # compara. Si no esta el fichero, se sale con codigo 4: el decode es
    # valido pero la CORROBORACION no esta hecha, y eso no es lo mismo.
    vm = "capturas/amdgpu_vram_mm.txt"
    if not os.path.exists(vm):
        print("  NO CONTRASTADO: falta %s" % vm)
        print("  El valor del VBIOS es legitimo, pero no se ha comprobado")
        print("  contra el kernel. Saliendo con codigo 4.")
        return 4
    import re as _re
    txt = open(vm, errors="replace").read()
    mt = _re.search(r"total:\s*(\d+)MiB", txt)
    if not mt:
        print("  NO CONTRASTADO: no se encontro 'total: NMiB' en %s" % vm)
        print("  Puede que el formato haya cambiado. Saliendo con codigo 4.")
        return 4
    kernel_mb = int(mt.group(1))
    coincide = (kernel_mb == vbios_mb)
    print("  CONTRASTE con amdgpu_vram_mm (lo que ve el kernel):")
    print("    VBIOS  usMemorySize          = %d MB" % vbios_mb)
    print("    kernel total                 = %d MiB" % kernel_mb)
    print("    -> %s" % ("COINCIDEN" if coincide else "NO COINCIDEN"))
    pn = d[p + VRAM_V8_PN_OFFSET:p + VRAM_V8_PN_OFFSET + 20].split(b"\x00")[0]
    print()
    print("  strMemPNString = %r es el part number fisico de la memoria." % pn)
    print("  Es un dato del firmware, no una inferencia: identifica la")
    print("  GDDR5 concreta que lleva esta tarjeta.")
    print()
    print("LO QUE NO SE AFIRMA")
    print("  ucMemoryType = 0x%02x y ucChannelWidth = %d no tienen"
          % (u8(d, p + 11), u8(d, p + 13)))
    print("  interpretacion establecida. El comentario del header dice que")
    print("  el nibble bajo de ucMemoryType 'must not be used for now', y")
    print("  ucChannelWidth se documenta como 0=16bit 1=32bit 2=64bit, asi")
    print("  que un 5 no encaja. Se imprime el valor crudo y se deja asi.")
    return 0 if coincide else 5


# ---------------------------------------------------------------------------
# EL PPTABLE v1, Y POR QUE ESTA SEPARADO DE `tablas`
# ---------------------------------------------------------------------------
# `tablas` localiza y da el HEADER de cada tabla, y dice explicitamente que el
# CONTENIDO no se decodifica. Aqui se decodifica UNA tabla, la que explica una
# medicion: PowerPlayInfo, y dentro de ella la tabla de dependencia de reloj de
# memoria. Es la que responde de donde sale el mclk que se mide en reposo.
#
# EL LAYOUT NO SE ESCRIBE A MANO. Los offsets se CALCULAN de la lista de campos
# de ATOM_Tonga_POWERPLAYTABLE (pptable_v1_0.h), y luego se comprueba contra
# usTableSize, que el propio struct lleva. Ese es el motivo de que la herramienta
# sea creible: un layout correcto se reconoce solo, porque el formato ofrece un
# checksum de si mismo. Si el layout fuera erroneo, usTableSize no casaria y esto
# dira INVALID en vez de imprimir numeros.
#
# Se calcula en pack(1), que es como van las tablas ATOM, y eso tambien se
# comprueba: si usTableSizeCalculado != usTableSizeLeido, no se sigue.
PPTX_CAMPOS = [
    ("sHeader", 4), ("ucTableRevision", 1), ("usTableSize", 2),
    ("ulGoldenPPID", 4), ("ulGoldenRevision", 4), ("usFormatID", 2),
    ("usVoltageTime", 2), ("ulPlatformCaps", 4),
    ("ulMaxODEngineClock", 4), ("ulMaxODMemoryClock", 4),
    ("usPowerControlLimit", 2), ("usUlvVoltageOffset", 2),
    ("usStateArrayOffset", 2), ("usFanTableOffset", 2),
    ("usThermalControllerOffset", 2), ("usReserv", 2),
    ("usMclkDependencyTableOffset", 2), ("usSclkDependencyTableOffset", 2),
    ("usVddcLookupTableOffset", 2), ("usVddgfxLookupTableOffset", 2),
    ("usMMDependencyTableOffset", 2), ("usVCEStateTableOffset", 2),
    ("usPPMTableOffset", 2), ("usPowerTuneTableOffset", 2),
    ("usHardLimitTableOffset", 2), ("usPCIETableOffset", 2),
    ("usGPIOTableOffset", 2), ("usReserved[6]", 12),
]
PPTX_OFF, _pos = {}, 0
for _n, _sz in PPTX_CAMPOS:
    PPTX_OFF[_n] = _pos
    _pos += _sz
PPTX_SIZE = _pos

# Los tamaños de registro se CALCULAN de sus listas de campos, NUNCA a mano.
#
# MEDIDO, Y ESTO ES UN ERROR QUE COMETI AL ESCRIBIR LA PRIMERA VERSION: puse
# SCLK_REC = 12 a mano y el registro suma 11. Con 12 el volcado daba 1879048199 y
# 134217733 como si fueran relojes, y la herramienta los imprimio sin protestar.
# Lo grave no es el 12: es que imprimio numeros sin plausibilidad como si fueran
# un dato. Un reloj de graficos de 1879048 MHz no es un dato raro, es un dato
# imposible, y una herramienta que no distingue las dos cosas no se puede usar
# como autoridad.
#
# Y hay un detalle que hace esto peor y no mejor: los DOS tamaños caben dentro de
# la tabla, asi que ningun control de limites los separa. Por eso el control de
# plausibilidad no es opcional, es la unica defensa que queda.
MCLK_CAMPOS = [("ucVddcInd", 1), ("usVddci", 2), ("usVddgfxOffset", 2),
               ("usMvdd", 2), ("ulMclk", 4), ("usReserved", 2)]
# El registro de sclk depende de la REVISION de la tabla, y el driver lo hace
# explicito: `if (sclk_dep_table->ucRevId < 1)` usa ATOM_Tonga_..., y la otra
# rama usa ATOM_Polaris_..., que anade ulSclkOffset. 11 + 4 = 15.
#
# MEDIDO, y con dos vias independientes: (a) el control de plausibilidad de esta
# herramienta, applied a los 144 candidatos de (tamano, desplazamiento), deja UN
# SOLO con todos los relojes plausibles: 15 con desplazamiento 3. (b) el codigo
# del driver, que para ucRevId >= 1 usa el registro de Polaris. Las dos dan 15.
# La herramienta NO busca el tamano: usa el del struct, y el control de
# plausibilidad queda como el que avisa si alguna vez dejaran de encajar.
SCLK_CAMPOS_TONGA = [("ucVddInd", 1), ("usVddcOffset", 2), ("ulSclk", 4),
                     ("usEdcCurrent", 2), ("ucReliabilityTemperature", 1),
                     ("ucCKSVOffsetandDisable", 1)]
SCLK_CAMPOS_POLARIS = SCLK_CAMPOS_TONGA + [("ulSclkOffset", 4)]


def _tam(campos):
    return sum(sz for _, sz in campos)


def _desplaz(campos, campo):
    o = 0
    for n, sz in campos:
        if n == campo:
            return o
        o += sz
    raise KeyError(campo)


MCLK_REC = _tam(MCLK_CAMPOS)
SCLK_REC = _tam(SCLK_CAMPOS_TONGA)
SCLK_REC_POLARIS = _tam(SCLK_CAMPOS_POLARIS)

# Un reloj de memoria o de graficos de esta familia esta en el orden de
# 10^5..10^6 kHz. Fuera de eso no es un reloj raro: es un byte leido en el sitio
# equivocado, y decirlo es parte del contrato.
PLO_CLOCKS_KHZ = (10000, 2000000)


def _layout_ppt():
    """El layout se recalcula cada vez, para que no pueda desincronizarse de la
    lista de campos."""
    off, pos = {}, 0
    for n, sz in PPTX_CAMPOS:
        off[n] = pos
        pos += sz
    return off, pos


def _dep_entries(d, base, campos, nombre):
    """
    Vuelca una tabla de dependencia, con el registro CALCULADO de sus campos.

    Devuelve ademas si los relojes son plausibles. No es un adorno: es lo unico
    que distingue un tamano de registro correcto de uno equivocado, porque con
    el equivocado los bytes siguen cabiendo y no hay ninguna otra senal.
    """
    recsz = _tam(campos)
    desp = _desplaz(campos, "ulMclk" if "ulMclk" in [c for c, _ in campos]
                    else "ulSclk")
    rev = u8(d, base)
    n = u8(d, base + 1)
    filas = []
    plausible = True
    for i in range(n):
        b = base + 2 + i * recsz
        if b + recsz > len(d):
            raise RomInvalido("%s: la entrada %d se sale del ROM (offset 0x%X)"
                              % (nombre, i, b))
        clk = u32(d, b + desp)
        if not (PLO_CLOCKS_KHZ[0] <= clk <= PLO_CLOCKS_KHZ[1]):
            plausible = False
        filas.append((i, b, clk))
    return rev, n, filas, recsz, desp, plausible


def cmd_ppt(d, a):
    """
    Decodifica PowerPlayInfo y sus tablas de dependencia de reloj.

    Se valida ANTES de imprimir nada: si el layout no casa con usTableSize, el
    resultado es INVALID, no una lista de numeros plausibles. Esa distincion es
    la que separa esta herramienta de buscar un valor hasta encontrar algo que
    encaje.
    """
    valida(d)
    masters = buscar_masters(d)
    if not masters:
        print("INVALID: no se encuentra la master data table, el layout del")
        print("corpus no describe este ROM. No es 'no hay tabla'.")
        return 4
    mt = masters[0]
    idx = TABLAS_MASTER.index("PowerPlayInfo")
    pp = u16(d, mt + HEADER_COMUN + 2 * idx)
    if pp == 0:
        print("INVALID: PowerPlayInfo no esta presente (offset 0).")
        return 4
    sz = u16(d, pp)
    if pp + sz > len(d):
        print("INVALID: PowerPlayInfo en 0x%X declara %d bytes y el ROM tiene %d"
              % (pp, sz, len(d)))
        return 4

    off, calc = _layout_ppt()
    leido = u16(d, pp + off["usTableSize"])
    print("PowerPlayInfo en 0x%04X, %d bytes, formato %d contenido %d"
          % (pp, sz, u8(d, pp + 2), u8(d, pp + 3)))
    print("  master data table en 0x%04X, PowerPlayInfo es la tabla %d de %d"
          % (mt, idx + 1, len(TABLAS_MASTER)))
    print()
    print("VALIDACION DEL LAYOUT, que es lo que da credibility al resto:")
    print("  usTableSize calculado del layout = %d" % calc)
    print("  usTableSize leido del ROM        = %d" % leido)
    if calc != leido:
        print("  NO COINCIDE -> layout NO demostrado. Se para aqui.")
        print("  No se imprime ninguna tabla: preferible INVALID a numeros falsos.")
        return 4
    print("  COINCIDE -> el layout esta demostrado")
    uc, crev = u8(d, pp + off["ucTableRevision"]), u16(d, pp + off["usFormatID"])
    print("  ucTableRevision = %d   usFormatID = %d" % (uc, crev))
    print("  usVoltageTime = %d us (microsegundos)"
          % u16(d, pp + off["usVoltageTime"]))
    print("  ulMaxODEngineClock = %d kHz   ulMaxODMemoryClock = %d kHz"
          % (u32(d, pp + off["ulMaxODEngineClock"]),
             u32(d, pp + off["ulMaxODMemoryClock"])))
    print()

    nombres = {"usStateArrayOffset": "StateArray",
               "usFanTableOffset": "FanTable",
               "usThermalControllerOffset": "ThermalController",
               "usMclkDependencyTableOffset": "MclkDependencyTable",
               "usSclkDependencyTableOffset": "SclkDependencyTable",
               "usVddcLookupTableOffset": "VddcLookupTable",
               "usVddgfxLookupTableOffset": "VddgfxLookupTable",
               "usMMDependencyTableOffset": "MMDpendencyTable",
               "usVCEStateTableOffset": "VCEStateTable",
               "usPPMTableOffset": "PPMTable",
               "usPowerTuneTableOffset": "PowerTuneTable",
               "usHardLimitTableOffset": "HardLimitTable",
               "usPCIETableOffset": "PCIETable",
               "usGPIOTableOffset": "GPIOTable"}
    dentro = fuera = 0
    print("SUBTABLAS que declara la cabecera:")
    for campo, nombre in nombres.items():
        v = u16(d, pp + off[campo])
        if v == 0:
            print("  %-22s ausente" % nombre)
            fuera += 1
            continue
        ok = 0 < v < sz
        dentro += ok
        print("  %-22s @0x%04X (%4d) %s" % (nombre, v, v, "" if ok else "FUERA"))
    print("  -> %d subtablas dentro de la tabla, %d ausentes" % (dentro, fuera))
    print()

    # La de memoria: la que explica el mclk medido.
    mclk_off = u16(d, pp + off["usMclkDependencyTableOffset"])
    if mclk_off:
        rev, n, filas, recsz, desp, ok = _dep_entries(d, pp + mclk_off,
                                                    MCLK_CAMPOS, "MCLK")
        print("TABLA DE DEPENDENCIA DE MCLK, en 0x%04X" % (pp + mclk_off))
        print("  ucRevId = %d   ucNumEntries = %d   registro = %d bytes"
              % (rev, n, recsz))
        print()
        print("  ATOM_Tonga_MCLK_Dependency_Record { ucVddcInd; usVddci;")
        print("    usVddgfxOffset; usMvdd; ulMclk; usReserved; }")
        print()
        print("  %-3s %-10s %-8s %-15s %-8s %-12s %-9s %s"
              % ("#", "ucVddcInd", "usVddci", "usVddgfxOffset", "usMvdd",
                 "ulMclk", "x10 kHz", "MHz"))
        for i, b, clk in filas:
            print("  %-3d %-10d %-8d %-15d %-8d %-12d %-9d %.0f"
                  % (i, u8(d, b), u16(d, b + 1), u16(d, b + 3),
                     u16(d, b + 5), clk, clk * 10, clk * 10 / 1000.0))
        if not ok:
            print()
            print("  INVALID: alguno de esos relojes esta fuera de %d..%d kHz."
                  % PLO_CLOCKS_KHZ)
            print("  Un reloj fuera de ese rango no es un reloj raro: son bytes")
            print("  leidos en el sitio equivocado. El tamano de registro NO esta")
            print("  demostrado y la tabla NO se da por buena.")
            return 4
        print()
        print("  UNIDAD: el driver copia el valor CRUDO, sin multiplicar")
        print("  (process_pptables_v1_0.c: clk = le32_to_cpu(ulMclk)). El x10 es la")
        print("  convencion de unidades de ATOM, y se comprueba por si los tres")
        print("  valores son relojes de memoria plausibles para esta tarjeta.")
        print("  NO se aplica: se informa, para que el multiplicar sea decision")
        print("  de quien lee y no un dato escondido en la herramienta.")
        print()

    sclk_off = u16(d, pp + off["usSclkDependencyTableOffset"])
    if sclk_off:
        # el registro lo elige la revision, igual que el driver
        campos_s = SCLK_CAMPOS_TONGA if u8(d, pp + sclk_off) < 1 else SCLK_CAMPOS_POLARIS
        nombre_r = "Tonga" if u8(d, pp + sclk_off) < 1 else "Polaris"
        rev, n, filas, recsz, desp, ok = _dep_entries(d, pp + sclk_off,
                                                    campos_s, "SCLK")
        print("  ucRevId = %d -> registro %s de %d bytes, por revision"
              % (rev, nombre_r, recsz))
        print("TABLA DE DEPENDENCIA DE SCLK, en 0x%04X" % (pp + sclk_off))
        print("  ucNumEntries = %d" % n)
        print()
        if not ok:
            print()
            print("  INVALID: alguno de esos relojes esta fuera de %d..%d kHz."
                  % PLO_CLOCKS_KHZ)
            print("  El tamano de registro NO esta demostrado.")
            return 4
        print("  %-3s %-9s %-13s %-11s %-9s %-9s %s"
              % ("#", "ucVddInd", "usVddcOffset", "ulSclk", "x10 kHz", "MHz",
                 "usEdcCurrent"))
        for i, b, clk in filas:
            print("  %-3d %-9d %-13d %-11d %-9d %-9.0f %d"
                  % (i, u8(d, b), u16(d, b + 1), clk, clk * 10, clk * 10 / 1000.0,
                     u16(d, b + 7)))
        print()
    print("LIMITES, DICHOS:")
    print("  - Se decodifica PowerPlayInfo y sus tablas de dependencia. Las otras")
    print("    subtablas se LOCALIZAN y no se decodifican: son NOT_IMPLEMENTED,")
    print("    no tablas vacias.")
    print("  - El x10 sobre los relojes es la convencion de ATOM, informada, no")
    print("    aplicada. El valor crudo es el dato.")
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="parseo del VBIOS ATOM de la RX550")
    ap.add_argument("cmd", choices=["rom", "tablas", "firmware", "vram", "ppt",
                                    "autotest"])
    ap.add_argument("fichero", nargs="?", default="capturas/amdgpu_vbios.txt")
    a = ap.parse_args()
    # El autotest fabrica su propio ROM y no necesita el fichero de disco.
    if a.cmd == "autotest":
        return cmd_autotest(a)
    # El resto necesita el ROM, asi que se carga ANTES de despachar. La
    # primera version de este dispatch llamaba a cmd_firmware(d, a) antes de
    # que existiera la variable d: NameError en tiempo de ejecucion.
    if not os.path.exists(a.fichero):
        print("no existe %s" % a.fichero)
        print("Se obtiene con: RX550_SUDO_PASS=... captura.py")
        return 2
    d = open(a.fichero, "rb").read()
    if a.cmd == "firmware":
        return cmd_firmware(d, a)
    if a.cmd == "vram":
        return cmd_vram(d, a)
    if a.cmd == "rom":
        return cmd_rom(d, a)
    if a.cmd == "ppt":
        return cmd_ppt(d, a)
    return cmd_tablas(d, a)


if __name__ == "__main__":
    sys.exit(main())

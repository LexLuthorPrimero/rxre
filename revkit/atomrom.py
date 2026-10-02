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


def main():
    ap = argparse.ArgumentParser(
        description="parseo del VBIOS ATOM de la RX550")
    ap.add_argument("cmd", choices=["rom", "tablas", "firmware", "autotest"])
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
    if a.cmd == "rom":
        return cmd_rom(d, a)
    return cmd_tablas(d, a)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Construye una ROM ATOMBIOS VALIDA por ESPECIFICACION DEL DRIVER, no leyendo el
# decodificador, y la pasa por el. Es el contraste cruzado independiente que faltaba.
#
# POR QUE ESTE FICHERO EXISTE, y no un self-test mas del decodificador:
#
# El decodificador se valida contra vectores que genera el mismo decodificador. Eso
# comprueba que el decodificador es consistente consigo mismo, y NADA mas. Si su
# criterio de aceptacion esta equivocado, sus vectores lo confirman igual, porque
# los dos vienen del mismo sitio.
#
# MEDIDO 2026-10-04: cuatro ROM sinteticas escritas por el nodo principal (incluida
# una de 131072 B con la firma ATOMv2 en 0) las rechazo el decodificador con rc=4, y
# por eso el rc=5 de ROM truncada, que el self-test declara, no se pudo reproducir
# desde fuera. Motivo: no se puede construir una entrada valida sin conocer el
# criterio de aceptacion, y ese criterio no estaba escrito.
#
# Aqui el criterio se toma del DRIVER, de fuente primaria, y se implementa aqui. Si el
# decodificador acepta o rechaza segun lo que dice el driver, hay concordancia. Si no,
# la divergencia es el hallazgo.
#
# TODO lo de abajo lleva la cita fichero:linea del driver. No hay ningun offset que no
# se pueda citar.
import struct
import subprocess
import sys

DECODER = sys.argv[1] if len(sys.argv) > 1 else "/tmp/opencode/rx550_atom_dec"

# --- constantes, del driver, no del decodificador -------------------------------
# amdgpu_bios.c:44
AMD_IS_VALID_VBIOS = lambda b: b[0] == 0x55 and b[1] == 0xAA
# atom.h:32
ATOM_BIOS_MAGIC = 0xAA55
# atom.h:33  ATOM_ATI_MAGIC_PTR = 0x30 ; atom.h:34 ATOM_ATI_MAGIC = " 761295520"
ATOM_ATI_MAGIC_PTR = 0x30
ATOM_ATI_MAGIC = b" 761295520"
# atom.h:35  ATOM_ROM_TABLE_PTR = 0x48
ATOM_ROM_TABLE_PTR = 0x48
# atom.h:37,38
ATOM_ROM_MAGIC = b"ATOM"
ATOM_ROM_MAGIC_PTR = 4
# atom.h:42,43
ATOM_ROM_CMD_PTR = 0x1E
ATOM_ROM_DATA_PTR = 0x20
# atom.h:52
ATOM_DATA_IIO_PTR = 0x32

# GetIndexIntoMasterTable(DATA, GFX_Info) = offsetof(ATOM_MASTER_LIST_OF_DATA_TABLES,
# GFX_Info) / sizeof(USHORT)   -- atombios.h:7151, y la estructura en atombios.h:2783.
# Derivado de la estructura contando campos, no de lo que haga el decodificador.
ATOM_MASTER_LIST_OF_DATA_TABLES = [
    "UtilityPipeLine", "MultimediaCapabilityInfo", "MultimediaConfigInfo",
    "StandardVESA_Timing", "FirmwareInfo", "PaletteData", "LCD_Info",
    "DIGTransmitterInfo", "SMU_Info", "SupportedDevicesInfo", "GPIO_I2C_Info",
    "VRAM_UsageByFirmware", "GPIO_Pin_LUT", "VESA_ToInternalModeLUT", "GFX_Info",
    "PowerPlayInfo", "GPUVirtualizationInfo", "SaveRestoreInfo", "PPLL_SS_Info",
    "OemInfo", "XTMDS_Info", "MclkSS_Info", "Object_Header", "IndirectIOAccess",
    "MC_InitParameter", "ASIC_VDDC_Info", "ASIC_InternalSS_Info", "TV_VideoMode",
    "VRAM_Info", "MemoryTrainingInfo", "IntegratedSystemInfo", "ASIC_ProfilingInfo",
    "VoltageObjectInfo", "PowerSourceInfo", "ServiceInfo",
]
IX_GFX_INFO = ATOM_MASTER_LIST_OF_DATA_TABLES.index("GFX_Info")

CU16 = lambda off: struct.unpack_from("<H", rom, off)[0]


def comprobar_criterio():
    """La regla del driver, comprobada sobre la ROM antes de darsela al decodificador.

    Si esto falla, el fallo es MIO y no del decodificador, y hay que decirlo antes de
    culpar a la herramienta."""
    fallos = []
    if not AMD_IS_VALID_VBIOS(rom):
        fallos.append("AMD_IS_VALID_VBIOS (amdgpu_bios.c:44)")
    if CU16(0) != ATOM_BIOS_MAGIC:
        fallos.append("CU16(0) != ATOM_BIOS_MAGIC (atom.c:1560)")
    if rom[ATOM_ATI_MAGIC_PTR:ATOM_ATI_MAGIC_PTR + len(ATOM_ATI_MAGIC)] != ATOM_ATI_MAGIC:
        fallos.append("ATOM_ATI_MAGIC en 0x%02X (atom.c:1565-1571)" % ATOM_ATI_MAGIC_PTR)
    base = CU16(ATOM_ROM_TABLE_PTR)
    if rom[base + ATOM_ROM_MAGIC_PTR:base + ATOM_ROM_MAGIC_PTR + 4] != ATOM_ROM_MAGIC:
        fallos.append("ATOM_ROM_MAGIC en base+4 (atom.c:1574-1580)")
    # amdgpu_bios.c:66-70  exige ademas que el puntero no sea cero, y :72-76 que
    # el tamaño cubra base+8
    if base == 0:
        fallos.append("bios_header_start == 0 (amdgpu_bios.c:67-70)")
    if len(rom) < base + 8:
        fallos.append("size < bios_header_start + 8 (amdgpu_bios.c:72-76)")
    if CU16(base + ATOM_ROM_MAGIC_PTR) == 0:
        fallos.append("la ROM magic esta vacia")
    return fallos


def construir(size=131072, base=0x0040, data_table=0x0100, cmd_table=0x0200,
              gfx_info=0x0300, iio=0x0280, con_iio=True,
              campos=(8, 4, 5, 2, 4, 4), frev=1, crev=1,
              firma=(0x55, 0xAA), ati_magic=ATOM_ATI_MAGIC,
              rom_magic=ATOM_ROM_MAGIC):
    """construye la ROM.

    `campos` son los seis bytes de GFX_Info en +4, en el orden del struct:
      +4 max_shader_engines, +5 max_tile_pipes, +6 max_cu_per_sh,
      +7 max_sh_per_se, +8 max_backends_per_se, +9 max_texture_channel_caches
    """
    global rom
    rom = bytearray(b"\x00" * size)
    rom[0] = firma[0]
    rom[1] = firma[1]
    rom[ATOM_ATI_MAGIC_PTR:ATOM_ATI_MAGIC_PTR + len(ATOM_ATI_MAGIC)] = ati_magic
    struct.pack_into("<H", rom, ATOM_ROM_TABLE_PTR, base)
    rom[base + ATOM_ROM_MAGIC_PTR:base + ATOM_ROM_MAGIC_PTR + 4] = rom_magic
    struct.pack_into("<H", rom, base + ATOM_ROM_CMD_PTR, cmd_table)
    struct.pack_into("<H", rom, base + ATOM_ROM_DATA_PTR, data_table)
    # atom.c:1583  data_table ; :1584  atom_index_iio(CU16(data_table+0x32)+4)
    struct.pack_into("<H", rom, data_table + ATOM_DATA_IIO_PTR, iio if con_iio else 0)
    # atom.c:1646-1648  offset = index*2 + 4 ; idx = CU16(data_table + offset)
    struct.pack_into("<H", rom, data_table + 4 + IX_GFX_INFO * 2, gfx_info)
    # la cabecera comun de la tabla: atom.c:1653-1659  size u16, frev u8, crev u8
    cuerpo = len(campos) + 6
    struct.pack_into("<H", rom, gfx_info, cuerpo)
    rom[gfx_info + 2] = frev
    rom[gfx_info + 3] = crev
    for k, v in enumerate(campos):
        rom[gfx_info + 4 + k] = v
    # una tabla IIO minima, para que atom_index_iio no devuelva NULL
    rom[iio:iio + 4] = b"ATOM"
    return rom


def pasar(nombre, **kw):
    construir(**kw)
    fallos = comprobar_criterio()
    if fallos:
        print("  %-34s DESCARTADA, mi ROM no cumple el criterio del driver: %s"
              % (nombre, "; ".join(fallos)))
        return None
    ruta = "/tmp/opencode/indep_%s.bin" % nombre
    with open(ruta, "wb") as fh:
        fh.write(bytes(rom))
    r = subprocess.run([DECODER, ruta], capture_output=True, text=True, timeout=120)
    primera = (r.stderr.strip().split("\n") + [""])[0][:62]
    print("  %-34s rc=%d  %s" % (nombre, r.returncode, primera))
    return r


print("indice de GFX_Info derivado de atombios.h:2783 y :7151: %d" % IX_GFX_INFO)
print("el puntero vive en data_table + %d" % (4 + IX_GFX_INFO * 2))
print()
print("el driver aceptaria estas ROM:")
print()
r_ok = pasar("valida_8cu", campos=(8, 4, 5, 2, 4, 4))
print()
print("y estos son los casos que tienen que RECHAZAR:")
print()
# amdgpu_bios.c:44  AMD_IS_VALID_VBIOS exige 0x55 0xAA.  Aqui no se cumple.
pasar("firma_incorrecta_0xEEAA", firma=(0xEE, 0xAA), campos=(8, 4, 5, 2, 4, 4))
# atom.c:1565-1571  el ATI magic no esta donde 0x30 dice
pasar("ati_magic_ausente", ati_magic=b"XXXXXXXXXX", campos=(8, 4, 5, 2, 4, 4))
# atom.c:1574-1580  la ROM magic no es "ATOM"
pasar("rom_magic_mala", rom_magic=b"NOPE", campos=(8, 4, 5, 2, 4, 4))
# sin la IIO: atom.c:1584-1586  atom_index_iio NULL -> no hay contexto
pasar("sin_iio", con_iio=False, campos=(8, 4, 5, 2, 4, 4))
# GFX_Info V2_4, donde el byte +7 se llama reserved en atomfirmware.h:1844
pasar("v2_4_tilepipes_es_reserved", frev=2, crev=4, campos=(8, 4, 5, 2, 4, 4))
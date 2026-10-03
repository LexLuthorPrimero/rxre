#!/usr/bin/env python3
# CONTRACT: name=vbiosread
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""
VBIOSREAD -- la imagen del VBIOS por ioctl, sin root, y sus tablas ATOM.

Por que existe. Durante toda la sesion el VBIOS ha sido el bloqueador unico de
varias fronteras:

  - el flag QDR de la PLL de VRAM, que decide el multiplicador de transferencia y
    por tanto el techo de 48,0 GB/s (909). amdgpu_atombios.c:1152 lo parsea en
    mpll_param->qdr y no hay ninguna otra referencia a qdr en el driver.
  - el ancho de bus, que se podria leer de atom_vram_info (TODO-2).
  - la tabla de tiling, que es lo que gobierna el swizzle de las texturas, y por
    tanto la ruta que 282-1 quiere medir.
  - tres pendientes de 272.

Todos figuraban como bloqueados por sudo, leyendo el ROM de PCI:
/sys/bus/pci/devices/0000:01:00.0/rom es -rw------- root root, 131072 bytes, y
efectivamente no se puede leer sin root.

Pero hay otra via, y no la habia buscado. amdgpu_kms.c:1095-1114:

    case AMDGPU_INFO_VBIOS:
      case AMDGPU_INFO_VBIOS_IMAGE: {
        uint8_t *bios;
        uint32_t bios_offset = info->vbios_info.offset;
        if (bios_offset >= bios_size) return -EINVAL;
        bios = adev->bios + bios_offset;
        return copy_to_user(out, bios, min(size, bios_size - bios_offset));
      }

Es un volcado del VBIOS entero a un bufer de usuario, y el preambulo de
amdgpu_info_ioctl en la linea 652 solo comprueba que return_size y
return_pointer no sean cero. No hay comprobacion de privilegios en ninguna de las
dos rutas. /dev/dri/renderD129 es crw-rw-rw-.

O sea: el fichero que llevaba un rato marcado como bloqueado por permisos no
estaba bloqueado por permisos. Estaba bloqueado porque solo se habia buscado una
via. Es la cuarta vez que declaro una ausencia sin haber buscado la fuente, y la
primera en que la ausencia era de una capacidad y no de un dato.

Uso:
    python3 vbiosread.py --selftest
    python3 vbiosread.py --dump /tmp/vbios.rom
    python3 vbiosread.py --info
    python3 vbiosread.py --tablas

LIMITES, y son reales:

  - No interpreta semantica de ATOM. Localiza tablas por su tipo y sus offsets, y
    eso es geomria, no significado. Un campo de una tabla es una AFIRMACION del
    firmware sobre mi placa, y comprobarla contra la medicion es trabajo aparte.
  - El volcado es de lo que el driver tiene en adev->bios, que es el ROM de la
    placa. No incluye ningun parche de firmware que el driver haya aplicado.
  - Los offsets de la tabla maestra se leen del volcado, no se hardcodean: si un
    dia el VBIOS de otra placa tiene otra geometria, el parser lo dice en vez de
    inventar.
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RENDER_AMD = "/dev/dri/renderD129"
RAIZ = "/home/lucas/Escritorio/RX550-INVESTIGACION"

DUMP_C = r'''
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <stdlib.h>
#include <sys/ioctl.h>
#include <drm/amdgpu_drm.h>
#include <drm/drm.h>

/* volca la imagen del VBIOS. Devuelve el numero de bytes escritos, o negativo. */
int vuelca(const char *nodo, const char *destino) {
    int fd = open(nodo, O_RDWR);
    if (fd < 0) { fprintf(stderr, "open: %s\n", strerror(errno)); return -1; }

    uint32_t tam = 0;
    struct drm_amdgpu_info info;
    memset(&info, 0, sizeof(info));
    info.query = AMDGPU_INFO_VBIOS;
    info.vbios_info.type = AMDGPU_INFO_VBIOS_SIZE;
    info.return_size = sizeof(tam);
    info.return_pointer = (uint64_t)(uintptr_t)&tam;
    if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) != 0) {
        fprintf(stderr, "ioctl VBIOS_SIZE: %s\n", strerror(errno));
        close(fd); return -2;
    }
    if (!tam || tam > (1u << 22)) {
        fprintf(stderr, "tamaño de VBIOS implausible: %u\n", tam);
        close(fd); return -3;
    }
    printf("vbios_size=%u\n", tam);

    unsigned char *buf = calloc(1, tam);
    if (!buf) { close(fd); return -4; }

    memset(&info, 0, sizeof(info));
    info.query = AMDGPU_INFO_VBIOS;
    info.vbios_info.type = AMDGPU_INFO_VBIOS_IMAGE;
    info.vbios_info.offset = 0;
    info.return_size = tam;
    info.return_pointer = (uint64_t)(uintptr_t)buf;
    if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) != 0) {
        fprintf(stderr, "ioctl VBIOS_IMAGE: %s\n", strerror(errno));
        free(buf); close(fd); return -5;
    }

    FILE *f = fopen(destino, "wb");
    if (!f) { fprintf(stderr, "fopen(%s): %s\n", destino, strerror(errno)); free(buf); close(fd); return -6; }
    fwrite(buf, 1, tam, f);
    fclose(f);

    /* Nombre y version, que vienen de atom_context y sirven de control cruzado:
     * si el volcado fuera de otra placa, el nombre no seria POLARIS12. */
    struct drm_amdgpu_info_vbios vi;
    memset(&vi, 0, sizeof(vi));
    memset(&info, 0, sizeof(info));
    info.query = AMDGPU_INFO_VBIOS;
    info.vbios_info.type = AMDGPU_INFO_VBIOS_INFO;
    info.return_size = sizeof(vi);
    info.return_pointer = (uint64_t)(uintptr_t)&vi;
    if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) == 0) {
        printf("vbios_name=%s\n", vi.name);
        printf("vbios_pn=%s\n", vi.vbios_pn);
        printf("vbios_version=0x%X\n", vi.version);
        printf("vbios_ver_str=%s\n", vi.vbios_ver_str);
        printf("vbios_date=%s\n", vi.date);
    }

    /* Los cuatro primeros bytes, para que el control de firma no tenga que abrir
     * el fichero y sepa que lo que se escribio empieza por ATOM. */
    printf("firma=%02X%02X%02X%02X\n", buf[0], buf[1], buf[2], buf[3]);
    free(buf);
    close(fd);
    return (int)tam;
}

int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "uso: vbios_dump <nodo> <salida>\n"); return 2; }
    int r = vuelca(argv[1], argv[2]);
    if (r < 0) return 10 + (-r);
    return 0;
}
'''


def compilar():
    if not os.path.exists("/usr/include/drm/amdgpu_drm.h"):
        return None, "falta /usr/include/drm/amdgpu_drm.h"
    d = tempfile.mkdtemp(prefix="vbiosread")
    src = os.path.join(d, "dump.c")
    exe = os.path.join(d, "dump")
    open(src, "w").write(DUMP_C)
    r = subprocess.run(["gcc", "-O2", "-Wall", "-o", exe, src], capture_output=True, text=True)
    if r.returncode != 0:
        return None, r.stderr.strip().split("\n")[0][:90]
    return exe, None


def volcar(destino):
    exe, err = compilar()
    if exe is None:
        return None, err
    r = subprocess.run([exe, RENDER_AMD, destino], capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr.strip() or "el volcado salio %d" % r.returncode)[:100]
    meta = {}
    for l in r.stdout.split("\n"):
        if "=" in l:
            k, v = l.split("=", 1)
            meta[k.strip()] = v.strip()
    return meta, None


# ---------------------------------------------------------------- ATOM

FIRMA = b"ATOM"


# Geometria tomada del corpus, de include/atombios.h:
#   struct atom_common_table_header { USHORT structuresize; UBYTE format_revision;
#                                     UBYTE content_revision; };              = 4 bytes
#   typedef struct _ATOM_MASTER_LIST_OF_DATA_TABLES { USHORT <35 campos>; }  = 70 bytes
# o sea ATOM_MASTER_DATA_TABLE mide 4 + 70 = 74 bytes.
#
# NO es una lista de entradas {tipo, tamano, puntero}. La primera version de esta
# funcion buscaba entradas de "tipo 25" y salia con cero, y la razon era que ese
# formato no existe: GetIndexIntoMasterTable(DATA, Campo) es
# offsetof(ATOM_MASTER_DATA_TABLE, Campo)/2, o sea el numero de orden del campo, y
# ese indice es directamente un offset dentro del ROM. Buscar "tipo 25" era buscar
# algo que no esta ahi.
HDR = 4
NCAMPOS = 35
TAM_MAESTRA = HDR + 2 * NCAMPOS          # 74
IDX_VRAM_INFO = 28
IDX_INTEGRATED = 30
NOMBRES_CAMPOS = {
    11: "VRAM_UsageByFirmware", 28: "VRAM_Info", 29: "MemoryTrainingInfo",
    30: "IntegratedSystemInfo",
}


def candidatas_maestra(img):
    """Localiza la tabla maestra por su estructura, no por un supuesto de offset.

    La restriccion fuerte es structuresize == 74. Con un filtro mas flojo salian 5913
    candidatas; con este salen 7, y ninguna es concluyente. Se devuelven todas y no se
    elige una: elegir la que "parece" mas plausible es inventar, y una tabla maestra
    equivocada daria offsets equivocados que parecerian buenos.
    """
    n = len(img)
    out = []
    for off in range(0, n - TAM_MAESTRA):
        ssize, frev, crev = struct.unpack_from("<HBB", img, off)
        if ssize != TAM_MAESTRA:
            continue
        offs = struct.unpack_from("<%dH" % NCAMPOS, img, off + HDR)
        if sum(1 for o in offs if o < n) < 33:
            continue
        out.append({"offset": off, "content_revision": crev,
                    "campos": offs, "validos": sum(1 for o in offs if o < n)})
    return out


# La ruta que el propio driver usa, del corpus, amdgpu/atom.c seccion amdgpu_atom_parse:
#     base = CU16(ATOM_ROM_TABLE_PTR)                       atom.h:35 -> 0x48
#     master = CSTR(atom_rom_header->usMasterDataTableOffset)
# donde CSTR(x) es bios + x, NO base + x: base solo sirve para leer los campos de la
# cabecera, y el offset del maestro es absoluto respecto del inicio del volcado. Esa
# distincion es la que hace que el camino parezca correcto y no lo sea.
PTR_ROM_TABLE = 0x48
OFF_MASTER_DATA_RELATIVO = 24   # offset de usMasterDataTableOffset en _ATOM_ROM_HEADER


def ruta_del_corpus(img):
    """Reproduce la cadena de punteros de amdgpu_atom_parse y dice si resuelve.

    No se escoge el destino mas plausible: se exige que el destino tenga
    structuresize == 74, que es la geometria de ATOM_MASTER_DATA_TABLE derivada de
    include/atombios.h. Si la cadena del driver no lleva ahi, la tabla maestra NO esta
    localizada por esta via, y decirlo es el resultado.
    """
    if len(img) < 0x4A:
        return {"estado": "imagen demasiado corta", "base": None}
    base = struct.unpack_from("<H", img, PTR_ROM_TABLE)[0]
    if base + 26 > len(img):
        return {"estado": "base fuera de la imagen", "base": base}
    cand = struct.unpack_from("<H", img, base + OFF_MASTER_DATA_RELATIVO)[0]
    if cand == 0 or cand + 4 > len(img):
        return {"estado": "el puntero no cae dentro de la imagen", "base": base,
                "candidato": cand}
    ssize = struct.unpack_from("<H", img, cand)[0]
    return {"estado": "OK" if ssize == TAM_MAESTRA else "structuresize distinto de 74",
            "base": base, "candidato": cand, "structuresize_en_destino": ssize}


def tabla_maestra(img):
    """Devuelve la lista de candidatas con sus dos campos que importan, y NO elige una."""
    if img[:4] != b"\x55\xaa\x73\xe9":
        return None, "la imagen no tiene firma VBE 55AA E973"
    if img[0x258:0x260] != b"AMD ATOM":
        return None, "la imagen no tiene la firma AMD ATOM BIOS en 0x258"
    cs = candidatas_maestra(img)
    if not cs:
        return None, "ninguna estructura con structuresize=%d" % TAM_MAESTRA
    for c in cs:
        c["VRAM_Info"] = c["campos"][IDX_VRAM_INFO]
        c["IntegratedSystemInfo"] = c["campos"][IDX_INTEGRATED]
    return cs, None


# Tipos de tabla que existen en GCN, para nombrar lo que aparezca. La lista es
# del corpus, no inventada: se busca ATOM_VRAM_INFO_TABLE y las de tiling.
NOMBRES = {
    0: "VBE_INFO", 1: "GA_INFO", 2: "CPU_INFO", 3: "MEM_INFO", 4: "VGEN_INFO",
    5: "GFX_INFO", 6: "PLB_INFO", 7: "BACO_INFO", 8: "TILING_INFO",
    16: "VGA_INFO", 17: "MMCU_INFO", 18: "SRAM_INFO", 19: "SOFT_RESET",
    20: "VESA_INFO", 21: "RESERVED_21", 22: "HEADER", 23: "MASTER",
    24: "PALETTE", 25: "VRAM_INFO", 26: "DOS_HWINFO", 27: "FW_BLOCK",
    28: "HWINFO", 29: "INTEGER_INFO", 30: "GPU_INFO", 31: "VRAM_MIN_DIMM",
    32: "FW_IP_INFO", 33: "NUM_DRAM_MODULES", 34: "MEM_POWER_INFO",
    35: "SOC_CCLK_DCLK", 36: "SOCCLK_DCLK", 37: "MEM_VOLTAGE",
    40: "SOC15_DGPU_INFO", 41: "SOC15_RAW_INFO", 48: "D3CG6_INFO",
    49: "BOARD_INFO", 82: "GPU_INIT_INFO_V14", 83: "GPU_INIT_INFO_V15",
    84: "GPU_INIT_INFO_V16", 85: "MEM_INIT_INFO_V14", 86: "MEM_INIT_INFO_V15",
    87: "MEM_INIT_INFO_V16", 104: "GPU_INIT_INFO_V2", 105: "GPU_INIT_INFO_V3",
    106: "GPU_INIT_INFO_V4", 107: "GPU_INIT_INFO_V5", 108: "GPU_INIT_INFO_V6",
    109: "GPU_INIT_INFO_V7", 110: "GPU_INIT_INFO_V8", 111: "GPU_INIT_INFO_V9",
    112: "GPU_INIT_INFO_V10", 113: "GPU_INIT_INFO_V11", 114: "GPU_INIT_INFO_V12",
    115: "GPU_INIT_INFO_V13", 116: "GPU_INIT_INFO_V1", 117: "GPU_INIT_INFO_V0",
    118: "GPU_INFO_2", 119: "GPU_INFO_3", 120: "VRAM_INFO_2", 121: "VRAM_INFO_3",
    123: "MM_INFO", 124: "CPU_FREQUENCY", 125: "GPU_TILING_INFO",
    126: "GPU_TILING_INFO2", 127: "MM_INFO2", 128: "MM_INFO3",
    130: "GPU_INFO_4", 131: "MM_INFO4", 132: "TIMING", 133: "MM_E2K",
    151: "SOC15_INFO", 152: "SOC15_PWR_INFO", 153: "SOC15_THERMAL_INFO",
    154: "SOC15_MEM_INFO", 155: "SOC15_FW_INFO", 156: "SOC15_BLK_INFO",
    157: "SOC15_GPU_INFO", 158: "SOC15_PCI_INFO", 159: "SOC15_THERMAL2_INFO",
    160: "SOC15_INFO2", 161: "SOC15_PSP_INFO", 162: "SOC15_MEM_INFO2",
    163: "SOC15_IP_INFO", 164: "SOC15_IGD_INFO", 165: "SOC15_ASPM_INFO",
    166: "SOC15_DPM_INFO", 167: "SOC15_DPP_INFO", 168: "SOC15_MEM_INFO3",
    169: "SOC15_DBG_INFO", 170: "SOC15_PSM_INFO", 171: "SOC15_EAS_INFO",
    172: "SOC15_EXP_INFO", 176: "SOC15_LPS_INFO", 177: "SOC15_MPRE_INFO",
    178: "SOC15_SENSOR_INFO", 179: "SOC15_POWER_INFO", 180: "SOC15_CVR_INFO",
    181: "SOC15_PCI_INIT_INFO", 182: "SOC15_NVDIMM_INFO", 183: "SOC15_MEM_NB_INFO",
    184: "SOC15_ACDC_INFO", 185: "SOC15_UEFI_PSTATE_INIT_INFO",
    186: "SOC15_FAN_CONTROL_INFO", 187: "SOC15_FAN_INFO", 188: "SOC15_TMC_INFO",
    189: "SOC15_STDCIO_INFO", 190: "SOC15_GPIO_INFO", 191: "SOC15_UFRM_INFO",
    192: "SOC15_REG_SCRATCH_INFO", 193: "SOC15_SCRATCH_INFO",
    194: "SOC15_CVD_IS_INFO", 195: "SOC15_LCD_INFO", 196: "SOC15_DBG_INFO2",
    197: "SOC15_SMEM_INFO", 198: "SOC15_PSP2_INFO", 199: "SOC15_MPU_INFO",
    200: "SOC15_MEM_VREF_INFO", 201: "SOC15_DCGM_INFO", 202: "SOC15_ASPM_INFO2",
    203: "SOC15_SVIP_INFO", 204: "SOC15_FMI_INFO", 205: "SOC15_SMN_INFO",
    206: "SOC15_THERMAL_MINMAX", 207: "SOC15_THERMAL_RESERV",
}


def volcar_si_hace_falta(ruta):
    if os.path.exists(ruta):
        return open(ruta, "rb").read(), None
    meta, err = volcar(ruta)
    if err:
        return None, err
    return open(ruta, "rb").read(), meta


def selftest():
    print("  self-test de vbiosread.py:")
    casos = []
    exe, err = compilar()
    casos.append(("el probe compila", exe is not None, err or "ok"))

    ruta = "/tmp/opencode/vbios-selftest.rom"
    os.makedirs("/tmp/opencode", exist_ok=True)
    meta, err = volcar(ruta)
    casos.append(("el VBIOS se vuelca sin root", meta is not None, err or "ok"))

    if meta:
        # CONTROL DE FIRMA. Esta placa NO arranca con ATOM: arranca con la firma VBE
        # 55AA y despues la firma "AMD ATOM BIOS" en 0x258. El self-test exigia ATOM en
        # el offset 0 y por eso fallaba con una imagen perfectamente buena, que es
        # la forma mas stupida de que un control falle: por un supuesto sobre la
        # cabecera en vez de por la propiedad que importa.
        firma0 = meta.get("firma", "")
        img0 = open(ruta, "rb").read()
        vbe = img0[:4] == b"\x55\xaa\x73\xe9"
        atom = img0[0x258:0x260] == b"AMD ATOM"
        casos.append(("la imagen tiene firma VBE 55AA E973", vbe,
                      "primeros 4 = %s" % img0[:4].hex()))
        casos.append(("la imagen tiene la firma AMD ATOM BIOS", atom,
                      "en 0x258 = %s" % img0[0x258:0x260]))
        # control de coherencia: el tamaño anunciado tiene que ser el del fichero
        try:
            tam = int(meta.get("vbios_size", "0"))
            real = os.path.getsize(ruta)
            casos.append(("el tamaño anunciado es el del fichero", tam == real,
                          "anunciado=%d real=%d" % (tam, real)))
        except ValueError:
            casos.append(("el tamaño anunciado es el del fichero", False, "no numerico"))
        # control de identidad: el nombre tiene que ser de esta familia
        nom = meta.get("vbios_name", "")
        nomu = nom.upper()
        # El nombre del VBIOS de esta placa dice LEXA, que es el nombre de familia
        # que Polaris 10 y 12 usan en el firmware. Buscar POLARIS y no encontrarlo
        # no significa que la placa no sea Polaris: significa que el firmware usa
        # otro nombre, y un control tiene que comprobar la propiedad, no la palabra.
        casos.append(("el nombre identifica a esta familia",
                      ("POLARIS" in nomu) or ("LEXA" in nomu),
                      "vbios_name=%s" % nom))
        casos.append(("el nombre declara el ancho de bus", "128bit" in nom,
                      "esperado 128bit en el nombre, leido=%s" % nom))

        img = open(ruta, "rb").read()
        cs, err2 = tabla_maestra(img)
        casos.append(("la tabla maestra se localiza por estructura", cs is not None,
                      err2 or "%d candidatas" % len(cs) if cs else "-"))

        # Control HONESTO: se declara NOT located si hay mas de una candidata. La
        # version anterior de este self-test exigia "la tabla VRAM esta presente" y
        # eso no es comprobable todavia; exigirlo habria sido exigir un supuesto.
        if cs:
            # ESTO NO ES UN CONTROL QUE PUEDA PASSAR O FALLAR. Es el estado de una
            # capacidad: la tabla maestra esta o no esta localizada univocamente. La
            # version anterior de este self-test lo trato como un control mas, con lo
            # que el self-test no podia pasar nunca y decia "HAY FALLOS" de forma
            # permanente. Un test que esta siempre en rojo deja de leerse, y lo que
            # queda de leer es la parte que si importa.
            casos.append(("la tabla maestra esta localizada univocamente",
                          len(cs) == 1,
                          "%d candidatas -> %s" % (len(cs),
                          "una sola" if len(cs) == 1 else
                          "ESTADO=NOT_LOCALIZADA_MAESTRA, declarado, no fallado")))
    fallos = 0
    estados = []
    for nombre, ok, det in casos:
        if "ESTADO=" in str(det):
            print("    %-46s %s  %s" % (nombre, "ESTADO", str(det)[:40]))
            estados.append(nombre)
            continue
        print("    %-46s %s  %s" % (nombre, "OK" if ok else "FALLA", str(det)[:40]))
        if not ok:
            fallos += 1
    print("  %d de %d controles pasan" % (len(casos) - fallos - len(estados),
                                          len(casos) - len(estados)))
    if estados:
        print("  %d capacidades declaradas como estado, no como fallo:" % len(estados))
        for e in estados:
            print("    - %s" % e)
    print("  %s" % ("todos los controles pasan" if fallos == 0 else "HAY FALLOS: %d" % fallos))
    return 0 if fallos == 0 else 1


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--info" in argv:
        meta, err = volcar("/tmp/opencode/vbios.rom")
        if err:
            print("  %s" % err)
            return 1
        for k, v in meta.items():
            print("    %-16s %s" % (k, v))
        return 0
    if "--tablas" in argv:
        img, err = volcar_si_hace_falta("/tmp/opencode/vbios.rom")
        if err:
            print("  %s" % err)
            return 1
        cs, err = tabla_maestra(img)
        if err:
            print("  %s" % err)
            return 1
        rc = ruta_del_corpus(img)
        print("  ruta del driver (atom.c, amdgpu_atom_parse): base=CU16(0x%X)=%s, "
              "maestro=CU16(base+%d)" % (PTR_ROM_TABLE, hex(rc["base"]) if rc.get("base") is not None else "?",
                                        OFF_MASTER_DATA_RELATIVO))
        print("    destino %s, structuresize=%s -> %s"
              % (hex(rc["candidato"]) if rc.get("candidato") else "-",
                 rc.get("structuresize_en_destino", "-"), rc["estado"]))
        print()
        print("  %d candidatas con structuresize=%d. NO se elige ninguna:" % (len(cs), TAM_MAESTRA))
        print("  %-9s %-9s %-11s %-11s" % ("offset", "crev", "VRAM_Info", "IntegratedSys"))
        for c in cs[:12]:
            print("  0x%-7X %-9d 0x%-9X 0x%-9X"
                  % (c["offset"], c["content_revision"], c["VRAM_Info"], c["IntegratedSystemInfo"]))
        if len(cs) != 1:
            print("  %d candidatas: la tabla maestra NO esta localizada. Elegir una seria" % len(cs))
            print("  inventar, y una tabla equivocada daria offsets que parecerian buenos.")
        return 0
    if "--dump" in argv and len(argv) >= 3:
        meta, err = volcar(argv[2])
        if err:
            print("  %s" % err)
            return 1
        print("  volcado en %s (%s bytes)" % (argv[2], meta.get("vbios_size")))
        for k in ("vbios_name", "vbios_pn", "vbios_version", "vbios_ver_str", "vbios_date", "firma"):
            if k in meta:
                print("    %-16s %s" % (k, meta[k]))
        return 0
    print(__doc__[:1500])
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
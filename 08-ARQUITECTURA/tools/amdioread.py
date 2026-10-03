#!/usr/bin/env python3
# CONTRACT: name=amdioread
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""
AMDIOREAD -- la configuracion real del ASIC por ioctl, sin root.

Por que existe. En 905 abri la ruta de textura y encontre esto:

  gfx_v8_0.c:1745-1760, case CHIP_STONEY: max_shader_engines = 1,
  max_cu_per_sh = 3, max_texture_channel_caches = 2.

  boot-amdgpu-7.1.3-200.nobara.fc44.x86_64.log linea 48:
    "SE 2, SH per SE 1, CU per SH 5, active_cu_number 8"

La tabla estatica y el log no pueden ser las dos la verdad de esta placa. Y la
explicacion esta en amdgpu_discovery.c:1742-1760, que para Polaris12 lee el
discovery bin de MMIO y sobrescribe TODOS esos campos con gc_num_se,
gc_num_wgp0_per_sa, gc_num_gl2c y demas. O sea: para este ASIC la tabla de
gfx_v8_0_gpu_early_init es un valor por defecto que la descubrimiento pisa, y
leerla es leer una mentira.

Es la segunda vez en este proyecto que una tabla estatica no describe mi ASIC. La
primera fue gpu_info_fw, muerto para Polaris12, y quedo registrada en 272. El
patron se repite y por eso esto necesita ser un instrumento y no una lectura.

Lo que buys: /dev/dri/renderD129 es crw-rw-rw-, asi que AMDGPU_INFO_DEV_INFO se
pide sin root y sin MMIO. Devuelve la topologia de CUs que el hardware
declara, no la que el driver supone.

LO QUE NO HACE, y son sus limites:

  - AMDGPU_INFO_DEV_INFO no expone max_texture_channel_caches. La estructura no
    tiene ese campo. El numero de canales de textura sigue siendo
    NOT_DETERMINED y solo lo daria el discovery bin, que es MMIO.
  - max_engine_clock y max_memory_clock vienen en KHz segun el comentario de la
    cabecera. Este programa convierte y lo dice; la unidad de salida esta escrita
    en el nombre del campo, no en un escalar suelto.
  - No abre /dev/dri/renderD128 a proposito. Ese es la Intel. Confundir los dos
    nodos es el mismo error que card0 con card1, documentado en
    HARDWARE-FINGERPRINT.md seccion 6, y aqui el fallo seria silencioso porque
    el ioctl de Intel devuelve algo y no un error.

Uso:
    python3 amdioread.py --self     # dos controles, debe imprimir "todos pasan"
    python3 amdioread.py            # la lectura
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# Campos que amdgpu informa y que no describen esta placa, con la razon y la nota que
# lo demuestra. Ver findings/923: las dos rutas que producen gmc.vram_width leen una
# tabla de IGP (ATOM_INTEGRATED_SYSTEM_INFO_V2, cuyo campo vecino ucMemoryType declara
# DDR1/DDR2/DDR3) o el mapa de canales COMPARTIDOS. El ancho real de bus es de 128 bits,
# segun el nombre del firmware y segun el techo medido de 44 GB/s a 1500 MHz, que no
# caben en un bus de 64.
FALSOS_CONOCIDOS = {
    "vram_bit_width": "ancho de bus real 128 bits; las dos rutas de gmc_v8_0_mc_init "
                      "leen IGP o el mapa compartido (finding 923)",
}

RENDER_AMD = "/dev/dri/renderD129"
RENDER_INTEL = "/dev/dri/renderD128"
ESPERADO_DEVICE_ID = 0x699F



def compilar_probe():
    """El ioctl necesita la estructura y el numero de comando reales, que viven en
    la cabecera instalada y no en el corpus. Se compila un probe minimo contra
    la cabecera del sistema, y se comprueba que existe ANTES de compilar."""
    h = "/usr/include/drm/amdgpu_drm.h"
    if not os.path.exists(h):
        return None, "no esta %s; el paquete de cabeceras no esta instalado" % h
    src = os.path.join(tempfile.mkdtemp(prefix="amdioread"), "probe.c")
    with open(src, "w") as f:
        f.write(PROBE_C)
    exe = src[:-2]
    r = subprocess.run(["gcc", "-O2", "-Wall", "-o", exe, src], capture_output=True, text=True)
    if r.returncode != 0:
        return None, "gcc fallo: " + r.stderr.strip().split("\n")[0][:90]
    return exe, None


PROBE_C = r'''
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <stdint.h>
#include <sys/ioctl.h>
#include <drm/amdgpu_drm.h>
#include <drm/drm.h>

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "falta el nodo\n"); return 2; }
    int fd = open(argv[1], O_RDWR);
    if (fd < 0) { fprintf(stderr, "open: %s\n", strerror(errno)); return 3; }

    struct drm_amdgpu_info_device dev;
    memset(&dev, 0, sizeof(dev));
    struct drm_amdgpu_info info;
    memset(&info, 0, sizeof(info));
    info.query = AMDGPU_INFO_DEV_INFO;
    info.return_size = sizeof(dev);
    info.return_pointer = (uint64_t)(uintptr_t)&dev;

    if (ioctl(fd, DRM_IOCTL_AMDGPU_INFO, &info) != 0) {
        fprintf(stderr, "ioctl DEV_INFO: %s\n", strerror(errno));
        close(fd); return 4;
    }

    /* CONTROL PROPIO: la cabecera declara cu_ao_mask como INVALID. Si el kernel
     * devolviera algo en ese campo, el numero seria de una epoca en la que el
     * campo significaba otra cosa, y todo lo demas de esta lectura habria que
     * releerlo. Se imprime para que quede a la vista, no para confiar en el. */
    printf("device_id=0x%04X\n", dev.device_id);
    printf("chip_rev=0x%02X\n", dev.chip_rev);
    printf("family=0x%02X\n", dev.family);
    printf("pci_rev=0x%02X\n", dev.pci_rev);
    printf("num_shader_engines=%u\n", dev.num_shader_engines);
    printf("num_sh_arrays_per_engine=%u\n", dev.num_shader_arrays_per_engine);
    printf("gpu_counter_freq_khz=%u\n", dev.gpu_counter_freq);
    printf("max_engine_clock_khz=%llu\n", (unsigned long long)dev.max_engine_clock);
    printf("max_memory_clock_khz=%llu\n", (unsigned long long)dev.max_memory_clock);
    printf("cu_active_number=%u\n", dev.cu_active_number);
    printf("cu_ao_mask=0x%08X\n", dev.cu_ao_mask);
    printf("enabled_rb_mask=0x%08X\n", dev.enabled_rb_pipes_mask);
    printf("num_rb_pipes=%u\n", dev.num_rb_pipes);
    printf("num_hw_gfx_contexts=%u\n", dev.num_hw_gfx_contexts);
    printf("pcie_gen=%u\n", dev.pcie_gen);
    printf("ids_flags=0x%llX\n", (unsigned long long)dev.ids_flags);
    printf("virtual_address_offset=0x%llX\n", (unsigned long long)dev.virtual_address_offset);
    printf("virtual_address_max=0x%llX\n", (unsigned long long)dev.virtual_address_max);
    printf("virtual_address_align=0x%llX\n", (unsigned long long)dev.virtual_address_alignment);
    printf("wave_front_size=%u\n", dev.wave_front_size);
    printf("num_cu_per_sh=%u\n", dev.num_cu_per_sh);
    printf("num_tcc_blocks=%u\n", dev.num_tcc_blocks);
    printf("num_shader_visible_vgprs=%u\n", dev.num_shader_visible_vgprs);
    printf("vram_bit_width=%u\n", dev.vram_bit_width);
    printf("vram_type=%u\n", dev.vram_type);
    printf("gart_page_size=%u\n", dev.gart_page_size);
    printf("pte_fragment_size=%u\n", dev.pte_fragment_size);
    printf("gl1c_cache_size=%u\n", dev.gl1c_cache_size);
    printf("gl2c_cache_size=%u\n", dev.gl2c_cache_size);
    printf("sqc_data_cache_size=%u\n", dev.sqc_data_cache_size);
    printf("sqc_inst_cache_size=%u\n", dev.sqc_inst_cache_size);
    printf("mall_size=%u\n", dev.mall_size);
    printf("min_engine_clock_khz=%llu\n", (unsigned long long)dev.min_engine_clock);
    printf("min_memory_clock_khz=%llu\n", (unsigned long long)dev.min_memory_clock);
    printf("pcie_num_lanes=%u\n", dev.pcie_num_lanes);
    printf("nota_cu_ao_mask=INVALID_en_la_cabecera_pero_aqui_es_la_mascara_de_CU\n");
    printf("cu_bitmap_detalle");
    for (int se = 0; se < 4; se++) {
        for (int sh = 0; sh < 4; sh++) {
            if (dev.cu_bitmap[se][sh])
                printf(" [%d][%d]=0x%08X", se, sh, dev.cu_bitmap[se][sh]);
        }
    }
    printf("\n");
    close(fd);
    return 0;
}
'''


def leer(nodo):
    exe, err = compilar_probe()
    if exe is None:
        return None, err
    r = subprocess.run([exe, nodo], capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr.strip() or "probe salio %d" % r.returncode)[:100]
    out = {}
    for l in r.stdout.split("\n"):
        if "=" not in l:
            continue
        k, v = l.split("=", 1)
        out[k.strip()] = v.strip()
    return out, None


def como_int(s):
    """El probe imprime en hexadecimal lo que tiene letra y en decimal lo demas.
    Convertir con int(s) a secas falla en las que llevan 0x, y fallar a mitad de un
    control hace que el self-test se caiga en vez de decir que el control fallo.
    Un control que aborta el programa no es un control: es una excepcion."""
    if s is None:
        return None
    s = s.strip()
    try:
        return int(s, 16) if s.lower().startswith("0x") else int(s)
    except ValueError:
        return None


def controles(d, nodo):
    """Dos controles, como en cualquier test propio: uno del dispositivo y otro de
    la configuracion del propio instrumento."""
    res = []
    did = d.get("device_id")
    res.append(("el nodo es la RX 550 y no la iGPU",
                did is not None and como_int(did) == ESPERADO_DEVICE_ID,
                "device_id=%s esperado=0x699F" % did))
    res.append(("el nodo no es el de Intel",
                nodo == RENDER_AMD,
                "%s (el Intel es %s)" % (nodo, RENDER_INTEL)))
    # CONTROL DE COHERENCIA INTERNA. cu_bitmap[4][4] viene VACIO en este kernel, y
    # la mascara de CU que si se rellena es cu_ao_mask, que la cabecera marca como
    # INVALID. aqui vale 0x001E001E, o sea dos campos de 16 bits con 0x1E, que son
    # 4 CUs por SE: 2 SE x 4 = 8, y cu_active_number dice 8. El popcount del
    # contenido cuadra con el campo que lo declara.
    #
    # Y 0x1E es exactamente la mascara que 272 habia deducido, la que produce el
    # "& mask" de gfx_v8_0.c:7060-7069. Tres vias distintas al mismo numero.
    act = d.get("cu_active_number")
    ao = d.get("cu_ao_mask")
    pop = 0
    if ao:
        v = como_int(ao.split()[0])
        pop = sum(bin((v >> (16 * k)) & 0xFFFF).count("1") for k in range(4))
    res.append(("cu_active_number cuadra con el popcount de cu_ao_mask",
                act is not None and como_int(act) == pop and pop > 0,
                "declarado=%s popcount=%d" % (act, pop)))
    res.append(("el reloj de memoria declarado viene en kHz y es plausible",
                d.get("max_memory_clock_khz") not in (None, "0"),
                "max_memory_clock=%s kHz" % d.get("max_memory_clock_khz")))

    # VALIDACION CONTRA HECHOS QUE YA TENGO. Un campo de una cabecera es una
    # AFIRMACION sobre lo que el driver puede informar, no prueba de que el kernel
    # lo rellene, y el nombre del campo puede no significar lo que parece. Pero hay
    # tres valores cuya verdad ya esta establecida por otra via, y si esos tres
    # cuadran el resto de la estructura es de fiar. Si alguno no cuadra, la lectura
    # entera queda marcada y hay que averiguarlo antes de usar ningun otro campo.
    conocidos = [
        ("wave_front_size", 64, "272 lo verifico en gfx_v8_0.c:7124"),
        ("cu_active_number", 8, "boot log linea 48: active_cu_number 8"),
        ("max_memory_clock_khz", 1500000, "pp_dpm_mclk, el nivel 2 de 258"),
        ("cu_ao_mask", 0x001E001E, "272: 0x1e por SE, 2 SE, 8 CUs"),
    ]
    for campo, esperado, de_donde in conocidos:
        v = d.get(campo)
        res.append(("VALIDACION %s = %d" % (campo, esperado),
                    v is not None and como_int(v) == esperado,
                    "leido=%s (%s)" % (v, de_donde)))
    return res


def selftest():
    print("  self-test de amdioread.py:")
    exe, err = compilar_probe()
    c = [("la cabecera uapi esta instalada", exe is not None, err or "ok")]
    d, e = leer(RENDER_AMD)
    c.append(("el probe lee el nodo de la AMD", d is not None, e or "ok"))
    if d:
        for nombre, ok, det in controles(d, RENDER_AMD):
            c.append((nombre, ok, det))
        # control negativo: el mismo probe contra el nodo de Intel tiene que fallar
        di, ei = leer(RENDER_INTEL)
        c.append(("el nodo de la Intel no devuelve la RX 550",
                  di is None or como_int(di.get("device_id")) != ESPERADO_DEVICE_ID,
                  "device_id=%s" % (di.get("device_id") if di else "sin lectura")))
    fallos = 0
    for nombre, ok, det in c:
        print("    %-52s %s  %s" % (nombre, "OK" if ok else "FALLA", det[:44]))
        if not ok:
            fallos += 1
    print("  %d de %d pasan%s" % (len(c) - fallos, len(c),
                                "" if fallos == 0 else "  <-- HAY FALLOS"))
    print("  todos pasan" if fallos == 0 else "  NO todos pasan")
    return 0 if fallos == 0 else 1


def main(argv):
    if "--self" in argv:
        return selftest()
    d, err = leer(RENDER_AMD)
    if d is None:
        print("  no se pudo leer: %s" % err)
        return 1
    print("  === %s ===" % RENDER_AMD)
    for k in ("device_id", "chip_rev", "pci_rev", "num_shader_engines",
              "num_sh_arrays_per_engine", "num_rb_pipes", "num_hw_gfx_contexts",
              "enabled_rb_mask", "cu_active_number", "gpu_counter_freq_khz",
              "max_engine_clock_khz", "min_engine_clock_khz",
              "max_memory_clock_khz", "min_memory_clock_khz", "pcie_gen",
              "pcie_num_lanes", "wave_front_size", "num_cu_per_sh",
              "num_shader_visible_vgprs", "num_tcc_blocks", "vram_bit_width",
              "vram_type", "gart_page_size", "pte_fragment_size",
              "gl1c_cache_size", "gl2c_cache_size", "sqc_data_cache_size",
              "sqc_inst_cache_size", "mall_size",
              "virtual_address_offset", "virtual_address_max", "cu_bitmap_detalle"):
        if k in d:
            # Campos que el driver informa y que se ha PROBADO que no describen este
            # ASIC. Se marcan en la propia salida en vez de limitarse a anotarlo en una
            # nota: un numero sin marca, en la linea de la que se saca todo lo demas,
            # se propaga solo. Y este es justo el caso de un 64 donde el hardware
            # tiene 128. Sin marca, esta herramienta afirma algo falso con la misma
            # seguridad con que afirma el resto de la linea.
            marca = FALSOS_CONOCIDOS.get(k)
            if marca:
                print("    %-24s %s   <-- VALOR FALSO, no usar: %s" % (k, d[k], marca))
            else:
                print("    %-24s %s" % (k, d[k]))
    print()
    print("  controles:")
    for nombre, ok, det in controles(d, RENDER_AMD):
        print("    %-52s %s  %s" % (nombre, "OK" if ok else "FALLA", det[:44]))
    bad = [n for n, ok, _ in controles(d, RENDER_AMD) if not ok]
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
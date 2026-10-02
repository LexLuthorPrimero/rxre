#!/usr/bin/env python3
# CONTRACT: name=fw_ipver
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""fw_ipver -- el IP version que declara cada firmware, contrastado con el driver.

POR QUE EXISTE. La frontera "GFX_HWIP" la dio 050 por sin fuente en el corpus, y
es cierto: el registro GFX_HWIP no aparece ni en el driver ni en los headers
generados. Pero el IP version de esta placa SI esta disponible, en otro sitio:
la cabecera del propio firmware, que el driver tiene en /lib/firmware/amdgpu/.

El campo se llama `ip_version` en `struct common_firmware_header`, y el layout
NO se adivina: sale de los nombres y tipos que usa
`amdgpu_ucode_print_common_hdr()` (amdgpu_ucode.c:37-49). Los offsets FIJOS son
4 bytes, 4 bytes y 4 u16, NO 5: con 5 el parseo desplaza todos los campos y da
numeros que no cuadran.

    size u32 @0x00 | header_size u32 @0x04
    hdr_ver_maj u16 @0x08 | hdr_ver_min u16 @0x0a
    ip_ver_maj u16 @0x0c | ip_ver_min u16 @0x0e
    ucode_version u32 @0x10 | ucode_size u32 @0x14
    array_offset u32 @0x18 | crc32 u32 @0x1c

Y lo que descubre: `ip_version` es POR BLOQUE DE MICROCODIGO, no el del GFX.
En polaris12 conviven 8.0 (pfp/me/ce/rlc), 8.1 (mc), 3.1 (sdma), 7.2 (smc),
6.3 (uvd) y 3.4 (vce). Los dos valores que NO son 8.0 son los que discriminan:
mc dice 8.1 y el driver declara gmc_v8_1_ip_block con minor=1; sdma dice 3.1 y
el driver declara sdma_v3_1_ip_block con major=3 minor=1.

Uso:
  fw_ipver.py --placa polaris12
  fw_ipver.py --placa polaris12 --cruce      cruza con los ip_block del driver
  fw_ipver.py --todas                        una linea por ASIC
  fw_ipver.py --self-test

Codigos de salida:
  0  todo bien
  2  ASIC no encontrado en /lib/firmware/amdgpu
  3  el directorio de firmware no existe
"""

import glob
import lzma
import os
import re
import struct
import subprocess
import sys

FW = "/lib/firmware/amdgpu"
AMD = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))),
    "RESEARCH", "working", "linux-7.1.3", "drivers", "gpu", "drm", "amd",
    "amdgpu")

HDR = "<IIHHHHIII"          # 4 u16, no 5. Ver docstring.
FIELDS = ["size", "hdr_size", "hdr_maj", "hdr_min",
          "ip_maj", "ip_min", "ucode_version",
          "ucode_size", "array_offset", "crc32"]


def parse(raw):
    """Cabecera del firmware. Devuelve None si no parece una cabecera."""
    if len(raw) < 32:
        return None
    v = struct.unpack_from(HDR, raw, 0)
    h = dict(zip(FIELDS, v))
    h["cobra"] = (h["array_offset"] + h["ucode_size"] == h["size"]
                  == len(raw))
    return h


def read(path):
    if path.endswith(".xz"):
        try:
            with lzma.open(path) as fh:
                return fh.read()
        except (OSError, lzma.LZMAError):
            return None
    try:
        with open(path, "rb") as fh:
            return fh.read()
    except OSError:
        return None


def asics():
    """{asic: [rutas]} a partir de los nombres de fichero del firmware."""
    out = {}
    for p in sorted(glob.glob(os.path.join(FW, "*.bin*"))):
        name = os.path.basename(p)
        a = name.split("_")[0]
        out.setdefault(a, []).append(p)
    return out


def bloques_del_driver():
    """{major.minor -> [nombres de ip_block]} leido del corpus."""
    out = {}
    pat = re.compile(r"const struct amdgpu_ip_block_version (\w+)\s*=\s*\{"
                     r"(.*?)\n\};", re.S)
    for f in sorted(glob.glob(os.path.join(AMD, "*.c"))):
        try:
            txt = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for m in pat.finditer(txt):
            nombre, cuerpo = m.group(1), m.group(2)
            maj = re.search(r"\.major\s*=\s*(\w+|\d+)", cuerpo)
            mino = re.search(r"\.minor\s*=\s*(\w+|\d+)", cuerpo)
            if not (maj and mino):
                continue
            try:
                v = "%d.%d" % (int(maj.group(1)), int(mino.group(1)))
            except ValueError:
                continue
            out.setdefault(v, []).append("%s (%s)" % (nombre, os.path.basename(f)))
    return out


def ver_por_bloque(asic):
    """[(fichero, ip_version, ucode_version, cuadra, nota)] para un ASIC.

    `cuadra` es el validador estructural: array_offset + ucode_size == size ==
    longitud del fichero. Los ficheros que NO cuadran NO son microcodigos con
    `common_firmware_header` -- son, en la practica, los *_ip_discovery.bin, que
    tienen otro formato. Publicar su ip_version seria presentar basura como
    dato, y sin embargo --todas los imprimia como si fueran medidas.
    """
    filas = []
    for p in sorted(glob.glob(os.path.join(FW, asic + "_*.bin*"))):
        raw = read(p)
        nombre = os.path.basename(p)
        if raw is None:
            filas.append((nombre, None, None, False, "ilegible"))
            continue
        h = parse(raw)
        if h is None:
            filas.append((nombre, None, None, False, "corto"))
            continue
        if not h["cobra"]:
            filas.append((nombre, None, None, False,
                          "otro formato (hdr=%d)" % h["hdr_size"]))
            continue
        filas.append((nombre, "%d.%d" % (h["ip_maj"], h["ip_min"]),
                      h["ucode_version"], True, ""))
    return filas


def print_placa(asic, cruce=False):
    filas = ver_por_bloque(asic)
    if not filas:
        print("no hay firmware para %s en %s" % (asic, FW))
        return 2
    print("FIRMWARE DE %s  (%d ficheros)\n" % (asic, len(filas)))
    print("%-32s %8s %9s  %s" % ("fichero", "ip_ver", "ucode_v", "cuadra"))
    print("-" * 66)
    for nombre, ip, uv, ok, nota in filas:
        print("%-32s %8s %9s  %s"
              % (nombre, ip if ip else "?", uv if uv is not None else "?",
                 "si" if ok else ("NO " + nota if nota else "no")))
    if cruce:
        bloq = bloques_del_driver()
        usados = sorted(set(ip for _n, ip, _u, _o, _x in filas if ip))
        print("\nCONTRASTE con los ip_block que declara el driver:\n")
        for v in usados:
            nombres = bloq.get(v, [])
            print("  firmware dice %-5s -> %s"
                  % (v, ", ".join(nombres[:4]) if nombres
                     else "NINGUN ip_block del driver con esa version"))
    return 0


def print_todas():
    print("%-16s %-34s %s" % ("asic", "ip_ver distintos", "bloques"))
    print("-" * 78)
    for asic in sorted(asics()):
        ips = {}
        for nombre, ip, uv, ok, _n in ver_por_bloque(asic):
            if ip:
                ips.setdefault(ip, []).append(nombre.split("_")[1]
                                              .replace(".bin", ""))
        if not ips:
            continue
        det = ", ".join("%s(%d)" % (v, len(u)) for v, u in
                        sorted(ips.items(), key=lambda kv: -len(kv[1])))
        print("%-16s %-34s %s" % (asic, det[:34],
                                  " ".join(sorted(set(
                                      b for u in ips.values() for b in u)))[:40]))
    return 0


def self_test():
    fails = []

    def eq(label, got, want):
        if got != want:
            fails.append("%s: %r != %r" % (label, got, want))

    if not os.path.isdir(FW):
        print("self-test FALLA: no existe %s" % FW)
        print("   Sin firmware no se puede validar. No se da por buena.")
        return 1

    # 1. VECTOR CONOCIDO, leído a mano del fichero de esta placa.
    p = os.path.join(FW, "polaris12_pfp.bin.xz")
    if not os.path.exists(p):
        fails.append("falta polaris12_pfp.bin.xz")
    else:
        h = parse(read(p))
        eq("size", h["size"], 17044)
        eq("header_size", h["hdr_size"], 44)
        eq("ip_maj", h["ip_maj"], 8)
        eq("ip_min", h["ip_min"], 0)
        eq("ucode_size", h["ucode_size"], 16788)
        eq("array_offset", h["array_offset"], 256)
        if not h["cobra"]:
            fails.append("la cabecera no cuadra: %d+%d != %d"
                         % (h["array_offset"], h["ucode_size"], h["size"]))

    # 2. CONTROL NEGATIVO del formato: con 5 u16 en vez de 4, el parseo NO
    #    cuadra. Si "cobra" fuera cierto con el formato erroneo, el control
        #    no estaria midiendo nada.
    raw = read(p)
    if raw:
        v5 = struct.unpack_from("<IIHHHHHIII", raw, 0)
        if v5[8] + v5[7] == v5[0] == len(raw):
            fails.append("el formato de 5 u16 tambien cuadra: el control "
                         "negativo no discrimina")

    # 3. Los tres valores que hacen la correlacion. mc y sdma son los que
    #    NO son 8.0: si cambian, la correspondencia queda refutada.
    for nombre, ip in [("polaris12_mc.bin.xz", "8.1"),
                       ("polaris12_sdma.bin.xz", "3.1"),
                       ("polaris12_pfp.bin.xz", "8.0")]:
        fp = os.path.join(FW, nombre)
        if not os.path.exists(fp):
            fails.append("falta %s" % nombre)
            continue
        hh = parse(read(fp))
        got = "%d.%d" % (hh["ip_maj"], hh["ip_min"])
        if got != ip:
            fails.append("%s dice %s, esperaba %s" % (nombre, got, ip))

    # 4. ip_version es POR BLOQUE: mismo ASIC, valores distintos. Si todos
    #    los ucodes de polaris12 dijeran lo mismo, la tabla no significaria
    #    nada y este control tiene que fallar.
    filas = ver_por_bloque("polaris12")
    ips = set(ip for _n, ip, _u, _o, _x in filas if ip)
    if len(ips) < 2:
        fails.append("polaris12 da un solo ip_version (%s): se perdio la "
                     "diferencia por bloque" % ips)

    # 5. CONTROL NEGATIVO: un ASIC inventado no debe devolver filas.
    if ver_por_bloque("este_asic_no_existe_xyz"):
        fails.append("un ASIC inexistente devolvio filas")

    # 6. CONTROL NEGATIVO: un fichero que no es firmware no debe parsearse
    #    como si lo fuera. 32 bytes de ceros tienen size=0 y no cuadran.
    h = parse(bytes(64))
    if h is not None and h["cobra"]:
        fails.append("64 bytes de ceros se aceptaron como cabecera valida")

    if fails:
        print("self-test FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        return 1
    print("self-test OK (10 vectores, 4 controles)")
    return 0


def main(argv):
    if "--self-test" in argv:
        return self_test()
    if not os.path.isdir(FW):
        print("no existe %s" % FW)
        return 3
    if "--todas" in argv:
        return print_todas()
    if "--placa" in argv:
        asic = argv[argv.index("--placa") + 1]
        return print_placa(asic, "--cruce" in argv)
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

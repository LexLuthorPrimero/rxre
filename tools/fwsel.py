#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fwsel.py — resolver qué firmware está EJECUTANDO realmente cada bloque IP.

POR QUÉ EXISTE
-------------
En gfx8 hay varios blobs candidatos por bloque IP, y la selección es por
NOMBRE con preferencia, no por contenido: `gfx_v8_0.c:1105-1113` pide primero
`polaris12_mec_2.bin` (AMDGPU_UCODE_OPTIONAL) y sólo recurre a `polaris12_mec.bin`
ante -ENODEV. Analizar el fichero equivocado no da error: da un análisis
correcto del binario que no se está ejecutando. Eso es una clase de error
silencioso, y por tanto una fuente de error humano que conviene automatizar.

CÓDIGO FUENTE DE LA ESTRUCTURA
------------------------------
El layout NO está supuesto aquí. Viene de la definición del driver:

    drivers/gpu/drm/amd/amdgpu/amdgpu_ucode.h:28-40
        struct common_firmware_header {
                uint32_t size_bytes;
                uint32_t header_size_bytes;
                uint16_t header_version_major;
                uint16_t header_version_minor;
                uint16_t ip_version_major;
                uint16_t ip_version_minor;
                uint32_t ucode_version;
                uint32_t ucode_size_bytes;
                uint32_t ucode_array_offset_bytes;
                uint32_t crc32;  /* crc32 checksum of the payload */
        };
        amdgpu_ucode.h:44-48  struct mc_firmware_header_v1_0  añade
                              io_debug_size_bytes e io_debug_array_offset_bytes
        amdgpu_ucode.h:51-54  struct smc_firmware_header_v1_0 añade ucode_start_addr
                              (de ahí que header_size == 36 => v1_0, sin soft pptable)

INDEPENDENCIA DE LAS FUENTES
----------------------------
Se comparan DOS fuentes que no se derivan una de otra:
  A) las cabeceras de los ficheros en disco
  B) /sys/kernel/debug/dri/<n>/amdgpu_firmware_info  (lo que el driver cargó)
Coincidencia exacta = CORROBORADO. Sin coincidencia = NOT_DETERMINED, no
"fallo": el bloque puede no existir en disco o no estar instrumentado.

ALCANCE
-------
Solo LECTURA. No toca la GPU, no escribe registros, no carga módulos.
El atributo `amdgpu_firmware_info` es de debugfs y requiereprivilegios; si no
es legible, la herramienta degrada a modo `--disk-only` y lo dice.

Uso:
    fwsel.py [--chip polaris12] [--debugfs /sys/kernel/debug/dri/1]
             [--firmware-dir /lib/firmware/amdgpu] [--disk-only] [--json]
"""

import argparse
import hashlib
import json
import lzma
import os
import re
import struct
import sys

# Bloques que publica amdgpu_firmware_info, con el prefijo de fichero que el
# driver usa. La lista viene de lo que el atributo imprime, no de una suposición.
BLOCKS = [
    ("MC",   "mc"),   ("UVD",  "uvd"),  ("VCE",  "vce"),  ("ME",   "me"),
    ("PFP",  "pfp"),  ("CE",   "ce"),   ("RLC",  "rlc"),
    ("MEC",  "mec"),  ("MEC2", "mec2"), ("IMU",  "imu"),  ("SOS",  "sos"),
    ("ASD",  "asd"),
]

# sufijos que el driver puede preferir para un mismo bloque. gfx_v8_0.c pide
# "%s_2.bin" antes que "%s.bin" para POLARIS10..POLARIS12; el orden importa.
SUFFIX_PREFERENCE = ["", "_2"]

HDR = "<IIHHHHIIII"         # size, hdrsize, hmj, hmn, ipj, ipn, ucode_ver, ucode_sz, ucode_off, crc32
HDR_FMT_SIZE = struct.calcsize(HDR)
assert HDR_FMT_SIZE == 32, (
    "common_firmware_header deberia medir 32 bytes (amdgpu_ucode.h:28-40); "
    "si esto falla, el layout cambio en el driver: revisa la fuente antes de tocar la tool")

# Las extensiones del header se eligen por VERSION, no por desplazamiento.
# Motivo, medido: rlc_firmware_header_v1_0 mide 52 bytes (amdgpu_ucode.h:216-223) pero
# el blob RLC de esta tarjeta declara header_size_bytes = 104 y header_version 2.0, asi
# que aplicarle los offsets del struct de gfx aOffset 44/48 produce valores SIN SENTIDO
# que ademas salen "validos". Por eso: version desconocida => NOT_DETERMINED, no suponga.
EXT_LAYOUTS = {
    ("GFX", "1.0"): {  # gfx_firmware_header_v1_0, amdgpu_ucode.h:181-186  (= 32+12 = 44)
        "ucode_feature_version": 40, "jt_offset": 44, "jt_size": 48,
    },
    # ("RLC", "2.0") -> NO IMPLEMENTADO a proposito: rlc_firmware_header_v2_0 no se ha
    # leido en la fuente. Se reporta NOT_DETERMINED en vez de adivinar el layout.
}

GFX_BLOCKS = {"ME", "PFP", "CE", "MEC", "MEC2"}


def load_blob(path):
    """Lee un blob, descomprimiendo .xz. Devuelve bytes o None."""
    if not os.path.exists(path):
        return None
    raw = open(path, "rb").read()
    if path.endswith(".xz"):
        try:
            raw = lzma.decompress(raw)
        except lzma.LZMAError:
            return None
    return raw


def parse_header(data, block=None):
    """Parsea common_firmware_header. Devuelve dict o None si no cabe.

    Las extensiones (campos mas alla del common) se aplican SOLO si el par
    (familia, header_version) tiene layout conocido en EXT_LAYOUTS. En cualquier
    otro caso se marca 'ext' como NOT_DETERMINED en vez de leer offsets a ciegas.
    """
    if data is None or len(data) < HDR_FMT_SIZE:
        return None
    (size, hdrsize, hmj, hmn, ipj, ipn,
     ucode_version, ucode_sz, ucode_off, crc32) = struct.unpack_from(HDR, data, 0)

    ver = "%d.%d" % (hmj, hmn)
    h = {
        "size_bytes": size,
        "header_size_bytes": hdrsize,
        "header_version": ver,
        "ip_version": "%d.%d" % (ipj, ipn),
        "ucode_version": ucode_version,
        "ucode_size_bytes": ucode_sz,
        "ucode_array_offset_bytes": ucode_off,
        "crc32": crc32,
        "sha256": hashlib.sha256(data).hexdigest(),
        "payload_bytes": len(data),
    }

    fam = "GFX" if block in GFX_BLOCKS else (block or "?")
    layout = EXT_LAYOUTS.get((fam, ver))
    if layout is None:
        h["ext"] = "NOT_DETERMINED"
        h["ext_reason"] = ("sin layout conocido para (%s, header_version %s); "
                           "no se leen offsets a ciegas" % (fam, ver))
    else:
        h["ext"] = "OK"
        h["ext_layout"] = "%s header_version %s" % (fam, ver)
        for name, off in sorted(layout.items(), key=lambda kv: kv[1]):
            if hdrsize >= off + 4 and len(data) >= off + 4:
                h[name] = struct.unpack_from("<I", data, off)[0]
                h.setdefault("_ext_offsets", {})[name] = off

    # Auto-comprobaciones. No son validacion: sonistency checks que delatan
    # que el parseo no se corresponde con el fichero.
    h["self_check_size"] = (size == len(data))
    h["self_check_payload_end"] = (ucode_off + ucode_sz == size)
    return h


def read_firmware_info(debugfs):
    """Lee amdgpu_firmware_info. Devuelve {BLOQUE: ucode_version} o None."""
    p = os.path.join(debugfs, "amdgpu_firmware_info")
    if not os.path.exists(p):
        return None
    try:
        txt = open(p, "r", errors="replace").read()
    except OSError:
        return None
    out = {}
    for line in txt.splitlines():
        m = re.match(r"\s*(\w+)\s+feature version:\s*(\S+),\s*"
                     r"firmware version:\s*(0x[0-9a-fA-F]+)", line)
        if m:
            out[m.group(1)] = (int(m.group(3), 16),
                               m.group(2))
    return out or None


def read_kfd_properties():
    """Lee las propiedades que publica KFD, si el nodo existe."""
    base = "/sys/class/kfd/kfd/topology/nodes"
    res = {}
    if not os.path.isdir(base):
        return res
    for node in sorted(os.listdir(base)):
        p = os.path.join(base, node, "properties")
        if not os.path.exists(p):
            continue
        try:
            for line in open(p, errors="replace"):
                kv = line.split(None, 1)
                if len(kv) == 2:
                    res.setdefault(node, {})[kv[0]] = kv[1].strip()
        except OSError:
            pass
    return res


def main():
    ap = argparse.ArgumentParser(
        description="Resuelve que blob de firmware ejecuta cada bloque IP.")
    ap.add_argument("--chip", default="polaris12",
                    help="prefijo de los blobs (default: polaris12)")
    ap.add_argument("--firmware-dir", default="/lib/firmware/amdgpu")
    ap.add_argument("--debugfs", default="/sys/kernel/debug/dri/1")
    ap.add_argument("--disk-only", action="store_true",
                    help="no leer debugfs; solo inventariar los blobs")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    # ---- fuente A: disco -------------------------------------------------
    disk = {}
    for block, stem in BLOCKS:
        cands = []
        for suf in SUFFIX_PREFERENCE:
            name = "%s_%s%s.bin" % (a.chip, stem, suf)
            data = load_blob(os.path.join(a.firmware_dir, name))
            if data is None:
                data = load_blob(os.path.join(a.firmware_dir, name + ".xz"))
                name += ".xz"
            if data is None:
                continue
            h = parse_header(data, block)
            if h:
                h["file"] = name
                # Puerta de validez: un blob cuyo size_bytes declarado no coincide
                # con el tamano real esta truncado o corrupto. No puede ser el que
                # ejecuta, asi que se marca y no se selecciona. (No se afirma que el
                # driver lo compruebe: se afirma que este analisis no lo usa.)
                h["valid"] = h["self_check_size"] and h["self_check_payload_end"]
                cands.append(h)
        disk[block] = cands

    # ---- fuente B: el driver --------------------------------------------
    live = None
    if not a.disk_only:
        live = read_firmware_info(a.debugfs)
    kfd = read_kfd_properties()

    # ---- resolucion ------------------------------------------------------
    rows = []
    for block, cands in disk.items():
        lv = live.get(block) if live else None
        chosen = None
        if lv is not None:
            for h in cands:                      # respeta el orden de preferencia
                if h["ucode_version"] == lv[0] and h.get("valid"):
                    chosen = h
                    break
        invalid = [c["file"] for c in cands if not c.get("valid")]
        rows.append({
            "block": block,
            "candidates": len(cands),
            "candidate_files": [c["file"] for c in cands],
            "candidate_versions": ["0x%08x" % c["ucode_version"] for c in cands],
            "invalid_candidates": invalid,
            "live_ucode_version": ("0x%08x" % lv[0]) if lv else None,
            "live_feature_version": lv[1] if lv else None,
            "executing_file": chosen["file"] if chosen else None,
            "executing_sha256": chosen["sha256"] if chosen else None,
            "executing_ip_version": chosen["ip_version"] if chosen else None,
            "state": "CORROBORADO" if chosen else
                     ("NO_COINCIDE_INVALIDO" if (lv and invalid) and not chosen
                      and any(c["ucode_version"] == lv[0] for c in cands)
                      else ("NOT_DETERMINED" if live else "DISK_ONLY")),
        })

    # El SMC no lo publica amdgpu_firmware_info: no hay entrada para el, porque
    # su microcodigo vive en SRAM y lo carga smu_init_smc, no la carga generica.
    # Por eso queda fuera de la resolucion y se informa aparte mas abajo.

    out = {
        "chip": a.chip,
        "firmware_dir": a.firmware_dir,
        "live_source": None if a.disk_only else a.debugfs + "/amdgpu_firmware_info",
        "live_available": live is not None,
        "blocks": rows,
        "kfd": kfd,
    }

    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print("=" * 78)
    print("fwsel — que firmware ejecuta cada bloque IP   (chip=%s)" % a.chip)
    print("=" * 78)
    print("fuente A (disco)      : %s/%s_*.bin[.xz]" % (a.firmware_dir, a.chip))
    print("fuente B (silicio)    : %s" %
          ("NO LEIDA (--disk-only)" if live is None
           else a.debugfs + "/amdgpu_firmware_info"))
    print("estructura            : amdgpu/amdgpu_ucode.h:28-40 (common_firmware_header)")
    print()

    hdr = "%-6s %-8s %-12s %-12s %-24s %s" % (
        "BLOQUE", "CAND.", "EN DISCO", "VIVO", "EJECUTA", "ESTADO")
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        if not r["candidate_files"]:
            print("%-6s %-8s %-12s %-12s %-24s %s" % (
                r["block"], 0, "-", r["live_ucode_version"] or "-",
                "(sin blob)", r["state"]))
            continue
        print("%-6s %-8d %-12s %-12s %-24s %s" % (
            r["block"], r["candidates"],
            ",".join(r["candidate_versions"]),
            r["live_ucode_version"] or "-",
            r["executing_file"] or "NINGUNO COINCIDE",
            r["state"]))
    print()

    if kfd:
        for node, props in kfd.items():
            fw = props.get("fw_version")
            sd = props.get("sdma_fw_version")
            if fw or sd:
                print("KFD nodo %s:  fw_version=%s  sdma_fw_version=%s" % (node, fw, sd))
        print()

    # La cabecera de los bloques gfx DECLARA donde esta su tabla de saltos.
    # No hay que buscarla adivinando: esta en el propio fichero.
    # gfx_firmware_header_v1_0 (amdgpu_ucode.h:181-186): jt_offset@44, jt_size@48.
    jt = []
    for block, cands in disk.items():
        for c in cands:
            if c.get("ext") == "OK" and c.get("valid") and c.get("jt_size"):
                jt.append((block, c))
    if jt:
        print("TABLA DE SALTOS declarada en la cabecera (gfx_firmware_header_v1_0:181-186)")
        print("-" * 78)
        for block, c in sorted(jt):
            print("  %-5s %-26s jt_offset=%-8d jt_size=%-8d feature_version=%s"
                  % (block, c["file"], c["jt_offset"], c["jt_size"],
                     c.get("ucode_feature_version", "?")))
        print("  NOTA: son candidatos en disco. Para la que este EJECUTANDO, mira la")
        print("        columna EJECUTA de la tabla de arriba.")
        print()

    unresolved = [r["block"] for r in rows
                  if r["live_ucode_version"] and r["state"] != "CORROBORADO"]
    if unresolved:
        print("SIN RESOLVER (vivo presente, ningun blob en disco coincide): %s"
              % ", ".join(unresolved))
    return 0


if __name__ == "__main__":
    sys.exit(main())
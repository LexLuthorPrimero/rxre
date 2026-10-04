#!/usr/bin/env python3
"""Extrae PPTable_t y sus dependencias del smu11_driver_if.h del corpus.

SCRIPT-FIRST: el mapa de offsets sale de COMPILAR el header real, no de
parsearlo a mano. Un mapa hecho a ojo es una suposicion; uno que sale de
`offsetof` es una medicion del compilador sobre el tipo que el driver usa.
"""
import glob, os, re, sys

INC = sys.argv[1] if len(sys.argv) > 1 else (
    "RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/powerplay/inc")
SAL = sys.argv[2] if len(sys.argv) > 2 else "ppt_tipo.h"
s = open(os.path.join(INC, "smu11_driver_if.h"), errors="replace").read()

need = set(re.findall(r"\bNUM_[A-Z0-9_]+_LEVELS\b", s)) | \
       set(re.findall(r"\b[A-Z][A-Z0-9_]*_COUNT\b", s))
defines, faltan = {}, []
fuentes = {f: open(f, errors="replace").read() for f in glob.glob(INC + "/*.h")}
for c in sorted(need):
    for t in fuentes.values():
        m = re.search(r"#define\s+%s\s+([^\n/]+)" % c, t)
        if m:
            defines[c] = m.group(1).strip(); break
    else:
        faltan.append(c)

ENUM = {"I2C_CONTROLLER_NAME_COUNT": r"typedef enum \{\s*I2C_CONTROLLER_NAME_VR_GFX.*?\}\s*I2cControllerName_e;",
        "PPCLK_COUNT":               r"typedef enum \{\s*PPCLK_GFXCLK.*?\}\s*PPCLK_e;",
        "AVFS_VOLTAGE_COUNT":        r"typedef enum \{\s*AVFS_VOLTAGE_GFX.*?AVFS_VOLTAGE_COUNT,?\s*\}\s*AVFS_VOLTAGE_TYPE_e;"}
piezas = ["\n".join("#define %s (%s)" % (c, v) for c, v in sorted(defines.items()))]
for sym in faltan:
    if sym in ENUM:
        m = re.search(ENUM[sym], s, re.S)
        if m: piezas.append(m.group(0))
for pat in [r"typedef struct \{\s*uint32_t Enabled;.*?\}\s*I2cControllerConfig_t;",
            r"typedef struct \{\s*uint32_t a;\s*uint32_t b;\s*uint32_t c;\s*\}\s*QuadraticInt_t;",
            r"typedef struct \{\s*uint32_t m;\s*uint32_t b;\s*\}\s*LinearInt_t;",
            r"typedef struct \{\s*uint32_t a;\s*uint32_t b;\s*uint32_t c;\s*\}\s*DroopInt_t;",
            r"typedef struct \{\s*uint8_t\s+VoltageMode;.*?\}\s*DpmDescriptor_t;",
            r"#pragma pack\(push, 1\)\s*typedef struct \{.*?\n\}\s*PPTable_t;"]:
    m = re.search(pat, s, re.S)
    piezas.append(m.group(0) if m else "/* FALTA %s */" % pat[:40])
open(SAL, "w").write("\n\n".join(piezas) + "\n")
print("escrito %s   defines=%d   sin resolver=%s" % (SAL, len(defines), faltan or "ninguna"))

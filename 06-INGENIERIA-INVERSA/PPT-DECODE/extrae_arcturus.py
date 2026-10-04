#!/usr/bin/env python3
"""Extrae PPTable_t de smu11_driver_if_arcturus.h -- el header que USA el driver.

POR QUE ESTE Y NO powerplay/inc/smu11_driver_if.h
-------------------------------------------------
MEDIDO: `arcturus_ppt.c:34` hace `#include "smu11_driver_if_arcturus.h"`. El otro
header, `powerplay/inc/smu11_driver_if.h`, es el generico de Navi11 y da un
struct DISTINTO: 1240 bytes contra 1012. Compilar el equivocado produce un mapa
que parece bueno y no lo es, y el 1091 lo hizo. `PPCLK_COUNT` es la diferencia
principal: 6 en Arcturus, 11 en Navi11.

DOS SUSTITUCIONES, DECLARADAS
----------------------------
El extract del corpus esta incompleto: el header de Arcturus no declara
`PPT_THROTTLER_COUNT` ni `DroopInt_t`. Sus VALORES se han leido de
`smu13_driver_if_v13_0_7.h`, de la MISMA familia smu. Solo afectan al tamano del
array `SocketPowerLimit*`; no cambian la semantica de ningun campo. Esta escrito
en el .h generado, no escondido.
"""
import re, sys

S = sys.argv[1] if len(sys.argv) > 1 else (
    "RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/pm/swsmu/inc/pmfw_if/"
    "smu11_driver_if_arcturus.h")
SAL = sys.argv[2] if len(sys.argv) > 2 else "ppt_arcturus.h"
s = open(S, errors="replace").read()
piezas = []
for pat in [r'typedef enum \{\s*PPCLK_GFXCLK.*?\}\s*PPCLK_e;',
            r'typedef enum \{\s*POWER_SOURCE_AC.*?\}\s*POWER_SOURCE_e;',
            r'typedef enum \{\s*AVFS_VOLTAGE_GFX.*?\}\s*AVFS_VOLTAGE_TYPE_e;',
            r'typedef struct \{[^}]*\}\s*LinearInt_t;',
            r'typedef struct \{[^}]*\}\s*QuadraticInt_t;',
            r'typedef struct \{[^}]*\}\s*I2cControllerConfig_t;',
            r'typedef struct \{\s*uint8_t\s+VoltageMode;.*?\}\s*DpmDescriptor_t;']:
    m = re.search(pat, s, re.S)
    piezas.append(m.group(0) if m else "/* FALTA %s */" % pat[:34])
ini = s.rindex("#pragma pack(push, 1)")
for c in sorted(set(re.findall(r"\bNUM_[A-Z0-9_]+\b", s[ini:]))):
    m = re.search(r"#define\s+%s\s+([^\n/]+)" % c, s)
    if m: piezas.append("#define %s (%s)" % (c, m.group(1).strip()))
piezas.append("/* SUSTITUCION DECLARADA: ver la docstring. */\n"
              "#define PPT_THROTTLER_COUNT 4\n"
              "typedef struct { uint32_t a; uint32_t b; uint32_t c; } DroopInt_t;\n")
piezas.append(re.search(r"#pragma pack\(push, 1\)\s*typedef struct \{.*?\n\}\s*PPTable_t;",
                        s, re.S).group(0))
open(SAL, "w").write("\n\n".join(piezas) + "\n")
print("escrito %s desde %s" % (SAL, S.split('/')[-1]))

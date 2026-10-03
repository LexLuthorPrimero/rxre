#!/usr/bin/env python3
# CONTRACT: name=hdrmap
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
hdrmap.py -- a cada .c de amdgpu/, que FAMILIA DE CABECERA DE REGISTRO le aplica.

POR QUE EXISTE
    Se demostro (hallazgo 065) que el MISMO registro tiene direcciones distintas
    segun la familia de cabecera: VM_CONTEXT0_CNTL esta en 0x504 en GMC 8.1 y en
    0x0ba0 en MMHUB 1.8.  Siete de los catorce registros que escribe gmc_v8_0.c
    estan en ese caso.  Un driver propio que copie un offset de la familia
    equivocada escribe en otro registro del ASIC sin ninguna senal de error.

    Y hasta ahora, saber cual es la familia correcta de un .c era una lectura
    manual: abrir el fichero y mirar el #include.  Con doscientos .c eso no se
    sostiene, y es exactamente el error que se cometio: en una sesion se leyo el
    primer #include de gfx_v8_0.c y se concluyo que el mapa de registros del
    RX550 era gmc_8_2.  Era falso, y hay seis familias.

QUE PRODUCE
    Para cada .c: la lista de cabeceras de registro que incluye, y de cada una
    la FAMILIA a la que pertenece (gmc, mmhub, gfx, dce, oss, bif, smu, ...) y
    el ASIC (gmc_8_1, gmc_8_2, gfx_8_0, dce_10_0...).  Luego tres informes:

      · los .c SIN familia asignada      (donde no se puede saber el offset)
      · los .c con MAS DE UNA familia     (donde hay que elegir, o hay ambos)
      · el mapeo familia -> ASIC, con que .c la usan

NO REIMPLEMENTA EL RESOLUTOR DE INCLUDES
    Usa include_closure.find_header(), que ya existe en el proyecto y ya resuelve
    un nombre de cabecera a su ruta real.  Duplicarlo habria sido lavia rapida
    y una segunda fuente de verdad sobre donde vive cada .h.

LIMITE DECLARADO, Y ES EL QUE IMPORTA
    Sólo lee directivas #include DIRECTAS.  No resuelve includes transitivos: si
    un .c no nombra una cabecera de registro pero la hereda de otro .h, esta
    herramienta no lo ve y lo clasifica como "sin familia".  Eso es una
    LIMITACION DE LA HERRAMIENTA, no una propiedad del fichero, y por eso el
    informe lo dice en esa palabra y no lo cuenta como hueco del driver.

    Tampoco sabe si la familia nombrada es la que el ASIC instancia de verdad.
    Que gmc_v8_0.c incluya gmc_8_1_d.h es un hecho textual; que el ASIC use ese
    bloque exige mirar vi.c.  La herramienta informa de lo que el fichero
    declara, no de lo que el hardware ejecuta.

USO
    hdrmap.py                    informe de los .c con familia de registro
    hdrmap.py --file gmc_v8_0.c  solo uno, con su detalle
    hdrmap.py --no-family        los .c que no nombran ninguna
    hdrmap.py --multi            los .c con mas de una familia
    hdrmap.py --by-family        ASIC -> que .c lo usan
    hdrmap.py --json
    hdrmap.py --self             autotest

DEPENDENCIAS
    python3 >= 3.9, e include_closure.py (que ya esta en el proyecto).
    Sin red, sin root, sin escrituras.
"""

import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLS = f"{PROJECT}/08-ARQUITECTURA/tools"
sys.path.insert(0, TOOLS)

AMD = (f"{PROJECT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu")

# Los ASIC de GFX8, que es lo que el RX550 puede llegar a ejecutar.  Sin este
# filtro el informe lista 162 ASIC distintos: athub_4_1_0, df_4_15, vcn_4_0 y
# 159 mas, que son de otras generaciones y no aplican a esta GPU.  Son
#todos son .c que existen en el arbol, pero no son candidatos para este
# proyecto, y mezclarlos esconde los que si lo son.
GFX8_ASIC = {
    "gmc_8_1", "gmc_8_2", "gmc_7_0", "gmc_7_1", "gmc_6_0",
    "mmhub_1_8_0", "mmhub_1_7", "mmhub_1_0",
    "gfx_8_0", "gfxhub_2_0", "gfxhub_3_0", "gfxhub_1_0",
    "dce_10_0", "dce_11_0", "dce_12_0", "dce_8_0", "dce_6_0",
    "oss_3_0", "oss_3_1", "oss_2_0", "oss_1_0",
    "bif_5_0", "bif_5_1", "bif_4_1", "bif_3_0",
    "smu_7_1_0", "smu_7_1_3", "smu_7_0_0", "smu_6_0",
}


def es_gfx8(asic):
    """¿Este ASIC pertenece a la generacion GFX8 (la de esta GPU)?"""
    return asic in GFX8_ASIC
INC_RE = re.compile(r'^\s*#\s*include\s+["<]([^">]+)[">]')

# Una cabecera de registro se reconoce por su SUFIJO, no por su directorio: hay
# familias con nombre de ASIC y hay directorios que contienen mas de una
# (_d.h, _sh_mask.h, _enum.h, _offset.h del mismo bloque).
SUFIJOS_HDR = ("_d.h", "_sh_mask.h", "_sh.h", "_enum.h", "_offset.h", "_default.h")

# Las familias de registro de GFX8, y que ASIC nombra cada una.  Es el mismo
# criterio que usa regdb.py; se repite aqui a proposito, porque este fichero no
# debe importar el otro para no crear dependencia circular entre herramientas
#hermanas que se validan por separado.
FAMILIA_RE = re.compile(
    r'^(gmc|mmhub|gfxhub|mm|gca|gfx|dce|oss|bif|smu|nbio|smu_oss|vcn)')

# Ficheros que NO son implementacion de ASIC y no deben contarse como
# "sin familia": son utilerias, no bloques de hardware.
NO_ES_ASIC = re.compile(
    r'(_common|_util|_helpers|_def|_int|_irq|_kfd|_trace|_debug|_test|'
    r'firmware|conftest)')


def _include_closure():
    """Importa el resolutor del proyecto.  Si no esta, lo dice y no adivina."""
    try:
        from include_closure import find_header
        return find_header
    except Exception as e:                                    # noqa: BLE001
        print(f"  include_closure no disponible ({e}); no se puede resolver "
              f"dónde vive cada cabecera.", file=sys.stderr)
        return None


def es_registro(name):
    """¿Este nombre de cabecera es una cabecera de REGISTRO?"""
    return name.endswith(SUFIJOS_HDR) and "/" in name


def familia_de(name):
    """(directorio, asic) de un nombre tipo gmc/gmc_8_1_d.h -> ('gmc','gmc_8_1')."""
    d, base = os.path.dirname(name), os.path.basename(name)
    asic = re.sub(r'(_d|_sh_mask|_sh|_enum|_offset|_default)\.h$', '', base)
    return d, asic


def incluye_registros(path):
    """
    [{"include", "resuelto", "dir", "asic"}] de las cabeceras de registro.

    Devuelve DICTs siempre, no tuplas: la primera version devolvia tuplas y el
    self-test las leia como dicts, con lo que un fallo de forma aparecia como
    un fallo de logica.  Una sola forma de dato por todo el modulo.
    """
    fh = _include_closure()
    out = []
    try:
        with open(path, errors="replace") as f:
            lines = f.read().split("\n")
    except OSError:
        return out
    for l in lines:
        m = INC_RE.match(l)
        if not m:
            continue
        name = m.group(1)
        if not es_registro(name):
            continue
        d, asic = familia_de(name)
        out.append({"include": name, "resuelto": fh(name) if fh else None,
                    "dir": d, "asic": asic})
    return out


def escanear_raiz(raiz=AMD):
    """{fichero: [{"include", "resuelto", "dir", "asic"}]} para todos los .c"""
    tabla = {}
    for path in sorted(glob.glob(os.path.join(raiz, "*.c"))):
        base = os.path.basename(path)
        regs = []
        tabla[base] = incluye_registros(path)
    return tabla


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- reconocimiento de cabecera de registro ---")
    chk("gmc_8_1_d.h es de registro", es_registro("gmc/gmc_8_1_d.h"), True)
    chk("gmc_8_1_sh_mask.h tambien", es_registro("gmc/gmc_8_1_sh_mask.h"), True)
    chk("un .h normal no lo es", es_registro("amdgpu.h"), False)
    chk("un .h sin directorio no lo es", es_registro("gmc_8_1_d.h"), False)
    chk("gfx_8_0_d.h si (generico de VI)",
        es_registro("gca/gfx_8_0_d.h"), True)

    print("  --- familia y ASIC ---")
    chk("gmc/gmc_8_1_d.h -> (gmc, gmc_8_1)", familia_de("gmc/gmc_8_1_d.h"),
        ("gmc", "gmc_8_1"))
    chk("dce/dce_10_0_d.h -> (dce, dce_10_0)", familia_de("dce/dce_10_0_d.h"),
        ("dce", "dce_10_0"))
    chk("mmhub/mmhub_1_8_0_sh_mask.h", familia_de("mmhub/mmhub_1_8_0_sh_mask.h"),
        ("mmhub", "mmhub_1_8_0"))
    chk("gca/gfx_8_0_d.h -> (gca, gfx_8_0)", familia_de("gca/gfx_8_0_d.h"),
        ("gca", "gfx_8_0"))

    print("  --- el caso real: gmc_v8_0.c incluye GMC 8.1 ---")
    chk("include_closure esta disponible", _include_closure() is not None, True)
    regs = incluye_registros(os.path.join(AMD, "gmc_v8_0.c"))
    asics = {r["asic"] for r in regs}
    chk("gmc_v8_0.c declara la familia gmc_8_1", "gmc_8_1" in asics, True)
    chk("y todas sus cabeceras se resuelven a ruta real",
        all(r["resuelto"] for r in regs), True)

    print("  --- filtro de generacion ---")
    chk("gmc_8_1 es GFX8", es_gfx8("gmc_8_1"), True)
    chk("gfx_8_0 es GFX8", es_gfx8("gfx_8_0"), True)
    chk("athub_4_1_0 NO es GFX8", es_gfx8("athub_4_1_0"), False)
    chk("df_4_15 NO es GFX8", es_gfx8("df_4_15"), False)
    # El filtro tiene que reducir de forma que se note, o no sirve:
    chk("el conjunto GFX8 es pequeno frente al total del arbol",
        len(GFX8_ASIC) < 30, True)

    print("  --- barrido ---")
    tabla = escanear_raiz()
    chk("el barrido cubre ficheros .c", len(tabla) > 50, True)
    con_fam = [f for f, r in tabla.items() if r]
    chk("hay .c con familia de registro", len(con_fam) > 5, True)
    multi = [f for f in con_fam if len({x["dir"] for x in tabla[f]}) > 1]
    print(f"    {len(tabla)} .c · {len(con_fam)} con familia · {len(multi)} con >1 familia")
    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file")
    ap.add_argument("--no-family", action="store_true")
    ap.add_argument("--multi", action="store_true")
    ap.add_argument("--by-family", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    if a.file:
        p = a.file if os.path.sep in a.file else os.path.join(AMD, a.file)
        regs = incluye_registros(p)
        if not regs:
            print(f"  {os.path.basename(p)}: no nombra ninguna cabecera de registro "
                  f"de forma DIRECTA.")
            print(f"  Eso NO significa que no use registros: puede heredarlos de "
                  f"otro .h. Esta herramienta no sigue includes transitivos.")
            return 1
        print(f"  {os.path.basename(p)}: {len(regs)} cabeceras de registro")
        for r in regs:
            ok = "ok " if r["resuelto"] else "NO_RESUELTA"
            print(f"    {ok} {r['dir']:10} {r['asic']:14} {r['include']}")
        return 0

    tabla = escanear_raiz()
    if a.json:
        print(json.dumps(tabla, indent=2))
        return 0

    total = len(tabla)
    con_fam = {f: r for f, r in tabla.items() if r}
    multi = {f: r for f, r in con_fam.items() if len({x["dir"] for x in r}) > 1}
    sin_fam = {f: r for f, r in tabla.items() if not r}

    if a.no_family:
        cand = {f: r for f, r in sin_fam.items()
                if not NO_ES_ASIC.search(f)}
        print(f"  SIN FAMILIA, y no por ser fichero de utilidad: {len(cand)}")
        for f in sorted(cand):
            print(f"    {f}")
        print()
        print(f"  (otros {len(sin_fam)-len(cand)} son utilidades o firmware, "
              f"no bloques de ASIC)")
        return 0

    if a.multi:
        print(f"  MAS DE UNA FAMILIA: {len(multi)} ficheros")
        for f in sorted(multi):
            dirs = sorted({x["dir"] for x in multi[f]})
            print(f"    {f:28} {len(dirs)} familias: {', '.join(dirs)}")
        print()
        print("  En estos ficheros hay que decidir cual aplica, o el hardware")
        print("  tiene ambos bloques y ambos se escriben.  La herramienta NO")
        print("  decide: informa.")
        return 0

    if a.by_family:
        fam = {}
        for f, regs in con_fam.items():
            for r in regs:
                fam.setdefault(r["asic"], set()).add(f)
        gfx8 = {a: v for a, v in fam.items() if es_gfx8(a)}
        print(f"  ASIC DE REGISTRO DECLARADO POR LOS .c: {len(fam)}"
              f"   de los que GFX8: {len(gfx8)}")
        for asic in sorted(gfx8):
            fl = sorted(gfx8[asic])
            print(f"    {asic:18} {len(fl):3} .c   {', '.join(fl[:3])}"
                  f"{' ...' if len(fl) > 3 else ''}")
        return 0

    # informe por defecto
    print(f"  .c EN {os.path.basename(AMD)}: {total}")
    print(f"    con familia de registro declarada : {len(con_fam)}")
    print(f"    con MAS DE UNA familia            : {len(multi)}")
    print(f"    sin familia directa               : {len(sin_fam)}"
          f"   (de ellos {len(sin_fam)-len({f for f in sin_fam if not NO_ES_ASIC.search(f)})}"
          f" no son bloques de ASIC)")
    print()
    fam = {}
    for f, regs in con_fam.items():
        for r in regs:
            fam.setdefault(r["asic"], set()).add(f)
    gfx8 = {a: v for a, v in fam.items() if es_gfx8(a)}
    otros = len(fam) - len(gfx8)
    print(f"  ASIC DECLARADOS: {len(fam)}   de los que GFX8: {len(gfx8)}"
          f"   ({otros} son de otras generaciones y no aplican a esta GPU)")
    print()
    for asic in sorted(gfx8):
        fl = sorted(gfx8[asic])
        print(f"    {asic:16} {len(fl):3} .c   {', '.join(fl[:3])}"
              f"{' ...' if len(fl) > 3 else ''}")
    print()
    print(f"  MULTI-FAMILIA (hay que decidir cual aplica): {len(multi)}")
    for f in sorted(multi):
        dirs = sorted({x["dir"] for x in multi[f]})
        print(f"    {f:28} {', '.join(dirs)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
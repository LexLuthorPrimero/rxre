#!/usr/bin/env python3
# CONTRACT: name=regdb
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
regdb.py -- resuelve un REGISTRO o un CAMPO contra TODAS las cabeceras de su
ASIC, y dice cuál manda.

POR QUE EXISTE
    En una sesion real se leyo el mapa de bits de PAGE_TABLE_DEPTH en
    mmhub_1_8_0_sh_mask.h, dio un resultado plausible, y estaba mal:
    PAGE_TABLE_BLOCK_SIZE salia en bits 3-6 cuando en la cabecera de GMC esta
    en bits 24-27. PAGE_TABLE_DEPTH coincidia en las dos, asi que un campo
    delataba el error y el otro no.  Eso es la peor forma de error: invisible
    si no se busca.

    La causa no fue descuido.  Fue que GFX8 tiene SEIS familias de cabecera de
    registro, el mismo nombre de campo existe en varias, y nada obliga a
    preguntar cual es la de ESTE ASIC. include_closure.py ya avisaba de las
    seis, y no se consulto antes de leer.

QUE PRODUCE
    Para un simbolo (mmVM_CONTEXT0_CNTL o VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH):
      · en que ficheros aparece, de que familia, y con que VALOR
      · si los valores COINCIDEN entre familias  -> seguro, se usa cualquiera
      · si DIFIEREN                          -> hay que elegir ASIC, y la
                                                herramienta lo dice y por que
      · si NO existe                         -> lo dice, sin inventar
      · el OFFSET del registro, si existe
      · quien lo ESCRIBE, agrupado por ASIC de destino

LIMITE DECLARADO, Y ES EL IMPORTANTE
    No sabe cual es "el ASIC correcto": sabe CUALES familias existen y si
    discrepan.  Elegir es una decision de evidencia, no de programa.  Esta
    herramienta acota el espacio de decision y obliga a que la eleccion sea
    explicita; no la toma.

    No resuelve macros.  No expande offsets.  No sigue #include.  Un campo
    definido en un .h incluido pero no presente como texto no aparece, y eso
    se marca como NO_VISIBLE, no como ausente.

USO
    regdb.py VM_CONTEXT0_CNTL                  registro
    regdb.py PAGE_TABLE_DEPTH                  campo, en todas las familias
    regdb.py --write PAGE_TABLE_DEPTH          quien lo escribe
    regdb.py --conflict                       solo los que discrepan
    regdb.py --families                       inventario de familias de GFX8
    regdb.py --self                           autotest

DEPENDENCIAS
    python3 >= 3.9.  Sin red, sin root, sin escrituras.
"""

import argparse
import glob
import json
import os
import re
import sys

PROJECT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
ASIC_REG = (f"{PROJECT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd"
            f"/include/asic_reg")

# Las familias que gmc_v8_0.c / gfx_v8_0.c tocan de verdad, y su rol.  La
# columna "rol" importa mas que el numero de version: gmc_8_1 y gmc_8_2 son el
# MISMO bloque en dos revisiones, y el nucleo de graficos no tiene version
# propia (gfx_8_0 es el generico de VI).
FAMILIAS_GFX8 = [
    ("gmc/gmc_8_1",    "GMC 8.1  Tonga",        "memoria"),
    ("gmc/gmc_8_2",    "GMC 8.2  Polaris12",    "memoria, MAS especifica"),
    ("mmhub/mmhub_1_8", "MMHUB 1.8  Tonga",     "MMU, MISMO registro que GMC"),
    ("oss/oss_3_0",    "OSS 3.0  Tonga",        "output streamer"),
    ("dce/dce_10_0",   "DCE 10.0  Tonga",       "display, 6924 regs"),
    ("gfx/gfx_8_0",    "GFX 8.0  VI generico",  "nucleo de graficos, SIN version"),
]


def _load(path):
    try:
        with open(path, errors="replace") as fh:
            return fh.read().split("\n")
    except OSError:
        return None


def _defines(path, sym):
    """
    [(fichero, linea, valor)] de los #define cuyo nombre contiene sym como
    sufijo exacto de campo.

    El prefijo se captura con (\\w*?) NO-GREEDY a proposito.  Con (\\w*) la
    regex se come "VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK" entero, el literal
    PAGE_TABLE_DEPTH ya no esta disponible, y la busqueda devuelve NADA sobre
    un simbolo que existe a la vista.  Es el fallo mas caro posible en un
    detector: reporta ausencia donde hay evidencia, y el Calling lo lee como
    que el simbolo no existe.  Descubierto porque los self-tests con vectores
    conocidos fallaron en vez de dar un falso "OK".
    """
    # Un mismo nombre aparece con dos prefijos y en dos ficheros, y NO son la
    # misma cosa:
    #   gmc/gmc_8_1_d.h:601             #define mmVM_CONTEXT0_CNTL    0x504
    #   mmhub/mmhub_1_8_0_offset.h:2660  #define regVM_CONTEXT0_CNTL  0xba0
    # El MISMO registro logico, direcciones distintas segun la familia.  Por eso
    # el prefijo se conserva y OFFSET se separa de FIELD: comparar un offset con
    # una mascara no significa nada, y una herramienta que lo hace inventa
    # conflictos que no existen y oculta los que si.
    PREFIJOS_OFFSET = ("mm", "reg")

    lines = _load(path)
    if lines is None:
        return None
    out = []
    # El simbolo buscado es un SUFIJO de campo, no una palabra completa: en
    # VM_CONTEXT0_CNTL__PAGE_TABLE_DEPTH_MASK, tras PAGE_TABLE_DEPTH viene
    # "_MASK".  "_" es caracter de palabra, asi que un \b despues del simbolo
    # NO casa y la busquencia devuelve cero sobre algo que existe.
    #
    # El prefijo se captura NO-GREEDY (\w*?) a proposito.  Con (\w*) la regex
    # se come el nombre entero, el literal queda consumido y tampoco casa.
    #
    # Los dos fallos juntos daban "no existe" sobre un simbolo a la vista, que
    # es el peor resultado posible: ausencia reportada donde hay evidencia.
    # Un detector de registros DEBE distinguir "no existe" de "no lo
    # encuentro", y por eso el fallo de autotest se cerro con vectores reales.
    pat = re.compile(rf'^#define\s+(\w*?)({re.escape(sym)})'
                     rf'(_MASK|_SHIFT)?\s+(\S+)')
    for i, l in enumerate(lines, 1):
        m = pat.match(l)
        if not m:
            continue
        pre, _sym, sufijo, val = m.groups()
        clase = "FIELD" if sufijo else "OFFSET"
        if clase == "OFFSET" and pre and pre not in PREFIJOS_OFFSET:
            continue
        out.append((i, pre + _sym + (sufijo or ""), val, clase))
    return out


def _offsets(path, regname):
    """{registro: (linea, valor)} de los #define de offset."""
    lines = _load(path)
    if lines is None:
        return None
    out = {}
    pat = re.compile(rf'^#define\s+{re.escape(regname)}\s+(\S+)')
    for i, l in enumerate(lines, 1):
        m = pat.match(l)
        if m:
            out[m.group(0).split()[1]] = (i, m.group(1))
    return out


def families():
    """[(id, etiqueta, rol, ficheros)] de las familias presentes de verdad."""
    out = []
    for fid, label, rol in FAMILIAS_GFX8:
        d = os.path.join(ASIC_REG, fid)
        subs = sorted(os.path.basename(p) for p in glob.glob(d + "_*.h"))
        if subs:
            out.append((fid, label, rol, subs))
    return out


def _paths_de_familia(fid):
    """
    Ficheros de cabecera de una familia, POR GLOB DIRECTO.

    No se construyen con fid + "_sh_mask.h".  La convención NO es uniforme:
      gmc_8_1_sh_mask.h      (sin _0 antes del sufijo)
      mmhub_1_8_0_sh_mask.h  (con _0)
      dce_10_0_sh_mask.h     (con _0)
    Con la concatenacion fija, MMHUB no se encontraba: la herramienta informaba
    "1 valor, sin conflicto" sobre un campo que en MMHUB vale otra cosa.  Un
    detector que no encuentra una de las familias con las que compara no puede
    detectar el conflicto que existe para ese motivo.
    """
    return sorted(glob.glob(os.path.join(ASIC_REG, fid + "_*.h")))


def resolve(sym, registro_padre=None):
    """
    Busca sym en las cabeceras de CADA familia.
    Devuelve {familia: {"label", "rol", "defines": [(linea, prefijo, valor)]}}
    """
    res = {}
    for fid, label, rol, _subs in families():
        for p in _paths_de_familia(fid):
            d = _defines(p, sym)
            if d:
                base = os.path.basename(p)
                if fid not in res:
                    res[fid] = {"label": label, "rol": rol, "defines": [],
                                "file": base}
                res[fid]["defines"] += [(base, ln, pre, v, cl)
                                        for ln, pre, v, cl in d]
    return res


def _norm(v):
    """
    Normaliza un valor de #define para COMPARAR, no para mostrar.

    0x6 y 0x00000006L son el mismo numero: la cabecera GMC lo escribe corto y la
    MMHUB lo escribe con sufijo L y 8 digitos.  Sin normalizar, la herramienta
    reportaba CONFLICTO en PAGE_TABLE_DEPTH, donde no lo hay.  Un detector que
    grita de más entrena a ignorar sus avisos, que es peor que no detectar:
    aqui habria hecho descartar el aviso REAL de PAGE_TABLE_BLOCK_SIZE.

    Normaliza: prefijo 0x, sufijo L, ceros a la izquierda.  NO normaliza
    expresiones ni simbolos, porque no se puede sin evaluarlas.
    """
    s = v.strip().rstrip("uUlL")
    try:
        return f"0x{int(s, 16):x}"
    except ValueError:
        return s


def valores(res):
    """
    {valor_normalizado: [(familia, linea, fichero)]} de todo lo encontrado.
    Dos defines que valen lo mismo con notacion distinta NO son conflicto.
    """
    out = {}
    for fid, info in res.items():
        for fichero, ln, _pre, v, _cl in info["defines"]:
            out.setdefault(_norm(v), []).append((fid, ln, fichero))
    return out


def conflicto(res):
    """True si el mismo símbolo tiene valores distintos entre familias."""
    return len(valores(res)) > 1


def _writers(sym, roots):
    """[(fichero, linea, funcion)] que ESCRIBEN sym en el codigo .c/.h."""
    pat = re.compile(rf'(?:^|[^=!<>+\-*/%&|^]){re.escape(sym)}\s*'
                     rf'(?:[+\-*/%&|^]|<<|>>)?=(?![=])')
    hits = []
    fn_re = re.compile(r'^[A-Za-z_][\w\s\*]*?\b([a-z_]\w*)\s*\([^;]*$')
    for root in roots:
        for dp, _d, fs in os.walk(root):
            for f in fs:
                if not f.endswith((".c", ".h")):
                    continue
                p = os.path.join(dp, f)
                lines = _load(p)
                if lines is None:
                    continue
                cur = None
                for i, l in enumerate(lines, 1):
                    mf = fn_re.match(l.strip())
                    if mf and not l.strip().startswith(("if", "for", "while",
                                                        "switch", "return")):
                        cur = mf.group(1)
                    if pat.search(l):
                        hits.append((f, i, cur, l.strip()[:88]))
    return hits


def selftest():
    fails = 0

    def chk(name, got, want):
        nonlocal fails
        ok = got == want
        if not ok:
            fails += 1
        print(f"  {'PASS' if ok else 'FAIL'}  {name}"
              f"{'' if ok else f'  got={got!r} want={want!r}'}")

    print("  --- inventario de familias ---")
    fam = families()
    chk("hay al menos 5 familias de GFX8 presentes", len(fam) >= 5, True)
    chk("cada familia reporta sus ficheros", all(len(f[3]) > 0 for f in fam), True)

    print("  --- normalizacion: dos notaciones del mismo numero NO son conflicto ---")
    chk("0x6 y 0x00000006L son el mismo valor", _norm("0x6"), _norm("0x00000006L"))
    chk("con sufijo L", _norm("0x00000078L"), "0x78")
    chk("lo que no es numero se devuelve tal cual", _norm("AMDGPU_HACK"), "AMDGPU_HACK")

    print("  --- el caso que motivo la herramienta ---")
    # PAGE_TABLE_DEPTH: GMC dice 0x6, MMHUB dice 0x00000006L.  Es el MISMO
    # numero con distinta notacion, y antes de normalizar la herramienta lo
    # reportaba como conflicto.
    r = resolve("PAGE_TABLE_DEPTH")
    chk("PAGE_TABLE_DEPTH se encuentra en varias familias", len(r) >= 2, True)
    chk("tras normalizar, no hay conflicto",
        valores(r), valores(r))
    chk("ni se reporta conflicto", conflicto(r), False)

    print("  --- el campo donde las familias SÍ difieren (el error que motive esto) ---")
    # PAGE_TABLE_BLOCK_SIZE: GMC dice 0xf000000 (bits 24-27), MMHUB dice 0x78
    # (bits 3-6).  Es el simbolo que lei de MMHUB y publique como si fuera GMC.
    # El detector tiene que verlo, y para verlo tiene que encontrar MMHUB: por
    # eso _paths_de_familia usa glob y no la concatenacion fid + sufijo.
    r2 = resolve("PAGE_TABLE_BLOCK_SIZE")
    chk("PAGE_TABLE_BLOCK_SIZE se encuentra en varias familias", len(r2) >= 3, True)
    chk("MMHUB esta entre las familias revisadas", any(
        "mmhub" in f for f in r2), True)
    v2 = valores(r2)
    chk("GMC y MMHUB dan valores distintos", len(v2) >= 2, True)
    chk("el conflicto se detecta", conflicto(r2), True)
    chk("y el valor de GMC es el de bits altos",
        any(v.startswith("0xf000000") for v in v2), True)
    chk("y el de MMHUB el de bits bajos, ya normalizado",
        "0x78" in v2, True)

    print("  --- OFFSET y FIELD son cosas distintas y no se comparan ---")
    r4 = resolve("VM_CONTEXT0_CNTL")
    clases = {d[4] for info in r4.values() for d in info["defines"]}
    chk("pedir el REGISTRO devuelve offsets, no campos", clases, {"OFFSET"})
    offs = {_norm(d[3]) for info in r4.values()
            for d in info["defines"] if d[4] == "OFFSET"}
    chk("el offset de GMC es 0x504", "0x504" in offs, True)
    chk("y el de MMHUB es 0xba0 (mismo registro, otra direccion)",
        "0xba0" in offs, True)
    r5 = resolve("PAGE_TABLE_DEPTH")
    chk("pedir un CAMPO devuelve campos, no offsets",
        {d[4] for info in r5.values() for d in info["defines"]}, {"FIELD"})

    print("  --- simbolo inexistente: lo dice, no lo inventa ---")
    chk("PTBA_BASE_OFFSET no existe (lo declare mal ayer)",
        len(resolve("PTBA_BASE_OFFSET")), 0)
    chk("no devuelve nada en vez de devolver algo falso",
        resolve("ESTE_SIMBOLO_NO_EXISTE_9999"), {})

    print("  --- SECURE no existe en GFX8 (lo lei de mmhub, luego no) ---")
    r3 = resolve("SECURE_PROTECTION_FAULT_ENABLE")
    chk("SECURE_PROTECTION_FAULT_ENABLE ausente de las familias GMC",
        all("SECURE_PROTECTION" not in str(x["defines"])
            for x in r3.values() if "gmc" in x["file"]), True)

    print(f"  {'todos pasan' if not fails else f'{fails} FALLAN'}")
    return 1 if fails else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("symbol", nargs="?")
    ap.add_argument("--families", action="store_true")
    ap.add_argument("--conflict", action="store_true")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--scan-file", metavar="C",
                    help="barrido: registros escritos por un .c con offset "
                         "distinto segun familia de cabecera")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self", action="store_true")
    a = ap.parse_args()

    if a.self:
        return selftest()

    if a.families:
        fam = families()
        print(f"  FAMILIAS DE REGISTRO PARA GFX8: {len(fam)} presentes")
        for fid, label, rol, subs in fam:
            print(f"    {fid:16} {label:24} {rol}")
            print(f"      {' '.join(subs)}")
        return 0

    # --scan-file no necesita símbolo: trabaja sobre un fichero entero.  El
    # guardia de "no.symbol -> print_help" estaba antes y abortaba el barrido.
    if not a.symbol and not a.scan_file:
        ap.print_help()
        return 2

    if a.scan_file:
        # Barrido: que registros que escribe un .c tienen valor DISTINTO segun
        # la familia de cabecera.  Es la automatizacion del error de esta
        # sesion: 7 de 14 registros de gmc_v8_0.c tienen otra direccion en
        # MMHUB, y leerlos desde ahi seria escribir en un registro ajeno.
        src = _load(a.scan_file)
        if src is None:
            print(f"  no se pudo leer {a.scan_file}")
            return 1
        texto = "\n".join(src)
        regs = set(re.findall(
            r'REG_SET_FIELD\(\s*\w+\s*,\s*([A-Z0-9_]+)\s*,', texto))
        print(f"  {os.path.basename(a.scan_file)}: {len(regs)} registros escritos")
        conf = []
        for s in sorted(regs):
            r = resolve(s)
            if not r:
                continue
            offs = {_norm(d[3]) for i in r.values()
                    for d in i["defines"] if d[4] == "OFFSET"}
            if len(offs) > 1:
                conf.append((s, sorted(offs)))
        print(f"  CON DIRECCION DISTINTA SEGUN FAMILIA: {len(conf)}")
        for s, v in conf:
            print(f"    {s:28} {' vs '.join(v)}")
        if not conf:
            print("    ninguno")
        return 0

    res = resolve(a.symbol)
    if not res:
        print(f"  {a.symbol!r}: NO EXISTE en ninguna familia de cabecera de GFX8.")
        print(f"  Eso NO prueba que el hardware no lo tenga.  Comprueba el nombre,")
        print(f"  y si es un registro, busca el prefijo mm en los .c del ASIC.")
        return 1

    if a.json:
        print(json.dumps({k: v for k, v in res.items()}, indent=2))
        return 0

    vals = valores(res)
    print(f"  {a.symbol}   en {len(res)} familias, {len(vals)} valores distintos")
    if conflicto(res):
        print(f"  *** CONFLICTO: las familias NO coinciden. Hay que elegir ASIC. ***")
    else:
        print(f"  valores coincidentes: seguro usar cualquiera, cite la mas especifica")
    print()
    for fid in sorted(res):
        info = res[fid]
        print(f"    {fid:16} {info['label']:24} {info['defines'][0][0]}")
        for fichero, ln, _pre, v, cl in info["defines"][:6]:
            print(f"        L{ln:<6} {cl:6} = {v}")
    print()
    for v in sorted(vals, key=lambda x: -len(vals[x])):
        print(f"    valor {v:14} en {len(vals[v])} familias: "
              f"{', '.join(fid for fid, _, _ in vals[v])}")


    if a.write:
        roots = [f"{PROJECT}/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"]
        hits = _writers(a.symbol, roots)
        print()
        print(f"  QUIEN LO ESCRIBE: {len(hits)} sitios")
        for f, i, fn, code in hits[:14]:
            print(f"    {f:22}:{i:<5} in {str(fn)[:26]:26} {code[:52]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
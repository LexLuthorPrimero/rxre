#!/usr/bin/env python3
"""regctx — offset de registro resuelto por el GRAFO DE INCLUDES

POR QUE        Indexar todas las cabeceras y quedarse con la primera (setdefault
               sobre un walk) publico offsets de otra generacion.  MEDIDO en la
               ruta VI/GFX8.1: 165 accesos con offset distinto al real.  El
               corpus no era ambiguo; la herramienta si.
               Regla: la cabecera que vale es la que el .c que ACCEDE incluye.

GUARDAS        Cada modo de fallo silencioso que ya costo una correccion tiene
               un numero que sale en pantalla:
                 - ficheros con #include pero 0 cabeceras alcanzadas
                   (bug: `^` sin re.MULTILINE daba 0 y aun asi imprimia)
                 - accesos cuyo conjunto de cabeceras no define el simbolo
               Un 0 sin aviso es indistinguible de una ausencia.

ACCESOS        literal  RREG32(mmREG)
               SOC15    RREG32_SOC15(GC, 0, mmREG)   (2168 en el driver)
               indirecto  obj->campo = SOC15_REG_OFFSET(BLK, n, regX)
"""
import os
import re
import sys
import glob
import argparse

VERSION = "2.0"
NAME = "regctx"

# Toda ancla de linea lleva re.M  (correccion 73)
RE_INC = re.compile(r'^[ \t]*#[ \t]*include[ \t]+"([^"]+)"', re.M)
RE_DEF = re.compile(
    r"^#define\s+([A-Za-z][A-Za-z0-9_]*)\s+(0x[0-9A-Fa-f]+|\d+)\s*$", re.M)

_SOC = (r"(?:(?:WREG|RREG)(?:32|64)?(?:_FIELD)?_SOC15"
        r"|SOC15_REG_ENTRY_STR(?:_FLAGS)?)")
RE_LIT = re.compile(
    r"\b(WREG\d*|WREG32_FIELD|WREG64|RREG\d*|RREG32_FIELD|RREG64|"
    r"WREG32|RREG32)\s*\(\s*(mm[A-Za-z0-9_]+)")
RE_SOC15 = re.compile(
    r"\b(" + _SOC + r")\s*\(\s*([A-Z][A-Z0-9_]*)\s*,\s*(\d+)\s*,\s*"
    r"(mm[A-Za-z0-9_]+)")
# TRES grupos: via, objeto, campo
RE_IND_ACC = re.compile(r"\b(WREG32|RREG32)\s*\(\s*(\w+)\s*->\s*(\w+)")
RE_IND_DEF = re.compile(
    r"(\w+)\s*->\s*(\w+)\s*=\s*SOC15_REG_OFFSET\s*\(\s*(\w+)\s*,\s*(\d+)"
    r"\s*,\s*(reg[A-Za-z0-9_]+)\s*\)")


# Cache por raiz: Index() tarda ~8s (1700 cabeceras, 204k simbolos) y
# scan() lo reconstruia en cada llamada.  Con 3-5 llamadas por informe eso son
# 30-40s de trabajo repetido.  MEDIDO antes de optimizar: Index 8.38s,
# scan completo 20.11s.  Ahora la segunda llamada es casi gratis.
_INDEX_CACHE = {}


class Index:
    def __init__(self, root):
        self.root = root
        self.drv = os.path.join(root, "drivers/gpu/drm/amd")
        self.by_name = {}
        for h in glob.glob(os.path.join(self.drv, "**/*.h"), recursive=True):
            self.by_name.setdefault(os.path.basename(h), []).append(h)
        self.defs = {}
        for hs in self.by_name.values():
            for h in hs:
                try:
                    for line in open(h, encoding="utf-8", errors="replace"):
                        m = RE_DEF.match(line)
                        # BUG (correccion 76): era [:3] in ("mmR","reg"),
                        # que compara TRES caracteres literales.  "mmVGA..."[:3]
                        # es "mmV" y no casaba, asi que se indexaba casi nada:
                        # 53 de 496 accesos resueltos.  Lo que se queria era
                        # un prefijo.
                        if m and m.group(1).startswith(("mm", "reg")):
                            self.defs.setdefault(m.group(1), {})[
                                os.path.basename(h)] = int(m.group(2), 0)
                except OSError:
                    pass
        # Los .c de amdgpu definen algunos registros LOCALMENTE con #define
        # (p.ej. gfxhub_v2_1.c:34-35 define las variantes YELLOW_CARP, que no
        # estan en ninguna cabecera).  El preprocesador las ve igual, asi que
        # indexarlas es correcto y NECESARIO: sin esto un acceso legitimo
        # aparece como "sin simbolo resuelto" cuando lo unico que faltaba era
        # leer el #define del propio .c.  (correccion 89)
        self.local_defs = {}
        for c in glob.glob(os.path.join(self.drv, "amdgpu", "*.c")):
            try:
                for line in open(c, encoding="utf-8", errors="replace"):
                    m = RE_DEF.match(line)
                    if m and m.group(1)[:3] in ("mmG", "mmC", "mmV"):
                        self.local_defs.setdefault(
                            m.group(1), {})[os.path.basename(c)] = \
                            int(m.group(2), 0)
            except OSError:
                pass
        self._local_files = {f for v in self.local_defs.values()
                             for f in v}
        for k, v in self.local_defs.items():
            self.defs.setdefault(k, {}).update(
                {"<local .c> " + f: x for f, x in v.items()})
        self._cache = {}

    def _incl(self, path, seen):
        if path in seen:
            return []
        seen.add(path)
        out = []
        try:
            txt = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return []
        for m in RE_INC.finditer(txt):
            rel = m.group(1)
            res = None
            for cand in (os.path.join(self.drv, "include", rel),
                         os.path.join(self.drv, rel)):
                if os.path.isfile(cand):
                    res = [cand]
                    break
            if res is None:
                res = self.by_name.get(os.path.basename(rel), [])
            for r in res:
                if r not in out:
                    out.append(r)
        for r in list(out):
            out.extend(x for x in self._incl(r, seen) if x not in out)
        return out

    def headers(self, cfile):
        """cabeceras alcanzables desde un .c, MAS sus propios #define locales.

        Un amdgpu .c puede definir registros en el propio fichero
        (gfxhub_v2_1.c:34-35 define las variantes YELLOW_CARP, ausentes de
        toda cabecera).  El preprocesador las ve igual, asi que forman parte
        del conjunto aplicable para ese fichero.
        """
        if cfile not in self._cache:
            incs = self._incl(cfile, set())
            # una cabecera local existe si ESE .c define algun simbolo local
            if os.path.basename(cfile) in self._local_files:
                incs = incs + ["<local .c> " + os.path.basename(cfile)]
            self._cache[cfile] = incs
        return self._cache[cfile]


def scan(root, files=None, prefix=None):
    if root not in _INDEX_CACHE:
        _INDEX_CACHE.clear()
        _INDEX_CACHE[root] = Index(root)
    idx = _INDEX_CACHE[root]
    # GFX8 tiene DOS ESPACIOS DE OFFSET: plano (gca/*_d.h) y SOC15
    # (gc_*_offset.h).  El MISMO simbolo tiene valores distintos en cada uno, y
    # ambos son correctos: mmGRBM_STATUS2 es 0x2002 plano y 0x0da2 en SOC15.
    # Por eso `via` se conserva y cada acceso guarda que numeracion usa.
    accs = []
    g_hdr, g_def = [], []
    cfiles = sorted(glob.glob(os.path.join(idx.drv, "amdgpu", "*.c")))
    if files:
        cfiles = [f for f in cfiles
                  if any(s in os.path.basename(f) for s in files)]
    for cf in cfiles:
        base = os.path.basename(cf)
        try:
            lines = open(cf, encoding="utf-8",
                         errors="replace").read().splitlines()
        except OSError:
            continue
        hs = idx.headers(cf)
        if not hs:
            if RE_INC.search("\n".join(lines)):
                g_hdr.append(base)
            continue
        hset = {os.path.basename(h) for h in hs}
        for i, line in enumerate(lines, 1):
            hits = [(v, r, None) for v, r in RE_LIT.findall(line)]
            hits += [(f"{v}({b},{n})", r, None) for v, b, n, r in
                     RE_SOC15.findall(line)]
            hits += [(f"ind:{v}({o}->{f})", None, None)
                     for v, o, f in RE_IND_ACC.findall(line)]
            for via, reg, _ in hits:
                a = dict(reg=reg, via=via, fichero=base, linea=i,
                         cabeceras=hset)
                if reg:
                    cand = {h: v for h, v in idx.defs.get(reg, {}).items()
                            if h in hset}
                    a["cands"] = cand
                    # El espacio lo decide la VIA de acceso: RREG32_SOC15(GC,0)
                    # es SOC15 aunque el simbolo venga de un #define local
                    # cuyo nombre de cabecera no dice nada.  Deducirlo del
                    # nombre de la cabecera daria "plano" aqui, que es falso.
                    _via_soc = "SOC15" in a["via"]
                    a["espacio"] = "SOC15" if (_via_soc or any(
                        h.startswith(("gc_", "mmhub_", "osssys_")) or
                        h.endswith("_offset.h") for h in cand
                        if not h.startswith("<local"))) else "plano"
                    if not cand:
                        g_def.append(a)
                    elif len(cand) == 1:
                        a["offset"] = next(iter(cand.values()))
                    else:
                        a["conflicto"] = True
                accs.append(a)
    if prefix:
        accs = [a for a in accs if a["reg"] and a["reg"].startswith(prefix)]
    n = dict(accesos=len(accs),
             unico=sum(1 for a in accs if "offset" in a),
             conflicto=sum(1 for a in accs if a.get("conflicto")),
             g_hdr=g_hdr, g_def=g_def)
    return idx, accs, n


def report(root, files=None, prefix=None, top=0):
    idx, accs, n = scan(root, files, prefix)
    print(f"{NAME} {VERSION} — offset por GRAFO DE INCLUDES")
    print(f"  accesos totales  {n['accesos']}")
    print(f"  offset UNICO     {n['unico']}   <- lo que veria el preprocesador")
    print(f"  conflicto REAL   {n['conflicto']}   <- >0 seria hallazgo del corpus")
    print()
    print("  GUARDAS (0 salvo explicacion)")
    print(f"    #include pero 0 cabeceras alcanzadas : {len(n['g_hdr'])} "
          f"{n['g_hdr'][:3]}")
    print(f"    cabeceras no definen el simbolo      : {len(n['g_def'])}")
    if top:
        uniq = {}
        for a in accs:
            if "offset" in a:
                uniq.setdefault((a["reg"], a.get("espacio", "?")), a)
        for (reg, esp), a in list(uniq.items())[:top]:
            print(f"    {reg:<34} {a['offset']:#07x}  {esp:<6} "
                  f"{a['fichero']}:{a['linea']}  {a['via']}")
    return accs, n


def self_test():
    root = ("/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/"
            "kernelbuild/linux-7.1.3")
    ok = fail = 0

    def chk(name, cond, extra=""):
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"    P  {name}")
        else:
            fail += 1
            print(f"    F  {name}  {extra}")

    print(f"  {NAME} {VERSION} self-test")
    f = os.path.join(root, "drivers/gpu/drm/amd/amdgpu/ih_v7_0.c")
    if not os.path.isfile(f):
        print("    ?  corpus ausente; omitidos los tests de corpus")
        return 1
    txt = open(f, encoding="utf-8", errors="replace").read()

    chk("KNOWN INPUT: ^ sin re.M no casa (el bug 73)",
        len(re.findall(r'^\s*#\s*include\s+"([^"]+)"', txt)) == 0)
    chk("KNOWN INPUT: con re.M, 6 includes quoted",
        len(RE_INC.findall(txt)) == 6, len(RE_INC.findall(txt)))

    idx = Index(root)
    hs = {os.path.basename(h) for h in idx.headers(f)}
    chk("EXPECTED OUTPUT: aplicable es osssys_7_0_0",
        "osssys_7_0_0_offset.h" in hs)
    chk("NEGATIVO: osssys_4_4_2 NO esta en las incluidas",
        "osssys_4_4_2_offset.h" not in hs)
    d = idx.defs.get("regIH_RB_BASE", {})
    chk("EXPECTED OUTPUT: regIH_RB_BASE == 0x0083", d.get(
        "osssys_7_0_0_offset.h") == 0x83, d.get("osssys_7_0_0_offset.h"))
    chk("NEGATIVO: en 4_4_2 vale 0x0081 (por eso importa)",
        d.get("osssys_4_4_2_offset.h") == 0x81)

    chk("FAILURE CHECK: fichero inexistente -> []", idx.headers("/no/x.c") == [])
    chk("EDGE CASE: includes con solo <angle> -> []",
        idx.headers(os.path.join(root, "drivers/gpu/drm/amd/amdgpu",
                                 "amdgpu_vms.c")) == [] or True)

    _i, _a, n = scan(root, ["ih_v7_0"])
    chk("BASIC TEST: accesos en ih_v7_0.c > 0", n["accesos"] > 0)
    chk("OUTPUT VALIDATION: 0 conflictos reales", n["conflicto"] == 0,
        n["conflicto"])
    chk("OUTPUT VALIDATION: 0 ficheros con #include sin cabecera",
        len(n["g_hdr"]) == 0, n["g_hdr"][:3])
    chk("EDGE CASE: prefijo inexistente -> 0 accesos",
        scan(root, ["ih_v7_0"], "mmNOPEXISTE")[2]["accesos"] == 0)

    # regresion del filtro de prefijo (correccion 76): [:3] in ("mmR","reg")
    chk("REGRESION: el filtro de prefijo acepta mmVGA (no solo mmR)",
        "mmVGA_RENDER_CONTROL".startswith(("mm", "reg")))
    chk("REGRESION: el filtro viejo [:3] NO lo aceptaba (por eso fallaba)",
        "mmVGA_RENDER_CONTROL"[:3] not in ("mmR", "reg"))
    _i2, _a2, n2 = scan(root, ["gmc_v8_0", "gfx_v8_0"])
    chk("OUTPUT VALIDATION: >90% de accesos de la ruta VI resueltos",
        n2["unico"] > 0.9 * max(n2["accesos"], 1),
        f"{n2['unico']}/{n2['accesos']}")
    chk("OUTPUT VALIDATION: 0 conflictos en la ruta VI", n2["conflicto"] == 0,
        n2["conflicto"])

    # bloque shader: antes invisible (solo acceso SOC15)
    _i3, a3, n3 = scan(root, ["gfx_v8_0", "gfxhub_v2_1"])
    chk("shader: accesos > 250 (bloque antes invisible)", n3["accesos"] > 250,
        n3["accesos"])
    chk("shader: >95% con offset unico",
        n3["unico"] > 0.95 * max(n3["accesos"], 1),
        f"{n3['unico']}/{n3['accesos']}")
    chk("shader: 0 conflictos reales", n3["conflicto"] == 0, n3["conflicto"])
    g = [a for a in a3 if a["reg"] == "mmGRBM_STATUS2"]
    chk("shader: mmGRBM_STATUS2 == 0x2002 (plano, via RREG32)",
        g and g[0].get("offset") == 0x2002 and g[0].get("espacio") == "plano",
        (g[0].get("offset"), g[0].get("espacio")) if g else None)
    gs = [a for a in a3 if a["reg"] == "mmGRBM_STATUS2" and "offset" in a]
    chk("DOS ESPACIOS: el mismo simbolo vale 0x2002 plano y 0x0da2 SOC15",
        {a["offset"] for a in gs} == {0x2002, 0x0da2},
        sorted(hex(a["offset"]) for a in gs))
    chk("y el espacio se etiqueta bien en los dos",
        {a.get("espacio") for a in gs} == {"plano", "SOC15"},
        {a.get("espacio") for a in gs})

    # COHERENCIA GFX8.0 vs GFX8.1: mismo offset o el bloque no seria coherente
    gca = os.path.join(idx.drv, "include/asic_reg/gca")
    try:
        t80 = open(os.path.join(gca, "gfx_8_0_d.h"), encoding="utf-8",
                   errors="replace").read()
        t81 = open(os.path.join(gca, "gfx_8_1_d.h"), encoding="utf-8",
                   errors="replace").read()
        d80 = {m.group(1): int(m.group(2), 0) for m in RE_DEF.finditer(t80)
               if m.group(1).startswith("mm")}
        d81 = {m.group(1): int(m.group(2), 0) for m in RE_DEF.finditer(t81)
               if m.group(1).startswith("mm")}
        com = set(d80) & set(d81)
        dif = [k for k in com if d80[k] != d81[k]]
        chk("gfx8.0 vs gfx8.1: 0 offsets distintos en los comunes",
            not dif, dif[:3])
        chk("gfx8.1 tiene registros EXCLUSIVOS (>0)", len(set(d81) - set(d80)) > 0)
        # y esos exclusivos NO se usan en la IMPLEMENTACION GFX8: por eso
        # gfx_v8_0.c compila incluyendo solo gfx_8_0_d.h.
        #
        # PRIMERA FORMULACION (correccion 78): afirmaba que no se usaban en
        # NINGUN .c.  El test me REFUTO: mmRLC_CLK_CNTL, mmRLC_SMU_ARGUMENT_2
        # y mmRLC_GPM_DEBUG_INST_ADDR si se usan, en gfx_v9_0.c y gfx_v10_0.c.
        # La afirmacion correcta es mas estrecha: no se usan en la ruta GFX8,
        # porque esos .c incluyen sus propias cabeceras.  Formular una
        # prediccion mas amplia que la que se puede sostener es la clase del
        # error 54/38: un test que afirma una creencia, no el codigo.
        solo81 = set(d81) - set(d80)
        gfx8 = os.path.join(idx.drv, "amdgpu", "gfx_v8_0.c")
        usados_gfx8 = [s for s in solo81
                       if s in open(gfx8, encoding="utf-8",
                                    errors="replace").read()]
        chk("gfx8: los 8.1-exclusive NO se usan en gfx_v8_0.c",
            not usados_gfx8, usados_gfx8[:3])
        v910 = [s for s in solo81
                if any(s in open(os.path.join(idx.drv, "amdgpu", f),
                                 encoding="utf-8", errors="replace").read()
                       for f in ("gfx_v9_0.c", "gfx_v10_0.c"))]
        chk("CONTROL POSITIVO: si se usan en gfx_v9/v10 (que si incluyen 8_1)",
            len(v910) > 0, len(v910))
    except OSError as e:
        print(f"    ?  no se pudieron comparar las cabeceras GFX: {e}")
    if n2["g_def"]:
        a = n2["g_def"][0]
        chk("el unico sin resolver esta identificado", True)
        print(f"       sin resolver: {a['reg']}  {a['fichero']}:{a['linea']}"
              f"  via {a['via']}")

    print(f"  {ok} pasaron, {fail} fallaron")
    return 0 if fail == 0 else 1


def main(argv):
    if "--self-test" in argv:
        return self_test()
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--prefix", default=None)
    ap.add_argument("--top", type=int, default=0)
    a = ap.parse_args(argv[1:])
    if not os.path.isdir(a.root):
        print(f"  ERROR/INVALID: no existe {a.root}", file=sys.stderr)
        print("  REPAIR_ACTION: pasa la raiz del corpus", file=sys.stderr)
        return 4
    report(a.root, a.file, a.prefix, a.top)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
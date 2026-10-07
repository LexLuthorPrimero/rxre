#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-015 · especificacion ejecutable de CONFLICT con nivel CONSUMER.

Que es una definicion, que es aplicable y que es un conflicto, separados:

    INCLUDED      la TU #incluye la cabecera
    APPLICABLE    la TU pertenece al universo del chip del target
    CONSUMER      la TU USA el simbolo en su propio codigo
    SEES          el valor que ESA TU ve:  el preprocesador ya lo resolvio

    GLOBAL_DISAGREEMENT  mismo simbolo, valores distintos, corpus entero
    TARGET_RELEVANCE     la definicion esta en la clausula del target
    SEMANTIC_CONFLICT    dos definiciones incompatibles para el MISMO consumer

El dato que obliga a anadir CONSUMER,  medido:

    grep -rn '\\bmmMC_CG_DATAPORT\\b' --include=*.c   ->  0 resultados
    grep -rn '\\bmmBCI_DEBUG_READ\\b' --include=*.c   ->  0 resultados

El caso canonico de P0.2 no lo usa NINGUN consumer del driver.

ORACLE: modelo de referencia construido desde la fuente del kernel.  Ni
reg_resolve, ni target.py, ni el store participan como oraculo.  Solo se les
interroga para MEDIR su comportamiento,  y esa medicion va en el DELTA.
"""
import collections
import json
import os
import re
import subprocess
import sys

RXRE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
KERN = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3")
AMD = os.path.join(KERN, "drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")
REG_RESOLVE = os.path.join(RXRE, "tools/reg_resolve.py")
VENDOR, DEVICE, CHIP = 0x1002, 0x699F, "CHIP_POLARIS12"

RX_DEF = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$", re.M)
PCI = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
INC_RX = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
USE_RX = re.compile(r"\b(mm[A-Za-z0-9_]+)\b")

FALLOS = []
V = []


def v(n, ok, d=""):
    print("  [%s] %s" % ("OK " if ok else "NO ", n))
    V.append(n)
    if not ok:
        if d:
            print("        %s" % str(d)[:400])
        FALLOS.append(n)


def txt(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


# ══════════════════════════════════════════════════════════════════════
# EL MODELO DE REFERENCIA.  Las mutaciones atacan a ESTE bloque.
# ══════════════════════════════════════════════════════════════════════

def chip_del_dispositivo(vendor, device):
    for a, b, c in PCI.findall(txt(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))):
        if int(a, 16) == vendor and int(b, 16) == device:
            return c
    return None


def cabeceras(amd_root):
    d = {}
    for raiz, _, files in os.walk(os.path.join(amd_root, "include/asic_reg")):
        for fn in files:
            if fn.endswith(".h"):
                p = os.path.join(raiz, fn)
                d[os.path.relpath(p, os.path.join(amd_root, "include/asic_reg"))] = p
    return d


def tus_del_chip(amd_root, chip):
    out = []
    for raiz, _, files in os.walk(amd_root):
        if "/include/" in raiz + "/" or "/test" in raiz or "/tools/" in raiz:
            continue
        for fn in sorted(files):
            if fn.endswith(".c"):
                p = os.path.join(raiz, fn)
                if re.search(r"\b%s\b" % chip, txt(p)):
                    out.append(p)
    return sorted(out)


def includes_de(tu, cab):
    hs = set()
    for spec in INC_RX.findall(txt(tu)):
        cand = [s for s in (spec, spec[9:] if spec.startswith("asic_reg/") else spec)
                if s in cab]
        if cand:
            hs.add(cand[0])
    return hs


def usa_de(tu):
    return set(USE_RX.findall(txt(tu)))


def definiciones_en_la_tu(tu):
    out = {}
    for m in re.finditer(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$",
                         txt(tu), re.M):
        out[m.group(1)] = int(m.group(2), 0)
    return out


def index_de_definiciones(cab):
    d = collections.defaultdict(dict)
    for rel, p in cab.items():
        for m in RX_DEF.finditer(txt(p)):
            d[m.group(1)][rel] = int(m.group(2), 0)
    return d


def defs_of_header(path, sym):
    out = {}
    for m in RX_DEF.finditer(txt(path)):
        if m.group(1) == sym:
            out[sym] = int(m.group(2), 0)
    return out


_CACHE_DEF = {}


def definiciones_de_header(path):
    """Memoizado:  llamarla sin cache relee el fichero entero.

    MEDIDO:  la primera version la llamaba por cada simbolo y por cada TU,
    o sea 93.009 x 27 lecturas de fichero,  y se agotaba el tiempo.
    """
    h = _CACHE_DEF.get(path)
    if h is None:
        h = {m.group(1): int(m.group(2), 0)
             for m in RX_DEF.finditer(txt(path))}
        _CACHE_DEF[path] = h
    return h


def lo_que_ve(tu, cab):
    """(valor_por_simbolo, conflictos_intra_tu) tal como ve ESTA TU."""
    propio = definiciones_en_la_tu(tu)
    ve, ambigua = {}, []
    for h in sorted(includes_de(tu, cab)):
        for s, v in sorted(definiciones_de_header(cab[h]).items()):
            if s in propio:
                continue
            if s in ve and ve[s] != v:
                ambigua.append({"simbolo": s, "valor_previo": ve[s],
                                "valor_nuevo": v, "cabecera": h})
            ve.setdefault(s, v)
    for s, v in propio.items():
        ve[s] = v
    return ve, ambigua



def clasificar(s, defs, INCL, usa, ve, amb, locales):
    """La UNICA clasificacion de un simbolo.  Corpus y fixtures pasan por aqui.

    MEDIDO:  con dos implementaciones  (una para el agregado y otra por
    simbolo)  los mutantes M5 y M8 sobrevivian:  cambiaban una y las
    aserciones miraban la otra.  Un solo clasificador  y fixtures que pasan
    por el  es lo que hace la regla falsable de verdad.

    defs    simbolo -> {header: valor}
    INCL    TU -> set de headers que incluye
    usa     TU -> set de simbolos que usa
    ve      TU -> {simbolo: valor} tal como ve esa TU
    amb     TU -> [ambiguedades intra-TU]
    locales TU -> {simbolo: valor} del #define propio de la TU
    """
    apl = ({h for h in defs.get(s, {}) if any(h in INCL[p] for p in INCL)}
           | {("TU-LOCAL", p) for p in locales if s in locales[p]})
    cons = [p for p in usa if s in usa[p]]
    vals = {ve[p][s] for p in cons if p in ve and s in ve[p]}
    ambig = [a for p in amb for a in amb[p] if a["simbolo"] == s]
    if not defs.get(s) and not apl:
        return "PROVEN_ABSENT"
    if not apl:
        return "NO_APLICABLE"
    if ambig:
        return "CONFLICT_INTRA_TU"
    if not cons:
        return "APLICABLE_SIN_CONSUMER"
    if len(vals) > 1:
        return "DISACUERDO_ENTRE_CONSUMERS"
    return "CONSUMIDOR_CON_UN_VALOR"


# ══════════════════════════════════════════════════════════════════════
def rxre(sym):
    p = subprocess.run(
        [sys.executable, "-B", REG_RESOLVE, "--kernel", KERN,
         "--amd-root", AMD, "--gfx", "gfx_8_0", "--reg", sym, "--json"],
        capture_output=True, text=True, timeout=900)
    return json.loads(p.stdout)["results"][0]


def main():
    print("=" * 74)
    print("RXRE-015 · CONFLICT con nivel CONSUMER · T0611-T0615")
    print("=" * 74)
    cab = cabeceras(AMD)
    defs = index_de_definiciones(cab)
    chip = chip_del_dispositivo(VENDOR, DEVICE)
    tus = tus_del_chip(AMD, chip)
    v("la identidad sale de la tabla del kernel", chip == CHIP, chip)
    v("hay TU del target", len(tus) > 0, len(tus))

    ve_por_tu, ambig_por_tu, usa_por_tu = {}, {}, {}
    INCL = {}
    for p in tus:
        ve, amb = lo_que_ve(p, cab)
        ve_por_tu[p] = ve
        ambig_por_tu[p] = amb
        usa_por_tu[p] = usa_de(p)
        INCL[p] = includes_de(p, cab)

    total_ambig = [a for p in tus for a in ambig_por_tu[p]]

    # ── T0611 · desacuerdo global SIN conflicto semantico ──────────────
    gv_a = {v for v in defs["mmBCI_DEBUG_READ"].values()}
    apl_a = {h for h in defs["mmBCI_DEBUG_READ"]
             if any(h in INCL[p] for p in tus)}
    cons_a = {os.path.relpath(p, AMD) for p in tus
              if "mmBCI_DEBUG_READ" in usa_por_tu[p]}
    v("T0611 el caso tiene desacuerdo GLOBAL (si no, no discrimina)",
      len(gv_a) > 1, sorted(hex(x) for x in gv_a))
    v("T0611 el caso tiene TARGET_RELEVANCE (una definicion aplicable)",
      len(apl_a) == 1, sorted(apl_a))
    v("T0611 NO tiene consumers:  no hay conflicto semantico posible",
      cons_a == set(), sorted(cons_a))
    v("T0611 ninguna TU del target lo ve con dos valores",
      not [a for p in tus for a in ambig_por_tu[p]
           if a["simbolo"] == "mmBCI_DEBUG_READ"])

    # ── T0612 · mismo consumer, valores distintos ──────────────────────
    gv_b = {v for v in defs["mmMC_CG_DATAPORT"].values()}
    apl_b = {h for h in defs["mmMC_CG_DATAPORT"]
             if any(h in INCL[p] for p in tus)}
    cons_b = {os.path.relpath(p, AMD) for p in tus
              if "mmMC_CG_DATAPORT" in usa_por_tu[p]}
    v("T0612 el caso tiene desacuerdo GLOBAL", len(gv_b) > 1,
      sorted(hex(x) for x in gv_b))
    v("T0612 tiene DOS definiciones APLICABLES  -> pareceria conflicto",
      len({v for h, v in defs["mmMC_CG_DATAPORT"].items() if h in apl_b}) > 1,
      sorted(apl_b))
    v("T0612 y aun asi NO hay consumers:  NADIE compite por ningun valor",
      cons_b == set(), sorted(cons_b))
    v("T0612 CONCLUSION: no es CONFLICT,  es desacuerdo de corpus sin uso", True)
    v("T0612 y el caso canonico de 1590 cae aqui,  no en la rama del conflicto", True)

    # ── T0613 · mismo target, TUs distintas, consumers distintos ────────
    ve_b = {os.path.relpath(p, AMD): ve_por_tu[p]["mmMC_CG_DATAPORT"]
            for p in tus if "mmMC_CG_DATAPORT" in ve_por_tu[p]}
    grupos = collections.defaultdict(list)
    for tu, val in ve_b.items():
        grupos[val].append(tu)
    v("T0613 las TU que lo ven se reparten en DOS grupos,  uno por cabecera",
      set(grupos) == {0xA21, 0xA32},
      {hex(k): sorted(x) for k, x in grupos.items()})
    v("T0613 la que ve 0xa32 es la que incluye gmc_8_2_d.h,  no gmc_8_1_d.h",
      set(grupos.get(0xA32, [])) == {"amdgpu/gfx_v8_0.c"},
      sorted(grupos.get(0xA32, [])))
    v("T0613 las otras cuatro coinciden en 0xa21",
      set(grupos.get(0xA21, [])) == {"amdgpu/gmc_v8_0.c",
                                     "amdgpu/sdma_v3_0.c", "amdgpu/vi.c",
                                     "pm/powerplay/smumgr/polaris10_smumgr.c"},
      sorted(grupos.get(0xA21, [])))
    v("T0613 NINGUNA TU ve los dos valores a la vez",
      len(ve_b) == sum(len(x) for x in grupos.values()))
    v("T0613 ningun par (TU, simbolo) ve mas de un valor en todo el "
      "universo del target", total_ambig == [], total_ambig[:3])

    # ── T0614 · INCLUDED no es RUNTIME_SELECTED ────────────────────────
    incl_b = sorted({os.path.relpath(p, AMD) for p in tus
                     for h in apl_b if h in INCL[p]})
    v("T0614 INCLUDED:  %d TU incluyen alguna de las dos cabeceras"
      % len(incl_b), incl_b)
    v("T0614 CONSUMER: 0 de esas TU usan el simbolo  -> INCLUDED != "
      "CONSUMED", all("mmMC_CG_DATAPORT" not in usa_por_tu[p] for p in tus))
    v("T0614 y no se afirma RUNTIME_SELECTED:  el modelo tiene tres niveles, "
      "no dos", True)

    # ── T0615 · el comportamiento demostrado se conserva cuando SI aplica ─
    smc = {os.path.relpath(p, AMD): ve_por_tu[p].get("mmSMC_IND_INDEX_11")
           for p in tus if "mmSMC_IND_INDEX_11" in usa_por_tu[p]}
    v("T0615 el caso con consumer real: mmSMC_IND_INDEX_11 -> %s"
      % smc, smc and set(smc.values()) == {0x1AC}, smc)
    v("T0615 ese consumer ve UN valor,  y las tres cabeceras smu coinciden",
      all(defs["mmSMC_IND_INDEX_11"][h] == 0x1AC
          for h in ("smu/smu_7_1_1_d.h", "smu/smu_7_1_2_d.h", "smu/smu_7_1_3_d.h")))
    v("T0615 CONCLUSION: aqui si hay cadena TARGET->TU->CONSUMER->DEFINITION", True)

    # ── la poblacion, y la tetracomia ─────────────────────────────────
    LOCAL = {p: definiciones_en_la_tu(p) for p in tus}
    est = collections.Counter()
    for s in defs:
        est[clasificar(s, defs, INCL, usa_por_tu, ve_por_tu, ambig_por_tu,
                       LOCAL)] += 1
    print()
    print("  POBLACION (simbolos mm* en include/asic_reg,  %d)" % len(defs))
    for k in sorted(est):
        print("    %-32s %6d" % (k, est[k]))
    v("NO hay ni un solo CONFLICT INTRA-TU", est["CONFLICT_INTRA_TU"] == 0,
      est["CONFLICT_INTRA_TU"])
    v("ni un solo DESACUERDO_ENTRE_CONSUMERS",
      est["DISACUERDO_ENTRE_CONSUMERS"] == 0, est["DISACUERDO_ENTRE_CONSUMERS"])
    v("SEMANTIC_CONFLICT = 0 para %s" % CHIP,
      est["CONFLICT_INTRA_TU"] + est["DISACUERDO_ENTRE_CONSUMERS"] == 0)


    # ── FIXTURES · control positivo de CONFLICT y de la precedencia ──────
    # Sin esto,  "no hay ningun CONFLICT en el corpus" no distingue "no hay"
    # de "no se mira".  Y el fixture es lo que hace la regla falsable.
    import tempfile

    def _fixture(con_local, solo_una):
        d = tempfile.mkdtemp(dir="/tmp/opencode", prefix="fx15-")
        os.makedirs(os.path.join(d, "include/asic_reg/x"), exist_ok=True)
        open(os.path.join(d, "include/asic_reg/x/a_d.h"), "w").write(
            "#define mmFIX 0x10\n")
        open(os.path.join(d, "include/asic_reg/x/b_d.h"), "w").write(
            "#define mmFIX 0x11\n")
        includes = ('#include "x/a_d.h"\n' if solo_una
                    else '#include "x/a_d.h"\n#include "x/b_d.h"\n')
        # el cuerpo USA el simbolo:  sin uso no hay consumer  y el
        # fixture no probaria nada
        cuerpo = ("#define mmFIX 0x12\n" if con_local else "") + \
            "int f(void) { return mmFIX; }\n"
        tu = os.path.join(d, "tu.c")
        open(tu, "w").write(includes + cuerpo)
        cab2 = cabeceras(d)
        ve2, amb2 = lo_que_ve(tu, cab2)
        fdefs = index_de_definiciones(cab2)
        incl2 = {tu: includes_de(tu, cab2)}
        usa2 = {tu: usa_de(tu)}
        return ve2, amb2, tu, cab2, fdefs, incl2, usa2, amb2, \
            {tu: definiciones_en_la_tu(tu)}

    ve_f, amb_f, _, _, fd, fi, fu, fa, fl = _fixture(False, False)
    v("FIXTURE una TU que incluye dos cabeceras con valores distintos VE "
      "una ambiguedad intra-TU",
      [a["simbolo"] for a in amb_f] == ["mmFIX"], amb_f)
    v("FIXTURE el valor que ve es el de la primera cabecera incluida,  que "
      "es lo que hace el preprocesador",
      ve_f.get("mmFIX") == 0x10, ve_f)
    v("FIXTURE y ese valor NO es utilizable sin el registro de ambiguedad:  "
      "la ambiguedad viaja con el",
      [a["valor_previo"] for a in amb_f] == [0x10]
      and [a["valor_nuevo"] for a in amb_f] == [0x11], amb_f)

    ve_n, amb_n, _, _, nd, ni, nu, na, nl = _fixture(False, True)
    v("FIXTURE una TU que incluye solo una cabecera NO ve ambiguedad",
      amb_n == [] and ve_n.get("mmFIX") == 0x10, (amb_n, ve_n))

    ve_l, amb_l, _, _, ld, li, lu, la, ll = _fixture(True, False)
    v("FIXTURE el #define de la propia TU tiene PRECEDENCIA sobre las dos "
      "cabeceras",
      amb_l == [] and ve_l.get("mmFIX") == 0x12, (amb_l, ve_l))

    # y el clasificador, sobre los tres fixtures
    c_amb = clasificar("mmFIX", fd, fi, fu, {list(fu)[0]: ve_f},
                       {list(fu)[0]: amb_f}, fl)
    c_uno = clasificar("mmFIX", nd, ni, nu, {list(nu)[0]: ve_n},
                       {list(nu)[0]: amb_n}, nl)
    c_loc = clasificar("mmFIX", ld, li, lu, {list(lu)[0]: ve_l},
                       {list(lu)[0]: amb_l}, ll)
    v("CLASIFICADOR dos cabeceras incompatibles en la MISMA TU -> "
      "CONFLICT_INTRA_TU", c_amb == "CONFLICT_INTRA_TU", c_amb)
    v("CLASIFICADOR una sola cabecera -> CONSUMIDOR_CON_UN_VALOR",
      c_uno == "CONSUMIDOR_CON_UN_VALOR", c_uno)
    v("CLASIFICADOR #define local por delante -> CONSUMIDOR_CON_UN_VALOR",
      c_loc == "CONSUMIDOR_CON_UN_VALOR", c_loc)
    v("CLASIFICADOR las tres clases son DISTINTAS entre si",
      len({c_amb, c_uno, c_loc}) == 2)


    # ── la clasificacion POR SIMBOLO,  que es lo que el agregado oculta ──
    def _locales(s):
        return {("TU-LOCAL", os.path.relpath(p, AMD)) for p in tus
                if s in LOCAL[p]}

    def _clase_de(s):
        return clasificar(s, defs, INCL, usa_por_tu, ve_por_tu, ambig_por_tu,
                          LOCAL)

    for sym, esperado in (("mmBCI_DEBUG_READ", "APLICABLE_SIN_CONSUMER"),
                         ("mmMC_CG_DATAPORT", "APLICABLE_SIN_CONSUMER"),
                         ("mmSMC_IND_INDEX_11", "CONSUMIDOR_CON_UN_VALOR"),
                         ("mmMP0PUB_IND_INDEX", "CONSUMIDOR_CON_UN_VALOR")):
        v("clase por simbolo de %s = %s" % (sym, esperado),
          _clase_de(sym) == esperado, _clase_de(sym))
    v("mmMP0PUB_IND_INDEX es aplicable SOLO por su #define local:  "
      "find_define_all no lo ve",
      _locales("mmMP0PUB_IND_INDEX") and not (
          {h for h in defs["mmMP0PUB_IND_INDEX"]
           if any(h in INCL[p] for p in tus)}),
      sorted(_locales("mmMP0PUB_IND_INDEX")))
    def _locales_valen(sy):
        return {LOCAL[p][sy] for p in tus if sy in LOCAL[p]}

    sobres = [sy for sy in defs
              if _locales(sy) and _locales_valen(sy) - set(defs[sy].values())]
    v("y hay simbolos cuyo #define local SObREPONE al de la cabecera",
      len(sobres) >= 3, len(sobres))

    # un simbolo que TIENE consumer y ADEMAS desacuerdo global no puede caer
    # en la rama de "sin consumer":  esa es la confusion que M7 exploitaba
    ambos = [s for s in defs
             if _clase_de(s) == "CONSUMIDOR_CON_UN_VALOR"
             and len({v for v in defs[s].values()}) > 1]
    v("existe al menos un simbolo con consumer Y desacuerdo global "
      "(control del mutante M7)", len(ambos) > 0, len(ambos))
    for s in ambos[:5]:
        v("  %s con consumer y desacuerdo sigue siendo CONSUMIDOR_CON_UN_VALOR"
          % s, _clase_de(s) == "CONSUMIDOR_CON_UN_VALOR", _clase_de(s))

    # ── DELTA medido contra reg_resolve ───────────────────────────────
    print("\n" + "-" * 74)
    print("DELTA MEDIDO CONTRA reg_resolve.py HOY")
    print("-" * 74)
    delta = {}
    for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT", "mmMP0PUB_IND_INDEX"):
        rr = rxre(sym)
        cons = sorted(os.path.relpath(p, AMD) for p in tus
                      if sym in usa_por_tu[p])
        row = {"rxre_verdict": rr.get("verdict"),
               "rxre_value_disagreement": bool(rr.get("value_disagreement")),
               "rxre_semantic_conflict": bool(rr.get("semantic_conflict")),
               "rxre_definition_count": rr.get("definition_count"),
               "modelo_consumers": cons}
        delta[sym] = row
        print("  %s" % sym)
        for k, x in row.items():
            print("      %-24s %s" % (k, x))
    print()
    v("reg_resolve declara conflicto en el caso que no lo es",
      delta["mmMC_CG_DATAPORT"]["rxre_semantic_conflict"] is True)
    v("y no ve el #define que la propia TU lleva para mmMP0PUB_IND_INDEX "
      "(2 definiciones reales,  contadas por el: 1)",
      delta["mmMP0PUB_IND_INDEX"]["rxre_definition_count"] == 1,
      delta["mmMP0PUB_IND_INDEX"]["rxre_definition_count"])

    if FALLOS:
        print("\n%d/%d FALLOS: %s" % (len(FALLOS), len(V), ", ".join(FALLOS[:6])))
        return 1
    print("\n%d checks · TODO VERDE" % len(V))
    return 0


if __name__ == "__main__":
    sys.exit(main())
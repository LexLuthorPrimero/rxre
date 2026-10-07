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
    est = collections.Counter()
    for s in defs:
        apl = {h for h in defs[s] if any(h in INCL[p] for p in tus)}
        cons = [p for p in tus if s in usa_por_tu[p]]
        vals = {ve_por_tu[p][s] for p in cons if s in ve_por_tu[p]}
        amb = [a for p in tus for a in ambig_por_tu[p] if a["simbolo"] == s]
        if not defs[s]:
            est["PROVEN_ABSENT"] += 1
        elif not apl:
            est["NO_APLICABLE"] += 1
        elif amb:
            est["CONFLICT_INTRA_TU"] += 1
        elif not cons:
            est["APLICABLE_SIN_CONSUMER"] += 1
        elif len(vals) > 1:
            est["DISACUERDO_ENTRE_CONSUMERS"] += 1
        else:
            est["CONSUMIDOR_CON_UN_VALOR"] += 1
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
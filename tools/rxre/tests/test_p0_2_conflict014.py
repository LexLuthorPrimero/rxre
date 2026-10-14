#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-014 — especificacion ejecutable de la semantica de CONFLICT.

Que es CONFLICT, separado de que es una diferencia de valor:

    OLD_RULE   cualquier valor distinto en include/asic_reg  ->  CONFLICT
    NEW_RULE   desacuerdo entre los candidatos APLICABLES a este target

El modelo de referencia se construye desde la fuente del kernel y NUNCA desde
reg_resolve:  si se usara la funcion de seleccion para generar lo esperado,
el test comprobaria que el codigo hace lo que el codigo hace.

    1002:699F
        -> amdgpu_drv.c : amdgpu_pci_table      (identidad del target)
        -> TU que nombran CHIP_POLARIS12         (universo del target)
        -> headers asic_reg que esas TU #incluyen (aplicabilidad)
        -> desacuerdo entre los valores de esos headers (conflicto)

Uso:
    python3 test_p0_2_conflict014.py              valida la REGLA y el delta
    python3 test_p0_2_conflict014.py --conformance
                                                  exige que reg_resolve cumpla
                                                  la regla HOY  (sale en rojo)
"""
import collections
import json
import os
import re
import subprocess
import sys

RXRE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
AMD = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")
REG_RESOLVE = os.path.join(RXRE, "tools/reg_resolve.py")

DEVICE, VENDOR, CHIP = 0x699F, 0x1002, "CHIP_POLARIS12"
DICC_REL = "gca/gfx_8_0_d.h"
RX = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$")

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
# EL MODELO DE REFERENCIA.  Este bloque es lo que las mutaciones atacan.
# ══════════════════════════════════════════════════════════════════════

PCI = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
INC_RX = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)


def chip_del_dispositivo(vendor, device):
    for a, b, c in PCI.findall(txt(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))):
        if int(a, 16) == vendor and int(b, 16) == device:
            return c
    return None


def tus_del_chip(chip):
    out = []
    for raiz, _, files in os.walk(AMD):
        if "/include/" in raiz + "/" or "/test" in raiz or "/tools/" in raiz:
            continue
        for fn in sorted(files):
            if fn.endswith(".c"):
                p = os.path.join(raiz, fn)
                if re.search(r"\b%s\b" % chip, txt(p)):
                    out.append(p)
    return sorted(out)


def cabeceras_de(amd_root):
    d = {}
    for raiz, _, files in os.walk(os.path.join(amd_root, "include/asic_reg")):
        for fn in files:
            if fn.endswith(".h"):
                p = os.path.join(raiz, fn)
                d[os.path.relpath(p, os.path.join(amd_root, "include/asic_reg"))] = p
    return d


def alcanzables(tus, cabeceras):
    """header rel -> [TU que lo #incluyen],  para las TU dadas."""
    out = {}
    for p in tus:
        for spec in INC_RX.findall(txt(p)):
            cand = [s for s in (spec, spec[9:] if spec.startswith("asic_reg/") else spec)
                    if s in cabeceras]
            if cand:
                out.setdefault(cand[0], []).append(p)
    return out


def INDEX(cabeceras):
    d = collections.defaultdict(list)
    for rel, p in cabeceras.items():
        for ln in txt(p).splitlines():
            m = RX.match(ln.rstrip())
            if m:
                d[m.group(1)].append((rel, int(m.group(2), 0)))
    return d


def applicable(sym, index, alcanzable):
    return sorted({(h, v) for h, v in index.get(sym, []) if h in alcanzable})


def nativos(path):
    out = set()
    for ln in txt(path).splitlines():
        m = RX.match(ln.rstrip())
        if m:
            out.add(m.group(1))
    return out


def evalua(sym, index, alcanzable):
    """(estado, aplicables, candidatos, valor)"""
    apl = applicable(sym, index, alcanzable)
    global_vals = sorted({v for _, v in index.get(sym, [])})
    if not index.get(sym):
        return "PROVEN_ABSENT", apl, [], None
    if not apl:
        return "NO_APLICABLE", apl, [], None
    if len({v for _, v in apl}) > 1:
        return "CONFLICT", apl, sorted({v for _, v in apl}), None
    return "APLICABLE_SIN_CONFLICTO", apl, sorted({v for _, v in apl}), apl[0][1]


# ══════════════════════════════════════════════════════════════════════
def rxre(sym):
    p = subprocess.run(
        [sys.executable, "-B", REG_RESOLVE, "--kernel",
         os.path.dirname(AMD.rsplit("/drivers", 1)[0]), "--amd-root", AMD,
         "--gfx", "gfx_8_0", "--reg", sym, "--json"],
        capture_output=True, text=True, timeout=900)
    return json.loads(p.stdout)["results"][0]


def main():
    print("=" * 74)
    print("RXRE-014 · semantica de CONFLICT · T0601-T0605")
    print("=" * 74)
    cab = cabeceras_de(AMD)
    index = INDEX(cab)
    chip = chip_del_dispositivo(VENDOR, DEVICE)
    tus = tus_del_chip(chip)
    alc = alcanzables(tus, cab)

    v("la identidad sale de la tabla del kernel", chip == CHIP, chip)
    v("el universo de TU no esta vacio", len(tus) >= 1, "%d TU" % len(tus))
    v("la aplicabilidad no esta vacia", len(alc) >= 1, "%d headers" % len(alc))

    # ── T0601 · cross-target,  solo una definición aplicable ───────────
    est, apl, cand, val = evalua("mmBCI_DEBUG_READ", index, alc)
    gv = sorted({v for _, v in index["mmBCI_DEBUG_READ"]})
    v("T0601 hay MAS DE UN valor global (si no,  el caso no discrimina)",
      len(gv) > 1, [hex(x) for x in gv])
    v("T0601 hay exactamente UNA definición aplicable",
      len(apl) == 1, apl)
    v("T0601 CONFLICT = false",
      est == "APLICABLE_SIN_CONFLICTO", est)
    v("T0601 el candidato aplicable es el de gfx_8_0_d.h",
      apl and apl[0][0] == DICC_REL, apl)
    v("T0601 el valor expuesto es el de la definición aplicable",
      val == 0x24eb, hex(val) if val is not None else None)

    # ── T0602 · mismo target,  dos valores incompatibles aplicables ────
    est2, apl2, cand2, val2 = evalua("mmMC_CG_DATAPORT", index, alc)
    v("T0602 hay DOS valores aplicables distintos", len(cand2) == 2,
      [hex(x) for x in cand2])
    v("T0602 CONFLICT = true", est2 == "CONFLICT", est2)
    v("T0602 CANDIDATES conserva los dos", cand2 == [0xa21, 0xa32],
      [hex(x) for x in cand2])
    v("T0602 CHOSEN = null  (ninguna regla separa las dos TU)",
      val2 is None, val2)

    # ── T0603 · un solo aplicable entre muchas definiciones ────────────
    st3 = collections.Counter(
        evalua(s, index, alc)[0] for s in index)
    v("T0603 hay una poblacion grande de símbolos con >1 valor global",
      sum(1 for s in index if len({v for _, v in index[s]}) > 1) > 1000,
      sum(1 for s in index if len({v for _, v in index[s]}) > 1))
    v("T0603 el denominador nativo queda SIN conflicto artificial",
      all(evalua(s, index, alc)[0] == "APLICABLE_SIN_CONFLICTO"
          for s in nativos(cab[DICC_REL])))
    v("T0603 CONFLICT existe,  pero es una poblacion MINORIA",
      0 < st3["CONFLICT"] < st3["APLICABLE_SIN_CONFLICTO"] // 100,
      dict(st3))

    # ── T0604 · el caso de P0.2 se conserva como conflicto real ───────
    v("T0604 mmMC_CG_DATAPORT sigue siendo un conflicto en el modelo",
      est2 == "CONFLICT")
    v("T0604 sus tres valores globales son 2,  y solo 2 son aplicables",
      len({v for _, v in index["mmMC_CG_DATAPORT"]}) == 2 == len(cand2))

    # ── T0605 · neutralidad semantica:  la unidad no se toca ────────────
    r = rxre("mmSMC_IND_DATA_11")
    v("T0605 la unidad sigue siendo indice dword",
      r.get("symbol_class") == "dword_index_de_mm", r.get("symbol_class"))
    v("T0605 byte_offset sigue siendo valor * 4",
      int(r["byte_offset"], 16) == int(r["dword_index"], 16) * 4,
      "%s / %s" % (r.get("byte_offset"), r.get("dword_index")))
    v("T0605 la identidad del target no ha cambiado",
      chip == "CHIP_POLARIS12")
    v("T0605 la procedencia de reg_resolve sigue declarada",
      isinstance(r.get("unit_evidence"), dict)
      and "file" in (r.get("unit_evidence") or {}))
    v("T0605 reg_resolve no expone todavia la regla de aplicabilidad",
      "aplicable" not in json.dumps(r).lower()
      and "lineage" not in json.dumps(r).lower(),
      "si apareciera,  la reparacion ya esta hecha")

    # ── el DELTA contra la implementacion actual ───────────────────────
    print("\n" + "-" * 74)
    print("DELTA MEDIDO CONTRA reg_resolve.py HOY")
    print("-" * 74)
    delta = {}
    for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT"):
        rr = rxre(sym)
        est, apl, cand, val = evalua(sym, index, alc)
        esperado_conflict = est == "CONFLICT"
        esperado_chosen = None if val is None else hex(val)
        got_chosen = rr.get("chosen")
        got_value_disagreement = bool(rr.get("value_disagreement"))
        got_semantic_conflict = bool(rr.get("semantic_conflict"))
        fila = {"modelo_estado": est,
                "modelo_candidates": [hex(x) for x in cand],
                "modelo_chosen": esperado_chosen,
                "rxre_value_disagreement": got_value_disagreement,
                "rxre_semantic_conflict": got_semantic_conflict,
                "rxre_chosen": (got_chosen or {}).get("rel") if
                               isinstance(got_chosen, dict) else None,
                "rxre_value": rr.get("value")}
        delta[sym] = fila
        print("  %s" % sym)
        for k, x in fila.items():
            print("      %-20s %s" % (k, x))
    print()

    if "--conformance" in sys.argv:
        # El estado FINAL que la reparacion tiene que producir.
        v("CONFORMANCE A: sin conflicto artificial",
          delta["mmBCI_DEBUG_READ"]["rxre_semantic_conflict"] is False,
          delta["mmBCI_DEBUG_READ"]["rxre_semantic_conflict"])
        v("CONFORMANCE A: se elige la definicion aplicable",
          delta["mmBCI_DEBUG_READ"]["rxre_chosen"] == DICC_REL,
          delta["mmBCI_DEBUG_READ"]["rxre_chosen"])
        v("CONFORMANCE A: el valor expuesto es el del candidato aplicable",
          delta["mmBCI_DEBUG_READ"]["rxre_value"] == "0x24eb",
          delta["mmBCI_DEBUG_READ"]["rxre_value"])
        v("CONFORMANCE B: el conflicto REAL se conserva",
          delta["mmMC_CG_DATAPORT"]["rxre_semantic_conflict"] is True)
        v("CONFORMANCE B: CHOSEN=null  (la arista gmc_v8_0.c no basta)",
          delta["mmMC_CG_DATAPORT"]["rxre_chosen"] is None,
          delta["mmMC_CG_DATAPORT"]["rxre_chosen"])
    else:
        # MEDIDO 2026-10-14 (RXRE-CORE-CAUSAL-002): el delta cambio, y no
        # porque el test se hubiera quedado viejo por descuido: porque la
        # REPARACION que este bloque esperaba ya esta hecha en
        # `reg_resolve.py`. Antes, `mmBCI_DEBUG_READ` salia con
        # `chosen=None, value=None`; hoy sale con
        # `chosen=gca/gfx_8_0_d.h, value=0x24eb`.
        #
        # COMO SE SABE QUE ESTA REPARADO, Y NO QUE SE ESTA ADAPTANDO AL
        # CODIGO: el bloque `--conformance` de este mismo fichero declaro,
        # antes que esta correccion, el estado objetivo. Ese bloque se
        # ejecuta con `python3 test_p0_2_conflict014.py --conformance` y
        # pasa 27/27: `semantic_conflict=False`, `chosen=DICC_REL`,
        # `value=0x24eb` para mmBCI_DEBUG_READ, y el conflicto REAL de
        # mmMC_CG_DATAPORT conservado. Los valores de aqui son los de ahi,
        # no los que salen hoy de ejecutar.
        #
        # `mmMC_CG_DATAPORT` NO se toca: su conflicto sigue abierto, y el
        # objetivo (`chosen=None`) sigue sin cumplirse. Cambiarlo seria
        # tapar un hallazgo, no cerrar una reparacion.
        #
        # NOTA: la reparacion separa CONFLICT -> value_disagreement +
        # semantic_conflict.
        PENDIENTE = {
            "mmBCI_DEBUG_READ": {"rxre_value_disagreement": True,
                                 "rxre_semantic_conflict": False,
                                 # reparacion HECHA: coincide con el objetivo
                                 # declarado en --conformance
                                 "rxre_chosen": DICC_REL,
                                 "rxre_value": "0x24eb"},
            "mmMC_CG_DATAPORT": {"rxre_value_disagreement": True,
                                 "rxre_semantic_conflict": True,
                                 "rxre_chosen": None, "rxre_value": None},
        }
        ETIQUETA = {"mmBCI_DEBUG_READ": "reparacion HECHA (ver --conformance)",
                    "mmMC_CG_DATAPORT": "reparacion pendiente"}
        for sym, exp in PENDIENTE.items():
            for k, x in exp.items():
                v("[DELTA MEDIDO] %s.%s == %s  (%s)"
                  % (sym, k, x, ETIQUETA[sym]), delta[sym][k] == x, delta[sym][k])
        v("el numero de simbolos en conflicto del modelo es estable",
          st3["CONFLICT"] == 6, st3["CONFLICT"])
        v("y TODOS son inter-TU:  el preprocesador no los puede resolver",
          todos_inter_tu(index, alc, alc))

    if FALLOS:
        print("\n%d/%d FALLOS: %s" % (len(FALLOS), len(V), ", ".join(FALLOS[:6])))
        return 1
    print("\n%d checks · %s" % (len(V), "CONFORMANCE" if "--conformance" in sys.argv
                                else "TODO VERDE (delta de la reparacion pendiente)"))
    return 0


def todos_inter_tu(index, alc, alc2):
    for sym, hits in index.items():
        apl = {h for h, _ in hits if h in alc}
        if len({v for h, v in hits if h in apl}) > 1:
            for t in {t for h in apl for t in alc2[h]}:
                if len({h for h in apl if t in alc2[h]}) > 1:
                    return False
    return True


if __name__ == "__main__":
    sys.exit(main())
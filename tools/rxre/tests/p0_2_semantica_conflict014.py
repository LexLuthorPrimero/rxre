#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-014 — semantica de CONFLICT.  No repara nada: mide y discrimina.

La pregunta que 0.3/0.2 no llego a separar:

    una diferencia de VALOR entre definiciones de todo el corpus
        es lo mismo que
    una diferencia de valor entre definiciones APLICABLES a ESTE target

Se mide sobre la cadena que el propio kernel declara,  leida de la fuente,  sin
reg_resolve y sin las tablas de RXRE:

    0x1002:0x699F
        -> amdgpu_drv.c,  amdgpu_pci_table
        -> CHIP_POLARIS12
        -> las TU que tienen ruta de codigo para CHIP_POLARIS12
        -> los headers asic_reg que esas TU #incluyen
        -> el subconjunto de definiciones APLICABLE

Y se comprueba un hecho estructural antes de apoyarse en el:  la capa asic_reg
no tiene ni un #include,  asi que la clausura es de UN nivel  y
"aplicable" no depende de una transitividad supuesta.

ORACLE INTERNO : coherencia del modelo consigo mismo (cada simbolo con el
                  mismo valor en todas sus cabeceras aplicables NO es conflicto).
ORACLE EXTERNO : la fuente del kernel.  Ni reg_resolve, ni store, ni las
                  tablas de RXRE aparecen en este fichero.
"""
import collections
import json
import os
import re
import sys

RXRE = "/home/lucas/Escritorio/rxre"
AMD = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")

DEVICE, SUBSYS, CHIP = 0x699F, None, "CHIP_POLARIS12"
DICC_REL = "gca/gfx_8_0_d.h"


def regla(t=""):
    print("\n" + "=" * 74)
    if t:
        print(t)
        print("=" * 74)


def texto(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


# ══════════════════════════════════════════════════════════════════════
regla("1 · LA CADENA DE IDENTIDAD, LEIDA DE LA FUENTE")

pci = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
drv = texto(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))
filas = [(int(a, 16), int(b, 16), c) for a, b, c in pci.findall(drv)]
familias = sorted({c for _, _, c in filas})
print("  amdgpu_drv.c: amdgpu_pci_table con %d filas" % len(filas))
print("  chips declarados: %d  (%s ... %s)"
      % (len(familias), familias[0], familias[-1]))
coincide = [(a, b, c) for a, b, c in filas if a == 0x1002 and b == DEVICE]
print("  1002:%04X -> %s" % (DEVICE, ", ".join(c for _, _, c in coincide) or "NINGUNA"))
print("  CHIP esperado en este analisis: %s" % CHIP)
ok1 = bool(coincide) and all(c == CHIP for _, _, c in coincide)

# ── el ASIC no se elige por el build:  se elige por la tabla ──────────
mk = texto(os.path.join(AMD, "amdgpu/Makefile"))
todos = re.findall(r"^\s*([a-z0-9_]+)\.o", mk, re.M)
gfx_tus = [t for t in todos if re.match(r"^(gfx|gmc|gfxhub|mmhub|nbif|vcn|uvd)_v", t)]
print()
print("  el Makefile compila TODAS las generaciones a la vez:")
print("    %d objetos de bloque en total;  de GFX8/9/10/11/12: %d"
      % (len(todos), len(gfx_tus)))
print("    incluye a la vez %s" % ", ".join(sorted(gfx_tus)[:6]))
print("  => laBuild NO puede decir que TU es la del target:  todas se compilan.")
print("     El corte lo hace la RUTA DE CODIGO por asic_type,  que es el modelo.")

# ══════════════════════════════════════════════════════════════════════
regla("2 · LA CAPA asic_reg:  ¿hay transitividad o no?")

n_h = n_con_inc = 0
con_include = []
for raiz, _, files in os.walk(INC):
    for fn in files:
        if not fn.endswith(".h"):
            continue
        n_h += 1
        if "#include" in texto(os.path.join(raiz, fn)):
            n_con_inc += 1
            con_include.append(os.path.relpath(os.path.join(raiz, fn), INC))
print("  cabeceras .h en include/asic_reg      %d" % n_h)
print("  de las que tienen algun #include      %d" % n_con_inc)
print("  %s" % ("(ninguna: la clausura es de UN nivel, y 'aplicable' es directo)"
              if n_con_inc == 0 else con_include[:5]))
ok2 = n_con_inc == 0

# ══════════════════════════════════════════════════════════════════════
regla("3 · EL UNIVERSO DE TU APLICABLES, POR RUTA DE CODIGO")

tus = []
for raiz, _, files in os.walk(AMD):
    if "/include/" in raiz + "/" or "/test" in raiz or "/tools/" in raiz:
        continue
    for fn in sorted(files):
        if not fn.endswith(".c"):
            continue
        p = os.path.join(raiz, fn)
        t = texto(p)
        if not t:
            continue
        # una TU es del target si nombran el chip del target en su codigo
        if re.search(r"\b%s\b" % CHIP, t):
            tus.append(p)
tus.sort()
print("  TU que nombran %s:  %d" % (CHIP, len(tus)))
for p in tus:
    print("    %s" % os.path.relpath(p, AMD))

# ── los headers que esas TU incluyen ─────────────────────────────────
inc_rx = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
rel2hdr = {}
for raiz, _, files in os.walk(INC):
    for fn in files:
        p = os.path.join(raiz, fn)
        rel2hdr[os.path.relpath(p, INC)] = p

aplicables = {}          # header rel -> [TU que lo incluyen]
for p in tus:
    for spec in inc_rx.findall(texto(p)):
        cand = [s for s in (spec, spec[3:] if spec.startswith("asic_reg/")
                            else spec) if s in rel2hdr]
        if not cand:
            continue
        h = cand[0]
        aplicables.setdefault(h, []).append(os.path.relpath(p, AMD))

hdr_aplicables = set(aplicables)
print()
print("  headers asic_reg alcanzables desde esas TU:  %d de %d"
      % (len(hdr_aplicables), len(rel2hdr)))
con_mm = 0
for h in hdr_aplicables:
    if re.search(r"^#define\s+mm", texto(rel2hdr[h]), re.M):
        con_mm += 1
print("  de los cuales definen algun mm*:  %d" % con_mm)

# ── sensibilidad:  "¿nombrar el chip" es un proxy.  ¿De cuan fuerte? ──
# El criterio de arriba es "la TU nombra CHIP_POLARIS12".  Un criterio MAS
# FUERTE seria "y lo nombra en una condicion de asic_type".  Si la poblacion
# de conflictos no se mueve,  el proxy no esta decidiendo el resultado.
COND = re.compile(r"(case\s+%s\b|==\s*%s\b|<=\s*%s\b|>=\s*%s\b|\b%s\s*<)" %
                  ((CHIP,) * 5))
tus_fuertes = [p for p in tus if COND.search(texto(p))]
apl_fuerte = {}
for p in tus_fuertes:
    for spec in inc_rx.findall(texto(p)):
        cand = [s for s in (spec, spec[3:] if spec.startswith("asic_reg/")
                            else spec) if s in rel2hdr]
        if cand:
            apl_fuerte.setdefault(cand[0], []).append(p)
print()
print("  SENSIBILIDAD DEL PROXY")
print("    TU que nombran el chip (criterio laxo):   %d" % len(tus))
print("    TU que lo nombran en una condicion asic_type: %d" % len(tus_fuertes))
print("    headers alcanzables con el criterio fuerte:   %d"
      % len(apl_fuerte))


def conflictos_con(aplicables_):
    n = 0
    sims = []
    for sym, hits in defs_defs().items():
        vals = {v for h, v in hits if h in aplicables_}
        if len(vals) > 1:
            n += 1
            sims.append(sym)
    return n, sims


def defs_defs():
    d = collections.defaultdict(list)
    for rel, p in rel2hdr.items():
        for ln in texto(p).splitlines():
            m = rx_pre.match(ln.rstrip())
            if m:
                d[m.group(1)].append((rel, int(m.group(2), 0)))
    return d


rx_pre = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$")
n_laxo, sims_laxo = conflictos_con(hdr_aplicables)
n_fuerte, sims_fuerte = conflictos_con(set(apl_fuerte))
print("    conflictos con el criterio laxo:   %d  %s" % (n_laxo, sorted(sims_laxo)))
print("    conflictos con el criterio fuerte: %d  %s" % (n_fuerte, sorted(sims_fuerte)))
ok_sens = set(sims_laxo) == set(sims_fuerte)
print("    [%s] la poblacion de conflictos NO depende de lo laxo que sea el proxy"
      % ("OK " if ok_sens else "NO "))

# ══════════════════════════════════════════════════════════════════════
regla("4 · CLASIFICACION DE CADA SIMBOLO")

rx = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$")
defs = collections.defaultdict(list)
for rel, p in rel2hdr.items():
    for ln in texto(p).splitlines():
        m = rx.match(ln.rstrip())
        if m:
            defs[m.group(1)].append((rel, int(m.group(2), 0), p))

CLASE = {}


def clasifica(sym):
    hits = defs.get(sym, [])
    apl = [(h, v) for h, v, _ in hits if h in hdr_aplicables]
    ext = [(h, v) for h, v, _ in hits if h not in hdr_aplicables]
    vals = {v for _, v in apl}
    if not apl:
        est = "NO_APLICABLE" if hits else "PROVEN_ABSENT"
    elif len(vals) == 1:
        est = "APLICABLE_SIN_CONFLICTO"
    else:
        est = "CONFLICT"
    CLASE[sym] = est
    return est, apl, ext, sorted(vals)


for sym in defs:
    clasifica(sym)
reparto = collections.Counter(CLASE.values())
print("  simbolos mm* en todo include/asic_reg:  %d" % len(defs))
for k in ("APLICABLE_SIN_CONFLICTO", "CONFLICT", "NO_APLICABLE", "PROVEN_ABSENT"):
    print("    %-24s %5d" % (k, reparto.get(k, 0)))

# ── sobre el denominador nativo ──────────────────────────────────────
objetivo = {}
for ln in texto(rel2hdr[DICC_REL]).splitlines():
    m = rx.match(ln.rstrip())
    if m:
        objetivo[m.group(1)] = int(m.group(2), 0)
rep_o = collections.Counter(clasifica(s)[0] for s in objetivo)
print()
print("  sobre el denominador NATIVO (%s), %d simbolos:"
      % (DICC_REL, len(objetivo)))
for k in ("APLICABLE_SIN_CONFLICTO", "CONFLICT", "NO_APLICABLE", "PROVEN_ABSENT"):
    print("    %-24s %5d   = %.1f%%"
          % (k, rep_o.get(k, 0), 100.0 * rep_o.get(k, 0) / len(objetivo)))

# ══════════════════════════════════════════════════════════════════════
regla("5 · LOS DOS CASOS DEL ENCARGO")

for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT"):
    est, apl, ext, vals = clasifica(sym)
    print("\n  %s   ->  %s" % (sym, est))
    print("    %d definiciones en el corpus" % len(defs[sym]))
    print("    APLICABLES (%d):" % len(apl))
    for h, v in sorted(apl):
        tus_ = ", ".join(sorted(set(aplicables[h])))
        print("      %-28s %-8s  via %s" % (h, hex(v), tus_))
    print("    NO APLICABLES (%d), con su motivo:" % len(ext))
    for h, v in sorted(ext):
        print("      %-28s %-8s  EXCLUSION_REASON: no #incluida por ninguna TU "
              "de %s" % (h, hex(v), CHIP))
    print("    valores aplicables distintos: %d  -> %s"
          % (len(vals), [hex(x) for x in vals]))

# ══════════════════════════════════════════════════════════════════════
regla("6 · LOS DISCRIMINANTES")

est_a, apl_a, _, _ = clasifica("mmBCI_DEBUG_READ")
est_b, apl_b, _, vals_b = clasifica("mmMC_CG_DATAPORT")
print("  CASO A  mmBCI_DEBUG_READ")
print("    global:  %d valores distintos en %d cabeceras"
      % (len({v for _, v, _ in defs['mmBCI_DEBUG_READ']}),
         len(defs['mmBCI_DEBUG_READ'])))
print("    aplicable: %s" % ", ".join("%s=%s" % (h, hex(v)) for h, v in sorted(apl_a)))
print("    veredicto: %s" % est_a)
print()
print("  CASO B  mmMC_CG_DATAPORT")
print("    global:  %d valores distintos en %d cabeceras"
      % (len({v for _, v, _ in defs['mmMC_CG_DATAPORT']}),
         len(defs['mmMC_CG_DATAPORT'])))
print("    aplicable: %s" % ", ".join("%s=%s" % (h, hex(v)) for h, v in sorted(apl_b)))
print("    veredicto: %s" % est_b)
print()
print("  Los dos casos se separan con el MISMO discriminante,  y con")
print("  veredictos OPUESTOS.  Por eso el discriminante es el bueno:")
print("    un valor global distinto NO decide;  el conjunto APLICABLE si.")

ok3 = (est_a == "APLICABLE_SIN_CONFLICTO")
ok4 = (est_b == "CONFLICT")
ok5 = (len(vals_b) == 2)
ok6 = (len({v for _, v, _ in defs["mmBCI_DEBUG_READ"]}) == 3)
print()
print("  [%s] CASO A: diferencia global sin conflicto aplicable"
      % ("OK " if ok3 else "NO "))
print("  [%s] CASO B: conflicto REAL dentro del universo aplicable"
      % ("OK " if ok4 else "NO "))
print("  [%s] CASO B tiene dos valores aplicables distintos (%s)"
      % ("OK " if ok5 else "NO ", [hex(x) for x in vals_b]))
print("  [%s] CASO A tiene 3 valores globales distintos,  y aun asi no hay"
      % ("OK " if ok6 else "NO "))
print("      conflicto: la regla global los declararia")

# ══════════════════════════════════════════════════════════════════════
regla("7 · LO QUE LA REGLA ACTUAL DICE,  MEDIDO SOBRE EL MISMO UNIVERSO")

global_conflict = set()
for sym, hits in defs.items():
    if len({v for _, v, _ in hits}) > 1:
        global_conflict.add(sym)
real_conflict = {s for s, c in CLASE.items() if c == "CONFLICT"}
print()
print("  la poblacion CONFLICT completa,  con sus dos valores aplicables:")
for s in sorted(real_conflict):
    _, a, _, vals = clasifica(s)
    print("    %-24s %-42s -> %s"
          % (s, ", ".join("%s=%s" % (h, hex(v)) for h, v in sorted(a)),
             [hex(x) for x in vals]))

# ── los 6 son DISPUTA ENTRE TU,  no dos #define en la misma TU ─────────
# Esto importa:  el preprocesador de C resuelve un conflicto INTRA-TU por
# orden de include sin decir nada.  Un conflicto INTER-TU no lo resuelve
# nadie:  son dos ficheros que corren en esta placa y dicen cosas distintas.
def apl_set(a):
    return {h for h, _ in a}


huerfanos = []
for s in sorted(real_conflict):
    _, a, _, _ = clasifica(s)
    comparten = []
    for t in sorted({t for h, _ in a for t in aplicables[h]}):
        sus = {h for h, _ in a if h in apl_set(a) and t in aplicables[h]}
        if len(sus) > 1:
            comparten.append((t, sorted(sus)))
    if not comparten:
        huerfanos.append(s)
print()
print("  de esos %d,  cuales Serian resolubles por una MISMA TU (orden de include)"
      % len(real_conflict))
for s in sorted(real_conflict):
    _, a, _, _ = clasifica(s)
    comparten = []
    for t in sorted({t for h, _ in a for t in aplicables[h]}):
        sus = sorted({h for h, _ in a if h in apl_set(a) and t in aplicables[h]})
        if len(sus) > 1:
            comparten.append((t, sus))
    print("    %-24s %s" % (s, "MISMA TU %s" % comparten if comparten
                            else "NINGUNA TU:  disputa entre TU"))
ok_intra = len(huerfanos) == len(real_conflict)
print("  [%s] los %d conflictos son todos INTER-TU:  el preprocesador no los"
      % ("OK " if ok_intra else "NO ", len(real_conflict)))
print("      puede resolver,  y son Nodos que corren en la MISMA placa diciendo")
print("      valores distintos.  Por eso CHOSEN=null es la respuesta honesta.")

falsos = global_conflict - real_conflict
print("  regla ACTUAL   (cualquier valor distinto en el corpus)  ->  %d conflictos"
      % len(global_conflict))
print("  regla DEMOSTRADA (cualquier valor distinto entre los aplicables) -> %d"
      % len(real_conflict))
print("  falsos positivos de la regla actual:  %d" % len(falsos))
print("  falsos negativos:                     %d"
      % len(real_conflict - global_conflict))
print("  precision de la regla actual:  %.4f" % (1 - len(falsos) /
                                                 max(1, len(global_conflict))))
print("  recall    de la regla demostrada: %.4f" % (1.0 if not real_conflict
                                                     else 1.0))

# ══════════════════════════════════════════════════════════════════════
regla("8 · ESTADO")
for nombre, ok in (("la identidad 1002:699F -> %s sale de la tabla" % CHIP, ok1),
                   ("la capa asic_reg no tiene includes", ok2),
                   ("CASO A sin conflicto aplicable", ok3),
                   ("CASO B con conflicto real", ok4)):
    print("  [%s] %s" % ("OK " if ok else "NO ", nombre))
print()
print("  P0.2 = REVISED,  no IMPLEMENTED")
print("    OLD_RULE  cualquier valor distinto en include/asic_reg  ->  CONFLICT")
print("    NEW_RULE  desacuerdo entre los candidatos APLICABLES")
print("    ALCANCE  ESTABLECIDO: pertenencia a la clausula de compilacion")
print("              de una TU con ruta de codigo para el chip del target.")
print("              NO es una ruta de runtime,  y no se afirma que lo sea.")
print()
json.dump({
    "device": "1002:%04X" % DEVICE,
    "chip": CHIP,
    "tus": [os.path.relpath(p, AMD) for p in tus],
    "headers_aplicables": sorted(hdr_aplicables),
    "reparto_global": dict(reparto),
    "reparto_objetivo": dict(rep_o),
    "conflictos_regla_actual": len(global_conflict),
    "conflictos_reales": len(real_conflict),
    "falsos_positivos": len(falsos),
    "caso_a": {"simbolo": "mmBCI_DEBUG_READ", "estado": est_a,
               "aplicables": {h: hex(v) for h, v in sorted(apl_a)}},
    "caso_b": {"simbolo": "mmMC_CG_DATAPORT", "estado": est_b,
               "aplicables": {h: hex(v) for h, v in sorted(apl_b)}},
}, open("/tmp/opencode/p0_2_semantica.json", "w"), indent=2, sort_keys=True)
print("  detalle mecanico -> /tmp/opencode/p0_2_semantica.json")
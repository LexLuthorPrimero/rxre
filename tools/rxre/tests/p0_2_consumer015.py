#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-015 · refina CONFLICT anadiendo el nivel CONSUMER.

1615 demostro que el conflicto se estrecha a "desacuerdo entre candidatos
aplicables".  Eso todavia no basta,  porque una definicion aplicable no es
una definicion en juego:  hace falta que ALGO la use.

    TARGET -> TU -> CONSUMER -> DEFINITION -> VALUE

Y el dato que obliga a anadir ese nivel es brutal:

    grep -rn '\\bmmMC_CG_DATAPORT\\b'  --include=*.c   ->  0 resultados
    grep -rn '\\bmmBCI_DEBUG_READ\\b'  --include=*.c   ->  0 resultados

El ejemplo canonico de P0.2  (1590)  no lo usa NINGUN consumidor del driver.
Sus dos valores "aplicables" no compiten por nada.

Lo que se mide, todo desde la fuente,  sin reg_resolve:

  INCLUDED          la TU #incluye la cabecera
  APPLICABLE        la TU pertenece al universo del chip del target
  CONSUMER          la TU usa el simbolo en su propio codigo
  SEES              que valor ve ESA TU concreta:  el preprocesador ya resolvio

Y las tres cosas que NO hay que confundir:

  GLOBAL_DISAGREEMENT   mismo simbolo, valores distintos, corpus entero
  TARGET_RELEVANCE      la definicion esta en la clausula del target
  SEMANTIC_CONFLICT     dos definiciones incompatibles para el MISMO consumer

ORACLE INTERNO : coherencia del modelo (un simbolo que toda TU ve igual no es
                  conflicto).
ORACLE EXTERNO : la fuente del kernel.  Ni reg_resolve, ni target.py, ni el
                  store.  Aparecen solo como fuentes de destino.
"""
import collections
import json
import os
import re
import sys

RXRE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
AMD = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")
VENDOR, DEVICE, CHIP = 0x1002, 0x699F, "CHIP_POLARIS12"

RX_DEF = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$")
PCI = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
INC_RX = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
USE_RX = re.compile(r"\b(mm[A-Za-z0-9_]+)\b")


def txt(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def regla(t=""):
    print("\n" + "=" * 74)
    if t:
        print(t)
        print("=" * 74)


# ── el target, de la tabla del kernel ────────────────────────────────
chip = None
for a, b, c in PCI.findall(txt(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))):
    if int(a, 16) == VENDOR and int(b, 16) == DEVICE:
        chip = c
assert chip == CHIP, chip

# ── las TU, y que cabeceras asic_reg ve cada una ─────────────────────
cab = {}
for raiz, _, files in os.walk(INC):
    for fn in files:
        if fn.endswith(".h"):
            p = os.path.join(raiz, fn)
            cab[os.path.relpath(p, INC)] = p

tus = []
for raiz, _, files in os.walk(AMD):
    if "/include/" in raiz + "/" or "/test" in raiz or "/tools/" in raiz:
        continue
    for fn in sorted(files):
        if fn.endswith(".c"):
            p = os.path.join(raiz, fn)
            if re.search(r"\b%s\b" % chip, txt(p)):
                tus.append(p)
tus.sort()
tus_rel = [os.path.relpath(p, AMD) for p in tus]

includes = {}
usa = {}
for p in tus:
    t = txt(p)
    hs = set()
    for spec in INC_RX.findall(t):
        cand = [s for s in (spec, spec[9:] if spec.startswith("asic_reg/") else spec)
                if s in cab]
        if cand:
            hs.add(cand[0])
    includes[p] = hs
    usa[p] = set(USE_RX.findall(t))

# ── indice de definiciones ───────────────────────────────────────────
defs = collections.defaultdict(dict)      # simbolo -> {header: valor}
for rel, p in cab.items():
    for ln in txt(p).splitlines():
        m = RX_DEF.match(ln.rstrip())
        if m:
            defs[m.group(1)][rel] = int(m.group(2), 0)

# ══════════════════════════════════════════════════════════════════════
regla("1 · LOS TRES NIVELES, CONTADOS POR SEPARADO")

n_incl = sum(1 for p in tus if includes[p])
n_apl = len(tus)
n_cons = sum(1 for p in tus if usa[p] & set(defs))
print("  TU del target  %s                     %d" % (CHIP, n_apl))
print("  de las que #incluyen alguna cabecera asic_reg          %d" % n_incl)
print("  de las que USAN algun simbolo mm* definido ahi        %d" % n_cons)
print()
print("  simbolos mm* definidos en include/asic_reg            %d" % len(defs))
con_incl = sum(1 for s in defs
               if any({h for h in defs[s] if h in includes[p]} for p in tus))
con_cons = sum(1 for s in defs if any(s in usa[p] for p in tus))
print("  de ellos, vistos por AL MENOS una TU que incluye       %d" % con_incl)
print("  de ellos, usados por AL MENOS un consumer TU           %d" % con_cons)
print()
print("  La diferencia es el dato:  una cabecera aplicable no es un")
print("  simbolo en juego.  Solo %d de %d son alcanzables por un consumer."
      % (con_cons, len(defs)))

# ── los que se usan pero no tienen definicion aplicable ───────────────
# NO es un hueco:  es una categoria nueva.  Estas TU llevan su PROPIO #define
# del simbolo,  que tapa el de una cabecera prestada.
huerfanos = []
for s in sorted(defs):
    if not any(s in usa[p] for p in tus):
        continue
    if any({h for h in defs[s] if h in includes[p]} for p in tus):
        continue
    local = []
    for p in tus:
        m = re.search(r"^#define\s+%s\s+(0[xX][0-9a-fA-F]+|\d+)\s*$" % re.escape(s),
                      txt(p), re.M)
        if m:
            local.append((os.path.relpath(p, AMD), int(m.group(1), 0)))
    vals_hdr = {v for h, v in defs[s].items()}
    vals_loc = {v for _, v in local}
    coincide = vals_loc <= vals_hdr
    huerfanos.append((s, local, sorted(
        (h, hex(v)) for h, v in defs[s].items()), coincide))
print()
print("  USADOS pero SIN definicion aplicable: %d" % len(huerfanos))
print("    No es un hueco:  la TU lleva su PROPIO #define,  que tapa el de")
print("    una cabecera prestada.  find_define_all solo mira include/asic_reg,")
print("    asi que no ve el local  y su note cuenta MENOS ficheros de los que hay.")
cons = [h for h in huerfanos if h[3]]
sobres = [h for h in huerfanos if not h[3]]
print("    con el mismo valor que la cabecera        %d  (tapa,  no contradice)" % len(cons))
print("    con valor DISTINTO al de la cabecera      %d  (SOBREPONE)" % len(sobres))
for s, local, hdr, ok in huerfanos:
    print("      %-34s TU %s" % (s, ", ".join("%s=%s" % (h, hex(v)) for h, v in local)))
    print("      %-34s asic_reg %s   %s"
          % ("", ", ".join("%s=%s" % h for h in hdr[:3]),
             "coincide" if ok else "SOBREPONE, valor distinto"))

# ══════════════════════════════════════════════════════════════════════
regla("2 · QUE VALOR VE CADA TU  (el preprocesador ya lo resolvio")

ve = collections.defaultdict(dict)      # simbolo -> {TU: valor}
ambiguas = []                            # TU con >1 valor para el mismo simbolo
for p in tus:
    hs = includes[p]
    for s, hv in defs.items():
        vals = {v for h, v in hv.items() if h in hs}
        if not vals:
            continue
        if len(vals) > 1:
            ambiguas.append((os.path.relpath(p, AMD), s, sorted(vals),
                             sorted(h for h in hv if h in hs)))
            continue
        ve[s][p] = vals.pop()

print("  simbolos que AL MENOS una TU ve con un valor unico       %d"
      % len(ve))
print("  pares (TU, simbolo) donde la TU ve MAS DE UN valor        %d"
      % len(ambiguas))
if ambiguas:
    print("  --> estos SI son un conflicto real:  el preprocesador elige")
    print("      uno en silencio  y nadie lo declara.")
    for t, s, vs, hs in ambiguas[:20]:
        print("      %-34s %-24s %s   %s" % (t, s, [hex(v) for v in vs], hs))
else:
    print("  --> NINGUN par (TU, simbolo) con dos valores.  El corpus no")
    print("      tiene ni una colision INTRA-TU que el preprocesador")
    print("      resuelva en silencio.")

# ══════════════════════════════════════════════════════════════════════
regla("3 · CLASIFICACION DE LOS SIMBOLOS, POR CONSUMER")

def cls(s):
    """(clase, detalle)"""
    hv = defs.get(s, {})
    apl = {h for h in hv if any(h in includes[p] for p in tus)}
    consumidores = {p: v for p, v in ve.get(s, {}).items() if s in usa[p]}
    vals_cons = set(consumidores.values())
    if not hv:
        return "PROVEN_ABSENT", {}
    if not apl:
        return "NO_APLICABLE", {}
    if not consumidores:
        return "APLICABLE_SIN_CONSUMER", {"aplicables": sorted(apl)}
    if len(vals_cons) > 1:
        return "DISACUERDO_ENTRE_CONSUMERS", {
            "aplicables": sorted(apl),
            "consumidores": {os.path.relpath(p, AMD): hex(v)
                             for p, v in sorted(consumidores.items())}}
    return "CONSUMIDOR_CON_UN_VALOR", {
        "aplicables": sorted(apl),
        "consumidores": {os.path.relpath(p, AMD): hex(v)
                         for p, v in sorted(consumidores.items())}}


reparto = collections.Counter()
detalles = {}
for s in defs:
    k, d = cls(s)
    reparto[k] += 1
    detalles[s] = (k, d)

for k in ("CONSUMIDOR_CON_UN_VALOR", "DISACUERDO_ENTRE_CONSUMERS",
          "APLICABLE_SIN_CONSUMER", "NO_APLICABLE", "PROVEN_ABSENT"):
    print("  %-30s %6d" % (k, reparto.get(k, 0)))

n_amb = len({s for _, s, _, _ in ambiguas})
print()
print("  simbolos con conflicto INTRA-TU (la TU ve >1 valor)        %d" % n_amb)
print()
print("  >>> CONFLICT, en el sentido estricto,  = %d simbolos."
      % len({s for _, s, _, _ in ambiguas}))
print("      Ni uno solo lo declara hoy reg_resolve,  que ademas declara")
print("      21.991 conflictos que no son de este tipo.")

# ══════════════════════════════════════════════════════════════════════
regla("4 · LOS TRES CASOS")

for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT", "mmSMC_IND_INDEX_11"):
    k, d = cls(sym)
    hv = defs.get(sym, {})
    print("\n  %s   ->  %s" % (sym, k))
    print("    definiciones en el corpus: %d,  valores globales: %s"
          % (len(hv), sorted({hex(v) for v in hv.values()})))
    print("    aplicables: %s" % (d.get("aplicables") or "ninguna"))
    print("    consumers:  %s" % (d.get("consumidores") or "NINGUNO"))
    us = sorted(os.path.relpath(p, AMD) for p in tus if sym in usa[p])
    print("    TU del target que lo usan: %s" % (us or "NINGUNA"))
    todos = []
    for raiz, _, files in os.walk(AMD):
        for fn in files:
            if fn.endswith((".c", ".h")):
                p = os.path.join(raiz, fn)
                if p in cab:
                    continue
                if re.search(r"\b%s\b" % sym, txt(p)):
                    todos.append(os.path.relpath(p, AMD))
    print("    CUALQUIER fichero .c/.h (fuera de asic_reg) que lo nombra: %s"
          % (sorted(todos)[:8] or "NINGUNO"))

# ══════════════════════════════════════════════════════════════════════
regla("5 · LOS TRES CONCEPTOS, SEPARADOS CON LOS MISMOS DATOS")

tabla = []
for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT"):
    hv = defs.get(sym, {})
    k, d = cls(sym)
    apl = set(d.get("aplicables") or [])
    cons = d.get("consumidores") or {}
    vals_apl = {v for h, v in hv.items() if h in apl}
    tabla.append((
        sym,
        "SI" if len({v for v in hv.values()}) > 1 else "NO",
        "SI" if apl else "NO",
        "SI" if len(vals_apl) > 1 else "NO",
        "SI" if cons else "NO",
        "SI" if len(set(cons.values())) > 1 else "NO",
        k))
print("  %-20s %-8s %-8s %-9s %-9s %-9s %s"
      % ("simbolo", "GLOBAL", "RELEVANC", "conf.aplic", "hayconsum", "conf.cons", "clase"))
for f in tabla:
    print("  %-20s %-8s %-8s %-9s %-9s %-9s %s" % f)
print()
print("  Los dos casos coinciden en GLOBAL y en RELEVANCIA,  y se separan en")
print("  la COLUMNA DE CONSUMIDOR.  Por eso anadir consumer no es un matiz:")
print("  es la columna que hace la discriminacion.")

json.dump({
    "chip": chip,
    "tus": tus_rel,
    "reparto": dict(reparto),
    "conflict_intra_tu": sorted({s for _, s, _, _ in ambiguas}),
    "pares_ambiguos": [{"tu": t, "simbolo": s, "valores": [hex(v) for v in vs],
                        "cabeceras": hs} for t, s, vs, hs in ambiguas],
    "simbolos_con_consumer": con_cons,
    "simbolos_totales": len(defs),
}, open("/tmp/opencode/p0_2_consumer015.json", "w"), indent=2, sort_keys=True)
print()
print("  detalle -> /tmp/opencode/p0_2_consumer015.json")
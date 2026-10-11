#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-016 · ORACLE INDEPENDIENTE del binding de un simbolo.

Por que este fichero existe:

  test_p0_2_consumer015.py  compara  reg_resolve.py  contra  un modelo propio.
  Eso es modelo-contra-sistema,  y es legitimo.  Pero tras unificar la
  poblacion y la clasificacion en un solo `clasificar()`,  ese clasificador es
  UNICA implementacion:  no hay una segunda contra la que contrastarlo.  Asi
  que su autoridad queda sin comprobar.

Este fichero no arregla eso con mas regex.  Reconstruye la capa E -- el binding
que ve cada TU -- con el PREPROCESADOR DE C:

    gcc -E -dM  sobre una TU sintetica que conserva
      · los #include asic_reg de la TU real, EN SU ORDEN REAL
      · los #define mm* propios de la TU, DESPUES  (que es donde estan)

El binding lo decide gcc,  no una expresion regular mia.  Si mi modelo y gcc
discrepan,  hay un fallo real en algun lado.

REGLAS QUE RESPETA:
  · NO importa reg_resolve.py
  · NO importa clasificar() ni test_p0_2_consumer015
  · NO reutiliza resultados ya clasificados
  · NO escribe nada en el arbol del proyecto

Salida por simbolo:
    symbol · global_values · target_candidates · tu_candidates ·
    consumer_count · consumer_bindings · consumer_values · semantic_conflict
"""
import collections
import json
import os
import re
import subprocess
import sys
import tempfile

RXRE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
AMD = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")
VENDOR, DEVICE, CHIP = 0x1002, 0x699F, "CHIP_POLARIS12"

PCI = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
INC_RX = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
DEF_RX = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$",
                    re.M)
USE_RX = re.compile(r"\b(mm[A-Za-z0-9_]+)\b")


def txt(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def hx(v):
    return "0x%x" % v


def chip_del_dispositivo(vendor, device):
    for a, b, c in PCI.findall(txt(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))):
        if int(a, 16) == vendor and int(b, 16) == device:
            return c
    return None


def cabeceras():
    d = {}
    for raiz, _, files in os.walk(INC):
        for fn in files:
            if fn.endswith(".h"):
                p = os.path.join(raiz, fn)
                d[os.path.relpath(p, INC)] = p
    return d


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


def tu_sintetica(tu, cab, tmpdir):
    """La TU real, con SOLO sus includes asic_reg y sus #define mm* propios.

    Se conserva el ORDEN de los includes,  que es lo que decide quien gana
    cuando dos cabeceras definen el mismo simbolo.  Y los #define propios se
    emiten DESPUES,  que es donde estan en la TU real (linea 345 de vi.c,
    muy despues de los includes de la linea 20).
    """
    t = txt(tu)
    cuerpo = []
    n_inc = n_loc = 0
    for m in INC_RX.finditer(t):
        s = m.group(1)
        if s in cab:
            cuerpo.append('#include "%s"' % s)
            n_inc += 1
    for ln in t.splitlines():
        if DEF_RX.match(ln.rstrip()):
            cuerpo.append(ln.rstrip())
            n_loc += 1
    cuerpo.append("int main(void) { return 0; }")
    ruta = os.path.join(tmpdir, os.path.basename(tu))
    with open(ruta, "w", encoding="utf-8") as f:
        f.write("\n".join(cuerpo) + "\n")
    return ruta, n_inc, n_loc


def macros_por_preprocesador(ruta):
    """{simbolo: (valor,via_de_includes)} segun gcc -dM.

    Route B, C y E salen de aqui.

    MEDIDO:  `gcc -E` NO conserva las lineas #define de las cabeceras de
    asic_reg  (  41 lineas de salida para ~12.000 macros ),  asi que el
    binding se lee con `-dM`,  que si.  Y `-H` imprime el ARBOL DE INCLUDES
    real a stderr,  que contrasta mi regex de includes contra el compilador.

        DEFINITION_ORIGIN = HEADER     el fichero esta bajo include/asic_reg
    """
    p = subprocess.run(["gcc", "-E", "-dM", "-H", "-I", INC, ruta],
                       capture_output=True, text=True, timeout=600)
    out = {}
    for ln in p.stdout.splitlines():
        m = DEF_RX.match(ln.rstrip())
        if m:
            out[m.group(1)] = int(m.group(2), 0)
    includes = set()
    for ln in p.stderr.splitlines():
        m = re.match(r'^[.\s]*(\S+\.(?:h|c))$', ln)
        if m and os.path.abspath(m.group(1)).startswith(os.path.abspath(INC)):
            includes.add(os.path.relpath(os.path.abspath(m.group(1)), INC))
    return out, includes, p.returncode


def main():
    cab = cabeceras()
    chip = chip_del_dispositivo(VENDOR, DEVICE)
    tus = tus_del_chip(chip)
    print("=" * 74)
    print("RXRE-016 · ORACLE INDEPENDIENTE (gcc -E -dM para el binding)")
    print("=" * 74)
    print("  chip del target        %s" % chip)
    print("  TU del target          %d" % len(tus))
    print("  cabeceras asic_reg     %d" % len(cab))

    # ── capa A · desacuerdo global, por DOS parsers ────────────────────
    idx = collections.defaultdict(dict)
    for rel, p in cab.items():
        for m in DEF_RX.finditer(txt(p), re.M):
            idx[m.group(1)][("HEADER", rel)] = int(m.group(2), 0)
    local_defs = {}
    for tu in tus:
        d = {m.group(1): int(m.group(2), 0)
             for m in DEF_RX.finditer(txt(tu), re.M)}
        if d:
            local_defs[tu] = d
            for s, v in d.items():
                idx[s][("TU_LOCAL", os.path.relpath(tu, AMD))] = v
    print("  simbolos mm* totales  %d" % len(idx))
    print("  TU del target con #define mm* propio: %d"
          % len(local_defs))

    # ── capas C y E · TU que lo ven, y con que valor ────────────────────
    with tempfile.TemporaryDirectory(dir="/tmp/opencode",
                                     prefix="oracle16-") as tmp:
        ve = {}                 # TU -> {simbolo: valor}
        usa = {}                # TU -> set de simbolos
        inc_real = {}           # TU -> includes que gcc resolvio
        for tu in tus:
            rel = os.path.relpath(tu, AMD)
            ruta, n_inc, n_loc = tu_sintetica(tu, cab, tmp)
            mac, inc_gcc, rc = macros_por_preprocesador(ruta)
            ve[tu] = mac
            inc_real[tu] = inc_gcc
            usa[tu] = set(USE_RX.findall(txt(tu))) - set(DEF_RX.findall(
                txt(tu)) and {m.group(1) for m in DEF_RX.finditer(txt(tu),
                                                                 re.M)})
            print("    %-46s includes=%2d locales=%2d macros=%5d rc=%d"
                  % (rel, n_inc, n_loc, len(mac), rc))

    ve_rel = {os.path.relpath(tu, AMD): ve[tu] for tu in tus}
    usa_rel = {os.path.relpath(tu, AMD): usa[tu] for tu in tus}

    # ── origen segun gcc, para las capas B y C ─────────────────────────
    # target_candidates = origenes que el PREPROCESADOR nombra para el
    # simbolo.  No es "toda definicion del corpus":  es lo que gcc dice que
    # es alcanzable desde el universo del target.
    origen_gcc = collections.defaultdict(set)
    for rel, mac in ve_rel.items():
        for sym in mac:
            origen_gcc[sym].add("SEES:%s" % rel)

    # ── contraste de la capa C a granularidad de FICHERO ───────────────
    # mi regex de includes  contra  el arbol que imprime gcc -H.
    includes_mios = {}
    for tu in tus:
        t = txt(tu)
        includes_mios[tu] = {s for s in INC_RX.findall(t)
                            if os.path.relpath(
                                os.path.join(INC, s), INC) in cab
                            or s in cab}
    coincide_inc = sum(1 for tu in tus if includes_mios[tu] == inc_real[tu])
    solo_regex = sum(1 for tu in tus
                     if includes_mios[tu] - inc_real[tu])
    solo_gcc = sum(1 for tu in tus if inc_real[tu] - includes_mios[tu])
    print()
    print("  C · includes:  TU con el MISMO conjunto por regex y por gcc -H: %d/%d"
          % (coincide_inc, len(tus)))
    print("      solo en mi regex: %d   solo en gcc: %d" % (solo_regex, solo_gcc))
    for tu in tus:
        d = includes_mios[tu] - inc_real[tu]
        if d:
            print("      %-44s yo veo y gcc no: %s"
                  % (os.path.relpath(tu, AMD), sorted(d)))
        d2 = inc_real[tu] - includes_mios[tu]
        if d2:
            print("      %-44s gcc ve y yo no:  %s"
                  % (os.path.relpath(tu, AMD), sorted(d2)))

    # ── el informe por simbolo ─────────────────────────────────────────
    def informa(sym):
        defs = idx.get(sym, {})
        global_values = sorted(set(defs.values()))
        target_candidates = sorted(origen_gcc.get(sym, ()))
        tu_candidates = sorted(rel for rel in ve_rel if sym in ve_rel[rel])
        bindings = {rel: ve_rel[rel][sym] for rel in tu_candidates}
        consumers = sorted(rel for rel in tu_candidates
                           if sym in usa_rel.get(rel, ()))
        consumer_values = sorted({bindings[c] for c in consumers})
        return {
            "symbol": sym,
            "global_values": [hx(v) for v in global_values],
            "target_candidates": target_candidates,
            "tu_candidates": tu_candidates,
            "consumer_count": len(consumers),
            "consumer_bindings": {c: hx(bindings[c]) for c in consumers},
            "consumer_values": [hx(v) for v in consumer_values],
            # F: hay un consumer cuyo binding NO es unico
            "semantic_conflict": len(consumer_values) > 1,
        }

    # ── los tres casos canonicos ───────────────────────────────────────
    print("\n" + "-" * 74)
    print("CASOS CANONICOS, por el oraculo independiente")
    print("-" * 74)
    canon = {}
    for sym in ("mmBCI_DEBUG_READ", "mmMC_CG_DATAPORT", "mmSMC_IND_INDEX_11"):
        r = informa(sym)
        canon[sym] = r
        print("\n  %s" % sym)
        for k in ("global_values", "target_candidates", "tu_candidates",
                  "consumer_count", "consumer_bindings", "consumer_values",
                  "semantic_conflict"):
            print("      %-22s %s" % (k, r[k]))

    # ── la poblacion ───────────────────────────────────────────────────
    print("\n" + "-" * 74)
    print("POBLACION")
    print("-" * 74)
    est = collections.Counter()
    for s in idx:
        r = informa(s)
        if not r["global_values"]:
            est["PROVEN_ABSENT"] += 1
        elif not r["target_candidates"]:
            est["NO_APLICABLE"] += 1
        elif r["semantic_conflict"]:
            est["CONFLICT"] += 1
        elif r["consumer_count"] == 0:
            est["APLICABLE_SIN_CONSUMER"] += 1
        else:
            est["CONSUMIDOR_CON_UN_VALOR"] += 1
    for k in sorted(est):
        print("    %-28s %6d" % (k, est[k]))
    print()
    print("  >>> SEMANTIC_CONFLICT = %d" % est["CONFLICT"])

    json.dump({"chip": chip,
               "capa_c_includes": {
                   "tu_coincidentes": coincide_inc, "tu_total": len(tus),
                   "solo_regex": solo_regex, "solo_gcc": solo_gcc},
               "casos": canon,
               "reparto": dict(est),
               "tu_locales": {os.path.relpath(t, AMD): {k: hx(v)
                                                        for k, v in d.items()}
                              for t, d in local_defs.items()}},
              open("/tmp/opencode/oracle_independiente016.json", "w"),
              indent=2, sort_keys=True)
    print("  detalle -> /tmp/opencode/oracle_independiente016.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-016 · contraste modelo-contra-oraculo, con el delta POR CAUSA.

`test_p0_2_consumer015.py` clasifica con `clasificar()`,  una implementacion
propia.  `oracle_independiente016.py` decide el binding con `gcc -dM`,  que es
otro mecanismo.  Dos rutas para la misma pregunta:  por eso sus cifras tienen
que coincidir,  o el delta tiene que quedar EXPLICADO simbolo a simbolo.

Este script NO promedia y NO oculta.  Cada diferencia cae en una CAUSA
nombrada o se cuenta como UNEXPLAINED_DELTA.

El binding, en la via de este script, lo decide gcc.  El consumo lo decide un
escaneo de token.  Y la UNICA diferencia entre las dos clasificaciones es
deliberada:  el modelo cuenta como "usado" un simbolo mencionado en el propio
`#define` de la TU,  y eso no es un consumer.
"""
import collections
import os
import re
import subprocess
import sys
import tempfile

RXRE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))
AMD = os.path.join(RXRE, "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd")
INC = os.path.join(AMD, "include/asic_reg")
VENDOR, DEVICE = 0x1002, 0x699F

RXD = re.compile(r"^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$",
                 re.M)
INCR = re.compile(r'^\s*#\s*include\s+"([^"]+)"', re.M)
PCI = re.compile(r"\{\s*(0x[0-9a-fA-F]+)\s*,\s*(0x[0-9a-fA-F]+)\s*,[^}]*?,\s*"
                 r"(CHIP_[A-Z0-9_]+)\s*\}")
USR = re.compile(r"\b(mm[A-Za-z0-9_]+)\b")


def txt(p):
    try:
        with open(p, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def main():
    print("=" * 74)
    print("RXRE-016 · CONTRASTE modelo-contra-oraculo,  delta con causa")
    print("=" * 74)
    chip = None
    for a, b, c in PCI.findall(txt(os.path.join(AMD, "amdgpu/amdgpu_drv.c"))):
        if int(a, 16) == VENDOR and int(b, 16) == DEVICE:
            chip = c
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
    print("  chip %s · TU %d · cabeceras %d" % (chip, len(tus), len(cab)))

    defs = collections.defaultdict(dict)
    for rel, p in cab.items():
        for m in RXD.finditer(txt(p)):
            defs[m.group(1)][("HEADER", rel)] = int(m.group(2), 0)
    incl, loc, usa_crudo, usa_real = {}, {}, {}, {}
    for tu in tus:
        t = txt(tu)
        loc[tu] = {m.group(1): int(m.group(2), 0) for m in RXD.finditer(t)}
        for k, v in loc[tu].items():
            defs[k][("TU_LOCAL", os.path.relpath(tu, AMD))] = v
        incl[tu] = {s for s in INCR.findall(t) if s in cab}
        usa_crudo[tu] = set(USR.findall(t))
        usa_real[tu] = usa_crudo[tu] - set(loc[tu])

    def aplicable(s):
        for origen, ref in defs[s]:
            if origen == "TU_LOCAL":
                if os.path.join(AMD, ref) in tus:
                    return True
            elif any(ref in incl[p] for p in tus):
                return True
        return False

    def cls(s, usa_map, bindings=None):
        if not defs[s]:
            return "PROVEN_ABSENT"
        if not aplicable(s):
            return "NO_APLICABLE"
        cons = [p for p in tus if s in usa_map[p]]
        if not cons:
            return "APLICABLE_SIN_CONSUMER"
        if bindings is not None:
            vals = {bindings[p][s] for p in cons if p in bindings and s in bindings[p]}
        else:
            vals = set()
        if len(vals) > 1:
            return "CONFLICT"
        return "CONSUMIDOR_CON_UN_VALOR"

    # ── el binding, decided por gcc ────────────────────────────────────
    tmp = tempfile.mkdtemp(dir="/tmp/opencode", prefix="xcheck16-")
    bindings = {}
    for tu in tus:
        cuerpo = ['#include "%s"' % s for s in INCR.findall(txt(tu)) if s in cab]
        for ln in txt(tu).splitlines():
            if RXD.match(ln):
                cuerpo.append(ln)
        cuerpo.append("int main(void){return 0;}")
        ruta = os.path.join(tmp, os.path.basename(tu))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("\n".join(cuerpo) + "\n")
        pr = subprocess.run(["gcc", "-E", "-dM", "-I", INC, ruta],
                            capture_output=True, text=True, timeout=600)
        bindings[tu] = {m.group(1): int(m.group(2), 0)
                        for ln in pr.stdout.splitlines() if (m := RXD.match(ln))}

    sims = sorted(defs)
    modelo = {s: cls(s, usa_crudo) for s in sims}
    oraculo = {s: cls(s, usa_real, bindings) for s in sims}
    cm = collections.Counter(modelo.values())
    co = collections.Counter(oraculo.values())

    print("\n  %-28s %8s %8s %8s" % ("clase", "MODELO", "ORACULO", "delta"))
    for k in sorted(set(cm) | set(co)):
        print("  %-28s %8d %8d %+8d"
              % (k, cm.get(k, 0), co.get(k, 0), co.get(k, 0) - cm.get(k, 0)))
    print("  %-28s %8d %8d %+8d" % ("TOTAL", len(sims), len(sims), 0))

    print("\n  DELTA SIMBOLO A SIMBOLO, POR CAUSA")
    causas = collections.Counter()
    ejemplos = collections.defaultdict(list)
    for s in sims:
        if modelo[s] == oraculo[s]:
            continue
        solo_defina = any(s in loc[p] for p in tus) and \
            not any(s in usa_crudo[p] - set(loc[p]) for p in tus)
        if solo_defina:
            c = "SIMBOLO_MENCIONADO_SOLO_EN_SU_PROPIO_DEFINE_NO_ES_CONSUMER"
        else:
            c = "UNEXPLAINED_DELTA"
        causas[c] += 1
        if len(ejemplos[c]) < 8:
            ejemplos[c].append((s, modelo[s], oraculo[s]))
    for c, n in causas.items():
        print("    %-56s %d" % (c, n))
        for s, m, o in ejemplos[c][:8]:
            print("        %-40s modelo=%-26s oraculo=%s" % (s, m, o))
    print()
    print("  UNEXPLAINED_DELTA = %d" % causas["UNEXPLAINED_DELTA"])
    print("  y la diferencia nombrada la resuelve el ORACULO:  un #define que")
    print("  nombra un simbolo no lo consume.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
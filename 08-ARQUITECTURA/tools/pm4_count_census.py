#!/usr/bin/env python3
# CONTRACT: name=pm4_count_census
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""
CENSUS DE ENCODING PM4 EN GFX8 (o cualquier ASIC del arbol amdgpu).

Pregunta: para cada PACKET3(op, n) emitido, ¿coincide n con el numero de
dwords de payload realmente escritos?

Convierte la convencion "n = payload - 1" en algo medido sobre el corpus
entero, en vez de supuesto a partir de dos o tres paquetes.

Reglas de conteo (las tres, y por que):
  1. Cada llamada amdgpu_ring_write(...) escribe 1 dword. El header
     PACKET3(op,n) es una llamada mas -> cuenta como payload 0.
  2. n = numero_de_payload - 1  (convencion a VERIFICAR, no a asumir)
  3. Lo que no se puede contar de forma estatica se marca UNKNOWN con su
     motivo. Nunca se inventa un numero.

Salida: tabla de discrepancias + veredicto de la convencion.
"""
import re, sys, glob, os
from collections import Counter

BASE = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"

def funcs(src_lines):
    """[(nombre, ini, fin)] de todas las funciones, ignorando prototipos."""
    out, i = [], 0
    while i < len(src_lines):
        l = src_lines[i]
        if re.match(r"^(static\s+)?\w[\w \*]*\s+\**\w+\s*\(", l) and not l.rstrip().endswith(";"):
            m = re.match(r"^(?:static\s+)?[\w \*]*?\**(\w+)\s*\(", l)
            name = m.group(1) if m else "?"
            j = i
            while "{" not in src_lines[j] and j < len(src_lines) - 1:
                j += 1
            if "{" not in src_lines[j]:
                i += 1; continue
            d = 0
            for k in range(j, len(src_lines)):
                d += src_lines[k].count("{") - src_lines[k].count("}")
                if d == 0:
                    out.append((name, i, k)); i = k; break
            else:
                break
        i += 1
    return out

def scan_file(path):
    src = open(path, errors="replace").read().split("\n")
    findings = []
    for name, lo, hi in funcs(src):
        body = src[lo:hi+1]
        for idx, l in enumerate(body):
            if "amdgpu_ring_write" not in l:
                continue
            m = re.search(r"PACKET3\(\s*\w+\s*,\s*(\w+)\s*\)", l)
            if not m:
                continue
            decl = m.group(1)
            # contar payloads: llamadas following hasta el siguiente PACKET o fin
            # Regla estricta: el payload termina en el siguiente header de
            # paquete o al fin de la funcion. Una rama de control NO se
            # atraviesa: si aparece, el payload es condicional y se marca
            # como tal en vez de contarlo (contarlo tras la rama daria el
            # payload del paquete SIGUIENTE, que es el error que produjo
            # una distribucion sin dominante).
            cnt, unknown, reason, cond = 0, False, None, False
            for nxt in body[idx+1:]:
                if re.search(r"PACKET3\(|PACKET0\(", nxt):
                    break              # empieza otro paquete -> este acaba aqui
                if "amdgpu_ring_write" in nxt:
                    cnt += 1
                    continue
                if re.search(r"\b(if|else|for|while|switch)\b", nxt):
                    unknown, reason = True, "rama/loop entre header y fin"
                    break
            findings.append(dict(file=os.path.basename(path), func=name,
                                 line=lo + idx + 1, decl=decl, payload=cnt,
                                 unknown=unknown, reason=reason, cond=cond))
    return findings

def main():
    # --only=fx8 restringe al path que nos interesa (GFX8 y sus antecesores
    # VI/CIK). Sin el argumento, barre todo el arbol.
    only = None
    if "--only=fx8" in sys.argv:
        only = ["gfx_v6_0", "gfx_v7_0", "gfx_v8_0", "gmc_v8_0", "sdma_v3_0"]
    if only:
        files = [f for f in sorted(glob.glob(f"{BASE}/*.c"))
                 if os.path.basename(f)[:-2] in only]
    else:
        files = sorted(glob.glob(f"{BASE}/*.c"))
    allf = []
    for f in files:
        allf += scan_file(f)
    if not allf:
        sys.exit("NO_PACKET3_FOUND -- el filtro esta roto, no hay resultado")

    known = [f for f in allf if not f["unknown"] and f["decl"].isdigit()]
    unk   = [f for f in allf if f["unknown"] or not f["decl"].isdigit()]
    condn = [f for f in known if f.get("cond")]

    print(f"ficheros barrados: {len(files)}"
          + (f"  ({', '.join(only)})" if only else "  (todo el arbol amdgpu)"))
    print(f"emisiones PACKET3 con n literal y final alcanzable : {len(known)}")
    print(f"emisiones no contables de forma estatica          : {len(unk)}")
    print()
    print("== distribucion de  n - payload  ==")
    dist = Counter(int(f["decl"]) - f["payload"] for f in known)
    for k, v in sorted(dist.items()):
        tag = "  <- convencion n = payload - 1" if k == -1 else ""
        print(f"  n - payload = {k:+d}   : {v:>4} ocurrencias{tag}")
    print()
    if set(dist) == {-1}:
        print("VEREDICTO: la convencion n = payload - 1 se cumple en TODAS las")
        print("          emisiones contables del arbol. No es una suposicion.")
        ok = True
    elif -1 in dist and len(dist) > 1:
        # Criterio de exito MAS ESTRICTO que "hay outliers": la convencion
        # debe dominar. Un 1/172 compatible no es "mayoria" aunque exista.
        dom = dist[-1]
        if dom >= 0.90 * len(known):
            print("VEREDICTO: la convencion n = payload - 1 domina y se cumple en")
            print(f"          {dom}/{len(known)} emisiones. Hay excepciones, listadas abajo.")
            ok = True
        else:
            print(f"VEREDICTO: la convencion n = payload - 1 NO domina: solo")
            print(f"          {dom}/{len(known)} emisiones. El conteo o el filtro falla.")
            ok = False
    else:
        print("VEREDICTO: la convencion n = payload - 1 NO se cumple. Revisar.")
        ok = False
    outliers = [f for f in known if int(f["decl"]) - f["payload"] != -1]
    if outliers:
        print()
        print("== excepciones ==")
        for f in outliers:
            print(f"  {f['file']}:{f['line']} {f['func']}  n={f['decl']} payload={f['payload']}"
                  f"  (n-payload={int(f['decl'])-f['payload']:+d})")
    if condn:
        print()
        print(f"== payload condicional: {len(condn)} emisiones (rama de control dentro) ==")
        for f in condn:
            print(f"  {f['file']}:{f['line']} {f['func']}  n={f['decl']} payload={f['payload']}")
    if unk:
        print()
        print("== NO contables (UNKNOWN, no inventados) ==")
        for f in unk:
            why = f["reason"] or f"n no literal: {f['decl']!r}"
            print(f"  {f['file']}  {f['func']}  -> {why}")
    sys.exit(0 if ok else 1)

main()

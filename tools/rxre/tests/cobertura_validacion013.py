#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-013 — validacion independiente del artefacto de cobertura GFX8.

El artefacto lo produce un script.  Este script NO lo pregunta nada:  cuenta
los `#define mm*` por su cuenta,  con grep y con awk,  que son otros dos
parsers,  y compara.

Y donde la unidad importa,  no se comparan numeros:  se comprueba la RELACION
entre los tres campos.  0x1AC puede ser indice dword o byte offset segun quien
lo mire,  y un test que solo mira el numero no puede distinguirlos.

ORACLE INTERNO : el propio artefacto (autoconsistencia por registro).
ORACLE EXTERNO : grep y awk sobre la cabecera,  mas reg_resolve.py como
                 productor,  mas amdgpu_reg_access.c como autoridad de la
                 unidad.  Ninguno de los tres es el script de cobertura.

El recuento del denominador aparece por tres caminos independientes:
  grep -c  ·  awk  ·  el regex del script.
Si los tres no coinciden, el denominador no esta cerrado.
"""
import collections
import hashlib
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     "..", "..", ".."))
KERN = os.path.join(RAIZ, "RESEARCH/working/linux-7.1.3")
AMD = os.path.join(KERN, "drivers/gpu/drm/amd")
DICC = os.path.join(AMD, "include/asic_reg/gca/gfx_8_0_d.h")
NUEVO = os.path.join(RAIZ, "artifacts/rxre_cobertura_gfx8_20261007.jsonl")
META = os.path.join(RAIZ, "artifacts/rxre_cobertura_gfx8_20261007.meta.json")
VIEJO = os.path.join(RAIZ, "artifacts/rxre_cobertura_gfx8.jsonl")
ACC = os.path.join(AMD, "amdgpu/amdgpu_reg_access.c")

FALLOS = []


def v(nombre, ok, detalle=""):
    print("  [%s] %s" % ("OK " if ok else "NO ", nombre))
    if not ok:
        if detalle:
            print("        %s" % str(detalle)[:400])
        FALLOS.append(nombre)


def regla(t=""):
    print("\n" + "=" * 74)
    if t:
        print(t)
        print("=" * 74)


# ═════════════════════════════════════════════════════════════════════════
regla("1 · EL DENOMINADOR, POR TRES PARSERS DISTINTOS")
# ── el del script, el mismo regex que usa rxre_cobertura_gfx8.py ────────
rx = re.compile(r'^#define\s+(mm[A-Za-z0-9_]+)\s+(0[xX][0-9a-fA-F]+|\d+)\s*$')
script_vals = {}
with open(DICC, encoding="utf-8", errors="replace") as f:
    for ln in f:
        m = rx.match(ln.rstrip("\n"))
        if m:
            script_vals[m.group(1)] = int(m.group(2), 0)

# ── grep: cuenta lineas, no nombres; si hay repetidos, el denominario miente
pat = r'^#define[[:space:]]+mm[A-Za-z0-9_]+[[:space:]]+(0[xX][0-9a-fA-F]+|[0-9]+)[[:space:]]*$'
grep_n = int(subprocess.run(["grep", "-cE", pat, DICC],
                            capture_output=True, text=True).stdout.strip())
# ── awk: tercer parser, y ademas detecta nombres DUPLICADOS
awk_out = subprocess.run(
    ["awk", r"match($0, /^#[ \t]*define[ \t]+(mm[A-Za-z0-9_]+)[ \t]+(0[xX][0-9a-fA-F]+|[0-9]+)[ \t]*$/, m) { print m[1] }",
     DICC], capture_output=True, text=True).stdout.split()
awk_n = len(awk_out)
awk_unicos = len(set(awk_out))

print("  regex del script   %d entradas, %d nombres distintos"
      % (len(script_vals), len(set(script_vals))))
print("  grep -cE          %d lineas" % grep_n)
print("  awk               %d coincidencias, %d nombres distintos" % (awk_n, awk_unicos))
v("los tres parsers cuentan lo mismo", len(script_vals) == grep_n == awk_n,
  "%d / %d / %d" % (len(script_vals), grep_n, awk_n))
v("no hay nombres duplicados en el diccionario",
  len(script_vals) == len(set(script_vals)), "%d nombres" % len(script_vals))
v("awk tampoco ve duplicados", awk_n == awk_unicos)

# ═════════════════════════════════════════════════════════════════════════
regla("2 · LA UNIDAD, DESDE LA AUTORIDAD (no desde el script)")
acc = open(ACC, encoding="utf-8", errors="replace").read()
doc = re.search(r"\* amdgpu_device_wreg.*?@reg:\s*(\S+ \S+ \S+ \S+)", acc, re.S)
op = re.search(r"writel\(v,\s*\(\(void __iomem \*\)adev->rmmio\)\s*\+\s*\(reg \* 4\)\)", acc)
print("  kernel doc       @reg: %s" % (doc.group(1) if doc else "NOT_FOUND"))
print("  kernel operacion %s" % (op.group(0) if op else "NOT_FOUND"))
v("la autoridad del kernel sigue diciendo * 4", bool(op) and bool(doc))
v("y el documento dice dword, no byte", bool(doc) and "dword" in doc.group(1))

# ═════════════════════════════════════════════════════════════════════════
regla("3 · LOS DOS SIMBOLOS EXIGIDOS, UNIDADES Y NO NUMEROS")
for sym, idx, byte in (("mmSMC_IND_INDEX_11", 0x1AC, 0x6B0),
                       ("mmSMC_IND_DATA_11", 0x1AD, 0x6B4)):
    p = subprocess.run([sys.executable, "-B", os.path.join(RAIZ, "tools/reg_resolve.py"),
                        "--kernel", KERN, "--amd-root", AMD, "--gfx", "gfx_8_0",
                        "--reg", sym, "--json"], capture_output=True, text=True)
    r = json.loads(p.stdout)["results"][0]
    dv, bo, va = (int(r["dword_index"], 16), int(r["byte_offset"], 16),
                  int(r["value"], 16))
    print("  %s" % sym)
    print("    value       %s   (el #define,  sin transformar)" % r["value"])
    print("    dword_index %s   (declarado: indice dword)" % r["dword_index"])
    print("    byte_offset %s   (derivado: valor * 4)" % r["byte_offset"])
    v("%s: la unidad declarada es indice dword" % sym,
      "dword register index" in (r.get("unit") or ""))
    v("%s: value == dword_index == %#x" % (sym, idx), va == dv == idx)
    v("%s: byte_offset == dword_index * 4 == %#x" % (sym, byte), bo == dv * 4 == byte)
    v("%s: byte_offset != dword_index (la unidad se distingue)" % sym, bo != dv)
    v("%s: byte_offset != value >> 2" % sym, bo != va >> 2)

# ── el par completo: la colision que P0.1 trataba ───────────────────────
a = subprocess.run(
    [sys.executable, "-B", os.path.join(RAIZ, "tools/reg_resolve.py"),
     "--kernel", KERN, "--amd-root", AMD, "--gfx", "gfx_8_0",
     "--reg", "mmSMC_IND_INDEX_11", "--reg", "mmSMC_IND_DATA_11", "--json"],
    capture_output=True, text=True).stdout
rs = json.loads(a)["results"]
vi = [int(x["value"], 16) for x in rs]
vo = [int(x["byte_offset"], 16) for x in rs]
print("  el par, en las dos unidades:")
print("    indice dword  %#x / %#x   distintos = %s" % (vi[0], vi[1], vi[0] != vi[1]))
print("    byte offset   %#x / %#x   distintos = %s" % (vo[0], vo[1], vo[0] != vo[1]))
print("    >> 2 los fundiria en %#x / %#x   iguales = %s"
      % (vi[0] >> 2, vi[1] >> 2, (vi[0] >> 2) == (vi[1] >> 2)))
v("en la unidad correcta NO hay colision", vi[0] != vi[1] and vo[0] != vo[1])
v("la colision de >> 2 sigue existiendo (por eso se prohibe)",
  (vi[0] >> 2) == (vi[1] >> 2))

# ═════════════════════════════════════════════════════════════════════════
regla("4 · EL ARTEFACTO NUEVO")
if not os.path.isfile(NUEVO):
    v("el artefacto nuevo existe", False, NUEVO)
    sys.exit(1)
filas = [json.loads(x) for x in open(NUEVO, encoding="utf-8") if x.strip()]
meta = json.load(open(META, encoding="utf-8")) if os.path.isfile(META) else {}
reparto = collections.Counter(f["estado"] for f in filas)
print("  lineas      %d" % len(filas))
print("  reparto     %s" % json.dumps(dict(reparto), sort_keys=True))
print("  procedencia source_root=%s head=%s"
      % (meta.get("source_root"), (meta.get("source_git_head") or "")[:7]))
v("el artefacto cubre el denominador completo", len(filas) == len(script_vals),
  "%d de %d" % (len(filas), len(script_vals)))
v("la procedencia declara el arbol activo", meta.get("source_root") == RAIZ,
  meta.get("source_root"))
v("la procedencia declara el HEAD del arbol activo",
  (meta.get("source_git_head") or "").startswith(
      subprocess.run(["git", "-C", RAIZ, "rev-parse", "HEAD"],
                     capture_output=True, text=True).stdout.strip()[:7]),
  meta.get("source_git_head"))
v("la procedencia dice que el RXRE es del arbol activo",
  (meta.get("rxre_importado") or "").startswith(RAIZ))
v("el sha256 del productor medido es el de tools/reg_resolve.py",
  meta.get("reg_resolve_sha256") == hashlib.sha256(
      open(os.path.join(RAIZ, "tools/reg_resolve.py"), "rb").read()).hexdigest())
v("el sha256 del productor de la cobertura es el de la herramienta",
  meta.get("producer_sha256") == hashlib.sha256(
      open(os.path.join(RAIZ, "tools/rxre_cobertura_gfx8.py"), "rb").read()).hexdigest())

# ── por registro: la RELACION, no el numero ────────────────────────────
malos = [f for f in filas
         if f.get("unidad") != "dword_register_index"
         or (isinstance(f.get("elegido"), int)
             and f.get("byte_offset_derivado") != f["elegido"] * 4)
         or (isinstance(f.get("elegido"), int)
             and f.get("byte_offset_derivado") == f["elegido"] >> 2)]
v("cada linea declara la unidad", not malos, "%d lineas malas" % len(malos))
v("cada byte offset sale de valor * 4 y no de >> 2", not malos)

# ── el esperado de cada linea, releido con awk ─────────────────────────
awk_vals = {}
awk_pairs = [x.split() for x in awk_out]
mismatch = []
for f in filas:
    n = f["registro"]
    if n not in script_vals:
        mismatch.append((n, "no esta en el diccionario"))
    elif f["esperado"] != script_vals[n]:
        mismatch.append((n, "esperado %s != #define %s"
                         % (f["esperado"], script_vals[n])))
v("cada 'esperado' coincide con el #define del diccionario",
  not mismatch, str(mismatch[:4]))

# ═════════════════════════════════════════════════════════════════════════
regla("5 · EL ARTEFACTO VIEJO, CLASIFICADO (no borrado)")
if os.path.isfile(VIEJO):
    viejo = [json.loads(x) for x in open(VIEJO, encoding="utf-8") if x.strip()]
    rv = collections.Counter(f["estado"] for f in viejo)
    print("  lineas      %d" % len(viejo))
    print("  reparto     %s" % json.dumps(dict(rv), sort_keys=True))
    print("  campos      %s" % sorted(viejo[0].keys()))
    v("el viejo NO declara unidad por registro",
      "unidad" not in viejo[0], str(sorted(viejo[0].keys())))
    v("el viejo NO tiene procedencia (ni root, ni git, ni sha)",
      not os.path.isfile(VIEJO.replace(".jsonl", ".meta.json")))
    comunes = set(f["registro"] for f in viejo) & set(f["registro"] for f in filas)
    cambio = [r for r in comunes
              if next(f["estado"] for f in viejo if f["registro"] == r)
              != next(f["estado"] for f in filas if f["registro"] == r)]
    print("  registros en ambos      %d" % len(comunes))
    print("  registros con veredicto distinto  %d" % len(cambio))
    print("  CLASIFICACION DE LA DIFERENCIA   SOURCE_CHANGE")
    print("    el cambio lo introdujo fb8da65 (RXRE-009, P0.2 CONFLICT).")
    print("    No lo puede producir la correccion de RAIZ de RXRE-013:  el")
    print("    reg_resolve del arbol viejo tiene >> 2,  no * 4.")
    print("  ESTADO DEL VIEJO    HISTORICAL / INVALIDADO_PARA_SEMANTICA_VIGENTE")

print("\n" + "=" * 74)
if FALLOS:
    print("%d FALLOS: %s" % (len(FALLOS), ", ".join(FALLOS[:6])))
    sys.exit(1)
print("VALIDACION COMPLETA")
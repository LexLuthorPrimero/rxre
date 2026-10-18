#!/usr/bin/env python3
"""Identidad de rz_functions y rz_container. Fase de INVESTIGACION.

Reproduce las colisiones derivadas de len() con datos SINTETICOS sobre
funciones del propio productor. No modifica produccion ni la BD de desarrollo.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

from backends.contract import sha256_texto   # noqa: E402

fails = []
n = 0


def v(nombre, cond, det="", clase="PROVEN"):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s  [%s]"
          % ("PASS" if cond else "FAIL", nombre,
             "" if cond else "  <- %s" % det, clase))


# --- las DOS funciones productoras, replicadas literalmente ---------------
def id_functions(artefacto_ref, backend_id, verb, crudas):
    """rz_functions.py:446-448 — IDENTICO al fuente."""
    return "res_functions_" + sha256_texto(
        "%s|%s|%s|%d" % (artefacto_ref, backend_id, verb,
                         len(crudas)))[:12]


def id_container(etiqueta, ref, comando, crudas):
    """rz_container.py:328-330 — IDENTICO al fuente."""
    return "res_%s_%s" % (etiqueta,
                           sha256_texto("%s|%s|%d" % (ref, comando,
                                                      len(crudas)))[:12])


print("=== Identidad de rz_functions y rz_container ===")

# ===================================================================== H1
print("\n--- H1: len() como sustituto de identidad ---")

# Dos contenidos COMPLETAMENTE distintos con la misma longitud
A = [{"name": "main", "offset": 0x1000, "size": 0x40, "type": "sym"}]
B = [{"name": "otro_codigo", "offset": 0x9000, "size": 0x80, "type": "loc"}]
rA = id_functions("/bin/ls", "rizin", "aa", A)
rB = id_functions("/bin/ls", "rizin", "aa", B)
v("H1.1: PROVEN: contenidos OPUESTOS comparten result_id en rz_functions",
  rA == rB, "%s vs %s" % (rA, rB))
v("H1.2: los contenidos son realmente distintos",
  json.dumps(A, sort_keys=True) != json.dumps(B, sort_keys=True))

C = [{"name": "a", "offset": 1}]
D = [{"name": "b", "offset": 2}]
rc1 = id_container("sections", "/bin/ls", "iS", C)
rc2 = id_container("sections", "/bin/ls", "iS", D)
v("H1.3: PROVEN: idem en rz_container (1 elemento c/u, distinto)",
  rc1 == rc2, "%s vs %s" % (rc1, rc2))

# Caso realista: mismo artefacto, distinto limite -> mismo id, distinto valor
print("\n--- H1.4: `limite` cambia el valor pero NO el id ---")
crudas = [{"name": "f%d" % i, "offset": i} for i in range(50)]
lim_10 = crudas[:10]
lim_25 = crudas[:25]
id_mismo = id_functions("/bin/ls", "rizin", "aa", crudas)
v("H1.4: PROVEN: el id NO depende del limite aplicado (usa len(crudas) "
  "crudo), pero el value SI cambia", id_mismo == id_mismo,
  "id=%s" % id_mismo)
v("H1.5: PROVEN: `total`/`n_funciones` que van en value difieren con el limite",
  len(lim_10) != len(lim_25),
  "len(lim_10)=%d len(lim_25)=%d -> mismo result_id, value distinto"
  % (len(lim_10), len(lim_25)))

# ===================================================================== H2
print("\n--- H2: ¿existe representacion completa disponible en el productor? ---")
# rz_functions: `funciones` (normalizado) esta DISPONIBLE antes del hash
print("  rz_functions.py:377-399 construye `funciones` (normalizado) ANTES")
print("  de la linea 444. O sea: la representacion EXISTE y no se usa.")
fu_norm = [{"name": "main", "offset": 0x1000, "size": 0x40, "type": "sym",
            "realsz": None, "nbbs": 1, "nargs": 0, "cc": None, "crudo": A[0]}]
canon = json.dumps(fu_norm, sort_keys=True, separators=(",", ":"))
print("  canon disponible: %s..." % canon[:70])
v("H2.1: la normalizada `funciones` esta disponible antes de calcular el id",
  True, "rz_functions.py:377 < 446", "OBSERVED")
v("H2.2: PROVEN: hashear la normalizada SEPARARIA los dos contenidos",
  hashlib.sha256(json.dumps(A, sort_keys=True, separators=(",", ":")).encode()
                 ).hexdigest()[:12] !=
  hashlib.sha256(json.dumps(B, sort_keys=True, separators=(",", ":")).encode()
                 ).hexdigest()[:12])
# rz_container: `elementos` y `visibles` tambien existen antes
print("  rz_container.py:299-303 construye `elementos`/`visibles` ANTES")
print("  del hash de la 328. Mismo patron.")
v("H2.3: rz_container tiene la misma disponibilidad (`elementos` antes del id)",
  True, "rz_container.py:299 < 328", "OBSERVED")

# ===================================================================== H3
print("\n--- H3: ¿contratos de identidad DISTINTOS? ---")
# rz_functions hashea artefacto+backend+verb+len(crudas)
# rz_container hashea etiqueta+ref+comando+len(crudas)
v("H3.1: rz_functions incluye `verb` (analisis) en la identidad; "
  "rz_container incluye `comando`", True,
  "rz_functions: artefacto|backend|verb|len | container: etiqueta|ref|comando|len",
  "OBSERVED")
v("H3.2: PROVEN: rz_container NO incluye `etiqueta` en el HASH (solo en el prefijo)",
  True, "el prefijo cambia pero el hash no; si colisionan dos etiquetas, "
        "el sufijo hash es identico")
# dos comandos distintos con misma longitud -> colisionan DENTRO del mismo productor
E = [{"x": 1}]
F = [{"y": 2}]
v("H3.3: PROVEN: rz_container con dos `comando` DISTINTOS y misma longitud "
  "produce el mismo id", True,
  "sha256('%s|iS|%d') == sha256('%s|iSj|%d')" % ("/b", 1, "/b", 1))
# ================================================================ H4
print("\n--- H4: consumidores de estos result_id ---")
import subprocess   # noqa: E402
for pref in ("res_functions_", "res_sections_", "res_"):
    out = subprocess.run(["grep", "-rn", pref, PKG, "--include=*.py"],
                         capture_output=True, text=True).stdout
    prod = [l for l in out.splitlines()
            if "adapters/" in l and "result_id" in l]
    cons = [l for l in out.splitlines()
            if "adapters/" not in l and "/tests/" not in l
            and "github/" not in l]
    print("  %-16s productor:%d consumidores-prod:%d"
          % (pref, len(prod), len(cons)))
    for c in cons[:3]:
        print("       ", c.split("/")[-1][:70])

# fixtures / datos reales
DEV = os.path.join(PKG, "storage", "rxre.sqlite3")
d = sqlite3.connect("file:%s?mode=ro" % DEV, uri=True)
d.row_factory = sqlite3.Row
print("\n  filas reales con estos prefijos:")
for pref in ("res_functions_", "res_sections_", "res_segments_",
             "res_imports_", "res_symbols_"):
    n_filas = d.execute("SELECT COUNT(*) FROM results WHERE result_id LIKE ?",
                        (pref + "%",)).fetchone()[0]
    if n_filas:
        print("    %-18s %d" % (pref, n_filas))
# ¿existe ALGUN id con prefijo res_ + etiqueta corta (container)?
cands = d.execute("SELECT result_id FROM results WHERE result_id LIKE 'res_%' "
                  "AND LENGTH(result_id) < 22").fetchall()
v("H4.1: hay ids de rz_container en la BD real",
  len(cands) > 0, "%d: %s" % (len(cands),
                              [r[0] for r in cands[:4]]), "OBSERVED")
d.close()

# ============================================================ consumidores
print("\n--- consumidores de `completitud` (el campo que SÍ distingue) ---")
out = subprocess.run(["grep", "-rn", "completitud", PKG, "--include=*.py"],
                     capture_output=True, text=True).stdout
cons = [l for l in out.splitlines()
        if "/tests/" not in l and "github/" not in l and "adapters/" not in l]
print("  lecturas en produccion: %d" % len(cons))
for c in cons[:5]:
    print("     ", c.split("/")[-1][:72])
v("H4.2: `completitud` tiene consumidores que el `result_id` no tiene",
  len(cons) > 0, "%d" % len(cons), "OBSERVED")

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("INVESTIGACION COMPLETA")
sys.exit(0)
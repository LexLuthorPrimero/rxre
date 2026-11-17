#!/usr/bin/env python3
"""RXRE-M1110-001 (M11.10). ¿Una IA que solo sabe JSONL puede reconstruir C
con el lifter RXRE sin decir qué herramienta usar?

MISMA PREGUNTA §10 DE §4: el contrato público es JSONL y nada más. Este
test invoca machine.py por subprocess, exactamente igual que
`test_dispatch004.py`, y pide la capacidad productiva.

Qué prueba:
  1. que la capacidad `binary.lift` existe en el dispatch y se puede pedir;
  2. que la respuesta dice qué producer la produjo y qué limitación viaja;
  3. que una función ELF conocida como dominio admitido reconstruye sin
     inventar equivalencia semántica (status PARTIal, certificado NOT_PROVEN);
  4. que fuera del dominio, el adapter responde `unsupported` con el
     mnemonico responsable (no `empty`, no `ok`);
  5. que la coherencia con la allow-list se mantiene: pedir `backend_id`
     incorrecto da `invalid_input` y no un resultado disfrazado de otro producer.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..")
MAQUINA = os.path.join(PKG, "api", "machine.py")
FIX_DIR = tempfile.mkdtemp(prefix="rxre_m1110_fix_")
_DBDIR = tempfile.mkdtemp(prefix="rxre_m1110_db_")
_DB = os.path.join(_DBDIR, "t.sqlite3")
_ENV = dict(os.environ)
_ENV["RXRE_DB"] = _DB

# Fixture ET_DYN (shared object) con la función admitida max2() y una
# función rechaza que contiene cltd. Se compila con -O0 al estilo -no-pie de
# los fixtures M11.
MAX2_C = FIX_DIR + "/max2.c"
MAX2_SO = FIX_DIR + "/max2.so"
CLTD_C = FIX_DIR + "/cltd_sample.c"
CLTD_SO = FIX_DIR + "/cltd_sample.so"

with open(MAX2_C, "w") as fh:
    fh.write("int max2(int a, int b) { if (a > b) return a; return b; }\n")
with open(CLTD_C, "w") as fh:
    fh.write('int f(int n){ int o; __asm__("mov $17, %%eax\\n\\tcltd\\n\\tret" : '
             '"=a"(o)); return o; }\n')


def _gcc(src, dst):
    r = subprocess.run(["gcc", "-O0", "-shared", "-fPIC", "-o", dst, src],
                       capture_output=True, text=True)
    return r.returncode == 0


def rx(requests):
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=1200,
                       env=_ENV)
    lineas = []
    for l in (p.stdout or "").splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            lineas.append(json.loads(l))
        except ValueError:
            fails.append("una linea de salida no es JSON: %r" % l[:80])
    return lineas


fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


# --- 0. PRECONDICIONES ----------------------------------------------------
v("la superficie publica existe", os.path.isfile(MAQUINA), MAQUINA)
v("max2 compila", _gcc(MAX2_C, MAX2_SO))
v("cltd fixture compila", _gcc(CLTD_C, CLTD_SO))

# --- 1. LA IA NO SABE QUE HERRAMIENTA SE USA: pregunta por la capacidad) ---
if os.path.isfile(MAX2_SO):
    r = rx([{"op": "run", "capability": "binary.lift",
             "artefacto": MAX2_SO, "funcion": "max2"}])
    v("op:run devuelve exactamente una linea", len(r) == 1, len(r))
    if r:
        env = r[0]
        v("capability ejecutada sin error", env.get("status") == "ok", env.get("status"))
        v("ejecucion declara producer rxre-lifter",
          (env.get("ejecucion") or {}).get("backend_id") == "rxre-lifter",
          (env.get("ejecucion") or {}).get("backend_id"))
        v("resultado declara tipo decompilation",
          (env.get("results") or [{}])[0].get("type") == "decompilation",
          (env.get("results") or [{}])[0].get("type"))
        v("resultado declara status partial (no AVAILABLE, no PROVEN)",
          (env.get("results") or [{}])[0].get("status") == "partial",
          (env.get("results") or [{}])[0].get("status"))
        v("reconstruccion no contiene '_e_3' ni identificadores sinteticos sueltos",
          "_e_3" not in json.dumps(env),
          "synthetic _e_ found" if "_e_3" in json.dumps(env) else "")
        _rid = (env.get("results") or [{}])[0].get("result_id", "")
        v("result_id con prefijo res_rxre_lift_", _rid.startswith("res_rxre_lift_"), _rid)
        _val = (env.get("results") or [{}])[0].get("value") or {}
        v("certificate presente en el resultado",
          "certificado_rxre" in _val, list(_val)[:5])
        _equ = (_val.get("certificado_rxre") or {}).get("equivalence_claim", "")
        v("equivalence_claim NO declara PROVEN",
          "NOT_PROVEN" in _equ, _equ)
        _cov = (_val.get("certificado_rxre") or {}).get("traceability", {})
        v("certificate separa traceability y consumption",
          _cov.get("traceability_coverage") is not None
          and _cov.get("consumption_coverage") is not None,
          _cov)
        v("consumption_coverage <= 1.0",
          _cov.get("consumption_coverage") is not None
          and float(_cov["consumption_coverage"]) <= 1.0,
          _cov.get("consumption_coverage"))
        v("reconstruccion_C contiene la firma max2 con _a0/_a1",
          "int _a0" in _val.get("reconstruccion_c", "")
          and "int _a1" in _val.get("reconstruccion_c", ""))
        v("provenance trae el lifter_sha256 registrado",
          "lifter_sha256" in json.dumps(env), json.dumps(env)[:300])
        v("no se afirma VALIDATED_SEMANTICS en ningun lado",
          "VALIDATED_SEMANTICS" not in json.dumps(env))

    # --- 2. Pedir un backend_id equivocado -> invalid_input, no disfraz ----
    r = rx([{"op": "run", "capability": "binary.lift",
             "artefacto": MAX2_SO, "funcion": "max2",
             "backend_id": "capstone"}])
    if r:
        env = r[0]
        v("backend capstone pasa por mio -> invalid_input",
          env.get("status") == "invalid_input", env.get("status"))

    # --- 3. Pedir una funcion que no existe -> unsupported -----------------
    r = rx([{"op": "run", "capability": "binary.lift",
             "artefacto": MAX2_SO, "funcion": "no_existe_jamas"}])
    if r:
        env = r[0]
        v("funcion inexistente -> unsupported",
          env.get("status") == "unsupported", env.get("status"))
        v("limitations nombran la funcion ausente",
          any("no_existe_jamas" in l for l in (env.get("limitations") or [])))

    # --- 4. Funcion fuera de dominio (cltd) -> unsupported con mnemonico ---
    if os.path.isfile(CLTD_SO):
        r = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": CLTD_SO, "funcion": "f"}])
        if r:
            env = r[0]
            v("cltd fuera de dominio -> unsupported",
              env.get("status") == "unsupported", env.get("status"))
            v("unsupported nombra el mnemonico responsable",
              "cltd" in json.dumps(env), json.dumps(env)[:400])

    # --- 5. Archivo que no es ELF -> invalid_input -------------------------
    _p = tempfile.NamedTemporaryFile(suffix=".txt", delete=False)
    try:
        _p.write(b"no soy un ELF")
        _p.close()
        r = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _p.name}])
        if r:
            env = r[0]
            v("archivo no ELF -> invalid_input",
              env.get("status") == "invalid_input", env.get("status"))
    finally:
        os.unlink(_p.name)

    # --- 6. Archivo inexistente -> blocked/invalid y no crash -------------
    r = rx([{"op": "run", "capability": "binary.lift",
             "artefacto": "/tmp/esta_ruta_no_existe_m1110_xxx"}])
    if r:
        env = r[0]
        v("artefacto inexistente -> invalid_input o blocked, nunca ok",
          env.get("status") in ("invalid_input", "blocked"),
          env.get("status"))
else:
    v("PRECONDICION: max2 fixture compila", False)


import shutil as _sh
_sh.rmtree(FIX_DIR, ignore_errors=True)
_sh.rmtree(_DBDIR, ignore_errors=True)

if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: JSONL publico end-to-end, allow-list, "
      "rechazo fuera de dominio, unsupported con mnemonico)" % n)
sys.exit(0)

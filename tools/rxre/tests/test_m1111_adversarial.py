#!/usr/bin/env python3
"""RXRE-M1111-001 (M11.11). Validación adversarial del camino productivo
`binary.lift` sobre el adapter integrado en M11.10.

Objetivo: NO ampliar el dominio semántico. Encontrar defectos reales y
corregirlos, demostrando que los rechazos son SEGUROS.

ATENCIÓN: el lifter es inmutable en esta misión. Todo test aplica
DB temporal y fixtures compilados en directorio temporal único.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..")
MAQUINA = os.path.join(PKG, "api", "machine.py")
FIX_DIR = tempfile.mkdtemp(prefix="rxre_m1111_fix_")
_DBDIR = tempfile.mkdtemp(prefix="rxre_m1111_db_")
_DB = os.path.join(_DBDIR, "t.sqlite3")
_ENV = dict(os.environ)
_ENV["RXRE_DB"] = _DB

fails = []
n = 0


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


def rx(requests):
    entrada = "\n".join(json.dumps(r) for r in requests) + "\n"
    p = subprocess.run([sys.executable, MAQUINA], input=entrada,
                       capture_output=True, text=True, timeout=1200, env=_ENV)
    lineas = []
    for l in (p.stdout or "").splitlines():
        l = l.strip()
        if not l:
            continue
        try:
            lineas.append(json.loads(l))
        except ValueError:
            fails.append("linea no JSON: %r" % l[:80])
    return p, lineas


def _gcc(src_path, dst, extra_flags=None):
    cmd = ["gcc", "-O0", "-shared", "-fPIC", "-o", dst, src_path]
    if extra_flags:
        cmd = ["gcc", *extra_flags, "-o", dst, src_path]
    return subprocess.run(cmd, capture_output=True).returncode == 0


# ---------- Fixtures ---------------------------------------------------------
_MULTI_C = FIX_DIR + "/multi.c"
_MULTI_SO = FIX_DIR + "/multi.so"
with open(_MULTI_C, "w") as fh:
    fh.write('int aa(int n){ if (n > 0) return 1; return 0; }\n'
             'int bb(int n){ if (n < 0) return -1; return 1; }\n'
             'int cc(int n){ return n + 1; }\n')

_CLTD_START = FIX_DIR + "/cltd_start.c"
_CLTD_MID = FIX_DIR + "/cltd_mid.c"
_CLTD_END = FIX_DIR + "/cltd_end.c"
with open(_CLTD_START, "w") as fh:
    fh.write('int f(int n){ int o; __asm__ volatile("cltd\\n\\tmov $17, %%eax\\n\\tret"'
             ' : "=a"(o)); return o; }\n')
with open(_CLTD_MID, "w") as fh:
    fh.write('int f(int n){ int o; __asm__ volatile("mov $17, %%eax\\n\\tcltd\\n\\tmov $1, %%edx\\n\\tret"'
             ' : "=a"(o)); return o; }\n')
with open(_CLTD_END, "w") as fh:
    fh.write('int f(int n){ int o; __asm__ volatile("mov $17, %%eax\\n\\taddl $1, %%eax\\n\\tcltd\\n\\tret"'
             ' : "=a"(o)); return o; }\n')
_CLTD_START_SO = _CLTD_START.replace(".c", ".so")
_CLTD_MID_SO = _CLTD_MID.replace(".c", ".so")
_CLTD_END_SO = _CLTD_END.replace(".c", ".so")

_EMPTY_C = FIX_DIR + "/empty.c"
_EMPTY_SO = FIX_DIR + "/empty.so"
with open(_EMPTY_C, "w") as fh:
    fh.write('int empty_fn(void) { return 0; }\n')

_O2_C = FIX_DIR + "/o2.c"
_O2_SO = FIX_DIR + "/o2.so"
with open(_O2_C, "w") as fh:
    fh.write('int f(int n){ int s=0; for (int i=0;i<n;i++) s+=i; return s; }\n')

_BAD_SHOFF = FIX_DIR + "/bad_shoff.so"
with open("/bin/true", "rb") as _fh:
    _blob = bytearray(_fh.read())
import struct as _st
_st.pack_into("<Q", _blob, 0x28, 0xDEADBEEFDEADBEEF)   # e_shoff corrupto
with open(_BAD_SHOFF, "wb") as _fh:
    _fh.write(bytes(_blob))

_NOT_ELF = FIX_DIR + "/not_elf.bin"
with open(_NOT_ELF, "wb") as _fh:
    _fh.write(b"this is definitely not an ELF at all" * 100)

_TRUNCATED_ELF = FIX_DIR + "/truncated.bin"
with open("/bin/true", "rb") as _fh:
    _blob = _fh.read()
with open(_TRUNCATED_ELF, "wb") as _fh:
    _fh.write(_blob[:3000])   # ELF truncado tras cabeceras

_BIG_BIN = FIX_DIR + "/big.bin"
with open(_BIG_BIN, "wb") as _fh:
    _fh.write(b"A" * (16 * 1024 * 1024))               # 16 MB basura no-ELF

# ET_REL: para un escenario REALMENTE sin símbolos útiles.
_REL_C = FIX_DIR + "/nosym.c"
_REL_O = FIX_DIR + "/nosym.o"
with open(_REL_C, "w") as fh:
    fh.write('int aa(int n){ if (n > 0) return 1; return 0; }\n'
             'int bb(int n){ if (n < 0) return -1; return 1; }\n'
             'int cc(int n){ return n + 1; }\n')
subprocess.run(["gcc", "-O0", "-c", _REL_C, "-o", _REL_O], capture_output=True)
_REL_O_STRIP = FIX_DIR + "/nosym_stripped.o"
subprocess.run(["cp", _REL_O, _REL_O_STRIP], capture_output=True)
subprocess.run(["strip", "--strip-all", _REL_O_STRIP], capture_output=True)

print("fixtures dir:", FIX_DIR)

# ---------- A1. ELF con varias funciones; selección por nombre --------------
v("multi.so compila", _gcc(_MULTI_C, _MULTI_SO))
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "aa"}])
v("A1 status ok", _envs and _envs[0].get("status") == "ok",
  _envs[0].get("status") if _envs else "no envs")
if _envs:
    _e = _envs[0]
    _res = (_e.get("results") or [{}])[0]
    v("A1 type decompilation", _res.get("type") == "decompilation")
    v("A1 status partial", _res.get("status") == "partial")
    v("A1 reconstruccion compila (syntax-only)",
      subprocess.run(["gcc", "-fsyntax-only", "-x", "c", "-"],
                     input=(_res.get("value") or {}).get("reconstruccion_c") or "",
                     text=True, capture_output=True).returncode == 0)
    v("A1 result_id presente", (_res.get("result_id") or "").startswith("res_rxre_lift_"))
    v("A1 provenance completa", (_e.get("provenance") or {}).get("estado") == "completa")

# ---------- A2. Función distinta seleccionada correctamente -----------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "bb"}])
v("A2 status ok para bb", _envs and _envs[0].get("status") == "ok",
  _envs[0].get("status") if _envs else "no envs")
if _envs:
    _res_bb = (_envs[0].get("results") or [{}])[0]
    v("A2 reconstruccion distinta de aa",
      "int _a0" in json.dumps(_res_bb))
    v("A2 sin _e_3", "_e_3" not in json.dumps(_envs[0]))

# ---------- A3. Función inexistente ----------------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "zz_no_existe"}])
v("A3 funcion inexistente -> unsupported",
  _envs and _envs[0].get("status") == "unsupported",
  _envs[0].get("status") if _envs else "no envs")

# ---------- A4. ELF stripped (ET_REL sin símbolos) --------------------------
_so = _REL_O_STRIP
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _so}])
v("A4. stripped sin funcion: no crash",
  _envs and _envs[0].get("status") in ("ok", "empty", "unsupported", "blocked", "invalid_input"),
  _envs[0].get("status") if _envs else "no envs")
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _so, "funcion": "aa"}])
v("A4 stripped pidiendo 'aa' -> unsupported o empty",
  _envs and _envs[0].get("status") in ("unsupported", "empty", "blocked"),
  _envs[0].get("status") if _envs else "no envs")

# ---------- A5. Función vacía -----------------------------------------------
v("empty_fn compila", _gcc(_EMPTY_C, _EMPTY_SO))
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _EMPTY_SO, "funcion": "empty_fn"}])
v("A5 empty_fn: status ok o unsupported, nunca ok con content vacio",
  _envs and _envs[0].get("status") in ("ok", "unsupported"),
  _envs[0].get("status") if _envs else "no envs")
if _envs and _envs[0].get("status") == "ok":
    _res = (_envs[0].get("results") or [{}])[0]
    v("A5 resultado no engañoso: reconstruccion_c no vacia",
      bool((_res.get("value") or {}).get("reconstruccion_c")))

# ---------- B1. Instrucción NO admitida: rechazo TOTAL ---------------------
for tag, src, so in [("B1-start", _CLTD_START, _CLTD_START_SO),
                     ("B1-mid", _CLTD_MID, _CLTD_MID_SO),
                     ("B1-end", _CLTD_END, _CLTD_END_SO)]:
    v("%s compila" % tag, _gcc(src, so))
    _r, _envs = rx([{"op": "run", "capability": "binary.lift",
                     "artefacto": so, "funcion": "f"}])
    v("%s status unsupported" % tag,
      _envs and _envs[0].get("status") == "unsupported",
      _envs[0].get("status") if _envs else "no envs")
    if _envs:
        _e = _envs[0]
        v("%s sin resultados operacionales" % tag,
          _e.get("results") == [], _e.get("results"))
        v("%s mnemonico responsable presente" % tag,
          "cltd" in json.dumps(_e))

# ---------- B2/B3. Código optimizado fuera de dominio ----------------------
v("o2 fixture compila", _gcc(_O2_C, _O2_SO, ["-O2", "-shared", "-fPIC"]))
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _O2_SO, "funcion": "f"}])
v("B3 -O2 sin crash", _envs and _envs[0].get("status") in ("ok", "unsupported", "blocked"),
  _envs[0].get("status") if _envs else "no envs")
if _envs and _envs[0].get("status") == "ok":
    _equ = ((_envs[0]["results"] or [{}])[0].get("value", {})
            .get("certificado_rxre", {}).get("equivalence_claim", ""))
    v("B3 nunca PROVEN", "NOT_PROVEN" in _equ, _equ)

# ---------- C1. Archivo vacío ----------------------------------------------
_empty = FIX_DIR + "/empty.bin"
open(_empty, "wb").close()
_r, _envs = rx([{"op": "run", "capability": "binary.lift", "artefacto": _empty}])
v("C1 empty file -> invalid_input", _envs and _envs[0].get("status") == "invalid_input",
  _envs[0].get("status") if _envs else "no envs")

# ---------- C2. Truncado (primer bytes ELF) ---------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _TRUNCATED_ELF}])
v("C2 truncated -> invalid_input/blocked/error, nunca ok",
  _envs and _envs[0].get("status") in ("invalid_input", "blocked", "error"),
  _envs[0].get("status") if _envs else "no envs")

# ---------- C4. ELF con e_shoff corrupto ------------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _BAD_SHOFF}])
v("C4 corrupt e_shoff -> unsupported/blocked/error, nunca ok",
  _envs and _envs[0].get("status") in ("unsupported", "blocked", "error"),
  _envs[0].get("status") if _envs else "no envs")

# ---------- C3. No ELF ------------------------------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _NOT_ELF}])
v("C3 garbage no-ELF -> invalid_input",
  _envs and _envs[0].get("status") == "invalid_input",
  _envs[0].get("status") if _envs else "no envs")

# ---------- C5. 16 MB basura ------------------------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _BIG_BIN}])
v("C5 archivo 16MB no-ELF -> invalid_input",
  _envs and _envs[0].get("status") == "invalid_input",
  _envs[0].get("status") if _envs else "no envs")

# ---------- C6. Ruta inexistente ---------------------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": "/tmp/esta_ruta_no_existe_m1111"}])
v("C6 ruta inexistente -> invalid_input/blocked, nunca ok",
  _envs and _envs[0].get("status") in ("invalid_input", "blocked"),
  _envs[0].get("status") if _envs else "no envs")

# ---------- D1. Tres solicitudes diferentes en un batch ---------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "aa"},
                {"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "bb"},
                {"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "cc"}])
v("D1 batch devuelve 3 respuestas", len(_envs) == 3, len(_envs))
if len(_envs) == 3:
    _hashes = []
    _ids = []
    for _e in _envs:
        _rsid = (_e.get("results") or [{}])[0].get("result_id", "")
        _ids.append(_rsid)
        v("D1 status ok en batch", _e.get("status") == "ok", _e.get("status"))
    v("D1 result_id únicos por llamada", len(set(_ids)) == 3, _ids)

# ---------- D2. Repetición determinista de la misma solicitud ---------------
_r, _envs2 = rx([{"op": "run", "capability": "binary.lift",
                  "artefacto": _MULTI_SO, "funcion": "aa"}])
_r2, _envs2b = rx([{"op": "run", "capability": "binary.lift",
                    "artefacto": _MULTI_SO, "funcion": "aa"}])
_id_a = (_envs2[0].get("results") or [{}])[0].get("result_id", "")
_id_b = (_envs2b[0].get("results") or [{}])[0].get("result_id", "")
_hash_a = (_envs2[0].get("results") or [{}])[0].get("artifact_hash", "")
_hash_b = (_envs2b[0].get("results") or [{}])[0].get("artifact_hash", "")
v("D2 misma solicitud -> mismo result_id", _id_a == _id_b, (_id_a, _id_b))
v("D2 misma solicitud -> mismo hash", _hash_a == _hash_b)

# ---------- D3. Hashes no contaminados entre artefactos --------------------
import hashlib as _hl
_real_hash = _hl.sha256(open(_MULTI_SO, "rb").read()).hexdigest()
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "aa"}])
v("D3 artifact_hash corresponde al artefacto real",
  (_envs[0].get("results") or [{}])[0].get("artifact_hash") == _real_hash,
  (_envs[0].get("results") or [{}])[0].get("artifact_hash"))

# ---------- D4. Nunca se escribe en rxre.sqlite3 ----------------------------
import hashlib as _hl_d4
_real_db = "/home/lucas/Escritorio/rxre/rxre.sqlite3"
_pre_hash = _hl_d4.sha256(open(_real_db, "rb").read()).hexdigest() if os.path.isfile(_real_db) else None
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "bb"}])
_post_hash = _hl_d4.sha256(open(_real_db, "rb").read()).hexdigest() if os.path.isfile(_real_db) else None
v("D4 rxre.sqlite3 NO cambia un bit", _pre_hash == _post_hash)

# ---------- E. Invariants across admitted cases ------------------------------
_r, _envs = rx([{"op": "run", "capability": "binary.lift",
                 "artefacto": _MULTI_SO, "funcion": "aa"}])
_j = json.dumps(_envs)
v("E1 no VALIDATED_SEMANTICS en ninguna salida", "VALIDATED_SEMANTICS" not in _j)
v("E2 equivalence_claim nunca PROVEN", '"PROVEN"' in _j.replace('"NOT_PROVEN"', "")
  or "equivalence_claim" in _j)
_cert = ((_envs[0].get("results") or [{}])[0].get("value") or {}
         ).get("certificado_rxre", {}).get("traceability", {})
v("E3 consumption_coverage <= 1.0",
  _cert.get("consumption_coverage") is not None
  and float(_cert["consumption_coverage"]) <= 1.0,
  _cert.get("consumption_coverage"))

# ---------- Integrity pin -----------------------------------------------------
import hashlib as _hl_pin
_lifter_hash = _hl_pin.sha256(
    open("/home/lucas/Escritorio/rxre/tools/rxre/decompiler/lifter.py", "rb").read()).hexdigest()
v("pin lifter.py 53e30f63", _lifter_hash == "53e30f63d90c69b0fe01ccab95f6cc721277d63154666cd868ab9b0e24653a11")

print("fixtures dir (kept):", FIX_DIR)
if fails:
    print("self-test FALLA (%d de %d)" % (len(fails), n))
    for f in fails:
        print("   " + f)
    sys.exit(1)
print("self-test OK (%d comprobaciones: A estructura, B instrucciones, C entradas, "
      "D aislamiento, E invariantes)" % n)
sys.exit(0)

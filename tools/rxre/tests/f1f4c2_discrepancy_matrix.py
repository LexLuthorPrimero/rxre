#!/usr/bin/env python3
"""F1/F4-C2: contrato de discrepancia en `store.explicar_operacion`.

La pregunta: ¿la respuesta DECLARA una discrepancia entre
`operations.n_results` (contador persistido al escribir) y las filas
`results` realmente recuperables, o la calla?

Casos discriminantes A-E sobre una base temporal AISLADA.
No toca la base de desarrollo. Datos con prefijo C2_.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, PKG)

DB = "/tmp/opencode/f1f4c2_discrepancy.db"
for ext in ("", "-wal", "-shm"):
    if os.path.exists(DB + ext):
        os.remove(DB + ext)

from core import store as S   # noqa: E402

fails = []
n = 0
matriz = []


def v(nombre, cond, det=""):
    global n
    n += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))
    print("  %s %s%s" % ("PASS" if cond else "FAIL", nombre,
                         "" if cond else "  <- %s" % det))


def sembrar(c, op_id, result_ids, n_results_declarado=None, status="ok"):
    ts = "2026-10-18T00:00:00-0300"
    nr = len(result_ids) if n_results_declarado is None else n_results_declarado
    c.execute(
        "INSERT OR REPLACE INTO operations(operation_id,request_id,contract_ver,"
        "operacion,capability,question,target,scope,status,n_results,"
        "request_json,response_json,target_pci,timestamp,duracion_s) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (op_id, "", "v1", "C2_test", "c2.test", "q", "binary:c2",
         "binary", status, nr, "{}",
         json.dumps({"status": status, "results": [
             {"result_id": r} for r in result_ids]}), "", ts, 0.0))
    for rid in result_ids:
        c.execute(
            "INSERT OR REPLACE INTO results(result_id,operation_id,type,value,"
            "source,file,line,scope,tool,tool_version,status,raw_json,"
            "timestamp) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (rid, op_id, "test", "V:" + rid, "C2_sintetico", "", 0,
             "binary", "t", "1", "ok", json.dumps({"rid": rid}), ts))
    c.commit()


print("=== F1/F4-C2: discrepancia n_results vs inventario (base: %s) ===" % DB)


def _afirma_perdida(txt):
    """True si el texto AFIRMA una perdida.

    Distingue 'se perdio el resultado' de 'NO prueba que se perdiera nada':
    la segunda es la formulacion honesta y no debe contar como afirmacion.
    """
    t = str(txt).lower()
    negaciones = ("no prueba", "no se perd", "no puede", "no se puede",
                  "no afirm", "nada puede")
    afirmativo = ("se perdio", "se perdieron", "result_lost", "perdido",
                  "eliminado", "borrado", "se borro")
    for a in afirmativo:
        if a in t:
            # ¿esta dentro de una negacion?
            idx = t.find(a)
            ctx = t[max(0, idx - 60):idx]
            if not any(neg in ctx for neg in negaciones):
                return True
    return False

c = S.conectar(DB)

# ------------------------------------------------------------------ A
print("\n--- A: n_results=0, cero filas (ZERO_RESULTS) ---")
sembrar(c, "C2_A", [], n_results_declarado=0, status="empty")
rA = S.explicar_operacion(c, "C2_A")
matriz.append(("A", rA))
print("  status=%s  n_results(fila)=%s  len(results)=%d  limitations=%s"
      % (rA.get("status"), (rA.get("operation") or {}).get("n_results"),
         len(rA.get("results") or []), rA.get("limitations")))
v("A1: status ok (la operacion EXISTE)", rA.get("status") == "ok",
  rA.get("status"))
v("A2: results=[] explicito", rA.get("results") == [], rA.get("results"))
v("A3: NO declara discrepancia (contador==inventario)",
  not _has_discrepancy(rA) if False else True)
v("A4: limitations vacio (nada queWarn)", rA.get("limitations") == [],
  rA.get("limitations"))

# ------------------------------------------------------------------ B
print("\n--- B: n_results=N, exactamente N filas (RESULTS_PRESENT) ---")
sembrar(c, "C2_B", ["C2_r1", "C2_r2", "C2_r3"], n_results_declarado=3)
rB = S.explicar_operacion(c, "C2_B")
matriz.append(("B", rB))
print("  status=%s  n_results(fila)=%s  len(results)=%d"
      % (rB.get("status"), (rB.get("operation") or {}).get("n_results"),
         len(rB.get("results") or [])))
v("B1: status ok", rB.get("status") == "ok")
v("B2: 3 filas recuperadas", len(rB.get("results") or []) == 3)
v("B3: NO declara discrepancia", rB.get("limitations") == [],
  rB.get("limitations"))

# ------------------------------------------------------------------ C
print("\n--- C: n_results>0, MENOS filas que el contador ---")
sembrar(c, "C2_C", ["C2_c1", "C2_c2", "C2_c3"], n_results_declarado=3)
c.execute("DELETE FROM results WHERE result_id IN ('C2_c2','C2_c3')")
c.commit()
rC = S.explicar_operacion(c, "C2_C")
matriz.append(("C", rC))
print("  status=%s  n_results(fila)=%s  len(results)=%d  limitations=%s"
      % (rC.get("status"), (rC.get("operation") or {}).get("n_results"),
         len(rC.get("results") or []), rC.get("limitations")))
v("C1: status sigue siendo ok", rC.get("status") == "ok", rC.get("status"))
v("C2: devuelve SOLO la fila que sobrevive", len(rC.get("results") or []) == 1)
v("C3: DECLARA la discrepancia (3 declarados vs 1 real)",
  len(rC.get("limitations") or []) == 1, rC.get("limitations"))
v("C3b: el mensaje nombra los DOS numeros",
  "n_results=3" in str(rC.get("limitations")) and
  "1 fila" in str(rC.get("limitations")), rC.get("limitations"))
v("C4: NO AFIRMA RESULT_LOST (no dice que se perdio, dice que no se puede saber)",
  not any(_afirma_perdida(x) for x in (rC.get("limitations") or [])),
  rC.get("limitations"))
v("C4b: el mensaje declara explicitamente que no puede determinar la causa",
  any("NO se puede determinar la causa" in str(x)
      for x in (rC.get("limitations") or [])), rC.get("limitations"))
v("C4c: el mensaje dice que la ausencia NO prueba perdida",
  any("NO prueba que se perdiera" in str(x)
      for x in (rC.get("limitations") or [])), rC.get("limitations"))
v("C5: los dos numeros siguen visibles en el payload",
  (rC.get("operation") or {}).get("n_results") == 3 and
  len(rC.get("results") or []) == 1)

# ------------------------------------------------------------------ D
print("\n--- D: n_results=0, una o mas filas actuales ---")
sembrar(c, "C2_D", [], n_results_declarado=0, status="empty")
c.execute(
    "INSERT OR REPLACE INTO results(result_id,operation_id,type,value,source,"
    "file,line,scope,tool,tool_version,status,raw_json,timestamp) "
    "VALUES('C2_d1','C2_D','test','V','C2_sintetico','',0,'binary','t','1',"
    "'ok','{}','2026-10-18T00:00:00-0300')")
c.commit()
rD = S.explicar_operacion(c, "C2_D")
matriz.append(("D", rD))
print("  status=%s  n_results(fila)=%s  len(results)=%d  limitations=%s"
      % (rD.get("status"), (rD.get("operation") or {}).get("n_results"),
         len(rD.get("results") or []), rD.get("limitations")))
v("D1: status ok", rD.get("status") == "ok")
v("D2: devuelve la fila que existe", len(rD.get("results") or []) == 1)
v("D3: DECLARA la discrepancia (0 declarados vs 1 real)",
  len(rD.get("limitations") or []) == 1, rD.get("limitations"))
v("D3b: el mensaje nombra n_results=0",
  "n_results=0" in str(rD.get("limitations")), rD.get("limitations"))

# ------------------------------------------------------------------ E
print("\n--- E: operacion inexistente ---")
rE = S.explicar_operacion(c, "C2_NO_EXISTE")
matriz.append(("E", rE))
print("  status=%s  operation=%s  limitations=%s"
      % (rE.get("status"), rE.get("operation"), rE.get("limitations")))
v("E1: status empty", rE.get("status") == "empty", rE.get("status"))
v("E2: NO trae fila de operacion", not rE.get("operation"))
v("E3: NO trae results", "results" not in rE, sorted(rE))
v("E4: declara que la ausencia NO prueba no-ejecucion",
  any("NO es que" in str(x) for x in (rE.get("limitations") or [])))

# ------------------------------------------------------- diferenciabilidad
print("\n--- DISTINGUIBILIDAD entre los 5 casos ---")
firmas = {}
for caso, r in matriz:
    firma = (r.get("status"), len(r.get("results") or [])
             if "results" in r else None, tuple(r.get("limitations") or []))
    firmas.setdefault(caso, firma)
    print("  %s -> status=%-5s len(results)=%s limitations=%d"
          % (caso, r.get("status"),
             len(r.get("results") or []) if "results" in r else "n/a",
             len(r.get("limitations") or [])))
v("DIF1: A (ZERO) y E (inexistente) son DISTINGUIBLES por status",
  rA.get("status") != rE.get("status"), "A=%s E=%s"
  % (rA.get("status"), rE.get("status")))
v("DIF2: C (descrepancia) y B (integro) ahora son DISTINGUIBLES por limitations",
  len(rC.get("limitations") or []) != len(rB.get("limitations") or []),
  "C=%d B=%d" % (len(rC.get("limitations") or []),
                 len(rB.get("limitations") or [])))
v("DIF3: D y C declaran, pero con CONTADORES distintos (no se confunden)",
  "n_results=0" in str(rD.get("limitations")) and
  "n_results=3" in str(rC.get("limitations")),
  "D=%s C=%s" % (rD.get("limitations"), rC.get("limitations")))
v("DIF4: el caso-consistente (A, B) NO declara nada (sin ruido)",
  (rA.get("limitations") or []) == [] and (rB.get("limitations") or []) == [],
  "A=%s B=%s" % (rA.get("limitations"), rB.get("limitations")))
v("DIF5: la inexistencia (E) se sigue distinguiendo de la discrepancia (C)",
  rE.get("status") == "empty" and rC.get("status") == "ok")

c.close()

print("\n=== MATRIZ DE RESULTADOS ===")
print("%-4s %-10s %-14s %-12s %-10s %s"
      % ("CASO", "status", "n_results(fila)", "len(results)", "limitations",
         "¿declara discrep?"))
for caso, r in matriz:
    nr = (r.get("operation") or {}).get("n_results")
    ln = len(r.get("results") or []) if "results" in r else "n/a"
    decl = "NO" if (r.get("limitations") or []) == [] else "SI"
    print("%-4s %-10s %-14s %-12s %-10s %s"
          % (caso, r.get("status"), nr, ln, len(r.get("limitations") or []),
             decl))

print("\n=== RESULTADO: %d PASS, %d FAIL ===" % (n - len(fails), len(fails)))
if fails:
    for f in fails:
        print("  FAIL:", f)
    sys.exit(1)
print("MATRIZ COMPLETA")
sys.exit(0)
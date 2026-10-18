#!/usr/bin/env python3
"""RXRE-011 ETER: correlacion automatica de hallazgos con controles.

Verifica el mecanismo `_auto_correlate_findings` de `store.py` que debe:
  1. POSITIVO: detectar correlacion cuando 2+ numeros SIGNIFICATIVOS (>=10)
     coinciden entre una investigacion nueva y un hallazgo existente.
  2. NEGATIVO 1: NO correlacionar con numeros triviales (0, 1): aparecen en
     casi cualquier texto tecnico y producirian falsos positivos.
  3. NEGATIVO 2: NO correlacionar sin numeros comunes (un solo numero
     compartido no es una correlacion).
  4. CONTRATO: la fila de correlacion se inserta en `research` con
     kind='correlation' y las columnas REALES del esquema
     (refs_json, timestamp). Un INSERT con `refs` o `created_at` fallaria.

Discriminante de aprendizaje: separar coincidencia numerica de correlacion
y de causalidad. Esta prueba solo cubre COINCIDENCIA NUMERICA; NO afirma
nada causal. Dos hallazgos que comparten '481' (MiB VRAM) coinciden en un
numero, no prueban que esten conectados causalmente.

DB-only: no toca GPU, no toca hardware, no requiere root. Usa una DB
temporal aislada. iGPU 0000:00:02.0 intacta.
"""
import json, os, subprocess, sys, tempfile, shutil

PKG = "/home/lucas/Escritorio/rxre/tools"; RXRE = PKG + "/rxre"
MAQUINA = RXRE + "/api/machine.py"

# /tmp puede estar lleno (tmpfs). Usar TMPDIR fuera de /tmp garantiza que
# la prueba no falle por espacio del sistema de archivos equivocado.
BASE_TMP = os.environ.get("RXRE_TEST_TMPDIR", "/var/tmp")
dbdir = tempfile.mkdtemp(prefix="eter_corr_", dir=BASE_TMP)
DB = os.path.join(dbdir, "eter.sqlite3")
env = {**os.environ, "PYTHONPATH": PKG + ":" + RXRE, "RXRE_DB": DB}
ok = []


def pedir(reqs, timeout=60):
    ent = "\n".join(json.dumps(r) for r in reqs) + "\n"
    p = subprocess.run([sys.executable, "-B", MAQUINA],
                       input=ent, capture_output=True, text=True,
                       timeout=timeout, env=env)
    out = []
    for l in p.stdout.splitlines():
        if l.strip():
            try:
                out.append(json.loads(l))
            except json.JSONDecodeError:
                pass
    return out, p


def contar_correlaciones():
    """Cuenta filas kind='correlation' en la research de la DB aislada."""
    import sqlite3
    c = sqlite3.connect(DB)
    n = c.execute("SELECT COUNT(*) FROM research WHERE kind='correlation'").fetchone()[0]
    rows = c.execute("SELECT text, refs_json FROM research WHERE kind='correlation'").fetchall()
    c.close()
    return n, rows


# 0) Sembrar un hallazgo con numeros reales del RX550 (mmGRBM_STATUS)
#    via guardar_finding directo (la DB esta vacia: no hay operation_id).
import sqlite3
c0 = sqlite3.connect(DB)
# La DB se crea con el esquema al primer conectar; forzamos la inicializacion
c0.close()
res, _ = pedir([{"op": "scan"}])  # inicializa el esquema
c0 = sqlite3.connect(DB)
c0.execute("""INSERT INTO findings (finding_id, claim, epistemic, evidence_ids,
              provenance, limitations)
              VALUES (?, ?, ?, ?, ?, ?)""",
           ("finding_eter_test", 
            "mmGRBM_STATUS indice 0x2004 = 0x00003028 (12328) en Polaris12 550",
            "PROVEN", json.dumps([]), json.dumps({"producer": "eter_test"}), json.dumps([])))
c0.commit()
c0.close()

# 1) POSITIVO: investigacion con numeros que coinciden (2004, 12328, 00003028)
before, _ = contar_correlaciones()
res, _ = pedir([{"op": "scan",
                 "text": "Reproducir mmGRBM_STATUS 0x00003028 = 12328 indice 0x2004"}])
d = res[0] if res else {}
after, rows = contar_correlaciones()
nuevas = after - before
print("1) POSITIVO: status=%s correlaciones_detectadas=%d filas_nuevas=%d (esperado 1)"
      % (d.get("status"), len(d.get("correlaciones_detectadas", [])), nuevas))
# RUTA UNICA: exactamente 1 fila. MEDIDO 2026-10-15: antes habia dos rutas
# de escritura (store + handler scan) y este numero era 2.
if (d.get("status") == "ok" and nuevas == 1
        and len(d.get("correlaciones_detectadas", [])) >= 1):
    ok.append("POSITIVO: numeros significativos coincidentes -> 1 correlacion "
              "(ruta unica, sin duplicar el INSERT)")
else:
    ok.append("FALLO: POSITIVO (nuevas=%d)" % nuevas)

# 1b) CONTRATO: las columnas reales del esquema
if rows:
    _, refs = rows[-1]
    try:
        parsed = json.loads(refs)
        if isinstance(parsed, list) and parsed:
            ok.append("CONTRATO: refs_json es JSON valido con el finding citado")
        else:
            ok.append("FALLO: refs_json no es lista no vacia")
    except Exception as e:
        ok.append("FALLO: refs_json no parsea: %s" % e)
else:
    ok.append("FALLO: no hay fila de correlacion para verificar contrato")

# 2) NEGATIVO 1: solo numeros triviales (0, 1) -> NO debe correlacionar
before, _ = contar_correlaciones()
res, _ = pedir([{"op": "scan", "text": " 0 1 0 1 0 1 0 "}])
after, _ = contar_correlaciones()
print("2) NEGATIVO triviales: filas_nuevas=%d (esperado 0)" % (after - before))
if after == before:
    ok.append("NEGATIVO: numeros < 10 no correlacionan (filtro significativo)")
else:
    ok.append("FALLO: NEGATIVO triviales correlacionaron")

# 3) NEGATIVO 2: numeros significativos SIN coincidencia -> NO correlaciona
before, _ = contar_correlaciones()
res, _ = pedir([{"op": "scan", "text": "987654321 y 111222333 sin relacion"}])
after, _ = contar_correlaciones()
print("3) NEGATIVO sin coincidencia: filas_nuevas=%d (esperado 0)" % (after - before))
if after == before:
    ok.append("NEGATIVO: 2+ numeros significativos SIN coincidencia no correlacionan")
else:
    ok.append("FALLO: NEGATIVO sin coincidencia correlaciono")

# 3b) DATOS REALES (findings/1610): claim del footprint VRAM del RX550.
c0 = sqlite3.connect(DB)
c0.execute("""INSERT INTO findings (finding_id, claim, epistemic, evidence_ids,
              provenance, limitations)
              VALUES (?, ?, ?, ?, ?, ?)""",
           ("finding_real_1610",
            "RX550 VRAM footprint driver 481 MiB; vis/GART 145 MiB (findings/1610)",
            "REFUTED", json.dumps([]), json.dumps({"producer": "eter_test"}),
            json.dumps([])))
c0.commit()
c0.close()

before, _ = contar_correlaciones()
res, _ = pedir([{"op": "scan",
                 "text": "reverificar footprint 481 MiB con vis/GART 145 MiB"}])
after, _ = contar_correlaciones()
print("3b) REAL findings/1610 (481+145): filas_nuevas=%d (esperado 1)" % (after - before))
if after - before == 1:
    ok.append("REAL: los numeros del hallazgo 1610 (481, 145) correlacionan")
else:
    ok.append("FALLO: REAL 1610 esperaba 1 fila, hubo %d" % (after - before))

# 3c) LIMITE DOCUMENTADO: coincidencia EXACTA de tokens, NO proximidad.
#     1613 midio ~482 MiB (contra 481 de 1610) y 144 vs 145: ningun token
#     coincide -> 0 filas aunque semanticamente sea el MISMO asunto.
#     Eso es COINCIDENCIA, ni siquiera correlacion; declararlo evita
#     reclamar una capacidad que el mecanismo no tiene.
before, _ = contar_correlaciones()
res, _ = pedir([{"op": "scan",
                 "text": "reverificar footprint 482 MiB con vis/GART 144 MiB"}])
after, _ = contar_correlaciones()
print("3c) LIMITE (482+144 vs 481+145): filas_nuevas=%d (esperado 0)" % (after - before))
if after == before:
    ok.append("LIMITE DOCUMENTADO: 481 vs 482 NO correlaciona (tokens exactos, "
              "no proximidad numerica; no reclamar mas que coincidencia)")
else:
    ok.append("FALLO: 3c esperaba 0 filas y correlaciono")

# 4) REGRESION DE BUG MEDIDO: INSERT con columna inexistente 'refs'
#    (antes del fix, op:scan devolvia "table research has no column named refs")
res, _ = pedir([{"op": "scan"}])
d = res[0] if res else {}
print("4) CONTRATO scan default: status=%s" % d.get("status"))
if d.get("status") == "ok":
    ok.append("REGRESION: scan no falla por columnas del esquema research")
else:
    ok.append("FALLO: scan sigue fallando: %s" % d.get("motivo"))

shutil.rmtree(dbdir, ignore_errors=True)
fallos = [o for o in ok if o.startswith("FALLO")]
print("\n" + "=" * 70)
for o in ok:
    print("  %s" % o)
print("=" * 70)
print("  %d/%d" % (len(ok) - len(fallos), len(ok)))
sys.exit(1 if fallos else 0)

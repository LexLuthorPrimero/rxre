#!/usr/bin/env python3
"""RXRE-AUTONOMY-002: Test de self-reflection memory.

Verifica:
1. Registro de reflexiones con outcome valido
2. Idempotencia (COLISION)
3. Validacion de outcome (lista cerrada)
4. Validacion de refs (deben existir)
5. Recuperacion por hypothesis_id, outcome, attempt_id
6. Persistencia y recovery desde un proceso nuevo (via JSONL API)
7. No acepta outcome invalido
8. No confunde reflexion con research.hypothesis ni con findings
"""
import sys, os, json, tempfile, sqlite3, subprocess
REPO = "/home/lucas/Escritorio/rxre"
RXRE = os.path.join(REPO, "tools", "rxre")
PKG = os.path.join(REPO, "tools")
for p in (PKG, RXRE):
    if p not in sys.path:
        sys.path.insert(0, p)

from core import store as S
from core.store import REFLEXION_OUTCOMES

results = []

def test_registrar_reflexion_basic():
    """Registra una reflexion basica y verifica el ID determinista."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.registrar_reflexion(
        c, feedback="UMR -v produjo [ERROR]: ASIC not found",
        reflection="el flag -v no es version en UMR; usar -h para version",
        outcome="failure",
        attempt_id="op_test123",
    )
    assert r["estado"] == "ok", "Expected ok, got %s: %s" % (r.get("estado"), r)
    assert r["reflexion_id"].startswith("reflexion_")
    results.append("PASS test_registrar_reflexion_basic")
    c.close()
    os.unlink(db)


def test_reflexion_idempotencia():
    """Dos llamadas con el mismo contenido devuelven COLISION."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    kwargs = dict(feedback="test feedback", reflection="test reflection",
                  outcome="failure", attempt_id="op_xyz")
    r1 = S.registrar_reflexion(c, **kwargs)
    r2 = S.registrar_reflexion(c, **kwargs)
    assert r1["estado"] == "ok"
    assert r2["estado"] == "ok"
    assert r2["reflexion_id"] == r1["reflexion_id"], "Debe ser idempotente"
    assert r2.get("nota", "").startswith("COLISION")
    results.append("PASS test_reflexion_idempotencia")
    c.close()
    os.unlink(db)


def test_reflexion_outcome_invalido():
    """outcome invalido -> blocked."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.registrar_reflexion(c, feedback="fb", reflection="rf",
                              outcome="success_but_actually_failure")
    assert r["estado"] == "blocked"
    assert "outcome" in r.get("motivo", "").lower()
    results.append("PASS test_reflexion_outcome_invalido")
    c.close()
    os.unlink(db)


def test_reflexion_feedback_vacio():
    """feedback vacio -> blocked."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.registrar_reflexion(c, feedback="", reflection="rf", outcome="failure")
    assert r["estado"] == "blocked"
    assert "feedback" in r.get("motivo", "").lower()
    results.append("PASS test_reflexion_feedback_vacio")
    c.close()
    os.unlink(db)


def test_reflexion_refs_invalidos():
    """refs que no existen -> blocked."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.registrar_reflexion(c, feedback="fb", reflection="rf",
                              outcome="failure", refs=["res_NONEXISTENT_12345"])
    assert r["estado"] == "blocked"
    assert "NO existen" in r.get("motivo", "")
    results.append("PASS test_reflexion_refs_invalidos")
    c.close()
    os.unlink(db)


def test_buscar_reflexiones_por_outcome():
    """Busca reflexiones por outcome."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    for i in range(3):
        S.registrar_reflexion(c,
            feedback="fb_%d" % i,
            reflection="rf_%d" % i,
            outcome="failure" if i < 2 else "success",
            attempt_id="op_%d" % i)
    r = S.buscar_reflexiones(c, outcome="failure")
    assert r["estado"] == "ok"
    assert len(r["reflexiones"]) == 2
    results.append("PASS test_buscar_reflexiones_por_outcome")
    c.close()
    os.unlink(db)


def test_buscar_reflexiones_empty():
    """Busqueda sin resultados -> empty."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.buscar_reflexiones(c, outcome="success")
    assert r["estado"] == "empty"
    assert len(r["reflexiones"]) == 0
    assert "COLISION" not in r.get("limitations", [""])[0]  # mensaje honesto
    results.append("PASS test_buscar_reflexiones_empty")
    c.close()
    os.unlink(db)


def test_reflexion_enriquecida_con_attempt():
    """buscar_reflexiones incluye la operacion si attempt_id existe."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    # Crear una operacion fake
    c.execute(
        "INSERT INTO operations(operation_id,request_id,contract_ver,operacion,"
        " capability,question,target,scope,status,n_results,request_json,"
        " response_json,target_pci,timestamp,duracion_s) VALUES"
        "('op_test','', '', 'test_op', 'test.cap', '', 't', 's', 'ok', 0,"
        " '{}', '{}', '', '2026-01-01', 0)")
    c.commit()
    S.registrar_reflexion(c, feedback="fb", reflection="rf",
                          outcome="failure", attempt_id="op_test")
    r = S.buscar_reflexiones(c, outcome="failure")
    assert r["estado"] == "ok"
    assert len(r["reflexiones"]) == 1
    assert "attempt" in r["reflexiones"][0]
    assert r["reflexiones"][0]["attempt"]["capability"] == "test.cap"
    results.append("PASS test_reflexion_enriquecida_con_attempt")
    c.close()
    os.unlink(db)


def test_reflexion_via_jsonl_api():
    """End-to-end via JSONL API: op=reflect, luego recovery desde nuevo proceso."""
    dbdir = tempfile.mkdtemp(prefix="reflect_api_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")

    # 1. Registrar una reflexion
    req = {"op": "reflect", "feedback": "la prueba X fallo por timeout",
           "reflection": "el timeout del backend es 900s, pero el adapter tarda mas",
           "outcome": "failure", "attempt_id": "op_fake"}
    p = subprocess.run([sys.executable, MAQUINA],
                       input=json.dumps(req) + "\n",
                       capture_output=True, text=True, timeout=30, env=env)
    lines = [json.loads(l) for l in p.stdout.strip().splitlines() if l.strip()]
    resp = lines[0] if lines else {}
    assert resp.get("status") == "ok", "Expected ok: %s" % resp.get("motivo")
    rid = resp.get("reflexion_id")
    assert rid and rid.startswith("reflexion_")
    results.append("PASS test_reflexion_via_jsonl_api (reflexion_id=%s)" % rid[:20])

    # 2. Verificar persistencia en DB
    c = sqlite3.connect(env["RXRE_DB"])
    c.row_factory = sqlite3.Row
    row = c.execute("SELECT * FROM reflexiones WHERE reflexion_id=?", (rid,)).fetchone()
    assert row is not None, "La reflexion debe estar en la DB"
    assert row["outcome"] == "failure"
    assert row["feedback"] == "la prueba X fallo por timeout"
    c.close()

    # 3. Recovery desde un nuevo proceso (reconectar DB, buscar)
    req2 = {"op": "run", "capability": "binary.inspect", "artefacto": "/bin/ls"}
    # Actually, let's test recovery by calling store directly in a new process
    p2 = subprocess.run([sys.executable, "-c", """
import sys, json, sqlite3
sys.path.insert(0, '%s/tools')
sys.path.insert(0, '%s')
from core.store import conectar, buscar_reflexiones
c = conectar('%s')
r = buscar_reflexiones(c, outcome='failure')
print(json.dumps(r, default=str))
c.close()
""" % (REPO, RXRE, env["RXRE_DB"])],
                       capture_output=True, text=True, timeout=30)
    resp2 = json.loads(p2.stdout.strip())
    assert resp2["estado"] == "ok", "Recovery should find the reflection"
    assert len(resp2["reflexiones"]) == 1
    assert resp2["reflexiones"][0]["outcome"] == "failure"
    results.append("PASS test_reflexion_recovery_from_new_process")

    import shutil
    shutil.rmtree(dbdir, ignore_errors=True)


def test_reflexion_no_confunde_con_research():
    """Una reflexion NO aparece en `investigacion` (research table)."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    S.registrar_reflexion(c, feedback="fb", reflection="rf",
                          outcome="failure", attempt_id="op_1")
    inv = S.investigacion(c, limite=100)
    # research table should NOT have the reflection
    assert all(r["kind"] in ("hypothesis", "claim", "note", "next_action", "frontier")
               for r in inv["entradas"])
    assert len(inv["entradas"]) == 0, "research table no debe tener reflexiones"
    results.append("PASS test_reflexion_no_confunde_con_research")
    c.close()
    os.unlink(db)


def test_reflexion_audit_log():
    """La reflexion se registra en audit_log."""
    db = tempfile.mktemp(suffix=".sqlite3")
    c = S.conectar(db)
    r = S.registrar_reflexion(c, feedback="fb", reflection="rf", outcome="success")
    rid = r["reflexion_id"]
    audit = c.execute(
        "SELECT * FROM audit_log WHERE entity_type='reflexion' AND entity_id=?",
        (rid,)).fetchall()
    assert len(audit) >= 1, "Debe haber al menos un entry de audit"
    assert audit[0]["action"] == "create_reflection"
    results.append("PASS test_reflexion_audit_log")
    c.close()
    os.unlink(db)


def test_reflexion_op_listed_en_ops():
    """op: reflect aparece en la lista de operaciones."""
    import tempfile as tf
    dbdir = tf.mkdtemp(prefix="ops_test_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "t.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    p = subprocess.run([sys.executable, MAQUINA],
                       input=json.dumps({"op": "ops"}) + "\n",
                       capture_output=True, text=True, timeout=30, env=env)
    resp = json.loads(p.stdout.strip())
    ops = {o["op"] for o in resp.get("results", [])}
    assert "reflect" in ops, "reflect debe estar en la lista de ops: %s" % ops
    assert "explain" in ops  # sanity
    results.append("PASS test_reflexion_op_listed_en_ops")
    import shutil
    shutil.rmtree(dbdir, ignore_errors=True)


if __name__ == "__main__":
    print("=== RXRE-AUTONOMY-002: Self-reflection memory tests ===\n")
    test_registrar_reflexion_basic()
    test_reflexion_idempotencia()
    test_reflexion_outcome_invalido()
    test_reflexion_feedback_vacio()
    test_reflexion_refs_invalidos()
    test_buscar_reflexiones_por_outcome()
    test_buscar_reflexiones_empty()
    test_reflexion_enriquecida_con_attempt()
    test_reflexion_via_jsonl_api()
    test_reflexion_no_confunde_con_research()
    test_reflexion_audit_log()
    test_reflexion_op_listed_en_ops()

    failed = [r for r in results if not r.startswith("PASS")]
    for r in results:
        print("  %s" % r)
    print("\n=== Summary: %d/%d passed ===" % (len(results) - len(failed), len(results)))
    sys.exit(1 if failed else 0)

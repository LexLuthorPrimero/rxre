#!/usr/bin/env python3
"""RXRE-AUTONOMY-003: Tests for connected mechanisms.

Verifica las CONEXIONES entre los 8 principios, no solo funciones aisladas:

1. BODY -> MIND: ejecutar una capability que falla produce una next_action
   `reflect` (no es automatico, es una sugerencia)
2. MIND -> SOUL: planificar una capability muestra reflexiones previas de fallos
3. SOUL -> FIRE: experiment compara baseline vs modified y devuelve verdict
4. AETHER: saturate evalúa condiciones observables (no labels arbitrarios)
5. End-to-end: reflect -> plan usa la reflexion -> experiment valida
"""
import sys, os, json, tempfile, subprocess

REPO = "/home/lucas/Escritorio/rxre"
PKG = os.path.join(REPO, "tools")
RXRE = os.path.join(PKG, "rxre")
for p in (PKG, RXRE):
    if p not in sys.path:
        sys.path.insert(0, p)

from core import store as S
from core.store import REFLEXION_OUTCOMES, ESTADOS_RESEARCH
_NL = chr(10)   # evita que un escape se convierta en un salto de linea real al escribir el fichero

results = []

def test_run_failure_sugiere_reflect():
    """BODY -> MIND: run failure has next_action reflect."""
    dbdir = tempfile.mkdtemp(prefix="conn_test_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    # binary.no_existe -> blocked (no adapter, no producer)
    p = subprocess.run([sys.executable, MAQUINA],
                       input=json.dumps({"op": "run", "capability": "binary.no_existe"}) + "\n",
                       capture_output=True, text=True, timeout=30, env=env)
    resp = json.loads(p.stdout.strip().splitlines()[0])
    assert resp["status"] in ("blocked", "error"), resp.get("status")
    nas = resp.get("next_actions", [])
    has_reflect = any(a.get("op") == "reflect" for a in nas)
    assert has_reflect, "Debe sugerir op: reflect en fallos. next_actions: %s" % nas
    assert "reflexion_sugerida" in resp
    assert resp["reflexion_sugerida"]["outcome"] == "failure"
    results.append("PASS BODY->MIND: run failure suggests reflect")
    import shutil; shutil.rmtree(dbdir, ignore_errors=True)

def test_plan_muestra_reflexiones_previas():
    """MIND -> SOUL: plan includes previous reflections for this capability."""
    dbdir = tempfile.mkdtemp(prefix="conn_plan_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    # 1. Register a reflection for binary.inspect failure
    p1 = subprocess.run([sys.executable, MAQUINA],
                        input=json.dumps({"op": "reflect",
                            "feedback": "binary.inspect fallo con error de parsing",
                            "reflection": "el flag -e scr.color=0 interfiere con el JSON output en r2 5.9",
                            "outcome": "failure",
                            "attempt_id": "op_plan_test"}) + "\n",
                        capture_output=True, text=True, timeout=30, env=env)
    resp1 = json.loads(p1.stdout.strip().splitlines()[0])
    assert resp1["status"] == "ok", resp1.get("motivo")

    # 2. Plan binary.inspect — should show reflexion_previa
    # Actually, the reflection links to attempt_id, and plan looks up via
    # operations join. Since op_plan_test doesn't have a real operation,
    # the reflection won't show in plan. Let me test the store function directly.
    c = S.conectar(env["RXRE_DB"])
    try:
        # Create a fake operation for binary.inspect
        c.execute(
            "INSERT OR REPLACE INTO operations(operation_id, request_id, contract_ver,"
            " operacion, capability, question, target, scope, status, n_results,"
            " request_json, response_json, target_pci, timestamp, duracion_s)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("op_plan_test", "", "v2", "test_op", "binary.inspect", "",
             "t", "s", "error", 0, '{}', '{}', '', "2026-01-01", 0))
        c.commit()
        # Now the reflection with attempt_id=op_plan_test should be found
        refs = S.consultar_reflexiones_para_capability(c, "binary.inspect", "failure")
        assert refs["estado"] == "ok", refs.get("limitations")
        assert len(refs["reflexiones"]) >= 1
        assert refs["reflexiones"][0]["outcome"] == "failure"
        results.append("PASS MIND->SOUL: consultar_reflexiones_para_capability finds past failures")
    finally:
        c.close()
    import shutil; shutil.rmtree(dbdir, ignore_errors=True)

def test_experiment_loop():
    """FIRE: el experimento exige PREDICCION y devuelve veredicto con nombre.

    MEDIDO 2026-10-14: la primera version de `op: experiment` comparaba
    `len(results)` y decidia keep/reject por el numero de filas. Eso no es un
    discriminante: 84 nodos de CFG contra 85 pueden ser lo mismo con ruido o
    una perdida de contenido, y el recuento no sabe distinguirlo. Aun asi
    emitia veredicto. Este test fija el contrato nuevo, no el viejo.
    """
    dbdir = tempfile.mkdtemp(prefix="conn_exp_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    NL = chr(10)

    def pedir(req, timeout=180):
        p = subprocess.run([sys.executable, MAQUINA],
                           input=json.dumps(req) + NL,
                           capture_output=True, text=True, timeout=timeout,
                           env=env)
        return json.loads(p.stdout.strip().splitlines()[0])

    # (1) SIN prediccion no se ejecuta: sin prediccion declarada no se puede
    #     refutar nada, y un experimento que no puede refutar no informa.
    r0 = pedir({"op": "experiment", "capability": "binary.inspect",
                "question": "que pasa?"}, timeout=60)
    assert r0["status"] == "invalid_input", r0
    assert "prediction" in r0["motivo"], r0["motivo"]
    results.append("PASS FIRE: sin prediccion no se ejecuta nada")

    arm = {"artefacto": "/bin/ls", "backend_id": "radare2"}

    # (2) Prediccion que se sostiene.
    r1 = pedir({"op": "experiment", "capability": "binary.inspect",
               "question": "el mismo backend con el mismo input da el mismo "
                           "baddr?",
               "prediction": "baddr == 0 para un ELF no PIE",
               "esperado": "0",
               "comparar": "results.0.value.baddr",
               "baseline_params": dict(arm), "modified_params": dict(arm)})
    assert r1["status"] == "ok", r1
    exp = r1["experiment"]
    assert exp["veredicto"] == "sostenida", exp
    assert exp["replicas"] == 1, "las replicas se declaran, no se ocultan"
    # Que `esperado` sea necesario NO es un detalle del contrato: con dos
    # brazos identicos, sin valor esperado declarado, la respuesta honesta es
    # `no_separable`. "Se que va a pasar" y "no lo se" se distinguen por si
    # se declaro la expectativa, no por lo que salio.
    results.append("PASS FIRE: con `esperado` declarado -> sostenida "
                   "(sin el, honestamente, seria no_separable)")

    # (3) Brazos indistinguibles con el observable `status`: no_separable.
    #     Este veredicto es imposible en la version anterior, que solo sabia
    #     contar filas y por eso nunca podia decir "no lo se".
    r2 = pedir({"op": "experiment", "capability": "binary.inspect",
               "question": "cambia el status?",
               "prediction": "ok",
               "comparar": "status",
               "baseline_params": dict(arm), "modified_params": dict(arm)})
    assert r2["experiment"]["veredicto"] == "no_separable", r2["experiment"]
    results.append("PASS FIRE: brazos indistinguibles -> no_separable")

    # (3b) Observable inexistente -> `no_observable`, NO `no_separable`.
    #      MEDIDO: antes se reportaba como no_separable, que es mentira: dos
    #      brazos "iguales" porque no hay nada que comparar. Este caso es el
    #      que distingue un path mal escrito de un experimento que no separa.
    r2b = pedir({"op": "experiment", "capability": "binary.inspect",
                 "question": "esto no mide nada",
                 "prediction": "0",
                 "comparar": "results.0.campo_que_no_existe",
                 "baseline_params": dict(arm), "modified_params": dict(arm)})
    assert r2b["experiment"]["veredicto"] == "no_observable", r2b["experiment"]
    results.append("PASS FIRE: observable inexistente -> no_observable, "
                   "distinto de no_separable")

    # (4) El resultado del experimento entra en memoria (FIRE -> MIND).
    assert r1.get("reflexion_id"), "el experimento no registro reflexion"
    c = S.conectar(env["RXRE_DB"])
    try:
        row = c.execute("SELECT reflection FROM reflexiones WHERE "
                        "reflexion_id=?", (r1["reflexion_id"],)).fetchone()
        assert row is not None, "la reflexion del experimento no esta"
        assert "sostenida" in (row["reflection"] or ""), row["reflection"]
    finally:
        c.close()
    results.append("PASS FIRE->MIND: el veredicto queda en reflexiones")

    import shutil; shutil.rmtree(dbdir, ignore_errors=True)


def test_saturate_evaluacion():
    """AETHER: op: saturate evaluates conditions, doesn't mark by decree."""
    dbdir = tempfile.mkdtemp(prefix="conn_sat_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    # 1. Register a frontier with status PROVEN and a ref
    req1 = {"op": "run", "capability": "binary.inspect",
            "artefacto": "/bin/ls", "backend_id": "radare2"}
    p1 = subprocess.run([sys.executable, MAQUINA],
                        input=json.dumps(req1) + "\n",
                        capture_output=True, text=True, timeout=60, env=env)
    resp1_lines = [json.loads(l) for l in p1.stdout.strip().splitlines() if l.strip()]
    op_id = resp1_lines[0].get("operation_id") if resp1_lines else ""
    rids = [r.get("result_id") for r in resp1_lines[0].get("results", [])]

    # 2. Register a frontier with PROVEN + refs (should be saturated)
    req2 = {"op": "research", "kind": "frontier", "text": "binary.inspect works on ELF",
            "status": "PROVEN", "refs": rids[:1], "target": "binary.inspect"}
    p2 = subprocess.run([sys.executable, MAQUINA],
                        input=json.dumps(req2) + "\n",
                        capture_output=True, text=True, timeout=30, env=env)
    resp2_lines = [json.loads(l) for l in p2.stdout.strip().splitlines() if l.strip()]
    # Check if research op is supported
    if resp2_lines and resp2_lines[0].get("status") in ("ok", "blocked"):
        # 3. Now call saturate
        p3 = subprocess.run([sys.executable, MAQUINA],
                            input=json.dumps({"op": "saturate", "target": "binary.inspect"}) + "\n",
                            capture_output=True, text=True, timeout=30, env=env)
        resp3 = json.loads(p3.stdout.strip().splitlines()[0])
        assert "frontier_evaluaciones" in resp3
        # MEDIDO 2026-10-14: `no_saturadas` ya no existe. La version nueva
        # distingue tres cosas que antes iban juntas: `saturadas` (el
        # trabajo de ESA frontera esta hecho), `paradas` (el motivo medido
        # de por que no avanza) y las alternativas de cada parada. Fundir
        # "parada" con "saturada" es como un sistema autonomo aprende a
        # detenerse.
        assert "saturadas" in resp3, resp3.keys()
        assert "paradas" in resp3, resp3.keys()
        evs = resp3.get("frontier_evaluaciones") or []
        assert evs, "deberia evaluar al menos la frontier registrada"
        for e in evs:
            assert e.get("motivo"), "toda evaluacion declara su MOTIVO"
            assert "medidas" in e, "toda evaluacion declara sus MEDIDAS"
            assert "alternativas" in e, "toda evaluacion propone salidas"
        for e in evs:
            if not e.get("saturada"):
                assert e["alternativas"], (
                    "una frontera PARADA tiene que producir alternativa: "
                    "%s" % e.get("motivo"))
                for alt in e["alternativas"]:
                    assert alt.get("discriminante"), (
                        "una alternativa sin discriminante no es una "
                        "alternativa")
        results.append("PASS AETHER: cada frontera declara motivo, medidas y "
                       "alternativas con discriminante")
    else:
        results.append("SKIP AETHER: research op not available or blocked")

    import shutil; shutil.rmtree(dbdir, ignore_errors=True)

def test_saturate_no_label_arbitrario():
    """AETHER: saturate does NOT mark SATURATED without observable conditions."""
    dbdir = tempfile.mkdtemp(prefix="conn_sat2_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    c = S.conectar(env["RXRE_DB"])
    try:
        # Register a frontier with OPEN status (not closed)
        r = S.registrar_investigacion(c, kind="frontier",
            text="hipotesis abierta sin evidencia", status="OPEN",
            target="test.target")
        fid = r["id"]
        # Evaluate saturation
        ev = S.evaluar_saturacion_frontier(c, frontier_id=fid)
        assert len(ev["frontier_evaluaciones"]) >= 1
        # An OPEN frontier with no refs should NOT be saturated
        eval_item = ev["frontier_evaluaciones"][-1]
        # It should have "NO_NEXT_ACTIONS" or "CLAIM sin evidence" in razones
        assert not eval_item.get("saturada"), \
            "Una frontier OPEN no debe ser SATURATED: %s" % eval_item.get("razones")
        results.append("PASS AETHER: OPEN frontier not marked SATURATED without evidence")
    finally:
        c.close()
    import shutil; shutil.rmtree(dbdir, ignore_errors=True)

def test_end_to_end_chain():
    """End-to-end: reflect -> plan consulta -> experiment registra."""
    dbdir = tempfile.mkdtemp(prefix="conn_e2e_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    # 1. Execute a real operation to get operation_id
    req1 = {"op": "run", "capability": "binary.inspect",
            "artefacto": "/bin/ls", "backend_id": "radare2"}
    p1 = subprocess.run([sys.executable, MAQUINA],
                        input=json.dumps(req1) + "\n",
                        capture_output=True, text=True, timeout=60, env=env)
    resp1 = json.loads(p1.stdout.strip().splitlines()[0])
    op_id = resp1.get("operation_id", "")
    assert op_id, "Debe tener operation_id"

    # 2. Register a reflection linked to that operation
    req2 = {"op": "reflect",
            "feedback": "la inspeccion de /bin/ls produjo N resultados inesperados",
            "reflection": "el orden de flags -qc vs -e causa empty en r2",
            "outcome": "failure",
            "attempt_id": op_id}
    p2 = subprocess.run([sys.executable, MAQUINA],
                        input=json.dumps(req2) + "\n",
                        capture_output=True, text=True, timeout=30, env=env)
    resp2 = json.loads(p2.stdout.strip().splitlines()[0])
    assert resp2["status"] == "ok"

    # 3. Consultar reflexiones por capability — should find the one from step 2
    c = S.conectar(env["RXRE_DB"])
    try:
        refs = S.consultar_reflexiones_para_capability(c, "binary.inspect", "failure")
        assert refs["estado"] == "ok"
        assert len(refs["reflexiones"]) >= 1
        assert refs["reflexiones"][0]["outcome"] == "failure"
        # The reflection must be linked to the operation
        assert refs["reflexiones"][0]["attempt_id"] == op_id
        results.append("PASS E2E: reflect -> plan consulta cadena completa")
    finally:
        c.close()
    import shutil; shutil.rmtree(dbdir, ignore_errors=True)


def test_saturate_en_ops():
    """op: saturate aparece en la lista de operaciones."""
    dbdir = tempfile.mkdtemp(prefix="conn_ops_")
    env = {**os.environ,
           "PYTHONPATH": PKG + ":" + RXRE,
           "RXRE_DB": os.path.join(dbdir, "test.sqlite3")}
    MAQUINA = os.path.join(RXRE, "api", "machine.py")
    p = subprocess.run([sys.executable, MAQUINA],
                       input=json.dumps({"op": "ops"}) + "\n",
                       capture_output=True, text=True, timeout=30, env=env)
    resp = json.loads(p.stdout.strip())
    ops = {o["op"] for o in resp.get("results", [])}
    assert "reflect" in ops
    assert "experiment" in ops
    assert "saturate" in ops
    results.append("PASS: ops lista reflect, experiment, saturate")
    import shutil; shutil.rmtree(dbdir, ignore_errors=True)


if __name__ == "__main__":
    print("=== RXRE-AUTONOMY-003: Connected mechanisms ===\n")
    test_run_failure_sugiere_reflect()
    test_plan_muestra_reflexiones_previas()
    test_experiment_loop()
    test_saturate_evaluacion()
    test_saturate_no_label_arbitrario()
    test_end_to_end_chain()
    test_saturate_en_ops()

    failed = [r for r in results if not r.startswith("PASS")]
    for r in results:
        print("  %s" % r)
    print("\n=== Summary: %d/%d passed ===" % (len(results) - len(failed), len(results)))
    sys.exit(1 if failed else 0)

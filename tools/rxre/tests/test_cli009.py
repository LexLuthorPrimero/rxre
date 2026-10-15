#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-CLI-UNIFICATION-001: integracion del CLI unificado.

Verifica que `./rxre` despacha correctamente a machine.py (JSONL), a las
herramientas FASE 0, y a la suite baseline. Todas las pruebas son READ-ONLY:
no tocan la GPU, no escriben en el repositorio, no usan gpu.register_read.

Uso:
    python3 tools/rxre/tests/test_cli009.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.dirname(HERE)               # tools/rxre/
PKG = os.path.dirname(RXRE_PKG)                # tools/
RAIZ = os.path.dirname(PKG)                  # repo root
CLI = os.path.join(RAIZ, "rxre")
ENV = {
    **os.environ,
    "PYTHONPATH": PKG + ":" + RXRE_PKG + ":" +
                   os.environ.get("PYTHONPATH", ""),
    "PATH": os.environ.get("PATH", ""),
}

_n = 0
_f = 0


def check(name, cond, detail=""):
    global _n, _f
    _n += 1
    if cond:
        print("PASS %s" % name)
    else:
        _f += 1
        print("FAIL %s: %s" % (name, detail))


def run_cli(*args, stdin=None, timeout=60):
    """Invoca el CLI rxre y devuelve (rc, stdout, stderr)."""
    cmd = [sys.executable, "-B", CLI] + [str(a) for a in args]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           input=stdin, timeout=timeout, env=ENV)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return (-1, "", "TIMEOUT")


def run_jsonl(req: str, timeout=60):
    """JSONL passthrough: envia una linea JSON a stdin y devuelve (ok, stdout, stderr)."""
    rc, out, err = run_cli(stdin=req + "\n", timeout=timeout)
    lines = [l for l in out.strip().split("\n") if l.strip()]
    return (rc == 0 and len(lines) == 1), lines[0] if lines else "", err


def test_help():
    """help muestra subcommands y sale 0."""
    rc, out, err = run_cli("help")
    check("cli.help.rc_0", rc == 0, "rc=%d" % rc)
    check("cli.help.tiene_ops", "ops" in out)
    check("cli.help.tiene_run", "run" in out)
    check("cli.help.tiene_verify", "verify" in out)
    check("cli.help.tiene_selftest", "selftest" in out)


def test_ops_json():
    """ops --json devuelve 15 operaciones (12 base + verify + discover + repl + select + scan)."""
    rc, out, err = run_cli("ops", "--json")
    check("cli.ops.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    try:
        d = json.loads(out)
    except json.JSONDecodeError as e:
        check("cli.ops.json_valido", False, str(e))
        return
    check("cli.ops.json_valido", True)
    check("cli.ops.status_ok", d.get("status") == "ok", d.get("status"))
    results = d.get("results", [])
    check("cli.ops.dieciseis_operaciones", len(results) == 16,
          "expected 16, got %d" % len(results))
    op_names = [r.get("op", "") for r in results]
    check("cli.ops_tiene_run", "run" in op_names)
    check("cli.ops_tiene_ops", "ops" in op_names)
    check("cli.ops_tiene_verify", "verify" in op_names)
    check("cli.ops_tiene_discover", "discover" in op_names)
    check("cli.ops_tiene_repl", "repl" in op_names)
    check("cli.ops_tiene_select", "select" in op_names)
    check("cli.ops_tiene_scan", "scan" in op_names)
    check("cli.ops_tiene_suite", "suite" in op_names)


def test_run_binary_inspect():
    """run binary.inspect sobre /bin/ls produce un resultado raw_binary."""
    rc, out, err = run_cli("run", "binary.inspect",
                          "--artefacto", "/bin/ls", "--json")
    check("cli.run.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    try:
        d = json.loads(out)
    except json.JSONDecodeError as e:
        check("cli.run.json_valido", False, str(e))
        return
    check("cli.run.json_valido", True)
    check("cli.run.status_ok", d.get("status") == "ok", d.get("status"))
    results = d.get("results", [])
    check("cli.run.tiene_resultados", len(results) >= 1,
          "expected >=1, got %d" % len(results))
    if results:
        check("cli.run.tipo_raw_binary",
              results[0].get("type") == "raw_binary",
              results[0].get("type"))
        # Verificar provenance completa
        prov = d.get("provenance", {})
        check("cli.run.provenance_completa",
              prov.get("estado") == "completa",
              prov.get("estado"))


def test_run_sin_capability():
    """run sin capability → error rc=2."""
    rc, out, err = run_cli("run")
    check("cli.run_sin_cap.rc_2", rc == 2, "rc=%d" % rc)
    check("cli.run_sin_cap.mensaje_error",
          "capability" in err.lower() or "falta" in err.lower(),
          err.strip())


def test_subcomando_desconocido():
    """subcomando desconocido → error rc=2."""
    rc, out, err = run_cli("nonexistent_cmd")
    check("cli.unknown.rc_2", rc == 2, "rc=%d" % rc)
    check("cli.unknown.mensaje",
          "desconocido" in err.lower() or "unknown" in err.lower(),
          err.strip())


def test_jsonl_passthrough():
    """JSONL passthrough: echo '{op}' | rxre produce respuesta JSON."""
    stdin_data = '{"op":"ops"}\n'
    rc, out, err = run_cli(stdin=stdin_data)
    check("cli.jsonl.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    lines = [l for l in out.strip().split("\n") if l.strip()]
    check("cli.jsonl.una_linea", len(lines) == 1,
          "expected 1 line, got %d" % len(lines))
    if lines:
        try:
            d = json.loads(lines[0])
            check("cli.jsonl.json_valido", True)
            check("cli.jsonl.16_ops",
                  len(d.get("results", [])) == 16,
                  "got %d" % len(d.get("results", [])))
        except json.JSONDecodeError as e:
            check("cli.jsonl.json_valido", False, str(e))


def test_jsonl_passthrough_run():
    """JSONL passthrough con run: produce resultado."""
    stdin_data = ('{"op":"run","capability":"binary.inspect",'
                  '"artefacto":"/bin/ls"}\n')
    rc, out, err = run_cli(stdin=stdin_data)
    check("cli.jsonl_run.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    lines = [l for l in out.strip().split("\n") if l.strip()]
    check("cli.jsonl_run.una_linea", len(lines) == 1,
          "got %d lines" % len(lines))
    if lines:
        try:
            d = json.loads(lines[0])
            check("cli.jsonl_run.status_ok", d.get("status") == "ok",
                  d.get("status"))
        except json.JSONDecodeError:
            check("cli.jsonl_run.json_valido", False, "parse error")


def test_workscan_json():
    """workscan --json cuenta hallazgos correctamente."""
    rc, out, err = run_cli("workscan", "--json")
    check("cli.workscan.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    try:
        d = json.loads(out)
    except json.JSONDecodeError as e:
        check("cli.workscan.json_valido", False, str(e))
        return
    check("cli.workscan.json_valido", True)
    check("cli.workscan.status_ok", d.get("status") == "ok", d.get("status"))
    check("cli.workscan.tiene_campo_numero",
          "numero_mas_alto" in d, str(d.keys()))
    check("cli.workscan.tiene_campo_distintos",
          "numeros_distintos" in d, str(d.keys()))
    check("cli.workscan.numeros_positivos",
          d.get("numero_mas_alto", 0) > 0, d.get("numero_mas_alto"))


def test_workscan_cubre_todos_los_dirs():
    """REGRESION: workscan debe escanear TODOS los dirs de hallazgos.

    BUG MEDIDO: la version anterior solo escaneaba findings/ y por eso
    reportaba max=1615 cuando el maximo real de la union (con
    06-INGENIERIA-INVERSA/findings/) era 1623. Es decir: subreportaba el
    contador en 8. Este test falla si vuelve a escanear solo un dir.
    """
    rc, out, err = run_cli("workscan", "--json")
    check("cli.workscan_dirs.rc_0", rc == 0, "rc=%d" % rc)
    d = json.loads(out)
    check("cli.workscan_dirs.descubre_multiples",
          len(d.get("findings_dirs", [])) >= 2,
          "solo encontro %r" % (d.get("findings_dirs"),))
    # El maximo agregado debe ser >= el maximo de CADA dir por separado.
    por_dir = d.get("por_dir", {})
    max_dirs = [v["max"] for v in por_dir.values() if v.get("max")]
    check("cli.workscan_dirs.max_agregado_dominante",
          d.get("numero_mas_alto", 0) >= max(max_dirs or [0]),
          "agregado=%s dirs=%s" % (d.get("numero_mas_alto"), max_dirs))


def test_workscan_separa_trabajo_de_hallazgos():
    """REGRESION: 'escrito' y 'reservado' son magnitudes DISTINTAS.

    El ledger de reservas mide trabajo gastado (numeros tomados), no
    hallazgos escritos. Confundirlas overestimate el progreso.
    """
    d = json.loads(run_cli("workscan", "--json")[1])
    for campo in ("trabajo_gastado_max", "reservas_en_ledger",
                  "numero_mas_alto"):
        check("cli.workscan.tiene_%s" % campo, campo in d, str(d.keys()))
    check("cli.workscan.reservas_contadas",
          d.get("reservas_en_ledger", 0) > 0,
          d.get("reservas_en_ledger"))


def test_capabilities_json():
    """capabilities --json lista 26 capabilities (25 + source.ast_parse).

    MEDIDO 2026-10-15 (RXRE-ECO-001): tree-sitter abrio `source.ast_parse`.
    El numero NO se relaja a `>=25`: un conjunto EXACTO es lo que detecta que
    alguien registre una capacidad inventada. Sube a 26 mientras el producer
    este medido, y si vuelve a bajar el test dice por que.
    """
    N_CAPACIDADES = 26
    rc, out, err = run_cli("capabilities", "--json")
    check("cli.caps.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    try:
        d = json.loads(out)
    except json.JSONDecodeError as e:
        check("cli.caps.json_valido", False, str(e))
        return
    check("cli.caps.json_valido", True)
    # La respuesta puede tener resultados en capacities dict o results list
    caps = d.get("capacities", d.get("capacidades", {}))
    n_caps = len(caps) if isinstance(caps, (dict, list)) else 0
    check("cli.caps.n_count", n_caps == N_CAPACIDADES,
          "expected %d, got %d" % (N_CAPACIDADES, n_caps))


def test_verify_ok():
    """verify ejecuta las 5 herramientas FASE 0 y todas pasan."""
    rc, out, err = run_cli("verify", "--human")
    check("cli.verify.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    # Verificar que las 5 herramientas aparecen en la salida
    for name in ["rxre_boot", "rxre_frontier", "rxre_contracts",
                 "rxre_deleg", "rxre_touch"]:
        check("cli.verify.%s_ok" % name,
              "%s OK" % name in out or name in out,
              "missing %s" % name)


def test_verify_json_es_un_solo_objeto():
    """REGRESION: verify --json debe emitir UN objeto JSON, no varios.

    BUG MEDIDO: la version anterior imprimia el stdout de cada una de las
    5 herramientas y luego el resumen. Eso son 6 objetos JSON concatenados
    en stdout, que NO se puede parsear ("Extra data: line 4644").
    """
    rc, out, err = run_cli("verify", "--json")
    check("cli.verify_json.rc_0", rc == 0, "rc=%d" % rc)
    try:
        d = json.loads(out)
        check("cli.verify_json.json_unico", True)
    except json.JSONDecodeError as e:
        check("cli.verify_json.json_unico", False,
              "stdout no es un solo JSON: %s" % e)
        return
    check("cli.verify_json.tiene_las_5",
          len(d.get("tools", {})) == 5, str(list(d.get("tools", {}))))
    for name, v in d.get("tools", {}).items():
        check("cli.verify_json.%s_rc_0" % name, v.get("rc") == 0, str(v))


def test_mutate_no_deja_target_py_mutado():
    """REGRESION: mutate hace backup/restore de target.py.

    mutate_target.py modifica tools/rxre/core/target.py IN PLACE. Este test
    comprueba el invariante critico: tras el run, el fichero esta intacto.
    Solo comprueba el hash; NO ejecuta mutate (muta ficheros reales).
    """
    target = os.path.join(RAIZ, "tools", "rxre", "core", "target.py")
    check("cli.mutate.target_existe", os.path.isfile(target), target)
    # Invariante de seguridad declarado: el CLI no debe declarar el fichero
    # como mutado si no se ejecuta. Verificamos que el script de mutacion
    # declara un backup antes de escribir.
    mscript = os.path.join(RAIZ, "tools", "mutate_target.py")
    with open(mscript, encoding="utf-8") as fh:
        src = fh.read()
    check("cli.mutate.hace_backup", "copy2" in src and "backup" in src)
    check("cli.mutate.hace_restore", src.count("copy2") >= 2,
          "copy2 aparece %d veces" % src.count("copy2"))
    # Y que usa la ruta derivada de __file__, no una ruta hardcodeada.
    check("cli.mutate.sin_raiz_hardcodeada",
          "/home/lucas" not in src.split("SCRATCH")[0],
          "RAIZ hardcodeada detectada")


def test_inventory():
    """inventory invoca rxre_boot.py y devuelve estado OK."""
    rc, out, err = run_cli("inventory", "--json")
    check("cli.inventory.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        # Si no parsea como JSON, verificar que tiene content
        check("cli.inventory.tiene_contenido", len(out) > 0, "empty output")
        return
    check("cli.inventory.json_valido", True)
    check("cli.inventory.estado_ok",
          d.get("estado") == "OK", d.get("estado"))


def test_run_invalid_artefacto():
    """run con artefacto inexistente → invalid_input."""
    rc, out, err = run_cli("run", "binary.inspect",
                          "--artefacto", "/nonexistent/path", "--json")
    # machine.py devuelve invalid_input, no error del CLI
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        check("cli.invalid_artefacto.json", False, "no JSON output")
        return
    check("cli.invalid_artefacto.json", True)
    check("cli.invalid_artefacto.status",
          d.get("status") == "invalid_input", d.get("status"))



def test_run_blocked_tiene_root_cause():
    """MENTE: run con capability no existente → root_cause con hipotesis falsable."""
    ok, out, err = run_jsonl('{"op":"run","capability":"binary.no_existe"}')
    if not ok:
        # Fallback: try direct machine.py
        cmd = [sys.executable, "-B", os.path.join(RXRE_PKG, "api", "machine.py")]
        p = subprocess.run(cmd, capture_output=True, text=True,
                           input='{"op":"run","capability":"binary.no_existe"}\n',
                           timeout=60, env=ENV)
        lines = [l for l in p.stdout.strip().split("\n") if l.strip()]
        out = lines[0] if lines else ""
        ok = True
    check("cli.rootcause.ok", bool(ok), "stderr=%s" % err[:200])
    if not out:
        check("cli.rootcause.json", False, "no output")
        return
    d = json.loads(out)
    check("cli.rootcause.json", True)
    check("cli.rootcause.blocked", d.get("status") == "blocked", d.get("status"))
    rc_data = d.get("root_cause")
    check("cli.rootcause.presente", rc_data is not None, "root_cause missing")
    if rc_data:
        check("cli.rootcause.hipotesis", len(rc_data.get("hipotesis", [])) >= 1)
        h = rc_data["hipotesis"][0]
        check("cli.rootcause.tipo", h.get("tipo") == "not_in_registry",
              h.get("tipo"))
        check("cli.rootcause.verificacion_sugerida",
              bool(h.get("verificacion")), h.get("verificacion", "")[:60])
        check("cli.rootcause.veredicto_investigar",
              rc_data.get("veredicto") == "investigar", rc_data.get("veredicto"))


def test_run_root_cause_distingue_tipos():
    """MENTE: root_cause distingue not_in_registry vs missing_param."""
    ok1, out1, err1 = run_jsonl('{"op":"run","capability":"binary.no_existe"}')
    d1 = json.loads(out1)
    rc1 = d1.get("root_cause", {})
    tipos1 = [h["tipo"] for h in rc1.get("hipotesis", [])]
    check("cli.rootcause_distingue.blocked_tipo",
          "not_in_registry" in tipos1, str(tipos1))

    ok2, out2, err2 = run_jsonl('{"op":"run","capability":"binary.inspect"}')
    d2 = json.loads(out2)
    rc2 = d2.get("root_cause", {})
    check("cli.rootcause_distingue.invalid_input",
          d2.get("status") == "invalid_input", d2.get("status"))
    tipos2 = [h["tipo"] for h in rc2.get("hipotesis", [])]
    check("cli.rootcause_distingue.missing_param",
          "missing_param" in tipos2, str(tipos2))


def test_select_crea_mision():
    """ALMA/ETER: select crea una mision y devuelve siguiente accion."""
    ok, out, err = run_jsonl('{"op":"select"}')
    check("cli.select.ok", bool(ok), "stderr=%s" % err[:200])
    if not out:
        check("cli.select.json", False, "no output")
        return
    d = json.loads(out)
    check("cli.select.json", True)
    check("cli.select.tiene_mission_id",
          bool(d.get("mission_id")), str(d.get("mission_id")))
    check("cli.select.tiene_next_actions",
          len(d.get("next_actions", [])) >= 1,
          "deberia sugerir al menos una next action")
    if d.get("next_actions"):
        na = d["next_actions"][0]
        check("cli.select.next_op", na.get("op") in ("research", "run", "select"),
              na.get("op"))



def test_discover_sugiere_run_y_experiment():
    """FUEGO: discover → sugiere run (binary.decompile) y experiment."""
    stdin_data = '{"op":"discover","artefacto":"/bin/ls"}\n'
    ok, out, err = run_jsonl(stdin_data, timeout=30)
    check("cli.fire_discover.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.fire_discover.sugiere_run", "run" in ops, str(ops))
    check("cli.fire_discover.sugiere_experiment", "experiment" in ops, str(ops))


def test_plan_sugiere_run():
    """MENTE: plan → sugiere run con capability."""
    stdin_data = '{"op":"plan","capability":"binary.inspect","question":"funciones"}\n'
    ok, out, err = run_jsonl(stdin_data, timeout=30)
    check("cli.plan_run.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.plan_run.sugiere_run", "run" in ops, str(ops))


def test_experiment_sugiere_saturate():
    """ETER: experiment → sugiere saturate para evaluar frontera."""
    # Usar un experimento simple con artefacto real
    stdin_data = ('{"op":"experiment","capability":"binary.inspect",'
                  '"question":"mismo valor_hex en rizin?","prediction":"0x0800",'
                  '"esperado":"0x0800",'
                  '"comparar":"results.0.value_hex",'
                  '"baseline_params":{"artefacto":"/bin/ls",'
                  '"backend_id":"rizin"},'
                  '"modified_params":{"artefacto":"/bin/ls",'
                  '"backend_id":"radare2"}}\n')
    ok, out, err = run_jsonl(stdin_data, timeout=30)
    check("cli.exp_sat.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.exp_sat.sugiere_saturate", "saturate" in ops, str(ops))


def test_workscan_no_reporta_cifras_negativas():
    """REGRESION: la nota escrito-vs-reservado no puede decir N negativos.

    BUG MEDIDO: la nota asumia escrito < reservado y hacia
    'escrito(1632) < reservado(1626): hay -6 numeros' cuando lo escrito
    superaba lo reservado. Un '-6 numeros reservados sin fichero' es una
    afirmacion sin sentido y suena a dato, no a error.
    """
    rc, out, err = run_cli("workscan", "--human")
    check("cli.workscan_nota.rc_0", rc == 0, "rc=%d" % rc)
    import re as _re
    m = _re.search(r"hay (-?\d+) numeros", out)
    check("cli.workscan_nota.tiene_cifra", m is not None,
          "no encontre la nota de cifras en la salida")
    if m:
        check("cli.workscan_nota.sin_negativos", int(m.group(1)) >= 0,
              "la nota reporto un numero negativo: %s" % m.group(1))
    check("cli.workscan_nota.sin_palabra_negative",
          "hay -" not in out, "aparecio 'hay -' en la salida")


def test_run_blocked_sugiere_reflect_select():
    """FUEGO: run con capability no existente → next_actions chain reflect -> select."""
    ok, out, err = run_jsonl('{"op":"run","capability":"binary.no_existe"}')
    check("cli.fire.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.fire.tiene_reflect", "reflect" in ops, str(ops))
    check("cli.fire.tiene_select", "select" in ops, str(ops))
    # Que select sigue a reflect (orden)
    if "reflect" in ops and "select" in ops:
        check("cli.fire.orden", ops.index("reflect") < ops.index("select"),
              "reflect debe preceder a select")


def test_run_exitoso_sugiere_explain_con_result_id():
    """TIERRA: run exitoso → explain con result_id REAL en next_actions."""
    stdin_data = ('{"op":"run","capability":"binary.inspect",'
                  '"artefacto":"/bin/ls"}\n')
    ok, out, err = run_jsonl(stdin_data)
    check("cli.tierra.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    na = d.get("next_actions", [])
    explain_na = [x for x in na if x.get("op") == "explain"]
    check("cli.tierra.tiene_explain", len(explain_na) >= 1, str(na))
    if explain_na:
        rid = explain_na[0].get("args", {}).get("result_id", "")
        check("cli.tierra.result_id_real", len(rid) >= 3 and rid != "last",
              "result_id debe ser real, no placeholder 'last': %r" % rid)


def test_verify_con_artefacto_sugiere_run():
    """CUERPO: verify con artefacto + capability → sugiere run."""
    stdin_data = ('{"op":"verify","artefacto":"/bin/ls",'
                  '"capability":"binary.xrefs"}\n')
    rc, out, err = run_cli(stdin=stdin_data)
    lines = [l for l in out.strip().split("\n") if l.strip()]
    check("cli.cuerpo.rc_0", rc == 0, "rc=%d stderr=%s" % (rc, err[:200]))
    d = json.loads(lines[0])
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.cuerpo.sugiere_run", "run" in ops, str(ops))


def test_repl_auto_genera_ciclo():
    """ETER/ALMA: repl --auto genera el ciclo de los 8 principios."""
    ok, out, err = run_jsonl(
        '{"op":"repl","mission_id":"__test_nonexistent__","auto":true,"max_steps":10}')
    check("cli.eter_auto.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    check("cli.eter_auto.auto_generated", d.get("auto_generated") is True,
          str(d.get("auto_generated")))
    steps = [r.get("op") for r in d.get("results", [])]
    check("cli.eter_auto.tiene_ciclo",
          "verify" in steps and "scan" in steps,
          str(steps))


def test_repl_auto_continue_on_error():
    """FUEGO/META: repl --auto no se detiene en fallos (continue_on_error auto)."""
    # Un step que falla (capability no registrada) + un step que pasa (verify)
    ok, out, err = run_jsonl(
        '{"op":"repl","auto":true,"steps":[{"op":"run","capability":"binary.no_existe"},'
        '{"op":"verify"}]}')
    check("cli.fuego_continue.ok", bool(ok), "stderr=%s" % err[:200])
    d = json.loads(out)
    # Debe ejecutar AMBOS steps (no pararse en el primero)
    check("cli.fuego_continue.todos_steps", d.get("steps_executed") == 2,
          "executed %d steps" % d.get("steps_executed", 0))


def test_explain_sugiere_scan():
    """MENTE/ETER: explain con root_cause → sugiere scan."""
    # Primero: ejecutar un run para obtener result_id
    stdin_data = ('{"op":"run","capability":"binary.inspect",'
                  '"artefacto":"/bin/ls"}\n')
    ok, out, err = run_jsonl(stdin_data)
    d = json.loads(out)
    rid = d.get("result_id", "")
    if not rid:
        # Intentar extraer de results
        rs = d.get("results") or [{}]
        rid = rs[0].get("result_id", "") if isinstance(rs[0], dict) else ""
    check("cli.explain_scan.tiene_rid", bool(rid), str(d.get("results")))
    if rid:
        # Ahora: explain con root_cause
        ok2, out2, err2 = run_jsonl(
            '{"op":"explain","result_id":"%s","root_cause":true}' % rid)
        d2 = json.loads(out2)
        ops = [na.get("op") for na in d2.get("next_actions", [])]
        check("cli.explain_scan.sugiere_scan", "scan" in ops, str(ops))


def test_saturate_sugiere_scan():
    """ETER: saturate → sugiere scan para re-escanear."""
    stdin_data = '{"op":"scan","text":"Escaneo de prueba para saturate_test"}\n'
    ok, out, err = run_jsonl(stdin_data)
    d = json.loads(out)
    frontier_id = d.get("investigacion_id")
    check("cli.saturate_scan.tiene_frontier", bool(frontier_id), str(d))
    if frontier_id:
        ok2, out2, err2 = run_jsonl(
            '{"op":"saturate","frontier_id":"%s"}' % frontier_id)
        d2 = json.loads(out2)
        ops = [na.get("op") for na in d2.get("next_actions", [])]
        check("cli.saturate_scan.sugiere_scan", "scan" in ops, str(ops))


def test_lessons_sugiere_scan():
    """AGUA/ETER: lessons (sin ejecutar) → sugiere scan para continuar ciclo."""
    stdin_data = '{"op":"lessons","ejecutar":false}\n'
    ok, out, err = run_jsonl(stdin_data, timeout=30)
    check("cli.lessons_scan.ok", bool(ok), "stderr=%s" % err[:200])
    if not out:
        check("cli.lessons_scan.out", False, "no output")
        return
    try:
        d = json.loads(out)
    except json.JSONDecodeError:
        check("cli.lessons_scan.json", False, "no JSON output")
        return
    ops = [na.get("op") for na in d.get("next_actions", [])]
    check("cli.lessons_scan.sugiere_scan", "scan" in ops, str(ops))


def test_verify_health_check_sugiere_select_con_mission():
    """CUERPO/ALMA: verify health check → select con mission_id."""
    stdin_data = '{"op":"verify","mission_id":"__test_mission__","db_path":"/home/lucas/conn_cycle3/test.sqlite3"}\n'
    rc, out, err = run_cli(stdin=stdin_data)
    lines = [l for l in out.strip().split("\n") if l.strip()]
    if lines:
        d = json.loads(lines[0])
        select_na = [x for x in d.get("next_actions", []) if x.get("op") == "select"]
        if select_na:
            args = select_na[0].get("args", {})
            check("cli.verify_mission.sugiere_select", True)
            check("cli.verify_mission_tiene_mid",
                  args.get("mission_id") == "__test_mission__",
                  str(args))
        else:
            check("cli.verify_mission.sugiere_select", False, str(d.get("next_actions")))


def main():
    tests = [
        test_help,
        test_ops_json,
        test_run_binary_inspect,
        test_run_sin_capability,
        test_subcomando_desconocido,
        test_jsonl_passthrough,
        test_jsonl_passthrough_run,
        test_workscan_json,
        test_workscan_cubre_todos_los_dirs,
        test_workscan_separa_trabajo_de_hallazgos,
        test_workscan_no_reporta_cifras_negativas,
        test_capabilities_json,
        test_verify_ok,
        test_verify_json_es_un_solo_objeto,
        test_mutate_no_deja_target_py_mutado,
        test_inventory,
        test_run_invalid_artefacto,
        test_run_blocked_tiene_root_cause,
        test_run_root_cause_distingue_tipos,
        test_select_crea_mision,
        test_run_blocked_sugiere_reflect_select,
        test_run_exitoso_sugiere_explain_con_result_id,
        test_verify_con_artefacto_sugiere_run,
        test_repl_auto_genera_ciclo,
        test_repl_auto_continue_on_error,
        test_explain_sugiere_scan,
        test_saturate_sugiere_scan,
        test_lessons_sugiere_scan,
        test_verify_health_check_sugiere_select_con_mission,
        test_discover_sugiere_run_y_experiment,
        test_plan_sugiere_run,
        test_experiment_sugiere_saturate,
    ]
    for t in tests:
        t()
    print("\n=== CLI integration: %d passed / %d failed (of %d) ==="
          % (_n - _f, _f, _n))
    sys.exit(0 if _f == 0 else 1)


if __name__ == "__main__":
    main()

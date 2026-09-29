"""rx550-torneo — CLI. Subcomandos: status, state-save, state-show, state-load, verify.

Fase 1 READ-ONLY: no se escribe nunca en /sys. La única escritura posible es
el archivo de estado en $XDG_STATE_HOME/rx550-torneo/state.json.
"""
import argparse
import datetime
import glob
import json
import os
import pwd
import sys

from . import gpu_finder, state_manager, failsafe, write_test, cap_test, cap_run

WRITES = []  # auditoría de escrituras de este proceso (solo archivos de estado)


def _env(name, default=None):
    return os.environ.get(name, default)


def _gpu_from_env():
    overrides = {"render_node": _env("RX550_TORNEO_RENDER_OVERRIDE"),
                 "hwmon": _env("RX550_TORNEO_HWMON_OVERRIDE")}
    overrides = {k: v for k, v in overrides.items() if v}
    return gpu_finder.discover(
        target_pci=_env("RX550_TORNEO_TARGET_PCI", gpu_finder.DEFAULT_TARGET_PCI),
        intel_pci=_env("RX550_TORNEO_INTEL_PCI", gpu_finder.DEFAULT_INTEL_PCI),
        drm_dir=_env("RX550_TORNEO_DRM_DIR", gpu_finder.DEFAULT_DRM_DIR),
        overrides=overrides,
    )


def _state_dir_from_env():
    return _env("RX550_TORNEO_STATE_DIR") or state_manager._state_dir_abs()


def _lock(state_dir):
    import fcntl
    os.makedirs(state_dir, exist_ok=True, mode=0o700)
    lock = os.path.join(state_dir, ".lock")
    fh = open(lock, "w")
    fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
    return fh


def _print(payload, as_json):
    if _env("RX550_TORNEO_AUDIT_WRITES") == "1":
        payload = dict(payload)
        payload["audit_writes"] = list(WRITES)
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))
        return
    text = payload.get("_text")
    if text:
        print(text)
    if "audit_writes" in payload:
        print(f"audit_writes: {payload['audit_writes']}")


def cmd_status(args):
    gpu = _gpu_from_env()
    st = state_manager.capture(gpu, target_pci=gpu["target_pci"])
    payload = {
        "gpu": {
            "target_pci": gpu["target_pci"],
            "intel_pci": gpu["intel_pci"],
            "drm_card": gpu["drm_card"],
            "intel_card": gpu["intel"]["card"],
            "bdf": gpu["target"]["bdf"],
            "driver": gpu["target"]["driver"],
            "vendor": gpu["target"]["vendor"],
            "device_id": gpu["target"]["device_id"],
            "hwmon": gpu["hwmon"],
            "render_node": gpu["render_node"],
        },
        "live": st["capture"]["live"],
        "restorable_active": st["restorable"]["active"],
        "kalm": st["kalm"],
        "mesa": st["mesa"],
        "runtime": {"dry_run": True, "writes": 0},
    }
    payload["_text"] = short_status(payload)
    _print(payload, args.json)


def short_status(p):
    g = p["gpu"]
    out = ["RX 550 Torneo — status (Fase 1, read-only)",
           f"  objetivo : {g['target_pci']}  card={g['drm_card']}  bdf={g['bdf']}  driver={g['driver']}",
           f"  hwmon    : {g['hwmon']}",
           f"  render   : {g['render_node']}",
           f"  intel    : {g['intel_pci']}  card={g['intel_card']}  (display)",
           f"  cap      : {p['live'].get('power1_cap')} µW  temp={p['live'].get('temp1_input')} m°C"]
    return "\n".join(out)


def cmd_state_save(args):
    state_dir = _state_dir_from_env()
    gpu = _gpu_from_env()
    lock = _lock(state_dir)
    try:
        st = state_manager.capture(gpu, target_pci=gpu["target_pci"])
        res = state_manager.save(st, state_dir=state_dir, force=args.force,
                                 audit_hook=lambda p: WRITES.append(p))
        payload = {"ok": True, "path": res["path"], "sha256": res["sha256"],
                   "bytes": res["bytes"], "forced": bool(args.force)}
        payload["_text"] = (f"estado guardado: {res['path']}\nsha256={res['sha256']} "
                            f"({res['bytes']} bytes)")

        _print(payload, args.json)
    finally:
        lock.close()


def cmd_state_show(args):
    sp, st = state_manager.load(_state_dir_from_env())
    if st is None:
        sys.exit(f"no hay estado: {sp}")
    errs = state_manager.validate_schema(st)
    if errs:
        sys.exit("estado inválido: " + "; ".join(errs))
    if not args.json:
        print(f"estado: {sp}")
        print(f"  timestamp : {st['timestamp']}")
        print(f"  kernel    : {st['kernel']}")
        print(f"  objetivo  : {st['target_pci']}  card={st['drm_card']}  render={st['render_node']}")
        if args.full:
            print(json.dumps(st, ensure_ascii=False, sort_keys=True, indent=2))
        else:
            live = st["capture"]["live"]
            print(f"  cap       : {live.get('power1_cap')} µW  (default {live.get('power1_cap_default')})")
            print(f"  dpm_level : {st['restorable']['active'].get('power_dpm_force_performance_level')}")
            sclk = st["restorable"]["files"].get("pp_dpm_sclk")
            if sclk:
                print("  pp_dpm_sclk:")
                for ln in sclk:
                    print(f"    {ln}")
        return
    _print(st, True)


def cmd_state_load(args):
    try:
        info = state_manager.load_for_rollback(_state_dir_from_env())
    except state_manager.util.SafeIOError as exc:
        sys.exit(str(exc))
    missing = info["missing_restorable"]
    ok = not missing
    payload = {"ok": ok, "path": info["path"], "missing_restorable": missing,
               "restorable_fields": len(info["state"]["restorable"]["files"])}
    payload["_text"] = (f"estado cargado OK: {info['path']}\n"
                        f"campos restaurables presentes: {payload['restorable_fields']}"
                        + ("" if ok else f"\nFALTAN: {missing}"))
    if not ok:
        payload["_text"] += "\nNO es seguro restaurar"
    _print(payload, args.json)


def cmd_write_test_text(a, ok):
    lines = [
        "RX 550 Torneo — state-write-test (TEST CONTROLADO, NO optimización)",
        f"  PCI       : {a['pci_id']}  card={a['drm_card']}  bdf={a.get('bdf')}",
        f"  path      : {a['path']}",
        f"  original  : {a['original']}",
        f"  temporal  : {a['temporary']}",
        f"  readback  : {a['readback']}",
        f"  restaurado: {a['restored']}  readback_final={a['readback_final']}",
        f"  rollback  : {a['rollback_attempts']} intento(s)",
        f"  aux       : {'sin cambios' if a.get('aux_unchanged') else 'CAMBIOS ' + str(a.get('aux_diff'))}",
        f"  resultado : {a['result']}",
    ]
    if a.get("fatal"):
        lines.append(f"  fatal     : {a['fatal']['code']}: {a['fatal']['message']}")
    return "\n".join(lines)


def cmd_state_write_test(args):
    """TEST CONTROLADO: write único de power/control + rollback. No optimiza nada.

    Sin --confirm es dry-run (preflight, sin escribir). En producción escribe el
    nodo autorizado de la RX 550; requiere privilegios. TEST_MODE solo permite
    un archivo plano fuera de /sys (para la suite).
    """
    gpu = _gpu_from_env()
    state_dir = _state_dir_from_env()
    test_mode = _env("RX550_TORNEO_TEST_MODE") == "1"

    if test_mode:
        target = _env("RX550_TORNEO_TEST_WRITE_PATH")
        if not target:
            sys.exit("TEST_MODE requiere RX550_TORNEO_TEST_WRITE_PATH")
        if os.path.realpath(target).startswith("/sys/"):
            sys.exit("TEST_MODE no puede apuntar a /sys")
        node = write_test.FileNode(target)
    else:
        node, _logical = write_test.production_node(gpu)

    if not args.confirm:
        session = write_test.WriteTestSession(gpu, node)
        try:
            original = session.preflight()
        except write_test.WriteTestError as exc:
            payload = {"ok": False, "dry_run": True, "no_write": True,
                       "error": exc.code, "message": exc.message,
                       "path": getattr(node, "path", None)}
            payload["_text"] = f"DRY-RUN: no se escribió nada [{exc.code}] {exc.message}"
            _print(payload, args.json)
            return 1
        payload = {"ok": True, "dry_run": True, "no_write": True,
                   "pci_id": f"{gpu['target']['vendor']:04x}:{gpu['target']['device_id']:04x}",
                   "drm_card": gpu["drm_card"], "path": node.path,
                   "original": original, "temporary": write_test.alternate(original)}
        payload["_text"] = (f"DRY-RUN: no se escribió nada\n  path: {node.path}\n"
                            f"  original={original} -> temporal={payload['temporary']}")
        _print(payload, args.json)
        return 0

    session = write_test.WriteTestSession(
        gpu, node, capture_fn=lambda: state_manager.capture(gpu, target_pci=gpu["target_pci"]))
    fatal = None
    try:
        audit = session.run()
        ok = audit["result"] == "OK"
    except write_test.WriteTestError as exc:
        audit = session.audit()
        fatal = {"code": exc.code, "message": exc.message}
        ok = False
    except BaseException as exc:  # noqa: BLE001
        audit = session.audit()
        fatal = {"code": "UNEXPECTED", "message": f"{type(exc).__name__}: {exc}"}
        ok = False
    if fatal:
        audit["fatal"] = fatal
    audit_path = write_test.save_audit(audit, state_dir)
    if _env("RX550_TORNEO_AUDIT_WRITES") == "1":
        WRITES.append(audit_path)
    payload = dict(audit)
    payload["ok"] = ok
    payload["audit_path"] = audit_path
    payload["_text"] = cmd_write_test_text(audit, ok)
    _print(payload, args.json)
    return 0 if ok else 1


def cmd_cap_test_text(a, ok):
    lines = [
        "RX 550 Torneo — cap-write-test (TEST CONTROLADO, NO optimización)",
        f"  PCI       : {a['pci_id']}  card={a['drm_card']}  hwmon={a.get('hwmon') or ''}",
        f"  path      : {a['path']}",
        f"  límites   : min={a.get('limits', {}).get('min')} max={a.get('limits', {}).get('max')} µW",
        f"  original  : {a['original']} µW",
        f"  temporal  : {a['temporary']} µW  (delta={a.get('delta_int')})",
        f"  readback  : {a['readback']} µW",
        f"  restaurado: {a['restored']} µW  readback_final={a['readback_final']} µW",
        f"  rollback  : {a['rollback_attempts']} intento(s)",
        f"  aux       : {'sin cambios' if a.get('aux_unchanged') else 'CAMBIOS ' + str(a.get('aux_diff'))}",
        f"  resultado : {a['result']}",
    ]
    if a.get("fatal"):
        lines.append(f"  fatal     : {a['fatal']['code']}: {a['fatal']['message']}")
    return "\n".join(lines)


def cmd_cap_write_test(args):
    """TEST CONTROLADO: write único de power1_cap + rollback. Sin benchmarks.

    Sin --confirm es dry-run (preflight, sin escribir). Escribe solo el
    power1_cap del hwmon dinámico de la RX 550; requiere privilegios.
    """
    gpu = _gpu_from_env()
    state_dir = _state_dir_from_env()
    test_mode = _env("RX550_TORNEO_TEST_MODE") == "1"
    value = args.value

    if test_mode:
        target = _env("RX550_TORNEO_TEST_WRITE_PATH")
        if not target:
            sys.exit("TEST_MODE requiere RX550_TORNEO_TEST_WRITE_PATH")
        if os.path.realpath(target).startswith("/sys/"):
            sys.exit("TEST_MODE no puede apuntar a /sys")
        node = write_test.FileNode(target)
    else:
        node, _logical = cap_test.production_cap_node(gpu)

    if not args.confirm:
        session = cap_test.CapTestSession(gpu, node, value=value)
        try:
            original = session.preflight()
        except write_test.WriteTestError as exc:
            payload = {"ok": False, "dry_run": True, "no_write": True,
                       "error": exc.code, "message": exc.message,
                       "path": getattr(node, "path", None)}
            payload["_text"] = f"DRY-RUN: no se escribió nada [{exc.code}] {exc.message}"
            _print(payload, args.json)
            return 1
        payload = {"ok": True, "dry_run": True, "no_write": True,
                   "pci_id": f"{gpu['target']['vendor']:04x}:{gpu['target']['device_id']:04x}",
                   "drm_card": gpu["drm_card"], "hwmon": gpu["hwmon"], "path": node.path,
                   "limits": session.limits, "original": original,
                   "temporary": str(session.temporary_int)}
        payload["_text"] = (f"DRY-RUN: no se escribió nada\n  path: {node.path}\n"
                            f"  límites: {session.limits}\n"
                            f"  original={original} -> temporal={session.temporary_int} µW")
        _print(payload, args.json)
        return 0

    session = cap_test.CapTestSession(
        gpu, node, value=value,
        capture_fn=lambda: state_manager.capture(gpu, target_pci=gpu["target_pci"]))
    fatal = None
    try:
        audit = session.run()
        ok = audit["result"] == "OK"
    except write_test.WriteTestError as exc:
        audit = session.audit()
        fatal = {"code": exc.code, "message": exc.message}
        ok = False
    except BaseException as exc:  # noqa: BLE001
        audit = session.audit()
        fatal = {"code": "UNEXPECTED", "message": f"{type(exc).__name__}: {exc}"}
        ok = False
    if fatal:
        audit["fatal"] = fatal
    audit["hwmon"] = gpu["hwmon"]
    audit_path = write_test.save_audit(audit, state_dir)
    if _env("RX550_TORNEO_AUDIT_WRITES") == "1":
        WRITES.append(audit_path)
    payload = dict(audit)
    payload["ok"] = ok
    payload["audit_path"] = audit_path
    payload["_text"] = cmd_cap_test_text(audit, ok)
    _print(payload, args.json)
    return 0 if ok else 1


def _workload_identity(geteuid, env):
    """(uid, gid) del usuario que invocó sudo, o (None, None) si no somos root.

    Si el proceso corre como root sin un SUDO_UID válido, rechaza el run ANTES
    de tocar sysfs: el workload NUNCA debe ejecutarse como root.
    """
    if geteuid() != 0:
        return None, None
    raw_uid = (env.get("SUDO_UID") or "").strip()
    raw_gid = (env.get("SUDO_GID") or "").strip()
    if not raw_uid:
        raise write_test.WriteTestError(
            "NO_SUDO_UID",
            "proceso como root sin SUDO_UID: ejecutá con `sudo` desde tu usuario "
            "(no `sudo -i`/login root); el workload no debe correr como root")
    try:
        uid = int(raw_uid)
        gid = int(raw_gid) if raw_gid else 0
    except ValueError:
        raise write_test.WriteTestError(
            "BAD_SUDO_ID", f"SUDO_UID/GID inválidos: {raw_uid!r}/{raw_gid!r}")
    if uid == 0:
        raise write_test.WriteTestError(
            "SUDO_UID_ZERO", "SUDO_UID=0: el workload correría como root")
    return uid, gid


def _workload_environment(uid, gid, base=None):
    """Entorno del workload como el usuario real (HOME/XDG), mínimo y seguro.

    Parte del entorno ya saneado por cap_run.workload_env (Mesa stock + selección
    RX 550) y sólo corrige lo necesario para que Mesa use el HOME del usuario y
    no `/root`. Las variables gráficas se conservan si están; si faltan, se
    derivan de forma conservadora desde la sesión del uid.
    """
    env = cap_run.workload_env(base=base)
    try:
        home = pwd.getpwuid(uid).pw_dir
    except KeyError:
        home = None
    if home:
        env["HOME"] = home
    runtime_dir = f"/run/user/{uid}"
    if os.path.isdir(runtime_dir):
        env["XDG_RUNTIME_DIR"] = runtime_dir
        if os.path.exists(os.path.join(runtime_dir, "bus")):
            env.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={runtime_dir}/bus")
    if not env.get("XAUTHORITY"):
        xs = sorted(glob.glob(os.path.join(runtime_dir, "xauth_*")))
        if xs:
            env["XAUTHORITY"] = xs[-1]
    if not env.get("WAYLAND_DISPLAY") and os.path.exists(os.path.join(runtime_dir, "wayland-0")):
        env["WAYLAND_DISPLAY"] = "wayland-0"
    return env


def _m1_context(args):
    gpu = _gpu_from_env()
    test_mode = _env("RX550_TORNEO_TEST_MODE") == "1"
    if test_mode:
        target = _env("RX550_TORNEO_TEST_WRITE_PATH")
        if not target:
            sys.exit("TEST_MODE requiere RX550_TORNEO_TEST_WRITE_PATH")
        if os.path.realpath(target).startswith("/sys/"):
            sys.exit("TEST_MODE no puede apuntar a /sys")
        node = write_test.FileNode(target)
    else:
        node, _logical = cap_test.production_cap_node(gpu)
    workload_cmd = None
    tw = _env("RX550_TORNEO_TEST_WORKLOAD")
    if tw:
        workload_cmd = ["/bin/bash", "-c", tw]
    uid, gid = _workload_identity(os.geteuid, os.environ)
    return gpu, node, workload_cmd, uid, gid, test_mode


def _m1_out_dir(args):
    if args.out:
        return args.out
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    return os.path.join(_state_dir_from_env(), "m1", f"{args.name}-{stamp}")


def _m1_test_session_kwargs():
    return {
        "aux_reader": cap_run.read_aux_test,
        "limits_reader": cap_run.read_limits_test,
    }


def _m1_dry_run(gpu, node, target, test_mode=False):
    extra = _m1_test_session_kwargs() if test_mode else {}
    session = cap_run.CapRunSession(gpu, node, target, out_dir=None, enable_guard=False,
                                   **extra)
    original = session.preflight()
    return session, original


def cmd_m1_run(args):
    """Una corrida: SET -> readback -> workload+sampler -> RESTORE -> readback."""
    gpu, node, workload_cmd, uid, gid, test_mode = _m1_context(args)
    target = args.target
    if not args.confirm:
        try:
            session, original = _m1_dry_run(gpu, node, target, test_mode=test_mode)
        except write_test.WriteTestError as exc:
            _print({"ok": False, "dry_run": True, "no_write": True,
                    "error": exc.code, "message": exc.message,
                    "path": getattr(node, "path", None),
                    "_text": f"DRY-RUN M1: no se escribió nada [{exc.code}] {exc.message}"},
                   args.json)
            return 1
        payload = {"ok": True, "dry_run": True, "no_write": True,
                   "pci_id": f"{gpu['target']['vendor']:04x}:{gpu['target']['device_id']:04x}",
                   "drm_card": gpu["drm_card"], "hwmon": gpu["hwmon"], "path": node.path,
                   "original": original, "target": target,
                   "workload": workload_cmd or cap_run.default_workload_command(args.duration),
                   "test_mode": test_mode}
        payload["_text"] = (f"DRY-RUN M1: no se escribió nada\n  path: {node.path}\n"
                            f"  original={original} -> target={target} µW\n"
                            f"  workload: {' '.join(payload['workload'])}")
        _print(payload, args.json)
        return 0

    out_dir = _m1_out_dir(args)
    session_kwargs = {
        "workload_user": uid,
        "workload_group": gid,
        "workload_env": _workload_environment(uid, gid) if uid is not None else None,
    }
    if test_mode:
        session_kwargs.update(_m1_test_session_kwargs())
    session = cap_run.CapRunSession(
        gpu, node, target, workload_cmd=workload_cmd, out_dir=out_dir,
        duration_s=args.duration, **session_kwargs)
    audit = session.run()
    audit_path = session.save()
    ok = audit["result"] == "OK"
    lines = [
        "RX 550 Torneo — M1 run (cap sostenido, NO optimización)",
        f"  path      : {audit['path']}",
        f"  original  : {audit['original']} -> target {audit['target']} µW",
        f"  set readback : {audit['set_readback']}",
        f"  workload rc  : {audit['workload_rc']}",
        f"  restaurado   : {audit['restored']} readback_final={audit['readback_final']}",
        f"  rollback     : {audit['rollback_attempts']} intento(s)",
        f"  aux          : {'sin cambios' if audit['aux_unchanged'] else 'CAMBIOS ' + str(audit['aux_diff'])}",
        f"  resultado    : {audit['result']}",
    ]
    if audit.get("fatal"):
        lines.append(f"  fatal     : {audit['fatal']['code']}: {audit['fatal']['message']}")
    payload = dict(audit)
    payload["ok"] = ok
    payload["audit_path"] = audit_path
    payload["_text"] = "\n".join(lines)
    _print(payload, args.json)
    return 0 if ok else 1


def cmd_m1_schedule(args):
    """5 bloques pareados 35/30 con cooldown y orden alternado."""
    gpu, node, workload_cmd, uid, gid, test_mode = _m1_context(args)
    if not args.confirm:
        try:
            session, original = _m1_dry_run(gpu, node, args.arms[1], test_mode=test_mode)
        except write_test.WriteTestError as exc:
            _print({"ok": False, "dry_run": True, "no_write": True, "error": exc.code,
                    "message": exc.message,
                    "_text": f"DRY-RUN M1 schedule: no se escribió nada [{exc.code}] {exc.message}"},
                   args.json)
            return 1
        payload = {"ok": True, "dry_run": True, "no_write": True, "original": original,
                   "blocks": args.blocks, "arms": list(args.arms),
                   "workload": workload_cmd or cap_run.default_workload_command(args.duration),
                   "test_mode": test_mode,
                   "_text": (f"DRY-RUN M1 schedule: no se escribió nada\n  original={original}\n"
                             f"  {args.blocks} bloques, brazos={list(args.arms)}")}
        _print(payload, args.json)
        return 0

    out_dir = _m1_out_dir(args)
    session_kwargs = {"workload_user": uid, "workload_group": gid}
    if uid is not None:
        session_kwargs["workload_env"] = _workload_environment(uid, gid)
    if test_mode:
        session_kwargs["enable_guard"] = True
        session_kwargs.update(_m1_test_session_kwargs())
    cooldown_fn = None if args.no_cooldown else (lambda: cap_run.cooldown(gpu))
    audits = cap_run.run_schedule(
        gpu, node, workload_cmd=workload_cmd, out_dir=out_dir, blocks=args.blocks,
        arms=tuple(args.arms), duration_s=args.duration, session_kwargs=session_kwargs,
        cooldown_fn=cooldown_fn, schedule_name=args.name)
    results = [a["result"] for a in audits]
    ok = all(r == "OK" for r in results)
    payload = {"ok": ok, "out_dir": out_dir, "n_runs": len(audits), "results": results,
               "_text": (f"M1 schedule: {len(audits)} corridas en {out_dir}\n"
                         f"  resultados: {results}")}
    _print(payload, args.json)
    return 0 if ok else 1


def cmd_verify(args):
    gpu = _gpu_from_env()
    violations = []
    checks = []
    t = gpu["target"]
    checks.append(("pci_target", f"{gpu['target_pci']} -> card {gpu['drm_card']}"))
    ok = (t["vendor"] == 0x1002 and t["device_id"] == 0x699f)
    if not ok:
        violations.append(f"vendor/device de objetivo inesperado: {t['pci']}")
    if t["driver"] != "amdgpu":
        violations.append(f"driver del objetivo no es amdgpu: {t['driver']}")
    if gpu["intel"]["vendor"] != 0x8086:
        violations.append(f"Intel no 0x8086: {gpu['intel']['pci']}")
    if gpu["intel"]["card"] == gpu["drm_card"]:
        violations.append("objetivo == Intel; imposible")
    checks.append(("driver", t["driver"]))
    checks.append(("display", f"Intel {gpu['intel']['card']} conectado; RX550 sin conectores"))

    # integridad de estado persistente
    sp, st = state_manager.load(_state_dir_from_env())
    state_checks = None
    if st is None:
        violations.append("no hay archivo de estado persistente (falta state-save)")
    else:
        errs = state_manager.validate_schema(st)
        if errs:
            violations.append("estado inválido: " + "; ".join(errs))
        else:
            if st["drm_card"] != gpu["drm_card"]:
                violations.append(f"estado apunta a {st['drm_card']} pero la RX 550 está en {gpu['drm_card']}")
            state_checks = {
                "path": sp, "timestamp": st["timestamp"], "kernel": st["kernel"],
                "restorable_fields": len(st["restorable"]["files"]),
                "missing": [n for _b, _r, n, _e in failsafe.state_manager_STATIC_restorable()
                            if st["restorable"]["files"].get(n) is None],
            }

    payload = {"ok": not violations, "checks": checks, "violations": violations,
               "state": state_checks}
    payload["_text"] = ("VERIFY OK (read-only, sin escrituras)" if not violations
                        else "VERIFY FALLIDO:\n" + "\n".join(f"  - {v}" for v in violations))
    _print(payload, args.json)
    return 0 if not violations else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="rx550-torneo", description="Fase 1 READ-ONLY")
    ap.add_argument("--json", action="store_true", help="salida JSON")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                        help="salida JSON (también válido antes del subcomando)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status", help="detecta RX 550 / Intel y lee el estado vivo",
                              parents=[common])
    p_status.set_defaults(fn=cmd_status)

    p_save = sub.add_parser("state-save", help="captura y persiste el estado (no sobrescribe sin --force)",
                            parents=[common])
    p_save.add_argument("--force", action="store_true", help="sobrescribir estado existente")
    p_save.set_defaults(fn=cmd_state_save)

    p_show = sub.add_parser("state-show", help="muestra el estado persistido", parents=[common])
    p_show.add_argument("--full", action="store_true", help="dump JSON completo")
    p_show.set_defaults(fn=cmd_state_show)

    p_load = sub.add_parser("state-load", help="carga y valida el estado (sin aplicar; Fase 1)",
                            parents=[common])
    p_load.set_defaults(fn=cmd_state_load)

    p_verify = sub.add_parser("verify", help="validaciones integrales read-only", parents=[common])
    p_verify.set_defaults(fn=cmd_verify)

    p_wtest = sub.add_parser(
        "state-write-test",
        help="TEST CONTROLADO (no optimización): write único de power/control + rollback",
        parents=[common])
    p_wtest.add_argument("--confirm", action="store_true",
                         help="ejecuta realmente el write+rollback (sin esto: dry-run, no escribe)")
    p_wtest.set_defaults(fn=cmd_state_write_test)

    p_ctest = sub.add_parser(
        "cap-write-test",
        help="TEST CONTROLADO (no optimización): write único de power1_cap + rollback",
        parents=[common])
    p_ctest.add_argument("--confirm", action="store_true",
                         help="ejecuta realmente el write+rollback (sin esto: dry-run, no escribe)")
    p_ctest.add_argument("--value", type=int, default=None,
                         help="valor temporal en µW (debe estar dentro de min/max)")
    p_ctest.set_defaults(fn=cmd_cap_write_test)

    p_m1 = sub.add_parser(
        "m1-run",
        help="M1: una corrida de cap sostenido (SET->workload+sampler->RESTORE)",
        parents=[common])
    p_m1.add_argument("--confirm", action="store_true",
                      help="ejecuta realmente (sin esto: dry-run, no escribe)")
    p_m1.add_argument("--target", type=int, default=cap_run.DEFAULT_TARGET,
                      help="cap objetivo en µW (default 30000000)")
    p_m1.add_argument("--duration", type=float, default=cap_run.DEFAULT_DURATION_S)
    p_m1.add_argument("--out", help="directorio de salida")
    p_m1.add_argument("--name", default="m1")
    p_m1.set_defaults(fn=cmd_m1_run)

    p_m1s = sub.add_parser(
        "m1-schedule",
        help="M1: bloques pareados 35/30 con cooldown y orden alternado",
        parents=[common])
    p_m1s.add_argument("--confirm", action="store_true")
    p_m1s.add_argument("--blocks", type=int, default=5)
    p_m1s.add_argument("--arms", type=int, nargs=2, default=[35000000, 30000000],
                       metavar=("W1", "W2"))
    p_m1s.add_argument("--duration", type=float, default=cap_run.DEFAULT_DURATION_S)
    p_m1s.add_argument("--out", help="directorio de salida")
    p_m1s.add_argument("--name", default="m1")
    p_m1s.add_argument("--no-cooldown", action="store_true",
                       help="omite la espera de cooldown (solo tests)")
    p_m1s.set_defaults(fn=cmd_m1_schedule)

    args = ap.parse_args(argv)
    if not hasattr(args, "json"):
        args.json = False
    try:
        rc = args.fn(args)
    except (gpu_finder.GPUError, state_manager.util.SafeIOError,
            state_manager.StateFileExists, write_test.WriteTestError) as exc:
        sys.stderr.write(f"ERROR [{getattr(exc, 'code', 'SAFE')}]: {exc}\n")
        sys.exit(1)
    if rc:
        sys.exit(rc)


if __name__ == "__main__":
    main()

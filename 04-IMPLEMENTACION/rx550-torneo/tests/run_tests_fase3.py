#!/usr/bin/env python3
"""rx550-torneo — Fase 3 (preparación): tests A–J de power1_cap SIMULADOS.

Nunca escribe sysfs: usa FakeNode en memoria o un archivo plano fuera de /sys.
El test J compara contenido/mtime de los nodos reales antes/después; el I usa
strace sobre una corrida en test-mode. NO hay benchmarks ni sweep.
"""
import copy
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT, "src")
CLI = os.path.join(PROJECT, "rx550-torneo")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from rx550_torneo import cap_test, gpu_finder, util, write_test  # noqa: E402

RESULTS = []
WT = write_test.WriteTestError
AUX3 = {k: "stub" for k in cap_test.STRICT_AUX3}
AUX3.update({k: "stub" for k in cap_test.NORMALIZED_AUX3})
ORIG = None
LIMITS = None
TEMP = None


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    return bool(cond)


def run_cli(args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.update(env_extra or {})
    p = subprocess.run([CLI] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def wr(path, text):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def rd(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def sess3(gpu, node, value=None, **kw):
    kw.setdefault("aux_reader", lambda _g: dict(AUX3))
    kw.setdefault("limits_reader", lambda _g: dict(LIMITS))
    return cap_test.CapTestSession(gpu, node, value=value, **kw)


def t_A(gpu):
    node = write_test.FakeNode(value=str(ORIG))
    a = sess3(gpu, node).run()
    check("3A: resultado OK", a["result"] == "OK", a["result"])
    check("3A: original exacto", a["original"] == str(ORIG), a["original"])
    check("3A: temporal seguro", a["temporary"] == str(TEMP), a["temporary"])
    check("3A: readback temporal", a["readback"] == str(TEMP), a["readback"])
    check("3A: restaurado original", a["restored"] == str(ORIG), a["restored"])
    check("3A: readback_final original", a["readback_final"] == str(ORIG), a["readback_final"])
    check("3A: rollback 1 intento", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("3A: escrituras [temp,orig]", node.writes == [str(TEMP), str(ORIG)], node.writes)
    check("3A: aux sin cambios", a["aux_unchanged"])


def t_B(gpu):
    for bad, label in ((LIMITS["max"] + 1, ">max"), (LIMITS["min"] - 1, "<min")):
        node = write_test.FakeNode(value=str(ORIG))
        code = None
        try:
            sess3(gpu, node, value=bad).preflight()
        except WT as exc:
            code = exc.code
        check(f"3B: {label} -> OUT_OF_RANGE", code == "OUT_OF_RANGE", code)
        check(f"3B: {label} sin escrituras", node.writes == [], node.writes)
    node = write_test.FakeNode(value=str(ORIG))
    code = None
    try:
        sess3(gpu, node, value=ORIG).preflight()
    except WT as exc:
        code = exc.code
    check("3B: igual al original -> SAME_VALUE", code == "SAME_VALUE", code)
    check("3B: SAME_VALUE sin escrituras", node.writes == [], node.writes)


def t_C(gpu):
    node = write_test.FakeNode(value=str(ORIG), bad_readback=str(ORIG))
    s = sess3(gpu, node)
    code = None
    try:
        s.run()
    except WT as exc:
        code = exc.code
    a = s.audit()
    check("3C: readback incorrecto detectado", code == "READBACK_MISMATCH", code)
    check("3C: se intentó rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("3C: estado final original", node.value == str(ORIG), node.value)
    check("3C: readback_final original", a["readback_final"] == str(ORIG), a["readback_final"])


def t_D(gpu):
    node = write_test.FakeNode(value=str(ORIG), fail_write=True)
    s = sess3(gpu, node)
    code = None
    try:
        s.run()
    except WT as exc:
        code = exc.code
    a = s.audit()
    check("3D: write rechazado detectado", code == "WRITE_FAILED", code)
    check("3D: no se continuó (sin rollback)", a["rollback_attempts"] == 0, a["rollback_attempts"])
    check("3D: nodo intacto", node.value == str(ORIG), node.value)
    check("3D: sin escrituras", node.writes == [], node.writes)


def t_E(gpu):
    bad = copy.deepcopy(gpu)
    bad["target"]["device_id"] = 0x1234
    node = write_test.FakeNode(value=str(ORIG))
    code = None
    try:
        sess3(bad, node).preflight()
    except WT as exc:
        code = exc.code
    check("3E: GPU incorrecta -> WRONG_GPU", code == "WRONG_GPU", code)
    check("3E: no escribió", node.writes == [], node.writes)
    rc, _o, err = run_cli(["cap-write-test", "--confirm", "--json"],
                          {"RX550_TORNEO_TARGET_PCI": "9999:9999"})
    check("3E: CLI GPU inexistente -> error sin write", rc != 0, err.strip()[-120:])


def t_F(gpu):
    bad = copy.deepcopy(gpu)
    bad["hwmon"] = "/sys/class/drm"
    node = write_test.FakeNode(value=str(ORIG))
    code = None
    try:
        sess3(bad, node).preflight()
    except WT as exc:
        code = exc.code
    check("3F: hwmon incorrecto -> BAD_HWMON", code == "BAD_HWMON", code)
    check("3F: no escribió", node.writes == [], node.writes)
    node2 = write_test.FakeNode(value=str(ORIG), authorized=False)
    code2 = None
    try:
        sess3(gpu, node2).preflight()
    except WT as exc:
        code2 = exc.code
    check("3F: nodo no autorizado -> PATH_INVALID", code2 == "PATH_INVALID", code2)
    check("3F: nodo no autorizado sin escrituras", node2.writes == [], node2.writes)


def t_G(gpu):
    for sig in (signal.SIGINT, signal.SIGTERM):
        node = write_test.FakeNode(value=str(ORIG))

        def hook(_s, _sig=sig):
            os.kill(os.getpid(), _sig)

        s = sess3(gpu, node, hooks={"after_write": hook})
        try:
            s.run()
        except WT:
            pass
        a = s.audit()
        check(f"3G: {sig.name} -> rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
        check(f"3G: {sig.name} -> final original", node.value == str(ORIG), node.value)
        check(f"3G: {sig.name} -> INTERRUPTED", a["result"] == "INTERRUPTED", a["result"])


def t_H(gpu):
    node = write_test.FakeNode(value=str(ORIG))

    def hook(_s):
        raise RuntimeError("boom tras el write")

    s = sess3(gpu, node, hooks={"after_write": hook})
    raised = None
    try:
        s.run()
    except RuntimeError:
        raised = "RuntimeError"
    a = s.audit()
    check("3H: excepción propagada", raised == "RuntimeError", raised)
    check("3H: se intentó rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("3H: estado final original", node.value == str(ORIG), node.value)


def t_access(gpu):
    node = write_test.FakeNode(value=str(ORIG), fail_read=True)
    code = None
    try:
        sess3(gpu, node).preflight()
    except WT as exc:
        code = exc.code
    check("3F2: pérdida de acceso -> NODE_UNREADABLE", code == "NODE_UNREADABLE", code)
    node2 = write_test.FakeNode(value=str(ORIG), fail_read_after_write=True)
    s = sess3(gpu, node2)
    try:
        s.run()
    except Exception:  # noqa: BLE001
        pass
    a = s.audit()
    check("3C2: pérdida de acceso tras write -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("3C2: un solo intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


SYS_WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")


def t_I(tmp):
    node_path = os.path.join(tmp, "fake-power1-cap")
    wr(node_path, str(ORIG))
    trace = os.path.join(tmp, "strace-cap.txt")
    env = {"PYTHONPATH": SRC, "XDG_STATE_HOME": tmp,
           "RX550_TORNEO_TEST_MODE": "1",
           "RX550_TORNEO_TEST_WRITE_PATH": node_path,
           "RX550_TORNEO_AUDIT_WRITES": "1"}
    p = subprocess.run(["strace", "-f", "-e", "trace=openat,open", "-o", trace,
                        CLI, "cap-write-test", "--confirm", "--json"],
                       capture_output=True, text=True, env={**os.environ, **env})
    check("3I: test-mode rc=0", p.returncode == 0, p.stderr.strip()[-200:])
    check("3I: nodo restaurado al original", (rd(node_path) or "").strip() == str(ORIG), rd(node_path))
    if not os.path.isfile(trace):
        check("3I: strace generado", False, "sin trace")
        return
    targets = []
    for ln in rd(trace).splitlines():
        m = re.search(r'"(/[^"]*)"', ln)
        if m and any(f in ln for f in SYS_WRITE_FLAGS):
            targets.append(m.group(1))
    sys_writes = [t for t in targets if t.startswith("/sys/")]
    node_writes = [t for t in targets if os.path.realpath(t) == os.path.realpath(node_path)]
    check("3I: sin escrituras a /sys", sys_writes == [], "; ".join(sys_writes[:3]))
    check("3I: escribe solo el nodo power1_cap", len(node_writes) >= 1, str(targets[:6]))
    check("3I: exactamente 2 writes (temp + rollback)", len(node_writes) == 2, len(node_writes))


def t_dryrun(tmp):
    node_path = os.path.join(tmp, "dryrun-cap")
    wr(node_path, str(ORIG))
    before = rd(node_path)
    rc, out, _e = run_cli(["cap-write-test", "--json"],
                          {"XDG_STATE_HOME": tmp, "RX550_TORNEO_TEST_MODE": "1",
                           "RX550_TORNEO_TEST_WRITE_PATH": node_path})
    check("3D2: dry-run rc=0", rc == 0, out.strip()[-120:])
    payload = json.loads(out)
    check("3D2: dry-run no escribe", payload.get("no_write") is True, payload)
    check("3D2: nodo sin cambios", rd(node_path) == before, rd(node_path))
    has_audit = any(f.startswith("write-test-") for f in os.listdir(tmp))
    check("3D2: dry-run no genera auditoría", not has_audit)


def t_J(gpu, snap_before, cap_path, cap_mtime, ctl_path, ctl_mtime):
    snap_after = cap_test.read_aux3(gpu)
    diff = [(k, snap_before.get(k), snap_after.get(k))
            for k in cap_test.STRICT_AUX3 if snap_before.get(k) != snap_after.get(k)]
    check("3J: power/control+DPM+profile sin cambios", diff == [], str(diff))
    ndiff = []
    for k in cap_test.NORMALIZED_AUX3:
        b = write_test.normalize_dpm(snap_before.get(k))
        a = write_test.normalize_dpm(snap_after.get(k))
        if b != a:
            ndiff.append((k, b, a))
    check("3J: SCLK/MCLK (normalizados) sin cambios", ndiff == [], str(ndiff))
    check("3J: power/control real intacto", (rd(ctl_path) or "").strip() == "on", rd(ctl_path))
    check("3J: mtime power/control sin cambios",
          os.stat(ctl_path).st_mtime_ns == ctl_mtime, os.stat(ctl_path).st_mtime_ns)
    check("3J: mtime power1_cap real sin cambios",
          os.stat(cap_path).st_mtime_ns == cap_mtime, os.stat(cap_path).st_mtime_ns)


def main():
    global ORIG, LIMITS, TEMP
    try:
        gpu = gpu_finder.discover()
    except gpu_finder.GPUError as exc:
        check("3: RX 550 disponible", False, f"{exc.code}: {exc.message}")
        return _report()
    LIMITS = cap_test.read_limits(gpu)
    ORIG = util.read_int(os.path.join(gpu["hwmon"], "power1_cap"), missing_ok=False)
    TEMP = cap_test.default_temporary(ORIG, LIMITS)
    cap_path = os.path.join(gpu["hwmon"], "power1_cap")
    ctl_path = os.path.join("/sys/class/drm", gpu["drm_card"], "device", "power", "control")
    cap_mtime = os.stat(cap_path).st_mtime_ns
    ctl_mtime = os.stat(ctl_path).st_mtime_ns
    snap_before = cap_test.read_aux3(gpu)
    tmp = tempfile.mkdtemp(prefix="rx550f3-")
    try:
        for fn in (t_A, t_B, t_C, t_D, t_E, t_F, t_G, t_H, t_access):
            try:
                fn(gpu)
            except Exception as exc:  # noqa: BLE001
                check(f"3{fn.__name__}: sin excepción no controlada", False,
                      f"{type(exc).__name__}: {exc}")
        for fn in (t_I, t_dryrun):
            try:
                fn(tmp)
            except Exception as exc:  # noqa: BLE001
                check(f"3{fn.__name__}: sin excepción", False, f"{type(exc).__name__}: {exc}")
        t_J(gpu, snap_before, cap_path, cap_mtime, ctl_path, ctl_mtime)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return _report()


def _report():
    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not ok else ""))
    print(f"\n{passed}/{len(RESULTS)} checks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

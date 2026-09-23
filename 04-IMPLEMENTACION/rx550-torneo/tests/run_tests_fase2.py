#!/usr/bin/env python3
"""rx550-torneo — Fase 2: tests obligatorios A–J (write+rollback SIMULADO).

Nunca escribe sysfs: usa FakeNode en memoria o un archivo plano fuera de /sys.
El test J compara contenido y mtime de los nodos reales antes/después; el I usa
strace sobre una corrida en test-mode.
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

from rx550_torneo import gpu_finder, write_test  # noqa: E402

RESULTS = []
AUX_STUB = {k: "stub" for k in write_test.STRICT_AUX}
WT = write_test.WriteTestError


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


def sess(gpu, node, **kw):
    kw.setdefault("aux_reader", lambda _g: dict(AUX_STUB))
    return write_test.WriteTestSession(gpu, node, **kw)


def t_A(gpu):
    node = write_test.FakeNode(value="on")
    a = sess(gpu, node).run()
    check("2A: resultado OK", a["result"] == "OK", a["result"])
    check("2A: original on", a["original"] == "on", a["original"])
    check("2A: temporal auto", a["temporary"] == "auto", a["temporary"])
    check("2A: readback auto", a["readback"] == "auto", a["readback"])
    check("2A: restaurado on", a["restored"] == "on", a["restored"])
    check("2A: readback_final on", a["readback_final"] == "on", a["readback_final"])
    check("2A: rollback 1 intento", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("2A: escrituras [auto,on]", node.writes == ["auto", "on"], node.writes)
    check("2A: aux sin cambios", a["aux_unchanged"])


def t_B(gpu):
    node = write_test.FakeNode(value="auto")
    a = sess(gpu, node).run()
    check("2B: resultado OK (orig auto)", a["result"] == "OK", a["result"])
    check("2B: temporal on", a["temporary"] == "on", a["temporary"])
    check("2B: rollback a auto", a["restored"] == "auto" and a["readback_final"] == "auto",
          a["readback_final"])
    check("2B: escrituras [on,auto]", node.writes == ["on", "auto"], node.writes)


def t_C(gpu):
    node = write_test.FakeNode(value="on", bad_readback="on")
    s = sess(gpu, node)
    code = None
    try:
        s.run()
    except WT as exc:
        code = exc.code
    a = s.audit()
    check("2C: readback incorrecto detectado", code == "READBACK_MISMATCH", code)
    check("2C: se intentó rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("2C: estado final == original", node.value == "on", node.value)
    check("2C: readback_final on", a["readback_final"] == "on", a["readback_final"])


def t_D(gpu):
    node = write_test.FakeNode(value="on", fail_write=True)
    s = sess(gpu, node)
    code = None
    try:
        s.run()
    except WT as exc:
        code = exc.code
    a = s.audit()
    check("2D: write rechazado detectado", code == "WRITE_FAILED", code)
    check("2D: no se continuó (sin rollback)", a["rollback_attempts"] == 0)
    check("2D: nodo intacto", node.value == "on", node.value)
    check("2D: sin escrituras", node.writes == [], node.writes)


def t_E(gpu):
    bad = copy.deepcopy(gpu)
    bad["target"]["device_id"] = 0x1234
    node = write_test.FakeNode(value="on")
    code = None
    try:
        sess(bad, node).preflight()
    except WT as exc:
        code = exc.code
    check("2E: GPU incorrecta -> WRONG_GPU", code == "WRONG_GPU", code)
    check("2E: no escribió", node.writes == [], node.writes)
    rc, _o, err = run_cli(["state-write-test", "--confirm", "--json"],
                          {"RX550_TORNEO_TARGET_PCI": "9999:9999"})
    check("2E: CLI GPU inexistente -> error sin write", rc != 0, err.strip()[-120:])


def t_F(gpu):
    node = write_test.FakeNode(value="on", authorized=False)
    code = None
    try:
        sess(gpu, node).preflight()
    except WT as exc:
        code = exc.code
    check("2F: path no autorizado -> PATH_INVALID", code == "PATH_INVALID", code)
    check("2F: sin escrituras", node.writes == [], node.writes)
    sn = write_test.SysfsNode("/tmp/rx550-fake-node-nonexistent",
                              "/sys/class/drm/card1/device/power/control")
    sn_code = None
    try:
        sn.write("auto")
    except WT as exc:
        sn_code = exc.code
    check("2F: SysfsNode rechaza path no autorizado", sn_code == "PATH_INVALID", sn_code)
    fn_code = None
    try:
        write_test.FileNode("/sys/class/drm/card1/device/power/control").write("auto")
    except WT as exc:
        fn_code = exc.code
    check("2F: FileNode rechaza /sys", fn_code == "PATH_INVALID", fn_code)


def t_G(gpu):
    for sig in (signal.SIGINT, signal.SIGTERM):
        node = write_test.FakeNode(value="on")

        def hook(_s, _sig=sig):
            os.kill(os.getpid(), _sig)

        s = sess(gpu, node, hooks={"after_write": hook})
        try:
            s.run()
        except WT:
            pass
        a = s.audit()
        check(f"2G: {sig.name} -> rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
        check(f"2G: {sig.name} -> final original", node.value == "on", node.value)
        check(f"2G: {sig.name} -> INTERRUPTED", a["result"] == "INTERRUPTED", a["result"])


def t_H(gpu):
    node = write_test.FakeNode(value="on")

    def hook(_s):
        raise RuntimeError("boom tras el write")

    s = sess(gpu, node, hooks={"after_write": hook})
    raised = None
    try:
        s.run()
    except RuntimeError:
        raised = "RuntimeError"
    a = s.audit()
    check("2H: excepción inesperada propagada", raised == "RuntimeError", raised)
    check("2H: se intentó rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("2H: estado final original", node.value == "on", node.value)
    check("2H: escrituras [auto,on]", node.writes == ["auto", "on"], node.writes)


def t_access(gpu):
    node = write_test.FakeNode(value="on", fail_read=True)
    code = None
    try:
        sess(gpu, node).preflight()
    except WT as exc:
        code = exc.code
    check("2F2: pérdida de acceso en preflight -> NODE_UNREADABLE", code == "NODE_UNREADABLE", code)
    check("2F2: sin escrituras", node.writes == [], node.writes)
    node2 = write_test.FakeNode(value="on", fail_read_after_write=True)
    s = sess(gpu, node2)
    try:
        s.run()
    except Exception:  # noqa: BLE001
        pass
    a = s.audit()
    check("2C2: pérdida de acceso tras write -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("2C2: un solo intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


SYS_WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")


def t_I(tmp):
    node_path = os.path.join(tmp, "fake-power-control")
    wr(node_path, "on")
    trace = os.path.join(tmp, "strace-write-test.txt")
    env = {"PYTHONPATH": SRC, "XDG_STATE_HOME": tmp,
           "RX550_TORNEO_TEST_MODE": "1",
           "RX550_TORNEO_TEST_WRITE_PATH": node_path,
           "RX550_TORNEO_AUDIT_WRITES": "1"}
    p = subprocess.run(["strace", "-f", "-e", "trace=openat,open", "-o", trace,
                        CLI, "state-write-test", "--confirm", "--json"],
                       capture_output=True, text=True, env={**os.environ, **env})
    check("2I: test-mode rc=0", p.returncode == 0, p.stderr.strip()[-200:])
    check("2I: nodo restaurado a on", (rd(node_path) or "").strip() == "on", rd(node_path))
    if not os.path.isfile(trace):
        check("2I: strace generado", False, "sin trace")
        return
    targets = []
    for ln in rd(trace).splitlines():
        m = re.search(r'"(/[^"]*)"', ln)
        if m and any(f in ln for f in SYS_WRITE_FLAGS):
            targets.append(m.group(1))
    sys_writes = [t for t in targets if t.startswith("/sys/")]
    node_writes = [t for t in targets if os.path.realpath(t) == os.path.realpath(node_path)]
    check("2I: sin escrituras a /sys", sys_writes == [], "; ".join(sys_writes[:3]))
    check("2I: escribe el nodo autorizado", len(node_writes) >= 1, str(targets[:6]))
    check("2I: exactamente 2 writes (temp + rollback)", len(node_writes) == 2, len(node_writes))


def t_dryrun(tmp):
    node_path = os.path.join(tmp, "dryrun-node")
    wr(node_path, "on")
    before = rd(node_path)
    rc, out, _e = run_cli(["state-write-test", "--json"],
                          {"XDG_STATE_HOME": tmp, "RX550_TORNEO_TEST_MODE": "1",
                           "RX550_TORNEO_TEST_WRITE_PATH": node_path})
    check("2D2: dry-run rc=0", rc == 0, out.strip()[-120:])
    payload = json.loads(out)
    check("2D2: dry-run no escribe", payload.get("no_write") is True, payload)
    check("2D2: nodo sin cambios", rd(node_path) == before, rd(node_path))
    has_audit = any(f.startswith("write-test-") for f in os.listdir(tmp))
    check("2D2: dry-run no genera auditoría", not has_audit)


def t_J(gpu, snap_before, real_path, mtime_before):
    snap_after = write_test.read_aux(gpu)
    diff = [(k, snap_before.get(k), snap_after.get(k))
            for k in write_test.STRICT_AUX if snap_before.get(k) != snap_after.get(k)]
    check("2J: settings de control sin cambios", diff == [], str(diff))
    ndiff = []
    for k in write_test.NORMALIZED_AUX:
        b = write_test.normalize_dpm(snap_before.get(k))
        a = write_test.normalize_dpm(snap_after.get(k))
        if b != a:
            ndiff.append((k, b, a))
    check("2J: tablas DPM (normalizadas) sin cambios", ndiff == [], str(ndiff))
    now = os.stat(real_path).st_mtime_ns
    check("2J: mtime power/control sin cambios", now == mtime_before, f"{now} != {mtime_before}")
    check("2J: power/control real intacto", (rd(real_path) or "").strip() == "on",
          rd(real_path))


def main():
    try:
        gpu = gpu_finder.discover()
    except gpu_finder.GPUError as exc:
        check("2: RX 550 disponible", False, f"{exc.code}: {exc.message}")
        return _report()
    snap_before = write_test.read_aux(gpu)
    real_path = write_test.production_node(gpu)[1]
    mtime_before = os.stat(real_path).st_mtime_ns
    tmp = tempfile.mkdtemp(prefix="rx550f2-")
    try:
        for fn in (t_A, t_B, t_C, t_D, t_E, t_F, t_G, t_H, t_access):
            try:
                fn(gpu)
            except Exception as exc:  # noqa: BLE001
                check(f"2{fn.__name__}: sin excepción no controlada", False,
                      f"{type(exc).__name__}: {exc}")
        try:
            t_I(tmp)
        except Exception as exc:  # noqa: BLE001
            check("2I: sin excepción", False, f"{type(exc).__name__}: {exc}")
        try:
            t_dryrun(tmp)
        except Exception as exc:  # noqa: BLE001
            check("2D2: sin excepción", False, f"{type(exc).__name__}: {exc}")
        t_J(gpu, snap_before, real_path, mtime_before)
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

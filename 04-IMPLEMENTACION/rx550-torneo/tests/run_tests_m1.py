#!/usr/bin/env python3
"""rx550-torneo — M1: tests del runner sostenido de power1_cap.

Todo no privilegiado: nodos en memoria (FakeNode/SeqNode) o archivo plano fuera
de /sys (test-mode del CLI). El workload es un comando trivial; NUNCA se ejecuta
vkmark ni se escribe sysfs. Incluye strace (solo power1_cap) y guard SIGKILL.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT, "src")
CLI = os.path.join(PROJECT, "rx550-torneo")
PY = sys.executable
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from rx550_torneo import cap_run, cli  # noqa: E402

RESULTS = []
TEMPDIRS = []

GPU = {
    "target": {"vendor": 0x1002, "device_id": 0x699f, "driver": "amdgpu",
               "pci": "0000:01:00.0", "bdf": "0000:01:00.0",
               "device": "/sys/class/drm/card1/device"},
    "intel": {"vendor": 0x8086, "card": "card0", "pci": "0000:00:02.0"},
    "drm_card": "card1",
    "hwmon": "/sys/class/drm/card1/device/hwmon/hwmon2",
    "display_cards": ["card0"],
}
LIMITS = {"min": 0, "max": 35000000}


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    return bool(cond)


def tmpdir():
    d = tempfile.mkdtemp(prefix="m1test-")
    TEMPDIRS.append(d)
    return d


def rd(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except OSError:
        return None


def base_aux():
    return {
        "power_control": "on",
        "power_dpm_force_performance_level": "auto",
        "pp_dpm_sclk": "0: 214Mhz *\n1: 1071Mhz",
        "pp_dpm_mclk": "0: 300Mhz *\n1: 625Mhz",
        "pp_power_profile_mode": "1 3D_FULL_SCREEN *:",
        "runtime_status": "active",
    }


def fake_reader(temp=45000):
    return {"gpu_busy_pct": 50, "mem_busy_pct": 10, "sclk_hz": 1071000000,
            "mclk_hz": 625000000, "power1_uw": 10000000, "power1_cap": 30000000,
            "temp_mc": temp, "runtime_status": "active"}


class SeqNode:
    """Nodo en memoria con readbacks guionados (valor post-write)."""

    def __init__(self, value="35000000", readbacks=None):
        self.value = value
        self.writes = []
        self._readbacks = list(readbacks or [])

    def verify_authorized(self):
        return True

    def read(self):
        return self.value

    def write(self, value):
        self.value = value
        self.writes.append(value)
        if self._readbacks:
            self.value = self._readbacks.pop(0)


def make_session(node, target=30000000, workload_cmd=None, **kw):
    kw.setdefault("aux_reader", lambda _g: base_aux())
    kw.setdefault("limits_reader", lambda _g: dict(LIMITS))
    kw.setdefault("reader", lambda: fake_reader())
    kw.setdefault("enable_guard", False)
    kw.setdefault("out_dir", tmpdir())
    kw.setdefault("log_reader", lambda since, until: ([], None, "short-iso"))
    if workload_cmd is None:
        workload_cmd = ["/bin/sh", "-c", "sleep 0.1"]
    return cap_run.CapRunSession(GPU, node, target, workload_cmd=workload_cmd, **kw)


def marker_workload(marker, body="sleep 0.1"):
    return ["/bin/sh", "-c", f"printf ran > {marker}; {body}"]


class ApplyThenRaiseNode(SeqNode):
    """Aplica el write y luego lanza (simula SET aplicado + excepción)."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.pending_raise = True

    def write(self, value):
        self.value = value
        self.writes.append(value)
        if self.pending_raise:
            self.pending_raise = False
            raise OSError("SET aplicado y luego excepción simulada")


def t_happy():
    out = tmpdir()
    marker = os.path.join(out, "marker.txt")
    node = SeqNode("35000000")
    s = make_session(node, workload_cmd=marker_workload(marker), out_dir=out)
    a = s.run()
    check("A: resultado OK", a["result"] == "OK", a["result"])
    check("A: original 35000000", a["original"] == 35000000, a["original"])
    check("A: set readback", a["set_readback"] == "30000000", a["set_readback"])
    check("A: restaurado", a["restored"] == "35000000", a["restored"])
    check("A: readback_final", a["readback_final"] == "35000000", a["readback_final"])
    check("A: exactamente 2 writes", node.writes == ["30000000", "35000000"], node.writes)
    check("A: workload ejecutado", os.path.exists(marker))
    check("A: rollback 1 intento", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("A: aux sin cambios", a["aux_unchanged"])
    lines = (rd(os.path.join(out, "telemetry.csv")) or "").splitlines()
    check("A: telemetry header",
          bool(lines) and lines[0] == ",".join(cap_run.TELEMETRY_COLUMNS),
          lines[0] if lines else "sin archivo")
    check("A: telemetry con muestras", len(lines) >= 2, len(lines))


def t_original_mismatch():
    node = SeqNode("30000000")
    a = make_session(node).run()
    check("B: original!=35M -> ERROR", a["result"] == "ERROR", a["result"])
    check("B: código ORIGINAL_MISMATCH",
          a["fatal"] and a["fatal"]["code"] == "ORIGINAL_MISMATCH", a["fatal"])
    check("B: sin escrituras", node.writes == [], node.writes)


def t_precondition(field, value, label):
    out = tmpdir()
    marker = os.path.join(out, "marker.txt")
    aux = base_aux()
    aux[field] = value
    node = SeqNode("35000000")
    a = make_session(node, aux_reader=lambda _g: dict(aux),
                     workload_cmd=marker_workload(marker), out_dir=out).run()
    check(f"C: {label} -> ERROR", a["result"] == "ERROR", a["result"])
    check(f"C: {label} -> PRECONDITION",
          a["fatal"] and a["fatal"]["code"] == "PRECONDITION", a["fatal"])
    check(f"C: {label} sin escrituras ni workload",
          node.writes == [] and not os.path.exists(marker), node.writes)


def t_forcing():
    aux = base_aux()
    aux["pp_dpm_sclk"] = "0: 214Mhz *\n1: 1071Mhz *"
    node = SeqNode("35000000")
    a = make_session(node, aux_reader=lambda _g: dict(aux)).run()
    check("E: forcing -> FORCING_DETECTED",
          a["fatal"] and a["fatal"]["code"] == "FORCING_DETECTED", a["fatal"])
    check("E: sin escrituras", node.writes == [], node.writes)


def t_out_of_range():
    node = SeqNode("35000000")
    a = make_session(node, target=40000000).run()
    check("F: target>max -> OUT_OF_RANGE",
          a["fatal"] and a["fatal"]["code"] == "OUT_OF_RANGE", a["fatal"])
    check("F: sin escrituras", node.writes == [], node.writes)


def t_set_readback_fail():
    out = tmpdir()
    marker = os.path.join(out, "marker.txt")
    node = SeqNode("35000000", readbacks=["11111111"])
    a = make_session(node, workload_cmd=marker_workload(marker), out_dir=out).run()
    check("G: set readback malo -> SET_READBACK",
          a["fatal"] and a["fatal"]["code"] == "SET_READBACK", a["fatal"])
    check("G: workload NO ejecutado", not os.path.exists(marker))
    check("G: restauró original", node.value == "35000000", node.value)
    check("G: 2 writes (set+restore)", node.writes == ["30000000", "35000000"], node.writes)


def t_restore_fail():
    out = tmpdir()
    marker = os.path.join(out, "marker.txt")
    node = SeqNode("35000000", readbacks=["30000000", "99999999"])
    a = make_session(node, workload_cmd=marker_workload(marker), out_dir=out).run()
    check("H: restore no verificado -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("H: fatal ROLLBACK_MISMATCH",
          a["fatal"] and a["fatal"]["code"] == "ROLLBACK_MISMATCH", a["fatal"])
    check("H: un solo intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])
    check("H: workload sí ejecutado", os.path.exists(marker))

def t_temp_abort():
    out = tmpdir()
    node = SeqNode("35000000")
    s = make_session(node, reader=lambda: fake_reader(91000),
                     workload_cmd=["/bin/sh", "-c", "sleep 5"], out_dir=out)
    s.workload_timeout = 10
    a = s.run()
    check("I: temp>=90 -> ABORTED", a["result"] == "ABORTED", a["result"])
    check("I: fatal TEMP_ABORT", a["fatal"] and a["fatal"]["code"] == "TEMP_ABORT", a["fatal"])
    check("I: restaurado", node.value == "35000000", node.value)
    check("I: un intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


def t_timeout():
    out = tmpdir()
    node = SeqNode("35000000")
    s = make_session(node, workload_cmd=["/bin/sh", "-c", "sleep 5"], out_dir=out)
    s.workload_timeout = 0.5
    a = s.run()
    check("J: timeout -> ABORTED", a["result"] == "ABORTED", a["result"])
    check("J: fatal WORKLOAD_TIMEOUT",
          a["fatal"] and a["fatal"]["code"] == "WORKLOAD_TIMEOUT", a["fatal"])
    check("J: restaurado", node.value == "35000000", node.value)


def t_order_before_workload():
    out = tmpdir()
    node = SeqNode("35000000")
    seen = {}

    def hook(sess):
        seen["readback"] = sess.set_readback
        seen["writes"] = list(node.writes)

    s = make_session(node, hooks={"before_workload": hook}, out_dir=out)
    s.run()
    check("K: readback confirmado antes del workload", seen.get("readback") == "30000000",
          seen.get("readback"))
    check("K: solo el set escrito antes del workload",
          seen.get("writes") == ["30000000"], seen.get("writes"))


def t_sigterm():
    out = tmpdir()
    node = SeqNode("35000000")

    def hook(_sess):
        os.kill(os.getpid(), signal.SIGTERM)

    a = make_session(node, hooks={"before_workload": hook}, out_dir=out).run()
    check("L: SIGTERM -> INTERRUPTED", a["result"] == "INTERRUPTED", a["result"])
    check("L: restaurado", node.value == "35000000", node.value)
    check("L: un intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


def t_aux_changed():
    out = tmpdir()
    counter = {"n": 0}

    def aux(_g):
        counter["n"] += 1
        d = base_aux()
        if counter["n"] >= 2:
            d["pp_dpm_mclk"] = "0: 400Mhz *\n1: 625Mhz"
        return d

    node = SeqNode("35000000")
    a = make_session(node, aux_reader=aux, out_dir=out).run()
    check("P: aux cambiado -> AUX_CHANGED", a["result"] == "AUX_CHANGED", a["result"])
    check("P: restaurado igualmente", node.value == "35000000", node.value)


def _sched_kwargs():
    return {
        "aux_reader": lambda _g: base_aux(),
        "limits_reader": lambda _g: dict(LIMITS),
        "reader": lambda: fake_reader(),
        "enable_guard": False,
        "log_reader": lambda since, until: ([], None, "short-iso"),
        "workload_cmd": ["/bin/sh", "-c", "sleep 0.05"],
    }


def t_schedule_alternation():
    out = tmpdir()
    node = SeqNode("35000000")
    audits = cap_run.run_schedule(GPU, node, out_dir=out, blocks=2,
                                  arms=(35000000, 30000000),
                                  cooldown_fn=lambda: None,
                                  session_kwargs=_sched_kwargs())
    check("O: 4 corridas OK", len(audits) == 4 and all(a["result"] == "OK" for a in audits),
          [a["result"] for a in audits])
    arm_seq = [audits[i]["target"] for i in range(len(audits))]
    check("O: orden alternado 35/30,30/35",
          arm_seq == [35000000, 30000000, 30000000, 35000000], arm_seq)
    check("O: 2 writes por corrida", len(node.writes) == 8, len(node.writes))
    check("O: restore=35000000 en writes impares",
          all(node.writes[i] == "35000000" for i in range(1, 8, 2)), node.writes)
    summary = json.loads(rd(os.path.join(out, "m1-schedule.json")))
    check("O: schedule sin parada temprana", summary["stopped_early"] is False, summary)


def t_workload_failed():
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, workload_cmd=["/bin/sh", "-c", "exit 7"], out_dir=out).run()
    check("R: rc!=0 -> ERROR", a["result"] == "ERROR", a["result"])
    check("R: fatal WORKLOAD_FAILED",
          a["fatal"] and a["fatal"]["code"] == "WORKLOAD_FAILED", a["fatal"])
    check("R: workload_rc en audit", a["workload_rc"] == 7, a["workload_rc"])
    check("R: restauró original", node.value == "35000000", node.value)
    check("R: set+restore", node.writes == ["30000000", "35000000"], node.writes)


def t_schedule_aborts_on_workload_failed():
    out = tmpdir()
    node = SeqNode("35000000")
    kw = _sched_kwargs()
    kw["workload_cmd"] = ["/bin/sh", "-c", "exit 7"]
    audits = cap_run.run_schedule(GPU, node, out_dir=out, blocks=3, arms=(30000000,),
                                  cooldown_fn=lambda: None, session_kwargs=kw)
    check("R: schedule aborta ante ERROR",
          len(audits) == 1 and audits[0]["result"] == "ERROR", [x["result"] for x in audits])
    summary = json.loads(rd(os.path.join(out, "m1-schedule.json")))
    check("R: stopped_early true", summary["stopped_early"] is True, summary)


def t_exception_after_set():
    out = tmpdir()
    node = ApplyThenRaiseNode("35000000")
    a = make_session(node, out_dir=out).run()
    check("T: excepción tras SET -> ERROR", a["result"] == "ERROR", a["result"])
    check("T: restauró tras excepción", node.value == "35000000", node.value)
    check("T: set+restore", node.writes == ["30000000", "35000000"], node.writes)
    check("T: un intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


def t_workload_identity():
    from rx550_torneo import cli, write_test
    check("S: no-root -> (None,None)",
          cli._workload_identity(lambda: 1000, {}) == (None, None))
    check("S: root+SUDO_UID -> usuario",
          cli._workload_identity(lambda: 0, {"SUDO_UID": "1000", "SUDO_GID": "1000"})
          == (1000, 1000))
    cases = [({}, "sin SUDO_UID"),
             ({"SUDO_UID": "0", "SUDO_GID": "0"}, "SUDO_UID=0"),
             ({"SUDO_UID": "abc"}, "no numérico")]
    for env, label in cases:
        rejected = False
        try:
            cli._workload_identity(lambda: 0, env)
        except write_test.WriteTestError:
            rejected = True
        check(f"S: root {label} -> rechazo", rejected)


def t_root_reject_no_write():
    from types import SimpleNamespace
    from rx550_torneo import cli, cap_test, write_test

    class Node:
        writes = []
        path = "/sys/class/drm/card1/device/hwmon/hwmon2/power1_cap"

        def verify_authorized(self):
            return True

    node = Node()
    saved = (cli.os.geteuid, cli._gpu_from_env, cap_test.production_cap_node)
    had = os.environ.pop("SUDO_UID", None)
    had_gid = os.environ.pop("SUDO_GID", None)
    cli.os.geteuid = lambda: 0
    cli._gpu_from_env = lambda: GPU
    cap_test.production_cap_node = lambda _g: (node, "logical")
    rejected = False
    try:
        try:
            cli._m1_context(SimpleNamespace())
        except write_test.WriteTestError as exc:
            rejected = exc.code == "NO_SUDO_UID"
    finally:
        cli.os.geteuid, cli._gpu_from_env, cap_test.production_cap_node = saved
        if had is not None:
            os.environ["SUDO_UID"] = had
        if had_gid is not None:
            os.environ["SUDO_GID"] = had_gid
    check("S: root sin SUDO_UID rechazado", rejected)
    check("S: sin escrituras", node.writes == [], node.writes)


def t_gpu_reset():
    out = tmpdir()
    node = SeqNode("35000000")
    reader = lambda since, until: (["sep 19 host amdgpu: ring gfx timeout"], None, "short-iso")
    a = make_session(node, log_reader=reader, out_dir=out).run()
    check("U: reset/hang -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("U: fatal GPU_RESET_OR_HANG",
          a["fatal"] and a["fatal"]["code"] == "GPU_RESET_OR_HANG", a["fatal"])
    check("U: evidencia en audit",
          a["gpu_reset_check"].get("matches") == ["sep 19 host amdgpu: ring gfx timeout"],
          a["gpu_reset_check"])
    check("U: checked true", a["gpu_reset_check"].get("checked") is True, a["gpu_reset_check"])
    check("U: restauró", node.value == "35000000", node.value)
    check("U: un intento de rollback", a["rollback_attempts"] == 1, a["rollback_attempts"])


def t_gpu_reset_unavailable_is_not_reset():
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, log_reader=lambda s, u: (None, "sin permiso", None), out_dir=out).run()
    check("U: journal no disponible -> OK y documentado",
          a["result"] == "OK" and a["gpu_reset_check"]["checked"] is False, a["gpu_reset_check"])
    check("U: error registrado",
          a["gpu_reset_check"]["error"] == "sin permiso", a["gpu_reset_check"])


def t_schedule_aborts_on_gpu_reset():
    out = tmpdir()
    node = SeqNode("35000000")

    def reader(since, until):
        return (["sep 19 host amdgpu: GPU reset begin!"], None, "short-iso")

    kw = _sched_kwargs()
    kw["log_reader"] = reader
    audits = cap_run.run_schedule(GPU, node, out_dir=out, blocks=2, arms=(30000000,),
                                  cooldown_fn=lambda: None, session_kwargs=kw)
    check("U: schedule aborta ante GPU reset",
          len(audits) == 1 and audits[0]["result"] == "CRITICAL",
          [x["result"] for x in audits])
    summary = json.loads(rd(os.path.join(out, "m1-schedule.json")))
    check("U: stopped_early true", summary["stopped_early"] is True, summary)


# --- A–H: detector 7d y entorno del workload --------------------------------
PRT_BENIGN = ("sep 18 host amdgpu 0000:01:00.0: Disabling VM faults because of PRT request!")
VM_FAULT = "sep 19 host amdgpu 0000:01:00.0: VM fault (0x02) on page 0x0, read from ring gfx"


def t_benign_prt_history():
    check("A: PRT histórico no es reset", cap_run.is_reset_line(PRT_BENIGN) is False)
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([PRT_BENIGN], None, "short-iso")).run()
    check("A: sesión con PRT -> OK", a["result"] == "OK", a["result"])
    check("A: checked true, 0 matches",
          a["gpu_reset_check"]["checked"] is True and a["gpu_reset_check"]["matches"] == [],
          a["gpu_reset_check"])


def t_isolated_vm_fault():
    check("B: VM fault aislado no es reset", cap_run.is_reset_line(VM_FAULT) is False)
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([VM_FAULT], None, "short-iso")).run()
    check("B: sesión con VM fault -> OK", a["result"] == "OK", a["result"])


def t_new_ring_timeout_critical():
    line = "sep 19 host amdgpu 0000:01:00.0: ring gfx_0.0.0 timeout, signaled seq=1"
    check("C: ring timeout es reset", cap_run.is_reset_line(line) is True)
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([line], None, "short-iso")).run()
    check("C: ring timeout nuevo -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("C: restauró", node.value == "35000000", node.value)


def t_new_gpu_reset_critical():
    line = "sep 19 host amdgpu 0000:01:00.0: GPU reset begin!"
    check("D: gpu reset es reset", cap_run.is_reset_line(line) is True)
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([line], None, "short-iso")).run()
    check("D: gpu reset nuevo -> CRITICAL", a["result"] == "CRITICAL", a["result"])
    check("D: restauró", node.value == "35000000", node.value)


def t_incompatible_log_format():
    out = tmpdir()
    node = SeqNode("35000000")
    line = "sep 19 host amdgpu 0000:01:00.0: GPU reset begin!"
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([line], None, "raw")).run()
    check("E: formato incompatible -> checked false", a["gpu_reset_check"]["checked"] is False,
          a["gpu_reset_check"])
    check("E: formato registrado", a["gpu_reset_check"]["format"] == "raw", a["gpu_reset_check"])
    check("E: NO CRITICAL", a["result"] == "OK", a["result"])


def t_empty_journal_window():
    out = tmpdir()
    node = SeqNode("35000000")
    a = make_session(node, out_dir=out,
                     log_reader=lambda s, u: ([], None, "short-iso")).run()
    check("F: ventana vacía -> checked true", a["gpu_reset_check"]["checked"] is True,
          a["gpu_reset_check"])
    check("F: 0 matches, OK", a["gpu_reset_check"]["matches"] == [] and a["result"] == "OK",
          a["gpu_reset_check"])
    check("F: ventana temporal registrada",
          a["gpu_reset_check"]["since"] < a["gpu_reset_check"]["until"], a["gpu_reset_check"])


def t_workload_home_nonroot():
    import pwd as _pwd
    uid = os.getuid()
    env = cli._workload_environment(uid, os.getgid(),
                                    base={"HOME": "/root", "XDG_RUNTIME_DIR": "/root",
                                          "PATH": "/usr/bin", "MESA_CUSTOM": "1"})
    expected_home = _pwd.getpwuid(uid).pw_dir
    check("G: HOME del usuario, no /root", env["HOME"] == expected_home, env.get("HOME"))
    check("G: HOME no es /root", env["HOME"] != "/root", env.get("HOME"))
    check("G: MESA_CUSTOM limpiado", "MESA_CUSTOM" not in env, env.get("MESA_CUSTOM"))
    check("G: PATH preservado", env.get("PATH") == "/usr/bin", env.get("PATH"))


def t_schedule_stops_on_critical():
    out = tmpdir()
    node = SeqNode("35000000", readbacks=["30000000", "99999999"])
    audits = cap_run.run_schedule(GPU, node, out_dir=out, blocks=3,
                                  arms=(30000000,),
                                  cooldown_fn=lambda: None,
                                  session_kwargs=_sched_kwargs())
    check("Q: se detiene ante CRITICAL", len(audits) == 1, len(audits))
    check("Q: resultado CRITICAL", audits[0]["result"] == "CRITICAL", audits[0]["result"])
    summary = json.loads(rd(os.path.join(out, "m1-schedule.json")))
    check("Q: stopped_early true", summary["stopped_early"] is True, summary)


WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")


def _parse_writes(trace_text):
    events = []
    for i, line in enumerate(trace_text.splitlines()):
        if "open" not in line or not any(f in line for f in WRITE_FLAGS):
            continue
        m = re.search(r'"([^"]+)"', line)
        if m:
            events.append((i, m.group(1)))
    return events


def t_workload_radv_icd_selector():
    env = cap_run.workload_env({
        "MESA_VK_DEVICE_SELECT": "Intel",
        "VK_DRIVER_FILES": "/tmp/intel.json",
        "LD_LIBRARY_PATH": "/tmp/custom",
    })
    check("G2: DRI_PRIME estable por vendor:device",
          env.get("DRI_PRIME") == "1002:699f", env.get("DRI_PRIME"))
    check("G3: ICD RADV forzado",
          env.get("VK_ICD_FILENAMES", "").endswith("radeon_icd.x86_64.json"),
          env.get("VK_ICD_FILENAMES"))
    check("G4: selector Mesa numérico/no confiable eliminado",
          "MESA_VK_DEVICE_SELECT" not in env, env.get("MESA_VK_DEVICE_SELECT"))
    check("G5: VK_DRIVER_FILES heredado eliminado",
          "VK_DRIVER_FILES" not in env, env.get("VK_DRIVER_FILES"))
    check("G6: LD_LIBRARY_PATH custom eliminado",
          "LD_LIBRARY_PATH" not in env, env.get("LD_LIBRARY_PATH"))


def t_strace():
    if not shutil.which("strace"):
        print("[SKIP] M: strace no instalado; no se instala ni se trata como PASS")
        return
    tmp = tmpdir()
    cap = os.path.join(tmp, "fake-power1-cap")
    marker = os.path.join(tmp, "marker.txt")
    trace = os.path.join(tmp, "trace.txt")
    with open(cap, "w", encoding="utf-8") as fh:
        fh.write("35000000")
    env = {
        "PYTHONPATH": SRC, "XDG_STATE_HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1",
        "RX550_TORNEO_TEST_MODE": "1", "RX550_TORNEO_TEST_WRITE_PATH": cap,
        "RX550_TORNEO_TEST_WORKLOAD": f"printf ran > {marker}",
    }
    p = subprocess.run(
        ["strace", "-f", "-e", "trace=openat,open", "-o", trace,
         PY, "-m", "rx550_torneo.cli", "m1-run", "--confirm", "--json"],
        capture_output=True, text=True, env={**os.environ, **env})
    check("M: CLI test-mode rc=0", p.returncode == 0, (p.stderr or p.stdout)[-200:])
    check("M: cap restaurado al original", (rd(cap) or "").strip() == "35000000", rd(cap))
    check("M: workload ejecutado", os.path.exists(marker))
    events = _parse_writes(rd(trace) or "")
    cap_events = [i for i, path in events if os.path.realpath(path) == os.path.realpath(cap)]
    sys_events = [path for _i, path in events if path.startswith("/sys/")]
    mk_events = [i for i, path in events if os.path.realpath(path) == os.path.realpath(marker)]
    check("M: cero escrituras a /sys", sys_events == [], "; ".join(sys_events[:3]))
    prohibited = [path for _i, path in events if re.search(
        r"(power/control|power_dpm_force_performance_level|pp_dpm_sclk|"
        r"pp_dpm_mclk|pp_power_profile_mode|/reset$|reset_method)", path)]
    check("H: 0 writes a nodos sysfs distintos de power1_cap", prohibited == [],
          "; ".join(prohibited[:3]))
    check("M: exactamente 2 writes a power1_cap", len(cap_events) == 2, len(cap_events))
    check("M: set antes de ejecutar el workload",
          bool(cap_events) and bool(mk_events) and min(cap_events) < min(mk_events),
          f"cap={cap_events} marker={mk_events}")


def t_guard_kill():
    tmp = tmpdir()
    cap = os.path.join(tmp, "fake-power1-cap")
    out = os.path.join(tmp, "out")
    with open(cap, "w", encoding="utf-8") as fh:
        fh.write("35000000")
    env = {
        "PYTHONPATH": SRC, "XDG_STATE_HOME": tmp, "PYTHONDONTWRITEBYTECODE": "1",
        "RX550_TORNEO_TEST_MODE": "1", "RX550_TORNEO_TEST_WRITE_PATH": cap,
        "RX550_TORNEO_TEST_WORKLOAD": "sleep 30",
    }
    proc = subprocess.Popen(
        [PY, "-m", "rx550_torneo.cli", "m1-run", "--confirm", "--json", "--out", out],
        env={**os.environ, **env}, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        start_new_session=True)
    try:
        applied = False
        for _ in range(100):
            if (rd(cap) or "").strip() == "30000000":
                applied = True
                break
            time.sleep(0.1)
        check("N: cap aplicado (30000000)", applied, rd(cap))
        os.kill(proc.pid, signal.SIGKILL)
        restored = False
        for _ in range(100):
            if (rd(cap) or "").strip() == "35000000":
                restored = True
                break
            time.sleep(0.1)
        check("N: guard restauró tras SIGKILL", restored, rd(cap))
    finally:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            pass


def main():
    tests = [
        t_happy, t_original_mismatch, t_forcing, t_out_of_range,
        t_set_readback_fail, t_restore_fail, t_temp_abort, t_timeout,
        t_order_before_workload, t_sigterm, t_aux_changed,
        t_schedule_alternation, t_schedule_stops_on_critical,
        t_workload_failed, t_schedule_aborts_on_workload_failed,
        t_exception_after_set, t_workload_identity, t_root_reject_no_write,
        t_gpu_reset, t_gpu_reset_unavailable_is_not_reset, t_schedule_aborts_on_gpu_reset,
        t_benign_prt_history, t_isolated_vm_fault, t_new_ring_timeout_critical,
        t_new_gpu_reset_critical, t_incompatible_log_format, t_empty_journal_window,
        t_workload_home_nonroot, t_workload_radv_icd_selector,
        t_strace, t_guard_kill,
        lambda: t_precondition("power_control", "auto", "power/control!=on"),
        lambda: t_precondition("power_dpm_force_performance_level", "high", "DPM!=auto"),
    ]
    try:
        for fn in tests:
            try:
                fn()
            except Exception as exc:  # noqa: BLE001
                check(f"{fn}: sin excepción no controlada", False,
                      f"{type(exc).__name__}: {exc}")
    finally:
        for d in TEMPDIRS:
            shutil.rmtree(d, ignore_errors=True)
    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" +
              (f"  -- {detail}" if detail and not ok else ""))
    print(f"\n{passed}/{len(RESULTS)} checks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

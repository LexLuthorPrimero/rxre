#!/usr/bin/env python3
"""rx550-torneo — Fase 1: tests obligatorios A–J (read-only).

Cada test se ejecuta con su propio XDG_STATE_HOME temporal. Ninguna prueba
escribe sysfs; el test J lo verifica con auditoría interna + strace.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(PROJECT, "src")
CLI = os.path.join(PROJECT, "rx550-torneo")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))
    return bool(cond)


def run(args, env_extra=None):
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC + (":" + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.update(env_extra or {})
    p = subprocess.run([CLI] + args, capture_output=True, text=True, env=env)
    return p.returncode, p.stdout, p.stderr


def read(p):
    try:
        with open(p, "r") as fh:
            return fh.read()
    except OSError:
        return None


def sha(p):
    d = read(p)
    return hashlib.sha256(d.encode()).hexdigest() if d is not None else None


def new_state_dir():
    return tempfile.mkdtemp(prefix="rx550test-")


# ---------------------------------------------------------------- A, B, C, D

def test_A(tmp):
    rc, out, err = run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    check("A: status rc=0", rc == 0, err.strip())
    try:
        j = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        check("A: status JSON válido", False, str(exc))
        return
    g = j["gpu"]
    check("A: detecta PCI objetivo 1002:699f", g["target_pci"] == "1002:699f", g["target_pci"])
    check("A: resuelve DRM card", g["drm_card"].startswith("card"), g["drm_card"])
    check("A: resuelve render node", bool(re.search(r"/renderD[0-9]+$", g["render_node"])),
          g["render_node"])
    check("A: hwmon existe", os.path.isdir(g["hwmon"]), g["hwmon"])
    check("A: driver amdgpu", g["driver"] == "amdgpu", g["driver"])
    check("A: cap leído > 0", int(j["live"]["power1_cap"]) > 0, j["live"]["power1_cap"])
    # verificación independiente del árbol sysfs
    card = g["drm_card"]
    v = read(f"/sys/class/drm/{card}/device/vendor")
    d = read(f"/sys/class/drm/{card}/device/device")
    check("A: vendor sysfs == 0x1002", (v or "").strip() == "0x1002", v)
    check("A: device sysfs == 0x699f", (d or "").strip() == "0x699f", d)


def test_B(tmp):
    rc, out, _err = run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    j = json.loads(out)
    g = j["gpu"]
    check("B: Intel detectada 8086:0412", g["intel_pci"] == "8086:0412", g["intel_pci"])
    check("B: Intel detectada por card dinámico", bool(re.fullmatch(r"card[0-9]+", g["intel_card"])),
          g["intel_card"])
    check("B: objetivo != Intel", g["drm_card"] != g["intel_card"],
          f"{g['drm_card']} vs {g['intel_card']}")
    intel_link = f"/sys/class/drm/{g['intel_card']}/device/driver"
    intel_drv = (os.path.basename(os.path.realpath(intel_link))
                 if os.path.islink(intel_link) else None)
    check("B: Intel es display (i915)", intel_drv == "i915", intel_drv)


def test_C(tmp):
    rc, out, _err = run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    j = json.loads(out)
    g = j["gpu"]
    check("C: driver objetivo == amdgpu", g["driver"] == "amdgpu", g["driver"])
    intel_drv_link = f"/sys/class/drm/{g['intel_card']}/device/driver"
    intel_drv = (os.path.basename(os.path.realpath(intel_drv_link))
                 if os.path.islink(intel_drv_link) else None)
    check("C: driver Intel == i915", intel_drv == "i915", intel_drv)


def test_D(tmp):
    rc, out, _err = run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    j = json.loads(out)
    g = j["gpu"]
    dev_real = os.path.realpath(f"/sys/class/drm/{g['drm_card']}/device")
    hw_real = os.path.realpath(g["hwmon"])
    check("D: hwmon pertenece al device de la RX550",
          hw_real.startswith(dev_real + os.sep), f"{hw_real} !< {dev_real}")
    check("D: render node es char device", os.path.exists(g["render_node"]) and
          (os.stat(g["render_node"]).st_mode & 0o170000) == 0o020000, g["render_node"])
    link = f"/dev/dri/by-path/pci-{g['bdf']}-render"
    tgt = os.path.realpath(link) if os.path.islink(link) else None
    check("D: by-path render apunta al render node detectado",
          tgt == os.path.realpath(g["render_node"]), f"{link} -> {tgt}")
    cap = os.path.join(g["hwmon"], "power1_cap")
    prot = os.path.join(f"/sys/class/drm/{g['drm_card']}/device", "power_dpm_force_performance_level")
    check("D: power1_cap localizado en hwmon", os.path.exists(cap), cap)
    check("D: dpm level localizado en device", os.path.exists(prot), prot)


# ---------------------------------------------------------------- E, F, G

def test_E(tmp):
    rc, out, err = run(["state-save", "--json"], {"XDG_STATE_HOME": tmp})
    check("E: state-save rc=0", rc == 0, err.strip())
    try:
        res = json.loads(out)
    except Exception as exc:  # noqa: BLE001
        check("E: salida JSON", False, str(exc))
        return None
    sp = res["path"]
    check("E: state.json creado", os.path.isfile(sp), sp)
    check("E: state.json.sha256 creado", os.path.isfile(sp + ".sha256"))
    body = read(sp)
    check("E: hash del archivo coincide con .sha256",
          hashlib.sha256(body.strip().encode()).hexdigest() == read(sp + ".sha256").strip())
    st = json.loads(body)
    check("E: schema_version==1", st.get("schema_version") == 1)
    for k in ("timestamp", "kernel", "target_pci", "drm_card", "hwmon", "render_node",
              "driver", "restorable", "capture"):
        check(f"E: campo {k} presente", k in st)
    check("E: 6 campos restaurables", len(st["restorable"]["files"]) == 6,
          list(st["restorable"]["files"]))
    check("E: power1_cap capturado", st["restorable"]["files"].get("power1_cap") is not None)
    return sp


def test_F(tmp, sp):
    rc, out, err = run(["state-show", "--json"], {"XDG_STATE_HOME": tmp})
    check("F: state-show rc=0", rc == 0, err.strip())
    try:
        shown = json.loads(out)
        saved = json.loads(read(sp))
    except Exception as exc:  # noqa: BLE001
        check("F: round-trip JSON", False, str(exc))
        return
    check("F: state-show == state.json (round-trip)", shown == saved)
    rc2, out2, err2 = run(["state-load", "--json"], {"XDG_STATE_HOME": tmp})
    check("F: state-load rc=0", rc2 == 0, err2.strip())
    info = json.loads(out2) if rc2 == 0 else {}
    check("F: sin campos restaurables faltantes", info.get("missing_restorable") == [],
          info.get("missing_restorable"))
    # F2: corrupción detectada
    with open(sp, "a") as fh:
        fh.write("x")
    rc3, _o, err3 = run(["state-show", "--json"], {"XDG_STATE_HOME": tmp})
    check("F2: estado corrupto rechazado", rc3 != 0 and "corrupto" in err3.lower(), err3.strip())
    with open(sp, "r+") as fh:  # restaurar
        data = fh.read()
        fh.seek(0)
        fh.write(data[:-1])
        fh.truncate()


def test_G(tmp, sp):
    before = sha(sp)
    rc, _o, err = run(["state-save"], {"XDG_STATE_HOME": tmp})
    check("G: segundo state-save sin --force falla", rc != 0, err.strip())
    check("G: mensaje de protección", "existe" in err.lower() or "force" in err.lower(), err.strip())
    check("G: estado existente NO modificado", sha(sp) == before)


# ---------------------------------------------------------------- H, I

def test_H(tmp):
    rc, _o, err = run(["status", "--json"],
                      {"XDG_STATE_HOME": tmp, "RX550_TORNEO_TARGET_PCI": "9999:9999"})
    check("H: GPU objetivo ausente -> error seguro", rc != 0 and "no encontrada" in err)
    rc2, _o2, err2 = run(["status", "--json"],
                         {"XDG_STATE_HOME": tmp, "RX550_TORNEO_INTEL_PCI": "8086:9999"})
    check("H: Intel ausente -> error seguro", rc2 != 0 and ("Intel" in err2 or "no encontrada" in err2))
    rc3, _o3, err3 = run(["status", "--json"],
                         {"XDG_STATE_HOME": tmp, "RX550_TORNEO_TARGET_PCI": "0000:0412"})
    check("H: PCI incorrecto (Intel como objetivo) -> error", rc3 != 0)


def test_I(tmp):
    rc, _o, err = run(["verify"], {"XDG_STATE_HOME": tmp,
                                   "RX550_TORNEO_RENDER_OVERRIDE": "/dev/fake-render-xyz"})
    check("I: render inesperado -> BAD_PATH seguro", rc != 0 and "BAD_PATH" in err, err.strip())
    rc2, _o2, err2 = run(["status"], {"XDG_STATE_HOME": tmp,
                                      "RX550_TORNEO_HWMON_OVERRIDE": "/sys/class/drm"})
    check("I: hwmon inesperado -> BAD_PATH seguro", rc2 != 0 and "BAD_PATH" in err2, err2.strip())
    # unit: override hwmon fuera del device -> GPUError
    from rx550_torneo import gpu_finder
    try:
        gpu_finder.discover(overrides={"hwmon": "/sys/class/drm"})
        check("I: discover() rechaza ruta inesperada", False)
    except gpu_finder.GPUError as exc:
        check("I: discover() rechaza ruta inesperada", exc.code == "BAD_PATH", exc.code)


# ---------------------------------------------------------------- J

SYS_WRITE_FLAGS = ("O_WRONLY", "O_RDWR", "O_CREAT", "O_TRUNC", "O_APPEND")


def test_J(tmp):
    ro = ["status", "state-show", "verify"]
    for cmd in ro:
        rc, out, _err = run([cmd, "--json"], {"XDG_STATE_HOME": tmp, "RX550_TORNEO_AUDIT_WRITES": "1"})
        try:
            writes = json.loads(out)["audit_writes"]
            check(f"J: {cmd} rc=0", rc == 0)
        except Exception:  # noqa: BLE001
            writes = ["<parse-error>"]
        check(f"J: {cmd} sin escrituras", writes == [], str(writes))

    # state-save: única escritura permitida = archivo de estado (no /sys)
    state_dir = tmp
    rc, out, _err = run(["state-save", "--force", "--json"],
                        {"XDG_STATE_HOME": state_dir, "RX550_TORNEO_AUDIT_WRITES": "1"})
    writes = json.loads(out)["audit_writes"]
    check("J: state-save solo escribe el archivo de estado",
          bool(writes) and all(w.endswith("state.json") and w.startswith(tmp) for w in writes), str(writes))
    check("J: state-save no escribe en /sys", not any(w.startswith("/sys") for w in writes))

    # strace: verificar ausencia de openat de escritura a /sys
    trace = os.path.join(tmp, "strace.txt")
    env = dict(os.environ)
    env["PYTHONPATH"] = SRC
    env["XDG_STATE_HOME"] = tmp
    if shutil.which("strace"):
        p = subprocess.run(["strace", "-f", "-e", "trace=openat,open", "-o", trace,
                            CLI, "status", "--json"], capture_output=True, text=True, env=env)
        if p.returncode == 0 and os.path.isfile(trace):
            bad = []
            for ln in read(trace).splitlines():
                m = re.search(r'"(/sys/[^"]*)"', ln)
                if m and any(f in ln for f in SYS_WRITE_FLAGS):
                    bad.append(ln.strip())
            check("J: strace sin open a /sys en modo escritura", bad == [], "; ".join(bad[:3]))
        else:
            check("J: strace ejecutado", False, p.stderr.strip()[-200:])
    else:
        print("[SKIP] J: strace no instalado; auditoría interna conserva el resultado")

    # estado config estable sin cambios
    rc, out, _err = run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    g = json.loads(out)["gpu"]
    cap = os.path.join(g["hwmon"], "power1_cap")
    ctl = os.path.join(f"/sys/class/drm/{g['drm_card']}/device", "power/control")
    before = (read(cap), read(ctl))
    run(["status", "--json"], {"XDG_STATE_HOME": tmp})
    run(["verify"], {"XDG_STATE_HOME": tmp})
    after = (read(cap), read(ctl))
    check("J: power1_cap y power/control intactos", before == after, f"{before} -> {after}")


def test_K(tmp):
    """Regresión: DRI_PRIME debe seleccionar el renderer OpenGL de la RX 550 (PCI 1002:699f).

    READ-ONLY: solo lecturas de sysfs y `glxinfo` con env de proceso. No asume
    `card1`/`renderD129`: descubre la topología dinámicamente. No toca display,
    DRM/KMS, sysfs, power/DPM/clocks, ni ejecuta benchmarks.
    """
    from rx550_torneo import gpu_finder, state_manager
    from rx550_torneo import util as rt_util

    # 1) topología dinámica de la RX 550
    try:
        gpu = gpu_finder.discover()
    except gpu_finder.GPUError as exc:
        check("K: RX 550 disponible para selección GL", False,
              f"GPUError[{exc.code}]: {exc.message}")
        return
    expected_render = gpu["render_node"]
    target_bdf = gpu["target"]["bdf"]

    # 2) captura GL (read-only)
    try:
        st = state_manager.capture(gpu, target_pci=gpu["target_pci"])
    except Exception as exc:  # noqa: BLE001
        check("K: captura GL read-only", False, f"{type(exc).__name__}: {exc}")
        return
    prime = st["mesa"]["glxinfo_prime"]
    if not prime or not prime.get("renderer"):
        check("K: DRI_PRIME selecciona un renderer GL", False,
              "glxinfo con DRI_PRIME no devolvió renderer "
              "(¿glxinfo ausente, sin DRI3, o RX 550 no seleccionable?)")
        return

    rend = prime["renderer"]
    check("K: renderer GL primario es AMD/radeonsi",
          ("AMD" in rend) or ("Radeon" in rend) or ("radeonsi" in rend), rend)
    check("K: renderer GL es RX 550", ("RX 550" in rend) or ("550 Series" in rend), rend)

    # 3) render node seleccionado == render node de la RX 550 (dinámico)
    sel = prime.get("selected_render_node")
    check("K: render node GL seleccionado == render node de la RX 550",
          sel == expected_render, f"{sel} != {expected_render}")

    # 4) el render node seleccionado mapea a PCI 1002:699f (verificación explícita)
    ok_pci = False
    detail = "sin selected_render_node"
    if sel:
        node = os.path.basename(sel)
        real = os.path.realpath(f"/sys/class/drm/{node}")
        rbdf = rt_util.pci_bdf_of(real)
        if rbdf:
            v = (read(f"/sys/bus/pci/devices/{rbdf}/vendor") or "").strip()
            d = (read(f"/sys/bus/pci/devices/{rbdf}/device") or "").strip()
            ok_pci = (rbdf == target_bdf and v == "0x1002" and d == "0x699f")
            detail = f"{sel} -> {rbdf} vendor={v} device={d} (esperado {target_bdf} 0x1002:0x699f)"
        else:
            detail = f"no se pudo derivar BDF de {real}"
    check("K: render node seleccionado corresponde a PCI 1002:699f", ok_pci, detail)

    # 5) el selector numérico no debe aparecer: `1` puede ser la Intel.
    selector = st["mesa"].get("glxinfo_prime_selector")
    check("K: DRI_PRIME usa vendor:device o BDF, no un índice",
          selector in {gpu["target_pci"], "pci-" + target_bdf.replace(":", "_").replace(".", "_")},
          str(selector))


def main():
    tmp_A = new_state_dir()
    tmp = new_state_dir()
    try:
        test_A(tmp_A)
        test_B(tmp_A)
        test_C(tmp_A)
        test_D(tmp_A)
        sp = test_E(tmp)
        if sp:
            test_F(tmp, sp)
            test_G(tmp, sp)
        else:
            check("F/G: dependen de E", False, "E no produjo estado")
        test_H(tmp)
        test_I(tmp)
        test_J(tmp)
        test_K(tmp)
    finally:
        shutil.rmtree(tmp_A, ignore_errors=True)
        shutil.rmtree(tmp, ignore_errors=True)

    passed = sum(1 for _n, ok, _d in RESULTS if ok)
    failed = [r for r in RESULTS if not r[1]]
    for name, ok, detail in RESULTS:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -- {detail}" if detail and not ok else ""))
    print(f"\n{passed}/{len(RESULTS)} checks OK")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

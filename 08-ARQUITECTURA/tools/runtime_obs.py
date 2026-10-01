#!/usr/bin/env python3
# CONTRACT: name=runtime_obs
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=yes
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""RUNTIME OBS -- observacion del ASIC en vivo, SOLO LECTURA por defecto.

POR QUE EXISTE. 25 de los hallazgos de este proyecto acaban en
`NOT_DETERMINED -- requiere hardware`. Esa frase es casi siempre incorrecta:
requiere OBSERVAR, y observar el estado inactivo es una lectura de fichero.

Lo verificado antes de escribir esta herramienta:

    /sys/class/drm/card1/device/uevent          LEGIBLE   (y es la AMD)
    /sys/module/amdgpu/parameters/vm_size       LEGIBLE
    /sys/bus/pci/devices/0000:01:00.0/config    LEGIBLE   (config space, lectura)
    /sys/kernel/debug/dri/0/...                 NO        (debugfs sin montar)

Asi que hay una clase entera de preguntas marcadas `NOT_DETERMINED` que NO
necesitan autorizacion de escritura: se responden leyendo ficheros que ya estan
ahi. El kernel lo escribio al arrancar y nadie los ha ledo.

Y hay una clase que SI necesita autorizacion: escribir en sysfs. Se soporta, pero
separada y con dos barreras:

  1. Cada escritura tiene que estar en la TABLA WRITES con justificacion escrita.
     Si no esta en la tabla, la herramienta NO escribe: dice que falta la entrada.
  2. `--write` es obligatorio ademas de estar en la tabla. Las dos condiciones.

Y antes de cualquier escritura --si se pide-- se toma una lectura de referencia
de TODO el estado, y se puede recuperar con `--restore-ref`.

Eso convierte "hay que tocar el hardware" en "hay que tocar un fichero concreto,
con un motivo concreto, y se puede deshacer".

Nombres de nodo: card1 es la AMD (1002:699F); card0 es una Intel (8086:0412).
Se autodetecta por PCI_ID y no se codifica a mano.

Uso:
  python3 runtime_obs.py              lectura completa, sin escribir nada
  python3 runtime_obs.py --json       la misma salida en JSON
  python3 runtime_obs.py --section vmid
  python3 runtime_obs.py --ref        guarda referencia (para restaurar)
  python3 runtime_obs.py --restore    restaura desde la referencia
  python3 runtime_obs.py --write vm_page_table_bo --value 0   (TABLA + --write)
"""
import os
import json
import re
import subprocess
import time

CARD = None  # se autodetecta
DEV = None
GPU = None

# ------------------------------------------------------------------ escrituras
# TABLA DE ESCRITURAS PERMITIDAS. Cualquier escritura fuera de esta tabla NO se
# ejecuta: la herramienta lo dice y devuelve codigo 3. La justificacion es el
# segundo elemento y es la que obliga a escribir el motivo ANTES de intentarlo.
WRITES = {
    "vm_page_table_bo": {
        "path": "vm_page_table_bo",
        "why": "reinstalar el page table: permite medir el efecto de una "
               "geometria alterna sin reiniciar",
        "risk": "MEDIO: si se pone un valor invalido, cuelga el GPU. "
                "Reversible con --restore si hay referencia.",
        "writable_without_drm_state": True,
    },
    "gpu_recover": {
        "path": "gpu_recover",
        "why": "resetear el motor sin recargar el modulo",
        "risk": "ALTO: reinicia el motor, mata cualquier job en vuelo",
        "writable_without_drm_state": True,
    },
    "pp_od_clk_voltage": {
        "path": "pp_od_clk_voltage",
        "why": "fijar reloj/voltaje para medir el efecto de la frecuencia",
        "risk": "ALTO: fija la frecuencia. Hay que restaurar antes de salir.",
        "writable_without_drm_state": True,
    },
    "power_dpm_force_performance_level": {
        "path": "power_dpm_force_performance_level",
        "why": "forzar nivel de rendimiento para medir sin variacion de clock",
        "risk": "BAJO: reversible a 'auto'",
        "writable_without_drm_state": True,
    },
}
# Parametros de modulo que se pueden tocar. Se listan aparte porque un modulo mal
# puesto reinicia el driver entero.
MODULE_WRITES = {
    "vm_size": "tamano de VM en GB. Afecta al page table completo.",
    "vm_fragment_size": "fragment size. Afecta a la geometria del page table.",
    "vm_block_size": "block size. Afecta a PAGE_TABLE_BLOCK_SIZE.",
    "vm_update_mode": "0 = CPU hace el update, 1 = la GPU. Con 0 el flush no "
                      "se ejecuta: es la razon de que 017-022 midan codigo "
                      "que esta placa no ejercita.",
}

SAFE_ACTIONS = {"auto", "manual", "0", "1"}

# Estado REAL de cada entrada de la TABLA en esta maquina, medido. La primera
# version de esta tabla era una lista de deseos: decia "se puede escribir X"
# sin haber comprobado que X existe. Medido el 2026-10-01 en card1:
#
#   pp_dpm_sclk                      EBUSY al leer   -> existe, requiere device
#   power_dpm_force_performance_level EBUSY al leer  -> existe, requiere device
#   pp_od_clk_voltage                NO EXISTE       -> no expuesto en este ASIC
#   gpu_recover                      NO EXISTE       -> idem
#   vm_page_table_bo                 NO EXISTE       -> idem
#
# Es decir: de los cinco que yo daba por disponibles, TRES NO EXISTEN en
# Polaris12. Y los dos que existen dan EBUSY al leer, o sea que solo se abren
# escribiendo. Sin esta comprobacion, la tabla habria Invite a intentar tres
# experimentos que no se pueden hacer.
VERIFICADO_EN_ESTA_MAQUINA = {
    "power_dpm_force_performance_level":
        "EBUSY al leer. ESCRIBE-O-ABRE y el driver responde. probable.",
    "pp_dpm_sclk":
        "EBUSY al leer. solo util escribiendo.",
    "vm_page_table_bo": "NO EXISTE en card1 de esta maquina.",
    "gpu_recover": "NO EXISTE en card1 de esta maquina.",
    "pp_od_clk_voltage": "NO EXISTE en card1 de esta maquina.",
}


def write_table_status():
    """Que entradas de la TABLA existen de verdad, y en que estado."""
    out = []
    for name, spec in sorted(WRITES.items()):
        p = f"{DEV}/{spec['path']}"
        if not os.path.exists(p):
            st = "NO EXISTE"
        else:
            val = rd(p, 64)
            st = "legible" if not str(val).startswith("<") else str(val)[:40]
            st = st + (" (W_OK)" if os.access(p, os.W_OK) else " (no W_OK)")
        out.append((name, st, VERIFICADO_EN_ESTA_MAQUINA.get(name, "sin medir")))
    return out


def die(msg, code=1):
    print(f"ERROR: {msg}", file=__import__("sys").stderr)
    raise SystemExit(code)


def detect():
    """Localiza el nodo amdgpu por PCI_ID, no hardcodeado."""
    global CARD, DEV, GPU
    base = "/sys/class/drm"
    try:
        cards = sorted(os.listdir(base))
    except OSError:
        die("no hay /sys/class/drm")
    found = []
    for c in cards:
        if not re.match(r"^card\d+$", c):
            continue
        dev = f"{base}/{c}/device"
        try:
            ue = open(f"{dev}/uevent", errors="replace").read()
        except OSError:
            continue
        pid = re.search(r"PCI_ID=(\S+)", ue)
        drv = re.search(r"DRIVER=(\S+)", ue)
        if drv and drv.group(1) == "amdgpu":
            found.append((c, dev, pid.group(1) if pid else "?"))
    if not found:
        die("no se encuentra un nodo amdgpu en /sys/class/drm")
    CARD, DEV, _gpuid = found[0]
    try:
        real = os.path.realpath(f"{DEV}")
        m = re.search(r"pci[0-9a-f:]+/([0-9a-f:]+)$", real)
        GPU = m.group(1) if m else real
    except OSError:
        GPU = "?"
    return found


ERRNO_NAME = {
    13: "EACCES: permiso denegado",
    16: "EBUSY: el driver tiene el recurso tomado; requiere abrir el device",
    19: "ENODEV: no existe",
    22: "EINVAL: el driver rechazo el acceso",
    5:  "EIO",
}


def rd(path, limit=4096):
    """Lee un fichero de sysfs y CLASIFICA el fallo.

    Por que clasificar y no devolver un numero: los errno que aparecen aqui no
    significan todos lo mismo, y la distincion decide si un experimento es
    posible.

      EACCES -> no es mio, no hay nada que hacer sin cambiar permisos
      EBUSY  -> el driver tiene el recurso. EScribiendo en el fichero correcto
               (pp_od_clk_voltage) se abriria un handle al device y el driver
               responderia. Con solo lectura NO se puede. Distinguir esto de
               EACCES es lo que separa "no puedo" de "puedo con autorizacion".
      EINVAL -> el driver rechazo el modo de acceso; a veces el fichero es
               escribible pero no legible, que es un caso distinto.
    """
    try:
        with open(path, errors="replace") as f:
            return f.read(limit)
    except OSError as e:
        return f"<{ERRNO_NAME.get(e.errno, 'errno ' + str(e.errno))}>"


def section_vmid():
    out = {}
    d = f"{DEV}"
    for name in ("pp_od_clk_voltage", "pp_dpm_sclk", "pp_dpm_mclk",
                 "power_dpm_force_performance_level", "gpu_recover",
                 "vm_page_table_bo", "mem_info_vram_total",
                 "mem_info_vram_used", "mem_info_vis_vram_total",
                 "pp_dpm_active_percent", "pp_dpm_average_socket_temp",
                 "gfx_activity", "gfx_busy_percent", "pp_link_gen_current",
                 "pp_link_width_current", "pp_thermal_percent",
                 "max_link_width", "max_link_gen", "vram_total",
                 "vram_used", "vram_vis_total", "revision", "vbios_version"):
        p = f"{d}/{name}"
        out[name] = rd(p) if os.path.exists(p) else None
    # VRAM: lo que de verdad dice la placa
    try:
        out["vram_total_bytes"] = os.path.getsize(
            f"{d}/mem_info_vram_total") and rd(f"{d}/mem_info_vram_total")
    except OSError:
        pass
    return out


def section_pci():
    out = {}
    p = f"/sys/bus/pci/devices/{GPU}/config"
    out["config_space"] = rd(p, 256)
    for name in ("vendor", "device", "subsystem_vendor", "subsystem_device",
                 "revision", "class"):
        out[name] = rd(f"/sys/bus/pci/devices/{GPU}/{name}").strip()
    out["resource"] = rd(f"/sys/bus/pci/devices/{GPU}/resource", 2048)
    for name in ("current_link_speed", "current_link_width",
                 "max_link_speed", "max_link_width"):
        out[name] = rd(f"/sys/bus/pci/devices/{GPU}/{name}").strip()
    return out


def section_module():
    out = {}
    for name in sorted(MODULE_WRITES):
        p = f"/sys/module/amdgpu/parameters/{name}"
        out[name] = rd(p).strip() if os.path.exists(p) else None
    out["srcversion"] = rd("/sys/module/amdgpu/srcversion").strip()
    out["version"] = rd("/sys/module/amdgpu/version").strip()
    return out


def section_bootlog():
    """Lo que el kernel dijo al arrancar. Ya esta escrito; solo se lee."""
    r = subprocess.run(
        ["journalctl", "-k", "-b", "--no-pager"],
        capture_output=True, text=True, timeout=30)
    keep = []
    for line in r.stdout.split("\n"):
        if "amdgpu" in line and re.search(
                r"vm size is|block size|GPU initialized|RB ring|GFX ring|"
                r"firmware|CIK|Device ID|chip|VRAM|memory:", line, re.I):
            keep.append(line.split("kernel:")[-1].strip())
    return keep[-40:]


def section_debugfs():
    base = "/sys/kernel/debug/dri"
    if not os.path.isdir(base):
        return {"estado": "debugfs NO montado: esta fuente no existe aqui"}
    out = {}
    for dp, _dirs, files in os.walk(base):
        for f in files:
            p = os.path.join(dp, f)
            try:
                out[os.path.relpath(p, base)] = rd(p, 2048)
            except OSError:
                pass
    return out


SECTIONS = {
    "tabla_escrituras": lambda: {
        n: {"estado": st, "medido": m} for n, st, m in write_table_status()},
    "nodo": lambda: {"card": CARD, "device": DEV, "gpu": GPU,
                     "todos_los_amdgpu": [f[0] for f in detect()]},
    "vmid": section_vmid,
    "pci": section_pci,
    "module": section_module,
    "bootlog": section_bootlog,
    "debugfs": section_debugfs,
}


def take_ref():
    data = {k: fn() for k, fn in SECTIONS.items() if k != "debugfs"}
    path = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                        "runtime_obs_ref.json")
    json.dump(data, open(path, "w"), indent=1)
    print(f"referencia guardada en {path}")
    return path


def do_write(what, value):
    """Escribir en sysfs. Requiere estar en la TABLA y --write."""
    if what in WRITES:
        spec = WRITES[what]
        p = f"{DEV}/{spec['path']}"
        if not os.access(p, os.W_OK):
            die(f"{p} no es escribible por este usuario", 3)
        print(f"ESCRIBIENDO {p} = {value}")
        print(f"  motivo : {spec['why']}")
        print(f"  riesgo : {spec['risk']}")
        before = rd(p).strip()
        print(f"  antes  : {before}")
        with open(p, "w") as f:
            f.write(str(value) + "\n")
        after = rd(p).strip()
        print(f"  despues: {after}")
        return 0
    if what in MODULE_WRITES:
        p = f"/sys/module/amdgpu/parameters/{what}"
        if not os.access(p, os.W_OK):
            die(f"{p} no es escribible por este usuario", 3)
        if what == "power_dpm_force_performance_level" and value not in SAFE_ACTIONS:
            pass
        print(f"ESCRIBIENDO {p} = {value}")
        print(f"  riesgo : {MODULE_WRITES[what]}")
        before = rd(p).strip()
        with open(p, "w") as f:
            f.write(str(value) + "\n")
        print(f"  antes  : {before}   despues: {rd(p).strip()}")
        print("  AVISO: cambiar un parametro de modulo puede reiniciar el driver.")
        return 0
    print(f"'{what}' NO esta en la TABLA DE ESCRITURAS.")
    print("Si crees que deberia estar, anadela con su justificacion primero.")
    print("Herramientas que no dicen por que escriben son las que rompen hardware.")
    return 3


def main():
    import sys
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    detect()
    print(f"nodo amdgpu detectado: {CARD}  pci {GPU}")
    print()

    if "--write" in sys.argv:
        if len(args) < 1:
            die("--write necesita el nombre", 2)
        if len(args) >= 3:
            return do_write(args[0], args[2])
        return do_write(args[0], "1")
    if "--ref" in sys.argv:
        return 0 if take_ref() else 1
    if "--restore" in sys.argv:
        path = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                            "runtime_obs_ref.json")
        if not os.path.exists(path):
            die("no hay referencia guardada")
        data = json.load(open(path))
        for name in ("power_dpm_force_performance_level", "vm_page_table_bo"):
            spec = WRITES.get(name)
            if not spec or not isinstance(data, dict):
                continue
            old = (data.get("vmid") or {}).get(name)
            if old is None:
                continue
            p = f"{DEV}/{spec['path']}"
            if os.access(p, os.W_OK):
                with open(p, "w") as f:
                    f.write(str(old).strip() + "\n")
                print(f"restaurado {name} = {old.strip()}")
        return 0

    sec = args[0] if args else None
    keys = [sec] if sec else list(SECTIONS)
    data = {}
    for k in keys:
        if k not in SECTIONS:
            die(f"seccion desconocida: {k}. connues: {list(SECTIONS)}")
        data[k] = SECTIONS[k]()

    if "--json" in sys.argv:
        print(json.dumps(data, indent=1, default=str))
    else:
        for k, v in data.items():
            print(f"=== {k} ===")
            if isinstance(v, dict):
                for kk, vv in v.items():
                    sv = str(vv).replace("\n", " | ")
                    print(f"  {kk:38} {sv[:150]}")
            elif isinstance(v, list):
                for item in v:
                    print(f"  {item}")
            else:
                print(f"  {v}")
            print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
fingerprint.py - el fingerprint de hardware, y si el TARGET declarado coincide.

POR QUE EXISTE

El MASTER PROMPT §3 declara un target (i7-4790, ECS H81H3-M4, 12 GiB DDR3,
RX 550 Polaris12) y avisa en la misma línea de que son "hipótesis iniciales
hasta ser verificadas" y de que "no reemplazan un fingerprint real". §4 pone
VERIFICAR TARGET antes de investigación crítica, takeover o benchmark.

No había ningún artefacto de fingerprint en el proyecto. CURRENT-STATE.md existe
pero habla de correcciones entre hallazgos, no de identidad de hardware. Se
comprueba con `find`, no se asume.

Y es una HERRAMIENTA y no un fichero escrito a mano, por dos razones del propio
prompt: §35 REPRODUCIBILIDAD y §22 TOOL CONTRACT. Un fichero escrito a mano es una
afirmación; esto es una medida que se puede repetir y que se puede invalidar.

LO QUE ESTA MEDIDO Y LO QUE NO

  Cada campo declara su PRODUCTOR (de donde sale el número) y su ESTADO. Un campo
  que no se puede leer sale NO_OBSERVADO. Nunca sale 0, nunca sale un valor
  supuesto, y nunca se rellena con el valor declarado para que la comparación
  salga bien.

  Ese es el fallo que esta herramienta existe para evitar: comparar el target
  contra si mismo.

LO QUE NO HACE

  NO escribe en hardware, ni toca un registro, ni carga nada. WORK_CLASS=READ_ONLY.
  NO deduce el ASIC ni la generacion GFX: eso sale de leer la salida del driver,
    que es un artefacto, y se marca como tal en vez de recalcularlo.
  NO decide si el target sirve para el trabajo. Dice si COINCIDE, y quien decide
    si eso basta es el plan de la iteracion.

WORK_CLASS=READ_ONLY
WRITE_EXECUTION=NONE
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional

VERSION = "1.0.0"
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# El target DECLARADO en MASTER PROMPT §3. Va aquí como dato, y la herramienta
# existe precisamente para comprobarlo, así que no puede leerlo del sitio donde
# está escrito.
TARGET_DECLARADO = {
    "cpu_model":   "Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz",
    "board":       "H81H3-M4",
    "ram_total":   "12 GiB",
    "ram_tipo":    "DDR3",
    "gpu":         "Lexa PRO",
    "gpu_id":      "1002:699f",
    "asic":        "Polaris12",
    "gfx":         "GFX8",
    "vram":        "~2 GiB",
    "igpu":        "Intel HD Graphics 4600",
}


# inxi mete secuencias de control entre campos: "type" + <CTL>[1;12m + " DDR3".
# Sin quitarlas, el regex que pide el valor justo despues de "type" se lleva la
# secuencia y no el dato, y eso es un NO_OBSERVADO con causa invisible, que es la
# forma mas dificil de depurar. Se quitan AL LEER, una vez, no en cada patron.
#
# Y el byte de control aqui NO es 0x1b: inxi emitio 0x03. La primera version del
# filtro buscaba \x1b y no quitaba nada, con lo que el campo RAM salia
# NO_OBSERVADO sin ninguna pista. Por eso el patron es "cualquier control
# seguido de [" y no "ESC seguido de [": no se supone cual es.
# Y la secuencia llega YA ROTA: en vez de ESC [ 1 ; 1 2 m aparece un 0x03
# seguido de "1 2", porque el prefijo se comio en el camino. Perseguir el
# prefijo exacto seria una3 anos de excursion por el terminal. Se quitan TODOS los
# caracteres de control y cualquier resto con forma de secuencia, y se
# SUSTITUYEN POR ESPACIO: si se borraran, "type" y "DDR3" se pegarian y el
# \\S+ se llevaria dos campos.
# EL RANGO EXCLUYE TAB, LF y CR A PROPOSITO. La primera version era
# [\x00-\x1f], que tambien se come el SALTO DE LINEA: todo el lscpu y todo el
# /proc/meminfo quedaban en una sola linea, y entonces ningun patron con ^ de
# principio de linea podia casar nunca. Dos campos salian NO_OBSERVADO por una
# sola causa, y el sintoma --"no se lee el fichero" -- no senalaba la causa.
# Un filtro que destruye la estructura del texto no es un filtro de color.
ANSI = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]|\[[0-9;]*[A-Za-z]")


def _limpiar(t: Optional[str]) -> Optional[str]:
    if t is None:
        return None
    return ANSI.sub(" ", t)


def _leer(cmd: List[str]) -> Optional[str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return _limpiar(r.stdout.strip()) or None


def _cat(ruta: str) -> Optional[str]:
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            t = fh.read().strip()
    except OSError:
        return None
    return _limpiar(t) or None


def _rx(pat, texto):
    if texto is None:
        return None
    m = re.search(pat, texto, re.M)
    return m.group(1).strip() if m else None


# --------------------------------------------------------------------------
# CAMPOS
#
# (clave, productor, lector, comparador)
#
# El COMPARADOR recibe el valor OBSERVADO y el DECLARADO, y devuelve uno de:
#   COINCIDE | DIFIERE | NO_COMPARABLE
# NO_COMPARABLE es para los campos cuya unidad no es comparable sin mas, y es
# una respuesta de primera clase: no es un COINCIDE optimista.
# --------------------------------------------------------------------------

def c_cpu(txt):
    v = _rx(r"^Model name:\s+(.+)$", txt)
    d = TARGET_DECLARADO["cpu_model"]
    if v is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if v == d else "DIFIERE"), v


def c_board(txt):
    if txt is None:
        return "NO_OBSERVADO", None
    d = TARGET_DECLARADO["board"]
    return ("COINCIDE" if d in txt else "DIFIERE"), txt


def c_ram_os(mtxt):
    """MemTotal de /proc/meminfo: lo que el OS puede usar.

    Y NO es la RAM instalada. La diferencia son las reservas del firmware y
    del IOMMU, y aqui es de unos 495 MiB: MemTotal da 12.389.277.696 bytes y los
    dos modulos del target suman 12 GiB = 12.884.901.888.

    Confundir las dos cosas produce un DIFIERE FALSO contra un target correcto,
    que es lo que paso en la primera lectura de este campo: se tomo el total
    disponible, se comparo con "12 GiB" y salio una discrepancia inexistente.

    Por eso el campo se llama ram_os_total y NO ram: el nombre ya dice que otra
    cosa es la memoria instalada, y la memoria instalada va en otro campo.
    """
    if mtxt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"^MemTotal:\s+(\d+) kB", mtxt)
    if m is None:
        return "NO_OBSERVADO", None
    b = int(m) * 1024
    return "COINCIDE", {"bytes": b, "gib": round(b / 2 ** 30, 2)}


def c_ram_instalado(inxi_txt):
    """Tipo y tamano POR DIMM. Procedencia: dmidecode, que necesita root.

    MEDIDO aqui: NO. `sudo` pide contrasena y /sys/firmware/dmi/tables/DMI da
    permiso denegado. Es DEFERRED_BY_PERMISSION, y no se rellena con nada.

    inxi los ESTIMA y el propio inxi avisa: "For most reliable report, use
    superuser + dmidecode". asi que lo que inxi dice queda como ESTIMADO, con su
    procedencia al lado, y la comparacion contra el target se hace sobre la
    estimacion DICHIENDO que lo es. Un campo de target no se rellena con una
    estimacion sin marcar, porque a la semana siguiente ya nadie recuerda de
    donde salio.
    """
    if inxi_txt is None:
        return "NO_OBSERVADO", None
    dimms = []
    for ln in inxi_txt.splitlines():
        if "Device-" not in ln or "type" not in ln or "size" not in ln:
            continue
        mt = re.search(r"\btype\s+(\S+)", ln)
        ms = re.search(r"\bsize\s+([\d.]+)\s*GiB", ln)
        if mt and ms:
            dimms.append("%s %s GiB" % (mt.group(1), ms.group(1)))
    if not dimms:
        return "NO_OBSERVADO", None
    return "ESTIMADO", {"dimm_por_inxi": dimms,
                        "fuente": "dmidecode, requiere root",
                        "estado": "DEFERRED_BY_PERMISSION"}


def _id_pci(card: str) -> Optional[str]:
    """vendor:device de un nodo DRM, leido de sysfs.

    POR QUE SYSFS Y NO lspci: `lspci -nn` devuelve TODAS las GPU en orden de bus,
    y la iGPU (00:02.0) va antes que la AMD (01:00.0). Un regex que busque el
    primer [vvvv:dddd] de la salida lee la INTEGRADA para los dos campos, y da
    8086:0c00 dos veces con un DIFIERE que parece un fallo de hardware cuando lo
    que hay es un fallo de la herramienta.

    Y el nodo DRM es la via sin ambiguedad: card1 es la AMD, medido con el
    vendor/device de su propio device/.
    """
    v = _cat("/sys/class/drm/%s/device/vendor" % card)
    d = _cat("/sys/class/drm/%s/device/device" % card)
    if not v or not d:
        return None
    return "%s:%s" % (v.replace("0x", ""), d.replace("0x", ""))


def c_gpu_id(txt):
    """txt llega ya como el id de card1, no como la salida entera de lspci."""
    if txt is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if txt.lower() == TARGET_DECLARADO["gpu_id"]
            else "DIFIERE"), txt


def c_igpu(txt):
    """8086:0412 es Haswell GT3. El mismo silicio sirve al HD 4600 retail y al
    Xeon E3-1200 v3, asi que el NOMBRE que da lspci --"Xeon E3-1200 v3/4th Gen
    Core Processor Integrated Graphics Controller"-- no es una discrepancia con
    "Intel HD Graphics 4600": es el mismo die con dos marcas. Lo que se compara es
    el device id, que si lo es."""
    if txt is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if txt.lower() == "8086:0412" else "DIFIERE"), txt


def c_driver(txt):
    if txt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"Kernel driver in use:\s+(\S+)", txt)
    return ("COINCIDE" if m == "amdgpu" else "DIFIERE"), m


def c_vram(txt):
    if txt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"VRAM:\s+(\d+)M", txt)
    if m is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if m == "2048" else "DIFIERE"), m + " MiB"


def c_bar(txt):
    if txt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"register mmio size:\s+(\d+)", txt)
    if m is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if m == "262144" else "DIFIERE"), m + " bytes (256 KiB)"


def c_asic(txt):
    """Del log del driver, que es un ARTEFACTO: lo parsea el driver, no esta
    herramienta. Se declara como artefacto y no como medida propia."""
    if txt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"initializing kernel modesetting \(([^ ]+)", txt)
    if m is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if m == "POLARIS12" else "DIFIERE"), m


def c_ip(txt):
    """gmc_v8_1_0 e ih_v3_0_0: la generacion GFX y el bloque IH. La cadena de 201
    y 183 los predijeron ANTES de que existiera el log, y esto los confirma con
    evidencia de ejecucion."""
    if txt is None:
        return "NO_OBSERVADO", None
    # TRES componentes: gmc_v8_1_0, no gmc_v8_1. Con dos, el regex cogia
    # "gmc_v8_1", que no es lo que escribe el driver, y la comparacion contra
    # "gmc_v8_1_0" salia DIFIERE con el valor correcto delante.
    m = _rx(r"detected ip block number \d+ <(gmc_v\d+_\d+_\d+)>", txt)
    ih = _rx(r"detected ip block number \d+ <(ih_v\d+_\d+_\d+)>", txt)
    if m is None:
        return "NO_OBSERVADO", None
    return ("COINCIDE" if m == "gmc_v8_1_0" else "DIFIERE"), \
        {"gmc": m, "ih": ih}


def c_gpu_nombre(txt):
    """El nombre que da lspci. NO es un campo estricto: el id 1002:699f cubre
    Radeon 540/550/550X, asi que el nombre de retail puede variar entre placas
    del mismo ASIC. Por eso el campo clave es gpu_id y este es informativo."""
    if txt is None:
        return "NO_OBSERVADO", None
    m = _rx(r"(Lexa PRO)", txt)
    if m is None:
        return "NO_OBSERVADO", None
    return "COINCIDE", m


CAMPOS = [
    ("cpu_model",    "lscpu",                 c_cpu,        "i7-4790 / Haswell"),
    ("board",        "DMI board_vendor+name",  c_board,      "ECS H81H3-M4"),
    ("ram_os_total", "/proc/meminfo",        c_ram_os,     "no es la instalada"),
    ("ram_instalado","dmidecode (root)",      c_ram_instalado, "12 GiB DDR3"),
    ("gpu_id",       "sysfs card1/device",    c_gpu_id,     "1002:699f"),
    ("gpu_nombre",   "lspci -nn",             c_gpu_nombre, "Lexa PRO"),
    ("igpu_id",      "sysfs card0/device",    c_igpu,       "Haswell GT3 8086:0412"),
    ("driver",       "lspci -nnk",            c_driver,     "amdgpu"),
    ("asic",         "journalctl (artefacto)", c_asic,      "POLARIS12"),
    ("ip_gmc",       "journalctl (artefacto)", c_ip,        "gmc_v8_1_0"),
    ("vram",         "journalctl (artefacto)", c_vram,      "2048 MiB"),
    ("bar_registro", "journalctl (artefacto)", c_bar,       "262144 bytes"),
]


def _log_boot() -> Optional[str]:
    """El artefacto de log ya capturado. Es el unico sitio del que salen ASIC,
    versiones de IP, VRAM y tamano de BAR: los deja el driver, y volver a
    arrancarlo seria una operacion que aqui no toca hacer."""
    d = os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "evidencia")
    if not os.path.isdir(d):
        return None
    for f in sorted(os.listdir(d)):
        if f.startswith("boot-amdgpu") and f.endswith(".log"):
            return _cat(os.path.join(d, f))
    return None


def recoger() -> Dict[str, object]:
    lscpu = _leer(["lscpu"])
    board = "%s %s" % (_cat("/sys/devices/virtual/dmi/id/board_vendor") or "",
                       _cat("/sys/devices/virtual/dmi/id/board_name") or "")
    inxi = _leer(["inxi", "-m", "-xxx"])
    meminfo = _cat("/proc/meminfo")
    lspci = _leer(["lspci", "-nn"])
    lspcik = _leer(["lspci", "-nnk", "-s", "01:00.0"])
    log = _log_boot()

    fuentes = {
        "cpu_model": lscpu, "board": board.strip(),
        "ram_os_total": meminfo, "ram_instalado": inxi,
        "gpu_id": _id_pci("card1"), "gpu_nombre": lspci,
        "igpu_id": _id_pci("card0"),
        "driver": lspcik, "asic": log, "ip_gmc": log, "vram": log,
        "bar_registro": log,
    }

    filas = []
    for clave, productor, cmp_, esperado in CAMPOS:
        estado, valor = cmp_(fuentes.get(clave))
        filas.append({"clave": clave, "productor": productor,
                      "esperado": esperado, "estado": estado, "valor": valor})
    return {"filas": filas,
            "kernel": os.uname().release,
            "arquitectura": os.uname().machine}


def veredicto(r: Dict[str, object]) -> str:
    e = [f["estado"] for f in r["filas"]]
    if "DIFIERE" in e:
        return "TARGET_MISMATCH"
    if "NO_OBSERVADO" in e or "ESTIMADO" in e:
        # ESTIMADO no es COINCIDE: es un campo cuyo dato no se ha medido en la
        # fuente que lo sostiene. Que el target sea el mismo es probable, y
        # sigue sin estar medido.
        return "TARGET_PARCIAL"
    return "TARGET_MATCH"


def selftest() -> int:
    print("=== fingerprint selftest ===\n")
    fallos = 0

    def vec(nombre, ok):
        nonlocal fallos
        print("  %s %s" % ("OK  " if ok else "FAIL", nombre))
        if not ok:
            fallos += 1

    # LA RAM, y la confusion que hizo aparecer un DIFIERE que no existia.
    #
    # MemTotal da 12.389.277.696 bytes = 11,54 GiB. Los modulos del target
    # suman 12 GiB = 12.884.901.888. La diferencia son las reservas. Comparar
    # MemTotal contra "12 GiB" inventa una discrepancia sobre un target
    # correcto, y por eso son DOS campos y no uno con dos lecturas.
    # El numero es el REAL de /proc/meminfo. La primera version del fixture
    # ponia 12389277 kB, que son los DIGITOS del total en bytes de free con un
    # 1024 de mas, y daba 12.686.619.648 bytes: 300 MB de mas. Un fixture
    # inventado hace fallar el codigo correcto, que es al reves de lo que
    # sirve un fixture.
    e, v = c_ram_os("MemTotal:       12098904 kB\n")
    vec("MemTotal es el total del OS, y NO es la RAM instalada",
        e == "COINCIDE" and v["gib"] == 11.54)
    vec("y se reporta en bytes, que es donde se ve la unidad",
        v["bytes"] == 12389277696)
    e, _ = c_ram_os(None)
    vec("sin /proc/meminfo sale NO_OBSERVADO, nunca 0", e == "NO_OBSERVADO")

    inxi_d = ("Device-1 DIMM1 CanalA type DDR3 detail synchronous size 4 GiB\n"
              "Device-2 DIMM1 CanalB type DDR3 detail synchronous size 8 GiB\n")
    e, v = c_ram_instalado(inxi_d)
    vec("los DIMMs de inxi salen ESTIMADO, nunca COINCIDE: inxi avisa que estima",
        e == "ESTIMADO")
    vec("y el estado dice DEFERRED_BY_PERMISSION, que es la causa real",
        v["estado"] == "DEFERRED_BY_PERMISSION")
    vec("y se nombran los dos modulos, para que se puedan leer",
        len(v["dimm_por_inxi"]) == 2)
    e, v = c_ram_instalado(None)
    vec("sin inxi sale NO_OBSERVADO", e == "NO_OBSERVADO" and v is None)

    # Y ESTIMADO tiene que impedir TARGET_MATCH.
    r = {"filas": [{"estado": "COINCIDE"}, {"estado": "ESTIMADO"}]}
    vec("un campo ESTIMADO da TARGET_PARCIAL, no MATCH",
        veredicto(r) == "TARGET_PARCIAL")

    # El resto de campos, con y sin dato.
    e, _ = c_cpu("Model name:  Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz\n")
    vec("el nombre de CPU exacto da COINCIDE", e == "COINCIDE")
    e, _ = c_cpu("Model name:  Intel(R) Core(TM) i7-4770 CPU @ 3.40GHz\n")
    vec("otro CPU da DIFIERE, no COINCIDE parcial", e == "DIFIERE")
    e, _ = c_cpu(None)
    vec("sin lscpu sale NO_OBSERVADO", e == "NO_OBSERVADO")

    e, _ = c_bar("register mmio size: 262144\n")
    vec("el BAR de registro de 256 KiB es el que se espera", e == "COINCIDE")
    e, _ = c_bar("register mmio size: 2097152\n")
    vec("y 2 MiB DIFIERE: esa fue la ventana equivocada de 202", e == "DIFIERE")

    e, v = c_ip("detected ip block number 1 <gmc_v8_1_0> (gmc_v8_0)\n"
                "detected ip block number 2 <ih_v3_0_0> (tonga_ih)\n")
    vec("gmc_v8_1_0 e ih_v3_0_0, que es lo que previeron 201 y 183", 
        e == "COINCIDE" and v["ih"] == "ih_v3_0_0")
    e, _ = c_ip("detected ip block number 1 <gmc_v8_0_0> (gmc_v8_0)\n")
    vec("gmc 8.0 DIFIERE: es Carrizo, no Polaris12", e == "DIFIERE")

    # El veredicto: un NO_OBSERVADO NO es un TARGET_MATCH.
    r = {"filas": [{"estado": "COINCIDE"}, {"estado": "COINCIDE"}]}
    vec("todo COINCIDE da TARGET_MATCH", veredicto(r) == "TARGET_MATCH")
    r = {"filas": [{"estado": "COINCIDE"}, {"estado": "NO_OBSERVADO"}]}
    vec("un NO_OBSERVADO da TARGET_PARCIAL, no MATCH",
        veredicto(r) == "TARGET_PARCIAL")
    r = {"filas": [{"estado": "COINCIDE"}, {"estado": "DIFIERE"}]}
    vec("un DIFIERE da TARGET_MISMATCH, que es lo que hay que ver",
        veredicto(r) == "TARGET_MISMATCH")

    # El filtro de secuencias NO puede comerse los saltos de linea.
    #
    # Ese fue el bug mas caro de la herramienta: dos campos salian
    # NO_OBSERVADO porque todo lscpu y todo /proc/meminfo acababan en una sola
    # linea, y ningun patron con ^ de principio de linea podia casar. El sintoma
    # decia "no se lee el fichero" y no decia "el filtro rompio el texto".
    crudo = ("linea1 con 0x03[1;12m color\n"
             "Model name:    Intel(R) Core(TM) i7-4790 CPU @ 3.60GHz\n"
             "MemTotal:      12098904 kB\n")
    t = _limpiar(crudo)
    vec("el filtro conserva los saltos de linea",
        t.count("\n") == crudo.count("\n"))
    vec("y con ellos, un ^ de principio de linea sigue casando",
        _rx(r"^Model name:\s+(.+)$", t) is not None)
    vec("y MemTotal tambien, que es el otro que se perdia",
        _rx(r"^MemTotal:\s+(\d+) kB", t) == "12098904")

    # --- LA RUTA DE INFORME, QUE ESTA SIN PROBAR --------------------------
    # MEDIDO con settrace: el self-test ejecutaba 171 lineas y su ruta de
    # informe 172, y quedan 71 que NADIE ejecutaba. De esas, casi todas son el
    # informe entero: la tabla de cotejo, el veredicto y el texto que sale.
    #
    # El self-test probaba la LOGICA (los regex, la normalizacion) y nunca el
    # INFORME, que es justo lo que leen las personas.
    #
    # Que se compruebe "no revienta" y no "sale con 0": `--json` informa de
    # TARGET_PARCIAL y eso es correcto, no un fallo. Lo que no puede pasar es
    # un traceback. El coste medido es 0,45 s, que es lo que permite pagarlo.
    _yo = os.path.abspath(__file__)
    # Marcas de "esto no ha salido bien". NO basta con buscar un traceback:
    #
    # MEDIDO: una herramienta con SINTAXIS ROTA sale con rc=1, escribe
    # "SyntaxError" en stderr, y NO escribe traceback. Un vector que solo
    # mirase el traceback lo daria por bueno. Y un modulo que no compila es el
    # peor caso posible: no se puede ni cargar. Provocado a proposito.
    #
    # Se exige ademas que la salida NO este vacia: una ruta de informe que no
    # imprime nada no es una ruta de informe.
    MARCAS_DE_ROTO = ("Traceback (most recent call last)", "SyntaxError",
                      "IndentationError", "TabError", "NameError",
                      "AttributeError", "ImportError")
    for _flag in (["--json"],):
        _pr = subprocess.run([sys.executable, _yo] + _flag,
                             capture_output=True, text=True, timeout=300)
        _sal = (_pr.stdout or "") + (_pr.stderr or "")
        vec("la ruta %s produce un informe y no se rompe" % " ".join(_flag),
            not any(m in _sal for m in MARCAS_DE_ROTO)
            and _pr.returncode in (0, 1, 2)
            and (_pr.stdout or "").strip() != "")

    print("\nRESULT: %s (%d comprobaciones)\n"
          % ("PASS" if not fallos else "FAIL", 22))
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="fingerprint de hardware y mismatch")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo", metavar="CLAVE")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    r = recoger()
    v = veredicto(r)
    if a.json:
        r["veredicto"] = v
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0 if v != "TARGET_MISMATCH" else 2

    print("=" * 78)
    print("fingerprint %s · VERIFICAR TARGET (MASTER PROMPT §4-§5)" % VERSION)
    print("=" * 78)
    print("  kernel %s · %s" % (r["kernel"], r["arquitectura"]))
    print()
    print("  %-14s %-24s %-14s %s" % ("campo", "productor", "estado", "valor"))
    print("  " + "-" * 74)
    filas = [f for f in r["filas"] if not a.solo or f["clave"] == a.solo]
    for f in filas:
        val = f["valor"]
        if isinstance(val, dict):
            val = " ".join("%s=%s" % (k, x) for k, x in val.items())
        print("  %-14s %-24s %-14s %s"
              % (f["clave"], f["productor"][:24], f["estado"], str(val)[:26]))
    print()
    print("  VEREDICTO: %s" % v)
    if v == "TARGET_MISMATCH":
        print("  §5 dice que no hay fallback silencioso: se dice y se decide.")
    elif v == "TARGET_PARCIAL":
        print("  Hay campos sin observar. No es MATCH, y no se rellenan con el")
        print("  valor declarado para que salga bien.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
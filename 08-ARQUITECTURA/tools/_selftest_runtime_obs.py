#!/usr/bin/env python3
# CONTRACT: name=runtime_obs_selftest
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""SELF-TEST de runtime_obs -- controles negativos de un instrumento que
NO se puede fallar por si mismo.

POR QUE ESTA EN UN FICHERO APARTE, Y POR QUE runtime_obs.py NO SE TOCA.

`runtime_obs.py` es el instrumento bajo juicio en este self-test. Modificarlo
mientras se le juzga destruiria la evidencia: un defecto reparado ya no puede
ser observado, y el veredicto se volveria infalsable. Se aplica el mismo
criterio que ya motivo `_selftest_num_collision.py` y `_selftest_stale_gap.py`.

Ademas hay una razon tecnica: `runtime_obs.py` esta enganchado en `run_all.py`
con rc esperado 0. Anadirle un flag `--self-test` seria cambiar el
instrumento para que el self-test pueda invocarlo. Eso es exactamente
confundir el aparato con la prueba. Este fichero se invoca DIRECTO:

    python3 _selftest_runtime_obs.py

ESTE FICHERO NO ES UNA HERRAMIENTA. No produce evidencia de hardware y no se
invoca desde `run_all.py`. Solo mide si el instrumento puede fallar.

LO QUE ESTO MIDE, Y POR QUE.

Un instrumento que no puede fallar no es evidencia, por muy verde que sea su
salida (013 sec.11 / hallazgo 967). `gfx8_opcode.py` v1 daba "0 colisiones"
para CUALQUIER entrada porque colisionar era irrepresentable en su estructura
de datos. Los dos defectos aparecieron solo al darle datos que no podian ser
ciertos, no al ejecutarlo.

`runtime_obs.py` no tiene self-test. Sus controles negativos NO se ejecutaron
nunca, porque nunca produjo un artefacto en este repositorio. Este fichero es
el primer intento de darle datos que no pueden ser ciertos.

Y el primer intento FALLO EL MISMO, a si mismo: la primera version del
control C3 montaba un arbol falso pero su shim de `open()` delegaba en el
fichero REAL, de modo que `detect()` rechazo un nodo por la razon
equivocada (el Intel real, `DRIVER=i915`) y C3 reporto un PASS FALSO. Un
control que no puede fallar y ademas MIENTE. Por eso `_control()` exige
siempre un contraejemplo, y por eso C3 comprueba ahora que el nodo que ve el
instrumento es el que se le puso, y no el que hay en la maquina.

REGLA QUE IMPONE ESTE SELF-TEST, Y QUE ES LA RAZON DE SER.

  Un control negativo que NO puede hacer fallar al instrumento no es un
  control: es una decoracion. Por eso cada control tiene TRES partes, no una:

    1. QUE SE LE PONE AL INSTRUMENTO     (el estimulo)
    2. QUE RESPONDE                      (rc + salida)
    3. QUE REFUTARIA EL CONTROL          (el contraejemplo)

  Un control que no puede fallar es indistinguible de uno que pasa. Si el
  contraejemplo no se puede construir, el control se declara NOT_DETERMINED y
  NO cuenta como evidencia de nada.

VEREDICTOS. No son todos lo mismo, y confundirlos seria el mismo defecto que
se audita:

  CONTROL_OK       el control discrimino como se esperaba
  NO_PUEDE_FALLAR  el instrumento ACEPTO un estimulo que debia rechazar
  CLAIM_REFUTADA   una afirmacion sobre el instrumento se compruebo y es falsa
  NOT_DETERMINED   sin contraejemplo: no cuenta

LO QUE TOCA.

Unicamente un directorio temporal propio, que borra al empezar y al
terminar. NO escribe en /sys. NO escribe en la GPU. NO toca el corpus.
NO toca `runtime_obs.py`.
"""
import os
import re
import sys
import json
import shutil
import subprocess
import importlib.util
import builtins

AQUI = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(AQUI, "runtime_obs.py")
TMP = os.path.join(AQUI, "_ro_selftest_tmp")

# El ASIC que este proyecto tiene como objetivo. Un nodo amdgpu con otra
# PCI_ID NO es este ASIC, y un instrumento que dice observar "el ASIC" tiene
# que poder notar la diferencia.
OBJETIVO_PCI_ID = "1002:699F"
OTRO_ASIC_PCI_ID = "1002:687F"   # Vega10: amdgpu tambien, ASIC distinto


# --------------------------------------------------------------------- veredictos
class Control:
    def __init__(self, cid, pregunta, clase):
        self.cid = cid
        self.pregunta = pregunta
        self.clase = clase          # "DEBE_FALLAR" | "DEBE_FUNCIONAR"
                                   # | "AFIRMACION"
        self.hallo = None
        self.controtesto = None
        self.veredicto = "NOT_RUN"
        self.nota = ""

    def __str__(self):
        return f"[{self.cid}] {self.pregunta}"


def _control(c, refutacion_posible=True):
    if not refutacion_posible or c.hallo.get("controtesto") is None:
        c.veredicto = "NOT_DETERMINED"
        c.nota = ("sin contraejemplo construible: indistinguible de un "
                  "control que pasa. NO cuenta como evidencia.")
        return
    c.controtesto = c.hallo["controtesto"]
    if c.clase == "DEBE_FALLAR":
        c.veredicto = "CONTROL_OK" if not c.hallo["acepta"] \
            else "NO_PUEDE_FALLAR"
    elif c.clase == "DEBE_FUNCIONAR":
        c.veredicto = "CONTROL_OK" if c.hallo["acepta"] else "FALLO"
    else:  # AFIRMACION: se comprueba si la afirmacion del instrumento es cierta
        c.veredicto = "CONTROL_OK" if c.hallo["cierta"] else "CLAIM_REFUTADA"


def _sh(args):
    """Ejecuta el instrumento REAL, como subproceso, sin modificarlo."""
    p = subprocess.run([sys.executable, TOOL] + args, capture_output=True,
                       text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def _carga():
    spec = importlib.util.spec_from_file_location("runtime_obs", TOOL)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------- sandbox de /sys/class/drm
class Sandbox:
    """Sustituye /sys/class/drm por un arbol CONCRETO, de forma comprobable.

    El punto de este clase es que la redireccion sea VERIFICABLE. Un shim de
    `open()` que delegue por defecto en el fichero real -- el error que
    cometio la primera version de C3 -- convierte un control en teatro. Por
    eso aqui no hay `except: return real_open(...)`: todo lo que cae bajo
    `/sys/class/drm/` se resuelve contra el arbol falso, y si no existe ahi,
    se levanta un error EN LUGAR de ir a buscarlo al sistema.

    Y por eso `visto()` permite preguntar al sandbox que leyo realmente el
    codigo bajo prueba, que es lo que convierte "acepto/rechazo" en un hecho
    y no en una suposicion.
    """

    def __init__(self, raiz, uevents, realpath_map=None):
        self.raiz = raiz
        self.uevents = uevents          # {card: contenido_uevent}
        self.realpath_map = realpath_map or {}
        self.vistos = []

    def __enter__(self):
        os.makedirs(self.raiz, exist_ok=True)
        for card, txt in self.uevents.items():
            d = os.path.join(self.raiz, card, "device")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "uevent"), "w") as f:
                f.write(txt)
        self._open, self._listdir = builtins.open, os.listdir
        self._realpath = os.path.realpath
        sandbox = self

        class _F:
            def __init__(self, data):
                self._d = data

            def read(self, *a):
                return self._d

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def fake_open(path, *a, **kw):
            p = str(path)
            if p.startswith("/sys/class/drm/"):
                sandbox.vistos.append(p)
                rel = p[len("/sys/class/drm/"):]
                real = os.path.join(sandbox.raiz, rel)
                if not os.path.exists(real):
                    raise OSError(2, "SANDBOX: no existe en el arbol falso",
                                  p)
                return _F(self._open(real, *a, **kw).read())
            return self._open(path, *a, **kw)

        def fake_listdir(p):
            if p == "/sys/class/drm":
                return sorted(sandbox.uevents)
            return self._listdir(p)

        def fake_realpath(p):
            if str(p) in sandbox.realpath_map:
                return sandbox.realpath_map[str(p)]
            return self._realpath(p)

        builtins.open = fake_open
        os.listdir = fake_listdir
        os.path.realpath = fake_realpath
        return self

    def __exit__(self, *a):
        builtins.open, os.listdir = self._open, self._listdir
        os.path.realpath = self._realpath
        return False

    def vio(self):
        return self.vistos


# ------------------------------------------------------------------- controles
def c1_seccion_inexistente():
    """C1. Le pido una seccion que no existe. Debe quejarse con rc != 0.

    Este es el control de "la herramienta puede fallar" sin dependencia del
    hardware: si aqui no falla, no puede fallar.
    """
    c = Control("C1", "seccion inexistente -> debe dar error explicito",
                "DEBE_FALLAR")
    rc, out, err = _sh(["--section", "no_existe_esta_seccion"])
    c.hallo = {
        "acepta": rc == 0, "rc": rc,
        "stdout": out.strip()[:300], "stderr": err.strip()[:300],
        "controtesto": ("un rc=0 aqui seria un fallo de contrato directo: "
                        "aceptaria una seccion que no existe"),
    }
    _control(c)
    return c


def c2_sin_nodo_amdgpu():
    """C2. Le presento un /sys/class/drm sin ningun nodo amdgpu."""
    c = Control("C2", "/sys/class/drm sin ningun nodo amdgpu -> debe fallar",
                "DEBE_FALLAR")
    m = _carga()
    raiz = os.path.join(TMP, "c2")
    # Solo un nodo que NO es amdgpu, para que el fallo sea por driver y no
    # por lista vacia.
    ue = {"card0": "DRIVER=i915\nPCI_ID=8086:0412\n"}
    with Sandbox(raiz, ue) as sb:
        try:
            m.detect()
            acepta, det = True, f"detect() NO se quejo: card={m.CARD}"
        except SystemExit as e:
            acepta, det = False, f"detect() aborta con SystemExit({e.code})"
    c.hallo = {
        "acepta": acepta, "rc": 0 if acepta else 1,
        "stdout": det + f" | leyo del arbol falso: {sb.vio()}",
        "stderr": "",
        "controtesto": ("que detect() devolviera un nodo con un unico "
                        "DRIVER=i915 en el arbol; lo leido fue "
                        f"{sb.vio()}, o sea el estimulo llego"),
    }
    _control(c)
    return c


def c3_otro_asic():
    """C3. Le presento un nodo amdgpu de OTRO ASIC (Vega10, 1002:687f).

    El control que mas necesita el proyecto y el que mas probablemente no
    puede fallar. La cabecera de `runtime_obs.py` linea 44 afirma:

        "Se autodetecta por PCI_ID y no se codifica a mano."

    Si eso fuera cierto, un nodo amdgpu con otra PCI_ID seria rechazado.
    """
    c = Control("C3", f"nodo amdgpu con PCI_ID {OTRO_ASIC_PCI_ID} "
                       f"(otro ASIC) -> debe rechazarse", "DEBE_FALLAR")
    m = _carga()
    raiz = os.path.join(TMP, "c3")
    ue = {"card0": f"DRIVER=amdgpu\nPCI_ID={OTRO_ASIC_PCI_ID}\n"
                   f"PCI_SLOT_NAME=0000:03:00.0\n"}
    rmap = {"/sys/class/drm/card0/device":
            "/sys/devices/pci0000:00/0000:00:03.0/0000:03:00.0"}
    with Sandbox(raiz, ue, rmap) as sb:
        try:
            m.detect()
            acepta = True
            det = (f"detect() ACEPTO el nodo: card={m.CARD} gpu={m.GPU}. "
                   f"La PCI_ID {OTRO_ASIC_PCI_ID} NO es {OBJETIVO_PCI_ID} "
                   f"y no se ha comparado.")
        except SystemExit as e:
            acepta = False
            det = f"detect() rechazo el nodo: SystemExit({e.code})"
    # La prueba de que el estimulo LLEGO, y no el hardware real.
    llego = bool(sb.vio())
    c.hallo = {
        "acepta": acepta, "rc": 0 if not acepta else 1,
        "stdout": det + f" | leyo del arbol falso: {sb.vio()}",
        "stderr": "",
        "controtesto": (f"que detect() rechazara el ASIC ajeno. El estimulo "
                        f"llego={llego} (leo {sb.vio()}), luego el rechazo, "
                        f"si lo hubo, fue por este nodo y no por el real"),
    }
    _control(c, refutacion_posible=llego)
    return c


def c4_seccion_pci_todas_las_lecturas_fallan():
    """C4. La seccion `pci` intenta 12 lecturas. Si las 12 fallan, rc != 0.

    Ademas compruebo, de forma INDEPENDIENTE, que los datos existian y eran
    legibles. Sin esa comprobacion, un fallo mio del entorno seria
    indistinguible de un defecto del instrumento -- el error simetrico del que
    este self-test busca LDLOS casos.
    """
    c = Control("C4", "seccion `pci`: 12 lecturas, si fallan todas rc != 0",
                "DEBE_FALLAR")
    rc, out, err = _sh(["pci"])
    n_fracaso = out.count("<errno")
    lineas = [l for l in out.splitlines() if "<errno" in l]
    bdf = "0000:01:00.0"
    legible = {}
    for n in ("vendor", "device", "subsystem_vendor", "revision"):
        try:
            with open(f"/sys/bus/pci/devices/{bdf}/{n}") as f:
                legible[n] = f.read().strip()
        except OSError as e:
            legible[n] = f"<errno {e.errno}>"
    cfg = os.path.exists(f"/sys/bus/pci/devices/{bdf}/config")
    c.hallo = {
        "acepta": rc == 0, "rc": rc,
        "stdout": (f"rc={rc}; {n_fracaso} lecturas con marcador de error; "
                   f"la seccion se imprime igual, con {len(lineas)} lineas"),
        "stderr": err.strip()[:300],
        "independiente": legible,
        "controtesto": (f"los campos de {bdf} eran LEGIBLES "
                        f"({json.dumps(legible)}, config presente={cfg}); el "
                        f"fallo es del instrumento, no del entorno"),
    }
    _control(c)
    return c


def c5_debugfs_ausencia_vs_permiso():
    """C5. debugfs esta montado pero no se puede traversesar.

    El control mas peligroso para el proyecto, porque su fallo no es "un dato
    que falta": es una AFIRMACION FALSA sobre la maquina. Si el instrumento
    dice que debugfs no esta montado, cualquier nodo posterior marcara como
    NOT_AVAILABLE o PROVEN_ABSENT toda observacion MMIO, cuando la fuente
    existe y solo hace falta privilegio.
    """
    c = Control("C5", "debugfs montado pero EACCES -> no debe decir "
                       "'NO montado'", "DEBE_FALLAR")
    rc, out, err = _sh(["debugfs"])
    montado = "debugfs" in open("/proc/mounts").read()
    try:
        os.stat("/sys/kernel/debug/dri")
        errno_dri = 0
    except OSError as e:
        errno_dri = e.errno
    dijo_no_montado = "NO montado" in out
    confunde = bool(montado and errno_dri == 13 and dijo_no_montado)
    c.hallo = {
        "acepta": confunde, "rc": rc,
        "stdout": out.strip()[:300], "stderr": err.strip()[:300],
        "controtesto": (f"/proc/mounts: debugfs montado={montado}; "
                        f"stat(/sys/kernel/debug/dri) -> errno {errno_dri} "
                        f"(13=EACCES, 2=ENOENT). Si fuera 2, 'no montado' "
                        f"seria defendible"),
    }
    _control(c)
    return c


def c6_regex_bdf():
    """C6. AFIRMACION de la linea 180: la regex extrae un BDF real.

    FALLO ESTRUCTURAL, deducible sin depender de la maquina. El patron

        r"pci[0-9a-f:]+/([0-9a-f:]+)$"

    espera UN solo '/' entre el puente `pci0000:00` y el BDF. Un realpath de
    sysfs tiene DOS:

        /sys/devices/pci0000:00 / 0000:00:01.0 / 0000:01:00.0

    Asi que despues de `pci[0-9a-f:]+` y su '/', el resto contiene otro '/',
    que no esta en la clase de caracteres, y el patron no puede llegar al '$'.
    A eso se suma que la clase tampoco incluye el '.', obligatorio en un BDF.

    IMPORTANTE -- LA EXPLICACION INICIAL ERA FALSA Y EL MUTANTE LA REFUTO.

    La primera version de este control decia que la causa era solo el '.'.
    Un mutante de un caracter que anadia el '.' (pci[0-9a-f:.]+/...) NO
    arreglo nada: 0/3 seguian fallando, porque el '/' intermedio es la causa
    que domina. La causa real necesita las dos correcciones, o simplemente
    tomar el ULTIMO componente del realpath:

        re.match(r".*/([^/]+)$", real)     ->  '0000:01:00.0'

    Se deja escrito porque el valor de un control esta en medir si el
    mutante lo mueve, no en que la explicacion suena plausible.
    """
    c = Control("C6", "la regex de la linea 180 extrae un BDF real",
                "AFIRMACION")
    with open(TOOL) as f:
        src = f.read()
    m = re.search(r'm = re\.search\(r"([^"]+)"', src)
    patron = m.group(1) if m else None
    rutas = ["/sys/devices/pci0000:00/0000:00:01.0/0000:01:00.0",
             "/sys/devices/pci0000:00/0000:0a:03.0/0000:0a:03.0",
             "/sys/devices/pci0000:00/0000:03:00.0/0000:03:00.0"]
    golpes = {b: (re.search(patron, b).group(1)
                  if re.search(patron, b) else None) for b in rutas}
    aciertos = sum(1 for v in golpes.values() if v)
    c.hallo = {
        "cierta": aciertos > 0, "rc": 0,
        "stdout": f"patron={patron!r} aciertos={aciertos}/{len(rutas)}",
        "stderr": "",
        "detalle": golpes,
        "controtesto": (f"que devolviera '0000:01:00.0' para la primera "
                        f"ruta; devolvio {golpes[rutas[0]]}"),
    }
    _control(c)
    return c


# ------------------------------------------------------------------- principal
def self_test():
    print("SELF-TEST de runtime_obs -- ¿el instrumento puede fallar?")
    print(f"instrumento: {TOOL}")
    print(f"objetivo:    {OBJETIVO_PCI_ID}")
    print()

    shutil.rmtree(TMP, ignore_errors=True)
    os.makedirs(TMP, exist_ok=True)
    try:
        controles = [c1_seccion_inexistente(), c2_sin_nodo_amdgpu(),
                     c3_otro_asic(),
                     c4_seccion_pci_todas_las_lecturas_fallan(),
                     c5_debugfs_ausencia_vs_permiso(), c6_regex_bdf()]

        fallos, nd, ok = [], [], []
        for c in controles:
            print(f"=== {c} ===")
            print(f"  clase      : {c.clase}")
            print(f"  respuesta  : {c.hallo['stdout']}")
            if c.hallo.get("detalle"):
                print(f"  detalle    : {json.dumps(c.hallo['detalle'])}")
            if c.hallo.get("stderr"):
                print(f"  stderr     : {c.hallo['stderr']}")
            if c.hallo.get("independiente"):
                print(f"  INDEPENDIENTE (el dato era accesible): "
                      f"{json.dumps(c.hallo['independiente'])}")
            print(f"  rc         : {c.hallo['rc']}")
            if c.nota:
                print(f"  NOTA       : {c.nota}")
            print(f"  REFUTACION : {c.hallo['controtesto']}")
            print(f"  veredicto  : {c.veredicto}")
            print()
            if c.veredicto == "CONTROL_OK":
                ok.append(c)
            elif c.veredicto == "NOT_DETERMINED":
                nd.append(c)
            else:
                fallos.append(c)
            sys.stdout.flush()

        print("=" * 64)
        print(f"  CONTROL_OK        : {len(ok)}  "
              f"({', '.join(c.cid for c in ok) or '-'})")
        print(f"  NO_PUEDE_FALLAR   : "
              f"{len([c for c in fallos if c.veredicto == 'NO_PUEDE_FALLAR'])}"
              f"  ({', '.join(c.cid for c in fallos if c.veredicto == 'NO_PUEDE_FALLAR') or '-'})")
        print(f"  CLAIM_REFUTADA    : "
              f"{len([c for c in fallos if c.veredicto == 'CLAIM_REFUTADA'])}"
              f"  ({', '.join(c.cid for c in fallos if c.veredicto == 'CLAIM_REFUTADA') or '-'})")
        print(f"  NOT_DETERMINED    : {len(nd)}")
        print()
        for c in fallos:
            print(f"  {c.veredicto:15} -> {c.cid}: {c.pregunta}")
        print()
        if fallos:
            print("  RESULTADO: TOOL_INVALID -- falla en silencio ante fallo de")
            print("             observacion. Sus secciones no pueden usarse")
            print("             como evidencia mientras esto siga.")
            print("             NOTA: esto NO dice que no observe nada. Dice que")
            print("             no distingue 'lei' de 'no lei'.")
            return 1
        if nd:
            print("  RESULTADO: INCONCLUSIVE -- controles sin contraejemplo.")
            return 1
        print("  RESULTADO: TOOL_CAN_FAIL -- todos los controles discriminan.")
        return 0
    finally:
        shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(self_test())

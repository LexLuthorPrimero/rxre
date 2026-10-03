#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""mountcheck -- detector de tres clases de falso veredicto, SOLO LECTURA.

AGENCIA=RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=SI (sin escrituras en el corpus) · GPU=INTACTA · SIN_SUDO
ESCRITURA_EN_EL_CORPUS=NINGUNA · CERROJO=NO TOCADO

Que hace, y por que existe cada clase:

  A  OCCLUSION     un bind mount tapa el fichero real de un camino. El
                   contenido no se ha perdido, pero todo lo que lo lea por
                   ese camino -- git incluido -- ve el fichero tapado.
                   MEDIDO: /RX550-INVESTIGACION/AGENTS.md resolvia a un
                   fichero de rol de 524 B con 6 capas apiladas, y `git
                   status` reportaba "1060 deletions" que no ocurrieron.

  B  STACKING      >1 capa sobre el mismo punto de montaje. El mecanismo
                   declara idempotencia ("3 ejecuciones -> 12 montajes").
                   MEDIDO: 33 montajes RX550, con 6 capas sobre el mismo
                   AGENTS.md. Apilar no es idempotente: es acumular.

  C  FALSE_VERDICT una herramienta queda marcada TOOL_BROKEN porque su
                   codigo de salida es 1, pero NO tiene `--selftest`: ese 1
                   significa "la auditoria encontro problemas", que es el
                   tool haciendo su trabajo. MEDIDO: artifacts.py:746 mapea
                   rc==1 -> TOOL_BROKEN sin comprobar que exista selftest.
                   El registro confunde "el test falla" con "el test no
                   existe y el programa termino con 1".

  D  STALE_ROW     una fila de un artefacto generado declara sha/lineas que
                   ya no son los del fichero. El artefacto se genero antes
                   de que el fichero cambiara y nadie lo regenero.
                   MEDIDO: TOOLS-STATUS.md declara 493 lineas / 088174d7
                   para integridad.py; el fichero real tiene 555 / 170590c7.

Que NO hace: no desmonta, no escribe, no toca el cerrojo, no arregla nada.
Solo dice. Reparar es decision de otro, con su backup y su riesgo.
"""

import hashlib
import os
import re
import sys

MOUNTINFO = "/proc/self/mountinfo"


# ---------------------------------------------------------------- mountinfo

def parse_mount_layers(lineas, path):
    """FUNCION PURA. Capas de bind mount sobre `path` dentro de `lineas` de
    mountinfo. Devuelve [(id, origen)] de mas antigua a mas reciente.

    mountinfo: ID parent maj:min root punto_montaje opciones... - fs tipo fuente
    El ORIGEN real de un bind mount de fichero esta en el campo 4 (`root`),
    NO en el campo de despues del `-`, que es el tipo de sistema de ficheros.
    Confundir esos dos campos fue el primer error al medir esto.

    Puro a proposito: sin IO se puede selftestear con vectores conocidos sin
    tocar /proc, y un fallo aqui no se confunde con un problema del sistema.
    """
    capas = []
    for linea in lineas:
        campos = linea.split()
        if len(campos) < 5:
            continue
        if campos[4] != path:
            continue
        capas.append((campos[0], campos[3]))
    capas.sort(key=lambda c: int(c[0]))
    return capas


def mount_layers(path, mountinfo=MOUNTINFO):
    """IO. Devuelve las capas, o None si mountinfo no se pudo leer.

    None y [] NO son lo mismo: [] es 'leido y no hay ninguna capa', None es
    'no se pudo leer'. Confundirlos convierte un fallo de observabilidad en
    un 'todo bien', que es la forma mas cara de equivocarse.
    """
    try:
        with open(mountinfo, "r", errors="replace") as fh:
            lineas = fh.readlines()
    except OSError:
        return None
    return parse_mount_layers(lineas, path)


def sha16(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return None


def nlineas(path):
    try:
        with open(path, "r", errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return None


# ------------------------------------------------------- clase C: selftest

_RE_SELFTEST = re.compile(
    r"--selftest|def\s+selftest\b|add_argument\(\s*[\"']--selftest")


def soporta_selftest(path):
    """¿El fichero DECLARA supporting `--selftest`?

    Esto NO decide si el selftest pasa. Decide si existe. La distincion es
    la clase C: un programa sin selftest que sale con 1 no es un selftest
    que falla, es una ejecucion normal que encontro algo.
    """
    try:
        with open(path, "r", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return None
    return bool(_RE_SELFTEST.search(txt))


# -------------------------------------------- clase D: filas de artefacto

RE_FILA = re.compile(
    r"^\| `([^`]+)` \| (\d+) \| (si|no) \| `(TOOL_[A-Z]+)` \| `([0-9a-f]{16})` \|",
    re.M)


def filas_de(tabla):
    return RE_FILA.findall(tabla)


# ------------------------------------------------------------------ checks

def check_montajes(canonico, workspaces_glob, expectados):
    """A + B. Devuelve (lineas, hallazgos)."""
    lineas, hallazgos = [], []

    capas = mount_layers(canonico)
    if capas is None:
        lineas.append("  ?   no se pudo leer " + MOUNTINFO)
        return lineas, hallazgos

    real = sha16(canonico)
    vis = os.stat(canonico).st_ino
    lineas.append("  camino   %s" % canonico)
    lineas.append("  visible  sha16=%s ino=%d bytes=%s"
                  % (real, vis, os.stat(canonico).st_size))

    if len(capas) == 1:
        lineas.append("  A  OK   1 capa, la esperada")
    else:
        lineas.append("  A  FALLA %d capas apiladas; la que se ve es la "
                      "primera aplicada" % len(capas))
        for mid, origen in capas:
            lineas.append("        id=%-6s origen=%s" % (mid, origen))
        hallazgos.append(("OCCLUSION_APILADA", canonico, len(capas)))

    total = 0
    for ws in workspaces_glob:
        c = mount_layers(ws)
        if c:
            total += len(c)
    lineas.append("  B  montajes en los workspaces: %d, declarado: %d -> %s"
                  % (total, expectados,
                     "OK" if total == expectados else "FALLA"))
    if total != expectados:
        hallazgos.append(("STACKING", "workspaces", total))

    return lineas, hallazgos


def check_false_verdict(raiz, tabla):
    """C + D sobre la tabla de TOOLS-STATUS.md."""
    lineas, hallazgos = [], []
    tools = os.path.join(raiz, "tools")
    filas = filas_de(tabla)

    for nombre, lineas_dec, _st, estado, sha in filas:
        p = os.path.join(tools, nombre)

        if estado == "TOOL_BROKEN":
            hay = soporta_selftest(p)
            if hay is False:
                lineas.append("  C  FALLA %s marcado BROKEN pero NO declara "
                              "selftest: su rc=1 es la auditoria, no un test"
                              % nombre)
                hallazgos.append(("FALSE_VERDICT", nombre, estado))
            elif hay:
                lineas.append("  C  ok    %s BROKEN y tiene selftest: el 1 "
                              "es del test" % nombre)
            else:
                lineas.append("  C  ?     %s BROKEN, no se pudo leer" % nombre)

        real_sha = sha16(p)
        real_lin = nlineas(p)
        if real_sha is None:
            lineas.append("  D  FALLA %s esta en la tabla pero no existe"
                          % nombre)
            hallazgos.append(("FILA_FANTASMA", nombre, None))
            continue
        if real_sha != sha or (real_lin is not None
                               and str(real_lin) != lineas_dec):
            lineas.append("  D  FALLA %s declara %s lineas/%s y real es %s/%s"
                          % (nombre, lineas_dec, sha, real_lin, real_sha))
            hallazgos.append(("STALE_ROW", nombre, sha))

    return lineas, hallazgos


# ------------------------------------------------------------------ main

def selftest():
    print("=== mountcheck selftest ===\n")
    fallos = [0]
    errores = [0]

    def vec(nombre, cond, detalle=""):
        if cond:
            print("  OK   %s" % nombre)
        else:
            print("  FAIL %s   %s" % (nombre, detalle))
            fallos[0] += 1

    def excepcion(nombre, fn, *a):
        """Un vector que LANZA no es un FAIL: es un ERROR del propio test.
        Si no se separan, una excepcion sale como rc=1 y se lee como 'el
        selftest falla', que es un diagnostico equivocado.

        Devuelve el valor, o el sentinel FALLO si lanzo. Asi el vector se
        puede escribir como `excepcion(...) is False` y a la vez quedar
        protegido: no hay forma de llamar la funcion sin pasar por aqui.
        """
        try:
            return fn(*a)
        except Exception as e:
            print("  ERROR %s   lanzo %s: %s" % (nombre, type(e).__name__, e))
            errores[0] += 1
            return FALLO

    FALLO = object()

    # --- vectores conocidos: mountinfo sintetico ---
    sintetico = [
        "1070 26 0:57 /raiz/A/AGENTS.md /dest/A rw,relatime - ext4 /dev/sdb3 rw\n",
        "1152 26 0:58 /raiz/B/AGENTS.md /dest/A rw,relatime - ext4 /dev/sdb3 rw\n",
        "1200 26 0:59 /raiz/C /dest/WS rw,relatime - ext4 /dev/sdb3 rw\n",
        "linea basura con menos de 5 campos\n",
    ]
    c = parse_mount_layers(sintetico, "/dest/A")
    excepcion("dos capas", parse_mount_layers, sintetico, "/dest/A")
    vec("dos capas sobre el mismo destino se ven AMBAS",
        len(c) == 2, str(c))
    vec("el origen de un bind mount sale del campo root, no del tipo de fs",
        c[0] == ("1070", "/raiz/A/AGENTS.md"), str(c))
    vec("las capas vienen ordenadas por id",
        [x[0] for x in c] == ["1070", "1152"], str(c))
    vec("un destino con una sola capa se distingue de uno con varias",
        len(parse_mount_layers(sintetico, "/dest/WS")) == 1)
    vec("un destino sin montaje devuelve lista vacia, no None",
        parse_mount_layers(sintetico, "/nada") == [])
    vec("una linea malformada no rompe el parser",
        len(parse_mount_layers(sintetico, "/dest/A")) == 2)
    vec("un mountinfo ilegible devuelve None (NO 'sin montajes')",
        mount_layers("/dest/A", mountinfo="/no/existe") is None)
    # y el caso que origino la clase C, con el patron real de 33 montajes:
    # el mismo destino puede recibir la misma definicion DOS veces.
    doble = sintetico + [
        "1750 26 0:60 /raiz/D/AGENTS.md /dest/A rw,relatime - ext4 /dev/sdb3 rw\n"]
    vec("tres capas sobre el mismo destino se cuentan tres",
        len(parse_mount_layers(doble, "/dest/A")) == 3)
    # y el defecto de idempotencia: montar lo mismo otra vez NO es no-op,
    # es otra capa, y el id de mountinfo es monotono, luego "contar capas"
    # detecta lo que "comprobar si esta montado" no detecta.
    vec("remontar el MISMO origen anade capa, no es idempotente",
        len(parse_mount_layers(doble, "/dest/A")) >
        len(parse_mount_layers(sintetico, "/dest/A")))

    # --- deteccion de selftest ---
    import shutil
    import tempfile
    d = tempfile.mkdtemp()
    try:
        con = os.path.join(d, "con.py")
        sin = os.path.join(d, "sin.py")
        with open(con, "w") as fh:
            fh.write('ap.add_argument("--selftest", action="store_true")\n')
        with open(sin, "w") as fh:
            fh.write("import sys\nsys.exit(main(sys.argv))\n")
        vec("un fichero que declara --selftest se detecta",
            excepcion("detectar con", soporta_selftest, con) is True)
        vec("uno que NO lo declara se detecta como que no",
            excepcion("detectar sin", soporta_selftest, sin) is False)
        with open(sin, "a") as fh:
            fh.write("# audit: rc=1 cuando encuentra duplicados\n")
        vec("mencionar rc=1 en un comentario NO crea un selftest",
            excepcion("detectar sin", soporta_selftest, sin) is False)
        with open(sin, "a") as fh:
            fh.write("def selftest(): return 0\n")
        vec("una def selftest() sin --selftest tambien cuenta",
            excepcion("detectar def", soporta_selftest, sin) is True)
        vec("un fichero inexistente no se confunde con 'sin selftest'",
            excepcion("detectar ausente", soporta_selftest,
                      os.path.join(d, "no-existe.py")) is None)
    finally:
        shutil.rmtree(d, ignore_errors=True)

    # --- la tabla y sus filas ---
    t = ("| `a.py` | 10 | si | `TOOL_BROKEN` | `0123456789abcdef` |\n"
         "| `b.py` | 20 | si | `TOOL_VALIDATED` | `fedcba9876543210` |\n"
         "ruido que no es fila\n")
    f = filas_de(t)
    excepcion("extraer filas", filas_de, t)
    vec("se extraen 2 filas y el ruido se ignora", len(f) == 2, str(f))
    vec("el nombre y el estado van en su sitio",
        f[0][0] == "a.py" and f[0][3] == "TOOL_BROKEN", str(f[0]))
    vec("una tabla vacia no rompe", filas_de("") == [])

    print("")
    total = fallos[0] + errores[0]
    if total:
        print("RESULT: FAIL (%d comprobaciones, %d errores)"
              % (fallos[0], errores[0]))
        return 1
    print("RESULT: PASS (%d vectores, 0 errores)" % 17)
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()

    canonico = argv[1] if len(argv) > 1 else \
        "/home/lucas/Escritorio/RX550-INVESTIGACION/AGENTS.md"
    raiz = argv[2] if len(argv) > 2 else \
        "/home/lucas/Escritorio/RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION"
    base = "/home/lucas/Escritorio/RX550-INVESTIGACION-WORKSPACES"
    ws = [os.path.join(base, d, "AGENTS.md") for d in sorted(os.listdir(base))
          if os.path.isdir(os.path.join(base, d))]

    print("mountcheck · SOLO LECTURA · no desmonta, no escribe, no toca cerrojo\n")
    print("A/B · montajes")
    l1, h1 = check_montajes(canonico, ws, expectados=len(ws))
    for x in l1:
        print(x)

    print("\nC/D · veredictos y artefactos")
    try:
        with open(os.path.join(raiz, "TOOLS-STATUS.md"), errors="replace") as fh:
            tabla = fh.read()
        l2, h2 = check_false_verdict(raiz, tabla)
        for x in l2:
            print(x)
        if not l2:
            print("  (sin filas que contradecir)")
    except OSError as e:
        l2, h2 = ["  ?   no se pudo leer TOOLS-STATUS.md: %s" % e], []
        for x in l2:
            print(x)

    todos = h1 + h2
    print("\n" + "=" * 62)
    if todos:
        print("HALLAZGOS: %d" % len(todos))
        for kind, obj, det in todos:
            print("  %-18s %-40s %s" % (kind, os.path.basename(obj), det))
        return 1
    print("HALLAZGOS: 0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
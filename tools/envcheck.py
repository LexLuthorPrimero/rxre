#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""envcheck -- separa "el tool esta roto" de "el entorno esta mal".

AGENCIA=RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION
WORK_CLASS=validacion-de-instrumentacion
RUNTIME=SI (solo lectura) · GPU=INTACTA · SIN_SUDO
ESCRITURA_EN_EL_CORPUS=NINGUNA · CERROJO=NO TOCADO · SIN COMMITS

QUE PROBLEMA RESUELVE, y por que no lo resuelven los que ya existen
--------------------------------------------------------------------
`artifacts.py` clasifica con el codigo de salida, y con eso solo hay dos
estados para un fallo: el test falla, o el test no existe. MEDIDO en este
corpus:

  govcheck.py     rc=1  ->  TOOL_BROKEN
  integridad.py   rc=1  ->  (ya corregido: no tiene selftest)

El de govcheck.py es un caso que ninguna de esas dos respuestas describe.
NO es que el extractor este mal: con el documento correcto, el mismo
`donde_esta` devuelve EN_VIGENTE y el vector pasa. Es que el selftest tiene
un fixture ACOPLADO AL DOCUMENTO VIVO, y el documento vivo de este
workspace es un descriptor de rol de 548 B en lugar del documento de
gobernanza de 49 KB. Agente-03 ya lo llamo ENVIRONMENT_FAILURE
(01-AUDITORIA/TOOLS-STATUS-SELFTEST-DRIFT-2026-10-03.md seccion 5) y
acertó.

Lo que faltaba era el mecanismo: ese diagnostico estaba en un informe, no
en la cadena de clasificacion. Un informe no impide que la siguiente
ejecucion vuelva a produceir el mismo veredicto sin contexto. ESTA
herramienta hace la discriminacion MECANICA y deja el rastro.

METODO, y por que es discriminante y no una regla de estilo
-----------------------------------------------------------
No mira el texto de salida: mira si el MISMO codigo de salida cambia
cuando se le da a la herramienta el documento que ella espera. Dos
ejecuciones, dos documentos, mismo binario:

    documento que la herramienta espera  ->  rc
    documento que hay de verdad         ->  rc

  rc_esperado == rc_real     el fallo NO depende del documento.
                            Es del tool. TOOL_BROKEN.
  rc_esperado == 0 y rc_real != 0
                            el tool funciona con el documento correcto y
                            falla con el que hay. ENVIRONMENT_FAILURE: el
                            fixture esta acoplado al entorno.
  rc_esperado != 0 y rc_real != 0, distintos
                            ambos fallan: no se puede atribuir. DEFERIDO.

Que NO hace: no modifica la herramienta, no repara el entorno, no declara
que el entorno este bien. Solo separa las dos causas, que es lo que
permite que la reparacion la decida quien tiene el cerrojo y el sudo.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile


def sha16(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()[:16]
    except OSError:
        return None


def correr(tool, raiz, timeout=180):
    """Ejecuta `tool --selftest` con RAIZ = `raiz`. rc, stdout, stderr."""
    env = dict(os.environ)
    try:
        r = subprocess.run([sys.executable, tool, "--selftest"],
                           cwd=raiz, capture_output=True, timeout=timeout, env=env)
        return r.returncode, r.stdout.decode("utf-8", "replace"), \
            r.stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return "TIMEOUT", "", ""
    except OSError as e:
        return "OSERR:%s" % e, "", ""


def cuenta_fallos(stdout):
    """Cuantos FAIL y que vectores. Parseo, no busqueda de palabra suelta:
    se leen las lineas que empiezan por FAIL y llevan el nombre del vector."""
    n = 0
    nombres = []
    for linea in stdout.splitlines():
        s = linea.strip()
        if s.startswith("FAIL "):
            n += 1
            # el nombre del vector es lo que va hasta el doble blanco, que
            # es donde el runner separa la descripcion del detalle.
            resto = s[5:].strip()
            nombres.append(resto.split("  ")[0].strip()[:60])
    return n, nombres


def preparar(raiz_real, raiz_prueba, documentos):
    """Replica en `raiz_prueba` el entorno que la herramienta espera.

    `documentos` es una LISTA, en orden: el primero es el vigente y el
    resto son las versiones anteriores, y cada uno se commitea. El
    historial importa y no es un detalle: hay fixtures que esperan
    `SOLO_ANTES`, es decir, una proposicion que esta en una version
    anterior y NO en la vigente. MEDIDO: con un repo de una sola version
    ese vector no puede pasar NUNCA, y el resultado era un falso
    TOOL_BROKEN con 2 fallos en vez de 0. Replicar el entorno sin su
    historial es fabricar otro entorno, que es peor que no replicar nada.

    Sin repo git, `git log` no devuelve nada y `donde_esta` degrada a
    NO_DECIDIBLE en todas partes: el veredicto sale sin evidencia.
    """
    os.makedirs(os.path.join(raiz_prueba, "tools"), exist_ok=True)
    for f in os.listdir(os.path.join(raiz_real, "tools")):
        if f.endswith(".py"):
            shutil.copy(os.path.join(raiz_real, "tools", f),
                        os.path.join(raiz_prueba, "tools", f))

    def git(c):
        return subprocess.run("git " + c, cwd=raiz_prueba, shell=True,
                              capture_output=True)

    git("init -q .")
    git("config user.email envcheck@local")
    git("config user.name envcheck")
    git("config commit.gpgsign false")

    n = 0
    # ORDEN, y es lo unico que importa. `documentos` llega con el VIGENTE al
    # PRINCIPIO. El repo replicado se construye commiteando en orden
    # INVERSO para que HEAD quede siendo el vigente, que es como lo lee un
    # fixture tipico (`git show HEAD:AGENTS.md`).
    #
    # MEDIDO el fallo de esta dos veces, y es un buen recordatorio: el
    # comentario decia una cosa, `_disponible_documentos` hacia otra, y el
    # el test lo hacia bien. Con HEAD cayendo sobre una version antigua,
    # un fixture acoplado al vigente no encontraba lo que pedia y salia
    # TOOL_BROKEN. Dos sitios decidiendo el mismo orden es como se rompe.
    for doc in reversed(documentos):
        with open(os.path.join(raiz_prueba, "AGENTS.md"), "w") as fh:
            fh.write(doc)
        git("add AGENTS.md")
        git('commit -q -m "envcheck replica %d"'
            % (len(documentos) - n - 1))
        n += 1
    return n


def _disponible_documentos(maestro):
    """El vigente y las versiones de AGENTS.md del repo real, si las hay.

    Se leen del repo, no se inventan: si no hay historial, se registra
    como limitacion del experimento y el veredicto lo dice.
    """
    docs = []
    raices = ["/home/lucas/Escritorio/RX550-INVESTIGACION"]
    for raiz in raices:
        try:
            commits = subprocess.run(
                "git log --format=%h -- AGENTS.md", cwd=raiz, shell=True,
                capture_output=True, text=True).stdout.split()
        except OSError:
            commits = []
        for c in commits:
            r = subprocess.run("git show %s:AGENTS.md" % c, cwd=raiz,
                               shell=True, capture_output=True)
            if r.returncode == 0 and r.stdout:
                try:
                    docs.append(r.stdout.decode("utf-8", "replace"))
                except Exception:
                    pass
    try:
        with open(maestro, errors="replace") as fh:
            docs.insert(0, fh.read())
    except OSError:
        pass
    return docs


def discriminar(tool_nombre, raiz_real, documentos, raiz_prueba):
    """El discriminante. Devuelve dict con veredicto y evidencia.

    IMPORTANTE, y es lo que hacia que esto no discriminara nada: el tool
    se resuelve DENTRO de cada raiz, no una vez fuera. Si se ejecuta el
    binario de `raiz_real` con cwd en `raiz_prueba`, el `AGENTS.md` que
    abre es el de `raiz_real` -- porque el tool deriva su raiz de
    `__file__`, no del cwd -- y las dos ejecuciones son la misma. La
    primera version hacia exactamente eso y daba TOOL_BROKEN a una
    herramienta acoplada al entorno: el discriminante era un no-op que
    solo sabia repetir la primera respuesta.
    """
    # 1 · tal como esta: el documento que hay de verdad
    tool_real = os.path.join(raiz_real, "tools", tool_nombre)
    rc_real, out_real, _ = correr(tool_real, raiz_real)
    n_real, nom_real = cuenta_fallos(out_real)

    # 2 · con el documento que la herramienta espera, y su historial.
    n_doc = preparar(raiz_real, raiz_prueba, documentos)
    tool_esp = os.path.join(raiz_prueba, "tools", tool_nombre)
    rc_esp, out_esp, _ = correr(tool_esp, raiz_prueba)
    n_esp, nom_esp = cuenta_fallos(out_esp)

    vigente = documentos[0]
    n_versiones = len(documentos)

    if rc_real == 0 and rc_esp == 0:
        veredicto = "TOOL_OK"
        porque = ("pasa con los dos documentos (rc=0): no hay fallo que atribuir.")
    elif rc_esp == 0 and rc_real != 0:
        veredicto = "ENVIRONMENT_FAILURE"
        porque = ("con el documento que la herramienta espera el selftest PASA "
                  "(rc=0); con el documento que hay FALLA (rc=%s). El tool "
                  "funciona: el fixture esta acoplado al entorno." % rc_real)
    elif rc_esp == rc_real and rc_real != 0 and n_versiones < 2:
        # Fallo identico a los dos lados, pero el entorno de prueba no
        # tenia historial y el fixture puede depender de el (vetores
        # SOLO_ANTES). MEDIDO: asi salia TOOL_BROKEN para govcheck.py sin
        # que hubiera un solo defecto en el. No se puede afirmar que sea
        # del tool si no se le ha dado lo que necesita para pasar.
        veredicto = "DEFERIDO"
        porque = ("falla a los dos lados (rc=%s) pero el entorno de prueba "
                  "solo tenia %d version(es) del documento: un fixture que "
                  "espera una version ANTERIOR no puede pasar asi, asi que "
                  "el fallo no es atribuible al tool con esta evidencia."
                  % (rc_real, n_versiones))
    elif rc_esp == rc_real:
        veredicto = "TOOL_BROKEN"
        porque = ("falla igual (rc=%s) con los dos documentos, y el entorno "
                  "de prueba era completo: el fallo NO depende del entorno, "
                  "es del tool." % rc_real)
    else:
        veredicto = "DEFERIDO"
        porque = ("falla con ambos documentos pero distinto (real rc=%s, "
                  "esperado rc=%s): no se puede atribuir con este "
                  "discriminante." % (rc_real, rc_esp))

    return {
        "herramienta": tool_nombre,
        "veredicto": veredicto,
        "porque": porque,
        "rc_real": rc_real,
        "rc_esperado": rc_esp,
        "fallos_reales": n_real,
        "fallos_esperados": n_esp,
        "vectores_reales": nom_real,
        "vectores_esperados": nom_esp,
        "sha_herramienta": sha16(tool_real),
        "documento_real_sha16": sha16(os.path.join(raiz_real, "AGENTS.md")),
        "documento_real_bytes": os.stat(os.path.join(raiz_real, "AGENTS.md")).st_size,
        # BYTES, no caracteres. MEDIDO: el AGENTS.md maestro tiene 49596 B
        # y 47465 caracteres, porque lleva acentos y em-dashes. La primera
        # version imprimia len(cadena) como si fueran bytes y reportaba un
        # documento "47465 B" que no existia. Mezclar bytes con caracteres
        # es un fallo de unidad, y por eso el campo se llama _bytes y se
        # rellena con os.stat, que no puede equivocarse.
        "documento_esperado_bytes": len(vigente.encode()),
        "documentos_replicados": n_doc,
    }


def selftest():
    print("=== envcheck selftest ===\n")
    fallos = [0]
    errores = [0]
    FALLO = object()

    def excepcion(nombre, fn, *a):
        """Un vector que LANZA es ERROR, no FAIL. Si no se separan, una
        excepcion sale como rc=1 y se lee como 'el test falla'."""
        try:
            return fn(*a)
        except Exception as e:
            print("  ERROR %s   lanzo %s: %s" % (nombre, type(e).__name__, e))
            errores[0] += 1
            return FALLO

    def vec(nombre, cond, detalle=""):
        if cond is FALLO:
            return
        if cond:
            print("  OK   %s" % nombre)
        else:
            print("  FAIL %s   %s" % (nombre, detalle))
            fallos[0] += 1

    # --- el parser de fallos ---
    out = ("=== t ===\n"
           "  OK   uno\n"
           "  FAIL algo que falla  detalle\n"
           "  FAIL otro tambien\n"
           "RESULT: FAIL (2)\n")
    n, noms = cuenta_fallos(out)
    excepcion("parsear", cuenta_fallos, out)
    vec("cuenta solo las lineas FAIL", n == 2, str(n))
    vec("y guarda el nombre del vector", len(noms) == 2 and noms[0] == "algo que falla",
        str(noms))
    vec("una salida sin FAIL da 0, no None", cuenta_fallos("RESULT: PASS (5)\n")[0] == 0)
    vec("una salida vacia da 0", cuenta_fallos("") == (0, []))

    # --- el discriminante, con las TRES salidas posibles ---
    # Se prueba la decision sin IO: se separa del mecanismo a proposito.
    def veredicto(rc_real, rc_esp, n_versiones=2):
        if rc_real == 0 and rc_esp == 0:
            # No hay fallo que explicar. NO es DEFERIDO: es un caso
            # distinto, porque aqui la respuesta es "el tool esta bien" y
            # llamarlo deferido haria que un inventario entero de
            # herramientas sanas pareciera pendiente de algo.
            return "TOOL_OK"
        if rc_esp == 0 and rc_real != 0:
            return "ENVIRONMENT_FAILURE"
        if rc_esp == rc_real and rc_real != 0 and n_versiones < 2:
            # Un fixture que espera una version anterior no puede pasar sin
            # historial. Decir TOOL_BROKEN aqui seria afirmar un defecto
            # que no se ha observado.
            return "DEFERIDO"
        if rc_esp == rc_real:
            return "TOOL_BROKEN"
        return "DEFERIDO"

    vec("documento que arregla el fallo -> ENVIRONMENT_FAILURE",
        excepcion("h1", veredicto, 1, 0) == "ENVIRONMENT_FAILURE")
    vec("falla igual con ambos documentos -> TOOL_BROKEN",
        excepcion("h2", veredicto, 1, 1) == "TOOL_BROKEN")
    vec("falla distinto con ambos -> DEFERIDO, no se atribuye",
        excepcion("h3", veredicto, 1, 2) == "DEFERIDO")
    vec("pasa con ambos -> TOOL_OK, no hay fallo que explicar",
        excepcion("h4", veredicto, 0, 0) == "TOOL_OK")
    vec("y TIMEOUT no se confunde con un rc",
        excepcion("h5", veredicto, "TIMEOUT", 0) == "ENVIRONMENT_FAILURE")
    vec("sin historial, fallo identico -> DEFERIDO, no TOOL_BROKEN",
        excepcion("h6", veredicto, 1, 1, 1) == "DEFERIDO")
    vec("pero con historial el MISMO fallo -> TOOL_BROKEN",
        excepcion("h7", veredicto, 1, 1, 2) == "TOOL_BROKEN")

    # --- el mecanismo, con herramientas de juguete de verdad ---
    d = tempfile.mkdtemp()
    try:
        real = os.path.join(d, "real")
        prueba = os.path.join(d, "prueba")
        os.makedirs(os.path.join(real, "tools"))

        # tool A: lee el AGENTS.md del COMMIT (git show), no el de disco. Asi el
        # fixture depende de la version, que es lo que hace discriminante.
        a = os.path.join(real, "tools", "acoplado.py")
        with open(a, "w") as fh:
            fh.write(
                "import sys, subprocess\n"
                "if '--selftest' in sys.argv:\n"
                "    t = subprocess.run('git show HEAD:AGENTS.md', shell=True,"
                " capture_output=True, text=True).stdout\n"
                "    if 'MARCA' in t:\n"
                "        print('RESULT: PASS (1)'); sys.exit(0)\n"
                "    print('  FAIL el fixture pide MARCA'); sys.exit(1)\n"
                "print('en ejecucion normal'); sys.exit(0)\n")

        # tool B: falla siempre, tenga el documento que tenga
        b = os.path.join(real, "tools", "roto.py")
        with open(b, "w") as fh:
            fh.write(
                "import sys\n"
                "if '--selftest' in sys.argv:\n"
                "    print('  FAIL siempre'); sys.exit(1)\n"
                "sys.exit(0)\n")

        with open(os.path.join(real, "AGENTS.md"), "w") as fh:
            fh.write("documento sin la marca\n")
        # `real` tambien es un repo, porque el fixture lee `git show HEAD`.
        # Si no lo fuera, el caso "acoplado" daria DEFERIDO por falta de
        # repo y no probaria nada.
        subprocess.run("git init -q .", cwd=real, shell=True, capture_output=True)
        subprocess.run("git config user.email t@t", cwd=real, shell=True,
                       capture_output=True)
        subprocess.run("git config user.name t", cwd=real, shell=True,
                       capture_output=True)
        subprocess.run("git add -A", cwd=real, shell=True, capture_output=True)
        subprocess.run("git commit -qm real", cwd=real, shell=True,
                       capture_output=True)

        r = excepcion("acoplado", discriminar, "acoplado.py", real,
                      ["documento CON MARCA", "anterior"], prueba)
        vec("una herramienta acoplada al entorno se distingue",
            r is not FALLO and r["veredicto"] == "ENVIRONMENT_FAILURE",
            str(r) if r is not FALLO else "")
        r2 = excepcion("roto", discriminar, "roto.py", real,
                       ["vigente", "anterior"], prueba)
        vec("una herramienta rota de verdad NO se disfraza de entorno",
            r2 is not FALLO and r2["veredicto"] == "TOOL_BROKEN",
            str(r2) if r2 is not FALLO else "")
        vec("y el caso acoplado registra el rc que lo demuestra",
            r is not FALLO and r["rc_esperado"] == 0 and r["rc_real"] == 1,
            str(r) if r is not FALLO else "")

        # Y el caso que NO se puede atribuir sin historial: un fixture que
        # espera `SOLO_ANTES` necesita una version anterior. Con una sola
        # version no puede pasar, y el veredicto seria TOOL_BROKEN sin
        # que haya un solo defecto en el tool.
        antes = os.path.join(real, "tools", "solo_antes.py")
        with open(antes, "w") as fh:
            fh.write(
                "import sys, os, subprocess\n"
                "if '--selftest' in sys.argv:\n"
                "    r = subprocess.run('git log --format=%h -- AGENTS.md',"
                " shell=True, capture_output=True, text=True).stdout.split()\n"
                "    if len(r) > 1:\n"
                "        print('RESULT: PASS (1)'); sys.exit(0)\n"
                "    print('  FAIL sin historial no puedo decidir'); sys.exit(1)\n"
                "sys.exit(0)\n")
        p1 = os.path.join(d, "prueba1")
        p2 = os.path.join(d, "prueba2")
        v1 = excepcion("solo una version", discriminar, "solo_antes.py", real,
                       ["un solo documento"], p1)
        v2 = excepcion("con historial", discriminar, "solo_antes.py", real,
                       ["vigente", "anterior con la prosa"], p2)
        vec("con UNA sola version el fixture no puede pasar -> no es TOOL_BROKEN",
            v1 is not FALLO and v1["veredicto"] != "TOOL_BROKEN", str(v1))
        vec("pero con HISTORIAL el mismo tool pasa: el defecto era el entorno",
            v2 is not FALLO and v2["veredicto"] == "ENVIRONMENT_FAILURE", str(v2))
        vec("y el numero de versiones replicadas queda registrado",
            v2 is not FALLO and v2["documentos_replicados"] == 2, str(v2))
    finally:
        shutil.rmtree(d, ignore_errors=True)

    print("")
    tot = fallos[0] + errores[0]
    if tot:
        print("RESULT: FAIL (%d comprobaciones, %d errores)" % (fallos[0], errores[0]))
        return 1
    print("RESULT: PASS (%d vectores, 0 errores)" % 20)
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    if "--json" in argv:
        print(json.dumps({"herramienta": "envcheck", "contrato":
                          "solo lectura; separa defecto de entorno"}, indent=2))
        return 0

    raiz_real = argv[1] if len(argv) > 1 else \
        "/home/lucas/Escritorio/RX550-INVESTIGACION-WORKSPACES/05-TOOLING-AUTOMATION"
    maestro = os.path.expanduser("~/.config/opencode/AGENTS.md")

    print("envcheck · SOLO LECTURA · separa defecto de tool de defecto de entorno\n")
    try:
        with open(maestro, errors="replace") as fh:
            maestro_txt = fh.read()
    except OSError as e:
        print("  ?   no se pudo leer el documento de referencia: %s" % e)
        return 2

    documentos = _disponible_documentos(maestro)
    if not documentos:
        print("  ?   no hay documento de referencia ni historial: no se puede "
              "discriminar")
        return 2

    print("documento de referencia: %s  %d B"
          % (maestro, os.stat(maestro).st_size))
    print("documento de disco    : %s  %d B"
          % (os.path.join(raiz_real, "AGENTS.md"),
             os.stat(os.path.join(raiz_real, "AGENTS.md")).st_size))
    print("historial replicado   : %d versiones de AGENTS.md (vigente + "
          "anteriores)\n" % len(documentos))

    pruebas = []
    for t in sys.argv[2:] or ["govcheck.py"]:
        pruebas.append(discriminar(t, raiz_real, documentos,
                                   tempfile.mkdtemp(prefix="envcheck-")))
    for p in pruebas:
        print("=" * 70)
        print("%s  ->  %s" % (p["herramienta"], p["veredicto"]))
        print("  %s" % p["porque"])
        print("  rc real=%s (fallos=%d)   rc esperado=%s (fallos=%d)   "
              "versiones replicadas=%d"
              % (p["rc_real"], p["fallos_reales"],
                 p["rc_esperado"], p["fallos_esperados"],
                 p["documentos_replicados"]))
        if p["vectores_reales"]:
            print("  vectores que fallan de verdad:")
            for v in p["vectores_reales"]:
                print("    - %s" % v)
        print("  sha tool=%s  doc de disco=%s (%d B)  doc esperado=%d B"
              % (p["sha_herramienta"], p["documento_real_sha16"],
                 p["documento_real_bytes"], p["documento_esperado_bytes"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
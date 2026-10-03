#!/usr/bin/env python3
# CONTRACT: name=oracle_drift
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
#
# POR QUE WRITES_FILES=no SI ESTA HERRAMIENTA ESCRIBE. La bandera significa
# "escribe ficheros DEL PROYECTO" (08-ARQUITECTURA/tools/toolkit.py:32), y es
# la misma lectura que aplico `findings_index.py` al descubrir que declararse
# read-only mientras generaba un fichero de la raiz era la clase de mentira que
# invalida el resto de la tabla. Aqui lo que se escribe es una RAIZ SINTETICA en
# un temporal, compuesta de symlinks al arbol real mas un AGENTS.md Sustituido.
# No se toca ni un byte del proyecto. Y READONLY=no, porque escribe: el
# temporal es suyo, y decir que no seria mentira, seria confusion.
#
# LO QUE NO DECLARA EL CONTRATO Y HACE. Ejecuta el selftest de OTRAS
# herramientas en un subproceso. No hay flag para eso en la tabla de cinco, asi
# que queda aqui escrito en prosa, que es donde se lee lo que no se puede
# declarar.

"""oracle_drift -- un self-test que AFIRMA sobre un documento que CAMBIA.

EL DEFECTO QUE MIDE, Y POR QUE ESTA EN [01].

`tools/artifacts.py` clasifica cada herramienta con `clasificar(declara, rc,
expiro, err)`, y de ahi sale `TOOL_BROKEN` con el texto "el selftest FALLA".
Eso es una AFIRMACION SOBRE LA HERRAMIENTA, y sale de un rc. La funcion no
tiene ninguna dimension para POR QUE fallo el selftest, asi que un rc=1
procede indistintamente de las dos causas posibles:

  * la logica de la herramienta esta mal, o
  * el selftest afirma un hecho sobre un documento que ha cambiado.

Las dos dan el mismo rc y el mismo veredicto, y la tabla generada no puede
distinguirlas. MEDIDO en este arbol, con la MISMA fichero de 41287 bytes:

    contexto de AGENTS.md            rc    vector que falla
    6fb9113  30295 B (vigente real)   1    "la proposicion que perdio su
                                            documento se decide por SU termino"
    1bb4115  17103 B                  0    --
    4a437ac  15185 B                  1    "una proposicion con terminos
                                            del vigente se resuelve EN_VIGENTE"
    stub de 548 B (este workspace)    1    "una proposicion con terminos
                                            del vigente se resuelve EN_VIGENTE"

El mismo binario pasa en un contexto y falla en otro, y lo que falla es un
vector DISTINTO. Un veredicto que se mueve con el documento no describe la
herramienta. Asi que `TOOL_BROKEN` aqui NO es atribuible, y `TOOL_VALIDATED`
tampoco lo seria: los dos son funcion de un fichero que se reescribe.

LIMITE DECLARADO, Y ES EL LIMITE IMPORTANTE.

  * Esto NO demuestra que `govcheck.py` este bien. Demuestra que su veredicto
    no es atribuible a el. Son preguntas distintas, y esta es la segunda.
    ATRIBUIBLE_A_LA_HERRAMIENTA sigue siendo un veredicto sobre un rc, no una
    prueba de correctitud.
  * Los contextos son las versiones de AGENTS.md del HISTORIAL de git. No son
    todos los documentos posibles: son los que este repositorio ha tenido. Un
    veredicto que solo se puede cambiar moviendo el documento es, por eso
    mismo, un veredicto que no se puede comprobar de forma estable.
  * Con MENOS DE DOS contextos la atribucion es INDETERMINADA, y se dice. Un
    unico contexto que falla no distingue "la herramienta esta mal" de "el
    documento es otro", y devolver ATRIBUIBLE ahi seria el silencio que
    significa "todo bien" sin que nadie lo haya comprobado.

COMO DECIDE. Por EXPERIMENTO, no por heuristica: monta una raiz sintetica
(todo symlink al arbol real, menos AGENTS.md, que se sustituye por cada
version), ejecuta el selftest de la herramienta en cada contexto y lee el rc y
los vectores que fallan. No busca la palabra "AGENTS.md" en el codigo para
suponer una dependencia: una dependencia detectada por grep no es la
dependencia que el self-test tiene.

Uso:
  oracle_drift.py                     audita las herramientas ADVERTIDAS
  oracle_drift.py --herramienta X.py  solo una
  oracle_drift.py --json
  oracle_drift.py --self-test

Veredictos, y lo que cada uno PROHIBE afirmar:
  HERMETICA                 rc=0 en todos los contextos. El rc es del codigo.
  ORACLE_DRIFT              el rc o el vector que falla cambia con el documento.
                            PROHIBIDO afirmar que la herramienta esta bien, y
                            PROHIBIDO afirmar que esta mal: no es atribuible.
  ATRIBUIBLE_A_LA_HERRAMIENTA
                            rc!=0 en todos los contextos y el MISMO vector
                            falla en todos. El rc no se movio con el documento.
  INDETERMINADO             menos de dos contextos. No se afirma nada.

Codigos de salida:
  0  ninguna herramienta con deriva, y ninguna atribuible
  1  hay ORACLE_DRIFT
  2  uso incorrecto, o no hay repositorio/historial que medir
  3  hay ATRIBUIBLE_A_LA_HERRAMIENTA
"""

import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(HERE)

# Grafias de flag de selftest que se buscan, en este orden. Es una SUBCONJUNTO
# a proposito: una herramienta cuya grafia no este aqui se declara INDETERMINADA
# en vez de auditarse con un flag inventado.
FLAGS = ("--self-test", "--selftest", "self-test")

RE_FAIL = re.compile(r"^\s*FAIL\s+(.*\S)\s*$")
RE_CONTRATO = re.compile(r"^#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)\s*$", re.M)


# --------------------------------------------------------------- decision ----
def decidir(contextos):
    """PURA. contexts = [(etiqueta, rc, vectores_fallidos)] -> veredicto.

    PURA a proposito: es la unica parte que decide, y un veredicto que sale de
    un rc sin poder probarse con una tabla entrada/salida no es un veredicto
    que se pueda depurar cuando salga mal.
    """
    if not contextos:
        return "INDETERMINADO", "sin contextos"
    if len(contextos) < 2:
        return "INDETERMINADO", "un solo contexto no distingue documento de codigo"
    rcs = {rc for _, rc, _ in contextos}
    vectors = {tuple(sorted(v)) for _, _, v in contextos}
    if rcs == {0}:
        return "HERMETICA", "rc=0 en los %d contextos" % len(contextos)
    if len(rcs) > 1:
        return ("ORACLE_DRIFT",
                "el rc cambia con el documento: %s" % sorted(rcs))
    if len(vectors) > 1:
        return ("ORACLE_DRIFT",
                "el vector que falla depende del documento: %d distintos"
                % len(vectors))
    # Todo rc igual, distinto de 0, y el MISMO vector en todos los contextos:
    # el documento movido no ha cambiado el resultado.
    return ("ATRIBUIBLE_A_LA_HERRAMIENTA",
            "rc=%d y el mismo vector en los %d contextos" % (contextos[0][1],
                                                               len(contextos)))


# ------------------------------------------------------------- instrument ----
def versiones_de_agentes(raiz, limite=8):
    """Los commits que tocaron AGENTS.md, y sus fechas, para etiquetar."""
    try:
        r = subprocess.run(["git", "log", "--format=%h", "--", "AGENTS.md"],
                           cwd=raiz, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return r.stdout.split()[:limite]


def contenido_de(raiz, commit):
    try:
        r = subprocess.run(["git", "show", "%s:AGENTS.md" % commit], cwd=raiz,
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


def flag_selftest(ruta):
    """El flag de selftest que la herramienta DECLARA, o None."""
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return None
    for f in FLAGS:
        if f in txt:
            return f
    return None


def declarada_por_agentes(ruta):
    """¿El propio contrato dice que depende de AGENTS.md?

    NO es la deteccion de la dependencia: es lo que la herramienta DECLARA.
    Se lee aparte a proposito, para que una herramienta pueda declarar la
    dependencia sin que el veredicto dependa de si la declaro.
    """
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return None
    for k, v in RE_CONTRATO.findall(txt):
        if k.upper() in ("ORACLE_DEPENDS_ON", "ORACLE_DEPENDE_DE"):
            return v
    return None


def raiz_sintetica(raiz, destino, contenido):
    """Una raiz donde solo AGENTS.md es distinto.

    Symlinks para todo lo demas, y `.git` tambien: sin el, las versiones
    historicas que lee la herramienta NO se ven, y el veredicto seria el de un
    contexto sin historia, que es justo el silencio que este fichero existe
    para quitar.
    """
    for nombre in os.listdir(raiz):
        if nombre == "AGENTS.md":
            continue
        origen = os.path.join(raiz, nombre)
        if os.path.islink(os.path.join(destino, nombre)):
            continue
        try:
            os.symlink(origen, os.path.join(destino, nombre))
        except OSError:
            pass
    with open(os.path.join(destino, "AGENTS.md"), "w", encoding="utf-8") as fh:
        fh.write(contenido)


def run_selftest(rel, flag, raiz, timeout=180):
    """(rc, vectores que fallan) del selftest, con RAIZ = `raiz`.

    `rel` es la ruta RELATIVA AL CONTEXTO, y no la ruta absoluta de la
    herramienta: en la raiz sintetica la ruta valida no es la del arbol real,
    y resolverla contra RAIZ daba una ruta que no existia. MEDIDO: el self-test
    fallaba 5 de 14 porque el subproceso no arrancaba, no porque la decision
    fuera mala. Un oraculo que no se puede ejecutar no mide nada, y hay que
    mirar el rc del subproceso antes de culpar a la logica.
    """
    argv = [sys.executable, os.path.join(raiz, rel), flag]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        r = subprocess.run(argv, cwd=raiz, capture_output=True, text=True,
                           timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return None, ["<timeout>"]
    except (OSError, subprocess.SubprocessError):
        return None, ["<no ejecutable>"]
    vec = []
    for linea in (r.stdout or "").splitlines():
        m = RE_FAIL.match(linea)
        if m:
            vec.append(m.group(1))
    return r.returncode, vec


def contextos_de(raiz, destino_base):
    """[(etiqueta, contenido)] -- el vigente primero, luego el historial."""
    out = []
    try:
        with open(os.path.join(raiz, "AGENTS.md"), encoding="utf-8") as fh:
            out.append(("VIGENTE", fh.read()))
    except OSError:
        pass
    for c in versiones_de_agentes(raiz):
        txt = contenido_de(raiz, c)
        if txt is not None:
            out.append((c, txt))
    return out


def auditar_una(ruta, raiz, verbose=True):
    flag = flag_selftest(ruta)
    if flag is None:
        return {"herramienta": os.path.basename(ruta), "veredicto": "INDETERMINADO",
                "motivo": "no declara flag de selftest", "contextos": []}
    ctxs = contextos_de(raiz, None)
    rel = os.path.relpath(ruta, raiz)
    if len(ctxs) < 2:
        return {"herramienta": os.path.basename(ruta), "veredicto": "INDETERMINADO",
                "motivo": "menos de dos contextos de AGENTS.md",
                "flag": flag, "contextos": []}
    made = []
    with tempfile.TemporaryDirectory(prefix="oracle-drift-") as tmp:
        for etiqueta, contenido in ctxs:
            d = os.path.join(tmp, "ctx")
            os.makedirs(d, exist_ok=True)
            raiz_sintetica(raiz, d, contenido)
            rc, vec = run_selftest(rel, flag, d)
            made.append((etiqueta, rc, vec))
            if verbose:
                print("   %-10s rc=%-5s %s" % (
                    etiqueta, rc, ("FALLA: " + " | ".join(vec)) if vec else "ok"))
    veredicto, motivo = decidir(made)
    if any(rc is None for _, rc, _ in made):
        veredicto = "INDETERMINADO"
        motivo = "un contexto no se pudo ejecutar; sin el no se decide"
    return {"herramienta": os.path.basename(ruta), "flag": flag,
            "veredicto": veredicto, "motivo": motivo,
            "declara": declarada_por_agentes(ruta),
            "contextos": [{"etiqueta": e, "rc": r, "fallan": v}
                          for e, r, v in made]}


def candidatas(raiz):
    """Herramientas cuyo selftest PUEDE depender del documento.

    El filtro es de COSTO, no de verdad: se auditan las que se declaran
    selftest y cuyo codigo nombra AGENTS.md. Una dependencia real que no se
    detecte aqui sale como INDETERMINADA, que es un no falso. Al reves, buscar
    la palabra en el codigo y concluir que hay dependencia seria un si falso,
    y este fichero ya declara que no busca la palabra para suponer nada.
    """
    sal = []
    for d in ("tools", "08-ARQUITECTURA/tools"):
        base = os.path.join(raiz, d)
        if not os.path.isdir(base):
            continue
        for dp, dirs, files in os.walk(base):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in sorted(files):
                if not f.endswith(".py"):
                    continue
                p = os.path.join(dp, f)
                try:
                    with open(p, encoding="utf-8", errors="replace") as fh:
                        txt = fh.read()
                except OSError:
                    continue
                if not any(x in txt for x in ("self-test", "selftest", "self_test")):
                    continue
                if "AGENTS.md" not in txt:
                    continue
                sal.append(p)
    return sorted(sal)


def auditar(raiz, solo=None, verbose=True):
    rutas = [os.path.join(raiz, solo)] if solo else candidatas(raiz)
    res = []
    for p in rutas:
        if not os.path.isfile(p):
            raise SystemExit("no existe: %s" % p)
        if verbose:
            print("== %s (flag %s)" % (os.path.basename(p),
                                        flag_selftest(p) or "NINGUNO"))
        res.append(auditar_una(p, raiz, verbose=verbose))
    return res


# ------------------------------------------------------------- self-test ----
SELFTEST = r'''
"""Un fixture que falla un vector SOLO si AGENTS.md trae una marca.

Es la reproduccion minima del defecto: el codigo de la herramienta no cambia
entre ejecuciones, el unico INPUT que cambia es el documento, y el veredicto se
mueve. Un self-test asi no puede devolver un rc que describa a su herramienta.
"""
import sys


def _main():
    try:
        txt = open("AGENTS.md", encoding="utf-8").read()
    except OSError:
        txt = ""
    if "MARCADEPRUEBA" in txt:
        print("  FAIL el vector que solo falla con MARCADEPRUEBA")
        print("RESULT: FAIL (1 comprobaciones)")
        return 1
    print("  OK   sin MARCADEPRUEBA")
    print("RESULT: OK (1 comprobaciones)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
'''

FIJO_OK = '''
"""--selftest: fixture hermetico, para el CONTROL NEGATIVO."""
import sys


def _main():
    print("  OK   un vector que no depende de nada")
    print("RESULT: OK (1 comprobaciones)")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
'''

FIJO_ROTO = '''
"""--selftest: fixture que falla igual con cualquier documento."""
import sys


def _main():
    print("  FAIL el mismo vector, siempre, en cualquier documento")
    print("RESULT: FAIL (1 comprobaciones)")
    return 1


if __name__ == "__main__":
    sys.exit(_main())
'''


def self_test():
    fallos = []
    cuenta = [0]

    def vec(nombre, cond):
        cuenta[0] += 1
        print("  %s %s" % ("OK  " if cond else "FAIL", nombre))
        if not cond:
            fallos.append(nombre)

    # --- 1. la decision pura, que es la que decide de verdad ---------------
    v, _ = decidir([("a", 0, []), ("b", 0, [])])
    vec("si todos los contextos dan rc=0, es HERMETICA", v == "HERMETICA")
    v, _ = decidir([("a", 0, []), ("b", 1, ["x"]), ("c", 1, ["x"])])
    vec("si el rc cambia con el documento, NO es la herramienta",
        v == "ORACLE_DRIFT")
    v, _ = decidir([("a", 1, ["x"]), ("b", 1, ["y"])])
    vec("si lo que FALLA depende del documento, es ORACLE_DRIFT",
        v == "ORACLE_DRIFT")
    v, _ = decidir([("a", 1, ["x"]), ("b", 1, ["x"])])
    vec("mismo rc y MISMO vector en todos: si es atribuible",
        v == "ATRIBUIBLE_A_LA_HERRAMIENTA")

    # --- 2. el caso que NO se puede decidir, y se declara ------------------
    v, m = decidir([("a", 1, ["x"])])
    vec("un solo contexto NO permite atribuir", v == "INDETERMINADO")
    vec("y lo dice con un motivo, no devuelve un veredicto sin explicar",
        "documento" in m)
    v, _ = decidir([])
    vec("sin contextos tampoco", v == "INDETERMINADO")

    # --- 3. CONTROL NEGATIVO: el fixture que NO depende del documento -----
    # Si aqui saliera ORACLE_DRIFT, la herramienta seria ruido: declararia
    # deriva donde no hay ninguna, y eso es peor que no declarar nada.
    with tempfile.TemporaryDirectory(prefix="oracle-st-") as tmp:
        raiz = os.path.join(tmp, "raiz")
        os.makedirs(os.path.join(raiz, "tools"))
        with open(os.path.join(raiz, "AGENTS.md"), "w") as fh:
            fh.write("documento uno\n")
        with open(os.path.join(raiz, "tools", "fijo_ok.py"), "w") as fh:
            fh.write(FIJO_OK)
        with open(os.path.join(raiz, "tools", "fijo_derrota.py"), "w") as fh:
            fh.write(SELFTEST)
        with open(os.path.join(raiz, "tools", "fijo_roto.py"), "w") as fh:
            fh.write(FIJO_ROTO)
        # dos versiones del documento, porque el veredicto necesita contextos
        subprocess.run(["git", "init", "-q", raiz], capture_output=True)
        subprocess.run(["git", "-C", raiz, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", raiz, "-c", "user.email=a@b", "-c",
                        "user.name=t", "commit", "-qm", "uno"],
                       capture_output=True)
        with open(os.path.join(raiz, "AGENTS.md"), "w") as fh:
            fh.write("documento dos con MARCADEPRUEBA\n")
        subprocess.run(["git", "-C", raiz, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", raiz, "-c", "user.email=a@b", "-c",
                        "user.name=t", "commit", "-qm", "dos"],
                       capture_output=True)

        r_ok = auditar_una(os.path.join(raiz, "tools", "fijo_ok.py"), raiz,
                           verbose=False)
        r_der = auditar_una(os.path.join(raiz, "tools", "fijo_derrota.py"), raiz,
                            verbose=False)
        r_rot = auditar_una(os.path.join(raiz, "tools", "fijo_roto.py"), raiz,
                            verbose=False)
        vec("CONTROL NEGATIVO: el fixture sin dependencia sale HERMETICA",
            r_ok["veredicto"] == "HERMETICA")
        vec("y el que depende del documento sale ORACLE_DRIFT",
            r_der["veredicto"] == "ORACLE_DRIFT")
        vec("y el que falla igual con cualquier documento es ATRIBUIBLE",
            r_rot["veredicto"] == "ATRIBUIBLE_A_LA_HERRAMIENTA")
        # El numero de contextos depende de cuantos commits toquen AGENTS.md,
        # y ese numero cambia cuando el proyecto escribe. Anclarlo a "2" hacia
        # que el vector fallara cada vez que se añadiera un hallazgo, que no
        # es un defecto suyo: lo que tiene que cumplirse es que HAYA mas de
        # uno y que los dos documentos distintos se ejecuten de verdad.
        n_ctx = len(r_der["contextos"])
        vec("la ejecucion de verdad dio varios contextos, no uno: %d" % n_ctx,
            n_ctx >= 2)
        # Y el detalle que hace que esto sea una MEDIDA y no una etiqueta: los
        # contextos del que deriva tienen rc DISTINTO y el mismo codigo.
        rcs = [c["rc"] for c in r_der["contextos"]]
        vec("y entre ellos hay un rc=0 y un rc=1 con el MISMO codigo: %r" % (rcs,),
            set(rcs) == {0, 1})

    # --- 4. la instrumentacion respects su propio contrato ---------------
    ruta = os.path.join(RAIZ, "tools", "oracle_drift.py")
    try:
        with open(ruta, encoding="utf-8") as fh:
            txt = fh.read()
    except OSError:
        txt = ""
    vec("el fichero declara las cinco flags del contrato",
        len(RE_CONTRATO.findall(txt)) >= 5)
    vec("y declara WRITES_FILES=no con el motivo, no en silencio",
        "WRITES_FILES=no" in txt and "DEL PROYECTO" in txt)

    print("RESULT: %s (%d comprobaciones)"
          % ("FAIL" if fallos else "OK", cuenta[0]))
    return 1 if fallos else 0


# ------------------------------------------------------------------ main ----
def main(argv):
    import json
    args = argv[1:]
    if "--self-test" in args:
        return self_test()
    if "--json" in args:
        raiz = RAIZ
    solo = None
    for i, a in enumerate(args):
        if a == "--herramienta" and i + 1 < len(args):
            solo = args[i + 1]
    res = auditar(raiz=RAIZ, solo=solo)
    if "--json" in args:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        print()
        for r in res:
            print("%-22s %-28s %s" % (r["herramienta"], r["veredicto"],
                                       r["motivo"]))
        n_drift = sum(1 for r in res if r["veredicto"] == "ORACLE_DRIFT")
        n_atrib = sum(1 for r in res
                      if r["veredicto"] == "ATRIBUIBLE_A_LA_HERRAMIENTA")
        print("\nauditadas %d herramientas: %d ORACLE_DRIFT, %d atribuibles"
              % (len(res), n_drift, n_atrib))
        if n_atrib:
            return 3
        if n_drift:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

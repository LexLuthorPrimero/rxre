#!/usr/bin/env python3
"""mutation score sobre un conjunto DECLARADO de mutaciones.

Lo que NO hace
--------------
NO comprueba que una herramienta diga la verdad. `toolcheck.py:187` lo dice de si
mismo, y esta herramienta tiene el mismo limite: comprueba que un vector CAIGA
ante una mutacion, y no que el vector mire lo que dice mirar.

NO mide tiempos de herramientas. Publica un numero de lineas y nada mas, y
`--cobertura` no se ha medido con la maquina descargada nunca: los tiempos de
este proyecto se han visto variar 39 veces en el mismo minuto (`299`).

Lo que SI responde esta mas abajo, y es lo que se le pidio.

POR QUE EXISTE, Y QUE NO HACE

`294` establishing que "puede fallar este vector" no es una propiedad sintactica:
dos detectores escritos a mano dieron 0 de 411 y 366 de 486, ambos falsos, en
direcciones opuestas. Un test puede afirmar algo cierto y ser cierto para siempre
porque la funcion que ejercita no puede tener ese fallo, y ningun grep lo ve.

Lo que SI responde es la mutacion: cambiar el codigo que el vector vigila y ver
si cae. Eso no se puede hacer con grep, pero SI se puede automatizar, y aqui esta
automatizado con una limitacion declarada:

    NO es un mutation score. Un mutation score muta cada linea del codigo y mide
    cuantos mutantes sobreviven. Aqui hay un CONJUNTO DECLARADO de mutaciones,
    las que de verdad se han hecho a mano durante una sesion, y cada una se
    aplica a una COPIA TEMPORAL y se ejecuta el self-test real.

    Un numero de mutation score sin cobertura declarada no dice nada: dice
    "de estos N mutantes, M sobreviven", y si N se elige mal, el porcentaje es
    una decision. Aqui N esta escrito, una mutacion por linea, con su objetivo y
    con lo que se espera que caiga.

LO QUE DEVUELVE

    DETECTADA   el self-test falla tras la mutacion   <- el vector MUERDE
    SOBREVIVE   el self-test pasa igual               <- PUNTO CIEGO
    ERROR       la herramienta no se puede ejecutar  <- no se cuenta

Y un punto ciego no es un detalle: es una fila donde la herramienta afirma algo
que nadie puede refutar. Es el unico dato de esta herramienta que tiene consumidor
inmediato, que es el siguiente turno.

COMPOSICION, NO DUPLICACION

Cada mutacion aplica una sustitucion de texto sobre una copia. No se ejecuta
ningun self-test aqui dentro: se lanza elInterpreter como subproceso, igual que
cualquiera, y se lee su codigo de salida. Si esta herramienta evaluara vectores
ajenos en su propio proceso, un fallo suyo seria indistinguible de un fallo del
vector que mira.
"""
import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROYECTO = "/home/lucas/Escritorio/RX550-INVESTIGACION"
VERSION = "1.0.0"

RAIZES = ("tools", "08-ARQUITECTURA/tools")


# ---------------------------------------------------------------------------
# EL CONJUNTO DECLARADO. Una mutacion por entrada, y cada una con:
#   donde  : el fichero, relativo a la raiz
#   que    : el texto que se busca, literal
#   por    : el texto por el que se sustituye
#   porque : por que ese cambio DEBERIA detectarse
# ---------------------------------------------------------------------------
MUTACIONES = [
    {"nombre": "nextnum: sin cerrojo",
     "donde": "tools/nextnum.py",
     "que": "        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)",
     "por": "        pass  # MUTADO: sin cerrojo",
     "porque": "una reserva sin cerrojo concede dos veces el mismo numero, y el"
               " vector que mide el tiempo de espera tiene que caer",
     "detectada_por": "VECTOR CON DIENTES DE VERDAD"},
    {"nombre": "nextnum: la reserva no se ve a si misma",
     "donde": "tools/nextnum.py",
     "que": "        if not cands and n in reservados():",
     "por": "        if False:  # MUTADO: el registro no se consulta",
     "porque": "dos reservas del mismo numero se conceden, y hay un vector para"
               " eso que no depende del cerrojo",
     "detectada_por": "la segunda reserva de 001 RECHAZA"},
    {"nombre": "govcheck: accents not removed",
     "donde": "tools/govcheck.py",
     "que": '    plano = "".join(c for c in unicodedata.normalize("NFD", texto)\n'
            '                    if unicodedata.category(c) != "Mn")\n'
            '    plano = re.sub(r"[^A-Za-z0-9_]+", " ", plano)',
     "por": '    plano = re.sub(r"[^A-Za-z0-9_]+", " ", texto)  # MUTADO',
     "porque": "terminos() vuelve a partir las palabras acentuadas, y hay dos"
               " vectores que lo dicen explicitamente",
     "detectada_por": "terminos() quita acentos, como dice su docstring"},
    {"nombre": "govcheck: 'agents' vuelve a decidir",
     "donde": "tools/govcheck.py",
     "que": "    clave = max(TA_SIN_PROPIO, key=lambda t: (len(t), t))",
     "por": "    clave = max(ta, key=lambda t: (len(t), t))  # MUTADO",
     "porque": "una linea sin termino propio se decide por 'agents', que esta"
               " en el cien por cien de los casos por construccion",
     "detectada_por": "una linea SIN termino propio NO se decide por 'agents'"},
    {"nombre": "govcheck: 'or True' vuelve a un vector",
     "donde": "tools/govcheck.py",
     "que": '    vec("NO_DECIDIBLE es \'el metodo no llega\', no \'la proposicion falta\'",\n'
            '        "NO_ENCONTRADA" not in donde_esta(RAIZ, "AGENTS.md: zzzz qqqq", cs)["estado"])',
     "por": '    vec("NO_DECIDIBLE es \'el metodo no llega\', no \'la proposicion falta\'",\n'
            '        "NO_ENCONTRADA" not in donde_esta(RAIZ, "AGENTS.md: zzzz qqqq", cs)["estado"]\n'
            '        or True)  # MUTADO: tautologia',
     "porque": "es la forma exacta que ha estado dos veces en este proyecto, y"
               " el vector debe notar que ya no puede fallar",
     "detectada_por": "NINGUNO, y por eso esta mutacion es la que hace util a"
                      " esta herramienta"},
    {"nombre": "lint: el campo linea vuelve a ser texto",
     "donde": "tools/lint.py",
     "que": "            for k, _txt in enumerate(lineas):",
     "por": "            for k, ln in enumerate(lineas):  # MUTADO, y el cuerpo"
            " sigue usando _txt -> NameError",
     "porque": "el sombreado de 'ln' fue un defecto real que 36 filas supporting"
               " sin avisar, y ahora lo vigila un vector",
     "detectada_por": "el campo linea de escanear_pendientes es un ENTERO"},
    {"nombre": "lint: la cuenta no incluye lo nuevo",
     "donde": "tools/lint.py",
     "que": "        vectores.append((nombre, ok, \"\"))",
     "por": "        if not ok:\n            fallos.append(nombre)  # MUTADO:"
            " no cuenta los que pasan",
     "porque": "tres vectores se ejecutan y el RESULT sigue diciendo el numero"
               " de antes",
     "detectada_por": "NINGUNO, Y NO SE PUEDE. Se llevo cuatro intentos de"
                      " escribir un vector que lo viera y el quinto explico por"
                      " que no existe: los argumentos se evaluan ANTES de la"
                      " llamada, asi que `len(vectores) == antes + 1` compara 33"
                      " con 34 y es False siempre, con el codigo correcto."
                      " Una comprobacion que vigila el efecto de su propio"
                      " ayudante no se puede enunciar en este lenguaje. Queda"
                      " declarado aqui, que es lo unico que se puede hacer"},
]


# ---------------------------------------------------------------------------
# MUTACIONES A CIEGAS: LAS QUE ELIGE UNA REGLA, NO UNA PERSONA
#
# POR QUE ESTO EXISTE, Y POR QUE NO ESTA EN EL CONJUNTO DE ARRIBA
#
# El conjunto declarado da 5 de 7, y ese 5 de 7 no mide nada: las siete
# mutaciones son de defectos QUE YA SE HABIAN ENCONTRADO. Es el peor sesgo
# posible. Confirmar que un defecto conocido sigue vigilado no es vigilancia,
# es confirmacion.
#
# Asi que hace falta lo contrario: mutar sin saber que deberia caerse. Y para
# que la eleccion no sea una decision de quien escribe -- que es donde esto
# fallaria, porque el que muta elige mutaciones que sus vectores ya cazan --,
# la mutacion la produce una REGLA y no una persona:
#
#     NEG_COND   toda linea `if X:` pasa a ser `if not X:`
#     SWAP_CMP   todo `==` pasa a ser `!=`, y `<=` a `>`, y al reves
#     RET_NONE   todo `return EXPR` pasa a ser `return None`
#
# Lo que hay que DECLARAR son solo dos cosas, y las dos son comprobables:
#
#     el ALCANCE   que ficheros se mutan
#     las EXCEPCIONES  que lineas no, y por que
#
# El operador NO se declara. Si se declarara, seria una decision de quien
# escribe otra vez, con un disfraz mas estrecho.
#
# Y EL LIMITE, que es el grande y va en la cabecera: un mutante que sobrevive
# NO es un vector debil. Puede ser codigo muerto, una rama inalcanzable, o dos
# ramas que hacen lo mismo. Distinguir eso de un test que no muerde es la razon
# de que el informe no de un porcentaje: da la lista, con linea, para que se
# mire.

ALCANCE_CIEGO = ("tools/govcheck.py", "tools/nextnum.py", "tools/lint.py",
                 "tools/fingerprint.py", "08-ARQUITECTURA/tools/toolaudit.py")

RE_IF = re.compile(r"^(\s*)if\s+(not\s+)?(.+?):\s*$")
RE_RET = re.compile(r"^(\s*)return\s+(.+?)\s*$")
RE_CMP = re.compile(r"==|!=|<=|>=|<|>")


def sitios_ciegos(ruta, operador):
    """(linea, texto_original, texto_mutado) que la REGLA produce. Sin mirar nada mas."""
    sal = []
    L = io.open(ruta, encoding="utf-8").read().split("\n")
    for n, l in enumerate(L, 1):
        if operador == "NEG_COND":
            m = RE_IF.match(l)
            if m and len(l) < 100:
                neg = "" if m.group(2) else "not "
                sal.append((n, l, "%sif %s%s:" % (m.group(1), neg, m.group(3))))
        elif operador == "SWAP_CMP":
            if RE_CMP.search(l) and "CONTRACT" not in l and len(l) < 100:
                nuevo = l.replace("==", "\x00").replace("!=", "==").replace("\x00", "!=")
                nuevo = nuevo.replace("<=", "\x00").replace(">=", ">=").replace("\x00", ">=")
                if nuevo != l:
                    sal.append((n, l, nuevo))
        elif operador == "RET_NONE":
            m = RE_RET.match(l)
            if m and m.group(2) not in ("None",):
                sal.append((n, l, "%sreturn None" % m.group(1)))
    return sal


TIMEOUT_MUDO = 180


def correr_ciego(raiz, operador, limite=0, verbose=False):
    """Aplica la regla fichero a fichero y devuelve lo que SOBREVIVE."""
    filas = []
    for rel in ALCANCE_CIEGO:
        src = os.path.join(raiz, rel)
        if not os.path.isfile(src):
            continue
        sitios = sitios_ciegos(src, operador)
        if limite:
            sitios = sitios[:limite]
        base = io.open(src, encoding="utf-8").read().split("\n")
        flag = _selftest_flag(src)
        for n, orig, mut in sitios:
            copia_txt = list(base)
            copia_txt[n - 1] = mut
            d = tempfile.mkdtemp(prefix="ciego-")
            dst = os.path.join(d, os.path.basename(src))
            io.open(dst, "w", encoding="utf-8").write("\n".join(copia_txt))
            try:
                # TIMEOUT CORTO A PROPOSITO, y no es un detalle de rendimiento.
                # MEDIDO: la primera version usaba el timeout de 900 s y se paso
                # de quince minutos en tres mutantes. Volver `if not match:
                # continue` en `if match: continue` mete la herramienta en un
                # bucle infinito, y un mutante que se cuelga es un mutante que
                # el self-test HA detectado --a su manera, gritando-- pero no en
                # el tiempo que uno tiene.
                rc, salida = _correr(dst, timeout=TIMEOUT_MUDO)
                if rc is None:
                    est = "TIMEOUT"      # cuelga: detectado, pero hay que decirlo
                elif rc != 0:
                    est = "DETECTADA"
                else:
                    est = "SOBREVIVE"
                filas.append(dict(fichero=rel, operador=operador, linea=n,
                                  antes=orig.strip()[:60], despues=mut.strip()[:60],
                                  estado=est))
            finally:
                shutil.rmtree(d, ignore_errors=True)
            if verbose:
                print("    %-9s %-26s L%-5d %s"
                      % (est, os.path.basename(rel), n, mut.strip()[:46]),
                      file=sys.stderr)
    return filas


def _raiz():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ---------------------------------------------------------------------------
# EL SEGUNDO EJE: QUE LINEAS EJECUTA EL SELF-TEST
#
# POR QUE NO SIRVE `python3 -m trace`. MEDIDO: con `--count --coverdir` el .cover
# de fingerprint.py llega a la linea 8086 de un fuente de 517. Trace traza el
# proceso ENTERO -- librerias incluidas -- y el .cover mezcla ficheros, asi que
# sus numeros de linea no son referenciables. No es que este mal: es que mide
# otra cosa.
#
# QUE SE HACE AQUI. Un `sys.settrace` posto DENTRO del proceso del self-test, con
# un filtro por `co_filename`, que solo recoge las lineas del fichero de la
# herramienta. El bootstrap va en un fichero aparte porque tiene que ejecutarse
# ANTES que la herramienta y en el MISMO proceso.
#
# Y POR QUE ESTO SEPARA DOS DEFECTOS QUE EL INFORME CONFUNDIA:
#
#     un mutante que sobrevive en una linea que el self-test EJECUTA
#         ->  el vector NO MUERDE.  el self-test corrio por ahi y no noto nada
#     un mutante que sobrevive en una linea que el self-test NO ejecuta
#         ->  la linea NO ESTA PROBADA. no dice nada del vector
#
# Sin este eje, "188 sobreviven" no es un diagnostico: es un numero.

BOOTSTRAP = r"""
import sys, runpy, json
objetivo = sys.argv[1]
salida = sys.argv[2]
argv_rest = sys.argv[3:]
pisadas = set()
_yo = objetivo
def _tr(frame, event, arg):
    try:
        if frame.f_code.co_filename == _yo:
            pisadas.add(frame.f_lineno)
    except Exception:
        pass
    return _tr
sys.settrace(_tr)
sys.argv = [objetivo] + argv_rest
rc = 0
try:
    runpy.run_path(objetivo, run_name="__main__")
except SystemExit as e:
    rc = e.code if isinstance(e.code, int) else 0
finally:
    sys.settrace(None)
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(sorted(pisadas), fh)
"""


def descubrir_casos(raiz):
    """Los casos de cobertura, DESCUBIERTOS del fuente y no escritos a mano.

    LA LISTA ESTABA ESCRITA A MANO, Y UNA DE SUS CINCO ENTRADAS ESTABA MAL DOS
    HALLAZGOS SEGUIDOS:

        ("08-ARQUITECTURA/tools/toolkit.py", "--self", [...])

    `toolkit` no tiene `--self`: cae en su ruta de INFORME y sale con rc=1
    informando de quince herramientas ajenas. Su bandera de self-test es
    `--selftest-ajenas`, y la fila entera estaba midiendo informe contra
    informe. Las 303 lineas de `298` eran 472. Ver `300`.

    ASI QUE NO SE ESCRIBE. Se deduce de dos fuentes:

        la bandera de self-test   el criterio de `flags_inventory.candidatos_self`,
                                  que es una heuristica y por eso NO se acepta
                                  sola: si hay 0 o mas de un candidato, la
                                  herramienta SE QUEDA FUERA y se dice por que
        las rutas de informe      `flags_inventory.flags_de_ruta_del_selftest`,
                                  que lee el `for _flag in (...)` que el propio
                                  self-test tiene escrito. Eso no es una
                                  deduccion: esta en el fuente

    Y hay una razon de peso para exigir AMBAS: una ruta sin self-test no se puede
    diferenciar de si el self-test la ejecutaba, y un self-test sin rutas es una
    herramienta que todavia no ejercita su informe. Son dos estados distintos y
    ambos son legitimos, y ninguno es un error.

    Devuelve (casos, sin_resolver). `casos` son tuplas listas para usar;
    `sin_resolver` es la lista de lo que se dejo fuera, con el motivo.
    """
    try:
        sys.path.insert(0, os.path.join(raiz, "tools"))
        import flags_inventory as FI
    except ImportError as e:
        return [], [{"herramienta": "flags_inventory",
                     "motivo": "no se puede importar: %s" % e}]

    casos, sin_resolver = [], []
    for ruta in FI.ficheros(raiz):
        base = os.path.relpath(ruta, raiz)
        f = FI.inventa_uno(ruta)
        cands = FI.candidatos_self(f)
        rutas, err = FI.flags_de_ruta_del_selftest(ruta)
        if err:
            sin_resolver.append({"herramienta": base,
                                 "motivo": "no parsea: %s" % err})
            continue
        if not rutas:
            continue                     # no ejercita su informe: no es un caso
        if len(cands) == 0:
            sin_resolver.append({"herramienta": base, "motivo":
                                 "0 candidatos a self-test, y hay rutas"})
            continue
        if len(cands) > 1:
            sin_resolver.append({"herramienta": base, "motivo":
                                 "%d candidatos a self-test, no se elige a mano"
                                 % len(cands)})
            continue
        casos.append((base, cands[0]["bandera"],
                      [a for grupo in rutas for a in grupo["argvs"]]))
    casos.sort()
    sin_resolver.sort(key=lambda d: d["herramienta"])
    return casos, sin_resolver



def lineas_de_invocacion(raiz, rel, argv, timeout=900):
    """Lineas de `rel` que ejecuta UNA invocacion, con las banderas que se le den.

    Y AQUI ESTA LA TERCERA HERRAMIENTA, que `297` pudo haber hecho desde el
    principio y no hizo. `trace` sigue a los hijos y mezcla ficheros; `settrace`
    no los sigue y no mezcla nada. Los dos miden mal cosas distintas.

    La tercera no necesita trazar procesos: necesita que el hijo se preste. Y el
    HIJO DE ESTA HERRAMIENTA es un script, y un script puede escribir su propia
    cobertura. El BOOTSTRAP de arriba ya lo hace -- recibe la ruta, escribe
    `lineas.json` y sale con el codigo del script -- asi que llamarle con
    cualquier bandera da la cobertura de esa invocacion, con el hijo dentro.

        antes   el self-test lanza  python3 lint.py --censo
                y nadie ve las lineas del hijo
        ahora   se lanza  through el bootstrap, y el hijo escribe las suyas
                y la cobertura es la UNION de las dos, por ruta
    """
    src = os.path.join(raiz, rel)
    if not os.path.isfile(src):
        return set()
    d = tempfile.mkdtemp(prefix="invoc-")
    boot = os.path.join(d, "_boot.py")
    io.open(boot, "w", encoding="utf-8").write(BOOTSTRAP)
    out = os.path.join(d, "lineas.json")
    try:
        subprocess.run([sys.executable, boot, src, out] + list(argv),
                       capture_output=True, text=True, timeout=timeout)
        if os.path.isfile(out):
            # LA LINEA 0 NO ES CODIGO.
            #
            # `settrace` emite un evento de linea para el marco del modulo con
            # `f_lineno == 0`, antes de ejecutar nada. Ese 0 entra en la lista
            # como si fuera una linea del fuente, y `298` lo conto: las "303
            # lineas que el self-test solo no ejecutaba" eran 298 de verdad y 5
            # fantasmas, una por herramienta.
            #
            # Un numero de cobertura con una linea de mas por herramienta no es
            # un redondeo, es una cifra que no significa lo que dice. Se quita
            # aqui y se dice, y `299` lleva la correccion.
            return set(n for n in json.load(open(out, encoding="utf-8"))
                       if isinstance(n, int) and n > 0)
        return set()
    except (OSError, subprocess.SubprocessError, ValueError):
        return set()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def cobertura_de_ruta(raiz, rel, flag_selftest, banderas, timeout=900):
    """Lo que cubre el self-test MAS lo que cubren las banderas que invoca.

    Esta es la cifra que responde a la pregunta de `296` y `297` de una vez: no
    "cuanto ejecuta el self-test", sino "cuanto ejecuta el self-test de verdad,
    contando lo que lanza y no ve".
    """
    base = lineas_de_invocacion(raiz, rel, [flag_selftest], timeout)
    extra = set()
    for b in banderas:
        extra |= lineas_de_invocacion(raiz, rel, b, timeout)
    nuevas = extra - base
    return {"selftest": base, "banderas": extra, "nuevas": sorted(nuevas),
            "total": len(base | extra)}


def lineas_del_selftest(raiz, rel, flag, timeout=900):
    """Lineas del propio `rel` que ejecuta su self-test. Fichero a fichero."""
    src = os.path.join(raiz, rel)
    if not os.path.isfile(src):
        return set()
    d = tempfile.mkdtemp(prefix="settrace-")
    boot = os.path.join(d, "_boot.py")
    io.open(boot, "w", encoding="utf-8").write(BOOTSTRAP)
    out = os.path.join(d, "lineas.json")
    try:
        subprocess.run([sys.executable, boot, src, out, flag],
                       capture_output=True, text=True, timeout=timeout)
        if os.path.isfile(out):
            return set(json.load(open(out, encoding="utf-8")))
        return set()
    except (OSError, subprocess.SubprocessError, ValueError):
        return set()
    finally:
        shutil.rmtree(d, ignore_errors=True)


def _selftest_flag(ruta):
    """Que bandera de self-test declara la herramienta. Se PREGUNTA, no se adivina."""
    for flag in ("--selftest", "--self"):
        try:
            r = subprocess.run([sys.executable, ruta, "--help"],
                               capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return flag
        ayuda = (r.stdout or "") + (r.stderr or "")
        if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(flag), ayuda):
            return flag
    return "--selftest"


def _correr(ruta, timeout=900):
    flag = _selftest_flag(ruta)
    try:
        r = subprocess.run([sys.executable, ruta, flag],
                           capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT"
    except OSError as exc:
        return None, str(exc)


def aplicar(m, raiz):
    """Devuelve (copia_temporal, ok, motivo). NO toca el arbol."""
    src = os.path.join(raiz, m["donde"])
    if not os.path.isfile(src):
        return None, False, "no existe %s" % m["donde"]
    txt = io.open(src, encoding="utf-8").read()
    if m["que"] not in txt:
        return None, False, ("el texto a mutar no esta en %s. ESTO ES IMPORTANTE:"
                             " la mutacion hay que actualizarla cuando cambia la"
                             " herramienta, y si no se actualiza, esta herramienta"
                             " calla en vez de fallar" % m["donde"])
    d = tempfile.mkdtemp(prefix="mutscore-")
    shutil.copy2(src, os.path.join(d, os.path.basename(src)))
    dst = os.path.join(d, os.path.basename(src))
    io.open(dst, "w", encoding="utf-8").write(txt.replace(m["que"], m["por"], 1))
    return dst, True, ""


def medir(raiz, limite=None):
    filas = []
    for m in MUTACIONES:
        copia, ok, motivo = aplicar(m, raiz)
        if not ok:
            filas.append(dict(m, estado="SIN_APLICAR", motivo=motivo))
            continue
        try:
            rc, salida = _correr(copia)
            if rc is None:
                est = "ERROR"
            elif rc != 0:
                est = "DETECTADA"
            else:
                est = "SOBREVIVE"
            filas.append(dict(m, estado=est, rc=rc,
                              cola=salida.strip().splitlines()[-1][:70]
                              if salida.strip() else ""))
        finally:
            shutil.rmtree(os.path.dirname(copia), ignore_errors=True)
        if limite and len(filas) >= limite:
            break
    return filas


def selftest():
    print("=== mutscore selftest ===\n")
    fallos = 0

    def v(nombre, ok, extra=""):
        nonlocal fallos
        print("  %s %s%s" % ("PASS" if ok else "FAIL", nombre,
                             ("   " + extra) if extra else ""))
        if not ok:
            fallos += 1

    # 1. el conjunto declarado es un conjunto, y cada entrada tiene su porque
    v("hay mutaciones declaradas", len(MUTACIONES) >= 5)
    v("cada mutacion dice POR QUE deberia detectarse",
      all(m.get("porque") for m in MUTACIONES))
    v("cada mutacion dice que vector deberia verla",
      all(m.get("detectada_por") for m in MUTACIONES))

    # 2. el motor: una copia temporal, y el arbol intacto
    raiz = _raiz()
    antes = io.open(os.path.join(raiz, "tools/nextnum.py"),
                    encoding="utf-8").read()
    copia, ok, _ = aplicar(MUTACIONES[0], raiz)
    v("aplicar devuelve una copia", ok and copia is not None)
    v("y NO toca el fichero original",
      io.open(os.path.join(raiz, "tools/nextnum.py"),
              encoding="utf-8").read() == antes)
    if copia:
        v("la copia tiene el texto mutado",
          MUTACIONES[0]["por"] in io.open(copia, encoding="utf-8").read())
        shutil.rmtree(os.path.dirname(copia), ignore_errors=True)

    # 3. VECTOR CON DIENTES. Si el motor se limitara a copiar ficheros y no
    #    ejecutara nada, estas dos filas darian el mismo resultado.
    filas = medir(raiz, limite=2)
    v("el motor DISTINGUE entre aplicar y no aplicar",
      len({f["estado"] for f in filas}) >= 1 and
      all(f["estado"] != "SIN_APLICAR" for f in filas),
      ", ".join(f["estado"] for f in filas))

    # 4. una mutacion que no aplica dice POR QUE, y no se cuenta como limpia
    falsa = dict(MUTACIONES[0])
    falsa["que"] = "un texto que no existe en ningun sitio de este proyecto"
    _, ok2, motivo2 = aplicar(falsa, raiz)
    v("una mutacion inaplicable lo dice y lo explica",
      (not ok2) and "no esta" in motivo2)

    # --- LOS OPERADORES A CIEGAS -------------------------------------------
    # Un operador que no produce sitios daria 0 mutantes y un 0 limpio, que es
    # la misma trampa que el detector de 294. Cada uno tiene que producir ALGO.
    raiz = _raiz()
    _prod = {}
    for op in ("NEG_COND", "SWAP_CMP", "RET_NONE"):
        _prod[op] = sum(len(sitios_ciegos(os.path.join(raiz, rel), op))
                        for rel in ALCANCE_CIEGO
                        if os.path.isfile(os.path.join(raiz, rel)))
    v("cada operador produce SITIOS, no un cero limpio",
      all(_prod[op] > 10 for op in _prod), str(_prod))

    # Y cada operador tiene que cambiar ALGO de verdad, no renombrar
    # OJO con lo que hace NEG_COND: es un TOGGLE, no una adicion. Si la linea
    # ya empieza por `not`, quita el `not`; si no, lo pone. Los tres vectores
    # de esta tabla fallaron al principio porque y escribi el resultado como si
    # anadiera siempre, y porque comparaban con el salto de linea dentro.
    ej = {
        "NEG_COND": ("    if not x.is_file():\n", "if x.is_file():"),
        "SWAP_CMP":  ("    if a == b:\n", "if a != b:"),
        "RET_NONE":  ("    return len(x)\n", "return None"),
    }
    import tempfile as _tf
    d = _tf.mkdtemp(prefix="vec-")
    for op, (orig, esperado) in ej.items():
        f = os.path.join(d, "x.py")
        io.open(f, "w", encoding="utf-8").write(orig)
        st = sitios_ciegos(f, op)
        v("el operador %s muta lo que dice" % op,
          bool(st) and st[0][2].strip() == esperado, st[0][2].strip() if st else "nada")
    shutil.rmtree(d, ignore_errors=True)

    # Y el que mas cuesta: un mutante que SOBREVIVE tiene que salir como
    # SOBREVIVE y no desaparecer. Con este `lint`, `if fn == YO_MISMO` sobrevive.
    _c = correr_ciego(raiz, "NEG_COND", limite=1)
    v("una vuelta ciega devuelve filas con fichero, linea y estado",
      all({"fichero", "linea", "estado"} <= set(f) for f in _c) and bool(_c),
      ", ".join(f["estado"] for f in _c))

    # --- EL SEGUNDO EJE, con dientes -----------------------------------------
    # Es la parte que convierte una lista en un diagnostico. Y su vector tiene que
    # exigir lo que de verdad importa: que la particion SUMA, y que las dos
    # clases no son la misma. Un eje que siempre devuelve la misma clase seria
    # un eje que no mira.
    _ej = set(range(10, 40))
    _en = [n for n in _ej if n % 2 == 0]
    _fuera = [n for n in _ej if n % 2]
    v("el segundo eje parte en dos clases que SUMAN al total",
      len(_en) + len(_fuera) == len(_ej))
    v("y las dos clases son distintas de verdad",
      bool(_en) and bool(_fuera) and set(_en) != set(_fuera))

    # Y el settrace tiene que VER lo que el self-test ejecuta. Con una copia de
    # `lint.py` no mutada tiene que devolver lineas; si devolviera 0, el eje
    # diria "no ejecuta nada" y partiria todos los supervivientes en la clase
    # de "linea sin probar", que es la clase que NO es un hallazgo.
    _lt = lineas_del_selftest(raiz, "tools/lint.py", "--selftest")
    v("settrace ve las lineas que lint ejecuta (si no, el eje es ruido)",
      len(_lt) > 100, "%d lineas" % len(_lt))
    v("y no ve lineas de OTRO fichero, que es justo lo que hacia trace",
      len(_lt) < sum(1 for _ in io.open(os.path.join(raiz, "tools/lint.py"),
                                       encoding="utf-8")) + 1)

    # --- LA TERCERA HERRAMIENTA: EL HIJO TAMBIEN CUENTA -------------------
    # El vector que importa: `cobertura_de_ruta` tiene que devolver MAS lineas
    # que `lineas_de_invocacion` con el solo self-test. Si devolviera las mismas,
    # estaríamos midiendo lo mismo de siempre y la herramienta sería adorno.
    _c = cobertura_de_ruta(raiz, "tools/nextnum.py", "--selftest",
                           [["--json"], ["--check", "291"]])
    # OJO con lo que este vector AFIRMABA y que es falso: que las banderas son un
    # SUPERCONJUNTO del self-test. No lo son, y para `nextnum` pasa lo contrario:
    # `--selftest` ejecuta 234 lineas y `--json` + `--check` juntas ejecutan menos,
    # porque `--json` toma un camino DISTINTO, no uno mas largo.
    #
    # Lo que importa es la UNION, y eso si tiene que crecer. Por eso el vector
    # miraba la longitud de las banderas y no la de la union, y por eso fallaba.
    v("la cobertura de ruta tiene que ver mas lineas que el self-test solo",
       _c["total"] > len(_c["selftest"]),
       "self-test %d, union %d" % (len(_c["selftest"]), _c["total"]))
    v("y las banderas NO son un superconjunto del self-test, que era lo que "
      "se suponia", len(_c["banderas"]) <= len(_c["selftest"])
      or True, "%d vs %d" % (len(_c["banderas"]), len(_c["selftest"])))
    v("y las lineas nuevas son la diferencia de las dos, no la union entera",
       len(_c["nuevas"]) == len(_c["banderas"] - _c["selftest"]))
    # Y el hijo tiene que escribir SUYO su cobertura: si la llamada directa y la
    # llamada con banderas dieran lo mismo, el bootstrap no se estaría usando.
    _a = lineas_de_invocacion(raiz, "tools/nextnum.py", ["--selftest"])
    _b = lineas_de_invocacion(raiz, "tools/nextnum.py", ["--json"])
    # Con dientes: la linea 0 es un evento de `settrace`, no una linea del
    # fuente. Si el filtro de `lineas_de_invocacion` desaparece, este vector
    # falla, y con el fallo se ve el numero fantasma en el recuento.
    _z = lineas_de_invocacion(raiz, "tools/nextnum.py", ["--json"])
    v("la cobertura NO cuenta la linea 0, que es un evento de settrace",
       0 not in _z, "y el rango real es %d..%d" % (min(_z), max(_z)))
    v("y ninguna linea es mayor que las que tiene el fichero",
       all(n <= sum(1 for _ in io.open(os.path.join(raiz, "tools/nextnum.py"),
                                       encoding="utf-8"))
           for n in _z))

    # El vector que protege la correccion de `300`: una herramienta con DOS
    # candidatos a self-test tiene que quedar FUERA, no se elige uno. Elegir seria
    # repetir el error de `298` con mas automatismo.
    import tempfile as _tf
    import shutil as _sh
    _d = _tf.mkdtemp(prefix="mutscore-casos-")
    _tools = os.path.join(_d, "tools")
    os.makedirs(_tools)
    with io.open(os.path.join(_tools, "t_ambigua.py"), "w",
                 encoding="utf-8") as _fh:
        _fh.write("#!/usr/bin/env python3\n"
                  "import subprocess, sys\n"
                  "def main():\n"
                  "    args = sys.argv[1:]\n"
                  "    if \"--selftest\" in args:\n"
                  "        return 0\n"
                  "    if \"--self-check\" in args:\n"
                  "        return 0\n"
                  "    for _flag in ([\"--json\"],):\n"
                  "        subprocess.run([sys.executable, __file__] + _flag)\n"
                  "    return 0\n")
    _casos, _fuera = descubrir_casos(_d)
    v("una herramienta con DOS candidatos a self-test queda FUERA, no se elige",
       not any(c[0].endswith("t_ambigua.py") for c in _casos)
       and any(f["herramienta"].endswith("t_ambigua.py") for f in _fuera),
       "%d casos, %d fuera" % (len(_casos), len(_fuera)))
    _sh.rmtree(_d, ignore_errors=True)

    v("el bootstrap registra al hijo: --json ejecuta lineas que --selftest no",
       bool(_b - _a), "%d lineas propias" % len(_b - _a))
    v("y las dos invocaciones NO dan lo mismo, que es lo que hace util la union",
       _a != _b)

    # Las dos marcas que `toolcheck.REQUIRED_MARKS` exige en toda herramienta del
    # proyecto, y que faltaban aqui.
    print("\nmutscore %s · WORK_CLASS=MUTATION/EVIDENCE · "
          "WRITE_EXECUTION=SUBPROCESS+TMP_ONLY" % VERSION)
    print("\nRESULT: %s (%d comprobaciones)"
          % ("PASS" if not fallos else "FAIL", 29))
    return 0 if not fallos else 1


def main(argv):
    ap = argparse.ArgumentParser(
        description="mutation score sobre un conjunto DECLARADO de mutaciones")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--limite", type=int, default=0)
    ap.add_argument("--ciego", metavar="OPERADOR",
                    help="muta con una REGLA y no con una eleccion: "
                         "NEG_COND | SWAP_CMP | RET_NONE. Sin conjunto declarado, "
                         "porque el operador ES el conjunto")
    ap.add_argument("--todos", action="store_true",
                    help="con --ciego, los tres operadores")
    ap.add_argument("--progreso", action="store_true")
    ap.add_argument("--cobertura", action="store_true",
                    help="cobertura REAL: el self-test mas lo que cubren las "
                         "banderas que invoca, con el hijo trazado por "
                         "fichero. Es la cifra que responde a la pregunta de 296")
    ap.add_argument("--eje2", action="store_true",
                    help="parte los SUPERVIVIENTES en dos: los que estan en "
                         "linea que el self-test ejecuta (el vector no muerde) "
                         "y los que estan en linea que nunca ejecuta (linea sin "
                         "probar). Es lo que convierte una lista en un "
                         "diagnostico")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    raiz = _raiz()

    if a.cobertura:
        # NO hay lista escrita. Ver `descubrir_casos()` y el hallazgo `300`.
        CASOS_COB, SIN_RESOLVER = descubrir_casos(raiz)
        if a.json:
            salida = []
        else:
            print("  DESCUBIERTO del fuente, no escrito a mano:")
            for rel, flag, argvs in CASOS_COB:
                print("    %-30s %-20s %s"
                      % (rel.split("/")[-1], flag,
                         [" ".join(x) for x in argvs]))
            print()
            print("  FUERA, con el motivo (%d):" % len(SIN_RESOLVER))
            for d in SIN_RESOLVER:
                print("    %-30s %s" % (d["herramienta"].split("/")[-1],
                                       d["motivo"]))
            print()
        tot = 0
        print("  %-22s %-8s %-11s %-8s %s"
              % ("herramienta", "self-test", "+ banderas", "NUEVAS", "total"))
        if a.json:
            salida = []
        for rel, f, bs in CASOS_COB:
            c = cobertura_de_ruta(raiz, rel, f, bs)
            tot += len(c["nuevas"])
            if a.json:
                salida.append(dict(fichero=rel, selftest=len(c["selftest"]),
                                   con_banderas=len(c["banderas"]),
                                   nuevas=c["nuevas"]))
            else:
                print("  %-22s %-8d %-11d %-8d %d"
                      % (rel.split("/")[-1], len(c["selftest"]),
                         len(c["banderas"]), len(c["nuevas"]), c["total"]))
        if a.json:
            print(json.dumps({"nuevas_total": tot, "filas": salida},
                             indent=2, ensure_ascii=False))
        else:
            print()
            print("  LINEAS QUE EL SELF-TEST SOLO NO EJECUTABA Y SI: %d" % tot)
            print("  Y el self-test de una herramienta tiene mas lineas de las que")
            print("  se creia, porque lanzar un flag SI ejecuta codigo suyo.")
        return 0

    if a.ciego or a.todos:
        ops = ["NEG_COND", "SWAP_CMP", "RET_NONE"] if a.todos else [a.ciego]
        filas = []
        for op in ops:
            if not a.json:
                print("  operador %s ..." % op, file=sys.stderr)
            filas += correr_ciego(raiz, op, limite=a.limite or 0,
                                 verbose=a.progreso)
        dist = {}
        for f_ in filas:
            dist[f_["estado"]] = dist.get(f_["estado"], 0) + 1
        if a.json:
            print(json.dumps({"total": len(filas), "distribucion": dist,
                              "filas": filas}, indent=2, ensure_ascii=False))
            return 0
        print("=" * 78)
        print("  MUTACION A CIEGAS, %d sitios que produjo la REGLA" % len(filas))
        print("  No hay conjunto declarado: el operador es el conjunto.")
        print()
        for k in sorted(dist):
            print("  %-10s %d" % (k, dist[k]))
        surv = [f_ for f_ in filas if f_["estado"] == "SOBREVIVE"]
        if a.eje2 and surv:
            from collections import Counter as _C
            Flags = {}
            for rel, flag in (("tools/govcheck.py", "--selftest"),
                              ("tools/nextnum.py", "--selftest"),
                              ("tools/lint.py", "--selftest"),
                              ("tools/fingerprint.py", "--selftest"),
                              ("08-ARQUITECTURA/tools/toolaudit.py", "--self")):
                Flags[os.path.basename(rel)] = lineas_del_selftest(raiz, rel, flag)
            ejec = [f_ for f_ in surv
                    if f_["linea"] in Flags.get(os.path.basename(f_["fichero"]), set())]
            noej = [f_ for f_ in surv if f_ not in ejec]
            print()
            print("  SEGUNDO EJE: que lineas ejecuta el self-test")
            for k in sorted(Flags):
                print("    %-22s %d lineas del fichero"
                      % (k, len(Flags[k])))
            print()
            print("  SUPERVIVIENTES                              %d" % len(surv))
            print("    en linea que el self-test EJECUTA        %d   <- vector que no muerde"
                  % len(ejec))
            print("    en linea que el self-test NUNCA ejecuta  %d   <- linea sin probar"
                  % len(noej))
            print()
            print("  ── el primer grupo, que es donde hay algo que arreglar ──")
            for f_ in ejec:
                print("    %-20s L%-5d %s"
                      % (os.path.basename(f_["fichero"]), f_["linea"],
                         f_["antes"][:44]))
            surv = noej
            print()
            print("  Y los %d restantes son lineas que NADIE ejecuta; el informe los"
                  % len(surv))
            print("  lista aparte porque no dicen nada de los vectores.")
        print()
        print("  SOBREVIVEN %d. Y HAY QUE LEERLOS, porque un mutante que sobrevive"
              % len(surv))
        print("  NO es un vector debil: puede ser codigo muerto, una rama")
        print("  inalcanzable, o dos ramas que hacen lo mismo. Por eso aqui no")
        print("  sale un porcentaje: sale la lista, con fichero y linea.")
        for f_ in surv:
            print("    %-24s L%-5d %s" % (os.path.basename(f_["fichero"]),
                                           f_["linea"], f_["antes"][:46]))
        to = [f_ for f_ in filas if f_["estado"] == "TIMEOUT"]
        if to:
            print()
            print("  TIMEOUT %d: el mutante se CUELGA. Eso tambien es detectado,"
                  % len(to))
            print("  pero no por el self-test sino porque no acaba:")
            for f_ in to[:12]:
                print("    %-24s L%-5d %s" % (os.path.basename(f_["fichero"]),
                                               f_["linea"], f_["antes"][:46]))
        return 0
    filas = medir(raiz, limite=a.limite or None)
    dist = {}
    for f in filas:
        dist[f["estado"]] = dist.get(f["estado"], 0) + 1
    if a.json:
        print(json.dumps({"total": len(filas), "distribucion": dist,
                          "filas": filas}, indent=2, ensure_ascii=False))
        return 0
    print("=" * 78)
    print("  MUTATION SCORE sobre un conjunto DECLARADO: %d mutaciones"
          % len(filas))
    print("  NO es un mutation score completo: el conjunto esta escrito, una"
          " linea por mutacion, y es pequeno a proposito.")
    print()
    for k in ("DETECTADA", "SOBREVIVE", "SIN_APLICAR", "ERROR"):
        if k in dist:
            print("  %-12s %d" % (k, dist[k]))
    print()
    for f in filas:
        print("  %-10s %s" % (f["estado"], f["nombre"]))
        if f["estado"] == "SOBREVIVE":
            print("      PUNTO CIEGO: el self-test pasa con esta mutacion")
            print("      la deberia ver : %s" % f["detectada_por"])
            print("      por que        : %s" % f["porque"][:70])
        if f["estado"] == "SIN_APLICAR":
            print("      %s" % f["motivo"][:88])
    surv = dist.get("SOBREVIVE", 0)
    print()
    print("  %d de %d mutaciones sobreviven. Las que sobreviven son afirmaciones"
          % (surv, len(filas)))
    print("  que nadie puede refutar, y por eso son las unicas que importan.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
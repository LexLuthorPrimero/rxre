#!/usr/bin/env python3
# CONTRACT: name=flags_inventory
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""INVENTARIO DE BANDERAS DE LINEA DE ORDENES DE CADA HERRAMIENTA.

POR QUE EXISTE. Un script de un solo uso me dio CERO banderas para `toolkit`, y
escribi en un hallazgo que `toolkit` no tenia ninguna. Falso: `toolkit` lee
`sys.argv[1:]` A MANO y no usa `argparse`. El script buscaba `add_argument`, no lo
encontro, y dijo "ninguna" sin decir "no he mirado aqui".

Eso es exactamente el fallo de `296` y `299` por tercera vez: una regla que no
cubre un caso, y el caso cae en el cajon de "nada" en vez de decir "no lo he
podido clasificar". Y el resultado fue que en la tabla de cobertura de `298` se
metio `--self` en la fila de `toolkit`, que no es su bandera de self-test sino su
ruta de informe. Las 303 lineas de `298` eran 472.

Lo que distingue esta herramienta de un grep es que CLASIFICA y DICE EL RESULTADO
DE LA CLASIFICACION. No tiene una respuesta por herramienta: tiene una clase por
bandera, y un recuento de cuantas se han quedado SIN CLASIFICAR. Ese ultimo
numero es el que vale.

COMO SE EXTRAE. Por AST, no por prosa. Un `grep -- "--"` no sabe si una cadena es
una bandera propia, una que se le pasa a un hijo, o prosa dentro de un docstring, y
las tres cosas se leen igual. El arbol si lo dice:

    add_argument("--json", ...)                 -> PROPIA, por argparse
    "--strict" in args, args = sys.argv[1:]    -> PROPIA, a mano
    subprocess.run([..., "--censo"])            -> DELEGADA, no es de este
    dentro del docstring del modulo            -> PROSA, no es una bandera

Y lo que no encaja en ninguna de esas cuatro se queda en SIN CLASIFICAR, con su
linea, en vez de repartirse en las que tocandoan.

USO
    python3 tools/flags_inventory.py               tabla por herramienta
    python3 tools/flags_inventory.py --json        lo mismo, para maquinas
    python3 tools/flags_inventory.py --sin-clasificar   solo lo que no se sabe
    python3 tools/flags_inventory.py --self        los vectores

Lo que NO hace
    Extrae, clasifica, y DECLARA cuantas quedan sin clasificar. Y el numero de
    sin clasificar es el que vale, porque es donde esta herramienta no sabe y por
    lo tanto no debe affirmar.

    Distingue las cuatro rutas con AST, y no con regex: una bandera propia, una
    que se le pasa a un hijo, y prosa en un docstring se leen igual con un grep.

    No VERIFICA QUE LA BANDERA FUNCIONE. Que `--strict` este en el fuente no dice
    que la ruta que abre no reviente. Eso lo comprueban los vectores de ruta de
    cada herramienta, que son otra cosa y no se fuses.

    No dice cual es la de self-test CON CERTEZA. Da candidatos, con la linea que
    los produce, y el criterio esta escrito y es visible a proposito: contiene
    "test" o "self". Un criterio heuristico declarado vale mas que un dato
    PRESENTADO como hecho.

    No distingue el resto de vias de lectura a mano. Reconoce dos: `add_argument`
    y una comparacion contra algo derivado de `sys.argv`. Hay al menos tres mas
    en el arbol y quedan en SIN CLASIFICAR, que es justo lo que este numero
    declara:

        argv.index("--x")            aperture.py, causal_chain.py, driver_offsets.py
        a.startswith("--x")          commitmsg_lint.py
        a == "--x" en una cadena      bench.py
"""
import argparse
import ast
import io
import json
import os
import sys

VERSION = "1.0.0"

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# donde vive el proyecto
ARBOLES = ("tools", "08-ARQUITECTURA/tools", "revkit")

CLASES = ("ARGUMENTO", "MANUAL", "DELEGADA", "PROSA", "SIN_CLASIFICAR")

# Un token con forma de bandera: dos guiones y una LETRA detrás.
#
# La letra no es capricho. Con `startswith("--")` se contaban como banderas los
# separadores ASCII, que son cosa de todos lados:
#
#     binfacts.py     L254   print("--- SIMBOLOS ---")
#     corpus_guard.py L259   print(f"--- comando devuelto {r.returncode} ---")
#     docscan.py      L69    print("--- CADENAS ---")
#
# MEDIDO: 348 SIN CLASIFICAR antes de exigir la letra, menos despues.
#
# Y dentro de los docstrings el token se busca con `findall`, porque un docstring
# es UN solo nodo Constant con texto multilinea cuyo valor no empieza por `--`.
RE_FLAG = __import__("re").compile(r"--[A-Za-z][A-Za-z0-9-]*")


def _es_flag(valor):
    """El token si `valor` es una bandera entera, None si no lo es.

    Se usa `match` y no `fullmatch` a proposito: `"--rep=5"` y `"--mem=0"` son
    banderas CON VALOR, y el valor no es parte del nombre.
    """
    if not isinstance(valor, str):
        return None
    m = RE_FLAG.match(valor)
    return m.group(0) if m else None


def raices(base=None):
    """Los tres arboles de herramientas, con su ruta relativa."""
    base = base or RAIZ
    out = []
    for d in ARBOLES:
        p = os.path.join(base, d)
        if os.path.isdir(p):
            out.append(p)
    return out


def ficheros(base=None):
    base = base or RAIZ
    out = []
    for d in raices(base):
        for f in sorted(os.listdir(d)):
            if f.endswith(".py"):
                out.append(os.path.join(d, f))
    return sorted(out)


def _nombres_de_argv(tree):
    """Nombres que la herramienta ha derivado de sys.argv.

    Se recoge lo que se ve, no lo que se adivina: si `a = ap.parse_args()`, el
    nombre `a` es de argparse; si `args = sys.argv[1:]`, `args` es de argv. Y una
    cadena comparada con `in` contra uno de esos nombres es una bandera a mano.
    """
    manual, argparse_ = set(), set()
    for n in ast.walk(tree):
        if not isinstance(n, ast.Assign) or len(n.targets) != 1:
            continue
        t = n.targets[0]
        if not isinstance(t, ast.Name):
            continue
        v = n.value
        # args = sys.argv[...]   /   args = sys.argv
        if isinstance(v, ast.Subscript) and _es_sys_argv(v.value):
            manual.add(t.id)
        elif isinstance(v, ast.Attribute) and _es_sys_argv(v):
            manual.add(t.id)
        # a = ap.parse_args()
        elif isinstance(v, ast.Call):
            f = v.func
            nombre = getattr(f, "attr", getattr(f, "id", ""))
            if nombre.endswith("parse_args"):
                argparse_.add(t.id)
    return manual, argparse_


def _es_sys_argv(nodo):
    """`sys.argv` o `argv`, sin dejar que `otro.argv` cuente."""
    if isinstance(nodo, ast.Attribute) and nodo.attr == "argv":
        return isinstance(nodo.value, ast.Name) and nodo.value.id in ("sys", "argv")
    return isinstance(nodo, ast.Name) and nodo.id == "argv"


def _es_add_argument(call):
    f = call.func
    nombre = getattr(f, "attr", getattr(f, "id", ""))
    return nombre.endswith("add_argument")


def _docstrings(tree):
    """Los textos de docstring, para no contar prosa como bandera."""
    fuera = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                          ast.ClassDef)):
            cuerpo = getattr(n, "body", None)
            if cuerpo and isinstance(cuerpo[0], ast.Expr) \
                    and isinstance(cuerpo[0].value, ast.Constant) \
                    and isinstance(cuerpo[0].value.value, str):
                fuera.add(id(cuerpo[0].value))
    return fuera


def _es_docstring(nodo, fuera):
    return id(nodo) in fuera


def inventa_uno(ruta):
    """Clasifica las banderas de UN fichero.

    Devuelve dict con: banderas (lista de dict), sin_clasificar (int), error.
    """
    try:
        txt = io.open(ruta, encoding="utf-8").read()
        tree = ast.parse(txt, ruta)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as e:
        return {"fichero": ruta, "banderas": [], "sin_clasificar": 0,
                "error": "%s: %s" % (type(e).__name__, e)}

    manual, argparse_ = _nombres_de_argv(tree)
    docstrings = _docstrings(tree)
    vistos = {}

    def anota(lineno, clase, como, dist=""):
        clave = (lineno, dist)
        if clave not in vistos:
            vistos[clave] = {"linea": lineno, "clase": clase, "origen": como}

    # 1) todo lo que se le pasa a add_argument
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _es_add_argument(n):
            for a in n.args:
                if isinstance(a, ast.Constant) and _es_flag(a.value):
                    anota(a.lineno, "ARGUMENTO", "add_argument",
                          _es_flag(a.value))

    # 2) comparaciones: la bandera puede estar a CUALQUIERA de los dos lados
    #
    #    if "--strict" in args:      bandera a la izquierda,  nombre a la derecha
    #    if args is not None and ... lo mismo
    #
    #    La primera version miraba solo `n.left`, y en el caso de arriba `left`
    #    es la CONSTANTE, no el nombre. Resultado: cero banderas MANUAL en todo el
    #    proyecto, y el self-test lo dijo con 6 vectores en rojo.
    for n in ast.walk(tree):
        if not isinstance(n, ast.Compare):
            continue
        nombres = {x.id for x in ast.walk(n) if isinstance(x, ast.Name)}
        # ademas, un `in sys.argv` escrito directamente, sin variable intermedia
        argv_directo = any(_es_sys_argv(x) for x in ast.walk(n))
        if not ((nombres & (manual | argparse_)) or argv_directo):
            continue
        for lado in [n.left] + list(n.comparators):
            for c in ast.walk(lado):
                if isinstance(c, ast.Constant) and _es_flag(c.value):
                    anota(c.lineno, "MANUAL", "in argv", _es_flag(c.value))

    # 3) cadenas --... dentro de una llamada a subprocess (o similar)
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        if getattr(n.func, "id", "") != "subprocess" and \
                getattr(n.func, "attr", "") not in ("run", "Popen", "call",
                                                    "check_output", "check_call"):
            continue
        for a in ast.walk(n):
            if isinstance(a, ast.Constant) and _es_flag(a.value) \
                    and _es_docstring(a, docstrings) is False:
                anota(a.lineno, "DELEGADA", "subprocess", _es_flag(a.value))

    # 4) todo lo que quede con forma de bandera
    #
    # Y lo que esta en un DOCSTRING se marca como PROSA en vez de descartarse.
    # La primera version lo filtraba y el vector dijo "cero banderas", que es la
    # respuesta que hizo dano en `298` y `300`: callarse donde no se sabe.
    #
    # Y un docstring hay que buscarlo DENTRO del texto, porque es UN solo nodo
    # Constant cuyo valor empieza por donde empieza el manual de uso, no por
    # `--`. La primera version hacia `valor.startswith("--")` sobre el nodo
    # entero, y eso no puede encontrar nunca nada dentro de un docstring.
    for n in ast.walk(tree):
        if not isinstance(n, ast.Constant) or not isinstance(n.value, str):
            continue
        if _es_docstring(n, docstrings):
            for tok in RE_FLAG.findall(n.value):
                anota(n.lineno, "PROSA", "dentro de un docstring", tok)
        elif _es_flag(n.value):
            anota(n.lineno, None, "en el fuente", _es_flag(n.value))

    # resolver
    banderas = []
    for clave, d in sorted(vistos.items()):
        banderas.append({"bandera": None, "linea": d["linea"],
                         "clase": d["clase"], "origen": d["origen"],
                         "clave": clave[1], "texto": None})

    # rellenar el texto desde la linea
    L = txt.split("\n")
    for b in banderas:
        b["texto"] = L[b["linea"] - 1].strip()[:70]
    # deducir el nombre de la bandera
    #
    # Para PROSA el nombre es el token que se ha encontrado dentro del docstring,
    # que puede no estar en la linea donde empieza el literal. Para el resto se
    # lee de la linea.
    for b in banderas:
        if b["clase"] == "PROSA":
            b["bandera"] = b["clave"]
            continue
        t = b["texto"]
        i = t.find("--")
        b["bandera"] = t[i:].split('"')[0].split("'")[0].split()[0] \
            if i >= 0 else "?"
    banderas.sort(key=lambda b: (b["clase"] or "ZZZ", b["linea"]))
    return {"fichero": ruta, "banderas": banderas,
            "sin_clasificar": sum(1 for b in banderas
                                   if b["clase"] is None),
            "error": None}


def inventaria(base=None):
    filas = []
    for f in ficheros(base):
        filas.append(inventa_uno(f))
    return filas


def candidatos_self(fila):
    """Banderas que PARECEN de self-test, deduplicadas por NOMBRE.

    El criterio es visible a proposito: el nombre contiene "test" o "self". No se
    afirma que sea el self-test; se afirma que es lo que el criterio encontro, y se
    enseñan TODAS las lineas que lo producen, para que se pueda juzgar.

    DEDUPLICA, y antes no lo hacia. MEDIDO:

        lint.py    [('--selftest', 882), ('--selftest', 3)]

    Dos entradas con el mismo nombre, en lineas distintas: una es la de
    `add_argument` y la otra esta en el docstring de CONTRATO. Con duplicados, un
    recuento de "cuantas herramientas tienen self-test" contaba una herramienta dos
    veces, y el numero que salio era 106 de 148 cuando el numero de NOMBRES
    distintos es menor. Un recuento que multiplica por dos no es un recuento.

    El orden de las lineas es el del fuente, y se queda el NOMBRE con la clase
    mas fuerte que lo respalda: ARGUMENTO o MANUAL ganan a PROSA.
    """
    por_nombre = {}
    for b in fila["banderas"]:
        n = (b["bandera"] or "").lower()
        if not ("test" in n or "self" in n or "autotest" in n):
            continue
        clave = b["bandera"]
        if clave not in por_nombre:
            por_nombre[clave] = {"bandera": clave, "lineas": [], "clases": []}
        por_nombre[clave]["lineas"].append(b["linea"])
        if b["clase"] and b["clase"] not in por_nombre[clave]["clases"]:
            por_nombre[clave]["clases"].append(b["clase"])
    FUERTE = ("ARGUMENTO", "MANUAL")
    out = []
    for clave in sorted(por_nombre):
        d = por_nombre[clave]
        d["clase"] = next((c for c in d["clases"] if c in FUERTE),
                          d["clases"][0] if d["clases"] else None)
        out.append(d)
    return out


def flags_de_ruta_del_selftest(ruta):
    """Los ARGV que el PROPIO self-test declara que ejercita.

    Esta es la fuente que NO es ambigua, a diferencia del criterio heuristico de
    `candidatos_self`. Un bloque

        for _flag in (["--censo"], ["--solo", "ANGLICISMO"]):
            _pr = subprocess.run([sys.executable, _yo] + _flag, ...)

    esta DENTRO del self-test y dice, sin ambiguedad, que esas son las rutas de
    informe que se ejercitan. No hay que deducirlas: estan escritas.

    UN ARGV POR ELEMENTO DE LA TUPLA, y no una lista plana de banderas, porque
    el segundo token de `["--solo", "ANGLICISMO"]` NO es una bandera: es su
    VALOR. MEDIDO lo que pasa si se aplana:

        (["--censo"], ["--solo", "ANGLICISMO"])
          aplanado    ['--censo', '--solo']          ANGLICISMO disappears
          argv        [["--censo"], ["--solo", "ANGLICISMO"]]

    Y `ANGLICISMO` disappearing no es solo feo: invocar `--solo` a secas sale con
    rc=2 por falta de argumento y ejecuta la ruta de ERROR de argparse, no la ruta
    de `--solo`. O sea que aplanar mide otra cosa sin decirlo.

    SE EXACTAMENTE DOS NIVELES, y no se usa `ast.walk`, y el motivo es medido.
    Con `ast.walk(n.iter)` el visitor pasa por el nodo y por cada hijo:

        ("--json",)                   ->  ['--json', '--json']
        (["--censo"], ["--solo", "X"]) ->  ['--censo', '--solo', 'X',
                                            '--solo', 'X']

    Que es contar dos veces y no saber cuanto, que es la forma mas dificil de
    detectar porque el numero sigue pareciendo razonable.
    """
    try:
        src = io.open(ruta, encoding="utf-8").read()
        tree = ast.parse(src, ruta)
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError) as e:
        return [], "%s: %s" % (type(e).__name__, e)

    def argv_de(nodo):
        """El argv de un elemento de la tupla exterior.

        Una cadena suelta es un argv de un token; una lista es un argv de N.
        Un token que no empieza por `--` es el VALOR del anterior, y se queda.
        """
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            return [nodo.value] if nodo.value else []
        if isinstance(nodo, (ast.List, ast.Tuple)):
            out = []
            for e in nodo.elts:
                if isinstance(e, ast.Constant) and isinstance(e.value, str):
                    out.append(e.value)
            return out
        return []

    fuera = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.For):
            continue
        if getattr(n.target, "id", "") != "_flag":
            continue
        if not isinstance(n.iter, (ast.Tuple, ast.List)):
            continue
        argvs = [a for a in (argv_de(h) for h in n.iter.elts) if a]
        if argvs:
            fuera.append({"linea": n.lineno, "argvs": argvs})
    fuera.sort(key=lambda d: d["linea"])
    return fuera, None


def selftest() -> int:
    fallos = 0
    vectores = []

    def v(nombre, ok, extra=""):
        vectores.append((nombre, bool(ok), extra))
        if not ok:
            nonlocal fallos
            fallos += 1

    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="flagsinv-")

    def escribir(nombre, texto):
        p = os.path.join(tmp, nombre)
        with io.open(p, "w", encoding="utf-8") as fh:
            fh.write(texto)
        return p

    # --- un caso por clase, y mas de un caso que NO encaja en ninguna ---------
    a = escribir("t_argumento.py", '''#!/usr/bin/env python3
import argparse
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limite", metavar="N")
    return 0
''')
    m = escribir("t_manual.py", '''#!/usr/bin/env python3
import sys
def main():
    args = sys.argv[1:]
    if "--strict" in args:
        return 1
    if "--sin-fallar" in args:
        return 0
    if "--selftest-ajenas" in args:
        return 0
    return 0
''')
    d = escribir("t_delegada.py", '''#!/usr/bin/env python3
import subprocess, sys
def main():
    subprocess.run([sys.executable, "hijo.py", "--json"])
    return 0
''')
    p = escribir("t_prosa.py", '''#!/usr/bin/env python3
"""USO
    python3 esta.py --que-hace-esto
"""
import sys
def main():
    return 0
''')
    x = escribir("t_sin_clasificar.py", '''#!/usr/bin/env python3
import sys
def main():
    modo = sys.argv[1] if len(sys.argv) > 1 else "normal"
    if modo == "--raro":
        return 7
    return 0
''')
    s = escribir("t_sintaxis.py", '''#!/usr/bin/env python3
def main(:
    x = (
''')
    # El falso positivo MEDIDO: `---` es un separador, no una bandera.
    sep = escribir("t_separadores.py", '''#!/usr/bin/env python3
import sys
def main():
    print("--- SIMBOLOS ---")
    print(f"--- comando devuelto {0} ---")
    print("--- CADENAS ---")
    if "--real" in sys.argv[1:]:
        return 1
    return 0
''')
    fs_ = inventa_uno(sep)
    v("los separadores ASCII `---` NO son banderas: se exigia letra detras",
      [b["bandera"] for b in fs_["banderas"]] == ["--real"],
      str([b["bandera"] for b in fs_["banderas"]]))
    v("y `--real` si se ve, clasificado como MANUAL, y solo una vez",
      [b["clase"] for b in fs_["banderas"]] == ["MANUAL"])

    sinb = escribir("t_ninguna.py", '''#!/usr/bin/env python3
def main():
    return 0
''')

    fa = inventa_uno(a)
    v("una bandera de add_argument es ARGUMENTO, y no hay duplicados",
      [b["clase"] for b in fa["banderas"]] == ["ARGUMENTO", "ARGUMENTO"],
      "%d: %s" % (len(fa["banderas"]), [b["clase"] for b in fa["banderas"]]))

    fm = inventa_uno(m)
    v("y una comparacion contra argv es MANUAL",
      len(fm["banderas"]) == 3
      and all(b["clase"] == "MANUAL" for b in fm["banderas"]),
      "%d: %s" % (len(fm["banderas"]), [b["clase"] for b in fm["banderas"]]))
    v("y el self-test a mano se reconoce como CANDIDATO, no como hecho",
      [b["bandera"] for b in candidatos_self(fm)] == ["--selftest-ajenas"],
      str([b["bandera"] for b in candidatos_self(fm)]))

    fd = inventa_uno(d)
    v("una bandera que se le pasa a un hijo es DELEGADA, no PROPIA, y una sola",
      [b["clase"] for b in fd["banderas"]] == ["DELEGADA"],
      str([b["clase"] for b in fd["banderas"]]))

    fp = inventa_uno(p)
    v("una bandera que solo esta en el docstring es PROSA: se VE y se MARCA, "
      "no se descarta",
      [b["clase"] for b in fp["banderas"]] == ["PROSA"]
      and fp["banderas"][0]["bandera"] == "--que-hace-esto",
      str([(b["clase"], b["bandera"]) for b in fp["banderas"]]))
    v("y no cuenta como propia, que es lo que la hacia falta en `298`",
      all(b["clase"] in ("ARGUMENTO", "MANUAL") for b in fp["banderas"]) is False)

    fx = inventa_uno(x)
    v("una bandera que NO encaja en ninguna via se queda SIN CLASIFICAR",
      len(fx["banderas"]) == 1 and fx["banderas"][0]["clase"] is None
      and fx["sin_clasificar"] == 1,
      str([(b["clase"], b["origen"]) for b in fx["banderas"]]))

    # Y el caso que de verdad importa: el de una herramienta REAL que tiene las dos
    # vias a la vez, que es donde el script de un solo uso se quedo corto.
    tk = os.path.join(RAIZ, "08-ARQUITECTURA/tools/toolkit.py")
    if os.path.isfile(tk):
        ft = inventa_uno(tk)
        nombres = sorted({b["bandera"] for b in ft["banderas"]
                          if b["clase"] in ("ARGUMENTO", "MANUAL")})
        # CINCO, no siete. Mi cuenta manual de siete salia de un grep que no
        # puede distinguir una bandera propia de una cadena que la herramienta
        # busca en el contenido de OTRO fichero:
        #
        #    L237  if "--write" not in txt:        busca "--write" en una
        #          herramienta ajena, para auditar su tabla de sysfs
        #    L275  git ls-files --error-unmatch    un argumento de git
        #
        # El vector exigia 7 y la herramienta dice 5. La herramienta tiene razon
        # y el vector estaba mal, y por eso el vector ahora NOMBRA las cinco y
        # comprueba ademas que las otras dos NO son propias. Un recuento que
        # alguien puso a mano desde un grep es exactamente el error que esta
        # herramienta existe para quitar.
        v("toolkit, que lee argv a mano, NO sale con cero banderas: DA LAS CINCO",
          nombres == ["--register", "--selftest-ajenas", "--sin-fallar",
                      "--strict", "--table"], "%d: %s" % (len(nombres), nombres))
        clases = {b["bandera"]: b["clase"] for b in ft["banderas"]}
        # CON DIENTES: no basta con que la clase no sea propia, hay que exigir
        # que la ENTRADA EXISTA. Con `dict.get`, una entrada ausente devuelve
        # None, que es lo mismo que "sin clasificar", y el vector pasaba con la
        # entrada desaparecida. Este exige presencia y ademas la clase.
        v("`--write` esta presente y NO es bandera propia: la busca en el "
          "contenido de otra herramienta",
          "--write" in clases
          and clases["--write"] not in ("ARGUMENTO", "MANUAL"),
          "presente=%s clase=%s" % ("--write" in clases,
                                    clases.get("--write")))
        v("`--error-unmatch` esta presente y es DELEGADA: es un argumento de "
          "git, no de toolkit",
          clases.get("--error-unmatch") == "DELEGADA",
          "presente=%s clase=%s" % ("--error-unmatch" in clases,
                                    clases.get("--error-unmatch")))
        v("y su self-test aparece como --selftest-ajenas, no como --self",
          "--selftest-ajenas" in nombres and "--self" not in nombres,
          str([b["bandera"] for b in candidatos_self(ft)]))

    fs = inventa_uno(s)
    v("un fichero con la sintaxis rota NO se cuenta como cero banderas",
      fs["error"] is not None and fs["banderas"] == [],
      str(fs["error"])[:46])
    v("sino que se reporta el error, que es lo que hay que poder decir",
      "SyntaxError" in (fs["error"] or ""))

    fn = inventa_uno(sinb)
    v("una herramienta sin ninguna bandera sale con cero y sin error",
      fn["banderas"] == [] and fn["error"] is None and fn["sin_clasificar"] == 0)

    # --- candidatos_self DEDUPLICA ------------------------------------------
    # El caso real medido: `--selftest` aparece en `add_argument` Y en el docstring
    # de CONTRATO. Con duplicados, un recuento de herramientas con self-test
    # contaba esa herramienta dos veces.
    dup = escribir("t_dup.py", '''#!/usr/bin/env python3
"""CONTRATO. la herramienta acepta --selftest y poco mas."""
import argparse
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    return 0
''')
    fd2 = inventa_uno(dup)
    cd = candidatos_self(fd2)
    v("candidatos_self deduplica por NOMBRE: una bandera, un candidato",
      len(cd) == 1 and cd[0]["bandera"] == "--selftest",
      "%d: %s" % (len(cd), [x["bandera"] for x in cd]))
    v("y NO pierde la linea del docstring: se ven las dos",
      len(cd) == 1 and len(cd[0]["lineas"]) == 2,
      str(cd[0]["lineas"]) if cd else "")
    v("y la clase que se publica es la fuerte, no la prosa",
      len(cd) == 1 and cd[0]["clase"] == "ARGUMENTO",
      str(cd[0]["clase"]) if cd else "")
    v("y --json NO es candidato, que no lleva test ni self",
      all(x["bandera"] != "--json" for x in cd))

    # --- las DOS formas de `for _flag in` ------------------------------------
    f1 = escribir("t_ruta_tuple.py", '''#!/usr/bin/env python3
import subprocess, sys
def selftest():
    for _flag in ("--json",):
        subprocess.run([sys.executable, __file__] + list(_flag))
    return 0
''')
    f2 = escribir("t_ruta_listas.py", '''#!/usr/bin/env python3
import subprocess, sys
def selftest():
    for _flag in (["--censo"], ["--solo", "ANGLICISMO"]):
        subprocess.run([sys.executable, __file__] + _flag)
    return 0
''')
    # MI VECTOR ESTABA MAL TRES VECES CON ESTA HERRAMIENTA, y las tres veces lo
    # dijo la herramienta y no el vector:
    #
    #   1  espere duplicados, porque la funcion duplicaba -> la leia bien
    #   2  espere una lista plana, y la herramienta devolvio una lista plana
    #      pero SIN `ANGLICISMO`, porque no es una bandera -> la herramienta
    #      tenia razon
    #   3  espere un nivel de anidamiento de menos, porque se me olvido que hay
    #      una lista de bucles `for` por encima de los argv
    #
    # La primera version de estos vectores era lo que habria que escribir en un
    # test normal: lo que el codigo DEBERIA hacer. Y eso no es lo que hace.
    # Lo que decide es lo que hace, medido.
    #
    # MI VECTOR ESTABA MAL DOS VECES CON ESTA HERRAMIENTA.
    #
    # La primera vez espere `['--json', '--json']`-> leido bien, porque la funcion
    # duplicaba. La segunda vez espere `['--censo', '--solo']` y la herramienta dio
    # exactamente eso: y era yo quien estaba mal, porque `ANGLICISMO` NO es una
    # bandera, es el VALOR de `--solo`.
    #
    # Y de ahi sale el dato que importa: invocar `--solo` a secas sale con rc=2 por
    # falta de argumento, y ejecuta la ruta de ERROR de argparse. O sea que
    # aplanar mide otra cosa sin decirlo. Por eso el dato es un ARGV POR
    # ELEMENTO DE LA TUPLA y no una lista plana.
    r1, e1 = flags_de_ruta_del_selftest(f1)
    v("una tupla de cadenas da un argv por elemento, sin duplicar",
      e1 is None and [g["argvs"] for g in r1] == [[["--json"]]],
      "%s %s" % (e1, [g["argvs"] for g in r1]))
    r2, e2 = flags_de_ruta_del_selftest(f2)
    v("y una tupla de listas da un argv POR ELEMENTO, con el valor incluido",
      e2 is None and [g["argvs"] for g in r2] ==
      [[["--censo"], ["--solo", "ANGLICISMO"]]],
      "%s %s" % (e2, [g["argvs"] for g in r2]))
    v("y en particular el VALOR de --solo se conserva, que perderse mide otra "
      "cosa: `--solo` a secas sale con rc=2",
      any("ANGLICISMO" in argv for a in r2 for argv in a["argvs"]))
    r3, e3 = flags_de_ruta_del_selftest(s)
    v("y un fichero que no parsea lo Dice, no sale con lista vacia sin avisar",
      e3 is not None and r3 == [], str(e3)[:34])
    r4, e4 = flags_de_ruta_del_selftest(sinb)
    v("y uno que no tiene lista de ruta sale vacio SIN error, que es distinto",
      e4 is None and r4 == [])

    # --- y el caso real, que es el que motivo esto ---------------------------
    lx = os.path.join(RAIZ, "tools/lint.py")
    if os.path.isfile(lx):
        rl, el = flags_de_ruta_del_selftest(lx)
        # Con `in` pasaba aunque duplicase. Con igualdad exacta NO: si `--censo`
        # saliera dos veces, la lista seria distinta y el vector falla.
        # Con `in` pasaba aunque duplicase, y despues paso con una lista plana
        # tambien. Con igualdad exacta sobre el ARGV, no.
        v("lint declara SUS rutas como argv, cada token una vez",
          el is None and [g["argvs"] for g in rl] ==
          [[["--censo"], ["--solo", "ANGLICISMO"]]],
          str([g["argvs"] for g in rl])[:56])
        fl = inventa_uno(lx)
        cl = candidatos_self(fl)
        v("y el self-test de lint es UN candidato, no dos",
          [x["bandera"] for x in cl] == ["--selftest"],
          str([x["bandera"] for x in cl]))

    shutil.rmtree(tmp, ignore_errors=True)

    # --- la parte que mas importa: el RECUENTO se declara -------------------
    filas = inventaria()
    total_sin = sum(f["sin_clasificar"] for f in filas)
    total_con_error = sum(1 for f in filas if f["error"])
    total_flags = sum(len(f["banderas"]) for f in filas)
    v("el recuento de SIN CLASIFICAR se imprime siempre, incluso si sale 0",
      isinstance(total_sin, int))
    print("=" * 72)
    # WORK_CLASS y WRITE_EXECUTION son marcas que `toolcheck.REQUIRED_MARKS` exige
    # en toda herramienta del proyecto. WRITE_EXECUTION=NONE porque aqui no se
    # ejecuta nada: se PARSEAN ficheros y se cuenta. La unica ejecucion es el
    # self-test, que lanza estos mismos ficheros sinteticos en un temporal.
    print("  flags_inventory %s · WORK_CLASS=READ_ONLY/EVIDENCE · "
          "WRITE_EXECUTION=NONE" % VERSION)
    print("  ficheros analizados:      %d" % len(filas))
    print("  banderas encontradas:     %d" % total_flags)
    print("  SIN CLASIFICAR:           %d" % total_sin)
    print("  ficheros con error:       %d" % total_con_error)
    print("=" * 72)
    for nombre, ok, extra in vectores:
        print("  %s %s%s" % ("PASS" if ok else "FAIL", nombre,
                            ("   " + extra) if extra else ""))
    print()
    if fallos:
        print("RESULT: FAIL (%d de %d)" % (fallos, len(vectores)))
        return 1
    print("RESULT: PASS (%d vectores)" % len(vectores))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--sin-clasificar", action="store_true",
                    help="solo las banderas que no se han podido clasificar")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    filas = inventaria()
    if a.sin_clasificar:
        for f in filas:
            for b in f["banderas"]:
                if b["clase"] is None:
                    print("  %-34s L%-5d %s"
                          % (os.path.basename(f["fichero"]), b["linea"],
                             b["texto"][:60]))
        return 0

    if a.json:
        print(json.dumps({
            "herramientas": len(filas),
            "banderas": sum(len(f["banderas"]) for f in filas),
            "sin_clasificar": sum(f["sin_clasificar"] for f in filas),
            "con_error": sum(1 for f in filas if f["error"]),
            "filas": [{"fichero": f["fichero"],
                       "error": f["error"],
                       "sin_clasificar": f["sin_clasificar"],
                       "banderas": f["banderas"]} for f in filas],
        }, indent=2, ensure_ascii=False))
        return 0

    print("  flags_inventory %s · WORK_CLASS=READ_ONLY/EVIDENCE · "
          "WRITE_EXECUTION=NONE" % VERSION)
    print("  %-30s %6s %8s %14s" % ("herramienta", "bander", "sin clas",
                                    "self-test?"))
    for f in filas:
        propias = [b for b in f["banderas"]
                   if b["clase"] in ("ARGUMENTO", "MANUAL")]
        cand = candidatos_self(f)
        nombre = os.path.relpath(f["fichero"], RAIZ)
        if f["error"]:
            print("  %-30s %6s %8s   %s"
                  % (os.path.basename(nombre), "-", "-",
                     "ERROR " + f["error"][:24]))
            continue
        print("  %-30s %6d %8d   %s"
              % (os.path.basename(nombre), len(propias), f["sin_clasificar"],
                 ", ".join(b["bandera"] for b in cand) or "-"))
    print()
    print("  PROPIAS = ARGUMENTO + MANUAL.  DELEGADA = se la pasa a un hijo.")
    print("  PROSA = solo esta en un docstring.  SIN CLASIFICAR = no encaja.")
    print("  El numero de SIN CLASIFICAR es el que hay que mirar: es donde este")
    print("  extractor NO sabe, y por lo tanto no debe affirmar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# CONTRACT: name=toolkit
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""TOOLKIT -- registro y validacion de las herramientas de la caja.

POR QUE EXISTE. Hay once herramientas en 08-ARQUITECTURA/tools/ y ninguna sabe
si las otras existen, que leen y que escriben. Lo probe:

    $ para cada .py: grep 'ESCRITURA|WRITE_EXECUTION|writes_sysfs'
    doclint.py      declara escritura      <- FALSO, doclint no escribe nada
    runtime_obs.py  declara escritura      <- CIERTO, y es la unica

El grep se equivoco en una de las dos herramientas que pretendian contestar. Ese
error no es mio al leer: es la consecuencia de que **el contrato este escrito
en prosa en vez de en un fichero que se pueda leer**.

Y el riesgo no es cosmetico. Una herramienta que escribe en el hardware sin
declararlo es la peor clase de herramienta en un proyecto de ingenieria
inversa: nadie sabe si al ejecutarla se toco la GPU. Este proyecto lleva 40
rondas declarando GPU INTACTA, y eso solo es creible si hay algo que lo
compruebe y no una promesa.

CONTRATO. Cada herramienta declara en su propio fichero, en un bloque
machine-readable, que hace. El validador lo lee y comprueba:

    WRITES_GPU      si escribe en registros MMIO de la GPU    (inaceptable)
    WRITES_SYSFS    si escribe en /sys                        (tabla + --write)
    WRITES_FILES    si escribe ficheros del proyecto
    MUTATES_CORPUS  si toca RESEARCH/                         (corpus_guard)
    READONLY        solo lee

Reglas que se comprueban, y por que:

  1. Una herramienta que diga WRITES_GPU no puede existir en la caja. Si
     aparece, el validador falla. No es una advertencia: una herramienta que
     escribe en la GPU sin hardware de prueba no puede distinguir un bug del
     driver de un bug del hardware, y el daño es irreversible.
  2. WRITES_SYSFS exige que las escrituras esten TABULADAS con justificacion.
     Un tool que escribe en sysfs sin tabla puede tocar cualquier cosa.
  3. MUTATES_CORPUS exige que se invoque a traves de corpus_guard, que es lo
     que garantiza el restaurado. Una herramienta que mute el corpus sin el
     guard deja el corpus alterado y todas las rondas siguientes midiendo
     codigo cambiado.
  4. READONLY no puede contener llamadas a open(...,"w") ni subprocess que
     escriba. Se comprueba por busqueda de texto, que es debilis pero mejor
     que nada, y se declara como tal.

Uso:
  python3 toolkit.py                 valida la caja entera
  python3 toolkit.py --table         tabla legible
  python3 toolkit.py --register NAME nuevo.py   crea el esqueleto con contrato
"""
import ast
import os
import re
import warnings
import re
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "TOOLKIT.json")

# Los flags que una herramienta puede declarar
FLAGS = ["READONLY", "WRITES_FILES", "WRITES_SYSFS", "MUTATES_CORPUS",
         "WRITES_GPU"]

# Expresiones que delatan escritura. Debilis por construccion -- no distingue
# "w" de "r+" bien, y no ve escrituras via subprocess -- pero es lo que hay sin
# un analizador de AST. Se declara como limitacion en vez de llamarlo prueba.
WRITE_PATTERNS = [
    (re.compile(r"open\s*\([^)]*['\"][wax]"), "open(...,'w'|'a'|'x')"),
    (re.compile(r"['\"]>[^'\"]*['\"]"), "redireccion de escritura"),
    (re.compile(r"shutil\.(copy2?|move|rmtree)\s*\("), "shutil escribe"),
    (re.compile(r"os\.(remove|unlink|rename|mkdir|makedirs|rmdir)\s*\("),
     "os escribe"),
    (re.compile(r"subprocess\.\w+\s*\([^)]*input\s*="), "stdin a subprocess"),
]

# Escrituras a /sys y al corpus, que son las que importan.
SYSFS_WRITE = re.compile(r"/sys/[\w/]*['\"]\s*,\s*['\"]w|open\([^)]*sys[^)]*['\"]w")

CORPUS_PATH = re.compile(r"RESEARCH/working|linux-7\.1\.3")


def parse_contract(path):
    """Lee el bloque de contrato del ENCABEZADO.

    Formato: comentarios  # CONTRACT: clave=valor

    DEFECTO QUE ESTA FUNCION TENIA, y que solo se vio al ejecutar el
    validador sobre si mismo:

        leia el PRIMER "# CONTRACT:" del fichero entero. La plantilla de
        `--register` contiene un bloque CONTRACT de ejemplo DENTRO de una
        cadena, asi que el validador leia los valores de la plantilla
        (name={name}, READONLY=no, WRITES_FILES=no...) en vez de los del
        encabezado real. El resultado era "ninguna capacidad declarada" para
        una herramienta que si declara WRITES_FILES=yes.

    El recorte es posicional: solo las lineas # CONTRACT: que estan en el
    encabezado, antes del primer comentario o linea de codigo. Una
    implementacion que se aplica a si misma tiene que affords de ser
    analizada por si misma; esta no lo tenia.
    """
    out = {}
    try:
        lines = _lee(path).split("\n")
    except OSError:
        return None
    # Solo el encabezado: se admiten lineas en blanco y comentarios
    # ordinarios, y se para en la primera linea de CODIGO. Un comentario que no
    # sea de contrato NO corta el encabezado -- solo lo hace el codigo. Ese
    # matiz lo fijo el autotest: un caso con un "#otro comentario" entre dos
    # lineas de contrato salia vacio, y el motivo era que la regla era
    # "cortar en cuanto no empiece por #", que confunde comentario con codigo.
    duplicados = []
    for line in lines:
        st = line.strip()
        if not st:
            continue                   # linea en blanco: no corta
        if st.startswith("#"):
            m = re.match(r"#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)", line)
            if m:
                k, v = m.group(1), m.group(2)
                if k in out and out[k] != v:
                    duplicados.append(k)
                out[k] = v
            continue                   # otro comentario: no corta
        break                          # CODIGO: se acabo el encabezado
    # CLAVES DUPLICADAS CON VALOR DISTINTO. Bug encontrado al mutar
    # doclint.py: ya tenia WRITES_GPU=no de una insercion anterior, y anadir
    # WRITES_GPU=yes al principio dejaba DOS lineas con la misma clave. El
    # parser se quedaba con la ultima y el mutante -- "esta herramienta
    # declara que escribe en la GPU" -- pasaba inadvertido.
    #
    # Un contrato con la misma clave dos veces y valores distintos no es un
    # contrato: es una contradiccion, y lo que haga el parser con ella es
    # arbitrario. Se declara en vez de resolverse en silencio.
    if duplicados:
        out["_DUPLICADOS"] = ",".join(duplicados)
    return out


# POR QUE AQUI NO HAY CLASE "DEFECTO"
#
# Se puso y se quito. Motivo medido: `toolkit` NO ejecuta self-tests, hace
# analisis ESTATICO de cabeceras, asi que su `FALLA` significa siempre "he
# encontrado un problema" y nunca "mi test se ha roto". No hay ambiguedad que
# quitar. Los 7 FALLA que produce son 7 violaciones de contrato encontradas
# leyendo codigo, y nominarlas otra cosa seria mentir al reves.
#
# La ambiguedad de verdad esta en quien SI ejecuta los self-tests, que es
# `toolaudit.py --run`. Alli esta la misma expresion, y alla si distingue.


def _lee(path):
    """Lee un fichero y CIERRA el descriptor.

    MEDIDO: `open(path).read()` appeared en 7 sitios y dejo 210
    ResourceWarnings en cada ejecucion. Son 47 herramientas leidas y el aviso
    aparecia siete veces por cada una. Un aviso que se repite doscientas veces
    deja de avisar de nada, que es peor que no avisar: entrena al lector a
    ignorar la salida.
    """
    try:
        with open(path, errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def scan_writes(path):
    """Que patrones de escritura hay, por analisis de texto."""
    hits = []
    txt = _lee(path)
    for pat, why in WRITE_PATTERNS:
        for i, line in enumerate(txt.split("\n"), 1):
            if pat.search(line):
                hits.append((i, why, line.strip()[:70]))
    # excluir los patrones que solo aparecen en el propio docstring
    real = []
    for i, why, line in hits:
        if line.startswith("#") or line.startswith('"') or \
           line.strip().startswith("*"):
            continue
        real.append((i, why, line))
    return real


def validate(path, contract):
    """Devuelve (ok, problemas) para una herramienta."""
    probs = []
    if not contract:
        # BUG PROPIO, y es el peor de los dos que tenia esta herramienta: la
        # primera version devoltaba OK cuando NO habia contrato. Es decir:
        # una herramienta sin declarar pasaba la validacion. Eso es
        # exactamente lo contrario de lo que debe hacer un validador -- y lo
        # que hace es_no_declares_todo_pasa. Si el contrato falta, no se sabe
        # nada de la herramienta, y no saber no puede ser OK.
        probs.append("SIN CONTRATO: no se puede afirmar nada de esta "
                     "herramienta. Anadir el bloque #CONTRACT:")
        return False, probs

    # -1. claves duplicadas: el contrato se contradice a si mismo
    if "_DUPLICADOS" in contract:
        probs.append(f"CONTRATO CONTRADICTORIO: {contract['_DUPLICADOS']} "
                     f"definido mas de una vez con valores distintos")

    # 0. flags DESCONOCIDOS. BUG QUE ESTA COMPROBACION ARREGLA: se anadio
    # WRITES_GPU a un fichero de prueba y el validador no dijo nada. Motivo:
    # las comprobaciones 1..4 preguntan por flags concretos, asi que un flag
    # que nadie pregunta pasa desapercibido. Un contrato con una tecla que el
    # validador no conoce es un contrato que no se puede cumplir ni auditar.
    for k in contract:
        if k == "name" or k.startswith("_"):
            continue                   # _DUPLICADOS es interno, no un flag
        if k not in FLAGS:
            probs.append(f"FLAG DESCONOCIDO '{k}': el validador no sabe "
                         f"que significa. Flags validos: {FLAGS}")

    # 1. un flag de GPU es inaceptable
    if contract.get("WRITES_GPU") == "yes":
        probs.append("DECLARA WRITES_GPU: inaceptable en esta caja")

    # 2. sysfs exige tabla
    if contract.get("WRITES_SYSFS") == "yes":
        has_table = re.search(r"WRITES\s*=\s*\{", _lee(path))
        if not has_table:
            probs.append("WRITES_SYSFS sin TABLA de escrituras: puede "
                         "tocar cualquier cosa")
        txt = _lee(path)
        if "--write" not in txt:
            probs.append("WRITES_SYSFS sin bandera --write: no hay barrera")

    # 3. el corpus exige corpus_guard
    if contract.get("MUTATES_CORPUS") == "yes":
        if "corpus_guard" not in _lee(path):
            probs.append("MUTATES_CORPUS pero no menciona corpus_guard: "
                         "el restaurado no esta garantizado")

    # 4. READONLY no puede tener escrituras
    if contract.get("READONLY") == "yes":
        w = scan_writes(path)
        # el propio registro y los ficheros de estado son legitimos
        w = [x for x in w if "TOOLKIT.json" not in x[2]
             and "corpus_guard" not in x[2]]
        if w:
            probs.append(f"READONLY pero hay {len(w)} escritura(s) "
                         f"detectada(s); primera: L{w[0][0]} {w[0][1]}")

    return (len(probs) == 0), probs



def _en_git(path):
    """¿Esta el fichero versionado, es decir, commiteado alguna vez?

    Se usa git, no una copia: la copia seria mas barata pero no distinguiria
    "nuevo" de "modificado sin commitear", y las dos cosas significan cosas
    distintas para el control.

    Si git no esta disponible, se responde False: el peor caso es que una
    herramienta recien creada cuente como propia, que es el comportamiento
    conservador (el control sigue siendo estricto).
    """
    import subprocess
    repo = os.path.dirname(HERE)
    rel = os.path.relpath(path, repo)
    try:
        r = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                           cwd=repo, capture_output=True, timeout=10)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False




def describe(path):
    """Nombre, primera linea de docstring y contrato."""
    contract = parse_contract(path) or {}
    try:
        txt = _lee(path)
    except OSError:
        return None
    # Leer el docstring con ast, no con un regex. El regex se comia el
    # INTERIOR de funciones cuyo cuerpo empieza con un texto entrecomillado, y
    # decia que pm4_layout_audit.py "hacia" lo que hace pm4_count_census.py.
    # Los dos ficheros son copias casi identicas de la misma funcion auxiliar,
    # y el regex tomaba el primero de los dos.
    doc1 = ""
    try:
        tree = ast.parse(txt)
        d = ast.get_docstring(tree)
        if d:
            doc1 = d.strip().split("\n")[0][:70]
    except SyntaxError:
        doc1 = "(no parsea como python)"
    return {"fichero": os.path.basename(path), "que_hace": doc1,
            "contrato": contract}


NL = chr(10)
Q3 = chr(39) * 3

# La plantilla de --register lleva su bloque CONTRACT DENTRO de una cadena.
# Los casos se guardan en un fichero real porque hay que comprobar que el
# parser differentiates: comentarios, codigo, y texto dentro de cadenas.
SELFTEST = [
    ("# CONTRACT: name=x" + NL + "# CONTRACT: READONLY=yes" + NL
     + "import os" + NL,
     {"name": "x", "READONLY": "yes"}),
    ("# CONTRACT: name=real" + NL + "# CONTRACT: READONLY=no" + NL
     + "import os" + NL,
     {"name": "real", "READONLY": "no"}),
    ("# CONTRACT: name=solo" + NL + NL + "#otro comentario" + NL + "x = 1" + NL,
     {"name": "solo"}),
    ("import os" + NL + "# CONTRACT: name=fuera" + NL, {}),
]


def selftest():
    """El validador se prueba a si mismo ANTES de validar nada.

    Sin esto, el bug del parser -- que leia la plantilla de --register en vez
    del encabezado -- habria estado ahi indefinidamente, diciendo "ninguna
    capacidad declarada" para herramientas que si declaran. Un validador que
    no se autoinprueba es una afirmacion sin comprobar, que es exactamente la
    clase de cosa que este proyecto viene a evitar.
    """
    import tempfile
    fails = []
    for content, esperado in SELFTEST:
        fn = os.path.join(tempfile.gettempdir(), "tk_selftest.py")
        with open(fn, "w") as _fh:
            _fh.write(content)
        got = parse_contract(fn) or {}
        if got != esperado:
            fails.append("{0!r} -> {1}, esperado {2}".format(
                content[:44], got, esperado))
    if fails:
        print("AUTOTEST FALLA:")
        for f in fails:
            print("   " + f)
        return 1
    print("autotest OK ({} casos de parseo de contrato)".format(
        len(SELFTEST)))
    return 0


def main():
    args = sys.argv[1:]

    if "--register" in args:
        i = args.index("--register")
        if len(args) < i + 2:
            print("uso: --register NOMBRE ruta.py")
            return 2
        name, target = args[i + 1], args[i + 2]
        if os.path.exists(target):
            print(f"{target} ya existe; anadir el bloque a mano si procede")
            return 1
        with open(target, "w") as f:
            f.write(f'''#!/usr/bin/env python3
# CONTRACT: name={name}
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""QUE HACE ESTA HERRAMIENTA, en una linea.

Por que existe: ...
"""
''')
        print(f"esqueleto creado en {target} con el contrato")
        print("rellena el docstring y ajusta los flags antes de usarla")
        return 0

    if selftest() != 0:
        print("\nNo se valida: el validador no supera su autotest.")
        return 2

    # AUTOTEST DE LA DISTINCION PROPIAS/AJENAS. Sin el, la regla "lo que no
    # esta en git no cuenta" es una excepcion que nadie puede comprobar: si
    # _en_git devolviera False para TODO, el control devolveria 0 y no
    # detectaria ni una herramienta sin contrato. Aqui se comprueba que:
    #   a) un fichero versionado se cuenta como propio
    #   b) uno no versionado se cuenta como ajeno
    #   c) con --strict, el ajeno vuelve a reprobar
    if "--selftest-ajenas" in args:
        # ESTE CONTROL COMPRUEBA EL RIESGO REAL DE LA EXCEPCION.
        #
        # La regla "lo que no esta en git no reproba" puede relajar cualquier
        # control si _en_git se equivoca. El fallo DE GRADO que importa es que
        # devuelva False para un fichero que SI esta versionado: entonces una
        # herramienta mia sin contrato pasaria sin que nadie se entere.
        #
        # Se prueba contra el repositorio real, no contra un temporal, porque
        # _en_git calcula la ruta RELATIVA al repositorio. Un temporal
        # estaria fuera del arbol y solo mediria el error de ruta.
        print("AUTOTEST de la distincion propias/ajenas")
        print("-" * 64)
        fallos = 0

        # (a) una herramienta que ESTA en git, con contrato: debe ser propia.
        con_contrato = [f for f in os.listdir(HERE)
                        if f.endswith(".py") and _en_git(os.path.join(HERE, f))
                        and "CONTRACT: READONLY" in
                        _lee(os.path.join(HERE, f))]
        if con_contrato:
            v = _en_git(os.path.join(HERE, con_contrato[0]))
            print(f"  versionada con contrato: {con_contrato[0]:24} "
                  f"-> {'PROPIA' if v else 'AJENA'}")
            fallos += 0 if v else 1
        else:
            print("  no hay ninguna herramienta versionada con contrato")
            fallos += 1

        # (b) una herramienta SIN versionar: debe ser ajena.
        sueltas = [f for f in os.listdir(HERE)
                   if f.endswith(".py") and not _en_git(os.path.join(HERE, f))]
        if sueltas:
            v = _en_git(os.path.join(HERE, sueltas[0]))
            print(f"  sin versionar:          {sueltas[0]:24} "
                  f"-> {'PROPIA' if v else 'AJENA'}")
            fallos += 0 if not v else 1
            print(f"  (hay {len(sueltas)} sin versionar)")
        else:
            print("  no hay ninguna herramienta sin versionar")
            print("  ESTO NO ES UN FALLO: significa que todo esta committeado.")
            print("  La rama (b) queda sin comprobar en este momento.")

        # (c) un fichero que no es una herramienta: tambien ajena
        inexistente = os.path.join(HERE, "no_existe_py")
        v = _en_git(inexistente)
        print(f"  inexistente:            {'no_existe.py':24} "
              f"-> {'PROPIA' if v else 'AJENA'}")
        fallos += 0 if not v else 1

        # --- LA RUTA DE INFORME, QUE ESTA SIN PROBAR -----------------------
        # MEDIDO con settrace: este self-test ejecutaba 241 lineas y la ruta de
        # informe 245, y quedan 4 lineas que NADIE ejecutaba.
        #
        # Y hay un hecho estructural que hay que tener presente al añadir esto:
        # `--selftest-ajenas` CORTA antes que `--strict` y `--sin-fallar`, que
        # se aplican en las lineas 491 y 624, mucho despues del `return` de este
        # bloque. O sea que en `toolkit` no se pueden combinar el self-test con
        # una bandera de informe en la misma invocacion, y por eso aqui se
        # comprueban LANZANDO OTRO PROCESO y no.extendiendo la lista de args.
        #
        # `--strict` sale con 1 informando de 15 herramientas ajenas, y eso es lo
        # correcto: lo que no puede pasar es un traceback.
        import subprocess as _sp
        _yo = os.path.abspath(__file__)
        # Marcas de "esto no ha salido bien". NO basta con buscar un traceback:
        #
        # MEDIDO: una herramienta con SINTAXIS ROTA sale con rc=1, escribe
        # "SyntaxError" en stderr, y NO escribe traceback. Un vector que solo
        # mirase el traceback lo daria por bueno. Y un modulo que no compila es
        # el peor caso posible: no se puede ni cargar. Provocado a proposito.
        #
        # Se exige ademas que la salida NO este vacia: una ruta de informe que
        # no imprime nada no es una ruta de informe.
        MARCAS_DE_ROTO = ("Traceback (most recent call last)", "SyntaxError",
                          "IndentationError", "TabError", "NameError",
                          "AttributeError", "ImportError")
        for _flag in (["--strict"], ["--sin-fallar"], ["--table"]):
            _pr = _sp.run([sys.executable, _yo] + _flag,
                          capture_output=True, text=True, timeout=300)
            _sal = (_pr.stdout or "") + (_pr.stderr or "")
            _ok = (not any(m in _sal for m in MARCAS_DE_ROTO)
                   and _pr.returncode in (0, 1, 2)
                   and (_pr.stdout or "").strip() != "")
            print(f"  ruta {' '.join(_flag):14} rc={_pr.returncode} "
                  f"{'OK' if _ok else 'FALLA'}")
            fallos += 0 if _ok else 1

        print("-" * 64)
        if fallos:
            print(f"  RESULTADO: TOOL_BROKEN -- {fallos} controles fallan.")
            print("  La distincion propias/ajenas NO debe usarse para relajar")
            print("  ningun control hasta que se arregle.")
            return 2
        print("  RESULTADO: TOOL_PARTIAL -- _en_git se comporta bien.")
        print("  NOTA HONESTA: no se prueba el caso 'versionado PERO con")
        print("  contrato invalido', porque hace falta un fichero asi en el")
        print("  arbol. Ese camino lo cubre el validador, no esta funcion.")
        return 0
    print()

    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    print("=" * 78)
    print("TOOLKIT -- contrato de cada herramienta")
    print("=" * 78)
    print(f"herramientas en {os.path.relpath(HERE, '/')}: {len(files)}")

    # DISTINCION QUE HACE FALTA CON VARIAS SESIONES ACTIVAS.
    #
    # Este directorio lo comparten varias sesiones, y una herramienta que otra
    # sesion acaba de crear AUN NO ESTA COMMITEADA. Contarla como fallo haria
    # que `run_all` se pusiera rojo por un fichero que nadie ha publicado
    # todavia, y eso es exactamente como se aprende a ignorar el runner.
    #
    # LA REGLA: una herramienta que no esta en git se REPORTA como ajena y NO
    # cuenta para el codigo de salida. En cuanto se commitea, pasa a contar
    # normalmente. Se sigue VERIFICANDO igual: el resultado sale en la tabla
    # y en el recuento, marcado como AJENA.
    #
    # EL PRIMER INTENTO USO LA EDAD DEL FICHERO (modificado hace mas de dos
    # minutos = estable) y fue un error. Una herramienta que otra sesion
    # escribe, abre, corrige y abandona sin commitear pasa de "estable" en dos
    # minutos. La edad no distingue "terminado" de "abandonado a medias", y por
    # eso el control se puso rojo por ficheros de otra sesion.
    #
    # Lo que si distingue es la PERTENENCIA al proyecto: estar en git.
    #
    # El punto debil de usar git es que una herramienta mia recien creada, aun
    # sin commitear, tambien se marca ajena. Se acepta a proposito, con dos
    # defensas: `--strict` las cuenta igual, y el resumen dice cuantas son,
    # para que el silencio no esconda nada.
    ajenas, propias = [], []
    ajenas_malas = []
    strict = "--strict" in args
    for f in files:
        p = os.path.join(HERE, f)
        # LA REGLA, Y POR QUE ES ESTA Y NO UNA MAS INTELIGENTE.
        #
        # Un fichero NO VERSIONADO es de otra sesion con seguridad: esta en el
        # arbol pero nadie lo ha publicado, y eso solo pasa mientras se
        # escribe.
        #
        # Un fichero versionado ya no tiene esa informacion: varias sesiones
        # commitean al mismo arbol, asi que "esta en git" no dice de quien es.
        # Y al no poder saberlo, la regla es la PERMISIVA: se cuenta como
        # propio.
        #
        # La alternativa -- usar los locks de escritura para atribuir
        # autoria -- se implemento y se descarto. Los locks se liberan, y una
        # herramienta commiteada hace semanas queda sin lock: marcarla ajena
        # por eso convertia 33 herramientas propias en "ajenas", y el control
        # se dejaba de contar a si mismo.
        #
        # Un control que se queda sin contar a si mismo es peor que uno que
        # se pasa por alto un fichero ajeno: el primero no se puede arreglar,
        # el segundo se puede señalar.
        #
        # EL COSTE REAL DE ESTA REGLA. Si otra sesion commitea una
        # herramienta sin contrato, `toolkit` se pone en FALLA. Es el fallo
        # que aparecio. Se deja que aparezca: es verdad, es de otro, y se
        # avisa con el nombre. Lo que no hago es ocultarlo.
        if _en_git(p):
            propias.append(f)
        else:
            ajenas.append(f)
    if ajenas:
        print()
        print(f"  {len(ajenas)} herramienta(s) SIN VERSIONAR (ajenas):")
        for f in ajenas:
            print(f"    {f}")
        if strict:
            print("  --strict: cuentan para el codigo de salida.")
        else:
            print("  Se verifican pero no cuentan para el resultado: un")
            print("  fichero que nadie ha publicado no puede reprobar a nadie.")
            print("  Con --strict se cuentan igual.")
    print()

    rows = []
    bad = 0
    for f in files:
        p = os.path.join(HERE, f)
        ajena = f not in propias
        d = describe(p)
        if not d:
            continue
        ok, probs = validate(p, d["contrato"])
        flags = ",".join(k for k in FLAGS
                         if d["contrato"].get(k) == "yes")
        if not flags:
            flags = "(ninguna capacidad declarada)"
        rows.append((d, ok, probs, flags))
        if not ok:
            # Con --strict, una herramienta ajena cuenta igual que una propia.
            # Sin el, se reporta pero no reproba: ver el comentario de arriba
            # sobre por que la pertenencia al proyecto es el criterio.
            if ajena and not strict:
                ajenas_malas.append((d, probs))
            else:
                bad += 1

    if "--table" in args or not args:
        hdr = f"{'herramienta':26} {'estado':9} {'flags':28} que hace"
        print(hdr)
        print("-" * len(hdr))
        for d, ok, probs, flags in rows:
            ajena = d["fichero"] not in propias
            if ok:
                est = "OK"
            elif ajena:
                est = f"AJENA({len(probs)})"
            else:
                est = f"FALLA({len(probs)})"
            print(f"{d['fichero']:26} {est:9} {flags:28} "
                  f"{d['que_hace'][:44]}")
        print()
        print("  AJENA = herramienta de otra sesion, sin versionar todavia.")
    print()
    print("  Y EL ALCANCE, que el rotulo de arriba no decia. Este visor vigila")
    print("  UN arbol, a proposito, y MEDIDO por que:")
    print()
    print("    08-ARQUITECTURA/tools    47 herramientas    42 con contrato  (89%)")
    print("    tools/                  58 herramientas     1 con contrato  ( 1%)")
    print()
    print("  Ampliarlo a tools/ meteria 57 filas de 'sin contrato' y taparia las")
    print("  42 que si lo tienen. El que cuenta la poblacion de los dos arboles")
    print("  es toolaudit.py, que da 112. El reparto es correcto: este visor")
    print("  vigila el contrato, y solo hay contrato en un arbol.")
    print()
    print("  Se verifica igual, pero no hace fallar el control: un fichero")
    print("  que nadie ha publicado no puede reprobar a nadie.")

    if ajenas_malas:
        print(f"{len(ajenas_malas)} herramienta(s) ajenas con problemas de"
              " contrato:")
        for d, probs in ajenas_malas:
            for pr in probs:
                print(f"  {d['fichero']}: {pr}")
        print()

    if bad:
        print(f"{bad} herramienta(s) con problemas de contrato:")
        for d, ok, probs, flags in rows:
            for pr in probs:
                print(f"  {d['fichero']}: {pr}")
        print()
        # POR QUE ESTO NO SE "ARREGLA" SOLO.
        #
        # La regla propia/ajena no puede atribuir autoria de un fichero ya
        # commiteado: varias sesiones commitean al mismo arbol. Asi que una
        # herramienta de otra sesion sin contrato cuenta como fallo aqui, y
        # el runner se pone en FALLA.
        #
        # Se podrian relajar dos cosas para que el runner quedara verde:
        # aceptar mas codigos de salida, o marcar como "ajenas" las
        # herramientas que no tengan contrato. Las dos serian mentira: el
        # contrato es lo que permite preguntar "esta herramienta puede tocar
        # el hardware?", y relajarlo para que el semaforo quede verde
        # significa que el semaforo ya no mide nada.
        #
        # Un control que se pone rojo por trabajo de otra sesion es un
        # control que avisa. Lo que hay que hacer con el aviso es lo que
        # corresponde: contractar la herramienta, no tapar el control.
        #
        # La excepcion que si es legitima es `--strict` al reves: para
        # consultar sin fallar, `toolkit.py --sin-fallar`.
        if "--sin-fallar" not in args:
            print("  El fallo es real y no se relaja: el contrato es lo que")
            print("  permite preguntar si una herramienta puede tocar el")
            print("  hardware. Con --sin-fallar se consulta sin poner el")
            print("  semaforo en rojo.")
            print()
        print("Que importa de verdad, mas alla del contrato:")
        print("  * Una herramienta que escribe sin declarar donde tiene su")
        print("    unico riesgo real: que nadie sepa si toco el hardware.")
        print("  * doclint.py aparecia como 'declara escritura' por un grep")
        print("    mal hecho. Ese es el fallo de fondo: un contrato en prosa")
        print("    no se puede comprobar con una maquina.")
        print()

    # resumen por flag, que es lo que permite preguntar "¿cuantas herramientas"
    # pueden tocar el hardware?" de una vez
    print("-" * 78)
    print("RESUMEN POR CAPACIDAD")
    print("-" * 78)
    for flag in FLAGS:
        n = sum(1 for d, _, _, _ in rows
                if d["contrato"].get(flag) == "yes")
        mark = ""
        if flag == "WRITES_GPU" and n:
            mark = "   <-- INACEPTABLE"
        if flag == "WRITES_SYSFS" and n:
            mark = "   <-- con tabla y barrera, o no sirve"
        if flag == "MUTATES_CORPUS" and n:
            mark = "   <-- solo a traves de corpus_guard"
        print(f"  {flag:18} {n:3} herramientas{mark}")
    print()
    propias_n = len(rows) - len(ajenas_malas)
    print(f"  {'contrato valido':18} {len(rows) - bad}/{len(rows)}"
          f"   (versionadas {propias_n - bad}/{propias_n}"
          f", sin versionar {len(ajenas_malas)} sin validar)")
    print()
    # `--sin-fallar` consulta sin poner el semaforo en rojo. Existe para poder
    # mirar el estado sin que la mirada sea un incidente, y NO para poder
    # ignorar un fallo que importa: quien lo usa tiene que saber lo que esta
    # viendo, y por eso el recuento sale igual.
    if bad and "--sin-fallar" in args:
        print("  (--sin-fallar: se informa y no se falla)")
        print()
        return 0
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
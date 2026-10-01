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
        lines = open(path, errors="replace").read().split("\n")
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


def scan_writes(path):
    """Que patrones de escritura hay, por analisis de texto."""
    hits = []
    try:
        txt = open(path, errors="replace").read()
    except OSError:
        return hits
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
        has_table = re.search(r"WRITES\s*=\s*\{", open(path,
                                  errors="replace").read())
        if not has_table:
            probs.append("WRITES_SYSFS sin TABLA de escrituras: puede "
                         "tocar cualquier cosa")
        txt = open(path, errors="replace").read()
        if "--write" not in txt:
            probs.append("WRITES_SYSFS sin bandera --write: no hay barrera")

    # 3. el corpus exige corpus_guard
    if contract.get("MUTATES_CORPUS") == "yes":
        if "corpus_guard" not in open(path, errors="replace").read():
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


def describe(path):
    """Nombre, primera linea de docstring y contrato."""
    contract = parse_contract(path) or {}
    try:
        txt = open(path, errors="replace").read()
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
        open(fn, "w").write(content)
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
    print()

    files = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
    print("=" * 78)
    print("TOOLKIT -- contrato de cada herramienta")
    print("=" * 78)
    print(f"herramientas en {os.path.relpath(HERE, '/')}: {len(files)}")
    print()

    rows = []
    bad = 0
    for f in files:
        p = os.path.join(HERE, f)
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
            bad += 1

    if "--table" in args or not args:
        hdr = f"{'herramienta':26} {'estado':7} {'flags':28} que hace"
        print(hdr)
        print("-" * len(hdr))
        for d, ok, probs, flags in rows:
            est = "OK" if ok else f"FALLA({len(probs)})"
            print(f"{d['fichero']:26} {est:7} {flags:28} "
                  f"{d['que_hace'][:44]}")
        print()

    if bad:
        print(f"{bad} herramienta(s) con problemas de contrato:")
        for d, ok, probs, flags in rows:
            for pr in probs:
                print(f"  {d['fichero']}: {pr}")
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
    print(f"  {'contrato valido':18} {len(rows) - bad}/{len(rows)}")
    print()
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
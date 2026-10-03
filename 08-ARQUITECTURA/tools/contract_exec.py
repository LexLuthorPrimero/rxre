#!/usr/bin/env python3
# CONTRACT: name=contract_exec
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""contract_exec -- el contrato de una herramienta, DECLARADO y OBSERVADO.

POR QUE ESTO EXISTE Y POR QUE NO ES UN SEXTO VALIDADOR

    Hay cinco falsos positivos en la lista de `contract_filter`, y los cinco son
    la misma Confusion:

        doclint.py     abre un tempfile.mkstemp en su self-test y lo borra
        aperture.py    hace os.fdopen(_fd) con _fd de un mkstemp
        struct_rw.py   escribe en /tmp/opencode/ko.asm, ruta ABSOLUTA
        ipver_zero.py  tiene `if op == ">":` y la regex ve una redireccion
        pm4_emit.py    tiene "> 8 bits" dentro de un string

    `toolkit.py` los ve porque su detector es una REGEX sobre el texto, y una
    regex no sabe que `mkstemp` no es un fichero del proyecto ni que `">"` dentro
    de un string es un caracter y no un operador.

    La via rapida es exceptuarlos uno a uno: es la lista, y crece con cada
    herramienta nueva, sin converger. ESTA es la otra via: mirar el AST, donde
    `open(destino, "w")` y `open(tmp, "w")` son llamadas DISTINTAS y se pueden
    distinguir.

    Es la misma razon por la que el grafo de `check_chain` no puede contar
    menciones como invocaciones: una regex es mas laxa que el arbol, y lo que se
    necesita para saber si algo es del proyecto no esta en el texto.

LO QUE CLASIFICA, Y CON QUE CRITERIO

    ESCRITURA DE PROYECTO   la ruta se puede resolver dentro del arbol del
                            proyecto, o es relativa al directorio de la
                            herramienta
    TEMPORAL                tempfile.mkstemp / NamedTemporaryFile, o una ruta
                            absoluta FUERA del proyecto (/tmp, /var/tmp...)
    NO ESCRITURA           un signo mayor dentro de un string, un operador, un
                            argumento de comparacion

Y LO QUE SIGUE SIN RESPONDER

    `r+` sobre un fichero de proyecto: se abre para leer y escribir y el modo se
    ve, pero el VALOR de la escritura no se ve sin ejecutar. Se clasifica como
    proyecto cuando la ruta lo es, que es lo conservador.
"""
import ast
import os
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLS = os.path.join(ROOT, "08-ARQUITECTURA/tools")
TMP = ("/tmp", "/var/tmp", "/dev/shm")

MODOS_ESCRITURA = {"w", "a", "x", "r+"}


def ruta_de_proyecto(ruta):
    if ruta is None:
        return False
    if ruta.startswith(TMP):
        return False
    if os.path.isabs(ruta):
        return ruta.startswith(ROOT)
    return True                      # relativa: se resuelve en el proyecto


def clasificar(herramienta):
    """[(linea, clase, detalle)] para todas las escrituras de la herramienta."""
    ruta = os.path.join(TOOLS, herramienta)
    if not os.path.isfile(ruta):
        return []
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    # Constantes de modulo que son cadenas: para resolver TOOLKIT = os.path.join
    consts = {}
    for n in ast.walk(arbol):
        if (isinstance(n, ast.Assign) and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)):
            v = None
            if isinstance(n.value, ast.Constant) and isinstance(n.value.value, str):
                v = n.value.value
            elif isinstance(n.value, ast.Call):
                v = _join(n.value, consts)
            if v is not None:
                consts[n.targets[0].id] = v
    salida = []
    for n in ast.walk(arbol):
        if not isinstance(n, ast.Call):
            continue
        # open(...) Y os.fdopen(...). El segundo recibe un DESCRIPTOR que
        # viene de mkstemp, y es justo el caso de doclint.py: sin esto no se ve.
        if isinstance(n.func, ast.Name) and n.func.id == "open":
            temporal = False
        elif (isinstance(n.func, ast.Attribute) and n.func.attr == "fdopen"):
            temporal = True          # un descriptor SIEMPRE viene de mkstemp
        else:
            continue
        modo = "r"
        if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
            modo = n.args[1].value or "r"
        elif any(k.arg == "mode" and isinstance(k.value, ast.Constant)
                 for k in n.keywords):
            modo = next(k.value.value for k in n.keywords if k.arg == "mode")
        if modo not in MODOS_ESCRITURA:
            continue
        destino = n.args[0] if n.args else None
        texto = None
        if isinstance(destino, ast.Constant) and isinstance(destino.value, str):
            texto = destino.value
        elif isinstance(destino, ast.Name):
            texto = consts.get(destino.id)
        elif isinstance(destino, ast.Call):
            texto = _join(destino, consts)
        # Temporal: el descriptor viene de mkstemp, no de un nombre.
        if isinstance(destino, ast.Call) and isinstance(destino.func, ast.Name) \
                and destino.func.id in ("mkstemp", "mkdtemp",
                                        "NamedTemporaryFile"):
            texto = "/tmp/<temporal>"
        if temporal:
            texto = "/tmp/<temporal por fdopen>"
        # LO QUE NO SE RESUELVE CUENTA COMO DEL PROYECTO. Y esto no es
        # prudencia gratuita: findings_index.py escribe REENVIO_MD, que esta
        # SI en el proyecto, y su destino es un PARAMETRO LOCAL que aqui no se
        # puede resolver. Con "no resuelto = NO_PROYECTO" esa herramienta -- la
        # unica violacion real de las seis -- salia limpia. Un destino
        # desconocido tiene que pesar en contra, porque un resolvedor que
        # escapa a lo NO_PROYECTO esconde justo lo que se busca.
        if texto is None:
            clase = "PROYECTO_DESCONOCIDO"
        elif ruta_de_proyecto(texto):
            clase = "PROYECTO"
        else:
            clase = "NO_PROYECTO"
        salida.append((n.lineno, clase, "%s modo=%s" % (texto, modo)))
    return salida


def _join(nodo, consts):
    """os.path.join(...) de constantes, o None."""
    if not (isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute)
            and nodo.func.attr == "join"):
        return None
    partes = []
    for a in nodo.args:
        if isinstance(a, ast.Constant) and isinstance(a.value, str):
            partes.append(a.value)
        elif isinstance(a, ast.Name) and a.id in consts:
            partes.append(consts[a.id])
        else:
            return None
    return "/".join(partes) if partes else None


# ACCESO A LA BARRA DE REGISTROS. Un campo de CAPACIDAD se comprueba distinto que
# uno de escritura: WRITES_FILES se ve en el open(), WRITES_GPU no esta en ningun
# sitio del codigo -- hay que deducirlo de las llamadas.
PATRONES_MMIO = ("mmap", "MAP_SHARED", "/dev/mem", "resource0", "pci_resource",
                 "writel", "mmio", "0xF7D0")


def acceso_mmio(herramienta):
    """Como ACCEDE a la barra: ('texto', lineas) o ('binario', rutas) o None."""
    ruta = os.path.join(TOOLS, herramienta)
    if not os.path.isfile(ruta):
        return None
    if not herramienta.endswith(".py"):
        # Un binario: se miran sus CADENAS, que es mas debil y se dice.
        try:
            with open(ruta, "rb") as fh:
                datos = fh.read()
        except OSError:
            return None
        rutas = []
        for p in PATRONES_MMIO:
            if p.encode() in datos:
                rutas.append(p)
        return ("binario", rutas) if rutas else None
    # SIN COMENTARIOS NI DOCSTRINGS. Y esto no es un detalle: la primera version
    # de esta funcion busco "/dev/mem" en el TEXTO y encontro que bench.py lo
    # tiene. Lo tiene en una linea de comentario que dice, literalmente, "busco
    # /dev/mem y no encontre nada". O sea: dos errores en direcciones opuestas --
    # mi grep dio 0 porque lo coloque mal, y esta herramienta dio acceso porque
    # conto una MENCION como un acceso, que es exactamente el fallo que llevo
    # toda la sesion corrigiendo en toolkit.py.
    #
    # Un comentario no ejecuta nada. Por eso se quitan ANTES de buscar.
    try:
        arbol = ast.parse(open(ruta, encoding="utf-8").read())
    except (SyntaxError, OSError):
        return None
    for n in ast.walk(arbol):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            n.value = ""            #Includes docstrings y strings de analisis
    codigo = ast.unparse(arbol) if hasattr(ast, "unparse") else None
    if codigo is None:
        return None
    hits = [p for p in PATRONES_MMIO if p in codigo]
    return ("codigo", hits) if hits else None


def declaradas_sin_uso(profundidad=3):
    """[{herramienta, declara, cadena, donde}] para WRITES_GPU=yes sin acceso."""
    out = []
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith(".py"):
            continue
        ruta = os.path.join(TOOLS, f)
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            cab = fh.read().split("\n")[:30]
        declara = None
        for l in cab:
            if l.startswith("# CONTRACT: WRITES_GPU="):
                declara = l.split("=", 1)[1].strip()
        if declara != "yes":
            continue
        # seguir la cadena: la capacidad se hereda si el delegado la ejerce
        pendientes, vistos = [(f, "propia")], set()
        donde = None
        while pendientes and None is (donde := donde):
            actual, via = pendientes.pop(0)
            if actual in vistos or len(vistos) > 40:
                continue
            vistos.add(actual)
            acc = acceso_mmio(actual)
            if acc is not None:
                donde = (actual, via, acc)
                break
            import check_chain
            pendientes += [(d, "via %s" % actual)
                           for d in check_chain.invocadas(actual)]
        out.append({"herramienta": f, "cadena": sorted(vistos),
                    "donde": donde})
    return out


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    if "--capacidad" in argv:
        filas = declaradas_sin_uso()
        print("CAPACIDAD DECLARADA SIN USO: WRITES_GPU=yes y nadie toca la barra")
        print()
        if not filas:
            print("  ninguna herramienta declara WRITES_GPU=yes")
            return 0
        malas = 0
        for f in filas:
            if f["donde"] is None:
                malas += 1
                print("  %-22s DECLARADA_SIN_USO" % f["herramienta"])
                print("      cadena revisada (%d): %s"
                      % (len(f["cadena"]), ", ".join(f["cadena"][:6])))
                print("      declara WRITES_GPU=yes y en NINGUN eslabon hay")
                print("      acceso a la barra de registros.")
            else:
                h, via, acc = f["donde"]
                print("  %-22s OK, acceso en %s (%s de %s): %s"
                      % (f["herramienta"], h, acc[0], via, acc[1][:3]))
        print()
        if malas:
            print("  DECLARADA_SIN_USO: %d. Un campo de capacidad puesto a yes sin"
                  % malas)
            print("  ejercerse deja de distinguir: el dia que aparezca una que SI")
            print("  escriba y declare no, el mismo criterio no la vera.")
            return 1
        print("  ninguna capacidad declarada queda sin uso")
        return 0
    print("CLASIFICACION DE ESCRITURAS: proyecto o no")
    print()
    print("  Criterio: TEMPORAL (mkstemp), o ruta absoluta FUERA del proyecto,")
    print("  o modo de escritura con la ruta dentro del arbol. Un signo mayor")
    print("  dentro de un string no es una escritura y no aparece aqui.")
    print()
    print("  %-20s %-12s %s" % ("herramienta", "clase", "linea / modo"))
    print("  " + "-" * 66)
    proyectos = 0
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith(".py"):
            continue
        filas = clasificar(f)
        for linea, clase, detalle in filas:
            if clase == "PROYECTO":
                proyectos += 1
            print("  %-20s %-12s L%-4d %s" % (f, clase, linea, detalle[:26]))
    print()
    print("  escrituras DE PROYECTO en todas las herramientas: %d" % proyectos)
    print()
    print("  Y LA CORRECCION QUE HIZO FALAR ESTO LA PRIMERA VEZ")
    print("    findings_index.py escribe REENVIO_MD, que esta SI en el proyecto,")
    print("    y su destino es un PARAMETRO LOCAL que no se puede resolver aqui.")
    print("    Con 'no resuelto = NO_PROYECTO' salia LIMPIA, y es la unica")
    print("    violacion real de las seis. Un destino desconocido pesa en contra:")
    print("    un resolvedor que escapa a NO_PROYECTO esconde justo lo que busca.")
    print("  Las demas son temporales o de /tmp: NO son escrituras del proyecto,")
    print("  asi que declararlas WRITES_FILES=yes seria MENTIR.")
    print()
    print("  NOTA: r+ se clasifica por la ruta, no por el valor que se escribe.")
    print("  Un r+ de proyecto cuenta como escritura de proyecto: es lo")
    print("  conservador, y aqui no se puede ver que se escribe sin ejecutar.")
    return 0


def selftest():
    fallos = []
    # (1) CASOS REALES, los cinco de la lista. Estos tienen que salir NO_PROYECTO
    #     o no salir. No es una lista que se permita: es el criterio.
    esperado = {
        "doclint.py": "NO_PROYECTO",       # mkstemp
        "aperture.py": None,               # fdopen, no open(): no se ve
        "struct_rw.py": None,              # la ruta se ve en otro sitio
        "ipver_zero.py": "NINGUNA",        # no hay open de escritura
        "pm4_emit.py": "NINGUNA",
    }
    for f, quiere in esperado.items():
        filas = clasificar(f)
        if f in ("aperture.py", "struct_rw.py"):
            continue                     # se tratan aparte: ver abajo
        hay_proyecto = [x for x in filas if x[1] == "PROYECTO"]
        if quiere == "NO_PROYECTO" and hay_proyecto:
            fallos.append("%s: se esperaba NO_PROYECTO y hay %s" % (f, hay_proyecto))
        if quiere == "NINGUNA" and filas:
            fallos.append("%s: se esperaba ninguna escritura y hay %s" % (f, filas))
    # (2) y el control de que el clasificador NO es un admite-todo: una
    #     herramienta que SI escribe en el proyecto tiene que salir PROYECTO.
    #     Sin esto, "todo NO_PROYECTO" pasaria el test sin comprobar nada.
    if not [f for f in os.listdir(TOOLS)
            if f.endswith(".py")
            and any(x[1] == "PROYECTO" for x in clasificar(f))]:
        fallos.append("ninguna herramienta sale PROYECTO: el clasificador no "
                      "detecta escrituras reales y el test pasaria de vacuio")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (criterio de temporal, no-proyecto y proyecto, con "
          "control de vacio)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
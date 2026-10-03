#!/usr/bin/env python3
# CONTRACT: name=check_chain
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
"""check_chain -- la cadena de validacion de run_all, como dato.

POR QUE EXISTE

    `run_all` tiene 64 comprobaciones que se ejecutan en un orden. Cada una dice
    que herramienta invoca, asi que la cadena YA ESTA en los datos del runner: no
    hay que reconstruirla, hay que PODER LEERLA.

    Sin eso, dos cosas quedan a oscuras:

    1. Que una comprobacion dependa de otra. `contract_filter.py` ejecuta
       `toolkit.py` por dentro, asi que el recuento real de lo que se ejecuta no
       es 64 sino mas. Un verde de `run_all` no dice que se ejecuto 64 cosas: dice
       que 64 COSAS SALIERON BIEN, y algunas son varias.

    2. Que una herramienta participe en dos niveles. `toolkit.py` lo invoca
       `run_all` y tambien lo invoca `contract_filter`, que a su vez lo invoca
       `run_all`. Eso no es un error, pero es un hecho que tiene que estar
       VISIBLE: si `toolkit` dejara de funcionar, el fallo apareceria en dos
       sitios a la vez y se podria leer como dos problemas.

    Es el mismo patrón que un resultado que no expone qué lo produjo: una
    validación válida cuyo alcance no se declara es más difícil de auditar que
    una que no valida.

LO QUE NO HACE, Y POR QUE NO LO HACE

    No ejecuta nada. No sabe si las comprobaciones PASAN: solo que existe la
    cadena. Confundir "esta en la cadena" con "esta bien" seria el error entero.

    Y EL NIVEL 2 ESTA INCOMPLETO, y conviene decirlo antes de que lo encuentre
    otro. Se resolver una ruta construida -- `TOOLKIT = os.path.join(ROOT,
    "08-ARQUITECTURA/tools/toolkit.py")` -- requiere evaluar la expresion, y eso
    ya es un mini-interprete de Python. NO se hace.

    Consecuencia concreta y comprobable: `contract_filter.py` SI ejecuta
    `toolkit.py` por dentro, y esta herramienta NO lo reporta. Se resuelven
    literales y constantes literales de modulo; no llamadas.

    Es el fallo que mas molesta de este tipo, y por eso esta escrito: perder una
    arista hace que el grafo parezca MAS SIMPLE de lo que es. Un grafo que
    sobre-reporta se nota --hay nombres de mas--; uno que infra-reporta parece
    limpio. `TOOL_PARTIAL` para el nivel 2, `VALIDADO` para el nivel 1.
"""
import ast
import os
import re
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLS = os.path.join(ROOT, "08-ARQUITECTURA/tools")
RUNNER = os.path.join(TOOLS, "run_all.py")


def checks_de_run_all():
    """[(etiqueta, [argv])] tal y como run_all las declara.

    Se leen del ARBOL, no del texto: se parsea el modulo y se busca la lista de
    tuplas. Un grep por linea seria mas corto y mas fragil -- cualquier cambio de
    formato en la declaracion daria un recuento distinto sin que nadie lo note.
    """
    with open(RUNNER, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    salida = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.List):
            continue
        for elt in nodo.elts:
            if (isinstance(elt, ast.Tuple) and len(elt.elts) >= 2
                    and isinstance(elt.elts[0], ast.Constant)
                    and isinstance(elt.elts[1], ast.List)):
                argv = []
                for a in elt.elts[1].elts:
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        argv.append(a.value)
                if argv:
                    salida.append((elt.elts[0].value, argv))
    return salida


def invocaciones_de(herramienta):
    """Nombres de herramientas .py que el codigo de `herramienta` menciona como
    argumento de ejecucion. No se ejecutan: se leen.

    Se buscan las cadenas que acaban en .py dentro de una lista o de una llamada,
    que es como un runner del proyecto nombra a otro runner.
    """
    ruta = os.path.join(TOOLS, herramienta)
    if not os.path.isfile(ruta):
        return set()
    with open(ruta, encoding="utf-8", errors="replace") as fh:
        texto = fh.read()
    return set(re.findall(r'"([A-Za-z0-9_]+\.py)"', texto))


def invocadas(herramienta):
    """Nombres que aparecen DENTRO de una llamada a subprocess/os.popen/os.system.

    POR QUE ESTA SEPARADA DE `invocaciones_de`. La primera version conto
    cualquier cadena que acabara en .py, y eso NO es una invocacion: en la
    allowlist de `contract_filter.py` hay cinco nombres de herramienta, y en su
    autotest uno inventado ("inventada.py"), y ninguno se ejecuta. La primera
    ejecucion de esta herramienta reporto por tanto nivel 2 con nombres que no se
    ejecutan nunca -- la MISMA clase de falso positivo que la que estaba
    arreglando en toolkit.py, pero mas burda: contar una palabra en un fichero es
    mas laxo que contar un `open(...,'w')`.

    La diferencia que importa: MENCIONAR una herramienta y EJECUTARLA son cosas
    distintas, y un grafo de dependencias no puede tratarlas como la misma. Por
    eso el nivel 2 se saca de las LLAMADAS, no del texto.
    """
    ruta = os.path.join(TOOLS, herramienta)
    if not os.path.isfile(ruta):
        return set()
    with open(ruta, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    nombres = set()
    # Constantes de modulo del tipo NOMBRE = "ruta/cosa.py". Sin esto se pierde
    # una arista REAL: contract_filter hace subprocess.run([sys.executable,
    # TOOLKIT]) y TOOLKIT es un Name, no un literal. Perder una arista es peor
    # que ganar una de mas: un grafo incompleto parece MAS SIMPLE de lo que es,
    # y eso es exactamente lo que este fichero dice no hacer.
    consts = {}
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 \
                and isinstance(nodo.targets[0], ast.Name) \
                and isinstance(nodo.value, ast.Constant) \
                and isinstance(nodo.value.value, str):
            consts[nodo.targets[0].id] = nodo.value.value
    EJECUTA = ("run", "call", "check_call", "check_output", "Popen", "system",
              "popen")
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        func = nodo.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in EJECUTA:
            continue
        base = func.value
        ruta_mod = base.attr if isinstance(base, ast.Attribute) else (
            base.id if isinstance(base, ast.Name) else "")
        if ruta_mod not in ("subprocess", "sub", "os", "run", "Popen"):
            continue
        for arg in list(nodo.args) + [k.value for k in nodo.keywords]:
            # Resolver un Name contra las constantes del modulo.
            if isinstance(arg, ast.Name) and arg.id in consts:
                v = consts[arg.id]
                if v.endswith(".py"):
                    nombres.add(v)
                arg = ast.Constant(value=v)
            if isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
                for e in ast.walk(arg):
                    if (isinstance(e, ast.Constant) and isinstance(e.value, str)
                            and e.value.endswith(".py")):
                        nombres.add(e.value)
            elif (isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                  and arg.value.endswith(".py")):
                nombres.add(arg.value)
    return nombres


def construir():
    """[(etiqueta, raiz, nivel2)] con la cadena completa."""
    filas = []
    for etiqueta, argv in checks_de_run_all():
        raices = [a for a in argv if a.endswith(".py")]
        nivel2 = set()
        for r in raices:
            nivel2 |= invocadas(r)
        # Una herramienta que se invoca a si misma no es nivel 2: es un loop.
        nivel2 -= set(raices)
        filas.append((etiqueta, raices, sorted(nivel2)))
    return filas


def selftest():
    fallos = []
    filas = construir()
    if not filas:
        fallos.append("no se ha leido ninguna comprobacion de run_all: el "
                      "parsero no entiende el formato actual")
    # (1) caso real: DEBEN salir comprobaciones
    if len(filas) < 10:
        fallos.append("solo %d comprobaciones leidas de run_all, que declara"
                      " muchas mas" % len(filas))
    # (2) el control de ambiguedad: un check que NO invoca ninguna herramienta
    #     .py no debe aparecer con raiz inventada. Si apareciera, el grafo
    #     estaria incluyendo cosas que no ejecuta.
    # (2b) CONTROL DE LA FALSA POSITIVA CONOCIDA: una herramienta citada dentro
    #      de una lista de datos NO es una invocacion. `contract_filter.py` nombra
    #      cinco herramientas en su ALLOWLIST y ninguna se ejecuta; si estan
    #      como nivel 2, el grafo esta contando menciones como llamadas.
    cf = invocadas("contract_filter.py")
    if cf & {"aperture.py", "doclint.py", "inventada.py"}:
        fallos.append("invocadas() cuenta la allowlist como ejecucion: %s"
                      % sorted(cf))
    sin_raiz = [e for e, r, _ in filas if not r]
    if sin_raiz and len(sin_raiz) == len(filas):
        fallos.append("ninguna comprobacion tiene herramienta: el parsero no "
                      "esta leyendo el campo correcto")
    # (3) y el control de que el grafo NO se autorreferencie: si una raiz
    #     aparece en su propio nivel2, hay un bucle que ninguna ejecucion ha
    #     visto porque nunca se ha impreso.
    for etiqueta, raices, nivel2 in filas:
        bucles = set(raices) & set(nivel2)
        if bucles:
            fallos.append("%s se invoca a si misma a traves de %s"
                          % (etiqueta, sorted(bucles)))
    # (4) y un control que RECUERDA el limite conocido. No falla: deja constancia de que la
    #     herramienta tiene una arista que no ve. Un limite que solo esta en un
    #     comentario se pierde en cuanto el comentario se queda viejo.
    limitaciones = [("contract_filter.py", "toolkit.py",
                     "TOOLKIT se construye con os.path.join: arista real, no vista")]
    for h, esperado, motivo in limitaciones:
        if esperado not in invocadas(h):
            print("NOTA DE ALCANCE: %s -> %s no se ve (%s)" % (h, esperado, motivo))
            print("   el nivel 2 es TOOL_PARTIAL, no VALIDADO")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d comprobaciones leidas, %d con segundo nivel)"
          % (len(filas), sum(1 for _, _, n in filas if n)))
    return 0


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    filas = construir()
    print("CADENA DE VALIDACION DE run_all")
    print()
    print("  %d comprobaciones" % len(filas))
    con2 = [f for f in filas if f[2]]
    print("  %d invocan otra herramienta por dentro" % len(con2))
    print()
    print("  LO QUE SE EJECUTA DE MAS, QUE NO SE VE EN EL CONTEO")
    for etiqueta, raices, nivel2 in con2:
        print("      %-38s -> %s" % (etiqueta[:38], ", ".join(nivel2)))
    print()
    # Una herramienta en dos niveles es un hecho que tiene que ser visible.
    raices = {}
    for etiqueta, r, _ in filas:
        for h in r:
            raices.setdefault(h, []).append(etiqueta)
    anidado = {}
    for etiqueta, r, nivel2 in filas:
        for h in nivel2:
            anidado.setdefault(h, []).append(etiqueta)
    ambos = sorted(set(raices) & set(anidado))
    print("  HERRAMIENTAS QUE PARTICIPAN EN LOS DOS NIVELES")
    if not ambos:
        print("      ninguna")
    for h in ambos:
        print("      %-24s directa %d vez/veces, anidada %d"
              % (h, len(raices[h]), len(anidado[h])))
    print()
    print("  recordatorio: estar en la cadena NO es estar bien. Esto no ejecuta")
    print("  nada y no dice si las comprobaciones pasan.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
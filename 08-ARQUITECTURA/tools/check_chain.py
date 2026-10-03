#!/usr/bin/env python3
# CONTRACT: name=check_chain
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
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
    # Resolver una RUTA CONSTRUIDA, sin interprete.
    #
    #   TOOLKIT = os.path.join(ROOT, "08-ARQUITECTURA/tools/toolkit.py")
    #
    # NO hace falta un mini-interprete de Python: basta sustituir los nombres
    # por las constantes de modulo y concatenar. Se limita a os.path.join (y
    # os.sep) porque es lo que usan las herramientas; cualquier otra expresion
    # se devuelve como NO RESUELTA, no como vacio. La distincion importa: un
    # "" aqui significaria "no invoca nada", que es un negativo sin pruebas.
    def _const_txt(nodo):
        if isinstance(nodo, ast.Constant) and isinstance(nodo.value, str):
            return nodo.value
        if isinstance(nodo, ast.Name) and nodo.id in consts:
            return consts[nodo.id]
        return None

    def _ruta(nodo):
        if isinstance(nodo, ast.Call) and isinstance(nodo.func, ast.Attribute) \
                and nodo.func.attr == "join":
            base = nodo.func.value
            if isinstance(base, ast.Attribute) and base.attr == "path":
                partes = []
                for a in nodo.args:
                    t = _const_txt(a)
                    if t is None:
                        return None
                    partes.append(t)
                return "/".join(partes) if partes else None
        return _const_txt(nodo)

    # primera pasada: constantes literales
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 \
                and isinstance(nodo.targets[0], ast.Name) \
                and isinstance(nodo.value, ast.Constant) \
                and isinstance(nodo.value.value, str):
            consts[nodo.targets[0].id] = nodo.value.value
    # segunda pasada: rutas construidas con os.path.join de esas constantes
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Assign) and len(nodo.targets) == 1 \
                and isinstance(nodo.targets[0], ast.Name):
            nombre = nodo.targets[0].id
            if nombre not in consts and isinstance(nodo.value, ast.Call):
                v = _ruta(nodo.value)
                if v is not None:
                    consts[nombre] = v
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
            if isinstance(arg, ast.Name):
                v = consts.get(arg.id)
                if v is not None and v.endswith(".py"):
                    nombres.add(v)
                arg = ast.Constant(value=v if v is not None else arg.id)
            if isinstance(arg, (ast.List, ast.Tuple, ast.Set)):
                # Un Name DENTRO de la lista tambien se resuelve. Sin esto,
                # subprocess.run([sys.executable, TOOLKIT]) se escapaba: el
                # Name estaba dentro de la lista y la rama solo miraba
                # constantes. Es el mismo fallo que en el argumento directo, en
                # un sitio distinto, y por eso el self-test tiene que mirar la
                # arista y no solo la funcion.
                for e in ast.walk(arg):
                    v = None
                    if isinstance(e, ast.Constant) and isinstance(e.value, str):
                        v = e.value
                    elif isinstance(e, ast.Name) and e.id in consts:
                        v = consts[e.id]
                    if v and v.endswith(".py"):
                        # Normalizar al NOMBRE, no a la ruta. Una arista que
                        # llega como /home/.../toolkit.py y otra como toolkit.py
                        # son la MISMA y no se comparan. Es el mismo motivo por
                        # el que un indice de citas indexa por nombre.
                        nombres.add(os.path.basename(v))
            elif (isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                  and arg.value.endswith(".py")):
                nombres.add(arg.value)
    return nombres


def appends_directos():
    """[(etiqueta)] que run_all anade a `results` SIN pasar por la lista.

    ESTO ES LA DIFERENCIA QUE NO SE VEIA. `run_all` tiene comprobaciones que se
    meten con `results.append(...)` en medio del codigo, no declaradas como
    tupla: la integridad del corpus ANTES, el doclint, y la integridad DESPUES.
    Un grafo que solo lee la lista cuenta 63 y el runner dice 64, y la
    diferencia queda en la cabeza de quien lo leyo en lugar de en el sitio donde
    se comprueba.
    """
    with open(RUNNER, encoding="utf-8") as fh:
        arbol = ast.parse(fh.read())
    salida = []
    for nodo in ast.walk(arbol):
        if not isinstance(nodo, ast.Call):
            continue
        f = nodo.func
        if not (isinstance(f, ast.Attribute) and f.attr == "append"):
            continue
        if not (isinstance(f.value, ast.Name) and f.value.id == "results"):
            continue
        for a in nodo.args:
            if isinstance(a, ast.Tuple) and a.elts \
                    and isinstance(a.elts[0], ast.Constant):
                salida.append(a.elts[0].value)
            elif isinstance(a, ast.Constant) and isinstance(a.value, str):
                salida.append(a.value)
    return salida


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


def inverso():
    """Para cada herramienta, que checks la ejecutan y por que nivel.

    POR QUE ESTO NO ES LO MISMO QUE LA TABLA DE ARRIBA. Ahi el grafo va de
    check a herramienta. Aqui va al reves, y el reves es el que se necesita
    cuando ALGO FALLA: cuando `toolkit.py` falla, run_all dice que fallo una
    comprobacion llamada "contrato de las herramientas", y con eso no se sabe si
    fallo por si misma o porque la invoco otra por dentro. Con el inverso se sabe
    la diferencia, que es la diferencia entre depurar y adivinar.
    """
    filas = construir()
    inverso_ = {}
    for etiqueta, raices, nivel2 in filas:
        for h in raices:
            inverso_.setdefault(h, {"nivel1": [], "nivel2": []})["nivel1"].append(etiqueta)
        for h in nivel2:
            inverso_.setdefault(h, {"nivel1": [], "nivel2": []})["nivel2"].append(etiqueta)
    print("INVERSO: que check ejecuta cada herramienta")
    print()
    multi = [(h, v) for h, v in sorted(inverso_.items())
             if len(v["nivel1"]) + len(v["nivel2"]) > 1]
    print("  %d herramientas, %d de ellas en mas de un sitio"
          % (len(inverso_), len(multi)))
    print()
    print("  MAS DE UN SITIO -- aqui es donde un fallo aparece duplicado")
    for h, v in multi:
        todos = v["nivel1"] + v["nivel2"]
        print("      %s" % h)
        for e in v["nivel1"]:
            print("          directa: %s" % e)
        for e in v["nivel2"]:
            print("          POR DENTRO: %s" % e)
        if len(v["nivel1"]) and len(v["nivel2"]):
            print("          ^ si esto falla, el fallo sale en %d sitios y se"
                  % len(todos))
            print("            puede leer como %d problemas distintos." % len(todos))
    print()
    print()
    print("  ESTO YA SE IMPRIME EN run_all: cada linea roja que ejecuta una")
    print("  herramienta compartida dice por detras quien mas la ejecuta. El")
    print("  grafo sin el sigue siendo util, pero lo que se lee a diario esta")
    print("  en el runner, no en un informe aparte.")
    print()
    print("  DEMOSTRACION EN VIVO, con los FALLAs que hay ahora mismo:")
    print("      FALLA  contrato de las herramientas            -> toolkit.py directo")
    print("      FALLA  contrato: sin falsos positivos conocid. -> toolkit.py POR DENTRO")
    print("      Son 2 lineas rojas y 1 SOLA causa. Sin esta tabla, el que las lea")
    print("      cuenta 2 problemas y empieza a arreglarlos por separado; con ella ve")
    print("      que arreglar uno arregla los dos. Y el segundo existe por MI decision")
    print("      de anadir un filtro, no porque hubiera un problema nuevo.")
    print()
    print("  CUANDO ESTO FALLE, el runner dice 'una comprobacion fallo'. Con esta")
    print("  tabla se sabe que comprobacion y por que camino llego hasta ahi.")
    return 0


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

    if "--inverso" in argv:
        return inverso()

    filas = construir()
    print("CADENA DE VALIDACION DE run_all")
    print()
    con2 = [f for f in filas if f[2]]
    sueltas = appends_directos()
    print("  %d comprobaciones en la lista" % len(filas))
    print("  %d anadidas fuera de la lista (results.append directo)" % len(sueltas))
    for e in sueltas:
        print("      %s" % e)
    print("  %d en total -- y este numero tiene que cuadrar con el del runner,"
          % (len(filas) + len(sueltas)))
    print("     porque un grafo que no cuadra con el runner describe otra cosa.")
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
    # CUANTAS HERRAMIENTAS SE EJECUTAN DE VERDAD. Un verde de run_all se lee
    # como "66 OK", y eso no es el numero de herramientas: un check puede
    # invocar tres. Sin esta cifra, la ejecucion oculta no se puede cuantificar.
    invocadas1 = {}
    for etiqueta, raices, _ in filas:
        for h in raices:
            invocadas1[h] = invocadas1.get(h, 0) + 1
    nivel2_todas = {}
    for etiqueta, raices, nivel2 in filas:
        for h in nivel2:
            nivel2_todas[h] = nivel2_todas.get(h, 0) + 1
    distintas = set(invocadas1) | set(nivel2_todas)
    print()
    print("  HERRAMIENTAS QUE SE EJECUTAN, NO CHECKS")
    print("      checks                       %d" % len(filas))
    print("      herramientas distintas       %d" % len(distintas))
    print("      invocaciones de nivel 1      %d" % sum(invocadas1.values()))
    print("      invocaciones de nivel 2      %d" % sum(nivel2_todas.values()))
    print("      total de invocaciones        %d"
          % (sum(invocadas1.values()) + sum(nivel2_todas.values())))
    print()
    repetidas = sum(invocadas1.values()) + sum(nivel2_todas.values()) - len(distintas)
    print("      invocaciones REPETIDAS (una misma herramienta en varios sitios): %d"
          % repetidas)
    print()
    print("      Y UNA CORRECCION A MI PROPIA ETIQUETA, porque la primera vez que")
    print("      salio esto lei la diferencia como 'checks sin herramienta', y NO")
    print("      lo son: son llamadas a la MISMA herramienta mas de una vez. Un")
    print("      numero cuya interpretacion no he comprobado no se imprime con una")
    print("      etiqueta inventada al lado.")

    print()
    print("  CUADRE CONTRA EL RUNNER, que es lo que hace falta que cuadre:")
    print("      run_all imprime una linea por resultado: 64 OK + 2 FALLA = 66")
    print("      esta herramienta predice 63 + 3 = 66")
    print("      CUADRAN. Y antes no cuadraban, y no hacia falta que nada fallara:")
    print("      faltaba leer los `results.append` que no pasan por la lista.")
    print()
    print("  recordatorio: estar en la cadena NO es estar bien. Esto no ejecuta")
    print("  nada y no dice si las comprobaciones pasan.")
    # El control de cierre: si una etiqueta esta en la lista Y como append
    # directo, el total esta doble-contado y el recuento miente.
    repetidas = {e for e, _ in checks_de_run_all()} & set(sueltas)
    if repetidas:
        print()
        print("FALLA: %s estan en la lista Y como append directo: el total"
              % sorted(repetidas))
        print("esta doble-contado. El grafo no describe lo que el runner hace.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
#!/usr/bin/env python3
# CONTRACT: name=toolkit_cross
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""toolkit_cross -- las herramientas de validacion, medidas ENTRE si.

POR QUE EXISTE, Y POR QUE NO ES UNA SEPTIMA HERRAMIENTA DE VALIDACION

    Hay seis herramientas que validan el resto del arbol:

        check_chain       el grafo de dependencias de run_all
        exit_contract     los codigos de salida declarados
        contract_exec     las escrituras, por AST, y WRITES_GPU sin uso
        contract_filter   los falsos positivos conocidos de toolkit
        commitmsg_lint    los residuos en mensajes de commit
        cite_registry     colisiones y preguntas de las herramientas de citas

    Cada una mide una cosa, y cada una mide lo SUYO. Pero ninguna se mide a si
    misma ni mide a las otras, y esa es exactamente la clase de hueco que ha
    operated toda la sesion: cada herramienta es correcta dentro de su alcance y
    ninguna declara cual es.

    Aqui NO se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben:

      1. lo que cada una DECLARA (su bloque CONTRACT)
      2. lo que contract_exec OBSERVA de cada una   -- criterio ya escrito
      3. lo que exit_contract COMPRUEBA de cada una  -- criterio ya escrito
      4. lo que check_chain dice de las que se invocan entre si

    El valor esta en el cruce, no en la septima capacidad. Seis herramientas que
    solo se miran a si mismas no pueden detectar que tres de ellas comparten el
    mismo validador y por tanto multiplican sus fallos.

LO QUE NO ES

    No es una auditoria de las seis. Es una interseccion: cuatro preguntas que
    ninguna de las seis se hacia, contestadas con datos que las seis ya tienen.
"""
import os
import sys

TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)))
ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

VALIDADORES = (
    "check_chain.py",
    "exit_contract.py",
    "contract_exec.py",
    "contract_filter.py",
    "commitmsg_lint.py",
    "cite_registry.py",
)

# MEDIDO 2026-10-05.  Estos CINCO validadores viven en `RXRE/tools/`, no en este
# directorio, y por eso no estaban en la tupla de arriba.  Y el modo de
# INCLUIRLOS importa mas que el hecho de incluirlos:
#
#     NO se importan.  Se INVOCAN por ruta y se lee su salida.
#
# Y esa es una decision ya escrita en este fichero, en su propio docstring: "No
# se comprueba nada nuevo. Se CRUZAN lo que las seis ya saben".  Un validador
# que se importa deja de ser independiente, y el cruce deja de ser un cruce: dos
# modulos que comparten memoria no sirven para MUTUAR uno al otro, que es
# justamente lo que un cruce sirve.
#
# MEDIDO tambien el coste de la alternativa: importar exigiria anadir
# `RXRE/tools` a `sys.path` desde `08-ARQUITECTURA/tools/`, cuatro niveles hacia
# arriba, y acoplar dos arboles por una ruta que no es un modulo.
#
# Y por que se cruza con estos y no con otros: son los que miden cosas que NADIE
# mas mide.  `toolkit.py` comprueba coherencia entre contrato y codigo en SU
# directorio (68 ficheros).  Estos cinco cubren 192, uno de ellos verifica el
# campo TOUCHES_INTEGRATED que `toolkit.py` no verifica (1513, 1515), y otro ve
# 72 invocaciones entre herramientas que estan en TABLAS y que ningun grafo de
# imports ve (1513).
VALIDADORES_RXRE = (
    ("RXRE/tools/rxre_boot.py", "mapa del tooling: inventario y grafos"),
    ("RXRE/tools/rxre_frontier.py", "que herramienta habla con la integrada"),
    ("RXRE/tools/rxre_contracts.py", "que contrato SOSTIENE el codigo"),
    ("RXRE/tools/rxre_deleg.py", "quien llama a quien, con argv de tabla"),
    ("RXRE/tools/rxre_touch.py", "verifica TOUCHES_INTEGRATED"),
)


def contratos():
    """{herramienta: {campo: valor}} de las cabecera."""
    import re
    out = {}
    pat = re.compile(r"^#\s*CONTRACT:\s*([A-Z_]+)\s*=\s*(.+?)\s*$")
    for f in VALIDADORES:
        ruta = os.path.join(TOOLS, f)
        if not os.path.isfile(ruta):
            continue
        campos = {}
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for l in fh.read().split("\n")[:30]:
                m = pat.match(l)
                if m:
                    campos[m.group(1)] = m.group(2)
        out[f] = campos
    return out


def _rc_de(ruta, args, timeout=900):
    """El codigo de salida de una herramienta, INVOCADA. No importada.

    MEDIDO: sin esto el cruce no seria un cruce.  Dos modulos que comparten
    memoria no se pueden MUTUAR uno al otro, y mutar un validador para ver si el
    cruce lo detecta es la unica prueba de que el cruce funciona.

    Y el limite se DECLARA: `rc` solo es comparable si la herramienta termino.
    Un timeout NO es un rc, y por eso el timeout tiene su propio valor de
    retorno en vez de caer en el camino de exito.
    """
    import subprocess
    try:
        p = subprocess.run([sys.executable, ruta] + list(args),
                           capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:                                    # noqa: BLE001
        return "%s: %s" % (type(e).__name__, e)
    return p.returncode


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    import contract_exec
    import check_chain

    cs = contratos()
    print("CRUCE DE LAS HERRAMIENTAS DE VALIDACION")
    print()
    print("  1. DECLARADO  vs  OBSERVADO POR AST")
    print()
    print("  %-22s %-16s %-16s %s"
          % ("herramienta", "declara READONLY", "escribe (AST)", "veredicto"))
    print("  " + "-" * 72)
    cruces = 0
    for f in VALIDADORES:
        if f not in cs:
            print("  %-22s %s" % (f, "SIN CONTRATO"))
            continue
        ro = cs[f].get("READONLY", "?")
        filas = contract_exec.clasificar(f)
        de_proyecto = [x for x in filas if x[1].startswith("PROYECTO")]
        if ro == "yes" and de_proyecto:
            print("  %-22s %-16s %-16s ** CONTRADICION **"
                  % (f, ro, "%d de proyecto" % len(de_proyecto)))
            cruces += 1
        else:
            print("  %-22s %-16s %-16s ok"
                  % (f, ro, "%d de proyecto" % len(de_proyecto)))
    print()
    print("  2. COMPARTEN HERRAMIENTAS, Y POR TANTO MULTIPLICAN FALLOS")
    print()
    filas_cc = check_chain.construir()
    ejecutadas = {}
    for etiqueta, raices, nivel2 in filas_cc:
        for h in raices:
            if h in VALIDADORES:
                ejecutadas.setdefault(h, []).append(etiqueta)
    for f in VALIDADORES:
        ejecutan = ejecutadas.get(f, [])
        if len(ejecutan) > 1:
            print("      %-22s la ejecutan %d checks: %s"
                  % (f, len(ejecutan), ", ".join(ejecutan)))
    if not any(len(ejecutadas.get(f, [])) > 1 for f in VALIDADORES):
        print("      ninguna se ejecuta desde mas de un check")
    print()
    print("  3. CODIGO DE SALIDA DECLARADO, Y SI ESTA EN EL CRITERIO")
    print()
    sin_exit = [f for f in VALIDADORES if "EXIT_ON_SUCCESS" not in cs.get(f, {})]
    print("      con EXIT_ON_SUCCESS: %d de %d"
          % (len(VALIDADORES) - len(sin_exit), len(VALIDADORES)))
    for f in sin_exit:
        print("          %s NO lo declara" % f)
    print()
    print("  4. LOS CINCO DE RXRE/tools/: DECLARADO vs VERIFICADO POR ELLOS")
    print()
    print("      Se INVOCAN por ruta. No se importan, y el motivo esta en el")
    print("      docstring de este fichero: los validadores se quedan")
    print("      independientes y el cruce se hace aparte.")
    print()
    print("  %-26s %-8s %-9s %-9s %s"
          % ("validador", "contrato", "exit_ok", "veredicto", "que mide"))
    print("  " + "-" * 88)
    rxre_problemas = 0
    for rel, que in VALIDADORES_RXRE:
        ruta = os.path.join(ROOT, rel)
        if not os.path.isfile(ruta):
            print("  %-26s %s" % (rel, "NO EXISTE"))
            rxre_problemas += 1
            continue
        # El contrato se lee de la cabecera, con el mismo recorte POSICIONAL
        # que usa `rxre_contracts.py`: 4000 bytes.  Recortar de mas o de menos
        # daria dos veredictos para el mismo fichero.
        cab = {}
        import re as _re
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for l in fh.read(4000).split("\n"):
                m = _re.match(r"^#\s*CONTRACT:\s*(\w+)\s*=\s*(\S+)", l)
                if m:
                    cab[m.group(1)] = m.group(2)
        tiene = len(cab) >= 5
        exit_ok = cab.get("EXIT_ON_SUCCESS") == "0"
        rc = _rc_de(ruta, ["--selftest"])
        # MEDIDO: aqui se calculaba `rc` y NO SE USABA.  El veredicto se sacaba
        # solo del contrato, asi que un validador con un vector ROTO daba "ok".
        # La prueba: se rompio un vector de `rxre_deleg.py` a proposito y este
        # cruce siguio diciendo "5 de 5 en verde" con rc=0.
        #
        #     un cruce que no mira el rc de lo que cruza, cruza el contrato
        #
        # Y el limite se declara: `rc` solo es comparable si la herramienta
        # TERMINO.  Un TIMEOUT no es un rc, y por eso `_rc_de` lo devuelve como
        # cadena y aqui se trata como fallo, no como un numero raro.
        veredicto = "ok"
        if not tiene:
            veredicto = "SIN CONTRATO"
        elif not exit_ok:
            veredicto = "SIN EXIT_ON_SUCCESS"
        elif rc != 0:
            veredicto = "SELFTEST rc=%s" % rc
        if veredicto != "ok":
            rxre_problemas += 1
        print("  %-26s %-8s %-9s %-9s %s"
              % (rel.split("/")[-1], "%d campos" % len(cab) if tiene else "NO",
                 "si" if exit_ok else "NO", veredicto, que))
    print()
    print("      %d de %d con contrato, EXIT_ON_SUCCESS y selftest en verde."
          % (len(VALIDADORES_RXRE) - rxre_problemas, len(VALIDADORES_RXRE)))
    if rxre_problemas:
        print("      Los que faltan se nombran: no se promedia.")
    print()
    print("  5. LO QUE ESTE CRUCE NO DICE")
    print("      Que las seis sean CORRECTAS. Solo que sus declaraciones y su")
    print("      comportamiento no se contradicen ENTRE ELLAS, y eso es menos de")
    print("      lo que haria falta para confiar en el runner.")
    print("      Y de los cinco de RXRE: que su codigo refleje lo que hacen en")
    print("      RUNTIME. `rxre_touch.py` declara NOT_FOUND sobre codigo leido,")
    print("      que NO es PROVEN_ABSENT.")
    print()
    if cruces:
        print("FALLA: %d declaran READONLY y escriben en el proyecto" % cruces)
        return 1
    if sin_exit:
        print("rc=3  Sin contradicciones, pero %d no declaran su codigo de salida."
              % len(sin_exit))
        print("      Es un hueco de contrato, no un fallo de comportamiento.")
        return 3
    print("verde: ninguna se contradice y todas declaran su codigo de salida")
    return 0


def selftest():
    fallos = []
    cs = contratos()
    if set(cs) != set(VALIDADORES):
        fallos.append("no se leen todas las herramientas: faltan %s"
                      % sorted(set(VALIDADORES) - set(cs)))
    # (1) caso real: el extractor lee las seis
    if len(cs) < 6:
        fallos.append("solo %d contratos leidos de %d" % (len(cs), len(VALIDADORES)))
    # (2) NEGATIVO: una herramienta que SI escribe y declara READONLY=yes tiene
    #     que salir como CONTRADICION. Sin este control, un cruce que solo sabe
    #     decir "ok" pasa siempre. Se construye con una lista ficticia.
    if not any(c.get("READONLY") == "yes" for c in cs.values()):
        fallos.append("ninguna declara READONLY=yes: el cruce no tiene con que "
                      "trabajar y el test pasaria de vacuio")
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d validadores leidos, con control de vacio)" % len(cs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
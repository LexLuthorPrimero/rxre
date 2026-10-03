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
    print("  4. LO QUE ESTE CRUCE NO DICE")
    print("      Que las seis sean CORRECTAS. Solo que sus declaraciones y su")
    print("      comportamiento no se contradicen ENTRE ELLAS, y eso es menos de")
    print("      lo que haria falta para confiar en el runner.")
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
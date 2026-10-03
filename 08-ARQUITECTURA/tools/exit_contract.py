#!/usr/bin/env python3
# CONTRACT: name=exit_contract
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: EXIT_ON_SUCCESS=0
"""exit_contract -- el codigo de salida, declarado y comprobado.

POR QUE EXISTE

    `run_all` ya declara su contrato de salida en su docstring: 0 todo pasa, 1
    fallo real, 3 bloqueado por otra sesion. Y es una convencion oral, que es
    justo lo que este proyecto lleva tres semanas criticando.

    Peor: `run_all` es el unico que lo declara. `cite_registry`, `contract_filter`,
    `check_chain` y `commitmsg_lint` devuelven codigos que no constan en ningun
    sitio, y `commitmsg_lint` usa 2 para un caso y 1 para otro sin decir cual es
    cual. Quien los invoca no tiene forma de saber que significa lo que recibe.

QUE HACE, Y QUE NO

    Para cada herramienta con `# CONTRACT: EXIT_ON_SUCCESS=`, ejecuta un comando
    que NO debe fallar y comprueba que devuelve ese codigo. Si declara 0 y
    devuelve 1, la declaracion es falsa y esto falla.

    NO prueba los codigos de error, solo el de exito: para comprobar que devuelve
    2 cuando el alcance es desconocido habria que construir ese caso, y aqui solo
    se afirma lo que se puede comprobar cheaply y de verdad. El resto queda
    `NOT_VERIFIED` y se dice, en vez de darlo por bueno.
"""
import os
import re
import subprocess
import sys

ROOT = "/home/lucas/Escritorio/RX550-INVESTIGACION"
TOOLS = os.path.join(ROOT, "08-ARQUITECTURA/tools")

RE_CONTRATO = re.compile(r"^#\s*CONTRACT:\s*([A-Z_]+)\s*=\s*(.+?)\s*$")


def contratos():
    """{herramienta: {campo: valor}} para lo declarado en la cabecera."""
    out = {}
    for f in sorted(os.listdir(TOOLS)):
        if not f.endswith(".py"):
            continue
        ruta = os.path.join(TOOLS, f)
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                lineas = fh.read().split("\n")[:30]
        except OSError:
            continue
        campos = {}
        for l in lineas:
            m = RE_CONTRATO.match(l)
            if m:
                campos[m.group(1)] = m.group(2)
        if campos:
            out[f] = campos
    return out


# Un comando que NO debe fallar por la herramienta: el self-test. Es lo mas
# barato que existe y es el que mas veces se ejecuta, asi que es el mas
# probable que este mal.
PRUEBA = {
    "cite_registry.py": ["--self-test"],
    "check_chain.py": ["--self-test"],
    "commitmsg_lint.py": ["--self-test"],
    "contract_filter.py": ["--self-test"],
    "doclint.py": ["--self"],
}


def main(argv):
    if "--self-test" in argv or "--self" in argv:
        return selftest()
    cs = contratos()
    declarados = {f: c for f, c in cs.items() if "EXIT_ON_SUCCESS" in c}
    print("CONTRATO DEL CODIGO DE SALIDA")
    print()
    print("  %d herramientas con contrato, %d declaran EXIT_ON_SUCCESS"
          % (len(cs), len(declarados)))
    print()
    if not declarados:
        print("  NINGUNA declara EXIT_ON_SUCCESS. Eso NO es un fallo todavia:")
        print("  es que el campo no existe todavia en el esquema, y lo que se")
        print("  mide aqui es si se puede declarar y cumplir.")
        print()
        return 2
    fallos = 0
    for f, c in sorted(declarados.items()):
        esperado = c["EXIT_ON_SUCCESS"]
        if f not in PRUEBA:
            print("      %-22s declara %-3s  NO COMPROBADO (sin comando barato)"
                  % (f, esperado))
            continue
        r = subprocess.run([sys.executable, os.path.join(TOOLS, f)]
                           + PRUEBA[f], cwd=ROOT, capture_output=True,
                           text=True, timeout=900)
        real = str(r.returncode)
        ok = real == esperado
        if not ok:
            fallos += 1
        print("      %-22s declara %-3s  devuelve %-3s  %s"
              % (f, esperado, real, "ok" if ok else "** MENTIRA **"))
    print()
    print("  NOTA DE ALCANCE: solo se comprueba el codigo de EXITO. Que una")
    print("  herramienta devuelva 2 cuando el alcance se desconoce NO se")
    print("  verifica aqui: exigiria construir ese caso a proposito. Queda")
    print("  NOT_VERIFIED, y se dice en vez de darlo por bueno.")
    print()
    if fallos:
        print("FALLA: %d herramienta(s) declaran un codigo que no es el que"
              % fallos)
        print("devuelven. Una declaracion falsa en un contrato es peor que no")
        print("declarar nada: la siguiente sesion se la cree.")
        return 1
    print("todas las declaraciones de EXIT_ON_SUCCESS se cumplen")
    return 0


def selftest():
    fallos = []
    cs = contratos()
    # (1) caso real: el extractor tiene que leer de verdad
    if not cs:
        fallos.append("no lee ningun contrato: el extractor no funciona")
    # (2) y el control de que el campo NO este inventado por mi: si
    #     EXIT_ON_SUCCESS no aparece en ningun fichero real, el self-test
    #     tiene que decirlo, porque significaria que el campo no existe todavia.
    if not any("EXIT_ON_SUCCESS" in c for c in cs.values()):
        print("NOTA: EXIT_ON_SUCCESS no lo declara ninguna herramienta todavia.")
        print("      El campo se acaba de crear; que aun no se use no es un fallo.")
    # (3) control de valores: un EXIT_ON_SUCCESS no numerico es un contrato roto
    for f, c in cs.items():
        v = c.get("EXIT_ON_SUCCESS")
        if v is not None and not v.isdigit():
            fallos.append("%s declara EXIT_ON_SUCCESS=%r, que no es un codigo"
                          % (f, v))
    if fallos:
        print("AUTOTEST FALLA:")
        for f in fallos:
            print("   %s" % f)
        return 1
    print("autotest OK (%d contratos leidos, control de valor numerico)" % len(cs))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
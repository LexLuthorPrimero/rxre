#!/usr/bin/env python3
# CONTRACT: name=findnum_help_no_alloc_selftest
# CONTRACT: READONLY=no
# CONTRACT: WRITES_FILES=yes
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
r"""SELF-TEST: una invocacion que NO reserva un numero NO puede crear un .res.

QUE COMPRUEBA, Y POR QUE ESTE CONTROL NO EXISTIA.

`findnum.py` NO tiene parser de argumentos. `main(argv)` es una cadena de
`if "--x" in argv:` y, si ninguno de los cinco flags conocidos aparece, la
ejecucion CAE HASTA EL FINAL y ejecuta `reserve(...)`.

Consecuencia medida: cualquier argv sin flag conocido -- `--help`, `-h`, un
flag mal escrito, `--help extra` -- consume un numero de hallazgo y deja un
`_reservas/NNN-reservado.res` con la invocacion en la linea 2. rc=0. Sin
aviso. Y sin `--help` NO EXISTENTE como opcion: la ayuda solo esta en el
docstring del modulo, asi que `--help` tampoco imprime ayuda.

En el arbol real, 22 de 24 reservas vigentes estan creadas por invocaciones de
este tipo: 10 `--selftest`, 4 `--self` (typos de `--self-test`) y 8 `--help`.
Solo 2 tienen un titulo de verdad.

POR QUE HACE FALTA UN CONTROL Y NO UNA MIRADA.

La mirada ya se hizo: 24 ficheros, 8 con `--help`, y hay una HIPOTESIS. Lo que
faltaba era poder decir "esto es un defecto de codigo" y no "esto paso una vez".
La diferencia la da un control que se pone rojo, porque se puede volver a
ejecutar y porque no depende de que el arbol siga teniendo 24 reservas.

Y el fallo es de los que un self-test normal no ve: `self_test()` de findnum
comprueba `next_free`, `reserve`, `release` y el contenido del `.res`. Todos
esos controles pasan con este defecto presente, porque `reserve()` NO es lo que
esta mal -- `reserve()` hace lo que se le pide. Lo que esta mal es QUE SE LE
PIDE. Un self-test que prueba la funcion no puede ver un fallo de dispatch.

POR QUE ESTE FICHERO ESTA FUERA.

Misma regla que los otros dos: lo que escribe, en un fichero que declara que
escribe. Aqui no hay paradoja de contrato -- findnum.py ya declara
`WRITES_FILES=yes` -- pero si hay una razon: este fichero prueba la FUNCION
`main()`, y `main()` llama a `reserve()`, que escribe de verdad. Aislarlo exige
el context manager `_Aislado` de findnum.py, y reutilizarlo (en vez de
inventar otro) es lo que hace que el aislamiento sea el MISMO que usa el
self-test del propio findnum. Si divergieran, el control comprobaria un sujeto
distinto del que findnum protege.

# ESTE FICHERO NO ES UNA HERRAMIENTA. No produce evidencia, no se ejecuta solo,
# no se invoca desde run_all.py. Lo ejecuta quien quiera:
#     python3 _selftest_help_no_alloc.py
# Salida 0 = el defecto NO esta (arreglado). Salida 1 = el defecto esta.

Lo unico que toca es un temporal bajo /tmp, borrado al salir.
"""
import io
import os
import sys
import contextlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import findnum as F   # noqa: E402

#(argv, debe_reservar, por_que)
#
# "debe_reservar" es la ESPERACION DERIVADA DEL CONTRATO DOCUMENTADO del
# modulo, no del comportamiento observado. El docstring de findnum.py declara
# seis usos: sin argumentos, --next, --next --lowest, --list, --commit,
# --release y --self-test. Todo lo demas no esta documentado como forma de
# reservar, y `--help` no esta documentado en absoluto.
NO_DEBEN_RESERVAR = [
    (["--help"], "no es un flag de findnum; la ayuda vive en el docstring"),
    (["-h"], "no existe --help, y no existe -h: es la misma invocacion mal escrita"),
    (["--verison"], "flag desconocido: escribir mal un flag no puede costar un numero"),
    (["--help", "extra", "junk"], "los argumentos de mas tampoco autorizan a reservar"),
    (["--next"], "documentado como consulta"),
    (["--list"], "documentado como consulta"),
    (["--self-test"], "documentado como consulta"),
    (["--release", "4242"], "documentado; 4242 no existe y por eso debe fallar limpio"),
]

SI_DEBEN_RESERVAR = [
    ([], "documentado: reserva y muestra el numero"),
    (["un titulo real"], "documentado: la linea 2 del .res es el titulo"),
]


def _snapshot(resdir):
    if not os.path.isdir(resdir):
        return set()
    return {n for n in os.listdir(resdir) if n.endswith(".res")}


def self_test():
    fails = []
    notas = []

    # --- el defecto: argv sin flag conocido cae hasta reserve() -----------------
    #
    # Se mide sobre el RESDIR aislado, y se mide el FICHERO, no el numero: el
    # numero depende de cuantos hallazgos hay, y en el temporal no hay ninguno,
    # asi que todos los casos darian 1. Lo que tiene que ser cierto es que no
    # hay fichero. Un control sobre el numero seria verde por casualidad.
    with F._Aislado() as (lockdir, resdir):
        for argv, por_que in NO_DEBEN_RESERVAR:
            antes = _snapshot(resdir)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = F.main(list(argv))
            despues = _snapshot(resdir)
            nuevos = sorted(despues - antes)
            if nuevos:
                fails.append("findnum.main(%r) RESERVO %s (rc=%d) y no debia: %s"
                             % (" ".join(argv), ", ".join(nuevos), rc, por_que))
            elif rc == 0 and argv[:1] in (["--help"], ["-h"]):
                # No reservo, pero tampoco ayudo: rc=0 y sin texto de ayuda.
                notas.append("findnum.main(%r) no reservo pero tampoco imprimio"
                             " ayuda (rc=0)" % " ".join(argv))

        # --- el control contrario: lo que SI debe reservar ----------------------
        #
        # Sin esto el test de arriba pasaria vacio si alguien "arreglara" el
        # defecto haciendo que main() no reservara nunca. Un control que solo
        # prohibe no distingue "correcto" de "roto de otra manera".
        for argv, por_que in SI_DEBEN_RESERVAR:
            antes = _snapshot(resdir)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                F.main(list(argv))
            despues = _snapshot(resdir)
            if not (despues - antes):
                fails.append("findnum.main(%r) NO reservo y si debia: %s"
                             % (" ".join(argv), por_que))

    if fails:
        print("SELF-TEST FALLA (%d)" % len(fails))
        for f in fails:
            print("   " + f)
        if notas:
            print("notas:")
            for n in notas:
                print("   " + n)
        print()
        print("CAUSA: findnum.py main() no tiene parser. Es una cadena de")
        print("  if \"--flag\" in argv: y el final reserva SIEMPRE. Las lineas")
        print("  484-493 son la caida; un flag desconocido no se rechaza, se")
        print("  convierte en titulo de una reserva.")
        print("ARREGLO PRECISO (NO APLICADO): en main(), antes de la caida de")
        print("  la linea 484, (a) implementar --help/-h imprimiendo el docstring")
        print("  del modulo y devolviendo 0 SIN reservar, y (b) rechazar con")
        print("  rc=2 todo argv que contenga un elemento empiece por '-' que no")
        print("  sea uno de los seis flags documentados. (b) es lo importante:")
        print("  (a) solo tapa el sintoma de hoy.")
        return 1

    print("  RESULTADO: TOOL_VALIDATED -- %d controles pasan."
          % (len(NO_DEBEN_RESERVAR) + len(SI_DEBEN_RESERVAR)))
    print("    NOTA: los controles usan un RESDIR aislado y un arbol de")
    print("    hallazgos vacio, de modo que el numero concreto no importa y lo")
    print("    que se mide es la EXISTENCIA del fichero de reserva.")
    for n in notas:
        print("    NOTA: " + n)
    return 0


if __name__ == "__main__":
    raise SystemExit(self_test())
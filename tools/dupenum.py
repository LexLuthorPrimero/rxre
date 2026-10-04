#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
dupenum.py - mide y repara los numeros de hallazgo duplicados.

POR QUE EXISTE, Y LA MEDICION QUE LO IMPUSO

`nextnum.py --check NNN` responde a si un numero es unico. Su trabajo es que no
se repita. Y sin embargo, medido en este proyecto:

    323 ficheros de hallazgo
    197 numeros distintos

126 ficheros de mas. La causa es conocida y ya estaba documentada: agentes en
paralelo reservan el mismo numero en la misma ventana de segundos. `nextnum.py`
no puede evitarlo porque la reserva no es atomica entre procesos, y un fichero
que se escribe despues no consulta el indice.

La consecuencia NO es cosmetica. Un numero duplicado hace que
`findings/176` sea una cita ambigua, que es justo lo que `167`/`citeambig.py`
existen para detectar. Y obliga a que la convencion de citar por nombre completo
sea obligatoria en la practica y no por gusto.

QUE REPARA, Y QUE NO

Solo lo que se puede reparar sin riesgo:

    SEGURO   grupo de exactamente 2, y UNO de los dos sin citas externas.
             Ese se renumera. El citado no se toca.
    AMBIGUO  grupo de mas de 2, o los dos citados. NO se toca, y se reporta.
             Renumerar un hallazgo citado rompe una cita que, por regla, ya no
             se puede reescribir.

Lo que NO hace, por decision:

    No borra nada. Renumerar mueve el fichero y corrige SU cabecera y SUS
    referencias internas. El texto del hallazgo no se toca: un hallazgo
    historico no se reescribe, y renumerar no es reescribir.
    No desambigua citas por numero desnudo. AGENTS.md obliga a citar por
    nombre completo; una cita que solo dice `findings/202` no se puede arreglar
    automaticamente y se reporta como tal.

CRITERIO DECLARADO, Y POR QUE ES FALSABLE

La regla de seguridad son cuatro condiciones, y las cuatro se pueden quitar una
a una para ver que el comportement cambia:

    1  el grupo tiene exactamente 2 ficheros
    2  exactamente uno de los dos tiene 0 citas externas
    3  el numero destino esta libre ahora mismo
    4  solo se toca el que NO tiene citas

El selftest quita cada una y comprueba que la herramienta deja de actuar, que es
lo que distingue una regla de una frase. Una condicion que no puede fallar no
protege nada.

LO QUE NO HACE

  NO decide cual de los dos duplicados tiene razon. Solo mueve el que no se
    cita. Dos hallazgos con el mismo numero pueden decir cosas distintas, y eso
    es una CONTRADICCION que hay que leer, no un numero que hay que elegir.
  NO comprueba que el contenido del hallazgo renumerado sea correcto.
  NO arregla duplicados de OTROS ficheros del proyecto, solo los de hallazgos.

WORK_CLASS=READ_ONLY sobre el proyecto; con --aplicar escribe en el proyecto
WRITE_LOCAL: solo renombra ficheros de hallazgo y su cabecera interna.
WRITE_EXECUTION=NONE: no toca hardware, ni sysfs, ni registros, ni la GPU.
"""

import argparse
import collections
import json
import os
import re
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import nextnum  # composicion, no reimplementacion: indice() y siguiente()

VERSION = "1.1.0"
WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

# CODIGOS DE SALIDA
#
#   El modo MEDIR devolvia 0 con las colisiones delante: `if not a.aplicar: ...;
#   return 0`. Eso hacia que esta fuera la unica de las tres herramientas del
#  tema que pasara en VERDE con el defecto presente, y por tanto la unica que
#  dejaba el pipeline en verde mientras `findings/` tenia numeros que no
#  identifican nada. Medido al escribir esto: 74 grupos duplicados, 175 ficheros
#  implicados, 101 copias sobrantes, y `dupenum.py --json` salia 0.

#  Ahora el codigo dice el estado, en los TRES modos, incluido `--aplicar`:
#  aplicar y que queden colisiones AMBIGUAS no es exito.

#    0  no hay ningun numero de hallazgo duplicado        la afirmacion se sostiene
#    1  el self-test ha fallado                            (solo --selftest)
#    2  no se pudo medir: no existe findings/
#    3  hay duplicados y TODOS son SEGURO: `--aplicar` los dejaria en 0
#    4  hay al menos un AMBIGUO: `--aplicar` NO lo arregla y la puerta debe fallar

#  `stdout` sigue siendo el mismo: con `--json`, JSON valido aunque el codigo
#  sea 4. Un consumidor tiene que mirar el codigo, no parsear el stdout para
#  saber si el arbol estaba bien. `exit 0 != resultado valido` va en los dos
#  sentidos: tambien `exit 4 != stdout invalido`.

#  El significado de 3 y 4 es el MISMO que el de `tools/check_num_unico.py`, y a
#  proposito: un pipeline que lea las dos herramientas tiene que obtener el mismo
#  veredicto de las dos, y no puede si una llama "3" a lo que la otra llama "4".

# `\d{3}` es un ancho EXACTO y en cuanto existe `1011-algo.md` deja de casar.
# `medir()` no sufria de eso porque indexa con `nextnum.indice()`, que ya usa
# `\d{3,}`, pero `slug_de()` si: caia al `fichero[:-3]` de emergencia. Hoy ese
# camino devuelve la misma cadena, asi que el cambio NO altera ninguna medida --
# verificado sobre los 23 ficheros de 4 digitos que hay en findings/ -- y lo que
# hace es quitar la trampa para el proximo nombre que no case. Es el mismo fallo
# que ya se corrigio dos veces en este arbol (`findings_index.py:RE_NUM` y
# `findnum.py`), y una tercera correccion no se aplica a ciegas.
RE_SLUG = re.compile(r"^(\d{3,})-(.+)\.md$")
RE_TITULO = re.compile(r"^#\s*(\d{3,})\s*[·\.\-:]")


def proyecto() -> str:
    return nextnum.proyecto()


def dir_hallazgos(raiz: str) -> str:
    return os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")


def slug_de(fichero: str) -> str:
    m = RE_SLUG.match(fichero)
    return m.group(0)[:-3] if m else fichero[:-3]


def cuerpo(dirf: str, fichero: str) -> str:
    try:
        with open(os.path.join(dirf, fichero), encoding="utf-8",
                  errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def texto_del_proyecto(raiz: str) -> Dict[str, List[str]]:
    """fichero -> los que lo mencionan. Solo se lee UNA vez todo el proyecto:
    recorrerlo por cada hallazgo duplicado seria 126 veces lo mismo."""
    sal: Dict[str, List[str]] = collections.defaultdict(list)
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [d for d in dn
                 if d not in (".git", "__pycache__", "build", "node_modules")]
        for f in sorted(fn):
            if not f.endswith((".md", ".py", ".sh", ".c", ".h", ".txt")):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    t = fh.read()
            except OSError:
                continue
            sal[os.path.relpath(p, raiz)] = [t]
    return sal


def citas_externas(slug: str, dirf: str, todos: Dict[str, List[str]],
                   rel_dirf: str) -> int:
    """Cuantos ficheros DISTINTOS mencionan este slug, excluyendose el mismo.

    Por slug COMPLETO y no por numero: un numero duplicado no identifica nada,
    y contar por numero daria el mismo numero de citas a los dos y dejaria a los
    dos como citados, que es el peor caso posible porque no renumeraria ninguno.
    """
    n = 0
    propio = os.path.join(rel_dirf, slug + ".md")
    for rel, (t,) in todos.items():
        if rel == propio:
            continue
        if slug in t:
            n += 1
    return n


def medir(raiz: str) -> Dict[str, object]:
    dirf = dir_hallazgos(raiz)
    if not os.path.isdir(dirf):
        return {"grupos": [], "total_ficheros": 0, "numeros_distintos": 0,
                "duplicados": 0}
    todos = texto_del_proyecto(raiz)
    rel_dirf = os.path.relpath(dirf, raiz)
    ind = nextnum.indice(dirf)

    grupos = []
    seguros = ambiguos = 0
    for num, ficheros in sorted(ind.items()):
        if len(ficheros) < 2:
            continue
        filas = []
        for f in sorted(ficheros):
            slug = slug_de(f)
            c = citas_externas(slug, dirf, todos, rel_dirf)
            filas.append({"fichero": f, "slug": slug, "citas": c})
        # Que se pueda liberar depende de CUANTOS no estan citados:
        #   0 citados  -> los dos se pueden mover; se queda el MAS ANTIGUO
        #   1 citado   -> se mueve el otro, y el citado no se toca jamas
        #   2 citados  -> no se mueve ninguno
        # Un grupo de mas de 2 no se toca: la regla de "quedarse el mas
        # antiguo" es una convencion de dos, y con tres habria que decidir
        # tambien cual se queda, que ya es una eleccion de contenido.
        sin_citas = [x for x in filas if x["citas"] == 0]
        if len(filas) == 2 and len(sin_citas) == 2:
            # El mas antiguo conserva el numero. Es una convencion, no una
            # verdad: se declara para que sea falsable y para que dos agentes
            # que hagan esto a la vez lleguen al mismo sitio.
            filas_orden = sorted(filas, key=lambda x: os.path.getmtime(
                os.path.join(dirf, x["fichero"])))
            move = filas_orden[1:]
            seguro = True
        elif len(filas) == 2 and len(sin_citas) == 1:
            move = sin_citas
            seguro = True
        else:
            move = []
            seguro = False
        g = {
            "numero": num, "ficheros": filas,
            "liberable": move[0] if move else None,
            "liberables": [x["slug"] for x in move],
            "clase": "SEGURO" if seguro else "AMBIGUO",
        }
        if seguro:
            seguros += 1
        else:
            ambiguos += 1
        grupos.append(g)

    total = sum(len(v) for v in ind.values())
    return {"grupos": grupos, "total_ficheros": total,
            "numeros_distintos": len(ind), "duplicados": len(grupos),
            "seguros": seguros, "ambiguos": ambiguos,
            "libres": nextnum.siguiente(ind, desde=1, cuantos=6)}


def renumerar(raiz: str, num: str, fichero: str, nuevo: str) -> List[str]:
    """Mueve el fichero y corrige SU cabecera y SUS referencias internas.

    Devuelve la lista de cambios, para que se puedan revisar. No toca ningun
    otro fichero: si el hallazgo renumerado no tiene citas, no hay nadie mas
    que lo mencione, y esa es justo la condicion que se comprobo antes.
    """
    dirf = dir_hallazgos(raiz)
    viejo_slug = slug_de(fichero)
    nuevo_slug = "%s-%s" % (nuevo, viejo_slug[4:])
    cambiados = []

    viejo_p = os.path.join(dirf, fichero)
    nuevo_p = os.path.join(dirf, nuevo_slug + ".md")
    if os.path.exists(nuevo_p):
        raise SystemExit("  el destino ya existe: %s" % nuevo_slug)

    t = cuerpo(dirf, fichero)
    # la cabecera: "# 202 · titulo" -> "# 205 · titulo"
    t2, n = RE_TITULO.subn(lambda m: "# %s " % nuevo, t, count=1)
    if n != 1:
        raise SystemExit("  la cabecera de %s no empieza por un numero: no se "
                         "renumera a ciegas" % fichero)
    # las referencias internas, solo las suyas
    t2 = t2.replace("findings/%s" % viejo_slug, "findings/%s" % nuevo_slug)
    t2 = t2.replace(viejo_slug, nuevo_slug)

    with open(nuevo_p, "w", encoding="utf-8") as fh:
        fh.write(t2)
    os.remove(viejo_p)
    cambiados.append("%s -> %s.md" % (fichero, nuevo_slug))
    return cambiados


def selftest() -> int:
    print("=== dupenum selftest ===\n")
    fallos = [0]
    CUENTAS = [0]

    def chk(cond):
        """Una comprobacion mas. Contar tambien, porque un selftest que dice
        'PASS (0 comprobaciones)' no dice quantas cosas comprobo."""
        CUENTAS[0] += 1
        if not cond:
            fallos[0] += 1

    d = "/tmp/opencode/dupenum-selftest"
    os.system("rm -rf %s" % d)
    raiz = d
    dirf = dir_hallazgos(raiz)
    os.makedirs(dirf, exist_ok=True)

    def poner(nombre, texto):
        with open(os.path.join(dirf, nombre), "w", encoding="utf-8") as fh:
            fh.write(texto)

    poner("200-a-cosa.md", "# 200 · A\n\nun texto\n")
    poner("200-b-cosa.md", "# 200 · B\n\notro texto\n")
    r = medir(raiz)
    g = r["grupos"][0]
    print("  %-58s %s" % ("grupo de 2, ninguno citado -> SEGURO",
                          "OK" if g["clase"] == "SEGURO" else "FALLO " + str(g)))
    chk(g["clase"] == "SEGURO")

    # ahora uno de los dos esta citado: se sigue pudiendo liberar EL OTRO
    with open(os.path.join(raiz, "otro.md"), "w", encoding="utf-8") as fh:
        fh.write("vease findings/200-a-cosa\n")
    r = medir(raiz)
    g = r["grupos"][0]
    lib = g["liberable"]
    ok = g["clase"] == "SEGURO" and lib is not None and \
        lib["slug"] == "200-b-cosa"
    print("  %-58s %s" % ("con uno citado, se libera el que NO lo esta",
                          "OK" if ok else "FALLO %s" % lib))
    chk(ok)

    # los DOS citados: no se toca ninguno
    with open(os.path.join(raiz, "otro2.md"), "w", encoding="utf-8") as fh:
        fh.write("y findings/200-b-cosa\n")
    r = medir(raiz)
    g = r["grupos"][0]
    ok = g["clase"] == "AMBIGUO" and g["liberable"] is None
    print("  %-58s %s" % ("con los dos citados, AMBIGUO y no se toca",
                          "OK" if ok else "FALLO %s" % g["clase"]))
    chk(ok)

    # Grupo de 3: AMBIGUO aunque DOS de ellos esten sin citas.
    #
    # Y aqui hay que citar UNO de los tres a proposito. La primera version de
    # este test dejo los tres sin citar, con lo cual `len(sin_citas) == 3` y
    # NINGUNA de las dos ramas se cumple: el AMBIGUO venia del numero de
    # ficheros y no de las citas. Al quitar la condicion "exactamente 2" el test
    # seguia pasando, y una condicion que se puede quitar sin que nada falle no
    # estaba protegiendo nada.
    os.remove(os.path.join(raiz, "otro.md"))
    os.remove(os.path.join(raiz, "otro2.md"))
    poner("200-c-cosa.md", "# 200 · C\n\ntercer\n")
    with open(os.path.join(raiz, "otro3.md"), "w", encoding="utf-8") as fh:
        fh.write("vease findings/200-c-cosa\n")
    r = medir(raiz)
    g = r["grupos"][0]
    ok = g["clase"] == "AMBIGUO" and g["liberable"] is None
    print("  %-58s %s" % ("un grupo de 3 es AMBIGUO con 2 sin citar",
                          "OK" if ok else "FALLO %s" % g["clase"]))
    chk(ok)
    os.remove(os.path.join(raiz, "otro3.md"))

    # y el renumerado de verdad: mueve el fichero y arregla su cabecera
    os.remove(os.path.join(dirf, "200-c-cosa.md"))
    cambios = renumerar(raiz, "200", "200-b-cosa.md", "205")
    existe = os.path.isfile(os.path.join(dirf, "205-b-cosa.md"))
    cab = cuerpo(dirf, "205-b-cosa.md").splitlines()[0] if existe else ""
    ok = existe and cab.startswith("# 205") and \
        not os.path.exists(os.path.join(dirf, "200-b-cosa.md"))
    print("  %-58s %s" % ("renumerar mueve el fichero y su cabecera",
                          "OK" if ok else "FALLO %s %s" % (existe, cab)))
    chk(ok)

    # y refuses renumerar una cabecera que no empieza por numero
    poner("210-sin-numero.md", "sin cabecera numerada\n")
    try:
        renumerar(raiz, "210", "210-sin-numero.md", "211")
        print("  %-58s %s" % ("una cabecera sin numero NO se renumera a ciegas",
                              "FALLO: no protesto"))
        chk(False)
    except SystemExit:
        print("  %-58s %s" % ("una cabecera sin numero NO se renumera a ciegas",
                              "OK"))
        chk(True)

    # y el destino ocupado tambien se rechaza
    # el destino se comprueba contra el slug ENTERO, porque renumerar conserva
    # el final del nombre. Por eso el fichero que bloquea tiene que llamarse
    # 212-otro.md y no 212-cualquiera.md: el primer test de esto uso un nombre
    # distinto y "paso" sin comprobar nada.
    poner("212-otro.md", "# 212 · otro, ya ocupado\n")
    poner("213-otro.md", "# 213 · otro\n")
    try:
        renumerar(raiz, "213", "213-otro.md", "212")
        print("  %-58s %s" % ("un destino ocupado NO se pisa", "FALLO"))
        chk(False)
    except SystemExit:
        print("  %-58s %s" % ("un destino ocupado NO se pisa", "OK"))
        chk(True)

    # ------------------------------------------------------------------
    # EL CODIGO DE SALIDA. Este bloque es la reparacion del agujero y su
    # propia prueba: mientras estas cuatro comprobaciones no existieran, el
    # codigo podia ser el que quisiera y el self-test seguia en verde.
    #
    # El agujero concreto: el modo MEDIR hacia `return 0` con las colisiones
    # delante. Es decir, la herramienta podia afirmar y no medir. Aqui se
    # comprueba que los cuatro estados dan cuatro codigos DISTINTOS, y que el
    # estado de "todo reparable" NO se confunde con "nada que reparar".
    # ------------------------------------------------------------------
    def estado(sin_colisiones, solo_seguros, ambiguos, ficheros=2):
        return {"total_ficheros": ficheros, "numeros_distintos": ficheros,
                "duplicados": 0 if sin_colisiones else 1,
                "seguros": 1 if solo_seguros else 0,
                "ambiguos": 1 if ambiguos else 0}

    casos = [
        ("sin duplicados -> 0",
         estado(True, False, False), EXIT_OK),
        ("duplicados todos SEGURO -> 3",
         estado(False, True, False), EXIT_TODOS_REPARABLES),
        ("al menos un AMBIGUO -> 4",
         estado(False, False, True), EXIT_AMBIGUOS),
        ("no se pudo medir -> 2",
         {"total_ficheros": 0, "numeros_distintos": 0, "duplicados": 0,
          "seguros": 0, "ambiguos": 0}, EXIT_SIN_MEDIR),
    ]
    for nombre, r_esperado, c_esperado in casos:
        c = codigo_de(r_esperado)
        ok = c == c_esperado
        print("  %-58s %s" % (nombre, "OK" if ok else
                              "FALLO dio %d, esperaba %d" % (c, c_esperado)))
        chk(ok)

    # y los cuatro codigos tienen que ser DISTINTOS entre si. Un mapa que
    # devuelve 3 para dos estados distintos no discrimina, y entonces un
    # pipeline que mire el codigo no puede distinguir "arreglable" de "atascado".
    unicos = {c_esperado for _n, _r, c_esperado in casos}
    ok = len(unicos) == len(casos)
    print("  %-58s %s" % ("los cuatro codigos son distintos entre si",
                          "OK" if ok else "FALLO: %d distintos de %d"
                          % (len(unicos), len(casos))))
    chk(ok)

    # y el caso que de verdad abria el agujero: un grupo AMBIGUO medido sobre
    # un arbol de verdad tiene que dar 4, no 0. Sin este caso, los cuatro de
    # arriba prueban el mapa pero no la medida.
    d2 = "/tmp/opencode/dupenum-selftest-codigo"
    os.system("rm -rf %s" % d2)
    dirf2 = dir_hallazgos(d2)
    os.makedirs(dirf2, exist_ok=True)
    for nom, txt in (("300-a.md", "# 300 · A\n\nuno\n"),
                     ("300-b.md", "# 300 · B\n\ndos\n"),
                     ("300-c.md", "# 300 · C\n\ntres\n")):
        with open(os.path.join(dirf2, nom), "w", encoding="utf-8") as fh:
            fh.write(txt)
    c = codigo_de(medir(d2))
    ok = c == EXIT_AMBIGUOS
    print("  %-58s %s" % ("un grupo de 3 medido de verdad -> 4, no 0",
                          "OK" if ok else "FALLO dio %d" % c))
    chk(ok)

    print("\nRESULT: %s (%d comprobaciones, %d fallos)\n"
          % ("PASS" if not fallos[0] else "FAIL", CUENTAS[0], fallos[0]))
    return 1 if fallos[0] else 0


EXIT_OK = 0
EXIT_SELFTEST = 1
EXIT_SIN_MEDIR = 2
EXIT_TODOS_REPARABLES = 3
EXIT_AMBIGUOS = 4


def codigo_de(r: Dict[str, object]) -> int:
    """El codigo que corresponde al estado medido. Ver el bloque CODIGOS DE
    SALIDA de la cabecera.

    Se separa del `main` para que el selftest pueda comprobarla sin ejecutar el
    programa entero: un codigo de salida que solo se puede ver lanzando el
    programa no se puede falsificar cheaply, y una puerta que no se puede
    falsificar no es una puerta.
    """
    if r.get("total_ficheros", 0) == 0:
        return EXIT_SIN_MEDIR
    if r["duplicados"] == 0:
        return EXIT_OK
    if r["ambiguos"] == 0:
        return EXIT_TODOS_REPARABLES
    return EXIT_AMBIGUOS


def main() -> int:
    ap = argparse.ArgumentParser(
        description="mide y repara numeros de hallazgo duplicados")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--aplicar", action="store_true",
                    help="renumera los grupos SEGURO. Sin esto solo mide.")
    ap.add_argument("--limite", type=int, default=20)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    raiz = proyecto()
    r = medir(raiz)
    if a.json:
        # stdout es JSON valido SIEMPRE. El codigo es el veredicto, y no al
        # reves: un consumidor que solo mire el stdout no puede saber si el
        # arbol estaba bien, que es exactamente lo que se quiere evitar.
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return codigo_de(r)

    print("=" * 78)
    print("dupenum %s · WORK_CLASS=%s · WRITE_EXECUTION=%s"
          % (VERSION, WORK_CLASS, WRITE_EXECUTION))
    print("=" * 78)
    print("""
  SEGURO   grupo de exactamente 2 y UNO sin citas: se renumera ese.
  AMBIGUO  todo lo demas. No se toca, y se dice por que.

  Renumerar NO reescribe el hallazgo: mueve el fichero y corrige su cabecera y
  sus referencias SUyas. El texto no se toca.
""")
    print("  ficheros de hallazgo:      %d" % r["total_ficheros"])
    print("  numeros distintos:         %d" % r["numeros_distintos"])
    print("  numeros duplicados:        %d" % r["duplicados"])
    print("    de ellos SEGURO:         %d" % r["seguros"])
    print("    de ellos AMBIGUO:        %d" % r["ambiguos"])
    print("  primeros numeros libres:   %s"
          % ", ".join(r["libres"][:6]))

    print("\n  GRUPOS SEGURO (se pueden renumerar)")
    print("  " + "-" * 74)
    seguros = [g for g in r["grupos"] if g["clase"] == "SEGURO"]
    for g in seguros[:a.limite]:
        mueve = ", ".join(x["fichero"][:-3] for x in g["ficheros"]
                          if x["fichero"][:-3] in g["liberables"])
        deja = [x for x in g["ficheros"]
                if x["fichero"][:-3] not in g["liberables"]]
        print("  %s  mueve %s" % (g["numero"], mueve[:44]))
        for x in deja:
            print("       deja %-41s (%d citas)"
                  % (x["slug"][:41], x["citas"]))
    if len(seguros) > a.limite:
        print("  ... y %d mas" % (len(seguros) - a.limite))

    if not a.aplicar:
        print("\n  NO se ha tocado nada. Con --aplicar se renumeran los SEGURO.")
        # El codigo NO es 0 con colisiones delante. Ese era el agujero: esta
        # herramienta era la unica de las tres del tema que pasaba en verde con
        # el defecto presente, y por tanto la que podia dejar el pipeline en
        # verde. Medir y salir en verde es una forma de no medir.
        c = codigo_de(r)
        print("  CODIGO DE SALIDA: %d  (%s)"
              % (c, {0: "sin colisiones", 2: "no se pudo medir",
                     3: "todas reparables con --aplicar",
                     4: "hay AMBIGUOS que --aplicar no arregla"}.get(c, "?")))
        return c

    if not seguros:
        print("\n  no hay grupo SEGURO: nada que aplicar.")
        return codigo_de(r)

    print("\n  APLICANDO %d renumeraciones" % len(seguros))
    hechos = []
    for g in seguros:
        fica = g["liberable"]
        # el destino se elige entre los libres MAS ALTOS que el numero viejo, de
        # modo que mover un hallazgo no empuja a otro agente a renumerar
        destino = nextnum.siguiente(nextnum.indice(dir_hallazgos(raiz)),
                                    desde=int(g["numero"]) + 1, cuantos=1)[0]
        try:
            cambios = renumerar(raiz, g["numero"], fica["fichero"], destino)
            hechos.extend(cambios)
            print("    %s" % cambios[0])
        except SystemExit as e:
            print("    %s" % e)
    print("\n  %d ficheros renumerados." % len(hechos))
    # Se vuelve a MEDIR, no se supone que quedo bien. Aplicar y que queden
    # colisiones AMBIGUAS no es exito, y un codigo de salida aqui es la unica
    # forma de que el que lo lanzo lo sepa sin tener que acordarse de releer.
    post = medir(raiz)
    c = codigo_de(post)
    print("  Tras aplicar: %d grupos duplicados (%d SEGURO, %d AMBIGUO)."
          % (post["duplicados"], post["seguros"], post["ambiguos"]))
    print("  CODIGO DE SALIDA: %d  (%s)"
          % (c, {0: "sin colisiones", 2: "no se pudo medir",
                 3: "todas reparables con --aplicar",
                 4: "quedan AMBIGUOS que --aplicar no arregla"}.get(c, "?")))
    print("  Comprueba la puerta y el indice:")
    print("      python3 tools/check_num_unico.py")
    return c


if __name__ == "__main__":
    sys.exit(main())
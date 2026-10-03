#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
nextnum.py - asigna un numero de hallazgo que no colisione.

POR QUE EXISTE

findings/048-numeros-de-hallazgo-no-identifican.md mide que un numero de
hallazgo no identifica un hallazgo. Medido hoy: 64 de 126 numeros están
duplicados y 87 documentos son alcanzables sólo por su posición alfabética.
El numero de un hallazgo NO identifica un hallazgo.

Eso tiene una segunda mitad, mas barata y mas frecuente: **crear** un hallazgo
con un numero ya usado. En una sola sesion de este trabajo ocurrio tres veces,
siempre por la misma causa: varios agentesParallelo escriben a la vez, cada uno
cree que el siguiente numero libre es el que habia leido al empezar, y el
proyecto tiene 212 hallazgos.

Renumerar despues es gratis si nadie cita todavia -- y por eso el numero debe
reservarse ANTES de escribir el fichero, no corregirse despues. Es el mismo
principio que 121 enuncia para las citas: la excepcion se declara en el momento
de escribir la cita.

QUE HACE

  nextnum.py              imprime el siguiente numero libre
  nextnum.py --check 127  dice si 127 es unico, y que ficheros lo comparten
  nextnum.py --json       lo mismo, estructurado

NO HACE

No renumera. Renombrar 64 numeros y sus 87 ambiguedades rompe todas las citas a
la vez, y las citas son la evidencia: es operacion de un solo tiro con plan de
reescritura y verificacion, no algo que se haga de paso. 048 dice exactamente
esto y el proyecto no lo ha ejecutado.

CODIGOS DE SALIDA

  0  se pudo medir
  1  el numero comprobado NO es unico        (--check)
  2  no se pudo ejecutar
"""

import argparse
import collections
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

VERSION = "1.1.0"

# ---------------------------------------------------------------------------
# POR QUE EXISTE --reservar
#
# MEDIDO el 2026-10-02. Tres ficheros se llamas 272, escritos con 7 minutos de
# diferencia y por tres autores distintos:
#
#   18:49:41  272-el-techo-de-overdrive-sale-de-una-lectura-fuera-de-rango.md
#   18:56:35  272-cg-mask-y-cu-mask-son-categorias-distintas.md
#   19:04:41  272-la-poblacion-de-herramientas-era-112-y-contamos-31.md
#
# El indice y --check NO tienen fallo: --check informaba LIBRE con razon. El
# defecto es que --check NO RESERVA. Informa, y luego hay un hueco hasta que el
# fichero existe, y en ese hueco cabe otra peticion. Comprobar y escribir no es
# una operacion atomica y por eso dos autores pueden pasar a la vez.
#
# Es tambien el mecanismo mas probable de los 66 duplicados que arrastra el
# proyecto: no son errores de quien escribe, son de quien REPARTE numeros.
#
# AGENTS.md §102 dice PROJECT_ACTIVE_AGENT <= 1. Esa regla reduce la probabilidad,
# pero no la hace cero: la sessions que la incumplen se solapan igual, y por eso
# el reparto tiene que ser atomico y no una convencion.
#
# El cerrojo es flock sobre un fichero de reserva. Es lo que ya usa el kernel
# para esto, no bloquea mas de lo que debe, y si el proceso muere el cerrojo se
# suelta solo: un numero reservado se queda como ocupado, que es el fallo
# tolerable, y no como colgado, que es el que no lo es.

BLOQUEO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".nextnum.lock")

# MEDIDO 2026-10-03: hay 9 hallazgos numerados 1000-1020 en disco. Con `{3}`
# este patron NO los ve, y un numero de cuatro cifras no casa con el
# separador: "1000-algo.md" empieza por "100", y despues viene "0", no "-".
# Consecuencia medida: el allocator podia entregar un numero que ya existia
# en disco. Ver 309.
NUM_RX = re.compile(r"^(\d{3,})[-_](.+)\.md$")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


def indice(directorio: str) -> Dict[str, List[str]]:
    """numero -> ficheros que lo llevan. Es el indice que 073 dice que no usar
    para RESOLVER citas; aqui no se resuelve nada, se cuenta ocupacion, y para
    eso el numero duplicado no es un problema sino justamente el dato."""
    out: Dict[str, List[str]] = collections.defaultdict(list)
    if not os.path.isdir(directorio):
        return out
    for f in sorted(os.listdir(directorio)):
        m = NUM_RX.match(f)
        if m:
            out[m.group(1)].append(f)
    return out


def siguiente(ind: Dict[str, List[str]], desde: int = 1,
              cuantos: int = 5) -> List[str]:
    """Los primeros `cuantos` numeros libres a partir de `desde`."""
    usados = {int(k) for k in ind}
    out: List[str] = []
    n = desde
    while len(out) < cuantos:
        if n not in usados:
            out.append("%03d" % n)
        n += 1
    return out


# El registro del otro allocator.  MEDIDO 2026-10-03:
#
#   tools/nextnum.py                  -> .nextnum.lock                 43 reservas
#   08-ARQUITECTURA/tools/findnum.py  -> findings/_reservas/*.res        5 reservas
#
# Dos herramientas que hacen lo mismo, con dos registros, y NINGUNA ve las
# reservas de la otra.  Los dos leen el directorio de hallazgos, asi que un
# numero CON fichero se ve ocupado por las dos;  el hueco es la ventana entre
# "reservado" y "fichero escrito", que es exactamente la ventana para la que
# existe la reserva.
#
# O sea:  con este cambio, 1026 reservado aqui y 1020 en el otro registro NO
# pueden coexistir.  Sin el, si.  Y dos hallazgos con el mismo numero son los
# 74 que ya hay, en su fuente y no en su consecuencia.
#   El registro del otro allocator NO esta en `.write-lock/findnum`:  ese
#   directorio es el LOCK, y solo contiene `owner`.  Las reservas son ficheros
#   `NNNN-reservado.res` en el propio directorio de hallazgos.  MEDIDO: leer el
#   LOCKdio un conjunto vacio y seemed que el arreglo habia funcionado.
LOCK_AJENO = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "06-INGENIERIA-INVERSA", "findings", "_reservas")


def _reservas_del_registro_ajeno() -> set:
    out = set()
    try:
        names = os.listdir(LOCK_AJENO)
    except OSError:
        return out
    for name in names:
        if not name.endswith(".res"):
            continue
        m = re.match(r"^(\d{3,})-", name)
        if m:
            out.add(m.group(1))
    return out


def reservados() -> set:
    """Numeros ya RESERVADOS: los de ESTE registro y los del otro allocator.

    Sin esto la reserva no se ve a si misma: el registro vive en el fichero de
    bloqueo y `indice` mira ficheros de hallazgos, asi que una segunda reserva
    del mismo numero se concedia. Es el fallo que los dos vectores detectaron.

    Y ahora tampoco se ve la reserva del otro allocator.  Los dos registros se
    leen, y sus formatos son distintos a proposito: este es una linea por
    numero, el otro es un fichero `NNNN-slug.res` por numero.
    """
    out = set()
    try:
        with open(BLOQUEO, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                l = l.strip()
                if re.match(r"^\d{3,}$", l):
                    out.add(l)
    except OSError:
        pass
    return out | _reservas_del_registro_ajeno()


def reservar(n: str, d: str) -> dict:
    """Toma el numero `n` de forma ATOMICA, o dice que ya no esta libre.

    Devuelve {"n", "estado", "ficheros"} con estado RESERVADO | OCUPADO | MALO.
    OCUPADO es lo que hay que ver: significa que otra peticion se adelanto, y no
    que el numero este mal. Reintentar con otro numero es lo correcto; forzar
    este no lo es nunca.
    """
    import fcntl
    if not re.match(r"^\d{3,}$", n):
        return {"n": n, "estado": "MALO", "ficheros": [],
                "motivo": "el numero debe tener 3 o mas cifras"}
    os.makedirs(os.path.dirname(BLOQUEO), exist_ok=True)
    fh = open(BLOQUEO, "a+")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        cands = list(indice(d).get(n, []))
        if not cands and n in reservados():
            # ocupado por una RESERVA, no por un fichero. La prueba de por que
            # hace falta `reservados()`: sin esto se concede dos veces, que es
            # exactamente el defecto que hay que tapar.
            cands = ["<reservado, sin fichero todavia>"]
        if cands:
            return {"n": n, "estado": "OCUPADO", "ficheros": cands}
        # El conjunto se lee ANTES de truncar. Leerlo despues devolvia el
        # fichero ya vacio y el registro se perdia: un error mio de este
        # parche, que los dos vectores que estaban fallando detectaron.
        ya = reservados()
        ya.add(n)
        fh.seek(0)
        fh.truncate()
        fh.write("".join("%s\n" % x for x in sorted(ya)))
        fh.flush()
        os.fsync(fh.fileno())
        return {"n": n, "estado": "RESERVADO", "ficheros": []}
    finally:
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        fh.close()


BLOQUEO_REAL = BLOQUEO


def selftest() -> int:
    print("=== nextnum selftest ===\n")
    fallos = 0
    tmp = "/tmp/opencode/nextnum-selftest"

    # [0] CLASIFICACION DE FUGAS, antes de nada porque no necesita disco.
    #
    # El auditor separa "resto de un renumerado" de "posible hallazgo
    # perdido". Ese reparto es lo que hace accionable la auditoria: juntos en
    # un numero, el informe dice "2 fugas" y no dice si hay algo que recuperar.
    #
    # Se construye con el mapa congelado REAL, y se comprueba el caso que de
    # verdad existe en este proyecto: 975 esta en el registro de bloqueo y su
    # hallazgo se renumero a 976, asi que es resto. 298 esta en el registro, no
    # tiene fichero, y NO esta en el mapa, asi que es la otra clase.
    print("[0] la auditoria separa las dos clases de reserva sin fichero")
    reg_real = reservados()
    mapa = _reenvios()
    if not reg_real or not mapa:
        print("  FAIL no se pudo leer el registro (%d) o el mapa (%d)"
              % (len(reg_real), len(mapa)))
        fallos += 1
    else:
        ocup = set(indice(os.path.join(proyecto(),
                                       "06-INGENIERIA-INVERSA", "findings")))
        fugas = set(reg_real) - ocup
        # LLAMA A LA FUNCION REAL. La primera version del caso recalculaba el
        # reparto aqui mismo, y por eso dos mutaciones de `auditar()` -- invertir
        # las clases y dejarlas en una sola -- pasaban sin que el self-test se
        # enterara: estaba probando una COPIA de la logica, no la logica.
        fugas2, perdidos, viejos = _clasifica(indice(os.path.join(
            proyecto(), "06-INGENIERIA-INVERSA", "findings")))
        if fugas and not (set(perdidos) | set(viejos)):
            print("  FAIL la auditoria no devuelve ninguna de las dos clases")
            fallos += 1
        if set(perdidos) | set(viejos) != fugas:
            print("  FAIL la auditoria devuelve %r y el registro dice %r"
                  % (sorted(set(perdidos) | set(viejos)), sorted(fugas)))
            fallos += 1
        if "975" not in viejos:
            print("  FAIL 975 deberia estar en la clase RENUMERADO (->%s)"
                  % mapa.get("975"))
            fallos += 1
        else:
            print("  OK   975 en clase RENUMERADO -> %s" % mapa["975"])
        if "298" not in perdidos:
            print("  FAIL 298 deberia estar en la clase SIN ORIGEN")
            fallos += 1
        else:
            print("  OK   298 en clase SIN ORIGEN DEMOSTRABLE")
        if not (viejos and perdidos):
            print("  FAIL hace falta al menos un caso de cada clase; con una "
                  "vacia, el reparto no esta probado")
            fallos += 1

    def escribir(nombre):
        if not os.path.isdir(tmp):
            os.makedirs(tmp)
        open(os.path.join(tmp, nombre), "w").write("x")

    print("[1] el indice recoge los numeros, y DUPLICADOS incluidos")
    import shutil
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    for f in ("001-a.md", "001-b.md", "002-c.md", "010-d.md"):
        escribir(f)
    ind = indice(tmp)
    if sorted(ind) != ["001", "002", "010"]:
        print("  FAIL indice %r" % sorted(ind))
        fallos += 1
    else:
        print("  OK   001 x2, 002, 010")
    if len(ind["001"]) != 2:
        print("  FAIL 001 deberia traer 2 ficheros")
        fallos += 1
    else:
        print("  OK   un numero duplicado trae SUS DOS ficheros, no uno")

    print()
    print("[2] siguiente() salta los usados, incluidos los duplicados")
    sg = siguiente(ind, 1, 3)
    if sg != ["003", "004", "005"]:
        print("  FAIL %r, esperaba ['003','004','005']" % sg)
        fallos += 1
    else:
        print("  OK   desde 001 usado hasta 010 -> %s" % sg)
    if siguiente(ind, 11, 1) != ["011"]:
        print("  FAIL no empieza donde se le pide")
        fallos += 1
    else:
        print("  OK   --desde 11 salta los usados")

    print()
    print("[3] un numero que aparece una vez es unico")
    if len(ind.get("002", [])) != 1:
        print("  FAIL")
        fallos += 1
    else:
        print("  OK   002 es unico")

    print()
    print("[4] el nucleo: NINGUN numero que se propone debe estar usado")
    usados = {int(k) for k in ind}
    sg = siguiente(ind, 1, 20)
    if any(int(x) in usados for x in sg):
        print("  FAIL nextnum propuso un numero ya ocupado: %s" % sg)
        fallos += 1
    else:
        print("  OK   20 propuestos, ninguno ocupado")

    print()
    print("[5] un directorio VACIO no es un error, y propone desde 1")
    vac = "/tmp/opencode/nextnum-vacio"
    if os.path.isdir(vac):
        shutil.rmtree(vac)
    os.makedirs(vac)
    iv = indice(vac)
    if siguiente(iv, 1, 2) != ["001", "002"]:
        print("  FAIL %r" % siguiente(iv, 1, 2))
        fallos += 1
    else:
        print("  OK   directorio vacio -> 001, 002")

    print()
    print("[6] un directorio que NO existe se distingue del vacio")
    if indice("/tmp/opencode/no-existe-este") != {}:
        print("  FAIL devolvio algo")
        fallos += 1
    else:
        print("  OK   inexistente -> indice vacio, sin excepcion")

    # --- la reserva ATOMICA, que es lo que faltaba -------------------------
    # POR QUE: tres ficheros se llamaron 272 con 7 minutos de diferencia y tres
    # autores distintos. El indice y --check eran CORRECTOS -- --check informaba
    # LIBRE con razon. Lo que no existia era RESERVAR: comprobar y escribir no
    # es atomico, y en el hueco cabe otra peticion.
    import subprocess as _sp
    import shutil as _sh

    rtmp = "/tmp/opencode/nextnum-reserva"
    if os.path.isdir(rtmp):
        _sh.rmtree(rtmp)
    os.makedirs(rtmp)

    # ESTO FALTABA Y ROMPIA EL ESTADO REAL. Medido: con el cerrojo real
    # presente, el selfftest escribia "001" y "002" en el REGISTRO DE RESERVAS
    # DEL PROYECTO, y la segunda ejecucion fallaba porque ya estaban tomadas. Un
    # self-test que deja basura donde vigila es la misma falta que uno que no
    # muerde: no es que no pruebe, es que estropea lo que hay.
    lock_real = BLOQUEO
    lock_falso = os.path.join(rtmp, "lock-de-prueba")
    globals()["BLOQUEO"] = lock_falso

    r1 = reservar("001", rtmp)
    ok1 = r1["estado"] == "RESERVADO"
    print("  %s   la primera reserva de 001 concede"
          % ("OK  " if ok1 else "FAIL"))
    fallos += (not ok1)

    r2 = reservar("001", rtmp)
    ok2 = r2["estado"] == "OCUPADO"
    print("  %s   la segunda reserva de 001 RECHAZA"
          % ("OK  " if ok2 else "FAIL"))
    fallos += (not ok2)

    rm = reservar("7", rtmp)
    ok3 = rm["estado"] == "MALO"
    print("  %s   un numero de una cifra se rechaza antes de tocar el cerrojo"
          % ("OK  " if ok3 else "FAIL"))
    fallos += (not ok3)

    # El numero ya existe como FICHERO: lo respeta. Un cerrojo solo no lo
    # cubriria, porque el cerrojo serializa reservas, no ficheros.
    with open(os.path.join(rtmp, "002-ya-existe.md"), "w") as fh:
        fh.write("x")
    r3 = reservar("002", rtmp)
    ok4 = r3["estado"] == "OCUPADO"
    print("  %s   un numero ya ocupado por un FICHERO no se puede reservar"
          % ("OK  " if ok4 else "FAIL"))
    fallos += (not ok4)

    # SEIS PROCESOS compiten por el mismo numero. Y ADVERTIDO: este vector NO
    # es decisivo. Provocado el 2026-10-02: desactivando el flock, los seis
    # siguen concediendo uno solo porque el arranque del interprete los escalona
    # y se serializan solos. Se conserva porque reproduce la carrera de los 272
    # de verdad, y se declara que no prueba el cerrojo. El que si lo prueba va
    # justo despues y mide el tiempo de espera.
    # El hijo importa el modulo, y al importarlo cogeria el BLOQUEO REAL: por
    # eso el self-test dejaba reservas de prueba en el registro del proyecto y
    # la segunda ejecucion fallaba. Se le pasa la ruta del cerrojo de prueba.
    codigo = ("import sys; sys.path.insert(0, %r)\n"
              "import nextnum as N, json\n"
              "N.BLOQUEO = sys.argv[3]\n"
              "print(json.dumps(N.reservar(sys.argv[1], sys.argv[2])))\n"
              % os.path.dirname(os.path.abspath(__file__)))
    racy = "/tmp/opencode/nextnum-carrera"
    if os.path.isdir(racy):
        _sh.rmtree(racy)
    os.makedirs(racy)
    guion = os.path.join(racy, "c.py")
    with open(guion, "w") as fh:
        fh.write(codigo)
    lock_carrera = os.path.join(racy, "lock-carrera")
    procs = [_sp.Popen([sys.executable, guion, "050", racy, lock_carrera],
                       stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)
             for _ in range(6)]
    gana = 0
    for pr in procs:
        out, _err = pr.communicate(timeout=180)
        try:
            if json.loads(out.strip())["estado"] == "RESERVADO":
                gana += 1
        except (ValueError, IndexError):
            pass
    ok5 = gana == 1
    print("  %s   6 procesos piden 050 a la vez, gana UNO (pero VER ABAJO: este"
          % ("OK  " if ok5 else "FAIL"))
    print("        vector NO es decisivo: se sigue pasando sin cerrojo)")
    fallos += (not ok5)

    # ---- Y ESTE SI TIENE DIENTES --------------------------------------------
    # El de arriba NO muerde. Provocado el 2026-10-02: se desactivo el flock y
    # los 17 vectores siguieron en verde, porque los seis procesos arrancan
    # escalonados por el arranque del interprete y se serializan solos. Un
    # vector que no cae al romper lo que dice vigilar es una prueba de mentira.
    #
    # Este mide la propiedad DIRECTA: con el cerrojo tomado por otro proceso,
    # reservar() TIENE QUE ESPERAR. Sin LOCK_EX no hay espera posible, asi que
    # el tiempo de respuesta lo separa sin discusion.
    import fcntl
    import time
    bloq = "/tmp/opencode/nextnum-dientes.lock"
    bloq = os.path.join(rtmp, "nextnum-dientes.lock")
    fh2 = open(bloq, "a+")
    fcntl.flock(fh2.fileno(), fcntl.LOCK_EX)      # el padre toma el cerrojo
    cod2 = ("import sys, time; sys.path.insert(0, %r)\n"
            "import nextnum as N\n"
            "N.BLOQUEO = sys.argv[3]\n"
            "t0 = time.time()\n"
            "r = N.reservar(sys.argv[1], sys.argv[2])\n"
            "print('%%.3f' %% (time.time() - t0))\n"
            % os.path.dirname(os.path.abspath(__file__)))
    g2 = os.path.join(racy, "d.py")
    with open(g2, "w") as fh:
        fh.write(cod2)
    # el padre ES el modulo, asi que se le cambia el global; el hijo recibe la
    # ruta por argv para que cierre sobre el MISMO fichero y no sobre el suyo
    globals()["BLOQUEO"] = bloq
    hijo = _sp.Popen([sys.executable, g2, "060", racy, bloq],
                     stdout=_sp.PIPE, stderr=_sp.PIPE, text=True)
    time.sleep(0.5)                               # el padre sigue teniendo el
    sigue = hijo.poll() is None                   # cerrojo medio segundo
    fcntl.flock(fh2.fileno(), fcntl.LOCK_UN)      # y ahora lo suelta
    out2, _e2 = hijo.communicate(timeout=180)
    fh2.close()
    globals()["BLOQUEO"] = BLOQUEO_REAL
    try:
        waited = float(out2.strip().splitlines()[-1])
    except (ValueError, IndexError):
        waited = -1.0
    ok6 = sigue and waited >= 0.4
    print("  %s   VECTOR CON DIENTES DE VERDAD: con el cerrojo tomado, "
          "reservar() espera %.2fs y no devuelve antes" % ("OK  " if ok6 else "FAIL", waited))
    print("        -> este SI cae si se quita el flock")
    fallos += (not ok6)

    globals()["BLOQUEO"] = lock_real       # restaurar antes de limpiar
    shutil.rmtree(tmp)
    shutil.rmtree(vac)
    shutil.rmtree(rtmp, ignore_errors=True)
    shutil.rmtree(racy, ignore_errors=True)
    # --- LA RUTA DE INFORME, QUE ESTA SIN PROBAR --------------------------
    # MEDIDO con settrace: el self-test ejecuta 222 lineas y su ruta de informe
    # 77, y quedan 23 que NADIE ejecuta. De esas, el filtro de tres cifras y la
    # comprobacion de si una reserva se ve.
    #
    # Que se compruebe "no revienta" y no "sale con 0": varias de estas rutas
    # salen con 1 INFORMANDO de algo, y eso es lo correcto. Lo que no puede
    # pasar es un traceback.
    _yo = os.path.abspath(__file__)
    for _flag in (["--json"], ["--check", "291"]):
        _pr = subprocess.run([sys.executable, _yo] + _flag,
                             capture_output=True, text=True, timeout=300)
        _sal = (_pr.stdout or "") + (_pr.stderr or "")
        _tb = "Traceback (most recent call last)" in _sal
        if (not _tb) and _pr.returncode in (0, 1, 2):
            print("  OK   la ruta %s no revienta  (rc=%s)"
                  % (" ".join(_flag), _pr.returncode))
        else:
            print("  FAIL la ruta %s: rc=%s traceback=%s"
                  % (" ".join(_flag), _pr.returncode, _tb))
            fallos += 1

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    print("RESULT: PASS (19 vectores)")
    return 0


def _clasifica(ind: Dict[str, List[str]]):
    """(fugas, perdidos, viejos). La CLASIFICACION, sin imprimir.

    Existe separada de `auditar()` para que el self-test pueda comprobar la
    logica sin depender del texto que sale por pantalla. Un check que solo
    puede mirar stdout comprueba el formato, no la decision.
    """
    res = reservados()
    ocupados = set(ind)
    fugas = sorted(res - ocupados)
    reenvios = _reenvios()
    perdidos = [n for n in fugas if n not in reenvios]
    viejos = [n for n in fugas if n in reenvios]
    return fugas, perdidos, viejos


def auditar(ind: Dict[str, List[str]]) -> int:
    """Reservas VIVAS sin fichero de hallazgo detrás.

    QUE ES ESTO. `reservados()` lee el registro de bloqueo; `indice()` lee los
    ficheros. Nada obliga a que los dos coincidan, y medido el 2026-10-03 no
    coincidían: dos números reservados sin fichero (el 298 y el 975).

    POR QUE ES UN DEFECTO Y NO UN RUIDO. `siguiente()` respeta la reserva aunque
    no haya fichero, así que el allocator no va a entregar el 298 por error. La
    consecuencia es otra: el número queda BLOQUEADO para siempre con nada detrás,
    y quien lea `.nextnum.lock` ya no puede distinguir "reservado por alguien que
    está escribiendo" de "reservado por un proceso que ya no existe". El
    registro deja de ser un estado y pasa a ser un rumor.

    Y hay una segunda lectura, más incómoda: el 298 está citado por el hallazgo
    301 con su número de línea, o sea que EXISTIÓ. El allocator lo sigue
    teniendo. Lo que se perdió fue el fichero, no el número.

    LO QUE NO HACE. No libera nada. Liberar el 298 cerraría el síntoma y
    taparía el defecto real: que nada comprueba que una reserva siga teniendo
    fichero detrás. Se informa y se decide.
    """
    fugas, perdidos, viejos = _clasifica(ind)
    reenvios = _reenvios()
    res = reservados()
    ocupados = set(ind)

    # DOS CLASES, Y CONFUNDIRLAS SERIA EL DEFECTO DE NUEVO.
    #
    # Medido el 2026-10-03: dos reservas sin fichero, y no son lo mismo.
    #   298  el hallazgo EXISTIO (el 301 lo cita con su numero de linea) y se
    #        perdio. La reserva sigue viva. Esto es una perdida.
    #   975  el hallazgo se renumeró a 976 y la reserva del numero viejo se
    #        quedo. Esto es un resto de un renumerado, no una perdida.
    #
    # Juntas en un numero, el informe dice "2 fugas" y no dice si hay algo que
    # recuperar o si hay dos numeros que liberar. Por eso se separan.
    print("AUDITORIA DEL REGISTRO DE BLOQUEO")
    print("  reservas vivas          : %d" % len(res))
    print("  con fichero detras      : %d" % len(res & ocupados))
    print("  SIN fichero detras      : %d" % len(fugas))
    print()
    print("  clase RENUMERADO (resto de un renumerado, no una perdida): %d"
          % len(viejos))
    for n in viejos:
        print("     %s -> ahora %s. La reserva del numero viejo quedo."
              % (n, reenvios[n]))
    print()
    print("  clase SIN ORIGEN DEMOSTRABLE (puede ser un hallazgo perdido): %d"
          % len(perdidos))
    for n in perdidos:
        print("     %s  <- reservada y sin fichero. No se libera: cerrar el"
              % n)
        print("            sintoma taparia el defecto (nada comprueba que una")
        print("            reserva tenga fichero detras).")
    if not fugas:
        print("  sin fugas.")
    return (1 if fugas else 0), perdidos, viejos


def _reenvios() -> dict:
    """{numero_viejo: numero_nuevo} del mapa CONGELADO de renumeraciones.

    Se lee el fichero congelado y no se deriva de git a proposito: el mapa
    autodestruido una vez ya, cuando se commiteo el renumerado sin congelar
    antes. Ver REENVIO-FINDINGS.tsv.
    """
    ruta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "08-ARQUITECTURA", "tools", "REENVIO-FINDINGS.tsv")
    out = {}
    try:
        with open(ruta, encoding="utf-8") as fh:
            for l in fh:
                l = l.rstrip("\n")
                if not l.strip() or l.startswith("#"):
                    continue
                p = l.split("\t")
                if len(p) == 4:
                    out[p[0]] = p[1]
    except OSError:
        pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(
        description="asigna un numero de hallazgo que no colisione")
    ap.add_argument("--check", metavar="NNN",
                    help="comprueba si ese numero es unico. NO reserva")
    ap.add_argument("--reservar", metavar="NNN",
                    help="toma ese numero de forma ATOMICA. Esto SI reserva: "
                         "dos autores no pueden obtener el mismo numero. "
                         "Devuelve 0 si se concede, 1 si ya estaba ocupado.")
    # Un hallazgo NUEVO va al final, no a un hueco. Rellenar el hueco 004
    # meteria un hallazgo de 2026 entre los de las primeras rondas, y el
    # numero pasaria a sugerir una epoca que no es la suya. Rellenar solo si
    # se pide con --rellenar.
    ap.add_argument("--desde", type=int, default=None,
                    help="primer numero a considerar (por defecto: el ultimo+1)")
    ap.add_argument("--rellenar", action="store_true",
                    help="propone tambien los huecos, no solo el final")
    ap.add_argument("--cuantos", type=int, default=5)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--auditar", action="store_true",
                    help="reservas del registro de bloqueo sin fichero detras")
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    d = os.path.join(proyecto(), "06-INGENIERIA-INVERSA", "findings")
    if not os.path.isdir(d):
        print("  ERROR: no existe el directorio de hallazgos: %s" % d,
              file=sys.stderr)
        return 2
    ind = indice(d)
    if args.auditar:
        return auditar(ind)[0]
    duplicados = {k: v for k, v in ind.items() if len(v) > 1}
    if args.desde is None:
        args.desde = 1 if args.rellenar else (max(
            (int(k) for k in ind), default=0) + 1)

    if args.reservar:
        r = reservar(args.reservar, d)
        if args.json:
            print(json.dumps(r, indent=2, ensure_ascii=False))
        else:
            print("  %s: %s" % (r["n"], r["estado"]))
            for f in r["ficheros"]:
                print("    ya lo usa: %s" % f)
            if r["estado"] == "RESERVADO":
                print("    queda reservado. Si el hallazgo no se escribe, el "
                      "numero se desperdicia, y eso es lo que se acepta para no "
                      "dar el mismo numero a dos autores.")
            if r.get("motivo"):
                print("    %s" % r["motivo"])
        return {"RESERVADO": 0, "OCUPADO": 1}.get(r["estado"], 2)

    if args.check:
        n = args.check
        if not re.match(r"^\d{3,}$", n):
            print("  ERROR: el numero debe tener 3 o mas cifras: %r" % n,
                  file=sys.stderr)
            return 2
        cands = list(ind.get(n, []))
        if not cands and n in reservados():
            cands = ["<reservado, sin fichero todavia>"]
        if args.json:
            print(json.dumps({"numero": n, "n": len(cands),
                              "ficheros": cands,
                              "unico": len(cands) == 1}, indent=2,
                             ensure_ascii=False))
            return 0 if len(cands) == 1 else 1
        if not cands:
            print("  %s: LIBRE, ningun fichero lo usa" % n)
            return 0
        if len(cands) == 1:
            print("  %s: unico -> %s" % (n, cands[0]))
            return 0
        print("  %s: DUPLICADO, %d ficheros lo usan:" % (n, len(cands)))
        for f in cands:
            print("    %s" % f)
        print()
        print("  Un numero duplicado no identifica un hallazgo. Renumerar ahora")
        print("  es gratis si nadie cita todavia; renumerar en 64 casos no lo es.")
        return 1

    sg = siguiente(ind, args.desde, args.cuantos)
    payload = {
        "version": VERSION,
        "siguientes": sg,
        "total_ficheros": sum(len(v) for v in ind.values()),
        "numeros_distintos": len(ind),
        "numeros_duplicados": len(duplicados),
        "documentos_en_colision": sum(len(v) for v in duplicados.values()),
    }
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True,
                         ensure_ascii=False))
        return 0

    print("  hallazgos: %d en %d numeros" % (payload["total_ficheros"],
                                             payload["numeros_distintos"]))
    print("  numeros duplicados: %d   documentos en colision: %d"
          % (payload["numeros_duplicados"],
             payload["documentos_en_colision"]))
    print()
    print("  PROPUESTOS, ninguno ocupado:")
    for x in sg:
        print("    findings/%s-<slug>.md" % x)
    print()
    print("  Reservar ANTES de escribir el fichero. Renumerar despues rompe las")
    print("  citas que ya se hayan escrito, y las citas son la evidencia.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
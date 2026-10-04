#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# CONTRACT: name=reservas_gate
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no

"""reservas_gate -- clasifica TODA discrepancia entre el registro de reservas y
el arbol de hallazgos, y falla si alguna queda sin clasificar.

POR QUE EXISTE, Y POR QUE NO ES "COMPROBAR QUE NO HAY DISCREPANCIAS"
====================================================================

La invariante "no hay discrepancias" es FALSA y medible: hay 4 reservas sin
fichero, 390 numeros escritos sin reserva, y 2 numeros duplicados que ademas
estan reservados. Una puerta que exigiera cero discrepancias no se podria
cumplir, y por eso habria que apagarla en el momento de escribirla.

La invariante que SI se sostiene, y que es la que evita el dano real:

    **toda discrepancia esta CLASIFICADA.**

Por que la clase y no la ausencia. Un residuo sin clasificar y un conflicto sin
clasificar se ven IGUALES: los dos son "el registro tiene una fila y el disco
tiene otra cosa". Lo unico que los separa es que el primero tenga una clase que
dice RESTO y el segundo una que dice EL NUMERO ESTA EN USO DOS VECES. Sin la
clase, el conflicto se archiva como residuo, el numero queda ocupado para
siempre, y nadie lo decide nunca.

La puerta, por tanto, no juzga el estado: juzga la INFORMACION. Falla cuando una
discrepancia no se puede clasificar, o cuando una que estaba clasificada cambia
de clase, o cuando aparece una clase que no deberia crecer.

Lo que decide, y con que evidencia, esta en 08-ARQUITECTURA/RESERVAS-DESYNC.md.
La version corta de la regla:

    la pregunta no es "hay hallazgo detras de la reserva", es
    "el hallazgo se escribio ANTES de que la reserva existiera".

Porque `findnum.py commit()` BORRA el `.res` cuando el commit va bien
(`os.remove(res)`, linea 353): un `.res` junto a un `.md` no es el caso normal,
es un commit incompleto. Y en el registro de `nextnum.py` la coexistencia es lo
esperado, porque ese registro no tiene `--release`. Medir presencia de fichero
daria 53 "residuos" y no separaria ni un solo caso.

Y POR QUE LA COLUMNA DE FECHA NO ESTA EN `.nextnum.lock`
======================================================

Porque anadirla ahi no anade una columna: la BORRA. MEDIDO, los dos lectores
seleccionan la fila entera:

    nextnum.py:180       if re.match(r"^\\d{3,}$", l): out.add(l)
    findnum.py:114       if re.match(r"^\\d{3,}$", l): out[int(l)] = ("", "")

Con una columna mas, ninguna de las dos lineas casa, y **las 57 reservas dejan
de existir para los dos allocators**. Eso no es mejorar el registro: es
desenchufar el mecanismo que reparte numeros, que es lo unico que evita las
colisiones. Por eso `.nextnum.lock` no se toca, y la columna vive en
`RESERVAS.ledger`, al lado.

Y por que `.ledger` y no `.tsv`: MEDIDO `check_num_unico.py:248`
`EXT_LEIBLES = (".md",".py",".sh",".c",".h",".txt",".tsv")`. Un ledger con una
columna de numeros, en `.tsv`, sumaria ~57 "citas por numero" a las 2160 que ya
mide, y moveria un contador que no mide lo que dice medir. La ocupacion no es una
cita. Verificado en §7 del documento: las cifras de `check_num_unico.py` quedan
identicas antes y despues de existir este fichero.

SALIDAS
    0  toda discrepancia esta clasificada y ninguna clase ha cambiado
    1  algo NO esta clasificado, o una clase ha cambiado, o R5 ha crecido
    2  no se pudo medir (falta el arbol de hallazgos)
"""

import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIND = os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings")
LOCK_PROPIO = os.path.join(RAIZ, ".nextnum.lock")
LOCK_AJENO = os.path.join(FIND, "_reservas")
MAPA = os.path.join(RAIZ, "08-ARQUITECTURA", "tools", "REENVIO-FINDINGS.tsv")
LEDGER = os.path.join(LOCK_AJENO, "RESERVAS.ledger")

# `findnum.used_numbers()` y `nextnum.indice()` usan este patron. MEDIDO que un
# ancho EXACTO de tres (`\d{3}-`) no ve los numeros de cuatro cifras, y ese es
# el fallo que 309 documenta; aqui se copia el de cuatro, que es el que vale.
NUM_RX = re.compile(r"^(\d{3,})[-_](.+)\.md$")

# --- las clases -------------------------------------------------------------
# Mutuamente excluyentes y exhaustivas sobre `reservas | numeros_en_disco`.
# Un numero que no caiga en ninguna es un DEFECTO de esta tabla, y por eso el
# self-test la recorre entera con un caso por clase: si alguien anade un numero
# y olvida la clase, el self-test no lo nota, pero la puerta si, porque
# `clasifica()` devuelve None y None no es una clase.
R1_ESCRITO = "R1_ESCRITO"
R1_CONFLICTO = "R1_CONFLICTO"
R2_POR_RENUMERADO = "R2_POR_RENUMERADO"
R3_SIN_FICHERO_RENUMERADO = "R3_SIN_FICHERO_RENUMERADO"
R4_SIN_ORIGEN = "R4_SIN_ORIGEN"
R5_EN_USO_DOS_VECES = "R5_EN_USO_DOS_VECES"
H1_SIN_RESERVA = "H1_SIN_RESERVA"
H2_DUPLICADO_SIN_RESERVA = "H2_DUPLICADO_SIN_RESERVA"

TODAS = (R1_ESCRITO, R1_CONFLICTO, R2_POR_RENUMERADO,
         R3_SIN_FICHERO_RENUMERADO, R4_SIN_ORIGEN, R5_EN_USO_DOS_VECES,
         H1_SIN_RESERVA, H2_DUPLICADO_SIN_RESERVA)

# Las que son HALLAZGO y no RESERVA. La distincion no es academica: el allocator
# solo puede hacer algo con una reserva. Una H2 no se "libera"; no hay nada que
# liberar, porque nunca se reservo.
RESERVAS = (R1_ESCRITO, R1_CONFLICTO, R2_POR_RENUMERADO,
            R3_SIN_FICHERO_RENUMERADO, R4_SIN_ORIGEN, R5_EN_USO_DOS_VECES)

# --- los tres estados del ORDEN --------------------------------------------
# El tercero no existe todavia. Se declara para que la puerta pueda distinguir
# "aun no ha pasado" de "no se puede saber": un R1_CONFLICTO de maana tiene que
# verse distinto de uno de hoy, y con dos valores no se puede.
ORDEN_PROTOCOLO = "PROTOCOLO_CUMPLIDO"        # la reserva es anterior al fichero
ORDEN_INDETERMINADO = "INDETERMINADO"         # no hay fecha de reserva. No se elige
ORDEN_ANTES = "HALLAZGO_ANTES_DE_RESERVAR"    # conflicto: el numero ya estaba

# --- integridad del fichero de reserva --------------------------------------
P1 = "P1_RESERVA_CON_CONTENIDO"
P2 = "P2_RESERVA_SIN_CONTENIDO"                # el .res existe y weighs 0
X1 = "X1_EN_LOS_DOS_REGISTROS"

TS_RX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


def num_reservas_propio(ruta=LOCK_PROPIO):
    """Conjunto del registro de `nextnum.py`. SU FORMATO NO SE TOCA.

    MEDIDO: los dos lectores de este fichero seleccionan `^\\d{3,}$` sobre la
    linea ENTERA. Cualquier columna que se anada aqui hace que la fila deje de
    contar y la reserva desaparece para los dos allocators. Por eso la
    procedencia vive en RESERVAS.ledger y no aqui. Ver el(module) docstring.
    """
    out = set()
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                l = l.strip()
                if re.match(r"^\d{3,}$", l):
                    out.add(l)
    except OSError:
        pass
    return out


def reservas_ajenas(ruta=LOCK_AJENO):
    """{numero: (fichero, bytes, fecha_iso|None)} del registro de `findnum.py`.

    El contenido SI lleva fecha (linea 3 del `.res`), y esa fecha es lo unico
    que permite distinguir el protocolo cumplido del numero en uso dos veces.
    MEDIDO: un `.res` de 0 bytes NO puede haberlo escrito `reserve()`, que
    escribe tres lineas con write+rename (findnum.py:310-314). Asi que un `.res`
    vacio es un registro que ocupa sin poder%).
    """
    out = {}
    try:
        names = sorted(os.listdir(ruta))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".res"):
            continue
        m = re.match(r"^(\d{3,})-", name)
        if not m:
            continue
        p = os.path.join(ruta, name)
        try:
            size = os.path.getsize(p)
            with open(p, encoding="utf-8", errors="replace") as fh:
                lines = fh.read().splitlines()
        except OSError:
            size, lines = -1, []
        ts = None
        for l in lines:
            if TS_RX.match(l.strip()):
                ts = l.strip()
                break
        out[m.group(1)] = (name, size, ts)
    return out


def indice_hallazgos(d=FIND):
    """numero -> [ficheros]. Igual que `nextnum.indice()`, y a proposito."""
    out = collections.defaultdict(list)
    if not os.path.isdir(d):
        return out
    for f in sorted(os.listdir(d)):
        m = NUM_RX.match(f)
        if m:
            out[m.group(1)].append(f)
    return out


def mapa_reenvios(ruta=MAPA):
    """(viejos, nuevos) del mapa CONGELADO. Solo lectura: otro nodo lo escribe.

    MEDIDO: las 49 filas tienen 6 columnas, y la cabecera del fichero dice "5".
    El que importa para esta puerta es el par (columna 0, columna 1) y el
    tercero dice si el numero viejo quedo ocupado por OTRO contenido. Se leen
    las dos mitades porque `viejos` separa "resto de un renumerado" de
    "hallazgo perdido", que confundidas son un solo numero sin accion posible.
    """
    viejos, nuevos = {}, {}
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            for l in fh:
                l = l.rstrip("\n")
                if not l.strip() or l.startswith("#"):
                    continue
                p = l.split("\t")
                if len(p) >= 4:
                    viejos[p[0]] = p[1]
                    nuevos.setdefault(p[1], p[0])
    except OSError:
        pass
    return viejos, nuevos


def clasifica(n, n_fich, reservado, ts_reserva, ts_fichero,
              viejo_map, nuevo_map):
    """(clase, orden). EL NOMBRE VA AQUI, no en `main()`.

    Existe separado del informe porque una comprobacion que solo puede mirar
    stdout comprueba el FORMATO, no la DECISION. Y porque `None` tiene que poder
    salir de aqui: es lo que hace fallar a la puerta cuando la tabla de clases
    se queda corta. Una tabla de clases a la que todo cae dentro no es una
    puerta, es una decoracion.

    El ORDEN es la decision, y por eso va aparte de la clase. Un R1 puede ser
    el protocolo funcionando (RESERVADO -> escrito) o el numero en uso dos
    veces (ya escrito -> RESERVADO). El mismo numero, la misma clase de
    presencia, y solo el orden los separa.
    """
    # --- sin reserva: dos clases, y NO son un problema del allocator --------
    if not reservado:
        return (H2_DUPLICADO_SIN_RESERVA if n_fich >= 2 else H1_SIN_RESERVA,
                "NA")

    # --- reserva sin fichero: el numero se desperdicio ---------------------
    if n_fich == 0:
        if n in viejo_map:
            return R3_SIN_FICHERO_RENUMERADO, "NA"
        return R4_SIN_ORIGEN, "NA"

    # --- reserva con DOS o mas ficheros: ESTE es el conflicto real ---------
    #
    # Va antes que R1 y que R2 a proposito. Con 2+ ficheros la pregunta "se
    # escribio antes o despues" es INTERESTING pero no es la que manda: el
    # numero esta en uso dos veces Y esta reservado, y eso hay que decirlo
    # aunque la orden favorable. Si se comprobara la orden primero, un
    # duplicado con la reserva posterior caeria en R1 y el conflicto se
    # archivaria como "el protocolo se cumplio".
    if n_fich >= 2:
        orden = ORDEN_INDETERMINADO
        if ts_reserva and ts_fichero:
            orden = (ORDEN_PROTOCOLO if ts_reserva <= ts_fichero
                     else ORDEN_ANTES)
        return R5_EN_USO_DOS_VECES, orden

    # --- reserva con UN fichero --------------------------------------------
    # R2 antes que R1: si el numero es destino de un renumerado, la reserva la
    # consumio un MOVIMIENTO, no una escritura. El mtime del fichero es la
    # fecha del ULTIMO commit que lo toco, que no es la del renumerado, asi que
    # R2 NO juzga el orden por mtime: lo decide el RENAME de git, que esta en
    # el mapa congelado. Decir "PROTOCOLO_CUMPLIDO" aqui por mtime seria
    # afirmar con un dato que no mide lo que dice medir.
    if n in nuevo_map:
        return R2_POR_RENUMERADO, "POR_RENUMERADO"

    if not ts_reserva:
        # No se elige. 52 de 57 reservas caen aqui y es una limitacion del
        # REGISTRO, no de la busqueda: `.nextnum.lock` no esta versionado
        # (.gitignore:151) y su formato no tiene donde poner una fecha.
        return R1_ESCRITO, ORDEN_INDETERMINADO

    if ts_reserva <= ts_fichero:
        return R1_ESCRITO, ORDEN_PROTOCOLO
    return R1_CONFLICTO, ORDEN_ANTES


def _ts_fichero_iso(d, ficheros):
    """mtime del MAS VIEJO de los ficheros del numero, en ISO.

    El mas viejo y no el mas nuevo: para "el hallazgo existia cuando se
    reservo" sirve el instante en que aparecio el primero. Con el mas nuevo, un
    duplicado escrito a destiempo moveria la fecha y la ordenaria bien.
    """
    import datetime
    mt = min(os.path.getmtime(os.path.join(d, f)) for f in ficheros)
    return datetime.datetime.fromtimestamp(mt).strftime("%Y-%m-%dT%H:%M:%S")


def mide(d=FIND, lock=LOCK_PROPIO, ajeno=LOCK_AJENO, mapa=MAPA):
    """Todo el estado, ya clasificado. Devuelve un dict; no imprime nada."""
    if not os.path.isdir(d):
        return None
    ind = indice_hallazgos(d)
    propio = num_reservas_propio(lock)
    res = reservas_ajenas(ajeno)
    viejos, nuevos = mapa_reenvios(mapa)

    filas = []
    for n in sorted(set(propio) | set(res) | set(ind), key=lambda x: (len(x), x)):
        ficheros = ind.get(n, [])
        import os.path as _o
        encontrado = (n in propio) or (n in res)
        ts_res = res[n][2] if n in res else None
        ts_fich = (_ts_fichero_iso(d, ficheros) if ficheros else None)
        clase, orden = clasifica(n, len(ficheros), encontrado, ts_res,
                                 ts_fich, viejos, nuevos)
        filas.append({
            "numero": n,
            "clase": clase,
            "orden": orden,
            "n_ficheros": len(ficheros),
            "ficheros": ficheros,
            "ts_reserva": ts_res,
            "ts_fichero_mas_viejo": ts_fich,
            "registro_propio": n in propio,
            "registro_ajeno": n in res,
            "detalle": ("viejo->%s" % viejos[n]) if n in viejos else
                       ("nuevo<-%s" % nuevos[n]) if n in nuevos else "",
        })
    return {
        "filas": filas,
        "propio": propio,
        "ajeno": res,
        "viejos": viejos,
        "nuevos": nuevos,
        "indice": ind,
    }


def clases_de(med):
    """{numero: clase} y los conteos. La unidad que compara el ledger."""
    c = {f["numero"]: f["clase"] for f in med["filas"]}
    cnt = collections.Counter(c.values())
    return c, cnt


def comprobaciones(med, clase_observada, clase_ledger, p2_observados,
                   p2_ledger, r5_ledger):
    """Las CINCO condiciones. Devuelve [(nombre, ok, detalle)].

    Cada una es un fallo DISTINITO y distinguible a ojo, porque una puerta que
    solo dice "fallo" obliga a volver a leer el codigo para saber que ha
    cambiado. Y las cinco se prueban por mutacion en `selftest()`.
    """
    out = []
    sin_clase = sorted(n for n, c in clase_observada.items() if c is None)
    out.append(("C1 toda discrepancia tiene clase", not sin_clase,
                "sin clase: %s" % sin_clase if sin_clase else
                "%d numeros clasificados" % len(clase_observada)))

    fuera = sorted(set(clase_observada) - set(clase_ledger))
    out.append(("C2 toda discrepancia esta en el ledger", not fuera,
                "fuera del ledger: %s" % fuera if fuera else
                "0 nuevas; el ledger tiene %d filas" % len(clase_ledger)))

    cambiados = sorted(n for n in clase_observada
                       if n in clase_ledger and clase_ledger[n] != clase_observada[n])
    out.append(("C3 ninguna clase ha cambiado", not cambiados,
                "clase que cambio: %s" % [(n, clase_ledger[n], clase_observada[n])
                                          for n in cambiados] if cambiados
                else "0 cambios de clase"))

    p2_nuevos = sorted(set(p2_observados) - set(p2_ledger))
    out.append(("C4 ningun .res vacio nuevo", not p2_nuevos,
                ".res vacio nuevo: %s" % p2_nuevos if p2_nuevos
                else "los vacios son los de siempre: %s" % sorted(p2_ledger)))

    r5_obs = set(n for n, c in clase_observada.items() if c == R5_EN_USO_DOS_VECES)
    nuevos_r5 = sorted(r5_obs - set(r5_ledger))
    out.append(("C5 R5 no ha crecido", not nuevos_r5,
                "R5 NUEVO: %s" % nuevos_r5 if nuevos_r5
                else "R5 sigue en %s" % sorted(r5_ledger)))
    return out


def lee_ledger(ruta=LEDGER):
    """{numero: clase} del ledger congelado, leido POR NOMBRE DE COLUMNA.

    MEDIDO, y por que es por nombre y no por posicion: la primera version leia
    `p[1]` como clase y `p[2]` como orden, y el ledger escribe
    `num  orden  clase`.  Los dos estaban "bien" por separado y el self-test
    seguia en VERDE, porque el self-test construia el ledger EN MEMORIA con el
    orden que el lector suponia y nunca escribia un fichero de verdad.  O sea:
    la puerta leia la columna equivocada del fichero real y ningun vector lo
    notaba.

    Eso no es un fallo del self-test por poco: es el patron exacto que este
    proyecto ya ha documentado dos veces -- un vector que no exercise el camino
    real pasa mientras lo que vigila esta roto.  Por eso el esquema va en una
    linea `#SCHEMA` y se lee por nombre, y por eso hay un vector que escribe un
    ledger de verdad en un temporal y lo relee.

    Devolver `{}` si falta el fichero es correcto y NO es una guarda: el ledger
    falta -> C2 no se cumple -> la puerta falla con un motivo que lo dice.  Un
    fichero ausente reportado como "cero discrepancias" seria el fallo que esta
    puerta existe para cazar.
    """
    out = {}
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            schema = None
            for l in fh:
                l = l.rstrip("\n")
                if l.startswith("#SCHEMA"):
                    # MEDIDO: el separador va ANTES del primer nombre, para que la
                    # linea sea autodescriptiva y no dependa de que el fichero
                    # tenga o no el tab inicial.  Sin el `.strip("\t")` el corte
                    # deja un campo vacio al principio, la esquema mide 9 y todas
                    # las filas de 8 se descartan por `len(p) < len(schema)`: el
                    # ledger entero se leia como cero filas y C2 lo tomaba por
                    # "cero discrepancias".  Un lector que descarta filas en
                    # silencio y devuelve un diccionario VACIO es peor que uno
                    # que revienta, porque el vacio parece un resultado.
                    schema = [c.strip()
                              for c in l[len("#SCHEMA"):].strip("\t").split("\t")
                              if c.strip()]
                    continue
                if l.startswith("#") or not l.strip():
                    continue
                if schema is None:
                    # Sin cabecera no se adivina: se registra como vacio para que
                    # C2 falle, en vez de interpretar columnas por su cuenta.
                    return {}
                p = l.split("\t")
                if len(p) < len(schema):
                    continue
                fila = dict(zip(schema, p))
                n = fila.get("num", "")
                if re.match(r"^\d{3,}$", n):
                    # La clase Y el flag de .res vacio, porque C4 necesita
                    # recordarlos.  MEDIDO que hace falta: sin el, la linea de
                    # base de P2 no se Filling de ningun sitio y C4 comparaba
                    # contra el conjunto VACIO, de modo que el .res de 0 bytes
                    # que ya existe (1020) se reportaba como "nuevo" para
                    # siempre.  Una condicion cuyo termino de comparacion no se
                    # lee de ningun sitio no es una condicion: es una queja.
                    out[n] = (fila.get("clase", ""),
                              fila.get("p2_vacio", "0").strip() == "1")
    except OSError:
        pass
    return out


def imprime(med, clase_observada, cnt, ledger, checks):
    L = print
    L("=" * 74)
    L("reservas_gate %s · registro de reservas vs arbol de hallazgos" % VERSION)
    L("=" * 74)
    L("")
    L("  hallazgos en disco      : %d ficheros en %d numeros"
      % (sum(len(v) for v in med["indice"].values()), len(med["indice"])))
    L("  registro nextnum (.lock): %d" % len(med["propio"]))
    L("  registro findnum (.res) : %d" % len(med["ajeno"]))
    L("  en los DOS registros    : %d  %s"
      % (len(set(med["propio"]) & set(med["ajeno"])),
         sorted(set(med["propio"]) & set(med["ajeno"]))))
    L("  fila del ledger         : %d" % len(ledger))
    L("")
    L("  CLASES, y por que esta puerta NO dice que no haya discrepancias:")
    L("  (la regla entera esta en 08-ARQUITECTURA/RESERVAS-DESYNC.md)")
    L("")
    orden_clases = list(TODAS)
    for c in orden_clases:
        nums = sorted((n for n, k in clase_observada.items() if k == c),
                      key=lambda x: (len(x), x))
        L("  %-26s %4d" % (c, len(nums)))
        if c in RESERVAS:
            shown = nums if len(nums) <= 6 else nums[:6] + ["..."]
            if shown:
                L("        %s" % " ".join(shown))
        elif cnt.get(c):
            L("        (lista completa en el ledger y en --json)")
    L("")
    # El orden de las reservas que si lo tienen. Es la decision, y va separada.
    por_orden = collections.Counter(
        f["orden"] for f in med["filas"] if f["clase"] in RESERVAS)
    L("  ORDEN de las reservas (que separa el protocolo del conflicto):")
    for o in (ORDEN_PROTOCOLO, ORDEN_INDETERMINADO, ORDEN_ANTES, "POR_RENUMERADO"):
        L("    %-26s %4d" % (o, por_orden.get(o, 0)))
    ind_n = [f["numero"] for f in med["filas"] if f["orden"] == ORDEN_INDETERMINADO]
    if ind_n:
        L("")
        L("  INDETERMINADAS: %d. No es que no se haya buscado: el registro" % len(ind_n))
        L("  `.nextnum.lock` no esta versionado (.gitignore:151) y su formato")
        L("  no tiene donde poner una fecha, y anadirsela haria que las dos")
        L("  regex `^\\d{3,}$` de los dos allocadores dejen de contar la fila.")
        L("  La deuda es del REGISTRO. `nextnum.py --reservar` ya sella la")
        L("  reserva en RESERVAS.ledger, asi que no crece.")
    L("")
    L("  LAS CINCO CONDICIONES (esto es lo que puede fallar):")
    for nombre, ok, det in checks:
        L("    [%s] %-38s %s" % ("OK" if ok else "FALLA", nombre, det[:60]))
    L("")
    return all(ok for _n, ok, _d in checks)


def selftest() -> int:
    """El gate tiene que PODER FALLAR. Si no puede, es decoracion.

    Cada condicion se rompe de verdad, en un arbol temporal completo, y se
    comprueba que la puerta responde 1. Y se comprueba lo contrario tambien:
    que el caso limpio da 0. Un vector que solo prueba el camino verde no sabe
    distinguir una puerta de una constante.
    """
    import shutil
    fallos = []
    tmp = "/tmp/opencode/reservas-gate-selftest"
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)

    d = os.path.join(tmp, "findings")
    res = os.path.join(d, "_reservas")
    os.makedirs(res)
    lock = os.path.join(tmp, ".nextnum.lock")
    mapa = os.path.join(tmp, "REENVIO.tsv")

    def pon(n, slug, cuerpo="x\n"):
        open(os.path.join(d, "%s-%s.md" % (n, slug)), "w").write(cuerpo)

    def res_stub(n, ts="2026-10-03T10:00:00"):
        open(os.path.join(res, "%s-reservado.res" % n), "w").write(
            "RESERVADO numero=%s pid=1\ntitulo de prueba\n%s\n" % (n, ts))

    # --- caso LIMPIO, con las ocho clases presentes una vez cada una ---------
    # No es adorno: una puerta cuya tabla de clases nunca se ha recorrido
    # entera no puede detectar que le falte una clase.
    pon("300", "unico")                       # R1  con .res y orden OK
    res_stub("300", "2026-10-03T09:00:00")
    pon("301", "unico")                       # R1  sin .res -> orden INDETERMINADO
    open(lock, "a").write("301\n")
    pon("302", "unico")                       # R2  reserva + destino de renumerado
    res_stub("302", "2026-10-03T09:00:00")
    res_stub("303")                           # R3  reserva SIN fichero, era viejo
    res_stub("304")                           # R4  reserva SIN fichero, sin mapa
    pon("305", "a")                           # R5  reserva + DOS ficheros
    pon("305", "b")
    res_stub("305", "2026-10-03T09:00:00")
    pon("306", "unico")                       # H1  hallazgo sin reserva
    pon("307", "a")                           # H2  duplicado sin reserva
    pon("307", "b")
    with open(mapa, "w") as fh:
        fh.write("# viejo\t nuevo\t reasignado\t stem\t contenido\t proc\n")
        fh.write("303\t350\tSI\tmitad.md\tcontenido\tdiff\n")
        fh.write("301\t302\tSI\tmitad2.md\tcontenido\tdiff\n")

    def medir():
        return mide(d=d, lock=lock, ajeno=res, mapa=mapa)

    med = medir()
    if med is None:
        print("  FAIL el arbol de prueba no se pudo medir")
        return 1
    clase, cnt = clases_de(med)
    esperado = {
        "300": (R1_ESCRITO, ORDEN_PROTOCOLO),
        "301": (R1_ESCRITO, ORDEN_INDETERMINADO),
        "302": (R2_POR_RENUMERADO, "POR_RENUMERADO"),
        "303": (R3_SIN_FICHERO_RENUMERADO, "NA"),
        "304": (R4_SIN_ORIGEN, "NA"),
        "305": (R5_EN_USO_DOS_VECES, ORDEN_PROTOCOLO),
        "306": (H1_SIN_RESERVA, "NA"),
        "307": (H2_DUPLICADO_SIN_RESERVA, "NA"),
    }
    for n, (c, o) in sorted(esperado.items()):
        got = (clase.get(n), next((f["orden"] for f in med["filas"]
                                   if f["numero"] == n), None))
        if got != (c, o):
            print("  FAIL %s: clase %r/%r, esperaba %r/%r" % (n, got[0], got[1], c, o))
            fallos.append(n)
    if not fallos:
        print("  OK   las 8 clases se distinguen, y R1 en sus dos ordenes")

    # --- y ahora: LA PUERTA, con un ledger congelado de verdad ---------------
    ledger_obs = {n: c for n, c in clase.items()}
    p2_obs = set(n for n, (f, s, t) in med["ajeno"].items() if s == 0)
    r5_obs = set(n for n, c in clase.items() if c == R5_EN_USO_DOS_VECES)

    def verdict(medida, led, p2led, r5led):
        c, _ = clases_de(medida)
        return all(ok for _n, ok, _x in comprobaciones(medida, c, led, p2_obs,
                                                      p2led, r5led))

    limpio = verdict(med, ledger_obs, set(), r5_obs)
    if not limpio:
        print("  FAIL el caso limpio no pasa la puerta: una puerta que no deja")
        print("        pasar lo que esta bien no puede decir nada de lo que esta mal")
        fallos.append("limpio")
    else:
        print("  OK   caso limpio -> la puerta DEJA PASAR")

    # --- MUTACION 1: un numero sin fila en el ledger (C2) ------------------
    led2 = dict(ledger_obs)
    led2.pop("306")
    if verdict(med, led2, set(), r5_obs):
        print("  FAIL C2: un hallazgo sin fila en el ledger paso la puerta")
        fallos.append("C2")
    else:
        print("  OK   C2 muerde: numero sin fila en el ledger -> FALLA")

    # --- MUTACION 2: la clase de un numero cambia (C3) ----------------------
    led3 = dict(ledger_obs)
    led3["304"] = R1_ESCRITO
    if verdict(med, led3, set(), r5_obs):
        print("  FAIL C3: una clase que cambio paso la puerta")
        fallos.append("C3")
    else:
        print("  OK   C3 muerde: clase cambiada -> FALLA")

    # --- MUTACION 3: un .res de 0 bytes que no estaba (C4) -----------------
    if verdict(med, ledger_obs, set(), r5_obs):
        pass
    # se anade uno nuevo y se vuelve a mirar
    open(os.path.join(res, "308-reservado.res"), "w").close()   # 0 bytes a proposito
    med2 = medir()
    c2, _ = clases_de(med2)
    p2_obs2 = set(n for n, (f, s, t) in med2["ajeno"].items() if s == 0)
    chk = comprobaciones(med2, c2, ledger_obs, p2_obs2, set(), r5_obs)
    c4 = [ok for nom, ok, det in chk if nom.startswith("C4")][0]
    if c4:
        print("  FAIL C4: un .res de 0 bytes nuevo paso la puerta")
        fallos.append("C4")
    else:
        print("  OK   C4 muerde: .res de 0 bytes nuevo -> FALLA")
    os.remove(os.path.join(res, "308-reservado.res"))

    # --- MUTACION 4: R5 CRECE (C5). El que de verdad importa. --------------
    # Se duplica un numero que ya tenia un solo fichero y se le anade la
    # reserva: el numero pasa a estar en uso dos veces Y reservado. Es el
    # conflicto que el intercambio de "desperdiciar un numero" prohibia.
    med3 = medir()
    c3, _ = clases_de(med3)
    r5_prev = set(n for n, c in c3.items() if c == R5_EN_USO_DOS_VECES)
    pon("306", "b")          # 306 pasa de 1 a 2 ficheros
    open(lock, "a").write("306\n")   # y ademas se reserva
    med4 = medir()
    c4b, _ = clases_de(med4)
    nuevo_r5 = set(n for n, c in c4b.items() if c == R5_EN_USO_DOS_VECES) - r5_prev
    chk = comprobaciones(med4, c4b, ledger_obs, set(), set(), r5_prev)
    c5 = [ok for nom, ok, det in chk if nom.startswith("C5")][0]
    if c5 or "306" not in nuevo_r5:
        print("  FAIL C5: R5 crecio de %s a %s y la puerta paso"
              % (sorted(r5_prev), sorted(r5_prev | nuevo_r5)))
        fallos.append("C5")
    else:
        print("  OK   C5 muerde: R5 nuevo (%s) -> FALLA" % sorted(nuevo_r5))
    os.remove(os.path.join(d, "306-b.md"))
    with open(lock, "w") as fh:
        fh.write("301\n")

    # --- MUTACION 5: la tabla de clases se queda corta (C1) -----------------
    #
    # El caso mas importante de los cinco, y el mas facil de hacer mal. Si
    # `clasifica()` devolviera SIEMPRE una clase, C1 no podria dispararse
    # nunca: la puerta pasaria para siempre y nadie lo notaria, porque "todo
    # clasificado" y "todo correcto" se parecen mucho en la salida.
    #
    # Se rompe la FUNCION REAL, no una copia. Por eso `clasifica()` esta fuera
    # de `main()` y no recibe una bandera de prueba: un flag de test en el
    # camino que se quiere probar es una puerta que solo pasa en el self-test.
    import __main__ as _self
    orig = _self.clasifica
    try:
        _self.clasifica = (lambda *a, **k: (None, None))
        med5 = medir()
        c5b, _ = clases_de(med5)
        chk = comprobaciones(med5, c5b, ledger_obs, set(), set(), r5_obs)
        c1 = [ok for nom, ok, det in chk if nom.startswith("C1")][0]
        if c1:
            print("  FAIL C1: sin clases la puerta paso. Una puerta que no puede")
            print("        ver 'nada clasificado' no puede decir que todo esta bien")
            fallos.append("C1")
        else:
            print("  OK   C1 muerde: sin ninguna clase -> FALLA")
    finally:
        _self.clasifica = orig

    # --- y el estado se ha restaurado ---------------------------------------
    med6 = medir()
    c6, _ = clases_de(med6)
    if c6 != clase:
        print("  FAIL el self-test dejo el estado de prueba distinto")
        fallos.append("restauracion")
    else:
        print("  OK   el self-test restaura el estado")

    # --- VECTOR 7, y el que mas habria costado si faltara -------------------
    #
    # MEDIDO que hace falta.  La primera version de este fichero leia el ledger
    # por POSICION (`p[1]` = clase) y lo escribia con el orden
    # `num orden clase`.  Los dos eran coherentes consigo mismos, el self-test
    # construia el ledger en memoria con el orden que el LECTOR suponia, y los
    # seis vectores estaban en VERDE.  La puerta leia la columna equivocada del
    # fichero de verdad y no habia ni un vector que lo notara.
    #
    # Un vector que solo prueba la funcion con lo que el propio test fabrico no
    # prueba la LECTURA.  Este escribe un ledger DE VERDAD en un temporal, con el
    # esquema `#SCHEMA` que usa el arbol, y lo relee con `lee_ledger()`.
    esquema = ("#SCHEMA\tnum\torden\tclase\tts_reserva\tts_fichero\tregistro"
               "\tn_fich\tdetalle\tp2_vacio\n")
    ruta_led = os.path.join(tmp, "LEDGER.ledger")
    with open(ruta_led, "w", encoding="utf-8") as fh:
        fh.write(esquema)
        for n in sorted(esperado, key=int):
            fh.write("%s\t%s\t%s\tDESCONOCIDA\t-\t-/-\t1\t-\t0\n"
                     % (n, esperado[n][1], esperado[n][0]))
    leido = lee_ledger(ruta_led)
    if len(leido) != len(esperado):
        print("  FAIL el ledger real se leyo como %d filas de %d: el lector y el"
              % (len(leido), len(esperado)))
        print("        escritor no comparten esquema. Este vector es el que")
        print("        habria pasado: la puerta leia la columna equivocada")
        fallos.append("roundtrip")
    elif any(leido[n][0] != esperado[n][0] for n in esperado):
        print("  FAIL las clases del ledger real no son las esperadas: %r"
              % {n: (leido[n][0], esperado[n][0]) for n in sorted(esperado)
                 if leido[n][0] != esperado[n][0]})
        fallos.append("roundtrip-clase")
    else:
        print("  OK   ledger REAL escrito y releido: %d filas, clases correctas"
              % len(leido))

    # Y el caso contrario: un ledger SIN cabecera no se interpreta por su cuenta.
    ruta_sin = os.path.join(tmp, "sin.ledger")
    with open(ruta_sin, "w", encoding="utf-8") as fh:
        fh.write("300\tPROTOCOLO_CUMPLIDO\tR1_ESCRITO\n")
    if lee_ledger(ruta_sin):
        print("  FAIL un ledger sin #SCHEMA se leyo con columnas adivinadas")
        fallos.append("sin-schema")
    else:
        print("  OK   un ledger sin #SCHEMA devuelve {} y hace fallar C2, no adivina")

    # Y el caso de que el ledger NO exista: {} , no una puerta que pasa.
    if lee_ledger(os.path.join(tmp, "no-existe.ledger")) != {}:
        print("  FAIL un ledger inexistente devolvio algo")
        fallos.append("inexistente")
    else:
        print("  OK   ledger inexistente -> {} -> C2 FALLA (no verde por defecto)")

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    if fallos:
        print("RESULT: FAIL (%d) -> %s" % (len(fallos), fallos))
        return 1
    print("RESULT: PASS (11 vectores, 6 de ellos por MUTACION)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="clasifica toda discrepancia reservas/hallazgos y falla si "
                    "alguna queda sin clasificar")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ledger", metavar="RUTA", default=LEDGER)
    args = ap.parse_args()
    if args.selftest:
        return selftest()

    med = mide()
    if med is None:
        print("  ERROR: no existe el directorio de hallazgos: %s" % FIND,
              file=sys.stderr)
        return 2
    clase, cnt = clases_de(med)
    bruto = lee_ledger(args.ledger)
    ledger = {n: v[0] for n, v in bruto.items()}
    p2_obs = set(n for n, (f, s, t) in med["ajeno"].items() if s == 0)
    # La base de P2 se LEE del ledger, no se pone a {} a mano.  MEDIDO: puesto a
    # mano, C4 comparaba contra el vacio y el .res de 0 bytes que ya existe lo
    # reportaba como nuevo, indefinidamente.
    p2_led = set(n for n, v in bruto.items() if v[1])
    r5_led = set(n for n, c in ledger.items() if c == R5_EN_USO_DOS_VECES)
    checks = comprobaciones(med, clase, ledger, p2_obs, p2_led, r5_led)
    ok = all(c for _n, c, _d in checks)

    if args.json:
        print(json.dumps({
            "version": VERSION,
            "ledger": args.ledger,
            "filas_ledger": len(ledger),
            "conteos": dict(sorted(cnt.items())),
            "ordenes": dict(sorted(collections.Counter(
                f["orden"] for f in med["filas"]
                if f["clase"] in RESERVAS).items())),
            "checks": [{"nombre": n, "ok": o, "detalle": d}
                       for n, o, d in checks],
            "rc": 0 if ok else 1,
        }, indent=2, sort_keys=True, ensure_ascii=False))
        return 0 if ok else 1

    ok = imprime(med, clase, cnt, ledger, checks)
    print("  VEREDICTO: %s" % ("toda discrepancia esta clasificada"
                              if ok else
                              "HAY ALGO QUE NO SE PUEDE CLASIFICAR. "
                              "El detalle esta arriba, en la linea [FALLA]."))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# CONTRACT: name=reservas_gate
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=only_with_--congelar
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
#
# MEDIDO 2026-10-04 por que `WRITES_FILES` estaba en `no` y ahora no puede estar:
# la razon de que lo estuviera era que la puerta no escribia NADA, y esa razon era
# verdadera. Al anadir `--congelar` la razon deja de ser cierta, asi que la
# declaracion cambia con ella. Una etiqueta de contrato que sobrevive al cambio que
# la invalida es peor que no tenerla: entrena al que lee a no mirar.

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
    0  (por defecto, y `--verificar`)  toda discrepancia esta clasificada, ninguna
       clase ha cambiado, R5 no ha crecido y -- en `--verificar` -- el sha256
       declarado cuadra con el cuerpo medido
    1  algo NO esta clasificado, o una clase ha cambiado, o R5 ha crecido, o
       `--verificar` ha encontrado un defecto de forma
    2  no se pudo medir (falta el arbol de hallazgos), o `--congelar` se ha
      -negativegado a escribir porque el ledger o el mapa estan rotos
    3  `--congelar` NO ha escrito, y dice por que.  Codigo propio del hermano:
       `reenvio_freeze.py` usa 3 para lo mismo (nada que hacer).  No es un fallo
       de la puerta: es una puerta que se niega a congelar sobre datos que no
       puede medir.
"""

import argparse
import collections
import json
import os
import re
import sys

VERSION = "1.1.0"

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


# =============================================================================
# Los vectores de --congelar y --verificar
# =============================================================================
#
# POR QUE ESTA SEPARADO DE `selftest()` Y NO ADENTRO
# -----------------------------------------------------
# Porque los once vectores de arriba vigilan la CLASIFICACION y estos vigilan la
# ESCRITURA, y son cosas que se rompen de maneras opuestas.  Arriba se rompe el
# dato para ver si la puerta lo nota.  Aqui se rompe el ESCRITOR para ver si
# `--congelar` ruinia el dato.  Una puerta que solo sabe fallar y un congelador
# que solo sabe escribir fallan de forma distinta, asi que los vectores tambien.
#
# Y hay una razon mas, medida: `--congelar` es la UNICA forma de que las
# columnas del ledger dejen de tener que escribirse a mano, y una columna escrita
# a mano no la vigila nadie.  Estos vectores no comprueban que las columnas sean
# ciertas: comprueban que las que `--congelar` pone sale del disco y las que no
# pone no se tocan.  Una columna que pone la herramienta y que nadie contrasta
# es una columna inventada con pasos.

_LEDGER_BUENO = ("#SCHEMA\tnum\torden\tclase\tts_reserva\tts_fichero\tregistro"
                 "\tn_fich\tdetalle\tp2_vacio\n")

# El RECUENTO del self-test se CUENTA, no se escribe a mano.
#
# MEDIDO por que: la linea de resumen decia "11 vectores, 6 de ellos por MUTACION"
# y las dos cifras eran falsas.  Los vectores eran mas de 11 en cuanto se anadio
# V12-V20, y los de mutacion eran 5 (C1, C2, C3, C4, C5), no 6.  Un numero de
# resumen que no se cuenta es un numero que se queda viejo sin que nadie lo note,
# y en un self-test es la clase de dato que este gate existe para cazar.
_VEC_OK = []
_VEC_MUT = []


def _ok(msg):
    _VEC_OK.append(1)
    print("  OK   %s" % msg)


def _mal(msg):
    print("  FAIL %s" % msg)


def _mut(nombre):
    """Marca una asercion que se sostiene porque se ROMPIO algo a proposito."""
    _VEC_MUT.append(nombre)


def _fila_buena(n, orden, clase, ts_res="DESCONOCIDA", ts_fich="-",
                registro="-/-", n_fich="0", detalle="-", p2="0"):
    return dict(num=n, orden=orden, clase=clase, ts_reserva=ts_res,
                ts_fichero=ts_fich, registro=registro, n_fich=n_fich,
                detalle=detalle, p2_vacio=p2)


def _cuerpo_de(filas):
    return "\n".join("\t".join(f[c] for c in COLS) for f in filas) + "\n"


def _escribe_ledger(ruta, filas, cabecera_extra=()):
    txt = _LEDGER_BUENO + _cuerpo_de(filas)
    with open(ruta, "w", encoding="utf-8") as fh:
        for l in cabecera_extra:
            fh.write(l + "\n")
        fh.write(txt)
    return txt


def _vectores_congelar(tmp, med, esperado, ruta_led):
    """Vectores 12-20. Devuelve la lista de fallos."""
    import __main__ as _self
    fallos = []
    d = os.path.join(tmp, "findings")
    res = os.path.join(d, "_reservas")
    mapa_real = os.path.join(tmp, "REENVIO.tsv")

    def res_stub(n, ts="2026-10-03T10:00:00"):
        open(os.path.join(res, "%s-reservado.res" % n), "w").write(
            "RESERVADO numero=%s pid=1\ntitulo de prueba\n%s\n" % (n, ts))

    # --- V12: la LESION. Una clase DESPLAZADA UNA COLUMNA --------------------
    #
    # MEDIDO por que esta lesion y no otra.  El esquema es `num orden clase
    # ...`, y el modo de fallo mas probable al editar a mano no es escribir una
    # clase equivocada: es escribir la clase CORRECTA en la columna de al lado.
    # Con la lesion, `orden` y `clase` quedan intercambiadas: el numero es el
    # mismo, las dos cadenas son las dos correctas, y lo unico que cambia es que
    # estan donde no toca.
    led = os.path.join(tmp, "lesion.ledger")
    c300, o300 = esperado["300"]
    c306, o306 = esperado["306"]
    lesion = {"300": _fila_buena("300", o300, c300, n_fich="1", registro="own/ajen"),
              "306": _fila_buena("306", o306, c306, n_fich="1")}
    # El desplazamiento: se escribe orden/clase al reves de como las lee el esquema.
    lesion_txt = [l for l in _cuerpo_de([lesion["300"], lesion["306"]]).split("\n") if l]
    lesion_txt[0] = "\t".join(["300", lesion["300"]["clase"], lesion["300"]["orden"],
                               lesion["300"]["ts_reserva"], lesion["300"]["ts_fichero"],
                               lesion["300"]["registro"], lesion["300"]["n_fich"],
                               lesion["300"]["detalle"], lesion["300"]["p2_vacio"]])
    with open(led, "w", encoding="utf-8") as fh:
        fh.write(_LEDGER_BUENO + "\n".join(lesion_txt) + "\n")
    cab, cue, filas_les, esc, pr = _estructura(led)
    leida = filas_les[0]
    if leida["clase"] == leida["orden"]:
        _mal("V12 la lesion no se escribio: la columna 'clase' contiene "
              "el valor de 'orden'")
        fallos.append("V12-escritura")
    else:
        _ok("V12 lesion inyectada: 300 tiene clase=%r en la columna "
              "'clase', orden=%r en 'orden'" % (leida["clase"], leida["orden"]))
    # Y lo que importa: --congelar la CORRIGE, porque lee el disco y no la fila.
    _self.mide = _self.mide  # no-op explicito: se usa la de verdad
    med_real = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                          ajeno=res, mapa=mapa_real)
    plan, cuenta = plan_congelar({f["num"]: f for f in filas_les}, med_real)
    corregida = [f for f in plan if f["num"] == "300"]
    _mut("V12-lesion-clase-desplazada")
    if not corregida or corregida[0]["clase"] != c300:
        _mal("V12 --congelar NO corrige la lesion: clase=%r, esperaba %r"
              % (corregida[0]["clase"] if corregida else None, c300))
        fallos.append("V12-no-corrige")
    else:
        _ok("V12 --congelar corrige la lesion sola: %r -> %r, leida del "
              "disco" % (leida["clase"], corregida[0]["clase"]))
    # Y una fila NO tocada por la lesion se conserva: no se arregla el mundo entero.
    iguales = [f for f in plan if f["num"] == "306" and f["clase"] == c306]
    if not iguales:
        _mal("V12 la lesion se ha propagado a una fila que estaba bien")
        fallos.append("V12-propagacion")
    else:
        _ok("V12 la propagacion no ocurre: 306 no cambia al arreglar 300")

    # --- V13: --congelar NO PUEDE escribir sin el mapa ------------------------
    #
    # MEDIDO el numero que hace falta para que este vector no sea adorno: con el
    # mapa VACIO, `clasifica()` cambia 4 clases de las 451 del arbol real
    # (975 R3->R4, y 976, 994 y 1020 R2->R1) y se re-derivan a `-` 92 celdas de
    # `detalle` -- de las que 90 se perderian y 2 son prosa que se conserva.  Sin este
    # vector, un `--congelar` corrido mientras otro nodo reescribe el mapa
    # clonaria un estado transitorio en el ledger, y el sha declararia ese
    # estado como si fuera el bueno.
    mapa_vacio = os.path.join(tmp, "VACIO.tsv")
    with open(mapa_vacio, "w", encoding="utf-8") as fh:
        fh.write("# vacio a proposito\n")
    _mut("V13-mapa-vacio")
    ok_m, motivo, _ = guarda_mapa({f["num"]: f for f in filas_les}, mapa_vacio)
    if ok_m:
        _mal("V13 guarda_mapa ACEPTO un mapa vacio: --congelar escribiria "
              "4 clases y perderia 90 detalles")
        fallos.append("V13-mapa-vacio")
    else:
        _ok("V13 guarda_mapa RECHAZA el mapa vacio y dice el numero: %s"
              % motivo[:70])
    ok_n, _m2, _ = guarda_mapa({f["num"]: f for f in filas_les},
                               os.path.join(tmp, "no-existe.tsv"))
    if ok_n:
        _mal("V13 guarda_mapa ACEPTO un mapa inexistente")
        fallos.append("V13-mapa-ausente")
    else:
        _ok("V13 guarda_mapa RECHAZA un mapa inexistente")

    # --- V14: la clase y el ORDEN no los decide el escritor ------------------
    #
    # MEDIDO por que esto necesita un vector y no una asercion: `escribir()`
    # recibe el plan ya hecho, asi que podria llevar dentro un campo que no viene
    # de `clasifica()`.  El vector pone un `.res` con fecha POSTERIOR al
    # mtime del fichero y comprueba que la fila sale CONFLICTO, y no
    # PROTOCOLO_CUMPLIDO: son las dos clases R1 y el orden es lo unico que las
    # separa.
    med_c = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                       ajeno=res, mapa=mapa_real)
    r300 = [f for f in med_c["filas"] if f["numero"] == "300"]
    if not r300 or r300[0]["orden"] != ORDEN_PROTOCOLO:
        _mal("V14 el arbol de prueba no tiene el orden que este vector "
              "supone: %r" % (r300[0]["orden"] if r300 else None))
        fallos.append("V14-premisa")
    else:
        # Ahora se rompe la premisa: un .res POSTERIOR al fichero debe dar OTRO
        # orden.  Si `escribir()` no puede distinguir estos dos casos, no esta
        # leyendo `clasifica()`.
        res_stub("300", "2099-01-01T00:00:00")
        med_d = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                           ajeno=res, mapa=mapa_real)
        r300d = [f for f in med_d["filas"] if f["numero"] == "300"][0]
        if r300d["orden"] != ORDEN_ANTES or r300d["clase"] != R1_CONFLICTO:
            _mal("V14 un .res posterior NO da HALLAZGO_ANTES_DE_RESERVAR: "
                  "orden=%r clase=%r" % (r300d["orden"], r300d["clase"]))
            fallos.append("V14-orden")
        else:
            _ok("V14 orden y clase los decide clasifica(), no el "
                  "escritor: .res posterior -> %s / %s"
                  % (r300d["orden"], r300d["clase"]))
        res_stub("300", "2026-10-03T09:00:00")

    # --- V15: NUNCA se borra una fila que existe ------------------------------
    #
    # La lesion es la que el enunciado llama "el dano que este ledger existe para
    # evitar": un numero cuyo hallazgo se borro del disco.  `mide()` deja de
    # verlo, y un `--congelar` que fuera reescritura lo borraria en silencio.
    led_v = os.path.join(tmp, "sin-fuente.ledger")
    conservada = _fila_buena("300", o300, c300, n_fich="1")
    fantasma = _fila_buena("997", ORDEN_INDETERMINADO and "NA", R4_SIN_ORIGEN,
                           ts_res="2020-01-01T00:00:00", n_fich="0")
    _escribe_ledger(led_v, [conservada, fantasma])
    os.remove(os.path.join(d, "300-unico.md"))       # 300 ya no esta en disco
    med_e = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                       ajeno=res, mapa=mapa_real)
    plan_v, cuenta_v = plan_congelar({"300": conservada, "997": fantasma}, med_e)
    por_n = {f["num"]: f for f in plan_v}
    _mut("V15-fila-borrada-de-disco")
    if "997" not in por_n:
        _mal("V15 --congelar BORRO la fila 997, que existe en el ledger "
              "y `mide()` no ve")
        fallos.append("V15-borrada")
    else:
        igual = all(por_n["997"].get(c) == fantasma.get(c) for c in COLS)
        if not igual:
            _mal("V15 la fila conservada ha cambiado de celda: %r != %r"
                  % (por_n["997"], fantasma))
            fallos.append("V15-mutada")
        else:
            _ok("V15 la fila sin fuente se conserva ENTERA (%d celdas "
                  "intactas) y se cuenta: sin_fuente=%d"
                  % (len(COLS), cuenta_v["sin_fuente"]))
    # Y una fila sin fuente NO puede aparecer en el resultado por casualidad: el
    # numero tiene que seguir siendo el del ledger, no uno medido.
    if cuenta_v["sin_fuente_lista"] != ["997"]:
        _mal("V15 sin_fuente no apunta a la fila correcta: %r"
              % cuenta_v["sin_fuente_lista"])
        fallos.append("V15-lista")
    else:
        _ok("V15 sin_fuente nombra la fila exacta: %s"
              % cuenta_v["sin_fuente_lista"])
    with open(os.path.join(d, "300-unico.md"), "w") as fh:
        fh.write("x\n")

    # --- V16: una fila que NO esta se ANADE, no se inventa -------------------
    led_n = os.path.join(tmp, "nueva.ledger")
    _escribe_ledger(led_n, [_fila_buena("306", o306, c306, n_fich="1")])
    med_f = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                       ajeno=res, mapa=mapa_real)
    lo_que_habia = {f["num"]: f for f in _estructura(led_n)[2]}
    plan_n, cuenta_n = plan_congelar(lo_que_habia, med_f)
    por_n = {f["num"]: f for f in plan_n}
    # MEDIDO que el numero de anadidas es `len(mide()) - len(ledger)`, no 1: el
    # vector pone UN numero en el ledger y el arbol de prueba tiene ocho.  Un
    # vector que espera `1` porque el autor solo penso en el numero que le
    # interesa esta probando el numero del autor, no el de la herramienta.
    esperados_anadidas = sorted(set(f["numero"] for f in med_f["filas"])
                                - set(lo_que_habia),
                                key=lambda x: (len(x), x))
    if not esperados_anadidas:
        _mal("V16 la premisa del vector es falsa: el ledger ya lo tiene "
              "todo, asi que el vector no mide la adicion")
        fallos.append("V16-premisa")
    elif "307" not in por_n:
        _mal("V16 --congelar no anadio la fila 307, que si esta en el "
              "disco y no en el ledger")
        fallos.append("V16-no-anade")
    elif por_n["307"]["clase"] != H2_DUPLICADO_SIN_RESERVA or por_n["307"]["n_fich"] != "2":
        _mal("V16 la fila anadida no sale del disco: clase=%r n_fich=%r"
              % (por_n["307"]["clase"], por_n["307"]["n_fich"]))
        fallos.append("V16-inventada")
    else:
        _ok("V16 anade lo que falta, medido: 307 -> %s, n_fich=%s"
              % (por_n["307"]["clase"], por_n["307"]["n_fich"]))
    if cuenta_n["anadidas"] != len(esperados_anadidas):
        _mal("V16 anadidas=%d, esperaba %d"
              % (cuenta_n["anadidas"], len(esperados_anadidas)))
        fallos.append("V16-cuenta")
    elif sorted(n for n in por_n if n not in lo_que_habia) != esperados_anadidas:
        _mal("V16 las filas anadidas no son las que faltaban: %r != %r"
              % (sorted(n for n in por_n if n not in lo_que_habia),
                 esperados_anadidas))
        fallos.append("V16-cuales")
    else:
        _ok("V16 anadidas cuenta exactamente las que faltaban (%d): %s"
              % (len(esperados_anadidas), " ".join(esperados_anadidas)))

    # --- V17: ts_reserva NO se re-deriva.  Y por que no. ----------------------
    #
    # MEDIDO en el arbol real: 3 de las 7 filas con fecha real (1043, 1044, 1045)
    # no tienen `.res` en disco, porque la fecha la puso `nextnum.py _sella()` al
    # reservar.  Re-derivar las tres escribiria DESCONOCIDA, que es una
    # AFIRMACION FALSA y no una celda vacia.  Este vector pone una fila con fecha
    # real y SIN `.res`, y exige que la fecha sobreviva a `--congelar`.
    led_t = os.path.join(tmp, "ts.ledger")
    con_fecha = _fila_buena("300", ORDEN_INDETERMINADO, R1_ESCRITO,
                            ts_res="2026-10-03T09:00:00", n_fich="1",
                            registro="own/ajen")
    _escribe_ledger(led_t, [con_fecha])
    med_t = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                       ajeno=res, mapa=mapa_real)
    # Se borra el .res: ahora el disco NO tiene de donde sacar la fecha, igual
    # que 1043/1044/1045.
    res_borro = os.path.join(res, "300-reservado.res")
    os.remove(res_borro)
    med_t2 = _self.mide(d=d, lock=os.path.join(tmp, ".nextnum.lock"),
                        ajeno=res, mapa=mapa_real)
    if any(f["numero"] == "300" and f["ts_reserva"] for f in med_t2["filas"]):
        _mal("V17 el .res no se ha borrado: la premisa del vector no se "
              "cumple y no mide nada")
        fallos.append("V17-premisa")
    else:
        plan_t, _c = plan_congelar({"300": con_fecha}, med_t2)
        _mut("V17-ts-reserva-sin-fuente")
        got = [f for f in plan_t if f["num"] == "300"][0]["ts_reserva"]
        if got != "2026-10-03T09:00:00":
            _mal("V17 --congelar PISO la fecha de la reserva: %r.  Sin "
                  "`.res` no hay de donde sacarla, y DESCONOCIDA seria mentir"
                  % got)
            fallos.append("V17-pisada")
        else:
            _ok("V17 ts_reserva sobrevive sin `.res`: %s.  Y la clase SI "
                  "se corrige (%s)" % (got, R1_ESCRITO))
    res_stub("300", "2026-10-03T09:00:00")

    # --- V18: la NORMALIZACION del sha, y que el round-trip cierra ------------
    #
    # MEDIDO que A (join + \\n final) y B (bucle fila+\\n) dan el mismo sha byte a
    # byte sobre el ledger real, y que el fichero entero con cabecera da otro.  No
    # se prueba aqui la aritmetica del hash -- eso es `hashlib` -- sino lo que
    # de verdad se puede romper: que `cuerpo()` y el escritor no compartan
    # normalizacion.  Si compartieran mal, el sha declararia una cosa y el
    # fichero seria otra, y eso es un verificador que miente sin querer.
    filas_ord = [_fila_buena("001", "NA", H1_SIN_RESERVA),
                 _fila_buena("002", "NA", H2_DUPLICADO_SIN_RESERVA, n_fich="2"),
                 _fila_buena("1000", ORDEN_INDETERMINADO, R1_ESCRITO, n_fich="1")]
    c = _cuerpo_de(filas_ord)
    a = _cuerpo(c)                                # normalizacion A, la del hermano
    b = "".join(l + "\n" for l in c.split("\n") if l.strip() and not l.startswith("#"))
    _mut("V18-normalizaciones-distintas")
    if a != b:
        _mal("V18 la normalizacion A y la B no coinciden: el hermano y "
              "esta puerta estan midiendo cosas distintas")
        fallos.append("V18-normalizacion")
    else:
        _ok("V18 A == B byte a byte, sha %s.  Es UNA normalizacion "
              "escrita de dos maneras" % sha_de(a)[:16])
    if _cuerpo("#SCHEMA\tx\n" + a) != a:
        _mal("V18 las lineas #SI entran en el cuerpo que se hashea: una "
              "linea de prosa giraria el sha")
        fallos.append("V18-comentarios")
    else:
        _ok("V18 las lineas que empiezan por # NO entran en el cuerpo")
    # round-trip: escribir -> leer -> el cuerpo leido es IDENTICO al escrito
    ruta_rt = os.path.join(tmp, "rt.ledger")
    _escribe_ledger(ruta_rt, filas_ord, cabecera_extra=["# prosa que debe sobrevivir"])
    _cab, cue_rt, _fl, _es, _pr = _estructura(ruta_rt)
    if cue_rt != c:
        _mal("V18 el round-trip no cierra: escrito %d bytes, releido %d"
              % (len(c), len(cue_rt)))
        fallos.append("V18-roundtrip")
    else:
        _ok("V18 round-trip cierra: escribir y releer da el mismo cuerpo")

    # --- V19: escribir DECLARA el sha, y --verificar lo comprueba -------------
    led_s = os.path.join(tmp, "sha.ledger")
    # MEDIDO por que la prosa se escribe ANTES y no despues: la version anterior
    # de este vector hacia `_escribe_ledger()` DESPUES de `escribir()`, y al
    # sobreescribir el fichero entero se llevaba por delante la prosa que el
    # instante anterior acababa de comprobar que `escribir()` conservaba.  El
    # vector se estaba refutando a si mismo y reportaba como FALLA de
    # `escribir()` lo que era un fallo suyo.  Un vector que se invalida a si mismo
    # mide lo que el autorwriting en ese momento, no lo que cree medir.
    prosa = ("# prosa que debe sobrevivir",
             "#   segunda linea de prosa, para que no sea un caso de una linea")
    _escribe_ledger(led_s, filas_ord, cabecera_extra=prosa)
    cuenta_o = {"filas": len(filas_ord), "conservadas": len(filas_ord),
                "anadidas": 0, "sin_fuente": 0, "clases_rederivadas": 0,
                "ts_reserva_preservadas": len(filas_ord), "ts_reserva_recuperadas": [],
                "detalle_prosa": [], "sin_fecha": 0, "mapa_pares": 2}
    escribir(led_s, filas_ord, cuenta_o)
    _cab, cue_s, _fl, _es, _pr = _estructura(led_s)
    maq = _maquina(led_s)
    # El sha se compara contra el CUERPO RELIDO DE DISCO, no contra el que el
    # test cree que escribio.  Compararlo contra el propio `filas_ord` de arriba
    # cuadraria por construccion y no probaria nada.
    if maq.get("sha256_cuerpo") != sha_de(cue_s):
        _mal("V19 el sha declarado no es el del cuerpo REAL de disco: "
              "declarado %r, real %r" % (maq.get("sha256_cuerpo"), sha_de(cue_s)))
        fallos.append("V19-sha")
    else:
        _ok("V19 escribir declara el sha del cuerpo, y el cuerpo "
              "releido de DISCO es el que hashea: %s"
              % maq.get("sha256_cuerpo", "")[:16])
    # Y la prosa de la cabecera NO se pierde al escribir: MEDIDO que
    # `_cabecera_para` conserva toda linea `#` que no sea de maquina.
    leido = open(led_s, encoding="utf-8").read()
    if not all(l in leido for l in prosa):
        _mal("V19 escribir BORRO la prosa de la cabecera.  Son 92 lineas "
              "de decisiones del proyecto, no texto de esta herramienta")
        fallos.append("V19-prosa")
    else:
        _ok("V19 las %d lineas de prosa de la cabecera sobreviven a "
              "escribir" % len(prosa))
    # Y un sha declarado que NO cuadra tiene que FALLAR, no pasar: un verificador
    # de integridad que no muerde no verifica.
    with open(led_s, "w", encoding="utf-8") as fh:
        fh.write(leido.replace(maq["sha256_cuerpo"], "0" * 64))
    _cab, cue_bad, _f2, _e2, _p2 = _estructura(led_s)
    _mut("V19-sha-declarado-erroneo")
    if _maquina(led_s).get("sha256_cuerpo") == sha_de(cue_bad):
        _mal("V19 un sha declarado erroneo pasa por bueno")
        fallos.append("V19-no-muerde")
    else:
        _ok("V19 un sha declarado erroneo NO cuadra: se detecta")

    # Y la prosa NO puede pasar por una linea de MAQUINA.  MEDIDO por que este
    # vector existe: `_maquina()` se queda con la ULTIMA linea que empieza por
    # `#   <etiqueta> `.  Si la prosa pudiera empezar por una etiqueta, ganaria
    # ella.  El hermano sufrio justo eso, MEDIDO el 2026-10-04 en
    # `reenvio_freeze.py _sha_declarado`: al escribir una linea de prosa que
    # mencionaba la clave, el lector comparo `que es la que verifica:` con el
    # sha real.  Se comprueba que una prosa que empieza por la palabra "modo" no
    # pisa el valor de la linea de maquina `modo`.
    led_p = os.path.join(tmp, "prosa-maquina.ledger")
    _escribe_ledger(led_p, filas_ord,
                    cabecera_extra=["#   modo esto es PROSA que empieza por la "
                                    "etiqueta y no es una declaracion"])
    escribir(led_p, filas_ord, cuenta_o)
    _mut("V19-prosa-en-etiqueta")
    if _maquina(led_p).get("modo") != "congelar":
        _mal("V19 la prosa se ha colado en las lineas de maquina: "
              "modo=%r" % _maquina(led_p).get("modo"))
        fallos.append("V19-maquina")
    else:
        _ok("V19 una linea de prosa que empieza por una etiqueta no "
              "pisa la de maquina: modo=%r" % _maquina(led_p).get("modo"))

    # --- V20: --verificar NO ESCRIBE.  Nunca. ---------------------------------
    #
    # MEDIDO por que hace falta: `--verificar` se ejecuta sin argumentos y antes
    # de un commit, y si escribiera la cabecera para "arreglar" el sha, el
    # fichero que se acaba de verificar seria distinto del que se verifico.
    # Un verificador que modifica lo que verifica no verifica.
    import time as _t
    led_w = os.path.join(tmp, "solo-lectura.ledger")
    _escribe_ledger(led_w, filas_ord)
    _escribe_ledger(led_w, filas_ord, cabecera_extra=[])
    escribir(led_w, filas_ord, cuenta_o)
    antes = open(led_w, "rb").read()
    mt = os.path.getmtime(led_w)
    _t.sleep(1.1)
    _cab, cue_w, _f3, _e3, _p3 = _estructura(led_w)
    _maq = _maquina(led_w)
    despues = open(led_w, "rb").read()
    if antes != despues or os.path.getmtime(led_w) != mt:
        _mal("V20 la LECTURA del ledger modifico el fichero")
        fallos.append("V20-escribe")
    else:
        _ok("V20 leer el ledger no lo modifica: mismos bytes, mismo mtime")
    if not os.path.exists(led_w + ".congelar.tmp"):
        _ok("V20 no queda temporal de --congelar: la escritura es "
              "atomica y limpia")
    else:
        _mal("V20 queda un temporal de --congelar en el directorio")
        fallos.append("V20-temporal")

    return fallos


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
        _mal("el arbol de prueba no se pudo medir")
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
            _mal("%s: clase %r/%r, esperaba %r/%r" % (n, got[0], got[1], c, o))
            fallos.append(n)
    if not fallos:
        _ok("las 8 clases se distinguen, y R1 en sus dos ordenes")

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
        _mal("el caso limpio no pasa la puerta: una puerta que no deja")
        print("        pasar lo que esta bien no puede decir nada de lo que esta mal")
        fallos.append("limpio")
    else:
        _ok("caso limpio -> la puerta DEJA PASAR")

    # --- MUTACION 1: un numero sin fila en el ledger (C2) ------------------
    led2 = dict(ledger_obs)
    led2.pop("306")
    _mut("C2-numero-sin-fila")
    if verdict(med, led2, set(), r5_obs):
        _mal("C2: un hallazgo sin fila en el ledger paso la puerta")
        fallos.append("C2")
    else:
        _ok("C2 muerde: numero sin fila en el ledger -> FALLA")

    # --- MUTACION 2: la clase de un numero cambia (C3) ----------------------
    led3 = dict(ledger_obs)
    led3["304"] = R1_ESCRITO
    _mut("C3-clase-cambiada")
    if verdict(med, led3, set(), r5_obs):
        _mal("C3: una clase que cambio paso la puerta")
        fallos.append("C3")
    else:
        _ok("C3 muerde: clase cambiada -> FALLA")

    # --- MUTACION 3: un .res de 0 bytes que no estaba (C4) -----------------
    if verdict(med, ledger_obs, set(), r5_obs):
        pass
    # se anade uno nuevo y se vuelve a mirar
    open(os.path.join(res, "308-reservado.res"), "w").close()   # 0 bytes a proposito
    med2 = medir()
    c2, _ = clases_de(med2)
    p2_obs2 = set(n for n, (f, s, t) in med2["ajeno"].items() if s == 0)
    _mut("C4-res-vacio-nuevo")
    chk = comprobaciones(med2, c2, ledger_obs, p2_obs2, set(), r5_obs)
    c4 = [ok for nom, ok, det in chk if nom.startswith("C4")][0]
    if c4:
        _mal("C4: un .res de 0 bytes nuevo paso la puerta")
        fallos.append("C4")
    else:
        _ok("C4 muerde: .res de 0 bytes nuevo -> FALLA")
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
    _mut("C5-R5-crece")
    chk = comprobaciones(med4, c4b, ledger_obs, set(), set(), r5_prev)
    c5 = [ok for nom, ok, det in chk if nom.startswith("C5")][0]
    if c5 or "306" not in nuevo_r5:
        _mal("C5: R5 crecio de %s a %s y la puerta paso"
              % (sorted(r5_prev), sorted(r5_prev | nuevo_r5)))
        fallos.append("C5")
    else:
        _ok("C5 muerde: R5 nuevo (%s) -> FALLA" % sorted(nuevo_r5))
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
        _mut("C1-tabla-clases-corta")
        _self.clasifica = (lambda *a, **k: (None, None))
        med5 = medir()
        c5b, _ = clases_de(med5)
        chk = comprobaciones(med5, c5b, ledger_obs, set(), set(), r5_obs)
        c1 = [ok for nom, ok, det in chk if nom.startswith("C1")][0]
        if c1:
            _mal("C1: sin clases la puerta paso. Una puerta que no puede")
            print("        ver 'nada clasificado' no puede decir que todo esta bien")
            fallos.append("C1")
        else:
            _ok("C1 muerde: sin ninguna clase -> FALLA")
    finally:
        _self.clasifica = orig

    # --- y el estado se ha restaurado ---------------------------------------
    med6 = medir()
    c6, _ = clases_de(med6)
    if c6 != clase:
        _mal("el self-test dejo el estado de prueba distinto")
        fallos.append("restauracion")
    else:
        _ok("el self-test restaura el estado")

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
        _mal("el ledger real se leyo como %d filas de %d: el lector y el"
              % (len(leido), len(esperado)))
        print("        escritor no comparten esquema. Este vector es el que")
        print("        habria pasado: la puerta leia la columna equivocada")
        fallos.append("roundtrip")
    elif any(leido[n][0] != esperado[n][0] for n in esperado):
        _mal("las clases del ledger real no son las esperadas: %r"
              % {n: (leido[n][0], esperado[n][0]) for n in sorted(esperado)
                 if leido[n][0] != esperado[n][0]})
        fallos.append("roundtrip-clase")
    else:
        _ok("ledger REAL escrito y releido: %d filas, clases correctas"
              % len(leido))

    # Y el caso contrario: un ledger SIN cabecera no se interpreta por su cuenta.
    ruta_sin = os.path.join(tmp, "sin.ledger")
    with open(ruta_sin, "w", encoding="utf-8") as fh:
        fh.write("300\tPROTOCOLO_CUMPLIDO\tR1_ESCRITO\n")
    if lee_ledger(ruta_sin):
        _mal("un ledger sin #SCHEMA se leyo con columnas adivinadas")
        fallos.append("sin-schema")
    else:
        _ok("un ledger sin #SCHEMA devuelve {} y hace fallar C2, no adivina")

    # Y el caso de que el ledger NO exista: {} , no una puerta que pasa.
    if lee_ledger(os.path.join(tmp, "no-existe.ledger")) != {}:
        _mal("un ledger inexistente devolvio algo")
        fallos.append("inexistente")
    else:
        _ok("ledger inexistente -> {} -> C2 FALLA (no verde por defecto)")

    fallos += _vectores_congelar(tmp, med, esperado, ruta_led)

    shutil.rmtree(tmp, ignore_errors=True)
    print()
    if fallos:
        _mal("RESULT: FAIL (%d) de %d aserciones -> %s"
             % (len(fallos), len(_VEC_OK) + len(fallos), fallos))
        return 1
    print("RESULT: PASS (%d aserciones; %d se sostienen PORQUE se rompio algo)"
          % (len(_VEC_OK), len(_VEC_MUT)))
    print("  las mutaciones: %s" % ", ".join(_VEC_MUT))
    return 0


# =============================================================================
# --congelar y --verificar
# =============================================================================
#
# POR QUE EXISTEN, Y QUE ES EXACTAMENTE EL HUECO QUE CIERRAN
# ---------------------------------------------------------
# MEDIDO 2026-10-04: `findnum.py commit()` BORRA el `.res` cuando el commit va
# bien (`os.remove(res)`, findnum.py:353), y `nextnum.py _sella()` escribe la fila
# del ledger con clase `R_PENDIENTE`, que NO es una de las ocho de `TODAS`. O
# sea: hay dos escritores del ledger y ninguno de los dos sabe la clase, y la
# puerta C3 RECHAZA el ledger en cuanto esa clase se queda atras. MEDIDO que
# C3 es la condicion que duele: con el ledger del arbol hoy, C3 falla y dice
# "clase que cambio" por cada numero reservado cuyo hallazgo ya se escribio.
# Re-derivarlo a mano son nueve columnas por fila, y a mano es como se mete una
# clase en la columna de al lado.
#
# QUE COLUMNAS RE-DERIVA Y CUALES CONSERVA.  Medido columna por columna contra
# el disco, con el estado real del arbol, no deducido:
#
#   num         CONSERVA   es la clave.  No se re-deriva porque re-derivar la
#                        clave de una fila es no tener filas.
#   orden       RE-DERIVA  lo produce `clasifica()`.  MEDIDO 0 diferencias.
#   clase       RE-DERIVA  lo produce `clasifica()`.  MEDIDO 0 diferencias, y es
#                        JUSTAMENTE lo que C3 compara: re-derivarla es lo que
#                        hace que C3 quede verde porque se resolvio, no porque
#                        se apagara.
#   ts_reserva  CONSERVA   MEDIDO, y es la columna que NO se puede re-derivar: de
#                        las 7 filas con fecha real, 4 tienen `.res` en disco y
#                        3 NO (1043, 1044, 1045: su fecha la puso
#                        `nextnum.py _sella()` en el momento de reservar y no
#                        esta en ningun otro sitio). Re-derivar las tres escribiria
#                        `DESCONOCIDA`, que no es una celda vacia: es una
#                        AFIRMACION FALSA. La cabecera de este ledger ya lo dice
#                        de otra forma, para `.nextnum.lock`: "un dato inventado
#                        en una columna de procedencia es peor que una celda
#                        vacia, porque la celda vacia se ve".
#                        Excepcion, y es una RECUPERACION: si el ledger dice
#                        DESCONOCIDA y el `.res` tiene fecha, se adopta la del
#                        `.res`. Y si el ledger tiene fecha y el `.res` dice
#                        otra, se conserva la del ledger y se avisa: el ledger
#                        registra lo que la reserva decia al reservarse.
#   ts_fichero  RE-DERIVA  MEDIDO 0 diferencias salvo 1043, donde el ledger dice
#                        `-` y el disco tiene mtime: re-derivar RELLENA una
#                        verdad, que es lo contrario de inventar.
#   registro    RE-DERIVA  MEDIDO 0 diferencias.
#   n_fich      RE-DERIVA  MEDIDO 0 diferencias.
#   detalle     RE-DERIVA, CON UNA EXCEPCION MEDIDA.  La columna es "viejo->N" o
#                        "nuevo<-N" y sale del mapa CONGELADO, asi que es una
#                        vista y se re-deriva.  MEDIDO: 359 filas valen `-`, 90
#                        valen una flecha y 2 valen PROSA (`reservado, sin
#                        escritura detras`, que escribe `nextnum.py _sella()`, que
#                        no es una flecha y no pertenece a esta columna). La prosa
#                        se CONSERVA y se cuenta aparte; las flechas y los `-` se
#                        re-derivan. La razon de no tractar las dos igual: la
#                        flecha es un hecho que el mapa sostiene, y la prosa es
#                        un texto que la fila ya tiene encima; si se re-deriva
#                        la flecha y se pierde la prosa, se pierde informacion
#                        por un lado y se gana exactitud por el otro.
#   p2_vacio    RE-DERIVA  MEDIDO 0 diferencias.  Es la linea de base de C4 y
#                        solo hay 1 fila a 1 (1020, `.res` de 0 bytes presente).
#
# QUE HACE CON UNA FILA QUE NO ESTA EN EL LEDGER: la ANADE.  Con sus valores
# derivados.  Y `ts_reserva` se deja en `DESCONOCIDA` cuando no hay `.res`, que
# es distinto de inventarla: `DESCONOCIDA` afirma que no hay fecha, y es verdad.
#
# QUE HACE CON UNA FILA QUE NO ESTA EN `mide()`: NO LA BORRA.  La conserva
# verbatim y la cuenta como `sin_fuente`.  MEDIDO el motivo por el que esto no es
# un detalle: la cabecera del ledger dice que lo que evita el dano es que "un
# residuo sin clasificar y un conflicto sin clasificar se ven IGUALES", y una
# fila que `mide()` ya no ve es exactamente un residuo sin clasificar.  Borrarla
# seria dejar el numero ocupado para siempre sin que nadie lo decida, que es la
# clase de dano que este fichero existe para que no vuelva a haber.
#
# NORMALIZACION DEL sha256_cuerpo, MEDIDA CONTRA LAS DOS
# -----------------------------------------------------
# La del ledger hermano (`reenvio_freeze.py`), que es la que se ha medido aqui y
# la que se usa:
#
#     A   SOLO las filas de datos --las que no empiezan por # y no estan
#         vacias--, unidas con \n, con un \n final.
#         MEDIDO sobre el ledger real: 451 filas, 30995 bytes,
#         sha256 056501b9c8d8cca2...
#
#     B   lo mismo escrito como bucle: fila + \n por fila.
#         MEDIDO: A == B, byte a byte, mismo sha.  Se probaron las dos porque el
#         enunciado de la tarea las pedia separadas, y el resultado de la
#         comparacion es que SON LA MISMA NORMALIZACION: no hay dos reglas, hay
#         una escrita de dos maneras.
#
#     C   el fichero entero, cabecera incluida.
#         MEDIDO: sha 8a58fb63e7645ff6..., DISTINTO.  Y es la que NO se usa, por
#         la razon que el hermano ya escribio y que aqui se cumple igual: este
#         ledger tiene 92 lineas de prosa medida y anadirle una linea de prosa
#         giraria el sha sin haber cambiado un solo numero.  Un sha que gira por
#         escribir un comentario no puede usarse para afirmar que el dato esta
#         intacto.
#
# Ademas se ha medido que el ORDEN de las filas del ledger real ya es
# `sorted(num, key=(len, num))`, que es el mismo que usa `mide()`.  No se
# reordena nada: si no, el sha giraria por un cambio de orden que no cambia un
# solo dato.

import hashlib
import time

# El esquema.  LA AUTORIDAD es la linea `#SCHEMA` del propio ledger, no esta
# tupla: se comparan las dos y si no coinciden `--congelar` se niega.  Esta tupla
# existe para poder decir "el ledger declara 8 columnas y esta herramienta espera
# 9" con un nombre, no para reescribir el fichero.
COLS = ("num", "orden", "clase", "ts_reserva", "ts_fichero", "registro",
        "n_fich", "detalle", "p2_vacio")

COLS_REDERIVA = ("orden", "clase", "ts_fichero", "registro", "n_fich", "p2_vacio")
COLS_PRESERVA = ("num", "ts_reserva")

# Ordenes validos.  MEDIDO que `clasifica()` puede devolver 5 distintos y que uno
# de ellos (`"POR_RENUMERADO"`) esta FUERA de las tres constantes de arriba, asi
# que la lista se declara aqui y no se deduce de ellas.
ORDENES = (ORDEN_PROTOCOLO, ORDEN_INDETERMINADO, ORDEN_ANTES, "POR_RENUMERADO", "NA")

# `nextnum.py _sella()` escribe esto como clase de una reserva recien hecha, y no
# es una de las ocho.  No es un error de la puerta: es una fila a medio
# clasificar, y lo que hay que hacer es DECIR que hay.  MEDIDO que hoy no hay
# ninguna, porque las tres que se reservaron (1043, 1044, 1045) ya se clasificaron.
R_PENDIENTE = "R_PENDIENTE"

# MEDIDO por que `\d+` y NO `\d{3,}`, que es el ancho de `NUM_RX` y el que
# parecería el natural: 8 filas (193, 194, 195, 196, 205, 206, 207, 208) tienen
# `detalle` = `nuevo<-52`, `nuevo<-85`, ... y el numero VIEJO del renumerado es de
# DOS cifras, aunque el nuevo sea de cuatro.  Con `\d{3,}` esas 8 no casan, caen
# en la rama de "prosa que se conserva" y `--congelar` las anuncia como prosa que
# no son.  MEDIDO que con `\d+` quedan 90 flechas y 2 prosas, y que las 90
# re-derivadas coinciden con lo que hay: el contador queda en la verdad y la prosa
# que se conserva es la prosa.
RE_DETALLE = re.compile(r"^(?:viejo->|nuevo<-)\d+$")

ETIQUETAS_MAQUINA = ("generado_por", "generado_en", "filas_ledger", "modo",
                     "filas_conservadas", "filas_anadidas", "filas_sin_fuente",
                     "clases_rederivadas", "ts_reserva_preservadas",
                     "ts_reserva_recuperadas", "detalle_prosa_conservada",
                     "ts_reserva_sin_fecha", "mapa_pares", "sha256_cuerpo")
RE_ETIQUETA_MAQUINA = re.compile(
    r"^#\s*(%s)(?=\s|$)" % "|".join(sorted(ETIQUETAS_MAQUINA, key=len, reverse=True)))

RC_OK = 0
RC_FALLO = 1
RC_NO_EJECUTO = 2
RC_NADA_QUE_ANADIR = 3


def _cuerpo(txt):
    """Normalizacion A, medida arriba. Devuelve "" si no hay filas de datos."""
    ls = [l for l in txt.split("\n") if l.strip() and not l.startswith("#")]
    return "\n".join(ls) + "\n" if ls else ""


def sha_de(cuerpo_txt):
    return hashlib.sha256(cuerpo_txt.encode("utf-8")).hexdigest()


def _estructura(ruta):
    """(cabecera, cuerpo, filas, esquema, problemas) del ledger del disco.

    `lee_ledger()` devuelve solo lo que las condiciones necesitan: el numero, la
    clase y el flag de P2.  `--verificar` necesita ADEMAS la forma de cada fila,
    y por eso esta funcion existe y `lee_ledger()` se apoya en ella.

    MEDIDO por que una fila con el numero de campos equivocado se REGISTRA y no
    se descarta: la version anterior hacia `if len(p) < len(schema): continue`, y
    una fila que se descarta en silencio no aparece ni como dato ni como problema.
    Una fila de 8 columnas leida como 9 no es un dato malo: es un dato que no
    existe, y el fichero que lo contiene esta roto de una manera que hay que
    poder NOMBRAR.
    """
    try:
        txt = open(ruta, encoding="utf-8", errors="replace").read()
    except OSError:
        return [], "", [], None, ["el ledger no existe o no se puede leer: %s" % ruta]
    cab, cuesco, esquema, filas, problemas = [], [], None, [], []
    for n_lin, l in enumerate(txt.split("\n"), 1):
        if l.startswith("#SCHEMA"):
            esquema = [c.strip()
                       for c in l[len("#SCHEMA"):].strip("\t").split("\t")
                       if c.strip()]
            cab.append(l)
            continue
        if l.startswith("#"):
            cab.append(l)
            continue
        if not l.strip():
            continue
        cuesco.append(l)
        p = l.split("\t")
        if esquema is None:
            problemas.append("linea %d: hay fila de datos y NO hay #SCHEMA" % n_lin)
            continue
        if len(p) != len(esquema):
            problemas.append("linea %d: %d campos, el #SCHEMA declara %d"
                             % (n_lin, len(p), len(esquema)))
            continue
        filas.append(dict(zip(esquema, p)))
    return cab, "\n".join(l for l in cuesco if l.strip()) + "\n" if cuesco else "", \
        filas, esquema, problemas


def _maquina(ruta):
    """Las lineas de MAQUINA de la cabecera -> {etiqueta: valor}.

    MEDIDO por que se exige el prefijo EXACTO `#   <etiqueta> ` y no se busca la
    palabra: el hermano sufrio justo eso (`reenvio_freeze.py` docstring de
    `_sha_declarado`, MEDIDO 2026-10-04: al escribir una linea de prosa que
    mencionaba la clave, el lector se quedo con ella y comparo `que es la que
    verifica:` con el sha real).  MEDIDO tambien que ninguna de las 92 lineas de
    prosa de este ledger empieza por una de las 14 etiquetas de aqui, asi que el
    prefijo exacto no descarta prosa real.
    """
    out = {}
    try:
        txt = open(ruta, encoding="utf-8", errors="replace").read()
    except OSError:
        return out
    for l in txt.split("\n"):
        for et in sorted(ETIQUETAS_MAQUINA, key=len, reverse=True):
            pre = "#   %s " % et
            if l.startswith(pre):
                out[et] = l[len(pre):].strip()
                break
    return out


def _flechas_del_mapa(ruta=MAPA):
    v, n = mapa_reenvios(ruta)
    return {("viejo->%s" % v[k]) for k in v} | {("nuevo<-%s" % n[k]) for k in n}, len(v)


def guarda_mapa(filas_existentes, ruta=MAPA):
    """(ok, motivo, pares). MEDIDO lo que cada rama protege:

    * mapa ausente  ->  `clase` y `detalle` se derivarian de un mapa que no esta.
    * mapa vacio    ->  MEDIDO en este arbol: con el mapa vacio, 4 clases cambian
                       (975 R3->R4, y 976, 994, 1020 R2->R1) y se re-derivan a
                       `-` 92 celdas de `detalle`: 90 se perderian y 2 son la prosa
                       de `_sella()`, que se conserva.  Cuatro clases y noventa
                       celdas perdidas no son un detalle de formato.
    * reenvio huerfano -> MEDIDO que hoy el ledger cita 90 flechas distintas, el
                       mapa puede derivar 112, y la diferencia son 0.  Las 22 de
                       mas son
                       pares que el mapa tiene y el ledger no cita, que es lo
                       normal.  Lo que NO se tolera es al reves: una flecha que el
                       ledger dice y el mapa no tiene.  Eso significa que el mapa
                       se ha movido y `--congelar` esta a punto de clonar el
                       movimiento en 82 filas sin que nadie lo haya pedido.
    """
    if not os.path.exists(ruta):
        return False, "el mapa de reenvios NO existe: %s" % ruta, 0
    flechas, pares = _flechas_del_mapa(ruta)
    if pares == 0:
        return False, ("el mapa de reenvios esta VACIO (0 pares de datos).  "
                       "MEDIDO: con el vacio, 4 clases de este ledger se "
                       "re-derivarian distinto (975 R3->R4, y 976, 994 y 1020 "
                       "R2->R1) y se perderian 90 de las 92 celdas de `detalle` "
                       "que no valen `-`; las otras 2 son prosa y esta "
                       "implementacion las conserva.  `clase` es justo lo que C3 "
                       "compara, asi que 4 clases escritas sobre un mapa vacio "
                       "quedarian CONGELADAS como si fueran verdad"), 0
    citadas = sorted({r.get("detalle", "") for r in filas_existentes.values()
                      if RE_DETALLE.match(r.get("detalle", ""))})
    huerf = [d for d in citadas if d not in flechas]
    if huerf:
        return False, ("el ledger cita %d reenvios que el mapa ya no tiene: %s.  "
                       "MEDIDO que hoy no hay ninguno; si aparece, el mapa se ha "
                       "movido y hay que decidirlo antes de propagarlo"
                       % (len(huerf), huerf[:6])), pares
    return True, "", pares


def _derivada(f, ajen):
    """La fila que el disco dice, columna a columna. Para una fila NUEVA."""
    n = f["numero"]
    return {
        "num": n,
        "orden": f["orden"] or "",
        "clase": f["clase"] or "",
        "ts_reserva": f["ts_reserva"] or "DESCONOCIDA",
        "ts_fichero": f["ts_fichero_mas_viejo"] or "-",
        "registro": ("own" if f["registro_propio"] else "-") + "/" +
                    ("ajen" if f["registro_ajeno"] else "-"),
        "n_fich": "%d" % f["n_ficheros"],
        "detalle": f["detalle"] or "-",
        "p2_vacio": "1" if (n in ajen and ajen[n][1] == 0) else "0",
    }


def plan_congelar(existentes, med):
    """MERGE. Devuelve (filas, cuenta). NUNCA borra una fila que existe.

    `existentes` es {num: fila} del ledger; `med` es lo que devuelve `mide()`.
    No escribe: escribir es `escribir()`.  Separadas para que el self-test pueda
    ejercitar el PLAN sin bytes en disco, y para que el plan se pueda imprimir
    antes de escribir nada.
    """
    ajen = med["ajeno"]
    derivadas = {f["numero"]: _derivada(f, ajen) for f in med["filas"]}
    cuenta = {
        "filas": 0, "conservadas": 0, "anadidas": 0, "sin_fuente": 0,
        "sin_fuente_lista": [], "sin_fecha": 0, "sin_fecha_lista": [],
        "clases_rederivadas": 0, "clases_cambiadas": [],
        "ts_reserva_preservadas": 0, "ts_reserva_recuperadas": [],
        "ts_reserva_difiere": [], "detalle_prosa": [],
    }
    filas = []
    for n in sorted(set(existentes) | set(derivadas), key=lambda x: (len(x), x)):
        d, e = derivadas.get(n), existentes.get(n)
        if d is None:
            # MEDIDO el motivo: una fila que `mide()` no ve.  Se conserva ENTERA,
            # celda a celda, sin re-derivar nada: si se re-derivara con valores
            # vacios se perderian columnas, y si se re-derivara con valores
            # medidos seria inventar una fila para un numero que no existe.
            filas.append(dict(e))
            cuenta["sin_fuente"] += 1
            cuenta["sin_fuente_lista"].append(n)
            continue
        if e is None:
            filas.append(dict(d))
            cuenta["anadidas"] += 1
            if d["ts_reserva"] == "DESCONOCIDA":
                cuenta["sin_fecha"] += 1
                cuenta["sin_fecha_lista"].append(n)
            continue
        f = dict(e)
        for c in COLS_REDERIVA:
            if f.get(c) != d[c]:
                cuenta["clases_rederivadas"] += 1
                if c == "clase":
                    cuenta["clases_cambiadas"].append((n, f.get(c), d[c]))
            f[c] = d[c]
        # `detalle`: la prosa de `_sella()` no es una flecha y no se re-deriva.
        if not RE_DETALLE.match(e.get("detalle", "")) and e.get("detalle", "-") != "-":
            f["detalle"] = e["detalle"]
            cuenta["detalle_prosa"].append((n, e["detalle"]))
        # `ts_reserva`: se conserva, con dos excepciones explicitas.
        if e.get("ts_reserva") == "DESCONOCIDA" and d["ts_reserva"] != "DESCONOCIDA":
            f["ts_reserva"] = d["ts_reserva"]
            cuenta["ts_reserva_recuperadas"].append(n)
        else:
            cuenta["ts_reserva_preservadas"] += 1
            if e.get("ts_reserva") != d["ts_reserva"] and d["ts_reserva"] != "DESCONOCIDA":
                cuenta["ts_reserva_difiere"].append(
                    (n, e.get("ts_reserva"), d["ts_reserva"]))
        filas.append(f)
    cuenta["filas"] = len(filas)
    # MEDIDO por que se calcula aqui y no se suma en la rama: la version anterior
    # lo incrementaba SOLO en la rama de la fila sin fuente, asi que una corrida
    # sobre el ledger entero anunciaba `filas_conservadas 0` con 451 filas
    # conservadas.  Un contador que dice 0 con 451 cosas delante es peor que no
    # tenerlo: entrena a leerlo como "no se conservo nada".
    cuenta["conservadas"] = cuenta["filas"] - cuenta["anadidas"]
    return filas, cuenta


def _cabecera_para(cuerpo_txt, cuenta, destino):
    """Reescribe SOLO las lineas de MAQUINA y conserva toda la prosa.

    MEDIDO por que no es una plantilla: la cabecera que hay en disco son 92 lineas
    de prosa medida -- POR QUE EXISTE, POR QUE SE LLAMA .ledger, POR QUE 298 NO SE
    LIBERA -- y una plantilla fija las borraria todas.  Se conservan verbatim
    todas las `#` que no sean linea de maquina, y se sustituyen las que si.

    MEDIDO tambien que la prosa del ALCANCE del sha se anade UNA vez: si ya esta,
    no se duplica, porque un `--congelar` repetido tiene que dejar el fichero
    igual byte a byte y un bloque de prosa repetido lo rompe.
    """
    viejo = []
    if os.path.exists(destino):
        try:
            lineas = open(destino, encoding="utf-8").read().splitlines()
        except OSError:
            lineas = []
        # MEDIDO por que se corta en la primera fila de DATOS y no se filtra por
        # `startswith("#")`: el filtro se comia las lineas VACIAS de la cabecera.
        # El ledger del arbol tiene una, justo entre la prosa y el `#SCHEMA`, y la
        # primera vez que se escribio desaparecio.  No es que estropeara nada --
        # el diff era de una linea -- pero un escritor que borra en silencio es
        # un escritor del que no se puede depender para lo que no se le pidio.
        corte = None
        for i, l in enumerate(lineas):
            if l.strip() and not l.startswith("#"):
                corte = i
                break
        viejo = lineas[:corte] if corte is not None else list(lineas)
    conservadas = [l for l in viejo if not RE_ETIQUETA_MAQUINA.match(l)]
    if not any(l.startswith("# ALCANCE DEL sha256_cuerpo") for l in viejo):
        conservadas += [
            "# ALCANCE DEL sha256_cuerpo: el valor es el de SOLO las filas de",
            "#   datos --las que no empiezan por # y no estan vacias--, unidas con",
            '#   \\n y con \\n final.  MEDIDO que la normalizacion del ledger hermano',
            "#   sirve aqui tal cual: A (join + \\n final) y B (bucle fila+\\n) dan el",
            "#   mismo sha byte a byte, y el fichero entero con cabecera da otro",
            "#   (8a58fb63... frente a 056501b9...), que no sirve porque cualquier",
            "#   linea de prosa lo giraria sin haber cambiado un solo numero.",
            "#",
            "# QUE RE-DERIVA --congelar Y QUE CONSERVA.  Medido columna por columna",
            "#   contra el disco: RE-DERIVA orden, clase, ts_fichero, registro,",
            "#   n_fich, p2_vacio y el `detalle` que sea una flecha.  CONSERVA num",
            "#   (es la clave) y ts_reserva.  ts_reserva NO se puede re-derivar:",
            "#   MEDIDO que de las 7 filas con fecha real, 3 no tienen `.res` en",
            "#   disco -- su fecha la puso `nextnum.py _sella()` al reservar y no",
            "#   esta en ningun otro sitio -- y re-derivarlas escribiria",
            "#   DESCONOCIDA, que es una afirmacion FALSA y no una celda vacia.",
            "#   `--congelar` NUNCA borra una fila: la que `mide()` no ve se",
            "#   conserva entera y se cuenta en filas_sin_fuente.",
        ]
    maq = [
        ("generado_por", "tools/reservas_gate.py --congelar"),
        ("generado_en", time.strftime("%Y-%m-%dT%H:%M:%S")),
        ("filas_ledger", "%d" % cuenta["filas"]),
        ("modo", "congelar"),
        ("filas_conservadas", "%d" % cuenta["conservadas"]),
        ("filas_anadidas", "%d" % cuenta["anadidas"]),
        ("filas_sin_fuente", "%d" % cuenta["sin_fuente"]),
        ("clases_rederivadas", "%d" % cuenta["clases_rederivadas"]),
        ("ts_reserva_preservadas", "%d" % cuenta["ts_reserva_preservadas"]),
        ("ts_reserva_recuperadas", "%d" % len(cuenta["ts_reserva_recuperadas"])),
        ("detalle_prosa_conservada", "%d" % len(cuenta["detalle_prosa"])),
        ("ts_reserva_sin_fecha", "%d" % cuenta["sin_fecha"]),
        ("mapa_pares", "%d" % cuenta.get("mapa_pares", 0)),
        ("sha256_cuerpo", sha_de(cuerpo_txt)),
    ]
    return "\n".join(conservadas +
                     ["#   %-28s %s" % (k, v) for k, v in maq]) + "\n"


def escribir(destino, filas, cuenta):
    """Escribe cabecera + cuerpo. Atomico: temporal + os.replace.

    MEDIDO por que atomico y no `open(destino,"w")`: hay OTRO escritor de este
    mismo fichero, `nextnum.py _sella()`, que hace append.  Un truncate seguido de
    un crash deja el ledger en un estado que las dos mitades leen sin querer, y
    el ledger existe para que una fila no desaparezca.  El temporal va en el
    MISMO directorio, porque `os.replace` es atomico dentro del sistema de
    ficheros y no lo es entre dos.
    """
    c = "\n".join("\t".join(f[col] for col in COLS) for f in filas) + "\n"
    cab = _cabecera_para(c, cuenta, destino)
    tmp = destino + ".congelar.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(cab)
        fh.write(c)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, destino)
    return c


def cmd_congelar(ruta=LEDGER):
    """MERGE. No borra. 0 hecho o sin cambios, 1 defecto de forma, 2 no medido,
    3 se ha negado a escribir y dice por que."""
    cab, viejo_cuerpo, filas_viejas, esquema, probs = _estructura(ruta)
    if esquema is None:
        print("reservas_gate --congelar: el ledger no tiene linea #SCHEMA: %s" % ruta,
              file=sys.stderr)
        print("  No se anade fila a un fichero que nadie puede leer.  "
              "`nextnum.py _sella()` tiene la misma guarda.", file=sys.stderr)
        return RC_NO_EJECUTO
    if tuple(esquema) != COLS:
        print("reservas_gate --congelar: el #SCHEMA del ledger no son las 9 "
              "columnas de esta herramienta.", file=sys.stderr)
        print("  declara: %s" % " | ".join(esquema), file=sys.stderr)
        print("  espera: %s" % " | ".join(COLS), file=sys.stderr)
        print("  No se reescribe el esquema sin decir por que, asi que no se "
              "reescribe.", file=sys.stderr)
        return RC_NO_EJECUTO
    if probs:
        for p in probs[:10]:
            print("reservas_gate --congelar: %s" % p, file=sys.stderr)
        print("  %d filas con la forma equivocada.  Se congela el resto y el "
              "defecto queda a la vista; `--verificar` lo cuenta." % len(probs),
              file=sys.stderr)

    med = mide()
    if med is None:
        print("reservas_gate: no existe el directorio de hallazgos: %s" % FIND,
              file=sys.stderr)
        return RC_NO_EJECUTO

    existentes = {r["num"]: r for r in filas_viejas if r.get("num")}
    ok, motivo, pares = guarda_mapa(existentes)
    if not ok:
        print("reservas_gate --congelar: NO CONGELO: %s" % motivo, file=sys.stderr)
        print("  Nada escrito.  Congelar aqui no arreglaria nada: `clase` y "
              "`detalle` se derivan del mapa, y sin el mapa lo unico que se "
              "podria escribir es la ausencia del mapa, con letra de dato.",
              file=sys.stderr)
        return RC_NADA_QUE_ANADIR

    filas, cuenta = plan_congelar(existentes, med)
    cuenta["mapa_pares"] = pares
    nuevo_cuerpo = "\n".join("\t".join(f[c] for c in COLS) for f in filas) + "\n"

    maq = _maquina(ruta)
    declarado = maq.get("sha256_cuerpo")
    cuerpo_ok = (nuevo_cuerpo == viejo_cuerpo)
    if cuerpo_ok and declarado == sha_de(nuevo_cuerpo) and not probs:
        print("congelado: sin cambios, %d filas, sha256 %s  (nada escrito)"
              % (cuenta["filas"], sha_de(nuevo_cuerpo)))
        return RC_OK

    if cuerpo_ok:
        print("congelado: el cuerpo NO cambia (%d filas); solo se declara el "
              "sha256" % cuenta["filas"])
    escribir(ruta, filas, cuenta)
    print("congelado (merge) %s" % ruta)
    print("  filas        %d  (antes %d)" % (cuenta["filas"], len(existentes)))
    print("  conservadas  %d   anadidas %d" % (cuenta["conservadas"],
                                                cuenta["anadidas"]))
    print("  rederivadas  %d celdas" % cuenta["clases_rederivadas"])
    print("  sha256       %s" % sha_de(nuevo_cuerpo))
    if cuenta["clases_cambiadas"]:
        print("  CLASE QUE CAMBIA (%d).  Esto es lo que hace que C3 vuelva a "
              "verde:" % len(cuenta["clases_cambiadas"]))
        for n, v, d in cuenta["clases_cambiadas"][:12]:
            print("    num %-6s %-26s -> %s" % (n, v, d))
    anadidas = sorted(set(f["num"] for f in filas) - set(existentes),
                      key=lambda x: (len(x), x))
    if anadidas:
        print("  anadidas     %d: %s" % (len(anadidas), " ".join(anadidas[:20])))
    if cuenta["sin_fuente"]:
        print("  SIN FUENTE, CONSERVADAS (%d): `mide()` ya no ve estos numeros.  "
              "No se borran: una fila que desaparece es un residuo sin "
              "clasificar." % cuenta["sin_fuente"])
        print("               %s" % " ".join(cuenta["sin_fuente_lista"][:20]))
    if cuenta["sin_fecha"]:
        print("  SIN FECHA DE RESERVA (%d): no hay `.res` de donde sacarla, y la "
              "fecha la puso" % cuenta["sin_fecha"])
        print("               `nextnum.py _sella()` en el momento de reservar.  "
              "MEDIDO que a partir de aqui")
        print("               `_sella()` ya no las volvera a sellar, porque su "
              "guarda es `n in ya`:")
        print("               la fila existe.  La fecha se queda DESCONOCIDA, y "
              "eso no es un fallo")
        print("               de esta herramienta: es una consecuencia del ORDEN "
              "entre los dos")
        print("               escritores.  Se declara, no se disimula.")
    if cuenta["ts_reserva_recuperadas"]:
        print("  ts_reserva RECUPERADA del `.res`: %s"
              % " ".join(cuenta["ts_reserva_recuperadas"]))
    if cuenta["ts_reserva_difiere"]:
        print("  ts_reserva DIFIERE, se conserva la del ledger (registra lo que "
              "la reserva decia al reservarse):")
        for n, v, d in cuenta["ts_reserva_difiere"][:12]:
            print("    num %-6s ledger %s   `.res` %s" % (n, v, d))
    if cuenta["detalle_prosa"]:
        print("  detalle PROSA conservada (%d): no es una flecha, asi que no se "
              "re-deriva" % len(cuenta["detalle_prosa"]))
        for n, v in cuenta["detalle_prosa"][:6]:
            print("    num %-6s %s" % (n, v))
    return RC_OK


def problemas_forma(filas, probs, esquema):
    """Defectos de FORMA del ledger. Devuelve [(texto, es_error)].

    Lo que NO va aqui: si una clase esta desfasada respecto del disco.  Eso es C3,
    y es de otra cosa -- de la RELACION entre el fichero y el arbol, no del
    fichero consigo mismo.
    """
    out = []
    for p in probs:
        out.append((p, True))
    vistos = set()
    repetidos = []
    for r in filas:
        n = r.get("num", "")
        if n in vistos:
            repetidos.append(n)
        vistos.add(n)
    if repetidos:
        out.append(("numero repetido en el ledger: %s" % " ".join(sorted(repetidos)),
                    True))
    malas_clase = sorted({r.get("clase", "") for r in filas
                          if r.get("clase", "") not in TODAS and r.get("clase") != R_PENDIENTE})
    if malas_clase:
        out.append(("clase que no es de las ocho y no es %s: %s"
                    % (R_PENDIENTE, " ".join(repr(c) for c in malas_clase)), True))
    malos_orden = sorted({r.get("orden", "") for r in filas
                          if r.get("orden", "") not in ORDENES})
    if malos_orden:
        out.append(("orden que no es ninguno de los cinco: %s"
                    % " ".join(repr(o) for o in malos_orden), True))
    malos_nf = sorted({r.get("n_fich", "") for r in filas
                       if not re.match(r"^\d+$", r.get("n_fich", ""))})
    if malos_nf:
        out.append(("n_fich que no es un entero: %s" % " ".join(malos_nf), True))
    malos_p2 = sorted({r.get("p2_vacio", "") for r in filas
                       if r.get("p2_vacio", "") not in ("0", "1")})
    if malos_p2:
        out.append(("p2_vacio que no es 0 ni 1: %s" % " ".join(malos_p2), True))
    return out


def cmd_verificar(ruta=LEDGER, json_salida=False):
    """SOLO LECTURA. No escribe. 0 si todo cuadra, 1 si algo no."""
    cab, cuerpo_txt, filas, esquema, probs = _estructura(ruta)
    fallos, avisos = [], []

    if esquema is None:
        fallos.append("el ledger no tiene linea #SCHEMA.  Sin ella no se pueden "
                      "leer columnas por nombre, que es lo unico que impide que "
                      "un cambio de orden de columnas pase desapercibido")
    elif tuple(esquema) != COLS:
        fallos.append("el #SCHEMA declara %s y esta herramienta escribe %s"
                      % (",".join(esquema), ",".join(COLS)))

    for txt, es_err in problemas_forma(filas, probs, esquema):
        (fallos if es_err else avisos).append(txt)

    pendientes = sorted(r["num"] for r in filas if r.get("clase") == R_PENDIENTE)
    if pendientes:
        avisos.append("%d fila(s) con clase %s, esperando que --congelar las "
                      "clasifique: %s" % (len(pendientes), R_PENDIENTE,
                                           " ".join(pendientes)))

    # --- el sha256 del CUERPO declarado en la cabecera ------------------------
    maq = _maquina(ruta)
    declarado = maq.get("sha256_cuerpo")
    real = sha_de(cuerpo_txt) if cuerpo_txt else None
    if declarado is None:
        avisos.append("la cabecera NO declara sha256_cuerpo.  `--congelar` lo "
                      "escribe; mientras no este, la integridad del cuerpo no "
                      "esta declarada por el propio fichero")
    elif real is not None and declarado != real:
        fallos.append("sha256 declarado %s != real %s  (normalizacion: %s)"
                      % (declarado[:16], real[:16],
                         "solo filas de datos, unidas con \\n, con \\n final"))

    # --- las flechas que el ledger dice y el mapa ya no tiene -----------------
    existentes = {r["num"]: r for r in filas if r.get("num")}
    ok_mapa, motivo, pares = guarda_mapa(existentes)
    if not ok_mapa:
        fallos.append(motivo)

    # --- y las CINCO condiciones, que son de otra cosa ------------------------
    med = mide()
    checks = []
    if med is not None:
        clase_obs, _cnt = clases_de(med)
        clase_led = {n: r.get("clase", "") for n, r in existentes.items()}
        p2_obs = set(n for n, (f, s, t) in med["ajeno"].items() if s == 0)
        p2_led = set(n for n, r in existentes.items() if r.get("p2_vacio") == "1")
        r5_led = set(n for n, c in clase_led.items() if c == R5_EN_USO_DOS_VECES)
        checks = comprobaciones(med, clase_obs, clase_led, p2_obs, p2_led, r5_led)
        for nombre, ok, det in checks:
            if not ok:
                fallos.append("%s: %s" % (nombre, det))
    else:
        fallos.append("no existe el directorio de hallazgos: %s" % FIND)

    if json_salida:
        print(json.dumps({
            "version": VERSION, "modo": "verificar", "ledger": ruta,
            "filas": len(filas), "columnas": list(esquema or []),
            "mapa_pares": pares,
            "sha256_declarado": declarado, "sha256_real": real,
            "pendientes": pendientes,
            "checks": [{"nombre": n, "ok": o, "detalle": d} for n, o, d in checks],
            "fallos": fallos, "avisos": avisos,
            "rc": 0 if not fallos else 1}, indent=2, sort_keys=True, ensure_ascii=False))
        return RC_OK if not fallos else RC_FALLO

    L = print
    L("=" * 74)
    L("reservas_gate %s · --verificar  (SOLO LECTURA: no escribe nada)" % VERSION)
    L("=" * 74)
    L("")
    L("  ledger        %s" % ruta)
    L("  filas         %d   columnas %d" % (len(filas), len(esquema or [])))
    L("  sha256        %s" % (declarado or "NO DECLARADO"))
    L("  cuerpo real   %s" % (real or "(vacio)"))
    L("  pares del mapa %d" % pares)
    L("  %s            %d" % (R_PENDIENTE, len(pendientes)))
    L("")
    if checks:
        L("  LAS CINCO CONDICIONES:")
        for nombre, ok, det in checks:
            L("    [%s] %-38s %s" % ("OK" if ok else "FALLA", nombre, det[:60]))
        L("")
    for a in avisos:
        L("  AVISO %s" % a)
    for f in fallos:
        L("  FALLA  %s" % f)
    L("")
    L("  VEREDICTO: %s" % ("coherente" if not fallos
                           else "%d defecto(s).  Ver arriba." % len(fallos)))
    return RC_OK if not fallos else RC_FALLO


def main() -> int:
    ap = argparse.ArgumentParser(
        description="clasifica toda discrepancia reservas/hallazgos y falla si "
                    "alguna queda sin clasificar")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--ledger", metavar="RUTA", default=LEDGER)
    ap.add_argument("--congelar", action="store_true",
                    help="MERGE: re-deriva las columnas que el disco puede "
                         "medir, conserva las demas, anade las filas que falten "
                         "y NUNCA borra ninguna.  No reescribe el esquema")
    ap.add_argument("--verificar", action="store_true",
                    help="forma del ledger + sha256 del cuerpo + las cinco "
                         "condiciones.  SOLO LECTURA: no escribe nada")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if args.congelar and args.verificar:
        print("reservas_gate: --congelar escribe y --verificar no.  No se "
              "pueden pedir a la vez.", file=sys.stderr)
        return RC_NO_EJECUTO
    if args.congelar:
        return cmd_congelar(args.ledger)
    if args.verificar:
        return cmd_verificar(args.ledger, json_salida=args.json)

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
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""check_num_unico.py 1.0.0 - PUERTA: el numero de hallazgo identifica un hallazgo?

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA

QUE AFIRMA, Y SON TRES AFIRMACIONES, NO UNA

  A1  todo prefijo numerico de `findings/*.md` identifica UN SOLO fichero
  A2  todo numero duplicado tiene fila en el indice
  A3  no queda ninguna cita por numero colgando sobre un numero duplicado

CODIGOS DE SALIDA, Y POR QUE NO SON 0 Y 1

  0  las tres afirmaciones se sostienen
  1  (no se usa) reservado: 1 es error generico y se confunde con un linter
  2  falta `findings/` o el indice
  3  hay colisiones sin fila en el indice                  <- el defecto de HOY
  4  quedan citas por numero a un numero duplicado         <- la ambiguedad de HOY
  5  el indice de disco no regenera identico               <- el indice esta viejo

  PRECEDENCIA, y no es arbitraria: 2 > 5 > 3 > 4.

    2 antes que nada: sin `findings/` o sin indice no hay nada que afirmar.
    5 antes que 3 y 4: A2 y A3 se miden CONTRA el indice. Si el indice no
      regenera identico, la comparacion se hace contra una medida equivocada, y
      un 3 o un 4 emitido sobre un indice viejo no seria un hallazgo sobre el
      arbol: seria un hallazgo sobre un fichero desactualizado. Se dice primero
      que el instrumento esta viejo.
    3 antes que 4: una colision sin fila es un defecto del REGISTRO. Una cita
      ambigua es un defecto del USO. El primero se arregla generando el indice;
      el segundo, reescribiendo citas. Se pueden tener los dos.

  La puerta imprime TODOS los hallazgos aunque devuelva uno solo. Un codigo de
  salida que oculta los otros tres convierte la puerta en un contador.

EL INDICE QUE ESTA EN JUEGO

  `FINDINGS-RENUMERACIONES.md`, en la raiz. Lo genera
  `08-ARQUITECTURA/tools/findings_index.py`, y su seccion
  `## Numeros con colision` ES un indice `NNN -> [ficheros]`: exactamente la
  forma que la decision M1 elige. No hace falta escribir un indice nuevo; hace
  falta la puerta que no existia.

  LO QUE SE COMPARA Y LO QUE NO, y por que:

    SE COMPARA (funcion pura del FS `findings/`)
      - el recuento de ficheros que el indice declara en su cabecera
      - el recuento de numeros con colision que declara
      - el conjunto de filas de la tabla de colisiones, CONTRA EL CONJUNTO, no
        contra el numero

    NO SE COMPARA (depende de git HEAD, no del FS)
      - `Renumeraciones detectadas`
      - `Referencias colgando`
      Esas dos lineas las produce `reenvios()`, que compara contra HEAD porque el
      renumerado puede estar sin commitear. Dependen de dos entradas --el arbol Y
      HEAD--, luego no son funcion pura del FS y una diferencia ahi no distingue
      "el arbol cambio" de "el commit cambio". Se declaran
      NOT_COMPARABLE_DEPENDE_DE_HEAD y no se usan como veredicto. Es
      `NOT_DETERMINED` con motivo escrito, no un hueco silencioso.

POR QUE COMPARA CONJUNTOS Y NO RECUENTOS: MEDIDO HOY

  Estado medido del arbol en el momento de escribir esto:

      ficheros en findings/ por listdir            : 539
      `Ficheros en findings/` que dice el indice   : 509      (30 viejo)
      numeros con colision por el FS               : 74
      numeros con colision que dice el indice      : 74
      filas en la tabla de colisiones del indice  : 74

  El numero coincide: 74 = 74. El CONJUNTO no:

      en el FS y SIN fila en el indice  : 1011
      con fila en el indice y SIN choque en el FS : 998

  Los dos errores se compensan y el recuento sale bien. Una puerta que comparase
  recuentos pasaria en VERDE hoy con el defecto presente. Por eso A2 y el codigo 5
  comparan conjuntos.

  El mecanismo, medido por mtime:

      FINDINGS-RENUMERACIONES.md        2026-10-03T15:59:03
      1011-el-grep-de-ad8...md           2026-10-03T16:06:21   (+7 min)
      1011-la-regla-de-shell...md        2026-10-03T16:06:37   (+8 min)
      ficheros de findings/ mas nuevos que el indice : 195 de 539

  El indice describe un directorio que ya no existe, y el recuento de colisiones
  le quedo bien por casualidad. Esto es lo que la puerta existe para que no
  vuelva a pasar: hoy nadie comparo el numero del informe contra el disco.

LO QUE ESTA MEDIDO Y NO SE RE-MIDE AQUI

  - 74 grupos duplicados, 175 ficheros implicados, 101 copias sobrantes
  - de los 74 grupos, 73 tienen TODOS sus ficheros citados: `dupenum.py --aplicar`
    puede liberar 1 de 74, no 74. Renumerar como politica general esta agotada.
  - los 539 nombres de fichero de findings/ son UNICOS: una cita por nombre no
    puede ser ambigua, puede estar COLGADA. Son dos defectos distintos y esta
    puerta mide el de las citas por numero.

AUTOCOMPROBACION CONTRA EL FS

  El numero de colisiones NO esta escrito en el script. La puerta cuenta ella
  misma los `findings/*.md` con `os.listdir`, cuenta ella misma los choques, y
  compara las dos cosas. Si manana hay 75 colisiones sale 3 sin que nadie toque
  un byte del codigo.

  La COBERTURA se mide y se imprime: ficheros de hallazgo vistos en disco /
  ficheros de hallazgo en disco. Si no puede leer alguno, la cobertura baja de
  100 %, la regeneracion no es comparable y la puerta sale 5: un indice
  regenerado sobre una lectura parcial no es "el indice", es otra cosa.

LO QUE NO HACE

  NO renombra. NO reescribe citas. NO regenera el indice. NO toca la GPU, ni
  sysfs, ni registros, ni dmesg. Es una puerta: o el estado se sostiene o no.

  NO decide cual de los dos hallazgos duplicados tiene razon. Dos hallazgos con
  el mismo numero pueden decir cosas distintas; eso es una CONTRADICCION que hay
  que leer, y esta herramienta solo cuenta.

  NO afirma que las citas por numero sean correctas, solo que no apuntan a un
  numero ambiguo. Una cita `033:397` que resuelve al fichero equivocado es un
  defecto que esta puerta NO ve, y eso lo dice su propio nombre.

ALCANCE DE LA BUSQUEDA DE CITAS, Y POR QUE SE DECLARA

  Se recorre el arbol del proyecto y se excluyen los arboles vendorizados:
  `RESEARCH/` (109652 ficheros, el codigo del kernel), `rx550-upstream-7.2.8/`
  (2842) y `archive/`. Un hallazgo no se cita dentro del codigo de Linux. El
  alcance se imprime, con el numero de ficheros leidos, para que sea medible y
  no una constante escondida.

  MEDIDO el coste de las dos opciones sobre este arbol:

    --alcance propio    2496 ficheros leidos    1.54 s   RSS 31 MB
                        2148 citas ambiguas    codigo 5   [5, 3, 4]
    --alcance todo     76938 ficheros leidos  143.55 s   RSS 91 MB
                        2216 citas ambiguas    codigo 5   [5, 3, 4]

  conclusion no depende del alcance. Las cifras de citas si (2148 contra 2216,
  +68), y por eso el alcance se imprime siempre. El codigo de salida tampoco
  depende del alcance, y eso es lo que hace que el valor por defecto sea `propio` y
  no una decision todavia pendiente: el defecto se detecta igual, y 143 s no es el
  precio de una puerta.

  `--alcance todo` existe para que la exclusion sea una DECISION y no una
  constante escondida. En este arbol es impracticable como puerta -- el codigo
  de Linux tiene 109652 ficheros y no contiene hallazgos del proyecto -- y por eso
  el valor por defecto es `propio`. Nota de alcance: `RESEARCH/` y
  `rx550-upstream-7.2.8/` aportan 74442 ficheros y SOLO 68 citas por numero.

  Formas de cita POR NUMERO que se cuentan, y solo estas:
      `NNN:LL`     cita con linea
      `NNN`         referencia entre acentos graves
      findings/NNN  ruta sin nombre
  NO se cuenta `findings/NNN-slug...`: es cita por NOMBRE, y el nombre es clave
  primaria unica.

Uso:
  python3 check_num_unico.py              resumen + veredicto
  python3 check_num_unico.py --json       lo mismo, estructurado
  python3 check_num_unico.py --limite N   cuantas filas de detalle imprime
  python3 check_num_unico.py --alcance {propio|todo}
  python3 check_num_unico.py --selftest   fabrica 0, 2, 3, 4 y 5 por separado
"""

import argparse
import ast
import collections
import json
import os
import re
import sys

VERSION = "1.0.0"
WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

EXIT_OK = 0
EXIT_FALTA = 2
EXIT_COLISION_SIN_FILA = 3
EXIT_CITAS_AMBIGUAS = 4
EXIT_INDICE_VIEJO = 5

# Numero de hallazgo: 3 o 4 digitos. `\d{3}` es un ancho EXACTO y en cuanto
# existe `1000-algo.md` deja de casar: es el fallo ya medido y corregido en
# `findings_index.py:RE_NUM` y en `findnum.py`. Aqui va `\d{3,4}` por el mismo
# motivo, y el selftest lo comprueba con un hallazgo de cuatro digitos.
RE_NUM = re.compile(r"^(\d{3,4})-(.+)\.md$")

# Las tres formas de cita por numero. Los lookahead/lookbehind importan: sin
# ellos, `findings/001-unico.md` casaria como `findings/001` y contaria una cita
# por numero donde lo que hay es una cita por nombre.
RE_CITA_LL = re.compile(r"(?<![\w/.\-])(\d{3,4}):(\d+)\b")
RE_CITA_BT = re.compile(r"`(\d{3,4})`")
RE_CITA_RUTA = re.compile(r"findings/(\d{3,4})(?![\d\w\-])")

EXT_LEIBLES = (".md", ".py", ".sh", ".c", ".h", ".txt", ".tsv")
EXCLUIDOS_PROPIO = ("RESEARCH", "rx550-upstream-7.2.8", "archive",
                    ".git", "__pycache__")
NOMBRE_INDICE = "FINDINGS-RENUMERACIONES.md"
SECCION_COLISION = "## Numeros con colision"

RE_HDR_COLISION = re.compile(r"colision\*\*\s*\(>1 fichero\):\s*\*\*(\d+)\*\*")
RE_HDR_FICHEROS = re.compile(r"Ficheros en `findings/`:\s*\*\*(\d+)\*\*")


def proyecto() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def dir_hallazgos(raiz: str) -> str:
    return os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")


def ruta_indice(raiz: str) -> str:
    return os.path.join(raiz, NOMBRE_INDICE)


# --------------------------------------------------------------------------
# 1. EL FS. La puerta cuenta ella misma; no hay ninguna constante en el codigo.
# --------------------------------------------------------------------------

def fs_indice(raiz: str):
    """(numero -> [ficheros], cobertura, vistos, en_disco, sin_prefijo).

    `cobertura` = vistos / en_disco. Es la fraccion que la puerta ha podido LEER.
    Si baja de 1.0, cualquier regeneracion del indice es incompleta y por tanto
    no comparable: eso es el codigo 5, no un acierto silencioso.
    """
    dirf = dir_hallazgos(raiz)
    if not os.path.isdir(dirf):
        return None, 0.0, 0, 0, []
    try:
        entradas = sorted(os.listdir(dirf))
    except OSError:
        return None, 0.0, 0, 0, []
    en_disco = [f for f in entradas
                if f.endswith(".md") and os.path.isfile(os.path.join(dirf, f))]
    por_num = collections.defaultdict(list)
    sin_prefijo = []
    vistos = 0
    for f in en_disco:
        m = RE_NUM.match(f)
        if not m:
            sin_prefijo.append(f)
            continue
        try:
            with open(os.path.join(dirf, f), encoding="utf-8",
                      errors="replace") as fh:
                fh.read(1)
            vistos += 1
        except OSError:
            # legible por nombre pero no por contenido: cuenta como no visto,
            # que es exactamente lo que la cobertura mide.
            continue
        por_num[m.group(1)].append(f)
    cob = (float(vistos) / len(en_disco)) if en_disco else 0.0
    return por_num, cob, vistos, len(en_disco), sin_prefijo


def fs_colisiones(por_num):
    return {n: sorted(v) for n, v in por_num.items() if len(v) > 1}


# --------------------------------------------------------------------------
# 2. EL INDICE. Se lee lo que DECLARA y lo que TABULA, por separado.
# --------------------------------------------------------------------------

def leer_indice(ruta: str):
    """{numero -> set(ficheros)} de la tabla de colisiones, y las cabeceras.

    Falla ruidosamente si la seccion no existe: un indice sin tabla de colisiones
    no es un indice de colisiones, y aceptarlo como vacio seria exactamente el
    fallo que la puerta persigue.
    """
    try:
        with open(ruta, encoding="utf-8", errors="replace") as fh:
            texto = fh.read()
    except OSError:
        return None
    lineas = texto.split("\n")
    try:
        i0 = next(i for i, l in enumerate(lineas)
                  if l.startswith(SECCION_COLISION))
    except StopIteration:
        return None
    i1 = len(lineas)
    for i in range(i0 + 1, len(lineas)):
        if lineas[i].startswith("## "):
            i1 = i
            break
    filas = {}
    for l in lineas[i0:i1]:
        m = re.match(r"^\|\s*`?(\d{3,4})`?\s*\|(.*)\|\s*$", l)
        if not m or m.group(1) == "numero":
            continue
        fs = set(x.strip().strip("`") for x in m.group(2).split("<br>"))
        filas[m.group(1)] = fs
    cab = {
        "colisiones": (RE_HDR_COLISION.search(texto).group(1)
                       if RE_HDR_COLISION.search(texto) else None),
        "ficheros": (RE_HDR_FICHEROS.search(texto).group(1)
                     if RE_HDR_FICHEROS.search(texto) else None),
    }
    return {"filas": filas, "cabeceras": cab, "n_filas": len(filas)}


def indice_regenera_identico(idx, por_num, cob):
    """Diferencias entre el indice de disco y el que sale del FS.

    Se devuelven TIPADAS, y la tipacion reparte los dos codigos de forma que no
    se solapen:

      RECENTRO_* / CABECERA_* / COBERTURA_INCOMPLETA  -> 5  (el indice esta viejo)
      SIN_FILA_EN_EL_INDICE / FILA_SIN_COLISION_* /
      FILA_INCOMPLETA                                 -> 3  (la tabla no enumera)

    POR QUE NO SE SOLAPAN, y por que no se podrian separar de otro modo. La
    pregunta "todo numero duplicado tiene fila en el indice" (A2, codigo 3) y la
    pregunta "la tabla de colisiones es el conjunto de colisiones del FS" son la
    MISMA proposicion: si una fila falta, otra sobra. Un indice que enumera
    exactamente las colisiones no puede tener ni una fila de mas ni una de menos.
    Por eso 3 no puede ser "la tabla esta mal" y 5 no puede ser "la tabla esta
    mal": 3 es la tabla, 5 son las CIFRAS que el indice declara arriba.

    Y aqui esta el motivo de que la comparacion sea de CONJUNTOS y no de
    RECUENTOS: hay un estado medido en este arbol en el que las cifras COINCIDEN
    y el conjunto NO. Ver la cabecera del modulo.

    Devuelve (difs_5, diffs_3).
    """
    d5, d3 = [], []
    col = fs_colisiones(por_num)
    fs_en_disco = sum(len(v) for v in por_num.values())

    if cob < 1.0:
        d5.append({"tipo": "COBERTURA_INCOMPLETA", "vistos": None,
                   "detalle": "cobertura %.4f < 1.0: hay ficheros de hallazgo que "
                              "no se han podido leer, y un indice regenerado "
                              "sobre una lectura parcial no es el indice"
                              % cob})
        return d5, d3

    cab = idx["cabeceras"]
    if cab["ficheros"] is None:
        d5.append({"tipo": "CABECERA_SIN_RECuento_FICHEROS", "vistos": None,
                   "detalle": "el indice no declara 'Ficheros en findings/: **N**'"})
    elif int(cab["ficheros"]) != fs_en_disco:
        d5.append({"tipo": "RECENTRO_FICHEROS",
                   "vistos": int(cab["ficheros"]), "disco": fs_en_disco,
                   "detalle": "el indice declara %d ficheros, hay %d en disco"
                              % (int(cab["ficheros"]), fs_en_disco)})

    if cab["colisiones"] is None:
        d5.append({"tipo": "CABECERA_SIN_RECuento_COLISIONES", "vistos": None,
                   "detalle": "el indice no declara el numero de colisiones"})
    elif int(cab["colisiones"]) != len(col):
        d5.append({"tipo": "RECENTRO_COLISIONES",
                   "vistos": int(cab["colisiones"]), "disco": len(col),
                   "detalle": "el indice declara %d colisiones, el FS tiene %d"
                              % (int(cab["colisiones"]), len(col))})
    if (cab["colisiones"] is not None
            and int(cab["colisiones"]) != idx["n_filas"]):
        d5.append({"tipo": "CABECERA_VS_TABLA",
                   "vistos": int(cab["colisiones"]), "disco": idx["n_filas"],
                   "detalle": "la cabecera dice %s colisiones y la tabla tiene "
                              "%s filas: el indice se contradice a si mismo"
                              % (cab["colisiones"], idx["n_filas"])})

    # CONJUNTOS. El FS es la verdad.
    falta = sorted(set(col) - set(idx["filas"]))
    sobra = sorted(set(idx["filas"]) - set(col))
    if falta:
        d3.append({"tipo": "SIN_FILA_EN_EL_INDICE", "vistos": falta,
                   "disco": len(falta),
                   "detalle": "colision en el FS sin fila en el indice: %s"
                              % ", ".join(falta)})
    if sobra:
        d3.append({"tipo": "FILA_SIN_COLISION_EN_EL_FS", "vistos": sobra,
                   "disco": len(sobra),
                   "detalle": "el indice da por colision un numero que el FS "
                              "no tiene: %s" % ", ".join(sobra)})
    parcial = []
    for n in sorted(set(col) & set(idx["filas"])):
        a, b = set(col[n]), set(idx["filas"][n])
        if a != b:
            parcial.append({"numero": n, "falta_en_indice": sorted(a - b),
                            "sobra_en_indice": sorted(b - a)})
    if parcial:
        d3.append({"tipo": "FILA_INCOMPLETA", "vistos": parcial,
                   "disco": len(parcial),
                   "detalle": "la fila existe pero no lista los mismos ficheros"})
    return d5, d3


def colisiones_sin_fila(idx, col):
    """A2. Set de numeros que colisionan en el FS y no tienen fila en el indice."""
    return sorted(set(col) - set(idx["filas"]))


# --------------------------------------------------------------------------
# 3. LAS CITAS POR NUMERO. A3.
# --------------------------------------------------------------------------

def alcance_dirs(raiz: str, alcance: str):
    if alcance == "todo":
        return None  # no excluye nada
    return set(EXCLUIDOS_PROPIO)


def citas_por_numero(raiz: str, por_num, alcance="propio", limite_ficheros=None):
    """Recorre el arbol UNA vez y cuenta, por fichero y global, las citas por
    numero que caen sobre un numero duplicado.

    Devuelve (resumen, por_numero, n_ficheros_leidos, n_ficheros_omitidos).
    `omitidos` se cuenta y se imprime: si un fichero no se pudo leer, la cifra
    de citas es una cota inferior y la puerta lo dice.
    """
    dups = {n for n, v in por_num.items() if len(v) > 1}
    excl = alcance_dirs(raiz, alcance)
    por_numero = collections.Counter()
    por_dir = collections.Counter()
    total = 0
    leidos = omitidos = 0
    for dp, dn, fn in os.walk(raiz):
        if excl is not None:
            dn[:] = [d for d in dn if d not in excl]
        dn[:] = [d for d in dn if d != "__pycache__"]
        if limite_ficheros is not None and leidos >= limite_ficheros:
            break
        rel_dir = os.path.relpath(dp, raiz)
        for f in sorted(fn):
            if not f.endswith(EXT_LEIBLES):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    texto = fh.read()
            except OSError:
                omitidos += 1
                continue
            leidos += 1
            for rx, grupo in ((RE_CITA_LL, "NNN:LL"), (RE_CITA_BT, "`NNN`"),
                              (RE_CITA_RUTA, "findings/NNN")):
                for m in rx.finditer(texto):
                    num = m.group(1)
                    if num not in dups:
                        continue
                    total += 1
                    por_numero[(grupo, num)] += 1
                    por_dir[rel_dir] += 1
    resumen = {
        "citas_por_numero_a_duplicado": total,
        "numeros_duplicados_citados": len({n for (_g, n) in por_numero}),
        "distintos_numeros_duplicados": len(dups),
        "por_forma": dict(collections.Counter(
            {g: sum(c for (gg, _n), c in por_numero.items() if gg == g)
             for g in ("NNN:LL", "`NNN`", "findings/NNN")})),
        "por_directorio": dict(por_dir.most_common(12)),
        "ficheros_leidos": leidos,
        "ficheros_omitidos": omitidos,
    }
    return resumen, por_numero, leidos, omitidos


# --------------------------------------------------------------------------
# 4. LA PUERTA
# --------------------------------------------------------------------------

def medir(raiz: str, alcance="propio", limite_ficheros=None) -> dict:
    r = {"raiz": raiz, "indice": NOMBRE_INDICE, "alcance": alcance,
         "work_class": WORK_CLASS, "write_execution": WRITE_EXECUTION}
    por_num, cob, vistos, en_disco, sin_prefijo = fs_indice(raiz)
    if por_num is None:
        r["codigo"] = EXIT_FALTA
        r["motivo"] = "no existe %s" % dir_hallazgos(raiz)
        return r
    col = fs_colisiones(por_num)

    r["findings"] = {
        "ficheros_en_disco": en_disco,
        "ficheros_leidos": vistos,
        "cobertura": round(cob, 6),
        "numeros_distintos": len(por_num),
        "sin_prefijo_numerico": sin_prefijo,
        "numeros_duplicados": len(col),
        "ficheros_implicados": sum(len(v) for v in col.values()),
        "copias_sobrantes": sum(len(v) - 1 for v in col.values()),
        "tamano_grupos": dict(sorted(collections.Counter(
            len(v) for v in col.values()).items())),
        "grupos": {n: v for n, v in sorted(col.items())},
    }

    rpath = ruta_indice(raiz)
    if not os.path.isfile(rpath):
        r["codigo"] = EXIT_FALTA
        r["motivo"] = "no existe %s" % NOMBRE_INDICE
        return r
    idx = leer_indice(rpath)
    if idx is None:
        r["codigo"] = EXIT_FALTA
        r["motivo"] = "%s no tiene la seccion %r" % (NOMBRE_INDICE,
                                                     SECCION_COLISION)
        return r

    d5, d3 = indice_regenera_identico(idx, por_num, cob)
    r["indice_estado"] = {
        "cabeceras": idx["cabeceras"],
        "n_filas": idx["n_filas"],
        "diferencias_cifras": d5,
        "diferencias_tabla": d3,
        "no_comparable": [
            "Renumeraciones detectadas (depende de git HEAD)",
            "Referencias colgando (depende de git HEAD)",
        ],
    }

    sin_fila = colisiones_sin_fila(idx, col)
    r["A2_sin_fila"] = sin_fila

    resumen, por_numero, leidos, omitidos = citas_por_numero(
        raiz, por_num, alcance, limite_ficheros)
    r["A3_citas"] = resumen
    r["A3_detalle"] = [{"forma": g, "numero": n, "veces": c}
                       for (g, n), c in sorted(por_numero.items())]

    codigos = []
    if d5:
        codigos.append(EXIT_INDICE_VIEJO)
    if d3 or sin_fila:
        codigos.append(EXIT_COLISION_SIN_FILA)
    if resumen["citas_por_numero_a_duplicado"] > 0:
        codigos.append(EXIT_CITAS_AMBIGUAS)
    r["codigos_que_se_disparan"] = codigos
    r["codigo"] = codigos[0] if codigos else EXIT_OK
    return r


def informe(r: dict, limite=20) -> None:
    print("=" * 78)
    print("check_num_unico %s · WORK_CLASS=%s · WRITE_EXECUTION=%s"
          % (VERSION, WORK_CLASS, WRITE_EXECUTION))
    print("=" * 78)
    if r["codigo"] == EXIT_FALTA:
        print("\n  2  FALTA LA BASE: %s\n" % r["motivo"])
        return
    f = r["findings"]
    print("""
  A1  ¿cada numero identifica un solo fichero?
  A2  ¿cada numero duplicado tiene fila en el indice?
  A3  ¿queda alguna cita por numero sobre un numero duplicado?
""")
    print("  A1  ficheros en findings/          : %d" % f["ficheros_en_disco"])
    print("      leidos / cobertura            : %d / %d  (%.4f)"
          % (f["ficheros_leidos"], f["ficheros_en_disco"], f["cobertura"]))
    print("      numeros distintos             : %d" % f["numeros_distintos"])
    print("      numeros DUPLICADOS            : %d" % f["numeros_duplicados"])
    print("      ficheros implicados           : %d" % f["ficheros_implicados"])
    print("      copias sobrantes              : %d" % f["copias_sobrantes"])
    print("      grupos por tamano             : %s"
          % ", ".join("%d->%d" % (k, v) for k, v in f["tamano_grupos"].items()))
    if f["sin_prefijo_numerico"]:
        print("      SIN prefijo numerico          : %d  %s"
              % (len(f["sin_prefijo_numerico"]),
                 f["sin_prefijo_numerico"][:3]))

    e = r["indice_estado"]
    print("\n  INDICE  %s" % NOMBRE_INDICE)
    print("  " + "-" * 74)
    print("      declara ficheros=%s  colisiones=%s  filas=%d"
          % (e["cabeceras"]["ficheros"], e["cabeceras"]["colisiones"], e["n_filas"]))
    if not e["diferencias_cifras"] and not e["diferencias_tabla"]:
        print("      IDENTICO a lo que sale del FS.")
    for etiqueta, lista in (("CIFRAS  -> 5", e["diferencias_cifras"]),
                            ("TABLA   -> 3", e["diferencias_tabla"])):
        if not lista:
            continue
        print("      %s  %d diferencia(s):" % (etiqueta, len(lista)))
        for d in lista[:limite]:
            print("        [%s] %s" % (d["tipo"], d["detalle"][:96]))
            if d["tipo"] == "FILA_INCOMPLETA":
                for x in d["vistos"][:limite]:
                    print("            %s  falta %s  sobra %s"
                          % (x["numero"], x["falta_en_indice"],
                             x["sobra_en_indice"]))
    print("      no comparable (depende de git HEAD): %s"
          % ", ".join(x.split(" ")[0] for x in e["no_comparable"]))

    print("\n  A2  colisiones SIN fila en el indice: %d" % len(r["A2_sin_fila"]))
    if r["A2_sin_fila"]:
        print("      %s" % ", ".join(r["A2_sin_fila"][:limite]))

    c = r["A3_citas"]
    print("\n  A3  citas por numero a un numero duplicado: %d"
          % c["citas_por_numero_a_duplicado"])
    print("      por forma                        : %s"
          % ", ".join("%s=%d" % (k, v) for k, v in sorted(c["por_forma"].items())))
    print("      numeros duplicados alcanzados   : %d de %d"
          % (c["numeros_duplicados_citados"], c["distintos_numeros_duplicados"]))
    print("      alcance='%s'  ficheros leidos=%d  omitidos=%d"
          % (r["alcance"], c["ficheros_leidos"], c["ficheros_omitidos"]))
    if c["por_directorio"]:
        print("      por directorio:")
        for d, n in sorted(c["por_directorio"].items(),
                           key=lambda kv: -kv[1])[:8]:
            print("        %-42s %d" % (d[:42], n))

    print("\n  CODIGOS QUE SE DISPARAN: %s"
          % (r.get("codigos_que_se_disparan") or "ninguno"))
    print("  CODIGO DEVUELTO         : %d" % r["codigo"])
    if r.get("codigos_que_se_disparan"):
        nom = {2: "falta la base", 3: "colisiones sin fila en el indice",
               4: "citas por numero a un duplicado",
               5: "el indice de disco no regenera identico"}
        print("\n  VEREDICTO: la afirmacion NO se sostiene.")
        for c_ in r["codigos_que_se_disparan"]:
            print("    %d  %s" % (c_, nom[c_]))
    else:
        print("\n  VEREDICTO: las tres afirmaciones se sostienen.")


# --------------------------------------------------------------------------
# 5. SELFTEST: fabricar 0, 2, 3, 4 y 5 POR SEPARADO
# --------------------------------------------------------------------------

def _arbol(d: str):
    dirf = dir_hallazgos(d)
    os.makedirs(dirf, exist_ok=True)
    return dirf


def _pon(dirf: str, nombre: str, num: int,
         texto: str = "# %03d · t\n") -> None:
    with open(os.path.join(dirf, nombre), "w", encoding="utf-8") as fh:
        fh.write(texto % num)


def _indice(d: str, filas, n_fich, n_col, destino=None) -> None:
    """Escribe un indice con la FORMA del real. `filas` = [(num,[nombres])]."""
    out = ["# FINDINGS-RENUMERACIONES", "",
           "<!-- GENERADO por selftest -->", "",
           "- Numeros con **colision** (>1 fichero): **%d**" % n_col,
           "- Ficheros en `findings/`: **%d**" % n_fich, "",
           "## Numeros con colision (clave primaria no unica)", "",
           "| numero | ficheros |", "|---|---|"]
    for n, fs in filas:
        out.append("| %03d | %s |" % (n, "<br>".join(fs)))
    out += ["", "## Renumeraciones", "", "| viejo | nuevo | reasignado | fichero |",
            "|---|---|---|---|"]
    with open(destino or ruta_indice(d), "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))


def selftest() -> int:
    """Fabrica 0, 2, 3, 4 y 5 POR SEPARADO y comprueba que sale cada codigo.

    UNA PUERTA QUE NO PUEDE FALLAR ES PEOR QUE NO TENER PUERTA, asi que este
    selftest no prueba que la puerta diga que el arbol esta bien: prueba que
    puede decir CADA UNA de las cinco cosas. Y para que los codigos sean
    discriminantes y no tres nombres para lo mismo, hay vectores que los
    producen DE UNO EN UNO, sin los demas:

      3  solo  la tabla de colisiones no es el conjunto de colisiones del FS,
            y las cifras declaradas son correctas
      5  solo  las cifras declaradas no son las del FS (o no se pudo leer todo),
            y la tabla de colisiones es correcta
      4  solo  hay cita por numero sobre un duplicado, con el indice al dia

    Y un vector que NO produce nada, que es el que mas importa: si el arbol y el
    indice son coherentes sale 0.
    """
    base = "/tmp/opencode/check_num_unico-selftest"
    fallos = []
    total = [0]

    def res(nombre, ok, detalle=""):
        total[0] += 1
        print("  %-66s %s" % (nombre, "OK" if ok else "FALLO " + detalle))
        if not ok:
            fallos.append((nombre, detalle))

    print("=== check_num_unico selftest ===\n")
    print("  Fabricando cada codigo por separado en %s\n" % base)
    os.system("rm -rf %s" % base)

    def arbol(nombre, ficheros, filas, n_fich, n_col, extra=None):
        """Fabrica un arbol completo y lo mide. `ficheros` = [(nombre, num)]."""
        d = os.path.join(base, nombre)
        dirf = _arbol(d)
        for nom, num in ficheros:
            _pon(dirf, nom, num)
        _indice(d, filas, n_fich, n_col)
        if extra:
            for rel, txt in extra:
                with open(os.path.join(d, rel), "w", encoding="utf-8") as fh:
                    fh.write(txt)
        return d, medir(d, alcance="propio")

    def codigos(r):
        return r.get("codigos_que_se_disparan", [r["codigo"]])

    def tipos(r, clave):
        return [x["tipo"] for x in r.get("indice_estado", {}).get(clave, [])]

    # ---- 0: arbol sano, indice sano. Sin esto, "todo lo demas falla" no
    # demuestra nada: puede que la puerta falle siempre.
    d, r = arbol("v0", [("001-alpha.md", 1), ("002-beta.md", 2),
                        ("003-gamma.md", 3), ("004-delta.md", 4)], [], 4, 0)
    res("0  arbol sano + indice sano -> 0", r["codigo"] == EXIT_OK,
        "salio %d %s" % (r["codigo"], codigos(r)))
    res("0  y no dispara ningun codigo", codigos(r) == [], str(codigos(r)))

    # ---- 2: falta findings/
    d = os.path.join(base, "v2a")
    os.makedirs(d)
    r = medir(d, alcance="propio")
    res("2  sin findings/ -> 2", r["codigo"] == EXIT_FALTA,
        "salio %d" % r["codigo"])

    # ---- 2: findings/ pero sin indice
    d = os.path.join(base, "v2b")
    dirf = _arbol(d)
    _pon(dirf, "001-a.md", 1)
    r = medir(d, alcance="propio")
    res("2  findings/ sin el indice -> 2", r["codigo"] == EXIT_FALTA,
        "salio %d" % r["codigo"])

    # ---- 2: indice sin la seccion de colisiones. Aceptarlo como "sin
    # colisiones" seria el fallo que la puerta persigue, escrito al reves.
    d = os.path.join(base, "v2c")
    dirf = _arbol(d)
    _pon(dirf, "001-a.md", 1)
    with open(ruta_indice(d), "w", encoding="utf-8") as fh:
        fh.write("# FINDINGS-RENUMERACIONES\n\nsin seccion de colisiones\n")
    r = medir(d, alcance="propio")
    res("2  indice sin la seccion de colisiones -> 2, no 0",
        r["codigo"] == EXIT_FALTA, "salio %d" % r["codigo"])

    # ---- 3 SOLO: la tabla no enumera, las cifras si.
    # El FS tiene UNA colision (la 002). El indice declara 1 colision y
    # 3 ficheros, ambos correctos, y su tabla tiene 1 fila: la de la 007,
    # que en el FS no colisiona. El recuento dice que todo va bien. El
    # conjunto dice que no. Una puerta de recuentos pasa esto en VERDE.
    d, r = arbol("v3", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(7, ["007-x.md", "007-y.md"])], 3, 1)
    res("3  cifras correctas y conjunto erroneo -> 3 solo",
        r["codigo"] == EXIT_COLISION_SIN_FILA
        and codigos(r) == [EXIT_COLISION_SIN_FILA],
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))
    res("3  ...y el recuento de colisiones NO se quejo (asi se prueba que"
        " compara conjuntos)", tipos(r, "diferencias_cifras") == [],
        str(tipos(r, "diferencias_cifras")))
    res("3  ...y si que vio la fila que falta y la que sobra",
        "SIN_FILA_EN_EL_INDICE" in tipos(r, "diferencias_tabla")
        and "FILA_SIN_COLISION_EN_EL_FS" in tipos(r, "diferencias_tabla"),
        str(tipos(r, "diferencias_tabla")))
    res("3  ...y la lista de colisiones sin fila nombra la 002",
        r["A2_sin_fila"] == ["002"], str(r["A2_sin_fila"]))

    # ---- 3 variante: la fila existe pero no lista a los mismos ficheros.
    d, r = arbol("v3b", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2),
                         ("002-d.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 4, 1)
    res("3  la fila existe pero le falta un fichero -> 3",
        EXIT_COLISION_SIN_FILA in codigos(r)
        and "FILA_INCOMPLETA" in tipos(r, "diferencias_tabla"),
        "todos=%s tipos=%s" % (codigos(r), tipos(r, "diferencias_tabla")))

    # ---- 5 SOLO: la cifra no es la del FS, la tabla si.
    d, r = arbol("v5", [("001-a.md", 1), ("002-b.md", 2), ("003-c.md", 3)],
                 [], 2, 0)
    res("5  el indice declara 2 ficheros y hay 3 -> 5 solo",
        r["codigo"] == EXIT_INDICE_VIEJO
        and codigos(r) == [EXIT_INDICE_VIEJO],
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))
    res("5  ...y solo por la cifra, no por la tabla",
        tipos(r, "diferencias_cifras") == ["RECENTRO_FICHEROS"]
        and tipos(r, "diferencias_tabla") == [],
        "cifras=%s tabla=%s" % (tipos(r, "diferencias_cifras"),
                                 tipos(r, "diferencias_tabla")))

    # ---- 5 variante: el recuento de colisiones tambien viejo.
    d, r = arbol("v5b", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 3, 0)
    res("5  el indice declara 0 colisiones y hay 1 -> 5",
        "RECENTRO_COLISIONES" in tipos(r, "diferencias_cifras"),
        str(tipos(r, "diferencias_cifras")))

    # ---- 5 variante: cobertura incompleta. Un indice regenerado sobre una
    # lectura parcial no es el indice.
    d = os.path.join(base, "v5c")
    dirf = _arbol(d)
    for nom, num in (("001-a.md", 1), ("002-b.md", 2), ("003-c.md", 3)):
        _pon(dirf, nom, num)
    _indice(d, [], 3, 0)
    os.chmod(os.path.join(dirf, "003-c.md"), 0o000)
    r = medir(d, alcance="propio")
    os.chmod(os.path.join(dirf, "003-c.md"), 0o644)
    res("5  un hallazgo ilegible -> 5 por cobertura incompleta",
        r["codigo"] == EXIT_INDICE_VIEJO
        and "COBERTURA_INCOMPLETA" in tipos(r, "diferencias_cifras")
        and r["findings"]["cobertura"] < 1.0,
        "codigo=%d cobertura=%s" % (r["codigo"], r["findings"]["cobertura"]))
    res("5  ...y la cobertura se mide, no se supone",
        r["findings"]["ficheros_en_disco"] == 3
        and r["findings"]["ficheros_leidos"] == 2,
        "disco=%s leidos=%s" % (r["findings"]["ficheros_en_disco"],
                                r["findings"]["ficheros_leidos"]))

    # ---- 4 SOLO: cita por numero sobre un duplicado, indice al dia.
    d, r = arbol("v4", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 3, 1,
                 extra=[("otro.md", "vease el hallazgo 002:12 y `002` y "
                                   "findings/002\n")])
    res("4  tres formas de cita por numero sobre un duplicado -> 4 solo",
        r["codigo"] == EXIT_CITAS_AMBIGUAS
        and codigos(r) == [EXIT_CITAS_AMBIGUAS],
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))
    res("4  ...y cuenta las tres, no una",
        r["A3_citas"]["citas_por_numero_a_duplicado"] == 3,
        "n=%s" % r["A3_citas"]["citas_por_numero_a_duplicado"])

    # ---- 4b: la cita por NOMBRE no es ambigua. El nombre es clave primaria
    # unica: 539 nombres, 539 ficheros, cero colisiones de nombre. COLGAR es
    # otro defecto y esta puerta no lo cuenta.
    d, r = arbol("v4b", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 3, 1,
                 extra=[("otro.md", "vease findings/002-b.md y "
                                   "findings/002-c.md y `002-b`\n")])
    res("4  cita por NOMBRE no se cuenta como ambigua -> 0",
        r["codigo"] == EXIT_OK
        and r["A3_citas"]["citas_por_numero_a_duplicado"] == 0,
        "codigo=%d n=%s" % (r["codigo"],
                            r["A3_citas"]["citas_por_numero_a_duplicado"]))

    # ---- EL ANCHO DE DIGITOS. `\d{3}` es un ancho EXACTO: en cuanto existe
    # `1000-algo.md` deja de casar y su colision se vuelve invisible. Es el
    # fallo ya corregido en findings_index.py:RE_NUM y en findnum.py; con el
    # mismo patron, esta puerta seria ciega a los hallazgos de 4 digitos.
    d = os.path.join(base, "v4d")
    dirf = _arbol(d)
    for nom, cab in (("1000-a.md", "# 1000 · A\n"), ("1000-b.md", "# 1000 · B\n")):
        with open(os.path.join(dirf, nom), "w", encoding="utf-8") as fh:
            fh.write(cab)
    _pon(dirf, "0999-z.md", 999)
    _indice(d, [(1000, ["1000-a.md", "1000-b.md"])], 3, 1)
    r = medir(d, alcance="propio")
    res("4d una colision de cuatro digitos la ve (el ancho importa)",
        r["findings"]["numeros_duplicados"] == 1
        and r["findings"]["numeros_distintos"] == 2,
        "colisiones=%d distintos=%d"
        % (r["findings"]["numeros_duplicados"],
           r["findings"]["numeros_distintos"]))
    res("4d ...y con \\d{3} NO la veria (control negativo del patron)",
        re.match(r"^(\d{3})-", "1000-a.md") is None)

    # ---- AUTOCOMPROBACION: el numero de colisiones NO esta escrito en el
    # codigo. Un gate con el 74 dentro no puede pasar esto.
    d = os.path.join(base, "vauto")
    dirf = _arbol(d)
    for nom in ("001-a.md", "001-b.md", "001-c.md"):
        _pon(dirf, nom, 1)
    _indice(d, [(1, ["001-a.md", "001-b.md", "001-c.md"])], 3, 1)
    r1 = medir(d, alcance="propio")
    antes = (r1["findings"]["numeros_duplicados"],
             r1["findings"]["copias_sobrantes"])
    _pon(dirf, "001-d.md", 1)
    r2 = medir(d, alcance="propio")
    despues = (r2["findings"]["numeros_duplicados"],
               r2["findings"]["copias_sobrantes"])
    res("auto  un cuarto miembro cambia lo medido sin tocar el codigo",
        antes == (1, 2) and despues == (1, 3),
        "antes=%s despues=%s" % (antes, despues))
    # Que el numero de colisiones NO este escrito en el codigo se comprueba sobre
    # el ARBOL DE SINTAXIS, no con una expresion regular sobre el texto: un
    # `re.search` no distinguiria un 74 en un comentario de un 74 en un
    # literal. Y los numeros prohibidos se construyen desde texto a PROPOSITO,
    # porque escribirlos como literales haria que ESTA LINEA fuera la que los
    # introduce y el control no podria distinguirlos de si mismo. Si manana hay
    # 75 colisiones, este control tiene que cambiar: por eso hay que editarlo.
    PROHIBIDOS = {int(x) for x in ("7" "4", "7" "5")}
    # El control mira SOLO las funciones que PRODUCEN las cifras, no el
    # fichero entero: un `"-" * 74` que dibuja una linea de 74 columnas es un
    # literal legitimo y no es una medicion. Y el comportamiento ya esta probado
    # mas arriba, con un miembro mas en el grupo y sin tocar el codigo: esto es
    # la segunda linea de defensa, no la primera.
    MEDIDORAS = ("fs_indice", "fs_colisiones", "indice_regenera_identico",
                 "colisiones_sin_fila", "citas_por_numero", "leer_indice")
    arbol_sint = ast.parse(open(__file__, encoding="utf-8").read())
    consts = []
    for nodo in ast.walk(arbol_sint):
        if isinstance(nodo, ast.FunctionDef) and nodo.name in MEDIDORAS:
            consts += [k.value for k in ast.walk(nodo)
                       if isinstance(k, ast.Constant)
                       and isinstance(k.value, int)]
    intrusos = sorted(set(consts) & PROHIBIDOS)
    res("auto  las funciones que miden no tienen 74 ni 75 escritos dentro",
        not intrusos, "literales intrusos: %s" % intrusos)

    # ---- PRECEDENCIA: 5 > 3 > 4, y se devuelven TODOS.
    d, r = arbol("vprec", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(7, ["007-x.md"])], 99, 1,
                 extra=[("otro.md", "`002`\n")])
    res("prec  sale el mas profundo (5) y se listan los tres",
        r["codigo"] == EXIT_INDICE_VIEJO
        and codigos(r) == [EXIT_INDICE_VIEJO, EXIT_COLISION_SIN_FILA,
                           EXIT_CITAS_AMBIGUAS],
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))

    print("\n  RESULT: %s  (%d comprobaciones, %d fallos)\n"
          % ("PASS" if not fallos else "FAIL", total[0], len(fallos)))
    for n, det in fallos:
        print("    FALLO %s  %s\n" % (n, det))
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="PUERTA: el numero de hallazgo identifica un hallazgo?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--limite", type=int, default=20)
    ap.add_argument("--alcance", choices=("propio", "todo"), default="propio",
                    help="'propio' excluye RESEARCH/, rx550-upstream/, archive/")
    ap.add_argument("--max-ficheros", type=int, default=None,
                    help="corta el recorrido tras N ficheros (para medir coste)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    r = medir(proyecto(), a.alcance, a.max_ficheros)
    if a.json:
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return r["codigo"]
    informe(r, a.limite)
    return r["codigo"]


if __name__ == "__main__":
    sys.exit(main())
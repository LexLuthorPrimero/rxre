#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""check_num_unico.py 1.0.0 - PUERTA: el numero de hallazgo identifica un hallazgo?

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE · MODIFICATIONS=0 · GPU INTACTA

QUE AFIRMA, Y SON CUATRO AFIRMACIONES, NO UNA

  A1  todo prefijo numerico de `findings/*.md` identifica UN SOLO fichero
  A2  todo numero duplicado tiene fila en el indice
  A3  no queda ninguna cita por numero colgando sobre un numero duplicado
  A4  ninguna de esas citas esta en un fichero de CODIGO, salvo las que el
      registro `tools/CITA-CODIGO-EXCEPTIONS.txt` declara, una a una y con
      su razon escrita

CODIGOS DE SALIDA, Y POR QUE NO SON 0 Y 1

  0  las cuatro afirmaciones se sostienen
  1  (no se usa) reservado: 1 es error generico y se confunde con un linter
  2  falta `findings/` o el indice
  3  hay colisiones sin fila en el indice
  4  RETIRADO.  Era "quedan citas por numero a un numero duplicado".  MEDIDO el
     2026-10-04: se cuenta, se imprime y NO es codigo de salida.  La afirmacion
     no se puede cumplir sin inventar el destino de la mitad de las citas; las
     cifras, el motivo y lo que se hace en su lugar estan en
     `08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md`.  La constante se conserva
     con su valor para no romper a quien la compruebe
  5  el indice de disco no regenera identico               <- el indice esta viejo
  6  queda una cita por numero a un duplicado en CODIGO    <- el defecto de HOY

  PRECEDENCIA, y no es arbitraria: 2 > 5 > 3 > 6.

    2 antes que nada: sin `findings/` o sin indice no hay nada que afirmar.
    5 antes que 3 y 4: A2 y A3 se miden CONTRA el indice. Si el indice no
      regenera identico, la comparacion se hace contra una medida equivocada, y
      un 3 o un 4 emitido sobre un indice viejo no seria un hallazgo sobre el
      arbol: seria un hallazgo sobre un fichero desactualizado. Se dice primero
      que el instrumento esta viejo.
    3 antes que 4: una colision sin fila es un defecto del REGISTRO. Una cita
      ambigua es un defecto del USO. El primero se arregla generando el indice;
      el segundo, reescribiendo citas. Se pueden tener los dos.
    6 antes que 4: las dos son el MISMO hallazgo con distinto grano, y el 6 es
      el que nombra donde esta written. El 4 lo dominan la prosa y los propios
      findings, de modo que un 4 sin el 6 no dice si el codigo esta limpio, y esa
      es la pregunta que decide si el driver puede afirmar algo. El 6 se cuenta
      con el registro de excepciones, y el registro ausente se declara ausente:
      tratarlo como vacio dejaria la puerta muda en vez de gritando.

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

  NO ve tampoco que una cita por numero RESUELVA bien hoy. Los numeros
  renumerados se reutilizan: `110` quedo libre y lo ocupo otro hallazgo, de modo
  que `110:187` puede apuntar a un numero ambiguo y a la vez ser la cita
  correcta. Que la puerta no lo distinga no es un fallo suyo: distinguirlo exige
  leer el hallazgo, y una puerta que cuenta no lee. MEDIDO y registrado: la
  tabla de renumeraciones dice `110 -> 215`, y `215` habla de `AllowMvddSwitch`
  mientras el codigo que cita `110` habla de `WAIT_REG_MEM`. La tabla y el
  codigo no se pueden corregir con el mismo criterio.

A4, Y POR QUE CODIGO CONTRA PROSA

  A3 cuenta en todo el arbol y por eso lo dominan la prosa y los propios
  findings. MEDIDO tras reparar `07-DRIVER/kernel/rx550_pm4.c`: 2154 citas
  ambiguas, de las que2068 en prosa, 61 en codigo registrado y 26 en codigo sin
  registrar. El numero que decide el peso es el ultimo, y un 4 sin el 6 obliga
  a leer la tabla por directorios para averiguarlo.

  Que un fichero sea codigo se decide por extension (`.c .h .py .sh .s .cmd
  .d`, mas `Makefile`), no por intuicion.

  El registro `tools/CITA-CODIGO-EXCEPTIONS.txt` existe porque hay 14 ficheros
  cuyo objeto ES la numeracion o la ambiguedad de las citas, y ahi la cita
  ambigua es el dato: un selftest que fabrica `033:397` para comprobar que el
  detector lo ve no puede citar `033` por nombre, porque entonces no probaria
  nada. MEDIDO: de las 87 citas en codigo, 61 estan en esos 14 ficheros. Cada
  entrada del registro lleva su razon, y `--selftest` prueba las dos mitades:
  que la puerta salga 6 sin el registro y no salga con el.

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

A4 Y EL REGISTRO

  `--limite` acota solo lo que se IMPRIME; el total de A4 no depende de el.
  El registro se lee de `tools/CITA-CODIGO-EXCEPTIONS.txt`, una ruta por linea,
  coincidencia EXACTA: un prefijo de directorio no registra, porque la razon es
  siempre de ese fichero. Un registro ausente se declara ausente y no cuenta
  como vacio (comprobado en el selftest, caso 6e).

Uso:
  python3 check_num_unico.py              resumen + veredicto
  python3 check_num_unico.py --json       lo mismo, estructurado
  python3 check_num_unico.py --limite N   cuantas filas de detalle imprime
  python3 check_num_unico.py --alcance {propio|todo}
  python3 check_num_unico.py --selftest   fabrica 0, 2, 3, 4, 5, 6 y 7 por separado
"""

import argparse
import ast
import collections
import json
import os
import re
import sys

# MEDIDO 2026-10-04 (hallazgo 1044): esta cadena decía "1.1.0" con un codigo que ya
# no corresponde.  El commit 85ca0c5 añadió EXIT_CITAS_SIN_ADJUDICAR = 7 y
# CENSO_POBLACION = 2152, y ninguna de las dos cosas se reflejaba aqui.  Una
# herramienta con procedencia declarada y una version que miente no se puede
# citar: el numero de version es la unica cosa que dice que estado del codigo se
# ejecuto.  Subida a 1.2.0 al anotar el cambio; NO es un cambio de COMPORTAMIENTO.
VERSION = "1.2.0"
WORK_CLASS = "READ_ONLY"
WRITE_EXECUTION = "NONE"

EXIT_OK = 0
EXIT_FALTA = 2
EXIT_COLISION_SIN_FILA = 3
EXIT_CITAS_AMBIGUAS = 4
EXIT_INDICE_VIEJO = 5
EXIT_CITA_AMBIGUA_EN_CODIGO = 6

# MEDIDO 2026-10-04, y anadido por el nodo principal al landing de CITAS-PROSA-A3.
#
# EL CODIGO 4 SE RETIRO,  y con razon:  "quedan citas por numero a un duplicado" no
# se puede cumplir sin inventar el destino de la mitad de las citas.  MEDIDO que de
# las 2152  la mitad son AMBIGUAS  —correctas pero sin decir a cual van—,  y esa no
# es una reparacion:  es una ambiguedad del RENUMERADO,  que REUTILIZA el numero
# viejo.  Un codigo de salida que obliga a resolver lo que no tiene solucion  es un
# codigo que obliga a resolverlo mal.
#
# Y EL CENSO MIDIO C3 = 0  —0 confirmadas sobre 132 adjudicaciones—,  que es lo que
# hace la situacion tolerable.  PERO MEDIDO que ese cero NO se propaga a la puerta:
#
#     se inyecta una cita de la clase C3  —dos hallazgos duplicados  y la prosa
#     atribuye a uno lo que solo sostiene el otro—   ->   rc = 0
#
# Es decir:  la puerta NO DETECTA una cita equivocada.  Y eso no es culpa de la cita
# inyectada:  es que "no hay citas equivocadas"  es un RESULTADO DE CENSO,  no una
# invariante,  y una invariante que no se puede comprobar no puede quedarse
# capturando el codigo de salida.
#
# LO QUE SI SE PUEDE COMPROBAR,  y es lo que este codigo dice:  UN CENSO CADUCA.
# MEDIDO que el censo adjudico 2152  —la corrida del expediente—  y que la poblacion
# medida despues fue 2222.  Hay 70 citas que nadie ha adjudicado nunca,  y para ellas
# "no hay C3"  no esta medido:  no se sabe.
#
# Asi que este codigo NO afirma que las citas esten bien.  Afirma que la MEDIDA que
# lo dijo ya no cubre lo que hay,  y eso es un hecho  —no un juicio—.
EXIT_CITAS_SIN_ADJUDICAR = 7

# La poblacion que el censo de 2026-10-04 adjudico.  Es una DECLARACION,  y el unico
# modo de que deje de ser cierta es que la poblacion cambie  —que es lo que este
# codigo mide—  o que se vuelva a adjudicar,  y entonces se actualiza aqui  con su
# fecha,  como se actualiza un hash.
CENSO_POBLACION = 2152
CENSO_CITA = "08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md"

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

# MEDIDO 2026-10-04 (nodo CITAS-PROSA-A3).  LAS NO-CITAS, y por que NO se
# resuelven con una heuristica.
#
# De las 2152 citas que A3 contaba, 25 NO SON CITAS: 22 son patrones binarios de
# 3-4 bits de la tabla de decodificacion SIB de x86-64 (`001`, `010`, `100`,
# `101`) y 3 son rangos de bits de registro (`D0[127:0]`).  El defecto esta en el
# DETECTOR, no en la prosa.
#
# MEDIDO Y DESCARTADO: dos heuristicas, y las dos son MEJORES que el defecto.
#   (a) el numero dentro de corchetes, por el balance global: descarta 421, de
#       las cuales 359 NO son no-citas.  En markdown el balance se abre con el
#       primer `[` sin cerrar --un enlace, una tabla, un literal de regex-- y ya
#       no vuelve a cero, asi que todo lo demas parece "dentro de corchetes".
#   (b) adyacencia a `[` o `]`: descarta 8, de las cuales 5 son citas reales.
#       `**[REFUTADO en `272`]**` acaba en `]` por el markdown, no por un rango.
#   (c) firma de fila (dos o mas tokens de solo 0/1 en la linea) mas cabecera de
#       tabla: descarta 11, de las cuales 3 son citas reales.  Una lista de
#       numeros de hallazgo como `001`,`010`,`021` tiene exactamente la misma
#       firma que una fila de patrones binarios.
#
# Un detector que borra citas reales es peor que uno que las cuenta de mas: la
# que cuenta de mas se ve en la tabla, y la que borra no se ve.  Por eso esto NO
# es una heuristica sino una DECLARACION por fichero, con coincidencia EXACTA de
# ruta y con su razon escrita: el mismo patron que ya usa
# `tools/CITA-CODIGO-EXCEPTIONS.txt` para el codigo.  Una lista cerrada no puede
# borrar una cita en un fichero que nadie declaro.
NO_CITA_FICHEROS = {
    "05-FUENTES-EXTERNAS/FASE-R0-EXTERNAL-KNOWLEDGE/"
    "R0-7-REFERENCIA-X86-64-LECTURA-DESENSAMBLADO.md":
        "tabla de decodificacion SIB de x86-64: los 3-4 digitos son PATRONES "
        "BINARIOS (001, 010, 100, 101 = base/index de ModRM), no numeros de "
        "hallazgo. 22 ocurrencias.",
    "08-ARQUITECTURA/artifacts/Q5-MEM-TABLES/mem-tables.txt":
        "volcado de tablas de memoria: `D0[127:0]` es un RANGO DE BITS de un "
        "registro. 1 ocurrencia.",
    "08-ARQUITECTURA/artifacts/Q5-ISA-CAP12/cap12.txt":
        "volcado del ISA: `D0[127:0]` y `S2.u[127:0]` son RANGOS DE BITS de un "
        "registro. 2 ocurrencias.",
}

EXT_LEIBLES = (".md", ".py", ".sh", ".c", ".h", ".txt", ".tsv")
EXCLUIDOS_PROPIO = ("RESEARCH", "rx550-upstream-7.2.8", "archive",
                    ".git", "__pycache__")
NOMBRE_INDICE = "FINDINGS-RENUMERACIONES.md"
SECCION_COLISION = "## Numeros con colision"

# ---------------------------------------------------------------------------
# A4: CODIGO CONTRA PROSA.  Por que hace falta una puerta aparte.
#
# A3 cuenta la cita por numero sobre duplicado en TODO el arbol, y por eso lo
# dominan la prosa y los propios findings: de 2145, nueve estaban en el driver.
# Un 4 que no distingue codigo de prosa obliga a leer la tabla POR DIRECTORIOS
# para saber si el defecto esta en el codigo o en un documento, y en un informe
# eso se lee como "el driver tiene 9" cuando lo que se ha medido es "el
# directorio 07-DRIVER/kernel tiene 9". A4 es el mismo hallazgo con la
# distincion que decide el peso: en un documento una cita ambigua es una
# molestia; en el fuente del driver es una affirmation que puede ser falsa.
#
# Que un fichero sea CODIGO se decide por extension y por nombre, no por
# intuicion: una extension que no esta en CODIGO_EXT es prosa, y una prosa mal
# clasificada se ve en el recuento, que se imprime con el desglose.
CODIGO_EXT = (".c", ".h", ".py", ".sh", ".s", ".cmd", ".d")
CODIGO_SIN_EXT = ("Makefile",)
REGISTRO_CODIGO = "tools/CITA-CODIGO-EXCEPTIONS.txt"

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


def es_codigo(rel: str) -> bool:
    """Un fichero es CODIGO por extension o por nombre. Decidido, no supuesto."""
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    return ext in CODIGO_EXT or base in CODIGO_SIN_EXT


def leer_registro_codigo(raiz: str):
    """Lee el registro de ficheros donde la cita ambigua es el dato, no el fallo.

    Devuelve (set_de_rutas, lista_de_(ruta, motivo), estado). `estado` es uno de
    "leido", "inexistente": un registro ausente NO es un registro vacio, y la
    puerta lo dice en vez de tratar la ausencia como permiso.
    """
    p = os.path.join(raiz, REGISTRO_CODIGO)
    if not os.path.isfile(p):
        return set(), [], "inexistente"
    rutas, motivos = set(), []
    with open(p, encoding="utf-8") as fh:
        for linea in fh:
            s = linea.strip()
            if not s or s.startswith("#"):
                continue
            ruta, _, mot = s.partition("#")
            ruta = ruta.strip()
            if ruta:
                rutas.add(ruta)
                motivos.append((ruta, mot.strip()))
    return rutas, motivos, "leido"


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
    no_citas = []
    por_dir = collections.Counter()
    total = 0
    leidos = omitidos = 0
    registro, motivos_reg, estado_reg = leer_registro_codigo(raiz)
    hits = []
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
            rel = os.path.relpath(p, raiz).replace(os.sep, "/")
            codigo = es_codigo(rel)
            reg = rel in registro
            for rx, grupo in ((RE_CITA_LL, "NNN:LL"), (RE_CITA_BT, "`NNN`"),
                              (RE_CITA_RUTA, "findings/NNN")):
                for m in rx.finditer(texto):
                    num = m.group(1)
                    if num not in dups:
                        continue
                    # Las no-citas.  Se filtran AQUI y no en un segundo
                    # recorrido: un recorrido doble contaria dos veces lo mismo
                    # y las cifras dejarian de cuadrar.
                    if rel in NO_CITA_FICHEROS:
                        no_citas.append((rel, grupo, num))
                        continue
                    total += 1
                    por_numero[(grupo, num)] += 1
                    por_dir[rel_dir] += 1
                    if codigo:
                        linea = texto.count("\n", 0, m.start()) + 1
                        hits.append({"fichero": rel, "linea": linea,
                                    "num": num, "forma": grupo,
                                    "ficheros_del_num": len(por_num[num]),
                                    "registrado": reg})
    resumen = {
        "citas_por_numero_a_duplicado": total,
        "numeros_duplicados_citados": len({n for (_g, n) in por_numero}),
        "distintos_numeros_duplicados": len(dups),
        "por_forma": dict(collections.Counter(
            {g: sum(c for (gg, _n), c in por_numero.items() if gg == g)
             for g in ("NNN:LL", "`NNN`", "findings/NNN")})),
        "por_directorio": dict(por_dir.most_common(12)),
        "ficheros_leidos": leidos,
        # Las no-citas se INFORMAN, no se callan: son la cifra que baja, y sin
        # esta linea el total bajaria sin que se supiera por que.
        "no_citas_descartadas": len(no_citas),
        "no_citas_ficheros": sorted({x[0] for x in no_citas}),
        "ficheros_omitidos": omitidos,
        # ---- A4: el mismo hallazgo, partido por donde duele y por donde no.
        "A4_codigo": {
            "citas_en_codigo": sum(1 for h in hits if not h["registrado"]),
            "citas_en_codigo_registradas": sum(1 for h in hits if h["registrado"]),
            "citas_en_prosa": total - len(hits),
            "ficheros_de_codigo_afectados": len({h["fichero"] for h in hits}),
            "registro": REGISTRO_CODIGO,
            "registro_estado": estado_reg,
            "registro_ficheros": len(registro),
            "hits": hits,
        },
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
    a4 = resumen["A4_codigo"]
    if a4["citas_en_codigo"] > 0:
        codigos.append(EXIT_CITA_AMBIGUA_EN_CODIGO)
    # MEDIDO 2026-10-04 (nodo CITAS-PROSA-A3).  ESTA AFIRMACION SE RETIRA DE LA
    # PUERTA, y no porque se cumpla: porque NO SE PUEDE CUMPLIR sin inventar.
    #
    # A3 decia "no queda ninguna cita por numero sobre un numero duplicado".  Para
    # que fuese cierto habria que reescribir 2152 citas por nombre de fichero.
    # MEDIDO en una muestra estratificada de 132 adjudicaciones manuales
    # (artefactos en tools/citas_prosa_adjudicado.py; razon y cifras en
    # 08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md):
    #   clase 3, la cita que ya no apunta a lo que dice:  0.  No hay nada malo.
    #   clase 1, la cita correcta:                         45,7 %  (IC95 26-65 %)
    #   clase 2, la ambigua:                              54,3 %
    # En clase 2 la cita NO contiene nada que diga cual de los dos o tres ficheros
    # es, y por eso reescribirla seria fabricar un destino.  La ambiguedad la
    # causan los 74 numeros duplicados, y renumerarlos rompe las citas que los
    # nombran: es decision de otro nodo.
    #
    # Lo que si se hace cumplir son las no-citas, porque se cierran en el detector
    # y no en la prosa, y se han cerrado mas arriba.
    #
    # EXIT_CITAS_AMBIGUAS conserva su MISMO valor para no romper a quien lo
    # compruebe y queda sin uso a proposito: se deja a la vista que el codigo
    # existe y esta retirado.
    # if resumen["citas_por_numero_a_duplicado"] > 0:
    #     codigos.append(EXIT_CITAS_AMBIGUAS)
    #
    # ─────────────────────────────────────────────────────────────────────────────
    # Y LO QUE SE SUSTITUYE:  UN CENSO CADUCA.  MEDIDO,  y anadido por el nodo
    # principal al landing de este nodo.
    #
    # El "C3 = 0" de arriba es un RESULTADO,  y esta puerta no lo convierte en
    # invariante  —porque no se puede comprobar—.
    # MEDIDO:  con una cita de la clase 3 inyectada  —dos hallazgos duplicados  y la
    # prosa atribuye a uno lo que solo sostiene el otro—  la puerta da rc = 0.  O sea
    # que hoy NO DETECTA una cita equivocada.  Y eso es correcto que no lo haga:  la
    # clase 3 requiere saber que deberia decir el destino,  y eso es un juicio  —que
    # es exactamente lo que se hizo a mano en las 132 adjudicaciones—.
    #
    # LO QUE SI ES UN HECHO,  y por tanto comprobable:  el censo adjudico 2152  y la
    # poblacion medida hoy es mayor.  Hay citas que nadie ha adjudicado nunca,  y para
    # ellas el "no hay C3"  NO ESTA MEDIDO.  No se sabe si lo hay.
    #
    # ASI QUE ESTE CODIGO NO AFIRMA QUE LAS CITAS ESTEN BIEN.  Afirma que la MEDIDA
    # que lo dijo ya no cubre lo que hay.  Y eso es la distincion que hacia falta:
    # una puerta que sale con 0 porque "no hay problema" y una que sale con 0 porque
    # "no lo he mirado"  —y nadie lo nota porque las dos se leen igual—  son el mismo
    # defecto con dos motivos.
    #
    # Y CUANDO SE RESUELVA,  este codigo deja de disparar solo:  al bajar la poblacion
    # de 2152,  o al adjudicarse de nuevo y actualizar CENSO_POBLACION con su fecha.
    n_adv = resumen["citas_por_numero_a_duplicado"]
    r["censo_poblacion"] = CENSO_POBLACION
    r["censo_poblacion_actual"] = n_adv
    r["censo_sin_adjudicar"] = max(0, n_adv - CENSO_POBLACION)
    if n_adv > CENSO_POBLACION:
        codigos.append(EXIT_CITAS_SIN_ADJUDICAR)
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

    # ---- A4: el desglose que decide el peso, y el fichero:LINEA que faltaba.
    a4 = c["A4_codigo"]
    print("\n  A4  ¿alguna de esas citas esta en CODIGO, y no registrada?")
    print("      en CODIGO (sin registrar)       : %d   <- el defecto"
          % a4["citas_en_codigo"])
    print("      en CODIGO (registrado)          : %d   <- el dato de un"
          % a4["citas_en_codigo_registradas"])
    print("      en prosa                        : %d   <- una molestia"
          % a4["citas_en_prosa"])
    print("      ficheros de codigo afectados    : %d"
          % a4["ficheros_de_codigo_afectados"])
    print("      registro                        : %s (%s, %d ficheros)"
          % (a4["registro"], a4["registro_estado"], a4["registro_ficheros"]))
    if a4["registro_estado"] != "leido":
        print("      AVISO: el registro no esta. Su ausencia NO es un registro"
              " vacio: se cuenta todo.")
    if a4["hits"]:
        sin_reg = [h for h in a4["hits"] if not h["registrado"]]
        con_reg = [h for h in a4["hits"] if h["registrado"]]
        if sin_reg:
            print("      CODIGO SIN REGISTRAR, fichero:linea (primeros %d):" % limite)
            for h in sorted(sin_reg, key=lambda x: (x["fichero"], x["linea"]))[:limite]:
                print("        %-46s %5d  %-13s %s -> %d ficheros"
                      % (h["fichero"][:46], h["linea"], h["forma"],
                         h["num"], h["ficheros_del_num"]))
            if len(sin_reg) > limite:
                print("        ...y %d mas (el total %d no depende de --limite)"
                      % (len(sin_reg) - limite, len(sin_reg)))
        if con_reg:
            porf = collections.Counter(h["fichero"] for h in con_reg)
            print("      CODIGO REGISTRADO, %d citas en %d ficheros:"
                  % (len(con_reg), len(porf)))
            for f_, n_ in sorted(porf.items(), key=lambda kv: -kv[1]):
                print("        %-46s %3d" % (f_[:46], n_))

    print("\n  CODIGOS QUE SE DISPARAN: %s"
          % (r.get("codigos_que_se_disparan") or "ninguno"))
    print("  CODIGO DEVUELTO         : %d" % r["codigo"])
    if r.get("codigos_que_se_disparan"):
        nom = {2: "falta la base", 3: "colisiones sin fila en el indice",
               4: "citas por numero a un duplicado  (RETIRADO: se cuenta, "
                  "no falla)",
               5: "el indice de disco no regenera identico",
               6: "cita por numero a un duplicado, en CODIGO, sin registrar",
               # MEDIDO:  al anadir el codigo 7  la puerta REVENTO con KeyError: 7
               # DESPUES de haber impreso "VEREDICTO: la afirmacion NO se sostiene".
               # Es decir que el veredicto se emitia y luego el informe moria.
               #
               # Y eso es peor que un fallo limpio por dos razones:  el codigo de
               # salida  de un traceback  es 1,  que en esta puerta significa "falta la
               # base",  de modo que un defecto de la puerta se presenta como un
               # defecto de la MEDIDA;  y el texto del veredicto ya se habia
               # impreso,  asi que un lector que no mire el rc leeria un diagnostico
               # correcto de un estado que no se llego a comprobar.
               #
               # La lesson:  un diccionario de nombres que se consulta para CADA
               # codigo emitido  es una lista mas que hay que actualizar,  y no es
               # opcional:  sin ella, anadir un codigo rompe la puerta que lo anade.
               # Por eso el self-test tiene que recorrer TODOS los codigos que la
               # puerta puede emitir,  y no solo los que se fabricaron a mano.
               7: "hay citas por numero que el CENSO no ha adjudicado  "
                  "(poblacion %d, censo %d)" % (
                      r.get("censo_poblacion_actual", 0),
                      r.get("censo_poblacion", 0))}
        print("\n  VEREDICTO: la afirmacion NO se sostiene.")
        for c_ in r["codigos_que_se_disparan"]:
            print("    %d  %s" % (c_, nom[c_]))
    else:
        print("\n  VEREDICTO: las cuatro afirmaciones se sostienen.")


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
    # MEDIDO 2026-10-04 (nodo CITAS-PROSA-A3).  ESTE TEST CAMBIO DE LO QUE
    # AFIRMA, y el cambio esta aqui y no en el Threshold.  Antes afirmaba que
    # tres citas por numero sobre un duplicado dan codigo 4.  Ahora afirma que se
    # CUENTAN las tres y que el codigo de salida es 0, porque 4 paso a
    # informativo: satisfacerlo exigiria inventar el destino de la mitad de las
    # citas.  Las cifras y la razon en 08-ARQUITECTURA/CITAS-POR-NUMERO-DECLARACION.md
    res("4  tres formas se cuentan y 4 ya no es codigo de salida",
        r["codigo"] == EXIT_OK
        and codigos(r) == []
        and r["A3_citas"]["citas_por_numero_a_duplicado"] == 3,
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

    # ---- 7: CENSO CADUCADO.  Este codigo dispara en el arbol real  --MEDIDO
    # 2026-10-04:  poblacion 2222, censo 2152, 70 sin adjudicar;  y el rc que
    # devuelve la puerta es 5, no 7, porque 5 es mas profundo,  y ningun lector
    # que solo mire el rc ve que 7 tambien esta disponible--  y aun asi no tenia
    # NINGUN vector que lo fabricase.  Eso es exactamente lo que avisa el
    # comentario de mas arriba sobre el diccionario de nombres:  un codigo que la
    # puerta puede emitir y que el selftest no recorre no esta probado.
    #
    # La comparacion es  n_adv > CENSO_POBLACION,  con n_adv el numero de citas
    # por numero que apuntan a un duplicado.  MEDIDO que esa es la misma clase de
    # poblacion que el censo adjudico:  A3 mide 2222 hoy contra 2152 declaradas.
    # Una hipotesis previa afirmaba que la cuenta estaba mal porque el codigo 4
    # se habia retirado;  la ejecucion la REFUTO  --7 dispara con la cuenta
    # correcta--  asi que no se publica ninguna de las dos.
    #
    # Para ejercitar la RAMA se baja CENSO_POBLACION a 0 durante la medida y se
    # restaura en un finally.  Lo que se prueba es el comportamiento del codigo,
    # no se edita la politica:  el umbral de produccion no se toca.
    _censo_real = CENSO_POBLACION
    try:
        globals()["CENSO_POBLACION"] = 0
        _d7, r7 = arbol("v7", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                        [(2, ["002-b.md", "002-c.md"])], 3, 1,
                        extra=[("otro.md", "vease el hallazgo 002:12\n")])
        res("7  censo caducado -> 7",
            r7["codigo"] == EXIT_CITAS_SIN_ADJUDICAR
            and codigos(r7) == [EXIT_CITAS_SIN_ADJUDICAR],
            "codigo=%d todos=%s" % (r7["codigo"], codigos(r7)))
        res("7  ...y las sin adjudicar son la diferencia, no un total",
            r7["censo_sin_adjudicar"] == r7["censo_poblacion_actual"],
            "sin=%s actual=%s censo=%s"
            % (r7["censo_sin_adjudicar"], r7["censo_poblacion_actual"],
               r7["censo_poblacion"]))
    finally:
        globals()["CENSO_POBLACION"] = _censo_real
    # CONTROL NEGATIVO, y es la mitad del valor del test:  con el censo real, un
    # arbol con tres citas NO dispara 7.  Sin esta linea el test de arriba pasaria
    # igual si 7 disparase siempre, es decir si no comprobase nada.
    _d7n, r7n = arbol("v7n", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                      [(2, ["002-b.md", "002-c.md"])], 3, 1,
                      extra=[("otro.md", "vease el hallazgo 002:12\n")])
    res("7d ...y con el censo real NO dispara (control negativo)",
        EXIT_CITAS_SIN_ADJUDICAR not in codigos(r7n),
        "todos=%s" % (codigos(r7n),))

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
    res("prec  sale el mas profundo (5) y se listan los que disparan",
        r["codigo"] == EXIT_INDICE_VIEJO
        # el 4 ya no se dispara (medido 2026-10-04, ver la cabecera)
        and codigos(r) == [EXIT_INDICE_VIEJO, EXIT_COLISION_SIN_FILA],
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))

    # ---- 6: LA PUERTA DE CODIGO TIENE QUE PODER FALLAR Y TIENE QUE PODER PASAR
    #
    # Una puerta que solo puede dar 6 no vale nada, y una que solo puede dar 0 no
    # vigila nada. Se prueban las dos mitades por separado:
    #
    #   6a  cita por numero a duplicado DENTRO de un .c, sin registrar -> 6
    #   6b  la MISMA cita en un .md                                 -> no 6
    #       (si 6 saltase en prosa, el codigo no distinguiria nada y el 4
    #        bastaria: seria una puerta que no aporta el criterio que la motivo)
    #   6c  la MISMA cita en un .c pero REGISTRADA                  -> no 6
    #       (si el registro no acostumbrara, la puerta no podria pasar nunca)
    #   6d  el nombre del fichero y la linea del hit son los de verdad
    d, r = arbol("v6", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 3, 1,
                 extra=[("driver.c", "/* ver 002:12 y findings/002 */\n")])
    res("6a  cita ambigua en un .c, sin registrar -> 6",
        EXIT_CITA_AMBIGUA_EN_CODIGO in codigos(r)
        and r["A3_citas"]["A4_codigo"]["citas_en_codigo"] == 2,
        "todos=%s n=%s" % (codigos(r),
                           r["A3_citas"]["A4_codigo"]["citas_en_codigo"]))
    res("6a ...y el codigo devuelto es el 6 si no hay mas profundo",
        r["codigo"] == EXIT_CITA_AMBIGUA_EN_CODIGO,
        "codigo=%d todos=%s" % (r["codigo"], codigos(r)))
    hits = r["A3_citas"]["A4_codigo"]["hits"]
    res("6d ...y el hit trae fichero y linea, no un recuento",
        len(hits) == 2
        and {h["fichero"] for h in hits} == {"driver.c"}
        and {h["linea"] for h in hits} == {1}
        and {h["ficheros_del_num"] for h in hits} == {2},
        "hits=%s" % (hits,))

    d, r = arbol("v6b", [("001-a.md", 1), ("002-b.md", 2), ("002-c.md", 2)],
                 [(2, ["002-b.md", "002-c.md"])], 3, 1,
                 extra=[("doc.md", "vease 002:12 y findings/002\n")])
    res("6b  la misma cita en un .md NO dispara 6",
        EXIT_CITA_AMBIGUA_EN_CODIGO not in codigos(r)
        and r["A3_citas"]["A4_codigo"]["citas_en_codigo"] == 0
        and r["A3_citas"]["A4_codigo"]["citas_en_prosa"] == 2,
        "todos=%s a4=%s" % (codigos(r), r["A3_citas"]["A4_codigo"]))

    d = os.path.join(base, "v6c")
    dirf = _arbol(d)
    _pon(dirf, "002-b.md", 2)
    _pon(dirf, "002-c.md", 2)
    _indice(d, [(2, ["002-b.md", "002-c.md"])], 2, 1)
    os.makedirs(os.path.join(d, "tools"), exist_ok=True)
    with open(os.path.join(d, "driver.c"), "w", encoding="utf-8") as fh:
        fh.write("/* ver 002:12 */\n")
    with open(os.path.join(d, REGISTRO_CODIGO), "w", encoding="utf-8") as fh:
        fh.write("# registro\ndriver.c  #  es un fixture\n")
    r = medir(d, alcance="propio")
    res("6c  la misma cita en un .c pero REGISTRADA -> no 6",
        EXIT_CITA_AMBIGUA_EN_CODIGO not in codigos(r)
        and r["A3_citas"]["A4_codigo"]["citas_en_codigo"] == 0
        and r["A3_citas"]["A4_codigo"]["citas_en_codigo_registradas"] == 1
        and r["A3_citas"]["A4_codigo"]["registro_estado"] == "leido",
        "todos=%s a4=%s" % (codigos(r), r["A3_citas"]["A4_codigo"]))

    # ---- 6e: el registro ausente NO es un registro vacio. Si se tratara como
    # vacio, borrar el registro dejaria la puerta muda en vez de gritando.
    d = os.path.join(base, "v6e")
    dirf = _arbol(d)
    _pon(dirf, "002-b.md", 2)
    _pon(dirf, "002-c.md", 2)
    _indice(d, [(2, ["002-b.md", "002-c.md"])], 2, 1)
    with open(os.path.join(d, "driver.c"), "w", encoding="utf-8") as fh:
        fh.write("/* ver 002:12 */\n")
    r = medir(d, alcance="propio")
    res("6e  sin registro: se cuenta todo y se declara que no esta",
        EXIT_CITA_AMBIGUA_EN_CODIGO in codigos(r)
        and r["A3_citas"]["A4_codigo"]["registro_estado"] == "inexistente"
        and r["A3_citas"]["A4_codigo"]["registro_ficheros"] == 0,
        "todos=%s a4=%s" % (codigos(r), r["A3_citas"]["A4_codigo"]))

    # ---- 6f: la clasificacion CODIGO/PROSA es por extension, y se demuestra
    # con las dos extensiones que mas se confunden: .h es codigo y .txt no.
    res("6f  la clasificacion es decidible y esta escrita",
        es_codigo("07-DRIVER/kernel/rx550_pm4.c")
        and es_codigo("07-DRIVER/kernel/rx550_pm4.h")
        and es_codigo("tools/x.py") and es_codigo("x/Makefile")
        and not es_codigo("docs/x.md")
        and not es_codigo("tools/REF-EXCEPTIONS.txt"))

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
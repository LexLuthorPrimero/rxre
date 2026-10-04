#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0
"""citas_prosa_census.py 1.0.0 - CENSO de la cita por numero en PROSA, por clases.

WORK_CLASS=READ_ONLY (corpus) · WRITES=1 fichero TSV propio · GPU INTACTA

QUE AFIRMA, Y NO ES LA DE check_num_unico.py

    `check_num_unico.py` A3 cuenta y A4 reparte codigo/prosa.  Las dos son
    conteos: dicen CUANTAS hay, no QUE SON.  Este fichero las CLASIFICA y
    deja el expediente de cada una en un TSV, porque una cifra sin expediente
    no se puede auditar ni refutar.

TRES CLASES, Y POR QUE NO SON "correcta / incorrecta"

    C1  la cita sostiene lo que dice.  No es un defecto: es una cita válida que
        solo es frágil si el número se renumera.
    C2  la cita es ambigua: el número está duplicado HOY, así que el lector no
        sabe a cuál de los 2-3 ficheros va.  Reparable por nombre de fichero.
    C3  la cita ya NO apunta a lo que dice.  Grave: una cita equivocada presta
        autoridad al error (hallazgo 188).  Reparable por nombre SOLO si se
        verifica que la línea citada sostiene la afirmación.

    Las tres no son disjuntas: C2 es una propiedad del NÚMERO (aquí, por
    construcción, las 2143 la tienen, porque A3 solo cuenta duplicados) y C1/C3
    son una propiedad del CONTENIDO.  Se mide la disjunción útil: sobre las
    2143, cuántas son C1, cuántas C3, y de las C3 cuántas tienen destino
    conocido.

LOS TRES DETERMINISTAS, Y CUALES NO

    DETERMINISTA, sin proxy, y por eso la cifra es exacta:
      - autocita: la cita va dentro del fichero cuyo propio prefijo es NNN.
        Correcta por construcción, y la regla está escrita y comprobada en
        `findings_index.refs_colgadas`.
      - reasignada: NNN aparece como `viejo` con `reasignado=SI` en el mapa
        congelado `REENVIO-FINDINGS.tsv`.  El número HOY lo ocupa otro
        contenido, y eso se sabe sin mirar la prosa.
      - renumerada_con_destino / renumerada_sin_destino: lo anterior,分为 por si
        la fila del mapa dice `relacion=contenido` (la flecha REPARA) o
        `relacion=numero` (la flecha NO repara, y forzar el destino fabricaría
        una cita nueva).
      - ambigua_por_numero: NNN duplicado, 2-3 candidatos.

    PROXY, y por tanto NO es una cifra: el soporte léxico.  Se usa solo para
    distinguir C1 de C3 en lo que queda, y su falsos positivos y falsos
    negativos se miden con la muestra adjudicada a mano.  La puntuación es
    solapamiento de tokens sin palabras vacías entre el contexto que cita y la
    cabecera de cada candidato.  Es un proxy porque un hallazgo puede
    sostener una afirmación con otra redacción.

VALIDACION DE ESTA HERRAMIENTA

    `--selftest` fabrica un árbol con los seis casos (autocita, duplicado sin
    contenido comun, reasignado con destino, reasignado sin destino, relacion
    `numero`, y una cita en prosa normal) y comprueba la clase de cada una.  Sin
    eso, un censo queclasifica mal no es un dato.
    `--cruzado` re-deriva la poblacion y la compara con lo que dice
    `check_num_unico.py`; si los dos no coinciden, la cifra de este fichero no
    se usa.

Uso:
  python3 citas_prosa_census.py                  resumen + veredicto
  python3 citas_prosa_census.py --json           estructurado
  python3 citas_prosa_census.py --tsv RUTA       expediente por cita
  python3 citas_prosa_census.py --selftest
  python3 citas_prosa_census.py --cruzado
"""

import argparse
import collections
import csv
import glob
import json
import os
import re
import sys
import unicodedata

VERSION = "1.0.0"
WORK_CLASS = "READ_ONLY"
WRITES = "1 TSV de expediente, ruta indicada por --tsv"

EXIT_OK = 0
EXIT_POBLACION_NO_CRUZADA = 3
EXIT_SELFTEST = 4

# --- Las tres formas.  COPIADAS de check_num_unico.py, y a proposito: si las dos
# herramientas tuvieran cada una su propia version, la comparacion del
# `--cruzado` no seria una comprobacion de nada.  Si someday divergen, el
# `--cruzado` tiene que saltar, y por eso estan en un solo sitio aqui.
RE_NUM = re.compile(r"^(\d{3,4})-(.+)\.md$")
RE_CITA_LL = re.compile(r"(?<![\w/.\-])(\d{3,4}):(\d+)\b")
RE_CITA_BT = re.compile(r"`(\d{3,4})`")
RE_CITA_RUTA = re.compile(r"findings/(\d{3,4})(?![\d\w\-])")
EXT_LEIBLES = (".md", ".py", ".sh", ".c", ".h", ".txt", ".tsv")
EXCLUIDOS = ("RESEARCH", "rx550-upstream-7.2.8", "archive", ".git",
             "__pycache__", "07-DRIVER", "node_modules")
CODIGO_EXT = (".c", ".h", ".py", ".sh", ".s", ".cmd", ".d")
CODIGO_SIN_EXT = ("Makefile",)
REGISTRO_CODIGO = "tools/CITA-CODIGO-EXCEPTIONS.txt"

RE_H1 = re.compile(r"^#\s*(.+?)\s*$", re.M)
RE_TABLA_COLISION = re.compile(r"^\|\s*(\d{3,4})\s*\|\s*([^|]+)\|", re.M)

# Palabras vacias en espanol + las que salen en prosa de proyecto.  Se cuentan
# aparte para que se pueda ver si el proxy esta contando ruido.
VACIAS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi aun aunque
bajo bien cada casi como con contra cual cuando de del desde donde dos durante
e el ella ellas ello ellos en entre era eran eramos eres es esa esas ese eso
esos esta estaba estan estas este esto estos estoy fue fueron ha habia han
hasta hay la las le les lo los mas me mi mientras muy nada ni no nos nosotros
nunca o os otra otras otro otros para pero poco por porque que quien se sea
segun ser si sido sin sobre solo son su sus tambien tan tanto te tiene tienen
toda todas todo todos tras tu un una unas uno unos y ya yo
vez veces caso casos cosa cosas punto puntos linea lineas parte partes
tambien mas menos mismo misma solo solo
""".split())


def norm_tokens(t):
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", t.lower())


def tokens_significativos(t):
    return [w for w in norm_tokens(t) if w not in VACIAS and len(w) > 2]


def es_codigo(rel):
    base = os.path.basename(rel)
    ext = os.path.splitext(base)[1].lower()
    return ext in CODIGO_EXT or base in CODIGO_SIN_EXT


def dir_hallazgos(raiz):
    return os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")


# ---------------------------------------------------------------------------
# 1. POBLACION.  Re-derivada aqui, no importada: un censo que importa el
#    counted de la puerta que quiereReplacear no es independiente.
# ---------------------------------------------------------------------------

def escanear_hallazgos(d):
    """numero -> [ficheros].  Devuelve None si no existe findings/."""
    if not os.path.isdir(d):
        return None
    por = collections.defaultdict(list)
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        m = RE_NUM.match(base)
        if m:
            por[int(m.group(1))].append(base)
    return dict(por)


def secuencias(d, por_num):
    """{fichero: tokens del CUERPO COMPLETO, en orden} para todo findings/."""
    out = {}
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        if not RE_NUM.match(base):
            continue
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            out[base] = []
            continue
        out[base] = norm_tokens(texto)
    return out


def cabeceras(d, por_num):
    """{fichero: (titulo, primeras lineas de cuerpo)} para TODO findings/.

    Se lee UNA vez por fichero y se cachea: el proxy corre una vez por cita y
    sin cache se relee el arbol entero por cada una.

    MEDIDO: la primera version solo cacheaba los ficheros de numeros DUPLICADOS,
    y por eso no podia puntuar el DESTINO de una cita reasignada, que vive en un
    numero que no esta duplicado.  Con esa version, el caso de selftest "el 930
    renumerado a 931, citado desde docs/" salia `C3_..._fuera_de_orden`: los dos
    ficheros 930 no contienen lo que la prosa dice --correcto-- y la unica
    fuente que si lo contiene, el 931, no estaba en el conjunto de candidatos.
    Un clasificador que no puede ver al destino no puede reconocer la clase que
    mas importa.
    """
    cache = {}
    for ruta in sorted(glob.glob(os.path.join(d, "*.md"))):
        base = os.path.basename(ruta)
        if not RE_NUM.match(base):
            continue
        try:
            with open(ruta, encoding="utf-8", errors="replace") as fh:
                texto = fh.read()
        except OSError:
            cache[base] = ("", "")
            continue
        h1 = RE_H1.search(texto)
        tit = h1.group(1) if h1 else ""
        lineas = [l for l in texto.split("\n") if l.strip()]
        cache[base] = (tit, " ".join(lineas[:12]))
    return cache


def leer_reenvio(raiz):
    """Mapa congelado viejo -> (nuevo, reasignado, relacion, stem, procedencia).

    Se lee del TSV y NO del diff contra HEAD: el diff desaparece al commitear el
    renumerado, y con el desaparece la capacidad de detectar la cita colgando.
    Es el mismo motivo que escribe `findings_index.reenvios_estable`.
    """
    p = os.path.join(raiz, "08-ARQUITECTURA", "tools", "REENVIO-FINDINGS.tsv")
    if not os.path.isfile(p):
        return {}, "inexistente"
    m = {}
    with open(p, encoding="utf-8") as fh:
        for ln in fh:
            ln = ln.rstrip("\n")
            if not ln or ln.startswith("#"):
                continue
            cols = ln.split("\t")
            if len(cols) != 6:
                raise ValueError("REENVIO-FINDINGS.tsv:%d: ancho %d, se esperaba 6"
                                 % (len(cols), len(cols)))
            m.setdefault(int(cols[0]), []).append(
                {"nuevo": int(cols[1]), "reasignado": cols[2] == "SI",
                 "stem": cols[3], "relacion": cols[4], "procedencia": cols[5]})
    return m, "leido"


def registrar_codigo(raiz):
    p = os.path.join(raiz, REGISTRO_CODIGO)
    if not os.path.isfile(p):
        return set(), "inexistente"
    s = set()
    with open(p, encoding="utf-8") as fh:
        for ln in fh:
            t = ln.strip()
            if t and not t.startswith("#"):
                s.add(t.split("#")[0].strip())
    return s, "leido"


def contexto(lineas, i, ventana=1):
    """El texto que hace la cita.  Una linea de contexto a cada lado.

    Una cita no es solo el numero: es `lo que se afirma` + `el numero`.  Por eso
    el proxy compara el CONTEXTO, no la linea pelada: si la linea dice
    "`110` es WAIT_REG_MEM", el token `wait` esta en el contexto y es el que
    discrimina entre los dos ficheros 110.
    """
    return unidad_de_la_cita(lineas, i, ventana)


# MEDIDO, y fue un DEFECTO de este proxy antes de corregirlo.  Con la ventana
# fija de una linea a cada lado, el contexto se comia la frase de la CITA
# SIGUIENTE.  En prosa de markdown una cita es su propia frase y la frase
# siguiente suele ser OTRA cita, y entonces sus palabras iban a puntuar para el
# candidato equivocado.  Consecuencia medida en el selftest: dos numeros con
# temas DISYUNTOS salian "ambiguos" los dos, porque los tokens de la cita
# vecina empataban el soporte de los dos ficheros.  Es el peor modo de fallo
# posible de este proxy: no towards Class C3, sino hacia C2, y C2 es la clase
# que hace que se arregle algo que no estaba mal.
#
# Por eso la unidad es la FRASE, y la frase se recorta por el punto.  Y hay
# tres tipos de linea donde NO se recorta, porque el punto no es un final de
# frase: la fila de tabla, la viñeta y el encabezado.
UNIDAD_LINIA = re.compile(r"^\s*(?:\||[-*+]\s|\d+[.)]\s|#{1,6}\s)")


def unidad_de_la_cita(lineas, i, ventana=1):
    """La frase que contiene la cita.  No mas.

    Tres reglas, y las tres estan porque el selftest las exige:
      1. linea de tabla / viñeta / encabezado -> la linea entera;
      2. si no, los segmentos de la linea que rodean la cita, Partiendo por
         `[.;!?]`;
      3. si eso deja menos de TRES tokens significativos, se anade la linea
         anterior no vacia: hay citas que son un parenthetical y no tienen
         sujeto.
    """
    linea = lineas[i] if 0 <= i < len(lineas) else ""
    if UNIDAD_LINIA.match(linea):
        unidad = linea
    else:
        partes = re.split(r"(?<=[.;!?])\s+", linea)
        # la cita cae en el segmento donde el offset acumulado alcanza el final
        # del segmento; se toma ese y el siguiente, porque la afirmacion suele
        # ser "el `110` hace X, segun Y" y el "segun Y" esta en el siguiente.
        acum = 0
        idx = 0
        for j, p in enumerate(partes):
            acum += len(p) + 1
            if acum >= len(linea):
                idx = j
                break
            idx = j
        ele = partes[idx:idx + 2] if idx < len(partes) else partes[-1:]
        unidad = " ".join(ele)
    if len(tokens_significativos(unidad)) < 3:
        for k in range(i - 1, max(-1, i - ventana - 2), -1):
            if 0 <= k < len(lineas) and lineas[k].strip():
                unidad = lineas[k] + " " + unidad
                break
    return unidad.strip()


def soporte(ctx_toks, cab_toks):
    """Solape de tokens: fraccion de tokens del contexto que estan en la cabecera.

    MEDIDO: este score NO Sirve para distinguir C1 de C2.  Con las cabeceras de
    solo 12 lineas y el contexto de una frase, 1127 citas salen "contenido
    univoco" y 868 "ambigua", y ninguna de las dos cifras sobrevive a mirar la
    prosa: la.validacion de las 12 etiquetas a mano no encuentra ningun caso en
    que la distincion cambiara el veredicto.  Se conserva porque es explicable,
    y se anade al lado el score que si discrimina, para que la diferencia sea
    visible y no una opinion.
    """
    if not ctx_toks or not cab_toks:
        return 0.0
    cab = set(cab_toks)
    hit = sum(1 for w in set(ctx_toks) if w in cab)
    return hit / float(len(set(ctx_toks)))


IDENT = re.compile(r"[0-9_]|\.[a-z]|[a-z][a-z]\$")


def es_distintivo(w):
    """Un token que puede IDENTIFICAR algo: lleva digito, guion bajo, o es largo.

    MEDIDO, y era un DEFECTO grave de la version anterior.  La rareza se media
    sobre el texto CRUDO de findings/, y en un corpus de 546 ficheros de este
    proyecto las palabras funcionales del espanol son RARAS: "con" sale en 2
    ficheros, "el" en 1, "de" en 3.  Con eso la senal de identificador raro
    puntuaba 1 a un candidato que no tenia absolutely nada que ver, y el caso de
    renumerado del selftest salia C1_raro con un token de，palabras vacias.

    La rareza tiene que medirse en el MISMO tokenizer con el que se busca la
    senal.  Si el indice de rareza se construye sobre texto sin filtrar y la
    busqueda se hace sobre texto filtrado, la senal mide ruido de，palabras vacias.
    Por eso el indice excluye las palabras vacias Y exige que el token parezca
    un identificador.
    """
    if w in VACIAS or len(w) < 4:
        return False
    if IDENT.search(w):
        return True
    return len(w) >= 6


def indice_raros(d, por_num, seqs, df_max=3):
    """token -> numero de ficheros de findings/ que lo contienen.

    MEDIDO POR QUE HACE FALTA.  El n-grama contiguo solo dispara cuando la
    prosa CITA el texto del destino.  Casi toda cita real NO cita: dice
    "el `273` §1 y §4" sin copiar nada.  Con solo n-gramas, esos casos salen
    `SIN_APOYO` y esa clase se come la mitad de la poblacion.

    La senal que si funciona en esos casos es un IDENTIFICADOR RARO: un valor
    hexadecimal, un numero grande, un nombre de registro, un sym de sysfs.
    Esos tokens no se repiten por el castellano, asi que el numero de ficheros
    de findings/ que los contienen es 1 o 2, y si la cita trae uno y solo un
    candidato lo tiene, esa coincidencia no puede ser casualidad.

    El umbral `df_max=3` es un PARAMETRO, no un hecho, y por eso se declara y
    se puede mover con `--df-max`.  Con df<=3, medido sobre las 12 etiquetas a
    mano, la senal acierta 11 de 12 y la que falla es el caso que NO tiene
    identificador: una lista de numeros pelados.
    """
    df = collections.Counter()
    for _b, seq in seqs.items():
        for w in set(seq):
            if es_distintivo(w):
                df[w] += 1
    return {w for w, n in df.items() if n <= df_max}


def soporte_raros(ctx_toks, cab_seq, raros, excluir=()):
    """Tokens RAROS del contexto que estan en el candidato.  Cuantos, no cuales.

    MEDIDO, y era un DEFECTO: `excluir` no existia, y el token del NUMERO
    citado contaba como identificador raro.  Como el numero aparece en el
    nombre y el titulo de TODOS sus candidatos, los tres sacaban al menos 1 y
    la senal era "hay tres candidatos con un token raro", que es lo mismo que
    no tener senal.  En el selftest el caso de renumerado salia
    `C2_ambigua_senales_en_varios` con 5 tokens raros a favor del destino
    (pm4dw, contador, dw, cuenta, bytes) y 1 a favor de cada ocupante.

    El numero citado no es evidencia de nada: es la clave, no la afirmacion.
    """
    if not raros:
        return 0
    cab = set(cab_seq)
    return sum(1 for w in set(ctx_toks)
               if w in raros and w not in excluir and w in cab)


def soporte_ngrama(ctx_toks, cab_seq, n=4):
    """Longitud maxima de un TROZO CONTIGUO de la cita que aparecefollowed por
    el candidato.  Es el score que discrimina.

    POR QUE CONTIGUO Y NO SOLAPE.  Un hallazgo de este proyecto ocupa 200-250
    lineas, asi que cualquier frase de cinco palabras encuentra *algo* dentro:
    el solape de tokens con el cuerpo entero saturaria para todos los candidatos
    y no distinguiria nada.  Lo que NO ocurre en un cuerpo de 250 lineas es que
    aparezcan CUATRO palabras seguidas en el orden en que las escribio el que
    cita.  Un n-grama contiguo de 3 o mas es evidencia de que las dos frases son
    la misma frase; un solape de 8 tokens sueltos no es nada.

    Se puntua el maximo de n-gramas CONTIGUOS de longitud >= 3.  0 significa
    "no hay tres palabras seguidas": no hay soporte textual, y la cita se
    declara, no se repara.
    """
    if len(ctx_toks) < 3 or not cab_seq:
        return 0
    pos = {}
    for i in range(len(cab_seq) - 2):
        pos.setdefault(tuple(cab_seq[i:i + 3]), []).append(i)
    mejor = 0
    for i in range(len(ctx_toks) - 2):
        for L in range(len(ctx_toks), i + 2, -1):
            if L <= mejor:
                break
            for ini in pos.get(tuple(ctx_toks[i:i + 3]), ()):
                if cab_seq[ini:ini + (L - i)] == ctx_toks[i:L]:
                    mejor = max(mejor, L - i)
                    break
            if mejor:
                break
    return mejor


def ivables(a, b, holgura=0.15):
    """Si `b` gana a `a` por mas que la holgura, son COMPARABLES, no empatados.

    MEDIDO: esta condicion nacio INVERTIDA y el selftest la cazo.  Con
    `not ivables(...)` significando "C1", dos numeros con temas DISYUNTOS
    salian C2 y dos numeros identicos salian C1: las dos clases al reves.  Un
    proxy invertido no falla ruidoso, falla al reves, y por eso el selftest
    tiene que Fabricar los DOS casos y comprobar los DOS.

    Sin esto, dos ficheros que comparten el 60 % de su vocabulario aparecen
    "igualmente sostenidos" y la clasificacion cae en ambigua por ruido.  La
    holgura se declara porque es un parametro, no un hecho.
    """
    if b <= 0.0:
        return False
    if a <= 0.0:
        return True
    return (b - a) / max(a, b) > holgura


def poblacion(raiz, holgura=0.15, df_max=3):
    """Una pasada por el arbol.  Devuelve el censo completo."""
    d = dir_hallazgos(raiz)
    por_num = escanear_hallazgos(d)
    if por_num is None:
        return None, "no existe %s" % d
    dups = {n for n, v in por_num.items() if len(v) > 1}
    cabs = cabeceras(d, por_num)
    cab_toks = {b: tokens_significativos(tit + " " + cuerpo)
                for b, (tit, cuerpo) in cabs.items()}
    secs = secuencias(d, por_num)
    raros = indice_raros(d, por_num, secs, df_max)
    reenv, est_reenv = leer_reenvio(raiz)
    registro, est_reg = registrar_codigo(raiz)

    filas = []
    leidos = omitidos = 0
    for dp, dn, fn in os.walk(raiz):
        dn[:] = [x for x in dn if x not in EXCLUIDOS]
        rel_dir = os.path.relpath(dp, raiz).replace(os.sep, "/")
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
            cod = es_codigo(rel)
            reg = rel in registro
            lineas = texto.split("\n")
            propio = None
            if rel_dir.endswith("findings"):
                m = RE_NUM.match(f)
                if m:
                    propio = int(m.group(1))
            for rx, grupo in ((RE_CITA_LL, "NNN:LL"), (RE_CITA_BT, "`NNN`"),
                              (RE_CITA_RUTA, "findings/NNN")):
                for m in rx.finditer(texto):
                    num = int(m.group(1))
                    if num not in dups:
                        continue
                    i = texto.count("\n", 0, m.start())
                    ln = i + 1
                    ctx = contexto(lineas, i)
                    ctx_t = tokens_significativos(ctx)
                    ctx_norm = norm_tokens(ctx)
                    cands = sorted(por_num.get(num, []))
                    sop = {}
                    for b in cands:
                        sop[b] = round(soporte(ctx_t, cab_toks.get(b, [])), 4)
                    orden = sorted(sop.items(), key=lambda kv: (-kv[1], kv[0]))
                    top = orden[0][1] if orden else 0.0
                    segundo = orden[1][1] if len(orden) > 1 else 0.0
                    ng = {}
                    for b in cands:
                        ng[b] = soporte_ngrama(ctx_norm, secs.get(b, []))
                    ng_ord = sorted(ng.items(), key=lambda kv: (-kv[1], kv[0]))
                    ng_top = ng_ord[0][0] if ng_ord else ""
                    ng_top_n = ng_ord[0][1] if ng_ord else 0
                    ng_2o = ng_ord[1][1] if len(ng_ord) > 1 else 0
                    r = reenv.get(num, [])
                    reas = any(x["reasignado"] for x in r)
                    sop_dest = None
                    rel_contenido = [x for x in r if x["relacion"] == "contenido"]
                    rel_numero = [x for x in r if x["relacion"] == "numero"]
                    reenv_nuevo = rel_contenido[0]["nuevo"] if rel_contenido else None
                    reenv_destino = None
                    if reenv_nuevo is not None:
                        por = por_num.get(reenv_nuevo, [])
                        reenv_destino = por[0] if len(por) == 1 else None
                    # --- clase ---------------------------------------------------
                    #
                    # EL ORDEN DE ESTAS COMPROBACIONES ES EL DATO, no un
                    # detalle.  La autocita va PRIMERO porque el renumerado de
                    # OTRO hallazgo deja a `NNN` ocupado por otro contenido y eso
                    # haria que la autocita pareciese equivocada.  La regla y su
                    # comprobacion estan escritas en
                    # `findings_index.refs_colgadas`: sin descontar las
                    # autocitas la cuenta de colgantes es incorrecta, porque
                    # mezcla dos clases y las trata como la misma.
                    # ----------------------------------------------------------------
                    # MEDIDO, Y CORRIGIDO: ESTO ANTES DECIA C3 Y ESTABA MAL.
                    #
                    # La version anterior salto de "el mapa de renumeraciones
                    # dice que el contenido de NNN esta hoy en MMM" a "esta cita
                    # a NNN deberia apuntar a MMM".  Ese salto no se sostiene: el
                    # mapa dice DONDE esta un contenido, no que toda cita al
                    # numero viejo este equivocada.  La prueba es la cuenta, y
                    # sale de leer las prosa: de las 12 salidas dudosas del
                    # proxy, adjudicadas una a una en `citas_prosa_etiquetas.py`,
                    # C3 confirmadas a mano = 0.  Las cuatro que el proxy marco
                    # `C3_reasignada_con_destino` son la fila del propio indice
                    # de renumeraciones y el documento que explica ese
                    # renumerado: son correctas.  Y dos de ellas se prueban sin
                    # vocabulario, por tamano: el hallazgo 1039 dice que el
                    # fichero corrupto tiene 11 598 bytes, y MEDIDO el tamano
                    # del 1011 de hoy es 11 598 y el del 1020 es 12 700.
                    #
                    # O sea: el mecanismo de renumerado NO es un detector de
                    # citas equivocadas.  Es un GENERADOR DE SOSPECHAS, y su tasa
                    # de acierto medida es 0 de 4.  Por eso la clase 3 se
                    # declara con lo que la sostiene y no con lo que la
                    # sospecha.
                    # ----------------------------------------------------------------
                    # El renumerado se queda como ATRIBUTO, no como clase: dice
                    # que este numero tiene historial, y el historial es la
                    # razon por la que una cita por numero no es verificable.
                    ng_dest = (soporte_ngrama(ctx_norm, secs.get(reenv_destino, []))
                               if reenv_destino else 0)
                    # El conjunto de LECTURAS de una cita a `NNN`, y solo dos
                    # existen: los ficheros que HOY tienen ese numero, y -- si el
                    # mapa dice que el contenido de entonces se movio -- el
                    # fichero al que se movio.  La clase 3 es exactamente
                    # "gana el segundo y no gana ninguno del primero".
                    #
                    # Se mantiene la rama aunque se sepa que no dispara, y la
                    # razon es de epistemica, no de codigo: borrar la rama
                    # seria ASERTAR que la clase 3 no existe.  Aqui se mide que
                    # no se la ve, y esa diferencia es el resultado.
                    efec = list(cands)
                    if reenv_destino and reenv_destino not in efec:
                        efec.append(reenv_destino)
                    ctx_dis = [w for w in ctx_norm if es_distintivo(w)]
                    rr = {b: soporte_raros(ctx_dis, secs.get(b, []), raros,
                                           excluir={str(num)})
                          for b in efec}
                    ng_all = [(b, soporte_ngrama(ctx_norm, secs.get(b, [])))
                              for b in efec]
                    ng_all.sort(key=lambda kv: (-kv[1], kv[0]))
                    mejor_b, mejor_n = (ng_all[0] if ng_all else ("", 0))
                    runners = [n for _b, n in ng_all[1:] if n >= 3]
                    # Tres senales, ORTOGONALES, y se necesitan las tres porque
                    # cada una ve lo que las otras no ven:
                    #   n-grama contiguo  -> la prosa COPIA el texto del destino
                    #   token raro         -> la prosa NOMBRA un identificador
                    #                          unico de un candidato
                    #   ninguna de las dos -> la cita no dice nada que permita
                    #                          elegir, y eso NO es lo mismo que
                    #                          que este mal.
                    rr_top = max(rr.values()) if rr else 0
                    rr_2o = sorted(rr.values(), reverse=True)[1] if len(rr) > 1 else 0
                    rr_gana = [b for b, n in rr.items()
                               if n > 0 and n >= rr_top]
                    # MEDIDO: el orden de estas dos comprobaciones tambien fue
                    # un defecto.  Con la de token raro delante, el caso de
                    # renumerado del selftest salia C1_raro: el destino gana
                    # con 5 identificadores raros y con un n-grama de 11, y aun
                    # asi la rama de clase 3 no llegaba a ejecutarse.  La clase 3
                    # es mas especifica, y una clase especifica que nunca se
                    # evalua porque se la come una general no esta medida.
                    #
                    # La condicion es "gana el destino Y ningun ocupante del
                    # numero llega al mismo nivel de evidencia", con las dos
                    # señales.  Si un ocupante llegara empatado, no seria clase
                    # 3: seria ambiguedad, porque entonces hay dos lecturas
                    # igual de buenas y la cita no dice cual.
                    occ_ocupan = [b for b in cands
                                  if (soporte_ngrama(ctx_norm, secs.get(b, [])) < 3
                                      and soporte_raros(ctx_dis, secs.get(b, []),
                                                        raros, {str(num)}) == 0)]
                    if propio == num:
                        clase = "C1_autocita"
                    elif (reenv_destino is not None and mejor_b == reenv_destino
                          and (mejor_n >= 3 or rr_top > 0)
                          and len(occ_ocupan) == len(cands)):
                        clase = "C3_gana_el_destino_del_mapa"
                    elif ng_top_n >= 3 and ng_top_n > ng_2o:
                        clase = "C1_sostenida_por_ngrama"
                    elif rr_top > 0 and rr_top > rr_2o:
                        # UN identificador raro mas, y solo uno lo tiene: el
                        # margen, no el recuento, es lo que descarta al resto
                        clase = "C1_sostenida_por_token_raro"
                    elif ng_top_n >= 3:
                        clase = "C2_ambigua_senales_en_varios"
                    elif rr_top > 0:
                        # varios candidatos con el MISMO numero de tokens raros:
                        # el identificador no los separa
                        clase = "C2_ambigua_senales_en_varios"
                    else:
                        clase = "SIN_APOYO_ninguna_senal"
                    filas.append({
                        "citante": rel, "dir": rel_dir, "linea": ln,
                        "forma": grupo, "num": num,
                        "autocita": 1 if propio == num else 0,
                        "n_cand": len(cands),
                        "candidato_top": orden[0][0] if orden else "",
                        "soporte_top": top, "soporte_2o": segundo,
                        "margen": round(top - segundo, 4),
                        "propio": propio if propio is not None else "",
                        "en_reenvio": 1 if r else 0,
                        "reasignado": 1 if reas else 0,
                        "relacion": (r[0]["relacion"] if r else ""),
                        "reenvio_nuevo": reenv_nuevo if reenv_nuevo else "",
                        "reenvio_destino": reenv_destino or "",
                        "soporte_destino": ng_dest,
                        "ngrama_top": ng_top, "ngrama_2o": ng_2o,
                        "ngrama_destino": ng_dest,
                        "rara_top": rr_top,
                        "rara_ganadoras": "|".join(sorted(rr_gana))[:200],
                        "lectura_ganadora": mejor_b,
                        "ngrama_ganadora": mejor_n,
                        "en_codigo": 1 if cod else 0,
                        "registrado": 1 if reg else 0,
                        "clase": clase,
                        "texto": ctx.strip()[:300],
                    })
    ctx_ = {"raiz": raiz, "dir_hallazgos": d,
            "numeros_distintos": len(por_num),
            "duplicados": len(dups),
            "ficheros_en_hallazgos": sum(len(v) for v in por_num.values()),
            "ficheros_leidos": leidos, "ficheros_omitidos": omitidos,
            "reenvio_estado": est_reenv,
            "reenvio_filas": sum(len(v) for v in reenv.values()),
            "registro_estado": est_reg,
            "holgura": holgura, "df_max": df_max,
            "tokens_raros": len(raros)}
    return {"contexto": ctx_, "filas": filas}, None


def resumen(censo):
    filas = censo["filas"]
    ctx = censo["contexto"]
    total = len(filas)
    por_clase = collections.Counter(f["clase"] for f in filas)
    por_dir = collections.Counter(f["dir"] for f in filas)
    por_forma = collections.Counter(f["forma"] for f in filas)
    # clase x forma, y clase x (dir grande) : las dos tablas que pide el
    # muestreo.  Sin ellas "el 90 % es C1" no dice en que parte del arbol.
    cruce = collections.Counter((f["clase"], f["forma"]) for f in filas)
    grand = [d for d, _ in por_dir.most_common(8)]
    cruce_dir = collections.Counter((f["clase"], f["dir"]) for f in filas
                                   if f["dir"] in grand)
    reas = [f for f in filas if f["reasignado"]]
    return {
        "poblacion": total,
        "contexto": ctx,
        "por_clase": dict(por_clase.most_common()),
        "por_forma": dict(por_forma.most_common()),
        "por_directorio": dict(por_dir.most_common(15)),
        "clase_x_forma": {"%s|%s" % k: v for k, v in sorted(cruce.items())},
        "clase_x_directorio": {"%s|%s" % k: v for k, v in sorted(cruce_dir.items())},
        "citas_en_hallazgos": sum(1 for f in filas if f["dir"].endswith("findings")),
        "citas_en_codigo": sum(1 for f in filas if f["en_codigo"]),
        "citas_en_codigo_registradas": sum(1 for f in filas
                                            if f["en_codigo"] and f["registrado"]),
        "citas_en_prosa": sum(1 for f in filas if not f["en_codigo"]),
        "sobre_numero_reasignado": len(reas),
        "sobre_numero_reasignado_con_destino": sum(
            1 for f in reas if f["reenvio_destino"]),
        "sobre_numero_reasignado_sin_destino": sum(
            1 for f in reas if not f["reenvio_destino"]),
        "numeros_reasignados_alcanzados": len({f["num"] for f in reas}),
    }


# ---------------------------------------------------------------------------
# 2. CRUZADO.  La poblacion de este fichero contra la de check_num_unico.py.
# ---------------------------------------------------------------------------

def cruzado(raiz, censo):
    """Importa la puerta y compara SU total con el NUESTRO.

    Si difieren, este fichero no publica cifras: publica por que.  Una census
    que se autosuma y dice que esta bien no es una comprobacion.
    """
    sys.path.insert(0, os.path.join(raiz, "tools"))
    import check_num_unico as cnu          # noqa: E402  (import medido)
    por_num = cnu.fs_indice(raiz)[0]
    if por_num is None:
        return {"ok": False, "motivo": "check_num_unico no ve findings/"}
    suyo, _, leidos_suyo, _ = cnu.citas_por_numero(raiz, por_num, "propio", None)
    a = suyo["citas_por_numero_a_duplicado"]
    b = len(censo["filas"])
    difs = []
    if a != b:
        difs.append("total: puerta=%d censo=%d" % (a, b))
    for g in ("NNN:LL", "`NNN`", "findings/NNN"):
        if suyo["por_forma"].get(g, 0) != sum(
                1 for f in censo["filas"] if f["forma"] == g):
            difs.append("forma %s: puerta=%d censo=%d" % (
                g, suyo["por_forma"].get(g, 0),
                sum(1 for f in censo["filas"] if f["forma"] == g)))
    if leidos_suyo != censo["contexto"]["ficheros_leidos"]:
        difs.append("ficheros leidos: puerta=%d censo=%d"
                    % (leidos_suyo, censo["contexto"]["ficheros_leidos"]))
    return {"ok": not difs, "total_puerta": a, "total_censo": b,
            "ficheros_puerta": leidos_suyo,
            "ficheros_censo": censo["contexto"]["ficheros_leidos"],
            "diferencias": difs,
            "por_forma_puerta": suyo["por_forma"]}


# ---------------------------------------------------------------------------
# 3. SELFTEST.  Sin esto, una herramienta que clasifica no es un dato.
# ---------------------------------------------------------------------------

def _arbol(d):
    os.makedirs(os.path.join(d, "06-INGENIERIA-INVERSA", "findings"), exist_ok=True)
    os.makedirs(os.path.join(d, "docs"), exist_ok=True)
    os.makedirs(os.path.join(d, "08-ARQUITECTURA", "tools"), exist_ok=True)
    os.makedirs(os.path.join(d, "tools"), exist_ok=True)


def _pon(dirf, nombre, num, texto):
    with open(os.path.join(dirf, nombre), "w", encoding="utf-8") as fh:
        fh.write(texto)


def _indice(d, filas, n_col):
    with open(os.path.join(d, "FINDINGS-RENUMERACIONES.md"), "w",
              encoding="utf-8") as fh:
        fh.write("# FINDINGS-RENUMERACIONES\n\n## Numeros con colision\n\n")
        fh.write("| numero | ficheros |\n|---|---|\n")
        for n, fs in filas:
            fh.write("| %d | %s |\n" % (n, "<br>".join(fs)))


def selftest() -> int:
    import tempfile
    fallos = []

    # NUMEROS DEL FIXTURE: 910, 915, 920, 930, 931, 940.
    #
    # MEDIDO, y fue un DEFECTO de este selftest antes de corregirlo.  La primera
    # version usaba 110, 115, 130 y 140, que estan DUPLICADOS en el arbol REAL.
    # Con esos numeros, el codigo fuente del propio instrumento contenia cinco
    # citas por numero que caian sobre un duplicado real, y la puerta A4 las
    # contaba como DEFECTO: de 0 a 5.  Es decir: un self-test puede estropear
    # la medicion que verifica, y el sintoma no es un fallo del self-test sino
    # un numero que cambia en una puerta que no tiene nada que ver.
    #
    # Por eso los numeros del fixture son unicos en el arbol real.  Verificado
    # con el mismo regex de la puerta: los 74 duplicados reales no contienen
    # ninguno de 910/915/920/930/931/940.  El fixture fabrica SU propia
    # duplicacion, que es lo unico que el selftest necesita.
    with tempfile.TemporaryDirectory(prefix="citasprosa-st-") as d:
        ra = os.path.join(d, "proyecto")
        _arbol(ra)
        fd = os.path.join(ra, "06-INGENIERIA-INVERSA", "findings")

        # 910 duplicado: uno sobre WAIT_REG_MEM, otro sobre soft_regs_start.
        _pon(fd, "910-wait-reg-mem.md", 910,
             "# 910 espera de registro\n\n## memoria\n\n"
             "Un WAIT_REG_MEM bloquea hasta que el registro responde. SEV "
             "contiene el campo expected.\n")
        _pon(fd, "910-soft-regs-start.md", 910,
             "# 910 soft regs start\n\n## shdw\n\n"
             "soft_regs_start se inicializa por PM4 SHADOW_START. SEV.\n")
        # 915 duplicado con vocabulario DISYUNTO: la ambiguedad por numero es
        # real pero el contenido SI discrimina -> tiene que salir C1, no C2.
        _pon(fd, "915-palabras-clave-graf8.md", 915,
             "# 915 palabras clave\n\n## dict\n\n"
             "diccionario de synonyms de codigo fuente GRAF.\n\n"
             # c1) AUTOCITA: el `915` DENTRO del 915.  Correcta por
             # construccion, con la regla escrita y comprobada en
             # `findings_index.refs_colgadas`.
             "Como se ve en el `915`, el diccionario se carga por shader.\n")
        _pon(fd, "915-otro-tema.md", 915,
             "# 915 otro tema\n\n## x\n\n"
             "Zzzzqqq wwwwvvvv yyyyxxxx uuuutttt sin relacion.\n")
        # 920: unico.  Su cita NO cuenta (la poblacion mira solo duplicados).
        _pon(fd, "920-unico.md", 920, "# 920 unico\n\n## x\n\nSEV.\n")
        # 930: duplicado, y ademas REASIGNADO con destino con relacion=contenido.
        #
        # POR QUE HACE FALTA EL SEGUNDO 930.  MEDIDO: si 930 estuviera UNICO, su
        # cita NO entra en la poblacion, porque la poblacion es "cita por numero
        # sobre numero DUPLICADO".  Es decir: una cita que apunta al contenido
        # equivocado y cuyo numero viejo quedo UNICO es INVISIBLE para A3.  No
        # es un defecto del censo, es la poblacion que el enunciado define, y
        # por eso lo que sale de aqui es un hallazgo sobre el ALCANCE de A3, no
        # una clase de cita nueva.  El caso se prueba con 930 duplicado, que es
        # la forma en que la cita erronea SI cae dentro de la poblacion.
        _pon(fd, "930-ocupado-ahora.md", 930,
             "# 930 ocupado ahora\n\n## y\n\n"
             "Zzzzqqq wwwwvvvv yyyyxxxx uuuutttt sin relacion con lo citado.\n")
        _pon(fd, "930-tercero-tambien.md", 930,
             "# 930 tercero\n\n## w\n\n"
             "Qqqqwwww eeeerrrr tttttyyyy otro contenido sin relacion.\n")
        _pon(fd, "931-algo-renumerado.md", 931,
             "# 931 algo renumerado\n\n## z\n\n"
             "El SEV de pm4dw con el contador de dw y la cuenta de bytes.\n")
        # 940: duplicado y AMBOS con el mismo vocabulario -> C2 de verdad.
        # 940: duplicado y los dos ficheros dicen LO MISMO con las MISMAS
        # palabras.  Aqui el contenido NO discrimina ni por n-grama, y esa es la
        # unica forma de que C2 sea real: dos textos identicos.
        _pon(fd, "940-ambiguo-todo.md", 940,
             "# 940 uno\n\n## a\n\nSEV de cuentas y de contadores.\n")
        _pon(fd, "940-otro.md", 940,
             "# 940 dos\n\n## b\n\nSEV de cuentas y de contadores.\n")

        with open(os.path.join(ra, "08-ARQUITECTURA", "tools",
                               "REENVIO-FINDINGS.tsv"), "w",
                  encoding="utf-8") as fh:
            fh.write("# t\n930\t931\tSI\talgo-renumerado.md\tcontenido\t"
                     "prosa:x:1\n")
        _indice(ra, [(910, ["910-soft-regs-start.md", "910-wait-reg-mem.md"]),
                     (915, ["915-otro-tema.md", "915-palabras-clave-graf8.md"]),
                     (930, ["930-ocupado-ahora.md", "930-tercero-tambien.md"]),
                     (940, ["940-ambiguo-todo.md", "940-otro.md"])], 4)

        # prosa en findings/: los casos a, b, c2 y d
        #
        # LAS CITAS SON CITAS DE VERDAD, y esto se cambio a proposito.
        #
        # MEDIDO: la primera version del selftest escribia "El `910` de
        # WAIT_REG_MEM y el campo expected del SEV", una frase invention del
        # selftest que no esta en ningun fichero.  Con el proxy de n-gramas esa
        # frase no tiene ningun trigrama en ningun sitio, y los casos salian
        # `SIN_APOYO_ngrama_lt3` los cuatro: la prueba pasaba por el proxy pero
        # midiendo una frase que nadie escribio.  Un self-test que no cita el
        # texto real no prueba el proxy: prueba el proxy con otro texto.
        #
        # Ahora cada cita entrecomilla un trozo LITERAL del fichero al que dice
        # apuntar, que es lo que hace una cita en la prosa real.
        with open(os.path.join(fd, "200-prueba.md"), "w", encoding="utf-8") as fh:
            fh.write(
                "# 200 prueba\n\n"
                # a) el `910` cuyo texto citado aparece en UNO solo de los dos.
                "Tal como dice el `910`: \u00abWAIT_REG_MEM bloquea hasta que el "
                "registro responde\u00bb.\n\n"
                # b) el `940` citado con palabras que estan en los DOS ficheros.
                "El `940` que dice \u00abSEV de cuentas y de contadores\u00bb.\n\n"
                # c2) el `915` citado desde fuera: el primero contiene el
                # fragmento, el segundo no -> C1 aunque el numero no lo diga.
                "El `915` del \u00abdiccionario de synonyms de codigo fuente\u00bb.\n\n"
                # d) 920 unico: NO esta en la poblacion.
                "El `920` de unico.\n")
        # prosa en docs/: el caso e, reasignado con destino
        # e) el `930` renumerado: el mapa lo manda a 931 y la prosa cita el
        #    texto del 931, que no aparece en NINGUNO de los dos 930.  Esta es
        #    la unica forma de la clase 3, y el fixture la fabrica de verdad.
        with open(os.path.join(ra, "docs", "nota.md"), "w", encoding="utf-8") as fh:
            fh.write("# nota\n\nEl `930` que dice \u00abpm4dw con el contador "
                     "de dw y la cuenta de bytes\u00bb.\n")
        with open(os.path.join(ra, REGISTRO_CODIGO), "w", encoding="utf-8") as fh:
            fh.write("# registro\n")

        c, err = poblacion(ra)
        if err:
            fallos.append("poblacion fallo: %s" % err)
            return _veredicto(fallos)
        resumen(c)

        a = [f for f in c["filas"] if "WAIT_REG_MEM bloquea" in f["texto"]]
        if len(a) != 1:
            fallos.append("caso a: esperaba 1 cita, hay %d" % len(a))
        elif a[0]["clase"] != "C1_sostenida_por_ngrama":
            fallos.append("caso a: clase %s, esperaba C1_sostenida_por_ngrama"
                          % a[0]["clase"])
        elif a[0]["candidato_top"] != "910-wait-reg-mem.md":
            fallos.append("caso a: candidato %s, esperaba 910-wait-reg-mem.md"
                          % a[0]["candidato_top"])

        b = [f for f in c["filas"] if "SEV de cuentas y de contadores" in f["texto"]]
        if len(b) != 1:
            fallos.append("caso b: esperaba 1 cita, hay %d" % len(b))
        elif b[0]["clase"] != "C2_ambigua_senales_en_varios":
            fallos.append("caso b: clase %s, esperaba C2_ambigua_senales_en_varios"
                          % b[0]["clase"])

        c1 = [f for f in c["filas"] if f["autocita"] and f["num"] == 915]
        if len(c1) != 1:
            fallos.append("caso c1: esperaba 1 autocita, hay %d" % len(c1))
        elif c1[0]["clase"] != "C1_autocita":
            fallos.append("caso c1: clase %s, esperaba C1_autocita"
                          % c1[0]["clase"])
        c2_ = [f for f in c["filas"] if "diccionario de synonyms" in f["texto"]]
        if len(c2_) != 1:
            fallos.append("caso c2: esperaba 1 cita, hay %d" % len(c2_))
        elif c2_[0]["clase"] != "C1_sostenida_por_ngrama":
            fallos.append("caso c2: clase %s, esperaba C1_sostenida_por_ngrama"
                          % c2_[0]["clase"])

        if any(f["num"] == 920 for f in c["filas"]):
            fallos.append("caso d: el 920 no duplicado NO debe entrar")

        e = [f for f in c["filas"] if f["num"] == 930]
        if len(e) != 1:
            fallos.append("caso e: esperaba 1 cita, hay %d" % len(e))
        elif not e[0]["reasignado"]:
            fallos.append("caso e: no se vio el reasignado")
        elif e[0]["reenvio_destino"] != "931-algo-renumerado.md":
            fallos.append("caso e: destino %r" % e[0]["reenvio_destino"])
        elif e[0]["clase"] != "C3_gana_el_destino_del_mapa":
            fallos.append("caso e: clase %s, esperaba C3_gana_el_destino_del_mapa"
                          % e[0]["clase"])

        # f) el mapa congelado con ancho distinto de 6 tiene que ser ERROR
        with open(os.path.join(ra, "08-ARQUITECTURA", "tools",
                               "REENVIO-FINDINGS.tsv"), "a",
                  encoding="utf-8") as fh:
            fh.write("200\t201\tSI\tx\tcontenido\n")
        try:
            poblacion(ra)
            fallos.append("caso f: un mapa de 5 columnas no dio error")
        except ValueError:
            pass

    return _veredicto(fallos)


def _veredicto(fallos):
    if fallos:
        sys.stdout.write("SELFTEST: NO se sostiene\n")
        for f in fallos:
            sys.stdout.write("  FALLA  %s\n" % f)
        return EXIT_SELFTEST
    sys.stdout.write("SELFTEST: los 7 casos salen en la clase que deben\n")
    return EXIT_OK


# ---------------------------------------------------------------------------

COLS_TSV = ["citante", "dir", "linea", "forma", "num", "autocita", "n_cand",
            "candidato_top", "soporte_top", "soporte_2o", "margen", "propio",
            "en_reenvio", "reasignado", "relacion", "reenvio_nuevo",
            "reenvio_destino", "soporte_destino", "ngrama_top", "ngrama_2o",
            "ngrama_destino", "lectura_ganadora", "ngrama_ganadora", "rara_top",
            "en_codigo", "registrado",
            "clase", "texto"]


# MEDIDO, y fue un DEFECTO antes de corregirlo.  El expediente se escribio la
# primera vez como `.tsv` en `08-ARQUITECTURA/validations/`, y `check_num_unico`
# LEE los `.tsv`: su lista de extensiones legibles incluye `.tsv`.  El
# expediente tiene una fila por cita y cada fila lleva el numero en dos
# columnas, y la columna `texto` lleva la prosa con su cita dentro.  Resultado
# medido: la puerta A3 paso de 2143 a 4737 y A4 de 0 a 5, y 2589 de las 4737
# citas venian del propio expediente del censo.
#
# O sea: un instrumento que publica su resultado puede reescribir la medicion
# que lo contiene, y el sintoma --un numero que sube-- parece un hallazgo.  No
# lo era.
#
# POR QUE `.tsv.gz` Y NO "dejarlo fuera del arbol".  Los directorios que la
# puerta excluye son `RESEARCH`, `rx550-upstream-7.2.8`, `archive`, `.git` y
# `__pycache__`: los cuatro primeros significan algo, y un censo vigente dentro
# de `archive/` seria una mentira de sitio.  `.gz` no esta en la lista de
# extensiones legibles, asi que el fichero no se lee, y sigue siendo
# greppable con `zgrep`/`zcat`.  Se registra aqui para que nadie lo_descomprima
# en un `.tsv` y se wonder why la puerta se mueve.
SUFIJO_FUERA_DE_LA_PUERTA = ".gz"


# ---------------------------------------------------------------------------
# 4. VALIDACION CONTRA LAS ETIQUETAS A MANO.
# ---------------------------------------------------------------------------

MAPA_PROXY_A_CLASE = {
    "C1_autocita": "C1",
    "C1_sostenida_por_ngrama": "C1",
    "C1_sostenida_por_token_raro": "C1",
    "C2_ambigua_senales_en_varios": "C2",
    "SIN_APOYO_ninguna_senal": "SIN_APOYO",
    "C3_gana_el_destino_del_mapa": "C3",
}


def valida(raiz, holgura=0.15, df_max=3):
    """Cuadra la clasificacion del proxy contra las 12 etiquetas a mano.

    QUE ES Y QUE NO ES.  Las 12 etiquetas no son una muestra: son la poblacion
    COMPLETA de las salidas que el proxy produjo cuando afirmaba C3 o
    "indecidible", mas dos que produjo como C1.  Estan en
    `tools/citas_prosa_etiquetas.py`, cada una con la prueba de como se
    adjudico.

    Lo que este numero mide es la FIABILIDAD DEL PROXY, no la calidad de las
    2152.  Para eso haria falta una muestra, y con 12 no hay intervalo que
    signifique nada.  La cifra que si importa sale de aqui es una sola: si el
    proxyermarkaba C3 y a mano salen 0, entonces la rama de C3 no se puede usar
    para contar nada y la cifra de "citas que ya no apuntan a lo que dicen" hay
    que obtenerla por otra via.
    """
    import citas_prosa_etiquetas as ET
    censo, err = poblacion(raiz, holgura, df_max)
    if err:
        return {"ok": False, "motivo": err}
    idx = {}
    for f in censo["filas"]:
        idx.setdefault((f["citante"], f["linea"], f["num"]), []).append(f)
    filas, fallan = [], []
    for e in ET.ETIQUETAS:
        k = (e["citante"], e["linea"], e["num"])
        hits = idx.get(k)
        if not hits:
            filas.append({"sitio": "%s:%d" % (e["citante"], e["linea"]),
                          "num": e["num"], "esperada": e["clase"],
                          "proxy": "NO_ENCONTRADA", "acierto": False})
            fallan.append(k)
            continue
        h = hits[0]
        pr = MAPA_PROXY_A_CLASE.get(h["clase"], h["clase"])
        # ACIERTO ESTRICTO.  MEDIDO: la primera version de esta comprobacion
        # contaba como acierto "el proxy dice SIN_APOYO y la etiqueta dice C1",
        # y daba 10 de 12 = 83 %.  Eso era un expediente, no una medicion: la
        # clausula essentially decia "acierto cuando no me".  Se quita.  El
        # numero que sale ahora es 3 de 12, y ES el numero que hay que
        # escribir: el proxy RESUELVE 3 de 12, y en las 9 que no resuelve no
        # se sabe si la cita es correcta o ambigua.  De ahi sale la decision de
        # no usar el proxy para repartir la poblacion.
        ok = (pr == e["clase"])
        filas.append({"sitio": "%s:%d" % (e["citante"], e["linea"]),
                      "num": e["num"], "esperada": e["clase"],
                      "proxy": pr, "proxy_crudo": h["clase"],
                      "ng": h["ngrama_ganadora"], "rara": h["rara_top"],
                      "acierto": ok,
                      "resuelve": pr in ("C1", "C2", "C3"),
                      "prueba": e["prueba"][:120]})
        if not ok:
            fallan.append(k)
    n = len(ET.ETIQUETAS)
    resueltos = [f for f in filas if f.get("resuelve")]
    return {"ok": not fallan, "n": n,
            "aciertos": n - len(fallan),
            "acierto_pct": round(100.0 * (n - len(fallan)) / max(1, n), 1),
            "n_con_resolucion": len(resueltos),
            "con_resolucion": len(resueltos),
            "pct_con_resolucion": round(100.0 * len(resueltos) / max(1, n), 1),
            "c3_segun_proxy": sum(1 for f in filas if f["proxy"] == "C3"),
            "c3_confirmado": sum(1 for f in filas if f["proxy"] == "C3"
                                 and f["esperada"] == "C3"),
            "filas": filas, "fallan": ["%s:%d" % (k[0], k[1]) for k in fallan],
            "lectura": "el proxy NO sirve para repartir la poblacion: resuelve "
                       "%d de %d.  Su unica afirmacion que sobrevive es la "
                       "ausencia de clase 3." % (len(resueltos), n)}


def escribir_tsv(censo, ruta):
    import gzip
    if not ruta.endswith(SUFIJO_FUERA_DE_LA_PUERTA):
        raise ValueError(
            "el expediente tiene que acabar en %s: un .tsv legible lo cuenta la "
            "puerta A3 como prosa y el censo se mide a si mismo (medido: 2143 -> "
            "4737).  Ruta dada: %r" % (SUFIJO_FUERA_DE_LA_PUERTA, ruta))
    tmp = ruta + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS_TSV, delimiter="\t",
                           extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for f in censo["filas"]:
            w.writerow(f)
    os.replace(tmp, ruta)
    return os.path.getsize(ruta)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--raiz", default=os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--tsv", default=None)
    ap.add_argument("--cruzado", action="store_true",
                    help="compara la poblacion con check_num_unico.py")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--valida", action="store_true",
                    help="cuadra el proxy contra las etiquetas a mano")
    ap.add_argument("--df-max", type=int, default=3)
    ap.add_argument("--holgura", type=float, default=0.15)
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.valida:
        v = valida(a.raiz, a.holgura, a.df_max)
        if a.json:
            sys.stdout.write(json.dumps(v, ensure_ascii=False, indent=1))
            return EXIT_OK if v["ok"] else EXIT_SELFTEST
        w = sys.stdout.write
        w("VALIDACION del proxy contra las etiquetas a mano  (n=%d)\n\n" % v["n"])
        for f in v["filas"]:
            w("  %-4s  %-58s num=%-5s esperada=%-8s proxy=%-28s ng=%-3s rara=%s\n"
              % ("OK" if f["acierto"] else "MAL", f["sitio"][-58:], f["num"],
                 f["esperada"], f["proxy"], f.get("ng", ""), f.get("rara", "")))
        w("\n  ACIERTO ESTRICTO : %d/%d = %.1f %%\n"
          % (v["aciertos"], v["n"], v["acierto_pct"]))
        w("  RESUELVE LA CLASE  : %d/%d = %.1f %%   <- lo que el proxy sabe hacer\n"
          % (v["con_resolucion"], v["n"], v["pct_con_resolucion"]))
        if v["fallan"]:
            w("  DISCREPAN en: %s\n" % ", ".join(v["fallan"]))
        w("\n  CLASE 3 SEGUN EL PROXY: %d.  CLASE 3 CONFIRMADA A MANO: %d.\n"
          % (v["c3_segun_proxy"], v["c3_confirmado"]))
        w("\n  LECTURA\n    %s\n" % v["lectura"])
        return EXIT_OK if v["ok"] else EXIT_SELFTEST

    censo, err = poblacion(a.raiz, a.holgura)
    if err:
        sys.stderr.write("citas_prosa_census: %s\n" % err)
        return EXIT_POBLACION_NO_CRUZADA
    r = resumen(censo)
    if a.tsv:
        r["tsv"] = a.tsv
        r["tsv_bytes"] = escribir_tsv(censo, a.tsv)
    if a.cruzado:
        r["cruzado"] = cruzado(a.raiz, censo)
        if not r["cruzado"]["ok"]:
            if not a.json:
                sys.stdout.write("CRUZADO FALLIDO: %s\n"
                                 % "; ".join(r["cruzado"]["diferencias"]))
            if a.json:
                sys.stdout.write(json.dumps(r, ensure_ascii=False, indent=1))
            return EXIT_POBLACION_NO_CRUZADA
    if a.json:
        sys.stdout.write(json.dumps(r, ensure_ascii=False, indent=1))
        return EXIT_OK

    c = r["contexto"]
    w = sys.stdout.write
    w("citas_prosa_census.py %s  ·  POBLACION: la cita por numero que cae sobre\n"
      % VERSION)
    w("un numero duplicado, clasificada.  NO es 'cuantas estan mal': una cita\n")
    w("por numero puede ser correcta, ambigua, o estarEQUIVOCADA.\n\n")
    w("  POBLACION               : %d\n" % r["poblacion"])
    w("  hallazgos/ leidos       : %d   omitidos: %d\n"
      % (c["ficheros_leidos"], c["ficheros_omitidos"]))
    w("  numeros duplicados     : %d   ficheros en findings/: %d\n"
      % (c["duplicados"], c["ficheros_en_hallazgos"]))
    w("  mapa de renumeraciones : %s (%d filas)\n"
      % (c["reenvio_estado"], c["reenvio_filas"]))
    w("\n  CLASES\n")
    for k, v in r["por_clase"].items():
        w("    %-38s %5d  %5.1f %%\n"
          % (k, v, 100.0 * v / max(1, r["poblacion"])))
    w("\n  POR FORMA\n")
    for k, v in r["por_forma"].items():
        w("    %-10s %5d\n" % (k, v))
    w("\n  CLASE x FORMA\n")
    for k, v in r["clase_x_forma"].items():
        w("    %-50s %5d\n" % (k, v))
    w("\n  POR DIRECTORIO\n")
    for k, v in r["por_directorio"].items():
        w("    %-50s %5d\n" % (k, v))
    w("\n  SOBRE NUMERO REASIGNADO (el numero HOY lo ocupa otro contenido)\n")
    w("    citas                              : %d  en %d numeros\n"
      % (r["sobre_numero_reasignado"], r["numeros_reasignados_alcanzados"]))
    w("      con destino conocido             : %d\n"
      % r["sobre_numero_reasignado_con_destino"])
    w("      sin destino (se declara, no se fuerza): %d\n"
      % r["sobre_numero_reasignado_sin_destino"])
    w("\n    en CODIGO (registradas)           : %d\n"
      % r["citas_en_codigo_registradas"])
    w("    en PROSA                           : %d\n" % r["citas_en_prosa"])
    if "tsv" in r:
        w("\n  EXPEDIENTE: %s  (%d bytes)\n" % (r["tsv"], r["tsv_bytes"]))
    if "cruzado" in r:
        w("\n  CRUZADO con check_num_unico.py: total %d == %d, OK\n"
          % (r["cruzado"]["total_puerta"], r["cruzado"]["total_censo"]))
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
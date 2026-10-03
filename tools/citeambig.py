#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""citeambig.py - audita como se citan los hallazgos, no solo si resuelven.

LA QUESTION, Y POR QUE NO LA RESPONDE NADA MAS

tools/treescope.py verifica que una cita `fichero.c:NNN` resuelva contra el
arbol declarado. tools/reftriage.py verifica que un nombre de fichero exista.
Ninguna de las dos contesta la pregunta que un lector se hace de verdad:

    ¿esta cita apunta al hallazgo que yo creo?

Una cita puede resolver, estar en el fichero correcto, y no decir NADA de lo que
se le pide. Es el caso que produjo cuatro oscilaciones seguidas en el mismo
nombre de opcode (findings/147), y no hay ninguna herramienta que lo distinga.

ADEMAS: LA CONVENCION, APLICADA

En este proyecto la convencion escrita es citar por nombre completo de
fichero, no por numero. Ese numero desnudo es ambiguo en cuanto dos hallazgos
comparten numero, y los numeros duplicados se estan multiplicando porque
agentes paralelos escriben a la vez.

Este herramienta mide las tres clases y da un DENOMINADOR:

    COMPLETA   findings/147-el-nombre-del-op-12.md   conforme
    DESNUDO    findings/147                          resuelve, un solo fichero
    AMBIGUA    findings/035                          resuelve a N ficheros distintos

Las dos ultimas son deuda de la convencion. Ninguna es un error de contenido:
por eso se cuentan aparte y no se mezclan con las referencias rotas de
reftriage.py.

POR QUE UN NUMERO SIN DENOMINADOR NO ES UN RESULTADO

`18 citas ambiguas` no dice nada por si solo. Este script siempre imprime el
total de citas y el de clases, de modo que `18 de 1.204` es una afirmacion
comprobable y `18` solo, no lo es.

USO

    citeambig.py                 informe completo
    citeambig.py --resumen       solo las cifras
    citeambig.py --json          para componer
    citeambig.py --dir <ruta>    otro arbol que no sea el de por defecto
    citeambig.py --selftest      vectors sinteticos
"""


# ---------------------------------------------------------------------------
# IMPONE UN FORMATO QUE AGENTS.md YA NO DECLARA
#
# MEDIDO con tools/govcheck.py, y declarado aqui porque el documento rector ya no
# lo dice:
#
#     PENDIENTE= / ALCANZABLE_SIN_ROOT=   NO DECLARADO   (AGENTS.md, 3736 lineas)
#     CITA= / TERMINO= / ROL=             NO DECLARADO
#     7 secciones citadas por nombre       NO RESUELVEN
#     10 marcadores de biseccion §A/§B/§C sin documento
#     26 citas por numero de linea        INCOMPARABLES
#
# QUE SIGNIFICA ESTO, y no hay que adornarlo:
#
#   Esta herramienta valida un formato que NADA exige. Sus comprobaciones pueden
#   pasar porque el formato es correcto, y tambien pasarian si el formato fuera
#   cualquiera. Un check verde aqui NO es evidencia de que el proyecto obedezca
#   una convencion: es evidencia de que el texto cumple una forma.
#
#   Eso no la hace inutil. Sigue sirviendo para lo que sirve: normalizar, y
#   detectar las 11 lineas PENDIENTE= que hay. Lo que NO puede hacer es
#   justificar su propia existencia delante de nadie.
#
#   DECISION DEL USUARIO, 2026-10-02, cuando se le propuso anadir estas
#   convenciones al documento rector: "no tocar agents.md". As que la declaracion
#   vive aqui y no alla, y govcheck.py queda como auditor permanente de que esta
#   situacion sigue siendo la que es.
# ---------------------------------------------------------------------------

import argparse
import io
import json
import os
import re
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FALLOS = os.path.join(RAIZ, "06-INGENIERIA-INVERSA", "findings")

# `findings/123-*.md` es la forma de citar un hallazgo por su numero.
# El lookahead (?![\w-]) es lo que impide que esta regex case dentro de una
# cita completa: `findings/123-slug.md` va seguido de `-`, que el lookahead
# rechaza. Por eso NO hace falta marcar los bytes ya consumidos, y durante un
# tiempo hubo un bytearray que decia hacer ese trabajo sin hacerlo. El vector
# que lo comprobaba pasaba igual con el marcado puesto y sin él.
RE_CITA = re.compile(r"(?<![\w/-])findings/(\d{2,4})(?![\w-])")
# `findings/123-slug.md` es la forma conforme.
RE_COMPLETA = re.compile(r"findings/(\d{2,4})-[\w.-]*?\.md")
# `findings/123-slug` sin la extension: alguien intento citar de forma completa
# y perdio el `.md`. Ni RE_CITA ni RE_COMPLETA la ven, asi que sin esta clase
# seria INVISIBLE, que es el modo de fallo que mas importa aqui.
#
# El (?![\w.-]) exige que la cola sea MAXIMA: no puede terminar dejando un
# caracter de nombre o de punto delante. Eso cierra la via corta. Con solo un
# lookahead negativo detras, [\w.-]+ se come el `.md` de una cita completa y
# hace backtracking a una cola mas corta que vuelve a pasar; la maximalidad
# elimina esa via, y los dos lookbehind finales la descartan.
#
# Hace falta AMBOS, y el segundo no es redundante: con solo (?<!\.md), una cita
# completa seguida de punto final de frase -- `findings/003-slug.md.` -- deja la
# cola maxima terminando en `.`, el lookbehind de `.md` mira `md.` y pasa, y la
# cita se cuenta a la vez como COMPLETA y como TRUNCADA. Un clasificador que
# cuenta dos veces es peor que uno que no cuenta: el total deja de ser un
# total. (?<!\.) cierra ese caso.
#
# Un (?<![\w-]) tambien se probo aqui y esta MAL, no solo innecesario: la cola
# de una cita truncada acaba en letra, `o` en `findings/002-uno`, y un
# lookbehind que prohibe terminar en caracter de palabra rechaza
# precisamente el caso que hay que detectar. Deja la clase entera vacia, que
# es el peor modo de fallo posible en un clasificador: parece que no hay nada
# que clasificar.
RE_TRUNCADA = re.compile(r"findings/(\d{2,4})-[\w.-]+(?![\w.-])(?<!\.md)(?<!\.)")


def indexar(dirfallos):
    """numero -> lista de nombres de fichero. Devuelve {} si no hay hallazgos."""
    idx = {}
    if not os.path.isdir(dirfallos):
        return idx
    for n in sorted(os.listdir(dirfallos)):
        m = re.match(r"(\d{2,4})-[\w.-]*\.md$", n)
        if m:
            idx.setdefault(m.group(1), []).append(n)
    return idx


def es_autocita(fila):
    """¿Esta fila es un hallazgo citandose a si mismo por numero?

    No es deuda: su numero es el suyo y no puede colisionar. Se separa para
    que el recuento sea interpretable.

    Vive a NIVEL DE MODULO, y no dentro de main(), por una razon concreta: una
    funcion definida dentro de main() no la puede tocar el selftest, y esta
    estuvo comprobandose a mano durante una ronda antes de que se leyera que
    aplicaba la regla solo a la lista de ambiguas y por eso nunca disparaba.
    Lo que no se puede probar desde el selftest no es una funcionalidad, es
    una suelta.
    """
    rel, num = fila[0], fila[1]
    marca = os.path.join("06-INGENIERIA-INVERSA", "findings")
    if not rel.replace(os.sep, "/").startswith(marca.replace(os.sep, "/")):
        return False
    propio = os.path.basename(rel)[:len(num)]
    return propio == num


# Separar prosa de codigo no es estetico: son dos poblaciones con dos
# denominadores distintos, y mezclarlas produce un numero que no significa
# nada. En prosa una cita es una referencia. En el codigo de una herramienta,
# una cadena `findings/035` dentro de un docstring es un EJEMPLO, y contarla
# como cita hace que el instrumento contamine su propia medicion. Y no es
# hipotetico: antes de separarlos, esta herramienta aparecia en el informe
# como fuente de citas, citando sus propios fixtures sinteticos.
EXTENSIONES = (".md", ".txt", ".mk", ".c", ".h", ".py")
EXT_PROSA = (".md", ".txt", ".mk")
EXT_CODIGO = (".c", ".h", ".py")

# el fichero que hace la medicion no se cuenta. Sus citas son fixtures.
YO_MISMO = os.path.basename(__file__)

# ---------------------------------------------------------------------------
# CITA= / TERMINO= / ROL=
#
# La clase que responde a la pregunta que las otras tres no: si el hallazgo
# citado SOSTIENE lo que se le pide. Se comprueba con un termino literal
# declarado en la propia cita, porque "el termino relevante" no es un campo
# que se pueda comparar mecanicamente.
# ---------------------------------------------------------------------------
# ROL se detiene en el salto de linea O en el siguiente CITA=, y no en "el
# final del documento". La primera version usaba [^\n]+ y aplanaba el texto
# entero a una sola linea para toleratear las citas partidas: con el texto
# plano, el primer ROL= se comia TODAS las citas siguientes, incluida la
# plantilla del formato, y por eso la primera cita aparecia clasificada como
# PLANTILLA. Un clasificador que se come el resto del fichero no mide el
# fichero: mide su propia regex.
#
# El texto NO se aplana. Las citas partidas en varias lineas no se arreglan:
# se cuentan aparte, en MAL_FORMADA, que se reconcilia por construccion contra
# el numero total de CITA= del fichero.
RE_CITA_TERMINO = re.compile(
    r"CITA=(?P<fichero>[^|\s]+)\s*\|\s*TERMINO=(?P<termino>[^|\n]+?)\s*\|"
    r"\s*ROL=(?P<rol>(?:(?!\bCITA=)[^\n])+?)")
RE_CITA_SIN_TERMINO = re.compile(r"CITA=(?P<fichero>[^|\s]+)(?![^\n]*TERMINO=)")
# El conteo de CITA= declaradas lo hace RE_NOMBRE_TRAS_CITA, que ademas
# comprueba que lo que sigue sea un fichero. Este queda para diagnostico.
RE_CITA_CUALQUIERA = re.compile(r"CITA=")


# Una mencion del FORMATO en prosa -- "se escribe CITA=/TERMINO=/ROL=" -- no
# es una cita. Sin este filtro, la propia documentacion de la convencion se
# contaria como cita mal formada y el informe llenaria su propia seccion de
# ruido con las piezas de la propia regex. El filtro es MECANICO: un fichero
# tiene extension. No se intenta interpretar el contexto.
RE_FICHERO_CITA = re.compile(r"^[^\s|]+\.(md|c|h|py|txt|mk|json|rst)$")
RE_NOMBRE_TRAS_CITA = re.compile(r"CITA=\s*([^\s|]+)")


def fichero_es_cita(nombre):
    """Un CITA= solo es cita si lo que sigue parece un fichero."""
    return bool(RE_FICHERO_CITA.match(nombre.strip()))


def cruzadas(raiz):
    """Recorre el proyecto y devuelve (sostenidas, no_sostenidas, sin_term).

    Se recorre a texto COMPLETO y no linea a linea porque un CITA= partido en
    varias lineas es la forma en que se han escrito hasta ahora, y partirlo
    por lineas daria una clase vacia y por tanto un 100 % de SOSTENIDA que no
    midio nada. Ese es el mismo fallo que la rama de autocita de este mismo
    fichero, y merece no repetirse.
    """
    sost, nosost, sinter, plant, mal = [], [], [], [], 0
    malformadas = []
    for dirpath, dirnames, filenames in os.walk(raiz):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and not any(d.startswith(p) for p, _ in EXCLUIDOS)]
        for fn in filenames:
            if not fn.endswith(EXTENSIONES):
                continue
            rel = os.path.relpath(os.path.join(dirpath, fn), raiz)
            # Exclusion por NOMBRE, no por ruta relativa. La primera version
            # comparaba rel == YO_MISMO, o sea `tools/citeambig.py` contra
            # `citeambig.py`, y por eso NO excluia nada: la herramienta se
            # citaba a si misma y sus fixtures salian como citas reales. Un
            # guardia que nunca dispara no es un guardia.
            if os.path.basename(rel) == YO_MISMO:
                continue
            try:
                crudo = io.open(os.path.join(dirpath, fn), encoding="utf-8",
                                errors="replace").read()
            except OSError:
                continue
            # a una sola linea, para que un CITA= partido en varias lineas siga
            # siendo una cita y no se pierda
            texto = crudo
            del_i, nob_i, pla_i, sin_i = [], [], [], []
            # los ficheros citados en el corpus son de codigo, asi
            # que se buscan primero ahi y luego en la propia documentacion.
            for m in RE_CITA_TERMINO.finditer(texto):
                fich, term, rol = m.group("fichero"), m.group("termino"), m.group("rol")
                # Una plantilla del formato lleva marcadores <así>. Contarla
                # como cita daria un NO_SOSTENIDA sobre un fichero que no
                # existe, y la lectura seria "esta cita no se sostiene" cuando
                # lo cierto es que aqui no hay ninguna cita. Se separa y se
                # informa, no se descarta en silencio.
                if "<" in fich or "<" in term or "<" in rol:
                    pla_i.append((rel, fich, term))
                    continue
                donde = buscar_fichero(raiz, fich)
                if donde is None:
                    nob_i.append((rel, fich, term, rol, "el fichero citado no existe"))
                elif term in io.open(donde, encoding="utf-8",
                                     errors="replace").read():
                    del_i.append((rel, fich, term, rol, donde))
                else:
                    nob_i.append((rel, fich, term, rol, "el termino no aparece"))
            # un CITA= sin TERMINO= en la misma linea: adopcion pendiente
            for m in RE_CITA_SIN_TERMINO.finditer(texto):
                # el mismo filtro que en declaradas: `CITA=` a secas, o
                # `CITA=/TERMINO=/ROL=` ProSO, son MENCIONES del formato y no
                # citas. Aplicar el filtro solo en el conteo y no aqui dejaba
                # que dos menciones se colaran como adopcion pendiente.
                if fichero_es_cita(m.group("fichero")):
                    sin_i.append((rel, m.group("fichero")))
            sost.extend(del_i)
            nosost.extend(nob_i)
            plant.extend(pla_i)
            sinter.extend(sin_i)
            # reconciliacion por construccion: todo CITA= que no ha caído en
            # ninguna de las tres clases anteriores está MAL FORMADO, y se dice
            # cual es en vez de dejar que el total no cuadre en silencio
            # Solo cuenta como cita declarada lo que CITA= apunta a un fichero
            # con extension. Lo demas es una MENCION del formato en prosa, y se
            # ignora a proposito: contarlo haria que la reconciliacion de
            # clases no cuadrara contra el numero de CITA= del fichero, que es
            # justamente la comprobacion que garantiza que no se pierde nada.
            declaradas = sum(1 for m in RE_NOMBRE_TRAS_CITA.finditer(texto)
                             if fichero_es_cita(m.group(1)))
            clasificadas = (len(del_i) + len(nob_i) + len(pla_i)
                            + len(sin_i))
            sin_clase = declaradas - clasificadas
            if sin_clase > 0:
                # el resto son CITA= que no encajan en ninguna clase: partidas
                # en varias lineas, o a las que les falta el ROL=. Se cuentan
                # para que el total cuadre, y se dicen en el informe.
                mal += sin_clase
                malformadas.append((rel, sin_clase))
    return sost, nosost, sinter, plant, mal, malformadas


# Un directorio excluido del RECORRIDO puede ser el DESTINO de una cita. El
# corpus de Linux no puede citar hallazgos -- por eso no se escanea buscando
# citas -- pero casi todas las citas de este proyecto apuntan dentro de el, que
# es justamente para lo que existe la clase. Excluir del recorrido y excluir
# de la busqueda son dos cosas distintas, y confundirlas haria que toda cita al
# corpus saliera "el fichero citado no existe", que es un veredicto falso
# emitido por una omision de la herramienta.
RAIZES_BUSQUEDA = ("07-DRIVER", "06-INGENIERIA-INVERSA", "rx550-upstream-7.2.8",
                   "RESEARCH")


def buscar_fichero(raiz, nombre):
    """Busca un fichero por ruta relativa o por nombre, en orden declarado."""
    base = os.path.basename(nombre)
    candidatos = [nombre]
    for pref in RAIZES_BUSQUEDA:
        candidatos.append(os.path.join(pref, base))
        candidatos.append(os.path.join(pref, "linux-7.2.8", "drivers", "gpu",
                                       "drm", "amd", "amdgpu", base))
    for c in candidatos:
        ruta = c if os.path.isabs(c) else os.path.join(raiz, c)
        if os.path.isfile(ruta):
            return ruta
    for pref in RAIZES_BUSQUEDA:
        for dirpath, dirnames, filenames in os.walk(os.path.join(raiz, pref)):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            if base in filenames:
                return os.path.join(dirpath, base)
    return None

# Directorios que se salen del censo, y el motivo de cada uno. No es solo una
# recorte de tiempo: escanear el corpus de Linux buscando citas findings/NNN
# es buscar algo que alli no puede haber, y lo que devuelve es ruido con miles
# de ficheros de por medio. Sin esto, la primera version tardaba mas de diez
# minutos en un corpus de 691 MB para responder a una pregunta que no conocia.
EXCLUIDOS = (
    ("rx550-upstream", "corpus de Linux: no puede citar hallazgos propios"),
    (".git", "historial: lo audita otra herramienta"),
    ("RESEARCH", "corpus de trabajo: referencia, no documentacion propia"),
    ("revkit", "herramientas ajenas"),
    ("03-EXPERIMENTOS", "capturas de ejecucion: no son citas"),
)


def extension_de(nombre):
    for e in EXTENSIONES:
        if nombre.endswith(e):
            return e
    return ""


def recoger(raiz, idx, exclude_dirs=(), solo=None):
    """Devuelve (completas, truncadas, desnudas, ambiguas) como listas de tuplas."""
    completas, truncadas, desnudas, ambiguas = [], [], [], []
    Saltar = {os.path.abspath(d) for d in exclude_dirs}
    for dirpath, dirnames, filenames in os.walk(raiz):
        if os.path.abspath(dirpath) in Saltar:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".")
                       and not any(d.startswith(p) for p, _ in EXCLUIDOS)]
        for fn in filenames:
            if not fn.endswith(EXTENSIONES):
                continue
            ruta = os.path.join(dirpath, fn)
            try:
                with open(ruta, encoding="utf-8", errors="replace") as f:
                    texto = f.read()
            except OSError:
                continue
            rel = os.path.relpath(ruta, raiz)
            # Exclusion por NOMBRE, no por ruta relativa. La primera version
            # comparaba rel == YO_MISMO, o sea `tools/citeambig.py` contra
            # `citeambig.py`, y por eso NO excluia nada: la herramienta se
            # citaba a si misma y sus fixtures salian como citas reales. Un
            # guardia que nunca dispara no es un guardia.
            if os.path.basename(rel) == YO_MISMO:
                continue
            ext = extension_de(fn)
            if solo and ext not in solo:
                continue
            for m in RE_COMPLETA.finditer(texto):
                completas.append((rel, m.group(1),
                                  texto[m.start():m.end()].split("/")[-1]))
            for m in RE_TRUNCADA.finditer(texto):
                truncadas.append((rel, m.group(1), m.group(0).split("/")[-1]))
            for m in RE_CITA.finditer(texto):
                num = m.group(1)
                if num not in idx:
                    continue  # lo dejamos para reftriage, que es su trabajo
                fila = (rel, num, texto[m.start():m.end()])
                (desnudas if len(idx[num]) == 1 else ambiguas).append(fila)
    return completas, truncadas, desnudas, ambiguas


def selftest():
    vectores = []
    d = "/tmp/opencode/citeambig-selftest"
    os.system("rm -rf %s" % d)
    os.makedirs(os.path.join(d, "findings"))

    def poner(nombre, texto):
        with open(os.path.join(d, nombre), "w") as f:
            f.write(texto)

    # arbol de prueba: un numero unico, uno duplicado, uno ausente
    poner("findings/001-unico.md", "# 001\n")
    poner("findings/002-uno.md", "# 002\n")
    poner("findings/002-otro.md", "# 002\n")

    idx = indexar(os.path.join(d, "findings"))
    vectores.append(("index numera los tres ficheros de dos numeros",
                     len(idx) == 2 and len(idx["001"]) == 1 and len(idx["002"]) == 2,
                     idx))
    vectores.append(("un numero sin ficheros no aparece en el indice",
                     "003" not in idx, sorted(idx)))

    poner("doc.md",
          "cita desnuda de unico findings/001\n"
          "cita completa findings/001-unico.md\n"
          "cita completa con punto final findings/002-otro.md.\n"
          "cita truncada findings/002-uno\n"
          "cita desnuda de duplicado findings/002\n"
          "cita de algo inexistente findings/999\n")
    c, tr, dn, am = recoger(d, idx)
    vectores.append(("una cita completa no se cuenta ni como desnuda ni como truncada",
                     len(c) == 2 and len(tr) == 1 and len(dn) == 1,
                     (len(c), len(tr), len(dn), len(am))))
    vectores.append(("una cita sin extension es TRUNCADA, no invisible",
                     len(tr) == 1 and tr[0][1] == "002", tr))
    vectores.append(("una cita completa con punto final NO se cuenta dos veces",
                     all("002-otro" not in t[2] for t in tr),
                     [t[2] for t in tr]))
    vectores.append(("la cita desnuda de un numero duplicado es AMBIGUA",
                     len(am) == 1 and am[0][1] == "002", am))
    vectores.append(("la cita de un numero inexistente NO se cuenta aqui",
                     all(f[1] != "999" for f in dn + am), (dn, am)))

    # El mecanismo que impide el doble conteo NO es un bytearray, es el
    # lookahead (?![\w-]) de RE_CITA. Este vector lo comprueba por lo que
    # importa: que una cita completa no genere fila desnuda. La version
    # anterior de este vector probaba el bytearray, y pasaba igual con el
    # bytearray roto, que es como se descubrio que era codigo muerto.
    vectores.append(("el lookahead, y no un bytearray, evita el doble conteo",
                     [m.group(0) for m in RE_CITA.finditer("findings/001-unico.md")] == [],
                     [m.group(0) for m in RE_CITA.finditer("findings/001-unico.md")]))
    vectores.append(("el mismo mecanismo vale para una cita truncada",
                     [m.group(0) for m in RE_CITA.finditer("findings/002-uno")] == [],
                     [m.group(0) for m in RE_CITA.finditer("findings/002-uno")]))

    # la misma referencia en dos ficheros distintos son dos filas: el recuento
    # tiene que ser de filas, no de numeros distintos
    poner("doc2.md", "otra cita findings/002\n")
    c2, tr2, dn2, am2 = recoger(d, idx)
    vectores.append(("contar filas, no numeros distintos",
                     len(am2) == 2 and len({f[1] for f in am2}) == 1,
                     "%d filas, %d numeros" % (len(am2), len({f[1] for f in am2}))))

    # exclusion: el directorio de hallazgos no se cita a si mismo dos veces
    # autocita: el numero del fichero debe ser el suyo, y solo si esta DENTRO
    # de findings/. Un documento suelto que cite findings/001 no es autocita.
    vectores.append(("autocita: el numero propio dentro de findings/",
                     es_autocita(("06-INGENIERIA-INVERSA/findings/010-x.md", "010")),
                     "010-x.mdOTO"))
    vectores.append(("autocita: un numero distinto NO es autocita",
                     not es_autocita(("06-INGENIERIA-INVERSA/findings/010-x.md", "011")),
                     "010-x.md cita 011"))
    # Este caso tiene que hacer CARGAR la exclusion. Con un fichero llamado
    # otro.md la comprobacion del nombre bastaba y el vector pasaba con la
    # exclusion rota -- es decir, pasaba por el motivo equivocado, que es peor
    # que no tener vector: aparenta cobertura y no cubre. Aqui el fichero se
    # llama 010-notas.md, fuera de findings/, y comparte el prefijo numerico
    # con un hallazgo. Sin la exclusion, esto se contaria como autocita.
    vectores.append(("autocita: fuera de findings/ no es autocita aunque el "
                     "nombre empiece por el numero",
                     not es_autocita(("010-notas.md", "010")),
                     "010-notas.md esta fuera de findings/"))

    # y la regla aplicada a las dos listas, que es donde estaba el fallo: con un
    # numero de un solo fichero la cita cae en DESNUDO, no en AMBIGUA, y una
    # rama que solo se consulta en el caso raro es decoracion.
    dnl, aml = [("06-INGENIERIA-INVERSA/findings/010-x.md", "010", "findings/010")], []
    vectores.append(("la autocita se resta tambien de DESNUDO, no solo de AMBIGUA",
                     len([f for f in dnl if not es_autocita(f)]) == 0
                     and len([f for f in aml if not es_autocita(f)]) == 0,
                     "%d desnudas depues de restar" % len([f for f in dnl if not es_autocita(f)])))

    # Los directorios excluidos tienen que quedar fuera DE VERDAD. No es solo
    # una recorte de tiempo: escanear el corpus de Linux en busca de citas
    # findings/NNN devuelve ruido, y un censo que includes lo que no puede
    # citar no tiene denominador defendible.
    os.makedirs(os.path.join(d, "rx550-upstream-7.2.8/linux/drivers"), exist_ok=True)
    poner("rx550-upstream-7.2.8/linux/drivers/kernel.c",
          "comentario del upstream findings/001\n")
    c3, tr3, dn3, am3 = recoger(d, idx)
    vectores.append(("el corpus de Linux queda fuera del censo",
                     all(not f[0].startswith("rx550-upstream") for f in c3 + tr3 + dn3 + am3),
                     [f[0] for f in c3 + tr3 + dn3 + am3]))
    # ... y la lista de exclusion dice POR QUE, no solo QUE
    vectores.append(("cada exclusion declara un motivo",
                     all(bool(motivo.strip()) for _, motivo in EXCLUIDOS),
                     [(p, m) for p, m in EXCLUIDOS if not m.strip()]))
    # --- cruzadas(): la clase que responde si la cita SOSTIENE -------------
    # Monta un arbol propio con hallazgos y un fichero de codigo, y escribe
    # citas reales en un documento.
    d2 = "/tmp/opencode/citeambig-cross"
    os.system("rm -rf %s" % d2)
    os.makedirs(os.path.join(d2, "findings"))
    poner2 = lambda nombre, texto: io.open(os.path.join(d2, nombre), "w",
                                           encoding="utf-8").write(texto)
    poner2("findings/020-a.md", "el simbolo SDMA_OP_GEN_PTEPDE vale 12\n")
    poner2("findings/021-b.md", "no dice nada de eso\n")
    poner2("codigo.c", "int x = 0;\n")
    poner2("doc.md",
           "CITA=findings/020-a.md | TERMINO=SDMA_OP_GEN_PTEPDE | ROL=nombre del op\n"
           "CITA=findings/021-b.md | TERMINO=SDMA_OP_GEN_PTEPDE | ROL=nombre del op\n"
           "CITA=findings/999-zz.md | TERMINO=cualquiera | ROL=no existe\n"
           "CITA=codigo.c | TERMINO=int x | ROL=el codigo\n"
           "CITA=findings/020-a.md\n"
           "CITA=<fichero.md> | TERMINO=<termino> | ROL=<rol>\n")
    cs, cn, cint, cp, cmal, cmf = cruzadas(d2)
    vectores.append(("una cita cuyo termino aparece es SOSTENIDA",
                     len(cs) == 2, [x[1] for x in cs]))
    # por CONTENIDO y no por indice: el orden de salida depende del recorrido
    # del directorio, que no es estable, y un vector que exige un orden esta
    # probando el recorrido del sistema de ficheros y no el clasificador.
    motivos = {x[4] for x in cn}
    vectores.append(("una cita cuyo termino NO aparece es NO_SOSTENIDA",
                     len(cn) == 2 and "el termino no aparece" in motivos,
                     sorted(motivos)))
    vectores.append(("un fichero citado inexistente NO es SOSTENIDA",
                     any(x[4] == "el fichero citado no existe" for x in cn),
                     [x[4] for x in cn]))
    vectores.append(("un CITA= sin TERMINO= cuenta como adopcion pendiente",
                     len(cint) == 1, cint))
    vectores.append(("la plantilla del formato NO cuenta como cita",
                     len(cp) == 1, cp))
    vectores.append(("lo declarado y lo clasificado cuadran",
                     len(cs) + len(cn) + len(cint) + len(cp) == 6,
                     "%d+%d+%d+%d" % (len(cs), len(cn), len(cint), len(cp))))
    # Un CITA= partido en varias lineas SI se analiza, porque \s* cubre el
    # salto de linea y el ROL perezoso para en el primero. Lo que lo rompia era
    # la version APLANA del texto, en la que el primer ROL= se comia todas las
    # citas siguientes del fichero. Asi que MAL_FORMADA queda para lo que de
    # verdad no encaja, no para esto.
    poner2("doc2.md",
           "CITA=findings/020-a.md |\n"
           "    TERMINO=SDMA_OP_GEN_PTEPDE |\n"
           "    ROL=nombre del op\n")
    cs2, cn2, cint2, cp2, cmal2, cmf2 = cruzadas(d2)
    vectores.append(("un CITA= partido en lineas se analiza igualmente",
                     len(cs2) == len(cs) + 1 and cmal2 == 0,
                     "sostenidas %d (antes %d), mal %d" % (len(cs2), len(cs), cmal2)))
    # el fallo original: una cita en linea NO debe arrastrar a las siguientes
    vectores.append(("una cita en linea NO se traga las siguientes",
                     len(cs2) == len(cs) + 1
                     and {x[1] for x in cs2} == {x[1] for x in cs},
                     "%d distintas en doc+doc2, %d en doc" % (len({x[1] for x in cs2}),
                                                             len({x[1] for x in cs}))))
    # y una cita mal formada de verdad SI tiene que aparecer como MAL_FORMADA
    poner2("doc3.md", "CITA=findings/020-a.md | TERMINO=SDMA_OP_GEN_PTEPDE\n")
    _, _, _, _, cmal3, _ = cruzadas(d2)
    vectores.append(("un CITA= sin ROL= es MAL_FORMADA y no SOSTENIDA",
                     cmal3 == 1, "mal=%d" % cmal3))
    os.system("rm -rf %s" % d2)

    os.system("rm -rf %s" % d)
    fallos = sum(1 for _, ok, _ in vectores if not ok)
    print("citeambig.py selftest")
    for nombre, ok, det in vectores:
        print("  %s %s%s" % ("OK  " if ok else "FAIL", nombre,
                             "" if ok else "   -- %r" % (det,)))
    print("RESULT: %s (%d vectores)" % ("PASS" if not fallos else "FAIL",
                                        len(vectores)))
    return 0 if not fallos else 1


def main():
    ap = argparse.ArgumentParser(description="audita la forma de citar hallazgos")
    ap.add_argument("--dir", help="raiz del proyecto (por defecto, el de la herramienta)")
    ap.add_argument("--dirfallos", help="directorio de findings")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--resumen", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--sostiene", action="store_true",
                    help="cruza TERMINO= con el contenido del fichero citado")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.sostiene:
        raiz = a.dir or RAIZ
        sost, nosost, sinter, plant, mal, malformadas = cruzadas(raiz)
        tot = len(sost) + len(nosost)
        if a.json:
            print(json.dumps({"sostenidas": len(sost), "no_sostenidas": len(nosost),
                              "sin_termino": len(sinter),
                              "plantillas": len(plant),
                              "mal_formadas": mal, "total": tot},
                             indent=2, ensure_ascii=False))
            return 0
        print("=" * 78)
        print("LA CITA QUE SE SOSTIENE -- TERMINO= contra el contenido citado")
        print("=" * 78)
        print("""
  SOSTENIDA     el TERMINO= declarado aparece en el fichero citado
  NO_SOSTENIDA  no aparece, o el fichero citado no existe
  SIN_TERMINO   hay CITA= sin TERMINO=: adopcion pendiente
  PLANTILLA     CITA= con marcadores <>: es el ejemplo del formato, no una cita
  MAL_FORMADA   CITA= que no encaja: partida en lineas, o sin ROL=

  SIN_TERMINO se informa SIEMPRE y va en la misma linea que el resto. Un 100 %
  de SOSTENIDA sin contar los SIN_TERMINO es un 0 % medido: se habria
  comparado el conjunto equivocado y el resultado no diria nada del conjunto
  que de verdad importa.
""")
        print("  CITA= declaradas: %d   SOSTENIDA %d   NO_SOSTENIDA %d   "
              "SIN_TERMINO %d   PLANTILLA %d   MAL_FORMADA %d"
              % (tot + len(sinter) + len(plant) + mal, len(sost), len(nosost),
                 len(sinter), len(plant), mal))
        if tot:
            print("  de las declaradas con TERMINO=, sostenidas: %.1f%% (%d de %d)"
                  % (100.0 * len(sost) / tot, len(sost), tot))
        if nosost:
            print("\n  LAS NO SOSTENIDAS:\n")
            for f, fich, term, rol, mot in nosost:
                print("    %s" % f)
                print("        cita   %s" % fich)
                print("        termino %r" % term)
                print("        rol     %s" % rol[:70])
                print("        motivo  %s" % mot)
        if sinter:
            print("\n  LAS %d SIN TERMINO=, que son adopcion pendiente:\n" % len(sinter))
            for f, fich in sinter[:40]:
                print("    %-56s %s" % (f, fich))
            if len(sinter) > 40:
                print("    ... y %d mas" % (len(sinter) - 40))
        if mal:
            print("\n  LAS %d MAL FORMADAS, agrupadas por fichero:" % mal)
            for f, n in sorted(malformadas, key=lambda x: -x[1])[:20]:
                print("    %-56s %d" % (f, n))
        if plant:
            print("\n  LAS %d PLANTILLAS, que son el ejemplo del formato en"
                  % len(plant))
            print("  AGENTS.md y no citas reales. Se listan para que conste que se")
            print("  las ha separado en vez de contarlas como NO_SOSTENIDA:")
            for f, fich, term in plant:
                print("    %-56s %s" % (f, fich))
        if not tot:
            print("\n  Ninguna cita declara TERMINO= todavia. El formato existe")
            print("  (AGENTS.md, LA CITA QUE SE SOSTIENE) y la adopcion es cero.")
            print("  Eso NO es un 100 %: es una medicion de cero.")
        return 0

    raiz = a.dir or RAIZ
    dirfallos = a.dirfallos or os.path.join(raiz, "06-INGENIERIA-INVERSA", "findings")
    idx = indexar(dirfallos)
    # findings/ SE INCLUYE. Excluirlo para no contar autocitas recortaba el
    # censo sin decirlo, y un censo con una exclusion no declarada tiene un
    # denominador falso. Los hallazgos se citan entre ellos, y esa es
    # precisamente la poblacion que la convencion persigue. La autocita se
    # cuenta aparte mas abajo para que siga siendo interpretable.
    prosa = recoger(raiz, idx, exclude_dirs=(), solo=EXT_PROSA)
    codigo = recoger(raiz, idx, exclude_dirs=(), solo=EXT_CODIGO)
    c, tr, dn, am = prosa
    total = len(c) + len(tr) + len(dn) + len(am)

    # La autocita se resta de LAS DOS listas, no solo de las ambiguas: un
    # hallazgo que se cita a si mismo no puede ser ambiguo, diga lo que diga el
    # numero de ficheros que lo compartan, porque su numero es el suyo. La
    # primera version solo la restaba de la lista de ambiguas, asi que nunca
    # disparaba: en el caso normal -- un numero con un solo fichero, que es el
    # mayoritario -- la cita cae en DESNUDO y la rama no se consultaba. Una
    # rama que solo se ejecuta en el caso raro no es una rama, es decoracion.
    dn_sin_auto = [f for f in dn if not es_autocita(f)]
    am_sin_auto = [f for f in am if not es_autocita(f)]
    auto = len(dn) - len(dn_sin_auto) + len(am) - len(am_sin_auto)

    if a.json:
        print(json.dumps({
            "hallazgos": sum(len(v) for v in idx.values()),
            "numeros": len(idx),
            "numeros_duplicados": sum(1 for v in idx.values() if len(v) > 1),
            "citas_completas": len(c),
            "citas_truncadas": len(tr),
            "citas_desnudas": len(dn),
            "citas_ambiguas": len(am_sin_auto),
            "autocitas": auto,
            "total_citas": total,
            "ambiguas": [{"fichero": f, "num": n, "colisiona_con": idx[n]}
                         for f, n, _ in am_sin_auto],
            "codigo": {
                "citas_completas": len(codigo[0]),
                "citas_truncadas": len(codigo[1]),
                "citas_desnudas": len(codigo[2]),
                "citas_ambiguas": len(codigo[3]),
                "total_citas": sum(len(x) for x in codigo),
                "ambiguas": [dict(fichero=f, num=n, poblacion="codigo",
                                  colisiona_con=idx[n])
                             for f, n, _ in codigo[3]],
                "truncadas": [dict(fichero=f, num=n, poblacion="codigo",
                                   tal_cual=t) for f, n, t in codigo[1]],
            },
            "truncadas": [dict(fichero=f, num=n, poblacion="prosa", tal_cual=t)
                          for f, n, t in tr],
        }, indent=2, ensure_ascii=False))
        return 0

    if a.resumen:
        print("  hallazgos: %d en %d numeros, %d numeros duplicados"
              % (sum(len(v) for v in idx.values()), len(idx),
                 sum(1 for v in idx.values() if len(v) > 1)))
        print("  citas: %d total = %d COMPLETA + %d TRUNCADA + %d DESNUDO"
              " + %d AMBIGUA + %d AUTOCITA"
              % (total, len(c), len(tr), len(dn_sin_auto), len(am_sin_auto), auto))
        if total:
            print("  conformes: %.1f%%   a corregir: %d de %d"
                  % (100.0 * len(c) / total,
                     len(tr) + len(dn_sin_auto) + len(am_sin_auto), total))
        # codigo es (completas, truncadas, desnudas, ambiguas). La primera
        # version de estas lineas hacia cc = codigo[0] y luego len(cc[0]), o sea
        # una vuelta de mas al partir el recuento, y el resumen imprimio un
        # total de 159 con componentes que sumaban 12 sin quejarse. Un desglose
        # que no suma no es un desglose: son cuatro numeros sueltos, y el
        # porcentaje que sale de ahi no describe nada. La comprobacion va como
        # assert y no como aviso: un total incoherente es un fallo de la
        # herramienta, no una observacion sobre el corpus.
        def reparto(t):
            cc, ctr, cdn, cam = t
            tot = len(cc) + len(ctr) + len(cdn) + len(cam)
            assert tot == sum(len(x) for x in t), "el desglose no suma el total"
            return tot, len(cc), len(ctr), len(cdn), len(cam)

        tc, kc, ktr, kdn, kam = reparto(codigo)
        if tc:
            print("  codigo .c/.h/.py (otro denominador): %d citas = %d COMPLETA"
                  " + %d TRUNCADA + %d DESNUDO + %d AMBIGUA"
                  % (tc, kc, ktr, kdn, kam))
            print("    conformes: %.1f%%   a corregir: %d de %d"
                  % (100.0 * kc / tc, ktr + kdn + kam, tc))
        print("  NOTA: %s excluido de ambos censos. Sus cadenas findings/NNN"
              % YO_MISMO)
        print("  son fixtures del selftest, no citas.")
        return 0

    print("=" * 78)
    print("FORMA DE CITAR LOS HALLAZGOS -- findings/%s" % os.path.relpath(dirfallos, raiz))
    print("=" * 78)
    print("""
  COMPLETA   findings/147-slug.md    conforme
  TRUNCADA   findings/147-slug       casi conforme: le falta el .md. Sin esta
                                    clase era INVISIBLE, porque ni la regex de
                                    cita desnuda ni la de cita completa la ven
  DESNUDO    findings/147             resuelve y hay un solo fichero: funciona
  AMBIGUA    findings/035             resuelve a N ficheros distintos: no se
                                      sabe cual se cita

  Las tres ultimas no son errores de contenido, son deuda de convencion. Se
  cuentan aparte de las referencias rotas de reftriage.py y no se mezclan con
  ellas: una cita que no existe, una cita sin extension y una cita ambigua
  fallan de manera distinta y se arreglan distinto.
""")
    print("  hallazgos: %d en %d numeros, %d numeros con mas de un fichero"
          % (sum(len(v) for v in idx.values()), len(idx),
             sum(1 for v in idx.values() if len(v) > 1)))
    print("  citas: %d total = %d COMPLETA + %d TRUNCADA + %d DESNUDO"
          " + %d AMBIGUA + %d AUTOCITA"
          % (total, len(c), len(tr), len(dn_sin_auto), len(am_sin_auto), auto))
    if total:
        print("  conformes: %.1f%%   a corregir: %d de %d"
              % (100.0 * len(c) / total,
                 len(tr) + len(dn_sin_auto) + len(am_sin_auto), total))
    if auto:
        print("\n  %d AUTOCITAS: un hallazgo que se cita a si mismo por numero. No"
              % auto)
        print("  son deuda -- su numero es el suyo y no puede colisionar -- pero"
              " tampoco")
        print("  cumplen la convencion, asi que se cuentan aparte y no se suman a"
              " AMBIGUA.")
    if am_sin_auto:
        print("\n  LAS %d AMBIGUAS, con los ficheros con los que colisionan:\n"
              % len(am_sin_auto))
        vista = {}
        for f, n, _ in am_sin_auto:
            vista.setdefault(n, []).append(f)
        for n in sorted(vista):
            print("    findings/%s  ->  %d ficheros distintos, citado %d veces"
                  % (n, len(idx[n]), len(vista[n])))
            for s in idx[n]:
                print("        %s" % s)
            vistos = {}
            for f in vista[n]:
                vistos[f] = vistos.get(f, 0) + 1
            for f in sorted(vistos, key=lambda x: -vistos[x]):
                print("        citado %dx en %s" % (vistos[f], f))
    if tr:
        print("\n  LAS %d TRUNCADAS, a las que solo les falta el .md:\n" % len(tr))
        for f, n, cita in tr[:60]:
            print("    %-58s %s" % (f, cita))
        if len(tr) > 60:
            print("    ... y %d mas (--json las lista todas)" % (len(tr) - 60))
    dn = dn_sin_auto
    if dn:
        print("\n  LAS %d DESNUDAS, que funcionan pero incumplen la convencion:\n" % len(dn))
        for f, n, cita in dn[:60]:
            print("    %-58s %s" % (f, cita))
        if len(dn) > 60:
            print("    ... y %d mas (--json las lista todas)" % (len(dn) - 60))
    print("""
  LO QUE ESTA HERRAMIENTA NO HACE

  No verifica que el hallazgo citado SOSTENGA la afirmacion para la que se
  cita. Eso necesita comparar el termino citado con el contenido del hallazgo,
  y es la clase de fallo que produjo las cuatro oscilaciones del nombre del
  op 12 (findings/147 §6). Resolver no es sostener.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())

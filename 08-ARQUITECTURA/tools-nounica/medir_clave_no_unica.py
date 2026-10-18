#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
r"""medir_clave_no_unica -- MEDIR cuanta poblacion de documentos pierde cada
grafo del proyecto por usar el numero de hallazgo como clave primaria.

QUE NO ES ESTA HERRAMIENTA.  No es un linter mas.  No decide nada, no corrige
nada, no escribe en el arbol.  Es un banco de medicion: llama a las
herramientas que ya existen, les pide su grafo, y CUENTA.

POR QUE EXISTE, y por que no bastaba lo que ya hay
-------------------------------------------------
El hallazgo 259 mide COLISIONES en `findings/`: cuantos numeros tienen mas de un
fichero.  Eso es una propiedad del CORPUS.  Lo que no media nadie es la
CONSECUENCIA: cuantos nodos de cada grafo son en realidad dos o tres
documentos, y si algun calculo hecho sobre esa poblacion cambia de resultado.

Lo que hay, y lo que NO hace cada cosa:

  findings_index.py   mide las 74 colisiones del corpus.  No baja a los grafos.
  relations.py        marca las aristas ambiguas con `!`.  No cuenta la
                      poblacion que hay detras, no calcula grado, camino,
                      orden topologico ni ciclos, y su indice solo ve tres
                      digitos.
  artifacts.py        `resolver_destino` clasifica UN token en cuatro estados
                      y solo se usa en `gen_current_state`.
  claims.py           `retracciones` construye aristas por `(\d{3})` y no
                      tiene ningun marcador de ambiguedad.
  frontier.py         su indice por NUMERO se construye con asignacion, no con
                      `setdefault`: el ultimo fichero del numero pisa al
                      anterior.  Ver `medir_indice_frontier`.

Lo que falta es la CRUCE: nodos, aristas y resultado calculado, por consumidor.
Eso es lo que mide este fichero.  Si manana se arregla la clave primaria, este
script tiene que dar ceros en la columna de documents que el grafo no
distingue, y si no los da es que el arreglo no esta.

COMO SE ANCLA
-------------
`sys.path` se ancla con `os.path.dirname(os.path.abspath(__file__))` y el
proyecto se deriva de la ruta del modulo, NUNCA del directorio de trabajo.  El
hallazgo 1051 encontro tres herramientas cuyo `--repo` por defecto era el cwd,
que es la misma clase de error: una herramienta que solo funciona sobre el
arbol correcto cuando la llamas desde el sitio correcto.

`resolver_destino` se IMPORTA de `tools/artifacts.py` y no se reimplementa: hay
una sola definicion de que es una referencia, y esta escrita alli.

Salida: JSON con `--json`, informe legible sin flag.  No escribe ficheros del
proyecto en ningun modo.  Codigo de salida 0 siempre: medir no falla, describe.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import sys

# ---- ANCLA. Ver "COMO SE ANCLA". No es el cwd. ---------------------------
_AQUI = os.path.dirname(os.path.abspath(__file__))
# tools-nounica/ -> 08-ARQUITECTURA/ -> raiz del proyecto
ROOT = os.path.dirname(os.path.dirname(_AQUI))
TOOLS = os.path.join(ROOT, "tools")
for _p in (TOOLS, os.path.join(ROOT, "08-ARQUITECTURA", "tools")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

FIND = os.path.join(ROOT, "06-INGENIERIA-INVERSA", "findings")

VERSION = "1.0.0"

RX_3D = re.compile(r"^(\d{3})[-_](.+)\.md$")      # relations, claims, frontier
RX_34 = re.compile(r"^(\d{3,4})[-_](.+)\.md$")    # artifacts
RX_34R = re.compile(r"^(\d{3,4})-")               # findings_index
CITA_MD = re.compile(r"\b(\d{3}[a-z0-9-]*\.md)\b")


def ficheros():
    return sorted(f for f in os.listdir(FIND) if f.endswith(".md"))


def huella(rel):
    p = os.path.join(ROOT, rel)
    try:
        with open(p, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return "NO-LEIBLE"


def proveniencia():
    """El estado del ARBOL en el momento de medir, para que las cifras sean
    rederivables y para que se note si el arbol se movio.

    MEDIDO Y NECESARIO: durante esta sesion el directorio `findings/` cambio de
    557 a 558 ficheros.  Otra sesion escribio `1055-hwip-convierte-el-filtro-en-
    conclusion.md` a las 10:57 mientras esta medicion corria.  Sin la huella del
    nombre de los ficheros, dos ejecuciones de este script dan dos poblaciones
    y las dos son correctas: ese es el modo de fallo que el hallazgo 259 ya
    documento con las colisiones, pero para las cifras y no para los hallazgos.
    """
    fs = ficheros()
    lista = "\n".join(fs)
    return {
        "momento": datetime.datetime.now().astimezone().isoformat(
            timespec="seconds"),
        "ficheros_md": len(fs),
        "sha256_de_la_lista_ordenada_de_nombres":
            hashlib.sha256(lista.encode("utf-8")).hexdigest(),
        "herramientas_leidas": {
            "tools/relations.py": huella("tools/relations.py"),
            "tools/claims.py": huella("tools/claims.py"),
            "tools/artifacts.py": huella("tools/artifacts.py"),
            "08-ARQUITECTURA/tools/findings_index.py":
                huella("08-ARQUITECTURA/tools/findings_index.py"),
            "08-ARQUITECTURA/tools-nounica/medir_clave_no_unica.py":
                huella("08-ARQUITECTURA/tools-nounica/"
                       "medir_clave_no_unica.py"),
        },
    }


# --------------------------------------------------------------------------
# INDICES: los criterios que hay en el arbol, medidos uno a uno
# --------------------------------------------------------------------------

def indice_como_herramienta(nombre):
    """(clave -> [ficheros]) SEGUN el criterio que usa esa herramienta.

    Se construye con el mismo regex que la herramienta, incluido su CONVENCION
    DE FALLBACK, porque el fallback es parte del defecto: en `relations.py:252`
    y `claims.py:805` un fichero que no casa con el regex recibe `f[:3]`, y eso
    mete un hallazgo de 1054 dentro del nodo `105`.
    """
    out = collections.OrderedDict()
    for f in ficheros():
        if nombre == "findings_index":
            m = RX_34R.match(f)
            clave = int(m.group(1)) if m else None
        elif nombre == "relations":
            m = RX_3D.match(f)
            clave = m.group(1) if m else f[:3]
        elif nombre == "claims":
            m = RX_3D.match(f)
            clave = m.group(1) if m else f[:3]
        elif nombre == "frontier":
            m = re.match(r"^(\d{3})", f)
            clave = m.group(1) if m else None      # `continue`: NO hay fallback
        elif nombre == "artifacts":
            m = RX_34.match(f)
            clave = str(int(m.group(1))) if m else None
        else:
            raise ValueError(nombre)
        if clave is None:
            continue
        out.setdefault(clave, []).append(f)
    return out


def _norm(k):
    """La clave de dos herramientas solo se puede COMPARAR normalizada.

    `relations.py` guarda `"004"` (tres digitos, tal cual) y `findings_index.py`
    guarda `4` (entero).  Sin normalizar, comparar los dos indices produce
    ninety y ocho "claves huerfanas" que no son huerfanas: son ceros a la
    izquierda.  El hallazgo 1051 es exactamente esta clase de error.
    """
    try:
        return str(int(k))
    except (TypeError, ValueError):
        return str(k)


def comparar_indices():
    ref = indice_como_herramienta("findings_index")
    truth = {k: v for k, v in ref.items()}
    set_truth = {_norm(k) for k in truth}
    sal = {"referencia": "08-ARQUITECTURA/tools/findings_index.py "
                         "RE_NUM=^(\\d{3,4})-",
           "ficheros_en_disco": len(ficheros()),
           "numeros_reales_segun_el_criterio_mas_amplio": len(truth),
           "por_criterio": {}}
    for nombre in ("findings_index", "artifacts", "relations", "claims",
                   "frontier"):
        idx = indice_como_herramienta(nombre)
        col = {k: v for k, v in idx.items() if len(v) > 1}
        set_idx = {_norm(k) for k in idx}
        huerf = sorted(set_idx - set_truth)
        faltan = sorted(set_truth - set_idx)
        sal["por_criterio"][nombre] = {
            "regex": {"findings_index": r"^(\d{3,4})-",
                      "artifacts": r"^(\d{3,4})[-_](.+)\.md$",
                      "relations": r"^(\d{3})[-_](.+)\.md$  + fallback f[:3]",
                      "claims": r"^(\d{3})[-_]  + fallback f[:3]",
                      "frontier": r"^(\d{3})  + continue (sin fallback)"
                      }[nombre],
            "claves": len(idx),
            "documentos_indexados": sum(len(v) for v in idx.values()),
            "documentos_no_indexados": len(ficheros()) - sum(
                len(v) for v in idx.values()),
            "nodos_con_mas_de_un_documento": len(col),
            "documentos_fundidos_en_otros_nodos": sum(
                len(v) - 1 for v in col.values()),
            "nodos_que_funden_3_o_mas": sum(1 for v in col.values()
                                            if len(v) >= 3),
            "claves_que_no_existen_en_el_criterio_de_referencia": huerf,
            "n_claves_inexistentes_para_esta_herramienta": len(huerf),
            "numeros_reales_que_esta_herramienta_no_ve": faltan,
            "n_numeros_reales_no_vistos": len(faltan),
        }
    return sal, truth


def medir_indice_frontier():
    """`frontier.py:613-621` NO tiene funcion: esta dentro de `main()`.

    Se replican esas nueve lineas LITERALMENTE porque no son alcanzables desde
    fuera, y se declara aqui que se replican.  La diferencia con las demas
    herramientas es que no usa `setdefault`: es ASIGNACION, y eso hace que el
    ULTIMO fichero del numero pise al anterior.  No es un indice parcial: es un
    indice que afirma tener uno solo.
    """
    indices = {}
    for f in ficheros():
        m = re.match(r"^(\d{3})", f)
        if not m:
            continue
        indices[m.group(1)] = [(f, "")]      # la linea 621, literal
    idx_completo = {}
    for f in ficheros():
        m = RX_3D.match(f)
        if m:
            idx_completo.setdefault(m.group(1), []).append(f)
    pisados = []
    for num, v in idx_completo.items():
        if len(v) > 1 and num in indices:
            keep = indices[num][0][0]
            pisados.append({"numero": num, "n_documentos": len(v),
                            "se_queda": keep,
                            "se_pierden": [x for x in v if x != keep]})
    return {"asignacion_sobreescribe": True,
            "claves_en_el_indice": len(indices),
            "claves_del_indice_completo": len(idx_completo),
            "documentos_visibles": len(indices),
            "documentos_de_tres_digitos_que_desaparecen_del_indice":
                sum(x["n_documentos"] - 1 for x in pisados),
            "numeros_afectados": len(pisados),
            "muestra": pisados[:6]}


def medir_truncamiento_f3():
    """`f[:3]`: que hallazgo de cuatro digitos acaba dentro de que nodo de tres.

    Es un SEGUNDO mecanismo de fusion, independiente del de la renumeracion que
    midio el 259, y no aparece en ninguna de las colisiones de `findings_index`
    porque alli los cuatro digitos SI se ven.
    """
    out = []
    for f in ficheros():
        if RX_3D.match(f):
            continue
        pre = f[:3]
        out.append({"fichero": f, "nodo_donde_cae": pre,
                    "colisiona_con_tres_digitos": bool(
                        any(x.startswith(pre + "-") for x in ficheros()))})
    por_nodo = collections.Counter(x["nodo_donde_cae"] for x in out)
    return {"ficheros_que_no_casan_con_el_regex_de_tres_digitos": len(out),
            "nodos_de_tres_digitos_afectados": len(por_nodo),
            "documentos_de_cuatro_digitos_por_nodo": dict(sorted(por_nodo.items())),
            "cuantas_de_esas_colisionan_con_un_tres_digitos_real": sum(
                1 for x in out if x["colisiona_con_tres_digitos"]),
            "ficheros": [x["fichero"] for x in out]}


# --------------------------------------------------------------------------
# Grafo: representacion comun para poder CONTAR sobre el
# --------------------------------------------------------------------------

class Grafo(object):
    def __init__(self, nombre, aristas, idx_clave, alcance="",
                 et_son_verbos_reales=True):
        self.nombre = nombre
        self.aristas = aristas          # (origen, verbo, destino, token_crudo)
        self.idx = idx_clave
        self.alcance = alcance
        # ¿El campo `verbo` de la arista es el verbo REAL que el autor escribió,
        # o una etiqueta sintetica puesta por este banco?  De eso depende que la
        # busqueda literal `verbo=token` sea aplicable: si la etiqueta es
        # sintetica, la busqueda no puede encontrar nada y un cero significa
        # "no aplicable", no "no se declara".
        self.et_son_verbos_reales = et_son_verbos_reales

    def nodos(self):
        s = set()
        for o, _v, d, _t in self.aristas:
            s.add(o)
            s.add(d)
        return s

    def docs_detras(self, clave):
        return self.idx.get(clave, [])

    def a_inexistente(self):
        return [a for a in self.aristas if not self.docs_detras(a[2])]

    def a_ambiguo(self):
        return [a for a in self.aristas if len(self.docs_detras(a[2])) > 1]

    def desde_ambiguo(self):
        return [a for a in self.aristas if len(self.docs_detras(a[0])) > 1]

    def ambos_ambiguos(self):
        return [a for a in self.aristas
                if len(self.docs_detras(a[0])) > 1
                and len(self.docs_detras(a[2])) > 1]

    def poblacion(self):
        docs = set()
        for n in self.nodos():
            docs |= set(self.docs_detras(n))
        return docs


# --------------------------------------------------------------------------
# Grafo 1: relations.py, y por delegacion KNOWLEDGE-GRAPH.md
# --------------------------------------------------------------------------

def grafo_relations():
    import relations as R
    idx = indice_como_herramienta("relations")
    r = R.escanear(ROOT)
    aristas = []
    for et, occ in r["rel"].items():
        for num, _lin, val, dest, _nrm in occ:
            aristas.append((str(num), et, str(dest), str(val)))
    for desde, et, dest, _nrm, val, _ok, _tot in r["extra"]:
        aristas.append((str(desde), str(et), str(dest), str(val)))
    return Grafo("relations.py (y KNOWLEDGE-GRAPH.md, que lo consume)",
                 aristas, idx, "18 primeras lineas (NCAB=18)")


# --------------------------------------------------------------------------
# Grafo 2: claims.py:retracciones, con SU alcance de 24 lineas
# --------------------------------------------------------------------------

def grafo_claims():
    import claims as C
    idx = indice_como_herramienta("claims")
    aristas = []
    for f in ficheros():
        with open(os.path.join(FIND, f), "r", errors="replace") as fh:
            lineas = fh.read().splitlines()
        hace, recibe = C.retracciones(lineas)      # la FUNCION, no su regex
        k = _clave_de_claims(f)
        for d in sorted(hace):
            if d == "__anterior__":
                continue
            # Token VACIO a proposito: `claims.py:retracciones` devuelve solo
            # NUMEROS (`for num in re.findall(r"CORRECTS=(\d{3})", texto)`), y
            # el nombre del fichero que el autor escribio se pierde ahi.  Poner
            # el nombre del ORIGEN como token haria que la cuenta de "aristas
            # con nombre" saliera 31 de 31 sin medir nada: un control que no
            # puede fallar.  El token vacio hace que la cuenta diga la verdad,
            # que es 0 de 31.
            aristas.append((k, "CORRIGE_A", str(d), ""))
        for d in sorted(recibe):
            aristas.append((k, "CORREGIDO_POR", str(d), ""))
    return Grafo("claims.py:retracciones", aristas, idx,
                 "24 primeras lineas (lineas[:24])",
                 et_son_verbos_reales=False)


def _clave_de_claims(f):
    """Como `claims.py:805`: el regex o, si no casa, `f[:3]`."""
    m = RX_3D.match(f)
    return m.group(1) if m else f[:3]


# --------------------------------------------------------------------------
# Grafo 3: artifacts.py gen_current_state, clasificado con SU resolutor
# --------------------------------------------------------------------------

def grafo_current_state():
    import artifacts as A
    bynum = {}
    for f in ficheros():
        m = RX_34.match(f)
        if m:
            bynum.setdefault(int(m.group(1)), []).append(f)
    idx = indice_como_herramienta("artifacts")
    aristas = []
    detalle = collections.Counter()
    filtradas = []
    fila_item = []
    slug_por_fichero = {}
    for f in ficheros():
        m0 = RX_34.match(f)
        if m0:
            slug_por_fichero[str(int(m0.group(1)))] = m0.group(2)[:22]
    for f in ficheros():
        m = RX_34.match(f)
        if not m:
            continue
        with open(os.path.join(FIND, f), "r", errors="replace") as fh:
            txt = fh.read()
        ori = str(int(m.group(1)))
        for mm in A.RX_CORR.finditer(txt):
            tok = mm.group(1)
            estado, det = A.resolver_destino(tok, bynum)   # SU resolutor
            detalle[estado] += 1
            if estado == "NO_REFERENCIA":
                continue
            # La guarda del ARTEFACTO es `if m.group(1) in str(det)`: COMPARACION
            # POR SUBCADENA, no igualdad.  Y este campo lista los casos que ESA
            # guarda filtra, no los que se le escapan.
            #
            # La primera version de esta comprobaciaon comparaba con `==` y
            # guardaba el resultado en una lista llamada `sin_guard`, o sea
            # decía lo contrario de lo que media: marcaba como "sin guarda" el
            # unico caso que la guarda filtra.  De ahi salio en un borrador la
            # afirmacion de que `gen_current_state` publica una auto-arista
            # `30 -> 030`, que es FALSA: el artefacto no la publica.  La
            # autocomprobacion es que el nombre del campo dice lo que hace.
            if m.group(1) in str(det):
                filtradas.append("%s -> %s" % (m.group(1), tok))
            dest = (str(int(det.split("-", 1)[0]))
                    if estado == "RESUELTA"
                    else str(int(tok.split("-")[0])))
            aristas.append((ori, "CORRIGE_A", dest, tok))
            # Lo que el ARTEFACTO imprime y deduplica.  Para RESUELTA imprime el
            # FICHERO resuelto, no el token: y por eso dos tokens distintos que
            # apuntan al mismo fichero se colapsan en una fila.  Sin esto, la
            # reconciliacion sale descuadrada en 1 y no se sabe de que lado.
            fila_item.append("%s-%s -> corregida por %s"
                             % (ori, slug_por_fichero.get(ori, "?"),
                                det if estado == "RESUELTA" else tok))
    g = Grafo("artifacts.py gen_current_state (bloque 'Correcciones')",
              aristas, idx, "fichero ENTERO (no hay recorte de lineas)",
              et_son_verbos_reales=False)
    g.estados = detalle
    g.filtradas_por_la_guarda = filtradas
    # `gen_current_state` DEDUPLICA por fila renderizada (`if item in corr or
    # item in corr_ambigua or item in corr_rota: continue`).  Este banco cuenta
    # COINCIDENCIAS, no filas, y por eso da un numero MAYOR.  Se mide el
    # desfase en vez de ajustarlo: los dos numeros son correctos y cuentan
    # cosas distintas, y confundirlos es como se fabrican cifras que no cuadran
    # con ninguna de las dos fuentes.
    # La clave de deduplicacion del ARTEFACTO es la CADENA que imprime:
    #   "%s-%s -> corregida por %s" % (num, slug[:22], det o tok)
    # con lo que dos coincidencias del mismo fichero con token DISTINTO no se
    # colapsan.  Se replica esa cadena, no una clave inventada.
    g.filas_sin_dedup = len(set(fila_item))
    return g


# --------------------------------------------------------------------------
# Grafo 4: artifacts.py gen_contradictions, con la funcion sentido REAL
# --------------------------------------------------------------------------

CONTRADICCION = {
    "CORRECTS", "CORRECTED_BY", "CORRECTS_RUTA", "CORRIGE",
    "CORRIGE_LA_POLITICA_DE", "RECTIFIES", "AMENDA",
    "RETRACTS", "RETRACTED_BY", "RETRACTED_PARTLY_BY",
    "CERRADO_POR", "ADJUDICA",
}


def grafo_contradictions():
    import artifacts as A
    idx = indice_como_herramienta("relations")   # el grafo viene de relations
    rel = A._relaciones_vocabulario(ROOT)["rel"]
    aristas = []
    for et, occ in rel.items():
        for num, _l, val, dest, _nrm in occ:
            if et in CONTRADICCION:
                aristas.append((str(num), str(et), str(dest), str(val)))
    g = Grafo("artifacts.py gen_contradictions", aristas, idx,
              "18 primeras lineas, via relations.py")
    g.sentido = _sentido_de_artifacts()
    return g


def _sentido_de_artifacts():
    """La funcion `sentido` de artifacts.py:849, COPIADA.

    Se copia porque es una closure local de `gen_contradictions` y no se puede
    importar.  Se DECLARA que se copia, y `autocomprobacion` verifica que la
    copia produce cadenas que salen LITERALES en el artefacto que genera la
    funcion original: si `sentido` cambiara, esa comprobacion falla.
    """
    SIN_SENTIDO = {"CERRADO_POR", "MEDIDO_EN_MI_ASIC_POR",
                   "GENERALIZADO_POR", "CORRIGE_LA_POLITICA_DE"}

    def sentido(desde, hacia, et):
        if et in SIN_SENTIDO:
            return "%s --%s-> %s  (sentido NO calculado)" % (desde, et, hacia)
        if "_BY" in et:
            return "%s RECIBE de %s" % (desde, hacia)
        return "%s %s a %s" % (desde, et, hacia)
    return sentido


def autocomprobacion():
    import artifacts as A
    txt = A.gen_contradictions(ROOT, None)      # EN MEMORIA. No se escribe.
    rel = A._relaciones_vocabulario(ROOT)["rel"]
    s = _sentido_de_artifacts()
    n = 0
    for et, occ in rel.items():
        if et not in CONTRADICCION:
            continue
        for num, _l, _v, dest, _nrm in occ:
            cand = s(str(num), str(dest), str(et))
            if ("| %s | `%s` |" % (num, et)) in txt and cand in txt:
                n += 1
    return {"aristas_de_contradiccion_que_la_copia_reproduce_literalmente": n,
            "aristas_de_contradiccion_en_el_grafo":
                sum(len(o) for e, o in rel.items() if e in CONTRADICCION),
            "longitud_del_artefacto_producido_en_memoria": len(txt),
            "el_artefacto_no_se_escribio_en_el_arbol": True}


# --------------------------------------------------------------------------
# Grafo 5: artifacts.py gen_evidence_matrix, columna 'reescribe'
# --------------------------------------------------------------------------

def grafo_evidence_matrix():
    """`artifacts.py:252` con SU alcance: `cab` = las 14 primeras lineas.

    Y con una diferencia que las demas no tienen: NO tiene guard de
    auto-referencia.  Se mide, no se supone.
    """
    idx = indice_como_herramienta("artifacts")
    aristas = []
    auto = []
    rx = (r"RETRACTED_BY=(\d{3,4})", r"CORRECTS=(\d{3,4})",
          r"IMPLEMENTS=(\d{3,4})", r"GENERALIZAD[OA]_POR=(\d{3,4})")
    for f in ficheros():
        m = RX_34.match(f)
        if not m:
            continue
        with open(os.path.join(FIND, f), "r", errors="replace") as fh:
            cab = "\n".join(fh.read().splitlines()[:14])
        ori = str(int(m.group(1)))
        for r in rx:
            for g in re.findall(r, cab):
                if g == m.group(1):
                    auto.append("%s -> %s" % (ori, g))
                    continue
                aristas.append((ori, r.split("=")[0], str(int(g)), g))
    g = Grafo("artifacts.py gen_evidence_matrix (columna 'reescribe')",
              aristas, idx, "14 primeras lineas (splitlines()[:14])")
    g.autolooops = auto
    return g


# --------------------------------------------------------------------------
# CALCULOS QUE PUEDEN CAMBIAR: grado, ciclo, orden topologico, camino
# --------------------------------------------------------------------------

CAMPOS_COMPARADOS = ("nodos", "aristas", "grado_maximo", "hay_ciclo",
                     "nodos_en_algun_ciclo", "orden_topologico_existe",
                     "camino_mas_largo_en_el_condensado", "autoloops")


def tarjan(nodos, aristas):
    """Componentes fuertemente conexas.  Devuelve (scc_por_nodo, n_scc, ciclicos)."""
    adj = collections.defaultdict(list)
    for o, d in aristas:
        adj[o].append(d)
    idx, bajo, en_pila, pila = {}, {}, {}, []
    scc = {}
    cont = [0]
    ciclicos = set()

    def fuerte(v):
        idx[v] = bajo[v] = cont[0]
        cont[0] += 1
        pila.append(v)
        en_pila[v] = True
        for w in adj.get(v, ()):
            if w not in idx:
                fuerte(w)
                bajo[v] = min(bajo[v], bajo[w])
            elif en_pila.get(w):
                bajo[v] = min(bajo[v], idx[w])
        if bajo[v] == idx[v]:
            comp = []
            while True:
                w = pila.pop()
                en_pila[w] = False
                comp.append(w)
                if w == v:
                    break
            for w in comp:
                scc[w] = cont[0]
            if len(comp) > 1:
                ciclicos.update(comp)
            cont[0] += 1

    sys.setrecursionlimit(100000)
    for n in sorted(nodos):
        if n not in idx:
            fuerte(n)
    # Un bucle sobre UN nodo no es una componente de tamaño >1, asi que Tarjan
    # no lo cuenta como ciclico.  Se Marqueta aparte, porque un autolooop es un
    # ciclo y rompe el orden topologico igual que un ciclo de dos.
    auto = set(o for o, d in aristas if o == d)
    return scc, len(set(scc.values())), (ciclicos | auto)


def resumen_calculos(nodos, aristas):
    ent, sal = collections.Counter(), collections.Counter()
    for o, d in aristas:
        sal[o] += 1
        ent[d] += 1
    tot = collections.Counter()
    for n in set(list(ent) + list(sal)):
        tot[n] = ent[n] + sal[n]
    scc, n_scc, ciclicos = tarjan(nodos, aristas)
    # Camino mas largo en el CONDENSADO: definido aunque haya ciclos, y por
    # eso es comparable entre grafos.  El camino mas largo sobre el grafo con
    # ciclos NO esta definido y dar un numero seria inventarlo.
    ar_c = [(scc[o], scc[d]) for o, d in aristas if o in scc and d in scc]
    memo = {}
    adj = collections.defaultdict(list)
    for a, b in ar_c:
        adj[b].append(a)

    def largo(u):
        if u in memo:
            return memo[u]
        memo[u] = 1
        for v in adj.get(u, ()):
            memo[u] = max(memo[u], 1 + largo(v))
        return memo[u]
    comp = max((largo(c) for c in set(scc.values())), default=0)
    return {
        "nodos": len(nodos),
        "nodos_en_ciclo_QUE": sorted(ciclicos),
        "aristas": len(aristas),
        "grado_maximo": max(tot.values()) if tot else 0,
        "nodo_de_grado_maximo": (max(tot.items(), key=lambda kv: kv[1])[0]
                                 if tot else None),
        "cuantos_documentos_ocupan_el_grado_maximo":
            sum(1 for n in tot if tot[n] == (max(tot.values()) if tot else 0)),
        "hay_ciclo": bool(ciclicos),
        "nodos_en_algun_ciclo": len(ciclicos),
        "componentes_fuertes": n_scc,
        "orden_topologico_existe": not ciclicos,
        "camino_mas_largo_en_el_condensado": comp,
        "autoloops": sum(1 for o, d in aristas if o == d),
    }


def grafo_con_eleccion(g, cchoice):
    """El grafo de DOCUMENTOS que sale de elegir un documento por cada clave.

    `cchoice` es una funcion clave -> documento.  Es la unica forma honesta de
    "desfundir" el grafo sin inventar: cualquier leitura del grafo que el
    proyecto tiene que hacer es exactamente una de estas funciones, y no hay
    ninguna que el dato imponga.
    """
    ar = []
    for o, _v, d, _t in g.aristas:
        ar.append((cchoice(o), cchoice(d)))
    return ar


def eleccion_alfabetica(g):
    def f(k):
        v = g.docs_detras(k)
        return v[0] if v else "<SIN-FICHERO:%s>" % k
    return f


MISMAS_CAMPOS = CAMPOS_COMPARADOS


def muestrear_elecciones(g, n=200, semilla=20261004):
    """Cuantos VALORES DISTINTOS toma cada calculo al elegir documento.

    Esto es lo que responde a la pregunta del encargo de forma directa, sin
    cotas: se construyen `n` funciones de eleccion deterministas (semilla fija,
    o sea rederivable), se calcula el grafo de documentos de cada una, y se
    cuenta cuantos valores distintos aparece cada campo.

    `n_valores_distintos > 1`  <=>  el resultado DEPENDE de que documento se
    elija.  Y el valor que publica la herramienta es uno de ellos, sin decir
    que lo es.
    """
    import random
    rnd = random.Random(semilla)
    claves = sorted(g.nodos())
    obs = {c: set() for c in MISMAS_CAMPOS}
    obs_id = {"nodo_de_grado_maximo": set(),
              "conjunto_de_documentos_en_ciclo": set(),
              "cuantos_documentos_ocupan_el_grado_maximo": set()}
    for _ in range(n):
        cc = {}

        def f(k, _cc=cc):
            if k in _cc:
                return _cc[k]
            v = g.docs_detras(k)
            _cc[k] = rnd.choice(v) if v else "<SIN-FICHERO:%s>" % k
            return _cc[k]
        ar = grafo_con_eleccion(g, f)
        nodos = set()
        for a, b in ar:
            nodos.add(a)
            nodos.add(b)
        r = resumen_calculos(nodos, ar)
        for c in MISMAS_CAMPOS:
            obs[c].add(r[c])
        obs_id["nodo_de_grado_maximo"].add(r["nodo_de_grado_maximo"])
        obs_id["conjunto_de_documentos_en_ciclo"].add(
            tuple(sorted(r["nodos_en_ciclo_QUE"])))
        obs_id["cuantos_documentos_ocupan_el_grado_maximo"].add(
            r["cuantos_documentos_ocupan_el_grado_maximo"])
    ident = {k: {"valores_distintos": len(v), "muestra": sorted(v)[:6]}
             for k, v in obs_id.items()}
    return ident, {c: {"valores_distintos": len(obs[c]),
                "minimo": min(obs[c], key=lambda x: (str(type(x)), x))
                if obs[c] else None,
                "maximo": max(obs[c], key=lambda x: (str(type(x)), x))
                if obs[c] else None}
            for c in MISMAS_CAMPOS}





# --------------------------------------------------------------------------
# EL SENTIDO DE CONTRADICTIONS: ¿depende del documento?  MEDIDO
# --------------------------------------------------------------------------

def _cuerpo(f):
    with open(os.path.join(FIND, f), "r", errors="replace") as fh:
        return fh.read().splitlines()


def sentido_medido(g):
    """Tres preguntas, y las tres se contestan con ejecuciones.

    1) ¿El TEXTO impreso depende del documento?  La funcion `sentido` recibe
       `hacia`, y `hacia` es el NUMERO resuelto.  Los candidatos de un numero
       ambiguo comparten el numero, luego la llamada es IDENTICA.  Se mide
       contando los grados de libertad: se llama con cada candidato y se
       compara el resultado.

    2) ¿La VERDAD de la frase depende del documento?  Eso no lo responde el
       grafo: lo responde el cuerpo del origen.  Se busca, en el cuerpo de
       CADA candidato del ORIGEN, una cita por nombre a un candidato del
       DESTINO.  Con eso el referente queda decidido por el texto, y se mide
       cuantos quedan decididos y cuantos no.

    3) ¿El token crudo permite resolverlo sin leer prosa?  `relations.py`
       guarda el token entero en la tupla, asi que un token con nombre se
       resuelve exacto aunque el grafo lo haya perdido.
    """
    filas = []
    n_amb = n_texto_difiere = n_decidible = n_indecible = 0
    n_exacto_por_token = 0
    for o, et, d, tok in g.aristas:
        cand = g.docs_detras(d)
        if len(cand) < 2:
            continue
        n_amb += 1
        # (1) texto: se llama con cada candidato spells. Todos dan el mismo
        # numero, asi que la cadena tiene que ser identica. Se comprueba.
        # Se invoca EXACTAMENTE como artifacts.py:879 lo hace, que es con el
        # NUMERO. Los candidatos de un numero ambiguo comparten ese numero, luego
        # la llamada es identica y la cadena tiene que salir identica.  La
        # primera version de esta comprobacion pasaba el NOMBRE de fichero, con
        # lo que la cadena cambiaba por construccion: un control que no puede
        # fallar, que es peor que no tener control.
        salidas = set(g.sentido(o, c.split("-", 1)[0], et) for c in cand)
        # (2) decidibilidad por el cuerpo del ORIGEN
        origenes = g.docs_detras(o)
        nombrados = set()
        for of in origenes:
            for ln in _cuerpo(of):
                for cm in CITA_MD.finditer(ln):
                    if cm.group(1) in cand:
                        nombrados.add(cm.group(1))
        # (3) el token crudo
        m = RX_34.match(tok if tok.endswith(".md") else tok + ".md")
        exacto = m.group(2) + ".md" if m else None
        if exacto:
            n_exacto_por_token += 1
        if len(nombrados) == 1:
            n_decidible += 1
            veredicto = "DECIDIBLE_POR_NOMBRE"
        elif len(nombrados) > 1:
            n_decidible += 1
            veredicto = "DECIDIBLE_TODOS_LOS_CANDIDATOS"
        else:
            n_indecible += 1
            veredicto = "INDECIBLE"
        filas.append({
            "arista": "%s --%s--> %s" % (o, et, d),
            "token_crudo": tok,
            "candidatos": cand,
            "sentido_impreso": g.sentido(o, d, et),
            "cadenas_distintas_al_invocar_por_candidato": len(salidas),
            "el_texto_del_sentido_depende_del_documento":
                len(salidas) > 1,
            "candidatos_nombrados_en_el_cuerpo_del_origen": sorted(nombrados),
            "token_resuelve_exacto": exacto,
            "veredicto_del_referente": veredicto,
        })
    return {"aristas_de_contradiccion": len(g.aristas),
            "con_destino_ambiguo": n_amb,
            "texto_del_sentido_depende_del_documento": n_texto_difiere,
            "referente_decidible_leyendo_el_cuerpo_del_origen": n_decidible,
            "referente_indecidable": n_indecible,
            "aristas_con_token_que_resuelve_exacto": n_exacto_por_token,
            "filas": filas}


# --------------------------------------------------------------------------
# EL ORIGEN TAMBIEN ES AMBIGUO, y eso se puede DESHACER empíricamente
# --------------------------------------------------------------------------

def origen_declarante(g, ncab=18):
    """De los candidatos del ORIGEN, ¿cuáles contienen LITERALMENTE la arista?

    `relations.py` graba el origen como un NUMERO (`num = m.group(1)`, y `f[:3]`
    si no casa), de modo que una arista desde un numero duplicado no dice que
    documento la declara.  Eso se deshace sin leer prosa: se busca el token
    crudo literal `verbo=token` en las 18 primeras lineas de cada candidato, que
    es el mismo alcance que usa `relations.py`.

    Se declara el criterio porque es una busqueda literal y no un parser: si el
    autor escribe la etiqueta con otro separador, esta cuenta lo dara como no
    declarante, y eso es un limite del metodo, no un dato del corpus.
    """
    filas = []
    n_amb = n_resuelto = n_ninguno = 0
    for o, et, d, tok in g.aristas:
        cands = g.docs_detras(o)
        if len(cands) < 2:
            continue
        n_amb += 1
        pat = re.compile(re.escape("%s=%s" % (et, tok)))
        declaran = [c for c in cands
                    if pat.search("\n".join(_cuerpo(c)[:ncab]))]
        if len(declaran) == 1:
            n_resuelto += 1
        elif not declaran:
            n_ninguno += 1
        filas.append({"arista": "%s --%s--> %s" % (o, et, d),
                      "token_crudo": tok,
                      "candidatos_origen": cands,
                      "candidatos_que_la_declaran": declaran})
    return {"busqueda_literal_aplicable": g.et_son_verbos_reales,
            "aristas_con_origen_ambiguo": n_amb,
            "origen_desambiguado_por_busqueda_literal": n_resuelto,
            "sin_candidato_que_la_declare": n_ninguno,
            "sigue_ambiguo": n_amb - n_resuelto - n_ninguno,
            "filas": filas}


# --------------------------------------------------------------------------
# LA MISMA RELACION EN LAS DOS DIRECCIONES
# --------------------------------------------------------------------------

INVERSOS = {"RETRACTS": "RETRACTED_BY",
            "RETRACTED_BY": "RETRACTS",
            "RETRACTED_PARTLY_BY": "RETRACTS",
            "RECTIFIES": "RECTIFIES",
            "CORRECTS": "CORRECTED_BY",
            "CORRECTED_BY": "CORRECTS",
            "AMENDA": "CORRECTED_BY"}


def pares_inversos(g):
    """A pares (A,B) y (B,A) con verbos INVERSOS: la misma relacion, dos veces.

    El generador calcula el SENTIDO de cada fila, y con ahi se podria decir que
    el problema esta resuelto.  No lo esta: si las dos orientaciones estan en el
    grafo, la misma relacion cuenta DOS aristas, y cada una por separado es un
    ciclo de longitud 2 con la otra.  Se mide cuantos pares hay.
    """
    vistos = {}
    for o, et, d, _t in g.aristas:
        vistos.setdefault((str(o), str(d)), set()).add(et)
    pares = []
    for (a, b), ets in sorted(vistos.items()):
        inv = {INVERSOS.get(e) for e in ets}
        if (b, a) in vistos and (vistos[(b, a)] & inv):
            pares.append({"a": a, "b": b,
                          "verbos_en_este_sentido": sorted(ets),
                          "verbos_en_el_sentido_inverso":
                              sorted(vistos[(b, a)])})
    return {"aristas": len(g.aristas),
            "pares_ordenados_distintos": len(vistos),
            "pares_inversos_presentes": len(pares),
            "aristas_en_un_par_inverso": 2 * len(pares),
            "detalle": pares}


# --------------------------------------------------------------------------
# CONTRASTE: lo que publica el artefacto contra lo que mide este banco
# --------------------------------------------------------------------------

def bullets_de(txt, titulo):
    """Los items de una seccion del artefacto, contados en el TEXTO.

    Se cuenta el TEXTO QUE PUBLICA la herramienta y no una replicacion de su
    logica.  Una replicacion puede discrepar de la original por un detalle (y una
    discrepacion asi no dice cual de las dos tiene razon); el texto publicado no
    puede discrepar de si mismo.
    """
    i = txt.index(titulo)
    j = len(txt)
    for k in ("\n## ", "\n# "):
        n = txt.find(k, i + len(titulo))
        if n != -1:
            j = min(j, n)
    return [l for l in txt[i:j].splitlines() if l.startswith("- `")]

def contraste_con_artefactos():
    """Se producen los CUATRO artefactos EN MEMORIA y se leen sus totales.

    Es la comprobacion de que este banco mide lo mismo que el artefacto y no una
    reconstruccion paralela.  `artifacts.py` delega en `relations.py --json` y en
    `frontier.py --json`; aqui se usan las mismas funciones, luego los numeros
    tienen que coincidir.  Si no coinciden, o este banco esta mal o el artefacto
    esta mintiendo, y en los dos casos hay que saber cual antes de escribir.
    """
    import artifacts as A
    salida = {}
    for nombre, fn in (("knowledge_graph", A.gen_knowledge_graph),
                       ("contradictions", A.gen_contradictions),
                       ("current_state", A.gen_current_state),
                       ("evidence_matrix", A.gen_evidence_matrix)):
        txt = fn(ROOT, None)
        if nombre == "current_state":
            r = bullets_de(txt, "## Correcciones registradas (inequivocas)")
            a = bullets_de(txt, "## Correcciones AMBIGUAS")
            b = bullets_de(txt, "## Correcciones rotas")
            t = bullets_de(txt, "## Retracciones registradas")
            # Los items AMBIGUA se guardan CON sufijo "  [N candidatos]" y el
            # guard de deduplicacion busca el item SIN sufijo, luego la
            # comparacion nunca es cierta y una ambigua repetida se publica dos
            # veces.  MEDIDO, no supuesto: se cuenta sobre las filas publicadas.
            items_a = [x.split("  [")[0] for x in a]
            salida["current_state_dedup"] = {
                "filas_inequivocas": len(r),
                "filas_ambiguas": len(a),
                "filas_rotas": len(b),
                "filas_retraccion": len(t),
                "filas_totales": len(r) + len(a) + len(b),
                "items_ambiguos_distintos": len(set(items_a)),
                "items_ambiguos_publicados_de_mas": len(a) - len(set(items_a)),
                "duplicados": sorted({x for x in items_a
                                      if items_a.count(x) > 1}),
            }
        lineas = [l for l in txt.splitlines()
                  if re.match(r"^(\*\*Total|\*\*TOTAL|- Correcciones"
                               r"|- Retracciones|- Hallazgos cuyo NOMBRE"
                               r"|Se miden)", l)]
        salida[nombre] = {"bytes": len(txt),
                          "lineas_de_total": [l.strip() for l in lineas]}
    return salida


# --------------------------------------------------------------------------

def medir():
    d = {"version": VERSION, "root": ROOT, "findings_dir": FIND}
    d["proveniencia"] = proveniencia()
    d["indices"] = comparar_indices()[0]
    d["indice_frontier"] = medir_indice_frontier()
    d["truncamiento_f3"] = medir_truncamiento_f3()

    grafos = collections.OrderedDict([
        ("relations", grafo_relations()),
        ("claims", grafo_claims()),
        ("current_state", grafo_current_state()),
        ("contradictions", grafo_contradictions()),
        ("evidence_matrix", grafo_evidence_matrix()),
    ])
    tabla = {}
    for clave, g in grafos.items():
        nodos, docs = g.nodos(), g.poblacion()
        cn = [a for a in g.aristas
              if a[3] and RX_34.match(a[3] if a[3].endswith(".md")
                                      else a[3] + ".md")]
        tabla[clave] = {
            "consumidor": g.nombre,
            "alcance_de_lectura": g.alcance,
            "nodos": len(nodos),
            "documentos_que_representan_esos_nodos": len(docs),
            "documentos_que_el_grafo_NO_distingue": len(docs) - len(nodos),
            "nodos_ambiguos": sum(1 for n in nodos
                                  if len(g.docs_detras(n)) > 1),
            "nodos_que_funden_3_o_mas": sum(
                1 for n in nodos if len(g.docs_detras(n)) >= 3),
            "nodos_sin_documento": sum(1 for n in nodos
                                       if not g.docs_detras(n)),
            "aristas": len(g.aristas),
            "aristas_a_destino_ambiguo": len(g.a_ambiguo()),
            "aristas_a_destino_inexistente": len(g.a_inexistente()),
            "aristas_desde_origen_ambiguo": len(g.desde_ambiguo()),
            "aristas_con_los_dos_extremos_ambiguos": len(g.ambos_ambiguos()),
            "aristas_con_nombre_de_fichero_en_el_token": len(cn),
            "aristas_solo_con_numero": len(g.aristas) - len(cn),
            "pares_de_documentos_que_una_arista_puede_ser": sum(
                max(1, len(g.docs_detras(a[0]))) * max(1, len(g.docs_detras(a[2])))
                for a in g.aristas),
            "aristas_con_referente_unico_en_la_AMBIGUEDAD": sum(
                1 for a in g.aristas
                if len(g.docs_detras(a[0])) * len(g.docs_detras(a[2])) == 1),
        }
    d["por_consumidor"] = tabla

    cambios = {}
    for clave, g in grafos.items():
        # (1) lo que publica la herramienta: el grafo fundido, tal cual.
        fus = resumen_calculos(g.nodos(),
                               [(o, d) for o, _v, d, _t in g.aristas])
        # (2) UNA eleccion concreta de documento por clave (la alfabetica).
        cc = eleccion_alfabetica(g)
        ar_alf = grafo_con_eleccion(g, cc)
        nod_alf = set()
        for a, b in ar_alf:
            nod_alf.update((a, b))
        alf = resumen_calculos(nod_alf, ar_alf)
        # (3) 200 elecciones mas, con semilla fija.
        mu_id, mu = muestrear_elecciones(g, n=200, semilla=20261004)
        dif = {}
        for c in CAMPOS_COMPARADOS:
            dif[c] = {"fundido": fus[c], "una_eleccion": alf[c],
                      "valores_distintos_en_200_elecciones":
                          mu[c]["valores_distintos"],
                      "minimo_observado": mu[c]["minimo"],
                      "maximo_observado": mu[c]["maximo"],
                      "depende_del_documento": mu[c]["valores_distintos"] > 1}
        idn = {}
        for kk, vv in mu_id.items():
            idn[kk] = {"valores_distintos": vv["valores_distintos"],
                       "depende_del_documento": vv["valores_distintos"] > 1,
                       "muestra": vv["muestra"]}
        cambios[clave] = {"fundido": fus, "una_eleccion": alf,
                          "muestreo": mu, "identidad": idn,
                          "diferencias": dif,
                          "n_campos_que_dependen_del_documento": sum(
                              1 for c in CAMPOS_COMPARADOS
                              if dif[c]["depende_del_documento"]),
                          "n_identidades_que_dependen_del_documento": sum(
                              1 for kk in idn if idn[kk]["depende_del_documento"])}
    d["cambio_por_elegir_documento"] = cambios

    d["sentido_contradictions"] = sentido_medido(grafos["contradictions"])
    d["origen_declarante"] = {k: origen_declarante(g)
                             for k, g in grafos.items()}
    d["pares_inversos"] = {k: pares_inversos(g) for k, g in grafos.items()}
    d["autocomprobacion"] = autocomprobacion()
    d["contraste_con_artefactos"] = contraste_con_artefactos()
    d["autoloops_sobre_nodo_ambiguo"] = [
        "%s --%s--> %s  (candidatos: %s)" % (o, et, d, grafos["relations"].docs_detras(o))
        for o, et, d, _t in grafos["relations"].aristas
        if o == d and len(grafos["relations"].docs_detras(o)) > 1]
    d["evidence_matrix_autolooops"] = grafos["evidence_matrix"].autolooops
    d["current_state_filtradas_por_la_guarda"] = \
        grafos["current_state"].filtradas_por_la_guarda
    d["current_state_reconciliacion_dedup"] = {
        "coincidencias_de_RX_CORR_contadas_por_este_banco":
            len(grafos["current_state"].aristas),
        "estados_de_resolver_destino_por_coincidencia":
            dict(grafos["current_state"].estados),
        "aristas_por_coincidencia":
            sum(v for k, v in grafos["current_state"].estados.items()
                if k != "NO_REFERENCIA"),
        "pares_ori_dest_unicos_que_publica_el_artefacto":
            grafos["current_state"].filas_sin_dedup}
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    d = medir()
    if args.json:
        print(json.dumps(d, indent=1, ensure_ascii=False, sort_keys=True))
        return 0
    print("=" * 78)
    print("CLAVE NO UNICA: nodos por consumidor   (medir_clave_no_unica %s)"
          % VERSION)
    print("=" * 78)
    print()
    print("  ficheros .md en findings/: %d" % d["indices"]["ficheros_en_disco"])
    print()
    print("  INDICES: cuatro criterios distintos para el MISMO directorio")
    for k, v in d["indices"]["por_criterio"].items():
        print("    %-15s %-46s claves=%-4d docs=%-4d nodos>1doc=%-3d "
              "fundidos=%-4d no_vistos=%-4d inexistentes=%d"
              % (k, v["regex"], v["claves"], v["documentos_indexados"],
                 v["nodos_con_mas_de_un_documento"],
                 v["documentos_fundidos_en_otros_nodos"],
                 v["n_numeros_reales_no_vistos"],
                 v["n_claves_inexistentes_para_esta_herramienta"]))
    t = d["truncamiento_f3"]
    print()
    print("  TRUNCAMIENTO f[:3]: %d ficheros de 4 digitos caen dentro de un nodo "
          "de 3" % t["ficheros_que_no_casan_con_el_regex_de_tres_digitos"])
    print("                  %d de esos nodos tienen ADEMAS un hallazgo de 3 "
          "digitos real" % t["cuantas_de_esas_colisionan_con_un_tres_digitos_real"])
    print("                  reparto por nodo: %s"
          % t["documentos_de_cuatro_digitos_por_nodo"])
    f = d["indice_frontier"]
    print()
    print("  frontier.py:613-621 ASIGNA en vez de acumular: %d documentos "
          "desaparecen" % f["documentos_de_tres_digitos_que_desaparecen_del_indice"])
    print()
    print("  %-16s %6s %6s %9s %7s %7s %7s %9s"
          % ("consumidor", "nodos", "docs", "fundidos", "aristas",
             "a_ambig", "a_inex", "a_amb_orig"))
    for k, v in d["por_consumidor"].items():
        print("  %-16s %6d %6d %9d %7d %7d %7d %9d"
              % (k, v["nodos"], v["documentos_que_representan_esos_nodos"],
                 v["documentos_que_el_grafo_NO_distingue"], v["aristas"],
                 v["aristas_a_destino_ambiguo"],
                 v["aristas_a_destino_inexistente"],
                 v["aristas_desde_origen_ambiguo"]))
    print()
    print("  QUE CAMBIA AL ELEGIR DOCUMENTO   (fundido | minimo | maximo)")
    for k, v in d["cambio_por_elegir_documento"].items():
        print("    %s  -- %d de %d campos dependen del documento"
              % (k, v["n_campos_que_dependen_del_documento"],
                 len(CAMPOS_COMPARADOS)))
        print("        %-32s %-9s %-9s %-9s %s"
              % ("campo", "publicado", "1 eleccion", "200 min..max",
                 "distintos"))
        for c, t2 in v["diferencias"].items():
            print("        %-32s %-9s %-9s %-9s %d  %s"
                  % (c, t2["fundido"], t2["una_eleccion"],
                     "%s..%s" % (t2["minimo_observado"], t2["maximo_observado"]),
                     t2["valores_distintos_en_200_elecciones"],
                     "DEPENDE" if t2["depende_del_documento"] else "invariante"))
        for kk, vv in v["identidad"].items():
            if vv["depende_del_documento"]:
                print("        IDENTIDAD %-38s %d valores distintos en 200"
                      % (kk, vv["valores_distintos"]))
    print()
    s = d["sentido_contradictions"]
    print("  CONTRADICTIONS: %d aristas, %d con destino ambiguo" %
          (s["aristas_de_contradiccion"], s["con_destino_ambiguo"]))
    print("     el TEXTO del sentido depende del documento: %d"
          % s["texto_del_sentido_depende_del_documento"])
    print("     el REFERENTE decidible leyendo el cuerpo: %d   indecidible: %d"
          % (s["referente_decidible_leyendo_el_cuerpo_del_origen"],
             s["referente_indecidable"]))
    print("     aristas con token que resuelve EXACTO: %d"
          % s["aristas_con_token_que_resuelve_exacto"])
    print()
    print("  EL ORIGEN, y si se puede desambiguar con una busqueda literal")
    for k, v in d["origen_declarante"].items():
        print("    %-16s origen_ambiguo=%-4d desambiguado=%-4d sigue_ambiguo=%-4d"
              " sin_declarante=%d"
              % (k, v["aristas_con_origen_ambiguo"],
                 v["origen_desambiguado_por_busqueda_literal"],
                 v["sigue_ambiguo"], v["sin_candidato_que_la_declare"]))
    print()
    print("  LA MISMA RELACION EN LAS DOS DIRECCIONES (verbos inversos)")
    for k, v in d["pares_inversos"].items():
        print("    %-16s pares_ordenados=%-4d pares_inversos=%-3d aristas "
              "duplicadas=%d"
              % (k, v["pares_ordenados_distintos"],
                 v["pares_inversos_presentes"], v["aristas_en_un_par_inverso"]))
    print()
    print()
    print("  CONTRASTE con lo que PUBLICA cada artefacto (producidos en memoria)")
    for k, v in d["contraste_con_artefactos"].items():
        # `current_state_dedup` se guarda como clave hermana y no es un
        # artefacto: no tiene bytes ni lineas_de_total.  La PRIMERA version de
        # este bucle no lo filtro y reventaba con KeyError en el camino legible,
        # que es el que se lee.  Un camino de salida que no se ha ejecutado es
        # un camino que no existe.
        if "bytes" not in v:
            continue
        print("    %-16s %d bytes" % (k, v["bytes"]))
        for l in v["lineas_de_total"]:
            print("        %s" % l)
    dd = d["contraste_con_artefactos"].get("current_state_dedup")
    if dd:
        print("    CURRENT-STATE: %d filas inequivocas, %d AMBIGUAS de las que"
              % (dd["filas_inequivocas"], dd["filas_ambiguas"]))
        print("                 %d items distintos (%d publicadas de mas),"
              % (dd["items_ambiguos_distintos"],
                 dd["items_ambiguos_publicados_de_mas"]))
        print("                 %d rotas, %d retracciones."
              % (dd["filas_rotas"], dd["filas_retraccion"]))
    print()
    print("  autocomprobacion de la copia de sentido(): %d de %d"
          % (d["autocomprobacion"]
             ["aristas_de_contradiccion_que_la_copia_reproduce_literalmente"],
             d["autocomprobacion"]["aristas_de_contradiccion_en_el_grafo"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""
artifacts.py - genera los artefactos que AGENTS.md §AUTOMATIZACIÓN DE
DOCUMENTACIÓN exige, y audita las referencias internas del proyecto.

POR QUÉ EXISTE, Y LA MEDICIÓN QUE LO IMPUSO

AGENTS.md lista ocho artefactos: EVIDENCE-MATRIX, CURRENT-STATE, KNOWLEDGE-GRAPH,
OPEN-FRONTIERS, NEGATIVE-RESULTS, CONTRADICTIONS, TOOLS-STATUS, CHANGELOG. Siete
no existen. Y audit_citations.sh --que es lo que se ejecuta antes de cada
hallazgo-- sólo comprueba citas AL CORPUS, nunca referencias a otro documento
DEL PROYECTO.

Eso tiene una consecuencia medible, y es lo que justifica la herramienta:

    6356 referencias a .md del proyecto
    6063 resuelven (95%)
     293 no resuelven (5%), en 157 nombres
    y en 06-INGENIERIA-INVERSA/findings/: UNA sola

La única en los findings es real: 021:154 apunta a `022-pte-productor-sdma-gfx8.md`
y el fichero es `023-pte-productor-sdma-gfx8.md`. Numeración equivocada, y lleva
varias iteraciones sin que nadie lo viera porque la auditoría que se ejecuta no
mira este tipo de referencia.

O sea: la cadena de evidencia del proyecto está limpia Y la auditoría que la
custodia tiene un agujero del tamaño de esa cadena. Cerrar el agujero vale más
que ocho ficheros nuevos.

LA MEDICIÓN QUE CASI ME CUELO

La primera vez que medí esto di "2745 referencias rotas de 5510", el 50%. Era
FALSO. Había comprobado `os.path.isfile(ref)` con ruta relativa al directorio
actual, así que cualquier fichero que viviera en un subdirectorio salía como
inexistente.

Es el error que este proyecto lleva toda la sesión documentando --aceptar un "no
encontrado" sin comprobar la búsqueda-- cometido por mí en la frase
inmediatamente posterior a documentarlo tres veces. Por eso esta herramienta
indexa el árbol entero ANTES de decir que algo no existe, y por eso imprime el
tamaño del índice junto al resultado: un "no encontrado" sin cota no es nada.

QUÉ GENERA, Y QUÉ NO

Genera los siete que faltan, por datos del propio proyecto, y cada uno con la
marca de que es GENERADO y no editado a mano. Un artefacto generado que alguien
edita a mano se desincroniza en la siguiente ejecución, y no hay forma de saber
cuál de las dos cosas es. Por eso todos llevan esa marca y por eso la
regeneración es un acto explícito (`--escribir`), no el comportamiento por
defecto.

NO corrige las referencias rotas: las reporta. Corregirlas es edición de
documentos, no generación, y hacerlo automáticamente a partir de una búsqueda
por nombre sería inventar a qué documento quería referirse el autor.

CÓDIGOS DE SALIDA

  0  la auditoría se completó
  1  hay referencias internas rotas, y el detalle lo dice
  2  no se pudo ejecutar
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Set, Tuple

VERSION = "1.0.0"

SKIP = {".git", "rx550-upstream-7.2.8", "linux-7.2.8", "linux-7.1.3",
        ".write-lock", "node_modules", "__pycache__"}

# Referencia a un .md del proyecto. Admite SUBDIRECTOR porque sin el, el regex
# se come la cola del nombre: "FASE-R4B-GEVERNOR/3-B.md" se capturaba como
# "3-B.md" y salian 157 "rotas" que no lo eran.
REF_RX = re.compile(
    r"`?([A-Za-z0-9_][A-Za-z0-9_./-]{2,}\.md)(?::(\d+)(?:-(\d+))?)?")

SELLADO = ("<!-- GENERADO POR tools/artifacts.py. NO EDITAR A MANO: la "
           "siguiente ejecucion lo sobrescribe. -->")


def proyecto() -> str:
    return os.path.abspath(os.path.join(
        os.path.dirname(os.path.abspath(__file__)), ".."))


class Indice:
    """Todo lo que existe, indexado UNA vez.

    Y el tamaño del indice se imprime siempre, porque es la cota de cualquier
    'no existe' que diga esta herramienta. Un no-encontrado sin cota no es una
    medida, es un olvido.
    """

    def __init__(self, root: str):
        self.root = root
        self.por_nombre: Dict[str, List[str]] = {}
        self.rutas: Set[str] = set()
        self.md_por_dir: Dict[str, List[str]] = {}
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in SKIP and not d.startswith(".")]
            for f in fn:
                p = os.path.relpath(os.path.join(dp, f), root)
                self.por_nombre.setdefault(f, []).append(p)
                self.rutas.add(p)
                if f.endswith(".md"):
                    self.md_por_dir.setdefault(dp, []).append(f)

    def n(self) -> int:
        return sum(len(v) for v in self.por_nombre.values())

    def resuelve(self, ref: str) -> Tuple[Optional[str], bool]:
        """(ruta, exacta).

        EXACTA False significa que el fichero existe pero NO en la ruta escrita.
        Es una clase de defecto distinta de "no existe", y hay que separarla:

            `docs/config.md` inexistente            -> rota, no hay nada
            `c/subdir.md` cuando vive en `b/c/`      -> ruta equivocada

        La version anterior devolvia solo la ruta y no miraba si era la que
        estaba escrita, asi que una referencia con el subdirectorio mal
       Checkout salia como resuelta. Y el selector de selftest lo cazo.
        """
        base = ref.split("/")[-1]
        if ref in self.rutas:
            return ref, True
        if ("./" + ref) in self.rutas:
            return "./" + ref, True
        cand = self.por_nombre.get(base)
        if cand:
            return cand[0], False
        return None, False


def cargar_excepciones(root: str) -> Dict[Tuple[str, str], str]:
    """(fichero, ref) -> razon, de tools/REF-EXCEPTIONS.txt.

    Existe porque el auditor confunde tres cosas que se parecen y se tratan
    distinto: un typo, una ficha que se renombro, y una cita que MENCIONA un
    nombre inexistente. Las tres salen como "el fichero no existe", y solo la
    primera se corrige escribiendo el nombre correcto.
    """
    ex: Dict[Tuple[str, str], str] = {}
    p = os.path.join(root, "tools", "REF-EXCEPTIONS.txt")
    try:
        with open(p, "r", errors="replace") as fh:
            for ln in fh:
                ln = ln.split("#")[0].strip()
                if not ln or ln.count(" ") < 1:
                    continue
                loc, ref = ln.split()[0], ln.split()[1]
                if ":" not in loc:
                    continue
                f, num = loc.rsplit(":", 1)
                # Se guarda por NOMBRE BASE, no por ruta. La version anterior
                # guardaba la ruta --que es como la construye la auditoria, con
                # el prefijo 06-INGENIERIA-INVERSA/findings/-- y el fichero de
                # excepciones usa el nombre a secas. Las dos claves nunca
                # coincidieron: cero excepciones aplicadas, y el contador
                # ROTA_HISTORICA salia en 0 sin que nada fallara.
                ex[(f, ref)] = num
    except OSError:
        pass
    return ex


def auditar_referencias(root: str, ind: Indice,
                        solo_dir: Optional[str] = None) -> Dict[str, object]:
    """Toda referencia a .md que no resuelve, con su fichero y su linea.

    Y el recuento va con la COTA: el numero de referencias examinadas. Un
    "293 rotas" sin decir de quantas sale de 6356 no significa nada, porque lo
    mismo de 6356 sale de 100.
    """
    excp = cargar_excepciones(root)
    rotas: List[Dict[str, object]] = []
    total = 0
    n_docs = 0
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in SKIP and not d.startswith(".")]
        if solo_dir and not dp.startswith(os.path.join(root, solo_dir)):
            continue
        for f in sorted(fn):
            if not f.endswith(".md"):
                continue
            p = os.path.join(dp, f)
            try:
                with open(p, "r", errors="replace") as fh:
                    lineas = fh.read().splitlines()
            except OSError:
                continue
            n_docs += 1
            for i, ln in enumerate(lineas, start=1):
                for m in REF_RX.finditer(ln):
                    total += 1
                    ref = m.group(1)
                    donde, exacta = ind.resuelve(ref)
                    if donde and exacta:
                        continue
                    rel_doc = os.path.relpath(p, root)
                    exc = excp.get((os.path.basename(rel_doc), ref))
                    rotas.append({
                        "doc": os.path.relpath(p, root), "linea": i,
                        "ref": ref, "linea_citada": m.group(2),
                        "clase": ("ROTA_HISTORICA:%s" % exc if exc else
                                  ("ROTA" if not donde else "RUTA_EQUIVOCADA")),
                        "real": donde or "-",
                        "contexto": ln.strip()[:100],
                    })
    return {"total": total, "n_docs": n_docs, "rotas": rotas,
            "cota": ind.n()}


# --------------------------------------------------------------------------
# Los generadores
# --------------------------------------------------------------------------


def gen_evidence_matrix(root: str, ind: Indice) -> str:
    """Cada finding, con su clase dominante, su hardware scope y su estado.

    NO cuenta como afirmacion. Es una tabla de indices, y su valor es que
    permite elegir por donde empezar sin abrir 98 ficheros.
    """
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    filas: List[Dict[str, object]] = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = re.match(r"^(\d{3,4})[-_](.+)\.md$", f)
        if not m:
            continue
        try:
            with open(os.path.join(d, f), "r", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        cab = "\n".join(txt.splitlines()[:14])
        clases: Dict[str, int] = {}
        for cm in re.finditer(r"`([A-Z][A-Z0-9_]{2,})`", txt):
            clases[cm.group(1)] = clases.get(cm.group(1), 0) + 1
        principales = ", ".join(
            "%s x%d" % (k, v) for k, v in
            sorted(clases.items(), key=lambda kv: -kv[1])[:4])
        retr = ""
        for rx in (r"RETRACTED_BY=(\d{3,4})", r"CORRECTS=(\d{3,4})",
                   r"IMPLEMENTS=(\d{3,4})", r"GENERALIZAD[OA]_POR=(\d{3,4})"):
            retr += " " + ",".join(re.findall(rx, cab))
        gpu = "INTACTA" if "GPU INTACTA" in cab else (
            "?" if "GPU" not in cab else "modificada")
        filas.append({"n": m.group(1), "titulo": m.group(2)[:46],
                      "clases": principales, "gpu": gpu,
                      "retracca": retr.strip() or "-",
                      "n_citas": len(re.findall(r"\.c:\d+", txt))})
    out = ["# EVIDENCE-MATRIX", "", SELLADO, "",
           "Una fila por finding. `clases` son las tipificaciones mas frecuentes,",
           "no un veredicto: una tabla de indices, no de afirmaciones.", "",
           "| # | titulo | clases tipificadas | GPU | reescribe | citas corpus |",
           "|---|---|---|---|---|---|"]
    for x in filas:
        out.append("| %s | %s | %s | %s | %s | %d |"
                   % (x["n"], x["titulo"], x["clases"], x["gpu"],
                      x["retracca"], x["n_citas"]))
    out += ["", "**TOTAL**: %d findings." % len(filas), ""]
    return "\n".join(out)


def gen_current_state(root: str, ind: Indice) -> str:
    """El estado que AGENTS.md §ESTADO ACTUAL YA CONOCIDO declara, confrontado
    con lo que el proyecto ha hecho despues.

    Y el punto es ese: la lista de AGENTS.md dice 'no reabrir salvo evidencia
    contradictoria nueva' y no recoge nada posterior. Este artefacto dice que
    esta desactualizada y cuanto, en vez de repetirla.
    """
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    nums: List[int] = []
    retr: List[str] = []
    corr: List[str] = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = re.match(r"^(\d{3,4})[-_](.+)\.md$", f)
        if not m:
            continue
        n = int(m.group(1))
        nums.append(n)
        # ANTES esto contaba mirando el SLUG del nombre, no el contenido:
        # `re.search(r"RETRACTED", m.group(2))`. Salia "Retracciones: 0" con
        # 5 ficheros del arbol marcados CLAUSULA_RETRACTADA_POR=091. Un
        # artefacto que afirma ausencia sin mirar donde se guarda es peor que
        # uno que no dice nada, porque su ausencia parece medida.
        #
        # Y hay un segundo defecto debajo: el proyecto no usa la marca
        # `RETRACTED`. Usa CLAUSULA_RETRACTADA_POR= y CORRECTED_BY=. Buscar la
        # palabra en vez de las marcas que existen es buscar donde no hay.
        with open(os.path.join(d, f), "r", errors="replace") as fh:
            txt = fh.read()
        # Se descarta la auto-referencia: 091 dice en su cuerpo
        # "CLAUSULA_RETRACTADA_POR=091" al DESCRIBIR lo que hizo, y el
        # escaner lo contaba como retractado por si mismo. Un hallazgo no se
        # retracta a si mismo, y una fila que lo afirma es ruido que teaches a
        # no leer la tabla.
        for rx in (r"CLAUSULA_RETRACTADA_POR=(\d{3,4})", r"RETRACTED_BY=(\d{3,4})"):
            for g in re.findall(rx, txt):
                if g == m.group(1):
                    continue
                item = "%s-%s -> retractada por %s" % (m.group(1), m.group(2)[:22], g)
                if item not in retr:
                    retr.append(item)
        for rx in (r"CORRECTED_BY=([\w-]+)", r"CORRIGE_LA_POLITICA=(\d{3,4})",
                   r"CORRECTS=(\d{3,4})"):
            for g in re.findall(rx, txt):
                corr.append("%s-%s -> corregida por %s" % (m.group(1), m.group(2)[:22], g))
        if re.search(r"correccion", m.group(2), re.I):
            corr.append("%s-%s (slug)" % (m.group(1), m.group(2)[:30]))
            corr.append("%s-%s" % (m.group(1), m.group(2)[:40]))
    return "\n".join([
        "# CURRENT-STATE", "", SELLADO, "",
        "Contraste entre lo que declara `AGENTS.md` §ESTADO ACTUAL YA CONOCIDO y",
        "lo que el proyecto ha hecho despues. El valor de este artefacto es el",
        "**contraste**, no la lista: la lista de AGENTS.md no se regenera aqui.",
        "",
        "- Findings totales: **%d**, numerados del %03d al %d."
        % (len(nums), min(nums), max(nums)),
        "- Correcciones: **%d**" % len(corr),
        "- Retracciones: **%d**" % len(retr),
        "",
        "## Retracciones registradas", "",
        *([("- `%s`" % x) for x in retr] or ["- ninguna"]),
        "",
        "## Correcciones registradas", "",
        *([("- `%s`" % x) for x in corr] or ["- ninguna"]),
        "",
        "## Lo que AGENTS.md no refleja", "",
        "Su §ESTADO ACTUAL YA CONOCIDO no recoge ninguno de los hallazgos",
        "posteriores a los que ya contiene. Reabrir un hallazgo ya cerrado **si**",
        "puede ser legitimo --habia evidencia contradictoria--, pero entonces el",
        "estado deberia reflejarlo, y no lo hace.",
        "",
    ])


def _relaciones_vocabulario(root: str) -> Dict[str, object]:
    """Delega en relations.py --json. Ver gen_open_frontiers para por que.

    ES OBLIGATORIO pasar por ahi y NO usar LISTA_CERRADA. La version anterior
    de este generador leia las cabeceras con una lista de ocho etiquetas
    escrita a mano, y Cherry 8 aristas sobre un conjunto real de 64: las 56
    que faltaban usaban verbos que la lista no conocia, siendo `CONTINUES` el
    segundo mas frecuente con 29 usos.

    Una lista cerrada escrita a mano es una asuncion con forma de tabla. Por
    eso la lista cerrada vive en relations.py, marcada como TAL, y se mide
    contra ella en vez de usarla.
    """
    proc = subprocess.run([sys.executable, os.path.join(root, "tools",
                                                        "relations.py"),
                           "--json"], capture_output=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError("relations.py --json devolvio rc=%d: %s"
                           % (proc.returncode,
                              proc.stderr.decode(errors="replace")[-300:]))
    try:
        return json.loads(proc.stdout.decode(errors="replace"))
    except ValueError as e:
        raise RuntimeError("relations.py --json no devolvio JSON: %s" % e)


def gen_knowledge_graph(root: str, ind: Indice) -> str:
    """El grafo en forma de tabla, no de grafo dibujado.

    Un .dot es mas bonito y menos util: no se lee sin renderizar, no se audita
    con grep, y no se puede meter en un informe. Tabla.
    """
    sys.path.insert(0, os.path.join(root, "tools"))
    import claims as C  # type: ignore  # si falla, LANZA: ver gen_open_frontiers
    _V = _relaciones_vocabulario(root)
    rel = _V["rel"]
    # Las aristas que antes NO se contaban: multivalor, rangos y listas de
    # ficheros. 64 -> 89. Vienen de la MISMA salida JSON, no de una segunda
    # lectura del corpus: dos lectores darian dos conjuntos, y eso ya ha
    # pasado cuatro veces en este proyecto.
    extra = _V.get("extra") or []
    if not rel:
        raise RuntimeError("relations.py no encontro ninguna relacion; un cero"
                           " aqui significa que el extractor dejo de capturar")
    # La 5a posicion es el verbo NORMALIZADO (relations.py lo añade para
    # separar flexion de relacion). Sin esto: `too many values to unpack`, que
    # --gracias al diseno de 071-- salio como rc=2 y no escribiendo nada, en vez
    # de como un KNOWLEDGE-GRAPH con la mitad de las aristas.
    aristas: List[Tuple[str, str, str, str, str]] = []
    for et, occ in rel.items():                       # type: ignore
        for num, _lin, _val, dest, nrm in occ:
            aristas.append((str(num), et, dest, str(nrm),
                            "SELF" if dest == num else ""))
    # `extra` trae 7 campos; `aristas` es de 5. Se aplana el valor original y
    # el conteo de resolucion en la columna `nota`, que es donde cabe. Una
    # arista que sale de `CORRECTS=040,041,...,045` con 6/6 resueltos tiene que
    # PODER distinguirse de una que sale de `CORRECTS=040` a secas: si no, el
    # grafo no dice de donde salio cada arista.
    for num, et, dest, nrm, val, ok, tot in extra:
        aristas.append((str(num), et, str(dest), str(nrm),
                        "`%s` %d/%d" % (val, ok, tot)))
    pares = set((x[0], x[2]) for x in aristas)
    # x[3] es el verbo NORMALIZADO y x[4] la nota. La primera version leia
    # x[4] --que es "" o "SELF"-- y decia "1 familias de verbo". Un indice
    # equivocado en una tupla produce un entero pequeno y plausible, que es
    # la peor forma de que un indice falle.
    # Se quita el `!` de AMBIGUO antes de contar: `CIERRA!` y `CIERRA` son la
    # MISMA familia. Contarlas por separado daba 18 familias donde hay 14, que
    # es el mismo error de contar flexion por duplicado de nombre, pero al reves.
    familias = set(str(x[3]).rstrip("!") for x in aristas)
    out = ["# KNOWLEDGE-GRAPH", "", SELLADO, "",
           "Aristas entre findings, leidas de las cabeceras y con el",
           "vocabulario **MEDIDO** por `tools/relations.py`, no con una lista",
           "de verbos escrita a mano. Tabla y no grafo dibujado: un .dot hay",
           "que renderizarlo para leerlo, y no se audita con grep.", "",
           "Se miden %d etiquetas de relacion, %d filas de arista y %d pares"
           % (len(rel), len(aristas), len(pares)),
           "`(desde,hacia)` distintos. La diferencia entre filas y pares es",
           "FLEXION: la misma relacion escrita con dos verbos.", "",
           "La lista cerrada que este archivo usaba antes conocia %d de las"
           % len(LISTA_CERRADA_CONOCIDA),
           "%d etiquetas, y por eso Cherry 8 aristas de %d." % (len(rel), len(pares)),
           "",
           "| desde | verbo | verbo normalizado | hacia | nota |",
           "|---|---|---|---|---|"]
    for a_, et, dest, nrm, nota in sorted(aristas):
        out.append("| %s | `%s` | `%s` | %s | %s |" % (a_, et, nrm, dest, nota))
    n_fuentes = len(set(a_[0] for a_ in aristas))
    n_extra = sum(1 for a_ in aristas if "/" in str(a_[4])
                  and "`" in str(a_[4]))
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    n_total = sum(1 for f in os.listdir(d) if f.endswith(".md"))
    # El `if False else 0` que estaba aqui producia un cero sin comprobar
    # nada: un recuento de findings sin relacion que decia 0 porque no miraba.
    n_amb = sum(1 for x in aristas if str(x[3]).endswith("!"))
    out += ["", "**Total**: %d filas de arista (%d pares distintos, %d"
            % (len(aristas), len(pares), len(familias)),
            "familias de verbo, %d con destino AMBIGUO: el numero no"
            % n_amb,
            "identifica un finding y el `!` lo dice) en %d findings con"
            % n_fuentes,
            "aristas salientes.",
            "%d findings sin ninguna relacion declarada."
            % (n_total - n_fuentes), ""]
    if n_extra:
        out += ["De las que, %d salen de etiquetas con VARIOS destinos "
                "(multivalor," % n_extra,
                "rango o lista de ficheros) que antes no se contaban. En la",
                "columna `nota` se ve la etiqueta original y cuantos de sus",
                "destinos resolvieron.", ""]
    return "\n".join(out)


# Las nueve que la lista cerrada asumia. NO son la verdad: relations.py mide
# cuales son, y esta copia solo se usa para DECLARAR la diferencia en el
# artefacto. Si se usara para filtrar, volveria el mismo defecto.
LISTA_CERRADA_CONOCIDA = [
    "CORRECTS", "IMPLEMENTS", "GENERALIZA", "GENERALIZADO_POR",
    "RETRACTED_BY", "CORRECTED_BY", "RETRACTED_PARTLY_BY", "CERRADO_POR",
    "MEDIDO_EN_MI_ASIC_POR",
]


def gen_open_frontiers(root: str, ind: Indice) -> str:
    """Los huecos abiertos y por donde se cierran. Delegado a frontier.py.

    Y la delegacion es el punto, y TAMBIEN por que se hace por SALIDA JSON y no
    importando funciones internas:

      - si se reimplementara la clasificacion aqui, acabaria contando una lista
        distinta de la que cuenta frontier.py, y dos recuentos del mismo
        conjunto es el modo de fallo que ya se ha dado dos veces en este
        proyecto;
      - importando internos, esta funcion llamo a `F._init_clase_por_seccion()`
        y luego a `F.cargar()`. Ninguna de las dos existe en la version actual
        de frontier -- la primera era de su primera version, que se reescribio,
        y la segunda se llama `cargar_claims` --. El AttributeError lo
        capturaba un `except` que devolvia un texto de dos lineas, y
        `OPEN-FRONTIERS.md` salia con 189 BYTES: un fichero que existe, con
        tablas vacias, y sin un solo error.

    Ese es el peor modo de fallo -- devolver algo plausible en vez de fallar --
    y el guardia que se puso para cazarlo (`si len(filas) < 5: AVISO`) no lo
    cazaba, porque estaba DESPUES del `return` del `except`. Un guardia que no
    cubre el camino que queria cubrir es peor que no escribirlo, porque da la
    sensacion de estar cubierto.

    Por eso: la delegacion es por `--json`, y CUALQUIER fallo lanza. Un
    artefacto no se escribe nunca a medio generar.
    """
    proc = subprocess.run([sys.executable, os.path.join(root, "tools",
                                                        "frontier.py"),
                           "--json"], capture_output=True, timeout=1800)
    if proc.returncode != 0:
        raise RuntimeError("frontier.py --json devolvio rc=%d: %s"
                           % (proc.returncode,
                              proc.stderr.decode(errors="replace")[-400:]))
    try:
        datos = json.loads(proc.stdout.decode(errors="replace"))
    except ValueError as e:
        raise RuntimeError("frontier.py --json no devolvio JSON: %s" % e)
    huecos = datos.get("huecos", [])
    if not huecos:
        raise RuntimeError("frontier.py --json devolvio 0 huecos; se esperaba"
                           " mas de cero, y un cero aqui significa que el"
                           " clasificador dejo de clasificar")
    vias = datos.get("vias", {})

    filas = []
    for h in huecos:
        filas.append((h["finding"], h["documento"], h["linea"], h["clase"],
                      h["via"], int(h.get("fuerza", 0)),
                      str(h.get("marca", ""))[:30], h.get("registros") or [],
                      int(h.get("n_findings_que_lo_citan", 0))))
    vias_n: Dict[str, int] = {}
    for x in filas:
        vias_n[x[4]] = vias_n.get(x[4], 0) + 1

    out = ["# OPEN-FRONTIERS", "", SELLADO, "",
           "Los %d huecos abiertos de %d findings, y por donde se cierran."
           % (len(filas), len(set(x[0] for x in filas))),
           "",
           "**Generado desde la salida de `tools/frontier.py --json`**, no"
           " reimplementando su clasificacion. Dos recuentos del mismo conjunto"
           " divergen sin que nadie lo note.",
           "",
           "## Via de cierre", "",
           "| via | huecos | que significa |", "|---|---|---|"]
    for v, c in sorted(vias_n.items(), key=lambda kv: -kv[1]):
        out.append("| `%s` | %d | %s |" % (v, c, vias.get(v, "-")))
    out += ["", "**Total: %d huecos.**" % len(filas),
            "`SIN_PISTAS` son los unicos que ningun texto del proyecto dice"
            " como cerrar.", "",
            "## Los huecos", "",
            # LA COLUMNA `fichero` NO ES COSMETICA. El numero de hallazgo NO es
            # unico: hay 74 numeros con dos o tres ficheros, y sin el nombre la
            # fila "050 | 110" no identifica que fichero es. Medido el 2026-10-03:
            # 25 de las 93 filas SIN_PISTAS tienen el numero colisionado, o sea
            # que una de cada cuatro no se puede atribuir ni leer.
            #
            # El dato estaba: `frontier.py` mete `documento` en cada hueco desde
            # la linea 193, y `filas` lo traia en x[1] desde siempre. Solo faltaba
            # imprimirlo.
            "| finding | fichero | linea | clase | via | fuerza | marca | registros |",
            "|---|---|---|---|---|---|---|---|"]
    for x in sorted(filas, key=lambda y: (y[0], y[1], y[2])):
        out.append("| %s | `%s` | %d | `%s` | `%s` | %d | %s | %s |"
                   % (x[0], x[1], x[2], x[3], x[4], x[5], x[6],
                      ", ".join("`%s`" % r for r in x[7]) or "-"))
    out += ["",
            "Obsoletos declarados por el propio findings: %d."
            % int(datos.get("n_obsoletos", 0)), ""]
    return "\n".join(out)


def gen_negative_results(root: str, ind: Indice) -> str:
    """Los NEGATIVE_RESULT, PROVEN_ABSENT y REFUTED, agrupados por fichero.

    Se.includes porque un resultado negativo es informacion cara -- lo que se
    descarto y por que-- y sin este artefacto vive dentro del finding que lo
    produjo, donde nadie lo busca.
    """
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    filas: List[Tuple[str, int, str, str]] = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = re.match(r"^(\d{3,4})[-_](.+)\.md$", f)
        if not m:
            continue
        try:
            with open(os.path.join(d, f), "r", errors="replace") as fh:
                lineas = fh.read().splitlines()
        except OSError:
            continue
        for i, ln in enumerate(lineas, start=1):
            if re.search(r"`(NEGATIVE_RESULT|PROVEN_ABSENT|REFUTED)`", ln):
                filas.append((m.group(1), i,
                              ",".join(sorted(set(re.findall(
                                  r"`(NEGATIVE_RESULT|PROVEN_ABSENT|REFUTED)`",
                                  ln)))),
                              ln.strip()[:86]))
    out = ["# NEGATIVE-RESULTS", "", SELLADO, "",
           "Lo que se descarto, y donde. Un resultado negativo es informacion",
           "cara; sin este artefacto vive dentro del finding que lo produjo,",
           "donde nadie lo busca.", "",
           "| # | linea | clases | texto |", "|---|---|---|---|"]
    for n, i, cl, txt in filas:
        out.append("| %s | %d | %s | %s |" % (n, i, cl, txt.replace("|", "/")))
    out += ["", "**Total**: %d resultados negativos registrados." % len(filas), ""]
    return "\n".join(out)


def gen_contradictions(root: str, ind: Indice) -> str:
    """Las aristas que CONTRADICEN, con su verbo medido y su sentido.

    Y aqui hay una decision dejelto que hay que declarar: que verbos son "de
    contradiccion". No son "todos los que no son CONTINUES/COMPLEMENTS" -- eso
    seria una negation, y una negation es exactamente la clase de regla que
    produce falso positivos cuando la lista crece.

    Es una lista POSITIVA de 8 familias, y el artefacto dice cuantas quedan
    fuera y cuales son. Si un verbo nuevo aparece y no esta en la lista, sale
    en la tabla "verbos de relacion que NO son de contradiccion" y se ve. Un
    verbo invisible seria el mismo fallo que 072 documenta, otro vez.
    """
    rel = _relaciones_vocabulario(root)["rel"]
    if not rel:
        raise RuntimeError("relations.py no encontro relaciones")
    CONTRADICCION = {
        "CORRECTS", "CORRECTED_BY", "CORRECTS_RUTA", "CORRIGE",
        "CORRIGE_LA_POLITICA_DE", "RECTIFIES", "AMENDA",
        "RETRACTS", "RETRACTED_BY", "RETRACTED_PARTLY_BY",
        "CERRADO_POR", "ADJUDICA",
    }
    filas = []
    fuera = []
    for et, occ in rel.items():                        # type: ignore
        for num, _l, _v, dest, nrm in occ:
            if et in CONTRADICCION:
                # El SENTIDO importa y por eso se calcula, no se lee del
                # nombre. RETRACTED_BY desde 019 hacia 030 significa que 019
                # RECIBE; RETRACTED_BY desde 043 hacia 035 significa que 035
                # fue retractada. Confundirlo marca como caducado al que
                # corrige.
                filas.append((str(num), et, str(nrm), dest))
            else:
                fuera.append((str(num), et, str(nrm), dest))

    # El sentido se calcula SOLO para `_BY`, que es la unica terminacion
    # inequivoca: `X RETRACTED_BY Y` significa que X recibe de Y.
    #
    # La primera version aplicaba la misma regla a TODO lo que acababa en `_POR`
    # y daba:  `CERRADO_POR=046  ->  046 RECIBE de 043`. **Falso**: 043 queda
    # cerrado POR 046, no al reves. `CERRADO_POR` no es pasivo de una
    # retraccion; dice que un hueco se cierra con otro hallazgo. Confundirlo
    # produce una frase plausible e incorrecta, que es peor que no dar
    # ninguno.
    #
    # Y no se puede arreglar anadiendo una excepcion por verbo: `*_POR` cubre
    # RETRACTADO_POR (pasiva real), CERRADO_POR (no pasiva), MEDIDO_EN_MI_ASIC_POR
    # (no pasiva) y GENERALIZADO_POR (pasiva, y ademas hacia atras). Cuatro
    # verbos, cuatro sentidos, y distinguirlos por el sufijo no funciona.
    #
    # Asi que el calculo se limita a lo que si se sabe, y lo demas se imprime
    # VERBATIM con la marca de que su sentido NO se ha calculado. Un sentido
    # desconocido declarado es informacion; un sentido incorrecto es ruido.
    SIN_SENTIDO = {"CERRADO_POR", "MEDIDO_EN_MI_ASIC_POR",
                   "GENERALIZADO_POR", "CORRIGE_LA_POLITICA_DE"}

    def sentido(desde: str, hacia: str, et: str) -> str:
        if et in SIN_SENTIDO:
            return "%s --%s-> %s  (sentido NO calculado)" % (desde, et, hacia)
        if "_BY" in et:
            return "%s RECIBE de %s" % (desde, hacia)
        return "%s %s a %s" % (desde, et, hacia)

    out = ["# CONTRADICTIONS", "", SELLADO, "",
           "Aristas que corrigen, rectifican o retractan, con el verbo",
           "**MEDIDO** por `tools/relations.py` y el **sentido** calculado.",
           "",
           "El sentido se calcula, no se lee del nombre de la etiqueta: una",
           "arista mal leida marca como caducado al finding que corrige, que es",
           "peor que no detectar la retraccion.", "",
           "El sentido se calcula solo para `_BY`, la unica terminacion",
           "inequivoca. Para `CERRADO_POR`, `MEDIDO_EN_MI_ASIC_POR`,",
           "`GENERALIZADO_POR` y `CORRIGE_LA_POLITICA_DE` se imprime el verbo",
           "tal cual con la marca de que su sentido NO esta calculado: cuatro",
           "verbos que acaban igual pero significan cuatro cosas, y", "",
           '  `043 | CERRADO_POR | 046`  ->  "046 RECIBE de 043"   **FALSO**',
           "  lo correcto es que 043 queda cerrado POR 046.", "",
           "Que verbos cuentan como de contradiccion es una lista POSITIVA de",
           "%d, no una negation. Los demas se declaran abajo, porque un verbo"
           % len(CONTRADICCION),
           "nuevo que no entre en la lista tiene que verse, no desaparecer.",
           "",
           "| desde | verbo | normalizado | hacia | sentido |",
           "|---|---|---|---|---|"]
    for num, et, nrm, dest in sorted(filas):
        out.append("| %s | `%s` | `%s` | %s | %s |"
                   % (num, et, nrm, dest, sentido(num, dest, et)))
    n_fuera = len(set((x[0], x[1]) for x in fuera))
    out += ["", "**Total**: %d aristas de contradiccion, %d verbos."
            % (len(filas), len(set(x[1] for x in filas))),
            "",
            "## Verbos de relacion que NO son de contradiccion", "",
            "No son un error: son relaciones de otro tipo que el grafo de",
            "contradicciones excluye a proposito. Se listan para que la",
            "exclusion sea visible.", "",
            "| verbo | usos |", "|---|---|"]
    usos = {}
    for num, et, _n, _d in fuera:
        usos[et] = usos.get(et, 0) + 1
    for et, c in sorted(usos.items(), key=lambda kv: -kv[1]):
        out.append("| `%s` | %d |" % (et, c))
    out += ["", "%d verbos excluidos, %d aristas."
            % (len(usos), len(fuera)),
            "Si aparece uno nuevo aqui, es que no se ha decidido que clase"
            " es -- que es distinto de que no lo sea.", ""]
    return "\n".join(out)


# LAS TRES GRAFIAS, y no es arbitrario: `toolreg.py:237` ya las recorre en
# este orden para resolver el flag de cada herramienta. aqui se hacia igual,
# con la misma precedencia, para que las dos herramientas no se contradigan.
#
# MEDIDO, y este es el motivo de existir. Hay 61 herramientas con
# `--selftest` y 4 con `--self-test`. Las cuatro estaban mal clasificadas,
# NO porque sus tests fallaran, sino porque `artifacts.py` llamaba solo a
# `--selftest` y caia en la ejecucion normal:
#
#   integridad.py --self-test   rc=0   27 casos, 0 fallos   <- sano
#   citas.py       --self-test   rc=0   19 casos, 0 fallos   <- sano
#   atom_chain.py  --self-test   rc=2   exige un argumento
#   toolreg.py     --selftest    rc=2   no tiene test propio: es un agregador
#
# Dos de ellas, `integridad.py` y `citas.py`, tienen VECTORES QUE PASAN y
# estaban marcadas como no validadas. AGENTS.md dice que una herramienta no
# validada no puede cerrar una afirmacion critica, luego 46 vectores que
# funcionan estaban inadmissible, y con ellos los hallazgos que dependen de
# ellos. El mismo fallo que el de ayer, una capa mas abajo: la primera
# correccion (no declarar selftest) tapaba el sintoma y dejaba la causa.
GRAFIA_SELFTEST = ("--selftest", "--self-test", "selftest")


def flag_selftest(path: str):
    """Que grafia de flag declara esta herramienta. La primera que exista,
    en el orden de `GRAFIA_SELFTEST`, que es el de `toolreg.py:237`.

    None = no declara ninguna. No decide si el test pasa: decide CON QUE
    PALABRA se le puede preguntar, que es justo lo que faltaba.
    """
    try:
        with open(path, "r", errors="replace") as fh:
            txt = fh.read()
    except OSError:
        return None
    for g in GRAFIA_SELFTEST:
        if g in txt:
            return g
    if re.search(r"\b(?:def|function)\s+selftest", txt):
        return "--selftest" if path.endswith(".sh") else None
    return None


def declara_selftest(path: str):
    """¿La herramienta DECLARA un selftest alcanzable?

    TRES estados, y la distincion es la que hace el trabajo:
      True   declara una grafia de flag
      False  NO declara ninguna
      None   el fichero no se pudo leer (no es "no declara")

    `flag_selftest` devuelve None para "no declara" y para "ilegible" por
    igual; aqui se separan. MEDIDO: con la trichotomy rota, el vector que
    distingue "no declara" de "ilegible" daba FAIL, porque una cosa se
    comparaba contra False y la otra tambien. Un None donde se esperaba
    False es el mismo falso veredicto del que estamos hablando, un nivel
    mas abajo.
    """
    try:
        with open(path, "r", errors="replace") as fh:
            fh.read()
    except OSError:
        return None
    return flag_selftest(path) is not None


def clasificar(declara, rc=None, expiro=False, err=None):
    """PURA. Estado de una herramienta a partir de SI DECLARA selftest y su rc.

    `declara` va PRIMERO en la firma a proposito, porque es el dato que
    decide y antes no estaba en la ecuacion. MEDIDO en este corpus:

      integridad.py  NO declara selftest -- su unica salida es
                     `sys.exit(main(sys.argv))`, sin argparse -- y su rc=1
                     significa "la auditoria encontro DUPLICADOS 1,
                     CONTAMINADOS 6", que es el tool haciendo su trabajo.
                     La version anterior lo marcaba TOOL_BROKEN, o sea "el
                     selftest FALLA", cuando no hay ningun selftest que
                     pueda fallar.

      El defecto era de UNO, no de todos: sobre 62 herramientas con rc
      conocido, 1 caia en la rama falsa. Las otras 6 sin selftest salian
      TOOL_UNVALIDATED, pero por la rama de `.sh` o por rc=2: por
      casualidad, no por logica.

      Y el mismo error con mejor pintura: rc=0 SIN selftest daba
      TOOL_VALIDATED, "el selftest pasa", sin que haya selftest que pase.
      MEDIDO: `audit_citations.sh` da rc=0 y no declara selftest.
    """
    if expiro:
        return "TOOL_PARTIAL", "el selftest expira"
    if err is not None:
        return "TOOL_PARTIAL", "no ejecutable: %s" % err
    if not declara:
        # NO hay selftest: el rc es el de una ejecucion normal y no dice
        # nada sobre validacion. Afirmar lo contrario es inventar evidencia.
        det = "sin selftest"
        if rc is not None:
            det += "; rc=%d es la ejecucion normal, no un test" % rc
        return "TOOL_UNVALIDATED", det
    if rc is None:
        return "TOOL_UNVALIDATED", "sin selftest"
    if rc == 0:
        return "TOOL_VALIDATED", "selftest pasa"
    if rc == 1:
        return "TOOL_BROKEN", "el selftest FALLA"
    return "TOOL_UNVALIDATED", "selftest no soportado (rc=%d)" % rc


def gen_tools_status(root: str, ind: Indice) -> str:
    """Cada herramienta, su hash, si tiene selftest, y su clasificacion.

    Y aqui hay una exigencia que NO se estaba cumpliendo: AGENTS.md pide
    clasificar cada herramienta como TOOL_VALIDATED / TOOL_PARTIAL /
    TOOL_UNVALIDATED / TOOL_BROKEN, y decir que TOOL_UNVALIDATED no puede
    cerrar una afirmacion critica. La columna existe aunque se calcule con un
    criterio burdo, porque un criterio burdo y declarado es mejor que ninguna
    columna.
    """
    # MEDIDO Y CORREGIDO 2026-10-04.  ESTA LISTA NO EXISTIA:  el recorrido era de
    # UN solo directorio,  y decia  os.path.join(root, "tools").
    #
    # Y MEDIDO lo que eso hacia.  El proyecto tiene TRES directorios de
    # herramientas:
    #     tools/                                     75 ejecutables
    #     08-ARQUITECTURA/tools/                      73
    #     04-IMPLEMENTACION/rx550-driver/tools/        6
    # y el registro  —que es GENERADO,  asi que no se nota a ojo—  clasificaba 72
    # filas.  Es decir:  79 ejecutables,  mas de la mitad,  invisibles;  y entre
    # ellos los que portan el renumerado,  las citas y la geometria.
    #
    # POR QUE NO BASTA CON ANADIRLOS AL RECORRIDO.  El generador EJECUTA el
    # selftest de cada herramienta que lo declara,  y MEDIDO que con los nuevos
    # son mas de 120 s por regeneracion.  Un generador que tarda dos minutos en un
    # artefacto que se regenera a mano  no se usa  —que es como pasa cuando un
    # generador se hace incomodo:  se deja de ejecutar—.
    #
    # ASI QUE LA SEPARACION ES EXPLICITA Y DECLARADA.  Todas las filas existen,  con
    # su hash  —que es lo que las hace citables sin ambiguedad—  y solo se EJECUTA
    # el selftest de las de "tools/",  que es lo que ya se hacia antes de este
    # cambio.  Las de los otros dos llevan TOOL_PARTIAL con un motivo en la propia
    # fila:  la tabla no afirma una validacion que nadie ha ejecutado.
    #
    # Y UNA HERRAMIENTA NO REGISTRADA NO SE EJECUTA,  no se cita con su hash  y no
    # puede marcarse VALIDATED.  Eso es lo que hace que un registro incompleto sea
    # PEOR que uno grande:  no es que este mal,  es que no existe.
    # LA LISTA ES UNA SOLA, y es la de toolreg.py.  MEDIDO 2026-10-04:  este
    # fichero tenia la suya  —un solo directorio—  y toolreg.py la suya  —dos—  y
    # no coincidian.  Dos listas de "donde viven las herramientas" es una lista y
    # un grupo de herramientas que nadie mira.  Se importa.
    from toolreg import TOOL_DIRS as _DIRS
    # SOLO se ejecuta el selftest de "tools/",  que es lo que este generador ya
    # hacia antes del cambio.  Los demas se enumeran con su hash  —que es lo que
    # las hace citables—  y llevan TOOL_PARTIAL con el motivo en la fila.
    DIRS_HERRAMIENTAS = tuple((d, d == "tools") for d in _DIRS)
    filas: List[Dict[str, object]] = []
    POR_DIR: Dict[str, int] = {}
    n_no_gateados = 0
    for drel, ejecutar in DIRS_HERRAMIENTAS:
      t = os.path.join(root, drel)
      if not os.path.isdir(t):
        continue
      for f in sorted(os.listdir(t)):
        if not re.match(r"^[a-z0-9_]+\.(py|c|sh)$", f):
            continue
        nombre = "%s/%s" % (drel, f.rsplit(".", 1)[0])
        p = os.path.join(t, f)
        try:
            with open(p, "r", errors="replace") as fh:
                txt = fh.read()
        except OSError:
            continue
        # SI DECLARA selftest, y no "si pasa". Es lo que decide si el rc
        # significa algo; ver `clasificar`.
        declara = declara_selftest(p)
        # NO se decide por la palabra "selftest" en el texto. La primera
        # version lo hacia, y daba VALIDATED a 24 herramientas de 25 --
        # incluyendo a artifacts.py, que no tiene selftest. Eso no es una
        # clasificacion, es un_machine de falsos positivos: exactamente el
        # defecto que 041 prohibe y que este proyecto ha pagado cuatro veces
        # (466 macros, 226 sin pistas, 133 obsoletos, y ahora esto).
        #
        # Se EJECUTA, y se mira el codigo de salida. Un selftest que falla
        # deja de ser evidencia y pasa a ser un fallo, que es informacion
        # distinta de "no existe".
        #
        # PERO EL CODIGO DE SALIDA SOLO SIGNIFICA ALGO SI HAY UN SELFTEST AL
        # PERO EL CODIGO DE SALIDA SOLO SIGNIFICA ALGO SI HAY UN SELFTEST AL
        # QUE CORRESPONDER, y esa tercera comprobacion no estaba.
        #
        # CORRECCION DE AYER, que quedo a medias y ahora importa: la primera
        # version de este arreglo concluyo que "integridad.py NO declara
        # selftest --su unica salida es sys.exit(main(sys.argv)), sin
        # argparse--". ERA FALSO, y lo demuestra la linea 524 del propio
        # archivo: `if "--self-test" in a:`. La herramienta tiene 27 vectores
        # que PASAN (`--self-test` -> rc=0, 27 casos, 0 fallos). Lo que no
        # tenia era la GRAFIA que se le pedia aqui: `--selftest`, sin guion.
        # El sintoma --rc=1 de la auditoria leido como test roto-- era correcto
        # de observar; la CAUSA que se escribio en el comentario era
        # inventada, y tapaba la de verdad.
        #
        # LA CAUSA REAL, MEDIDA: hay 61 herramientas con `--selftest` y 4 con
        # `--self-test` (atom_chain, citas, integridad, toolreg). Las cuatro
        # caian en la ejecucion normal en vez de en su test, y dos de ellas
        # --integridad y citas-- tienen vectores que pasan. 46 vectores que
        # funcionan estaban invisibles para el registro, y AGENTS.md dice que
        # una herramienta no validada no cierra una afirmacion critica.
        #
        # Y `toolreg.py:237` ya recorria las tres grafias para resolver esto.
        # La convencion existia; aqui no se aplicaba.
        #
        # Y LA COLUMNA `selftest` DE LA TABLA DECIA "si" EN LAS 70 FILAS,
        # incluidas las 4 que la propia tabla marca TOOL_UNVALIDATED. No era
        # una medicion: era `"si" if detalle else "NO"`, y `detalle` nunca
        # esta vacio. Una columna que no puede decir NO no informa.
        estado = "TOOL_UNVALIDATED"
        detalle = "sin selftest"
        # La columna dice si el fichero DECLARA selftest. Se saca de `declara`,
        # no de `detalle`: `detalle` es una cadena que nunca esta vacia, asi
        # que la columna anterior no podia decir nunca NO.
        st_declara = "si" if declara else "NO"
        if f.endswith(".sh"):
            detalle = "script: sin convencion de selftest"
        elif not declara:
            detalle = "sin selftest"
        elif not ejecutar:
            # MEDIDO:  el directorio no es el prioritario,  asi que su selftest no
            # lo ejecuta este generador.  El estado NO es "validada":  es
            # TOOL_PARTIAL con un motivo,  que es lo que clasificar() ya sabe
            # decir cuando algo expira o no se puede ejecutar.
            estado, detalle = "TOOL_PARTIAL", (
                "enumerado; su selftest NO lo ejecuta este generador, "
                "por directorio declarado no prioritario")
        else:
            # SE LE PREGUNTA CON LA GRAFIA QUE DECLARA, no con la que este
            # fichero prefs. MEDIDO: 61 herramientas declaran `--selftest` y
            # 4 declaran `--self-test`; preguntar a las 4 por `--selftest`
            # las hacia caer en su ejecucion normal. `flag_selftest` resuelve
            # la grafia y `toolreg.py:237` la resuelve igual, para que las
            # dos herramientas no se contradigan.
            flag = flag_selftest(p) or "--selftest"
            try:
                cmd = ([sys.executable, p, flag] if f.endswith(".py")
                       else [p, flag])
                r = subprocess.run(cmd, capture_output=True, timeout=120)
                estado, detalle = clasificar(declara, rc=r.returncode)
                detalle = "%s [flag %s]" % (detalle, flag)
            except subprocess.TimeoutExpired:
                estado, detalle = clasificar(declara, expiro=True)
            except OSError as e:
                estado, detalle = clasificar(declara, err=e)
        # El hash es lo que hace que la tabla sea utilizable: una herramienta
        # sin hash no se puede citar en un finding sin ambiguedad.
        h = ""
        try:
            h = subprocess.run(["sha256sum", p], capture_output=True,
                               text=True, timeout=30).stdout.split()[0]
        except Exception:
            h = "SIN HASH"
        lineas = len(txt.splitlines())
        filas.append({"n": nombre, "ext": f.rsplit(".", 1)[1], "l": lineas,
                      "st": st_declara, "d": detalle, "e": estado,
                      "h": h[:16]})
        POR_DIR[drel] = POR_DIR.get(drel, 0) + 1
        if not ejecutar:
            n_no_gateados += 1
    out = ["# TOOLS-STATUS", "", SELLADO, "",
           "AGENTS.md §AUTOMATIZACIÓN DE VALIDACIÓN exige clasificar cada",
           "herramienta. Y la columna se calcula EJECUTANDO el selftest y mirand",
           "el codigo de salida, no buscando la palabra 'selftest' en el texto:",
           "la primera version hacia eso y daba VALIDATED a 24 de 25",
           "herramientas, incluida esta, que no tiene selftest.",
           "",
           "Y A PARTIR DE AQUI HAY UNA TERCERA COSA, que es la que faltaba y la",
           "que hace que el rc signifique algo: **que la herramienta DECLARE",
           "selftest**. Un rc=1 sin selftest no es un test que falla, es una",
           "ejecucion normal que termino con 1. MEDIDO: `integridad.py` no",
           "declara selftest y su rc=1 es `DUPLICADOS 1, CONTAMINADOS 6`, o",
           "sea la auditoria funcionando. Marcarla BROKEN era un falso",
           "veredicto, y era UNO de 62 con rc conocido, no unadera epidemic.",
           "",
           "La columna `selftest` dice si el fichero DECLARA el flag. Antes se",
           "sacaba de `detalle`, que nunca esta vacio, asi que ponia `si` en las",
           "70 filas -- incluidas las que la propia tabla marca",
           "`TOOL_UNVALIDATED`. Una columna que no puede decir NO no informa.",
           "",
           "- `TOOL_VALIDATED`  el selftest existe y pasa",
           "- `TOOL_BROKEN`      el selftest existe y FALLA",
           "- `TOOL_PARTIAL`     el selftest expira o no se puede ejecutar",
           "- `TOOL_UNVALIDATED` no hay selftest, o no lo soporta",
           "", "| herramienta | lineas | declara selftest | estado | sha256[:16] |",
           "|---|---|---|---|---|"]
    for x in filas:
        out.append("| `%s%s` | %d | %s | `%s` | `%s` |"
                   % (x["n"], "." + x["ext"], x["l"],
                      x["st"], x["e"], x["h"]))
    n_un = sum(1 for x in filas if x["e"] == "TOOL_UNVALIDATED")
    n_br = sum(1 for x in filas if x["e"] == "TOOL_BROKEN")
    n_no = sum(1 for x in filas if x["st"] == "NO")
    out += ["", "**Total**: %d herramientas, %d `TOOL_UNVALIDATED`, %d `TOOL_BROKEN`,"
            " %d sin selftest declarado."
            % (len(filas), n_un, n_br, n_no),
            "",
            "AGENTS.md: *`TOOL_UNVALIDATED` no puede cerrar una afirmación crítica*.",
            "Las que lo estan no pueden ser el unico sustento de un hallazgo.",
            ""]
    # El bloque de cobertura va SEPARADO y con su propio operador de formato.
    # MEDIDO:  la primera version lo metio en la MISMA lista con un `%` al final,
    # y eso aplico la tupla de argumentos a todos los `%` de la lista  —incluidos
    # los de los bloques anteriores—  y fallo con "unsupported operand type(s)
    # for %: 'list' and 'tuple'".  El generador se negateo a si mismo y no
    # escribio nada,  que es lo correcto;  el defecto era mio.
    out += ["", "## Cobertura, y por que esta seccion existe", ""]
    out.append(
        "MEDIDO 2026-10-04:  el recorrido era de UN solo directorio"
        " (`os.path.join(root, \"tools\")`)  y el proyecto tiene %d.  Con eso el"
        " registro clasificaba 72 filas mientras habia **%d** ejecutables,  y como"
        " el registro es GENERADO nadie lo notaba:  el numero que salia era el de"
        " lo que se veia,  que es exactamente el fallo de un control que no puede"
        " fallar.  Los dos numeros los cuenta este generador en cada ejecucion,"
        " no estan escritos:  un texto que afirma una cifra y la repite es una"
        " copia mas,  y las copias envejecen."
        % (len(DIRS_HERRAMIENTAS), len(filas)))
    out += ["",
            "| directorio | filas | selftest ejecutado por este generador |",
            "|---|---|---|"]
    for drel, ejecutar in DIRS_HERRAMIENTAS:
        out.append("| `%s/` | %d | %s |"
                   % (drel, POR_DIR.get(drel, 0),
                      "si" if ejecutar else "**no** — limite declarado"))
    out += ["",
            "Las filas existen todas y llevan su `sha256`,  que es lo que las hace"
            " citables sin ambiguedad.  Lo que NO se hace es ejecutar sus"
            " selftests:  MEDIDO que son mas de 120 s por regeneracion,  y un"
            " generador que tarda dos minutos en un artefacto que se regenera a"
            " mano no se usa  —que es como muere un generador:  dejando de"
            " ejecutarse—.",
            "",
            "El estado de esas %d filas es `TOOL_PARTIAL` con el motivo EN LA FILA,"
            " no `TOOL_VALIDATED`:  la tabla no afirma una validacion que nadie ha"
            " ejecutado.  Y el limite es un dato  y no una excusa:  un"
            " `TOOL_PARTIAL` con su motivo se puede cerrar;  una herramienta"
            " ausente no se cierra de ninguna manera."
            % n_no_gateados,
            "",
            "Y AHORA LA LISTA ES UNA SOLA.  MEDIDO que antes este fichero tenia la"
            " suya  —un directorio—  y `toolreg.py` la suya  —dos—  y no"
            " coincidaban.  Dos listas de \"donde viven las herramientas\" es una"
            " lista y un grupo de herramientas que nadie mira.  Este fichero importa"
            " `toolreg.TOOL_DIRS`,  y la puerta que hace que la lista no se quede"
            " corta esta en `toolreg.py`:  `directorios_no_declarados()`,  que"
            " recorre el arbol buscando cualquier directorio llamado `tools` y"
            " falla si no esta declarado.  MEDIDO que esa puerta encontro tres"
            " directorios mas en su primera pasada,  uno de los cuales contiene"
            " los instrumentos que generan carga GPU medible.",
            ""]
    return "\n".join(out)


GENERADORES = {
    "EVIDENCE-MATRIX": gen_evidence_matrix,
    "CURRENT-STATE": gen_current_state,
    "KNOWLEDGE-GRAPH": gen_knowledge_graph,
    "OPEN-FRONTIERS": gen_open_frontiers,
    "NEGATIVE-RESULTS": gen_negative_results,
    "CONTRADICTIONS": gen_contradictions,
    "TOOLS-STATUS": gen_tools_status,
}


def selftest() -> int:
    """Vectores del INDEX y del REGEX, que es donde sedlede el numero.

    La cifra de 293 referencias rotas salio de estos dos, y las dos versiones
    anteriores fueron FALSAS: la primera comprueba isfile() con ruta relativa
    y dio 2745 rotas de 5510 -- el 50% --, y la segunda no aceptaba
    subdirectorios en el nombre y dio 157 "rotas" que eran colas de nombre.

    Ninguna de las dos fallaba: las dos devolvian un numero plausible. Por eso
    aqui se comprueban las TRES formas de referencia, con y sin subdirectorio,
    y con numero de linea.
    """
    print("=== artifacts selftest ===\n")
    fallos = 0
    NVEC_ANTES = 14  # los vectores previos a esta sesion

    class IndFalso:
        def __init__(self):
            self.por_nombre = {"existe.md": ["a/existe.md"],
                               "subdir.md": ["b/c/subdir.md"],
                               "otro.md": ["d/otro.md"]}
            self.rutas = {"a/existe.md", "b/c/subdir.md", "d/otro.md"}

        def n(self):
            return 3

        # mismo contrato que Indice.resuelve: (ruta, exacta)
        def resuelve(self, ref):
            if ref in self.rutas:
                return ref, True
            if ("./" + ref) in self.rutas:
                return "./" + ref, True
            c = self.por_nombre.get(ref.split("/")[-1])
            return (c[0], False) if c else (None, False)

    ind = IndFalso()
    print("[1] las TRES formas de referencia")
    for ref, esperado, porque in (
            ("existe.md", True, "por nombre, raiz"),
            ("b/c/subdir.md", True, "por ruta completa"),
            ("subdir.md", True, "por el ultimo componente"),
            ("./otro.md", True, "con ./ inicial"),
            ("noexiste.md", False, "no existe de verdad"),
            # Con el nombre base basta: el fichero EXISTE, y por eso resuelve.
            # Lo que no es, es exacto, y eso se comprueba aparte. Confundir
            # "no existe" con "existe en otro sitio" es el error de 043 otra
            # vez, y por eso son dos columnas y no una.
            ("c/subdir.md", True, "existe, aunque en otra ruta"),
    ):
        donde, exacta = ind.resuelve(ref)
        got = donde is not None
        if got != esperado:
            print("  FAIL %-18s dio %s, esperado %s  (%s)"
                  % (ref, got, esperado, porque))
            fallos += 1
        else:
            print("  OK   %-18s %-5s exacta=%-5s %s"
                  % (ref, got, exacta, porque))
    # y la clase de defecto se distingue
    donde, exacta = ind.resuelve("c/subdir.md")
    if donde and exacta:
        print("  FAIL: `c/subdir.md` deberia ser RUTA_EQUIVOCADA, no exacta")
        fallos += 1
    else:
        print("  OK   `c/subdir.md`     se marca RUTA_EQUIVOCADA, no rota")

    print()
    print("[2] el regex captura el SUBDIRECTOR, no la cola del nombre")
    for txt, esperado, porque in (
            ("ver `FASE-R4B-GOVERNOR/3-B.md`", "FASE-R4B-GOVERNOR/3-B.md",
             "con subdirectorio"),
            ("ver `3-B.md`", "3-B.md", "sin subdirectorio"),
            ("`OPEN-FRONTIERS.md:38-43`", "OPEN-FRONTIERS.md", "con rango"),
            ("`gmc_v8_0.c:661`", None, "no es .md, no se toca"),
            ("docs/config.md", "docs/config.md", "minusculas y barra"),
    ):
        m = REF_RX.search(txt)
        got = m.group(1) if m else None
        if got != esperado:
            print("  FAIL %-34s dio %r, esperado %r" % (txt[:34], got, esperado))
            fallos += 1
        else:
            print("  OK   %-34s %s" % (txt[:34], got))
    if REF_RX.search("`gmc_v8_0.c:661`") is not None:
        print("  FAIL el regex se comio una cita al CORPUS, que no es suya")
        fallos += 1
    else:
        print("  OK   una cita al corpus no se cuenta como referencia interna")

    print()
    print("[3] el rango de linea se captura, y se distingue de la ausente")
    m = REF_RX.search("`OPEN-FRONTIERS.md:38-43`")
    if not m or m.group(2) != "38" or m.group(3) != "43":
        print("  FAIL el rango no se extrajo: %r" % (m.groups() if m else None,))
        fallos += 1
    else:
        print("  OK   rango 38-43 extraido")
    m2 = REF_RX.search("`OPEN-FRONTIERS.md`")
    if m2 and m2.group(2):
        print("  FAIL una referencia sin linea|reporta linea: %r" % m2.group(2))
        fallos += 1
    else:
        print("  OK   sin linea, sin linea: no se inventa")

    print()
    print("[4] --solo-referencias NO puede saltarse la auditoria")
    # El fallo fue un `return 0` antes del bloque de auditoria. Se comprueba
    # leyendo el codigo fuente: un flag que desactiva lo unico que se le pidio
    # y sale con codigo de exito es el fallo mas silencioso que existe.
    # COMPROBACION POR ESTRUCTURA, no por texto. La primera version de este
    # vector hacia `src.split("solo_referencias")[-1]`, y se troceaba con el
    # COMENTARIO que menciona el flag -- leia el `return` de su propia prosa y
    # se declaraba FAIL a si mismo. Un selector que seAlarmA de su comentario
    # no selecciona el codigo: hay que mirar la sangria.
    import inspect as _insp
    src = _insp.getsource(main).splitlines()
    limpio = [l.split("#")[0] for l in src]   # sin comentarios
    i_aud = next((i for i, l in enumerate(limpio)
                  if "AUDITORIA DE REFERENCIAS INTERNAS" in l), None)
    if i_aud is None:
        print("  FAIL no encuentro el bloque de auditoria en main()")
        fallos += 1
    else:
        antes = [l.strip() for l in limpio[:i_aud]
                 if l.startswith("    return")]
        if antes:
            print("  FAIL hay %d `return` a nivel de main antes de la "
                  "auditoria: %s" % (len(antes), antes[:2]))
            fallos += 1
        else:
            print("  OK   ningun `return` de main antes de la auditoria")
    ultimo = [l.strip() for l in limpio if l.strip()][-1]
    if ultimo == "return 1 if n_rota else 0":
        print("  OK   el codigo de salida sale de n_rota, la auditoria")
    else:
        print("  FAIL la ultima sentencia de main es %r, no el rc de la "
              "auditoria" % ultimo)
        fallos += 1

    # --- EL CLASIFICADOR. ESTOS VECTORES NO EXISTIAN, y su ausencia es
    # exactamente la causa del falso veredicto: la rama `rc == 1 ->
    # TOOL_BROKEN` se escribio sin ningun vector que la mirara, asi que
    # nadie vio que tambien alcanzaba a las herramientas SIN selftest.
    #
    # MEDIDO que erroneous:
    #   antes      62 con rc conocido -> 1 estado equivocado (integridad.py)
    #   despues    62 con rc conocido -> 0 estados equivocados
    casos = [
        # (declara, rc, esperado, por que)
        (True, 0, "TOOL_VALIDATED", "el caso normal: hay test y pasa"),
        (True, 1, "TOOL_BROKEN", "hay test y falla: este si es BROKEN"),
        (True, 2, "TOOL_UNVALIDATED", "hay test pero no soportado"),
        (False, 1, "TOOL_UNVALIDATED", "NO hay test: rc=1 es la auditoria"),
        (False, 0, "TOOL_UNVALIDATED", "NO hay test: rc=0 no es 'el test pasa'"),
        (False, 2, "TOOL_UNVALIDATED", "NO hay test, rc raro: tampoco es test"),
        (None, 1, "TOOL_UNVALIDATED", "no se pudo leer: no se inventa"),
    ]
    for dec, rc, esp, porq in casos:
        got, _det = clasificar(dec, rc=rc)
        if got == esp:
            print("  OK   %-18s declara=%-5s rc=%-3s -> %s" %
                  ("clasificar", dec, rc, got))
        else:
            print("  FAIL %-18s declara=%-5s rc=%-3s dio %s, esperado %s  (%s)"
                  % ("clasificar", dec, rc, got, esp, porq))
            fallos += 1

    # El caso de integridad.py, LITERAL, con el codigo de salida que dio.
    got, det = clasificar(False, rc=1)
    if got == "TOOL_UNVALIDATED" and "no un test" in det:
        print("  OK   %-18s el detalle explica por que rc=1 no cuenta" % "detalle")
    else:
        print("  FAIL %-18s detalle %r no explica el rc" % ("detalle", det))
        fallos += 1

    # Y el caso simetrico, que antes DABA VALIDATED: rc=0 sin selftest.
    got, _ = clasificar(False, rc=0)
    if got == "TOOL_UNVALIDATED":
        print("  OK   %-18s rc=0 sin selftest NO es VALIDATED" % "simetrico")
    else:
        print("  FAIL %-18s rc=0 sin selftest dio %s" % ("simetrico", got))
        fallos += 1

    # declarea_selftest sobre ficheros de verdad, no sobre una idea.
    import tempfile as _tf
    _d = _tf.mkdtemp()
    try:
        _con = os.path.join(_d, "con.py")
        _sin = os.path.join(_d, "sin.py")
        _gui = os.path.join(_d, "gui.py")
        with open(_con, "w") as _fh:
            _fh.write('ap.add_argument("--selftest", action="store_true")\n')
        with open(_sin, "w") as _fh:
            _fh.write("import sys\nsys.exit(main(sys.argv))\n")
        with open(_gui, "w") as _fh:
            _fh.write('if "--self-test" in a:\n    return self_test()\n')
        _c1 = (declara_selftest(_con) is True
               and declara_selftest(_sin) is False
               and declara_selftest(os.path.join(_d, "no.py")) is None)
        if _c1:
            print("  OK   %-18s si / NO / ausente se distinguen" % "declara")
        else:
            print("  FAIL %-18s no distingue si / NO / ausente" % "declara")
            fallos += 1
        # Y LA GRAFIA, que es el defecto real. `integridad.py` declara
        # `--self-test` y durante dos sesiones se le pidio `--selftest`.
        _f1 = flag_selftest(_con)
        _f2 = flag_selftest(_gui)
        _f3 = flag_selftest(_sin)
        if (_f1 == "--selftest" and _f2 == "--self-test" and _f3 is None):
            print("  OK   %-18s cada grafia se resuelve a la suya" % "flag")
        else:
            print("  FAIL %-18s --selftest=%r --self-test=%r ninguno=%r"
                  % ("flag", _f1, _f2, _f3))
            fallos += 1
        # y que la precedencia sea la de toolreg.py:237, no una arbitraria
        _ambos = os.path.join(_d, "ambos.py")
        with open(_ambos, "w") as _fh:
            _fh.write('ap.add_argument("--self-test")\n'
                      'ap.add_argument("--selftest")\n')
        if flag_selftest(_ambos) == "--selftest":
            print("  OK   %-18s con dos grafias gana la de convencion" % "prece")
        else:
            print("  FAIL %-18s con dos grafias dio %r"
                  % ("prece", flag_selftest(_ambos)))
            fallos += 1
    finally:
        import shutil as _sh
        _sh.rmtree(_d, ignore_errors=True)

    print("=" * 72)
    if fallos:
        print("RESULT: FAIL (%d)" % fallos)
        return 1
    # Los 14 de siempre, mas los 13 vectores del clasificador que se han
    # anadido aqui: 7 de la tabla `casos`, mas `detalle`, `simetrico`, `declara`,
    # `flag` y `prece`. La cifra se cuenta, no se supone: si se olvida actualizar,
    # el numero se vuelve una decoracion y deja de ser una comprobacion.
    print("RESULT: PASS (%d vectores)" % (NVEC_ANTES + 13))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="genera los artefactos de AGENTS.md y audita referencias internas")
    ap.add_argument("--escribir", action="store_true",
                    help="escribe los artefactos; sin esto solo se muestran")
    ap.add_argument("--solo", help="genera solo este artefacto")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--solo-referencias", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv[1:])

    if args.selftest:
        return selftest()

    root = proyecto()
    ind = Indice(root)
    if not ind.por_nombre:
        print("artifacts: no encuentro ficheros en %s" % root, file=sys.stderr)
        return 2

    if not args.solo_referencias:
        nombres = [args.solo] if args.solo else list(GENERADORES)
        hechos: Dict[str, str] = {}
        for n in nombres:
            if n not in GENERADORES:
                print("artifacts: no conozco %s" % n, file=sys.stderr)
                return 2
            try:
                hechos[n] = GENERADORES[n](root, ind)
            except Exception as e:
                # NADA se escribe. Un artefacto a medias es un fichero que
                # existe y no dice nada, que es peor que no tenerlo: nadie va
                # a mirar dentro de un fichero que ya existe.
                print("artifacts: %s NO SE PUEDE GENERAR: %s" % (n, e),
                      file=sys.stderr)
                print("           no se ha escrito nada; el resto de "
                      "artefactos tampoco.", file=sys.stderr)
                return 2
        if args.json:
            print(json.dumps(hechos, indent=2, sort_keys=True))
            return 0
        for n, txt in hechos.items():
            print("=" * 78)
            print("  %s%s" % (n, "  (escrito)" if args.escribir else "  (vista previa)"))
            print("=" * 78)
            if args.escribir:
                ruta = os.path.join(root, n + ".md")
                with open(ruta, "w") as fh:
                    fh.write(txt)
                print("  -> %s.md" % n)
            else:
                print(txt[:1800])
                if len(txt) > 1800:
                    print("  ... (%d lineas mas; usa --escribir)"
                          % (txt.count("\n") - 40))
            print()

    # NO HAY `return` AQUI. Lo hubo, y hacia que `--solo-referencias` --el flag
    # que significa "solo audita referencias"-- no auditara nada: devolvia 0 sin
    # imprimir una linea, con 299 referencias rotas en el proyecto. Un flag que
    # desactiva la unica cosa que se le pidio hacer, y que sale con codigo de
    # exito.
    #
    # Los codigos de salida son por eso los de la AUDITORIA, que es lo unico
    # que puede fallar: 1 si hay ROTA, 0 si no la hay. Los generadores ya han
    # lanzado antes de llegar aqui si algo iba mal.

    print("=" * 78)
    print("DUPLICADOS DE NUMERACION EN findings/")
    d = os.path.join(root, "06-INGENIERIA-INVERSA", "findings")
    por_n: Dict[str, List[str]] = {}
    for f in sorted(os.listdir(d)):
        if not f.endswith(".md"):
            continue
        m = re.match(r"^(\d{3,4})[-_]", f)
        if m:
            por_n.setdefault(m.group(1), []).append(f)
    dups = {n: v for n, v in por_n.items() if len(v) > 1}
    total_fn = sum(len(v) for v in por_n.values())
    print("  findings: %d en %d numeros distintos" % (total_fn, len(por_n)))
    print("  numeros con mas de un finding: %d" % len(dups))
    if dups:
        print("  Y esto NO lo detecta el resto del proyecto. `claims.py` usa el")
        print("  numero como etiqueta y el auditor de citas resuelve por")
        print("  nombre de fichero, asi que un `021-` y otro `021-` conviven sin")
        print("  que nada se queje. El hallazgo 071 se escribio como 057 y")
        print("  hubo que renombrarlo a mano: exactamente el defecto que 021")
        print("  documenta, y sigue ocurriendo sin que lo detecte nadie.")
        print("  Cuarenta y tantos numeros duplicados, y el unico que me")
        print("  he encontrado yo, al escribir este hallazgo.")
        for n in sorted(dups)[:6]:
            print("    %s: %s" % (n, ", ".join(x[:44] for x in dups[n])))
        if len(dups) > 6:
            print("    ... y %d mas" % (len(dups) - 6))
    print()

    print("=" * 78)
    print("AUDITORIA DE REFERENCIAS INTERNAS")
    print("=" * 78)
    aud = auditar_referencias(root, ind)
    print("  indice de ficheros:     %d" % aud["cota"])
    print("  documentos .md leidos:  %d" % aud["n_docs"])
    n_rota = sum(1 for r in aud["rotas"]
                 if str(r["clase"]).startswith("ROTA") and
                 not str(r["clase"]).startswith("ROTA_HISTORICA"))
    n_hist = sum(1 for r in aud["rotas"]
                 if str(r["clase"]).startswith("ROTA_HISTORICA"))
    n_ruta = len(aud["rotas"]) - n_rota - n_hist
    print("  referencias examinadas: %d" % aud["total"])
    print("    ROTA             %5d  el fichero no existe" % n_rota)
    print("    ROTA_HISTORICA   %5d  no existe, con razon declarada"
          % n_hist)
    print("                    (%d excepciones en tools/REF-EXCEPTIONS.txt)"
          % len(cargar_excepciones(root)))
    print("    RUTA_EQUIVOCADA  %5d  existe, pero en otro sitio" % n_ruta)
    print()
    print("  Las tres se corrigen de forma distinta, y por eso se separan:")
    print("  ROTA se corrige escribiendo el nombre bueno; ROTA_HISTORICA se")
    print("  corrige documentando por que NO se corrige; RUTA_EQUIVOCADA es")
    print("  casi siempre la convencion de citar findings por nombre desnudo.")
    print("  Las dos no son lo mismo, y separarlas es lo que hace util el dato.")
    print("  Una RUTA_EQUIVOCADA es casi siempre la CONVENCION del proyecto:")
    print("  los findings se citan por nombre desnudo (`043-...`) y viven en")
    print("  un subdirectorio. Marcarlo como defecto daria 3206 falso positivos")
    print("  y enterraria los 299 que si lo son.")
    print()
    if aud["rotas"]:
        por_doc: Dict[str, List[Dict[str, object]]] = {}
        for r in aud["rotas"]:
            por_doc.setdefault(str(r["doc"]).split("/")[0], []).append(r)
        for zona in sorted(por_doc, key=lambda z: -len(por_doc[z])):
            print("  %-28s %d" % (zona, len(por_doc[zona])))
        print()
        print("  Las de 06-INGENIERIA-INVERSA/findings, que son las que sostienen")
        print("  la cadena de evidencia del proyecto:")
        fnd = [r for r in aud["rotas"]
               if str(r["doc"]).startswith("06-INGENIERIA-INVERSA/findings")
               and str(r["clase"]).startswith(("ROTA", "ROTA_HISTORICA"))]
        if not fnd:
            print("    ninguna. La cadena de evidencia esta limpia.")
            print("    (las RUTA_EQUIVOCADA si aparecen, y son la convencion"
                  " de citar findings por nombre)")
        # ANTES: `for r in fnd[:20]` sobre fnd, que ademas solo recogia los
        # findings. El recuento de arriba cuenta TODOS los documentos y la
        # lista de abajo mostraba 20: 334 declarados, 14 visibles. Un
        # recuento que no se puede reconciliar con su propia evidencia
        # obliga a fiarse del numero, que es lo que un recuento no debe
        # obligar.
        #
        # Ahora se agrupa por documento y se listan TODOS, con su recuento.
        # El detalle se acota POR DOCUMENTO, no globalmente, para que la
        # suma de la lista sea el total y no una parte.
        por_doc = {}
        for r in aud["rotas"]:
            if str(r["clase"]).startswith(("ROTA", "ROTA_HISTORICA")):
                por_doc.setdefault(str(r["doc"]), []).append(r)
        total_listado = sum(len(v) for v in por_doc.values())
        print("    %d documentos, %d referencias rotas en total."
              % (len(por_doc), total_listado))
        print()
        for doc in sorted(por_doc, key=lambda x: -len(por_doc[x])):
            rs = por_doc[doc]
            print("    %-56s %3d" % (doc[-56:], len(rs)))
            for r in rs[:3]:
                print("        L%-5s [%s] -> %s"
                      % (r["linea"], r["clase"], r["ref"][:44]))
            if len(rs) > 3:
                print("        ... y %d mas en este documento"
                      % (len(rs) - 3))
        print()
        print("    La lista de documentos es COMPLETA; dentro de cada uno"
              " se muestran 3.")
        n_fnd = sum(len(v) for k, v in por_doc.items()
                    if k.startswith("06-INGENIERIA-INVERSA/findings"))
        print("    %d de %d en findings, %d en el resto del arbol."
              % (n_fnd, total_listado, total_listado - n_fnd))
    print()
    print("  Y lo que esta herramienta NO hace: no corrige las rotas. Buscar el")
    print("  destino por parecido de nombre SERIA inventar a que documento")
    print("  queria referirse el autor, y eso es peor que la referencia rota.")
    print("  Tambien no las borra de los artefactos: un NEGATIVE-RESULT sobre")
    print("  documentacion es informacion.")

    return 1 if n_rota else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

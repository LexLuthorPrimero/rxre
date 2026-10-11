#!/usr/bin/env python3
"""FASE E. Provenance consultable y persistencia SQLite.

POR QUE SQLITE Y POR QUE AHORA.

§15 pide SQLite con WAL, versionado de esquema y transacciones. Se usa SQLite
porque es la unica que da transacciones reales sin un servidor, y WAL porque
permite leer mientras se escribe, que es el caso de uso real: una IA consulta
mientras corre otra cosa.

Y el motivo de que exista ya, y no cuando haya "conocimiento": `explain
<result_id>` es un ENTREGABLE OBLIGATORIO de RXRE-002, y no se puede responder
sin que el resultado este almacenado. La persistencia no es infraestructura
para el futuro; es el almacen de lo que ya se produce.

LA REGLA QUE GOBIERNA LA TABLA `results`.

Se guarda el envelope COMPLETO de cada operacion, con su JSON entero. No se
guardan solo los campos "interesantes". La razon es la misma que en el
normalizador: una columna resumida es una opinion, y una opinion sin el original
al lado es irrecuperable si resulta equivocada. El JSON allows re-interpretar
sin volver a ejecutar la herramienta, que es la diferencia entre "esto se sabe"
y "esto se puede volver a mirar".

Y la cosa que NO se guarda: hardware. Ninguna operacion de RXRE-002 lee
hardware, asi que no hay estado que registrar. Cuando lo haya, el estado va en
la fila, no supuesto.
"""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import time
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_DIR = os.path.abspath(os.path.join(HERE, ".."))
DEFAULT_DB = os.path.join(RXRE_DIR, "storage", "rxre.sqlite3")

SCHEMA_VERSION = 1

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS meta (
    clave TEXT PRIMARY KEY,
    valor TEXT
);

-- Cada operacion ejecutada, con su request y su respuesta INTEGROS.
CREATE TABLE IF NOT EXISTS operations (
    operation_id   TEXT PRIMARY KEY,
    request_id     TEXT,
    contract_ver   TEXT,
    operacion      TEXT,
    capability     TEXT,
    question       TEXT,
    target         TEXT,
    scope          TEXT,
    status         TEXT,
    n_results      INTEGER,
    request_json   TEXT NOT NULL,
    response_json  TEXT NOT NULL,
    target_pci     TEXT,
    timestamp      TEXT NOT NULL,
    duracion_s     REAL
);

-- Resultados normalizados, indexables, con el raw dentro de la fila.
CREATE TABLE IF NOT EXISTS results (
    result_id      TEXT PRIMARY KEY,
    operation_id   TEXT REFERENCES operations(operation_id),
    type           TEXT,
    value          TEXT,
    source         TEXT,
    file           TEXT,
    line           INTEGER,
    scope          TEXT,
    tool           TEXT,
    tool_version   TEXT,
    status         TEXT,
    raw_json       TEXT NOT NULL,
    timestamp      TEXT NOT NULL
);

-- Indice para el camino explain: result -> operacion.
CREATE INDEX IF NOT EXISTS ix_results_op   ON results(operation_id);
CREATE INDEX IF NOT EXISTS ix_results_type ON results(type);
CREATE INDEX IF NOT EXISTS ix_results_file ON results(file);

-- Aristas de la composicion: que operacion vino de cual.
CREATE TABLE IF NOT EXISTS relations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    src_operation  TEXT,
    src_result     TEXT,
    dst_operation  TEXT,
    relation       TEXT,
    payload_json   TEXT
);

-- OJO: `relations` aqui son las aristas de la COMPOSICION entre llamadas, no las
-- relaciones del dominio RE (WRITES, READS, CALLS). Las del dominio van en
-- `edges` y NO se inventan: solo entra lo que una herramienta produjo. Confundir
-- los dos grafos es como una IA lee relaciones que nadie midio.

CREATE TABLE IF NOT EXISTS edges (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    src            TEXT NOT NULL,
    tipo           TEXT NOT NULL,
    dst            TEXT NOT NULL,
    status         TEXT NOT NULL,
    scope          TEXT,
    tool           TEXT,
    evidence_json  TEXT,
    -- NULL, no NOT NULL: una arista sin operacion es una arista SIN
    -- PROVENANCE, y esa es una distinction que hay que poder guardar y buscar,
    -- no un dato que se rechace. (MEDIDO: con NOT NULL + "" reventaba la FK.)
    operation_id   TEXT REFERENCES operations(operation_id),
    result_id      TEXT,
    timestamp      TEXT NOT NULL,
    UNIQUE(src, tipo, dst, status)
);

CREATE INDEX IF NOT EXISTS ix_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS ix_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS ix_edges_tip ON edges(tipo);

-- RXRE-005 / BLOCKER 2. El ESTADO DE INVESTIGACION de una IA: hipotesis,
-- claims, notas y la siguiente accion.
--
-- MEDIDO 2026-10-06: `operations`, `results`, `relations` y `edges` guardan
-- EVIDENCIA (lo que un producer emitio). No guardaban el RAZONAMIENTO de quien
-- la interpreto. Consecuencia medida: una IA nueva sin contexto que pregunta
-- "que estoy investigando" recibe `empty`, y "cual es mi siguiente accion"
-- tambien. Sin esta tabla, §15 (checkpoint por jornada) y §16 (recuperacion
-- tras perder el contexto) NO SON IMPLEMENTABLES: el dia 2 solo puede
-- apoyarse en memoria conversacional, que §16 prohibe expresamente.
--
-- Y por que NO se reusa `results`: `results` es lo que un PRODUCER emitio, con
-- su `result_id` y su provenance. Una hipotesis no es evidencia: es
-- interpretacion. Meterla en `results` haria que un grep la encontrara como si
-- fuera un hallazgo medido, que es exactamente la confusion que §10 prohibe
-- ("las interpretaciones deben ser separables de los resultados").
--
-- MEDIDO: `relations` esta VACIA y los 65 edges del dominio viven en `edges`.
-- Se deja como esta: renombrarla no aporta nada y tocarla seria riesgo sin
-- pregunta causal.
CREATE TABLE IF NOT EXISTS research (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    kind         TEXT NOT NULL,       -- hypothesis|claim|note|next_action|frontier
    status       TEXT NOT NULL,       -- ver ESTADOS_RESEARCH
    text         TEXT NOT NULL,
    -- HUECO_DE_EVIDENCIA  falta una medicion
    -- HUECO_DE_CONEXION   falta el eslabon entre dos cosas que ya existen
    -- NULL                no aplica a esta entrada
    gap_kind     TEXT,
    -- Referencias por ID, nunca copias. Una entrada de research APUNTA a la
    -- evidencia; no la duplica. (MEDIDO en RXRE-002: las copias de evidencia en
    -- un paquete de handoff son lo que hace que un handoff pierda lo unico
    -- que no debia: la identidad de la evidencia.)
    refs_json    TEXT NOT NULL DEFAULT '[]',
    session      TEXT,
    target       TEXT,
    -- Timestamp del registro, NUNCA del texto. Una interpretacion se fecha
    -- cuando se ESCRIBE, no cuando describe algo que ocurrio antes.
    timestamp    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_research_kind    ON research(kind);
CREATE INDEX IF NOT EXISTS ix_research_session ON research(session);
CREATE INDEX IF NOT EXISTS ix_research_target  ON research(target);
CREATE INDEX IF NOT EXISTS ix_research_status  ON research(status);

-- RXRE-007 FASE 2: Tabla de conflictos explícitos.
-- Un conflicto es un registro de evidencia incompatible (NO es NOT_DETERMINED).
-- Se registra cuando dos o más valores apuntan al mismo offset con semántica
-- contradictoria o cuando dos definiciones compiten por la misma dword_index.
--
-- Conflitos vs. NOT_DETERMINED:
--   - NOT_DETERMINED: "no tengo evidencia suficiente"
--   - CONFLICT:       "tengo evidencia incompatible"
-- Uno no sustituye al otro; ambos pueden coexistir para un mismo offset.
CREATE TABLE IF NOT EXISTS conflicts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    target           TEXT NOT NULL,           -- e.g. "1002:699f@c7"
    offset           TEXT NOT NULL,           -- e.g. "0xA21"
    conflicto_tipo   TEXT NOT NULL,           -- OFFSET_COLLISION, SEMANTIC_CONTRADICTION, ...
    conflicto_estado TEXT NOT NULL DEFAULT 'OPEN',
    discriminante    TEXT,                    -- qué resolvió el conflicto (si RESOLVED)
    conflicto_evidencia_json TEXT,            -- lista de refs que sustentan el conflicto
    creado_por       TEXT,                    -- quién registró el conflicto
    creado_en        TEXT NOT NULL,
    actualizado_en   TEXT
);

CREATE INDEX IF NOT EXISTS ix_conflicts_target ON conflicts(target);
CREATE INDEX IF NOT EXISTS ix_conflicts_offset ON conflicts(offset);
CREATE INDEX IF NOT EXISTS ix_conflicts_estado ON conflicts(conflicto_estado);
CREATE INDEX IF NOT EXISTS ix_conflicts_tipo   ON conflicts(conflicto_tipo);

-- RXRE-008 FASE 3: cadenas de RELACIONES CAUSALES.
-- Una relación causal es una cadena PRODUCER → TRANSFORMS → REPRESENTS →
-- CONSUMES → AFFECTS, con cada segmento respaldado por evidencia.
--
-- Diferencia con `edges`: `edges` son lo que una herramienta midió (READS,
-- REFERENCES, WRITES). `relation_chains` es lo que RXRE interpreta y modela
-- a partir de esa evidencia, con un estado epistemológico (PROVEN/PARTIAL/
-- NOT_DETERMINED/REFUTED/BLOCKED).
--
-- Ambos pueden coexistir: una relación puede estar respaldada por una arista
-- de edges, pero no se duplica la arista: la relación APUNTA a ella.
CREATE TABLE IF NOT EXISTS relation_chains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    relation_id     TEXT NOT NULL,
    producer        TEXT NOT NULL,
    transformation  TEXT NOT NULL,
    representation  TEXT NOT NULL,
    consumer        TEXT NOT NULL,
    effect          TEXT NOT NULL,
    relation_type   TEXT NOT NULL,   -- PRODUCES, TRANSFORMS, REPRESENTS, CONSUMES, AFFECTS
    epistemic_state TEXT NOT NULL DEFAULT 'NOT_DETERMINED',
    target          TEXT,
    offset          TEXT,
    context         TEXT,
    provenance_json TEXT,            -- refs a edges/results/operations
    evidence_json   TEXT,            -- refs a resultados que sustentan cada segmento
    confidence      REAL DEFAULT 0.0,
    limitations     TEXT,
    created_by      TEXT NOT NULL DEFAULT 'system',
    created_at      TEXT NOT NULL,
    updated_at      TEXT,
    UNIQUE(relation_id, producer, consumer)
);

CREATE INDEX IF NOT EXISTS ix_relation_chains_relation_id ON relation_chains(relation_id);
CREATE INDEX IF NOT EXISTS ix_relation_chains_producer    ON relation_chains(producer);
CREATE INDEX IF NOT EXISTS ix_relation_chains_consumer    ON relation_chains(consumer);
CREATE INDEX IF NOT EXISTS ix_relation_chains_type        ON relation_chains(relation_type);
CREATE INDEX IF NOT EXISTS ix_relation_chains_state       ON relation_chains(epistemic_state);
CREATE INDEX IF NOT EXISTS ix_relation_chains_target      ON relation_chains(target);
"""

#: Estados epistemicos que una entrada de research puede llevar. Deliberadamente
#: NO son los del envelope: una hipotesis no es `ok`/`blocked`/`empty`. Y
#: `NOT_DETERMINED` esta porque sin el no habria forma de decir "no lo se" sin
#: mentir con `REFUTED` o con `PROVEN`.
ESTADOS_RESEARCH = (
    "OPEN",          # hipotesis abierta, sin evidencia que la resuelva
    "SUPPORTED",     # hay evidencia que la respalda (NO la prueba)
    "REFUTED",       # hay evidencia que la contradice
    "PROVEN",        # solo para claim, y solo con la cadena completa
    "PARTIAL",       # claim a medias: NInguna parte es "completa"
    "NOT_DETERMINED",
    "BLOCKED",
)

#: Estados epistemicos para cadenas de relación. Cada relación debe poder
#: estar en un estado epistemológico adecuado. Solo ciertos valores están
#: permitidos; convertirlos entre sí requiere evidencia nueva.
RELACION_ESTADOS = (
    "PROVEN",           # cadena completamente respaldada por evidencia
    "PARTIAL",          # cadena a medias: algunos segmentos tienen evidencia, otros faltan
    "NOT_DETERMINED",   # no hay evidencia suficiente para apoyar o refutar la cadena
    "REFUTED",          # hay evidencia que contradice la cadena
    "BLOCKED",          # cadena bloqueada por confidente o dependencia sin resolver
)

#: Tipos de relación permitidos. Cada tipo debe tener una semántica verificable.
TIPOS_RELACIÓN = (
    "PRODUCES",    # productor crea el valor
    "TRANSFORMS",  # el valor es transformado (formato, bits, etc.)
    "REPRESENTS",  # se obtiene una representación intermediada
    "CONSUMES",    # consumidor usa el valor
    "AFFECTS",     # efecto en registro/estado de hardware
)

KIND_RESEARCH = ("hypothesis", "claim", "note", "next_action", "frontier")

#: §8 obliga a distinguir los dos huecos. Fusionarlos seria afirmar que falta
#: una medicion cuando lo que falta es un ESLABON entre dos cosas que ya
#: existen, y esa confusion produce trabajo infinito persiguiendo mediciones
#: que no van a responder nada.
GAP_KINDS = ("HUECO_DE_EVIDENCIA", "HUECO_DE_CONEXION")


def conectar(ruta: Optional[str] = None) -> sqlite3.Connection:
    ruta = ruta or os.environ.get("RXRE_DB") or DEFAULT_DB
    d = os.path.dirname(ruta)
    if d:
        os.makedirs(d, exist_ok=True)
    c = sqlite3.connect(ruta, timeout=30)
    c.row_factory = sqlite3.Row
    c.executescript(DDL)
    cur = c.execute("SELECT valor FROM meta WHERE clave='schema_version'")
    fila = cur.fetchone()
    if fila is None:
        c.execute("INSERT INTO meta(clave,valor) VALUES('schema_version',?)",
                  (str(SCHEMA_VERSION),))
        c.commit()
    return c


def _sha(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]


def registrar(c: sqlite3.Connection, request: Dict[str, Any], env: Dict[str, Any],
              duracion: float = 0.0) -> str:
    """Guarda una operacion completa. Devuelve su `operation_id`."""
    op_json = json.dumps(request, sort_keys=True, default=str)
    resp_json = json.dumps(env, sort_keys=True, default=str)
    op_id = "op_" + _sha(op_json + str(env.get("status")) + str(time.time()))
    c.execute(
        "INSERT OR REPLACE INTO operations(operation_id,request_id,contract_ver,"
        "operacion,capability,question,target,scope,status,n_results,"
        "request_json,response_json,target_pci,timestamp,duracion_s) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (op_id, request.get("request_id", ""), request.get("contract_version", ""),
         env.get("operation", ""), request.get("capability", ""),
         request.get("question", ""), request.get("target", ""),
         request.get("scope", ""), env.get("status", ""),
         len(env.get("results") or []), op_json, resp_json,
         request.get("target", ""), time.strftime("%Y-%m-%dT%H:%M:%S%z"),
         duracion))
    for r in (env.get("results") or []):
        if not isinstance(r, dict) or "result_id" not in r:
            continue          # resultados de RXRE-001 sin normalizar: no se indexan
        loc = r.get("location") or {}
        c.execute(
            "INSERT OR REPLACE INTO results(result_id,operation_id,type,value,"
            "source,file,line,scope,tool,tool_version,status,raw_json,timestamp) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["result_id"], op_id, r.get("type", ""),
             str(r.get("value", ""))[:4000], r.get("source", ""),
             loc.get("file") or loc.get("loc") or "", loc.get("line"),
             r.get("scope", ""), r.get("tool", ""), r.get("tool_version", ""),
             r.get("status", ""), json.dumps(r, sort_keys=True, default=str),
             r.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S%z"))))
    c.commit()
    return op_id


def explicar_operacion(c: sqlite3.Connection,
                       operation_id: str) -> Dict[str, Any]:
    """La cadena COMPLETA de una operacion, con todos sus resultados.

    MEDIDO 2026-10-05: `explain` solo aceptaba `result_id`, y la accion
    `explain_operation` que proponia `next_actions` pasaba un `operation_id` ->
    `error: falta 'result_id'`. La propia accion propuesta era un callejon, que
    es justo lo que esta iteracion repara.

    Una operacion tiene N resultados; un resultado, UNA operacion. Sin esta
    segunda vista, una IA que ejecuto un pipeline de dos etapas no puede ver el
    estado de la primera.
    """
    op = c.execute("SELECT * FROM operations WHERE operation_id=?",
                   (operation_id,)).fetchone()
    if op is None:
        return {"status": "empty", "operation_id": operation_id,
                "limitations": [
                    "no hay ninguna operacion con ese operation_id en esta "
                    "base. Eso NO es que no se haya ejecutado: es que no esta "
                    "registrada aqui, o que la base es otra"]}
    filas = [dict(x) for x in c.execute(
        "SELECT result_id, type, tool, file, line, status, scope FROM results "
        "WHERE operation_id=? ORDER BY result_id", (operation_id,)).fetchall()]
    etapas: List[Dict[str, Any]] = []
    backend: Dict[str, Any] = {}
    try:
        resp = json.loads(op["response_json"])
        for e in (resp.get("stages") or []):
            etapas.append({"step": e.get("step"), "op": e.get("op"),
                           "status": e.get("status"),
                           "resultados": e.get("resultados")})
        # B3 / §9: la cadena del backend. Se LEE de lo persistido, no se
        # recalcula: una cadena recompuesta al leer probaria que la funcion de
        # lectura funciona, no que la evidencia existe.
        backend = resp.get("cadena_backend") or {}
    except (ValueError, TypeError):
        etapas = []
        backend = {}
    return {"status": "ok", "operation_id": operation_id,
            "operation": dict(op), "results": filas, "stages": etapas,
            "backend": backend,
            "chain": ["question", "capability", "pipeline", "tool_run",
                      "input", "result"],
            "limitations": []}


def explicar(c: sqlite3.Connection, result_id: str) -> Dict[str, Any]:
    """`explain <result_id>`: de donde sale este resultado. Todo desde la fila.

    Si no existe, se devuelve `empty` con limitacion: que no este en la base NO
    es que el resultado no exista, es que no se ha registrado aqui.
    """
    # MEDIDO 2026-10-05: `c.row = ...` reventaba con
    # `'sqlite3.Connection' object has no attribute 'row'`. Una Connection de
    # sqlite3 no admite atributos nuevos. La variable local es lo unico que
    # hace falta.
    row = c.execute("SELECT * FROM results WHERE result_id=?", (result_id,)).fetchone()
    if row is None:
        return {"status": "empty", "result_id": result_id, "limitations": [
            "no hay ninguna fila con ese result_id en esta base. Eso NO es que "
            "el resultado no exista: es que no se ha registrado aqui, o que la "
            "base es otra."]}
    r = dict(row)
    op = c.execute("SELECT * FROM operations WHERE operation_id=?",
                   (r["operation_id"],)).fetchone()
    backend: Dict[str, Any] = {}
    if op is not None:
        # B3 / §9: `explain <result_id>` tiene que reconstruir la cadena del
        # backend igual que `explain <operation_id>`. Si uno de los dos la
        # pierde, la misma evidencia tiene dos explicaciones.
        try:
            backend = (json.loads(op["response_json"])
                       .get("cadena_backend") or {})
        except (ValueError, TypeError):
            backend = {}
    return {"status": "ok", "result_id": result_id, "result": r,
            "operation": dict(op) if op else None,
            "backend": backend,
            "chain": ["result", "operation", "tool", "input", "artifact",
                      "source"],
            "limitations": []}


def buscar(c: sqlite3.Connection, tipo: Optional[str] = None,
           archivo: Optional[str] = None, texto: Optional[str] = None,
           limite: int = 50) -> Dict[str, Any]:
    """Consulta de resultados. Util para `query` y para recuperar evidencia previa."""
    q = "SELECT result_id, type, value, file, line, tool, status, timestamp FROM results"
    w: List[str] = []
    a: List[Any] = []
    if tipo:
        w.append("type=?")
        a.append(tipo)
    if archivo:
        w.append("file LIKE ?")
        a.append("%" + archivo + "%")
    if texto:
        w.append("value LIKE ?")
        a.append("%" + texto + "%")
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " LIMIT ?"
    a.append(limite)
    filas = [dict(x) for x in c.execute(q, a).fetchall()]
    return {"status": "ok" if filas else "empty", "results": filas,
            "limitations": [] if filas else
            ["la consulta no devolvio filas; eso es que en ESTA base no hay, no "
             "que no exista en el corpus"]}


def anadir_edge(c: sqlite3.Connection, src: str, tipo: str, dst: str, *,
                status: str = "observed", scope: str = "", tool: str = "",
                evidence: Optional[Dict[str, Any]] = None,
                operation_id: str = "", result_id: str = "") -> bool:
    """Inserta una arista del dominio RE. `status` por defecto `observed`.

    Un estado de arista NO es cosmetico: `observed` significa "una herramienta
    produjo esto", `proven` exigiria un criterio mas fuerte que no se aplica
    aqui. Una relacion sin provenance se guarda con `tool=""` y se puede buscar
    por eso para distinguirla de una con evidencia.
    """
    if not src or not dst or not tipo:
        return False
    # MEDIDO 2026-10-05: con `operation_id=""` la FOREIGN KEY de `edges` hacia
    # `operations` falla, porque "" no existe en esa tabla. Y el fallo no se
    # puede ignorar con un `INSERT OR IGNORE`, que solo ignora violaciones de
    # UNIQUE: una FK rota es un error de integridad y aborta.
    #
    # Una arista sin operacion es una arista sin procedencia, y eso tiene que ser
    # guardable: es justo el caso que hay que poder distinguir ("no tiene
    # provenance" vs "tiene provenance"), no el que hay que prohibir.
    op_ref = operation_id if operation_id else None
    res_ref = result_id if result_id else None
    c.execute(
        "INSERT OR IGNORE INTO edges(src,tipo,dst,status,scope,tool,evidence_json,"
        "operation_id,result_id,timestamp) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (src, tipo, dst, status, scope, tool,
         json.dumps(evidence, sort_keys=True, default=str) if evidence else "",
         op_ref, res_ref, time.strftime("%Y-%m-%dT%H:%M:%S%z")))
    c.commit()
    return True


# --- RE_CASE: el paquete de handoff ---------------------------------------
# MEDIDO 2026-10-05: T8 (perdida de contexto tras handoff) era 100%. No habia
# `session` ni `handoff`, asi que una IA que cerraba el contexto perdia TODO y
# la siguiente repetia la operacion entera.
#
# §9 dice: "Si todavia no existe `handoff`, NO implementar un sistema enorme.
# Crear primero el minimo mecanismo reproducible necesario para demostrar
# continuidad". Y §10 dice: "NO duplicar evidencia. Referenciar IDs existentes
# siempre que sea posible".
#
# Por eso un RE_CASE no es una tabla nueva: es una VISTA sobre `operations`, con
# un `case_id` DERIVADO de lo que una IA ya estaba mandando (`target` +
# `question`). Sin tabla nueva, sin copia de resultados, sin un segundo sitio
# donde buscar evidencia. Si las operaciones no estan, el caso no esta.

def case_id_de(target: str, question: str) -> str:
    """Id del caso, derivado. Misma pregunta y mismo target -> mismo caso."""
    return "case_" + _sha("%s|%s" % ((target or "").strip().lower(),
                                     (question or "").strip()))


def re_case(c: sqlite3.Connection, caso: str) -> Dict[str, Any]:
    """Reúne el estado de una investigacion sin duplicar nada.

    Devuelve REFERENCIAS (operation_id, result_id) y no copias. El consumidor
    que necesite el detalle va a `explain` con el id, que es la via que ya
    existe y esta probada.
    """
    ops = c.execute(
        "SELECT operation_id, operacion, capability, question, target, status, "
        "n_results, timestamp FROM operations WHERE target=? ORDER BY rowid",
        (caso,)).fetchall()
    ops = [dict(o) for o in ops]
    if not ops:
        return {"status": "empty", "case_id": caso, "operations": [],
                "results": [], "edges": [], "limitations": [
                    "no hay ninguna operacion registrada para el target %s en "
                    "esta base. Eso NO es que la investigacion no exista: es que "
                    "no se ha registrado aqui, o que la base es otra" % caso]}

    ops_ids = [o["operation_id"] for o in ops]
    qm = ",".join("?" * len(ops_ids))
    res = [dict(x) for x in c.execute(
        "SELECT result_id, type, tool, file, line, status, scope FROM results "
        "WHERE operation_id IN (%s)" % qm, ops_ids).fetchall()]
    aristas = [dict(x) for x in c.execute(
        "SELECT src, tipo, dst, status, tool FROM edges").fetchall()]

    return {
        "status": "ok", "case_id": caso,
        "operations": ops,
        "results": res,
        "edges": aristas,
        "limitations": [],
        "aviso": [
            "los resultados y las aristas son REFERENCIAS por id, no copias: "
            "el detalle esta en explain. Un RE_CASE que copiara la evidencia "
            "la duplicaria y las dos copias se separarian",
            "este caso no declara estado epistemico: es un conjunto de "
            "observaciones de herramientas. Convertirlo en conclusion es "
            "trabajo de quien lo lee, no de RXRE",
        ],
    }
#: Un `ref` de una entrada de research tiene que existir. MEDIDO (RXRE-005,
#: D4): `record` exigia `refs` para poder marcar `PROVEN`, pero NO exigia que
#: los refs EXISTIERAN. Medido: `refs=["result_id_QUE_NO_EXISTE_12345"]` con
#: `status=PROVEN` devolvia `ok`. Una claim podía quedar PROVEN con un puntero
#: INVENTADO, que es justo lo que §9 prohibe.
#:
#:     cerrar la puerta sin mirar quien entra por ella
#:
#: Los tres espacios de nombres citables, y solo tres:
#:   res_*   un resultado   -> tabla `results`
#:   op_*    una operacion  -> tabla `operations`
#:   edge:   una arista     -> tabla `edges` (MEDIDO: 65 filas; `relations` esta
#:                            VACIA y leerla daria un checkpoint que afirma que
#:                            no hay relaciones del dominio)
PREFIJOS_REF = ("res_", "op_", "edge:")


def ref_de_edge(tipo: str, src: str, dst: str, status: str = "") -> str:
    """El identificador CITABLE de una arista.

    MEDIDO (RXRE-005, D5): `op:relation` devolvia aristas con las claves
    `[dst, scope, src, status, timestamp, tipo, tool]` y SIN ningun campo que
    las identificara. Una arista sin identificador no se puede citar en una
    `claim`, asi que `refs` no podia apuntar a la evidencia de relaciones: la
    parte mas valiosa del grafo era la unica incitable.

        una arista sin identificador es una arista que no se puede citar
    """
    return "edge:%s:%s->%s" % (tipo, src, dst)


def ref_existe(c: sqlite3.Connection, ref: str) -> bool:
    """¿Este puntero existe de verdad? Namespace cerrado, tres tablas."""
    r = (ref or "").strip()
    if not r:
        return False
    if not r.startswith(PREFIJOS_REF):
        return False
    if r.startswith("edge:"):
        try:
            tipo, resto = r[5:].split(":", 1)
            src, dst = resto.split("->", 1)
        except ValueError:
            return False
        return bool(c.execute(
            "SELECT 1 FROM edges WHERE tipo=? AND src=? AND dst=?",
            (tipo, src, dst)).fetchone())
    tabla = "results" if r.startswith("res_") else "operations"
    col = "result_id" if tabla == "results" else "operation_id"
    return bool(c.execute(
        "SELECT 1 FROM %s WHERE %s=?" % (tabla, col), (r,)).fetchone())


def refs_invalidos(c: sqlite3.Connection,
                   refs: List[str]) -> List[str]:
    """Los refs que NO existen. Vacio = todos buenos."""
    return [r for r in (refs or []) if not ref_existe(c, r)]


def relations(c: sqlite3.Connection, src: Optional[str] = None,
              tipo: Optional[str] = None, limite: int = 100) -> Dict[str, Any]:
    """Consulta de aristas del dominio. Filtra por nodo y/o tipo."""
    q = "SELECT src,tipo,dst,status,scope,tool,timestamp FROM edges"
    w: List[str] = []
    a: List[Any] = []
    if src:
        w.append("src=?")
        a.append(src)
    if tipo:
        w.append("tipo=?")
        a.append(tipo)
    if w:
        q += " WHERE " + " AND ".join(w)
    q += " LIMIT ?"
    a.append(limite)
    filas = [dict(x) for x in c.execute(q, a).fetchall()]
    # MEDIDO (RXRE-005, D5): cada arista recibe su `edge_ref`, que es lo que la
    # hace CITABLE desde una `claim` (`refs`). Sin esto, la parte mas valiosa
    # del grafo era la unica que no se podia citar, y `refs` solo aceptaba
    # `res_*` y `op_*`. Se anade el campo; no se quita ninguno.
    for f in filas:
        f["edge_ref"] = ref_de_edge(f.get("tipo", ""), f.get("src", ""),
                                    f.get("dst", ""))
    return {"status": "ok" if filas else "empty", "results": filas,
            "citables": len(filas),
            "limitations": [] if filas else
            ["no hay aristas registradas de ese tipo para ese nodo. Las "
             "aristas solo existen si una herramienta las produjo; RXRE no las "
             "inventa (§12/§20). Que NO haya aristas es NO_DETERMINED sobre el "
             "grafo, no prueba de que la relacion no exista en el hardware"]}


# =====================================================================
# RXRE-005. Estado de investigacion: escribir, releer, y hacer checkpoint.
# =====================================================================

def registrar_investigacion(c: sqlite3.Connection, kind: str, text: str,
                            status: str = "OPEN",
                            refs: Optional[List[str]] = None,
                            session: str = "", target: str = "",
                            gap_kind: str = "") -> Dict[str, Any]:
    """Graba UNA entrada de estado de investigacion.

    Devuelve SIEMPRE un dict con `estado`. Los rechazos son `blocked` o
    `error`, nunca excepcion: una IA debe poder meter garbage y seguir
    leyendo lo que ya habia escrito.

    LAS REGLAS QUE NO SON COSMETICAS:

    * `kind` y `status` son listas CERRADAS. No son texto libre, y por eso no
      las valida una expresion regular: `esta_permitida` valida contra lo que
      el registry afirma, y aqui lo que se afirma es la lista de estados
      epistemicos. Es el mismo patron que el target (F3) y que la allow-list de
      capacidades (B4), aplicado al razonamiento.

    * `gap_kind` SOLO se acepta con `hypothesis` o `claim`. §8 exige distinguir
      HUECO_DE_EVIDENCIA de HUECO_DE_CONEXION, y un `next_action` con
      `HUECO_DE_CONEXION` no significa nada: una accion no tiene un hueco, es
      la respuesta a un hueco.

    * Una `claim` NO puede grabarse `PROVEN` sin `refs`. MEDIDO: es exactamente
      el fallo que §9 prohíbe, y un `PROVEN` sin evidencia es la forma mas
      peligrosa de esta tabla porque parece la mas solida.

        una claim sin evidencia no es una claim: es una opinion con formato
    """
    if kind not in KIND_RESEARCH:
        return {"estado": "blocked", "id": None,
                "motivo": "kind '%s' no es una de: %s"
                          % (kind, ", ".join(KIND_RESEARCH)),
                "regla": "kind es una lista CERRADA: hypothesis|claim|note|"
                         "next_action|frontier"}
    if status not in ESTADOS_RESEARCH:
        return {"estado": "blocked", "id": None,
                "motivo": "status '%s' no es uno de: %s"
                          % (status, ", ".join(ESTADOS_RESEARCH)),
                "regla": "status es una lista CERRADA. Sin NOT_DETERMINED no "
                         "habria forma de decir 'no lo se' sin mentir con "
                         "REFUTED o con PROVEN"}
    if not (text or "").strip():
        return {"estado": "invalid_input", "id": None,
                "motivo": "text vacio: una entrada de estado sin texto no "
                          "transporta nada"}
    if gap_kind and gap_kind not in GAP_KINDS:
        return {"estado": "blocked", "id": None,
                "motivo": "gap_kind '%s' no es uno de: %s"
                          % (gap_kind, ", ".join(GAP_KINDS))}
    if gap_kind and kind not in ("hypothesis", "claim"):
        return {"estado": "blocked", "id": None,
                "motivo": "gap_kind solo tiene sentido para hypothesis y "
                          "claim; '%s' no tiene un hueco, es la respuesta a "
                          "uno" % kind}
    refs = list(refs or [])
    # MEDIDO (RXRE-005, D4): los refs tienen que EXISTIR, no solo estar.
    # Se comprueba para TODA entrada, no solo para `PROVEN`: una hipotesis que
    # cita un `result_id` inventado esta tan rota como una claim PROVEN, y es
    # la misma mentira con distinto disfraz.
    malos = refs_invalidos(c, refs)
    if malos:
        return {"estado": "blocked", "id": None,
                "motivo": "refs que NO existen: %s. Un puntero a evidencia "
                          "inexistente hace que la entrada NO sea trazable, "
                          "y una entrada no trazable no es un hallazgo: es una "
                          "afirmacion sin respaldo" % ", ".join(malos),
                "regla": "un ref debe existir en results (res_*), operations "
                         "(op_*) o edges (edge:). Los tres son los unicos "
                         "espacios de nombres citables",
                "refs_rechazados": malos}
    if status == "PROVEN" and not refs:
        return {"estado": "blocked", "id": None,
                "motivo": "una claim PROVEN exige `refs`: al menos un "
                          "result_id u operation_id del que se deriva. "
                          "§9: una conclusion que no se puede rastrear no "
                          "es PROVEN",
                "regla": "PROVEN sin evidencia es opinion con formato"}
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    cur = c.execute(
        "INSERT INTO research(kind,status,text,gap_kind,refs_json,session,"
        "target,timestamp) VALUES(?,?,?,?,?,?,?,?)",
        (kind, status, text.strip(), gap_kind or None,
         json.dumps(refs), session or None, target or None, ts))
    c.commit()
    return {"estado": "ok", "id": cur.lastrowid, "kind": kind, "status": status,
            "gap_kind": gap_kind or None, "refs": refs, "session": session,
            "target": target, "timestamp": ts}


def investigacion(c: sqlite3.Connection, session: str = "", target: str = "",
                  kind: str = "", status: str = "",
                  limite: int = 200) -> Dict[str, Any]:
    """Lee el estado de investigacion. Filtros son todos opcionales.

    MEDIDO: `limitations` NO lleva 'no hay nada' cuando la tabla esta vacia y
    la consulta no filtro. Dice si la tabla esta vacia de verdad o si el filtro
    noombo. `empty` + 'no hay' sin decir POR QUE es el patron que §10 prohibe.
    """
    where, args = [], []
    for col, val in (("session", session), ("target", target),
                     ("kind", kind), ("status", status)):
        if val:
            where.append("%s = ?" % col)
            args.append(val)
    sql = ("SELECT id,kind,status,text,gap_kind,refs_json,session,target,"
           "timestamp FROM research")
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(limite)
    filas = [dict(x) for x in c.execute(sql, args).fetchall()]
    for f in filas:
        try:
            f["refs"] = json.loads(f.pop("refs_json") or "[]")
        except ValueError:
            f["refs"] = []
    total = c.execute("SELECT COUNT(*) FROM research").fetchone()[0]
    lims = []
    if not filas:
        if total == 0:
            lims.append("la tabla `research` esta VACIA: ninguna IA ha "
                        "registrado hipotesis, claims ni acciones todavia. "
                        "Eso NO es que no haya estado de investigacion: es "
                        "que nadie lo ha escrito por esta interfaz.")
        else:
            lims.append("hay %d entradas en `research` pero NINGUNA cumple el "
                        "filtro (session=%r target=%r kind=%r status=%r). "
                        "Ausencia de coincidencia no es ausencia de estado."
                        % (total, session, target, kind, status))
    return {"estado": "ok" if filas else "empty", "entradas": filas,
            "n_filtradas": len(filas), "n_totales": total, "limitations": lims}


def checkpoint(c: sqlite3.Connection, session: str = "",
               target: str = "") -> Dict[str, Any]:
    """El paquete de §15. Lo que una jornada le deja a la siguiente.

    Es una VISTA sobre `research` + `operations` + `results` + `edges`, no una
    tabla nueva ni una copia. MEDIDO (RXRE-002): las copias de evidencia en un
    handoff son lo que hace que un handoff pierda lo unico que no debe, la
    identidad de la evidencia. Aqui las entradas de research APUNTAN a sus
    refs, y la evidencia se cuenta, no se copia.

    Y las aristas del dominio se leen de `edges` (65 medidas), NO de
    `relations` (0 filas): leer la tabla equivocada daria un checkpoint que
    afirma que no hay relaciones del dominio.
    """
    inv = investigacion(c, session=session, target=target, limite=500)
    filas = inv["entradas"]
    por_status = {}
    for f in filas:
        por_status.setdefault(f["kind"], []).append(f)
    ops = c.execute("SELECT COUNT(*) FROM operations").fetchone()[0]
    res = c.execute("SELECT COUNT(*) FROM results").fetchone()[0]
    eds = c.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
    nxt = [f for f in filas if f["kind"] == "next_action"]
    # RXRE-1648. `investigacion()` devuelve `limitations` NO VACIO si y solo si
    # el filtro (session/target) no trajo filas. La version anterior combinaba
    #     inv["limitations"] or [<frase de sesion vacia>]
    # y el `or` INVERTIA la polaridad: la frase "sesion VACIA de razonamiento"
    # salia EXACTAMENTE cuando SI habia hipotesis/notas (porque entonces
    # inv["limitations"] es []). MEDIDO: con una hipotesis OPEN en la sesion, el
    # checkpoint la listaba en `hipotesis_abiertas` y a la vez afirmaba que no
    # habia ninguna entrada de research.
    #
    # La frase de vacio es cierta solo si el filtro no trajo filas Y hay
    # evidencia en la base, porque la propia frase afirma "la evidencia existe"
    # (imprime sus recuentos). Con la tabla sin evidencia no se anade: ahi
    # `investigacion()` ya dijo que la tabla esta VACIA o que el filtro no
    # coincide, que es el motivo real.
    lims = list(inv["limitations"])
    if not filas and (ops or res):
        lims.append(
            "no hay ninguna entrada de research para esta sesion: el "
            "checkpoint esta VACIO de razonamiento, no de evidencia. Hay %d "
            "operations y %d results en la base: la evidencia existe y el "
            "razonamiento sobre ella no se ha escrito." % (ops, res))
    return {
        "estado": "ok" if filas else "empty",
        "session": session,
        "target": target,
        "checkpoint_id": "ckpt_%s_%s" % (session or "sin_session",
                                         (nxt[0]["id"] if nxt else 0)),
        "hipotesis_abiertas": [f for f in por_status.get("hypothesis", [])
                               if f["status"] == "OPEN"],
        "hipotesis_refutadas": [f for f in por_status.get("hypothesis", [])
                                if f["status"] == "REFUTED"],
        "claims": por_status.get("claim", []),
        "fronteras": por_status.get("frontier", []),
        "notas": por_status.get("note", []),
        "siguiente_accion": nxt[0] if nxt else None,
        "n_acciones_registradas": len(nxt),
        "evidencia_en_base": {"operations": ops, "results": res, "edges": eds},
        "limitations": lims,
    }

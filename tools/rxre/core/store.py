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
import re
import sqlite3
import sys
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

-- =====================================================================
-- [v3] Append-only en results: triggers + columnas nuevas.
--
-- El diagrama: "EVIDENCE: append-only, delete prohibido por permiso en
-- punto de escritura". Lo mismo aplica a results: un result_id repetido
-- sobrescribe el contenido anterior sin dejar rastro, y eso es lo que
-- sostiene los resultados huerfanos y los COLISION: documentados.
--
-- `row_hash` y `supersedes_ref` se agregan via _asegurar_columnas_results,
-- no aqui: ALTER TABLE ADD COLUMN lanza si ya existe.
-- =====================================================================
CREATE TRIGGER IF NOT EXISTS trg_results_no_update
BEFORE UPDATE ON results
BEGIN
  SELECT RAISE(ABORT, 'RESULTS_APPEND_ONLY: UPDATE prohibido sobre results');
END;

CREATE TRIGGER IF NOT EXISTS trg_results_no_delete
BEFORE DELETE ON results
BEGIN
  SELECT RAISE(ABORT, 'RESULTS_APPEND_ONLY: DELETE prohibido sobre results');
END;

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
                                    -- + 'correlation' (SOLO maquina: _auto_correlate_findings)
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

-- RXRE-1640. Findings table for knowledge graph.
-- Stores technical claims with epistemic state and evidence provenance.
CREATE TABLE IF NOT EXISTS findings (
    finding_id   TEXT PRIMARY KEY,
    op_id        TEXT REFERENCES operations(operation_id),
    claim        TEXT NOT NULL,
    epistemic    TEXT,            -- PROVEN, PARTIAL, NOT_DETERMINED, PROVEN_ABSENT, DEFERRED, INVALIDATED
    evidence_ids TEXT,            -- JSON array de result_id que soportan este finding
    provenance   TEXT,            -- JSON con producer, tool_version, params, timestamp
    limitations  TEXT,            -- JSON array de limitaciones declaradas
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS finding_relations (
    relation_id  TEXT PRIMARY KEY,
    source_id    TEXT REFERENCES findings(finding_id),
    target_id    TEXT REFERENCES findings(finding_id),
    relation     TEXT NOT NULL,   -- CORRIGE, IMPLEMENTA, GENERALIZA, CONTINUA, COMPLETA, RETRACTA, MEDIDO_EN_MI_ASIC_POR
    evidence     TEXT,            -- JSON con la evidencia y método que sostiene la relación
    confidence   TEXT,            -- FUERTE, DEBIL, INFERIDA
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS ix_findings_epistemic ON findings(epistemic);
CREATE INDEX IF NOT EXISTS ix_finding_relations_source ON finding_relations(source_id);
CREATE INDEX IF NOT EXISTS ix_finding_relations_target ON finding_relations(target_id);

-- =====================================================================
-- [v3] CHECK DE 6 ESTADOS EN findings — como MECANISMO, no como comentario.
--
-- El diagrama dice 6 estados: PROVEN | PARTIAL | NOT_DETERMINED |
-- PROVEN_ABSENT | DEFERRED | INVALIDATED.
--
-- store.py:210 decia "epistemic TEXT -- PROVEN, ..., INVALIDATED" pero la
-- columna no tenia CHECK. Decir no es imponer. Y una columna que acepta
-- cualquier string no es un CHECK: es una sugerencia.
--
-- SQLite no permite ALTER TABLE ADD CHECK. La via es el trigger, que es lo
-- que el audit A-F midio como "0 triggers" y lo que la v3-5 exige.
--
-- El trigger es BEFORE INSERT y BEFORE UPDATE OF epistemic. No bloquea
-- filas OBSERVED ya existentes (no hay INSERT ni UPDATE que disparelo), pero
-- si bloquea cualquier intento futuro de escribir OBSERVED o GARBAGE.
--
-- OBSERVED es un estado que existe en produccion (9 findings) pero NO esta
-- en los 6 canonicos. Se documenta como gap, no se borra ni se migra aqui:
-- el trigger protege el futuro, no reescribe el pasado.
-- =====================================================================
CREATE TRIGGER IF NOT EXISTS trg_findings_epistemic_valid_insert
BEFORE INSERT ON findings
WHEN NEW.epistemic IS NOT NULL
  AND NEW.epistemic NOT IN ('PROVEN','PARTIAL','NOT_DETERMINED',
                            'PROVEN_ABSENT','DEFERRED','INVALIDATED')
BEGIN
  SELECT RAISE(ABORT, 'EPISTEMIC_INVALID: ' || NEW.epistemic);
END;

CREATE TRIGGER IF NOT EXISTS trg_findings_epistemic_valid_update
BEFORE UPDATE OF epistemic ON findings
WHEN NEW.epistemic IS NOT NULL
  AND NEW.epistemic NOT IN ('PROVEN','PARTIAL','NOT_DETERMINED',
                            'PROVEN_ABSENT','DEFERRED','INVALIDATED')
BEGIN
  SELECT RAISE(ABORT, 'EPISTEMIC_INVALID: ' || NEW.epistemic);
END;

-- =====================================================================
-- [v3] Trigger de validacion del CONTRATO para findings nuevos.
--
-- El diagrama define 10 campos obligatorios. Los 5 nuevos (object_hash,
-- scope, derivation_refs, contradiction_refs, falsification_test) son
-- nullable para no romper los 12 findings existentes. Pero un finding NUEVO
-- que no tenga los 10 campos no cumple el contrato.
--
-- Solo INSERT, no UPDATE: los findings viejos siguen operables (grandfathered).
-- Excepcion explicita con prefijo F-LEGACY-: nadie puede insertar un finding
-- incompleto sin marcarlo como legacy a proposito.
-- =====================================================================
CREATE TRIGGER IF NOT EXISTS trg_findings_contrato_nuevo
BEFORE INSERT ON findings
WHEN NEW.finding_id NOT LIKE 'F-LEGACY-%'
  AND (
    NEW.object_hash IS NULL OR
    NEW.scope IS NULL OR
    NEW.falsification_test IS NULL OR
    NEW.derivation_refs IS NULL OR
    NEW.contradiction_refs IS NULL
  )
BEGIN
  SELECT RAISE(ABORT, 'CONTRATO_INCOMPLETO: 10 campos obligatorios para findings nuevos');
END;

-- =========================================================================
-- [v3-2] INVALIDATED NO ES AUTOMATICO.
--
-- El diagrama: "contradiccion -> reevaluacion documentada -> puede resultar
-- en INVALIDATED o volver a PROVEN si se refuta la contradiccion".
--
-- Lo que hace falta para que eso sea mas que un string: un REGISTRO de quien
-- reevalua, por que, y con que resultado. Sin esta tabla, INVALIDATED seria un
-- valor mas de una columna, y escribirlio no dejaria rastro de nada — que es
-- exactamente el fallo que la v3-2 corrige.
--
-- Por eso la reevaluacion es una fila, no un UPDATE: queda en el historico.
-- =========================================================================
CREATE TABLE IF NOT EXISTS finding_reevaluations (
    reevaluation_id   TEXT PRIMARY KEY,
    finding_id        TEXT NOT NULL,
    contradiction     TEXT NOT NULL,     -- que se contradice
    decision          TEXT NOT NULL,     -- INVALIDATED | REVERTED | PARTIAL
    rationale         TEXT NOT NULL,     -- por que se decide eso
    reviewer          TEXT NOT NULL,     -- quien reevalua
    created_at        TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (finding_id) REFERENCES findings(finding_id)
);

CREATE INDEX IF NOT EXISTS ix_reeval_finding ON finding_reevaluations(finding_id);

-- La columna `reevaluation_id` de `findings` se agrega en
-- `_asegurar_columnas_reevaluacion()`, NO aqui: `ALTER TABLE ADD COLUMN` lanza
-- si la columna ya existe, y el DDL se ejecuta en cada `conectar()`. El
-- patron ya existe en `_asegurar_columnas_execution_events`.

-- [v3] Columna `version` para optimistic locking. Mismo patron.
-- Se agrega en `_asegurar_columnas_version()`, no aqui.

-- RXRE-AUTONOMY-001. Persistent mission state for autonomous execution.
-- These tables bind a mission objective to its acceptance criteria, tasks,
-- and evidence, so the system can track progress and resume after interruption
-- without relying on conversational context.

-- La tabla missions es la RAIZ: sin ella las FK de mission_criteria y
-- mission_tasks fallan. Se crea ANTES que las tablas hijas.
CREATE TABLE IF NOT EXISTS missions (
    mission_id     TEXT PRIMARY KEY,
    title          TEXT NOT NULL,
    description    TEXT,
    status         TEXT DEFAULT 'PENDING',  -- PENDING, IN_PROGRESS, COMPLETED, BLOCKED, FAILED
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now')),
    completed_at   TEXT,                    -- cuando se marcó COMPLETED
    last_checkpoint TEXT,                  -- último checkpoint serializado
    CHECK (status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'BLOCKED', 'FAILED'))
);

CREATE INDEX IF NOT EXISTS ix_missions_status ON missions(status);

-- BMS-EXT-001. Audit log inspired by RKA Core's audit_log table.
-- Each registrar, guardar_finding, and relacionar_findings writes an entry.
-- This allows forensic analysis of who did what and when — a capability
-- RXRE lacked before (BMS-007 gap analysis: "Audit log (who did what, when)"
-- was NOT_IMPLEMENTED, only operations.timestamp existed).
CREATE TABLE IF NOT EXISTS audit_log (
    audit_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    action        TEXT NOT NULL,          -- 'register', 'create_finding', 'create_relation', etc.
    entity_type   TEXT NOT NULL,          -- 'operation', 'finding', 'finding_relation'
    entity_id     TEXT NOT NULL,          -- la PK del entity afectado
    actor         TEXT,                   -- quien actua (capability, producer, "system")
    details       TEXT,                   -- JSON con contexto adicional (op_id, claim_snippet, etc.)
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS ix_audit_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_log(action);

CREATE TABLE IF NOT EXISTS dependency_states (
    -- Una dependency es un requisito MEDIDO de una validacion concreta, no una
    -- opinion general. Cada fila es una hipotesis de dependencias que se
    -- comprobo con una herramienta y cuyo resultado viaja con todo su
    -- contexto.
    --
    -- DEPENDENCY_NO_MISSING vs dependency_no_missing: la primera es el estado
    -- (ya comprobado), la segunda es el valor que un backend podria haber
    -- devuelto y que aqui normalizamos.
    dep_id           TEXT PRIMARY KEY,                -- dep_<sha> (identificador CITABLE)
    target           TEXT NOT NULL,                   -- la validacion o target para el que se midio
    name             TEXT NOT NULL,                   -- e.g. "SDL3", "libX11", "vulkan-headers>=1.2"
    state            TEXT NOT NULL,                   -- MISSING|SATISFIED|OPTIONAL|NOT_DETERMINED
    required         INTEGER DEFAULT 1,               -- 1: obligatorio, 0: opcional (requisito medido, no opinion)
    -- El diagnostico OBSERVADO que produjo el estado. No es un resumen: es la
    -- linea exacta de CMake/rpm/dnf que determino el estado.
    diagnostic       TEXT,                            -- CMake error / rpm error / dnf output
    source           TEXT,                            -- el archivo/linea/origen del diagnostico (cmake log)
    -- Contexto irrepetible: revision, herramientas y flags en que se midio.
    -- Una dependency sin contexto es basura reutilizable: la misma "libX11"
    -- puede estar MISSING en una maquina y SATISFIED en otra.
    context          TEXT,                            -- JSON con revision, compiler, cmake flags, env
    validated_by     TEXT,                            -- la operacion/result_id que lo comprobo
    recorded_at      TEXT NOT NULL,                   -- momento del registro (no del diagnostico)
    -- La observacion es un estado FROZEN de un momento concreto.
    -- Para volver a validar, el consumidor debe comprobar el contexto.
    CHECK (state IN ('MISSING', 'SATISFIED', 'OPTIONAL', 'NOT_DETERMINED')),
    CHECK (required IN (0, 1))
);

-- ARISTAS DEL DOMINIO dependency: la cadena VALIDATION -> DEPENDENCY ->
-- REMEDIATION -> RESULTADO. Son distintas de edges READS/WRITES/REFERENCES:
-- no describen el hardware, describen el PROCESO DE VALIDACION.
CREATE TABLE IF NOT EXISTS validation_remediations (
    rem_id           TEXT PRIMARY KEY,                -- rem_<sha>
    target           TEXT NOT NULL,                   -- la misma validacion
    dep_id           TEXT REFERENCES dependency_states(dep_id),  -- a la que se quiere remediar
    remediation      TEXT NOT NULL,                   -- e.g. "dnf install SDL3-devel libX11-devel"
    remediation_type TEXT,                            -- INSTALL|CONFIGURE|UPDATE|SKIP|DONT_APPLY
    attempted        INTEGER DEFAULT 0,               -- 0: propuesta, 1: intentada
    attempted_at     TEXT,                            -- cuando se ejecuto la remediation
    verified         INTEGER DEFAULT 0,               -- 0: no comprobada, 1: comprobada
    verification_result TEXT,                         -- RESOLVED|FAILED|PENDING
    verification_at  TEXT,                            -- cuando se comprobo
    -- Evidencia independiente de la VERIFICACION, no de la observacion original:
    -- result_id de un CMake que ahora pasa, o de dnf que devuelve exito.
    verification_evidence TEXT,                       -- res_*
    recorded_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mission_criteria (
    criterion_id   TEXT PRIMARY KEY,
    mission_id     TEXT REFERENCES missions(mission_id),
    description    TEXT NOT NULL,
    epistemic      TEXT DEFAULT 'NOT_DETERMINED',
    evidence_ids   TEXT,
    required       INTEGER DEFAULT 1,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS mission_tasks (
    task_id        TEXT PRIMARY KEY,
    mission_id     TEXT REFERENCES missions(mission_id),
    title          TEXT NOT NULL,
    description    TEXT,
    status         TEXT DEFAULT 'PENDING',
    priority       INTEGER DEFAULT 0,
    dependencies   TEXT,
    created_at     TEXT DEFAULT (datetime('now')),
    completed_at   TEXT
);

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

-- RXRE-AUTONOMY-002. Tabla de reflexiones: el lazo de retroalimentacion
-- que Reflexion/Recuris/MemSkill llaman "aprender de los resultados".
--
-- Inspirado en:
--   - Reflexion (noahshinn/reflexion): attempt -> feedback -> self-reflection -> retry
--   - Recuris: retroalimentacion sobre fracasos para corregir procedimientos
--   - MemSkill: memoria de que operaciones tuvieron exito o fracaso
--
-- Esta tabla NO duplica `research` (que guarda hypotheses/claims/notes/next_actions).
-- Aqui se guarda la LECCION CONCRETA de un intento: que se intento, que paso,
-- por que, y que debe cambiar. La diferencia epistemica:
--
--   research.hypothesis  = "creo que X" (abierta)
--   reflexiones.reflection = "X fallo porque Y, la siguiente vez Z" (cerrada, aprendida)
--
-- Schema:
--   reflexion_id  TEXT PK     — ID determinista (SHA256 de attempt_id + feedback)
--   hypothesis_id TEXT       — ref a research(id) si la reflexion bajo una hipotesis
--   attempt_id    TEXT       — ref a operations(operation_id) del intento
--   feedback      TEXT       — evidencia observada (lo que paso)
--   reflection    TEXT       — analisis causal (por que paso)
--   outcome       TEXT       — success | failure | timeout | error
--   strategy      TEXT       — sugerencia concreta para el proximo intento
--   refs_json     TEXT       — result_ids que sustentan el feedback
--   timestamp     TEXT NOT NULL
CREATE TABLE IF NOT EXISTS reflexiones (
    reflexion_id   TEXT PRIMARY KEY,
    hypothesis_id  TEXT,                     -- ref a research(id), nullable
    attempt_id     TEXT,                     -- ref a operations(operation_id)
    feedback       TEXT NOT NULL,            -- evidencia observada
    reflection     TEXT NOT NULL,            -- analisis causal
    outcome        TEXT NOT NULL,            -- success|failure|timeout|error
    strategy       TEXT,                     -- sugerencia para el proximo intento
    refs_json      TEXT DEFAULT '[]',        -- result_ids que sustentan el feedback
    timestamp      TEXT NOT NULL,
    -- WATER/MIND: una reflexion ESCRITA no es una leccion aprendida.
    -- MEDIDO 2026-10-14: este arbol llevaba meses con tres cosas FALSAS en
    -- prosa (flags de UMR que no existen, y un nombre de registro que nunca
    -- existio). No habia memoria de por que estaban mal, y por tanto no
    -- habia forma de saber que eranWrong. Este campo enlaza la reflexion
    -- con un CHECK EJECUTABLE: si alguien vuelve a escribir el error, el
    -- check falla en vez de que el error vuelva a pasar inadvertido.
    check_ejecutable TEXT DEFAULT '',        -- fichero:test que la vigila
    verificada_en    TEXT DEFAULT '' ,       -- ultima vez que el check corrio
    -- MEDIDO 2026-10-14 (RXRE-CORE-CAUSAL-002): sin estas dos columnas una
    -- leccion NO PUEDE influenciar ninguna decision. Las 11 lecciones que
    -- tenia RXRE estaban todas con `attempt_id` nulo, o sea huerfanas: se
    -- guardaban, se ejecutaba su check, y no las leia nadie para decidir
    -- nada. Memoria vigilada y memoria inerte son la misma cosa si nadie la
    -- consulta.
    --
    -- `target` y `capability` son el enlace. Se derivan de la operacion
    -- cuando existe, y se pueden declarar cuando la leccion sale de otra
    -- cosa (leer un bytecode, mirar un manual, comparar dos arboles).
    target     TEXT DEFAULT '',
    capability TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS ix_reflexiones_hypothesis ON reflexiones(hypothesis_id);
CREATE INDEX IF NOT EXISTS ix_reflexiones_attempt    ON reflexiones(attempt_id);
CREATE INDEX IF NOT EXISTS ix_reflexiones_outcome    ON reflexiones(outcome);

-- RXRE-CORE-CAUSAL-002. Event-log ejecutable: el registro DURABLE de la
-- cadena OpenCode -> terminal -> RXRE. MEDIDO: antes de esto, la cadena
-- solo se imprimia en una traza efimera (test_fase5_trace); nada sobre lo
-- que ejecuto hoy quedaba grabado para mañana. Ese es el cuello de
-- §6 (durable record) que queda sin cerrar.
--
-- Por que una tabla NUEVA y no reusar `operations`: `operations` guarda el
-- REQUEST y RESPONSE INTEGROS de cada adapter (lo que un producer emitió).
-- Un evento de ejecución es lo que la ORQUESTACION observó: qué se ejecutó,
-- cuándo, con qué salida del proceso, si se persistió, y cuántas lecciones
-- previas pesaban sobre la decisión. Esa es interpretación del orchestrator,
-- no evidencia del producer: §10 exige separarlas.
--
-- Se registra en op:run y op:plan. Nunca falla la ejecución por esto: el
-- evento se escribe en best-effort y cualquier error se reporta como
-- limitation, no como abort.
CREATE TABLE IF NOT EXISTS execution_events (
    evento_id      TEXT PRIMARY KEY,
    op             TEXT NOT NULL,          -- run | plan
    capability     TEXT,
    backend_id     TEXT,
    exit_status    INTEGER,                -- del proceso real, no del adapter
    operation_id   TEXT,                   -- ref a operations(operation_id)
    result_id      TEXT,                   -- ref a results(result_id)
    persistido     INTEGER,                -- 1/0, no bool
    n_lessons      INTEGER,                -- lecciones de fallo consultadas antes
    limitations    TEXT,                   -- JSON
    timestamp      TEXT NOT NULL,
    trace_id       TEXT,                   -- traza por invocacion, no caller agent
    lecciones_json  TEXT DEFAULT '[]'     -- ids surfaceados (AGUA)
);
CREATE INDEX IF NOT EXISTS ix_exec_op        ON execution_events(op);
CREATE INDEX IF NOT EXISTS ix_exec_cap       ON execution_events(capability);
CREATE INDEX IF NOT EXISTS ix_exec_op_id     ON execution_events(operation_id);
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
    # AETHER: SATURATED es un estado terminal para frontier entries.
    # Se asigna solo si evaluar_saturacion_frontier() confirma condiciones
    # observables (no por un label arbitrario). Ver §100 FRONTIER SATURATION.
    "SATURATED",
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

KIND_RESEARCH = ("hypothesis", "claim", "note", "next_action", "frontier", "performance")

#: `correlation` NO se suma a KIND_RESEARCH a proposito: KIND_RESEARCH es la
#: lista de lo que un consumidor puede REGISTRAR via `registrar_investigacion`
#: (texto suyo, refs citables res_/op_/edge:). Las filas 'correlation' las
#: escribe SOLO `_auto_correlate_findings` —una coincidencia numerica medida,
#: no una afirmacion del usuario— y sus refs son finding_id, que
#: `refs_invalidos` no admite como citables de usuario; abrirlas al registro
#: general obligaria a relajar esa validacion. Extension DOCUMENTADA de la
#: maquina, no un kind suelto.
KIND_CORRELATION = "correlation"

#: `correlation` NO se suma a KIND_RESEARCH a proposito: KIND_RESEARCH es la
#: lista de lo que un consumidor puede REGISTRAR via `registrar_investigacion`
#: (texto suyo, refs citables res_/op_/edge:). Las filas 'correlation' las
#: escribe SOLO `_auto_correlate_findings` —una coincidencia numerica medida,
#: no una afirmacion del usuario— y sus refs son finding_id, que
#: `refs_invalidos` no admite como citables de usuario; abrirlas al registro
#: general obligaria a relajar esa validacion. Es una extension DOCUMENTADA
#: de la maquina, no un kind suelto: cualquier otro writer usa solo la lista
#: cerrada de arriba.
KIND_CORRELATION = "correlation"

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
    # MEDIDO 2026-10-15: el `commit` (fsync de FULL) era el 68% del tiempo de
    # `op:plan`. Medido EN EL CAMINO REAL (1 escritura por proceso):
    #   FULL rollback  : commit 0.081s + close 0.018s
    #   WAL + NORMAL   : commit 0.071s + close 0.109s  (PEOR: close hace
    #                    checkpoint del -wal; "una escritura por proceso" lo paga)
    #   NORMAL rollback: la elegida
    # `synchronous=NORMAL` en rollback sigue durable contra fallo de proceso;
    # la ventana de riesgo es corte de energia en el instante exacto.
    try:
        c.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.Error:
        pass
    c.executescript(DDL)
    cur = c.execute("SELECT valor FROM meta WHERE clave='schema_version'")
    fila = cur.fetchone()
    if fila is None:
        c.execute("INSERT INTO meta(clave,valor) VALUES('schema_version',?)",
                  (str(SCHEMA_VERSION),))
        c.commit()
    _asegurar_columnas_execution_events(c)
    _asegurar_columnas_reevaluacion(c)
    _asegurar_columnas_version(c)
    _asegurar_columnas_results(c)
    _asegurar_columnas_findings_contrato(c)
    return c


def _sha(txt: str) -> str:
    return hashlib.sha256(txt.encode("utf-8")).hexdigest()[:16]


def _asegurar_columnas_version(c: sqlite3.Connection) -> None:
    """[v3-4] Agrega `findings.version` para optimistic locking.

    Mismo patron que `_asegurar_columnas_execution_events`: `CREATE TABLE IF
    NOT EXISTS` no altera tablas viejas, y `ALTER TABLE ADD COLUMN` lanza si
    la columna ya existe.

    `version` empieza en 0 y se incrementa en cada `UPDATE` optimista. Un
    escritor que leyo version=N y encuentra que otro ya movio a N+1 recibe
    rowcount=0 y reintenta con la version nueva. Sin lock, sin espera.
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(findings)")}
    except sqlite3.Error:
        return
    if "version" not in cols:
        try:
            c.execute("ALTER TABLE findings ADD COLUMN version INTEGER NOT NULL DEFAULT 0")
        except sqlite3.OperationalError:
            pass


def _asegurar_columnas_reevaluacion(c: sqlite3.Connection) -> None:
    """[v3-2] Agrega `findings.reevaluation_id` en bases existentes.

    Mismo motivo y mismo patron que `_asegurar_columnas_execution_events`:
    `CREATE TABLE IF NOT EXISTS` no altera tablas viejas, y `ALTER TABLE ADD
    COLUMN` lanza si la columna ya existe.

    La columna guarda QUE reevaluacion produjo el estado actual. NULL no es
    "no hay dato": es informacion, y distingue dos cosas que de otro modo
    quedan indistinguibles al leer `findings.epistemic`:

        INVALIDATED con reevaluation_id    -> alguien lo reviso y decidio
        INVALIDATED con reevaluation_id NULL -> se escribio a mano
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(findings)")}
    except sqlite3.Error:
        return
    if "reevaluation_id" not in cols:
        try:
            c.execute("ALTER TABLE findings ADD COLUMN reevaluation_id TEXT")
        except sqlite3.OperationalError:
            pass


def _asegurar_columnas_findings_contrato(c: sqlite3.Connection) -> None:
    """[v3] Agrega los 5 campos del contrato TIERRA-1 a `findings`.

    Mismo patron que `_asegurar_columnas_execution_events`: `CREATE TABLE IF
    NOT EXISTS` no altera tablas viejas, y `ALTER TABLE ADD COLUMN` lanza si
    la columna ya existe.

    Los 5 campos son NULLABLE a proposito: los 12 findings existentes no
    tienen estos datos. Hacerlos NOT NULL romperia la migracion. Se vuelven
    NOT NULL cuando haya backfill (fuera de este paso).

    Campos:
      object_hash         TEXT   hash del objeto que el finding describe
      scope               TEXT   binary/source/runtime/formal
      derivation_refs     TEXT   JSON array, default '[]'
      contradiction_refs  TEXT   JSON array, default '[]'
      falsification_test  TEXT   prueba que tumbaria el finding
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(findings)")}
    except sqlite3.Error:
        return
    migraciones = [
        ("object_hash", "TEXT"),
        ("scope", "TEXT"),
        ("derivation_refs", "TEXT DEFAULT '[]'"),
        ("contradiction_refs", "TEXT DEFAULT '[]'"),
        ("falsification_test", "TEXT"),
    ]
    for col, tipo in migraciones:
        if col not in cols:
            try:
                c.execute("ALTER TABLE findings ADD COLUMN %s %s" % (col, tipo))
            except sqlite3.OperationalError:
                pass


def _asegurar_columnas_results(c: sqlite3.Connection) -> None:
    """[v3] Agrega `row_hash` y `supersedes_ref` a `results` en bases existentes.

    Mismo patron que `_asegurar_columnas_execution_events`: `CREATE TABLE IF
    NOT EXISTS` no altera tablas viejas, y `ALTER TABLE ADD COLUMN` lanza si
    la columna ya existe.

    `row_hash` es el SHA-256 de los campos del result (sin row_hash). Se
    verifica al leer, igual que en `evidence`. `supersedes_ref` apunta al
    result_id que este result corrige; la fila anterior NO se borra.
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(results)")}
    except sqlite3.Error:
        return
    if "row_hash" not in cols:
        try:
            c.execute("ALTER TABLE results ADD COLUMN row_hash TEXT")
        except sqlite3.OperationalError:
            pass
    if "supersedes_ref" not in cols:
        try:
            c.execute("ALTER TABLE results ADD COLUMN supersedes_ref TEXT")
        except sqlite3.OperationalError:
            pass


def _asegurar_columnas_execution_events(c: sqlite3.Connection) -> None:
    """Agrega columnas nuevas a `execution_events` en bases existentes.

    MEDIDO 2026-10-14: `trace_id` (RXRE-TRACE-ID-001) y `lecciones_json`
    (AGUA) ya viven en la BD real pero el codigo no lo declaraba; ahora se
    suma. CREATE TABLE IF NOT EXISTS no altera tablas viejas.
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(execution_events)")}
    except sqlite3.Error:
        return
    for nombre, tipo in (("trace_id", "TEXT"),
                         ("lecciones_json", "TEXT DEFAULT '[]'")):
        if nombre not in cols:
            try:
                c.execute("ALTER TABLE execution_events ADD COLUMN %s %s"
                          % (nombre, tipo))
            except sqlite3.OperationalError:
                pass


def _auto_correlate_findings(c: sqlite3.Connection, kind: str, text: str,
                             session: str = "") -> List[Dict[str, Any]]:
    """ETER: detecta COINCIDENCIA NUMERICA entre investigacion nueva y hallazgos.

    ALCANCE (lo que esta funcion NO dice): no es causalidad ni correlacion
    estadistica. Compara los numeros >= 10 del texto nuevo contra los de la
    `claim` de cada finding. Con 2+ numeros comunes, registra UNA fila en
    `research` (kind='correlation') que cita TODOS los findings implicados en
    `refs_json`, y devuelve la lista de coincidencias para que el consumidor
    la reporte. Un humano (o una IA) decide despues si hay relacion real.

    Por que 2+ numeros y no 1: dos textos que comparten un unico numero
    (p.ej. 481 = MiB de VRAM) coinciden en un dato, no en una historia;
    exigir 2+ baja el azar y hace que la pista valga una revision.

    Por que >= 10: '0' y '1' aparecen en casi cualquier texto tecnico y
    producirian coincidencias espurias. MEDIDO 2026-10-15 (negativo con
    ' 0 1 0 1 ' -> 0 filas).

    MEDIDO 2026-10-15 (GLOB): `LIKE "finding_%"` sobre finding_id (PK,
    colacion BINARY) es case-insensitive y NO puede usar el indice -> SCAN
    findings. `GLOB "finding_*"` es case-sensitive y usa el indice de la PK.
    Los ids se generan siempre "finding_" + hex o numero en minusculas.

    Devuelve [] si: kind no es frontier/observation, hay <2 numeros nuevos,
    o ningun finding alcanza 2+ numeros comunes.
    """
    if kind not in ("frontier", "observation"):
        return []

    def _numeros_significativos(t: str) -> set:
        return {n for n in re.findall(r"\d+", t or "") if int(n) >= 10}

    numbers = _numeros_significativos(text)
    if len(numbers) < 2:
        return []

    cursor = c.execute("""
        SELECT finding_id, claim FROM findings
        WHERE finding_id GLOB "finding_*"
        ORDER BY created_at DESC
        LIMIT 50
    """)
    correlaciones: List[Dict[str, Any]] = []
    for fid, claim in cursor:
        existing_numbers = _numeros_significativos(claim)
        if len(existing_numbers) < 2:
            continue
        common = numbers & existing_numbers
        if len(common) >= 2:
            correlaciones.append({
                "finding_id": fid,
                "numeros_comunes": sorted(common),
                "claim": (claim or "")[:200],
            })
            if len(correlaciones) >= 5:
                break
    if not correlaciones:
        return []

    # UNA fila cita TODOS los findings implicados. MEDIDO 2026-10-15: dos
    # rutas de escritura producian 2 filas por evento; ahora la ruta es
    # unica (store) y el handler scan solo REPORTA lo que esta funcion
    # devuelve.
    c.execute("""
        INSERT INTO research(kind, status, text, refs_json, session, target, timestamp)
        VALUES (?, "OPEN", ?, ?, ?, "", ?)
    """, (KIND_CORRELATION,
          "Coincidencia numerica (NO causal): %d hallazgo(s) comparten >=2 "
          "numeros con la entrada: %s"
          % (len(correlaciones),
             ", ".join(x["finding_id"][:20] for x in correlaciones)),
          json.dumps([x["finding_id"] for x in correlaciones]),
          session or "auto_correlation",
          time.strftime("%Y-%m-%dT%H:%M:%S%z")))
    c.commit()
    return correlaciones


def trazar_aplicacion_lecciones(c: sqlite3.Connection, capability: str) -> Dict[str, Any]:
    """AGUA (1621): lee como se SURFACEAN las lecciones de una capability.

    Reutiliza `execution_events` (event-log durable) via `lecciones_json`;
    NO crea tabla nueva. Distingue, y esta es la parte que importa:

      surfaceada        el id aparece en algun evento plan/run
      candidata_aplicada hay un run POSTERIOR con exit_status=0
      sin_datos         el id no aparece

    `candidata_aplicada` es INDICIO, no prueba: el run pudo triunfar por
    otra razon. La causalidad leccion->exito NO es medible con estos datos,
    y el reporte no debe afirmarla.
    """
    _asegurar_columnas_execution_events(c)
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(execution_events)")}
    except sqlite3.Error:
        cols = set()
    if "lecciones_json" not in cols:
        return {"estado": "blocked", "capability": capability,
                "motivo": "execution_events sin lecciones_json",
                "lecciones": []}

    filas = [dict(r) for r in c.execute(
        "SELECT op, capability, exit_status, lecciones_json, timestamp "
        "FROM execution_events WHERE capability=? ORDER BY timestamp",
        (capability,))]

    por_leccion: Dict[str, Dict[str, Any]] = {}
    orden: List[str] = []
    for f in filas:
        ids: List[str] = []
        try:
            bruto = f.get("lecciones_json")
            if bruto:
                val = json.loads(bruto)
                if isinstance(val, list):
                    ids = [str(x) for x in val if str(x)]
        except (ValueError, TypeError):
            ids = []
        for lid in ids:
            if lid not in por_leccion:
                por_leccion[lid] = {"reflexion_id": lid,
                                    "veces_surfaceada": 0,
                                    "ultimo_surfaceado": None,
                                    "candidate_aplicada": False}
                orden.append(lid)
            info = por_leccion[lid]
            info["veces_surfaceada"] += 1
            ts = f.get("timestamp")
            if ts and (info["ultimo_surfaceado"] is None
                       or ts >= info["ultimo_surfaceado"]):
                info["ultimo_surfaceado"] = ts
        # candidata: run OK posterior a la ultima vez que se surfaceo
        if f.get("op") == "run" and f.get("exit_status") == 0:
            ts = f.get("timestamp") or ""
            for lid, info in por_leccion.items():
                if info["ultimo_surfaceado"] and ts >= info["ultimo_surfaceado"]:
                    info["candidate_aplicada"] = True

    salida = [por_leccion[l] for l in orden]
    return {"estado": "ok" if salida else "empty",
            "capability": capability,
            "lecciones": salida,
            "limitations": ([] if salida else
                            ["ninguna leccion surfaceada para '%s': eso NO es "
                             "que no se pueda fallar, es que no hay eventos "
                             "que la citen" % capability])}


def eventos_por_trace(c: sqlite3.Connection, trace_id: Optional[str]) -> Dict[str, Any]:
    """RXRE-TRACE-ID-001: reconstruye la cadena de eventos de un `trace_id`.

    El trace_id lo emite el agente, uno por invocacion. Reusarlo = reintento
    del mismo intento; uno nuevo = intento nuevo. Leer por trace es lo que
    convierte la columna en evidencia: sin esta funcion, `trace_id` estaba
    ESCRITA y nadie la LEIA (medido: el test reventaba con AttributeError).

    Read-only: no escribe ni duplica. trace_id vacio/None -> `empty`: no es
    un error, es que no hay cadena que reconstruir.
    """
    _asegurar_columnas_execution_events(c)
    if not trace_id:
        return {"status": "empty", "eventos": [], "trace_id": trace_id,
                "limitations": ["trace_id vacio: no hay cadena que reconstruir"]}
    filas = [dict(r) for r in c.execute(
        "SELECT evento_id, op, capability, backend_id, exit_status, "
        "operation_id, result_id, persistido, n_lessons, limitations, "
        "timestamp, trace_id, lecciones_json FROM execution_events "
        "WHERE trace_id=? ORDER BY timestamp", (trace_id,)).fetchall()]
    if not filas:
        return {"status": "empty", "eventos": [], "trace_id": trace_id,
                "limitations": ["ningun evento con trace_id=%r" % trace_id]}
    for f in filas:
        try:
            f["limitations"] = json.loads(f.get("limitations") or "[]")
        except (ValueError, TypeError):
            f["limitations"] = []
        try:
            f["lecciones"] = json.loads(f.get("lecciones_json") or "[]")
        except (ValueError, TypeError):
            f["lecciones"] = []
        f.pop("lecciones_json", None)
    return {"status": "ok", "eventos": filas, "trace_id": trace_id,
            "n": len(filas),
            "ops": sorted({e["op"] for e in filas}),
            "capabilities": sorted({e["capability"] for e in filas
                                    if e.get("capability")}),
            "limitations": []}


def registrar_evento(c: sqlite3.Connection, op: str, capability: str,
                     env: Dict[str, Any], lecciones: List[Any]) -> str:
    """Registra un evento de ejecucion orquestada (op:run / op:plan).

    MEDIDO 2026-10-14: el event-log DURABLE que cierra el cuello §6
    (durable record of the chain). op:run consulta lecciones antes de
    ejecutar y ahora tambien LO QUE EJECUTO y CON QUE RESULTADO, con
    timestamp real. Best-effort: si falla, el llamador catcha y lo reporta
    como limitation, no como abort.
    """
    op_id = env.get("operation_id") or ""
    rs = env.get("results") or []
    rid = (rs[0].get("result_id", "") if rs and isinstance(rs[0], dict) else "")
    be = env.get("backend")
    beid = be.get("backend_id") if isinstance(be, dict) else be
    # MEDIDO 2026-10-15 (RXRE-TRACE-ID-001): el hash solo con
    # (ejecucion, op, capability, op_id) hacia que 4 llamadas identicas
    # generaran 3 evento_id. La razon: `operation_id` sale como
    # "COLISION:res_..." cuando el result_id es deterministico (por diseño),
    # asi que elOperation_id NO distingue reintentos. El trace_id SI es la
    # unidad que el agente varia por invocacion: va en el hash.
    # Sin trace_id (llamadores viejos) el hash queda como antes.
    _tid = env.get("trace_id") or ""
    evento_id = "ev_" + _sha(json.dumps(env.get("ejecucion") or {},
                                       sort_keys=True, default=str)
                             + op + capability + str(op_id) + _tid)
    c.execute(
        "INSERT OR REPLACE INTO execution_events(evento_id, op, capability, "
        "backend_id, exit_status, operation_id, result_id, persistido, "
        "n_lessons, limitations, timestamp, trace_id, lecciones_json) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (evento_id, op, capability, beid,
         (env.get("ejecucion") or {}).get("exit_status"),
         op_id, rid, int(bool(env.get("persistido"))),
         len(lecciones or []),
         json.dumps(env.get("limitations") or [], default=str),
         time.strftime("%Y-%m-%dT%H:%M:%S%z"),
         env.get("trace_id"),
         json.dumps([l.get("reflexion_id") if isinstance(l, dict) else str(l)
                     for l in (lecciones or [])], default=str)))
    c.commit()
    return evento_id


def registrar(c: sqlite3.Connection, request: Dict[str, Any], env: Dict[str, Any],
              duracion: float = 0.0) -> str:
    """Guarda una operacion completa. Devuelve su `operation_id`."""
    op_json = json.dumps(request, sort_keys=True, default=str)
    # RXRE-AUTO-003: S.registrar persiste una operacion; si llegamos aqui,
    # persistido=True es intrinsecamente verdadero. Setearlo aqui garantiza
    # que response_json tenga el flag para el gate de AGUA, sin requerir
    # que cada adapter lo incluya en su dict de respuesta.
    env.setdefault("persistido", True)
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
        # [v3-5] Append-only: si el result_id ya existe, se devuelve sin
        # sobrescribir. La colision se registra en el audit_log para que quede
        # traza del intento, pero la fila anterior no se toca.
        existing = c.execute(
            "SELECT result_id FROM results WHERE result_id=?",
            (r["result_id"],)).fetchone()
        if existing:
            registrar_audit_log(c, "collision", "result", r["result_id"],
                                actor=request.get("capability", "unknown"),
                                details={"nuevo_op_id": op_id,
                                         "motivo": "result_id ya existia; "
                                                   "no se sobrescribe"})
            continue
        # [v3] row_hash: SHA-256 de los campos del result (sin row_hash ni
        # supersedes_ref). Se calcula aqui, al escribir, y se verifica al
        # leer en recuperar_evidencia_resultados.
        campos_result = {
            "result_id": r["result_id"],
            "operation_id": op_id,
            "type": r.get("type", ""),
            "value": str(r.get("value", ""))[:4000],
            "source": r.get("source", ""),
            "file": loc.get("file") or loc.get("loc") or "",
            "line": loc.get("line"),
            "scope": r.get("scope", ""),
            "tool": r.get("tool", ""),
            "tool_version": r.get("tool_version", ""),
            "status": r.get("status", ""),
            "raw_json": json.dumps(r, sort_keys=True, default=str),
            "timestamp": r.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S%z")),
        }
        row_hash = hashlib.sha256(
            json.dumps(campos_result, sort_keys=True, default=str).encode()
        ).hexdigest()
        c.execute(
            "INSERT INTO results(result_id,operation_id,type,value,"
            "source,file,line,scope,tool,tool_version,status,raw_json,timestamp,"
            "row_hash) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["result_id"], op_id, r.get("type", ""),
             str(r.get("value", ""))[:4000], r.get("source", ""),
             loc.get("file") or loc.get("loc") or "", loc.get("line"),
             r.get("scope", ""), r.get("tool", ""), r.get("tool_version", ""),
             r.get("status", ""), json.dumps(r, sort_keys=True, default=str),
             r.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S%z")),
             row_hash))
    c.commit()
    # BMS-EXT-001: audit log entry for operation registration
    # Usar request["capability"] (no env["capability"], que se setea DESPUES)
    registrar_audit_log(c, "register", "operation", op_id,
                        actor=request.get("capability", "unknown"),
                        details={"n_results": len(env.get("results") or []),
                                 "status": env.get("status", "")})
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
    # F1/F4-C2: `n_results` es el CONTADOR que se escribio al insertar
    # (`len(env["results"])`, store.py:862) y que NUNCA se recalcula. Antes de
    # esta linea, un contador que no cuadraba con las filas se callaba: la
    # respuesta salia `status:"ok"` con `limitations: []`, que se lee como
    # "no hay nada que reportar". Los dos numeros SIESTAN en el payload, pero
    # el que solo mira `status` no ve la contradiccion.
    #
    # Se DECLARA y NO SE DIAGNOSTICA. La causa puede ser un borrado, un
    # `INSERT OR REPLACE` de otro `result_id`, o un resultado sin `result_id`
    # que el propio `registrar` no indexa (store.py:867). Esta funcion no tiene
    # como distinguirlo, y afirmar una seria inventar historia.
    #
    #     una discrepancia es un HECHO; su causa es una HIPOTESIS
    #
    # No se afirma `RESULT_LOST`: la ausencia de filas NO prueba perdida, y el
    # contrato no tiene forma hoy de afirmarla.
    _limitaciones: List[str] = []
    _declarado = op["n_results"]
    _real = len(filas)
    if _declarado is not None and _declarado != _real:
        _limitaciones.append(
            "discrepancia de inventario: la operacion declara n_results=%s y "
            "hay %d fila(s) en `results`. NO se puede determinar la causa desde "
            "aqui: puede ser un resultado no indexado por falta de "
            "`result_id`, un `result_id` reescrito, o una fila eliminada. La "
            "ausencia de filas NO prueba que se perdiera nada."
            % (_declarado, _real))
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
            "limitations": _limitaciones}


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


def recuperar_evidencia_resultados(c: sqlite3.Connection,
                                   result_ids: List[str]) -> Dict[str, Any]:
    """Recupera evidencia para un conjunto de result_id.

    Devuelve un dict: result_id -> {result: dict, operation: dict, op_id: str}.
    Los result_id que no existen se omiten (el caller decide si eso es un error).

    Los dicts de result y operation incluyen alias de campo para el contrato
    del adapter: result_value (alias de value), result_type (alias de type),
    op_id (alias de operation_id), y raw (response_json parseado).
    """
    if not result_ids:
        return {}
    placeholders = ", ".join("?" for _ in result_ids)
    rows = c.execute(
        "SELECT * FROM results WHERE result_id IN (%s)" % placeholders,
        tuple(result_ids)
    ).fetchall()
    evidencia: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        r = dict(row)
        r["result_value"] = r.get("value")
        r["result_type"] = r.get("type")
        # [v3] Verificar row_hash al leer. Si el hash no coincide, la fila fue
        # alterada por una via que el trigger no cubre. Se lanza IntegrityError
        # en vez de devolver una bandera: un registro alterado no es "un poco
        # raro", no es fiable, y el llamador no deberia poder seguir.
        row_hash = r.get("row_hash")
        if row_hash:
            campos = {
                "result_id": r.get("result_id"),
                "operation_id": r.get("operation_id"),
                "type": r.get("type"),
                "value": r.get("value"),
                "source": r.get("source"),
                "file": r.get("file"),
                "line": r.get("line"),
                "scope": r.get("scope"),
                "tool": r.get("tool"),
                "tool_version": r.get("tool_version"),
                "status": r.get("status"),
                "raw_json": r.get("raw_json"),
                "timestamp": r.get("timestamp"),
            }
            recalculado = hashlib.sha256(
                json.dumps(campos, sort_keys=True, default=str).encode()
            ).hexdigest()
            if recalculado != row_hash:
                raise IntegrityError(
                    "row_hash de %s no coincide: almacenado=%s "
                    "recalculado=%s. La fila fue alterada por una via que "
                    "el trigger no cubre." % (
                        r.get("result_id"), row_hash[:16],
                        recalculado[:16]))
        op = c.execute(
            "SELECT * FROM operations WHERE operation_id=?",
            (r.get("operation_id"),)
        ).fetchone()
        op_dict = dict(op) if op else None
        op_id = op_dict.get("operation_id") if op_dict else None
        backend = {}
        raw = {}
        if op_dict:
            op_dict["op_id"] = op_dict.get("operation_id")
            try:
                response = json.loads(op_dict.get("response_json") or "{}")
                backend = response.get("cadena_backend", {}) or {}
                raw = response
            except (ValueError, TypeError):
                backend = {}
        evidencia[r["result_id"]] = {
            "result": r,
            "operation": op_dict or {},
            "op_id": op_id,
            "backend": backend,
            "backend_status": (op_dict or {}).get("status") if op_dict else None,
            "raw": raw,
        }
    return evidencia


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
    # AUTO-CORRELACION DE HALLAZGOS (ETER): SOLO despues de que la entrada
    # quedo grabada. Correlacionar ANTES de validar registraria lazos de una
    # investigacion que nunca fue aceptada. Best-effort: un fallo de la
    # correlacion (esquema, regex) no impide leer la entrada recien grabada,
    # pero NO se silencia: viaja como error explicito en la respuesta.
    # MEDIDO 2026-10-15: un fallo silenciado aqui hizo que `op:scan`
    # devolviera status=ok con 0 correlaciones durante dias. Invisible.
    correlaciones, error_corr = [], ""
    try:
        correlaciones = _auto_correlate_findings(c, kind, text, session)
    except Exception as e:  # aislar auxiliar del contrato de grabacion
        error_corr = "auto-correlacion fallo: %s" % e
    salida = {"estado": "ok", "id": cur.lastrowid, "kind": kind,
              "status": status, "gap_kind": gap_kind or None, "refs": refs,
              "session": session, "target": target, "timestamp": ts}
    if correlaciones:
        # Campo ADITIVO: los consumidores que ignoran `correlaciones` siguen
        # leyendo estado/id exactamente como antes.
        salida["correlaciones"] = correlaciones
    if error_corr:
        salida["auto_correlacion_error"] = error_corr
    return salida


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
        "limitations": inv["limitations"] or [
            "no hay ninguna entrada de research para esta sesion: el "
            "checkpoint esta VACIO de razonamiento, no de evidencia. Hay %d "
            "operations y %d results en la base: la evidencia existe y el "
            "razonamiento sobre ella no se ha escrito." % (ops, res)],
    }


def registrar_dependency(c: sqlite3.Connection,
                        target: str,
                        name: str,
                        state: str,
                        required: bool = True,
                        diagnostic: Optional[str] = None,
                        source: Optional[str] = None,
                        context: Optional[Dict[str, Any]] = None,
                        validated_by: Optional[str] = None) -> Dict[str, Any]:
    """Registra un estado de dependency observado para una validacion concreta.

    Cada fila es una medicion FROZEN de un momento concreto. El mismo nombre
    de dependency en un contexto distinto NO significa lo mismo.

    Args:
        target: la validacion o target (ej. "S_ADD_U32_regtest" o el target PCI).
        name: nombre del dependency (ej. "SDL3", "libX11", "libwayland-dev").
        state: 'MISSING', 'SATISFIED', 'OPTIONAL', 'NOT_DETERMINED'.
        required: 1=obligatorio para este target, 0=opcional.
        diagnostic: la linea exacta de error observado (CMake error, dnf output, etc).
        source: archivo/origen del diagnostico (ej. ruta del CMakeCache.txt).
        context: dict con revision, compiler, cmake flags, entorno. Es OBLIGATORIO
                 para que la dependency pueda ser reutilizada.
        validated_by: operation_id o result_id que comprobo este estado.

    Returns:
        Dict con estado y dep_id. El estado es 'ok' o 'error' si falta el contexto.
    """
    if state not in ("MISSING", "SATISFIED", "OPTIONAL", "NOT_DETERMINED"):
        return {"estado": "error", "id": None,
                "motivo": "state debe ser uno de: MISSING, SATISFIED, OPTIONAL, NOT_DETERMINED"}

    if not (name or "").strip():
        return {"estado": "error", "id": None,
                "motivo": "name vacio: una dependency sin nombre no transporta nada"}

    # El contexto es CRUCIAL: sin contexto la dependency no es reutilizable.
    # Sin embargo, permitimos que sea JSON vacio {} para casos limite, pero avisamos.
    if context is None:
        context = {}
    context_json = json.dumps(context, sort_keys=True, default=str) if context else "{}"

    dep_id = "dep_" + _sha(target + name + state + str(time.time()))

    # Guardar la dependency
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    cur = c.execute(
        "INSERT INTO dependency_states(dep_id, target, name, state, required, "
        "diagnostic, source, context, validated_by, recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (dep_id, target, name, state, 1 if required else 0,
         diagnostic, source, context_json, validated_by, ts))
    c.commit()

    # Verificar si ya hay una remediation asociada y marcarla como propuesta si es necesario
    # (esto es opcional y se deja al llamado)

    return {"estado": "ok", "id": dep_id, "target": target, "name": name,
            "state": state, "required": required, "diagnostic": diagnostic,
            "source": source, "context": context, "dep_id": dep_id,
            "timestamp": ts}


def registrar_remediation(c: sqlite3.Connection,
                         dep_id: str,
                         remediation: str,
                         remediation_type: str = "INSTALL",
                         target: Optional[str] = None) -> Dict[str, Any]:
    """Registra una remediation propuesta o intentada para un dependency.

    Args:
        dep_id: el dep_id de la dependency a remediar.
        remediation: la accion a tomar (ej. "dnf install SDL3-devel libX11-devel").
        remediation_type: INSTALL|CONFIGURE|UPDATE|SKIP|DONT_APPLY.
        target: la validacion objetivo (si es distinto del que vino en dep_id).

    Returns:
        Dict con rem_id y estado.
    """
    if target is None:
        target = c.execute(
            "SELECT target FROM dependency_states WHERE dep_id=?", (dep_id,)
        ).fetchone()[0]

    rem_id = "rem_" + _sha(dep_id + remediation + str(time.time()))

    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    cur = c.execute(
        "INSERT INTO validation_remediations(rem_id, target, dep_id, remediation, "
        "remediation_type, attempted, recorded_at) VALUES(?,?,?,?,?,0,?)",
        (rem_id, target, dep_id, remediation, remediation_type, ts))
    c.commit()

    return {"estado": "ok", "id": rem_id, "dep_id": dep_id,
            "remediation": remediation, "remediation_type": remediation_type,
            "attempted": False, "timestamp": ts}


def marcar_remediation_completada(c: sqlite3.Connection,
                                 rem_id: str,
                                 verification_result: str,
                                 verification_evidence: Optional[str] = None) -> Dict[str, Any]:
    """Marca una remediation como intentada y verificada.

    Args:
        rem_id: el rem_id de la remediation.
        verification_result: RESOLVED, FAILED, PENDING.
        verification_evidence: result_id de la verificacion (opcional).

    Returns:
        Dict con estado actualizado.
    """
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")

    updates = ["verified = 1", "verification_result = ?", "verification_at = datetime('now')"]
    params = [verification_result]

    if verification_evidence is not None:
        updates.append("verification_evidence = ?")
        params.append(verification_evidence)

    c.execute(
        f"UPDATE validation_remediations SET {', '.join(updates)} WHERE rem_id = ?",
        params + [rem_id])
    c.commit()

    # Opcional: tambien actualizar el estado de la dependency si la remediacion lo resuelve
    # Esto se deja al criterio del consumidor, pero podemos hacer la conexion aqui.

    row = c.execute("SELECT * FROM validation_remediations WHERE rem_id=?", (rem_id,)).fetchone()
    if row is None:
        return {"estado": "error", "motivo": "rem_id no existe"}

    # Actualizar el dependency_state si fue verificado como resuelto
    if verification_result == "RESOLVED" and verification_evidence is not None:
        c.execute(
            "UPDATE dependency_states SET state = 'SATISFIED', validated_by = ? "
            "WHERE dep_id = ?",
            (verification_evidence, row["dep_id"]))
        c.commit()

    return {"estado": "ok", "rem_id": rem_id,
            "verified": True, "verification_result": verification_result}


def query_validation_chain(c: sqlite3.Connection,
                          target: Optional[str] = None,
                          dep_name: Optional[str] = None,
                          state: Optional[str] = None) -> Dict[str, Any]:
    """Recupera la cadena de validacion: dependency -> remediacion -> resultado.

    Esta es la consulta principal que permite a una IA responder preguntas como:
    - '¿Por que no puedo ejecutar el test S_ADD_U32?'
    - '¿Que dependency me falta y como lo remedio?'
    - 'Si ya intente remediar, que resultado tuve?'

    La cadena devuelta es: dependency -> remediation -> verification_result.

    Args:
        target: filtrar por target de la validacion.
        dep_name: filtrar por nombre de dependency.
        state: filtrar por estado (MISSING, SATISFIED, OPTIONAL, NOT_DETERMINED).

    Returns:
        Dict con la cadena de validacion recuperada.
    """
    where, args = [], []
    if target is not None:
        where.append("ds.target = ?")
        args.append(target)
    if dep_name is not None:
        where.append("name = ?")
        args.append(dep_name)
    if state is not None:
        where.append("ds.state = ?")
        args.append(state)

    q_where = " WHERE " + " AND ".join(where) if where else ""

    # Traer dependencies con su remediation y verificacion
    sql = f"""
    SELECT ds.dep_id, ds.name, ds.state, ds.target, ds.required,
           ds.diagnostic, ds.source, ds.recorded_at,
           vr.rem_id, vr.remediation, vr.remediation_type,
           vr.attempted, vr.verification_result, vr.verification_evidence,
           vr.recorded_at AS rem_recorded_at
    FROM dependency_states ds
    LEFT JOIN validation_remediations vr ON ds.dep_id = vr.dep_id
    {q_where}
    ORDER BY ds.recorded_at DESC, vr.recorded_at DESC
    """

    filas = [dict(x) for x in c.execute(sql, args).fetchall()]

    # Agrupar por dependency
    deps = {}
    for f in filas:
        dep_id = f["dep_id"]
        if dep_id not in deps:
            deps[dep_id] = {
                "dep_id": dep_id,
                "name": f["name"],
                "state": f["state"],
                "target": f["target"],
                "required": f["required"],
                "diagnostic": f["diagnostic"],
                "source": f["source"],
                "recorded_at": f["recorded_at"],
                "remediation": None,
                "verified": False,
                "verification_result": None,
                "evidence": None,
            }
        # Si hay remediation asociada, actualizar el registro de la dependency
        if f["rem_id"] is not None and f["rem_id"] != "":
            deps[dep_id]["remediation"] = {
                "rem_id": f["rem_id"],
                "remediation": f["remediation"],
                "remediation_type": f["remediation_type"],
                "attempted": f["attempted"],
                "verification_result": f["verification_result"],
                "evidence": f["verification_evidence"],
                "rem_recorded_at": f["rem_recorded_at"],
            }
            deps[dep_id]["verified"] = f["verification_result"] is not None and f["verification_result"] != ""
            deps[dep_id]["verification_result"] = f["verification_result"]

    return {"estado": "ok" if deps else "empty",
            "limitations": [] if deps else
            ["no hay dependencias registradas con los filtros proporcionados"],
            "dependencias": list(deps.values())}


# =====================================================================
# RXRE-AUTONOMY-001. Misiones persistentes para ejecución autónoma.
# =====================================================================

def crear_mision(c: sqlite3.Connection, title: str, description: str = "") -> str:
    """Crea una nueva misión en la base de datos. Devuelve su mission_id."""
    mission_id = "mission_" + _sha(title + str(time.time()))
    c.execute(
        "INSERT INTO missions (mission_id, title, description, status, created_at, updated_at) "
        "VALUES (?, ?, ?, 'PENDING', datetime('now'), datetime('now'))",
        (mission_id, title, description))
    c.commit()
    return mission_id

def agregar_tarea_a_mision(c: sqlite3.Connection, mission_id: str, title: str,
                          description: str = "", priority: int = 0,
                          dependencies: Optional[List[str]] = None) -> str:
    """Añade una tarea a una misión existente. Devuelve su task_id."""
    task_id = "task_" + _sha(title + str(time.time()) + str(priority))
    deps = json.dumps(dependencies) if dependencies else None
    c.execute(
        "INSERT INTO mission_tasks (task_id, mission_id, title, description, status, "
        "priority, dependencies, created_at) "
        "VALUES (?, ?, ?, ?, 'PENDING', ?, ?, datetime('now'))",
        (task_id, mission_id, title, description, priority, deps))
    c.commit()
    return task_id

def marcar_tarea_completada(c: sqlite3.Connection, task_id: str,
                           completed_at: Optional[str] = None) -> None:
    """Marca una tarea como completada con su timestamp."""
    if completed_at is None:
        completed_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    c.execute(
        "UPDATE mission_tasks SET status = 'COMPLETED', completed_at = ? WHERE task_id = ?",
        (completed_at, task_id))
    c.commit()

def obtener_mision(c: sqlite3.Connection, mission_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene los datos de una misión. Retorna None si no existe."""
    row = c.execute(
        "SELECT mission_id, title, description, status, created_at, updated_at, "
        "completed_at, last_checkpoint FROM missions WHERE mission_id = ?",
        (mission_id,)).fetchone()
    return dict(row) if row else None

def obtener_criterios_mision(c: sqlite3.Connection, mission_id: str) -> List[Dict[str, Any]]:
    """Obtiene todos los criterios de aceptación de una misión."""
    rows = c.execute(
        "SELECT criterion_id, description, epistemic, evidence_ids, required, created_at "
        "FROM mission_criteria WHERE mission_id = ? ORDER BY criterion_id",
        (mission_id,)).fetchall()
    return [dict(r) for r in rows]

def obtener_tareas_mision(c: sqlite3.Connection, mission_id: str) -> List[Dict[str, Any]]:
    """Obtiene todas las tareas de una misión, ordenadas por prioridad."""
    rows = c.execute(
        "SELECT task_id, title, description, status, priority, dependencies, "
        "created_at, completed_at FROM mission_tasks WHERE mission_id = ? "
        "ORDER BY priority, status DESC",
        (mission_id,)).fetchall()
    return [dict(r) for r in rows]

def verificar_criterios_mision(c: sqlite3.Connection, mission_id: str) -> Dict[str, Any]:
    """Verifica el estado de todos los criterios de aceptación de una misión.

    Para epistemic == 'PROVEN': exige que TODOS los evidence_ids existan en
     y tengan epistemic == 'PROVEN'.
    Para epistemic == 'PARTIAL': exige que AL MENOS UNO de los evidence_ids
    exista y sea 'PROVEN'.
    Para otros estados ('NOT_DETERMINED', 'PROVEN_ABSENT', 'DEFERRED'):
    se marca como 'PENDING' porque requiere verificación manual.
    """
    criterios = obtener_criterios_mision(c, mission_id)
    resultados = []
    for criterio in criterios:
        epistemic_required = criterio['epistemic']
        if epistemic_required == 'PROVEN':
            evidence_ids = json.loads(criterio['evidence_ids'] or '[]')
            if not evidence_ids:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'FAIL',
                    'reason': 'No hay evidence_ids para este criterio'
                })
                continue
            all_proven = True
            for finding_id in evidence_ids:
                finding = c.execute(
                    "SELECT epistemic FROM findings WHERE finding_id = ?",
                    (finding_id,)).fetchone()
                if finding is None or finding[0] != 'PROVEN':
                    all_proven = False
                    break
            if all_proven:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'PASS',
                    'reason': 'Criterio cumplido'
                })
            else:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'FAIL',
                    'reason': 'Criterio no cumplido'
                })
        elif epistemic_required == 'PARTIAL':
            evidence_ids = json.loads(criterio['evidence_ids'] or '[]')
            if not evidence_ids:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'FAIL',
                    'reason': 'No hay evidence_ids para este criterio'
                })
                continue
            found_proven = False
            for finding_id in evidence_ids:
                finding = c.execute(
                    "SELECT epistemic FROM findings WHERE finding_id = ?",
                    (finding_id,)).fetchone()
                if finding is not None and finding[0] == 'PROVEN':
                    found_proven = True
                    break
            if found_proven:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'PASS',
                    'reason': 'Criterio cumplido (parcial)'
                })
            else:
                resultados.append({
                    'criterion_id': criterio['criterion_id'],
                    'status': 'FAIL',
                    'reason': 'Criterio no cumplido (parcial)'
                })
        else:
            resultados.append({
                'criterion_id': criterio['criterion_id'],
                'status': 'PENDING',
                'reason': 'Verificación manual requerida'
            })
    return {
        'mission_id': mission_id,
        'criterios': criterios,
        'resultados': resultados,
        'total_criterios': len(criterios),
        'criterios_cumplidos': sum(1 for r in resultados if r['status'] == 'PASS'),
        'criterios_fallidos': sum(1 for r in resultados if r['status'] == 'FAIL'),
        'criterios_pendientes': sum(1 for r in resultados if r['status'] == 'PENDING')
    }

# ====================================================================
# RXRE-CAUSAL-EVOL-001. SOUL: una funcion de VALOR, no un entero puesto a mano.
#
# EL PROBLEMA QUE ESTA, MEDIDO
# ----------------------------
# `seleccionar_siguiente_accion` ordenaba por:
#     pendientes.sort(key=lambda t: (-t['priority'], t['created_at']))
# `priority` es un entero que escribe una persona. Es decir: la prioridad NO
# estaba en el sistema de conocimiento; estaba en el texto de la tarea. Dos
# consecuencias concretas:
#   * una tarea facil y sin impacto con priority=5 gana a una tarea que
#     desbloquea tres dependents con priority=1, porque no hay nada en el
#     sistema que diga "desbloquea tres dependents".
#   * cuando el mundo cambia (una tarea se bloquea, aparece evidencia,
#     una reflexion registra un fallo que se repite), la prioridad no se
#     entera. No puede: no lee nada.
#
# LO QUE HACE ESTA FUNCION, Y LO QUE NO
# -------------------------------------
# Calcula un valor POR TAREA a partir de lo que esta MEDIDO en las tablas,
# y dice de donde sale cada parte. No es un modelo: son siete componentes
# con significado declarado, peso declarado y fuente declarada.
#
# REGLAS QUE NO SE ROMPEN, Y QUE EL VALOR NO PUEDE SOBRESCRIBIR
# -----------------------------------------------------------
#  1. Una tarea BLOQUEADA por dependencia no se selecciona, valga lo que
#     valga. Un numero alto no convierte un bloqueo en una accion posible.
#  2. Un componente SIN DATOS no vale cero: se EXCLUYE y se renormaliza,
#     y se reporta la cobertura. Un 0 y un "no lo se" no son lo mismo, y
#     confundirlos hace que la ausencia de datos parezca una certeza.
#  3. Cada componente lleva `fuente` (la tabla de la que sale) y
#     `confianza` (observado / asumido). El valor es un HEURISTICO de
#     priorizacion, no una verdad sobre el mundo, y se dice.
#  4. Los pesos son enteros pequenos y declarados. No se inventan
#     decimales: una precision que no se puede sostener no es precision.
#
# DIRECCION DE CADA COMPONENTE (por que suma o resta)
# ---------------------------------------------------
#   desbloquea        +  cuantas tareas PENDING dependen de esta
#   incertidumbre     +  cuantas preguntas ABIERTAS tocan su objetivo
#   evidencia_ausente +  no hay hallazgo que la sustente: hay que medir
#   reincidencia      +  fallos repetidos sobre su objetivo: se rompe
#   coste            -  lo que cuesta ejecutarla
#   alineacion       +  toca un criterio de la mision
# ====================================================================

#: Pesos. Intencionados y documentados, no ajustados a un dataset: no hay
#: datos suficientes en este arbol para justifiable, y fingir que si los hay
#: seria justo el numero sin significado que esta funcion evita.
PESOS_SOUL = {
    "desbloquea": 3,
    "incertidumbre": 2,
    "reincidencia": 2,
    "evidencia_ausente": 2,
    "alineacion": 2,
    "coste": 1,
}

#: Estados de `research` que significan "esta pregunta sigue abierta".
ESTADOS_ABIERTOS = ("OPEN", "NOT_DETERMINED", "PARTIAL")

#: Outcomes de reflexion que indican que algo fallo.
OUTCOMES_FALLO = ("failure", "error", "timeout")


def _deps_de(tarea: Dict[str, Any]) -> List[str]:
    """Dependencias declaradas de una tarea, como lista de task_id."""
    raw = tarea.get("dependencies")
    if not raw:
        return []
    if isinstance(raw, list):
        return [str(x) for x in raw]
    try:
        d = json.loads(raw)
        return [str(x) for x in d] if isinstance(d, list) else []
    except (ValueError, TypeError):
        return []


def _componente(valor: Optional[float], fuente: str,
                confianza: str = "observado") -> Dict[str, Any]:
    """Un componente con su procedencia. `None` = NO SE SABE, no vale 0."""
    return {"valor": valor, "fuente": fuente, "confianza": confianza,
            "conocido": valor is not None}


def _observados_de(observados: set, target: str) -> int:
    """Cuantas claves observadas corresponden a `target`.

    Existe solo para el texto de la fuente del componente. El numero REAL
    esta en la consulta SQL; esto evita meterla en el mensaje y que el
    mensaje y el dato puedan divergir.
    """
    return 1 if target in observados else 0


def _contiene(texto: str, aguja: str) -> bool:
    if not texto or not aguja:
        return False
    return aguja.lower() in str(texto).lower()


def valorar_tareas(c: sqlite3.Connection, mission_id: str) -> Dict[str, Any]:
    """Valora cada tarea PENDING de una mision con datos reales.

    Devuelve, por tarea: los componentes CON su fuente, el valor agregado,
    la cobertura (que proporcion de componentes seyles), si esta bloqueada
    y por que, y una frase que explica el resultado. La frase no es
    decorativa: sin ella, un numero no se puede auditar.
    """
    tareas = obtener_tareas_mision(c, mission_id)
    pendientes = [t for t in tareas if t.get("status") == "PENDING"]
    criterios = obtener_criterios_mision(c, mission_id)
    textos_criterio = " ".join((k.get("description") or "") for k in criterios)

    estado_por_id = {t["task_id"]: t.get("status") for t in tareas}

    # --- datos medidas UNA vez, no una por tarea ------------------------
    abiertas_por_target: Dict[str, int] = {}
    for r in c.execute("SELECT target, status FROM research WHERE kind IN "
                       "('hypothesis','claim','frontier')"):
        if (r["status"] or "") in ESTADOS_ABIERTOS and r["target"]:
            abiertas_por_target[r["target"]] = abiertas_por_target.get(r["target"], 0) + 1

    # MEDIDO 2026-10-14: esto buscaba el target en `operations`, uniendolas
    # por `attempt_id`. Con las 11 lecciones reales — todas con
    # `attempt_id` nulo — devolvia CERO para cualquier target, y el
    # componente `reincidencia` era siempre "desconocido". Es decir: la
    # memoria existia y no influia en nada.
    #
    # Ahora se lee la columna propia. Y si la reflexion no la trae, se
    # recurre a la operacion, para que las antiguas sigan contando.
    fallos_por_target: Dict[str, int] = {}
    totales_por_clave: Dict[str, int] = {}
    _args = OUTCOMES_FALLO
    for r in c.execute(
            "SELECT COALESCE(NULLIF(f.target,''), o.target) AS t, "
            "       COALESCE(NULLIF(f.capability,''), o.capability) AS c, "
            "       SUM(CASE WHEN f.outcome IN (%s) THEN 1 ELSE 0 END) AS n_fail, "
            "       COUNT(f.reflexion_id) AS n_total "
            "FROM reflexiones f LEFT JOIN operations o "
            "  ON f.attempt_id = o.operation_id "
            "GROUP BY t, c" % ",".join("?" * len(_args)), _args):
        for clave in (r["t"], r["c"]):
            if clave:
                totales_por_clave[clave] = totales_por_clave.get(clave, 0) + (r["n_total"] or 0)
                fallos_por_target[clave] = fallos_por_target.get(clave, 0) + (r["n_fail"] or 0)

    # MEDIDO 2026-10-14 (bug propio, cazado por el test): esto iteraba
    # `for t in abiertas_por_target`, es decir, SOLO sobre targets que ya
    # tenian una pregunta abierta. Un hallazgo que cita un target cerrado
    # — que es el caso normal: ya lo resolviste — no se contaba nunca, y su
    # tarea salia con `evidencia_ausente = 1.0` cuando lo correcto es 0.0.
    # Es justo el error que el componente existe para evitar: afirmar que no
    # hay evidencia cuando si la hay.
    #
    # Los targets se reunen de research Y de findings, antes de comparar.
    targets_conocidos = set(abiertas_por_target) | set(fallos_por_target)
    for r in c.execute("SELECT claim FROM findings"):
        targets_conocidos |= set(re.findall(r"[\w.]+\.[\w.]+", r["claim"] or ""))

    hallazgos_por_target: Dict[str, int] = {}
    for r in c.execute("SELECT claim FROM findings"):
        for t in targets_conocidos:
            if t and _contiene(r["claim"], t):
                hallazgos_por_target[t] = hallazgos_por_target.get(t, 0) + 1

    # cuantas tareas PENDING dependen de cada una
    dependientes: Dict[str, int] = {}
    for t in pendientes:
        for d in _deps_de(t):
            dependientes[d] = dependientes.get(d, 0) + 1

    salida = []
    for t in pendientes:
        tid = t["task_id"]
        texto = " ".join(str(t.get(k) or "") for k in ("title", "description"))
        target = _target_de(texto)

        # --- COMPONENTE: desbloquea -----------------------------------
        n_dep = dependientes.get(tid, 0)
        c_desbloquea = _componente(
            float(min(n_dep, 3)) / 3.0,
            "mission_tasks.dependencies (%d tareas PENDING dependen de esta)" % n_dep)

        # --- COMPONENTE: bloqueada (PUERTA, no puntuacion) --------------
        deps = _deps_de(t)
        sin_cumplir = [d for d in deps if estado_por_id.get(d) not in
                       ("COMPLETED", "DONE")]
        bloqueada = bool(sin_cumplir)

        # --- COMPONENTE: incertidumbre ---------------------------------
        abiertas = abiertas_por_target.get(target, 0) if target else None
        c_inc = _componente(
            float(min(abiertas, 3)) / 3.0 if abiertas is not None else None,
            "research con status abierto y target=%r" % (target or ""),
            "observado" if target else "asumido")

        # --- COMPONENTE: evidencia_ausente ----------------------------
        if target:
            n_hall = hallazgos_por_target.get(target, 0)
            c_ev = _componente(0.0 if n_hall else 1.0,
                               "findings que citan %r: %d" % (target, n_hall))
        else:
            c_ev = _componente(None, "la tarea no nombra un target reconocible",
                               "asumido")

        # --- COMPONENTE: reincidencia ---------------------------------
        # MEDIDO 2026-10-14 (replay FASE 4): esto devolvia 0.0 cuando no
        # habia ninguna reflexion sobre el target. Y eso es WRONG de una
        # forma que importa: `0.0` dice "lo observe y no fallo", cuando en
        # realidad no se ha observado NADA. Con las dos tareas empatadas a
        # 0.0, el replay dio el MISMO resultado con y sin leccion, y no
        # habia forma de distinguir el efecto del azar.
        #
        # La distincion correcta:
        #   - hay AL MENOS UNA reflexion sobre el target y ninguna es de
        #     fallo  -> 0.0 MEDIDO. Se observo y no se rompio.
        #   - no hay ninguna reflexion sobre el target -> DESCONOCIDO. No
        #     se ha mirado, y "no se ha mirado" no es "no pasa".
        fallos = fallos_por_target.get(target, 0) if target else None
        if not target:
            c_reinc = _componente(None, "la tarea no nombra un target reconocible",
                                  "asumido")
        elif target in totales_por_clave:
            c_reinc = _componente(
                float(min(fallos, 3)) / 3.0,
                "reflexiones de fallo sobre target=%r: %d de %d "
                "reflexiones observadas" % (target, fallos,
                                            totales_por_clave[target]),
                "observado")
        else:
            c_reinc = _componente(
                None,
                "no hay NINGUNA reflexion sobre target=%r: no se ha medido si "
                "se rompe, que no es lo mismo que medir que no se rompe"
                % (target,), "desconocido")
        # `observados` se usaba antes para el mismo proposito; se mantiene
        # como vista del conjunto aunque el mensaje ahora use totales claros.

        # --- COMPONENTE: alineacion -----------------------------------
        alineada = bool(target and _contiene(textos_criterio, target))
        c_ali = _componente(1.0 if alineada else 0.0,
                            "mission_criteria que mencionan %r" % (target or ""))

        # --- COMPONENTE: coste ----------------------------------------
        cap = _capability_de(texto)
        coste = None
        if cap:
            try:
                from backends import dispatch as _D
                f = _D._todas_las_fichas().get(cap) or {}
                est = f.get("estado_agregado")
                if est == "AVAILABLE":
                    coste = 0.0          # ejecutable de inmediato: barato
                elif est in ("PARTIAL",):
                    coste = 0.5
                else:
                    coste = 1.0          # no ejecutable: caro de verdad
            except Exception:
                coste = None
        c_coste = _componente(coste,
                              "registry: estado de la capability %r" % (cap or ""))

        comps = {"desbloquea": c_desbloquea, "incertidumbre": c_inc,
                 "evidencia_ausente": c_ev, "reincidencia": c_reinc,
                 "alineacion": c_ali, "coste": c_coste}

        # --- AGREGADO --------------------------------------------------
        # MEDIDO 2026-10-14 (replay FASE 4): el denominador era la suma de
        # los pesos CONOCIDOS, y eso premia la ignorancia. Una tarea sin
        # ningun componente medido salia con valor 0 sobre una base de 5; la
        # misma tarea con un solo componente conocido a 1.0 salia 1.0 sobre
        # base 2. Es decir: cuanto menos se sabe de una tarea, mas alto
        # puntua. Para priorizar eso esta al reves.
        #
        # El denominador es ahora FIJO (la suma de todos los pesos). Un
        # componente desconocido aporta 0, que NO es lo mismo que aportar un
        # cero medido: significa "no hay senal positiva aqui". La fraccion
        # que si falta se declara en `cobertura`, que es donde se lee si la
        # puntuacion se apoya en datos o en suposiciones.
        #
        # El componente con valor 0 MEDIDO (por ejemplo: se observo y no
        # fallo) sigue aportando 0 al numerador y 0 a la cobertura, asi que
        # los dos casos se distinguen en el reporte aunque puntuen igual.
        base = sum(PESOS_SOUL.values()) or 1
        conocidos = {k: v for k, v in comps.items() if v["conocido"]}
        valor = sum(PESOS_SOUL[k] * (v["valor"] or 0.0)
                    for k, v in comps.items()) / base
        cobertura = len(conocidos) / float(len(comps))

        if bloqueada:
            porque = ("BLOQUEADA por %s (valor %.3f no la desbloquea: un numero "
                      "no convierte una dependencia sin cumplir en una accion "
                      "posible)" % (", ".join(sin_cumplir[:3]), valor))
        else:
            piezas = ["%s=%.2f" % (k, v["valor"]) for k, v in
                      sorted(conocidos.items(), key=lambda kv: -PESOS_SOUL[kv[0]])[:3]]
            porque = ("valor %.3f = %.3f/%d sobre cobertura %.0f%% con %s"
                      % (valor,
                         sum(PESOS_SOUL[k] * (v["valor"] or 0.0)
                             for k, v in comps.items()),
                         base, cobertura * 100,
                         ", ".join(piezas) or "ningun componente medido"))

        salida.append({
            "task_id": tid, "title": t.get("title"), "valor": round(valor, 4),
            "cobertura": round(cobertura, 3),
            "bloqueada": bloqueada, "bloqueada_por": sin_cumplir,
            "componentes": comps, "por_que": porque,
            "priority_manuscrita": t.get("priority"),
        })

    # --- desempate DETERMINISTA --------------------------------------
    # El valor manda; a igualdad, la que mas desbloquea; a igualdad, la
    # `priority` escrita a mano; y solo al final el task_id.
    #
    # MEDIDO 2026-10-14: antes de este cambio el desempate final era el
    # `task_id`, y eso ROMPIO `test_mission001.test_resume_after_restart`.
    # No por casualidad: con dos tareas que no nombran target, no tienen
    # dependencias y no tocan ningun criterio, la funcion de valor no tiene
    # NADA que distinguirlas. Las dos vale 0.0 y el orden salia del hash del
    # id, que es arbitrario. Un desempate arbitrario es peor que no tener
    # ninguno: pierde una senal que el operador si declaro.
    #
    # Por eso `priority` se usa como ultimo recurso, NO como criterio
    # principal. Sigue siendo lo que es: un entero escrito a mano. Pero
    # cuando el sistema no puede distinguir, es mejor la senal declarada
    # que un hash. La funcion degrada con elegancia al comportamiento
    # anterior en vez de perderlo, y solo cuando hay senal manda ella.
    salida.sort(key=lambda x: (-(0 if x["bloqueada"] else 1), -x["valor"],
                               -x["componentes"]["desbloquea"]["valor"],
                               -int(x["priority_manuscrita"] or 0),
                               x["task_id"]))
    return {"mission_id": mission_id, "tareas": salida,
            "pesos": PESOS_SOUL,
            "limitaciones": [
                "el valor es un HEURISTICO de priorizacion, no una verdad "
                "sobre el mundo: no hay en este arbol datos suficientes para "
                "ajustar los pesos, y se declaran en vez de ajustarlos.",
                "la cobertura dice que proporcion de componentes se pudo "
                "medir. Una tarea con cobertura 0.5 y valor alto no es la "
                "misma cosa que una con cobertura 1.0 y valor alto.",
            ]}


def _target_de(texto: str) -> str:
    """Saca un objetivo reconocible del texto de una tarea.

    `target:<algo>` es la convencion explicita. Sin ella, se usa el
    nombre de una capability registrada, que es lo unico que RXRE puede
    resolver de verdad. Inventar un target a partir de palabras sueltas
    seria hacer que el valor dependa de la prosa.
    """
    import re as _re
    m = _re.search(r"target:\s*([A-Za-z0-9_.:\-]+)", texto or "")
    if m:
        return m.group(1).strip()
    m2 = _re.search(r"\b(binary|gpu|rxre|source)\.[a-z_]+", texto or "")
    if m2:
        return m2.group(0)
    return ""


def _capability_de(texto: str) -> str:
    """Nombre de una capability citada en el texto de la tarea, o ""."""
    import re as _re
    m = _re.search(r"\b(?:binary|gpu|rxre|source)\.[a-z_]+", texto or "")
    return m.group(0) if m else ""


def seleccionar_siguiente_accion(c: sqlite3.Connection, mission_id: str,
                                 por_valor: bool = True) -> Optional[str]:
    """Selecciona la siguiente accion. Retorna None si no hay ninguna posible.

    MEDIDO 2026-10-14 (RXRE-CAUSAL-EVOL-001): antes esto ordenaba por
    `priority`, un entero escrito por una persona. Con dos tareas identicas
    salvo por ese entero, ganaba la de mayor numero. La funcion de valor
    (`valorar_tareas`) lee el estado REAL: cuantas tareas dependen de esta,
    cuantas preguntas abiertas la tocan, si hay fallos repetidos sobre su
    objetivo, si existe evidencia, y cuanto cuesta.

    `por_valor=False` conserva el comportamiento anterior, para poder
    COMPARAR los dos en vez de sustituirlos sin dejar forma de volver.

    La puerta no es negociable: una tarea bloqueada por una dependencia sin
    cumplir no se devuelve, diga lo que diga su valor. Antes no habia ni
    puerta: `dependencies` se guardaba y no se leia.
    """
    if por_valor:
        v = valorar_tareas(c, mission_id)
        viables = [t for t in v["tareas"] if not t["bloqueada"]]
        return viables[0]["task_id"] if viables else None
    tareas = obtener_tareas_mision(c, mission_id)
    pendientes = [t for t in tareas if t['status'] == 'PENDING']
    if pendientes:
        pendientes.sort(key=lambda t: (-t['priority'], t['created_at']))
        return pendientes[0]['task_id']
    return None

def marcar_mision_completada(c: sqlite3.Connection, mission_id: str) -> Dict[str, Any]:
    """Marca una misión como completada solo si todos los criterios requeridos están satisfechos.
    
    Returns:
        Dict with 'success' (bool), 'mission_id', and 'reason' if failed
    """
    # Verificar que todos los criterios requeridos estén satisfechos
    criterios_result = verificar_criterios_mision(c, mission_id)
    
    # Revisar cada criterio requerido usando los resultados de verificación
    for criterio, resultado in zip(criterios_result['criterios'], criterios_result['resultados']):
        # Solo los criterios required=1 y epistemic=PROVEN deben pasar para completar
        if criterio['required'] == 1 and criterio['epistemic'] == 'PROVEN':
            if resultado['status'] != 'PASS':
                return {
                    'success': False,
                    'mission_id': mission_id,
                    'reason': f"Criterio requerido no satisfecho: {criterio['description']} (verificación: {resultado['status']} - {resultado['reason']})"
                }
    
    # Si llegamos aquí, todos los criterios requeridos y PROVEN pasan
    c.execute(
        "UPDATE missions SET status = 'COMPLETED', completed_at = datetime('now') "
        "WHERE mission_id = ?", (mission_id,))
    c.commit()
    
    return {
        'success': True,
        'mission_id': mission_id,
        'reason': 'Misión completada exitosamente'
    }

def crear_criterio_mision(c: sqlite3.Connection, mission_id: str, description: str,
                          epistemic: str = 'NOT_DETERMINED',
                          evidence_ids: Optional[List[str]] = None,
                          required: int = 1) -> str:
    """Crea un criterio de aceptación para una misión. Devuelve su criterion_id."""
    criterion_id = "crit_" + _sha(description + str(time.time()))
    c.execute(
        "INSERT INTO mission_criteria (criterion_id, mission_id, description, epistemic, "
        "evidence_ids, required, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (criterion_id, mission_id, description, epistemic,
         json.dumps(evidence_ids) if evidence_ids else None, required))
    c.commit()
    return criterion_id

def resumir_mision(c: sqlite3.Connection, mission_id: str) -> Dict[str, Any]:
    """Resumen compacto del estado de una misión, útil para handoff a otra IA."""
    mision = obtener_mision(c, mission_id)
    if not mision:
        return {'status': 'empty', 'limitations': ['no hay ninguna misión con ese id']}
    criterios = verificar_criterios_mision(c, mission_id)
    return {
        'status': 'ok',
        'mission_id': mission_id,
        'title': mision['title'],
        'status': mision['status'],
        'total_criterios': criterios['total_criterios'],
        'criterios_cumplidos': criterios['criterios_cumplidos'],
        'criterios_fallidos': criterios['criterios_fallidos'],
        'criterios_pendientes': criterios['criterios_pendientes'],
        'total_tareas': len(obtener_tareas_mision(c, mission_id)),
        'siguiente_accion': seleccionar_siguiente_accion(c, mission_id),
        'limitations': [],
    }


def capturar_evidencia_desde_ejecucion(c: sqlite3.Connection, execution_result: Dict[str, Any], 
                                       capability: str = "") -> str:
    """Captura los resultados de una ejecución dispatch como evidencia de finding.
    
    Crea un registro en la tabla findings con:
    - claim: resumen del resultado
    - epistemic: PROVEN si exit_code == 0, PARTIAL si rc != 0
    - provenance: capability, timestamp, tool info
    - limitations: descripción del entorno
    
    Returns:
        finding_id del registro creado
    """
    import datetime
    
    # Determinar epistemic basado en exit code
    exit_code = execution_result.get('rc', execution_result.get('exit_code', -1))
    status = execution_result.get('status', 'unknown')
    
    if exit_code == 0 and status not in ('blocked', 'error'):
        epistemic = 'PROVEN'
        claim = f"Ejecucion exitosa: {capability or 'desconocido'}"
        limitations = f"[runtime] exit_code=0, status={status}"
    elif exit_code is not None and exit_code != 0:
        epistemic = 'PARTIAL'
        claim = f"Ejecucion completada con exit_code={exit_code}"
        limitations = f"[runtime] exit_code={exit_code}, status={status}"
    else:
        epistemic = 'NOT_DETERMINED'
        claim = f"Ejecucion no pudo completarse: {status}"
        limitations = f"[runtime] status={status}, rc={exit_code}"
    
    provenance = json.dumps({
        "capability": capability,
        "timestamp": datetime.datetime.now().isoformat(),
        "tool": "dispatch.ejecutar",
        "result_hash": hashlib.sha256(
            json.dumps(execution_result, sort_keys=True).encode()
        ).hexdigest()[:16]
    })
    
    # Insertar finding
    c.execute(
        "INSERT INTO findings (finding_id, claim, epistemic, evidence_ids, provenance, limitations, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (f"exec_{int(time.time())}_{hash(capability or '') % 10000:04d}", claim, epistemic, 
         json.dumps([]), provenance, limitations)
    )
    c.commit()
    
    finding_id = c.execute(
        "SELECT last_insert_rowid() FROM findings"
    ).fetchone()[0]
    
    # Formatear ID string
    finding_id_str = f"finding_{int(finding_id):06d}"
    
    return finding_id_str


# ====================================================================
# RXRE-1641: Knowledge persistence functions (guardar_finding,
# recuperar_finding, recuperar_relaciones_finding, relacionar_findings)
#
# These functions implement the persistence contract declared by the
# rz_findings adapter. Each follows the epistemic rules:
#   - finding_id is DETERMINISTIC (SHA256 of claim + evidence_ids)
#   - collisions are reported as "COLISION:<existing_id>" (idempotency)
#   - JSON fields are serialized/deserialized on the boundary
# ====================================================================


# =========================================================================
# [v3-4] Optimistic locking: errores tipados y funcion publica.
# =========================================================================
class IntegrityError(RuntimeError):
    """El `row_hash` recalculado no coincide con el almacenado.

    No es un error de base de datos: la base esta bien. Lo que esta mal es
    que la fila fue alterada por una via que el trigger no cubre. Se distingue
    para que el llamador no la confunda con un fallo de disco y reintente.
    """


class StaleVersionError(RuntimeError):
    """El `version` cambio entre la lectura y el UPDATE.

    No es un error de disco ni de base de datos: la base esta bien. Lo que
    esta mal es que la lectura que se hizo antes ya no es vigente. El
    llamador debe releer y reintentar, no reintentar a ciegas.
    """


def actualizar_estado_finding(c: sqlite3.Connection, finding_id: str,
                              nuevo_estado: str,
                              version_esperada: int) -> int:
    """[v3-4] UPDATE optimista de `findings.epistemic`.

    Retorna rowcount: 1 = aplico, 0 = otro escritor gano la carrera.

    La semantica es la misma que `update_claim_state` del esqueleto, pero
    adaptada a `findings` (que tiene `epistemic`, no `epistemic_state`).

    Por que devuelve int y no lanza: esta es la funcion PUBLICA, y su
    contrato es "dime si aplique". Quien quiera lanzar (reevaluar_finding)
    chequea el 0 y lanza StaleVersionError. Dos semantica, una decision:
    la funcion publica reporta, la de alto nivel exige.

    [v3-2] INVALIDATED no es automatico: si alguien intenta setear
    INVALIDATED sin haber registrado una reevaluacion documentada, se
    rechaza. La unica via legitima es reevaluar_finding(), que registra
    la reevaluacion Y actualiza el estado en el mismo paso.
    """
    if nuevo_estado == "INVALIDATED":
        reev = c.execute(
            "SELECT 1 FROM finding_reevaluations "
            "WHERE finding_id=? AND decision='INVALIDATED' LIMIT 1",
            (finding_id,)).fetchone()
        if reev is None:
            raise ValueError(
                "INVALIDATED requiere reevaluacion documentada "
                "(finding_reevaluations con decision='INVALIDATED')")
    cur = c.execute(
        "UPDATE findings SET epistemic = ?, version = version + 1 "
        "WHERE finding_id = ? AND version = ?",
        (nuevo_estado, finding_id, version_esperada))
    return cur.rowcount


def guardar_finding(c: sqlite3.Connection, finding_dict: Dict[str, Any]) -> str:
    """Persiste un hallazgo con ID determinista basado en claim + evidence_ids.

    Contrato del adapter (rz_findings.py:273):
        finding_id = S.guardar_finding(c, finding_dict)

    finding_dict contiene:
        claim: str (texto de la afirmacion)
        epistemic: str (PROVEN, PARTIAL, NOT_DETERMINED, PROVEN_ABSENT, DEFERRED)
        evidence_ids: list[str] (result_ids que soportan el claim)
        provenance: dict (producer, tool_version, params, timestamp)
        limitations: list[str] (limitaciones declaradas)
        op_id: str (operation_id de origen, opcional)

    Retorna:
        finding_id (str) — nuevo, si se creo
        "COLISION:<existing_id>" — si ya existia uno con la misma fingerprint
    """
    claim = finding_dict.get("claim", "")
    evidence_ids = finding_dict.get("evidence_ids", [])
    epistemic = finding_dict.get("epistemic", "NOT_DETERMINED")
    provenance = finding_dict.get("provenance", {})
    limitations = finding_dict.get("limitations", [])

    # Deterministic ID: SHA256 de claim + evidence_ids ordenados
    # La fingerprint captura el claim y la evidencia exacta. Si dos llamadas
    # crean el mismo claim con la misma evidencia, deben devolver el mismo
    # finding_id -> idempotencia, no duplicacion.
    evidencia_str = json.dumps(sorted(evidence_ids), sort_keys=True)
    fingerprint = (claim or "") + "|" + evidencia_str
    finding_id = "finding_" + hashlib.sha256(fingerprint.encode()).hexdigest()[:16]

    # Verificar colision (idempotencia)
    existing = c.execute(
        "SELECT finding_id FROM findings WHERE finding_id=?",
        (finding_id,)
    ).fetchone()
    if existing:
        return "COLISION:" + existing["finding_id"]

    # Insertar el hallazgo.
    #
    # ANTES: INSERT OR REPLACE. Eso pisaba un finding existente con el mismo
    # id sin dejar rastro, y reseteaba la version a 0, invalidando el
    # optimistic locking. La verificacion de colision de arriba ya cubre el
    # caso "mismo id": si existe, se devuelve "COLISION:<id>" y no se llega
    # aqui. Por tanto el REPLACE es codigo muerto que ademas hace dano, y se
    # quita.
    c.execute(
        "INSERT INTO findings "
        "(finding_id, op_id, claim, epistemic, evidence_ids, "
        " provenance, limitations, created_at, version, "
        " object_hash, scope, derivation_refs, contradiction_refs, "
        " falsification_test) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), 0, "
        " ?, ?, ?, ?, ?)",
        (
            finding_id,
            finding_dict.get("op_id") or None,  # NULL when no op_id (FK)
            claim,
            epistemic,
            json.dumps(evidence_ids) if evidence_ids else "[]",
            json.dumps(provenance) if provenance else "{}",
            json.dumps(limitations) if limitations else "[]",
            finding_dict.get("object_hash"),
            finding_dict.get("scope"),
            json.dumps(finding_dict.get("derivation_refs", []))
            if finding_dict.get("derivation_refs") is not None
            and not isinstance(finding_dict.get("derivation_refs"), str)
            else (finding_dict.get("derivation_refs") or "[]"),
            json.dumps(finding_dict.get("contradiction_refs", []))
            if finding_dict.get("contradiction_refs") is not None
            and not isinstance(finding_dict.get("contradiction_refs"), str)
            else (finding_dict.get("contradiction_refs") or "[]"),
            finding_dict.get("falsification_test"),
        )
    )
    c.commit()
    # BMS-EXT-001: audit log entry for finding creation
    registrar_audit_log(c, "create_finding", "finding", finding_id,
                        actor="rxre.create_finding",
                        details={"claim_preview": (claim or "")[:80],
                                 "epistemic": epistemic,
                                 "op_id": finding_dict.get("op_id") or None})
    return finding_id


# BMS-EXT-001: Audit log function (inspired by RKA Core's audit_log table).
# Each write operation calls this to record who did what and when.
def registrar_audit_log(c: sqlite3.Connection, action: str, entity_type: str,
                         entity_id: str, actor: str = "system",
                         details: Optional[Dict[str, Any]] = None) -> int:
    """Registra una entrada en el audit_log.

    Contrato: cada registrar(), guardar_finding() y relacionar_findings()
    escribe un entry para forense de quién hizo qué y cuándo.

    No levanta excepciones: si el audit_log falla, no debe romper la
    operación principal.
    """
    try:
        c.execute(
            "INSERT INTO audit_log (action, entity_type, entity_id, actor, details) "
            "VALUES (?, ?, ?, ?, ?)",
            (action, entity_type, entity_id, actor,
             json.dumps(details) if details else "{}")
        )
        c.commit()
    except Exception:
        # BMS-EXT-001: el audit log es best-effort. Si falla, no romper
        # la operación principal.
        pass
    return c.execute("SELECT last_insert_rowid()").fetchone()[0]


def recuperar_finding(c: sqlite3.Connection, finding_id: str) -> Optional[Dict[str, Any]]:
    """Recupera un hallazgo por su ID.

    Contrato del adapter (rz_findings.py:280, 297, 427, 506, 611, 612, etc.):
        f = S.recuperar_finding(c, finding_id)
        if f is None: ...handle not found...

    Los campos JSON (evidence_ids, provenance, limitations) se parsean de vuelta
    a objetos Python.

    Retorna None si no existe.
    """
    row = c.execute(
        "SELECT finding_id, op_id, claim, epistemic, evidence_ids, "
        " provenance, limitations, created_at, reevaluation_id, version, "
        " object_hash, scope, derivation_refs, contradiction_refs, "
        " falsification_test "
        "FROM findings WHERE finding_id=?",
        (finding_id,)
    ).fetchone()
    if row is None:
        return None

    f = dict(row)
    # Parsear campos JSON
    if f.get("evidence_ids"):
        try:
            f["evidence_ids"] = json.loads(f["evidence_ids"])
        except (ValueError, TypeError):
            pass
    else:
        f["evidence_ids"] = []
    if f.get("provenance"):
        try:
            f["provenance"] = json.loads(f["provenance"])
        except (ValueError, TypeError):
            f["provenance"] = {}
    else:
        f["provenance"] = {}
    if f.get("limitations"):
        try:
            f["limitations"] = json.loads(f["limitations"])
        except (ValueError, TypeError):
            f["limitations"] = []
    else:
        f["limitations"] = []
    # Los 5 campos nuevos del contrato TIERRA-1. Se parsean si son JSON,
    # se dejan como string si son texto (object_hash, scope, falsification_test).
    for campo in ("derivation_refs", "contradiction_refs"):
        if f.get(campo):
            try:
                f[campo] = json.loads(f[campo])
            except (ValueError, TypeError):
                pass
        else:
            f[campo] = []
    return f


# =========================================================================
# [v3-2] REEVALUACION: la UNICA via por la que un finding llega a
# INVALIDATED. Y la unica via por la que vuelve a PROVEN.
# =========================================================================
DECISION_REEVALUACION = ("INVALIDATED", "REVERTED", "PARTIAL")

# Que estado epistémico produce cada decisión. `REVERTED` no es un estado:
# es la decisión de DEVOLVER a PROVEN porque se refutó la contradicción.
_ESTADO_POR_DECISION = {
    "INVALIDATED": "INVALIDATED",
    "REVERTED": "PROVEN",
    "PARTIAL": "PARTIAL",
}


def reevaluar_finding(c: sqlite3.Connection, finding_id: str,
                      contradiction: str, decision: str, rationale: str,
                      reviewer: str) -> Dict[str, Any]:
    """[v3-2] Reevalúa un finding y REGISTRA quién lo hizo y por qué.

    El diagrama: "INVALIDATED ≠ automático: contradicción → reevaluación
    documentada → puede resultar en INVALIDATED o volver a PROVEN si se refuta
    la contradicción".

    Por qué una función y no un `UPDATE findings SET epistemic=...`:

      · Si cualquiera pudiera escribir INVALIDATED, el estado no valdría nada:
        bastaría con teclear la palabra para tumbar un hallazgo sin evidencia
        de por qué. La v3-2 pide que la invalidación sea un ACTO con autor,
        no un valor.
      · La fila en `finding_reevaluations` es el rastro. Sin ella, un
        INVALIDATED posterior sería indistinguible de uno escrito a mano.
      · `REVERTED` existe porque refutar una contradicción es tan legítimo
        como aceptarla. Sin la vía de vuelta, aceptar la primera contradicción
        que llegue sería irreversible, y un sistema así aprende a ignorar las
        contradicciones antes que a resolverlas.

    Returns:
        {"reevaluation_id", "finding_id", "epistemic", "decision", "reviewer"}

    Raises:
        ValueError si la decisión no es válida, o si el finding no existe, o
        si faltan `contradiction` / `rationale` / `reviewer` — porque una
        reevaluación sin autor declarado no es una reevaluación.
    """
    if decision not in DECISION_REEVALUACION:
        raise ValueError(
            "decision de reevaluacion invalida: %r (validas: %s)"
            % (decision, ", ".join(DECISION_REEVALUACION)))
    if not contradiction:
        raise ValueError("reevaluar sin `contradiction` no es reevaluar: "
                         "hay que decir QUE se contradice")
    if not rationale:
        raise ValueError("reevaluar sin `rationale` no deja por que se "
                         "decidio, que es justo lo que la v3-2 exige")
    if not reviewer:
        raise ValueError("reevaluar sin `reviewer` deja la invalidacion sin "
                         "autor; la v3-2 prohibe exactamente eso")

    fila = c.execute("SELECT finding_id FROM findings WHERE finding_id=?",
                     (finding_id,)).fetchone()
    if fila is None:
        raise ValueError("finding inexistente: %s" % finding_id)

    # id determinista: la misma reevaluación con los mismos cinco datos es la
    # misma. Repetirla no duplica el rastro.
    fingerprint = "|".join([finding_id, contradiction, decision, rationale,
                            reviewer])
    reevaluation_id = "reeval_" + hashlib.sha256(
        fingerprint.encode()).hexdigest()[:16]

    c.execute(
        "INSERT OR IGNORE INTO finding_reevaluations "
        "(reevaluation_id, finding_id, contradiction, decision, rationale, "
        " reviewer, created_at) VALUES (?,?,?,?,?,?,?)",
        (reevaluation_id, finding_id, contradiction, decision, rationale,
         reviewer, _ahora_iso())
    )
    # [v3-4] Optimistic locking: la reevaluacion no puede pisar un estado que
    # otro escritor movio entre la lectura y el UPDATE. Si rowcount != 1, la
    # version cambio y se lanza StaleVersionError.
    fila = c.execute("SELECT version FROM findings WHERE finding_id=?",
                     (finding_id,)).fetchone()
    version_actual = fila["version"] if fila else 0
    cur = c.execute(
        "UPDATE findings SET epistemic=?, reevaluation_id=?, version=version+1 "
        "WHERE finding_id=? AND version=?",
        (_ESTADO_POR_DECISION[decision], reevaluation_id, finding_id,
         version_actual))
    if cur.rowcount != 1:
        raise StaleVersionError(
            "version de %s cambio antes del UPDATE (se esperaba %d). "
            "Reintenta con la version leida." % (finding_id, version_actual))
    c.commit()
    return {"reevaluation_id": reevaluation_id, "finding_id": finding_id,
            "decision": decision, "reviewer": reviewer,
            "epistemic": _ESTADO_POR_DECISION[decision]}


def reevaluaciones_de_finding(c: sqlite3.Connection,
                              finding_id: str) -> List[Dict[str, Any]]:
    """[v3-2] El HISTÓRICO de reevaluaciones de un finding.

    Se lee entero y en orden cronológico. Un sistema donde solo se conserva la
    última decisión no tiene histórico: tiene estado, y el estado no explica.
    """
    rows = c.execute(
        "SELECT reevaluation_id, contradiction, decision, rationale, "
        "       reviewer, created_at "
        "FROM finding_reevaluations WHERE finding_id=? "
        "ORDER BY created_at, rowid",
        (finding_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def _ahora_iso() -> str:
    """Timestamp UTC con precision de microsegundos.

    Se usa `time` y no `datetime` a proposito: `datetime` no esta importado
    en este modulo y anadirlo por una sola llamada seria mas ruido que el que
    evita.

    LA PRECISION NO ES COSMETICA. Con segundos, dos reevaluaciones seguidas
    empatan en `created_at` y el desempate pasa a ser el `reevaluation_id`, que
    es un hash: el historico se ordenaria al azar dentro del mismo segundo. Un
    historico que no ordena no es un historico. Los microsegundos evitan el
    empate; el `ORDER BY ... , rowid` de abajo lo cubre igualmente.
    """
    ahora = time.time()
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(ahora)) + \
        ".%06dZ" % int((ahora % 1) * 1000000)


def recuperar_relaciones_finding(c: sqlite3.Connection, finding_id: str) -> List[Dict[str, Any]]:
    """Recupera todas las relaciones donde el finding es source o target.

    Contrato del adapter (rz_findings.py:441, 515):
        relaciones = S.recuperar_relaciones_finding(c, finding_id)

    Cada relacion incluye: relation_id, source_id, target_id, relation,
    evidence (dict parseado), confidence, created_at.
    """
    rows = c.execute(
        "SELECT relation_id, source_id, target_id, relation, evidence, "
        " confidence, created_at "
        "FROM finding_relations "
        "WHERE source_id=? OR target_id=? "
        "ORDER BY created_at",
        (finding_id, finding_id)
    ).fetchall()

    relaciones = []
    for row in rows:
        r = dict(row)
        if r.get("evidence"):
            try:
                r["evidence"] = json.loads(r["evidence"])
            except (ValueError, TypeError):
                r["evidence"] = {}
        else:
            r["evidence"] = {}
        relaciones.append(r)
    return relaciones


def relacionar_findings(
    c: sqlite3.Connection,
    source_finding_id: str,
    target_finding_id: str,
    relation: str,
    evidence: Dict[str, Any],
    confidence: str = "DEBIL",
) -> str:
    """Crea una relacion entre dos hallazgos con ID determinista.

    Contrato del adapter (rz_findings.py:661):
        rel_id = S.relacionar_findings(
            c, source_finding_id, target_finding_id,
            relation, evidence, confidence
        )

    La fingerprint es: source_id|target_id|relation
    Si la relacion ya existe, retorna "COLISION:<existing_id>" (idempotencia).
    """
    # Deterministic ID basado en source|target|relation
    relation_seed = f"rel:{source_finding_id}|{target_finding_id}|{relation}"
    relation_id = "rel_" + hashlib.sha256(relation_seed.encode()).hexdigest()[:16]

    # Verificar colision (idempotencia)
    existing = c.execute(
        "SELECT relation_id FROM finding_relations WHERE relation_id=?",
        (relation_id,)
    ).fetchone()
    if existing:
        return "COLISION:" + existing["relation_id"]

    # Insertar la relacion
    c.execute(
        "INSERT OR REPLACE INTO finding_relations "
        "(relation_id, source_id, target_id, relation, evidence, confidence, "
        " created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
        (
            relation_id,
            source_finding_id,
            target_finding_id,
            relation,
            json.dumps(evidence) if evidence else "{}",
            confidence,
        )
    )
    c.commit()
    # BMS-EXT-001: audit log entry for relation creation
    registrar_audit_log(c, "create_relation", "finding_relation", relation_id,
                        actor="rxre.create_finding_relation",
                        details={"source_id": source_finding_id,
                                 "target_id": target_finding_id,
                                 "relation": relation,
                                 "confidence": confidence})
    return relation_id


# ====================================================================
# RXRE-AUTONOMY-002. Self-reflection memory.
#
# Inspirado en Reflexion (noahshinn/reflexion), Recuris y MemSkill:
# registro estructurado de lo que se intento, que salio, por que, y que
# debe cambiar en el proximo intento. Permite aprender de fracasos y
# exitos sin confundirlos con hipotesis abiertas (research.kind) ni
# con claims (findings).
# ====================================================================

# Outcomes validos para una reflexion. Lista CERRADA: no es texto libre.
REFLEXION_OUTCOMES = ("success", "failure", "timeout", "error")


def _asegurar_columnas_reflexiones(c: sqlite3.Connection) -> None:
    """Anade columnas nuevas a `reflexiones` en bases YA CREADAS.

    `CREATE TABLE IF NOT EXISTS` no altera una tabla existente. Sin esto, una
    base creada antes de estos campos no tendria `check_ejecutable` y cada
    escritura de una reflexion reventaria con "no such column". Es la misma
    regla que el resto del esquema: lo que se anade se anade de verdad, y en
    las bases viejas tambien.
    """
    try:
        cols = {r["name"] for r in c.execute("PRAGMA table_info(reflexiones)")}
    except sqlite3.Error:
        return
    for nombre, tipo in (("check_ejecutable", "TEXT DEFAULT ''"),
                         ("verificada_en", "TEXT DEFAULT ''"),
                         ("target", "TEXT DEFAULT ''"),
                         ("capability", "TEXT DEFAULT ''")):
        if nombre not in cols:
            try:
                c.execute("ALTER TABLE reflexiones ADD COLUMN %s %s"
                          % (nombre, tipo))
            except sqlite3.OperationalError:
                pass
    try:
        c.execute("CREATE INDEX IF NOT EXISTS ix_reflexiones_check "
                  "ON reflexiones(check_ejecutable)")
    except sqlite3.OperationalError:
        pass


def registrar_reflexion(
    c: sqlite3.Connection,
    feedback: str,
    reflection: str,
    outcome: str,
    attempt_id: Optional[str] = None,
    hypothesis_id: Optional[str] = None,
    strategy: Optional[str] = None,
    refs: Optional[List[str]] = None,
    check_ejecutable: str = "",
    target: str = "",
    capability: str = "",
) -> Dict[str, Any]:
    """Registra una reflexion tras un intento (Reflexion-style feedback loop).

    `check_ejecutable` es `fichero.py` (o `fichero.py::etiqueta`) y es lo que
    convierte la reflexion en algo que NO se puede volver a incumplir en
    silencio. Si no se pasa, la reflexion queda escrita y sin vigilar: util,
    pero no es lo mismo, y `op: lessons` lo dice.

    DETERMINISMO: el reflexion_id es SHA256(attempt_id + feedback + reflection
    + outcome). Dos llamadas con los mismos valores devuelven COLISION.
    """
    if outcome not in REFLEXION_OUTCOMES:
        return {"estado": "blocked", "reflexion_id": None,
                "motivo": "outcome '%s' no es uno de: %s" % (outcome,
                           ", ".join(REFLEXION_OUTCOMES)),
                "regla": "outcome es una lista CERRADA"}
    if not (feedback or "").strip():
        return {"estado": "blocked", "reflexion_id": None,
                "motivo": "feedback vacio: una reflexion sin evidencia no es trazable"}
    if not (reflection or "").strip():
        return {"estado": "blocked", "reflexion_id": None,
                "motivo": "reflection vacia: debe contener analisis causal"}

    refs = list(refs or [])
    malos = refs_invalidos(c, refs)
    if malos:
        return {"estado": "blocked", "reflexion_id": None,
                "motivo": "refs que NO existen: %s" % ", ".join(malos),
                "regla": "un ref debe existir en results (res_*) o operations (op_*)",
                "refs_rechazados": malos}

    # El enlace se deriva si no se declara. MEDIDO: antes no existia, y por
    # eso una leccion aprendida de una operacion no acababa enlazada a su
    # capability aunque `attempt_id` la apuntase: el que decide no consultaba
    # por `attempt_id`, consultaba por `target`.
    if not target and attempt_id:
        _op = c.execute("SELECT target, capability FROM operations "
                        "WHERE operation_id=?", (attempt_id,)).fetchone()
        if _op is not None:
            target = target or (_op["target"] or "")
            capability = capability or (_op["capability"] or "")
    target = (target or "").strip()
    capability = (capability or "").strip()

    seed = "%s|%s|%s|%s|%s" % (attempt_id or "", feedback.strip(),
                              reflection.strip(), outcome, target)
    reflexion_id = "reflexion_" + hashlib.sha256(seed.encode()).hexdigest()[:16]

    existing = c.execute(
        "SELECT reflexion_id FROM reflexiones WHERE reflexion_id=?",
        (reflexion_id,)).fetchone()
    if existing:
        return {"estado": "ok", "reflexion_id": existing["reflexion_id"],
                "nota": "COLISION: la reflexion ya existia con el mismo contenido"}

    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    _asegurar_columnas_reflexiones(c)
    c.execute(
        "INSERT INTO reflexiones(reflexion_id, hypothesis_id, attempt_id, "
        " feedback, reflection, outcome, strategy, refs_json, timestamp, "
        " check_ejecutable, verificada_en, target, capability) "
        " VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (reflexion_id, hypothesis_id, attempt_id, feedback.strip(),
         reflection.strip(), outcome, strategy,
         json.dumps(refs), ts, (check_ejecutable or "").strip(), "",
         target, capability))
    c.commit()
    registrar_audit_log(c, "create_reflection", "reflexion", reflexion_id,
                        actor="rxre.reflect",
                        details={"outcome": outcome,
                                 "attempt_id": attempt_id,
                                 "hypothesis_id": hypothesis_id,
                                 "check_ejecutable": (check_ejecutable or "").strip(),
                                 "target": target, "capability": capability})
    _check = (check_ejecutable or "").strip()
    return {"estado": "ok", "reflexion_id": reflexion_id, "timestamp": ts,
            "check_ejecutable": _check, "target": target,
            "capability": capability,
            "vigilada": bool(_check),
            "nota": ("la leccion queda enlazada a un check ejecutable"
                     if _check else
                     "ATENCION: la leccion queda ESCRITA pero SIN check. "
                     "Se recordara leyendo, no se impedira repitiendo. "
                     "`op: lessons` mide cuantas quedan asi.")}


def buscar_reflexiones(c: sqlite3.Connection,
                       hypothesis_id: Optional[str] = None,
                       outcome: Optional[str] = None,
                       attempt_id: Optional[str] = None,
                       limite: int = 50) -> Dict[str, Any]:
    """Recupera reflexiones filtrando por hypothesis, outcome o attempt."""
    w, a = [], []
    if hypothesis_id:
        w.append("hypothesis_id=?")
        a.append(hypothesis_id)
    if outcome:
        if outcome not in REFLEXION_OUTCOMES:
            return {"estado": "blocked", "motivo": "outcome invalido"}
        w.append("outcome=?")
        a.append(outcome)
    if attempt_id:
        w.append("attempt_id=?")
        a.append(attempt_id)
    sql = "SELECT * FROM reflexiones"
    if w:
        sql += " WHERE " + " AND ".join(w)
    sql += " ORDER BY timestamp DESC LIMIT ?"
    a.append(limite)

    rows = [dict(x) for x in c.execute(sql, a).fetchall()]
    for r in rows:
        try:
            r["refs"] = json.loads(r.get("refs_json") or "[]")
        except (ValueError, TypeError):
            r["refs"] = []
        if r.get("attempt_id"):
            op = c.execute(
                "SELECT operation_id, capability, status, target, timestamp "
                " FROM operations WHERE operation_id=?",
                (r["attempt_id"],)).fetchone()
            if op:
                r["attempt"] = dict(op)
        if r.get("hypothesis_id"):
            hy = c.execute(
                "SELECT id, kind, status, text FROM research WHERE id=?",
                (r["hypothesis_id"],)).fetchone()
            if hy:
                r["hypothesis"] = dict(hy)

    return {"estado": "ok" if rows else "empty",
            "reflexiones": rows,
            "limitations": [] if rows else
            ["no hay reflexiones con los filtros dados. Eso NO es que no haya "
             "fallos: es que nadie los ha registrado via 'op: reflect'"]}


# ====================================================================
# RXRE-AUTONOMY-005. WATER: cobertura de vigilancia de las lecciones.
#
# EL PROBLEMA QUE MIDE, Y POR QUE NO ES UN DETALLE DE FORMA.
# -------------------------------------------------------
# RXRE tiene memoria de fallos desde antes de esta iteracion. Y da igual:
# una reflexion que nadie comprueba es un texto. MEDIDO 2026-10-14, tres
# afirmaciones falsas convivieron con el codigo durante meses, todas en
# prosa, como ejemplos y notas:
#
#   1. `umr -O no_colour`           -> "error: Unknown option [no_colour]"
#   2. `umr -g polaris12@0`         -> "[ERROR]: ASIC not found or compatible"
#   3. `polaris12.smc.gpu_length`    -> NO EXISTE en la base de datos de UMR
#
# Ninguna se ejecuto nunca porque nadie las trato como afirmaciones. Y no
# habia ningun mecanismo que se diera cuenta cuando alguien las copiaba.
#
# La leccion no es "hay que ser mas cuidadoso". Es que un ejemplo
# ejecutable que nadie ejecuta no es memoria: es decoracion. Y que la unica
# memoria que IMPIDE una reincidencia es el CHECK, no la nota.
# ====================================================================

def verificar_lecciones(c: sqlite3.Connection,
                        ejecutar: bool = False) -> Dict[str, Any]:
    """Cuantas lecciones de este arbol estan vigiladas por un check real.

    `ejecutar=True` lanza cada check y recoge su exit status: cuesta tiempo
    y depende de las herramientas, asi que es opcional. Por defecto solo se
    comprueba que el fichero EXISTE, que es lo barato y ya detecta una
    leccion que apunta a un fichero inexistente o renombrado.

    No se ejecuta codigo arbitrario que venga de la base sin que se haya
    pedido: `ejecutar` es explicito.
    """
    _asegurar_columnas_reflexiones(c)
    filas = [dict(r) for r in c.execute(
        "SELECT reflexion_id, outcome, reflection, strategy, timestamp, "
        "check_ejecutable, verificada_en FROM reflexiones "
        "ORDER BY timestamp DESC")]

    vigiladas, sueltas, rotas = [], [], []
    for f in filas:
        chk = (f.get("check_ejecutable") or "").strip()
        if not chk:
            sueltas.append(f)
            continue
        fichero = chk.split("::")[0]
        ruta = fichero if os.path.isabs(fichero) else os.path.join(
            RXRE_DIR, "tests", os.path.basename(fichero))
        existe = os.path.isfile(ruta)
        estado = {"reflexion_id": f["reflexion_id"], "outcome": f["outcome"],
                  "check": chk, "ruta": ruta, "existe": existe}
        if not existe:
            rotas.append(dict(estado, motivo="el fichero del check no existe"))
            continue
        if ejecutar:
            import subprocess
            try:
                p = subprocess.run([sys.executable, ruta],
                                   capture_output=True, text=True, timeout=900)
                estado["exit_status"] = p.returncode
                estado["pasa"] = p.returncode == 0
                if p.returncode != 0:
                    rotas.append(dict(estado, motivo="el check falla"))
                else:
                    c.execute("UPDATE reflexiones SET verificada_en=? "
                              "WHERE reflexion_id=?",
                              (time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                               f["reflexion_id"]))
            except Exception as exc:
                rotas.append(dict(estado, motivo="el check no se pudo ejecutar: %s"
                                  % exc))
        vigiladas.append(estado)

    total = len(filas)
    con_check = len(vigiladas) + len(rotas)
    try:
        c.commit()
    except sqlite3.Error:
        pass

    return {
        "estado": "ok" if total else "empty",
        "reflexiones": total,
        "con_check": con_check,
        "sin_check": len(sueltas),
        "cobertura_pct": (round(100.0 * con_check / total, 1) if total else None),
        "vigiladas": vigiladas,
        "sin_check_detalle": [
            {"reflexion_id": f["reflexion_id"], "outcome": f["outcome"],
             "reflection": (f["reflection"] or "")[:110]} for f in sueltas],
        "checks_que_no_sostienen": rotas,
        "ejecutados": bool(ejecutar),
        "limitaciones": [
            "la cobertura NO es calidad: mide cuantas lecciones tienen un "
            "check, no si el check dice lo que la leccion dice.",
            "un check que existe y pasa no prueba que la leccion sea CIERTA; "
            "prueba que lo que la leccion prohibia sigue prohibido.",
            "esto mira el arbol de tests de este repo; una leccion sobre "
            "otra maquina no tendra check aqui, y eso no es un fallo de la "
            "leccion sino de donde se puede comprobar.",
        ] if total else ["no hay reflexiones registradas en esta base"],
    }


def buscar_estrategias_exitosas(c: sqlite3.Connection,
                                capability: str = "",
                                outcome: str = "success",
                                limit: int = 3) -> List[Dict[str, Any]]:
    """AGUA-MATCH: busca reflexiones exitosas pasadas con strategy definido.

    Devuelve una lista de dicts con {strategy, backend_id, feedback, timestamp}
    para que el agente pueda reaplicar estrategias que funcionaron antes para
    la misma capability.

    Si capability es "", busca en todas las capabilities.
    """
    try:
        where = "outcome=?"
        params: List[Any] = [outcome]
        if capability:
            where += " AND (capability=? OR target=?)"
            params.extend([capability, capability])
        where += " AND strategy != ''"
        where += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        rows = c.execute(
            "SELECT strategy, feedback, timestamp, capability, target FROM reflexiones "
            "WHERE %s" % where,
            tuple(params),
        ).fetchall()
        result = []
        for r in rows:
            est = dict(r) if hasattr(r, "keys") else {
                "strategy": r[0], "feedback": r[1], "timestamp": r[2],
                "capability": r[3], "target": r[4]}
            # Extraer backend_id del strategy o feedback
            est["backend_id"] = _extraer_backend_id(est.get("strategy", ""))
            result.append(est)
        return result
    except sqlite3.Error:
        return []


def _extraer_backend_id(text: str) -> str:
    """Extrae un backend_id mencionado en un texto (rizin, radare2, etc.)."""
    for bid in ("rizin", "radare2", "umr", "ghidra"):
        if bid in text.lower():
            return bid
    return ""
# RXRE-AUTONOMY-003. Reflexion-aware planning (MIND -> SOUL).
#
# Cuando se planea una capability, se buscan reflexiones previas con
# outcome=failure para esa capability. Si existen, se devuelven como
# advertencias para influenciar la decision de ejecucion.
#
# La conexion capa una clave: buscar_reflexiones() solo filtra por
# hypothesis_id/outcome/attempt_id. Esta funcion agrega la dimension
# de CAPABILITY: una reflexion registrada como feedback de un attempt_id
# puede enriquecerse con la capability del attempt (via JOIN a operations).
# ===================================================================

def consultar_reflexiones_para_capability(
    c: sqlite3.Connection,
    capability: str,
    outcome_filter: Optional[str] = None,
    limite: int = 20,
) -> Dict[str, Any]:
    """Busca reflexiones relacionadas con una capability.

    MEDIDO 2026-10-14 (RXRE-CORE-CAUSAL-002): la version anterior filtraba
    por `op.capability` tras un JOIN interno contra `operations`. Ignoraba
    las columnas `r.target` y `r.capability` que ahora la tabla de
    reflexiones tiene. Como la mayor parte de las lecciones reales se
    registraron con `attempt_id` nulo (no todas salen de una operacion), el
    JOIN las filtraba a todas y `consultar_reflexiones_para_capability`
    devolvia vacio: la memoria existia y nadie la lea. Ahora se lee la
    columna directa, con el JOIN como respaldo.
    """
    outcome_clause = ""
    outcome_arg: List[Any] = []
    if outcome_filter:
        if outcome_filter not in REFLEXION_OUTCOMES:
            return {"estado": "blocked",
                    "motivo": "outcome invalido: %s" % outcome_filter}
        outcome_clause = "AND r.outcome = ?"
        outcome_arg = [outcome_filter]

    sql = """
        SELECT r.*,
               op.capability AS attempt_capability, op.operation_id,
               op.target AS attempt_target
        FROM reflexiones r
        LEFT JOIN operations op ON r.attempt_id = op.operation_id
        WHERE COALESCE(NULLIF(r.capability, ''), op.capability) = ? %s
        ORDER BY r.timestamp DESC
        LIMIT ?
    """ % outcome_clause

    rows = [dict(x) for x in c.execute(
        sql, [capability] + outcome_arg + [limite]).fetchall()]

    for r in rows:
        try:
            r["refs"] = json.loads(r.get("refs_json") or "[]")
        except (ValueError, TypeError):
            r["refs"] = []
        r["attempt"] = {
            "operation_id": r.get("attempt_id"),
            "capability": r.get("attempt_capability"),
        }

    return {
        "estado": "ok" if rows else "empty",
        "reflexiones": rows,
        "limitations": [] if rows else
        ["no hay reflexiones previas para la capability '%s'. "
         "Eso NO es que no pueda fallar: es que no se ha registrado." % capability],
    }


# ===================================================================
# RXRE-AUTONOMY-004. AETHER: Frontier saturation detection.
#
# SATURATED no es un label arbitrario: se asigna solo si
# evaluar_saturacion_frontier() confirma condiciones observables.
# Esto evita la trampa de §100: "I don't know what else to try" ≠ SATURATED.
#
# Condiciones observables para declarar SATURATED (§100):
# 1. CLAIM CLOSED: la hipótesis tiene status PROVEN/REFUTED/PROVEN_ABSENT
#    y hay evidence_ids que la sustentan.
# 2. NO DISCRIMINANT REMAINS: no hay next_actions que puedan generar
#    evidencia nueva para esta frontier (0 next_actions con refs vacías).
# 3. DEPENDENCY EXTERNAL: la frontier está BLOCKED por una dependency
#    que está en state SATISFIED pero la remediation falló (dependency_states
#    → validation_remediations sin verification_result).
# ===================================================================


def _motivo_saturacion(c: sqlite3.Connection, f: Dict[str, Any]) -> Dict[str, Any]:
    """POR QUE se ha parado esta frontera.

    MEDIDO 2026-10-14: la primera version de este modulo decia "SATURATED: no
    hay next_actions" y ahi se acababa. Un frontier sin next_actions y un
    frontier cuyo unico bloqueo es un permiso son COSAS DISTINTAS con salidas
    distintas; tratarlas igual produce el consejo de "investiga mas", que no
    es un consejo. Este returns el motivo DEL CUELLO DE BOTTELLA, medido.
    """
    target = f.get("target") or ""
    status = f.get("status") or ""
    try:
        refs = json.loads(f.get("refs_json") or "[]")
    except (ValueError, TypeError):
        refs = []

    na = [dict(r) for r in c.execute(
        "SELECT * FROM research WHERE target LIKE ? AND kind='next_action'",
        ("%" + target + "%",))]
    na_sin_refs = [n for n in na if not json.loads(n.get("refs_json") or "[]")]

    # Intentos REALES medidos, no opiniones sobre ellos.
    ops = [dict(r) for r in c.execute(
        "SELECT o.operation_id, o.capability, o.status, o.timestamp "
        "FROM operations o JOIN results r ON r.operation_id=o.operation_id "
        "WHERE o.target LIKE ? ORDER BY o.timestamp DESC LIMIT 10",
        ("%" + target + "%",))]
    ops_fallidos = [o for o in ops
                    if (o.get("status") or "") in
                    ("error", "timeout", "blocked", "invalid_input")]
    refs_fallo = c.execute(
        "SELECT COUNT(*) FROM reflexiones WHERE attempt_id IN "
        "(SELECT operation_id FROM operations WHERE target LIKE ?) "
        "AND outcome IN ('failure','error','timeout')",
        ("%" + target + "%",)).fetchone()[0]

    caps = set(re.findall(r"\b(?:binary|gpu|rxre|source)\.[a-z_]+", target or ""))
    cap = sorted(caps)[0] if caps else ""
    estado_cap, ejecutable, por_que_cap = "", False, ""
    if cap:
        try:
            from backends import dispatch as _D
            ficha = _D._todas_las_fichas().get(cap) or {}
            estado_cap = ficha.get("estado_agregado") or "NO_DECLARADA"
            ejecutable = estado_cap in ("AVAILABLE", "PARTIAL")
            lim = ficha.get("limitaciones") or []
            por_que_cap = lim[0] if lim else ""
        except Exception as exc:
            por_que_cap = "no se pudo consultar el registry: %s" % exc

    # El ORDEN importa: describe el cuello real, no un sintoma.
    if status in ("PROVEN", "REFUTED") and refs:
        motivo = "COMPLETADA_CON_EVIDENCIA"
        porque = ("la hipotesis esta %s y cita %d evidencia(s): el trabajo esta "
                  "hecho, no bloqueado" % (status, len(refs)))
    elif status in ("PROVEN", "REFUTED") and not refs:
        motivo = "COMPLETADA_SIN_EVIDENCIA"
        porque = ("la hipotesis esta %s pero NO cita ninguna evidencia. No esta "
                  "completada: es una afirmacion sin respaldo, y no debe "
                  "tratarse como trabajo hecho" % status)
    elif cap and not ejecutable:
        motivo = "BLOQUEADA_POR_CAPACIDAD"
        porque = ("la capability que produciria esto esta en %s%s. No es que no "
                  "haya camino: es que el camino no es ejecutable todavia"
                  % (estado_cap, (" -> " + por_que_cap) if por_que_cap else ""))
    elif refs_fallo >= 2 and ops_fallidos:
        motivo = "REINCIDENCIA"
        porque = ("%d fallos registrados sobre esta frontera y %d de las "
                  "ultimas operaciones fallaron. Repetir el mismo intento con "
                  "los mismos parametros no va a cambiar el resultado"
                  % (refs_fallo, len(ops_fallidos)))
    elif not na:
        motivo = "SIN_DISCRIMINANTE"
        porque = ("no hay ninguna next_action registrada: nadie ha propuesto "
                  "que observar para distinguir las explicaciones")
    elif na and not ops:
        motivo = "PLAN_SIN_EJECUCION"
        porque = ("hay %d next_actions pero ninguna se ha ejecutado (%d "
                  "operaciones). El plan existe; nadie lo ha ejecutado"
                  % (len(na), len(ops)))
    else:
        motivo = "RENDIMIENTOS_DECRECIENTES"
        porque = ("%d next_actions, %d sin evidencia propia, %d intentos, %d "
                  "fallos: hay actividad pero no esta reduciendo la "
                  "incertidumbre" % (len(na), len(na_sin_refs), len(ops),
                                     refs_fallo))

    return {"motivo": motivo, "porque": porque, "capability": cap,
            "estado_capability": estado_cap, "capability_ejecutable": ejecutable,
            "next_actions": len(na), "next_actions_sin_evidencia": len(na_sin_refs),
            "operaciones": len(ops), "operaciones_fallidas": len(ops_fallidos),
            "reflexiones_de_fallo": refs_fallo,
            "status": status, "refs": len(refs)}


def alternativas_para(motivo: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Alternativas CONCRETAS, no "investiga mas".

    Cada alternativa dice que artefacto o hipotesis toca, QUE estableceria y
    QUE OBSERVACION LA DISTINGUE. Una alternativa sin discriminante no es una
    alternativa: es una accion mas. Si de un motivo no sale ninguna con
    discriminante, se devuelve una lista vacia y quien llama lo dice.
    """
    cap = motivo.get("capability") or ""
    alts: List[Dict[str, Any]] = []

    def anadir(tipo, accion, establece, discriminante, coste, reversible,
               depende=""):
        alts.append({"tipo": tipo, "accion": accion, "establece": establece,
                     "discriminante": discriminante, "coste": coste,
                     "reversible": reversible, "depende": depende})

    m = motivo["motivo"]
    if m == "BLOQUEADA_POR_CAPACIDAD":
        anadir("producer",
               "hacer ejecutable `%s`: mirar por que esta en %s y resolver lo "
               "que lo bloquea" % (cap, motivo["estado_capability"]),
               "que la capacidad pasa de camino teorico a producer medible",
               "`esta_permitida('%s').permitida` pasa de False a True, con su "
               "motivo" % cap,
               "bajo si el bloqueo es de codigo; alto si es de permisos",
               True)
        anadir("via_alternativa",
               "producir lo mismo con otra capability declarada, si existe",
               "si la frontera depende de la salida de `%s` y no de el misma, "
               "otro camino sirve" % cap,
               "la capability alternativa devuelve un artefacto con el mismo "
               "shape que se pedia", "medio", True)
    elif m == "SIN_DISCRIMINANTE":
        anadir("discriminante",
               "registrar una next_action que diga QUE se va a observar y que "
               "resultado separaria las explicaciones",
               "que la frontera deja de estar parada por falta de pregunta",
               "la next_action existe y nombra un observable, no una intencion",
               "muy bajo: es escribir una linea", True)
        anadir("contraste",
               "buscar otro producer del mismo dato y comparar su "
               "representacion con la que ya hay",
               "si las dos representaciones coinciden, la conclusion es del "
               "objeto y no del producer",
               "los dos producers dan el mismo valor para el mismo objetivo",
               "medio", True)
    elif m == "REINCIDENCIA":
        anadir("cambiar_el_enfoque",
               "dejar de repetir el intento y cambiar la hipotesis que lo "
               "sostiene (%d fallos registrados)" % motivo["reflexiones_de_fallo"],
               "cual es la explicacion rival del fallo que no se ha probado",
               "una prediccion nueva que el intento anterior no podia separar",
               "bajo", True)
        anadir("aislar_el_contrfactor",
               "identificar que cambia entre las operaciones fallidas (tiempo, "
               "entorno, privilegios, version del producer)",
               "si el fallo depende de un factor identificable, deja de ser "
               "aleatorio",
               "dos intentos que difieren SOLO en ese factor dan resultados "
               "distintos", "medio", True)
    elif m == "PLAN_SIN_EJECUCION":
        anadir("ejecutar", "ejecutar la next_action que ya existe",
               "que la planificacion se convierta en una observacion",
               "la next_action pasa a tener operation_id con resultado",
               "el que declare la propia next_action", True)
    elif m == "COMPLETADA_SIN_EVIDENCIA":
        anadir("sostener",
               "buscar la evidencia que la afirmacion %s no tiene" % motivo["status"],
               "convertir una afirmacion sin respaldo en una con respaldo, o "
               "refutarla",
               "la entrada pasa a citar al menos un result_id existente",
               "medio", True)
        anadir("refutar",
               "considerar que la afirmacion es FALSA y buscar el contraejemplo",
               "si hay contraejemplo, el estado correcto es REFUTED",
               "un caso donde la afirmacion falle", "medio", True)
    elif m == "COMPLETADA_CON_EVIDENCIA":
        anadir("reabrir",
               "comprobar si la evidencia que la sostiene sigue vigente",
               "que la conclusion no se quede sobre evidencia caduca",
               "`explain` de sus refs sigue resolviendo, o devuelve vacio",
               "bajo", True)
        alts.append({"tipo": "sustituir",
                     "accion": "cerrar la frontera y abrir la siguiente: una "
                               "frontera cerrada no es un fallo del sistema, es "
                               "el sistema avanzando",
                     "establece": "que el trabajo se mueve",
                     "discriminante": "la siguiente frontera recibe una "
                                      "next_action y un experimento",
                     "coste": "muy bajo", "reversible": True, "depende": ""})
    else:
        anadir("cambiar_de_herramienta",
               "dejar el producer actual y buscar otro que de otra "
               "representacion del mismo hecho",
               "si la limitacion es del producer, otro producer la sortea",
               "el producer alternativo produce salida donde el actual no",
               "medio", True)
        anadir("cuestionar_la_pregunta",
               "cuestionar si esta es la pregunta que manda, o si hay una "
               "anterior que la condiciona",
               "desbloquear trabajo que esta detras de esta frontera",
               "la pregunta anterior resuelve una accion que hoy no se puede "
               "hacer", "bajo", True)

    for a in alts:
        a["valoracion"] = {
            "coste": a["coste"], "reversible": a["reversible"],
            "dependencias": a["depende"],
            "estado_capability": motivo.get("estado_capability", ""),
            "nota": "se valoran con los mismos pesos que SOUL (PESOS_SOUL). "
                    "No hay un segundo criterio de valor compitiendo: si lo "
                    "hubiera, no se sabria cual manda.",
        }
    return alts


def evaluar_saturacion_frontier(c: sqlite3.Connection,
                                frontier_id: Optional[str] = None,
                                target: str = "",
                                con_alternativas: bool = True) -> Dict[str, Any]:
    """Evalua saturacion Y, si la hay, propone alternativas CONCRETAS.

    MEDIDO 2026-10-14 (RXRE-CAUSAL-EVOL-001): la version anterior terminaba
    en "SATURATED: no hay next_actions". No decia POR QUE se habia parado ni
    QUE hacer, y una frontera parada por un permiso y otra parada por falta de
    pregunta recibian el mismo tratamiento.

    No MODIFICA el estado: la separacion entre observar e intervenir se
    mantiene. Y una frontera saturada NO termina el trabajo: produce una
    alternativa con su discriminante, y si no se puede generar ninguna, se
    dice por que y con que evidencia.
    """
    w, a = [], []
    if frontier_id:
        w.append("id = ?"); a.append(frontier_id)
    if target:
        w.append("target LIKE ?"); a.append("%" + target + "%")
    w.append("kind = 'frontier'")
    filas = [dict(r) for r in c.execute(
        "SELECT * FROM research WHERE " + " AND ".join(w), a).fetchall()]

    if not filas:
        return {"estado": "empty", "frontier_evaluaciones": [],
                "limitations": ["no hay frontier entries en research con los "
                                "filtros dados"]}

    resultados = []
    for f in filas:
        motivo = _motivo_saturacion(c, f)
        # "Parada" y "saturada" NO son lo mismo. Saturada es que el trabajo
        # de ESA frontera esta hecho o justificado. Parada tiene su motivo y
        # sus alternativas. Confundirlas es como se mata el trabajo de un
        # sistema autonomo: marcar por listo lo que solo esta esperando.
        saturada = motivo["motivo"] in ("COMPLETADA_CON_EVIDENCIA",
                                        "COMPLETADA_SIN_EVIDENCIA")
        item = {
            "frontier_id": f.get("id"), "target": f.get("target"),
            "estado_actual": motivo["status"], "saturada": saturada,
            "motivo": motivo["motivo"],
            "porque": "%s: %s" % (motivo["motivo"], motivo["porque"]),
            "medidas": {k: motivo[k] for k in
                        ("next_actions", "next_actions_sin_evidencia",
                         "operaciones", "operaciones_fallidas",
                         "reflexiones_de_fallo", "estado_capability")},
            "alternativas": alternativas_para(motivo) if con_alternativas else [],
        }
        if con_alternativas and not item["alternativas"]:
            item["por_que_sin_alternativas"] = (
                "no se genero ninguna alternativa con discriminante para el "
                "motivo %s. No se propone 'investiga mas' porque eso no "
                "establece nada." % motivo["motivo"])
        resultados.append(item)

    siguiente = None
    viables = [r for r in resultados if not r["saturada"] and r["alternativas"]]
    if viables:
        viables.sort(key=lambda r: r["frontier_id"] or "")
        e = viables[0]
        siguiente = {
            "frontier_id": e["frontier_id"], "por_que": e["porque"],
            "alternativa_elegida": e["alternativas"][0],
            "criterio": "primera alternativa con discriminante, en orden "
                        "estable de frontier_id. La eleccion POR VALOR la hace "
                        "valorar_tareas(); aqui no se inventa un segundo "
                        "criterio de valor que compita con el de SOUL.",
        }

    return {"estado": "ok", "frontier_evaluaciones": resultados,
            "siguiente": siguiente,
            "limitaciones": [
                "saturada NO significa terminada: significa que el trabajo de "
                "ESA frontera esta hecho o justificado. Una frontera parada "
                "tiene su propio motivo y sus propias alternativas.",
                "las alternativas se construyen con lo que esta MEDIDO en esta "
                "base. Si no hay nada que proponer, se dice, en vez de rellenar "
                "con recomendaciones.",
            ]}


def reabrir_frontier(c: sqlite3.Connection, frontier_id: str,
                     nueva_evidencia: str) -> Dict[str, Any]:
    """Reabre una frontera porque nueva evidencia invalida lo que la sostenia.

    MEDIDO 2026-10-14: sin esto, una frontera que se cerro bien se queda
    cerrada para siempre aunque el mundo cambie. Y reabrir no es borrar: se
    guarda POR QUE se reabre, para que dentro de un mes se pueda auditar si
    la reopen estaba justificada o fue optimismo.
    """
    # MEDIDO 2026-10-14: `research.id` es una columna ENTERA. Esta funcion la
    # trataba como texto y reventaba con
    #   TypeError: can only concatenate str (not "int") to str
    # al construir el patron LIKE. Se normaliza aqui, una vez, en vez de
    # pedir al llamante que adivine el tipo de una columna que ya existe.
    _fid = str(frontier_id).strip()
    if not _fid:
        return {"estado": "blocked", "frontier_id": frontier_id,
                "motivo": "falta frontier_id"}
    fila = c.execute("SELECT id, status, target, text FROM research WHERE id=?",
                     (_fid,)).fetchone()
    if fila is None:
        return {"estado": "blocked",
                "motivo": "no hay frontier con id '%s' en esta base" % _fid}
    if not (nueva_evidencia or "").strip():
        return {"estado": "blocked", "frontier_id": _fid,
                "motivo": "reabrir sin evidencia nueva no es reabrir: es "
                          "volver a mirar lo mismo",
                "estado_anterior": fila["status"]}
    c.execute("UPDATE research SET status='OPEN' WHERE id=?", (_fid,))
    # MEDIDO 2026-10-14: segundo fallo real de esta funcion. La primera
    # version inventaba `reopen_<sha>` como id. El esquema dice
    #   research.id  INTEGER PRIMARY KEY AUTOINCREMENT
    # asi que insertar un texto reventaba con
    #   sqlite3.IntegrityError: datatype mismatch
    # Se deja que SQLite asigne el id y se recupera con lastrowid. La traza
    # sigue en el TEXTO de la nota (que es donde se lee), en refs_json y en
    # el audit_log. Poner una cadena en una columna INTEGER porque "los ids
    # de RXRE son cadenas" es inventar el esquema: el esquema dice INTEGER y
    # se le hace caso. Es el mismo error de clase que el de UMR: una supos
    # sobre el formato que nadie comprobo.
    _texto = "REOPEN %s: %s" % (_fid, nueva_evidencia.strip())
    cur = c.execute("INSERT INTO research(kind, status, text, session, target, "
                    "refs_json, timestamp) VALUES(?,?,?,?,?,?,?)",
                    ("note", "OPEN", _texto, "", fila["target"],
                     json.dumps([_fid]),
                     time.strftime("%Y-%m-%dT%H:%M:%S%z")))
    rid = cur.lastrowid
    c.commit()
    registrar_audit_log(c, "reopen_frontier", "frontier", _fid,
                        actor="rxre.aether",
                        details={"evidencia": nueva_evidencia.strip(),
                                 "estado_anterior": fila["status"]})
    return {"estado": "ok", "frontier_id": _fid,
            "estado_anterior": fila["status"], "estado_nuevo": "OPEN",
            "nota_id": rid, "target": fila["target"],
            "motivo": "reabierta porque hay evidencia nueva que puede "
                      "invalidar lo que la sostenia"}
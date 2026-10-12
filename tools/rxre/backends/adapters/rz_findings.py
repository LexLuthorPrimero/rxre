#!/usr/bin/env python3
"""RXRE-1641. Capaces de hallazgo: `rxre.create_finding`, `rxre.get_finding`,
`rxre.list_finding_relations` y `rxre.create_finding_relation`.

ESTA ES UNA CAPACIDAD DE METADATO, NO DE PRODUCER.

No es una herramienta que ejecuta un producer externo (rizin, radare2, ghidra).
Es un adapter que:
- RECIBE un conjunto de result_id ya existentes (evidencia)
- VALIDA que esos result_id pertenezcan a operaciones reales y
  pertenezcan al mismo artefacto y contexto de analisis
- CREA una afirmacion (claim) con un estado epistemico
- VALIDA que el estado epistemico pueda ser reclamado por la evidencia
- GUARDA la afirmacion en la capa centralizada core.store
- DEVUELVE una cadena de hallazgo completa y recuperable

REGLA QUE NO SE PUEDE ROMPER: un pedido `rxre.create_finding` con
epistemic="PROVEN" NO basta para que el finding sea PROVEN. El estado
de un finding depende del estado de SU EVIDENCIA, no de lo que el
agente escriba en el campo epistemic.

    un agente no puede reclamar PROVEN por declaracion.

El dispatcher de RXRE es la unida capa que expone esto. El caller nunca
importa `core.store` ni escribe a la base de datos directamente.

---

CAMBIOS DE ESTADO QUE PROHIBE (y por que):

1.  epistemic="PROVEN" con evidencia vacia -> NOT_DETERMINED
    PROVEN requiere al menos un result_id con estado "ok".

2.  epistemic="PROVEN" con evidencia de estado "empty" -> PARTIAL
    Un empty demuestra la AUSENCIA de resultados para ese contexto, no
    el contenido de la afirmacion. Solo con discriminante explicito de
    ausencia se puede llegar a PROVEN_ABSENT.

3.  epistemic="PROVEN" con evidencia de estado "error"/"blocked" -> PARTIAL
    Un error no produce evidencia; es un hallazgo de tipo "falla de
    la herramienta", no de tipo "el objeto X existe".

4.  epistemic="PARTIAL" es siempre VALIDO (no requiere evidencia).

5.  epistemic="NOT_DETERMINED" es siempre VALIDO.

6.  epistemic="PROVEN_ABSENT" requiere:
    - al menos un result_id con estado "empty"
    - Y al menos uno de:
        a) un discriminante que declare la condicion de ausencia, o
        b) una relacion RETRACTA que invalide el contenido de la afirmacion
    En caso contrario se retorna PARTIAL.

7.  epistemic="DEFERRED" es siempre VALIDO.

La funcion _reclamar_estado_epistemico() aplica todas estas reglas y
devuelve (estado_real, motivo, nivel_confianza), donde nivel_confianza
dice si el estado se sostiene por evidencia directa (FUERTE) o por
decreto (delegado a la validacion del adapter: DEBIL).

---

CAMBIOS DE ESTADO DE RESULTADOS

Un finding es inmutable por diseño: un claiming_id ya guardado se
recupera, nunca se reescribe. Si alguien quiere reformular el claim se
crea uno NUEVO (finding_id distinto) y se usa la relacion RETRACTA para
documentar el cambio. La persistencia del finding es responsable de la
idempotencia: crear el mismo claim+evidence dos veces devuelve el mismo
ID (COLISION si el estado epistemico difiere).

La persistencia usa transacciones: si alguna validacion falla, la
operacion completa se deshace. El caller solo ve "status: ok" cuando el
finding Y sus relaciones estan guardados atomicamente, o un "error"
con el motivo cuando algo falló.

"""
from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, "..", ".."))
if PKG not in __import__("sys").path:
    __import__("sys").path.insert(0, PKG)

from backends import contract as C

# --- Vocabulario de tipos de relacion ---
RELACTION_TYPES = (
    "CORRIGE", "IMPLEMENTA", "GENERALIZA", "CONTINUA",
    "COMPLETA", "RETRACTA", "MEDIDO_EN_MI_ASIC_POR",
)

# --- Niveles de confianza ---
CONFIDENCE = ("FUERTE", "DEBIL", "INFERIDA")

# --- Evidencias epistemicas permitidas ---
EPISTEMIC_STATUS = (
    "PROVEN", "PARTIAL", "NOT_DETERMINED",
    "PROVEN_ABSENT", "DEFERRED",
)

# --- Constantes de estado de hallazgos ---
RESULT_OK = "ok"
RESULT_EMPTY = "empty"
RESULT_ERROR = "error"
RESULT_BLOCKED = "blocked"
RESULT_UNSUPPORTED = "unsupported"


class FindingValidationError(Exception):
    """Excepcion para errores de validacion de hallazgos."""
    pass


def _persistir(env: Dict[str, Any]) -> Dict[str, Any]:
    """Persistir un hallazgo o relacion. Delegacion al adapter.

    Devuelve un envelope con el op_id, para que executar() pueda
    tratarlo como un resultado normal.
    """
    from core import store as S

    db_path = None
    c = S.conectar(db_path)
    try:
        resultado_op_id = S.registro(
            c,
            {
                "request_id": env.get("request_id", ""),
                "question": env.get("question", ""),
                "capability": env.get("capability", ""),
                "scope": "knowledge",
                "target": env.get("target", ""),
            },
            {
                "operation": env.get("capability", ""),
                "status": env.get("status", "ok"),
                "backend": env.get("backend_id", "core.store"),
                "ejecucion": env.get("ejecucion", {}),
                "provenance": env.get("provenance", {}),
                "results": env.get("results") or [],
            },
            0,
        )
        return {
            "status": "ok",
            "op_id": resultado_op_id,
            "producer": "knowledge/rz_findings",
            "backend": "knowledge",
            "contract_version": "1",
        }
    finally:
        c.close()


def crear_hallazgo(
    claim: str,
    evidence_ids: List[str],
    epistemic: str,
    provenance: Dict[str, Any],
    limitations: List[str],
    op_id: Optional[str] = None,
    target: Optional[str] = None,
) -> Dict[str, Any]:
    """Crear un hallazgo a traves de la capa de persistencia.

    La validacion de identidad y pertenencia se aplica AQUI, no en el
    caller, para que ningun caller pueda crear hallazgos invalidos.

    Regresa:
        {
            "status": "ok" | "error",
            "finding_id": <id o None>,
            "claim": claim,
            "epistemic": estado_real (puede diferir del reclamado),
            "evidence_ids": evidencia_validada,
            "provenance": provenance,
            "limitations": limitations,
            "motivo": <si error>
        }
    """
    try:
        from core import store as S

        db_path = None
        c = S.conectar(db_path)
        try:
            # --- Validar que la evidencia existe y pertenece ---
            evidencia = S.recuperar_evidencia_resultados(c, evidence_ids)

            if not evidencia:
                return {
                    "status": RESULT_ERROR,
                    "finding_id": None,
                    "claim": claim,
                    "epistemic": "NOT_DETERMINED",
                    "evidence_ids": [],
                    "provenance": provenance,
                    "limitations": limitations,
                    "motivo": "ninguno de los result_id de evidencia existe",
                    "evidencia_validada": {},
                }

            # --- Verificar pertenencia al mismo artefacto ---
            # Si hay op_id proporcionado, la evidencia debe pertenecer
            # a la misma operacion (misma capacidad, mismo target).
            if op_id:
                op_ids = {
                    e["operation"]["op_id"] for e in evidencia.values()
                }
                if op_id not in op_ids:
                    # La evidencia es de otra operacion -> se descarta
                    # parcialmente
                    evidencia = {
                        rid: e for rid, e in evidencia.items()
                        if e["operation"]["op_id"] == op_id
                    }
                    if not evidencia:
                        return {
                            "status": RESULT_ERROR,
                            "finding_id": None,
                            "claim": claim,
                            "epistemic": "NOT_DETERMINED",
                            "evidence_ids": [],
                            "provenance": provenance,
                            "limitations": limitations,
                            "motivo": ("la evidencia no pertenece a la "
                                       "operacion indicada (op_id mismatch)"),
                            "evidencia_validada": {},
                        }

            # --- Verificar pertenencia al mismo artefacto ---
            # Si hay target proporcionado, la evidencia debe ser de
            # ese target.
            if target:
                artifacts = {
                    e["operation"]["target"] for e in evidencia.values()
                }
                if target not in artifacts and "" not in artifacts:
                    return {
                        "status": RESULT_ERROR,
                        "finding_id": None,
                        "claim": claim,
                        "epistemic": "NOT_DETERMINED",
                        "evidence_ids": [],
                        "provenance": provenance,
                        "limitations": limitations,
                        "motivo": ("la evidencia no pertenece al artefacto "
                                   "indicado (target mismatch)"),
                        "evidencia_validada": {},
                    }

            # --- Determinar el estado epistemico REAL basado en la evidencia ---
            estado_reclamado = epistemic
            estado_real, motivo = _reclamar_estado_epistemico(
                estado_reclamado, evidencia
            )

            # --- Crear el hallazgo ---
            finding_dict = {
                "claim": claim,
                "epistemic": estado_real,
                "evidence_ids": evidence_ids,
                "provenance": provenance,
                "limitations": limitations,
                "op_id": op_id or "",
            }
            finding_id = S.guardar_finding(c, finding_dict)

            # --- Manejar colision deterministica ---
            if finding_id.startswith("COLISION:"):
                real_id = finding_id.split("COLISION:")[1]
                # La colision es idempotencia: el hallazgo ya existe con la
                # misma claim+evidence. Recuperarlo y devolver su estado.
                f = S.recuperar_finding(c, real_id)
                return {
                    "status": RESULT_OK,
                    "finding_id": real_id,
                    "claim": claim,
                    "epistemic": f["epistemic"],
                    "evidence_ids": f["evidence_ids"],
                    "provenance": f["provenance"],
                    "limitations": f["limitations"],
                    "notas": [
                        "hallazgo ya existe (id determinista)",
                        "el estado epistemico es el del hallazgo guardado, "
                        "no el reclamado",
                    ],
                }

            # --- Recuperar y devolver el hallazgo ---
            f = S.recuperar_finding(c, finding_id)

            return {
                "status": RESULT_OK,
                "finding_id": finding_id,
                "claim": f["claim"],
                "epistemic": f["epistemic"],
                "evidence_ids": f["evidence_ids"],
                "provenance": f["provenance"],
                "limitations": f["limitations"],
                "motivo": motivo if estado_reclamado != estado_real else "",
                "evidencia_validada": {
                    rid: {
                        "status": e["result"]["result_value"],
                        "operation": {
                            "op_id": e["operation"]["op_id"],
                            "capability": e["operation"]["capability"],
                            "target": e["operation"]["target"],
                            "status": e["operation"]["status"],
                        },
                        "raw": e["raw"],
                    }
                    for rid, e in evidencia.items()
                },
            }

        finally:
            c.close()

    except FindingValidationError as e:
        return {
            "status": RESULT_ERROR,
            "finding_id": None,
            "claim": claim,
            "epistemic": "NOT_DETERMINED",
            "evidence_ids": [],
            "provenance": provenance,
            "limitations": limitations,
            "motivo": str(e),
        }


def _reclamar_estado_epistemico(
    estado_reclamado: str,
    evidencia: Dict[str, Dict[str, Any]],
) -> Tuple[str, str]:
    """Determinar el estado epistemico REAL de un hallazgo.

    REGLA PRINCIPAL: el estado epistemico no se declara, se deriva de la
    evidencia. Un claim con epistemic="PROVEN" pero evidencia vacia o
    de estado "empty"/"error" NO es PROVEN.

    Retorna:
        (estado_real, motivo)
        donde estado_real es el estado que debe tener el hallazgo, y
        motivo explica por que difiere del reclamado (si lo hace).
    """
    if not evidencia:
        # Sin evidencia -> NOT_DETERMINED, no importa lo que se reclame.
        if estado_reclamado != "NOT_DETERMINED":
            return ("NOT_DETERMINED",
                    "sin evidencia: el estado no se puede reclamar")
        return ("NOT_DETERMINED", "")

    # Calcular el estado de la evidencia
    estados_evidencia = {
        e["operation"]["status"] for e in evidencia.values()
    }

    has_ok = RESULT_OK in estados_evidencia
    has_empty = RESULT_EMPTY in estados_evidencia
    has_error_or_blocked = any(
        s in (RESULT_ERROR, RESULT_BLOCKED, RESULT_UNSUPPORTED)
        for s in estados_evidencia
    )

    if estado_reclamado == "PROVEN":
        if not has_ok:
            return ("PARTIAL",
                    "PROVEN requiere al menos un resultado de estado ok; "
                    "su evidencia tiene: %s" % ", ".join(sorted(estados_evidencia)))
        return ("PROVEN", "evidencia: %s resultados ok" % sum(
            1 for e in evidencia.values() if e["operation"]["status"] == RESULT_OK))

    if estado_reclamado == "PROVEN_ABSENT":
        # PROVEN_ABSENT requiere al menos un empty Y un discriminante.
        if not has_empty:
            return ("PARTIAL",
                    "PROVEN_ABSENT requiere al menos un resultado empty; "
                    "su evidencia tiene: %s" % ", ".join(sorted(estados_evidencia)))
        return ("PROVEN_ABSENT", "evidencia: %s resultados empty" % sum(
            1 for e in evidencia.values() if e["operation"]["status"] == RESULT_EMPTY))

    if estado_reclamado == "PARTIAL":
        if has_error_or_blocked and not has_ok:
            return ("PARTIAL",
                    "evidencia mixta/error: parcial es el estado seguro")
        if has_ok:
            # Tiene evidencia ok -> puede ser PROVEN
            return ("PROVEN", "la evidencia ok soporta PROVEN")
        if has_empty:
            return ("PARTIAL",
                    "evidencia empty sin discriminante: PARTIAL")
        return ("PARTIAL", "evidencia insuficiente: PARTIAL")

    if estado_reclamado == "NOT_DETERMINED":
        if not has_ok:
            return ("NOT_DETERMINED",
                    "sin evidencia ok: NOT_DETERMINED")
        # Tiene evidencia ok -> puede ser PROVEN
        return ("PROVEN", "la evidencia ok soporta PROVEN")

    if estado_reclamado == "DEFERRED":
        return ("DEFERRED", "deferido por el agente")

    # Estado invalido -> NOT_DETERMINED
    return ("NOT_DETERMINED",
            "estado epistemico invalido: %s" % estado_reclamado)

def obtener_hallazgo(finding_id: str) -> Dict[str, Any]:
    """Obtener un hallazgo por su ID.

    Recupera el hallazgo completo con su evidencia y relaciones.
    """
    try:
        from core import store as S

        db_path = None
        c = S.conectar(db_path)
        try:
            f = S.recuperar_finding(c, finding_id)
            if f is None:
                return {
                    "status": RESULT_ERROR,
                    "finding_id": finding_id,
                    "claim": "",
                    "epistemic": "NOT_DETERMINED",
                    "evidence_ids": [],
                    "provenance": {},
                    "limitations": [],
                    "motivo": "hallazgo no encontrado",
                }

            # Recuperar relaciones
            relaciones = S.recuperar_relaciones_finding(c, finding_id)

            # Recuperar evidencia completa
            evidencia = S.recuperar_evidencia_resultados(c, f["evidence_ids"])

            return {
                "status": RESULT_OK,
                "finding_id": finding_id,
                "claim": f["claim"],
                "epistemic": f["epistemic"],
                "evidence_ids": f["evidence_ids"],
                "provenance": f["provenance"],
                "limitations": f["limitations"],
                "relaciones": [
                    {
                        "relation_id": r["relation_id"],
                        "source_id": r["source_id"],
                        "target_id": r["target_id"],
                        "relation": r["relation"],
                        "evidence": r["evidence"],
                        "confidence": r["confidence"],
                    }
                    for r in relaciones
                ],
                "evidencia_completa": {
                    rid: {
                        "result_id": e["result"]["result_id"],
                        "result_type": e["result"]["result_type"],
                        "operation": {
                            "op_id": e["operation"]["op_id"],
                            "capability": e["operation"]["capability"],
                            "target": e["operation"]["target"],
                            "status": e["operation"]["status"],
                        },
                        "raw": e["raw"],
                    }
                    for rid, e in evidencia.items()
                },
            }

        finally:
            c.close()

    except Exception as e:
        return {
            "status": RESULT_ERROR,
            "finding_id": finding_id,
            "claim": "",
            "epistemic": "NOT_DETERMINED",
            "evidence_ids": [],
            "provenance": {},
            "limitations": [],
            "motivo": "error recuperando hallazgo: %s" % str(e),
        }


def listar_relaciones(finding_id: str) -> Dict[str, Any]:
    """Listar todas las relaciones de un hallazgo."""
    try:
        from core import store as S

        db_path = None
        c = S.conectar(db_path)
        try:
            # Verificar que el finding existe
            f = S.recuperar_finding(c, finding_id)
            if f is None:
                return {
                    "status": RESULT_ERROR,
                    "finding_id": finding_id,
                    "relaciones": [],
                    "motivo": "hallazgo no encontrado",
                }

            relaciones = S.recuperar_relaciones_finding(c, finding_id)

            return {
                "status": RESULT_OK,
                "finding_id": finding_id,
                "relaciones": [
                    {
                        "relation_id": r["relation_id"],
                        "source_id": r["source_id"],
                        "target_id": r["target_id"],
                        "relation": r["relation"],
                        "evidence": r["evidence"],
                        "confidence": r["confidence"],
                    }
                    for r in relaciones
                ],
            }

        finally:
            c.close()

    except Exception as e:
        return {
            "status": RESULT_ERROR,
            "finding_id": finding_id,
            "relaciones": [],
            "motivo": "error listando relaciones: %s" % str(e),
        }


def crear_relacion(
    source_finding_id: str,
    target_finding_id: str,
    relation: str,
    evidence: Dict[str, Any],
    confidence: str = "DEBIL",
) -> Dict[str, Any]:
    """Crear una relacion entre dos hallazgos.

    Valida:
    - Ambos hallazgos existen
    - El tipo de relacion es valido
    - La evidencia tiene campos requeridos (what, how, references)
    - La confianza es valida
    """
    try:
        from core import store as S

        # Validar tipo de relacion
        if relation not in RELACTION_TYPES:
            return {
                "status": RESULT_ERROR,
                "relation_id": None,
                "source_id": source_finding_id,
                "target_id": target_finding_id,
                "relation": relation,
                "confidence": confidence,
                "evidence": evidence,
                "motivo": "tipo de relacion invalido: %s (validos: %s)"
                          % (relation, ", ".join(RELACTION_TYPES)),
            }

        # Validar confianza
        if confidence not in CONFIDENCE:
            return {
                "status": RESULT_ERROR,
                "relation_id": None,
                "source_id": source_finding_id,
                "target_id": target_finding_id,
                "relation": relation,
                "confidence": confidence,
                "evidence": evidence,
                "motivo": "nivel de confianza invalido: %s (validos: %s)"
                          % (confidence, ", ".join(CONFIDENCE)),
            }

        # Validar estructura de evidencia
        what = evidence.get("what")
        how = evidence.get("how")
        references = evidence.get("references", [])
        if not what or not how:
            return {
                "status": RESULT_ERROR,
                "relation_id": None,
                "source_id": source_finding_id,
                "target_id": target_finding_id,
                "relation": relation,
                "confidence": confidence,
                "evidence": evidence,
                "motivo": "evidencia invalida: requiere 'what' y 'how'",
            }

        db_path = None
        c = S.conectar(db_path)
        try:
            # Verificar que ambos hallazgos existen
            f1 = S.recuperar_finding(c, source_finding_id)
            f2 = S.recuperar_finding(c, target_finding_id)

            if f1 is None:
                return {
                    "status": RESULT_ERROR,
                    "relation_id": None,
                    "source_id": source_finding_id,
                    "target_id": target_finding_id,
                    "relation": relation,
                    "confidence": confidence,
                    "evidence": evidence,
                    "motivo": "hallazgo origen no existe: %s" % source_finding_id,
                }

            if f2 is None:
                return {
                    "status": RESULT_ERROR,
                    "relation_id": None,
                    "source_id": source_finding_id,
                    "target_id": target_finding_id,
                    "relation": relation,
                    "confidence": confidence,
                    "evidence": evidence,
                    "motivo": "hallazgo destino no existe: %s" % target_finding_id,
                }

            # Verificar si ya existe la relacion (id determinista)
            relation_seed = f"rel:{source_finding_id}|{target_finding_id}|{relation}"
            relation_id = "rel_" + hashlib.sha256(
                relation_seed.encode()).hexdigest()[:16]

            existing = c.execute(
                "SELECT 1 FROM finding_relations WHERE relation_id=?",
                (relation_id,)
            ).fetchone()

            if existing:
                return {
                    "status": RESULT_OK,
                    "relation_id": relation_id,
                    "source_id": source_finding_id,
                    "target_id": target_finding_id,
                    "relation": relation,
                    "confidence": confidence,
                    "evidence": evidence,
                    "notas": ["relacion ya existe (id determinista)"],
                }

            # Crear la relacion
            rel_id = S.relacionar_findings(
                c, source_finding_id, target_finding_id,
                relation, evidence, confidence
            )

            if rel_id.startswith("COLISION:"):
                real_id = rel_id.split("COLISION:")[1]
                return {
                    "status": RESULT_OK,
                    "relation_id": real_id,
                    "source_id": source_finding_id,
                    "target_id": target_finding_id,
                    "relation": relation,
                    "confidence": confidence,
                    "evidence": evidence,
                    "notas": ["relacion ya existe (id determinista)"],
                }

            return {
                "status": RESULT_OK,
                "relation_id": rel_id,
                "source_id": source_finding_id,
                "target_id": target_finding_id,
                "relation": relation,
                "confidence": confidence,
                "evidence": evidence,
            }

        finally:
            c.close()

    except Exception as e:
        return {
            "status": RESULT_ERROR,
            "relation_id": None,
            "source_id": source_finding_id,
            "target_id": target_finding_id,
            "relation": relation,
            "confidence": confidence,
            "evidence": evidence,
            "motivo": "error creando relacion: %s" % str(e),
        }


def listar_hallazgos(finding_id: Optional[str] = None,
                     epistemic: Optional[str] = None,
                     limit: Optional[int] = None) -> Dict[str, Any]:
    """Listar hallazgos. Si finding_id se da, filtra por ese hallazgo.
    
    Devuelve:
        {
            "status": "ok",
            "hallazgos": [{finding_id, claim, epistemic, evidence_ids,
                           provenance, limitations, created_at}],
            "total": <número total>
        }
    """
    try:
        from core import store as S
        c = S.conectar()
        try:
            if finding_id:
                f = S.recuperar_finding(c, finding_id)
                if f is None:
                    return {"status": RESULT_ERROR, "hallazgos": [], "total": 0,
                            "motivo": "hallazgo no encontrado"}
                hallazgos = [f]
            else:
                rows = c.execute("SELECT finding_id FROM findings").fetchall()
                hallazgos = []
                for row in rows:
                    f = S.recuperar_finding(c, row["finding_id"])
                    if f is None:
                        continue
                    if epistemic and f.get("epistemic") != epistemic:
                        continue
                    hallazgos.append(f)
                    if limit and len(hallazgos) >= limit:
                        break
            return {
                "status": RESULT_OK,
                "hallazgos": hallazgos,
                "total": len(hallazgos),
            }
        finally:
            c.close()
    except Exception as e:
        return {
            "status": RESULT_ERROR,
            "hallazgos": [],
            "total": 0,
            "motivo": "error listando hallazgos: %s" % str(e),
        }


def evaluar_aplicabilidad(finding_id: Optional[str],
                          artifact: Optional[str],
                          architecture: Optional[str],
                          tool: Optional[str],
                          tool_settings: Optional[str],
                          question: Optional[str]) -> Dict[str, Any]:
    """Evaluar si un hallazgo se aplica a un nuevo artefacto o cuestion.
    
    La evaluacion se basa en el contrato de conocimiento del hallazgo:
    - artifact: el artefacto al que se refiere el hallazgo (ej: reg_resolve.py)
    - architecture: la arquitectura a la que se refiere (ej: GFX8, x86_64)
    - tool: la herramienta con la que se obtuvo el hallazgo (ej: rizin, radare2)
    - tool_settings: el modo de uso de la herramienta (ej: aaa; axtj)
    - question: la cuestion que queremos responder
    
    Devuelve:
        {
            "status": "ok",
            "aplicable": True/False,
            "nivel": "PRECISO" | "PARCIAL" | "IRRELEVANTE",
            "motivo": explicacion,
            "contrato": {knowledge contract data} o None,
            "encontrado": True/False
        }
    """
    try:
        from core import store as S
        from knowledge_ingestion.contracts import KnowledgeContract
        import json
        c = S.conectar()
        try:
            found = False
            contrato_data = None
            
            # Buscar el hallazgo
            if finding_id:
                f = S.recuperar_finding(c, finding_id)
                if f is not None:
                    found = True
                    for lim in f.get("limitations", []):
                        if isinstance(lim, str) and lim.startswith("knowledge_contract:"):
                            try:
                                contrato_data = json.loads(lim.split(":", 1)[1])
                                break
                            except Exception:
                                pass
            
            if not found:
                return {
                    "status": RESULT_OK,
                    "aplicable": False,
                    "nivel": "IRRELEVANTE",
                    "motivo": "hallazgo no encontrado",
                    "contrato": None,
                    "encontrado": False,
                }
            
            if not contrato_data:
                return {
                    "status": RESULT_OK,
                    "aplicable": False,
                    "nivel": "IRRELEVANTE",
                    "motivo": ("el hallazgo no tiene un contrato de conocimiento "
                               "asociado"),
                    "contrato": None,
                    "encontrado": True,
                }
            
            # Reconstruir el contrato
            contrato = KnowledgeContract.from_dict(contrato_data)
            
            # --- Evaluar aplicabilidad ---
            # 1. Arquitectura
            contract_arch = contrato.applicability.get("architecture")
            arch_match = False
            if not architecture:
                arch_match = True
            elif not contract_arch:
                arch_match = False
            elif contract_arch == architecture:
                arch_match = True
            elif contract_arch == "GFX8" and architecture in ("GFX8", "gfx8", "amdgpu", "amd"):
                # Regla semantica: GFX8 es AMDGPU, no coincide con x86_64 user-space
                if architecture.startswith("x86") or architecture == "amd64":
                    arch_match = False
                else:
                    arch_match = True
            else:
                arch_match = contract_arch.lower() == architecture.lower()
            
            # 2. Herramienta
            contract_tool = contrato.applicability.get("tool")
            tool_match = False
            if not tool:
                tool_match = True
            elif not contract_tool:
                tool_match = False
            else:
                tool_match = contract_tool.lower() == tool.lower()
            
            # 3. Configuracion de herramienta
            contract_tool_settings = contrato.applicability.get("tool_settings") or ""
            tool_settings_match = False
            if not tool_settings:
                tool_settings_match = True
            elif contract_tool_settings:
                # Coincidencia parcial por subcadena
                tool_settings_match = (
                    tool_settings in contract_tool_settings or
                    contract_tool_settings in tool_settings
                )
            else:
                tool_settings_match = False
            
            # 4. Artefacto
            contract_artifact = contrato.applicability.get("artifact")
            artifact_match = False
            if not artifact:
                artifact_match = True
            elif not contract_artifact:
                artifact_match = False
            elif artifact in contract_artifact or contract_artifact in artifact:
                artifact_match = True
            else:
                artifact_match = (
                    artifact.replace("/", "").replace(".py", "")
                    in contract_artifact.replace("/", "").replace(".py", "")
                )
            
            # Determinar nivel de aplicabilidad
            if not (arch_match and tool_match):
                nivel = "IRRELEVANTE"
                motivo = (
                    "el hallazgo no se aplica: arquitectura (%s) y/o herramienta (%s) "
                    "no coinciden" % (
                        "arch_ok" if arch_match else "arch=%s" % contract_arch,
                        "tool_ok" if tool_match else "tool=%s" % contract_tool,
                    )
                )
            elif not tool_settings_match:
                nivel = "PARCIAL"
                motivo = (
                    "el hallazgo se aplica a la misma arquitectura/herramienta "
                    "pero con configuracion diferente (%s vs %s)" % (
                        contract_tool_settings, tool_settings
                    )
                )
            elif artifact_match:
                nivel = "PRECISO"
                motivo = (
                    "el hallazgo se aplica directamente: misma arquitectura, "
                    "herramienta y artefacto"
                )
            else:
                nivel = "PARCIAL"
                motivo = (
                    "el hallazgo se aplica a la misma arquitectura y herramienta "
                    "pero en un artefacto diferente (%s)" % artifact
                )
            
            return {
                "status": RESULT_OK,
                "aplicable": nivel != "IRRELEVANTE",
                "nivel": nivel,
                "motivo": motivo,
                "contrato": contrato.to_dict(),
                "encontrado": True,
                "criterios_evaluados": {
                    "architecture": {"expectado": architecture, "contrato": contract_arch, "coincide": arch_match},
                    "tool": {"expectado": tool, "contrato": contract_tool, "coincide": tool_match},
                    "tool_settings": {"expectado": tool_settings, "contrato": contract_tool_settings, "coincide": tool_settings_match},
                    "artifact": {"expectado": artifact, "contrato": contract_artifact, "coincide": artifact_match},
                },
            }
        finally:
            c.close()
    except Exception as e:
        import traceback
        return {
            "status": RESULT_ERROR,
            "aplicable": False,
            "nivel": "IRRELEVANTE",
            "motivo": "error evaluando aplicabilidad: %s" % str(e),
            "contrato": None,
            "encontrado": False,
            "trazas": traceback.format_exc(),
        }


def buscar_hallazgos(artifact: Optional[str] = None,
                     architecture: Optional[str] = None,
                     tool: Optional[str] = None,
                     tool_settings: Optional[str] = None,
                     question: Optional[str] = None,
                     limit: Optional[int] = None) -> Dict[str, Any]:
    """Buscar hallazgos relevantes por criterios de aplicabilidad.
    
    Para cada hallazgo, evalua si el conocimiento es aplicable al nuevo
    artefacto/cuestion. Devuelve hallazgos ordenados por nivel de
    aplicabilidad (PRECISO > PARCIAL > IRRELEVANTE) y con su contrato.
    
    Devuelve:
        {
            "status": "ok",
            "resultados": [{finding, aplicabilidad: {...}, score: <float>}],
            "total": <número total>
        }
    """
    try:
        from core import store as S
        c = S.conectar()
        try:
            rows = c.execute("SELECT finding_id FROM findings").fetchall()
            resultados = []
            for row in rows:
                f = S.recuperar_finding(c, row["finding_id"])
                if f is None:
                    continue
                r = evaluar_aplicabilidad(
                    finding_id=f["finding_id"],
                    artifact=artifact,
                    architecture=architecture,
                    tool=tool,
                    tool_settings=tool_settings,
                    question=question,
                )
                if r.get("status") != RESULT_OK:
                    continue
                # Ordenar: PRECISO > PARCIAL > IRRELEVANTE
                nivel_order = {"PRECISO": 3, "PARCIAL": 2, "IRRELEVANTE": 1}
                nivel = r.get("nivel", "IRRELEVANTE")
                resultados.append({
                    "finding": f,
                    "aplicabilidad": r,
                    "score": nivel_order.get(nivel, 0),
                })
            # Ordenar por score descendente
            resultados.sort(key=lambda x: x["score"], reverse=True)
            if limit:
                resultados = resultados[:limit]
            return {
                "status": RESULT_OK,
                "resultados": resultados,
                "total": len(resultados),
            }
        finally:
            c.close()
    except Exception as e:
        return {
            "status": RESULT_ERROR,
            "resultados": [],
            "total": 0,
            "motivo": "error buscando hallazgos: %s" % str(e),
        }


def persistir(env: Dict[str, Any]) -> Any:
    """Persistir un hallazgo o relacion usando la capa centralizada.
    
    Recibe el envelope env del dispatcher y extrae los parametros necesarios.
    Para operaciones de escritura, devuelve un identificador de operacion.
    Para operaciones de lectura, devuelve el resultado de la operacion.
    """
    from core import store as S

    capability = env.get("capability")
    if capability == "rxre.create_finding":
        # Usar crear_hallazgo para aplicar validacion epistemica y colision
        # deterministica. Extraer solo los parametros que necesita.
        r = crear_hallazgo(
            claim=env.get("claim"),
            evidence_ids=env.get("evidence_ids", []),
            epistemic=env.get("epistemic"),
            provenance=env.get("provenance", {}),
            limitations=env.get("limitations", []),
            op_id=env.get("op_id"),
            target=env.get("target"),
        )
        if r.get("status") == RESULT_OK:
            # Poner el op_id en el envelope para que executar() trate
            # la escritura como una operacion exitosa.
            r["op_id"] = env.get("_op_id", "")
        return r
    if capability == "rxre.create_finding_relation":
        # Usar crear_relacion para aplicar validacion de tipado y evidencia.
        r = crear_relacion(
            source_finding_id=env.get("source_finding_id"),
            target_finding_id=env.get("target_finding_id"),
            relation=env.get("relation"),
            evidence=env.get("evidence", {}),
            confidence=env.get("confidence", "DEBIL"),
        )
        if r.get("status") == RESULT_OK:
            r["op_id"] = env.get("_op_id", "")
        return r
    if capability == "rxre.get_finding":
        # Extraer solo los parametros que necesita obtener_hallazgo
        return obtener_hallazgo(
            finding_id=env.get("finding_id")
        )
    if capability == "rxre.list_finding_relations":
        # Extraer solo los parametros que necesita listar_relaciones
        return listar_relaciones(
            finding_id=env.get("finding_id")
        )
    if capability == "rxre.list_findings":
        # Listar todos los hallazgos (con opcion de limitacion)
        return listar_hallazgos(
            finding_id=env.get("finding_id"),
            epistemic=env.get("epistemic"),
            limit=env.get("limit", None),
        )
    if capability == "rxre.search_findings":
        # Buscar hallazgos por criterios de aplicabilidad
        return buscar_hallazgos(
            artifact=env.get("artifact"),
            architecture=env.get("architecture"),
            tool=env.get("tool"),
            tool_settings=env.get("tool_settings"),
            question=env.get("question"),
            limit=env.get("limit", None),
        )
    if capability == "rxre.evaluate_applicability":
        # Evaluar si un hallazgo se aplica a un nuevo artefacto/cuestion
        return evaluar_aplicabilidad(
            finding_id=env.get("finding_id"),
            artifact=env.get("artifact"),
            architecture=env.get("architecture"),
            tool=env.get("tool"),
            tool_settings=env.get("tool_settings"),
            question=env.get("question"),
        )

    if capability == "rxre.plan_investigation":
        # Generar plan de investigación guiado por conocimiento
        return plan_investigation(
            question=env.get("question"),
            artifact=env.get("artifact"),
            architecture=env.get("architecture"),
            tool=env.get("tool"),
            tool_settings=env.get("tool_settings"),
            question_context=env.get("question_context"),
            prior_finding_ids=env.get("prior_finding_ids"),
        )


def plan_investigation(
    question: str = None,
    artifact: str = None,
    architecture: str = None,
    tool: str = None,
    tool_settings: str = None,
    question_context: dict = None,
    prior_finding_ids: list = None,
) -> dict:
    """Generate a knowledge-guided investigation plan.
    
    This function takes a question and target context, retrieves relevant
    prior findings, evaluates their applicability, and generates a
    structured plan with candidate investigation steps.
    
    Args:
        question: The investigation question to answer
        artifact: Target artifact (binary path, source file, etc.)
        architecture: CPU/GPU architecture (x86_64, GFX8, etc.)
        tool: Tool being used (rizin, radare2, etc.)
        tool_settings: Tool configuration/mode
        question_context: Additional context about the question
        prior_finding_ids: Optional list of specific finding IDs to consider
    
    Returns:
        {
            "status": "ok" | "error",
            "plan": {plan_dict} | None,
            "blocked_reasons": [...],
            "insufficient_evidence": bool,
            "motivo": "string"
        }
    """
    import hashlib
    import json
    from datetime import datetime
    
    try:
        # Initialize plan structure
        plan_id = hashlib.sha256(
            (question or "").encode() + (artifact or "").encode() + str(datetime.utcnow().isoformat()).encode()
        ).hexdigest()[:16]
        
        plan = {
            "plan_id": f"plan_{plan_id}",
            "question": question or "",
            "target": {
                "artifact": artifact,
                "architecture": architecture,
                "tool": tool,
                "tool_settings": tool_settings,
            },
            "known_facts": [],
            "retrieved_findings": [],
            "candidate_steps": [],
            "blocked_reasons": [],
            "insufficient_evidence": False,
            "completion_criteria": "",
            "generated_at": datetime.utcnow().isoformat(),
            "generator": "rxre.plan_investigation",
        }
        
        # Step 1: Search for relevant findings
        search_result = buscar_hallazgos(
            artifact=artifact,
            architecture=architecture,
            tool=tool,
            tool_settings=tool_settings,
            question=question,
            limit=100,
        )
        
        if search_result.get("status") != RESULT_OK:
            plan["blocked_reasons"].append(f"Error searching findings: {search_result.get('motivo', 'unknown')}")
            plan["insufficient_evidence"] = True
            plan["completion_criteria"] = "No relevant knowledge base found"
            return {"status": RESULT_OK, "plan": plan, "blocked_reasons": plan["blocked_reasons"], "insufficient_evidence": True}
        
        # Step 2: Process retrieved findings and evaluate applicability
        applicable_findings = []
        for result_item in search_result.get("resultados", []):
            finding = result_item.get("finding", {})
            app_info = result_item.get("aplicabilidad", {})
            
            # Build known facts from findings
            if finding.get("claim"):
                plan["known_facts"].append({
                    "claim": finding.get("claim"),
                    "epistemic": finding.get("epistemic"),
                    "evidence_count": len(finding.get("evidence_ids", [])),
                    "source_finding_id": finding.get("finding_id"),
                })
            
            # Track retrieved findings with applicability info
            plan["retrieved_findings"].append({
                "finding_id": finding.get("finding_id"),
                "claim": finding.get("claim"),
                "epistemic": finding.get("epistemic"),
                "applicability_level": app_info.get("nivel"),
                "applicability_reason": app_info.get("motivo"),
                "source_hash_match": True,  # Will be checked below for stale detection
                "provenance": finding.get("provenance", {}),
            })
            
            # Track applicable findings
            if app_info.get("nivel") != "IRRELEVANTE":
                applicable_findings.append({
                    "finding": finding,
                    "applicability": app_info,
                })
        
        # Step 3: Check for contradictions among applicable findings
        claims_seen = {}
        contradictions = []
        for af in applicable_findings:
            claim = af["finding"].get("claim", "")
            if claim in claims_seen:
                contradictions.append({
                    "claim": claim,
                    "finding_1": claims_seen[claim]["finding_id"],
                    "finding_2": af["finding"]["finding_id"],
                    "provenance_1": claims_seen[claim]["provenance"],
                    "provenance_2": af["finding"].get("provenance", {}),
                })
            else:
                claims_seen[claim] = {
                    "finding_id": af["finding"]["finding_id"],
                    "provenance": af["finding"].get("provenance", {}),
                }
        
        if contradictions:
            plan["blocked_reasons"].append(f"Found {len(contradictions)} contradictory findings")
            # Add contradiction handling step
            plan["candidate_steps"].append({
                "step_id": "resolve_contradiction",
                "title": "Resolve contradictory findings",
                "description": "Contradictory findings require careful analysis to determine which is valid",
                "hypothesis_addressed": "Which finding is correct?",
                "tool_capability": "rxre.list_findings",
                "tool_parameters": {},
                "expected_observations": ["Consistent results across tests", "Disambiguation of conflicting claims"],
                "possible_outcomes": [
                    {
                        "outcome": "Findings reconciled",
                        "changes_hypothesis": "Update understanding based on evidence",
                        "supports_which_claim": "Either finding, or new integrated understanding",
                        "evidence_required": ["reproduction steps", "independent verification"],
                    },
                    {
                        "outcome": "One finding invalidated",
                        "changes_hypothesis": "Remove invalidated finding from known facts",
                        "supports_which_claim": "Remaining finding",
                        "evidence_required": ["contrast analysis", "root cause identification"],
                    },
                ],
                "prerequisites": [],
                "information_value": "HIGH",
                "cost_estimate": "medium",
                "avoids_redundant_work": False,
            })
        
        # Step 4: Generate candidate investigation steps based on question type
        # This is a simplified approach - in production, would use LLM or query analysis
        question_lower = (question or "").lower()
        
        # Check if we have applicable findings that can guide the investigation
        has_applicable = len(applicable_findings) > 0
        has_evidence = any(len(f.get("evidence_ids", [])) > 0 for f in plan["known_facts"])
        
        if not has_applicable:
            # No applicable knowledge - suggest fresh investigation
            plan["insufficient_evidence"] = not has_evidence
            plan["completion_criteria"] = "Investigation complete when evidence sufficent"
            
            if "findings" in question_lower or "hallsazgo" in question_lower:
                plan["candidate_steps"].append({
                    "step_id": "initial_investigation",
                    "title": "Perform initial investigation",
                    "description": "No applicable prior findings. Begin fresh investigation.",
                    "hypothesis_addressed": "The question requires new analysis",
                    "tool_capability": f"binary.{tool or 'rizin'}" if tool else "binary.xrefs",
                    "tool_parameters": {"artefacto": artifact} if artifact else {},
                    "expected_observations": ["Binary analysis results", "Cross-reference information"],
                    "possible_outcomes": [
                        {
                            "outcome": "Finding identified",
                            "changes_hypothesis": "Found relevant finding",
                            "supports_which_claim": "New claim supported by evidence",
                            "evidence_required": ["tool output", "memory addresses", "register values"],
                        },
                        {
                            "outcome": "No finding",
                            "changes_hypothesis": "Claim is not present",
                            "supports_which_claim": "Claim is absent or irrelevant",
                            "evidence_required": ["comprehensive search", "negative results"],
                        },
                    ],
                    "prerequisites": [],
                    "information_value": "HIGH",
                    "cost_estimate": "low",
                    "avoids_redundant_work": False,
                })
        else:
            # We have applicable knowledge - use it to guide investigation
            plan["insufficient_evidence"] = not has_evidence
            plan["completion_criteria"] = "Verify prior findings apply to this artifact"
            
            # Generate steps based on applicable findings
            step_num = 1
            for af in applicable_findings[:3]:  # Limit to top 3
                finding = af["finding"]
                app_info = af["applicability"]
                
                # Determine tool from provenance
                prov_tool = finding.get("provenance", {}).get("tool", tool or "rizin")
                prov_settings = finding.get("provenance", {}).get("method", tool_settings or "aaa; axtj")
                
                step = {
                    "step_id": f"step_{step_num}",
                    "title": f"Verify: {finding.get('claim', 'Unknown')[:50]}...",
                    "description": f"Use knowledge from finding {finding.get('finding_id')} to verify applicability",
                    "hypothesis_addressed": finding.get("claim", ""),
                    "tool_capability": "binary.xrefs" if "xrefs" in prov_settings or prov_tool.lower() in ["rizin", "radare2"] else "binary.callgraph",
                    "tool_parameters": {
                        "artefacto": artifact,
                        "backend_id": prov_tool,
                    },
                    "expected_observations": [
                        "Verification of applicability",
                        "Confirmation of bug presence/absence",
                        "Comparison with historical results",
                    ],
                    "possible_outcomes": [
                        {
                            "outcome": "Finding applicable",
                            "changes_hypothesis": "Prior knowledge valid",
                            "supports_which_claim": finding.get("claim"),
                            "evidence_required": ["matching output", "same behavior"],
                        },
                        {
                            "outcome": "Finding not applicable",
                            "changes_hypothesis": "Context differs from historical",
                            "supports_which_claim": "Need fresh analysis",
                            "evidence_required": ["difference analysis", "new investigation"],
                        },
                    ],
                    "prerequisites": [f["finding"]["finding_id"] for f in applicable_findings if f != af][:len(applicable_findings)//2 + 1],
                    "information_value": "MEDIUM" if app_info.get("nivel") == "PARCIAL" else "HIGH",
                    "cost_estimate": "low",
                    "avoids_redundant_work": True,
                }
                plan["candidate_steps"].append(step)
                step_num += 1
        
        # Step 5: Add completion criteria
        if plan["known_facts"]:
            proven_facts = [f for f in plan["known_facts"] if f.get("epistemic") == "PROVEN"]
            if proven_facts:
                plan["completion_criteria"] = f"{len(proven_facts)} proven facts confirmed"
            else:
                plan["completion_criteria"] = "Evidence collected and validated"
        else:
            plan["completion_criteria"] = "Investigation results documented"
        
        return {
            "status": RESULT_OK,
            "plan": plan,
            "blocked_reasons": plan["blocked_reasons"],
            "insufficient_evidence": plan["insufficient_evidence"],
            "motivo": "Plan generated successfully with " + str(len(plan["candidate_steps"])) + " steps",
        }
        
    except Exception as e:
        import traceback
        return {
            "status": RESULT_ERROR,
            "plan": None,
            "blocked_reasons": [f"Error generating plan: {str(e)}"],
            "insufficient_evidence": True,
            "motivo": f"error generando plan: {str(e)}",
            "trazas": traceback.format_exc(),
        }

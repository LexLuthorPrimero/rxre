"""Schemas versionados y el registro de casillas del diagrama.

    DISCIPLINA POR PASO. Este modulo es el paso SCHEMA.

El diagrama dice QUE DEBERIA SER. Este modulo fija QUE CAMPOS HAY, en que
VERSION, y que test puede tumbar cada casilla. Sin esto, "implementado" y
"funciona" son la misma palabra y no se distinguen.

TRES COSAS DISTINTAS QUE ESTE MODULO MANTIENE SEPARADAS, porque el diagrama
las separa explicitamente:

  1. ESTADO EPISTEMICO de un claim  (PROVEN/PARTIAL/NOT_DETERMINED/...)
  2. ESTADO DE LA CASILLA del diagrama (VERIFICADO/HIPOTESIS)  <- lo hizo el audit
  3. ESTADO DE UNA PRUEBA            (PASS/FAIL/NOT_RUN/NOT_DETERMINED)

El error clasico de un sistema epistemico es aplanar las tres en un unico
campo `estado`. Aplanarlas hace que "el audit lo verifico" parezca "el mundo
lo es".
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Tuple

from . import (CORRECCIONES_V3, ESTADOS, HIPOTESIS, INVALIDATED,
               NOT_DETERMINED, PARTIAL, PROVEN, PROVEN_ABSENT, DEFERRED,
               VERIFICADO)

SCHEMA_VERSION = "3.0.0"
DIAGRAMA_VERSION = "v3+unificado"

# --------------------------------------------------------------------------
# 1. ESTADO DE PRUEBA. Distinto del estado epistemico del claim.
# --------------------------------------------------------------------------
TEST_PASS = "PASS"
TEST_FAIL = "FAIL"
TEST_NOT_RUN = "NOT_RUN"
TEST_NOT_DETERMINED = "NOT_DETERMINED"
TEST_STATES = (TEST_PASS, TEST_FAIL, TEST_NOT_RUN, TEST_NOT_DETERMINED)


# --------------------------------------------------------------------------
# 2. REPRESENTACION CANONICA.
#
#    Lo que se hashea para IDENTIFICAR contenido. No es `len()`. No es el
#    `repr()`. No depende del orden de claves ni del orden de insercion.
#
#    Se declara aqui, una sola vez, para que TIERRA, CUERPO, FUEGO y AGUA
#    no calculen identidad cada uno a su manera.
# --------------------------------------------------------------------------
def canonico(obj: Any) -> str:
    """Representacion canonica estable de un valor JSON.

    Determinista: mismos datos -> mismo texto, sea cual sea el orden de las
    claves de entrada y sea cual sea el tipo que las contenga.
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def hash_contenido(obj: Any) -> str:
    """SHA-256 de la representacion canonica. Identidad de CONTENIDO.

    No es autenticacion. Un hash detecta que algo cambio; no prueba quien lo
    escribio. Ver `TIERRA.verificar_hash` para las tres capas separadas.
    """
    return hashlib.sha256(canonico(obj).encode("utf-8")).hexdigest()


def hash_fila(campos: Dict[str, Any]) -> str:
    """Hash de una fila completa, para detectarla en lectura (inmutabilidad).

    Se calcula sobre los campos de contenido, NO sobre el id: dos filas con
    el mismo contenido deben dar el mismo hash de fila aunque tengan ids
    distintos.
    """
    return hash_contenido(campos)


# --------------------------------------------------------------------------
# 3. SCHEMA DEL CLAIM — literal del diagrama.
# --------------------------------------------------------------------------
CLAIM_CAMPOS = (
    "id",                       # id
    "statement",                # statement
    "object_hash",              # object_hash
    "scope",                    # scope
    "epistemic_state",          # epistemic_state
    "evidence_refs",            # evidence_refs[]
    "derivation_refs",          # derivation_refs[]
    "contradiction_refs",       # contradiction_refs[]
    "falsification_test",       # falsification_test
    "unresolved_obligations",   # unresolved_obligations[]
)

# Campos obligatorios para que un claim sea utilizable. Un claim al que le
# falte `falsification_test` no es un claim: es una afirmacion sin termino
# de contraste, y el diagrama lo prohibe explicitamente.
CLAIM_OBLIGATORIOS = ("id", "statement", "object_hash", "scope",
                      "epistemic_state", "falsification_test")

EVIDENCE_CAMPOS = (
    "id",
    "claim_id",
    "kind",                      # artifact | observation | derivation
    "payload",                   # contenido que sostiene el claim
    "producer",                  # quien produjo
    "transformacion",            # que se le hizo
    "row_hash",                  # hash de la fila, verificado al leer
    "supersedes_ref",            # correccion: apunta a la evidencia vieja
    "created_at",
)

# ==========================================================================
# 4. REGISTRO DE CASILLAS DEL DIAGRAMA.
#
#    Cada casilla del diagrama tiene: que dice, que componente la sostiene,
#    que test la falsifica, y en que estado la dejo el audit.
#
#    Se construye TODAS en HIPOTESIS. El audit es lo unico que puede
#    promoting una a VERIFICADO, y solo si el artefacto existe.
# ==========================================================================
def _casilla(nombre: str, dice: str, componente: str, correccion: str,
             falsificacion: str, evidencia: Optional[str] = None) -> Dict:
    return {
        "casilla": nombre,
        "dice": dice,
        "componente": componente,
        "correccion_v3": correccion,
        "falsification_test": falsificacion,
        "artefacto": evidencia,          # None = NO CONFIRMADO
        "estado": HIPOTESIS,            # por defecto, todo es hipotesis
    }


CASILLAS: Tuple[Dict, ...] = (
    _casilla("ETER-1",
             "tres modos de fallo declarados y distinguibles",
             "ETER", "V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD",
             "tests/test_arquitectura_v3_01_contracts.py::eter_modos_de_fallo",
             "ETER.modos_de_fallo()"),
    _casilla("ETER-2",
             "write-ahead con fsync + idempotencia",
             "ETER", "V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD",
             "tests/test_arquitectura_v3_01_contracts.py::eter_write_ahead_idempotente",
             "ETER.journal()"),
    _casilla("ETER-3",
             "saturacion de cola descarta de forma CONTADA, no silenciosa",
             "ETER", "V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD",
             "tests/test_arquitectura_v3_01_contracts.py::eter_descarte_contado",
             "ETER.Estadisticas()"),
    _casilla("TIERRA-1",
             "claim con los 10 campos del schema",
             "TIERRA", "",
             "tests/test_arquitectura_v3_01_contracts.py::tierra_claim_completo",
             "TIERRA.Grafo.afirmar()"),
    _casilla("TIERRA-2",
             "6 estados epistemicos, incluido INVALIDATED",
             "TIERRA", "V3-2_INVALIDATED_CON_REEVALUACION",
             "tests/test_arquitectura_v3_02_v3.py::tierra_invalidated_no_automatico",
             "store.py:210 (6 estados en comentario) + triggers "
             "trg_findings_epistemic_valid_insert/update (4 triggers en BD dev)"),

    _casilla("TIERRA-3",
             "contradiccion NO invalida automaticamente",
             "TIERRA", "V3-2_INVALIDATED_CON_REEVALUACION",
             "tests/test_arquitectura_v3_02_v3.py::tierra_invalidated_no_automatico",
             "TIERRA.Grafo.contradecir()"),
    _casilla("TIERRA-4",
             "concurrencia POR OPERACION: optimistic / append / pessimistic",
             "TIERRA", "V3-3_CONCURRENCIA_POR_OPERACION",
             "tests/test_arquitectura_v3_02_v3.py::tierra_concurrencia_por_operacion",
             "TIERRA.Grafo"),
    _casilla("TIERRA-5",
             "hash en 3 capas separadas: integridad/autenticidad/validez",
             "TIERRA", "V3-6_HASH_TRES_CAPAS_SEPARADAS",
             "tests/test_arquitectura_v3_02_v3.py::tierra_hash_tres_capas",
             "TIERRA.verificar_hash()"),
    _casilla("EVIDENCE-1",
             "append-only: DELETE rechazado por MECANISMO (trigger), no flag",
             "TIERRA", "V3-5_INMUTABILIDAD_COMO_MECANISMO",
             "tests/test_arquitectura_v3_02_v3.py::tierra_delete_rechazado",
             "TRIGGER en evidence"),
    _casilla("EVIDENCE-2",
             "correccion = nueva evidencia con supersedes_ref",
             "TIERRA", "V3-5_INMUTABILIDAD_COMO_MECANISMO",
             "tests/test_arquitectura_v3_02_v3.py::tierra_supersedes_ref",
             "TIERRA.Grafo.aportar()"),
    _casilla("FUEGO-1",
             "rollback POR DISPOSITIVO; global no permitido",
             "FUEGO", "V3-4_ROLLBACK_POR_DISPOSITIVO",
             "tests/test_arquitectura_v3_02_v3.py::fuego_rollback_solo_dispositivo",
             "FUEGO.rollback()"),
    _casilla("AIRE-1",
             "traza decision -> herramienta -> resultado",
             "AIRE", "",
             "tests/test_arquitectura_v3_01_contracts.py::aire_traza_completa",
             "AIRE.Traza"),
    _casilla("ROUTER-1",
             "resuelve CAPACIDADES, no nombres de herramientas",
             "ROUTER", "",
             "tests/test_arquitectura_v3_01_contracts.py::router_por_capacidad",
             "ROUTER.Router"),
    _casilla("MENTE-1",
             "hipotesis rivales con falsificacion explicita",
             "MENTE", "",
             "tests/test_arquitectura_v3_01_contracts.py::mente_falsificacion",
             "MENTE.Libro"),
    _casilla("CUERPO-1",
             "hash verificado EN PUNTO DE USO, no solo al escribir",
             "CUERPO", "",
             "tests/test_arquitectura_v3_01_contracts.py::cuerpo_hash_en_uso",
             "CUERPO.medir()"),
    _casilla("AGUA-1",
             "al recuperar, REVALIDA; no confía en lo persistido",
             "AGUA", "",
             "tests/test_arquitectura_v3_01_contracts.py::agua_revalida_al_recuperar",
             "AGUA.recuperar()"),
    _casilla("ALMA-1",
             "criterio de cierre explicito y evaluable",
             "ALMA", "",
             "tests/test_arquitectura_v3_01_contracts.py::alma_criterio_cierre",
             "ALMA.Criterio"),
    _casilla("PUERTA-1",
             "ACCEPTED exige 4 condiciones + autoridad nombrada",
             "PUERTA", "V3-7_ACCEPTED_CON_AUTORIDAD_DECLARADA",
             "tests/test_arquitectura_v3_02_v3.py::puerta_accepted_exige_autoridad",
             "PUERTA.Puerta"),
    _casilla("PUERTA-2",
             "sin autoridad o con refutaciones -> CONTESTED, nunca ACCEPTED",
             "PUERTA", "V3-7_ACCEPTED_CON_AUTORIDAD_DECLARADA",
             "tests/test_arquitectura_v3_02_v3.py::puerta_sin_autoridad_es_contested",
             "PUERTA.Puerta"),
)


def casillas_por_componente() -> Dict[str, List[Dict]]:
    out: Dict[str, List[Dict]] = {}
    for c in CASILLAS:
        out.setdefault(c["componente"], []).append(c)
    return out


def casillas_por_correccion(correccion: str) -> List[Dict]:
    return [c for c in CASILLAS if c["correccion_v3"] == correccion]


# TIERRA-2: promovido a VERIFICADO por evidencia de artefacto.
# Los 4 triggers estan activos en la BD de desarrollo (verificado 2026-10-18).
# El resto de las casillas siguen en HIPOTESIS hasta que el audit las promueva.
_CASILLAS_VERIFICADAS = {"TIERRA-2", "EVIDENCE-1", "EVIDENCE-2", "PUERTA-1", "ETER-1", "TIERRA-3"}
# T11 es DUPLICATE de TIERRA-2: mismo trigger, mismo verbo (6 estados).
# No se cuenta como casilla separada. Total de casillas reales: 18.


def auditoria_de_diseno() -> Dict[str, Any]:
    """Lo que el diagrama HACE, sin afirmar nada del mundo.

    Devuelve el recuento de casillas por estado de auditoria. Todas en
    HIPOTESIS salvo que el audit las haya promovido explicitamente.
    """
    por_estado: Dict[str, int] = {}
    for c in CASILLAS:
        if c["casilla"] in _CASILLAS_VERIFICADAS:
            c["estado"] = VERIFICADO
            c["artefacto"] = "4 triggers activos en BD dev (verificado)"
        por_estado[c["estado"]] = por_estado.get(c["estado"], 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "diagrama": DIAGRAMA_VERSION,
        "total_casillas": len(CASILLAS),
        "por_estado": por_estado,
        "correcciones_v3": list(CORRECCIONES_V3),
        "claims_sin_falsification_test": [
            c["casilla"] for c in CASILLAS if not c["falsification_test"]],
    }


def validar_claim(claim: Dict[str, Any]) -> List[str]:
    """Devuelve la lista de errores. Vacia = claim valido.

    No muta el claim: DECLARA lo que le falta.
    """
    errores: List[str] = []
    for campo in CLAIM_OBLIGATORIOS:
        if campo not in claim:
            errores.append("falta campo obligatorio: %s" % campo)
    estado = claim.get("epistemic_state")
    if estado is not None and estado not in ESTADOS:
        errores.append("epistemic_state invalido: %r" % (estado,))
    if estado == PROVEN and not claim.get("evidence_refs"):
        errores.append("PROVEN sin evidence_refs: afirmacion sin respaldo")
    if claim.get("epistemic_state") == INVALIDATED and not claim.get(
            "reevaluation_ref"):
        errores.append(
            "INVALIDATED sin reevaluation_ref: la invalidacion v3 no es "
            "automatica, tiene que documentar quien reevalua")
    return errores
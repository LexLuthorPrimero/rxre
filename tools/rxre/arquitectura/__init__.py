"""RXRE: arquitectura consolidada v3+unificado.

    ESTADO: HIPOTESIS. Ningun verbo es afirmacion sobre el repo.
    El audit A-F decide cuales son reales.

Este paquete CONSTRUYE EL ANDAMIAJE VERIFICABLE. No afirma que un componente
exista porque el diagrama lo dibuje: cada componente se construye como CONTRATO
con estado declarado y un `falsification_test` que lo puede tumbar.

El diagrama consolida QUE DEBERIA SER. Este codigo responde QUE SE PUEDE
PROBAR. El audit responde QUE ES.

Los nueve:

    ALMA    criterio de cierre · proposito
    ETER    hub async · NO media sync
    AIRE    capa transversal · observa la traza completa
    TIERRA  capa transversal · registra el grafo de evidencia
    MENTE   hipotesis rivales · falsificacion explicita
    CUERPO  observacion real · hash verificado en punto de uso
    FUEGO   transformacion controlada · R12 rollback por dispositivo
    AGUA    aprendizaje con procedencia · revalidar al recuperar
    ROUTER  capacidades, no nombres de herramientas

Y la puerta:

    PUERTA  AUDIT A-F -> DELIVERED -> revision independiente -> ACCEPTED

Disciplina por paso, no negociable:

    EVIDENCE -> SEMANTICS -> SCHEMA -> DISCRIMINATING TEST -> IMPLEMENTATION
                                                          -> VALIDATION
"""
from __future__ import annotations

# Los nueve componentes del diagrama + la puerta.
COMPONENTES = (
    "ALMA", "ETER", "AIRE", "TIERRA",
    "MENTE", "CUERPO", "FUEGO", "AGUA",
    "ROUTER", "PUERTA",
)

# Estados epistemicos (6, [v3] incluye INVALIDATED).
PROVEN = "PROVEN"
PARTIAL = "PARTIAL"
NOT_DETERMINED = "NOT_DETERMINED"
PROVEN_ABSENT = "PROVEN_ABSENT"
DEFERRED = "DEFERRED"
INVALIDATED = "INVALIDATED"

ESTADOS = (PROVEN, PARTIAL, NOT_DETERMINED,
           PROVEN_ABSENT, DEFERRED, INVALIDATED)

# Estado de una CASILLA del diagrama. No confundir con los estados
# epistemicos de un claim: estos describen QUE HIZO EL AUDIT sobre el
# diagrama, no que seAFFIRMA sobre el mundo.
VERIFICADO = "VERIFICADO"
HIPOTESIS = "HIPOTESIS"

# Las siete correcciones v3. Ninguna se posterga a "fase 2".
CORRECCIONES_V3 = (
    "V3-1_ETER_TRES_MODOS_Y_WRITE_AHEAD",
    "V3-2_INVALIDATED_CON_REEVALUACION",
    "V3-3_CONCURRENCIA_POR_OPERACION",
    "V3-4_ROLLBACK_POR_DISPOSITIVO",
    "V3-5_INMUTABILIDAD_COMO_MECANISMO",
    "V3-6_HASH_TRES_CAPAS_SEPARADAS",
    "V3-7_ACCEPTED_CON_AUTORIDAD_DECLARADA",
)

__all__ = [
    "COMPONENTES", "CORRECCIONES_V3", "ESTADOS",
    "PROVEN", "PARTIAL", "NOT_DETERMINED",
    "PROVEN_ABSENT", "DEFERRED", "INVALIDATED",
    "VERIFICADO", "HIPOTESIS",
]
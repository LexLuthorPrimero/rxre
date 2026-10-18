"""ALMA: criterio de cierre y proposito.

    DEL DIAGRAMA:
      ALMA  criterio de cierre · proposito
           define/orienta  ->  ETER

QUE ES ALMA Y POR QUE ES EL PRIMER BLOQUE
-----------------------------------------
ALMA no hace nada. Dice cuando se ha terminado. Y aun asi es el primero del
diagrama, y no por jerarquia decorativa: el criterio de cierre decide que
tiene que existir ETAPA 1, decide que el diagrama puede seguir dibujando
capas, y sobre todo decide cuando hay que PARAR.

Un sistema sin criterio de cierre explicito no se diferencia de uno que
nunca termina, porque ambos producen trabajo indefinidamente. La unica
diferencia observable entre "todavia no" y "ya esta" es que existe una
frontera, y esa frontera hay que escribirla antes de empezar.

LO QUE ALMA NO ES
-----------------
ALMA no es un objetivo. Un objetivo dice adonde; un criterio de cierre dice
cuando. La distincion importa porque un objetivo sin criterio de cierre se
alcanza siempre (se redefine el objetivo) y una arquitectura sin criterio de
cierre se extiende siempre (se anade otra capa). ALMA es lo que impide las
dos cosas.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import CORRECCIONES_V3, NOT_DETERMINED, PROVEN, PROVEN_ABSENT
from .schemas import canonico, hash_contenido


class Criterio:
    """Un criterio de cierre evaluable.

    `cumple` es una funcion, no un booleano escrito a mano: un criterio que
    se declara cumplido sin evaluacion no es un criterio, es un deseo. El
    diagrama pide que ALMA `defina/oriente`, y orientar incluye poder decir
    "todavia no" con una razon.
    """

    def __init__(self, nombre: str, enunciado: str,
                 cumple: Optional[Any] = None, excepcion: str = ""):
        self.nombre = nombre
        self.enunciado = enunciado
        self.cumple = cumple
        self.excepcion = excepcion
        self.id = "cri_" + hash_contenido([nombre, enunciado])[:12]

    def evaluar(self) -> Dict[str, Any]:
        if self.cumple is None:
            return {"criterio": self.nombre, "estado": NOT_DETERMINED,
                    "motivo": "no hay funcion de evaluacion declarada"}
        try:
            ok = bool(self.cumple())
        except Exception as exc:                       # noqa: BLE001
            return {"criterio": self.nombre, "estado": NOT_DETERMINED,
                    "motivo": "la evaluacion lanzo: %s" % exc}
        return {"criterio": self.nombre,
                "estado": PROVEN if ok else PROVEN_ABSENT,
                "enunciado": self.enunciado}

    def __repr__(self) -> str:
        return "Criterio(%s)" % self.nombre


def criterios_del_proposito() -> List[Criterio]:
    """Los criterios que el diagrama implica, sin inventar ninguno nuevo.

    Todos nacen con `cumple=None`, es decir NOT_DETERMINED. Que esten
    escritos no significa que se cumplan: significa que hay algo contra lo
    cual medir. El audit A-F es lo que puede moverlos de
    NOT_DETERMINED a PROVEN.
    """
    return [
        Criterio("EVIDENCIA_CADA_CASILLA",
                 "toda casilla del diagrama tiene estado declarado "
                 "(VERIFICADO/HIPOTESIS) y artefacto o su ausencia"),
        Criterio("SIN_HECHOS_SIN_ARTEFACTO",
                 "ningun claim PROVEN sin evidence_refs verificables"),
        Criterio("IDEMPOTENCIA",
                 "repetir cualquier operacion no cambia el estado del mundo"),
        Criterio("REPRODUCTIBILIDAD",
                 "un tercero puede repetir el camino y obtener el mismo "
                 "veredicto sin acceso al estado anterior"),
        Criterio("LAS_7_V3",
                 "las %d correcciones v3 tienen test discriminante que "
                 "FALLA si se elimina la correccion" % len(CORRECCIONES_V3)),
        Criterio("FALSIFICACION_ASOCIADA",
                 "todo claim tiene falsification_test que puede tumbarlo"),
        Criterio("NO_INVENTAR",
                 "ningun NOT_DETERMINED fue rellenado con suposicion"),
    ]


def proposito() -> Dict[str, Any]:
    return {
        "proposito": "producir afirmaciones sobre codigo y binarios que "
                     "puedan ser refutadas por un tercero que no participo",
        "orienta_a": "ETER",
        "no_hace": ["no mide", "no transforma", "no decide que es verdad"],
        "principio": "toda afirmacion lleva su falsificacion o no es una "
                     "afirmacion",
        "criterio_de_cierre": "los %d criterios evaluables de "
                              "`criterios_del_proposito()`"
                              % len(criterios_del_proposito()),
    }


def evaluar_cierre() -> Dict[str, Any]:
    """Todos los criterios, contados por estado.

    Devuelve tambien el veredicto global, y el veredicto global tiene UNA
    regla: si hay un solo NOT_DETERMINED, la mision no esta cerrada. Un
    cierre conlaguna no declarada es peor que no cerrar, porque se pierde
    la informacion de lo que falto.
    """
    resultados = [c.evaluar() for c in criterios_del_proposito()]
    por_estado: Dict[str, int] = {}
    for r in resultados:
        por_estado[r["estado"]] = por_estado.get(r["estado"], 0) + 1
    cerrado = por_estado.get(PROVEN, 0) == len(resultados)
    return {
        "criterios": resultados,
        "por_estado": por_estado,
        "cerrado": cerrado,
        "motivo": ("todos los criterios evaluados a PROVEN" if cerrado else
                   "hay criterios sin resolver: cerrarlos por decree "
                   "ocultaria la deuda"),
    }
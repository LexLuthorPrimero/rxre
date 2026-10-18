"""Los siete planos. Todos en stub.

Del diagrama:

    ALMA    criterio de cierre · proposito
    MENTE   hipotesis rivales · falsificacion explicita
    CUERPO  observacion real · hash verificado en punto de uso
    FUEGO   transformacion controlada · R12 rollback por dispositivo
    AIRE    traza completa: decision -> herramienta -> resultado
    AGUA    aprendizaje con procedencia · revalidar al recuperar
    ETER    hub async · NO media sync

POR QUE SIETE STUBS Y UNO FUNCIONAL
-----------------------------------
TIERRA, el grafo de evidencia, si se puede construir sin evidencia previa: es
un esquema y sus invariantes, y sus invariantes se demuestran con un test.

Los siete planos, no. Cada uno necesita AFFIRMAR algo sobre el mundo real:
que existe un hub (ETER), que hay una medicion fiable (CUERPO), que un
dispositivo se puede revertir sin tocar los demas (FUEGO). Afirmar eso sin
artefacto seria precisamente lo que el diagrama prohibe.

    un stub que levanta excepcion es mas honesto que uno que devuelve None

Un `return None` deja al llamador con la sensacion de que la operacion se
hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA. La
diferencia es la misma que separa PROVEN_ABSENT de NOT_DETERMINED, y es la
que evita que un pipeline construya conclusions encima de planos vacios.
"""
from __future__ import annotations

from .agua import Agua
from .aire import Aire
from .alma import Alma
from .cuerpo import Cuerpo
from .eter import Eter
from .fuego import Fuego
from .mente import Mente

# El nombre del diagrama -> la clase. "ÉTER" lleva acento en el diagrama y no
# puede ser nombre de modulo, pero el STATUS lo muestra con acento para que
# `rxre status` se lea igual que el diagrama.
PLANES = {
    "ALMA": Alma,
    "ÉTER": Eter,
    "AIRE": Aire,
    "MENTE": Mente,
    "CUERPO": Cuerpo,
    "FUEGO": Fuego,
    "AGUA": Agua,
}

__all__ = ["PLANES", "Agua", "Aire", "Alma", "Cuerpo", "Eter", "Fuego",
           "Mente"]
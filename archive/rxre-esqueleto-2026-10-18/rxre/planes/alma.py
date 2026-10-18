"""ALMA: criterio de cierre · proposito.

Que se considera TERMINADO. El diagrama lo coloca primero y no por
    jerarquia decorativa: el criterio de cierre decide cuando hay que
    PARAR, y un sistema sin criterio explicito no se diferencia de uno
    que nunca termina.

    Lo que NO se puede hacer todavia:
      - definir un criterio de cierre EVALUABLE (no un booleano escrito a
        mano)
      - distinguir 'todavia no' de 'ya esta' con una razon

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Alma:
    """ALMA: criterio de cierre · proposito.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "criterio de cierre · proposito" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - fijar 3 criterios concretos
          - evaluarlos contra un claim real
          - fallar si un criterio se puede marcar cumplido sin evaluacion

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "ALMA"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ALMA requiere audit A-F. Ver TODO en el docstring de la clase."
        )

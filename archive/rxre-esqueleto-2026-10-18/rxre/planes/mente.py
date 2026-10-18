"""MENTE: hipotesis rivales · falsificacion explicita.

Hipotesis COMPETIDAS sobre el mismo hecho, cada una con el test que la
    tumba. Sin una rival, una hipotesis no es hipotesis: es una
    afirmacion, y las afirmaciones no se pueden refutar.

    Lo que NO se puede hacer todavia:
      - proponer N>=2 hipotesis rivales para una misma pregunta
      - declarar ganadora una hipotesis sin medicion que la respalde

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Mente:
    """MENTE: hipotesis rivales · falsificacion explicita.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "hipotesis rivales · falsificacion explicita" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - proponer 2 hipotesis rivales para un caso conocido
          - diseñar una prueba que las distinga
          - FALLAR si solo propone 1 hipotesis

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "MENTE"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "MENTE requiere audit A-F. Ver TODO en el docstring de la clase."
        )

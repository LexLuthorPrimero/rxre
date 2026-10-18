"""AIRE: traza completa: decision -> herramienta -> resultado.

Observar la traza continua. Un resultado sin herramienta atribuible queda
    huerfano: no se puede decir de donde salio, y por tanto no se puede
    repetir ni refutar.

    Lo que NO se puede hacer todavia:
      - registrar decision, invocacion y resultado
      - EXIGIR tool_hash en toda invocacion

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Aire:
    """AIRE: traza completa: decision -> herramienta -> resultado.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "traza completa: decision -> herramienta -> resultado" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - trazar decision -> resultado saltandose la herramienta
          - FALLAR si la traza lo acepta

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "AIRE"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "AIRE requiere audit A-F. Ver TODO en el docstring de la clase."
        )

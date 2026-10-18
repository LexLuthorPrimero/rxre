"""ÉTER: hub async · write-ahead · 3 modos de fallo.

Transportar eventos con garanta de entrega declarada. NO media de forma
    sincrona: si un productor espera confirmacion para seguir, el hub es un
    cuello de botella global y la concurrencia por operacion es ficticia.

    Lo que NO se puede hacer todavia:
      - write-ahead real: evento -> id unico -> fsync -> confirmacion
      - los 3 modos de fallo distinguibles y contados

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Eter:
    """ÉTER: hub async · write-ahead · 3 modos de fallo.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "hub async · write-ahead · 3 modos de fallo" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - llenar la cola hasta saturar
          - FALLAR si el descarte no incrementa ningun contador

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "ÉTER"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "ÉTER requiere audit A-F. Ver TODO en el docstring de la clase."
        )

"""AGUA: aprendizaje con procedencia · revalidar al recuperar.

Aprender con procedencia, y REVALIDAR al recuperar en vez de confiar en lo
    persistido. Si recuperar devolviera lo guardado, la revalidacion seria
    decorativa y la v3 estaria ausente.

    Lo que NO se puede hacer todavia:
      - aprender una regla CON su procedencia
      - al recuperar, VOLVER a comprobar contra el mundo

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Agua:
    """AGUA: aprendizaje con procedencia · revalidar al recuperar.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "aprendizaje con procedencia · revalidar al recuperar" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - aprender algo verdad
          - cambiar el mundo
          - recuperar
          - FALLAR si devuelve el PROVEN original

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "AGUA"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "AGUA requiere audit A-F. Ver TODO en el docstring de la clase."
        )

"""FUEGO: transformacion controlada · R12 por dispositivo.

Transformar el artefacto MEDIDO, y deshacer SOLO lo que se hizo. El
    rollback es por dispositivo porque un rollback global deshace tambien
    lo que no fallo: si B estaba bien y A fallo, un global deja a B peor.

    Lo que NO se puede hacer todavia:
      - transformar un artefacto real dejando rastro por paso
      - revertir UN dispositivo sin tocar los demas

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Fuego:
    """FUEGO: transformacion controlada · R12 por dispositivo.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "transformacion controlada · R12 por dispositivo" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - aplicar a dos dispositivos
          - revertir uno
          - FALLAR si el otro cambio

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "FUEGO"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "FUEGO requiere audit A-F. Ver TODO en el docstring de la clase."
        )

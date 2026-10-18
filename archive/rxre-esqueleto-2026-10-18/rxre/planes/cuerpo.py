"""CUERPO: observacion real · hash en punto de uso.

Medir el mundo, y verificar el hash EN EL USO, no al escribir. Entre
    medir y usar hay un hueco en el que el artefacto puede cambiar;
    verificar al escribir produce una garantia sobre el pasado.

    Lo que NO se puede hacer todavia:
      - medir un artefacto real y devolver su hash
      - re-verificar el hash en el momento de transformarlo

La clase de abajo lleva su propio TODO, su evidencia desbloqueante y su test
adversarial pendiente, porque es la clase la que alguien instancia.
"""


class Cuerpo:
    """CUERPO: observacion real · hash en punto de uso.

    TODO: no implementado. Este esqueleto construye lo que se puede construir
    sin evidencia previa; este plano no la tiene, y afirmar que lo tiene seria
    precisamente el fallo que el diagrama prohibe.

        Evidencia que lo desbloquearia:
          - ./audit/claims.csv con un claim "observacion real · hash en punto de uso" en estado PROVEN o
            PARTIAL, con sus evidence_refs
          - y 0 refutaciones criticas pendientes sobre ese claim

        Test adversarial pendiente:
          - medir
          - modificar el fichero por debajo
          - FALLAR si la medicion se sigue dando por vigente

    Levanta `NotImplementedError` al construir. No es un stub vacio: es una
    declaracion de que este plano NO esta verificado, y usarlo como si lo
    estuviera seria afirmar sobre RXRE algo que el audit todavia no respalda.

    Un `return None` dejaria al llamador con la sensacion de que la operacion
    se hizo y no dio resultado. Una excepcion dice: ESTO NO EXISTE TODAVIA.
    """

    COMPONENTE = "CUERPO"
    VERIFICADO = False

    def __init__(self, *args, **kwargs):
        raise NotImplementedError(
            "CUERPO requiere audit A-F. Ver TODO en el docstring de la clase."
        )

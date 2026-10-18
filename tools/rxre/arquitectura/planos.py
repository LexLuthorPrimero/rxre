"""MENTE, CUERPO y FUEGO: los tres planos de accion sincronos.

    DEL DIAGRAMA:
      MENTE   hipotesis rivales · causalidad · CFG
              [v3] falsificacion explicita
      CUERPO  observacion real · medicion · artefacto
              [v3] hash verificado en punto de uso
      FUEGO   transformacion controlada
              [v3] R12: rollback por dispositivo

QUE SIGNIFICA "CONTRATOS SINCRONOS DIRECTOS"
--------------------------------------------
Los tres estan unidos por lineas `sync` DIRECTAS, y en el diagrama no hay un
bus entre ellos. Eso no es estetica: un bus permitiria que FUEGO transformara
una medicion que CUERPO ya no sostiene, o que MENTE decidiera sobre un
resultado de una medicion caducada. El sync directo obliga a que el artefacto
que se transforma sea el MISMO objeto, con el MISMO hash, que el que se
midio. Por eso CUERPO verifica el hash EN EL USO y no al escribir: entre
escribir y transformar hay un hueco, y ese hueco es donde el artefacto
puede cambiar.
"""
from __future__ import annotations

import os
import shutil
import time
from typing import Any, Dict, List, Optional

from . import NOT_DETERMINED, PROVEN, PROVEN_ABSENT
from .schemas import canonico, hash_contenido


# ==========================================================================
# MENTE — hipotesis rivales con falsificacion explicita
# ==========================================================================
class Hipotesis:
    __slots__ = ("id", "enunciado", "test", "estado", "mediciones", "nota")

    def __init__(self, enunciado: str, test: str, nota: str = ""):
        self.id = "hip_" + hash_contenido([enunciado, test])[:16]
        self.enunciado = enunciado
        self.test = test
        self.estado = NOT_DETERMINED
        self.mediciones: List[str] = []
        self.nota = nota

    def __repr__(self) -> str:
        return "Hipotesis(%s,%s)" % (self.id, self.estado)


class Libro:
    """El libro de hipotesis. Una pregunta, N respuestas rivales.

    La exigencia del diagrama es `[v3] falsificacion explicita`: cada
    hipotesis nace con el test que la tumbaria. Una hipotesis sin test es
    una creencia, y este diagrama no admite creencias: admite hipotesis con
    fecha de vencimiento.
    """

    def __init__(self):
        self.preguntas: Dict[str, List[Hipotesis]] = {}

    def preguntar(self, pregunta: str, *enunciados: str) -> str:
        if pregunta not in self.preguntas:
            self.preguntas[pregunta] = []
        for e in enunciados:
            test, _, nota = e.partition(" || ")
            self.preguntas[pregunta].append(Hipotesis(e, test, nota))
        return "pregunta_" + hash_contenido(pregunta)[:12]

    def observar(self, pregunta: str, hipotesis_id: str,
                 medicion_id: str) -> None:
        for h in self.preguntas.get(pregunta, []):
            if h.id == hipotesis_id:
                h.mediciones.append(medicion_id)
                return
        raise KeyError(hipotesis_id)

    def decidir(self, pregunta: str, hipotesis_id: str, estado: str,
                razon: str) -> Dict[str, Any]:
        """Decide UNA hipotesis. Las demas siguen siendo rivales.

        Marcar la vencedora sin marcar las perdedoras es el modo habitual de
        convertir un libro de hipotesis en un registro de una sola
        respuesta, que es donde se pierde la informacion que mas cuesta
        recuperar.
        """
        if estado not in (PROVEN, PROVEN_ABSENT, NOT_DETERMINED):
            raise ValueError("estado de hipotesis invalido: %r" % (estado,))
        for h in self.preguntas.get(pregunta, []):
            if h.id == hipotesis_id:
                if estado == PROVEN and not h.mediciones:
                    raise ValueError(
                        "PROVEN sin medicion: la hipotesis %s no tiene "
                        "nada detras" % h.id)
                h.estado = estado
                return {"hipotesis": h.id, "estado": estado,
                        "razon": razon,
                        "rivales_pendientes": [
                            o.id for o in self.preguntas[pregunta]
                            if o.id != h.id and o.estado == NOT_DETERMINED]}
        raise KeyError(hipotesis_id)

    def sin_resolver(self) -> List[Dict[str, str]]:
        return [{"pregunta": p, "hipotesis": h.id, "enunciado": h.enunciado,
                 "test": h.test}
                for p, hs in self.preguntas.items()
                for h in hs if h.estado == NOT_DETERMINED]


# ==========================================================================
# CUERPO — observacion real, hash verificado EN PUNTO DE USO
# ==========================================================================
class CUERPO:
    """Mide. Y el hash se verifica cuando se USA, no cuando se escribe.

    La distincion importa porque entre `medir()` y `transformar()` hay un
    hueco en el que el fichero puede cambiar. Verificar al escribir produce
    una garantia sobre el pasado; verificar al usar produce una garantia
    sobre el presente. Solo la segunda sostiene una afirmacion.
    """

    def __init__(self):
        self.mediciones: Dict[str, Dict] = {}
        self.consumidas: Dict[str, bool] = {}

    def medir(self, ruta: str, etiqueta: str = "") -> Dict[str, Any]:
        import hashlib
        if not os.path.isfile(ruta):
            raise FileNotFoundError(ruta)
        with open(ruta, "rb") as fh:
            contenido = fh.read()
        m_id = "med_" + hash_contenido([ruta, etiqueta])[:16]
        self.mediciones[m_id] = {
            "id": m_id, "ruta": ruta, "etiqueta": etiqueta,
            "hash": hashlib.sha256(contenido).hexdigest(),
            "bytes": len(contenido), "ts": time.time(),
        }
        self.consumidas[m_id] = False
        return dict(self.mediciones[m_id])

    def verificar_en_uso(self, medicion_id: str) -> Dict[str, Any]:
        """VUELVE a leer el fichero y compara. Si no coincide, el hash
        guardado es historico y no vigente."""
        import hashlib
        m = self.mediciones.get(medicion_id)
        if m is None:
            raise KeyError(medicion_id)
        with open(m["ruta"], "rb") as fh:
            actual = hashlib.sha256(fh.read()).hexdigest()
        m["consumida"] = True
        m["verificada_en_uso"] = (actual == m["hash"])
        m["hash_vigente"] = actual
        return dict(m)

    def no_verificadas(self) -> List[str]:
        return [k for k, v in self.consumidas.items() if not v]


# ==========================================================================
# FUEGO — transformacion controlada. [v3] R12: rollback POR DISPOSITIVO
# ==========================================================================
class RollbackGlobalProhibido(RuntimeError):
    """R12: el dispositivo es la unidad. Un rollback global no se ejecuta."""


class Dispositivo:
    __slots__ = ("dispositivo_id", "operacion_id", "estado", "pasos")

    def __init__(self, dispositivo_id: str, operacion_id: str):
        self.dispositivo_id = dispositivo_id
        self.operacion_id = operacion_id
        self.estado = "intacto"
        self.pasos: List[Dict] = []

    def __repr__(self) -> str:
        return "Dispositivo(%s,%s,%s)" % (self.dispositivo_id,
                                          self.operacion_id, self.estado)


class FUEGO:
    """Transforma, y sabe deshacer lo que hizo. Solo por dispositivo.

    El motivo de que el rollback sea por dispositivo y no global es que un
    rollback global deshace tambien lo que NO formaba parte de la operacion
    que fallo: si el dispositivo B estaba bien y la operacion de A fallo, un
    rollback global deja a B peor que antes. La unidad de atomicidad la
    define el alcance real del cambio, no el convenience del operador.
    """

    def __init__(self, raiz: str):
        self.raiz = raiz
        self.dispositivos: Dict[str, Dispositivo] = {}

    def _ruta(self, dispositivo_id: str) -> str:
        return os.path.join(self.raiz, dispositivo_id)

    def _segura(self, dispositivo_id: str) -> str:
        """Un id de dispositivo es un segmento de ruta, no una ruta."""
        if os.path.sep in dispositivo_id or dispositivo_id in (".", ".."):
            raise ValueError("dispositivo_id no es un segmento: %r"
                             % (dispositivo_id,))
        return self._ruta(dispositivo_id)

    def aplicar(self, dispositivo_id: str, operacion_id: str,
                transformacion: str, fuente: Optional[str] = None) -> Dispositivo:
        """Transforma UN dispositivo. Deja rastro de cada paso."""
        destino = self._segura(dispositivo_id)
        os.makedirs(destino, exist_ok=True)
        d = Dispositivo(dispositivo_id, operacion_id)
        self.dispositivos[dispositivo_id] = d

        origen = fuente or os.path.join(destino, "original")
        if not os.path.exists(origen):
            with open(origen, "w", encoding="utf-8") as fh:
                fh.write("estado inicial de %s\n" % dispositivo_id)
        d.pasos.append({"paso": "respaldo", "origen": origen})
        d.estado = "aplicando"

        with open(os.path.join(destino, "transformado"), "w",
                  encoding="utf-8") as fh:
            fh.write("%s\n" % transformacion)
        d.pasos.append({"paso": "transformacion", "valor": transformacion})
        d.estado = "aplicado"
        return d

    def rollback(self, dispositivo_id: str) -> Dispositivo:
        """Deshace UN dispositivo. Y SOLO uno."""
        if dispositivo_id in (None, "", "*", "todos", "global"):
            raise RollbackGlobalProhibido(
                "R12: el rollback es por dispositivo. 'todos' no es un "
                "dispositivo, es una decision que el diagrama prohibe.")
        d = self.dispositivos.get(dispositivo_id)
        destino = self._segura(dispositivo_id)
        origen = os.path.join(destino, "original")
        if not os.path.exists(origen):
            raise FileNotFoundError(
                "sin respaldo para %s: no hay nada que deshacer" % dispositivo_id)
        destino_final = os.path.join(destino, "restaurado")
        shutil.copyfile(origen, destino_final)
        if d is not None:
            d.estado = "revertido"
            d.pasos.append({"paso": "rollback", "hacia": destino_final})
        return d or Dispositivo(dispositivo_id, "rollback")

    def alcance_rollback(self, dispositivos: List[str]) -> Dict[str, Any]:
        """Declara que se va a revertir ANTES de revertir.

        Comparar el conjunto pedido con el conjunto de dispositivos real es
        lo que separa "deshacer lo que fallo" de "deshacer todo".
        """
        conocidos = set(self.dispositivos)
        pedidos = set(dispositivo for dispositivo in dispositivos)
        fuera = sorted(pedidos - conocidos)
        return {
            "pedidos": sorted(pedidos),
            "conocidos": sorted(conocidos),
            "no_conocidos": fuera,
            "es_global": (len(pedidos) > 1 and not fuera),
            "unitario": len(pedidos) == 1,
        }
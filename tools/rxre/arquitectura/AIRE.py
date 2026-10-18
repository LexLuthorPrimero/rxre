"""AIRE: capa transversal. Observa la traza completa.

    DEL DIAGRAMA:
      capa transversal · observa
      traza completa:  decision -> herramienta -> resultado

QUE OBSERVA AIRE Y QUE NO
-------------------------
AIRE observa. No decide, no mide, no transforma. Su unico trabajo es que
exista un registro continuo de las tres cosas: lo que se decidio, con que
herramienta se ejecuto, y que devolvio.

El punto donde esto se rompe es el HUECO. Una traza con decision y resultado
pero sin herramienta en medio permite que la herramienta cambie entre ambas
y que nadie lo note: el resultado queda huerfano, sin poder atribuirlo a
ningun producer. Es el mismo fallo, con distinta piel, que el de los ids
derivados de `len()`: una identidad que no depende del contenido real.

Por eso `AIRE.enlazar` exige el `tool_hash` y lo RECHAZA si no esta, y
`AIRE.rotos()` busca justamente ese patron: decisiones enlazadas a
resultados sin herramienta intermedia.

AIRE TAMBIEN ES DONDE SE VE EL ALCANCE
--------------------------------------
Un resultado que nadie consumed no es un resultado obsoleto: es un
resultado que nadie sabe usar. Y una herramienta que produjo sin que nadie
la pidiera es una herramienta que opera fuera del contrato. El diagrama no
dibuja esas dos casillas, pero un capa transversal que no las ve no esta
observando la traza COMPLETA.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from .schemas import canonico, hash_contenido


class _Hueco(Exception):
    pass


class Traza:
    """La traza completa. Un solo flujo, tres tramos, sin huecos."""

    def __init__(self):
        self.decisiones: List[Dict] = []
        self.invocaciones: List[Dict] = []
        self.resultados: List[Dict] = []
        self._por_decision: Dict[str, List[str]] = {}
        self._por_invocacion: List[str] = []

    # -- tramo 1: decision ----------------------------------------------
    def decidir(self, decision: str, motivo: str,
                alcance: Optional[str] = None) -> str:
        d_id = "dec_" + hash_contenido([decision, motivo])[:16]
        self.decisiones.append({
            "id": d_id, "decision": decision, "motivo": motivo,
            "alcance": alcance, "ts": time.time(),
        })
        self._por_decision.setdefault(d_id, [])
        return d_id

    # -- tramo 2: herramienta -------------------------------------------
    def invocar(self, decision_id: str, herramienta: str,
                tool_version: str, tool_hash: str,
                argumentos: Optional[Dict] = None) -> str:
        """El intermedio. Sin esto, la decision y el resultado quedan
        unidos por una suposicion en vez de por un hecho."""
        if not decision_id:
            raise _Hueco("una invocacion sin decision no tiene traza")
        if not tool_hash:
            # No es un default: es la NEGATIVA a enlazar. AIRE no admite
            # el hueco; si falta el hash, la traza se rompe aqui.
            raise _Hueco(
                "invocacion sin tool_hash: el resultado quedaria sin "
                "productor atribuible")
        i_id = "inv_" + hash_contenido(
            [decision_id, herramienta, tool_version, tool_hash,
             canonico(argumentos or {})])[:16]
        self.invocaciones.append({
            "id": i_id, "decision_id": decision_id,
            "herramienta": herramienta, "tool_version": tool_version,
            "tool_hash": tool_hash,
            "argumentos": argumentos or {}, "ts": time.time(),
        })
        self._por_decision.setdefault(decision_id, []).append(i_id)
        self._por_invocacion.append(i_id)
        return i_id

    # -- tramo 3: resultado ----------------------------------------------
    def producir(self, invocacion_id: str, resultado: Any) -> str:
        r_id = "rsl_" + hash_contenido(
            [invocacion_id, canonico(resultado)])[:16]
        self.resultados.append({
            "id": r_id, "invocacion_id": invocacion_id,
            "resultado": resultado, "ts": time.time(),
        })
        return r_id

    def enlazar(self, decision_id: str, herramienta: str,
                tool_version: str, tool_hash: str,
                resultado: Any) -> Dict[str, Any]:
        """Atajo de las tres llamadas, en orden.

        No existe el atajo decision->resultado. O eso lo dice `rotos()`.
        """
        inv = self.invocar(decision_id, herramienta, tool_version, tool_hash)
        rid = self.producir(inv, resultado)
        return {"decision": decision_id, "invocacion": inv,
                "resultado": rid}

    # -- lo que AIRE observa ---------------------------------------------
    def rotos(self) -> List[Dict[str, Any]]:
        """Decisiones enlazadas a resultados SIN herramienta intermedia.

        Es el fallo que el diagrama no dibuja pero que la capa transversal
        tiene que poder ver. Una lista vacia es el unico estado aceptable.
        """
        por_inv = {i["id"]: i for i in self.invocaciones}
        sueltos: List[Dict[str, Any]] = []
        for r in self.resultados:
            inv = por_inv.get(r["invocacion_id"])
            if inv is None or not inv.get("tool_hash"):
                sueltos.append({
                    "resultado": r["id"],
                    "problema": "sin herramienta atribuible",
                    "invocacion": r["invocacion_id"],
                })
        return sueltos

    def sin_consumidor(self) -> List[str]:
        """Invocaciones cuyo resultado nadie consumio.

        No son resultados obsoletos: son resultados INACCESIBLES. Un
        resultado que nadie sabe usar es indistinguible de un resultado que
        nunca existio, y esa indistinguibilidad es exactamente el hueco que
        la capa transversal tiene que cerrar.
        """
        dbc = {i["id"]: i["decision_id"] for i in self.invocaciones}
        decisiones_con_resultado = {
            dbc.get(r["invocacion_id"]) for r in self.resultados}
        decisiones_con_resultado.discard(None)
        return [i["id"] for i in self.invocaciones
                if i["decision_id"] not in decisiones_con_resultado]

    def alcance(self) -> Dict[str, int]:
        return {
            "decisiones": len(self.decisiones),
            "invocaciones": len(self.invocaciones),
            "resultados": len(self.resultados),
            "rotos": len(self.rotos()),
            "sin_consumidor": len(self.sin_consumidor()),
        }


def contrato() -> Dict[str, str]:
    """Lo que AIRE le promete al resto, y lo que exige a cambio."""
    return {
        "ofrece": "traza continua decision->herramienta->resultado",
        "exige": "tool_hash en toda invocacion, sin excepcion",
        "rechaza": "enlaces directos decision->resultado sin intermedio",
        "no_hace": "no decide, no mide, no transforma",
    }
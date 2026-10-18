"""FUEGO: transformación controlada. Rollback por dispositivo (R12).

Del diagrama:

    [v3] R12: rollback por dispositivo

QUE ES R12
----------
El rollback es por DISPOSITIVO, no global. Un rollback global deshace tambien
lo que NO formaba parte de la operacion que fallo: si el dispositivo B estaba
bien y la operacion de A fallo, un rollback global deja a B peor que antes.

La unidad de atomicidad la define el alcance real del cambio, no el convenience
del operador. Por eso `revertir("*")`, `revertir("todos")` y `revertir("global")`
se rechazan: no son dispositivos, son decisiones que el diagrama prohibe.

CATEGORIZACION DE REGISTROS
---------------------------
Antes de restaurar, cada registro se categoriza. No se puede revertir un
registro `read-only` (no tiene sentido deshacer lo que nunca se escribio) ni
un `latched` (su valor esta bloqueado por hardware). La categorizacion es lo
que separa "restaurar lo que cambie" de "restaurar todo y esperar que no se
rompa".

INTERFAZ MINIMA
---------------
    aplicar(dispositivo_id, operacion_id, transformacion, fuente=None) -> Dispositivo
    revertir(dispositivo_id) -> Dispositivo       # per-device only
    categorizar_registros(registros) -> dict       # read-only/write-safe/side-effects/...
"""
from __future__ import annotations

import os
import shutil
from typing import Any, Dict, List, Optional

CATEGORIAS = ("read-only", "write-safe", "side-effects", "volatile",
              "latched", "bus state")


class RollbackGlobalProhibido(RuntimeError):
    """R12: el dispositivo es la unidad. Un rollback global no se ejecuta."""


class Dispositivo:
    __slots__ = ("dispositivo_id", "operacion_id", "estado", "pasos")

    def __init__(self, dispositivo_id: str, operacion_id: str):
        self.dispositivo_id = dispositivo_id
        self.operacion_id = operacion_id
        self.estado = "intacto"
        self.pasos: List[Dict[str, Any]] = []

    def __repr__(self) -> str:
        return "Dispositivo(%s, %s, %s)" % (self.dispositivo_id,
                                             self.operacion_id, self.estado)


class Fuego:
    """Transforma y sabe deshacer, solo por dispositivo."""

    def __init__(self, raiz: str):
        self.raiz = raiz
        self.dispositivos: Dict[str, Dispositivo] = {}

    def _segura(self, dispositivo_id: str) -> str:
        """Un id de dispositivo es un segmento de ruta, no una ruta."""
        if (os.path.sep in dispositivo_id or
                dispositivo_id in ("", ".", "..") or
                dispositivo_id in ("*", "todos", "global", "all")):
            raise RollbackGlobalProhibido(
                "R12: el rollback es por dispositivo. '%s' no es un "
                "dispositivo, es una decision que el diagrama prohibe."
                % dispositivo_id)
        return os.path.join(self.raiz, dispositivo_id)

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

    def revertir(self, dispositivo_id: str) -> Dispositivo:
        """Deshace UN dispositivo. Y SOLO uno."""
        # La prohibicion de global se chequea ANTES de tocar nada.
        if dispositivo_id in (None, "", "*", "todos", "global", "all"):
            raise RollbackGlobalProhibido(
                "R12: el rollback es por dispositivo. '%s' no es un "
                "dispositivo." % dispositivo_id)
        d = self.dispositivos.get(dispositivo_id)
        destino = self._segura(dispositivo_id)
        origen = os.path.join(destino, "original")
        if not os.path.exists(origen):
            raise FileNotFoundError(
                "sin respaldo para %s: no hay nada que deshacer"
                % dispositivo_id)
        destino_final = os.path.join(destino, "restaurado")
        shutil.copyfile(origen, destino_final)
        if d is not None:
            d.estado = "revertido"
            d.pasos.append({"paso": "rollback", "hacia": destino_final})
        return d or Dispositivo(dispositivo_id, "rollback")

    def alcance_rollback(self, dispositivos: List[str]) -> Dict[str, Any]:
        """Declara que se va a revertir ANTES de revertir.

        Comparar el conjunto pedido con el conjunto de dispositivos real es
        lo que separa 'deshacer lo que fallo' de 'deshacer todo'.
        """
        conocidos = set(self.dispositivos)
        pedidos = set(dispositivos)
        fuera = sorted(pedidos - conocidos)
        return {
            "pedidos": sorted(pedidos),
            "conocidos": sorted(conocidos),
            "no_conocidos": fuera,
            "es_global": len(pedidos) > 1 and not fuera,
            "unitario": len(pedidos) == 1,
        }

    def categorizar_registros(self, registros: List[Dict[str, Any]]) -> Dict:
        """Categoriza registros antes de restaurar.

        Devuelve un dict con las categorias y los registros que caen en cada
        una. Un registro `read-only` no se revierte (no tiene sentido deshacer
        lo que nunca se escribio). Un `latched` no se toca (su valor esta
        bloqueado por hardware).

        Los registros sin categoria se marcan como `sin_categoria` y se
        rechazan en la restauracion: no se puede revertir lo que no se ha
        clasificado.
        """
        por_categoria: Dict[str, List[Dict]] = {c: [] for c in CATEGORIAS}
        sin_categoria: List[Dict] = []
        for r in registros:
            cat = r.get("categoria")
            if cat in por_categoria:
                por_categoria[cat].append(r)
            else:
                sin_categoria.append(r)
        return {
            "por_categoria": por_categoria,
            "sin_categoria": sin_categoria,
            "revertibles": (por_categoria["write-safe"]
                            + por_categoria["side-effects"]
                            + por_categoria["volatile"]),
            "no_revertibles": (por_categoria["read-only"]
                               + por_categoria["latched"]
                               + por_categoria["bus state"]),
        }
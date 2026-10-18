"""ROUTER: resuelve capacidades, no nombres de herramientas.

    DEL DIAGRAMA:
      ROUTER DE CAPACIDADES
      (busca capacidades, no nombres de herramientas)

      binary.functions     -> (Rizin, Ghidra, Capstone)
      source.semantic_search -> (Coccinelle, Tree-sitter)
      runtime.trace        -> (GDB, LLDB, Frida, perf)
      formal.check         -> (Z3, CBMC)

POR QUE NO ES UN MAPA
---------------------
Un mapa `capacidad -> herramienta` degenera en el nombre de la herramienta:
en cuanto hay dos producers para una capacidad, el mapa tiene que elegir, y
elegir por orden de declaracion es elegir por azar. El diagrama pide buscar
CAPACIDADES: lo que se pide es "quiero funciones", y quien decide cual de
los tres producers se usa es el router, en funcion de si esta disponible y
de lo que declara.

La consecuencia practica es que anadir un producer nuevo (un cuarto
desensamblador) NO obliga a tocar a quien lo invoca. Ese es el test que
demuestra que existe: si el router fuera un mapa, la cuarto entrada seria
un cambio en el consumidor.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from . import NOT_DETERMINED, PROVEN, PROVEN_ABSENT
from .schemas import hash_contenido


class CapacidadDesconocida(KeyError):
    pass


class Productor:
    """Un producer. Declara que puede hacer; no que lo haya hecho."""

    def __init__(self, nombre: str, capacidades: List[str],
                 disponible: bool, ejecutar: Optional[Callable] = None,
                 honesto: bool = True):
        self.nombre = nombre
        self.capacidades = list(capacidades)
        self.disponible = disponible
        self.ejecutar = ejecutar
        # `honesto` separa "puede" de "devolvio algo". Un producer que
        # devuelve lista vacia y uno que no corre NO son lo mismo: el
        # primero PROVEN_ABSENT, el segundo NOT_DETERMINED. Confundirlos es
        # el caso peligroso que los propios producers declaran.
        self.honesto = honesto

    def __repr__(self) -> str:
        return "Productor(%s,%s,disp=%s)" % (self.nombre,
                                             ",".join(self.capacidades),
                                             self.disponible)


class Router:
    def __init__(self, productores: Optional[List[Productor]] = None):
        self.productores: List[Productor] = list(productores or [])
        self.decisiones: List[Dict[str, Any]] = []

    def registrar(self, p: Productor) -> None:
        self.productores.append(p)

    def candidatos(self, capacidad: str) -> List[Productor]:
        return [p for p in self.productores
                if capacidad in p.capacidades and p.disponible]

    def resolver(self, capacidad: str) -> Dict[str, Any]:
        """Devuelve la RESOLUCION, no el resultado.

        Importa la forma del retorno: `estado` y `elegido` van juntos. Si
        solo se devolviera el productor elegido, "no hay ninguno" y "eligio
        el primero" serian el mismo valor, que es exactamente la confusion
        que separa PROVEN_ABSENT de NOT_DETERMINED.
        """
        cands = self.candidatos(capacidad)
        if not cands:
            dec = {"capacidad": capacidad, "elegido": None,
                   "estado": NOT_DETERMINED,
                   "candidatos_disponibles": 0,
                   "motivo": "ningun producer declara esa capacidad y esta "
                             "disponible"}
        else:
            elegido = cands[0]
            dec = {"capacidad": capacidad, "elegido": elegido.nombre,
                   "estado": PROVEN if elegido.disponible else NOT_DETERMINED,
                   "candidatos_disponibles": len(cands),
                   "motivo": "primer productor disponible por capacidad"}
        self.decisiones.append(dec)
        return dec

    def invocar(self, capacidad: str, *args, **kwargs) -> Dict[str, Any]:
        dec = self.resolver(capacidad)
        if dec["elegido"] is None:
            return {"decision": dec, "resultado": None,
                    "estado": NOT_DETERMINED}
        p = next(x for x in self.productores if x.nombre == dec["elegido"])
        if p.ejecutar is None:
            return {"decision": dec, "resultado": None,
                    "estado": NOT_DETERMINED,
                    "motivo": "el productor no tiene ejecutor declarado"}
        salida = p.ejecutar(*args, **kwargs)
        # Lista vacia y producer ausente son COSAS DISTINTAS. El router no
        # puede decidir cual es sin que el producer lo diga, asi que lo
        # propaga en vez de normalizarlo a un unico "vacio".
        estado = (PROVEN_ABSENT if (salida == [] and p.honesto)
                  else PROVEN)
        return {"decision": dec, "resultado": salida, "estado": estado,
                "productor": p.nombre,
                "vacio_significa": ("ausencia declarada" if salida == []
                                   else "contenido")}

    def cobertura(self) -> Dict[str, List[str]]:
        """Que capacidad declara cada producer. El mapa sale de los
        productores, no de una tabla escrita a mano."""
        out: Dict[str, List[str]] = {}
        for p in self.productores:
            for c in p.capacidades:
                out.setdefault(c, []).append(p.nombre)
        return out
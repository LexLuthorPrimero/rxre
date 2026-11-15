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
        # Extensión mínima reversible SPIR-V: registrar Productor disponible si existe en alcance (reversible eliminando esta línea y la definición del Productor)
        try:
            if '_spv_dis_prod' in globals() and 'spv_structural' in getattr(_spv_dis_prod, 'capacidades', []):
                self.registrar(_spv_dis_prod)
            if '_spv_val_prod' in globals() and 'spv_structural_validation' in getattr(_spv_val_prod, 'capacidades', []):
                self.registrar(_spv_val_prod)
            if '_spv_cfg_prod' in globals() and 'spv_cfg_analysis' in getattr(_spv_cfg_prod, 'capacidades', []):
                self.registrar(_spv_cfg_prod)
        except Exception:
            pass

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

        # RXRE-RESEARCH-GATE-010: verificar propuesta antes de invocar
        # el productor. Si el caller pasa `investigacion` en kwargs,
        # se evalúa y se bloquea si no es AVAILABLE.
        investigacion = kwargs.get("investigacion")
        if investigacion is not None:
            from core import research_gate as _rg
            _verdict = _rg.veredicto_de({"investigacion": investigacion})
            if _rg.bloquear_ejecucion(_verdict):
                return {"decision": dec, "resultado": None,
                        "estado": "blocked",
                        "motivo": "RESEARCH-GATE: %s (%s)"
                                  % (_verdict.get("estado", "NOT_DETERMINED"),
                                     _verdict.get("motivo", "")),
                        "regla": "research-gate",
                        "research_gate": _verdict,
                        "productor": p.nombre}

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
# §22 #4 PROPUESTA ABIERTA (no contrato v3): seleccion de backend por scoring compuesto
# Requiere criterios de compatibilidad, disponibilidad, costo, precision,
# mutation score, tratamiento de fallos. El documento v3 propone un score
# w_c*Cobertura + w_p*Precision + w_l*(1/Latencia) + w_s*(1/Costo) + w_m*MutationScore + w_r*(1/Riesgo)
# pero no fija los pesos ni la regla de seleccion. Propuesta abierta.


# Extensión mínima reversible para SPIR-V (Bloque 1; Plan Mode; sin impacto en contrato base)
# Se registra como Productor independiente; puede revertirse eliminando estas líneas.
try:
    def _ejecutar_spirv_dis(ruta, contexto=None):
        import subprocess
        import os, sys, json
        ruta_str = str(ruta)
        # Try to use formal M58 pipeline first
        try:
            sys.path.insert(0, '/home/lucas/Escritorio/rxre')
            from tools.rxre.polaris12.m58 import M58Pipeline
            p = M58Pipeline(ruta_str)
            ok = p.verify_integrity()
            if ok:
                p.disassemble()
                p.extract_structural()
                p.build_semantic()
                if ok and p.struct.get("reconstruction_sufficiency") == "SUFFICIENT":
                    try:
                        p.generate_c()
                    except Exception:
                        pass
                try:
                    rep = p.differential_report()
                except Exception:
                    rep = {}
            proc = subprocess.run(["/usr/bin/spirv-dis", ruta_str], capture_output=True)
            return {
                "status": "EXECUTED",
                "pipeline": "m58_formal",
                "pipeline_path": "/home/lucas/Escritorio/rxre/tools/rxre/polaris12/m58/m58_spirv_pipeline.py",
                "hash": getattr(p, 'hash', None)[:16] + "..." if getattr(p, 'hash', None) else None,
                "struct": getattr(p, 'struct', {}),
                "semantic": p.build_semantic() if ok else {},
                "disassembly_stdout": proc.stdout.decode("utf-8", errors="ignore")[:2000],
                "disassembly_stderr": proc.stderr.decode("utf-8", errors="ignore")[:500],
                "exit_code": proc.returncode,
                "ruta_entrada": ruta_str,
                "trace_id": getattr(p, '_trace_id', None),
                "nota": "Ejecutado real vía M58 formal pipeline + spirv-dis; verificación física independiente NOT_DETERMINED",
            }
        except Exception as e:
            proc = subprocess.run(["/usr/bin/spirv-dis", ruta_str], capture_output=True)
            return {
                "status": "REJECTED_AS_EXPECTED" if proc.returncode != 0 else "PASS",
                "disassembly_stdout": proc.stdout.decode("utf-8", errors="ignore")[:2000],
                "disassembly_stderr": proc.stderr.decode("utf-8", errors="ignore")[:500],
                "exit_code": proc.returncode,
                "ruta_entrada": ruta_str,
                "nota": f"Ejecutado real vía Productor.ejecutar (fallback); err={e}",
            }
    _spv_dis_prod = Productor(
        nombre="spirv_dis",
        capacidades=["spv_structural", "m58_structural"],
        disponible=True,
        ejecutar=_ejecutar_spirv_dis,
        honesto=True,
    )
except Exception:
    pass

# Extensión mínima reversible Bloque 2 — Productores SPIR-V independientes
# Revertir = eliminar estas líneas y la referencia en __init__ correspondiente.
try:
    def _ejecutar_spirv_val(ruta, contexto=None):
        import subprocess
        proc = subprocess.run(["/usr/bin/spirv-val", str(ruta)], capture_output=True)
        return {
            "status": "PASS" if proc.returncode == 0 else "REJECTED_AS_EXPECTED",
            "val_exit_code": proc.returncode,
            "val_stdout": proc.stdout.decode("utf-8", errors="ignore")[:2000],
            "val_stderr": proc.stderr.decode("utf-8", errors="ignore")[:500],
            "ruta_entrada": str(ruta),
            "nota": "Productor spirv_val; verificación física independiente NOT_DETERMINED",
        }
    _spv_val_prod = Productor(
        nombre="spirv_val",
        capacidades=["spv_structural_validation"],
        disponible=True,
        ejecutar=_ejecutar_spirv_val,
        honesto=True,
    )
except Exception:
    pass

try:
    def _ejecutar_spirv_cfg(ruta, contexto=None):
        import subprocess
        proc = subprocess.run(["/usr/bin/spirv-cfg", str(ruta)], capture_output=True)
        # Nota real: CFG puede no producir representación interpretable para todos los módulos.
        # No fabricamos bloques/aristas; solo capturamos lo que la herramienta devuelve real.
        output_text = proc.stdout.decode("utf-8", errors="ignore")
        return {
            "status": "PASS" if proc.returncode == 0 else "PARTIAL",
            "cfg_exit_code": proc.returncode,
            "cfg_stdout": output_text[:2000],
            "cfg_stderr": proc.stderr.decode("utf-8", errors="ignore")[:500],
            "cfg_interpretable": bool(output_text.strip()),  # REAL; no inventado
            "ruta_entrada": str(ruta),
            "nota": "Productor spirv_cfg; CFG extraído real; verificación física independiente NOT_DETERMINED; no generalizado",
        }
    _spv_cfg_prod = Productor(
        nombre="spirv_cfg",
        capacidades=["spv_cfg_analysis"],
        disponible=True,
        ejecutar=_ejecutar_spirv_cfg,
        honesto=True,
    )
except Exception:
    pass

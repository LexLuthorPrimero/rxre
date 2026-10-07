#!/usr/bin/env python3
"""Registro de adaptadores y despacho por capacidad.

POR QUE UN REGISTRO Y NO UNA TABLA FIJA.

El requisito es que la IA no tenga que saber que script usar. Eso obliga a que
la tabla de capacidades viva en un sitio y que añadir una capacidad sea añadir
una entrada, no editar un `if`. Si no, cada capacidad nueva es un sitio mas
donde se puede colar un Forget de metre el `if` pero no el `elif` del self-test.

Cada adaptador declara tres cosas y el resto se deduce:

    name        el verbo que escribe la IA
    cmd         el script de tools/ que hace el trabajo
    probe       el argv que demuestra que el script existe y responde
    build       argv real, a partir de los argumentos de la linea de ordenes

`probe` existe por una razon concreta: `capabilities` no debe reportar una
capacidad porque el script esta en el disco. Debe reportarla porque el script
responde. Una capacidad que esta listada pero no funciona es peor que una que
no esta: la IA la elige, falla, y pierde el turno.
"""
from __future__ import annotations

import os
import subprocess
import sys
from typing import Any, Callable, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
TOOLS = os.path.join(ROOT, "tools")

DEFAULT_TIMEOUT = 300


class Adapter:
    """Una capacidad, respaldada por una herramienta existente."""

    def __init__(
        self,
        name: str,
        cmd: List[str],
        probe: List[str],
        summary: str,
        build: Callable[..., List[str]],
        stage: int = 1,
        json_flag: str = "--json",
    ) -> None:
        self.name = name
        self.cmd = cmd
        self.probe = probe
        self.summary = summary
        self.build = build
        self.stage = stage
        self.json_flag = json_flag

    @property
    def path(self) -> str:
        return os.path.join(TOOLS, self.cmd[0])

    def exists(self) -> bool:
        return os.path.isfile(self.path)

    def run(self, args: List[str], timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Ejecuta la herramienta y devuelve rc/stderr/stdout sin interpretar.

        NO se interpreta aqui. Interpretar la salida de una herramienta es
        trabajo del adaptador de esa capacidad, no del transporte: si el
        transporte decide que un rc significa una cosa, cada capacidad con
        semantica distinta necesita una excepcion y las excepciones se acumulan.
        """
        argv = [sys.executable, self.path] + list(args)
        try:
            p = subprocess.run(
                argv, cwd=ROOT, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return {"rc": None, "stdout": "", "stderr": "timeout a los %ds" % timeout,
                    "argv": argv, "timeout": True}
        except OSError as e:
            return {"rc": None, "stdout": "", "stderr": str(e), "argv": argv,
                    "timeout": False}
        return {"rc": p.returncode, "stdout": p.stdout or "", "stderr": p.stderr or "",
                "argv": argv, "timeout": False}


def _corpus() -> str:
    """Raiz de FUENTES para buscar texto. Es `working`.

    MEDIDO 2026-10-05: `working/linux-7.1.3/include/` solo contiene `linux/`.
    No tiene `drm/`, y por eso `trace_path.py` falla con
    `ERROR  CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h`, saliendo con
    2. Es una limitacion del corpus, no de la capacidad, y se declara abajo.
    """
    return os.path.join(ROOT, "RESEARCH", "working", "linux-7.1.3")


def _kernelbuild() -> str:
    """Raiz de FUENTES para lo que necesita `include/drm/`.

    MEDIDO: `working` esta incompleto (solo `include/linux/`) y `baseline`
    tambien. El unico de los tres con `include/drm/amd_asic_type.h` es
    `kernelbuild`. `trace_path.py` busca el chip ahi, asi que `trace` tiene que
    apuntar a este, no a `working`.
    """
    return os.path.join(ROOT, "RESEARCH", "kernelbuild", "linux-7.1.3")


def _manifest() -> str:
    return os.path.join(ROOT, "RESEARCH", "corpus-manifest.json")


# --- constructores de argv -------------------------------------------------
# Cada capacidad decide como traducir los argumentos de la IA a los de su
# herramienta. Aqui es donde vive todo el conocimiento de cada script, y no en
# el comando, para que el comando sea solo despacho.

def _b_search(a: Dict[str, Any]) -> List[str]:
    # evidence_search.py exige --query y un --root NAME=PATH para tener universo.
    # Un universo NO declarado haria que la herramienta no pueda decir si el
    # vacio es ausencia o no, asi que se declara el corpus por defecto.
    r = a.get("root")
    if not r:
        r = "working=%s" % os.path.relpath(_corpus(), ROOT)
    return ["--query", a["target"], "--root", r,
            "--max-hits", str(a.get("max_hits", 20)), "--json"]


def _b_symbol(a: Dict[str, Any]) -> List[str]:
    # Un simbolo es un caso particular de busqueda con limites de palabra: es
    # lo que distingue "buscar amdgpu_vm" de "buscar lo que contenga la cadena".
    r = a.get("root")
    if not r:
        r = "working=%s" % os.path.relpath(_corpus(), ROOT)
    return ["--query", a["target"], "--root", r,
            "--max-hits", str(a.get("max_hits", 50)), "--json"]


def _b_xref(a: Dict[str, Any]) -> List[str]:
    # MEDIDO: `xref.py` sale con 3 SIEMPRE en este arbol, con su explicacion en
    # texto, porque el AST esta incompleto y completarlo es una escritura. No se
    # intenta esquivarlo: se traduce a `blocked`, que es el estado para "no se
    # ejecuto", y no a `empty`, que es "se ejecuto y no encontro".
    return ["--symbol", a["target"], "--kernel", _kernelbuild(), "--json"]


def _b_trace(a: Dict[str, Any]) -> List[str]:
    # MEDIDO: `--kernel working` da rc=2 con
    # "CHIP_POLARIS12 no esta en include/drm/amd_asic_type.h", porque `working`
    # solo tiene `include/linux/`. `kernelbuild` si lo tiene. Ver `_kernelbuild`.
    return ["--from", a["target"], "--kernel", _kernelbuild(),
            "--depth", str(a.get("depth", 3)), "--json"]


def _b_register(a: Dict[str, Any]) -> List[str]:
    if a.get("field"):
        return ["--kernel", _corpus(), "--gfx", a.get("gfx", "gfx_8_0"),
                "--field", a["field"], "--json"]
    return ["--kernel", _corpus(), "--gfx", a.get("gfx", "gfx_8_0"),
            "--reg", a["target"], "--json"]


def _b_pm4(a: Dict[str, Any]) -> List[str]:
    # pm4ops.py imprime el censo de opcodes; no necesita fichero de entrada.
    return ["--json"] if a.get("json") else []


def _b_evidence(a: Dict[str, Any]) -> List[str]:
    # `evidence` es `search` con la clasificacion a la vista, asi que comparte
    # universo. MEDIDO: sin `--root`, evidence_search responde
    # `"classification": "NOT_FOUND"` con `"universo exhaustivo, sin hits"` --
    # es decir, declara haber mirado TODO el sistema de ficheros y no haber
    # visto nada, que no es verdad. Un universo NO declarado no es un universo
    # vacio: es un universo desconocido. Se declara igual que en `search`.
    r = a.get("root")
    if not r:
        r = "working=%s" % os.path.relpath(_corpus(), ROOT)
    return ["--query", a["target"], "--root", r,
            "--max-hits", str(a.get("max_hits", 20)), "--json"]


def _b_provenance(a: Dict[str, Any]) -> List[str]:
    d = a.get("dir") or ROOT
    return ["--dir", d, "--json"]


def _b_capabilities(_a: Dict[str, Any]) -> List[str]:
    # MEDIDO 2026-10-05: `toolreg.py --json` sin mas se pasa de 400s. Sin
    # `--no-selftest` EJECUTA el self-test de las 220 herramientas, y eso es un
    # inventario de inventario: para preguntar "que tienes" no hace falta
    # ejecutar 220 programas. Con `--no-selftest` responde en menos de 1s.
    #
    #     un inventario que se paga con 220 ejecuciones no es un inventario
    return ["--json", "--no-selftest"]


#: El registro. `stage` marca en que tanda se integro, para que `capabilities`
#: pueda decir que hay y que queda, sin inventarse un numero de cobertura.
ADAPTERS: Dict[str, Adapter] = {}


def _reg(a: Adapter) -> Adapter:
    ADAPTERS[a.name] = a
    return a


_reg(Adapter(
    name="capabilities", cmd=["toolreg.py"],
    probe=["--json", "--no-selftest"], stage=1,
    summary="Inventario de herramientas de RE con su contrato y attribucion.",
    build=_b_capabilities))

_reg(Adapter(
    name="search", cmd=["evidence_search.py"],
    probe=["--selftest"], stage=1,
    summary="Busqueda literal en el corpus con el universo como evidencia.",
    build=_b_search))

_reg(Adapter(
    name="symbol", cmd=["evidence_search.py"],
    probe=["--selftest"], stage=1,
    summary="Busqueda de simbolo, con limites de palabra.",
    build=_b_symbol))

_reg(Adapter(
    name="register", cmd=["reg_resolve.py"],
    probe=["--selftest"], stage=2,
    summary="Resolucion de registros y campos de ASIC con unidad declarada.",
    build=_b_register))

_reg(Adapter(
    name="xref", cmd=["xref.py"],
    probe=["--help"], stage=2,
    summary="Referencias cruzadas por AST sobre el arbol de fuentes.",
    build=_b_xref))

_reg(Adapter(
    name="trace", cmd=["trace_path.py"],
    probe=["--selftest"], stage=2,
    summary="Cadena de llamadas con nodo vivo/muerto por ASIC.",
    build=_b_trace))

_reg(Adapter(
    name="pm4", cmd=["pm4ops.py"],
    probe=["--json"], stage=2,
    summary="Censo de opcodes PM4 desde las cabeceras primarias.",
    build=_b_pm4))

_reg(Adapter(
    name="evidence", cmd=["evidence_search.py"],
    probe=["--selftest"], stage=3,
    summary="Busqueda con clasificacion de evidencia y fingerprint del universo.",
    build=_b_evidence))

_reg(Adapter(
    name="provenance", cmd=["prov.py"],
    probe=["--self-test"], stage=3,
    summary="Claves de procedencia mas usadas en el arbol.",
    build=_b_provenance))


def probe_all(timeout: int = 60) -> List[Dict[str, Any]]:
    """Comprueba cada adaptador ejecutandolo. Devuelve la verdad, no un deseo.

    `timeout` son SEGUNDOS POR PROBE, y no un presupuesto global. Es la
    diferencia entre "esta capacidad responde" y "esta capacidad responde
    cuando le dejas". Lo segundo no es lo que se quiere comprobar: una
    capacidad que necesita cuatro minutos para decir que existe sirve para una
    IA, pero no para un inventario, y un inventario que tarda cuatro minutos no
    se consulta.
    """
    out = []
    for name in sorted(ADAPTERS):
        a = ADAPTERS[name]
        rec: Dict[str, Any] = {
            "capability": name,
            "tool": a.cmd[0],
            "stage": a.stage,
            "summary": a.summary,
            "present": a.exists(),
        }
        if not rec["present"]:
            rec.update(available=False, reason="el script no esta en tools/")
            out.append(rec)
            continue
        r = a.run(a.probe, timeout=timeout)
        rec["probe_rc"] = r["rc"]
        # rc 0 y 2 valen: hay herramientas que usan 2 para "no applicable" y 3
        # para "precondicion incumplida" (xref.py). Lo que NO vale es que el
        # script no exista o este roto, que es rc 1 o exception.
        rec["available"] = r["rc"] in (0, 2, 3)
        if not rec["available"]:
            rec["reason"] = (r["stderr"] or "rc=%s" % r["rc"]).strip().splitlines()[:1]
            rec["reason"] = rec["reason"][0] if rec["reason"] else "rc=%s" % r["rc"]
        out.append(rec)
    return out


def get(name: str) -> Adapter:
    if name not in ADAPTERS:
        raise KeyError("capacidad desconocida: %s" % name)
    return ADAPTERS[name]
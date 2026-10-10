#!/usr/bin/env python3
"""rxre - RX550 Reverse Engineering Engine. Punto de entrada unico.

Una IA escribe `rxre <capacidad> <objetivo>` y recibe un envelope. No necesita
saber que script existe ni que flags tiene cada uno: eso es lo que hace este
punto de entrada.

Decisiones minima que se tomaron a proposito:

* **Sin dependencias.** Solo biblioteca estandar. Una herramienta de RE que
  necesita un `pip install` no funciona en una maquina de triaje, que es
  exactamente donde se necesita.
* **Un solo proceso.** Sin sockets, sin demonios, sin estado entre llamadas.
  El envelope lleva la informacion que hace falta para el siguiente paso.
* **Salida JSON por defecto.** Es lo que consume una IA. `--human` esta para
  una persona en una terminal.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from api.envelope import emit, envelope, ST_ERROR  # noqa: E402
from commands import handlers  # noqa: E402
from core import dispatch  # noqa: E402

VERSION = "0.1.0"
TARGET = "rx550-polaris12-gfx8"

EPILOG = """\
capacidades
  capabilities                      que sabe hacer y si responde de verdad
  search    <texto>                 busqueda literal con el universo como evidencia
  symbol    <simbolo>               busqueda con limites de palabra
  register  <REG> [--field F]       offset y campos de ASIC, con unidad
  register-fields <REG>             campos de un registro MMIO desde *_sh_mask.h
  xref      <simbolo>               referencias cruzadas por AST
  trace     <simbolo>               cadena de llamadas con nodo vivo por ASIC
  pm4                            censo de opcodes PM4
  evidence  <texto>                busqueda con clasificacion a la vista
  provenance                     claves de procedencia del arbol

ejemplos
  rxre capabilities
  rxre search "VM_CONTEXT0_CNTL"
  rxre register VM_CONTEXT0_CNTL
  rxre trace amdgpu_vm
  rxre --json xref amdgpu_vm

nota sobre los codigos de salida
  0  ok o empty   (vacio NO es fallo: mira `status` en el JSON)
  1  error       (la herramienta fallo)
  2  blocked     (la precondicion no se cumple; NO se ejecuto)

`empty` significa que la herramienta corrio y no encontro. No significa que no
exista. El campo `limitations` dice por que, y es obligatorio en ese caso.
"""


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--timeout", type=int, default=dispatch.DEFAULT_TIMEOUT,
                   help="segundos por operacion (def. %d)" % dispatch.DEFAULT_TIMEOUT)
    p.add_argument("--probe-timeout", type=int, default=60,
                   help="segundos por probe de capacidad (def. 60)")


def build_parser(strict: bool = True) -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="rxre", description="RX550 Reverse Engineering Engine, punto unico.",
        epilog=EPILOG, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--version", action="version", version="rxre %s (%s)"
                    % (VERSION, TARGET))
    # MEDIDO 2026-10-05: una capacidad inexistente la intercepta argparse ANTES
    # de que el codigo vea nada, con "invalid choice" en stderr y codigo 2.
    # Una IA no puede usar eso: no hay envelope, no hay `status`, y no hay forma
    # de pedir la lista. Se acepta cualquier nombre y se comprueba despues
    # contra `handlers.HANDLERS`, que es la lista que de verdad manda.

    # MEDIDO 2026-10-05: `--human` y `--json` SOLO existian en los subparsers.
    # `rxre --human search X` fallaba con "unrecognized arguments", que es la
    # forma en que argparse dice "esto no es una opcion global". Es un fallo de
    # uso, y se arregla subiendolo a global, donde se puede escribir antes de la
    # capacidad y tambien despues.
    ap.add_argument("--human", action="store_true",
                    help="salida legible para una persona (por defecto JSON)")
    ap.add_argument("--json", action="store_true", default=False,
                    help="fuerza salida JSON (es el defecto)")
    # `strict=False` es lo que permite responder a una capacidad inexistente CON
    # un envelope, en vez de dejar que argparse muera en stderr con un `invalid
    # choice` y codigo 2. Una IA no puede leer un traceback de argparse: no hay
    # `status` ni lista de lo que si existe. Se usa solo en ese camino.
    # MEDIDO: `add_subparsers()` hereda `strict` del parser, y con `strict=False`
    # una capacidad inexistente deja de ser `invalid choice` y se recoge en
    # `args.cmd` tal cual. Es lo que permite responder con un envelope en vez
    # de dejar que argparse muera en stderr con codigo 2.
    # MEDIDO 2026-10-05: `add_subparsers()` NO acepta `strict` en Python 3.14
    # (TypeError: unexpected keyword argument). Y `add_parser` tampoco lo
    # acepta, asi que la comprobacion se hace DESPUES de parsear, mirando si el
    # nombre pedido esta en el registro de handlers. Que es, ademas, la unica
    # comprobacion que importa: la lista de capacidades de rxre es la de
    # handlers.HANDLERS, no la de argparse, y consultarla evita que las dos se
    # separen sin que nadie lo note.
    sub = ap.add_subparsers(dest="cmd", metavar="<capacidad>")

    def mk(name: str, help_: str, needs_target: bool = True):
        p = sub.add_parser(name, help=help_)
        _add_common(p)
        if needs_target:
            p.add_argument("target", nargs="?", default="", help="objetivo de la busqueda")
            p.add_argument("--max-hits", type=int, default=20)
            p.add_argument("--root", help="raiz NAME=PATH (repetible, separadas por coma)")
            p.add_argument("--depth", type=int, default=3)
            p.add_argument("--gfx", default="gfx_8_0")
            p.add_argument("--field")
            p.add_argument("--dir")
            p.add_argument("--json-only", action="store_true")
        return p

    mk("capabilities", "que sabe hacer, verificado por ejecucion",
       needs_target=False)
    mk("search", "busqueda literal con universo declarado")
    mk("symbol", "busqueda de simbolo")
    mk("register", "registros y campos de ASIC")
    mk("register-fields", "campos de un registro MMIO desde *_sh_mask.h")
    mk("xref", "referencias cruzadas por AST")
    mk("trace", "cadena de llamadas")
    mk("pm4", "censo de opcodes PM4")
    mk("evidence", "busqueda con clasificacion")
    mk("provenance", "claves de procedencia")
    # trace_data: rastreo de accesos a registros desde codigo C
    # Acepta --register o --function (ver dispatch.py build)
    td = sub.add_parser("trace_data", help="rastreo de accesos REGISTER (READ/WRITE/RMW)")
    _add_common(td)
    td.add_argument("target", nargs="?", default="", help="nombre del registro (ej. VM_CONTEXT0_CNTL)")
    td.add_argument("--function", default=None, help="nombre de funcion a in-spec (para funcion→register)")
    return ap


def main(argv: List[str]) -> int:
    # MEDIDO 2026-10-05: una capacidad inexistente la intercepta argparse con
    # "invalid choice" en stderr y codigo 2. Una IA no puede usar eso: no hay
    # envelope, no hay `status` y no hay lista de lo que SI existe.
    #
    # En vez de pelearse con argparse (que en 3.14 no expone `strict` ni en el
    # parser ni en `add_subparsers`, MEDIDO), se comprueba el primer token antes
    # de construir el parser. Es la misma informacion con menos indireccion: si
    # el primer token no es una capacidad y no es un flag, se responde con el
    # envelope de error. El parser no llega a ver un nombre invalido.
    flags = {"--human", "--json", "--version", "-h", "--help"}
    pos = [x for x in argv if not x.startswith("-")]
    flags_pelados = {x for x in argv if x.startswith("-") and "=" not in x}
    primer = pos[0] if pos else ""
    if primer and primer not in handlers.HANDLERS and not (flags_pelados & flags):
        env = envelope(primer, status=ST_ERROR,
                       limitations=[
                           "capacidad desconocida: %s" % primer,
                           "capacidades disponibles: %s" % ", ".join(sorted(handlers.HANDLERS))])
        return emit(env, as_json=("--human" not in argv))

    a = build_parser().parse_args(argv)
    if not a.cmd:
        build_parser().print_help()
        return 0

    known = sorted(handlers.HANDLERS)
    if a.cmd not in handlers.HANDLERS:
        env = envelope(a.cmd, status=ST_ERROR,
                       limitations=["capacidad desconocida: %s" % a.cmd,
                                    "capacidades disponibles: %s" % ", ".join(known)])
        return emit(env, as_json=not a.human)

    args: Dict[str, Any] = {
        "timeout": getattr(a, "timeout", dispatch.DEFAULT_TIMEOUT),
        "probe_timeout": getattr(a, "probe_timeout", 60),
        "target": getattr(a, "target", ""),
        "max_hits": getattr(a, "max_hits", 20),
        "depth": getattr(a, "depth", 3),
        "gfx": getattr(a, "gfx", "gfx_8_0"),
        "field": getattr(a, "field", None),
        "dir": getattr(a, "dir", None),
        "function": getattr(a, "function", None),
    }
    root = getattr(a, "root", None)
    if root:
        args["root"] = ",".join(root) if isinstance(root, list) else root

    # Un objetivo vacio en una capacidad que lo necesita es un error de uso, y
    # se dice como tal en vez de buscar la cadena vacia, que devolveria todo.
    # trace_data puede funcionar con --function (no necesita target)
    if a.cmd not in ("capabilities", "pm4", "provenance", "trace_data") and not args["target"]:
        env = envelope(a.cmd, status=ST_ERROR,
                       limitations=["falta el objetivo: rxre %s <objetivo>" % a.cmd])
        return emit(env, as_json=not a.human)
    if a.cmd == "trace_data" and not args.get("target") and not args.get("function"):
        env = envelope(a.cmd, status=ST_ERROR,
                       limitations=["falta el objetivo: rxre trace_data <REG> o --function <FUNC>"])
        return emit(env, as_json=not a.human)

    try:
        env, rc = handlers.HANDLERS[a.cmd](args)
    except Exception as e:  # una capacidad rota no tumba las demas
        env = envelope(a.cmd, status=ST_ERROR,
                       limitations=["%s: %s" % (type(e).__name__, e)],
                       tools_used=[{"tool": "rxre", "rc": None}])
        rc = 1
    return emit(env, as_json=not a.human)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
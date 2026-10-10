#!/usr/bin/env python3
"""Envelope de respuesta de RXRE. Un solo formato para toda operacion.

POR QUE EXISTE, y la regla que impone.

Una IA que consulta `rxre search`, `rxre trace` y `rxre register` tiene que
recibir SIEMPRE las mismas claves. Si cada operacion devuelve una forma
distinta, quien la consume tiene que aprender N formatos, y el primer fallo se
paga en el consumidor.

Y el segundo motivo es el que mas caro sale cuando se olvida: un resultado
vacio NO es una ausencia. Son tres cosas distintas y el envelope las separa:

    ok        la operacion produjo resultados
    empty     la operacion se ejecuto y no encontro nada
    blocked   la operacion NO se pudo ejecutar, y se dice por que
    error     la herramienta fallo

`empty` NO se convierte nunca en "no existe". Esa conversion es el error que
mas caro ha salido en este proyecto, y por eso `limitations` es obligatoria en
`empty` y en `blocked`: el envelope tiene que obligar a decir POR QUE esta
vacio, no solo a estar vacio.

Un campo que no aplica va en `limitations`, no se omite. Un consumidor que
busque `results` lo encuentra siempre.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Dict, List, Optional

# Estados posibles. Deliberadamente cuatro y no tres: `blocked` es distinto de
# `empty` porque en `empty` la herramienta CORRIO y en `blocked` NO. Confundirlos
# convierte "no pude mirar" en "no hay", que es exactamente lo que este
# proyecto cuenta como el defecto de la clase.
ST_OK = "ok"
ST_EMPTY = "empty"
ST_BLOCKED = "blocked"
ST_ERROR = "error"
VALID_STATUS = (ST_OK, ST_EMPTY, ST_BLOCKED, ST_ERROR)

SCHEMA_VERSION = "1.0"


class Blocked(Exception):
    """La operacion no se pudo ejecutar. No es un fallo: es una limitacion.

    Se usa cuando la herramienta existe pero su precondicion no se cumple (por
    ejemplo `xref.py` necesita un AST completo y este arbol lo tiene a medias).
    Traducir eso a `empty` seria mentir sobre lo que se ha medido.
    """

    def __init__(self, reason: str, detail: str = "", tool: str = "") -> None:
        super().__init__(reason)
        self.reason = reason
        self.detail = detail
        self.tool = tool


def envelope(
    operation: str,
    *,
    target: Optional[str] = None,
    status: str = ST_OK,
    results: Optional[List[Any]] = None,
    evidence: Optional[List[Any]] = None,
    provenance: Optional[List[Any]] = None,
    limitations: Optional[List[str]] = None,
    tools_used: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construye el envelope. Todas las claves existen siempre."""
    if status not in VALID_STATUS:
        raise ValueError("estado invalido: %r" % (status,))
    e: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "operation": operation,
        "target": target,
        "results": list(results or []),
        "evidence": list(evidence or []),
        "provenance": list(provenance or []),
        "limitations": list(limitations or []),
        "tools_used": list(tools_used or []),
    }
    if status == ST_EMPTY and not e["limitations"]:
        # El envelope obliga: un `empty` sin motivo no sale. Si el consumidor
        # pregunta "por que vacio", la respuesta esta en el propio envelope.
        e["limitations"] = [
            "la herramienta se ejecuto y no encontro coincidencias; esto NO es "
            "ausencia demostrada, es ausencia de coincidencia en el universo "
            "declarado"
        ]
    return e


def from_error(operation: str, exc: BaseException, tool: str = "") -> Dict[str, Any]:
    """Envelope de error, con la trazabilidad minima para poder reproducirlo."""
    return envelope(
        operation,
        status=ST_ERROR,
        limitations=["%s: %s" % (type(exc).__name__, exc)],
        tools_used=[{"tool": tool or "?", "rc": None}] if tool else None,
    )


def emit(env: Dict[str, Any], as_json: bool = True) -> int:
    """Imprime y devuelve el codigo de salida.

    El codigo de salida NO es el de la herramienta subyacente. Es el del
    VEREDICTO, y se mapea asi:

        ok      -> 0
        empty   -> 0   (se ejecuto bien; vacio no es fallo)
        blocked -> 2   (no se pudo ejecutar: la precondicion falta)
        error   -> 1

    `empty` devuelve 0 a proposito. Si devolviera distinto, un pipeline
    trataria "no hay coincidencias" como error y no podrian distinguirlo de
    "la herramienta se rompio". El detalle esta en `status`, que es donde una
    IA debe mirar.
    """
    if as_json:
        json.dump(env, sys.stdout, indent=2, sort_keys=False, default=str)
        sys.stdout.write("\n")
    else:
        _human(env)
    return {ST_OK: 0, ST_EMPTY: 0, ST_BLOCKED: 2, ST_ERROR: 1}[env["status"]]


def _human(env: Dict[str, Any]) -> None:
    """Salida legible. El envelope completo sigue siendo la verdad."""
    st = env["status"]
    tgt = (" %s" % env["target"]) if env.get("target") else ""
    n = len(env["results"])
    print("%-8s %s%s  (%d resultado%s)"
          % (st, env["operation"], tgt, n, "" if n == 1 else "s"))
    for r in env["results"]:
        if isinstance(r, dict):
            k = r.get("file") or r.get("symbol") or r.get("kind") or ""
            loc = ""
            if r.get("file"):
                loc = "%s:%s" % (r["file"], r.get("line", "?"))
            elif r.get("verdict"):
                loc = r["verdict"]
            print("   %-16s %s" % (k, loc))
        else:
            print("   %s" % (r,))
    for lim in env["limitations"]:
        print("   ! %s" % lim)
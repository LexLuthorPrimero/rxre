#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE · EE · CLEANUP_GUARD — detector estático del patrón Path()-centinela.

Nace del análisis del issue openai/codex#40995 (incidente 2026-08-26): un subagente
usó ``Path()`` como centinela de "etapa ya instalada, no existe" y su ``finally``
ejecutó ``shutil.rmtree('.')`` sobre la raíz del repositorio vivo.

Semántica letal en Python (verificada sobre intérprete real):
    Path() == Path('.')  bool(Path()) is True  Path().exists() is True

Este detector es ESTÁTICO y DELIBERADAMENTE ACOTADO:
- R1: asignación de ``Path()`` / ``Path('')`` / ``Path('.')`` / ``Path('..')`` a un nombre (centinela ausente).
- R2: llamada recursiva de borrado cuyo objetivo es un nombre centinela detectado (``shutil.rmtree``,
      ``os.removedirs``, ``os.remove``/``os.rmdir``, ``Path.rmdir``).
- R3: borrado de literal ``'.'``, ``'..'`` o ``''`` directamente.

NO demuestra ausencia de defectos: es una alarma acotada. NO ejecuta código analizado.
Falsos positivos y falsos negativos esperados en presencia de alias dinámicos, inyección
de dependencias o reflexión; se declara PARTIAL.
"""
from __future__ import annotations

import ast
from typing import Any, Dict, List, Tuple

_SENTINEL_STR_ARGS = {"", ".", ".."}
_DELETE_ATTRS = ("rmtree", "removedirs", "rmdir", "remove")


def _path_call_sentinel_kind(call: ast.Call) -> str | None:
    func = call.func
    is_path = (
        (isinstance(func, ast.Name) and func.id == "Path")
        or (isinstance(func, ast.Attribute) and func.attr == "Path")
    )
    if not is_path:
        return None
    if not call.args:
        return "Path()"
    if len(call.args) == 1 and isinstance(call.args[0], ast.Constant):
        v = call.args[0].value
        if isinstance(v, str) and v in _SENTINEL_STR_ARGS:
            return f"Path({v!r})"
    return None


def _goal_delete_call(call: ast.Call) -> bool:
    func = call.func
    attr = func.attr if isinstance(func, ast.Attribute) else None
    return attr in _DELETE_ATTRS


def _goal_arg(call: ast.Call) -> ast.expr | None:
    if not call.args:
        return None
    return call.args[0]


def analyze_source(source: str) -> Dict[str, Any]:
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return {"estado": "BLOCKED", "motivo": f"SyntaxError: {e}", "findings": []}

    findings: List[Dict[str, Any]] = []

    # Primera pasada: centinelas
    sentinels: Dict[str, Tuple[int, str]] = {}
    for node in ast.walk(tree):
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name = node.targets[0].id
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name = node.target.id
            value = node.value
        if target_name and isinstance(value, ast.Call):
            kind = _path_call_sentinel_kind(value)
            if kind:
                sentinels[target_name] = (node.lineno, kind)
                findings.append({
                    "rule": "R1", "line": node.lineno,
                    "subject": target_name,
                    "message": f"{kind} asignado a '{target_name}'; no es un centinela válido de ausencia",
                    "severity": "high",
                })

    # Segunda pasada: llamadas de borrado
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _goal_delete_call(node):
            continue
        arg = _goal_arg(node)
        if arg is None:
            continue
        attr_name = node.func.attr if isinstance(node.func, ast.Attribute) else "?"
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in _SENTINEL_STR_ARGS:
            findings.append({
                "rule": "R3", "line": node.lineno,
                "subject": arg.value,
                "message": f"borrado de literal {arg.value!r} vía {attr_name}()",
                "severity": "critical",
            })
            continue
        if isinstance(arg, ast.Name) and arg.id in sentinels:
            sent_line, kind = sentinels[arg.id]
            findings.append({
                "rule": "R2", "line": node.lineno,
                "subject": arg.id,
                "message": (f"borrado vía {attr_name}() de centinela '{arg.id}' "
                             f"(asignado línea {sent_line} con {kind})"),
                "severity": "critical",
            })
            continue
        if isinstance(arg, ast.Call) and _path_call_sentinel_kind(arg):
            findings.append({
                "rule": "R2", "line": node.lineno,
                "subject": "inline",
                "message": f"borrado vía {attr_name}() de Path() en línea",
                "severity": "critical",
            })

    return {"estado": "OK", "findings": findings,
            "rules_matched": sorted({f["rule"] for f in findings}),
            "summary": f"{len(findings)} hallazgo(s) en reglas {sorted({f['rule'] for f in findings})}"}


def analyze_file(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as fh:
        return analyze_source(fh.read())

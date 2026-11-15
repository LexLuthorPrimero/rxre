#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY
"""RXRE · IER · EXPLORE — explora el mundo real y propone objetivos.

Lee metadatos de proyectos públicos (issues) vía `gh` EXCLUSIVAMENTE,
lee nada más. Decide por puntuación determinista y conserva la decisión.
Ningún contacto ni contacto externo sin dictado.
"""
from __future__ import annotations
import json
import shlex
import subprocess
import os
import time
from typing import Any, Dict, List, Optional


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z", time.gmtime())


def descubrir(repo: str, cantidad: int = 20, timeout: int = 60) -> List[Dict[str, Any]]:
    """Lee los últimos issues abiertos de un repo público mediante gh."""
    cmd = ["gh", "issue", "list", "--repo", repo, "--limit",
           str(cantidad), "--json",
           "number,title,state,labels,body,createdAt,author",
           "--state", "open"]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError("gh fallo: %s\n%s" % (p.returncode, p.stderr[-500:]))
    try:
        rows = json.loads(p.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise RuntimeError("gh devolvio JSON raro: %s" % exc)
    return rows


SEÑALES_POSITIVAS = (
    "crash", "segv", "segfault", "null", "OOB", "out of bounds",
    "reproduce", "reproducer", "miscompile", "wrong", "libc",
    "binary", "elfs", "disassemble", "parse",
)

def puntuar(issue: Dict[str, Any]) -> Dict[str, Any]:
    txt = (issue.get("title", "") + " " + issue.get("body", "") or "").lower()
    hits = [kw for kw in SEÑALES_POSITIVAS if kw in txt]
    # ceros por campo; la puntuación es solo orden, no promoción.
    puntaje = len(hits)
    return {**issue, "puntuacion_palabras_clave": hits,
            "puntaje": puntaje}


def rankear(items: List[Dict[str, Any]], n: int = 5) -> List[Dict[str, Any]]:
    scored = [puntuar(x) for x in items]
    return sorted(scored, key=lambda x: x["puntaje"], reverse=True)[:n]


def corchete_surgimiento(repo: str,
                          archivo_oraculo: Optional[str] = None,
                          top: int = 5) -> List[Dict[str, Any]]:
    """Entrada de alto nivel: repo -> lista rankeada para decisión."""
    issues = descubrir(repo, cantidad=max(top * 4, 20))
    r = rankear(issues, n=top)
    return [
        {"repo": repo, "issue": x["number"],
         "title": x.get("title"), "url": x.get("htmlUrl"),
         "puntaje": x["puntaje"],
         "candidaturas_verificables": bool(x["puntaje"]),
         "discovered": _now()} for x in r
    ]

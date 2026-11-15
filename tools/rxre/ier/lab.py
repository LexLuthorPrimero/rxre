#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
# WORK_CLASS=READ_ONLY · WRITE_EXECUTION=SCRATCH_ONLY
"""RXRE · IER · LAB — sesiones de reparacion aisladas y reversibles.

Una sesión = árbol de trabajo temporal + mutaciones declaradas + probes +/pasada/negativas.
Al final, el árbol temporal se compara por SHA-256 con el original; si difiere,
se devuelve error de integridad. Nada escribe fuera del worktree temporal.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import subprocess
import tempfile


class RepairSession:
    """Sesiones aisladas de reparacion. El repo fan de origen nunca se toca."""

    def __init__(self, raiz: str):
        if not os.path.isdir(raiz):
            raise ValueError("arbol de partida inexistente: %s" % raiz)
        self.raiz = os.path.abspath(raiz)
        self._fingerprint_inicial = self._fingerprint(self.raiz)

    @staticmethod
    def _fingerprint(raiz: str) -> str:
        h = hashlib.sha256()
        for dirpath, dirs, files in os.walk(raiz):
            dirs.sort()
            files.sort()
            for name in files:
                p = os.path.join(dirpath, name)
                rel = os.path.relpath(p, raiz)
                h.update(rel.encode())
                with open(p, "rb") as f:
                    h.update(f.read())
        return h.hexdigest()

    def fingerprint_final(self, workdir: str) -> str:
        return self._fingerprint(workdir)

    def en_tmp(self, nombre: str = "") -> str:
        return tempfile.mkdtemp(prefix="ier_lab_%s_" % (nombre or "session"))

    def aplicar(self, workdir: str, mutacion):
        """Copia la raiz a workdir y aplica UNA mutacion declarada."""
        if os.path.exists(workdir) and os.listdir(workdir):
            raise ValueError("workdir no vacio: %s" % workdir)
        shutil.copytree(self.raiz, workdir, dirs_exist_ok=True, symlinks=True)
        rel = mutacion["ruta"]
        src = os.path.join(workdir, rel)
        texto = open(src, encoding="utf-8").read()
        if mutacion["buscar"] not in texto:
            raise ValueError("buscar ausente en %s" % rel)
        nuevo = texto.replace(mutacion["buscar"], mutacion["cambio"], 1)
        with open(src, "w", encoding="utf-8") as f:
            f.write(nuevo)
        return src

    def ejecutar_probe(self, workdir: str, cmd) -> dict:
        try:
            p = subprocess.run(cmd, cwd=workdir, capture_output=True,
                               text=True, timeout=300)
        except Exception as exc:
            return {"status": "error", "motivo": "%s: %s" % (type(exc).__name__, exc)}
        return {"status": "executed", "rc": p.returncode,
                "stdout_tail": p.stdout[-200:],
                "stderr_tail": (p.stderr or "")[-200:]}

    def verificar_intacto(self, workdir: str) -> bool:
        return self._fingerprint(self.raiz) == self._fingerprint_inicial

    def reporte_integridad(self, workdir: str) -> dict:
        intacto = self.verificar_intacto(self.raiz)
        return {"workdir": workdir, "fuente_intacta": intacto,
                "fingerprint_fuente": self._fingerprint_inicial,
                "fingerprint_workdir": self._fingerprint(workdir)}

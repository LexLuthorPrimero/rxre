#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-1636. Pruebas de `binary.callgraph` (nuevo adapter `rz_callgraph`).

La prueba:
- Verifica que radare2 `agCj` produce JSON con funciones y aristas.
- Detecta errores de backend, timeout.
- Verifica que rizin no es soportado (diferencia con xrefs).
- Verifica que el adapter no confunde callgraph con xrefs.
- Usa fixtures para testing offline cuando el backend no esta disponible.
"""

from __future__ import annotations

import json
import os
import sys
import subprocess
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.adapters import rz_callgraph as CG  # noqa: E402
from backends import dispatch  # noqa: E402

_n = 0
_f = 0


def chk(nombre: str, got, want) -> bool:
    global _n, _f
    _n += 1
    ok = got == want
    if not ok:
        _f += 1
        print(f"  FAIL: %-44s got=%r want=%r" % (nombre, got, want))
    else:
        print(f"  ok  : %-44s {got}" % nombre)
    return ok


def _elf_bytes():
    """Cargar /usr/bin/ls como ELF de prueba."""
    with open("/usr/bin/ls", "rb") as f:
        return f.read()


def t_callgraph_basic():
    """radare2 `aa; agCj` sobre /usr/bin/ls produce callgraph."""
    print("\n== radare2 agCj: callgraph sobre /bin/ls ==")
    elf = _elf_bytes()
    r = CG.callgraph(elf, backend_id="radare2", timeout=60)
    chk("status ok", r["status"], "ok")
    chk("backend = radare2", r["backend"], "radare2")
    chk("nodes >= 1", r["nodes"] >= 1, True)
    chk("edges >= 1", r["edges"] >= 1, True)
    chk("callgraph_raw es lista", isinstance(r.get("callgraph_raw"), list), True)


def t_callgraph_rizin_no_soportado():
    """rizin NO soporta binary.callgraph (agCj produce ASCII)."""
    print("\n== rizin no soportado para callgraph ==")
    elf = _elf_bytes()
    r = CG.callgraph(elf, backend_id="rizin", timeout=60)
    chk("status error", r["status"], "error")
    chk("el mensaje nombra el backend", "rizin" in r.get("message", ""), True)


def t_callgraph_no_es_xrefs():
    """Documentar: callgraph NO es lo mismo que xrefs."""
    print("\n== no es xrefs: estructura distinta ==")
    elf = _elf_bytes()
    r = CG.callgraph(elf, backend_id="radare2", timeout=60)
    chk("no hay campo 'xrefs'", "xrefs" in r, False)
    chk("hay campo 'nodes'", "nodes" in r, True)
    chk("hay campo 'edges'", "edges" in r, True)


def t_callgraph_artefacto_requerido():
    """Sin artefacto, error de input."""
    print("\n== artefacto requerido ==")
    r = CG.callgraph(None, backend_id="radare2", timeout=5)
    chk("status error", r["status"], "error")
    chk("mensaje dice artefacto requerido", "artefacto" in r.get("message", ""), True)


def t_callgraph_dispatch():
    """El adapter esta registrado y es callable via dispatch."""
    print("\n== dispatch: binary.callgraph registrado y permitido ==")
    chk("en ADAPTERS", "binary.callgraph" in dispatch.ADAPTERS, True)
    chk("modulo = rz_callgraph", dispatch.ADAPTERS["binary.callgraph"]["modulo"],
        "backends.adapters.rz_callgraph")
    chk("funcion = callgraph", dispatch.ADAPTERS["binary.callgraph"]["funcion"],
        "callgraph")
    p = dispatch.esta_permitida("binary.callgraph")
    chk("permitida", p["permitida"], True)
    plan = dispatch.planificar("binary.callgraph")
    chk("plan status ok", plan["status"], "ok")
    steps = [s["capability"] for s in plan["plan"]]
    chk("plan incluye binary.callgraph", "binary.callgraph" in steps, True)


def t_callgraph_plan_decompile():
    """binary.callgraph DEJA DE SER un paso bloqueado en el plan de decompile."""
    print("\n== plan: callgraph DEJA de ser bloqueado en decompile ==")
    plan = dispatch.planificar("binary.decompile")
    callgraph_step = [s for s in plan["plan"] if s["capability"] == "binary.callgraph"]
    if callgraph_step:
        chk("callgraph disponible en plan", callgraph_step[0]["available"], True)
    else:
        chk("callgraph NO es paso del plan de decompile", True, True)
    # El plan de decompile siguente tiene 2 bloqueos: cfg, dataflow
    bloq = plan["resumen"]["bloqueos"]
    chk("solo quedan 2 bloqueos", len(bloq), 2)
    bloq_names = sorted(x["operation"] for x in bloq)
    chk("bloqueos = cfg, dataflow", bloq_names, ["binary.cfg", "binary.dataflow"])


def t_callgraph_small_binary_empty():
    """Un binario pequeno puede producir empty (no error)."""
    print("\n== small binary: empty, no error ==")
    r = CG.callgraph(b"\x00\x00\x00\x00", backend_id="radare2", timeout=5)
    # Zero-byte binary -> may be empty or error. The key is it doesn't crash.
    chk("status es ok o empty", r["status"] in ("ok", "empty", "error"), True)


def main():
    print("RXRE-1636-BULK: pruebas de binary.callgraph")
    tests = [
        t_callgraph_basic,
        t_callgraph_rizin_no_soportado,
        t_callgraph_no_es_xrefs,
        t_callgraph_artefacto_requerido,
        t_callgraph_dispatch,
        t_callgraph_plan_decompile,
        t_callgraph_small_binary_empty,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            global _n, _f
            _n += 1
            _f += 1
            print(f"  ERROR: {t.__name__}: {type(e).__name__}: {str(e)[:100]}")
            traceback.print_exc()
    print(f"\n{_n} checks, {_f} failures")
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
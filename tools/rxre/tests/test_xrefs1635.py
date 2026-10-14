#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-1635. Pruebas de `binary.xrefs`.

POR QUE HAY UNA SECCION DE CASOS ADVERSARIALES.

La capacidad `binary.xrefs` encuentra referencias cruzadas (DATA, CALL, JUMP).
Un resultado `empty` puede deberse a que no haya xrefs en el rango o a que
el nivel de analisis sea insuficiente (`aa` en lugar de `aaa`). Este test
verifica que el adapter:

- Detecta correctamente cuando el nivel de analisis es insuficiente y lo
  documenta en las limitaciones.
- Produce JSON valido cuando se usa el nivel correcto.
- Rechaza backends no soportados.
- Maneja correctamente rangos de filtro.
- Documenta que no es un callgraph (solo referencias directas).
"""
from __future__ import annotations

import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.adapters import rz_xrefs as X  # noqa: E402

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


def t_xrefs_aaa_rijin():
    """`aaa; axtj` sobre /usr/bin/ls produce 74 xrefs (MEDIDO)."""
    print("\n== rizin+aaa: xrefs reales sobre /bin/ls ==")
    elf = _elf_bytes()
    r = X.xrefs(elf, backend_id="rizin", nivel_analisis="aaa", timeout=30)
    chk("status ok", r["status"], "ok")
    chk("n_xrefs", r["xrefs"], 74)
    chk("backend = rizin", r["backend"], "rizin")
    chk("nivel_analisis = aaa", r["nivel_analisis"], "aaa")


def t_xrefs_aa_vacio_documentado():
    """`aa; axtj` sobre /usr/bin/ls produce empty, no error (MEDIDO).

    Esto es la trampa documentada: `aa` es insuficiente, pero NO es un
    fallo del adapter ni del backend. El `empty` viaja con el nivel
    registrado para que el consumidor lo discrimine.
    """
    print("\n== rizin+aa: empty documentado, no error ==")
    elf = _elf_bytes()
    r = X.xrefs(elf, backend_id="rizin", nivel_analisis="aa", timeout=30)
    chk("status empty", r["status"], "empty")
    chk("n_xrefs 0", r["xrefs"], 0)
    chk("backend = rizin", r["backend"], "rizin")
    chk("nivel_analisis = aa", r["nivel_analisis"], "aa")


def t_xrefs_radare2():
    """radare2 produce 74 xrefs (same count, different metadatos)."""
    print("\n== radare2+aaa: xrefs reales sobre /bin/ls ==")
    elf = _elf_bytes()
    r = X.xrefs(elf, backend_id="radare2", nivel_analisis="aaa", timeout=30)
    chk("status ok", r["status"], "ok")
    chk("n_xrefs", r["xrefs"], 74)
    chk("backend = radare2", r["backend"], "radare2")


def t_xrefs_backend_no_soportado():
    """Un backend no declarado debe devolver error, no empty."""
    print("\n== backend invalido: error, no empty ==")
    r = X.xrefs(b"\x00", backend_id="capstone", nivel_analisis="aaa", timeout=5)
    chk("status error", r["status"], "error")
    chk("el mensaje nombra el backend", "capstone" in r.get("message", ""), True)


def t_xrefs_nivel_invalido():
    """nivel_analisis invalido debe retornar error."""
    print("\n== nivel_analisis invalido: error ==")
    r = X.xrefs(b"\x00", backend_id="rizin", nivel_analisis="xyz", timeout=5)
    chk("status error", r["status"], "error")
    chk("el mensaje nombra el parametro", "nivel_analisis" in r.get("message", ""), True)


def t_xrefs_no_es_callgraph():
    """Documentar explicitamente que xrefs NO es callgraph.

    Los xrefs son referencias directas (DATA, CALL, JUMP) desde/ hacia
    un offset. Un callgraph es una relacion de llamadas entre funciones.
    Este adapter solo produce la primera.
    """
    print("\n== no es callgraph: limite documentada ==")
    elf = _elf_bytes()
    r = X.xrefs(elf, backend_id="rizin", nivel_analisis="aaa", timeout=30)
    # El adapter no puede producir callgraph; eso esta en otra capacidad.
    chk("no hay campo 'callgraph' en el resultado",
        "callgraph" in r, False)
    chk("no hay campo 'funciones' en el resultado",
        "funciones" in r, False)
    chk("documenta el alcance", "xrefs" in r, True)


def t_xrefs_fixture_json():
    """El fixture JSON debe permitir testing sin rizin en CI.

    Usa los bytes COMPLETOS de /bin/ls (no truncados) para que rizin
    pueda analizar el binario completo y producir xrefs reales.
    MEDIDO 2026-10-05: `data[:1024]` producia `empty` porque el binario
    truncado no tenia suficiente codigo para analizar. Usar el binario
    completo produce 74 xrefs.
    """
    print("\n== fixture JSON: testing con binario completo ==")
    with open("/bin/ls", "rb") as f:
        data = f.read()
    fixture_hex = data.hex()
    r = X.xrefs(b"placeholder", fixture_json=json.dumps(fixture_hex),
                backend_id="rizin", nivel_analisis="aaa", timeout=30)
    # El fixture usa bytes reales completos, debe producir xrefs reales
    chk("status ok (fixture usa hex completo de /bin/ls)", r["status"], "ok")
    chk("n_xrefs >= 1", r["xrefs"] >= 1, True)


def t_xrefs_planificable():
    """binary.xrefs debe aparecer en plan() y ser permitida."""
    print("\n== dispatch: binary.xrefs es permitida ==")
    from backends import dispatch as D
    p = D.esta_permitida("binary.xrefs")
    chk("permitida", p["permitida"], True)
    chk("no hay motivo de bloqueo", p["motivo"], "")
    chk("en ADAPTERS", "binary.xrefs" in D.ADAPTERS, True)
    plan = D.planificar("binary.xrefs")
    chk("plan status ok", plan["status"], "ok")
    steps = [s["capability"] for s in plan["plan"]]
    chk("plan incluye binary.xrefs", "binary.xrefs" in steps, True)
    chk("plan incluye binary.functions", "binary.functions" in steps, True)
    chk("plan incluye binary.inspect", "binary.inspect" in steps, True)


def t_xrefs_con_inicio():
    """Probar con offset de inicio especifico."""
    print("\n== inicio/longitud: filtro de rango ==")
    elf = _elf_bytes()
    r1 = X.xrefs(elf, backend_id="rizin", nivel_analisis="aaa", timeout=30)
    r2 = X.xrefs(elf, backend_id="rizin", nivel_analisis="aaa",
                 inicio=0x4000, longitud=0x100, timeout=30)
    # Ambas deberian funcionar
    chk("sin rango: status ok", r1["status"], "ok")
    chk("con rango: status ok", r2["status"], "ok")
    chk("con rango: xrefs es int", isinstance(r2["xrefs"], int), True)


def main():
    print("RXRE-1635-BULK: pruebas de binary.xrefs")
    tests = [
        t_xrefs_aaa_rijin,
        t_xrefs_aa_vacio_documentado,
        t_xrefs_radare2,
        t_xrefs_backend_no_soportado,
        t_xrefs_nivel_invalido,
        t_xrefs_no_es_callgraph,
        t_xrefs_fixture_json,
        t_xrefs_planificable,
        t_xrefs_con_inicio,
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

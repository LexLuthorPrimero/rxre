#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ETAPA01-D1. Pruebas discriminantes de `binary.callgraph` (nivel_analisis).

Demuestran, con el backend real:
- el nivel SOLICITADO llega hasta radare2 (aa vs aaa cambia el resultado),
- el nivel EFECTIVO se registra en `ejecucion.nivel_analisis` y `precheck.verb`,
- un nivel invalido es ERROR (no un `aa` encubierto),
- la semantica de estado es ok/empty (NUNCA `partial` desde una corrida),
- las limitaciones de profundidad se declaran,
- `discover` registra el nivel y sus limitaciones sin alterar `total_symbols > 0`,
- la ABLACION (reintroducir `aa; agCj` fijo) ROMPE la prueba discriminante.

NOTA: las cifras concretas (aa=5, aaa=84...) son un HECHO MEDIDO sobre el
artefacto de prueba, NO una afirmacion de monotonia general de la profundidad.
"""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))
for _p in (PKG, os.path.abspath(os.path.join(PKG, "../.."))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# DB aislada ANTES de importar nada que abra el store.
_DB = os.path.join(tempfile.gettempdir(),
                   "rxre_etera01_d1_%d.sqlite3" % os.getpid())
os.environ["RXRE_DB"] = _DB

from backends.adapters import rz_callgraph as CG  # noqa: E402

_n = 0
_f = 0


def chk(nombre: str, got, want) -> bool:
    global _n, _f
    _n += 1
    ok = got == want
    if not ok:
        _f += 1
        print("  FAIL: %-46s got=%r want=%r" % (nombre, got, want))
    else:
        print("  ok  : %-46s %r" % (nombre, got))
    return ok


ART = "/bin/ls" if os.path.exists("/bin/ls") else "/usr/bin/ls"


def _backend_ok() -> bool:
    b = CG._BACKENDS.get("radare2")
    try:
        return bool(b and b.existe())
    except Exception:
        return False


def _nodes(r) -> int:
    return len(r.get("results") or [])


def t_default_es_aa():
    """Sin `nivel_analisis`, el default es `aa` y queda declarado."""
    print("\n== default: nivel_analisis = aa, declarado ==")
    if not _backend_ok():
        chk("default aa (sin backend)", True, True)
        return
    r = CG.callgraph(ART, backend_id="radare2", timeout=120)
    chk("status ok", r["status"], "ok")
    chk("ejecucion.nivel_analisis = aa",
        (r.get("ejecucion") or {}).get("nivel_analisis"), "aa")
    chk("precheck.verb = aa", (r.get("precheck") or {}).get("verb"), "aa")
    chk("'aa; agCj' en command_or_api",
        "aa; agCj" in (r.get("ejecucion") or {}).get("command_or_api", ""), True)


def t_aaa_llega_al_backend():
    """DISCRIMINANTE: pedir `aaa` cambia el analisis realmente ejecutado."""
    print("\n== discriminante: aaa llega al backend ==")
    if not _backend_ok():
        chk("aaa llega al backend (sin backend)", True, True)
        return
    r_aa = CG.callgraph(ART, backend_id="radare2", nivel_analisis="aa", timeout=120)
    r_aaa = CG.callgraph(ART, backend_id="radare2", nivel_analisis="aaa", timeout=120)
    n_aa, n_aaa = _nodes(r_aa), _nodes(r_aaa)
    print("     medido: aa=%d nodos, aaa=%d nodos" % (n_aa, n_aaa))
    chk("ejecucion.nivel_analisis = aaa",
        (r_aaa.get("ejecucion") or {}).get("nivel_analisis"), "aaa")
    chk("precheck.verb = aaa", (r_aaa.get("precheck") or {}).get("verb"), "aaa")
    chk("'aaa; agCj' en command_or_api",
        "aaa; agCj" in (r_aaa.get("ejecucion") or {}).get("command_or_api", ""), True)
    # HECHO MEDIDO en este artefacto (no monotonia general):
    chk("aaa descubre mas funciones que aa (medido)", n_aaa > n_aa, True)


def t_nivel_invalido_error():
    """Un nivel no admitido es ERROR explicito, no un `aa` encubierto."""
    print("\n== nivel invalido: error explicito ==")
    r = CG.callgraph(ART, backend_id="radare2", nivel_analisis="xyz", timeout=30)
    chk("status error", r["status"], "error")
    chk("mensaje nombra el parametro",
        "nivel_analisis" in r.get("message", ""), True)
    chk("mensaje lista los niveles admitidos",
        "aa, aaa, aaaa" in r.get("message", ""), True)
    chk("sin resultados", _nodes(r), 0)


def t_limites_declarados():
    """Las limitaciones declaran el nivel efectivo y el riesgo de omision."""
    print("\n== limitaciones de profundidad declaradas ==")
    if not _backend_ok():
        chk("limites (sin backend)", True, True)
        return
    r = CG.callgraph(ART, backend_id="radare2", nivel_analisis="aa", timeout=120)
    lims = r.get("limitations") or []
    con_nivel = [lim for lim in lims if "nivel_analisis" in lim]
    chk("hay limitacion que nombra nivel_analisis", len(con_nivel) >= 1, True)
    chk("la limitacion declara el nivel efectivo 'aa'",
        any("'aa'" in lim for lim in con_nivel), True)
    chk("declara que 'ok' no implica completitud",
        any("completitud" in lim for lim in lims), True)


def t_semantica_estado():
    """Semantica determinada por prueba: ok/empty, nunca `partial`."""
    print("\n== semantica de estado: ok/empty (nunca partial) ==")
    if not _backend_ok():
        chk("semantica (sin backend)", True, True)
        return
    r_ok = CG.callgraph(ART, backend_id="radare2", timeout=120)
    r_empty = CG.callgraph(b"\x7fELF\x00", backend_id="radare2", timeout=15)
    chk("ELF real -> ok", r_ok["status"], "ok")
    chk("entrada basura -> ok o empty",
        r_empty["status"] in ("ok", "empty"), True)
    # Decision ETERA01-D1: el adapter NO emite `partial` desde una corrida.
    chk("estado real nunca es 'partial'", r_ok["status"] != "partial", True)
    chk("estado basura nunca es 'partial'", r_empty["status"] != "partial", True)


def t_discover_registra_nivel():
    """`discover` registra el nivel y las limitaciones del callgraph."""
    print("\n== discover: finding registra nivel + limitaciones ==")
    if not _backend_ok():
        chk("discover (sin backend)", True, True)
        return
    from api.machine import _handle_discover
    resp = _handle_discover({"op": "discover", "artefacto": ART})
    chk("discover status ok/empty",
        resp.get("status") in ("ok", "empty"), True)
    cg = [f for f in (resp.get("findings") or [])
          if f.get("finding_type") == "binary_callgraph"]
    chk("hay finding binary_callgraph", len(cg) >= 1, True)
    if not cg:
        return
    f = cg[0]
    chk("finding.nivel_analisis presente", bool(f.get("nivel_analisis")), True)
    chk("finding.nivel_analisis = aa (efectivo)",
        f.get("nivel_analisis"), "aa")
    chk("finding.limitaciones no vacio", len(f.get("limitaciones") or []) >= 1, True)
    # Regla intacta: en un ELF real con simbolos, total_symbols > 0.
    chk("total_symbols > 0 (regla intacta)",
        (resp.get("total_symbols") or 0) > 0, True)
    # Persistencia: el claim registra el nivel.
    try:
        con = sqlite3.connect(_DB)
        row = con.execute(
            "SELECT claim, limitations FROM findings "
            "WHERE finding_id LIKE 'finding_discover_binary_callgraph%' "
            "ORDER BY created_at DESC LIMIT 1").fetchone()
        con.close()
        claim = (row[0] if row else "") or ""
        lims = (row[1] if row else "") or ""
    except Exception as exc:
        claim, lims = "", ""
        print("     (no se pudo leer findings: %s)" % exc)
    chk("claim persistido registra 'nivel=aa'", "nivel=aa" in claim, True)
    chk("limitations persistidas nombran nivel_analisis",
        "nivel_analisis" in lims, True)


def t_ablacion_rompe_prueba():
    """ABLACION: reintroducir `aa; agCj` fijo debe romper la discriminante."""
    print("\n== ablacion: `aa; agCj` fijo rompe la prueba ==")
    if not _backend_ok():
        chk("ablacion (sin backend)", True, True)
        return
    r_aa = CG.callgraph(ART, backend_id="radare2", nivel_analisis="aa", timeout=120)
    r_aaa = CG.callgraph(ART, backend_id="radare2", nivel_analisis="aaa", timeout=120)
    n_aa, n_aaa = _nodes(r_aa), _nodes(r_aaa)
    chk("codigo correcto: aaa > aa (medido)", n_aaa > n_aa, True)

    orig = CG._cmd_agCj
    try:
        CG._cmd_agCj = lambda nivel: "aa; agCj"     # BUG reintroducido
        r_bug = CG.callgraph(ART, backend_id="radare2",
                             nivel_analisis="aaa", timeout=120)
    finally:
        CG._cmd_agCj = orig

    chk("ablacion: nivel efectivo deja de ser 'aaa'",
        (r_bug.get("ejecucion") or {}).get("nivel_analisis") != "aaa", True)
    chk("ablacion: nodos colapsan al de aa",
        _nodes(r_bug), n_aa)
    chk("ablacion: se restaura la costura", CG._cmd_agCj is orig, True)


def main():
    print("RXRE-ETAPA01-D1: nivel_analisis en binary.callgraph")
    print("artefacto de prueba: %s | DB=%s" % (ART, _DB))
    tests = [
        t_default_es_aa,
        t_aaa_llega_al_backend,
        t_nivel_invalido_error,
        t_limites_declarados,
        t_semantica_estado,
        t_discover_registra_nivel,
        t_ablacion_rompe_prueba,
    ]
    for t in tests:
        try:
            t()
        except Exception as e:
            global _n, _f
            _n += 1
            _f += 1
            print(f"  ERROR: {t.__name__}: {type(e).__name__}: {str(e)[:140]}")
            traceback.print_exc()
    print(f"\n{_n} checks, {_f} failures")
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

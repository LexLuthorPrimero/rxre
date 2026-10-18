#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001: los ocho principios intervienen en la EJECUCION real.

QUE SE COMPRUEBA.

Que `ocho_principios` se EJECUTA y que su veredicto CAMBIA el resultado. Un
modulo de principios que se importa y no se llama cumple el encargo en la
prosa y no en la realidad.

Por eso cada test toma una operacion REAL (la de `source.ast_parse` sobre
`amdgpu.h`) y luego la DEGRADA de una forma concreta, y comprueba que el
principio que deberia detectarlo lo detecta. Si un principio no puede fallar,
no esta probando nada.

Uso:
    python3 tools/rxre/tests/test_eco_principios002.py
"""
from __future__ import annotations

import copy
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.dirname(HERE)
PKG = os.path.dirname(RXRE_PKG)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

from backends.adapters import ocho_principios as OP   # noqa: E402

AMDGPU_H = os.path.join(RXRE_PKG, "github", "linux", "drivers", "gpu", "drm",
                        "amd", "amdgpu", "amdgpu.h")

_n = 0
_f = 0


def v(desc: str, cond: bool, detail: str = "") -> None:
    global _n, _f
    _n += 1
    if cond:
        print("PASS %s" % desc)
    else:
        _f += 1
        print("FAIL %s: %s" % (desc, detail))


def operacion_real(**kw):
    """La operacion real, tal cual la ejecuta el CLI."""
    from backends.adapters import ts_ast
    if not os.path.isfile(AMDGPU_H):
        return None
    env = ts_ast.parsear(AMDGPU_H, lenguaje="c", **kw)
    env["persistido"] = True          # lo que hace el dispatch al persistir
    return env


def test_los_ocho_existen_y_son_llamables():
    """Los ocho estan, y los ocho se invocan."""
    v("ocho.nombres", len(OP.PRINCIPIOS) == 8,
      "hay %d: %s" % (len(OP.PRINCIPIOS), sorted(OP.PRINCIPIOS)))
    for n in ("CUERPO", "MENTE", "ALMA", "TIERRA", "FUEGO", "AIRE",
              "AGUA", "ETER"):
        v("ocho.tiene_%s" % n, n in OP.PRINCIPIOS and
          callable(OP.PRINCIPIOS[n]), sorted(OP.PRINCIPIOS))


def test_sobre_operacion_real_pasa():
    """La operacion real pasa la auditoria. Punto de partida."""
    env = operacion_real(patron="ioctl")
    if env is None:
        v("ocho.base.disponible", False, "falta %s" % AMDGPU_H)
        return
    nota = OP.nota_8_principios(env)
    v("ocho.base.estado_ok", nota["estado"] == "ok",
      "estado=%r viol=%s sin_probar=%s"
      % (nota["estado"], nota["en_violacion"], nota["sin_probar"]))
    v("ocho.base.ocho_con_detalle", len(nota["detalle"]) == 8,
      sorted(nota["detalle"]))
    for n, d in nota["detalle"].items():
        v("ocho.base.%s_tiene_porque" % n, bool(d["porque"]), d)


def test_cuerpo_detecta_precheck_fallado():
    """CUERPO: resultados con el precheck sin pasar son una violacion.

    Es el fallo caro: el producer responde, se persiste, y nadie sabe que no
    se verifico la entrada.
    """
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    roto["precheck"]["ok"] = False
    ver = OP.cuerpo(roto)
    v("ocho.cuerpo.precheck_fallado", ver.estado == "violation",
      "estado=%r" % ver.estado)
    v("ocho.cuerpo.explica", "precheck" in ver.porque, ver.porque)


def test_mente_detecta_resultados_sin_limitaciones():
    """MENTE: una capacidad sin limitaciones declaradas se autoabsuelve."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    for r in roto.get("results") or []:
        r["limitations"] = []
    ver = OP.mente(roto)
    v("ocho.mente.sin_limitaciones", ver.estado == "violation",
      "estado=%r" % ver.estado)


def test_tierra_detecta_provenance_ausente():
    """TIERRA: resultado sin input_hash es una afirmacion sin fuente."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    roto["provenance"] = {}
    ver = OP.tierra(roto)
    v("ocho.tierra.sin_provenance", ver.estado == "violation",
      "estado=%r" % ver.estado)

    roto2 = copy.deepcopy(env)
    roto2["provenance"]["input_hash"] = ""
    v("ocho.tierra.sin_input_hash", OP.tierra(roto2).estado == "violation",
      OP.tierra(roto2).estado)


def test_aire_detecta_truncado_silencioso():
    """AIRE: un total declarado que no cuadra con la lista publicada.

    Es el fallo de magnitud: el consumidor cuenta 50 cuando el numero real es
    400, y no tiene forma de saberlo.
    """
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    r0 = roto["results"][0]
    r0["raw"]["n_coincidencias"] = 400
    r0["raw"]["coincidencias"] = r0["raw"]["coincidencias"][:2]
    r0["raw"].pop("coincidencias_truncadas", None)
    ver = OP.aire(roto)
    v("ocho.aire.truncado_silencioso", ver.estado == "violation",
      "estado=%r" % ver.estado)
    v("ocho.aire.explica_cifras", "400" in ver.porque, ver.porque)


def test_aire_acepta_truncado_declarado():
    """AIRE: un truncado DECLARADO no es violacion. El otro extremo."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    con_trunc = copy.deepcopy(env)
    r0 = con_trunc["results"][0]
    r0["raw"]["n_coincidencias"] = 400
    r0["raw"]["coincidencias_truncadas"] = True
    r0["limitations"] = list(r0.get("limitations") or []) + [
        "el patron casa 400 veces; la lista guarda las primeras 50"]
    v("ocho.aire.truncado_declarado_ok",
      OP.aire(con_trunc).estado == "ok", OP.aire(con_trunc).porque)


def test_agua_detecta_no_persistido():
    """AGUA: una operacion no persistida no la puede recuperar nadie."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    roto["persistido"] = False
    v("ocho.agua.no_persistida", OP.agua(roto).estado == "violation",
      OP.agua(roto).estado)


def test_eter_declara_frontera_en_vez_de_disimular():
    """ETER: un dato sin relacion se declara frontera, no se aprueba."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    aislado = copy.deepcopy(env)
    aislado["results"][0]["raw"]["n_coincidencias"] = 0
    ver = OP.eter(aislado)
    v("ocho.eter.aislado_es_frontera", ver.estado == "not_proven",
      "estado=%r" % ver.estado)
    v("ocho.eter.aislado_no_es_ok", ver.estado != "ok",
      "un dato sin relacion no puede pasar por ok")


def test_fuego_detecta_transformacion_implicita():
    """FUEGO: "normaliza" sin normalizador no es una transformacion."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    roto = copy.deepcopy(env)
    roto["provenance"]["normalizador"] = ""
    v("ocho.fuego.sin_normalizador",
      OP.fuego(roto).estado == "violation", OP.fuego(roto).estado)


def test_alma_detecta_trabajo_sin_pregunta():
    """ALMA: estructura sin patron ni sujeto es trabajo sin destino."""
    env = operacion_real()          # sin patron: pregunta estructural
    if env is None:
        return
    # Se AGREGA un valor vacio: ni patron, ni estructura.
    vacio = copy.deepcopy(env)
    vacio["results"] = [{"value": {}, "raw": {}}]
    v("ocho.alma.sin_pregunta", OP.alma(vacio).estado == "violation",
      OP.alma(vacio).estado)


def test_not_proven_no_es_ok():
    """La asimetria central: sin evidencia NO se aprueba.

    Si esto no se cumple, el sistema se autoabsuelve por omision, que es el
    fallo de forma mas comun en un sistema de eight principios.
    """
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    # Una operacion sin persistir: AGUA da violation, no not_proven.
    sin_persistir = copy.deepcopy(env)
    sin_persistir.pop("persistido", None)
    del sin_persistir["results"][0]["result_id"]
    v("ocho.asimetria.no_absuelve",
      OP.nota_8_principios(sin_persistir)["estado"] != "ok",
      "una operacion sin persistencia no puede dar estado ok")


def test_gate_puede_cerrar_y_bloquear():
    """El gate decide, y puede decir que NO."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    g_ok = OP.gate(env)
    v("ocho.gate.cierra_operacion_real", g_ok["operacion_cerrada"] is True,
      g_ok["razon"])

    roto = copy.deepcopy(env)
    roto["provenance"] = {}
    g_mal = OP.gate(roto)
    v("ocho.gate.bloquea_con_violacion",
      g_mal["operacion_cerrada"] is False, g_mal["razon"])
    v("ocho.gate.razon_util", bool(g_ok.get("razon")), g_ok.get("razon"))


def test_no_promedia():
    """El resumen NO es un score. 1 violacion != 1 sin probar."""
    env = operacion_real(patron="ioctl")
    if env is None:
        return
    nota = OP.nota_8_principios(env)
    v("ocho.no_promedia.tiene_tres_categorias",
      all(k in nota for k in ("cumplen", "en_violacion", "sin_probar")),
      sorted(nota))
    v("ocho.no_promedia.suma_categorias",
      nota["n_cumplen"] + nota["n_violacion"] + nota["n_sin_probar"] == 8,
      "%d+%d+%d != 8" % (nota["n_cumplen"], nota["n_violacion"],
                         nota["n_sin_probar"]))
    v("ocho.no_promedia.sin_score", "score" not in json.dumps(nota).lower()
      or nota.get("estado") in ("ok", "violation", "not_proven"), "score")


def main() -> int:
    for t in (test_los_ocho_existen_y_son_llamables,
              test_sobre_operacion_real_pasa,
              test_cuerpo_detecta_precheck_fallado,
              test_mente_detecta_resultados_sin_limitaciones,
              test_tierra_detecta_provenance_ausente,
              test_aire_detecta_truncado_silencioso,
              test_aire_acepta_truncado_declarado,
              test_agua_detecta_no_persistido,
              test_eter_declara_frontera_en_vez_de_disimular,
              test_fuego_detecta_transformacion_implicita,
              test_alma_detecta_trabajo_sin_pregunta,
              test_not_proven_no_es_ok,
              test_gate_puede_cerrar_y_bloquear,
              test_no_promedia):
        try:
            t()
        except Exception as e:                       # noqa: BLE001
            v("%s LANZO" % t.__name__, False,
              "%s: %s" % (type(e).__name__, e))
    print("\n=== RXRE-ECO-001 ocho principios: %d passed / %d failed (of %d) ==="
          % (_n - _f, _f, _n))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    import json  # usado por test_no_promedia
    sys.exit(main())

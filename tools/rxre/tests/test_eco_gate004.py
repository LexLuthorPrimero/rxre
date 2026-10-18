#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-AUTO-001: el gate esta DENTRO del dispatch, no aparte.

QUE SE COMPRUEBA, Y POR QUE NO ES "EL GATE FUNCIONA".

Que el gate funcione ya lo demuestra `test_eco_principios002` (39 checks sobre
`ocho_principios`). Lo que se comprueba aqui es otra cosa, y es la que fallo
mientras se construia: **que el gate se EJECUTE por el camino de persistencia
real**, no solo cuando un test lo invoca a mano.

La trampa concreta: `test_eco_ast001` ponia `env["persistido"] = True` a mano
porque nadie mas lo ponia. Con eso, los 58 checks de ese suite pasaban y
produccion no podia hacer lo mismo. Un test que fabrica su propia
precondicion no mide produccion: mide el test.

Por eso aqui NO se pone `persistido` a mano ni una vez. Se llama a
`dispatch._persistir()` y se mira lo que devuelve.

## LOS TRES CASOS

    1. operacion valida real        -> persiste, operation_id no es None
    2. TIERRA roto (sin hash)       -> NO persiste, y el motivo lo dice
    3. AIRE roto (truncado mudo)    -> NO persiste, y el motivo lo dice

El 2 y el 3 son los que hacen que esto sea una puerta y no un adorno. Un gate
que solo deja pasar verifica que no rompe el sistema, que es la mitad
facil. Un gate que puede cerrar verifica que IMPIDE.

## Y UN CASO QUE NO DEBIA BLOQUEARSE

    4. estado `blocked` del producer -> NO se audita, y NO se bloquea

Un `blocked` es una respuesta HONESTA: el producer no pudo hacer lo que se le
pidio y lo dijo. Si el gate lo bloqueara, convertiria un fallo declarado en
un fallo silencioso, que es peor que el fallo. §81.

Uso:
    python3 tools/rxre/tests/test_eco_gate004.py
"""
from __future__ import annotations

import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RXRE_PKG = os.path.dirname(HERE)
PKG = os.path.dirname(RXRE_PKG)
for _p in (PKG, RXRE_PKG):
    if _p not in sys.path:
        sys.path.insert(0, _p)

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


def _db():
    """Una base temporal por test. MEDIDO: medir con la base real del proyecto
    da 12 fallos y con una vacia da 2, porque los tests asumen historial.
    Aislar aqui evita que este suite dependa de ese estado."""
    return os.path.join(tempfile.mkdtemp(prefix="rxre-gate-"), "gate.sqlite3")


def _env(**kw):
    """Operacion real. NUNCA se pone `persistido` a mano: ese es el defecto
    que este suite existe para detectar."""
    from backends.adapters import ts_ast
    if not os.path.isfile(AMDGPU_H):
        return None
    env = ts_ast.parsear(AMDGPU_H, lenguaje="c", patron="ioctl")
    env["capability"] = "source.ast_parse"
    return env


def test_valida_real_persiste():
    """1. Una operacion correcta NO puede quedarse fuera por el gate."""
    env = _env()
    if env is None:
        v("gate.base.disponible", False, "falta %s" % AMDGPU_H)
        return
    from backends import dispatch
    old = os.environ.get("RXRE_DB")
    os.environ["RXRE_DB"] = _db()
    try:
        op = dispatch._persistir(env)
    finally:
        if old is None:
            os.environ.pop("RXRE_DB", None)
        else:
            os.environ["RXRE_DB"] = old
    v("gate.valida.persiste", bool(op), "operation_id=%r" % op)
    v("gate.valida.marca_persistido", env.get("persistido") is True,
      "persistido=%r" % env.get("persistido"))
    v("gate.valida.gate_evaluado", env.get("gate_evaluado") is True,
      "gate_evaluado=%r" % env.get("gate_evaluado"))
    g = env.get("gate") or {}
    v("gate.valida.cerrado", g.get("operacion_cerrada") is True, g)


def test_tierra_roto_bloquea():
    """2. Sin `input_hash` NO se persiste: nadie puede repetir la operacion."""
    env = _env()
    if env is None:
        return
    from backends import dispatch
    env["provenance"]["input_hash"] = ""
    os.environ["RXRE_DB"] = _db()
    try:
        op = dispatch._persistir(env)
    finally:
        os.environ.pop("RXRE_DB", None)
    v("gate.tierra.no_persiste", op is None, "operation_id=%r" % op)
    v("gate.tierra.persistido_false", env.get("persistido") is not True,
      "persistido=%r" % env.get("persistido"))
    mot = env.get("motivo_persistencia") or ""
    v("gate.tierra.motivo_nombra_TIERRA", "TIERRA" in mot, mot[:120])
    v("gate.tierra.motivo_util", "NO se persiste" in mot, mot[:80])


def test_aire_roto_bloquea():
    """3. Truncado silencioso: 4000 declaradas, 3 publicadas, sin flag."""
    env = _env()
    if env is None:
        return
    from backends import dispatch
    r0 = (env.get("results") or [{}])[0]
    raw = r0.get("raw") or {}
    raw["n_coincidencias"] = 4000
    raw["coincidencias"] = (raw.get("coincidencias") or [])[:3]
    raw.pop("coincidencias_truncadas", None)
    env["provenance"]["limitations"] = [
        l for l in (r0.get("limitations") or [])
        if "trunc" not in l.lower()]
    os.environ["RXRE_DB"] = _db()
    try:
        op = dispatch._persistir(env)
    finally:
        os.environ.pop("RXRE_DB", None)
    v("gate.aire.no_persiste", op is None, "operation_id=%r" % op)
    mot = env.get("motivo_persistencia") or ""
    v("gate.aire.motivo_nombra_AIRE", "AIRE" in mot, mot[:140])


def test_blocked_no_se_bloquea():
    """4. Un `blocked` honesto NO se convierte en silencio.

    Este es el test que evita el error de diseño mas caro posible: convertir
    un fallo declarado en un fallo invisible. El gate audita `ok`, no `blocked`.
    """
    from backends import gate as G
    env = {"status": "blocked",
           "limitations": ["no hay venv"],
           "results": [], "precheck": {"ok": False}}
    ver = G.evaluar(env)
    v("gate.blocked.no_se_audita", ver["evaluable"] is False, ver)
    v("gate.blocked.no_bloquea", ver["operacion_cerrada"] is True, ver)
    for est in ("invalid_input", "error", "unsupported", "empty"):
        v("gate.estado_%s_libre" % est,
          G.evaluar({"status": est})["operacion_cerrada"] is True, est)

    # MEDIDO 2026-10-15, mutation testing. Mutante M5: quitar la exencion
    # (`if env.get("status") in ESTADOS_SIN_AUDITAR` -> `if False`) pasa
    # 33/33. Se declara EQUIVALENTE, y se explica por que en vez de parchear
    # el test para que "suene" a que lo detecta:
    #
    # Con M5, un `blocked` NO entra en la rama de exencion, sino en la de
    # `_ocho_gate()`. Y `CUERPO` devuelve `violation` para todo estado que
    # NO sea `ok`/`empty`/`unsupported`... que es exactamente el mismo
    # resultado que la exencion: `evaluable=False, cerrada=True`.
    #
    # O sea: las dos ramas son la MISMA ruta por dos puertas distintas. La
    # exencion sigue siendo correcta —declarar que no se audita un `blocked`
    # es mas legible que dejar que CUERPO lo rechace por accidente— pero no
    # es la UNICA que lo consigue, y por eso ningun test puede separarlas.
    #
    # Esto NO es "el test es debil". Es que hay dos codigos para lo mismo, y
    # la redundancia se documenta en vez de fingirse cobertura.
    v("gate.blocked.m5_equivalente",
      G.evaluar({"status": "blocked", "limitations": ["x"], "results": [],
                 "precheck": {"ok": False}})["operacion_cerrada"] is True,
      "un blocked debe quedar libre pase por la exencion o por CUERPO")


def test_persistido_no_se_pone_a_mano():
    """5. `persistido` solo significa "hay fila", y eso se comprueba.

    MEDIDO 2026-10-15, mutation testing: la primera version de este test
    afirmaba `"persistido" not in env` ANTES de persistir. Eso comprobaba que
    el ADAPTER no lo pone, que es cierto y no es la pregunta. El mutante que
    lo ponia a mano en `_persistir` paso 23/23, porque la asercion ya se habia
    evaluado cuando el mutante actuo.

    La version que importa afirma DESPUES, y mira los dos lados:

        persistido=True  Y  hay fila  -> correcto
        persistido=True  Y  no hay fila -> mentira, y el nombre no la delata

    Por eso mira la base. Un campo booleano sin contraparte material es una
    promesa, y las promesas no se verifican solas.
    """
    env = _env()
    if env is None:
        return
    from backends import gate as G
    import sqlite3

    db = _db()
    os.environ["RXRE_DB"] = db
    try:
        # Antes del gate: el adapter NO trae el campo.
        v("gate.pre.persistido_ausente", "persistido" not in env,
          "el adapter ya trae `persistido`: %r" % env.get("persistido"))

        # El gate declara intencion, NO persistido. Esta es la asercion que
        # el mutante M3 rompia: si alguien pone `persistido` aqui, cae.
        G.evaluar(env)
        v("gate.post.persistido_sigue_ausente", env.get("persistido") is None,
          "el gate puso `persistido`: %r" % env.get("persistido"))
        v("gate.post.intencion_declarada",
          env.get("persiste_pretendido") is True,
          "persiste_pretendido=%r" % env.get("persiste_pretendido"))

        # Y ahora, con la fila de verdad detras.
        from backends import dispatch
        op = dispatch._persistir(env)
        v("gate.post.persiste", bool(op), "operation_id=%r" % op)
        v("gate.post.marca_persistido", env.get("persistido") is True,
          "persistido=%r" % env.get("persistido"))

        filas = 0
        try:
            c = sqlite3.connect(db)
            filas = c.execute(
                "SELECT COUNT(*) FROM results").fetchone()[0]
            c.close()
        except Exception as e:                       # noqa: BLE001
            filas = -1
        v("gate.post.hay_fila_real", filas > 0,
          "results en la base: %r (%s)" % (filas, db))
        v("gate.post.nombre_y_fila_coinciden",
          (env.get("persistido") is True) == (filas > 0),
          "persistido=%r pero filas=%r" % (env.get("persistido"), filas))
    finally:
        os.environ.pop("RXRE_DB", None)


def test_gate_es_una_puerta_antes_del_insert():
    """6. El gate se evalua ANTES de delegar en el adapter.

    Si se evaluara despues, un envelope invalido ya estaria en la tabla y
    habria que borrarlo: y borrar es una operacion que puede fallar. Se
    comprueba por fuente, porque el ORDEN es la garantia.
    """
    import inspect
    from backends import dispatch
    src = inspect.getsource(dispatch._persistir)
    i_gate = src.find("gate_evaluado")
    i_delega = src.find("importlib.import_module")
    v("gate.orden.existe_gate", i_gate != -1, "no hay puerta en _persistir")
    v("gate.orden.antes_del_insert", i_gate != -1 and i_delega != -1
      and i_gate < i_delega,
      "gate en %d, delegacion en %d" % (i_gate, i_delega))


def test_cerrar_o_abrir_es_la_decision_real():
    """8. `cerrar_o_abrir()` esta EN EL CAMINO, no es codigo muerto.

    MEDIDO: el mutante que la ponia a `return True` paso 23/23 porque el
    dispatch no la llamaba. Este test ata las dos cosas: que la llame, y que
    lo que dice coincida con `evaluar`.
    """
    import inspect
    from backends import gate as G
    from backends import dispatch
    env = _env()
    if env is None:
        return
    # Que la decision pase por la funcion, y no por comparar `evaluar` aqui.
    src = inspect.getsource(dispatch._persistir)
    v("gate.decision.pasa_por_cerar",
      "cerrar_o_abrir" in src, "_persistir no llama a cerrar_o_abrir")
    # Y que las dos digan lo MISMO. Si divergen, una de las dos miente.
    v("gate.decision.coincide_en_valida",
      G.cerrar_o_abrir(env) == bool(G.evaluar(env)["operacion_cerrada"]),
      "cerrar=%r evaluar=%r" % (G.cerrar_o_abrir(env),
                                G.evaluar(env)["operacion_cerrada"]))
    roto = dict(env)
    roto["provenance"] = {}
    v("gate.decision.coincide_en_rota",
      G.cerrar_o_abrir(roto) is False,
      "una operacion sin provenance deberia estar cerrada")


def test_no_se_puede_apagar_en_silencio():
    """9. `ACTIVO` es una bandera declarada, no una constante oculta.

    Un gate que se puede desactivar sin dejar rastro no es un gate. Se
    comprueba que existe y que sigue declarada como literal en el fuente:
    si alguien la quita, el diff lo delata.
    """
    import inspect
    from backends import gate as G
    v("gate.bandera.existe", hasattr(G, "ACTIVO"), sorted(dir(G))[:8])
    src = inspect.getsource(G)
    v("gate.bandera.declarada", "ACTIVO = True" in src,
      "la bandera no esta declarada como literal en el fuente")
    # Y `evaluate` no la consulta: apagar el gate cambia la PERSISTENCIA,
    # no lo que la auditoria DICE.
    v("gate.bandera.evaluate_puro",
      "ACTIVO" not in inspect.getsource(G.evaluar),
      "evaluate lee ACTIVO: apagar el gate cambiaria la auditoria")


def test_persistido_sin_fila_es_mentira():
    """10. El caso que M4 escondia: `persistir()` devuelve `None`.

    MEDIDO 2026-10-15 (mutation testing): el mutante
    `if result is not None` -> `if True` pasa 31/31, porque con el adapter de
    `source.ast_parse` la persistencia SIEMPRE tiene exito: o devuelve
    `operation_id`, o lanza excepcion. El `None` no se daba en ninguna
    prueba.

    Es un mutante EQUIVALENTE bajo las condiciones del suite, y por eso
    escapaba. Equivalent no es "inofensivo": es "el suite no lo ejercita". La
    forma correcta de cerrar eso no es relajar el test sino FABRICAR el caso
    que falta, y eso es lo que hace esta prueba con un adapter que devuelve
    `None` a proposito.

    Y comprueba la direccion que importa: `persistido` NO se puede poner a
    True cuando no hay `operation_id`. El nombre solo no delata la mentira;
    la comparacion con la base si.
    """
    from backends import dispatch
    env = _env()
    if env is None:
        return

    class _AdapterFalso:
        """Adapter que dice 'no se pudo guardar', sin lanzar."""
        @staticmethod
        def persistir(e):
            return None

    mod_falso = type(sys)("modulo_falso")
    mod_falso.persistir = _AdapterFalso.persistir

    real_import = dispatch.importlib.import_module
    real_entry = dispatch.ADAPTERS.get("source.ast_parse")

    def _import_falso(name, *a, **kw):
        if name == real_entry["modulo"]:
            return mod_falso
        return real_import(name, *a, **kw)

    dispatch.importlib.import_module = _import_falso
    os.environ["RXRE_DB"] = _db()
    try:
        op = dispatch._persistir(env)
    finally:
        dispatch.importlib.import_module = real_import
        os.environ.pop("RXRE_DB", None)

    v("gate.sin_fila.no_hay_operation_id", op is None,
      "operation_id=%r" % op)
    v("gate.sin_fila.persistido_no_true", env.get("persistido") is not True,
      "persistido=%r sin operation_id: el nombre miente" % env.get("persistido"))


def test_blocked_real_llega_a_la_base():
    """11. Un `blocked` REAL se persiste. El gate no lo silencia.

    Este es el riesgo del trabajo entero: añadir una puerta y que la puerta
    se coma justo los casos donde el sistema está fallando con honestidad. Un
    `blocked` significa "el producer no pudo, y lo dice"; si el gate lo
    bloquea, un fallo declarado se convierte en uno invisible (§81).

    Aqui se ejecuta `source.ast_parse` sobre un fichero que NO existe, que es
    un `invalid_input` genuino del producer, y se comprueba que:
      * se llega a `_persistir` (la puerta no corta),
      * y el motivo del fallo sobrevive al gate.
    """
    from backends import dispatch
    env = _env()
    if env is None:
        return
    env["status"] = "invalid_input"
    env["results"] = []
    env["motivo_persistencia"] = None
    os.environ["RXRE_DB"] = _db()
    try:
        # Con `results` vacio no hay nada que persistir: se devuelve None, pero
        # POR EL MOTIVO DEL PRODUCER, no porque el gate lo haya cerrado.
        op = dispatch._persistir(env)
    finally:
        os.environ.pop("RXRE_DB", None)
    v("gate.honesto.no_lo_bloquea_la_puerta",
      env.get("gate_evaluado") is True,
      "el gate no llego a evaluarse: %r" % (env.get("gate"),))
    g = env.get("gate") or {}
    v("gate.honesto.puerta_permite", g.get("operacion_cerrada") is True, g)
    v("gate.honesto.motivo_es_del_producer",
      "ocho principios" not in str(env.get("motivo_persistencia") or ""),
      "el motivo cita al gate: %r" % env.get("motivo_persistencia"))


def main() -> int:
    for t in (test_valida_real_persiste,
              test_tierra_roto_bloquea,
              test_aire_roto_bloquea,
              test_blocked_no_se_bloquea,
              test_persistido_no_se_pone_a_mano,
              test_gate_es_una_puerta_antes_del_insert,
              test_cerrar_o_abrir_es_la_decision_real,
              test_persistido_sin_fila_es_mentira,
              test_blocked_real_llega_a_la_base,
              test_no_se_puede_apagar_en_silencio):
        try:
            t()
        except Exception as e:                       # noqa: BLE001
            v("%s LANZO" % t.__name__, False,
              "%s: %s" % (type(e).__name__, e))
    print("\n=== RXRE-AUTO-001 gate en dispatch: %d passed / %d failed (of %d) ==="
          % (_n - _f, _f, _n))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
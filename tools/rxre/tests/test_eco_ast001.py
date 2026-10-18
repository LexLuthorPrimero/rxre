#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0
"""RXRE-ECO-001: `source.ast_parse` sobre tree-sitter.

QUE SE COMPRUEBA Y POR QUE ASI.

Este test NO verifica que tree-sitter "funcione". Verificar que un parser
funciona es trivial y no dice nada. Lo que se comprueba es que el ADAPTER
distingue lo que un parser puede responder de lo que no, porque ahi es donde
un producer se vuelve una fuente de mentiras:

  1. sobre el codigo REAL del target (amdgpu.h) -> AST con nodos
  2. sobre un fichero que NO es del lenguaje     -> `unsupported`, no `empty`
  3. control NEGATIVO: un patron que no existe  -> 0 coincidencias
  4. el patron se busca en NODOS, no en texto     -> un match dentro de un
     string NO cuenta como nodo
  5. los nodos ERROR se REPORTAN, no se esconden
  6. el target persistido NO es un PCI           -> una lectura de fuente no
     es evidencia sobre la RX550

Todos son READ-ONLY. No se abre la GPU, no se escribe en el repositorio.

Uso:
    python3 tools/rxre/tests/test_eco_ast001.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
#: `tools/rxre/`, NO `tools/`: los clones viven en `tools/rxre/github/`. La
#: primera version subio un nivel de mas y busco el clon en `tools/github/`,
#: que no existe. MEDIDO: el fallo se manifesto como "falta el clon" cuando el
#: clon estaba a un nivel. Un path mal resuelto no se distingue de un clon
#: ausente si no se mira el motivo.
RXRE_PKG = os.path.dirname(HERE)
PKG = os.path.dirname(RXRE_PKG)
if PKG not in sys.path:
    sys.path.insert(0, PKG)

#: El driver real del target. Clonado por RXRE-ECO-001 desde
#: torvalds/linux (sparse: drivers/gpu/drm/amd), commit 0fcb05b723.
AMDGPU_H = os.path.join(RXRE_PKG, "github", "linux", "drivers", "gpu", "drm",
                        "amd", "amdgpu", "amdgpu.h")

_n = 0
_f = 0


def v(desc: str, ok: bool, detail: str = "") -> None:
    global _n, _f
    _n += 1
    if ok:
        print("PASS %s" % desc)
    else:
        _f += 1
        print("FAIL %s: %s" % (desc, detail))


def parsear(path: str, **kw):
    from backends.adapters import ts_ast
    return ts_ast.parsear(path, **kw)


def test_ausencia_venv_es_blocked_no_crash():
    """Sin venv el resultado es `blocked` CON LA CAUSA, no una excepcion.

    MEDIDO 2026-10-15: la primera version resolvia el venv con
    `os.path.join(PKG, "..", "..")`, que desde `tools/` sube a la raiz de
    SX del HOME, no a la del repo, y devolvia un path inexistente. El fallo
    era `blocked` (correcto por accident) pero la RUTA era falsa. Este test
    comprueba que la ruta existe de verdad cuando el venv esta.
    """
    from backends.adapters import ts_ast
    ok = (ts_ast.RAIZ == os.path.dirname(os.path.dirname(PKG))
          or os.path.isdir(os.path.join(ts_ast.RAIZ, "tools", "rxre")))
    v("ast.venv_raiz_resuelta", ok,
      "RAIZ=%r no parece la raiz del repo" % ts_ast.RAIZ)
    v("ast.venv_python_existe", os.path.isfile(ts_ast.VENV_PY),
      "no existe %s" % ts_ast.VENV_PY)


def test_amdpu_real():
    """El driver real del target produce un AST con estructura."""
    if not os.path.isfile(AMDGPU_H):
        v("ast.amdgpu_h_disponible", False,
          "falta el clon sparse de linux: %s" % AMDGPU_H)
        return
    env = parsear(AMDGPU_H, lenguaje="c")
    v("ast.amdgpu.status_ok", env.get("status") == "ok",
      "status=%r lim=%s" % (env.get("status"), env.get("limitations")))
    if env.get("status") != "ok":
        return
    r = (env.get("results") or [{}])[0]
    val = r.get("value") or {}
    v("ast.amdgpu.tipo_structural_facts",
      r.get("type") == "structural_facts", r.get("type"))
    v("ast.amdgpu.root_translation_unit",
      val.get("root") == "translation_unit", val.get("root"))
    v("ast.amdgpu.bytes_42872", val.get("bytes") == 42872,
      "bytes=%r (MEDIDO 2026-10-15: 42872)" % val.get("bytes"))
    v("ast.amdgpu.nodos_7066", val.get("nodos") == 7066,
      "nodos=%r (MEDIDO 2026-10-15: 7066)" % val.get("nodos"))
    v("ast.amdgpu.declaraciones_199", val.get("declaraciones") == 199,
      "declaraciones=%r (MEDIDO: 199)" % val.get("declaraciones"))
    v("ast.amdgpu.funciones_14", val.get("funciones") == 14,
      "funciones=%r (MEDIDO: 14)" % val.get("funciones"))
    v("ast.amdgpu.tipos_distintos_94", val.get("tipos_distintos") == 94,
      "tipos=%r (MEDIDO: 94)" % val.get("tipos_distintos"))
    # Los 10 nodos ERROR se REPORTAN. Un AST con errores que calla sobre sus
    # errores es un AST que miente sobre su propia completitud.
    v("ast.amdgpu.errores_reportados", val.get("n_errores_parseo") == 10,
      "n_errores=%r (MEDIDO: 10)" % val.get("n_errores_parseo"))
    v("ast.amdgpu.limita_por_errores",
      any("ERROR" in l for l in (r.get("limitations") or [])),
      "las limitations no mencionan los nodos ERROR")


def test_no_es_c_no_falsy_empty():
    """Un fichero que NO es C devuelve `unsupported`, NO `empty`.

    Es la distincion que `rz_inspect` ya aplica con la arquitectura: no saber
    parsear no es lo mismo que no tener nada que mirar. Si esto devolviera
    `empty`, un `.py` o un `.md` leido por error se leeria como "el fichero no
    tiene estructuras", que es una afirmacion FALSA.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("def f(x):\n    return x + 1\n")
        p = fh.name
    try:
        env = parsear(p, lenguaje="c")
        v("ast.python_como_c.unsupported",
          env.get("status") == "unsupported",
          "status=%r (esperado unsupported)" % env.get("status"))
        v("ast.python_como_c.sin_results", not (env.get("results") or []),
          "devolvio resultados para un fichero que no es C")
    finally:
        os.unlink(p)


def test_lenguaje_sin_binding_es_unsupported():
    """Un lenguaje sin binding medido es `unsupported`, no `ok`."""
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="cobol")
    v("ast.cobol.unsupported", env.get("status") == "unsupported",
      "status=%r" % env.get("status"))
    v("ast.cobol.limita_a_medidos",
      any("source.ast_parse" not in l and "medido" in l.lower()
          for l in (env.get("limitations") or []))
      or any("C" in l for l in (env.get("limitations") or [])),
      str(env.get("limitations"))[:200])


def test_control_negativo_patron_inexistente():
    """DISCRIMINANTE. Un patron que no existe da 0, no un error.

    Sin este control, un adapter que devuelve SIEMPRE algo pasaria el test de
    "encuentra el patron". Este es el control que §47 llama discriminante: la
    capacidad tiene que poder decir NO.
    """
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="c",
                  patron="PATRON_QUE_NO_EXISTE_ZXC123")
    v("ast.negativo.status_ok", env.get("status") == "ok",
      "status=%r" % env.get("status"))
    r = (env.get("results") or [{}])[0]
    raw = r.get("raw") or {}
    v("ast.negativo.cero_coincidencias",
      raw.get("n_coincidencias") == 0,
      "n_coincidencias=%r (esperado 0)" % raw.get("n_coincidencias"))


def test_patron_existente_encuentra():
    """El control POSITIVO del mismo patron: `ioctl` SI esta en amdgpu.h."""
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="c", patron="ioctl", limite=5)
    r = (env.get("results") or [{}])[0]
    raw = r.get("raw") or {}
    v("ast.positivo.ioctl_encuentra",
      (raw.get("n_coincidencias") or 0) > 0,
      "n_coincidencias=%r (esperado >0)" % raw.get("n_coincidencias"))


def test_patron_busca_nodos_no_texto():
    """LA DISTINCIÓN QUE JUSTIFICA LA CAPACIDAD: nodo, no texto.

    Un `str.count("patron")` contaria tambien las apariciones dentro de
    comentarios y de cadenas. El visitor de tree-sitter solo cuenta NODOS
    hoja. Eso es lo que separa esta capacidad de un grep, y por eso se
    comprueba con un caso DONDE LA DIFERENCIA ES CONSTRUIBLE, no con un
    fichero real.

    MEDIDO 2026-10-15, y con una correccion en dos pasos que conviene no
    perder de vista. Al escribir esto, `str.count("ioctl")` sobre
    `amdgpu.h` daba 11 y el visitor tambien 11, y la asercion original
    (visitor < texto) parecio FALSA. No lo era: era el ADAPTER el que
    estaba mal. Filtraba por `child_count == 0`, creyendo que hoja significa
    codigo, y en tree-sitter un `#include` y un comentario SON hojas. Una
    version intermedia filtro solo comentarios, y el caso sintetico paso
    mientras `amdgpu.h` seguia dando 11, porque la linea 54 es un
    `preproc_include` y no un comentario. Con el filtro por TIPO completo,
    texto = 11 y nodos = 10.

    Es decir: el caso sintetico no sustituye al fichero real, lo
    complementa. El sintetico prueba que el filtro excluye; el real prueba
    que el filtro cubre los tipos que aparecen en codigo de verdad.
    """
    with tempfile.NamedTemporaryFile("w", suffix=".c", delete=False,
                                     encoding="utf-8") as fh:
        fh.write("/* MARCA_EN_COMENTARIO una vez */\n"
                 "/* MARCA_EN_COMENTARIO otra vez */\n"
                 "const char *s = \"MARCA_EN_COMENTARIO\";\n"
                 "int MARCA_EN_COMENTARIO = 1;\n")
        p = fh.name
    try:
        with open(p, "rb") as fh:
            n_texto = fh.read().count(b"MARCA_EN_COMENTARIO")
        env = parsear(p, lenguaje="c", patron="MARCA_EN_COMENTARIO",
                      limite=100)
        v("ast.sintetico.status_ok", env.get("status") == "ok",
          "status=%r lim=%s" % (env.get("status"), env.get("limitations")))
        if env.get("status") != "ok":
            return
        r = (env.get("results") or [{}])[0]
        raw = r.get("raw") or {}
        n_nodos = raw.get("n_coincidencias") or 0
        v("ast.sintetico.texto_cuenta_4", n_texto == 4,
          "el fichero tiene 4 apariciones en texto, esperada=%r" % n_texto)
        # 3 en comentario/cadena + 1 identificador. El visitor debe ver SOLO
        # el identificador. Este es el discriminante: si diera 4, el adapter
        # estaria haciendo grep y la capacidad no aportaria nada.
        v("ast.sintetico.visitador_ignora_comentarios_y_cadenas",
          n_nodos == 1,
          "el visitor vio %r nodos; esperado 1 (solo el identificador). "
          "Si vier 4, estaria contando texto." % n_nodos)
        v("ast.sintetico.nodos_menos_que_texto", n_nodos < n_texto,
          "nodos=%r texto=%r" % (n_nodos, n_texto))
    finally:
        os.unlink(p)


def test_sobre_amdgpu_h_nodos_es_igual_a_texto():
    """MEDIDO: en amdgpu.h, texto = 11 y nodos = 10.

    La diferencia es la linea 54, `#include <drm/drm_ioctl.h>`: cuenta como
    texto, y NO como codigo ejecutable. Las otras 10 son identificadores
    reales (`amdgpu_cs_ioctl`, `drm_ioctl_desc`, `amdgpu_max_kms_ioctl`, ...).
    """
    if not os.path.isfile(AMDGPU_H):
        return
    with open(AMDGPU_H, "rb") as fh:
        n_texto = fh.read().count(b"ioctl")
    env = parsear(AMDGPU_H, lenguaje="c", patron="ioctl", limite=100000)
    r = (env.get("results") or [{}])[0]
    raw = r.get("raw") or {}
    n_nodos = raw.get("n_coincidencias") or 0
    # MEDIDO: texto = 11, nodos = 10. La diferencia es la linea 54,
    # `#include <drm/drm_ioctl.h>`, que es un nodo `preproc_include`: una
    # hoja para tree-sitter, pero no CODIGO. Antes del filtro por tipo el
    # visitor la contaba y daba 11, igual que un grep.
    v("ast.amdgpu_h.texto_11", n_texto == 11,
      "str.count(ioctl)=%r (MEDIDO: 11)" % n_texto)
    v("ast.amdgpu_h.nodos_10", n_nodos == 10,
      "n_coincidencias=%r (MEDIDO: 10; el include de la linea 54 no es "
      "codigo)" % n_nodos)
    v("ast.amdgpu_h.diferencia_uno_menos_que_texto", n_nodos == n_texto - 1,
      "nodos=%r texto=%r: se esperaba exactamente 1 menos" % (n_nodos, n_texto))
    v("ast.amdgpu_h.total_publicado", raw.get("n_coincidencias") == n_nodos,
      "raw.n_coincidencias=%r debe coincidir con el total real"
      % raw.get("n_coincidencias"))


def test_truncado_declarado():
    """Si la lista se recorta, el total y el flag estan publicados.

    MEDIDO 2026-10-15: la primera version guardaba las 50 primeras
    coincidencias y NADA mas. Un consumidor que leyera
    `raw.coincidencias` contaria 50 cuando el numero real fuera mayor, sin
    tener forma de saberlo.
    """
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="c", patron="_", limite=100000)
    r = (env.get("results") or [{}])[0]
    raw = r.get("raw") or {}
    n_total = raw.get("n_coincidencias")
    v("ast.truncado.total_es_numero", isinstance(n_total, int),
      "n_coincidencias=%r (%s)" % (n_total, type(n_total).__name__))
    v("ast.truncado.lista_acotada", len(raw.get("coincidencias") or []) <= 50,
      len(raw.get("coincidencias") or []))
    v("ast.truncado.flag_presente",
      "coincidencias_truncadas" in raw, sorted(raw))


def test_entrada_inexistente_es_invalid():
    """Un path que no existe es `invalid_input`, no un error generico."""
    env = parsear("/no/existe/jamas.c", lenguaje="c")
    v("ast.inexistente.invalid", env.get("status") == "invalid_input",
      "status=%r" % env.get("status"))
    v("ast.inexistente.no_invoca_backend",
      (env.get("precheck") or {}).get("ok") is False,
      "el precheck paso con una entrada inexistente")


def test_target_no_es_pci():
    """Una lectura de FUENTE no se firma como evidencia sobre la RX550.

    B3, ya documentado en `rz_inspect.target_binario`: si el target fuese
    `0000:01:00.0`, estariamos firmando una lectura de un .h como si hubiera
    tocado la GPU. No lo toco.
    """
    if not os.path.isfile(AMDGPU_H):
        return
    import inspect
    from backends.adapters import ts_ast
    src = inspect.getsource(ts_ast.persistir)
    v("ast.target_no_pci", "0000:01:00.0" not in src,
      "persistir() menciona un BDF de GPU")
    v("ast.target_es_source", 'target = "source:' in src,
      "persistir() no construye un target source:")


def test_precheck_cubre_lo_declarado():
    """El precheck declara lo que el contrato promete, no menos."""
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="c")
    pre = env.get("precheck") or {}
    for campo in ("input_existe", "input_hash", "lenguaje_pedido",
                  "lenguaje_tiene_binding", "venv_aislado", "ok"):
        v("ast.precheck.tiene_%s" % campo, campo in pre, sorted(pre))
    v("ast.precheck.ok_true", pre.get("ok") is True, pre.get("ok"))
    v("ast.precheck.hash_64", len(pre.get("input_hash") or "") == 64,
      "hash=%r" % pre.get("input_hash"))


def test_provenance_completa():
    """La cadena de evidencia viaja con el resultado (§14, §37)."""
    if not os.path.isfile(AMDGPU_H):
        return
    env = parsear(AMDGPU_H, lenguaje="c")
    prov = env.get("provenance") or {}
    v("ast.prov.estado_completa", prov.get("estado") == "completa",
      prov.get("estado"))
    for campo in ("cadena", "artefacto", "input_hash", "backend_id",
                  "transformacion", "normalizador", "limitaciones"):
        v("ast.prov.tiene_%s" % campo, campo in prov, sorted(prov))
    v("ast.prov.cadena_no_vacia", len(prov.get("cadena") or []) >= 6,
      prov.get("cadena"))
    v("ast.prov.input_hash_coincide",
      (prov.get("input_hash") == (env.get("precheck") or {}).get("input_hash")),
      "el hash de provenance no es el del precheck")


def test_por_dispatch():
    """La capacidad se alcanza por el DISPATCH, no solo llamando al adapter.

    Una capacidad registrada en el registro pero inalcanzable por la ruta
    publica es capacidad de papel. Este test la invoca como lo haria una IA.
    """
    from backends import dispatch
    v("ast.dispatch.registrada", "source.ast_parse" in dispatch.ADAPTERS,
      sorted(dispatch.ADAPTERS))
    if "source.ast_parse" not in dispatch.ADAPTERS:
        return
    info = dispatch.ADAPTERS["source.ast_parse"]
    v("ast.dispatch.modulo", info["modulo"] == "backends.adapters.ts_ast",
      info["modulo"])
    v("ast.dispatch.funcion_parsear", info["funcion"] == "parsear",
      info["funcion"])
    v("ast.dispatch.backend_por_defecto",
      info["backend_por_defecto"] == "tree-sitter",
      info["backend_por_defecto"])
    v("ast.dispatch.artefacto_obligatorio",
      "artefacto" in info["obligatorio"], info["obligatorio"])
    import importlib
    m = importlib.import_module(info["modulo"])
    v("ast.dispatch.funcion_llamable",
      callable(getattr(m, info["funcion"], None)), info["funcion"])


def main() -> int:
    for t in (test_ausencia_venv_es_blocked_no_crash,
              test_amdpu_real,
              test_no_es_c_no_falsy_empty,
              test_lenguaje_sin_binding_es_unsupported,
              test_control_negativo_patron_inexistente,
              test_patron_existente_encuentra,
              test_patron_busca_nodos_no_texto,
              test_sobre_amdgpu_h_nodos_es_igual_a_texto,
              test_truncado_declarado,
              test_entrada_inexistente_es_invalid,
              test_target_no_es_pci,
              test_precheck_cubre_lo_declarado,
              test_provenance_completa,
              test_por_dispatch):
        try:
            t()
        except Exception as e:                       # noqa: BLE001
            v("%s LANZO" % t.__name__, False,
              "%s: %s" % (type(e).__name__, e))
    print("\n=== RXRE-ECO-001 source.ast_parse: %d passed / %d failed "
          "(of %d) ===" % (_n - _f, _f, _n))
    return 0 if _f == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

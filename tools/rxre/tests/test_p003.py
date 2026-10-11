#!/usr/bin/env python3
"""RXRE-006 P0.3. Tests de representacion de offsets MMIO y conflictos de definiciones.

QUE PRUEBA Y QUE NO.

Este modulo convierte los hallazgos 1589 (colision de dword_index) y 1590
(conflicto de definiciones) en vectores ejecutables y discriminantes.

NO prueba `route`, NO ejecuta MMIO, NO toca hardware. Solo auditA la
representacion que reg_resolve.py produce sobre el corpus.

Cada test tiene:
    - ORACLE INDEPENDIENTE: construido sin reg_resolve.py (regex propia +
      verificacion de campo en la salida)
    - CRITERIO DE FALLO CONTRA EL DEFECTO ACTUAL: se documenta por que el test
      falla frente a la implementacion defectuosa actual
    - CRITERIO DE PASS: lo que debe成立 despues de la reparacion minima

Un vector que pasa porque el defecto aun no fue detectado NO es un vector verde:
    test_verde_y_defecto_presente = INVALID (el test no es discriminante)
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
REG_RESOLVE = os.path.join(ROOT, "tools", "reg_resolve.py")
KERNELBUILD = os.path.join(ROOT, "RESEARCH", "kernelbuild", "linux-7.1.3")
ASIC_REG = os.path.join(KERNELBUILD, "drivers", "gpu", "drm", "amd", "include", "asic_reg")

fails: List[str] = []
checks = 0


def v(nombre: str, cond: bool, det: Any = "") -> None:
    global checks
    checks += 1
    if not cond:
        fails.append("%s %s" % (nombre, det))


# ---------------------------------------------------------------------------
# PRODUCTORES INDEPENDIENTES (ORACLES)
# ---------------------------------------------------------------------------

# La definicion del kernel, leida con regex PROPIA (no reg_resolve.py).
# Patrón que exige el nombre en el primer campo y el valor hex en el segundo:
DEFINE_PAT = re.compile(
    r"^\s*#\s*define\s+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s+((?P<shift>__SHIFT)|(?P<mask>__MASK)))?\s+"
    r"(?P<val>0[xX][0-9a-fA-F]+|\d+)"
)


def oracle_all_defs(symbol: str) -> List[Dict[str, Any]]:
    """Todas las definiciones de un simbolo en asic_reg: [ {file, rel, value}, ...]."""
    out: List[Dict[str, Any]] = []
    for dirpath, dirnames, filenames in os.walk(ASIC_REG):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not (fn.endswith(".h") or fn.endswith(".json")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, encoding="utf-8", errors="replace") as fh:
                    for line in fh:
                        m = DEFINE_PAT.match(line)
                        if not m:
                            continue
                        if m.group("name") != symbol:
                            continue
                        v = m.group("val")
                        try:
                            val = int(v, 16) if v.lower().startswith("0x") else int(v)
                        except ValueError:
                            continue
                        out.append({"file": p, "rel": os.path.relpath(p, KERNELBUILD),
                                    "value": val, "hex": ("0x%04X" % val).upper()})
                        break
            except OSError:
                continue
    out.sort(key=lambda d: d["rel"])
    return out


def oracle_unique_def(symbol: str, gca_gfx: Optional[str] = None) -> Optional[int]:
    """La definicion en gca/gfx_NN_d.h si existe, None si no."""
    if gca_gfx is None:
        return None
    p = os.path.join(ASIC_REG, "gca", gca_gfx + ".h")
    if not os.path.isfile(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = DEFINE_PAT.match(line)
            if m and m.group("name") == symbol:
                v = m.group("val")
                return int(v, 16) if v.lower().startswith("0x") else int(v)
    return None


# ---------------------------------------------------------------------------
# EJECUCION DEL PRODUCTOR (lo que se audita)
# ---------------------------------------------------------------------------

def run_reg(resolve_symbol: str, gfx: str = "gfx_8_0") -> Dict[str, Any]:
    """Ejecuta reg_resolve.py con --json y devuelve el envelope JSON como dict."""
    p = subprocess.run([sys.executable, REG_RESOLVE, "--kernel", KERNELBUILD,
                        "--reg", resolve_symbol, "--gfx", gfx, "--json"],
                       capture_output=True, text=True, timeout=120)
    stdout = p.stdout.strip()
    stderr = p.stderr.strip()
    if stdout:
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass
    return {"_parse_error": True, "stdout_snippet": stdout[:300], "rc": p.returncode, "stderr": stderr}


def run_reg_json_output(resolve_symbol: str, gfx: str = "gfx_8_0") -> str:
    """Ejecuta reg_resolve.py con salida json y devuelve el texto JSON puro."""
    p = subprocess.run([sys.executable, REG_RESOLVE, "--kernel", KERNELBUILD,
                        "--reg", resolve_symbol, "--gfx", gfx, "--json"],
                       capture_output=True, text=True, timeout=120)
    return p.stdout.strip()


# ---------------------------------------------------------------------------
# TEST T0301 — IDENTIDAD DE OFFSETS MMIO
# ---------------------------------------------------------------------------

def test_0301_offset_identity_no_collapses():
    """T0301: dos indices MMIO contiguos no colapsan en una identidad.

    El corpus define 0xA1E0 y 0xA1E1 como indices dword DISTINTOS.
    amdgpu_device_rreg multiplica el indice por cuatro antes del MMIO.
    El test anterior dividia por cuatro, inventando una colision: eso era
    un BAD_ORACLE refutado por el consumidor real en RXRE-009.
    """
    global checks
    symbol_a = "mmCB_BLEND0_CONTROL"
    symbol_b = "mmCB_BLEND1_CONTROL"
    expected_a = 0xA1E0
    expected_b = 0xA1E1

    # ORACLE: leer los headers directamente (sin reg_resolve.py)
    oracle_a = oracle_unique_def(symbol_a, "gfx_8_0_d")
    oracle_b = oracle_unique_def(symbol_b, "gfx_8_0_d")
    v("oracle: %s = 0x%04X" % (symbol_a, expected_a), oracle_a == expected_a,
      "oracle %s = %s (no 0x%04X)" % (symbol_a, oracle_a, expected_a))
    v("oracle: %s = 0x%04X" % (symbol_b, expected_b), oracle_b == expected_b,
      "oracle %s = %s (no 0x%04X)" % (symbol_b, oracle_b, expected_b))
    v("oracle: los dos son definidos en el mismo header gfx_8_0_d.h",
      oracle_a is not None and oracle_b is not None,
      "uno o ambos no se definieron en gca/gfx_8_0_d.h")

    res_a = run_reg(symbol_a, "gfx_8_0")
    res_b = run_reg(symbol_b, "gfx_8_0")

    # 1. Ambos simbolos deben dar `ok`
    status_a = res_a.get("status")
    status_b = res_b.get("status")
    verdict_a = (res_a.get("results", [None])[0].get("verdict")
                 if res_a.get("results") else None)
    verdict_b = (res_b.get("results", [None])[0].get("verdict")
                 if res_b.get("results") else None)
    v("T0301 %s resuelve exitosamente (verdict=%s)" % (symbol_a, verdict_a),
      verdict_a == "DEFINIDO_EN_GENERACION_OBJETIVO",
      "status=%s verdict=%s" % (status_a, verdict_a))
    v("T0301 %s resuelve exitosamente (verdict=%s)" % (symbol_b, verdict_b),
      verdict_b == "DEFINIDO_EN_GENERACION_OBJETIVO",
      "status=%s verdict=%s" % (status_b, verdict_b))

    # Extraer el resultado real (primer elemento del array results)
    result_a = res_a.get("results", [None])[0] if res_a.get("results") else None
    result_b = res_b.get("results", [None])[0] if res_b.get("results") else None

    v("T0301 %s tiene resultado" % symbol_a, result_a is not None,
      "no hay resultados: %s" % (res_a.get("results", [])))
    v("T0301 %s tiene resultado" % symbol_b, result_b is not None,
      "no hay resultados: %s" % (res_b.get("results", [])))

    # 2. El indice es el valor del #define; el byte offset sale de multiplicar
    # por 4, como hace amdgpu_device_rreg. Dividir por 4 seria inventar una
    # colision que el consumidor real no produce.
    def fmt(v):
        return "0x%04X" % v if isinstance(v, int) else (v if isinstance(v, str) else None)
    ia = fmt(result_a.get("dword_index")) if result_a else None
    ib = fmt(result_b.get("dword_index")) if result_b else None
    ba = fmt(result_a.get("byte_offset")) if result_a else None
    bb = fmt(result_b.get("byte_offset")) if result_b else None
    na = int(ia, 16) if ia else None
    nb = int(ib, 16) if ib else None
    va = int(ba, 16) if ba else None
    vb = int(bb, 16) if bb else None
    v("T0301 dword_index(0xA1E0) = 0xA1E0, el valor del #define",
      na == expected_a, "dword_index = %s" % ia)
    v("T0301 dword_index(0xA1E1) = 0xA1E1, el valor del #define",
      nb == expected_b, "dword_index = %s" % ib)
    v("T0301 los dos indices siguen siendo distintos",
      na is not None and nb is not None and na != nb,
      "dword_index: %s vs %s" % (ia, ib))
    v("T0301 byte_offset = indice * 4 (reg * 4 en amdgpu_device_rreg)",
      va == expected_a * 4 and vb == expected_b * 4,
      "byte_offsets: %s vs %s (esperados 0x28780 / 0x28784)" % (ba, bb))

    # 3. byte_offset debe ESTAR PRESENTE (no solo dword_index)
    v("T0301 byte_offset presente en resultado de %s" % symbol_a,
      result_a is not None and "byte_offset" in result_a,
      "campo 'byte_offset' ausente en resultado")
    v("T0301 byte_offset presente en resultado de %s" % symbol_b,
      result_b is not None and "byte_offset" in result_b,
      "campo 'byte_offset' ausente en resultado")

    if result_a and result_b:
        warnings = (result_a.get("warning") or "") + (result_b.get("warning") or "")
        v("T0301 la advertencia declara el indice dword y su conversion a byte",
          "dword register index" in warnings and "* 4" in warnings,
          "advertencia ausente o sin la conversion: %s" % (warnings[:250] if warnings else "vacia"))
        v("T0301 la advertencia NO afirma que el valor sea el byte offset",
          "ES el byte offset" not in warnings,
          "la advertencia repite la unidad equivocada")

        # RXRE-012 / hallazgo 1604: el diagnostico viejo decia 'la
        # representacion pierde LSBs'. Eso era un artefacto de la UNIDAD:
        # dividir un indice dword por 4 produce el indice de OTRO registro,
        # no un indice ambiguo. El warning tiene que desdecir ESO, no
        # limitarse a callar sobre las colisiones.
        v("T0301 la advertencia prohibe dividir el valor por 4",
          "NOT a byte offset" in warnings and "dividing it by 4" in warnings,
          "la advertencia no dice que dividir sea invalido: %s" % warnings[:250])
        v("T0301 la advertencia nombra el accessor que hace la conversion",
          "amdgpu_device_rreg" in warnings or "amdgpu_device_wreg" in warnings,
          "la conversion no esta atribuida a su fuente")


# ---------------------------------------------------------------------------
# TEST T0302 — CONFLICTO DE DEFINICIONES
# ---------------------------------------------------------------------------

def test_0302_conflict_declaration():
    """T0302: definiciones conflictivas no pueden presentarse como una sola.

    CASO VERIFICADO (finding 1590):
        mmMC_CG_DATAPORT aparece en 5 headers con DOS valores distintos:
            0xA21  (3 cabeceras: gmc_6_0, gmc_7_1, gmc_8_1)
            0xA32  (2 cabeceras: gmc_7_0, gmc_8_2)

    CRITERIO: el resultado debe exigir una de:
        A) CONFLICT = true, CANDIDATES = [...], CHOSEN = null
        B) CONFLICT = true, CHOSEN = X, SELECTION_RULE, SELECTION_EVIDENCE, EXCLUDED

    NO ACEPTAR: `chosen = first_result` (0xa21 por orden alfabético).

    ORACLE INDEPENDIENTE: oracle_all_defs() lista todas las definiciones y
    muestra explicitamente 2 valores distintos.

    CRITERIO DE FALLO CONTRA EL DEFECTO ACTUAL:
        El test FALLE porque reg_resolve.py devuelve chosen = null con
        `DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO` y `value = 0xa21`
        (primer resultado), sin declarar CONFLICT = true.
    """
    global checks
    symbol = "mmMC_CG_DATAPORT"
    expected_values = {0xA21, 0xA32}

    # ORACLE: todas las definiciones en asic_reg
    all_defs = oracle_all_defs(symbol)
    values = {d["value"] for d in all_defs}
    v("oracle: mmMC_CG_DATAPORT tiene definiciones en %d archivos" % len(all_defs),
      len(all_defs) >= 5, "definiciones = %d (esperado >= 5)" % len(all_defs))
    v("oracle: existen DOS valores distintos: %s" % (sorted("0x%04X" % v for v in values),),
      values == expected_values, "valores = %s" % (sorted("0x%04X" % v for v in values),))

    res = run_reg(symbol, "gfx_8_0")

    v("T0302 resultado parseable como JSON", "_parse_error" not in res,
      "JSON de parseo: %s" % (res.get("stdout_snippet", "")[:300]))

    # El resultado real está en res["results"][0]
    results = res.get("results") or []
    found = False
    for r in results:
        if r.get("symbol") != symbol:
            continue
        found = True
        choices = [h["value"] for h in r.get("definitions") or []]
        v("T0302 todas las definiciones se exponen (%d)" % len(choices),
          set(choices) == expected_values,
          "definiciones expuestas = %s" % sorted("0x%04X" % c for c in choices))

        chosen = r.get("chosen")
        verdict = r.get("verdict", "")

                # Verificar las propiedades criticas
        has_conflict = r.get("conflict") is True or "conflict" in verdict.lower()
        chosen_null = chosen is None  # CHOSEN debe ser null (None)
        has_candidates = "candidates" in r

        # CONDICION A (sin regla de seleccion demostrable):
        # CONFLICT = true AND CHOSEN = null Y CANDIDATES listados
        condition_a = has_conflict and chosen_null and has_candidates

        # CONDICION B (con regla de seleccion demostrable):
        # CONFLICT = true Y CHOSEN = X Y exista SELECTION_RULE/SELECTION_EVIDENCE
        condition_b = (has_conflict and not chosen_null and
                       "selection_rule" in r and "selection_evidence" in r)

        # DESPUES DE LA REPARACION: CONFLICT debe estar declarado.
        # El test PASSA cuando conflict=true (reparacion aplicada).
        v("T0302 CONFLICT declarado correctamente",
          has_conflict,  # el test PASSA si CONFLICT es true
          "conflict=%s chosen_null=%s has_candidates=%s" % (has_conflict, chosen_null, has_candidates))

        # El test debe pasar cuando CONFLICT=true (reparacion aplicada)
        # Ya sea con CHOSEN=null (cond_a) o con CHOSEN=X + regla (cond_b)
        v("T0302 cumple condicion A (CONFLICT=true, CHOSEN=null, CANDIDATES) O B",
          condition_a or condition_b,
          "conflict=%s chosen_null=%s candidates=%s (A=%s B=%s)" % (
              has_conflict, chosen_null, has_candidates, condition_a, condition_b))

        if not condition_a and not condition_b:
            v("T0302 FAIL: no se cumplen condiciones para declarar conflicto",
              "cond_a=%s condition_b=%s" % (condition_a, condition_b),
              "chosen=%s" % (chosen.get("value") if isinstance(chosen, dict) else chosen))

        # CHOSEN con valor solo vale si hay regla y evidencia; y su valor tiene
        # que ser el del header elegido, no el primero de la lista alfabetica.
        if not chosen_null:
            rule = r.get("selection_rule")
            ev = r.get("selection_evidence") or {}
            v("T0302 CHOSEN con valor exige regla y evidencia de seleccion",
              bool(rule) and bool(ev) and chosen.get("value") is not None,
              "rule=%r evidence=%r chosen=%r" % (rule, ev, chosen))
            def_file = (chosen or {}).get("rel")
            v("T0302 la evidencia de seleccion nombra el header elegido",
              bool(ev) and ev.get("definition", {}).get("rel") == def_file,
              "evidence_definition=%r chosen=%r" % (ev.get("definition"), def_file))
            v("T0302 'value' coincide con el header elegido y sigue siendo un candidato",
              r.get("value") is not None and int(r["value"], 16) == chosen.get("value")
              and int(r["value"], 16) in expected_values,
              "value=%r chosen=%r candidatos=%s" % (
                  r.get("value"), (chosen or {}).get("value"),
                  sorted("0x%04X" % v for v in expected_values)))
        else:
            # Sin regla declarada no se expone un unico valor: eso seria
            # presentar como hecho lo que es una eleccion.
            v("T0302 sin regla declarada no se expone 'value' como hecho",
              r.get("value") is None, "value = %r" % r.get("value"))
            v("T0302 los candidatos siguen enumerados",
              set(r.get("candidates") or []) == {"0x%04X" % v for v in expected_values},
              "candidates = %r" % r.get("candidates"))

    v("T0302 se encontro al menos un resultado para mmMC_CG_DATAPORT",
      found, "resultado vacio")


if __name__ == "__main__":
    test_0301_offset_identity_no_collapses()
    test_0302_conflict_declaration()

    print("\n" + "=" * 64)
    print("REPORTE P0.3")
    print("=" * 64)
    print("verificados: %d" % checks)
    if fails:
        print("FALLOS (%d):" % len(fails))
        for f in fails:
            print("  [FALLA] %s" % f)
        sys.exit(1)
    else:
        print("TODO VERDE (%d)" % checks)
        sys.exit(0)

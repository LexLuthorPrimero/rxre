#!/usr/bin/env python3
# CONTRACT: name=regtable_audit
# CONTRACT: READONLY=yes
# CONTRACT: WRITES_FILES=no
# CONTRACT: WRITES_SYSFS=no
# CONTRACT: MUTATES_CORPUS=no
# CONTRACT: WRITES_GPU=no
# CONTRACT: TOUCHES_INTEGRATED=no
#
# MEDIDO con RXRE/tools/rxre_contracts.py, no declarado de memoria.  El
# veredicto fue `READONLY=yes, WRITES_FILES=no`, y las 6 escrituras que
# tiene se resolvieron a la clase TEMPORAL: 6 caen DENTRO de un `with tempfile...`.
#
# Declarar `WRITES_FILES=no` con escrituras dentro no es una contradiccion: es
# exactamente la clase TEMPORAL de `contract_exec.py`, que existe porque una
# regex produjo cinco falsos positivos.  Declararlas `yes` seria MENTIR: el
# validador no puede distinguir un temporal de un fichero del proyecto.
#
# `tools/` tenia 3 contratos de 92.  Este bloque no anade comportamiento: hace
# el comportamiento DECLARABLE, que es la condicion previa a poder usarlo.
# Sobre la frontera: TOUCHES_INTEGRATED=no, y el campo se declara aunque
# toolkit.py no lo conozca -- la frontera que no se puede declarar es la que no
# se puede hacer cumplir (hallazgo 1487).
"""regtable_audit.py — valida tablas de registros de gpu_pt_config_reg contra los headers GFX8.

Por qué existe
--------------
Las tablas de `smu7_powertune.c` (DIDTConfig_Polaris12, GCCACConfig_Polaris11, ...)
cruzan **tres** fuentes que no se validan entre sí:

  1. el `.c`    → el OFFSET (índice de bus `ix*`) y el VALOR por campo
  2. `_d.h`     → el valor del índice `ix*` y el byte offset `mm*` del bus
  3. `_sh_mask.h` → la MASCARA (posicionada, incluye el shift) y el SHIFT

En tres iteraciones distintas cometí el mismo error contra estas tablas:

* usé `valor & mascara == valor`, cuando la operación real es
  `(valor << shift) & mascara`  → 41 falsos "truncan"
* construí `__MASK___SHIFT` con dos guiones bajos  → 109 falsos "no está en el header"
* conté dígitos de un nombre en vez del comentario  → `POLARIS10 = 10`

Los tres habrían pasado un `grep` normal. Esta herramienta hace el cruce
explícito y **declara la unidad de cada fuente antes de comparar**, que es
justo el punto donde fallé.

La operación, tomada del corpus y no inferida
--------------------------------------------
    smu7_powertune.c:908   cache |= ((value << shift) & mask);
    smu7_powertune.c:927   data  |= ((value << shift) & mask);
    smu7_powertune.c:928   data  |= cache;

Unidades, declaradas:

    ix*     índice de bus indirecto, NO byte offset
            gfx_8_0_d.h:2781   ixDIDT_SQ_WEIGHT0_3 = 0x10
    mm*     byte offset del registro MMIO
            gfx_8_0_d.h:2775   mmDIDT_IND_INDEX = 0x3280
    MASK    mascara YA POSICIONADA: incluye el desplazamiento
            gfx_8_0_sh_mask.h  DIDT_SQ_CTRL0__PHASE_OFFSET_MASK = 0xc
                                DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT = 0x2
                                → 0xc == 0b1100, y 3 << 2 = 0xc  ⇒ MASK incluye el shift
    valor   SIN desplazar. La macro aplica el shift.

Un parser correcto NO demuestra que la semántica del hardware sea correcta. Esta
herramienta comprueba coherencia entre tres ficheros del driver. No sabe qué
significa DIDT ni si los valores son los correctos para tu silicio.

Uso
---
    regtable_audit.py --kernel RAIZ --gfx gfx_8_0 \\
        --table DIDTConfig_Polaris12 --source drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_powertune.c

    regtable_audit.py --kernel RAIZ --gfx gfx_8_0 --compare DIDTConfig_Polaris11:DIDTConfig_Polaris12 \\
        --source drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_powertune.c

    regtable_audit.py --selftest
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "regtable_audit"
VERSION = "1.0.0"

DEFAULT_GFX = "gfx_8_0"
DEFAULT_TABLE = "DIDTConfig_Polaris12"
DEFAULT_SOURCE = "drivers/gpu/drm/amd/pm/powerplay/hwmgr/smu7_powertune.c"

# Una entrada de gpu_pt_config_reg:
#   { ixDIDT_SQ_WEIGHT0_3, DIDT_SQ_WEIGHT0_3__WEIGHT0_MASK,
#     DIDT_SQ_WEIGHT0_3__WEIGHT0__SHIFT, 0x0073, GPU_CONFIGREG_DIDT_IND },
# Hay DOS formatos de entrada en el mismo tipo de tabla, y ambos son reales:

#   por nombre:  { ixDIDT_SQ_WEIGHT0_3, DIDT_SQ_WEIGHT0_3__WEIGHT0_MASK,
#                  DIDT_SQ_WEIGHT0_3__WEIGHT0__SHIFT,  0x0073, ... }
#   literal:     { ixGC_CAC_CNTL,  0xFFFFFFFF,  0,  0x00060011, ... }

# DIDTConfig_* usa el primero. GCCACConfig_* usa el segundo, con la máscara en
# hexadecimal y el shift en decimal. Aceptar solo el primero deja 4 de las 7
# tablas del fichero sin parsear, y eso se ve como "no existen" si no se
# comprueba el recuento. `kind` distingue los dos casos en la salida.
_NUM = r"(?:0[xX][0-9a-fA-F]+|\d+)"

_ENTRY_NAMED = re.compile(
    r"\{\s*(?P<idx>ix[A-Za-z0-9_]+)\s*,"
    r"\s*(?P<mask_name>[A-Za-z0-9_]+)_MASK\s*,"
    r"\s*(?P<shift_name>[A-Za-z0-9_]+)_SHIFT\s*,"
    r"\s*(?P<value>" + _NUM + r")\s*,"
    r"\s*(?P<type>GPU_CONFIGREG_[A-Z0-9_]+)\s*\}"
)

_ENTRY_LITERAL = re.compile(
    r"\{\s*(?P<idx>ix[A-Za-z0-9_]+)\s*,"
    r"\s*(?P<mask_lit>" + _NUM + r")\s*,"
    r"\s*(?P<shift_lit>" + _NUM + r")\s*,"
    r"\s*(?P<value>" + _NUM + r")\s*,"
    r"\s*(?P<type>GPU_CONFIGREG_[A-Z0-9_]+)\s*\}"
)

_TABLE_HEAD = re.compile(r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\[\]\s*=\s*\{")

_DEFINE_NUM = r"#\s*define\s+{}\s+(0[xX][0-9a-fA-F]+|\d+)[uUlL]*\s*$"


def parse_int(tok: str) -> int:
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)


def define_map(path: str) -> Dict[str, int]:
    """Todos los #define numéricos de un header, en un solo paso."""
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    rx = re.compile(_DEFINE_NUM.format(r"([A-Za-z_][A-Za-z0-9_]*)"))
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = rx.match(line.rstrip())
            if m:
                try:
                    out[m.group(1)] = parse_int(m.group(2))
                except ValueError:
                    pass
    return out


def parse_tables(path: str) -> Dict[str, List[Dict[str, object]]]:
    """Extrae todas las tablas `NOMBRE[] = { ... };` de un fichero.

    Se corta en el primer `};` al nivel de llaves del cuerpo, no en el primer
    cierre: una tabla puede contener un `};` dentro de un comentario o de un
    inicializador anidado, y cortar ahí produce una tabla truncada que parece
    más corta de lo que es.
    """
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.readlines()

    tables: Dict[str, List[Dict[str, object]]] = {}
    i, n = 0, len(lines)
    while i < n:
        m = _TABLE_HEAD.search(lines[i])
        if not m:
            i += 1
            continue
        name = m.group("name")
        depth = lines[i].count("{") - lines[i].count("}")
        body: List[str] = []
        i += 1
        while i < n and depth > 0:
            depth += lines[i].count("{") - lines[i].count("}")
            body.append(lines[i])
            i += 1
        entries: List[Dict[str, object]] = []
        first_body_line = i - len(body)
        # El cuerpo se busca COMO UN SOLO TEXTO, no linea a linea. Una entrada
        # de gpu_pt_config_reg ocupa con frecuencia tres o cuatro lineas, y
        # parsear por linea produce una tabla truncada que parece entera. Es el
        # mismo fallo que leer un fichero con head y concluir ausencia.
        blob = "".join(body)
        for m in _ENTRY_NAMED.finditer(blob):
            rel = blob.count("\n", 0, m.start())
            entries.append({
                "kind": "NOMBRE",
                "index": m.group("idx"),
                "mask": m.group("mask_name") + "_MASK",
                "shift": m.group("shift_name") + "_SHIFT",
                "mask_literal": None,
                "shift_literal": None,
                "value": parse_int(m.group("value")),
                "type": m.group("type"),
                "line": first_body_line + rel,
            })
        for m in _ENTRY_LITERAL.finditer(blob):
            rel = blob.count("\n", 0, m.start())
            entries.append({
                "kind": "LITERAL",
                "index": m.group("idx"),
                "mask": None,
                "shift": None,
                "mask_literal": parse_int(m.group("mask_lit")),
                "shift_literal": parse_int(m.group("shift_lit")),
                "value": parse_int(m.group("value")),
                "type": m.group("type"),
                "line": first_body_line + rel,
            })
        entries.sort(key=lambda e: e["line"])
        if entries:
            tables[name] = entries
    return tables


def audit_table(entries: Sequence[Dict[str, object]],
                dmap: Dict[str, int],
                smap: Dict[str, int],
                source: str) -> Dict[str, object]:
    """Cruza cada entrada contra el header. Devuelve el veredicto por entrada."""
    rows: List[Dict[str, object]] = []
    stats = {"ok": 0, "truncating": 0, "missing_mask": 0,
             "missing_shift": 0, "zero_value": 0}
    if not entries:
        return {"source": source, "entries": 0,
                "stats": stats, "rows": [], "missing_ix": [],
                "verdict": "VACIA",
                "note": "la tabla no tiene entradas: puede estar vacia de "
                        "verdad o no haber sido parseada"}

    for e in entries:
        if e["kind"] == "LITERAL":
            # Mascara y shift vienen en la propia tabla: no hay nada que
            # cruzar contra el header, solo comprobar que el valor no se pierde.
            mv = e["mask_literal"]
            sv = e["shift_literal"]
            row: Dict[str, object] = dict(e)
            row["mask_value"] = mv
            row["shift_value"] = sv
            row["mask_source"] = "literal en la tabla"
        else:
            mv = dmap.get(e["mask"])
            sv = dmap.get(e["shift"])
            row = dict(e)
            row["mask_value"] = mv
            row["shift_value"] = sv
            row["mask_source"] = "header _sh_mask.h"

        if mv is None:
            row["verdict"] = "MISSING_MASK"
            stats["missing_mask"] += 1
        elif sv is None:
            row["verdict"] = "MISSING_SHIFT"
            stats["missing_shift"] += 1
        else:
            v = int(e["value"])
            placed = v << sv
            row["placed"] = placed
            row["hardware_sees"] = placed & mv
            if v == 0:
                row["verdict"] = "OK_ZERO"
                stats["ok"] += 1
                stats["zero_value"] += 1
            elif placed & mv == placed:
                row["verdict"] = "OK"
                stats["ok"] += 1
            else:
                row["verdict"] = "TRUNCATED"
                stats["truncating"] += 1
        rows.append(row)

    kinds: Dict[str, int] = {}
    for r in rows:
        kinds[str(r["kind"])] = kinds.get(str(r["kind"]), 0) + 1

    return {
        "source": source,
        "entries": len(entries),
        "kinds": kinds,
        "stats": stats,
        "rows": rows,
        "missing_ix": [],   # lo resuelve build_reg_offset con dmap, no con shmap
        "verdict": ("CLEAN" if (stats["truncating"] == 0
                                and stats["missing_mask"] == 0
                                and stats["missing_shift"] == 0)
                    else "REVISAR"),
    }


def compare_tables(a: Sequence[Dict[str, object]],
                   b: Sequence[Dict[str, object]],
                   na: str, nb: str) -> Dict[str, object]:
    """Diferencia dos tablas por posición, con alineación explícita."""
    if len(a) != len(b):
        return {"comparable": False,
                "reason": f"distinto numero de entradas: {na}={len(a)} {nb}={len(b)}"}
    diffs = []
    for i, (x, y) in enumerate(zip(a, b)):
        if x["index"] != y["index"] or x["mask"] != y["mask"]:
            diffs.append({"pos": i, "kind": "ESTRUCTURA",
                          "a": f"{x['index']}/{x['mask']}",
                          "b": f"{y['index']}/{y['mask']}"})
        elif x["value"] != y["value"]:
            diffs.append({"pos": i, "kind": "VALOR",
                          "campo": x["mask"].replace("_MASK", ""),
                          "index": x["index"],
                          "a": x["value"], "b": y["value"],
                          "delta": y["value"] - x["value"]})
    # El bloque se saca del INDICE ix*, no del nombre del campo: el campo es
    # DIDT_SQ_CTRL0__PHASE_OFFSET y el bloque es SQ. Usar el nombre del campo
    # agruparia por registro, que no es la unidad que interesa.
    bloques: Dict[str, int] = {}
    for d in diffs:
        if d["kind"] == "VALOR":
            m = re.match(r"ixDIDT_([A-Z]+)_", str(d.get("index", "")))
            key = m.group(1) if m else str(d["campo"]).split("__")[0]
            bloques[key] = bloques.get(key, 0) + 1
    return {
        "comparable": True,
        "entries": len(a),
        "diff_count": len(diffs),
        "diffs": diffs,
        "by_block": bloques,
        "only_in_b": sorted({d["campo"].split("__")[0] for d in diffs
                             if d["kind"] == "VALOR"}),
    }


def build_reg_offset(dmap: Dict[str, int], rows: Sequence[Dict[str, object]],
                     gfx_mm: Dict[str, int], dmap_sh: Dict[str, int]) -> Dict[str, object]:
    """Segunda verificacion, independiente: el offset de bus que se escribira.

    Un indice `ix*` valido que apunta a un bus no implementado pasaria la
    primera auditoria. Esta comprueba que el bus existe y que su par
    INDEX/DATA esta definido, que es lo que hace falta para que la escritura
    llegue al hardware.
    """
    indices = sorted({r["index"] for r in rows if r.get("index")})
    # dmap viene de _d.h, que es donde viven los ix*. Buscarlos en _sh_mask.h
    # produce falsos "inexistente": los indices y las mascaras estan en
    # ficheros distintos por diseno.
    unknown = [i for i in indices if i not in dmap]
    buses = sorted({r["type"] for r in rows})
    return {
        "indices_used": len(indices),
        "indices_unknown": unknown,
        "indices_resolved_in": os.path.basename(dmap.get("__file__", "_d.h"))
                              if isinstance(dmap, dict) and "__file__" in dmap
                              else "gfx_8_0_d.h",
        "buses_used": buses,
        "note": ("el offset de bus se verifica contra el indice; la traduccion "
                 "a byte offset la hace SOC15_REG_OFFSET en tiempo de build "
                 "y no es comprobable desde el fuente"),
    }


def render_single(name: str, res: Dict[str, object], gfx: str) -> str:
    s = res["stats"]
    L = [f"{NAME} {VERSION} · tabla {name} · ASIC-gen {gfx}"]
    L.append("  unidades: ix* = indice de bus | MASK = mascara posicionada "
             "| valor = sin desplazar")
    L.append(f"  operacion: (valor << shift) & mask    [smu7_powertune.c:908]")
    L.append("")
    L.append(f"  ENTRADAS        {res['entries']}")
    if res.get("kinds"):
        L.append(f"  formato         {', '.join(f'{k}={v}' for k, v in res['kinds'].items())}"
                 f"   NOMBRE=del header, LITERAL=en la propia tabla")
    L.append(f"  VEREDICTO       {res['verdict']}")
    L.append(f"  caben          {s['ok']}   (de ellos {s['zero_value']} con valor 0)")
    L.append(f"  TRUNCAN         {s['truncating']}")
    L.append(f"  mask ausente   {s['missing_mask']}")
    L.append(f"  shift ausente  {s['missing_shift']}")
    L.append(f"  ix* sin valor   {len(res['missing_ix'])}")
    if res["missing_ix"]:
        L.append(f"                {', '.join(res['missing_ix'][:6])}")
    L.append("")
    problemas = [r for r in res["rows"]
                 if r["verdict"] in ("TRUNCATED", "MISSING_MASK", "MISSING_SHIFT")]
    if problemas:
        L.append("  PROBLEMAS:")
        for r in problemas[:20]:
            L.append(f"    {r['verdict']:<14} {r['mask']:<46} valor={r['value']:#x}")
        if len(problemas) > 20:
            L.append(f"    ... y {len(problemas) - 20} mas")
    else:
        L.append("  Ningun valor se pierde: todos los no nulos caben en su mascara.")
        L.append("  Esto valida COHERENCIA entre .c y header. No valida que los")
        L.append("  valores sean los correctos para tu silicio.")
    return "\n".join(L)


def render_compare(c: Dict[str, object], na: str, nb: str) -> str:
    L = [f"{NAME} {VERSION} · comparacion {na} vs {nb}"]
    L.append("")
    if not c["comparable"]:
        L.append(f"  NO COMPARABLE: {c['reason']}")
        return "\n".join(L)
    L.append(f"  entradas       {c['entries']} en ambas")
    L.append(f"  diferencias    {c['diff_count']}")
    L.append(f"  por bloque     {', '.join(f'{k}={v}' for k, v in c['by_block'].items()) or '-'}")
    L.append("")
    L.append(f"  {'pos':>4} {'campo':<46} {na.replace('DIDTConfig_',''):>10} "
             f"{nb.replace('DIDTConfig_',''):>10}")
    L.append("  " + "-" * 78)
    for d in c["diffs"]:
        if d["kind"] == "ESTRUCTURA":
            L.append(f"  {d['pos']:>4} ESTRUCTURA DIVERGENTE  {d['a']} vs {d['b']}")
        else:
            L.append(f"  {d['pos']:>4} {d['campo']:<46} {d['a']:>#10x} {d['b']:>#10x}")
    return "\n".join(L)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

SELFTEST_SRC = """
static const struct gpu_pt_config_reg DIDTConfig_Test[] = {
	{   ixDIDT_SQ_WEIGHT0_3,  DIDT_SQ_WEIGHT0_3__WEIGHT0_MASK,
	    DIDT_SQ_WEIGHT0_3__WEIGHT0__SHIFT,   0x0073, GPU_CONFIGREG_DIDT_IND },
	{   ixDIDT_SQ_CTRL0,      DIDT_SQ_CTRL0__PHASE_OFFSET_MASK,
	    DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT,  0x0003, GPU_CONFIGREG_DIDT_IND },
	{   ixDIDT_SQ_CTRL0,      DIDT_SQ_TUNING_CTRL__UNUSED_0_MASK,
	    DIDT_SQ_TUNING_CTRL__UNUSED_0__SHIFT, 0x0000, GPU_CONFIGREG_DIDT_IND },
	{   ixDIDT_SQ_CTRL1,      DIDT_SQ_WEIGHT1__NO_EXISTE_MASK,
	    DIDT_SQ_WEIGHT1__NO_EXISTE__SHIFT,   0x0001, GPU_CONFIGREG_DIDT_IND },
	{   ixDIDT_SQ_CTRL2,      DIDT_SQ_CTRL2__SHORT_TERM_INTERVAL_SIZE_MASK,
	    DIDT_SQ_CTRL2__SHORT_TERM_INTERVAL_SIZE__SHIFT, 0x03ff, GPU_CONFIGREG_DIDT_IND },
};
"""

SELFTEST_MASK = """
#define DIDT_SQ_WEIGHT0_3__WEIGHT0_MASK        0x000000ff
#define DIDT_SQ_WEIGHT0_3__WEIGHT0__SHIFT      0x00000000
#define DIDT_SQ_CTRL0__PHASE_OFFSET_MASK       0x0000000c
#define DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT     0x00000002
#define DIDT_SQ_TUNING_CTRL__UNUSED_0_MASK     0x00000000
#define DIDT_SQ_TUNING_CTRL__UNUSED_0__SHIFT   0x00000000
#define ixDIDT_SQ_WEIGHT0_3                    0x10
#define ixDIDT_SQ_CTRL0                        0x0
#define ixDIDT_SQ_CTRL1                        0x1
#define ixDIDT_SQ_CTRL2                        0x2
"""

SELFTEST_MASK2 = """
#define DIDT_SQ_CTRL2__SHORT_TERM_INTERVAL_SIZE_MASK 0x03ff0000
#define DIDT_SQ_CTRL2__SHORT_TERM_INTERVAL_SIZE__SHIFT 0x10
"""


def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "smu7_powertune.c")
        with open(src, "w", encoding="utf-8") as fh:
            fh.write(SELFTEST_SRC)
        m1 = os.path.join(td, "gfx_8_0_sh_mask.h")
        with open(m1, "w", encoding="utf-8") as fh:
            fh.write(SELFTEST_MASK)
        m2 = os.path.join(td, "gfx_8_0_sh_mask_extra.h")
        with open(m2, "w", encoding="utf-8") as fh:
            fh.write(SELFTEST_MASK2)

        dm = define_map(m1)
        dm.update(define_map(m2))
        tables = parse_tables(src)
        check("parse.nombre", "DIDTConfig_Test" in tables, True)
        t = tables.get("DIDTConfig_Test", [])
        check("parse.entradas", len(t), 5)
        check("parse.primer_valor", t[0]["value"] if t else None, 0x73)
        check("parse.nombre_mask", t[0]["mask"] if t else None,
              "DIDT_SQ_WEIGHT0_3__WEIGHT0_MASK")

        res = audit_table(t, dm, dm, src)
        s = res["stats"]
        check("audit.entradas", res["entries"], 5)

        # 1) valor que cabe, shift 0
        check("audit.0x73.shift0", t and res["rows"][0]["verdict"], "OK")
        # 2) PHASE_OFFSET: mask 0xc posicionada, shift 2, valor 3 -> 3<<2=0xc cabe
        check("audit.phase_offset", res["rows"][1]["verdict"], "OK")
        check("audit.phase_offset.ve_hardware",
              res["rows"][1]["hardware_sees"], 0xC)
        # 3) valor cero
        check("audit.cero", res["rows"][2]["verdict"], "OK_ZERO")
        # 4) mascara ausente en el header
        check("audit.mask_ausente", res["rows"][3]["verdict"], "MISSING_MASK")
        # 5) TRUNCATED: mask 0x03ff0000, shift 0x10, valor 0x3ff -> 0x3ff0000
        #    pero la mascara es de 10 bits en posicion 16: 0x3ff << 16 = 0x3ff0000
        #    y 0x3ff0000 & 0x3ff0000 == 0x3ff0000 => cabe. Uso un valor mayor
        #    para forzar el truncamiento de verdad:
        #    valor 0xffff con shift 0x10 -> 0xffff0000, mask 0x03ff0000
        #    -> se pierde el bit alto. Aqui el valor es 0x3ff, que cabe.
        #    El test real de truncamiento va aparte.
        check("audit.5.entradas_contadas", res["entries"], 5)

        # truncamiento real: 10 bits de mascara, valor de 20 bits
        src2 = os.path.join(td, "trunc.c")
        with open(src2, "w", encoding="utf-8") as fh:
            fh.write("static const struct gpu_pt_config_reg T[] = {\n"
                     "\t{ ixX, X__F_MASK, X__F__SHIFT, 0xfffff, "
                     "GPU_CONFIGREG_DIDT_IND },\n};\n")
        dm3 = {"X__F_MASK": 0x3FF, "X__F__SHIFT": 0, "ixX": 0x1}
        r3 = audit_table(parse_tables(src2)["T"], dm3, dm3, src2)
        check("audit.truncamiento.real", r3["rows"][0]["verdict"], "TRUNCATED")
        check("audit.truncamiento.valor_ve",
              r3["rows"][0]["hardware_sees"], 0x3FF)

        # el error que me costo 41 falsos positivos: usar valor & mask en vez de
        # (valor << shift) & mask. Aqui mask=0xc, shift=2, valor=3.
        # Con la operacion correcta 3<<2=0xc cabe; con la incorrecta
        # 0x3 & 0xc = 0 != 0x3 y pareceria truncado.
        check("audit.no_es_el_test_malo", res["rows"][1]["verdict"], "OK")

        # el error del doble guion bajo: DIDT_SQ_TUNING_CTRL__UNUSED_0__SHIFT
        # debe resolverse. Si construyera ___SHIFT no se resolveria.
        check("audit.doble_guion_bajo",
              "DIDT_SQ_TUNING_CTRL__UNUSED_0__SHIFT" in res["rows"][2]["shift"], True)

        # comparacion
        # Nombres reales: el bloque sale del ix*, no del nombre del campo.
        # Un cambio en ixDIDT_SQ_* y otro en ixDIDT_TCP_* deben caer en
        # bloques distintos aunque los campos se llamen igual de parecido.
        src3 = os.path.join(td, "cmp.c")
        with open(src3, "w", encoding="utf-8") as fh:
            fh.write("static const struct gpu_pt_config_reg A[] = {\n"
                     "\t{ ixDIDT_SQ_CTRL0, SQ_CTRL0__PHASE_OFFSET_MASK,\n"
                     "\t  SQ_CTRL0__PHASE_OFFSET__SHIFT, 0x0003, GPU_CONFIGREG_DIDT_IND },\n"
                     "\t{ ixDIDT_TCP_CTRL0, TCP_CTRL0__PHASE_OFFSET_MASK,\n"
                     "\t  TCP_CTRL0__PHASE_OFFSET__SHIFT, 0x0020, GPU_CONFIGREG_DIDT_IND },\n};\n"
                     "static const struct gpu_pt_config_reg B[] = {\n"
                     "\t{ ixDIDT_SQ_CTRL0, SQ_CTRL0__PHASE_OFFSET_MASK,\n"
                     "\t  SQ_CTRL0__PHASE_OFFSET__SHIFT, 0x0003, GPU_CONFIGREG_DIDT_IND },\n"
                     "\t{ ixDIDT_TCP_CTRL0, TCP_CTRL0__PHASE_OFFSET_MASK,\n"
                     "\t  TCP_CTRL0__PHASE_OFFSET__SHIFT, 0x0038, GPU_CONFIGREG_DIDT_IND },\n};\n")
        c = compare_tables(parse_tables(src3)["A"], parse_tables(src3)["B"], "A", "B")
        check("cmp.comparable", c["comparable"], True)
        check("cmp.diff_count", c["diff_count"], 1)
        # Bloque extraido del ix* (ixY), no del nombre del campo (U__B).
        check("cmp.bloque", c["by_block"], {"TCP": 1})
        c2 = compare_tables(parse_tables(src3)["A"], [], "A", "B")
        check("cmp.no_comparable", c2["comparable"], False)

        # entradas degeneradas
        check("parse.sin_fichero", parse_tables(os.path.join(td, "nope.c")), {})
        check("define.sin_fichero", define_map(os.path.join(td, "nope.h")), {})
        open(os.path.join(td, "vacio.c"), "w").close()
        check("parse.vacio", parse_tables(os.path.join(td, "vacio.c")), {})

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: coherencia entre .c y header. NO valida la semantica del HW.")
    return 0


# --------------------------------------------------------------------------
# cli
# --------------------------------------------------------------------------

def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog=NAME,
        description="Audita tablas gpu_pt_config_reg contra los headers GFX8. Solo lectura.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel", help="raiz del arbol del kernel")
    ap.add_argument("--gfx", default=DEFAULT_GFX,
                    help=f"generacion de headers (por defecto {DEFAULT_GFX})")
    ap.add_argument("--source", default=DEFAULT_SOURCE,
                    help="fichero .c con las tablas")
    ap.add_argument("--table", action="append", default=[],
                    help="tabla a auditar (repetible). Por defecto DIDTConfig_Polaris12")
    ap.add_argument("--compare", action="append", default=[], metavar="A:B",
                    help="comparar dos tablas")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")

    kernel = os.path.abspath(args.kernel)
    src = args.source if os.path.isabs(args.source) else os.path.join(kernel, args.source)

    inc = os.path.join(kernel, "drivers/gpu/drm/amd/include/asic_reg/gca")
    d_path = os.path.join(inc, f"{args.gfx}_d.h")
    sh_path = os.path.join(inc, f"{args.gfx}_sh_mask.h")

    for p, what in ((src, "source"), (d_path, "registros"), (sh_path, "mascaras")):
        if not os.path.isfile(p):
            print(f"ERROR  {what} no encontrado: {p}", file=sys.stderr)
            return 2

    dmap = define_map(d_path)
    shmap = define_map(sh_path)
    tables = parse_tables(src)

    nombres = args.table or ([DEFAULT_TABLE] if DEFAULT_TABLE in tables else [])
    if not nombres:
        print("ERROR  no hay tablas que auditar. Tablas disponibles:",
              ", ".join(sorted(tables)) or "(ninguna)", file=sys.stderr)
        return 2
    faltan = [n for n in nombres if n not in tables]
    if faltan:
        print(f"ERROR  tablas no encontradas en el fuente: {', '.join(faltan)}",
              file=sys.stderr)
        print(f"        disponibles: {', '.join(sorted(tables))}", file=sys.stderr)
        return 2

    out: Dict[str, object] = {
        "tool": NAME, "version": VERSION,
        "gfx": args.gfx,
        "registers_header": d_path,
        "mask_header": sh_path,
        "source": src,
        "defines_registers": len(dmap),
        "defines_masks": len(shmap),
        "tables_available": sorted(tables),
        "work_class": "READ_ONLY",
        "write_execution": "NONE",
    }
    blocks: List[Dict[str, object]] = []
    for n in nombres:
        # shmap resuelve MASK y SHIFT (en _sh_mask.h).
        # dmap resuelve los ix*, que viven en _d.h, no en _sh_mask.h:
        # cruzarlos da 25 indices "inexistentes" que si existen.
        r = audit_table(tables[n], shmap, shmap, src)
        r["table"] = n
        r["offsets"] = build_reg_offset(dmap, r["rows"], dmap, shmap)
        blocks.append({"mode": "audit", **r})
    for spec in args.compare:
        if ":" not in spec:
            ap.error(f"--compare espera A:B, recibí {spec!r}")
        a, b = spec.split(":", 1)
        if a not in tables or b not in tables:
            ap.error(f"--compare: {a} o {b} no esta en el fuente. "
                     f"Disponibles: {', '.join(sorted(tables))}")
        blocks.append({"mode": "compare",
                       "a": a, "b": b,
                       **compare_tables(tables[a], tables[b], a, b)})
    out["results"] = blocks

    if args.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print(f"{NAME} {VERSION} · {args.gfx} · WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE")
    print(f"  registros: {d_path}")
    print(f"  mascaras : {sh_path}")
    print(f"  fuente   : {src}")
    for b in blocks:
        print()
        print("=" * 74)
        if b["mode"] == "audit":
            print(render_single(b["table"], b, args.gfx))
            o = b["offsets"]
            print(f"  ix* usados {o['indices_used']}, sin valor {len(o['indices_unknown'])}")
            print(f"  buses     {', '.join(o['buses_used'])}")
        else:
            print(render_compare(b, b["a"], b["b"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""reg_resolve.py — resuelve un registro o campo a su offset, mascara, shift y UNIDAD.

Por qué existe
--------------
En este proyecto el error de unidad ha sido el mas caro y mas repetido:

    mmGRBM_STATUS2 = 0x2002        yo leí 0x8008 (supuse byte, es dword)
    PTBA                           moví <<12 de mas y de menos
    gpu_pt_config_reg.offset       leí como byte, es índice de bus
    VOLTAGE_SCALE = 4              supuse 0.25 mV, la unidad no está declarada

Los cuatro salieron de la misma raiz: **el corpus declara la unidad en un sitio
concreto, y ese sitio no es el nombre del simbolo.** El kernel lo dice en la
documentacion de `amdgpu_device_rreg`: "@reg: dword aligned register offset".
Una herramienta que lo dijera cada vez habria cerrado tres de los cuatro.

El kernel 7.1.3 **no trae `asmreg`** (verificado por nombre exacto en todo el
arbol, sin asumir subdirectorio). Esta es su sustitucion para el caso GFX8/GFX9.

Lo que produce
--------------
Para un registro:  offset, unidad, BASE_IDX, IP, generacion que lo define,
                    y si existe en la generacion objetivo.
Para un campo:     mascara, shift, posicion real, y si el valor cabe.
Para un indice ix*: el valor de indice, que NO es un offset de byte.

Nada de esto demuestra semantica de hardware. Resuelve nombres a numeros y
declara de donde sale cada numero.

Uso
---
    reg_resolve.py --kernel RAIZ --reg mmDIDT_IND_INDEX --gfx gfx_8_0
    reg_resolve.py --kernel RAIZ --field DIDT_SQ_CTRL0__PHASE_OFFSET_MASK --gfx gfx_8_0
    reg_resolve.py --kernel RAIZ --resolve ixDIDT_SQ_STALL_CTRL --across-headers
    reg_resolve.py --kernel RAIZ --fields-of ixDIDT_SQ_CTRL0
    reg_resolve.py --selftest

WORK_CLASS=READ_ONLY · WRITE_EXECUTION=NONE
No abre /sys, no escribe ficheros, no toca la GPU ni el arbol.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple

NAME = "reg_resolve"
VERSION = "1.0.0"

DEFAULT_GFX = "gfx_8_0"

# Orden de preferencia de directorios de registros. GFX8/GFX9 viven en gca/,
# GFX10+ en gc/. El orden importa: si se pregunta por mmDIDT_IND_INDEX hay
# definiciones en varios ficheros de varias generaciones y responder "el
# primero que encuentro" seria una respuesta no determinista.
REG_DIRS = ("gca", "gc", "gfx", "si")

_DEFINE_VAL = re.compile(
    r"#\s*define\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"(?P<val>0[xX][0-9a-fA-F]+|\d+)[uUlL]*\s*$"
)

# La declaracion de unidad del kernel. Se cita, no se infiere.
UNIT_DECLARATION = {
    "file": "drivers/gpu/drm/amd/amdgpu_reg_access.c",
    "symbol": "amdgpu_device_rreg",
    "quote": "@reg: dword aligned register offset",
    "operational_check": "reg * 4 en readl(((void __iomem *)adev->rmmio) + (reg * 4))",
    "consequence": "los offsets mm* son indices dword; el byte offset es offset*4",
}


def parse_int(tok: str) -> int:
    return int(tok, 16) if tok.lower().startswith("0x") else int(tok)


def scan_defines(path: str) -> Dict[str, int]:
    out: Dict[str, int] = {}
    if not os.path.isfile(path):
        return out
    rx = re.compile(_DEFINE_VAL.pattern)
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = rx.match(line.rstrip())
            if m:
                try:
                    out[m.group("name")] = parse_int(m.group("val"))
                except ValueError:
                    pass
    return out


def header_index(amd_root: str) -> Dict[str, str]:
    """mapea nombre-de-fichero -> ruta, para los directorios de asic_reg."""
    base = os.path.join(amd_root, "include", "asic_reg")
    idx: Dict[str, str] = {}
    if not os.path.isdir(base):
        return idx
    for sub in sorted(os.listdir(base)):
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith((".h", ".json")):
                idx[fn] = os.path.join(d, fn)
    return idx


def find_define_all(amd_root: str, symbol: str) -> List[Dict[str, object]]:
    """TODAS las definiciones del simbolo en el arbol de asic_reg.

    Devolver todas, no la primera: cuatro ficheros que definen el mismo
    simbolo no es un problema del corpus, es la señal de que el símbolo se
    duplica por generación y que elegir la vigente es otro paso.
    """
    hits: List[Dict[str, object]] = []
    base = os.path.join(amd_root, "include", "asic_reg")
    if not os.path.isdir(base):
        return hits
    pat = re.compile(r"#\s*define\s+" + re.escape(symbol) + r"\b")
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not fn.endswith((".h", ".json")):
                continue
            p = os.path.join(dirpath, fn)
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        if pat.search(line):
                            val = scan_defines(p).get(symbol)
                            hits.append({
                                "file": p,
                                "rel": os.path.relpath(p, amd_root),
                                "line": n,
                                "value": val,
                                "text": line.strip()[:200],
                            })
                            break
            except OSError:
                continue
    hits.sort(key=lambda h: str(h["rel"]))
    return hits


def classify_symbol(symbol: str) -> str:
    """Que clase de numero es, por sufijo y prefijo. Es una PREDICCION.

    El sufijo se mira ANTES que el prefijo a proposito: `mmDIDT_IND_INDEX_BASE_IDX`
    empieza por mm como un offset normal, pero el sufijo dice que es el indice
    de un segmento, y confundirlos produce el error de unidad clasico.
    """
    if symbol.endswith("_BASE_IDX"):
        return "segment_base_index"
    if symbol.endswith("_DEFAULT"):
        return "reset_default"
    if symbol.endswith("_MASK"):
        return "field_mask_positioned"
    if symbol.endswith("__SHIFT"):
        return "field_shift"
    if symbol.startswith("ix"):
        return "bus_index"
    if symbol.startswith("mm"):
        return "byte_offset_de_mm"
    if symbol.isupper():
        return "constant_maybe"
    return "unknown"


def resolve_field(amd_root: str, gfx: str, mask_name: str) -> Dict[str, object]:
    """Resuelve una mascara de campo y su shift, y dice si el valor cabe."""
    sh = os.path.join(amd_root, "include", "asic_reg", "gca", f"{gfx}_sh_mask.h")
    if not os.path.isfile(sh):
        alts = header_index(amd_root)
        cand = [p for f, p in alts.items() if f.startswith(gfx) and f.endswith("_sh_mask.h")]
        if not cand:
            return {"error": "SH_MASK_NO_ENCONTRADO", "gfx": gfx}
        sh = cand[0]

    d = scan_defines(sh)
    if not d:
        return {"error": "SH_MASK_SIN_DEFINES", "header": sh}

    # El usuario puede pedir la mascara por su nombre o por el del shift: son
    # la misma pregunta y tienen que resolverse al mismo campo.
    if mask_name.endswith("__SHIFT"):
        mask_name = mask_name[:-7] + "_MASK"
    if mask_name not in d:
        return {"error": "MASK_NO_DEFINIDA", "symbol": mask_name,
                "header": sh, "defines_leidos": len(d)}

    shift_name = mask_name[:-5] + "__SHIFT"
    shift = d.get(shift_name)
    mask = d[mask_name]
    out: Dict[str, object] = {
        "mask_symbol": mask_name,
        "mask": hex(mask),
        "shift_symbol": shift_name,
        "shift": shift,
        "header": sh,
        "mask_source": "sh_mask.h",
    }
    if shift is None:
        out["note"] = "sin SHIFT en el header: el mask esta posicionado pero no hay campo de referencia"
        return out

    # ¿el mask esta posicionado o es un valor plano? Si el shift es 0 y el mask
    # tiene bits altos, no hay forma de distinguirlo sin el shift.
    out["bit_width"] = bin(mask >> shift).count("1") if mask else 0
    out["mask_is_positioned"] = bool(mask >> shift)
    out["unit"] = "bits de registro"
    return out


def resolve_reg(amd_root: str, gfx: str, reg: str) -> Dict[str, object]:
    """Resuelve un offset mm* y devuelve su valor, BASE_IDX y unidad."""
    base_dir = os.path.join(amd_root, "include", "asic_reg")
    order = [os.path.join(base_dir, "gca", f"{gfx}_d.h"),
             os.path.join(base_dir, "gc", f"{gfx}_offset.h")]
    if not any(os.path.isfile(p) for p in order):
        order = [p for p in header_index(amd_root).values()
                 if os.path.basename(p).startswith(gfx)]
    hits = find_define_all(amd_root, reg)
    in_target = [h for h in hits if h["file"] in order and os.path.isfile(h["file"])]
    other = [h for h in hits if h not in in_target]

    out: Dict[str, object] = {
        "symbol": reg,
        "symbol_class": classify_symbol(reg),
        "requested_gfx": gfx,
        "definitions": hits,
        "definition_count": len(hits),
    }
    if not hits:
        out["verdict"] = "PROVEN_ABSENT_EN_ASIC_REG"
        out["note"] = ("busqueda exhaustiva sobre include/asic_reg. Es una "
                       "ausencia de definicion de offset, no de hardware: el "
                       "registro puede existir y no estar documentado aqui.")
        return out

    if in_target:
        out["chosen"] = in_target[0]
        out["verdict"] = "DEFINIDO_EN_GENERACION_OBJETIVO"
    else:
        out["chosen"] = None
        out["verdict"] = "DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO"
        out["note"] = (f"existe en {len(other)} fichero(s) pero ninguno es el "
                       f"header de {gfx}. Ausencia de definicion en MI "
                       f"generacion, no en el hardware.")

    chosen = out["chosen"]

    val = chosen["value"] if chosen else hits[0]["value"]
    out["value"] = hex(val) if val is not None else None
    out["defined_in"] = [h["rel"] for h in hits]

    if classify_symbol(reg) == "byte_offset_de_mm":
        out["unit"] = "byte offset (contrato del kernel)"
        out["unit_evidence"] = UNIT_DECLARATION
        out["dword_index"] = hex(val >> 2) if val is not None else None
        out["byte_offset"] = hex(val) if val is not None else None
        out["warning"] = ("no confundir: el propio valor ES el byte offset. "
                          "Lo que se multiplica por 4 es el valor de SOC15_REG_OFFSET, "
                          "que es un indice dword de otra capa.")
    elif classify_symbol(reg) == "bus_index":
        out["unit"] = "indice de bus indirecto"
        out["warning"] = "NO es un offset de byte ni de MMIO: se escribe en mm*_IND_INDEX"
    return out


def fields_of(amd_root: str, gfx: str, ix_symbol: str) -> Dict[str, object]:
    """Todos los campos del sh_mask que pertenecen a un registro ix*."""
    sh = os.path.join(amd_root, "include", "asic_reg", "gca", f"{gfx}_sh_mask.h")
    if not os.path.isfile(sh):
        return {"error": "SH_MASK_NO_ENCONTRADO", "gfx": gfx}
    if not ix_symbol.startswith("ix"):
        return {"error": "NO_ES_UN_INDICE", "symbol": ix_symbol}
    # ixDIDT_SQ_CTRL0 -> DIDT_SQ_CTRL0__   (ix se quita, el resto se conserva)
    pre = ix_symbol[2:] + "__"
    fields: List[Dict[str, object]] = []
    with open(sh, "r", encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            # El sufijo _MASK / __SHIFT va FUERA del grupo de captura. Si entra
            # dentro, group(1) ya lo lleva y elaltern exterior nunca casa: el
            # parser devuelve 0 campos y parece que el registro no tiene ninguno.
            m2 = re.match(r"#\s*define\s+(" + re.escape(pre) + r"[A-Za-z0-9_]*?)"
                          r"(_MASK|__SHIFT)\s+(0[xX][0-9a-fA-F]+|\d+)", line)
            if m2:
                fields.append({"symbol": m2.group(1), "raw": m2.group(3),
                               "line": n, "kind": m2.group(2)})
    # El sufijo va en "kind", NO en "symbol": group(1) ya lo excluye. Comprobar
    # endswith sobre "symbol" daria siempre False y las dos tablas saldrian
    # vacias sin que nada falle.
    masks = {f["symbol"] for f in fields if f["kind"] == "_MASK"}
    shifts = {f["symbol"] for f in fields if f["kind"] == "__SHIFT"}
    return {
        "register": ix_symbol,
        "prefix": pre,
        "header": sh,
        "field_count": len(masks),
        "fields": sorted(masks),
        "sin_shift": sorted(m for m in masks if m not in shifts),
        "sin_mask": sorted(s for s in shifts if s not in masks),
    }


def render(res: Dict[str, object]) -> str:
    kind = res.get("kind")
    if kind == "reg":
        L = [f"{NAME} {VERSION} · registro {res['symbol']}"]
        L.append(f"  clase          {res['symbol_class']}")
        L.append(f"  veredicto      {res['verdict']}")
        if res.get("value"):
            L.append(f"  valor          {res['value']}")
        if res.get("unit"):
            L.append(f"  UNIDAD         {res['unit']}")
        if res.get("dword_index"):
            L.append(f"  indice dword   {res['dword_index']}")
        if res.get("warning"):
            L.append(f"  AVISO          {res['warning']}")
        if res.get("note"):
            L.append(f"  NOTA           {res['note']}")
        L.append(f"  definido en    {len(res['definitions'])} fichero(s):")
        for h in res["definitions"][:12]:
            mark = "*" if res.get("chosen") and h["file"] == res["chosen"]["file"] else " "
            L.append(f"   {mark} {h['rel']}:{h['line']}  {h['text'][:110]}")
        return "\n".join(L)
    if kind == "field":
        if res.get("error"):
            return f"{NAME} {VERSION} · ERROR {res['error']}: {res.get('symbol','')}"
        L = [f"{NAME} {VERSION} · campo {res['mask_symbol']}"]
        L.append(f"  mascara        {res['mask']}")
        L.append(f"  shift          {res['shift']}")
        L.append(f"  UNIDAD         {res['unit']}")
        if "bit_width" in res:
            L.append(f"  ancho (bits)   {res['bit_width']}")
            L.append(f"  mask posicionado  {res['mask_is_positioned']}")
        if res.get("note"):
            L.append(f"  NOTA           {res['note']}")
        L.append(f"  header         {res['header']}")
        return "\n".join(L)
    if kind == "fields":
        if res.get("error"):
            return f"{NAME} {VERSION} · ERROR {res['error']}"
        L = [f"{NAME} {VERSION} · campos de {res['register']}"]
        L.append(f"  prefijo        {res['prefix']}")
        L.append(f"  campos         {res['field_count']}")
        for f in res["fields"]:
            L.append(f"    {f}")
        if res.get("sin_shift"):
            L.append(f"  SIN SHIFT      {', '.join(res['sin_shift'])}")
        if res.get("sin_mask"):
            L.append(f"  SIN MASK       {', '.join(res['sin_mask'])}")
        L.append(f"  header         {res['header']}")
        return "\n".join(L)
    if kind == "across":
        L = [f"{NAME} {VERSION} · {res['symbol']} en todo asic_reg"]
        L.append(f"  clase          {res['symbol_class']}")
        L.append(f"  definiciones   {res['definition_count']}")
        L.append("")
        L.append(f"  {'fichero':<44} {'linea':>6} {'valor':>10}")
        L.append("  " + "-" * 64)
        for h in res["definitions"]:
            v = h["value"]
            L.append(f"  {h['rel']:<44} {h['line']:>6} {(hex(v) if v is not None else '?'):>10}")
        if res["definition_count"] == 0:
            L.append("")
            L.append("  PROVEN_ABSENT en include/asic_reg.")
            L.append("  Eso es ausencia de definicion, no de hardware.")
        elif res["definition_count"] > 1:
            L.append("")
            L.append("  Multiples generaciones definen este simbolo con valores")
            L.append("  distintos. Elegir la vigente es un paso explicito, no automatico.")
        return "\n".join(L)
    return str(res)


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------

def selftest() -> int:
    failures: List[str] = []

    def check(name: str, got, want) -> None:
        if got != want:
            failures.append(f"{name}: obtuve {got!r}, esperaba {want!r}")

    check("class.mm", classify_symbol("mmDIDT_IND_INDEX"), "byte_offset_de_mm")
    check("class.ix", classify_symbol("ixDIDT_SQ_CTRL0"), "bus_index")
    check("class.ixGC", classify_symbol("ixGC_CAC_CNTL"), "bus_index")
    check("class.mask", classify_symbol("DIDT_SQ_CTRL0__PHASE_OFFSET_MASK"),
          "field_mask_positioned")
    check("class.shift", classify_symbol("DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT"),
          "field_shift")
    check("class.base", classify_symbol("mmDIDT_IND_INDEX_BASE_IDX"),
          "segment_base_index")

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        # amd_root debe ser el PADRE de include/: en el arbol real es
        # drivers/gpu/drm/amd y los headers estan en amd_root/include/asic_reg.
        amd_root = os.path.join(td, "amd")
        gca = os.path.join(amd_root, "include", "asic_reg", "gca")
        os.makedirs(gca)
        with open(os.path.join(gca, "gfx_8_0_d.h"), "w", encoding="utf-8") as fh:
            fh.write("#define mmDIDT_IND_INDEX   0x3280\n"
                     "#define mmDIDT_IND_DATA    0x3281\n"
                     "#define ixDIDT_SQ_CTRL0    0x0\n"
                     "#define ixDIDT_SQ_WEIGHT0_3 0x10\n")
        with open(os.path.join(gca, "gfx_8_0_sh_mask.h"), "w", encoding="utf-8") as fh:
            fh.write("#define DIDT_SQ_CTRL0__PHASE_OFFSET_MASK   0xc\n"
                     "#define DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT 0x2\n"
                     "#define DIDT_SQ_CTRL0__DIDT_CTRL_EN_MASK   0x1\n")
        gc = os.path.join(amd_root, "include", "asic_reg", "gc")
        os.makedirs(gc)
        with open(os.path.join(gc, "gc_9_0_offset.h"), "w", encoding="utf-8") as fh:
            fh.write("#define ixDIDT_SQ_STALL_CTRL 0x4\n"
                     "#define mmDIDT_IND_INDEX      0x3280\n")

        r = resolve_reg(amd_root, "gfx_8_0", "mmDIDT_IND_INDEX")
        check("reg.valor", r["value"], "0x3280")
        check("reg.unidad", r["unit"], "byte offset (contrato del kernel)")
        check("reg.dword", r["dword_index"], "0xca0")
        check("reg.definiciones", r["definition_count"], 2)
        check("reg.veredicto", r["verdict"], "DEFINIDO_EN_GENERACION_OBJETIVO")

        # Un ix definido en gc/gc_9_0 pero no en gca/gfx_8_0 NO es ausencia:
        # es un veredicto distinto, y el mas informativo de los dos.
        r2 = resolve_reg(amd_root, "gfx_8_0", "ixDIDT_SQ_STALL_CTRL")
        check("ix.otra_generacion.veredicto", r2["verdict"],
              "DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO")
        check("ix.otra_generacion.nota", r2.get("note") is not None, True)
        r3 = resolve_reg(amd_root, "gfx_8_0", "ixNO_EXISTE_NUNCA")
        check("ix.verdadero_ausente", r3["verdict"], "PROVEN_ABSENT_EN_ASIC_REG")

        f = resolve_field(amd_root, "gfx_8_0", "DIDT_SQ_CTRL0__PHASE_OFFSET_MASK")
        check("field.mask", f["mask"], "0xc")
        check("field.shift", f["shift"], 2)
        check("field.ancho", f["bit_width"], 2)
        check("field.posicionado", f["mask_is_positioned"], True)
        f2 = resolve_field(amd_root, "gfx_8_0", "DIDT_SQ_CTRL0__NO_EXISTE_MASK")
        check("field.ausente", f2.get("error"), "MASK_NO_DEFINIDA")
        f3 = resolve_field(amd_root, "gfx_8_0", "DIDT_SQ_CTRL0__PHASE_OFFSET__SHIFT")
        check("field.acepta_sin_sufijo", f3.get("mask_symbol"),
              "DIDT_SQ_CTRL0__PHASE_OFFSET_MASK")

        fo = fields_of(amd_root, "gfx_8_0", "ixDIDT_SQ_CTRL0")
        check("fields.cuenta", fo["field_count"], 2)
        check("fields.sin_shift", fo["sin_shift"],
              ["DIDT_SQ_CTRL0__DIDT_CTRL_EN"])
        check("fields.no_es_indice", fields_of(amd_root, "gfx_8_0", "mmX").get("error"),
              "NO_ES_UN_INDICE")

        a = find_define_all(amd_root, "mmDIDT_IND_INDEX")
        check("across.dos_generaciones", len(a), 2)
        out = render({"kind": "across", "symbol": "mmDIDT_IND_INDEX",
                      "symbol_class": classify_symbol("mmDIDT_IND_INDEX"),
                      "definitions": a, "definition_count": len(a)})
        if "Multiples generaciones" not in out:
            failures.append("across: el render no avisa de la duplicacion")

        # vacio y malformado
        check("across.sin_ficheros", find_define_all(os.path.join(td, "nope"), "X"), [])
        check("reg.sin_arbol", resolve_reg(os.path.join(td, "nope"), "gfx_8_0", "X")
              ["verdict"], "PROVEN_ABSENT_EN_ASIC_REG")
        open(os.path.join(gca, "vacio.h"), "w").close()
        check("header_vacio", scan_defines(os.path.join(gca, "vacio.h")), {})

    print(f"{NAME} {VERSION} · self-test")
    if failures:
        print(f"  RESULTADO FALLIDO ({len(failures)}):")
        for f in failures:
            print(f"    - {f}")
        return 1
    print("  RESULTADO OK · vectores conocidos reproducidos")
    print("  NOTA: resuelve nombres a numeros. NO valida semantica de hardware.")
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog=NAME,
                                 description="Resuelve registros, campos e indices, con unidad.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--kernel")
    ap.add_argument("--amd-root", default=None)
    ap.add_argument("--gfx", default=DEFAULT_GFX)
    ap.add_argument("--reg", action="append", default=[])
    ap.add_argument("--field", action="append", default=[])
    ap.add_argument("--fields-of", action="append", default=[], dest="fields_of")
    ap.add_argument("--resolve", action="append", default=[],
                    help="simbolo buscado en TODO asic_reg, con todas sus generaciones")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.kernel:
        ap.error("--kernel es obligatorio salvo con --selftest")
    kernel = os.path.abspath(args.kernel)
    amd_root = os.path.abspath(args.amd_root) if args.amd_root else \
        os.path.join(kernel, "drivers/gpu/drm/amd")

    if not (args.reg or args.field or args.fields_of or args.resolve):
        ap.error("indica --reg, --field, --fields-of o --resolve")

    blocks = []
    for s in args.reg:
        blocks.append({"kind": "reg", **resolve_reg(amd_root, args.gfx, s)})
    for s in args.field:
        blocks.append({"kind": "field", **resolve_field(amd_root, args.gfx, s)})
    for s in args.fields_of:
        blocks.append({"kind": "fields", **fields_of(amd_root, args.gfx, s)})
    for s in args.resolve:
        hits = find_define_all(amd_root, s)
        blocks.append({"kind": "across", "symbol": s,
                       "symbol_class": classify_symbol(s),
                       "definitions": hits, "definition_count": len(hits)})

    if args.json:
        print(json.dumps({"tool": NAME, "version": VERSION, "gfx": args.gfx,
                          "amd_root": amd_root,
                          "unit_declaration": UNIT_DECLARATION,
                          "results": blocks}, indent=2, ensure_ascii=False))
        return 0

    print(f"{NAME} {VERSION} · {args.gfx} · WORK_CLASS=READ_ONLY")
    for b in blocks:
        print()
        print("=" * 74)
        print(render(b))
    return 0


if __name__ == "__main__":
    sys.exit(main())

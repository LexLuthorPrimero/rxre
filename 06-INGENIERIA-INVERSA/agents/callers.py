#!/usr/bin/env python3
"""Llamantes de cada una de las funciones objetivo, con el AST de clang.

Dos vias, y se declaran por separado porque no son lo mismo:

  (A) llamadas DIRECTAS: CallExpr del AST cuyo callee se llama asi.  Como las
      23 son `static`, solo puede haberlas en el MISMO .c (enlace interno), y
      se comprueba con grep que el numero que da el AST coincide con el numero
      de ocurrencias del nombre en el fichero.

  (B) llamadas INDIRECTAS: la funcion se mete en una tabla de ops
      (`gfx_v8_0_ip_funcs.soft_reset = ...`) y luego se llama por
      `adev->gfx.soft_reset(...)`.  El CallExpr no aparece con el nombre de la
      funcion: es un MemberExpr.  Se buscan con grep del miembro.
"""
import json
import os
import re
import subprocess
import sys

AMD = "/home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"
AST = "/var/tmp/rx550/agents/ast"

TARGETS = [
    ("gfx_v8_0.c", "gfx_v8_0_write_harvested_raster_configs"),
    ("gfx_v8_0.c", "gfx_v8_0_set_cpg_door_bell"),
    ("gfx_v8_0.c", "gfx_v8_0_deactivate_hqd"),
    ("gfx_v8_0.c", "gfx_v8_0_mqd_commit"),
    ("gfx_v8_0.c", "gfx_v8_0_set_mec_doorbell_range"),
    ("gfx_v8_0.c", "gfx_v8_0_soft_reset"),
    ("gfx_v8_0.c", "gfx_v8_0_send_serdes_cmd"),
    ("gfx_v8_0.c", "gfx_v8_0_update_medium_grain_clock_gating"),
    ("gfx_v8_0.c", "gfx_v8_0_update_coarse_grain_clock_gating"),
    ("gfxhub_v2_1.c", "gfxhub_v2_1_disable_identity_aperture"),
    ("gfxhub_v2_1.c", "gfxhub_v2_1_gart_disable"),
    ("gfxhub_v2_1.c", "gfxhub_v2_1_restore_regs"),
    ("gmc_v8_0.c", "gmc_v8_0_mc_stop"),
    ("gmc_v8_0.c", "gmc_v8_0_mc_resume"),
    ("gmc_v8_0.c", "gmc_v8_0_mc_program"),
    ("gmc_v8_0.c", "gmc_v8_0_set_prt"),
    ("gmc_v8_0.c", "gmc_v8_0_gart_enable"),
    ("gmc_v8_0.c", "gmc_v8_0_gart_disable"),
    ("gmc_v8_0.c", "gmc_v8_0_vm_fault_interrupt_state"),
    ("gmc_v8_0.c", "fiji_update_mc_medium_grain_clock_gating"),
    ("gmc_v8_0.c", "fiji_update_mc_light_sleep"),
    ("sdma_v3_0.c", "sdma_v3_0_gfx_stop"),
    ("sdma_v3_0.c", "sdma_v3_0_ctx_switch_enable"),
]


def src_of(f):
    return open(os.path.join(AMD, f), encoding="utf-8", errors="replace").read().splitlines()


def enclosing(idx, line):
    """La funcion del indice que contiene la linea, la mas estrecha."""
    cand = [f for f in idx["functions"] if f["start"] and f["start"] <= line
            and (f["end"] or 10 ** 9) >= line]
    if not cand:
        return None
    return min(cand, key=lambda x: (x["end"] or 0) - (x["start"] or 0))


def main():
    out = {}
    for f, name in TARGETS:
        idx = json.load(open(os.path.join(AST, f[:-2] + ".idx.json")))
        src = src_of(f)
        nlines = len(src)
        decl = [x for x in idx["functions"] if x["name"] == name]
        rec = {"file": f, "name": name,
               "decl_start": decl[0]["start"] if decl else None,
               "decl_end": decl[0]["end"] if decl else None,
               "static": decl[0]["static"] if decl else None,
               "direct": [], "grep_check": None, "fnptr": []}

        # (A) llamadas directas por AST
        for c in idx["calls"]:
            if c["callee"] != name:
                continue
            ln = c["line"]
            if not ln or ln > nlines:
                continue          # el nodo es de una cabecera: se descarta
            if decl and decl[0]["start"] <= ln <= (decl[0]["end"] or 0):
                continue          # la definicion no es un CallExpr
            txt = src[ln - 1]
            if name not in txt:
                continue          # la linea no menciona el nombre: falso positivo
            enc = enclosing(idx, ln)
            rec["direct"].append({
                "line": ln,
                "src": txt.strip()[:110],
                "caller": enc["name"] if enc else None,
                "caller_span": [enc["start"], enc["end"]] if enc else None,
                "caller_static": enc["static"] if enc else None,
            })

        # comprobacion con grep: cuantas veces aparece `nombre(` en el fichero
        pat = re.compile(r"\b%s\s*\(" % re.escape(name))
        occ = [i + 1 for i, l in enumerate(src) if pat.search(l)
               and not re.match(r"\s*static\b.*\b%s\s*\(" % re.escape(name), l)]
        rec["grep_check"] = {"n_ocurrencias_fuente": len(occ), "lineas": occ}

        # (B) punteros a funcion: `miembro = nombre,` o `= nombre;`
        fpat = re.compile(r"(\.\s*|\->\s*)([A-Za-z_]\w*)\s*=\s*%s\b" % re.escape(name))
        for i, l in enumerate(src):
            m = fpat.search(l)
            if m:
                rec["fnptr"].append({"line": i + 1, "miembro": m.group(2),
                                      "src": l.strip()[:110]})
        out[f + ":" + name] = rec
    json.dump(out, open("/var/tmp/rx550/agents/callers.json", "w"), indent=1)
    for k, r in out.items():
        print("=" * 78)
        print("%s  static=%s  def=%s-%s" % (k, r["static"], r["decl_start"], r["decl_end"]))
        print("  grep en el .c: %d ocurrencias (lineas %s)"
              % (r["grep_check"]["n_ocurrencias_fuente"], r["grep_check"]["lineas"]))
        print("  AST: %d llamadas DIRECTAS" % len(r["direct"]))
        for d in r["direct"]:
            print("     %5d  en %-46s | %s" % (d["line"], d["caller"], d["src"]))
        if r["fnptr"]:
            print("  puntero a funcion:")
            for p in r["fnptr"]:
                print("     %5d  .%s = %s" % (p["line"], p["miembro"], p["src"]))


if __name__ == "__main__":
    main()
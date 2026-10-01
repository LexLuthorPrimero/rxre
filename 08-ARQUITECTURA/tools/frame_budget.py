#!/usr/bin/env python3
"""
Presupuesto de dwords del FRAME de una submission en GFX8 (ring GFX y COMPUTE).

Cada llamada amdgpu_ring_write() escribe 1 dword. PACKET3(op,n) ya se cuenta
con las n llamadas siguientes; no se suma nada extra.

Los items se miden sobre el fuente. Los que dependen de una condicion se
declaran explicitamente y se se muestran como "si" -- no se asumen.
"""
import re, sys

BASE = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"

def body(path, func):
    src = open(path, errors="replace").read().split("\n")
    # OJO: una declaracion provisional termina en ';' y no tiene cuerpo.
    # Sin este filtro el extractor casa con el forward-decl y cuenta 0 dw.
    st = next((i for i, l in enumerate(src)
               if re.match(rf"static .*\b{re.escape(func)}\s*\(", l)
               and not l.rstrip().endswith(";")), None)
    if st is None:
        sys.exit(f"FUNC_NOT_FOUND {func}")
    j = st
    while "{" not in src[j]: j += 1
    d = 0
    for k in range(j, len(src)):
        d += src[k].count("{") - src[k].count("}")
        if d == 0: return src[st:k+1]
    sys.exit(f"UNBALANCED {func}")

def dw(lines):
    return sum(1 for l in lines if "amdgpu_ring_write" in l)

def measure(func, file="gfx_v8_0.c", label=None):
    b = body(f"{BASE}/{file}", func)
    return dw(b), func

items = []
for f, name in [
    ("gfx_v8_0_ring_emit_init_cond_exec", "COND_EXEC"),
    ("gfx_v8_0_ring_emit_hdp_flush",       "HDP_flush"),
    ("gfx_v8_0_ring_emit_gds_switch",      "GDS_switch"),
    ("gfx_v8_0_ring_emit_vgt_flush",       "VGT_flush"),
    ("gfx_v8_ring_emit_cntxcntl",          "CNTX_CTRL"),
    ("gfx_v8_0_ring_emit_pipeline_sync",   "PIPELINE_SYNC"),
    ("gfx_v8_0_ring_emit_fence_gfx",       "FENCE_gfx"),
    ("gfx_v8_0_ring_emit_fence_compute",   "FENCE_compute"),
    ("gfx_v8_0_ring_emit_fence_kiq",       "FENCE_kiq"),
    ("gfx_v8_0_ring_emit_ce_meta",         "CE_META"),
    ("gfx_v8_0_ring_emit_de_meta",         "DE_META"),
    ("gfx_v8_0_emit_mem_sync_compute",     "mem_sync_compute"),
    ("gfx_v8_0_emit_wave_limit",          "wave_limit"),
    ("gfx_v8_0_ring_emit_ib_gfx",          "emit_ib_gfx"),
    ("gfx_v8_0_ring_emit_ib_compute",      "emit_ib_compute"),
]:
    n, _ = measure(f)
    items.append((name, n))

print("== COSTES MEDIDOS (dwords) ==")
for n, d in items:
    print(f"  {n:<22} {d:>3}")

cond   = dict(items)["COND_EXEC"]
hdp    = dict(items)["HDP_flush"]
gds    = dict(items)["GDS_switch"]
vgt    = dict(items)["VGT_flush"]
cntx   = dict(items)["CNTX_CTRL"]
psync  = dict(items)["PIPELINE_SYNC"]
fence  = dict(items)["FENCE_gfx"]
ce     = dict(items)["CE_META"]
de     = dict(items)["DE_META"]

# ring_funcs_gfx, gfx_v8_0.c:6878-6900  (orden de las líneas)
N = 3
# leido de ring_funcs_gfx:6879-6896
gfx_decl_items = [5, 7, N*5+9, 12, gds, 4, 5, hdp, vgt, 14, 31, 3, 5, 12, 12, 2, 5]
gfx_decl = sum(gfx_decl_items)
comp_decl = (gds + hdp + 5 + psync + N*5 + 7 + 21 + 7 + 5 + 15)

# Real: maximo que amdgpu_ib_schedule puede llegar a escribir
# (rama mas larga; no todos los items son acumulables entre si)
# amdgpu_ib.c, con la ruta mas larga. Los items de la reserva que ib.c NO
# emite tambien se listan, con su condicion, para que el residual sea
# explicable y no un numero suelto.
# CE_META / DE_META: el contador de llamadas solo ve 4 explicitos; el resto
# va por amdgpu_ring_write_multiple con un count calculado en runtime.
#   cnt  = (sizeof(payload) >> 2) + 4 - 2
#   total = 4 (PACKET3 + config + addr_lo + addr_hi) + (cnt - 2)
#         = 4 + (sizeof(payload) >> 2)          [sizeof en BYTES]
# sizeof en bytes = 4 * nº dword del struct.
def meta_total(dwords):
    return 4 + dwords

CE_REG, CE_CHAIN = 4, 10     # vi_ce_ib_state, vi_ce_ib_state_chained_ib
DE_REG, DE_CHAIN = 17, 27    # vi_de_ib_state, vi_de_ib_state_chained_ib

print()
print("== CE/DE_META: las dos variantes ==")
for nm, reg, ch, decl in (("CE", CE_REG, CE_CHAIN, 14), ("DE", DE_REG, DE_CHAIN, 31)):
    tr, tc = meta_total(reg), meta_total(ch)
    print(f"  {nm}_META regular      = {tr:>3} dw")
    print(f"  {nm}_META chained_ib   = {tc:>3} dw")
    print(f"  {nm}_META declarado    = {decl:>3} dw  -> "
          f"{'chained_ib (el peor caso)' if decl == max(tr, tc) else 'NO COINCIDE'}")
print("  => emit_frame_size reserva el maximo de las dos variantes, no la activa.")

COND2   = cond                  # ib.c:307, solo si cp_gfx_shadow (GFX11 -> falso en GFX8)
SB      = 2                     # gfx_v8_ring_emit_sb
SB2     = 4                     # "double SWITCH_BUFFER", reserva
HDP_INVL = 5                    # ib.c:253 amdgpu_device_flush_hdp
SURF    = 5                     # ib.c:236 emit_mem_sync = SURFACE_SYNC, si AMDGPU_IB_FLAG_EMIT_MEM_SYNC
CE_META_ = meta_total(CE_CHAIN)
DE_META_ = meta_total(DE_CHAIN)


gfx_real_max = (cond + psync + 19 + fence + gds + SB2 + COND2 + hdp + vgt
                + CE_META_ + DE_META_ + cntx + HDP_INVL + 12 + 12 + SB + SURF)

print()
print(f"{'RING':<9} {'declarado':>10} {'real(max)':>11} {'residual':>10}")
for ring, decl, real in (("GFX", gfx_decl, gfx_real_max),
                         ("COMPUTE", comp_decl, comp_decl)):
    print(f"{ring:<9} {decl:>10} {real:>11} {decl-real:>+10}")

print()

print()
print("Nota: la rama real depende de need_ctx_switch, need_pipe_sync,")
print("cp_gfx_shadow y job->uf_addr. 'real(max)' es la cota superior")
print("del path GFX, no una medicion de una submission concreta.")

#!/usr/bin/env python3
"""
Cuenta los dwords que el path de vm-flush de GFX8 escribe realmente en el
ring, y lo compara con lo que cada ring_funcs reserva en emit_frame_size.

REGLA DE CONTEO: cada llamada amdgpu_ring_write() escribe exactamente 1 dword.
PACKET3(op, n) no suma nada extra: sus n payload ya son las llamadas
siguientes, que se cuentan por separado. Contar "1+n" duplica.

Sin hardware. Solo lectura de fuente.
"""
import re, sys

BASE = "RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu"

def body_of(path, func):
    src = open(path, errors="replace").read().split("\n")
    start = None
    for i, l in enumerate(src):
        if re.match(rf"static .*\b{re.escape(func)}\s*\(", l):
            start = i; break
    if start is None:
        sys.exit(f"FUNC_NOT_FOUND {func}")
    j = start
    while "{" not in src[j]: j += 1
    depth = 0
    for k in range(j, len(src)):
        depth += src[k].count("{") - src[k].count("}")
        if depth == 0: return src[start:k+1]
    sys.exit(f"UNBALANCED {func}")

def dw(lines):
    return sum(1 for l in lines if "amdgpu_ring_write" in l)

wreg = dw(body_of(f"{BASE}/gfx_v8_0.c", "gfx_v8_0_ring_emit_wreg"))
tlb  = body_of(f"{BASE}/gmc_v8_0.c",  "gmc_v8_0_emit_flush_gpu_tlb")
vmf  = body_of(f"{BASE}/gfx_v8_0.c", "gfx_v8_0_ring_emit_vm_flush")

n_wreg = len(re.findall(r"amdgpu_ring_emit_wreg\s*\(", "\n".join(tlb)))
tlb_dw = n_wreg * wreg

vmf_txt = "\n".join(vmf)
cut = next(i for i, l in enumerate(vmf) if l.startswith("	if (usepfp)"))
wait_dw = dw(vmf[:cut])
pfp_dw  = dw(vmf[cut:])

print(f"gfx_v8_0_ring_emit_wreg            = {wreg} dw por llamada")
print(f"gmc_v8_0_emit_flush_gpu_tlb        = {n_wreg} llamadas a emit_wreg = {tlb_dw} dw")
print(f"  de los cuales, WAIT_REG_MEM      = {wait_dw} dw")
print(f"  de los cuales, PFP_SYNC_ME       = {pfp_dw} dw (solo ring GFX)\n")

N = 3  # VI_FLUSH_GPU_TLB_NUM_WREG, vi.h:27
rows = (
    ("GFX",     True,  N*5 + 9, "ring_funcs_gfx"),
    ("COMPUTE", False, N*5 + 7, "ring_funcs_compute"),
    ("KIQ",     False, 17,      "ring_funcs_kiq"),
)
print(f"{'RING':<8} {'declarado':>10} {'real':>6} {'residual':>10}   origen")
bad = 0
for ring, usepfp, decl, label in rows:
    actual = tlb_dw + wait_dw + (pfp_dw if usepfp else 0)
    resid  = decl - actual
    if resid < 0: bad += 1
    print(f"{ring:<8} {decl:>10} {actual:>6} {resid:>+10}   {label}")

print()
print(f"VI_FLUSH_GPU_TLB_NUM_WREG = {N} ; llamadas reales de emit_wreg = {n_wreg}")
print(f"exceso declarado = ({N}-{n_wreg}) * 5 = {(N-n_wreg)*5} dw = 1 PACKET3_WRITE_DATA")
sys.exit(1 if bad else 0)

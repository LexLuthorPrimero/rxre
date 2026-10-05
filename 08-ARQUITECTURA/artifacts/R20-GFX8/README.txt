# R20-GFX8: los shaders del driver, decodificados
generado=2026-10-05T01:06:44Z
SUJETO=gfx_v8_0.c, arrays vgpr_init_compute_shader y sgpr_init_compute_shader
HERRAMIENTA=llvm-mc 22.1.8 + llvm-objdump, backend amdgcn
SUBTARGET=gfx900 (gfx812 NO existe en LLVM; ver 1185)
ROUND_TRIP=264/264 bytes identicos (vgpr), 41/41 (sgpr sin la linea cndmask)
DISPOSITIVO_TOCADO=ninguno. Codigo puro; no se toco la GPU ni la Intel.

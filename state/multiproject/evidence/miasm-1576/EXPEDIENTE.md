# EXPEDIENTE — cea-sec/miasm#1576 + PR #1594

## Alcance
- Bug: el loader ELF de miasm mapeaba `(EM_ARM, 32, ELFDATA2MSB)` → `armb`, ignorando `e_flags`. Un ELF BE8 (EF_ARM_BE8, 0x00800000, lo que produce `arm-none-eabi-ld --be8`) almacena las instrucciones A32 **little-endian**; datos big-endian (AAELF32). Miasm decodificaba las instrucciones como big-endian → programa distinto, sin aviso.
- Fix: máquina nueva `armbe8` (decode LE, semántica IR arml, VM big-endian para datos); detección EF_ARM_BE8 en `guess_arch`; BE-32 sigue mapeando a `armb`.
- Rama: `fix/arm-be8-loader @ 16443de`. PR **#1594**: https://github.com/cea-sec/miasm/pull/1594

## Reproducción (control pre-fix)
- ELFs hand-crafted en `/home/lucas/eq-scratch/repro-1576/{make_elfs.py,be8.elf,be32.elf,repro.py}` (programa del issue: mov/add/mov/mul/eor → escritura por stdout con SVC).
- Pre-fix: BE8 → arch `armb`, decode basura (`ANDNE R10, R0, 0xE3`, …), ejecución simbólica → r0/r1/r2 = 0/0/0. BE-32 control → arch `armb`, decode correcto, r0=0x42 r1=0x14a5 r2=0x14a.
- Post-fix: BE8 → arch **armbe8**, mismo decode y mismos valores simbólicos que el control.

## Oráculo independiente (RXRE)
- `cs_disasm` extendido con arquitecturas **`arm` (A32 LE)** y **`armbe` (A32 BE)** (A32 no estaba soportado por el adapter). Fixture del mismo programa en ambos encodings → ambos decodifican a la misma secuencia `mov/add/mov` (test `t_arm_decode` en `test_disasm1634.py`, 40/40 checks OK). Funciona también vía `desensamblar(fixture_bin=…)`.
- Capstone 5.0.7 como oráculo de decode de los 17 primeros... (68 bytes) instrucción por instrucción coincidente con objdump del issue (mov/add/mov/mul/eor + secuencia completa hasta `svc #0`).
- Valor simbólico post-fix r0=0x42 r1=0x14a5 r2=0x14a coincide con qemu-armeb reportado en el issue (oracle NO ejecutable en este host: qemu-arm-static/qemu-armeb-static abortan silenciosamente ante cualquier ELF hand-made; no se pudo validar el Δ con qemu — reportado tal cual).

## Verificación miasm
- `test.arch.arm.elf_be8` (nuevo): BE8 → armbe8 + decode correcto; BE-32 → armb (control) ✓.
- `test.arch.arm.sem` 22/22 OK; `test/arch/arm/arch.py` (decode suite completa ARM) sin regresiones.
- ARM JIT (arml/armb/armbe8) requiere JitCore_arm nativo, ausente en este host: preexistente e idéntico para las máquinas existentes.

## Limitaciones explícitas
- Oracle qemu no verificable aquí (limitación del host, no del fix).
- AAELF64 fuera de scope.
- Simbolic engine miasm es little-endian por diseño para memoria concreta multi-byte (XXX TODO preexistente; afecta también a armb) — el fix no lo toca; el caso ARM data=BE base simbólica queda limitado.
- 1 host, 1 UID. TESTED_ONLY. Nada de PROVEN.
- PR #1594 abierto; pendiente review de mantenedores.

## RXRE delta (esta ejecución)
- Adapter `cs_disasm` extendido a A32 (arm/armbe) + test; 40/40 `test_disasm1634` OK.
- Primera vez que el oráculo RXRE decodifica/valida un caso ARM A32 (issue #1576) end-to-end; no hay nueva capacidad de análisis lógico (sigue PARTIAL la parte semántica).

# EXPEDIENTE — cea-sec/miasm#1561 + PR #1597

## Alcance
- Bug: miasm's Thumb PC replacement estaba sin alinear (`instr.offset + 4`), violando la regla Arm ARM: lecturas de PC en Thumb state = `AlignDown(addr + 4, 4)`.
- Síntoma: ADR T1 (`ADD Rd, PC, #imm`, 0xA0xx-0xA7xx) en dirección 2-mod-4 → puntero 2 bytes alto (0x40000a vs 0x400008) → loads corruptos.
- Fix: `Lifter_Armtl.mod_pc` alinea a 4 (`(instr.offset + 4) & ~0x3`). PC-literal LDR y ADR T3 (enmascaran internamente) idempotentes. Rama `fix/thumb-adr-align @ 17b755d`. PR **#1597**.

## Reproducción
- Fixture `/home/lucas/eq-scratch/repro-1561/adr2mod4.bin` (NOP at 0x400000, ADR at 0x400002, adr r0,#4): pre-fix r0=0x40000a, post-fix r0=0x400008 (valor Arm ARM).
- Control alineado (ADR at 0x400000): r0=0x400008 pre y post.
- Test de regresión `test/arch/arm/adr_align.py` (3/3): 2-mod-4, alineado, ADR con imm=8.

## Oráculo independiente (RXRE)
- `cs_disasm` (thumb T32) sobre el fixture: decode de todos los 5 instructions correcto (cobertura 100%), confirma que el error era semántico/PC-relative en el lifter, no el decodificador.
- Arm ARM pseudocode como oráculo de fórmula (AlignDown(addr+4,4)+imm*4) — los mismos valores que reporta qemu-arm en el issue.

## Verificación miasm
- test.arch.arm.sem 22/22 OK; suite decode ARM completa limpia; test adr_align 3/3 OK.
- Oracle qemu-arm NO ejecutable en este host (limitación documentada); verificación por semántica simbólica + Arm ARM.

## Limitaciones explícitas
- Oracle qemu no disponible aquí; test load-through-puntero no verificado en jitter (imposible sin JIT arm nativo).
- 1 host, 1 UID; TESTED_ONLY; nada de PROVEN.
- PR #1597 abierto; pendiente review de mantenedores.

## RXRE delta (esta ejecución)
- Sin capacidad nueva; `cs_disasm`/thumb como oráculo de decode (ADR T1 vs T3) en el caso real #1561.

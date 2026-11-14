# EXPEDIENTE — cea-sec/miasm#1578 + PR #1595

## Alcance
- Bug doble (issue #1578, JeroenRobben): una IT block Thumb-2 cuyo último instrucción escribe PC:
  1. El desensamblador descartaba el camino de continuación: `bxmi lr` se decodificaba como `BX LR` unconditional (cond=14) y el bloque terminaba sin sucesor (el código tras el early-return nunca se desensamblaba).
  2. El lifter lanzaba `ValueError: Multiple destinations!` (`do_it_block` appendía `IRDst := loc_next` tras una instrucción cuyo propio IR ya asignaba IRDst).
- Fix: máquina/traducción `mn_armt` con IT-state threading (T/E hints, inverse = cond^1); `instruction_armt.splitflow` predicaPC-writer predicado → split; `instruction_armt.breakflow` reconoce POP{pc}; lifter no duplica el IRDst de falling-through. Rama `fix/thumb-it-branch @ 5963d7d`. PR **#1595**.

## Reproducción
- Fixture `/home/lucas/eq-scratch/repro-1578/a1.bin`: bytes del early-return del issue (cmp/it mi/bxmi/push/bl/movs/pop.w/bx) obtenidos del objdump del issue (ground truth) — sin arm-none-eabi toolchain.
- Pre-fix: 3/8 instrucciones desensambladas (`CMP/IT/BX`), código tras `bxmi` perdido silenciosamente; lift → ValueError.
- Post-fix (miasm tree): 8/8 instrucciones; bloques `loc_0 (bx c_next) → loc_6 → loc_c`; IR lift OK; ejecución simbólica: r0=0x5 → r0=2 (fall-through), r0=0xfffffffb → r0=0xfffffffb (tomado vía LR).

## Oráculo independiente (RXRE)
- `cs_disasm` (thumb, T32) sobre el fixture: 8/8 instrucciones, cobertura 100 %, mismos límites de bloque que miasm post-fix. Capstone y miasm post-fix coinciden instrucción a instrucción (miasm normaliza `bxmi`→`BX` con cond=MI en additional_info — representación nativa de miasm).
- Oracle qemu-arm NO ejecutable en este host (qemu-arm-static aborta silenciosamente) — documentado; verificación por semántica + oráculo de decode.
- Casos Part 1 del issue reproducidos por ensamblado miasm: it_bxmi (tomado/no tomado, ambos con valores simbólicos correctos), itt_eq_mov_b (itt eq ; moveq ; beq) — ejecutados con éxito post-fix; controles `ctl_it_no_branch` y `ctl_branch_after_it` intactos.

## Verificación miasm
- `test.arch.arm.sem` 22/22 OK; suite decode ARM completa sin regresiones; BE8 test OK; test nuevo `test/arch/arm/it_branch.py` 4/4 (decode completo, cond MI + splitflow, lift sin excepción, ambos caminos simbólicos).

## Limitaciones explícitas
- Oracle qemu no disponible en el host.
- IT block que atraviesa un punto de entrada mid-block del desensamblador no se re-ancla al contexto IT (documentado).
- 1 host, 1 UID. TESTED_ONLY. Nada de PROVEN.
- PR #1595 abierto; pendiente review de mantenedores.

## RXRE delta (esta ejecución)
- Sin capacidad nueva; `cs_disasm` (thumb) validó el caso real instancia a instancia; RXRE como oráculo de decode del bug real.

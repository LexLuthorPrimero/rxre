# EXPEDIENTE — cea-sec/miasm#1560 + PR #1596

## Alcance
- Bug: el grupo Thumb T2 `0100 0100 xx 0x` (ADD high-reg / ADD SP plus register, `add r3, pc`, `add r0, sp`, `add r0, r8`, ...) se decodificaba como `ADDS` y actualizaba NZCV — Arm ARM declara `setflags = FALSE` (no existe forma ADDS).
- Síntoma: `cmp r0,#5 ; add r3,pc ; ble 1f` cambiaba el branch (a=3 → ble NO tomado) — invalida código PIC-base de `gcc -mthumb -O2 -fPIC`.
- Fix: rename del opcode en `hiregop_name` (`{'ADDS': 0}` → `{'ADD': 0}`); el resto del pipeline (sem.add flag guard `name == 'ADDS'`) ya era correcto. Rama `fix/thumb-hireg-add-no-flags @ 6a47aef`. PR **#1596**.

## Reproducción
- Bytes del issue (raw T2 encodings desde el reporte): `05287b4401dd012000e00220`, `4044`, `6844`, control `4018`.
- Pre-fix: los 3 casos BUG: cmp/add/ble plegaba mal (r0=0x1 en vez de 0x2), NZCV propagados según ADD → flags sucios (0000→0110 en add_r0_r8; 1001→0000 en add_r0_sp). Control adds_t1 OK.
- Post-fix (miasm tree): 4/4 casos spec: r0=0x2/flags 0000, add_r0_r8 flags intactos, add_r0_sp flags 1001 intactos, control 0110.

## Oráculo independiente (RXRE)
- `cs_disasm` (thumb T32) vía RXRE: `05287b44...` → `cmp add ble movs b movs`; `4044` → `add`; `6844` → `add`; `4018` → `adds`. Corresponde exactamente al Arm ARM (setflags=FALSE) y al despacho post-fix de miasm. 4/4 status ok, cobertura 100 %.
- Ejecutar vía RXRE como oráculo de decode del issue — sin arm-none-eabi toolchain en el host.

## Verificación miasm
- `test/arch/arm/hireg_add.py` (nuevo): decode ADD vs ADDS, control T1, ambos casos NZCV + flujo cmp/add/ble. 5/5 OK.
- `test.arch.arm.sem` 22/22 OK; suite decode ARM completa (rc=0, 0 Tracebacks); JIT python-jit no disponible en este host (preexistente: "Unsupported jit arch: arm") — documentado; ambos engines comparten el semántica `add`.

## Limitaciones explícitas
- python jitter no verificable aquí.
- 1 host, 1 UID. TESTED_ONLY. Nada de PROVEN.
- PR #1596 abierto; pendiente review de mantenedores.

## RXRE delta (esta ejecución)
- Sin capacidad nueva; `cs_disasm`/thumb como oráculo del caso real (#1560); confirmación adicional del decode T1 ADD (control) vs T2 ADD (arreglo).

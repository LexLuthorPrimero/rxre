# EXPEDIENTE — cea-sec/miasm#1570 (Thumb-2 literal LDR/LDRB U=0)

## Alcance
- Bug: LDR/LDRB literal T2 con U=0 (offset negativo desde PC) se decodificaba como registro-offset/imm8 en silencio.
- Fix: rama `fix/armt-ldr-literal-neg` @ 7eeccd1 (commit fix: +83 líneas en miasm/arch/arm/arch.py + test_thumb_ldr_literal_neg.py), PR #1591 abierto.

## Evidencia
- Reproducer minimal: bytes de los 4 casos (3+1 control) + suite de triaje vía capstone 5.0.7 (oracle independiente).
- Sello: SEALED_PREDICTION.json (b9ae044c…, creado antes de lanzar al verificador).
- Verificación en curso: verificador ciego en sesión hija (blind subagent), clona el fork y compara master vs fix, decodifica con miasm y con capstone, ejecuta el test de regresión.
- Veredicto: PENDIENTE de retorno del verificador.

## Reglas y límites
- Decoder-only fix; NO claim de soporte ensamblado para [PC, #imm] (upstream roto para positivos también).
- Control dff80800 sin cambios. Suite ARM tradicionalmente frágil: 1 fallo preexistente en master.

## Estado upstream
- PR #1591 abierto; esperando reviewers.

## ESTADO ACTUALIZADO — Verificación ciega COMPLETADA (2026-11-14)

Veredicto: **SEALED_CONSISTENT / TESTED_ONLY** (VERDICT.json, sello b9ae044c…).

- Verificador ciego (sesión hija fresca): clona desde GitHub (`master df358f7`/fix `7eeccd1`); venv nueva; capstone 5.0.9 como oráculo independiente; decodifica los 4 bytes con miasm (master y fix) vs capstone: mismatch en master, match tras fix; byte control (dff80800) idéntico en ambas versiones.
- Test de regresión 4/4 OK en el commit del fix.
- Auditoría de rutas: rxre NO accedido.
- Limitaciones: 1 host/1 UID/1 Python toolchain; verificación por sesión hija, no por tercero humano; scope decoder-only.

Estado upstream: PR #1591 abierto y limpio (rama master-based, sin contaminar la rama x86 conocida #1592).

## ESTADO ACTUALIZADO — RXRE como motor (RE-1639)

**RXRE se ejecutó de verdad sobre este caso**, no solo se leyó su código:

1. **Adapter extendido** (`tools/rxre/backends/adapters/cs_disasm.py`):
   - Nueva arquitectura `thumb` (Thumb-2) — antes no soportada.
   - Operandos ARM (REG/IMM/MEM) — antes solo x86.
   - `cs_disasm.desensamblar(..., arch="thumb")` sobre los 4 bytes clave:
     - 5ff80800 → `ldr.w r0, [pc, #-0x8]`
     - 1ff80a00 → `ldrb.w r0, [pc, #-0xa]`
     - 5ff80409 → `ldr.w r0, [pc, #-0x904]`
     - dff80800 → `ldr.w r0, [pc, #8]`
   - `test_disasm1634`: 36 checks 0 failures (sin regresión x86).
   - `test_backends004`: 3 failures PREEXISTENTES y sin cambios tras la extensión.

2. **Nueva capacidad** `tools/rxre/analysis/thumb_literal_oracle.py` (RE-1639):
   compara RXRE-capstone vs candidato externo (miasm, vía venv) sobre 4096 offsets/familia;
   declara status, coverage, disagreements explícitas.

3. **Resultados RXRE (los papeles ganados, no inferencias)**:

   | Familia | df358f7 (pre-fix) | 7eeccd1 (fix) |
   |---|---|---|
   | ldr_neg | 0/4096 matched (4096 disagreements) | **4096/4096, 0 disagreements** |
   | ldrb_neg | 0/4096 | **4096/4096** |
   | ldr_pos | 4096/4096 | **4096/4096** |
   | ldrb_pos | 4096/4096 | **4096/4096** |

   Coverage 100.00% (16,384 bytes totales; 8,192 de familia U=0 solo).
   Control negativo: las familias U=1 (control) pasan idénticas en ambas versiones — la disagreement es exactamente el bug reportado.

4. **El fix ya era válido** con oracle externo (capstone independiente, verificador ciego SEALED_CONSISTENT); agora RXRE lo ejecuta como oráculo propio y lo valida end-to-end.

## Estado epistémico actualizado
- TESTED_ONLY + SEALED_CONSISTENT (RXRE) + RXRE-EXECUTADO.
- Sin claim universal; 1 host, 1 UID; pipeline RXRE 100% ejecutado en este caso.
- Capacidad nueva integrada y validada; reutilizable contra angr/remill/binsec.

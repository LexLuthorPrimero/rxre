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

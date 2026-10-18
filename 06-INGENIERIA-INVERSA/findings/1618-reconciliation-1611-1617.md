# 1618 — RXRE-008 FASE 3: RECONCILIACIÓN 1611 vs 1617

```text
CLASSIFICATION=EPISTEMIC_RECONCILIATION
WORK_CLASS=RXRE-008-FASE-3
AUTOR=SISTEMA AUTÓNOMO RXRE
FECHA=2026-10-07
TARGET=1002:699f@c7 · Polaris12 · gfx_8_0
ACTION_EXECUTED=EXECUTED
ACTION_RESULT=LINK_NOT_FOUND
RELATION_STATUS=NOT_ESTABLISHED
CLAIM_STATUS=PROVEN
```

## Propósito

Resolver la aparente contradicción entre:
- Finding 1611: ACTION 82 ejecutada pero SHADOW_START → soft_regs_start NO_ENCONTRADO
- Finding 1617: H1 reparación implementada que propaga error desde el producer real

## Clasificación Epistemológica

### No confundir:

```text
ACTION_82_EXECUTED
        ≠
RELATION_PROVEN

REPAIR_H1_IMPLEMENTED
        ≠
ORIGINAL_CAUSAL_LINK_PROVEN

CASUAL_CHAIN_1 (SHADOW_START)  =  NOT_ESTABLISHED
CASUAL_CHAIN_2 (polaris10_process_firmware_header → soft_regs_start) = PROVEN
REPAIR (H1 - error propagation) = MITIGATED (independent of chain 1)
```

## Tabla de Reconciliación

| Item | Estado | Evidencia | Justificación |
|------|--------|-----------|---------------|
| **ACTION_82** | EXECUTED | DB registro | Se registró y ejecutó |
| **ACTION_82_RESULT** | LINK_NOT_FOUND | Búsqueda estática | No hay productor real de SHADOW_START |
| **SHADOW_START_PRODUCER** | NO_EXISTE | corpus kernel | Solo fixture test |
| **REAL_PRODUCER_CHAIN** | PROVEN | Finding 1612 | polaris10_process_firmware_header → smu7_read_smc_sram_dword → soft_regs_start |
| **CONSUMER_EFFECT** | ESTABLISHED | Finding 1613 | soft_regs_start → handshake disables |
| **PRE_REPAIR_RISK** | PROVEN | Finding 215 | soft_regs_start == 0 → consumers → incorrect writes |
| **POST_REPAIR_STATUS** | MITIGATED | Finding 1617 | Error propagation H1 cierra la ruta |
| **H1_DEPENDS_ON_SHADOW_START** | NO | análisis | H1 usa chain REAL, no SHADOW_START |

## Resolución del "Contradicción"

1. **Finding 1611** ejecutó ACTION 82 que tenía como objetivo resolver:
   ```
   SHADOW_START → ... → soft_regs_start
   ```
   Resultado: el enlace NO fue encontrado. SHADOW_START sólo existe en fixture de test.

2. **Finding 1612** (post-refutación) replanteó el modelo usando evidencia real disponible:
   ```
   polaris10_process_firmware_header() → smu7_read_smc_sram_dword() → data->soft_regs_start = tmp
   ```
   Resultado: el claim "soft_regs_start is populated from SoftRegisters" está PROVEN.

3. **Finding 1613** estableció el consumidor:
   ```
   soft_regs_start → sm7_disable_sclk_vce_handshake() / sm7_disable_handshake_uvd()
   ```
   Efecto: deshabilitar handshakes de reloj para operación estable.

4. **Finding 1617/215** implementó H1 (fail-fast/error propagation):
   - Cambio: `result = tmp_result;` → `return tmp_result;` en `smu7_hwmgr.c:1609`
   - Efecto: Cuando `smum_process_firmware_header()` falla, retorna inmediatamente
   - Resultado: `smu7_start_dpm()` y sus consumers **NUNCA se ejecutan** cuando falla el firmware header
   - `soft_regs_start == 0` nunca llega a un consumer que escriba HandshakeDisables
   - El riesgo está CERRADO/PROVEN como MITIGADO

5. **La reparación H1 NO depende de SHADOW_START**
   - H1 aborda la CAUSA REAL documentada (chain del producer)
   - No toca ni se refiere a SHADOW_START (que fue refutado)
   - La reparación es válida independiente del resultado de Finding 1611

## Conclusión

No hay contradicción real. Finding 1611 refutó un enlace hipotético (SHADOW_START) que no tenía evidencia productiva real. Finding 1617/215 reparó el riesgo basado en la CAUSA REAL documentada en Finding 1612, que SÍ tiene evidencia productiva y tests validados.

El estado epistemológico final es:

```
Claim: "soft_regs_start can reach consumers and cause incorrect writes"
    STATUS PRE-REPAIR: PROVEN (risk exists)
    STATUS POST-REPAIR: MITIGATED (H1 error propagation closed the route)
    EVIDENCE: Code modification + static analysis + test validation

Claim: "SHADOW_START → soft_regs_start"
    STATUS: NOT_ESTABLISHED (refuted in Finding 1611)
    EVIDENCE: No real producer found in kernel corpus
```

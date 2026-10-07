# 1622 — El hunk 1 del cambio concurrente rompe un contrato: medido, aislado, y el otro autor NO fue tocado

```text
CLASSIFICATION=CONTRATO_ROTO_MEDIDO+AISLAMIENTO+AUTOCORRECCION
WORK_CLASS=RXRE-017-RECONCILIARE-CAMBIO-CONCURRENTE
AUTOR=AGENTE_RXRE017 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f@c7 · CHIP_POLARIS12 · gfx_8_0
RUNTIME=NOT_RUN sobre hardware · solo lectura y suites de test
WRITE_EXECUTION=NINGUNO · sin MMIO, sin hardware, sin firmware
MODIFICATIONS=tools/rxre/tests/contrato_relpath017.py + este hallazgo
P0.2_STATUS=REOPENED_RECONCILIATION (sin cambios)
```

## EL BLOQUEO DE CONCURRENCIA, INTACTO Y REGISTRANTO

```text
  CURRENT_HEAD   3b82b23  (mi commit 1619)
  reg_resolve.py  sha 3952eb91...  (SIN commitear el cambio ajeno)
  112 ficheros modificados sin commit (+3533/-303)
  NO descartado · NO sobrescrito · NO reset · NO checkout · NO staged
  artifacts/concurrencia/  preservado (patch de 5169 líneas, status, sha)
```

## HUNK POR HUNK, con su clasificación

| # | archivo | cambio | capa semántica | afecta P0.2 | compat con CONSUMER_MODEL | riesgo |
|---|---|---|---|---|---|---|
| 1 | `reg_resolve.py` | `relpath(p,amd_root)`→`relpath(p,base)` | — (representaciún de ruta) | no | **ROTO**: cambia el contrato de `rel` | **ALTO**: rompio 1 test con assertion exacta |
| 2 | `reg_resolve.py` | `order` incluye el header GMC del consumer | B/C | sí (correctouen el sentido C: extiende aplicables) | compatible | bajo: ensancha `in_target` |
| 3 | `reg_resolve.py` | añade todos `gmc_8_*_d.h` a `order` | B | sí | **incorrecto**: mete lineages de GMC8 no target | medio: infla aplicables (el caso B pasa a 2) |
| 4 | `reg_resolve.py` | fallback `order` si nada existe | C | sí | compatible | bajo |
| 5–8 | `reg_resolve.py` | separa `value_disagreement` de `semantic_conflict` | A y F | sí | **error de F**: `semantic_conflict = len(applicable_values)>1` sin ningún consumer | **ALTO** para el claim F; benigno para A |

`hunk 1` es el que exige acción:

## PRODUCER → REPRESENTATION → CONSUMER del campo `rel`

```text
  PRODUCTOR   reg_resolve.py:160   "rel": os.path.relpath(p, base)
      Antes  os.path.relpath(p, amd_root)  -> 'include/asic_reg/gmc/gmc_8_1_d.h'
      Ahora  os.path.relpath(p, base)     -> 'gmc/gmc_8_1_d.h'

  CONSUMIDORES
    hits.sort()                          reg_resolve.py:168  reordena definiciones
    out["defined_in"]                    salida visible para el usuario
    normalize.py::de_registro            propaga raw sin tocar el string
    test_p003.py                         comparisons symmetric (no afectan)
    test_vm8_register009.py:52           ASSERTION EXACTA del string  <--- ROMPE
    test_p0_2_conflict014.py             usa (chosen or {}).get("rel") para check
```

**MEDIDO, no razonado** (dos árboles desechables, mesma suite en HEAD e en
HEAD+cambio concurrente):

```text
  test                         HEAD            CONCURRENTE          clase
  test_vm8_register009         VERDE           ROJO (assertEqual 'gmc/gmc_8_1_d.h'
                                                != 'include/asic_reg/...')  REGRESSION
  test_p003                    ROJO rc=1       VERDE                MEJORA (ajeno)
  test_p004                    ROJO rc=1       VERDE                MEJORA (ajeno)
  test_p005                    VERDE           VERDE                igual
  test_target_identity009      VERDE           VERDE                igual
  test_p0_2_conflict014        ROJO            ROJO (otro motivo)    CAMBIO_DE_MOTIVO
  test_p0_2_consumer015        ROJO            VERDE                MEJORA (ajeno)
  test_cobertura_root013       VERDE           VERDE                igual
  test_cobertura_drift015b     VERDE           VERDE                igual
```

**Una regresión de contrato, medida:** `test_vm8_register009` —
`'gmc/gmc_8_1_d.h' != 'include/asic_reg/gmc/gmc_8_1_d.h'`.

El resto de cambios de estado son el trabajo del otro autor aternizando, no
regresiones mías ni suyas en la semántica que toco.

**Clasificació: CONTRACT_REGRESSION.** No se corrige con otra transformación
arbitraria. La representación contractual vigente en RXRE es «ruta relativa a
`amd_root` con prefijo `include/asic_reg/`»; el hunk la relaja. El apuro no lo
resuelvo en esta iteración porque `reg_resolve.py` está en edición ajena.

## A/F DEL DIFF AJENO — ya se había dicho, queda MES:

`semantic_conflict = len(applicable_values) > 1 if in_target else False`
**no contiene ningún consumer**. Es la capa C etiquetada como F. El cambio
concurrente es correcto en separar A de F, pero su F está **mal computada**:
continúa calculada con la misma regla de «dos valores aplicables», solo que
con otro nombre. La forma correcta, ya medida en 1619:

```text
  F ⇔ ∃ consumer c  con  |{ binding(c) }| > 1
  binding(TU,símbolo) = definición que el preprocesador ve en esa TU
```

## BINDING — contrato técnico, y la precedencia se validó en el corpus real

```text
  binding(TU, symbol)  :=  la definición que ve el preprocesador en esa TU
  precedencia  validada con el corpus (no como ley universal de C):
      TU-local #define  >  última definición visible tras includes

  Verificado en los 9 headers del universo GFX8 target:
    · include/asic_reg/{gca,gmc,bif,oss,dce,smu}_*.h  → 0 condicionales
         (los `#ifdef` están en sdma1/* y dpcs/*,  fuera del universo target)
    · las 4 TU del target tienen #ifdef de config, no de mm*
    · ningún mm* se redefine dos veces dentro de la misma TU
    · 0 #undef en include/asic_reg
  → la precedencia medida se sostiene para ESTE target;  no afirmo más.
```

## find_define_all — contrato de extensión (diseñado, NO implementado)

```text
  DEFINITION_ORIGIN=HEADER | TU_LOCAL
  symbol · file · origin · value · source_line · include_context
  solo se implementa en una ruta segura (worktree aislado + reconciliación).
  Hoy: find_define_all solo recorre include/asic_reg,  así que no ve los
  #define locales  (9 defineks en 4 TU,  3 que sobresacan).
```

## ORACLE INDEPENDIENTE — estado

```text
  gcc -E -dM + gcc -H   ·  no importa reg_resolve.py ·  no importa clasificar()
  Valida sobre los 5 canónicos:
    mmBCI_DEBUG_READ   3 valores · 5 TU · 0 consumers · F=false
    mmMC_CG_DATAPORT   2 valores · 5 TU · 0 consumers · F=false
    mmSMC_IND_INDEX_11 1 valor   · vi.c → 0x1ac · F=false
    mmMP0PUB_IND_INDEX #define local vi.c → 0x180 · F=false
    mmVCE_LMI_BAR0     #define local vce_v3_0.c → 0x8616 (header 0x1096) · F=false
  ORACLE_MATCH/UNEXPLAINED_DELTA ya en 1619:  delta único y explicado (9, modelo
  vs oráculo, toda  – por #define local tratado como consumer en el modelo).
```

## EL CLAIM VIEJO, SUPERCEDED

```text
  mmMC_CG_DATAPORT = semantic_conflict=true        SUPERSEDED
  REASON = CONSUMER_LEVEL_DISPROVES_CONFLICT
```

Sobrevive de ese trabajo: VALUE_DISAGREEMENT, TARGET_APPLICABILITY, TU_APPLICABILITY.
Refutado: `applicable_values > 1 → semantic_conflict`.

## MUTATION

```text
  10/10 muertas del clasificador  (robustez del modelo, no independencia)
  Las 4 para el oráculo  (consumer_count ignorado · TU local ignorado ·
  binding incorrecto · consumer-less tratado como conflict) siguen pendientes:
  no se implementan hasta que el contrato CONSUMER tenga una ruta estable.
```

## COBERTURA

```text
  INVALIDATED_BY_CONCURRENCY  (1614)
  VALIDATED_COVERAGE = NONE
  No reejecutar mientras el SHA de reg_resolve.py cambie.
```

## P0.2

```text
  P0.2_STATUS = REOPENED_RECONCILIATION
  no se declara IMPLEMENTED+VALIDATED en esta iteración.
```

## NEXT_FRONTIER

1. **D(n) de contrato:** el campo `rel`, o se revierte a la ruta relativa a
   `amd_root`, o se migra `test_vm8_register009.py` y los consumidores
   con un nuevo contrato explícito.  No decidir sin el otro autor.
2. **Stratégie de F** en el change ajeno: cambiar de «dos aplicables» a
   «dos bindings por consumer» es un cambio pequeño y compatible.
3. **Git worktree aislado** para implementar la integración, preservando el
   patch concurrente (ya en `artifacts/concurrencia/`).
4. **Mutation del oráculo** cuando el contrato esté estabilizado.
5. **Cobertura** solo con SHA quieto.
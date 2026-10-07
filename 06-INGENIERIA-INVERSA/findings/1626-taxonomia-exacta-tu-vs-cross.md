# 1626 — Taxonomía exacta, nombres unívocos: la de `mmMC_CG_DATAPORT` es TU_VALUE_DIVERGENCE, no CROSS_TU

```text
CLASSIFICATION=TAXONOMIA_EXACTA+DECISION_DE_NOMENCLATURA+SCOPE_CLARIFICADO
WORK_CLASS=RXRE-020-TAXONOMIA-FINAL
AUTOR=AGENTE_RXRE020
FECHA=2026-10-07
P0.2_STATUS=REOPENED_RECONCILIATION
RUNTIME=NOT_RUN
WRITE_EXECUTION=NINGUNO
MODIFICATIONS=solo este hallazgo
```

## LA CORRECCIÓN DE NOMENCLATURA (el punto que pediste)

```text
  CROSS_TU_VALUE_DIVERGENCE  =  dos TUs **CONSUMER** (que USAN el símbolo)
                                 con bindings distintos
                              =>  exige CONSUMERS.  0 consumers ⇒ NO lo es

  TU_VALUE_DIVERGENCE        =  dos TUs **visibles** (quel símbolo aparece
                                 tras preprocesar, las usen o no) con valores
                                 distintos
                              =>  NO exige consumers.

  mmMC_CG_DATAPORT
      5 TU visibles  ·  valores 0xa32 (gfx_v8_0.c) y 0xa21 (otras 4)
      consumers = 0
      =>  TU_VALUE_DIVERGENCE = true
          CROSS_TU_VALUE_DIVERGENCE = **N/A** (no hay consumers)
          NÃO se puede llamar "CROSS_TU"  cuando los consumers son cero.
```

Mi 1624/1625 usaba CROSS_TU_VALUE_DIVERGENCE para ese caso.  Es un error
que ya medí y que este hallazgo corrige.

## TAXONOMÍA — cada categoría con su observación y distintiva

```text
  VALUE_DISAGREEMENT
    activa:      |global_values| > 1          (corpus, todas as cabeceras)
    diferencia:  no implica visibilidad ni uso
    ¿consumer?:  NO
    ¿TU?         NO
    ¿ocurrencia?:NO

  TARGET_APPLICABILITY
    activa:      la definición está en el contexto de esta placa
                 (header de TU que la consume, o #define local de TU del target)
    diferencia:  puede no tener consumer que la use
    ¿consumer?:  NO (CONSUMER_REACHABILITY aparte)

  TU_VISIBILITY
    activa:      la definición aparece tras preprocesar la TU
                 (gcc -E -dM sobre la TU sintética)
    diferencia:  puede no ser usada como consumer (puede estar en un header
                 que la TU incluye por otros símbolos)
    ¿consumer?:  NO

  CONSUMER_REACHABILITY
    activa:      existe uso textual del símbolo en la TU (consumer = TU)
    diferencia:  visibilidad sin uso NO activa esto
    ¿TU?         SÍ (la TU es el consumer)

  CONSUMER_BINDING
    activa:      el valor que ve esa TU (y esa ocurrencia)
    regla:       #define propio de la TU > header incluida (última en orden)
    ¿ocurrencia?: SÍ: binding es por ocurrencia/contexto

  TU_VALUE_DIVERGENCE
    activa:      2+ TUs visibles con valores distintos del símbolo
    diferencia:  NO exige consumer;  difiere de CROSS_TU_VALUE_DIVERGENCE

  CROSS_TU_VALUE_DIVERGENCE
    activa:      2+ TUs que USAN el símbolo con bindings distintos
    diferencia:  exige consumers;  subcaso estricto de TU_VALUE_DIVERGENCE

  TU_MULTI_BINDING
    activa:      en una MISMA TU, 2+ ocurrencias del símbolo ven bindings
                 distintos  (solo con #undef/#define explícito)
    diferencia:  ocurre DENTRO de un único consumer
```

Reglas de no implicación (ninguna activa a otra):
```text
  VALUE_DISAGREEMENT  ⇒  TARGET_APPLICABILITY     No
  TARGET_APPLICABILITY ⇒ TU_VISIBILITY            No(⊂) Sí, pero no uso
  TU_VISIBILITY       ⇒ CONSUMER_REACHABILITY     No
  CONSUMER_REACHABILITY ⇒ TU_MULTI_BINDING        No
  TU_MULTI_BINDING    ⇒ CROSS_TU_VALUE_DIVERGENCE No (intra-TU)
```

## La decisión en SEMANTIC_CONFLICT, con el ámbito correct

```text
  SEMANTIC_CONFLICT_FOR_REGISTER_MACRO_BINDING
    = REDUNDANT / NOT_APPLICABLE  para esta placa / GFX8
    · el corpus tiene 0  redefiniciones · 0 #undef · 0 condicionales en las 9
      cabeceras · 0 cardinalidad>1 por (TU, símbolo)
    · UNA definición efectiva por ocurrencia por construcción de C
    · NO generalizar:  «SEMANTIC_CONFLICT no existe en RXRE» queda ABOLIDO.
      Otros subsistemas (runtimes, acoplde de anillo, flags de PM4…)  pueden
      requerir una categoría así,  y no se hanegado.
```

## LOS CASOS CANÓNICOS, completos y corregidos

```text
  mmBCI_DEBUG_READ
    VALUE_DISAGREEMENT  true (3)
    TARGET_APPLICABILITY  1 (gca/gfx_8_0_d.h = 0x24eb)
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 0
    CONSUMER_BINDING    —
    TU_VALUE_DIVERGENCE true (se ve 0x24eb en 5 TU,  no hay otros valores
                         aplicables)  → false,  todas coinciden
                       mejor: false (una sola valoración aplicable)
    CROSS_TU_VALUE_DIVERGENCE  N/A (0 consumers)
    TU_MULTI_BINDING    false

  mmMC_CG_DATAPORT
    VALUE_DISAGREEMENT  true (2)
    TARGET_APPLICABILITY 2 (gmc_8_1_d.h, gmc_8_2_d.h)
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 0
    CONSUMER_BINDING    —
    TU_VALUE_DIVERGENCE true (0xa32 en gfx_v8_0.c vs 0xa21 en las otras 4)
    CROSS_TU_VALUE_DIVERGENCE  N/A (0 consumers)
    TU_MULTI_BINDING    false

  mmSMC_IND_INDEX_11
    VALUE_DISAGREEMENT  false (1)
    TARGET_APPLICABILITY 3 cabeceras smu
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 1 (vi.c)
    CONSUMER_BINDING   vi.c → 0x1ac
    TU_VALUE_DIVERGENCE false (todas las visibles: 0x1ac)
    CROSS_TU_VALUE_DIVERGENCE false (una sola TU consumer, y coinciden)
    TU_MULTI_BINDING    false
```

## ORACLE (igual de antes, sin tocar)

```text
  gcc -E -dM  binding   ·  gcc -H  includes
  no importa reg_resolve.py · no importa clasificar()
```

## P0.2

```text
  P0.2_STATUS=REOPENED_RECONCILIATION
  Cobertura:  INVALIDATED (1614).  No reejecutar con SHA en movimiento.
  artifacts/concurrencia/ intacto.
```

## REGLA FINAL verificada

```text
  TU_VALUE_DIVERGENCE       ≠  CROSS_TU_VALUE_DIVERGENCE  ≠  TU_MULTI_BINDING
  consumer divergence  exige consumers.  TU divergence no.
```
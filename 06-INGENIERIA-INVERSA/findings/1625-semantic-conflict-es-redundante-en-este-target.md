# 1625 — `SEMANTIC_CONFLICT` es redundante para este target: no hay observación del corpus que lo active

```text
CLASSIFICATION=DECISION_SEMANTICA+MEDICION_DE_CORPUS
WORK_CLASS=RXRE-019-DEFINIR-SEMANTIC-CONFLICT
AUTOR=AGENTE_RXRE019
FECHA=2026-10-07
P0.2_STATUS=REOPENED_RECONCILIATION
RUNTIME=NOT_RUN
WRITE_EXECUTION=NINGUNO
MODIFICATIONS=solo este hallazgo
```

## DECISIÓN: opción B

```text
  SEMANTIC_CONFLICT es REDUNDANTE / MAL DEFINIDO
  -> Se ELIMINA como categoría y se reemplaza por las categorías que el
     preprocesador y el corpus observan DISTINCTAMENTE.
  NO se preserva el nombre por compatibilidad histórica.
```

## Por qué — la cadena de fenómenos, cada uno con su

```text
  VALUE_DISAGREEMENT        distintos valores del símbolo en el corpus
  TARGET_APPLICABILITY      definiciones del target
  TU_VISIBILITY             definiciones visibles en una TU
  CONSUMER_REACHABILITY     el símbolo se usa en una TU
  CONSUMER_BINDING          el valor que ve una ocurrencia concreta
  CROSS_TU_VALUE_DIVERGENCE consumers distintos con valores distintos
  TU_MULTI_BINDING          dos bindings del mismo símbolo en dos puntos
                            de la MISMA TU  (solo con #undef+#define)
```

## La pregunta que cerró la iteración

```text
  ¿Qué observación real del corpus pondría SEMANTIC_CONFLICT = true?

  Opción «dos definiciones compiten por el mismo binding de una ocurrencia»:
    IMPOSIBLE por construcción de C.  En un punto dado del source existe UNA
    definición de macro,  no dos.  El preprocesador resuelve,  no ambiguiza.

  Opción «la misma identidad semántica de consumer con dos bindings
    incompatibles y sin resolución determinística»:
    la identidad candidata (TU) tiene UN ciclo de gcc -E  y UN entorno de
    macros.  Cardinalidad medida: |{binding(TU,mm*)}| = 1  en TODOS los pares.
    0 redefiniciones · 0 #undef · 0 resoluciones "ambiguas" en el corpus.

  Opción «TU_MULTI_BINDING»:
    el fixture sintético lo activa ··
        #define mmFIX 0x10 · uso · #undef · #define 0x11 · uso
    y eso es lo que valida ese fixture:  TU_MULTI_BINDING,  NO
    SEMANTIC_CONFLICT.  En el corpus:  0 ocurrencias.  Los #ifdef de las TU
    del target guardan código runtime (__BIG_ENDIAN, CONFIG_X86_64),  no
    definiciones de mm*.  Y ningún um* se redefine dos veces en la misma TU.
```

## SEMANTIC_CONFLICT_REAL_CASE = NOT_FOUND, y por qué no hay que inventarlo

```text
  A) categoría real y necesaria        -> RECHAZADA por encima
  B) redundante/mal definida           -> ESTA
  C) capa superior al binding de una TU -> lo que queda es
     CROSS_TU_VALUE_DIVERGENCE, y ese ya tiene su categoría
```

El «falso conflicto» que llamaba la atención de P0.2  (mmMC_CG_DATAPORT)  se
declara  hoy como  CROSS_TU_VALUE_DIVERGENCE  con 0 consumers,  y eso es
honesto:  es un hecho del corpus,  no una ambigüedad de ningún consumer.

## LOS CASOS CANÓNICOS, con su clasificación COMPLETA

```text
  mmBCI_DEBUG_READ
    VALUE_DISAGREEMENT  true (3)
    TARGET_APPLICABILITY  1  (gca/gfx_8_0_d.h = 0x24eb)
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 0
    CONSUMER_BINDING    —
    TU_MULTI_BINDING    false
    CROSS_TU_VALUE_DIVERGENCE false  (0 consumers)
    SEMANTIC_CONFLICT   ELIMINADO

  mmMC_CG_DATAPORT
    VALUE_DISAGREEMENT  true (2)
    TARGET_APPLICABILITY  2  (gmc_8_1_d.h, gmc_8_2_d.h)
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 0
    CONSUMER_BINDING    —
    TU_MULTI_BINDING    false
    CROSS_TU_VALUE_DIVERGENCE TRUE    (gfx_v8_0.c 0xa32 vs el resto 0xa21)
    SEMANTIC_CONFLICT   ELIMINADO

  mmSMC_IND_INDEX_11
    VALUE_DISAGREEMENT  false (1)
    TARGET_APPLICABILITY  3 cabeceras smu
    TU_VISIBILITY       5 TU
    CONSUMER_REACHABILITY 1  (vi.c)
    CONSUMER_BINDING   vi.c -> 0x1ac
    TU_MULTI_BINDING    false
    CROSS_TU_VALUE_DIVERGENCE false  (4 TU potenciales coinciden en 0x1ac)
    SEMANTIC_CONFLICT   ELIMINADO
```

## ORACLE

```text
  gcc -E -dM  +  gcc -H  ·  binding por gcc,  no por reg_resolve ni clasificar()
  Un #define que nombra un símbolo no lo consume.
```

## PRODUCE

```text
  PRODUCER_STABILITY=NO  (el autor ajeno sigue editando reg_resolve.py)
  INVALIDATED_COVERAGE: la de 1614 ({ok:402, SIN_CHOSEN:975, error:1256})
  VALID_COVERAGE=NONE  (no reejecutar con SHA en movimiento)
  artifacts/concurrencia/ intacto
```

## P0.2

```text
  P0.2_STATUS=REOPENED_RECONCILIATION
  reclamo superseguido:  mmMC_CG_DATAPORT = semantic_conflict=true
  REASON=CONSUMER_LEVEL_DISPROVES_CONFLICT  (esta iteración lo cierra con
  la semántica:  no existe el evento que lo active)
```

## NEXT_ACTION

```text
  1.  Contrato de `rel` (hunk 1):  decidir revertir a relpath(amd_root)  u
      migrar consumidores.  Medido: 1 regresión reproducida  (test_vm8…).
  2.  F en diff ajeno:  reemplazar la categoría  y la formula
      `len(applicable_values) > 1`  por las categorías validadas arriba.
  3.  `find_define_all` extender a #define de TU  (contrato ya diseñado).
  4.  Mutation del oráculo cuando cambie el contrato.
  5.  Cobertura solo con SHA quieto.
```

## REGLA FINAL verificada

```text
  diferencia de definiciones ≠ visibilidad ≠ uso ≠ binding
    ≠ divergencia entre TUs ≠ conflicto
```

Cada flecha tiene una observación distinta;  `SEMANTIC_CONFLICT` no tiene
ninguna pregunta del corpus que lo active,  así que no es una categoría.  Lo
que queda en su lugar ya existe:  CROSS_TU_VALUE_DIVERGENCE.
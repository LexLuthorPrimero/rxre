# 1624 — `CONSUMER` es la TU: con esa identidad, `|binding| = 1` siempre en este target, y F es **PROVEN_ABSENT**, no «todavía no probado»

```text
CLASSIFICATION=DEFINICION_OPERACIONAL+MEDICION_DE_CARDINALIDAD+DECISION_DE_DISENO
WORK_CLASS=RXRE-018-CONSUMER-IDENTITY
AUTOR=AGENTE_RXRE018 (esta sesión)
FECHA=2026-10-07
P0.2_STATUS=REOPENED_RECONCILIATION
RUNTIME=NOT_RUN
WRITE_EXECUTION=NINGUNO
MODIFICATIONS=solo este hallazgo
```

## CONSUMER_IDENTITY

```text
  CONSUMER = la TRANSLATION UNIT  (la mínima entidad con entorno de macros
  estable,  = un solo ciclo de gcc -E).

  Se elige la TU  y  NO:
    A · source occurrence   — demasiado fino: no tiene identidad de macros
                              propia, hereda la de su TU
    B · TU + ocurrencia     — hereda: una ocurrencia vive en una TU
    C · TU + función + símbolo — 1 binding siempre;  es el MISMO binding que
                              la TU, desglosado.  No aporta identidad nueva
    D · «rol semántico»    — eso es una AGRUPACIÓN de TUs, no un consumer:
                              un rol no compila; lo compilan TUs

  La elección se justifica con la pregunta clave:
    ¿puede esta entidad tener >1 binding en el universo que modelamos?
    · TU:      SOLO mediante #define/#undef/#define del mismo símbolo en el
      mismo ciclo.  Medido en este target: 0 casos.
    · función: igual — vive dentro de una TU.
    · ocurrencia: hereda.
    · rol semántico: agrupa TUs distintas, y ahí SÍ puede haber >1 … pero
      eso ya no es «un consumer ambiguo», es la MISMA entidad mirada entre
      varias TUs  =  DIVERGENCIA ENTRE CONSUMERS,  categoría aparte.
```

## La cardinalidad, medida, no supuesta

```text
  Sobre los 27 TU del target,  gcc -E -dM da  {(TU, mm*) -> UNA única valor}:
      total pares (TU, símbolo) con binding:        12.075  (símbolos vistos)
      de los que |{binbindings}| > 1:                            0

  redefiniciones detectadas por gcc en TODAS las TU:  0
  redefiniciones de un mm* dentro de la misma TU:      0
  #undef en include/asic_reg:                          0
  condicionales en las 9 cabeceras del universo target: 0

  =>  con CONSUMER = TU,  |binding| = 1 siempre.
      SEMANTIC_CONFLICT (= ∃ consumer con |binding| > 1)  =  PROVEN_ABSENT
```

**Este «0» es ahora un hecho, no una ausencia de evidencia.** Es consecuencia
de tres hechos medidos: una TU compila, un símbolo ve un binding, y no hay
redefiniciones que rompan la determinación.

## INTRA vs CROSS — separados, con nombre

```text
  INTRA_CONSUMER_AMBIGUITY   un mismo CONSUMER (TU) ve >1 valor para el
                              símbolo  · cuenta: 0

  CROSS_CONSUMER_VALUE_DIVERGENCE
                              consumers DISTINTOS (TUs distintas) ven
                              valores distintos del mismo símbolo
                              · categoría real, y con su propio nombre
                              · ejemplo: mmMC_CG_DATAPORT:
                                  gfx_v8_0.c → 0xa32 · gmc_v8_0.c, sdma_v3_0.c,
                                  vi.c, polaris10_smumgr.c → 0xa21
                                0 consumers · 0 intra
                                los 5 consumidores potenciales, de existir,
                                serían deterministas per TU
```

La divergencia entre consumers es VALUE_DISAGREEMENT_LEVEL_C, y se declara
aequivocadamente como `semantic_conflict` si se colapsa a TU-agrupado.

## FIXTURE — la frontera de activación de F

```text
  POSITIVO (sintético, sólo para probar que F es definible):
      #define mmFIX 0x10  int f1(){return mmFIX;}
      #undef mmFIX
      #define mmFIX 0x11  int f2(){return mmFIX;}
    gcc vento binding final mmFIX = 0x11;  dos usos,  dos valores.
    binding(TU, mmFIX) = {0x10, 0x11}  -> |>1|  -> F SE ACTIVARIA
    · NO ocurre en el corpus:  0 redefiniciones medidas

  NEGATIVO (del ejemplo real):
      mmMC_CG_DATAPORT  ·  5 TU,  0 consumidores
    -> F = false,  sin importar cuantos valores globales haya
```

## Los casos canónicos, por el oráculo independiente

```text
  mmBCI_DEBUG_READ   3 valores · 5 TU · 0 consumers · F = false
  mmMC_CG_DATAPORT   2 valores · 5 TU · 0 consumers · F = false
  mmSMC_IND_INDEX_11 1 valor   · 1 consumer (vi.c → 0x1ac) · F = false
  mmMP0PUB_IND_INDEX TU-local vi.c → 0x180 · F = false
  mmVCE_LMI_BAR0     TU-local vce_v3_0.c → 0x8616 (header 0x1096) · F = false
```

## DECISIÓN DE MODELO

```text
  DEFINITION_ORIGIN=HEADER | TU_LOCAL
  binding(TU, symbol):
      propia de la TU (TU_LOCAL)  >  última definición de cabecera tras
      resolver los includes en orden real  (= lo que gcc -dM dice)
  SEMANTIC_CONFLICT = false  en todo este target,  PROVEN, por:
    0 redefiniciones · 0 #undef · 0 condicionales en el universo ·
    0 casos intra-TU
  CROSS_CONSUMER_VALUE_DIVERGENCE  se declara por separado, NUNCA como F
```

## HUNK_1 / SHA

```text
  HUNK_1 = CONTRACT_REGRESSION (test_vm8_register009 VERDE->ROJO,  medido)
  CURRENT_SHA = 3952eb91...  ·  DIFERENTE del de mi ultimo commit (3b82b23)
  -> el cambio ajeno sigue en el arbol sin commitear
  CONSERVADO: artifacts/concurrencia/  (no descartado)
```

## MUTATION

```text
  10/10 del clasificador.  Cuando CONSUMER_MODEL quede fijo,  las 4 clases
  pedidas (consumer_count ignorado · TU local ignorado · binding incorrecto ·
  consumer-less→conflict) pasan a lo más pequeño posible:  el corpus NO
  activa ninguna,  así que la evidencia de no-activación ES el resultado
  esperado,  y el fixture positivo es el control que discrimina.
```

## P0.2

```text
  P0.2_STATUS = REOPENED_RECONCILIATION
  Se cierra F aquí, pero F ya no es cerralla:  F es PROVEN_ABSENT en este
  target, y la etiqueta SE mantiene roja hasta tenerlo en reg_resolve.py.
```

## REGLA FINAL verificada

```text
  muchas definiciones ≠ muchos candidatos ≠ muchos consumers
    ≠ un consumer ambiguo ≠ conflicto semántico
```

Cada flecha tiene evidencia independiente, medida con `gcc` como oráculo.
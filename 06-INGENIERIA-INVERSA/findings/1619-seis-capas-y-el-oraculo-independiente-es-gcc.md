# 1619 — Las seis capas de una definición de registro: el conflicto semántico es **cero** para esta placa, y el oráculo independiente es ahora `gcc`

```text
CLASSIFICATION=RECONCILIACION_EN_SEIS_CAPAS+ORACLE_INDEPENDIENTE+CONGELADO_DE_PRODUCTOR
WORK_CLASS=RXRE-016-P0.2-REAPERTURA
AUTOR=AGENTE_RXRE016 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f@c7 · CHIP_POLARIS12 · gfx_8_0
MODIFICATIONS=NINGUNO sobre reg_resolve.py · target.py · conflicts.py
              +3 scripts nuevos bajo tools/rxre/tests/
              + artifacts/concurrencia/  (registro del cambio ajeno, NO descartado)
WRITE_EXECUTION=NINGUNO · sin MMIO, sin hardware, sin firmware, sin VBIOS,
                sin tocar Intel, sin tocar display
P0.2_STATUS=REOPENED_RECONCILIATION
RUNTIME=NOT_RUN · todo es lectura de fuente y gcc sobre TU sinteticas
```

## EL BLOQUEO DE CONCURRENCIA, registrado y no resuelto

```text
  CURRENT_HEAD   1e390a7014d44a537b979403056b7825c1825a76
  CURRENT_SHA    3952eb914bf1e6f6f1f370382fd733e4516fe8d057f7d6d4dd91600d60ddb966
  ficheros modificados sin commit        112   (+3533 inserciones, -303)
  artefacto de lo anterior
    artifacts/concurrencia/diff_concurrente_2026-10-07.patch   5169 lineas
    artifacts/concurrencia/status_concurrente_2026-10-07.txt
    artifacts/concurrencia/reg_resolve.sha256
  NO descartado · NO sobrescrito · NO reset · NO checkout · NO staged
```

**NO he podido congelarlo.** Congelar exige que el otro autor deje de editar, y
eso no está en mi mano. Lo que sí he hecho es **quitarle la dependencia**: el
oráculo de esta iteración **no lee `reg_resolve.py`**, así que la reconciliación
ya no está bloqueada por su ritmo de trabajo. Es la única forma de «congelar»
que está realmente al alcance.

Además, el cambio ajeno toca **ficheros míos**: `test_p003.py` (+64),
`test_p004.py` y `test_p0_2_conflict014.py` (+22), los tres adaptados al
nombre de campo nuevo. Y hay un `P0.2_CLOSURE.md` sin commitear que declara
`P0.2_STATUS=IMPLEMENTED+VALIDATED`.

### Clasificación del diff ajeno de `reg_resolve.py` (8 hunks)

| # | contenido | capa | clasificación |
|---|---|---|---|
| 1 | `relpath(p, amd_root)` → `relpath(p, base)` | — | **OTRO_TRABAJO.** Cambia la ruta que RXRE reporta por definición. Rompe a todo consumidor que use el prefijo `include/asic_reg/…`. No es P0.2 |
| 2–4 | añade todos los `gmc_8_*_d.h` a `order` | **B/C** | **P0.2 · TARGET_APPLICABILITY.** Es lo que ensancha `in_target`, y por eso `mmMC_CG_DATAPORT` pasa a tener 2 candidatos aplicables |
| 5–8 | separa `value_disagreement` de `semantic_conflict`; define `applicable_candidates = [h for h in hits if h in in_target]`; retira la arista de inclusión de `gmc_v8_0.c` | **A y F** | **P0.2**, pero **F mal calculada** (ver abajo) |

**La objeción de fondo, y es una sola línea de código:**

```python
  semantic_conflict = len(applicable_values) > 1 if in_target else False
```

Eso es la **capa C** (TU_APPLICABILITY), etiquetada como **F**
(SEMANTIC_CONFLICT). No aparece ningún consumer en la expresión. Con la
definición de las seis capas, lo que ese código calcula es «más de un valor
distinto entre definiciones aplicables» — que es un hecho real, pero no es un
conflicto semántico, y el nombre afirma que lo es.

---

## LAS SEIS CAPAS, y la regla de no colapsar A → F, B → F, C → F

```text
  A  VALUE_DISAGREEMENT   el símbolo tiene valores distintos en el corpus
  B  TARGET_APPLICABILITY la definición pertenece al contexto/target
  C  TU_APPLICABILITY     la definición está disponible para una TU relevante
  D  CONSUMER_REACHABILITY esa TU USA el símbolo en su código
  E  CONSUMER_RESOLUTION  qué valor ve ESE consumer
  F  SEMANTIC_CONFLICT    algún consumer cuyo binding NO queda determinado
                          unívocamente entre candidatos incompatibles

  ALL DEFINITIONS → TARGET → TU → CONSUMER → ACTUAL RESOLUTION → CONFLICT
```

**F no se puede derivar de A, B ni C.** Un símbolo con tres valores globales y
una definición aplicable no está en juego; dos definiciones aplicables no
compiten por nada; y la falta de un origen determinado en una capa tampoco.

---

## ORACLE_INDEPENDENCE

```text
  MODELO     test_p0_2_consumer015.py · clasificar() · regex propia
  ORACULO    oracle_independiente016.py · gcc -E -dM  +  gcc -H

  El binding (capa E) lo decide el PREPROCESADOR DE C,  no una regex.
  Se construye una TU sintetica por TU real con
    · los #include asic_reg EN SU ORDEN REAL
    · los #define mm* propios DESPUES  (que es donde estan: vi.c:345, includes
      en la linea 20)
  y se lee lo que gcc ve.  No importa reg_resolve.py.  No importa
  clasificar().  No reutiliza resultados ya clasificados.

  MEDIDO Y RECONOCIDO:  gcc -E NO conserva las lineas #define de las cabeceras
  de asic_reg  (41 lineas de salida para ~12.000 macros).  Por eso el binding
  se lee con -dM,  que si.  Queda registrado para que no se repita.

  CAPA C, contrastada por granularidad de FICHERO:
    TU con el MISMO conjunto de includes por regex y por gcc -H:  27/27
    solo en mi regex: 0        solo en gcc: 0
```

## LOCAL_TU_DEFINES

9 `#define mm*` propios en 4 TU del target (`gfx_v8_0.c` 2, `gmc_v8_0.c` 1,
`vce_v3_0.c` 4, `vi.c` 2). **3 sobrescriben** con otro valor:

```text
  gfx_v8_0.c  mmSPI_WCL_PIPE_PERCENT_GFX_DEFAULT = 0x7ffffff
              gc/gc_10_3_0_default.h             = 0x7c1f07f
  vce_v3_0.c  mmVCE_LMI_VCPU_CACHE_40BIT_BAR0   = 0x8616
              vce/vce_4_0_offset.h               = 0x1096   (+1, +2 igual)
```

`find_define_all` solo recorre `include/asic_reg` y **no puede representar la
definición visible para esa TU**. Por eso `DEFINITION_ORIGIN` es obligatorio:
`HEADER` o `TU_LOCAL`. Y no se puede inferir que el valor del header es el
consumido: en los tres casos de sobrescritura, **no lo es**.

## CONSUMER_REACHABILITY y CONSUMER_RESOLUTION

```text
  simbolos mm* totales                                 93.011
    NO_APLICABLE                                      80.927
    APLICABLE_SIN_CONSUMER                            11.495
    CONSUMIDOR_CON_UN_VALOR                              589
    CONFLICT                                                0

  SEMANTIC_CONFLICT = 0
```

596 (0,64 %) de los símbolos del corpus son alcanzables por un consumer de esta
placa. Y **ninguna TU de las 27 incluye dos cabeceras que den al mismo símbolo
valores distintos**, así que el preprocesador nunca tiene que elegir en
silencio.

## SEMANTIC_CONFLICT_RULE

```text
  SEMANTIC_CONFLICT = true
     <=>  ∃ un CONSUMER c  tal que  |{ binding(c) }| > 1

  binding(TU) = el valor que ve ESA TU,  decidido por el preprocesador:
                 #define propio de la TU   >  (vence a cualquier cabecera)
                 cabecera incluida         >  gana la última en orden de
                                             include si dos discrepan
```

## LOS TRES CASOS CANÓNICOS, por el oráculo independiente

```text
  mmBCI_DEBUG_READ
      global_values       ['0x4eb', '0x24e3', '0x24eb']
      tu_candidates       5 TU  (gfx_v8_0, sdma_v3_0, vce_v3_0, vi.c,
                                 polaris10_smumgr)
      consumer_count      0
      consumer_bindings   {}
      semantic_conflict   False          NOT_ESTABLISHED, no «probado falso»

  mmMC_CG_DATAPORT
      global_values       ['0xa21', '0xa32']
      tu_candidates       5 TU
      consumer_count      0
      consumer_bindings   {}
      semantic_conflict   False          contra P0.2_CLOSURE.md, que dice true
      y lo que gcc ve:    gfx_v8_0.c → 0xa32 ;  gmc_v8_0.c, sdma_v3_0.c,
                          vi.c, polaris10_smumgr.c → 0xa21
                          cada TU ve UN valor.  No hay ambigüedad para nadie.

  mmSMC_IND_INDEX_11
      global_values       ['0x1ac']
      consumer_count      1
      consumer_bindings   {'amdgpu/vi.c': '0x1ac'}
      semantic_conflict   False
```

## FALSE_POSITIVES / FALSE_NEGATIVES / UNEXPLAINED_DELTA

```text
  UNEXPLAINED_DELTA = 0

  Los dos oráculos coinciden en los 93.011 símbolos salvo 9,  y la diferencia
  tiene una causa única y nombrada:

    SIMBOLO_MENCIONADO_SOLO_EN_SU_PROPIO_DEFINE_NO_ES_CONSUMER     9
      mmGRBM_GFX_INDEX_DEFAULT · mmMC_SEQ_MISC0_FIJI · mmMP0PUB_IND_DATA
      mmMP0PUB_IND_INDEX · mmSPI_WCL_PIPE_PERCENT_CS_DEFAULT
      mmSPI_WCL_PIPE_PERCENT_GFX_DEFAULT
      mmVCE_LMI_VCPU_CACHE_40BIT_BAR{0,1}   (+2 más)

    el modelo cuenta como «usado» un símbolo mencionado en el propio #define
    de la TU.  Un #define que nombra un símbolo no lo consume.  La resuelve el
    ORACULO.

    modelo      APLICABLE_SIN_CONSUMER 11.486  CONSUMIDOR_CON_UN_VALOR   598
    oraculo     APLICABLE_SIN_CONSUMER 11.495  CONSUMIDOR_CON_UN_VALOR   589
    NO_APLICABLE  coincide EXACTO: 80.927 en ambos
```

`FALSE_POSITIVES` de la regla implementada por el otro autor **no es 0**: son
todos los símbolos que él llama `SEMANTIC_CONFLICT` sin consumer. Con F
definido por consumer, la cifra correcta es 0, pero **su campo no mide F**, y
por eso no puedo confirmar su `FALSE_POSITIVES=21985 → 0` como escrita.
`FALSE_NEGATIVES`: 0 por construcción en ambas, porque F ⊆ A.

## COBERTURA

```text
  INVALIDATED   artifacts/rxre_cobertura_gfx8_20261007_INVALIDADA_por_concurrencia.jsonl
                {ok:402, SIN_CHOSEN:975, error:1256}
  VALID_COVERAGE=NONE
  No se reejecuta mientras reg_resolve.py siga en movimiento.
```

## MUTATION_RESULT

```text
  10/10 muertas  —  robustez del CLASIFICADOR,  NO independencia del oraculo
  INVALIDATED_AS_INDEPENDENT  el modelo contra si mismo no es un segundo
                              modelo;  por eso existe oracle_independiente016
  Pendiente,  segun el encargo:  consumer_count ignorado · TU local ignorado ·
  binding incorrecto · consumer-less tratado como conflict.  No se anaden hasta
  cerrar el modelo CONSUMER,  que es lo que hace este hallazgo.
```

## CRITERIO DE CIERRE — 10 puntos, estado real

| # | condición | estado |
|---|---|---|
| 1 | productor estable | **NO**.  Congelar exigiría que el otro autor pare, y eso no está en mi
  poder.  Lo que sí se ha logrado: el oráculo ya no depende de él |
| 2 | oráculo independiente | **CUMPLIDO**. `gcc -dM` + `gcc -H`, sin `reg_resolve` ni `clasificar()` |
| 3 | local TU defines incluidos | **CUMPLIDO** en el oráculo; **NO** en `find_define_all` |
| 4 | consumer reachability medida | **CUMPLIDO**: 596 de 93.011 |
| 5 | consumer binding reconstruido | **CUMPLIDO**: por el preprocesador |
| 6 | semantic_conflict derivado del consumer | **DEFINIDO**; **NO** implementado en `reg_resolve.py` |
| 7 | `mmMC_CG_DATAPORT` reclasificado | **CUMPLIDO**: `semantic_conflict = False`, `NOT_ESTABLISHED` |
| 8 | `mmSMC_IND_INDEX_11` resuelto | **CUMPLIDO**: `vi.c → 0x1ac` |
| 9 | cobertura válida sin drift | **NO**. INVALIDATED, y bloqueada |
| 10 | mutations 0 survivors | **PARCIAL**: 10/10 del clasificador; las del oráculo pendientes |

**P0.2 no se cierra. P0.2_STATUS = REOPENED_RECONCILIATION.**

## NEXT_FRONTIER

1. **Reconciliar el cambio concurrente con este modelo, no duplicarlo.** Su
   trabajo de A↔F es correcto y utilizable. Lo que hay que cambiar es la
   definición de F: de «más de un valor aplicable» a «más de un valor **por
   consumer**». Es un cambio pequeño sobre una base ya escrita.
2. **`find_define_all` debe incluir los `#define` de la TU**, con
   `DEFINITION_ORIGIN` distinto, o la aplicabilidad de `vi.c` y `vce_v3_0.c`
   queda mal. Con `order` extending a `in_target` por cabecera, hoy no hay
   forma de que un `#define` propio entre en el juego.
3. **El hunk 1 del cambio ajeno** (`relpath(p, base)`) rompe consumidores que
   depended del prefijo `include/asic_reg/`. Verificar `handlers.py` y
   `normalize.py` antes de que se commitee, no después.
4. **La prueba de mutación del oráculo**, con las cuatro clases que nombra el
   encargo.
5. **La cobertura**, solo cuando el sha del productor esté quieto.

## REGLA FINAL, comprobada

```text
  un header aplicable no está necesariamente en juego
  un símbolo en una TU no implica que exista consumer
  dos definiciones aplicables no implican conflicto
  y un oracle construido con la misma clasificación que valida
    NO es independiente
```

Las cuatro se han medido sobre 93.011 símbolos con dos mecanismos distintos, y
las tres primeras son la razón de que el conflicto semántico sea **cero**.
# 1616 — CONFLICT necesita el nivel CONSUMER: para esta placa el conflicto semántico es **cero**, y el caso canónico de P0.2 no lo usa nadie

```text
CLASSIFICATION=RECONCILIACION_DE_SEMANTICA+AUTOCORRECCION+DEFECTO_DE_INSTRUMENTO
WORK_CLASS=RXRE-015-P0.2-CONFLICT-CONSUMER
AUTOR=AGENTE_RXRE015 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f@c7 · CHIP_POLARIS12 · gfx_8_0
QUESTION=¿qué es una definición aplicable, y qué es un CONFLICT, cuando se
          exige la cadena TARGET -> TU -> CONSUMER -> DEFINITION -> VALUE?
MODIFICATIONS=NINGUNO sobre reg_resolve.py, target.py ni conflicts.py
              +3 scripts nuevos bajo tools/rxre/tests/
              tools/rxre_cobertura_gfx8.py  (guard de productor, ver 1614)
WRITE_EXECUTION=NINGUNO · sin MMIO, sin hardware, sin firmware, sin VBIOS,
                sin tocar Intel, sin tocar display
RUNTIME=NOT_RUN · lectura de fuente y aritmética
REVISES=1615 (su población de 6 conflictos queda REVISADA)
```

## OLD_RULE

```text
cualquier valor distinto en include/asic_reg  ->  CONFLICT, CHOSEN=null
```

## REFINED_RULE

```text
  INCLUDED     la TU #incluye la cabecera
  APPLICABLE   la TU pertenece al universo del chip del target,  o la propia
               TU lleva el #define del simbolo
  CONSUMER     la TU USA el simbolo en su codigo
  SEES         el valor que ESA TU ve;  el preprocesador ya lo resolvio

  GLOBAL_DISAGREEMENT  mismo simbolo, valores distintos, corpus entero
  TARGET_RELEVANCE     la definicion esta en la clausula del target
  SEMANTIC_CONFLICT    dos definiciones incompatibles para el MISMO CONSUMER

  CONFLICT = true  <=>  existe un CONSUMER para el que la resolucion de la
                        definicion NO es unica:
                          · dos cabeceras que la TU incluye dan valores
                            distintos  (CONFLICT_INTRA_TU),  o
                          · dos consumers ven valores distintos
                            (DISACUERDO_ENTRE_CONSUMERS)
```

## El dato que obliga a añadir el nivel

```text
  grep -rn '\bmmMC_CG_DATAPORT\b'  --include=*.c   ->  0 resultados
  grep -rn '\bmmBCI_DEBUG_READ\b'  --include=*.c   ->  0 resultados
```

**El caso canónico de P0.2 no lo usa ningún consumer del driver.** Sus dos
valores «aplicables» no compiten por nada. Añadir el nivel TU (1615) no
bastaba; hacía falta CONSUMER.

## EVIDENCE — la población, con numerador y denominador

```text
  simbolos mm* en include/asic_reg               93.009
    NO_APLICABLE                                80.934
    APLICABLE_SIN_CONSUMER                      11.486
    CONSUMIDOR_CON_UN_VALOR                        589
    CONFLICT_INTRA_TU                                 0
    DISACUERDO_ENTRE_CONSUMERS                         0

  >>> SEMANTIC_CONFLICT = 0 para CHIP_POLARIS12

  vistos por alguna TU que incluye la cabecera    12.075
  usados por algún consumer TU                       596
```

Los tres niveles se contaron por separado a propósito: una cabecera aplicable
**no es** un símbolo en juego. Solo el 0,64 % de los símbolos del corpus es
alcanzable por un consumer de esta placa.

Ninguna TU de las 27 incluye dos cabeceras que den al mismo símbolo valores
distintos, así que **el preprocesador nunca tiene que elegir en silencio**.
Ese cero es la razón de que el conflicto semántico sea cero, y por eso hace
falta un fixture positivo (§TESTS): sin él, «cero» no distingue «no hay» de
«no se mira».

## CASE_A · `mmBCI_DEBUG_READ`

```text
  GLOBAL           3 valores  (0x4eb, 0x24e3, 0x24eb)   en 6 cabeceras
  TARGET_RELEVANCE 1 aplicable: gca/gfx_8_0_d.h = 0x24eb
  CONSUMERS        NINGUNO
  CLASE            APLICABLE_SIN_CONSUMER
```

Las otras cinco (`gc_9_0_offset.h`, `gfx_6_0`, `gfx_7_0`, `gfx_7_2`,
`gfx_8_1`) no son candidatas por linaje, y esa parte de 1615 se sostiene: sus
TUs son Vega/GFX7 y ninguna menciona `CHIP_POLARIS12`. Lo que 1615 no vio es
que **la applicable tampoco la usa nadie**, así que ni siquiera eso es un
conflicto: es una definición documentada y no leída.

## CASE_B · `mmMC_CG_DATAPORT`

```text
  GLOBAL           2 valores  (0xa21, 0xa32)  en 5 cabeceras
  TARGET_RELEVANCE 2 aplicables: gmc_8_1_d.h (via gmc_v8_0.c, sdma_v3_0.c,
                        vi.c, polaris10_smumgr.c)   y  gmc_8_2_d.h (via gfx_v8_0.c)
  CONSUMERS        NINGUNO
  CLASE            APLICABLE_SIN_CONSUMER

  lo que VE cada TU:
    gmc_v8_0.c, sdma_v3_0.c, vi.c, polaris10_smumgr.c   ->  0xa21
    gfx_v8_0.c                                          ->  0xa32
```

Cinco TU ven el símbolo; **ninguna lo usa**; y cada una ve un único valor, el
de su propia cabecera. Esto refuta a 1615 en su punto central: aquí **no hay
conflicto**, hay desacuerdo entre dos cabeceras de un corpus que nadie consume.
`CHOSEN=null` es la respuesta honesta a *«¿cuál de las dos?»*, pero la
pregunta no se ha hecho.

## CASE_C · `mmSMC_IND_INDEX_11` — el caso donde sí hay cadena completa

```text
  GLOBAL           1 valor  (0x1ac)  en 3 cabeceras smu
  TARGET_RELEVANCE 3 aplicables: smu_7_1_1 / 7_1_2 / 7_1_3
  CONSUMER         amdgpu/vi.c
  SEES             0x1ac        (único)
  CLASE            CONSUMIDOR_CON_UN_VALOR
```

Y su pareja `mmSMC_IND_DATA_11 = 0x1ad` va por la misma TU. Aquí sí existe
`TARGET -> TU -> CONSUMER -> DEFINITION -> VALUE`, y el valor es único. Es la
única de las dos docenas de casos que 1590/1602 seleccionaban donde el trabajo
real está.

## Una quinta categoría que sale del dato

Siete símbolos los usa una TU del target y **la TU lleva su propio `#define`**,
que tapa el de una cabecera prestada. Cuatro coinciden y tres **SOBREPONEN**:

| símbolo | `#define` de la TU | asic_reg | |
|---|---|---|---|
| `mmGRBM_GFX_INDEX_DEFAULT` | `vce_v3_0.c` = 0xe0000000 | `gc_10_3_0_default.h` = 0xe0000000 | coincide |
| `mmMP0PUB_IND_DATA` | `vi.c` = 0x181 | `smu_8_0_d.h` = 0x181 | coincide |
| `mmMP0PUB_IND_INDEX` | `vi.c` = 0x180 | `smu_8_0_d.h` = 0x180 | coincide |
| `mmSPI_WCL_PIPE_PERCENT_GFX_DEFAULT` | `gfx_v8_0.c` = 0x7ffffff | `gc_10_3_0_default.h` = **0x7c1f07f** | **SOBREPONE** |
| `mmVCE_LMI_VCPU_CACHE_40BIT_BAR0` | `vce_v3_0.c` = 0x8616 | `vce_4_0_offset.h` = **0x1096** | **SOBREPONE** |
| `mmVCE_LMI_VCPU_CACHE_40BIT_BAR1` | `vce_v3_0.c` = 0x8617 | `vce_4_0_offset.h` = **0x1097** | **SOBREPONE** |
| `mmVCE_LMI_VCPU_CACHE_40BIT_BAR2` | `vce_v3_0.c` = 0x8618 | `vce_4_0_offset.h` = **0x1098** | **SOBREPONE** |

Y un defecto medible en RXRE: `find_define_all` solo recorre
`include/asic_reg`, así que **no ve el `#define` local** y su `note` cuenta
menos ficheros de los que hay. Para `mmMP0PUB_IND_INDEX` dice
«existe en 1 fichero(s)» y hay 2, uno de ellos en una TU que corre en esta
placa. El valor que rige aquí es 0x180, y RXRE no lo expone.

## TESTS

`test_p0_2_consumer015.py` — **48 checks verdes**. Oráculo: modelo de
referencia construido desde la fuente del kernel; `reg_resolve.py` solo se
interroga para medir su comportamiento, y eso va en el DELTA.

| | prueba | resultado |
|---|---|---|
| T0611 | desacuerdo global sin conflicto semántico | `mmBCI_DEBUG_READ` → `APLICABLE_SIN_CONSUMER` |
| T0612 | dos aplicables, ningún consumer | `mmMC_CG_DATAPORT` → `APLICABLE_SIN_CONSUMER` |
| T0613 | mismo target, TUs distintas | 5 TU en dos grupos (4×0xa21, 1×0xa32); ninguna ve ambos |
| T0614 | `INCLUDED` ≠ `RUNTIME_SELECTED` | 5 TU incluyen, 0 usan; tres niveles, no dos |
| T0615 | la cadena completa | `mmSMC_IND_INDEX_11`: consumer `vi.c` = 0x1ac |

Más **fixtures con control positivo**, que son lo que hace la regla falsable:

```text
  dos cabeceras incompatibles en la MISMA TU -> CONFLICT_INTRA_TU
  una sola cabecera                           -> CONSUMIDOR_CON_UN_VALOR
  #define local por delante                   -> CONSUMIDOR_CON_UN_VALOR
```

Y clasificación **por símbolo**, no solo agregada, con un control explícito:
existen símbolos con consumer **y** desacuerdo global
(`mmSDMA1_POWER_CNTL`, `mmSDMA1_CLK_CTRL`, …), y todos siguen siendo
`CONSUMIDOR_CON_UN_VALOR`. Esa es exactamente la confusión entre
`GLOBAL_DISAGREEMENT` y `SEMANTIC_CONFLICT`.

## MUTATIONS

`mutate_p0_2_consumer015.py` — **10/10 muertas, 0 supervivientes**.

La primera pasada tuvo **5 supervivientes**, y el hueco era mío, no del
mutante: la población y la clasificación por símbolo eran **dos
implementaciones**. `M5` y `M8` cambiaban una y las aserciones miraban la otra.
Se unificaron en un solo `clasificar()`, usado por el corpus y por los
fixtures.

| mutante | muerta por |
|---|---|
| `M1_target_ignorado` | T0611 TARGET_RELEVANCE |
| `M2_chip_no_resuelto` | «la identidad sale de la tabla» |
| `M3_tu_context_eliminado` | T0613 dos grupos |
| `M4_primer_candidato_global` | T0613 dos grupos |
| `M5_consumer_context_eliminado` | clase por símbolo de `mmBCI_DEBUG_READ` |
| `M6_mezclar_consumers` | «ni un solo DESACUERDO_ENTRE_CONSUMERS» |
| `M7_disagreement_es_conflict` | «NO hay ni un solo CONFLICT INTRA-TU» |
| `M8_conflict_oculto` | `CLASIFICADOR` fixture |
| `M9_define_local_ignorado` | `FIXTURE` precedencia del local |
| `M10_acuerdo_global_por_consumer` | «ni un solo DESACUERDO_ENTRE_CONSUMERS» |

## COVERAGE_STATUS

```text
  la corrida de 2.633 registros  INVALIDADA
  {ok:402, SIN_CHOSEN:975, error:1256}
  los 1.256 error empiezan en la fila 1378 y son consecutivos:  otro autor
  editaba tools/reg_resolve.py mientras la corrida lo media.

  NO SE USA COMO MEDICION.  Ver hallazgo 1614,  con el guard de productor que
  lo impide en adelante.
```

## REPAIR_READY

La reparación que propone la evidencia es coser, no añadir:

```text
  target.py            identidad fisica                    ya existe (1601)
  + la fila de amdgpu_pci_table                           fuente, no diccionario
  -> CHIP_POLARIS12
  -> universo de TU que lo nombran
  -> headers aplicables  +  #define propios de esas TU
  -> consumers:  TU que USA el simbolo
  -> CONFLICT solo si un consumer ve mas de un valor
```

Bloqueos y huecos conocidos antes de reparar:

1. `find_define_all` no ve los `#define` de las TU (7 símbolos, 3 con
   sobrescritura real). Sin eso, la aplicabilidad de `vi.c` y `vce_v3_0.c`
   está mal.
2. `target.py::_map_pci_id_to_asic_gfx` duplica `amdgpu_pci_table` con 1 de
   los 8 device id de `CHIP_POLARIS12` (12 %) y no expone el token `CHIP_*`.
3. **HUECO_DE_CONEXIÓN**: nadie llama a `get_current_target` (1601). Sin
   entrada, el pipeline no arranca.
4. **Otro autor edita `reg_resolve.py` sin commitear** y su cambio ya separa
   `value_disagreement` de `semantic_conflict`. No es mío, no lo he tocado y
   no lo commiteado. Reparar encima sería §88.

## LIMITACIONES

- **«la TU nombra `CHIP_POLARIS12`» es un proxy** de «esta TU corre en esta
  placa». 1615 midió la sensibilidad con un criterio más fuerte y la población
  de conflictos no se movió; aquí el corte importa más, y no está medido con
  el mismo cuidado. Un grafo de llamadas desde `asic_type == CHIP_POLARIS12`
  sería más fuerte.
- **«USA el símbolo» es un grep de token en el `.c`.** No distingue un uso
  alcanzable de uno dentro de un `#if 0`, ni el uso indirecto a través de una
  función de otra TU. El modelo no pretende más.
- **`#define` con continuación de línea no se parsean.**
- **`asic_reg` es solo el diccionario de registros.** Las tablas de SOC/NBIF y
  `df_*` no entran, y ahí «aplicable» puede depender de compilación
  condicional y no del include.
- Corpus `linux-7.1.3` frente a kernel en ejecución 7.2.9.

## HISTORIAL

| hallazgo | dice | aquí |
|---|---|---|
| 1576 | dos defectos: `dword_index` y conflicto silencioso | ambos **REVISED** |
| 1584 | `dword_index` inválido en el 73,4 % | **REFUTED** (era la unidad) |
| 1590 | `mmMC_CG_DATAPORT`: dos valores, declarar CONFLICT | el símbolo existe con dos valores; **`CONFLICT` queda REVISADO**: no hay consumer. Su §alineación es **REFUTADA** por 1604 |
| 1592 | P0.3 declara CONFLICT y `chosen=null` | **REVISED** en dos etapas: 1615 (universo) y aquí (faltaba CONSUMER) |
| 1602 | arista de inclusión `gmc_v8_0.c` | **REFUTADA como suficiente** (1615): `gfx_v8_0.c` también corre aquí e incluye `gmc_8_2_d.h` |
| 1604/1607 | unidad = índice dword, `×4` | **PROVEN**, intacto |
| 1615 | 6 conflictos reales que exigen `CHOSEN=null` | **REVISED**: 0 son conflictos semánticos. Aguanta la parte de aplicabilidad por TU |
| 1614 | la cobertura invalidada y su guard | esta iteración |

## NOTA DE ALCANCE

`findings/1589–1592` viven en un `findings/` suelto en la raíz, no en
`06-INGENIERIA-INVERSA/findings/`. `nextnum.py --check 1590` responde
*LIBRE*. Nodo abierto, no mezclado aquí.
# 1615 — P0.2 reconciliado: CONFLICT no es "cualquier valor distinto en el corpus", es desacuerdo entre candidatos **aplicables** a esta placa

```text
CLASSIFICATION=RECONCILIACION_DE_SEMANTICA+DISCRIMINANTE_CRUZADO
WORK_CLASS=RXRE-014-P0.2-CONFLICT-SEMANTICS
AUTOR=AGENTE_RXRE014 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f@c7 · CHIP_POLARIS12 · gfx_8_0
QUESTION=¿qué constituye realmente un CONFLICT para la definición de un registro?
MODIFICATIONS=NINGUNO sobre reg_resolve.py  (prohibido en esta iteración)
              +3 scripts nuevos, todos bajo tools/rxre/tests/
WRITE_EXECUTION=NINGUNO sobre hardware · sin MMIO, sin firmware, sin VBIOS,
                sin cargar módulo, sin tocar Intel, sin tocar display
RUNTIME=NOT_RUN · todo es lectura de fuente y aritmética sobre la salida
PRECEDE_A=HALLAZGO_1604 (unidad)  ·  HALLAZGO_1602 (arista de inclusión)
REVELA_REGRESION=fb8da65 : reg_resolve.py:319-321
```

## Estado

```text
P0.2 = REVISED        (antes: IMPLEMENTED)

OLD_RULE   cualquier valor distinto en include/asic_reg  ->  CONFLICT
NEW_RULE   desacuerdo entre los candidatos APLICABLES a este target

  TARGET      1002:699f · CHIP_POLARIS12 · gfx_8_0
  LINEAGE     amdgpu_drv.c:2041  amdgpu_pci_table  ->  CHIP_POLARIS12
              TU que nombran CHIP_POLARIS12  ->  los headers asic_reg que
              esas TU #incluyen  ->  esos son los candidatos APLICABLES
  ALCANCE     ESTABLECIDO como pertenencia a la clausula de compilacion de
              una TU con ruta de codigo para el chip del target.
              NO es una ruta de runtime y no se afirma que lo sea.
  TESTS       T0601-T0605,  30 checks verdes con el delta fijado por medicion;
              --conformance sale en ROJO con exactamente los 4 huecos que la
              reparacion tiene que cerrar.
  MUTATIONS   9/9 muertas en las siete clases exigidas  (+2 extra)
  NEXT_ACTION reparacion en iteracion separada,  y luego reejecucion de los 2633
```

---

## 1 · La cadena, leída de la fuente y no de RXRE

```text
  amdgpu_drv.c  amdgpu_pci_table      194 filas,  25 chips distintos
    {0x1002, 0x699F, ..., CHIP_POLARIS12}                    línea 2041

  la Build NO puede decidir el target:
    amdgpu/Makefile  compila gfx_v8_0.o, gfx_v9_0.o, gfx_v10_0.o, gfx_v11_0.o,
    gfx_v12_0.o ... A LA VEZ.   163 objetos de bloque,  32 de bloque GFX.
    El corte lo hace la RUTA DE CODIGO por asic_type,  no el Makefile.

  la capa asic_reg NO tiene ni un #include:
    476 cabeceras .h,  0 con #include
    => la clausura es de UN NIVEL y "aplicable" es una relacion DIRECTA
       entre una TU y un header.  No hay transitividad que suponer.

  universo del target:  27 TU nombran CHIP_POLARIS12
    de ellas, 25 headers asic_reg alcanzables, 13 de los cuales definen mm*

  con un criterio MAS FUERTE —solo "nombrar el chip en una condicion de
  asic_type":  26 TU, 25 headers,  Y LOS MISMOS CONFLICTOS.
  La poblacion no depende de lo laxo que sea el proxy.
```

## 2 · El discriminante, y por caso separa los dos casos

Los dos símbolos del encargo se separan con **el mismo criterio** y dan
**veredictos opuestos**. Eso es lo que lo hace buen discriminante: no hay dos
reglas, hay una.

### CASO A — `mmBCI_DEBUG_READ`

```text
  6 definiciones, 3 valores globales distintos:
      gc/gc_9_0_offset.h     0x4eb     no aplicable   (Vega: gfx_v10_0.c,
      gca/gfx_6_0_d.h        0x24e3    no aplicable    gfxhub_v2_0.c,
      gca/gfx_7_0_d.h        0x24eb    no aplicable    kfd_mqd_manager_v9.c)
      gca/gfx_7_2_d.h        0x24eb    no aplicable
      gca/gfx_8_1_d.h        0x24eb    no aplicable
      gca/gfx_8_0_d.h        0x24eb    APLICABLE
                                            via gfx_v8_0.c, sdma_v3_0.c,
                                                vce_v3_0.c, vi.c,
                                                polaris10_smumgr.c

  ESTADO = APLICABLE_SIN_CONFLICTO     1 valor aplicable
  CHOSEN = gca/gfx_8_0_d.h = 0x24eb
```

### CASO B — `mmMC_CG_DATAPORT`

```text
  5 definiciones, 2 valores globales distintos:
      gmc/gmc_6_0_d.h        0xa21     no aplicable
      gmc/gmc_7_0_d.h        0xa32     no aplicable
      gmc/gmc_7_1_d.h        0xa21     no aplicable
      gmc/gmc_8_1_d.h        0xa21     APLICABLE via gmc_v8_0.c, sdma_v3_0.c,
                                              vi.c, polaris10_smumgr.c
      gmc/gmc_8_2_d.h        0xa32     APLICABLE via gfx_v8_0.c

  ESTADO = CONFLICT          2 valores aplicables
  CANDIDATES = [0xa21, 0xa32]   CHOSEN = null
```

**Y un dato que endurece el caso B:** ninguna TU incluye las dos cabeceras. Las
seis de la población son **INTER-TU**. El preprocesador de C
resuelve un conflicto *intra*-TU por orden de `#include` sin decir nada; uno
*inter*-TU no lo resuelve nadie, porque son dos ficheros que corren en **esta
placa** diciendo cosas distintas. Por eso `CHOSEN=null` es la respuesta honesta,
y por eso la regla que hoy elige no puede sostenerse.

## 3 · La población completa, con numerador y denominador

```text
  simbolos mm* en todo include/asic_reg           93.009
    APLICABLE_SIN_CONFLICTO                      12.069
    CONFLICT                                          6
    NO_APLICABLE                                 80.934
    PROVEN_ABSENT                                     0

  sobre el denominador NATIVO  gca/gfx_8_0_d.h    2.633
    APLICABLE_SIN_CONFLICTO                       2.633  = 100,0 %
    CONFLICT                                           0
```

Las seis, con sus dos valores aplicables:

| símbolo | aplicable A | aplicable B |
|---|---|---|
| `mmBIF_RFE_MST_BX_CMDSTATUS` | `bif/bif_4_1_d.h` = 0x1448 | `bif/bif_5_0_d.h` = 0x1449 |
| `mmMC_CG_DATAPORT` | `gmc/gmc_8_1_d.h` = 0xa21 | `gmc/gmc_8_2_d.h` = 0xa32 |
| `mmUVD_PGFSM_CONFIG` | `uvd/uvd_4_2_d.h` = 0x38f8 | `uvd/uvd_5_0_d.h` = 0x38c0 |
| `mmUVD_PGFSM_READ_TILE1` | `uvd/uvd_4_2_d.h` = 0x38fa | `uvd/uvd_5_0_d.h` = 0x38c2 |
| `mmUVD_PGFSM_READ_TILE2` | `uvd/uvd_4_2_d.h` = 0x38fb | `uvd/uvd_5_0_d.h` = 0x38c3 |
| `mmUVD_POWER_STATUS` | `uvd/uvd_4_2_d.h` = 0x38fc | `uvd/uvd_5_0_d.h` = 0x38c4 |

El patrón es legible sin más análisis: `amdgpu_device.c` sigue con `bif_4_1`,
`amdgpu_uvd.c` con `uvd_4_2`, y `gfx_v8_0.c` / `vi.c` ya van con `bif_5_0` /
`uvd_5_0`. Son disagreement entre TU de una misma generación. Eso es un hecho sobre **el corpus del kernel**, y P0.2 existe exactamente para no resolverlo en
silencio.

## 4 · Lo que hace la regla actual, medida sobre el mismo universo

```text
  regla ACTUAL     (cualquier valor distinto en el corpus)     21.991 conflictos
  regla DEMOSTRADA (cualquier valor distinto entre aplicables)      6
  falsos positivos                                                 21.985
  falsos negativos                                                      0
  precision de la regla actual                                   0,0003
```

**Recall = 1,0.** La regla demostrada es estrictamente más estrecha y no pierde
ningún conflicto: los 6 reales son un subconjunto de los 21.991. Eso **descarta H2**: la regla actual no es «demasiado amplia» por prudencia,
es correcta como *criterio de sospecha* y falsa como *criterio de veredicto*.

## 5 · El delta medido, y una refutación que no esperaba

| | modelo | `reg_resolve.py` hoy |
|---|---|---|
| A `mmBCI_DEBUG_READ` | `APLICABLE_SIN_CONFLICTO` · chosen `0x24eb` | `conflict=true` · chosen `null` · value `null` |
| B `mmMC_CG_DATAPORT` | `CONFLICT` · `[0xa21,0xa32]` · chosen `null` | `conflict=true` · candidatos ambos · **chosen `gmc_8_1_d.h`** |

Yo escribí el estado esperado del caso B **por suposición** —«CHOSEN=null»— y
el test lo refutó al medirlo. Dos cosas se rompen a la vez en el caso B:

1. **A**: conflicto artificial sobre una definición aplicable única.
2. **B**: la arista de inclusión que 1602 añadió (`gmc_v8_0.c` incluye la
   cabecera seleccionada) **es una media verdad**. Prueban que *una* TU incluye
   ese header; no prueban que *ninguna otra* TU aplicable incluya uno con otro
   valor. `gfx_v8_0.c:41` incluye `gmc/gmc_8_2_d.h`, y esa TU también corre en
   esta placa. La regla necesita la forma «y ninguna otra TU aplicable trae un
   valor distinto», no la que tiene.

Esto es el mismo fallo de forma que el de 1584 y el de mi primer denominador:
**una condición necesaria (**esta** TU incluye) usada como si fuera suficiente.**

## 6 · T0601–T0605

`tools/rxre/tests/test_p0_2_conflict014.py`. El oráculo es un **modelo de
referencia construido desde la fuente del kernel**; generar lo esperado con la
función de selección sería comprobar que el código hace lo que el código hace.

| | prueba | resultado |
|---|---|---|
| T0601 | cross-target: `mmBCI_DEBUG_READ`, 3 valores globales, 1 aplicable | `CONFLICT=false` · elegido `gfx_8_0_d.h` |
| T0602 | mismo target: `mmMC_CG_DATAPORT`, 2 aplicables incompatibles | `CONFLICT=true` · `[0xa21,0xa32]` · `CHOSEN=null` |
| T0603 | único aplicable entre muchas globales; denominador nativo entero | sin conflicto artificial; CONFLICT es minoría |
| T0604 | el caso de P0.2 se conserva | sigue siendo `CONFLICT` |
| T0605 | neutralidad: unidad, identidad, procedencia | `dword_index_de_mm`, `* 4`, `CHIP_POLARIS12`, `unit_evidence` |

**Dos modos, porque un solo modo miente:**

```text
  sin --conformance   30 checks verdes, y exige que el delta sea EXACTAMENTE
                      el medido.  Si el mundo cambia sin repararse, falla.
  --conformance       exige el estado final.  Hoy: 4 FALLOS, que son
                      exactamente los 4 huecos de la reparacion:
                        A sin conflicto artificial
                        A se elige la definicion aplicable
                        A el valor expuesto es el del candidato aplicable
                        B CHOSEN=null  (la arista gmc_v8_0.c no basta)
```

## 7 · Mutation

`mutate_p0_2_conflict014.py`. Como el oráculo es el modelo, las mutaciones
atacan al propio test: eso demuestra que las aserciones no son vacías.

| mutante | clase | muerta por |
|---|---|---|
| `M1_aplicabilidad_ignorada` | target applicability | T0601 «una definición aplicable» |
| `M2_headers_equivalentes` | headers equivalentes | T0602 «dos valores aplicables» |
| `M3_lineage_filtrado_eliminado` | lineage filtering | T0601 |
| `M4_primer_candidato_global` | first global candidate | T0601 «el candidato es `gfx_8_0_d.h`» |
| `M5_conflicto_oculto` | ocultar conflict | T0602 |
| `M6_candidatos_borrados` | borrar candidates | T0602 |
| `M7_provenance_de_target_eliminada` | target provenance | «la identidad sale de la tabla» |
| `M8_no_aplicable_como_conflicto` | tricotomía | T0603 «minoría» |
| `M9_unidad_invertida` | la unidad se toca | T0605 |

**9/9 muertas, 0 supervivientes.**

## 8 · La costura que ya existe (no hace falta otro resolver)

```text
  core/target.py
    EXPECTED_BDF / EXPECTED_REVISION / EXPECTED_SUBSYSTEM      identidad fisica
    _map_pci_id_to_asic_gfx()   {"1002","699F"} -> ("Polaris12","gfx_8_0")
      REUTILIZABLE  pero DUPLICA la tabla del kernel y es MAS ESTRECHO:
        1 de los 8 device id de CHIP_POLARIS12  (6980 6981 6985 6986 6987
        6995 6997 699F)                              =  12 % de la fila
      y NO expone el token CHIP_POLARIS12,  que es justo lo que el routing
      necesita para elegir el universo de TU.
```

La reparación que propone la evidencia es coser, no añadir:

```text
  target.py      identidad fisica            (ya existe, 1601)
      + la fila de amdgpu_pci_table          (fuente, no diccionario a mano)
      -> CHIP_POLARIS12
      -> universo de TU que lo nombran
      -> headers aplicables
      -> conflicto entre los aplicables
```

Y un hueco ya registrado en 1601 sigue abierto: **ningún consumidor en
`cli.py` ni en `api/machine.py` llama a `get_current_target`.** Sin eso, el
pipeline de arriba no tiene entrada.

## 9 · Lo que NO se hace aquí

```text
  NO se toco reg_resolve.py.          prohibicion expresa de esta iteracion
  NO se borro la regla actual:        cubre los 6 casos reales,  solo que mas
                                      amplia de lo que el veredicto permite
  NO se generalizo a otras placas:    TODO el analisis es 1002:699f
  NO se ejecuto la cobertura de 2633: esa corrida, si, mide el estado
  POST-REPARACION,  y por la regla demostrada daria 2633/2633 ok en vez de
  los 153 que predice la regla actual.

  CONFRONTACION PARCIAL,  hecha de todas formas porque la cobertura de 013
  estaba corriendo en paralelo.  El modelo de referencia y el artefacto se
  comparan simbolo a simbolo sobre las primeras 505 lineas:

  ```text
    lineas comparadas                                  505
    desacuerdos entre el modelo y reg_resolve.py         0
  ```

  La tasa de `ok` NO es uniforme  —los simbolos que sobreviven se concentran
  al principio del orden alfabetico—,  asi que un reparto lineal sobre 450
  lineas habria dado ~257 `ok`.  Era una extrapolacion mia sin base.  El
  confrontation por simbolo,  no el reparto,  es el que vale.
```

## 10 · LIMITACIONES

- **«la TU nombra CHIP_POLARIS12» es un proxy** de «esta TU corre en esta
  placa». Se midió la sensibilidad con un criterio más fuerte y la población no
  se movió, pero un grafo de llamadas desde `asic_type == CHIP_POLARIS12` sería
  más fuerte y no se ha construido.
- **`asic_reg` es solo el diccionario de registros.** Las tablas de SOC, NBIF y
  `df_*` no entran en este análisis, y ahí el término «aplicable» puede
  depender de la compilación condicional, no del include.
- **`#define` con continuaciones de línea no se parsean.** La regex exige el
  valor al final de la línea, como la de `reg_resolve`.
- Corpus `linux-7.1.3` frente a kernel en ejecución 7.2.9.

## 11 · HISTORIAL

| hallazgo | qué dice | estado aquí |
|---|---|---|
| 1576 | dos defectos: `dword_index` y conflicto silencioso | `dword_index` **REVISED** en 1604/1607; conflicto **REVISED** aquí |
| 1584 | `dword_index` inválido en el 73,4 % | **REFUTED** (era la unidad invertida) |
| 1590 | `mmMC_CG_DATAPORT` con dos valores; propone declarar CONFLICT | **PROVEN**, y el caso sobrevive como conflicto real. Su §«alineación» (`0xa21 % 4 = 1`) es **REFUTED** por 1604: un índice dword no tiene por qué ser múltiplo de 4 |
| 1592 | P0.3 declara CONFLICT con `chosen=null` | **REVISED**: el universo estaba mal acotado y la arista no era suficiente |
| 1602 | la arista de inclusión `gmc_v8_0.c` | **REFUTADA como suficiente**: `gfx_v8_0.c` incluye `gmc_8_2_d.h` y también corre en Polaris12 |
| 1604/1607 | unidad = índice dword, `×4` | **PROVEN**, intacto |

## 12 · NOTA DE ALCANCE — dos directorios de hallazgos

`findings/1589.md … 1592.md` **no** están en `06-INGENIERIA-INVERSA/findings/`
sino en un `findings/` suelto en la raíz. Consecuencia medida:
`nextnum.py --check 1590` responde *LIBRE*, porque el ledger solo mira
`06-INGENIERIA-INVERSA/findings/`. Un número ocupado en una de las dos carpetas
puede volver a reservarse en la otra. No lo he reparado — es otro nodo — pero
afecta a la fiabilidad del contador que la directiva usa como medida de
progreso, y por eso se escribe aquí.
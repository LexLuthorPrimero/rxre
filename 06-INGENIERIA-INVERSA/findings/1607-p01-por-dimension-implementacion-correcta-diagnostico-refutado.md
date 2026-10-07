# 1607 — P0.1 reconciliado por dimensión: la implementación es correcta y el diagnóstico viejo queda REFUTADO

```text
CLASSIFICATION=RECONCILIACION_DE_CUATRO_DIMENSIONES+AMPLIACION_DE_WARNING
WORK_CLASS=RXRE-012-RECONCILIACION-P0.1-FINDING-1604
AUTOR=AGENTE_RXRE012 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7
QUESTION=¿La implementación actual de RXRE describe correctamente la unidad
          semántica y la advertencia asociada a dword_index, tras 1604?
MODIFICATIONS=tools/reg_resolve.py (warning: +1 frase acotada)
              tools/rxre/tests/test_p003.py (+2 checks de regresión)
              +2 scripts nuevos de reconciliación y mutación
WRITE_EXECUTION=NINGUNO sobre hardware · sin MMIO, sin firmware, sin VBIOS,
                sin cargar módulo, sin tocar Intel, sin tocar display
RUNTIME=NOT_RUN · solo lectura de fuente y de la salida de reg_resolve
PRECEDE_A=HALLAZGO_1604 (misma reconciliación, segunda pasada por dimensión)
```

## Estado final, una etiqueta por dimensión

```text
P0.1 = REVISED

  arithmetic_collision  = PROVEN
  semantic_unit          = PROVEN          (índice dword de registro)
  old_diagnosis          = REFUTED        ("la representación pierde LSBs")
  implementation         = CORRECTA       (sin cambios de lógica necesarios)
  warning                = CORRECTO, INCOMPLETO  (ampliado en esta iteración)
  repair                 = CORRECTA       (no revertida, no replanteada)
```

Las seis dimensiones van separadas porque una sola etiqueta las ocultaría. El
hallazgo 1592 usó una sola para las seis, y por eso su descripción de la
reparación ya no corresponde al código.

---

## Q1 · Unidad de entrada

**RESPUESTA: índice dword de registro.** Evidencia independiente de
`reg_resolve.py`, y del kernel:

```text
  amdgpu_reg_access.c:482   @reg: dword aligned register offset
  amdgpu_reg_access.c:501   writel(v, ((void __iomem *)adev->rmmio) + (reg * 4))
```

Un byte offset no necesita multiplicación para llegar a su dirección; un
índice dword sí. La conversión ocurre **una vez**, en el accessor.

## Q2 · Qué significa `val >> 2`

**`>>2` NO EXISTE en el código actual.** `grep '>> *2' tools/reg_resolve.py`
no devuelve nada. La pregunta tiene dos respuestas distintas según la versión:

| | código | `unit` | `dword_index` | `byte_offset` |
|---|---|---|---|---|
| **Histórico** (`2d2873c`) | `hex(val >> 2)` | `byte offset (contrato del kernel)` | `val >> 2` | `val` |
| **Actual** (`fb8da65`) | `hex(val * 4)` | `dword register index` | `val` | `val * 4` |

**Clasificación: opción C.** `>>2` es una transformación *correcta* (byte →
índice) aplicada a la representación *equivocada*. En el código histórico, `value`
se declaraba `byte_offset` y luego se dividía para obtener el índice. La
operación es invertible; el error es que el valor no era un byte offset.

**Hallazgo nuevo de esta iteración:** el mismo diccionario se contradecía a sí
mismo. `UNIT_DECLARATION.consequence` decía, literalmente:

```text
"los offsets mm* son indices dword; el byte offset es offset*4"
```

mientras el código 30 líneas más abajo hacía `val >> 2`. Una de las dos cosas
era falsa, y era el código: la cita textual era correcta y la aritmética no la
seguía. Eso ya lo había apuntado 1576; aquí queda con la cita exacta.

## Q3 · Naturaleza de la colisión

**Arithmetic collision = PROVEN. Semantic collision = PROVEN_ABSENT.**

```text
  aritmética:   f(0x1AC)=0x6B   f(0x1AD)=0x6B   iguales  ✓
  semántica índice: 0x1AC vs 0x1AD            distintos ✓
  semántica byte:   0x6B0 vs 0x6B4             distintos ✓
```

La diferencia importa y es la que el diagnóstico viejo no hizo. Y hay un
detalle que endurece el resultado:

```text
  0x6B * 4 = 0x1AC = mmSMC_IND_INDEX_11, NO mmSMC_IND_DATA_11
```

Dividir **no produce un índice ambiguo**. Produce el índice de **otro
registro**. Eso no es *identity loss*, es **identity substitution**: el sistema
no pierde la identidad de `DATA_11`, la reemplaza por la de `INDEX_11`, sin
aviso. Con dos registros contiguos es indistinguible de un acierto.

## Q4 · El warning actual

**Correcto en lo que dice, incompleto en lo que omite.** Verificado por
ejecución, no por lectura:

```text
  (a) declara la unidad          "dword register index"           ✓ presente
  (b) declara la transformación "byte offset is value * 4"        ✓ presente
  (c) cita el accessor           "in amdgpu_device_rreg"          ✓ presente
  (d) acota el alcance           "does not prove the hardware…"   ✓ presente
  (e) prohíbe dividir            ausente                            ✗
```

El warning viejo tampoco afirmaba pérdida de LSBs: `grep` sobre la versión
actual y sobre `2d2873c` no encuentra `pierde`, `LSB` ni `colision`. La
formulación «la representación pierde LSBs» estaba **en el hallazgo 1589**, no
en el código. El código decía otra cosa, también equivocada: «el propio valor
ES el byte offset».

## Q5 · Estado de la reparación

**CORRECTA. No necesita cambio de lógica, ni textual, ni reversión.**

```text
  [OK] índice expuesto == valor del #define      0x1ac / 0x1ad
  [OK] byte == índice × 4                        0x6b0 / 0x6b4
  [OK] no existe >>2 en el código
  [OK] clase renombrada a dword_index_de_mm
  [OK] warning nombra la conversión × 4
  [OK] warning no afirma que el valor sea el byte offset
```

**El único cambio necesario** fue una frase en el warning, para que deje de
callar sobre el error y lo prohíba explícitamente. Sin cambio de
productor→transformación→representación→consumidor. La alternativa de la
misión, y es la correcta: *test correcto + warning incompleto + implementación
correcta ⇒ corregir solo la descripción semántica y añadir regresión.*

---

## Cambio aplicado

```diff
  out["warning"] = ("value is the dword register index; the MMIO byte "
                    "offset is value * 4 in amdgpu_device_rreg. "
+                   "The value is NOT a byte offset: dividing it by 4 "
+                   "is not a valid conversion and would name a "
+                   "different register. "
                    "The header definition alone does not prove the "
                    "hardware effect or every PM4 encoding.")
```

Y dos checks en `test_p003.py`:

```text
  T0301 la advertencia prohibe dividir el valor por 4
         "NOT a byte offset" in warnings and "dividing it by 4" in warnings
  T0301 la advertencia nombra el accessor que hace la conversion
         "amdgpu_device_rreg" in warnings or "amdgpu_device_wreg" in warnings
```

## TEST

| Suite | Antes | Ahora |
|---|---|---|
| `test_p003.py` (P0.3) | 25 verde | **27 verde** |
| `test_p004.py` (P1) | verde | verde |
| `test_p005.py` (Conflict Tracking) | 37/37 | 37/37 |
| `test_target_identity009.py` (Conflict Tracking 009) | 5/5 | 5/5 |
| `test_vm8_register009.py` (Relation Engine, arista de inclusión) | 1/1 | 1/1 |
| `reg_resolve.py --selftest` | OK | OK |
| `relations`/`conflicts`/`store` importan | OK | OK |

## MUTATION

`mutate_p0_1_semantics012.py`, 10 mutaciones en las cinco clases exigidas,
baseline verde exigido antes. **10/10 muertas, 0 supervivientes.**

| Clase | Mutante | p003 | vm8 |
|---|---|---|---|
| UNIDAD | `U1_clase_vuelta_a_byte_offset` | 0 | **1** |
| UNIDAD | `U2_clase_renombrada` | **1** | 1 |
| TRANSFORMACIÓN | `T1_dividir_en_vez_de_multiplicar` | **1** | 1 |
| TRANSFORMACIÓN | `T2_dword_index_derivado` | **1** | 1 |
| TRANSFORMACIÓN | `T3_multiplica_por_8` | **1** | 1 |
| WARNING | `W1_warning_afirma_byte_offset` | **1** | 0 |
| WARNING | `W2_warning_sin_la_prohibicion` | **1** | 0 |
| WARNING | `W3_warning_sin_la_fuente` | **1** | 0 |
| IDENTIDAD | `I1_todos_los_valores_dos` | **1** | 1 |
| CONFLICT | `C1_conflict_suprimido` | **1** | 0 |

Nota sobre `U1`: la vuelta de `unit` a `"byte offset"` **no la detecta `test_p003`**
(rc=0); la detecta el oráculo independiente `test_vm8_register009` (rc=1). Eso
es exactamente para lo que existe un segundo oráculo: la suite principal
comprueba la aritmética, el oráculo exterior comprueba la etiqueta. Un solo
test no habría visto el cambio.

## Las dos categorías de conflicto, separadas

```text
  CATEGORÍA 1 — IDENTITY COLLISION (P0.1)
    dos SÍMBOLOS distintos cuyos valores derivados colisionan
    0x1AC vs 0x1AD → se resuelve por la UNIDAD
    CONFLICT/CANDIDATES NO aplica aquí

  CATEGORÍA 2 — SYMBOL DEFINITION CONFLICT (P0.2)
    un SÍMBOLO con dos VALORES en definiciones distintas
    mmMC_CG_DATAPORT: conflict=True, candidates=['0xa21','0xa32'],
    selection_rule='GFX8 GMC consumer includes the selected register header'
    chosen=include/asic_reg/gmc/gmc_8_1_d.h
```

Ambas siguen vivas y no comparten mecanismo. Medido en ejecución: la
categoría 2 se resuelve hoy por la arista de inclusión, con evidencia.

## Regla de casos sin consumidor, preservada

```text
  desalineado  +  sin consumer  ≠  unidad PROVEN
```

`mmCB_BLEND_RED` (0xa105) y `mmMC_ARB_AGE_CNTL` (0x9bf) tienen 0 usos en `.c`
en este árbol (medido en 1604). Siguen `NOT_DETERMINED`. **El resultado de los
registros con consumidor no se generaliza a los ~12.000 `mm*` del corpus.**

## LIMITACIONES

- `rxre_cobertura_gfx8.py:88` (`elegido.get("value", elegido.get("byte_offset"))`)
  sigue sin re-inspeccionar. Su `or` de fallback sugiere que esperaba byte
  offset. `NOT_DETERMINED`.
- No verificado si alguna tabla del corpus usa una API con byte offset real
  (`RREG8`, `amdgpu_mm_rreg8`). Ahí `>>2` sí sería correcta, porque la entrada
  sería un byte offset. Es otra API y no pasa por `reg_resolve`.
- P0.3 **nunca fue commiteado.** `git log --all -S'COLLISION:' -- tools/reg_resolve.py`
  no devuelve nada: la versión que 1592 describe existió solo en el árbol de
  trabajo. El único estado versionado de `reg_resolve.py` antes de este
  commit era `2d2873c`, con `>>2` y `unit="byte offset"`. Por eso 1605 y 1606
  quedaron reservados y se liberaron sin fichero: no hay nada que escribir.
- Corpus `linux-7.1.3` frente a kernel en ejecución 7.2.9.

## HISTORIAL PRESERVADO

| Hallazgo | Qué dice | Estado aquí |
|---|---|---|
| 1589 | «la representación pierde LSBs» produce la colisión | diagnóstico **REFUTED**; la colisión aritmética sigue **PROVEN** |
| 1590 | `mmMC_CG_DATAPORT`, dos valores | sigue **PROVEN**, resuelto por arista de inclusión |
| 1591 | P0.3 pide tests para `0x1AC != 0x1AD` | **PROVEN** como propiedad; la justificación era falsa |
| 1592 | describe la reparación de P0.3 | **REVISED**: el código descrito nunca se commiteó |
| 1602 | invierte la unidad, `byte = valor * 4` | **PROVEN**, confirmado aquí por el accessor |
| 1604 | `P0.1 = REVISED` | confirmado; este hallazgo lo abre por dimensión |

**La propiedad `0x1AC != 0x1AD` se conserva íntegra.** Lo que se revisa es la
explicación de por qué `>>2` la destruía.

## Las siete respuestas

1. **Unidad de 0x1AC/0x1AD:** índice dword de registro. Evidencia: accessor
   multiplica por 4; alineación; población.
2. **Transformación correcta:** `byte_offset = valor × 4`. No la inversa.
3. **`>>2` hoy:** no existe. Históricamente: byte→índice sobre una entrada que
   no era byte offset.
4. **Por qué aparece la colisión aritmética:** `>>2` es inyectiva solo sobre
   múltiplos de 4; `0x1AD` no lo es, y su imagen es la de `0x1AC`.
5. **Implementación actual:** correcta. Sin cambios de lógica.
6. **Warning:** correcto e incompleto. Ampliado con la prohibición de dividir.
7. **Qué se conserva de P0.1:** la colisión aritmética y la identidad de los
   dos registros. Se descarta: la causa semántica.

## Estado de la iteración

La misión era exclusivamente reconciliar P0.1 y está cerrada. No se
implementó A1/A2/A3/A4, no se creó ninguna capacidad, no se tocó hardware.

**GLOBAL WORK SCAN — la siguiente tarea sale de aquí:** el único punto abierto
que esta reconciliación dejó es `rxre_cobertura_gfx8.py:88`, cuyo fallback
`value → byte_offset` fue escrito bajo la unidad equivocada. Es un consumidor
de la representación que P0.1 trataba, y es el mismo patrón de la arista de
inclusión para el bloque SMC: un consumidor que hay que verificar contra la
fuente antes de confiar en él.
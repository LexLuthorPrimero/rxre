# 1604 — P0.1 reconciliado: la unidad es ÍNDICE DWORD, y `>>2` era una división sobre la unidad equivocada

```text
CLASSIFICATION=RECONCILIACION_SEMANTICA+REFUTACION_DE_UN_DEFECTO
WORK_CLASS=RXRE-011-RECONCILIACION-P0.1
AUTOR=AGENTE_RXRE011 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7
PREGUNTA=¿qué unidad representan 0x1AC y 0x1AD, y es correcto aplicar >>2?
MODIFICATIONS=NINGUNO sobre reg_resolve.py, tests ni schema.  Añadidos tres
              scripts de reconciliación de solo lectura
WRITE_EXECUTION=NINGUNO · solo scripts de reconciliación y este hallazgo
RUNTIME=NOT_RUN · sin MMIO, sin ejecución de herramientas de análisis, solo lectura
              de fuente y de la salida de reg_resolve
DISPOSITIVO_TOCADO=NINGUNO · no MMIO, no Intel, no display, no driver bind
ARTEFACTOS=tools/rxre/tests/p0_1_reconcile.py
           tools/rxre/tests/p0_1_discriminants.py
           tools/rxre/tests/p0_1_caso_c.py
```

## Respuesta a las nueve preguntas, con su base

| # | Pregunta | Respuesta | Base medida |
|---|---|---|---|
| 1 | ¿Qué unidad son 0x1AC / 0x1AD? | **Índice dword de registro** | alineación + consumidor real, abajo |
| 2 | ¿Qué unidad espera `reg_resolve.py`? | La que hoy **produce**: `dword_index=valor`, `byte_offset=valor*4` | ejecutado, `p0_1_reconcile.py` §5 |
| 3 | ¿Qué transformación hace hoy? | Multiplica por 4 para obtener el byte offset; ya no divide | `reg_resolve.py:299-309` |
| 4 | ¿`>>2` es semánticamente correcta? | **No**, aplicada a este valor | §«D3» de `p0_1_discriminants.py` |
| 5 | ¿`>>2` está aplicada a la unidad equivocada? | **Sí.** La unidad correcta es índice dword | alineación, abajo |
| 6 | ¿La advertencia de P0.3 describe el defecto? | **No.** Describe una colisión que era un artefacto de la unidad | §4 y §8 |
| 7 | ¿`CONFLICT/CANDIDATES` sigue siendo necesario? | **No para este caso.** Sí para `mmMC_CG_DATAPORT` | §7 |
| 8 | ¿Qué parte de P0 queda PROVEN? | La colisión aritmética y que son registros distintos | §8 |
| 9 | ¿Qué pasa a NOT_DETERMINED/REVISED? | La unidad canónica y el defecto | §8 |

**Clasificación: `P0.1 = REVISED`.** No `CONFIRMED` ni `REFUTED`, porque
la colisión aritmética es cierta y el defecto que la justificaba no lo era.

---

## 1 · LAS CONSTANTES

```
smu_7_1_1_d.h:179   mmSMC_IND_INDEX_11   0x01AC   %4 = 0
smu_7_1_1_d.h:180   mmSMC_IND_DATA_11    0x01AD   %4 = 1
smu_7_1_1_d.h:90    mmSMC_IND_ACCESS_CNTL 0x0092   %4 = 2
```
Idénticas en `smu_7_1_2_d.h:91-93` y `smu_7_1_3_d.h:94-96`. Sin discrepancia.

## 2 · EL DISCRIMINANTE: ALINEACIÓN

Un registro de 32 bits no puede vivir en una dirección de byte no alineada a
4: el hardware no tiene un registro de 32 bits que empiece en el byte
`0x1AD`, porque eso cruzaría dos dwords.

| Símbolo | valor | %4 | leído como índice ×4 | alineado |
|---|---|---|---|---|
| `mmSMC_IND_INDEX_11` | 0x01AC | 0 | 0x06B0 | sí |
| `mmSMC_IND_DATA_11` | 0x01AD | **1** | 0x06B4 | sí |
| `mmSMC_IND_ACCESS_CNTL` | 0x0092 | **2** | 0x0248 | sí |

Leídos como byte offsets, **dos de los tres** estarían desalineados. Leídos
como índice dword, los tres son válidos. **CASO A.**

Refuerzo con la misma propiedad en el mismo campo a través de generaciones:
`mmSMC_IND_ACCESS_CNTL` vale `0x8A` (smu_6_0), `0x90` (7_0_0, 7_0_1, 7_1_0) y
`0x92` (7_1_1, 7_1_2, 7_1_3). Dos de esos tres valores son no alineados a 4.

## 3 · LA CADENA COMPLETA, eslabón por eslabón

```
header        smu_7_1_1_d.h:179-180     #define mmSMC_IND_INDEX_11 0x1AC
              ↓
productor     smu7_smumgr.c:43          cgs_write_register(hwmgr->device,
                                               mmSMC_IND_INDEX_11, smc_addr)
              ↓                            PASA LA MACRO, no un offset
transform.    amdgpu_cgs.c:50-55         static void amdgpu_cgs_write_register(
                                               ..., unsigned offset, uint32_t value)
                                               { WREG32(offset, value); }
              ↓                            SIN TRANSFORMACIÓN: reenvía
macro         amdgpu.h:1295              #define WREG32(reg, v) \
                                               amdgpu_device_wreg(adev, (reg), (v), 0)
              ↓
consumer      amdgpu_reg_access.c:494    if ((reg * 4) < adev->rmmio_size)
                       :501               writel(v, adev->rmmio + (reg * 4))
              ↓                            TRANSFORMACIÓN DOCUMENTADA: ×4
declaración   amdgpu_reg_access.c:482    @reg: dword aligned register offset
```

La transformación ocurre **una sola vez**, en el accessor, y es una
**multiplicación**. El eslabón `?` que la misión pedía identificar es
`×4`, y su fuente es `amdgpu_reg_access.c:501`, no una convención de nombres.

Nota sobre el parámetro `offset` de `cgs_write_register`: el nombre sugiere
byte offset, pero `cgs_common.h:95` lo documenta como «register offset» y la
implementación lo reenvía a `WREG32`. **El nombre del parámetro es la probable
causa del error de P0.1**, y por eso la misión dice rightly que no hay que
inferir la unidad por el nombre de una variable.

## 4 · LA COLISIÓN RE-DERIVADA

```
0x1AC >> 2 = 0x6B     0x1AD >> 2 = 0x6B     iguales  → cierto
0x1AC * 4  = 0x6B0    0x1AD * 4  = 0x6B4    distintos → identidad preservada
```

Y lo que `>>2` produce **no es la dirección de ninguno de los dos**:

```
0x6B = 107
byte real de mmSMC_IND_INDEX_11 = 0x6B0 = 1712
byte real de mmSMC_IND_DATA_11  = 0x6B4 = 1716
```

`0x6B * 4 = 0x1AC`, que es el índice de `INDEX_11`. Dividir no pierde
información al azar: **devuelve el índice de otro registro**. Eso es peor que
una pérdida de identidad, porque es una identidad equivocada sin aviso.

## 5 · UN DISCRIMINANTE QUE NO DISCRIMINA (negativo, registrado)

El límite `rmmio_size` parece discriminante: `reg*4 < rmmio_size` acota a
`reg < 0x10000` si reg es índice, o a `reg < 0x40000` si es byte offset.
**No discrimina.** Medido: tras excluir los `mm*` que no son offsets
(Sentinel `>= 0xFFFF0000`, sufijos `_DEFAULT`, `_MASK`, `__SHIFT` — 26757
definiciones), el mayor offset real del corpus es `0x403D10D`, que está **por
encima** de ambos límites hypothesized.

Consecuencia: cualquier conclusión basada solo en `rmmio_size` sería falsa, y
este script no cuenta como oráculo. Se conserva porque un test que no
discrimina es información sobre el terreno, no sobre el objeto.

Dos defectos míos durante esta medición, ambos corregidos y registrados:
la primera versión del script contaba `0x10000FFFF` (`mmSDMA1_CONTEXT_REG_TYPE0_DEFAULT`,
un **valor de reset**, no un offset) como registro, y `0xFFFDF79F`
(``_DEFAULT` de SDMA, igualmente un valor de reset) como el máximo. El denominador
equivocado habría hecho el discriminante parecer decisivo. La clase de error es
la misma que el hallazgo 1584: **elegir el denominador por comodidad**.

## 6 · CASO C: PROBADO Y REFUTADO

CASO C dice que la unidad depende del contexto. El contraejemplo candidato es
NBIF: `mmRCC_DEV1_EPF2_STRAP0 = 0x403d100` con `_BASE_IDX 3`, desalineado, y
en un `*_offset.h` en vez de un `*_d.h`.

**Población medida** (fracción no alineada a 4):

```
gca/*_d.h         n=11595   desalineados 8495   73.3%
gmc/*_d.h         n=4302    desalineados 3238   75.3%
nbif/*_offset.h   n=73      desalineados 52     71.2%
smu/*_d.h         n=930     desalineados 685    73.7%
```

El 73% desalineado es **imposible** como byte offsets de registros de 32
bits. La misma proporción en las cuatro familias, incluido NBIF, indica una
sola convención.

**NBIF no usa otro accessor.** `soc15_common.h:36`:

```c
#define SOC15_REG_OFFSET(ip, inst, reg)  (adev->reg_offset[ip##_HWIP][inst][reg##_BASE_IDX] + reg)
```

Es una **suma de segmento**: `reg_offset[BASE_IDX] + reg`. El resultado sigue a
`WREG32` (`soc15_common.h:40-43, 50-56`) y de ahí a `reg * 4`. `_BASE_IDX`
cambia el **valor**, no la **unidad**. Un offset NBIF sigue siendo un índice
dword con una base sumada.

**Límite honesto:** `mmCB_BLEND_RED` (0xa105) y `mmMC_ARB_AGE_CNTL` (0x9bf) son
desalineados y tienen **0 usos en `.c`** en este árbol. Por §16 (READ SCOPE
GATE) quedan `NOT_DETERMINED`: sin consumidor no hay evidencia de uso que
confirme ni contradiga la unidad. `mmSMC_IND_INDEX_11` sí tiene 7 usos, y todos
llegan a `reg * 4`.

## 7 · CONFLICT/CANDIDATES PARA ESTE CASO

**No es necesario, y aplicarlo aquí sería un error de categoría.**
`0x1AC` y `0x1AD` son **símbolos distintos** que no compiten por un mismo
offset: son dos registros legítimos y adyacentes. El mecanismo
`CONFLICT`/`CANDIDATES` existe para el caso contrario —dos definiciones con
valores distintos **para el mismo símbolo**—, que es `mmMC_CG_DATAPORT`
(0xa21 en gmc_8_1_d.h frente a 0xa32 en gmc_8_2_d.h). Ahí sí aplica y ahí se
validó.

Confundir «dos símbolos con valores parecidos» con «dos valores para un
símbolo» es lo que produjo el sobredimensionamiento de P0.3.

## 8 · QUÉ QUEDA PROVEN, QUÉ PASA A REVISED

| Afirmación | Estado | Base |
|---|---|---|
| 0x1AC y 0x1AD son registros **distintos** | **PROVEN** | dos `#define` con valores distintos, 3 cabeceras cada uno |
| `0x1AC>>2 == 0x1AD>>2 == 0x6B` | **PROVEN** (aritmética) | verificado; pero es división sobre unidad equivocada |
| byte_offset de INDEX_11 = 0x6B0 | **PROVEN_DERIVED** | índice × 4, contrato del accessor |
| byte_offset de DATA_11 = 0x6B4 | **PROVEN_DERIVED** | ídem |
| el índice dword es la unidad **nativa** | **PROVEN_DERIVED** | alineación + consumidor real + población |
| byte_offset es la unidad canónica | **REFUTED** | 0x1AD%4=1 y 0x92%4=2 lo impiden |
| `>>2` es una colisión real de identidad | **REFUTED** | 0x6B no es la dirección de ninguno de los dos |
| la advertencia de P0.3 describe el defecto | **REFUTED** | describía una colisión que era artefacto de unidad |
| `rxre_cobertura_gfx8.py:88` pierde identidad | **NOT_DETERMINED** | no re-inspeccionado en esta iteración |
| `CONFLICT` para 0x1AC/0x1AD | **PROVEN_ABSENT_NEED** | símbolos distintos, no compiten |
| unidad de los `mm*` sin consumidor | **NOT_DETERMINED** | falta scope de consumidor (§16) |

## 9 · CONSECUENCIA PARA P0.3 Y PARA EL CÓDIGO ACTUAL

P0.3 (`test_p003.py` T0301) afirmaba `byte_offset(0xA1E0) == 0xA1E0` y exigía
una colisión de `dword_index` entre 0xA1E0 y 0xA1E1. Con la unidad correcta,
`0xA1E0 * 4 = 0x28780` y `0xA1E1 * 4 = 0x28784`: **no hay colisión**. El
código actual de `reg_resolve.py` y de `test_p003.py` ya está en la unidad
correcta por el trabajo de RXRE-009 (hallazgo 1602), pero **el hallazgo 1592
que documenta P0.3 sigue describiendo la reparación antigua** y queda
`REVISED` con este hallazgo.

Nada que reparar aquí: `reg_resolve.py` no se tocó en esta iteración, tal como
pide la misión. Lo que se registra es la **semántica**, que era lo que faltaba.

## 10 · Lo que sigue abierto, y no se cerrada aquí

- `mmCB_BLEND_RED`, `mmMC_ARB_AGE_CNTL` y los ~12.000 registros desalineados sin
  consumidor en este árbol: `NOT_DETERMINED` por §16. **No** se afirma que la
  unidad sea índice para todos ellos; se afirma para los que tienen consumidor.
- `rxre_cobertura_gfx8.py:88` (`elegido.get("value", elegido.get("byte_offset"))`):
  ese `or` de fallback sugiere que esperaba byte offset. No re-inspeccionado.
- Si existe alguna API de acceso con byte offset real (`RREG8`,
  `amdgpu_mm_rreg8`): es otra API y no pasa por `reg_resolve`. `>>2` sí sería
  correcta ahí. No verificado si alguna tabla del corpus la usa.

## Cierre de la iteración

La pregunta de la misión tiene respuesta defendible:

> **0x1AC y 0x1AD son índices dword de registro**, por tres motivos
> concordantes: la alineación que un byte offset no podría cumplir, el
> consumidor real (`amdgpu_device_wreg` → `reg * 4`), y la población del
> corpus (73% desalineados de forma uniforme).
>
> **Aplicar `>>2` es incorrecto**, porque la entrada es un índice, no un byte
> offset. El resultado `0x6B` no nombra ningún registro.
>
> **`P0.1 = REVISED`.**

No se modificó `reg_resolve.py`, ni los tests, ni el schema.
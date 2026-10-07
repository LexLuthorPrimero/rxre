# 1602 — RXRE-009: `rxre register` acertaba el índice y se equivocaba de unidad; el oráculo que lo «detectó» dividía por 4

```text
CLASSIFICATION=BAD_ORACLE_REFUTADO+CONTRACT_BUG_REPARADO
WORK_CLASS=RXRE-009-DOGFOODING · INVESTIGACION-RX550
AUTOR=AGENTE_RXRE009 (esta sesión)
FECHA=2026-10-07
TARGET=0000:01:00.0 · 1002:699f · rev c7
PREGUNTA=¿qué índice representa mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR para VMID8
          en el camino GFX8, y qué UNIDAD tiene ese número?
MODIFICATIONS=tools/reg_resolve.py; tools/rxre/tests/test_p003.py;
              tools/rxre/tests/test_vm8_register009.py;
              tools/rxre/tests/mutate_reg_resolve009.py; este hallazgo
WRITE_EXECUTION=NINGUNO · solo ficheros de herramienta y de test
DISPOSITIVO_TOCADO=NINGUNO · no MMIO, no Intel, no display, no driver bind
RUNTIME=solo lectura de fuente y de la CLI; corpus RESEARCH/working/linux-7.1.3
```

## Resultado primero: el registro es 0x50e, y findings/1588 y 1600 están equivocados

| Fuente primaria | Texto | Índice |
|---|---|---|
| `include/asic_reg/gmc/gmc_8_1_d.h:607` | `#define mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0x50e` | **0x50e** |
| `include/asic_reg/gmc/gmc_8_1_d.h:644` | `#define mmVM_CONTEXT0_PAGE_TABLE_START_ADDR 0x557` | 0x557 (otro registro) |
| `amdgpu/gmc_v8_0.c:35` | `#include "gmc/gmc_8_1_d.h"` | el consumidor GFX8 |
| `amdgpu/gmc_v8_0.c:676` | `reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8` | VMID 8 → 0x50e |
| `amdgpu/gmc_v8_0.c:915` | `WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8, ...)` | segundo consumidor, mismo valor |

`06-INGENIERIA-INVERSA/findings/1588:20,64` afirma «0x557 + (vmid-8)» y `:64` una tabla con `0x557 → byte 0x155C`. `1600:105,116` reproduce ese mismo `0x557` y lo codifica en `04-IMPLEMENTACION/rx550-driver/rx550_gpuvm.h:23,36,142` (`RX550_VM_CONTEXT8_PAGE_TABLE_BASE_ADDR 0x557u`). `0x557` es `VM_CONTEXT0_PAGE_TABLE_START_ADDR`: el hash `base+vmid` sin el corte cae, por construcción, en el registro START del bloque 0..7, como ya comprobaba `tests/test_ctxpt.c:81-84`. El error está en la **representación** publicada y propagada, no en el código de referencia. El índice correcto para el driver's `rx550_vm_context_ptb_reg()` es `0x50e`.

## La unidad: el corpus GFX8 declara un índice dword, no un byte offset

`amdgpu_device_rreg` (`amdgpu_reg_access.c:371-378`) acotaba con `reg * 4` y leía en `rmmio + (reg * 4)`. Un valor `0x1AD` de `#define` apunta a `0x6B4`, no a `0x1AD`: el número del header es **índice dword**, y el byte offset es `valor * 4`. `reg_resolve` afirmaba lo contrario (`unit="byte offset"`, `byte_offset=valor`, `dword_index=valor>>2`), y `1576:1-60` construyó sobre ello una tabla de «truncamientos que direccionan 4 bytes antes», incluido el caso `mmSMC_IND_DATA_11 → mmSMC_IND_INDEX_11`. Ese razonamiento era internamente consistente pero **invertía la operación**: la aritmética correcta es multiplicar. Los casos `0x1AD/0x1AC` y `0x8a/0x88` de `1576` no son colisiones del driver; son la prueba de que la división era falsa. `reg_resolve` ya cargaba la cita correcta y la contradicción con su propio cálculo, igual que `1576` se lo señaló.

Consecuencia sobre el estado: `findings/1589` y `1590`, tal como están escritos, **quedan refutados** en su término de colisión. El conflicto entre linajes (`mmMC_CG_DATAPORT`: `gmc_8_1_d.h` 0xa21 frente a `gmc_8_2_d.h` 0xa32) sí es real y sigue declarado; lo que cambia es su resolución: antes `chosen=null` sin regla, ahora se elige por arista de inclusión demostrada y se registra el consumidor, la línea y las definiciones excluidas.

## Discrepancia clasificada: C (hablan de cosas distintas), con una mitad de B

RXRE entregó el **valor correcto** `0x50e` en las cinco definiciones y con la cita textual de `gmc_8_1_d.h:607`. Fallas en dos ejes, y no son el mismo:

- **BAD_ORACLE / contrato de la prueba (B, la fuente de prueba estaba mal):** `test_p003.py` exigía `byte_offset(0xA1E0)==0xA1E0` y una colisión `dword_index` que no existe bajo la unidad real. Su expectativa codificaba la división por 4.
- **CONTRACT_BUG de la herramienta (A):** etiqueta de unidad invertida, y `verdict=DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO` con `chosen=null` para un registro que el consumidor GFX8 incluye directamente. Un `chosen=null` aquí induce a concluir que el offset no aplica a esta placa, cuando el registro del flush es precisamente el que la placa usa.

## Reparación, con el mínimo que cubre el mecanismo

- `classify_symbol`: clase `dword_index_de_mm`; `dword_index = valor`; `byte_offset = valor * 4`; advertencia que nombra la conversión y aclara que el `#define` no prueba el efecto hardware ni toda codificación PM4.
- `resolve_reg`: para `gfx_8_0` añade a la lista de generación el header GMC que el consumidor `amdgpu/gmc_v8_0.c` incluye, deducido con regex del propio `#include`, no de una lista escrita a mano. Con eso el registro VMID8 resuelve `DEFINIDO_EN_GENERACION_OBJETIVO`, `chosen=gmc_8_1_d.h`.
- Conflicto entre linajes: si el elegido es un header GMC prestado, `selection_rule` + `selection_evidence` (fichero, línea, texto del include, definición) + `excluded`; si no hay arista, `chosen=null` y `value=null`. No se elige por orden alfabético.
- `test_p003.py`: reescrito contra la unidad real. T0301 exige índice igual al `#define`, byte offset `= índice*4`, y que la advertencia **no** afirme que el valor sea el byte offset. T0302, con `chosen` no nulo, exige regla, evidencia que nombre el header elegido y `value` coherente con `chosen`; sin regla, exige ausencia de `value`.

## Validación

- `test_vm8_register009.py`, oráculo independiente (no usa la salida de RXRE para el valor esperado): lee `gmc_8_1_d.h`, `gmc_v8_0.c` y `amdgpu_reg_access.c`, comprueba `0x50e`, `0x557`, el `#include`, la expresión de `vmid - 8` y `reg * 4`; luego exige del envelope `verdict` de generación objetivo, `chosen=gmc_8_1_d.h`, `dword_index=0x50e`, `byte_offset=0x1438`. **1/1**.
- Antes de reparar, ese mismo test falló (`DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO`); discrimina.
- `tools/reg_resolve.py --selftest`: OK tras actualizar sus dos vectores de unidad.
- `test_p003.py`: 25/25. `test_p004.py`: verde. `test_target_identity009.py`: 5/5. `mutate_target_identity009.py`: 6/6 muertos.
- `mutate_reg_resolve009.py`: 5/5 muertos, 0 supervivientes — dividir por 4, afirmar byte offset, sustituir el header prestado, suprimir el conflicto, ignorar la arista de inclusión. Cada mutante corre en copia temporal de `tools/`; baseline verde exigido antes.
- **Medido y registrado:** el sitio `if "selection_evidence" not in out` no es banco con este corpus; con el grafo de includes real todo header en `in_target` está incluido, así que la rama no puede dispararse y una mutación ahí sobrevive por construcción. No se cuenta como defecto ni como éxito. Se sustituyó por la supresión del conflicto, que sí es alcanzable.
- Reuso de la API tras reparar: `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` → `0x54f`, byte `0x153c`; `mmVM_INVALIDATE_REQUEST` → `0x51e`, byte `0x1478`. Ambos con `chosen=gmc_8_1_d.h`, antes `chosen=null`.

## Límites y lo que queda abierto

- `mmSMC_IND_INDEX_11` y `mmSMC_IND_DATA_11` siguen **`DEFINIDO_EN_OTRA_GENERACION_NO_EN_LA_OBJETIVO`** con `chosen=null`: viven en `smu_7_1_*_d.h` (hallazgo `1574 §3`), y el consumidor es `smu7_smumgr.c`, no `gmc_v8_0.c`. El módulo `rx550_smc.c` los usa como byte offsets `0x6B0/0x6B4` — que **coinciden** con índice×4 — pero el mecanismo que acabo de añadir no cubre el bloque SMC. `ROUTING_GAP`: la arista de inclusión debería derivarse del consumidor del símbolo, no de un bloque fijo. Es la siguiente acción, no un defecto silencioso: el envelope declara el veredicto y `chosen=null`.
- PTE/PDE, `WAIT_REG_MEM` (que según `gfx_v8_0.c:6199-6205` escribe **7** dwords de payload, incluido el intervalo `0x20`, mientras `rx550_gpuvm.c` emite 5) y la conversión de puntero a `uint32_t` en `rx550_gpuvm.c:80` siguen **sin verificar**. No se afirma corrección del módulo.
- `0x50e` es el índice del registro; el byte offset `0x1438` sale de la conversión declarada, no de una lectura MMIO.
- Límite transversal: corpus `linux-7.1.3` frente a kernel en ejecución 7.2.9.

## Estado y siguiente acción

`VM_CONTEXT8_PTB_INDEX = 0x50e`: `PROVEN_DERIVED` por header incluido por el consumidor y por dos usos concordantes; el uso en `rx550_gpuvm.h` es `REFUTED`. `REG_UNIT_DWORD`: `PROVEN` por `amdgpu_reg_access.c`. `findings/1589`/`1590`: término de colisión `REFUTED`, conflicto entre linajes `CORROBORATED`. Siguiente acción única: extender la arista de inclusión al bloque SMC leyendo `smu7_smumgr.c`, con test que discriminate `mmSMC_IND_DATA_11` sin escribir en el dispositivo.
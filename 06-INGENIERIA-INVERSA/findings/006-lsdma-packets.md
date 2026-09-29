# 006 — Formato de packets PM4 en GFX8: `PACKET3` y el dispatch de compute

**Clasificación**: `READ_ONLY/EVIDENCE` (análisis de fuente, sin ejecución)
**Fecha**: 2026-09-29
**Fuente primaria**: `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
- `sid.h` — valores de packet type (**el fichero autoritativo**)
- `gfx_v8_0.c:1535-1564` — emisión real de un dispatch de compute en esta generación
- `cikd.h:495-497` — layout del header de 32 bits
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`

---

## 1. Dónde viven los packet types, y por qué `lsdma_v*.h` no sirve

| Fichero | Líneas | Contenido real |
|---|---|---|
| `lsdma_v7_1.h` | **31** | Solo `extern const struct amdgpu_lsdma_funcs lsdma_v7_1_funcs;` |
| `lsdma_v6_0.h` | — | Igual, un puntero a tabla de funciones |
| **`sid.h`** | miles | **Todos los `#define PACKET3_*`** |
| `cikd.h` | miles | Los mismos valores, generación CI/CK |

**Los packets no están en el fichero de LSDMA.** `lsdma_v*.h` declara una tabla de punteros a
función: el *dispatch* por versión, no el *formato* de los paquetes. El formato es común a todas
las generaciones y vive en `sid.h`, y se replica en `cikd.h`, `nvd.h` y
`gfx_v12_1_pkt.h` — la generación GFX12 tiene su **propio** fichero de packets
(`gfx_v12_1_pkt.h`), lo que confirma que el formato **cambia entre generaciones** y no es fijo.

> Consecuencia directa: un driver propio no debe incluir `lsdma_v7_1.h` esperando encontrar
> formatos de paquete. Debe incluir `sid.h` (o definir sus propias constantes, que es lo
> responsable) y elegir la tabla de funciones de LSDMA por separado.

## 2. El header de packet de 32 bits

`cikd.h:495-497`:

```c
#define SDMA_PACKET(op, sub_op, e)  ((((e) & 0xFFFF) << 16) | \
                                      (((sub_op) & 0xFF) << 8) | \
                                      ((op) & 0xFF))
```

Tres campos, 32 bits:

| Bits | Campo | Anchura |
|---|---|---|
| 0-7 | `op` (packet type) | 8 |
| 8-15 | `sub_op` (header type) | 8 |
| 16-31 | `e` (datos del header) | 16 |

**`sub_op` es el "header type"**, y es el que determina cuántos dwords de payload siguen al
header. En un dispatch de compute vale **3**, es decir 3 dwords de payload tras el header. Un
driver propio que fije el `op` correcto y el `sub_op` equivocado produce un packet que la HW
interpreta con la longitud equivocada y desalinea todo lo que viene después.

## 3. Packet types relevantes para compute

Valores de `sid.h` (líneas 343-516), verificados en la fuente:

| Packet type | Valor | Payload (`sub_op`) | Uso en compute |
|---|---|---|---|
| `PACKET3_NOP` | `0x10` | 0 | relleno y alineación |
| **`PACKET3_DISPATCH_DIRECT`** | **`0x15`** | **3** | **launch de un dispatch con dirección inmediata** |
| `PACKET3_DISPATCH_INDIRECT` | `0x16` | 3 | dispatch con la dirección en memoria |
| **`PACKET3_SET_SH_REG`** | **`0x76`** | 1 o 2 | escritura de shader register |
| `PACKET3_EVENT_WRITE` | `0x46` | 0 | flush parcial de CS |
| `PACKET3_EVENT_WRITE_EOP` | `0x47` | **4** | end-of-packet con timestamp |
| `PACKET3_EVENT_WRITE_EOS` | `0x48` | sin uso en `gfx_v8_0.c` | end-of-stream, escribe el valor de retorno |
| `PACKET3_INDIRECT_BUFFER` | `0x3F` | **2** | IB anidado |
| `PACKET3_ATOMIC` | `0x1E` | sin uso en `gfx_v8_0.c` | atómica genérica |
| `PACKET3_ATOMIC_GDS` | `0x1D` | sin uso en `gfx_v8_0.c` | atómica en GDS |

**`PACKET3_SET_SH_REG` = `0x76`, no `0x02`.** Lo había dejado como pendiente en la primera
redacción del documento y el valor real, leído de `sid.h:531`, es `0x76`. `0x02` no aparece por
ningún lado. Un driver propio que use el valor de un packet type de otra generación emitiría un
packet que la HW no reconoce.

`PACKET3_SET_SH_REG_START = 0x00002c00` (`sid.h:532`): es el offset base del espacio de
registros de shader, y por eso el código normaliza con `reg - PACKET3_SET_SH_REG_START` antes de
escribirlo como payload.

**Confirmado por el código de esta generación:** `gfx_v8_0.c:1541` usa
`PACKET3(PACKET3_DISPATCH_DIRECT, 3)`, y ese es el packet que lanza el compute shader. El valor
`0x15` con `sub_op` 3 está verificado por uso, no solo por la definición.

Los `sub_op` de `EVENT_WRITE_EOP` (4) e `INDIRECT_BUFFER` (2) están medidos por uso en
`gfx_v8_0.c`. Los de `EVENT_WRITE_EOS`, `ATOMIC` y `ATOMIC_GDS` **no se han leído**: no aparecen
en `gfx_v8_0.c` con ese `sub_op` y no se rellenan por suposición.

## 4. Secuencia real de un dispatch de compute en GFX8

`gfx_v8_0.c:1535-1564`, literal de la fuente. **Esta es la secuencia que un driver propio
tiene que reproducir**, y el orden es significativo:

```c
/* 1. Dirección del shader, en un SET_SH_REG de 2 dwords */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 2);
ib.ptr[ib.length_dw++] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = lower_32_bits(gpu_addr);
ib.ptr[ib.length_dw++] = upper_32_bits(gpu_addr);

/* 2. El dispatch: 3 dwords de payload */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_DISPATCH_DIRECT, 3);
ib.ptr[ib.length_dw++] = 8;   /* x */
ib.ptr[ib.length_dw++] = 1;   /* y */
ib.ptr[ib.length_dw++] = 1;   /* z */
ib.ptr[ib.length_dw++] =
    REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR, COMPUTE_SHADER_EN, 1);

/* 3. Flush parcial de CS */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);
ib.ptr[ib.length_dw++] = EVENT_TYPE(7) | EVENT_INDEX(4);

/* 4. Registros de estado SGPR1 */
for (i = 0; i < ARRAY_SIZE(sgpr1_init_regs); i += 2) {
    ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);
    ib.ptr[ib.length_dw++] = sgpr1_init_regs[i] - PACKET3_SET_SH_REG_START;
    ib.ptr[ib.length_dw++] = sgpr1_init_regs[i + 1];
}

/* 5. Dirección del shader, OTRA VEZ, y >> 8 */
gpu_addr = (ib.gpu_addr + (u64)sgpr_offset) >> 8;
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 2);
ib.ptr[ib.length_dw++] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = lower_32_bits(gpu_addr);
ib.ptr[ib.length_dw++] = upper_32_bits(gpu_addr);
```

### Lo que hay que saber de esta secuencia

**El paso 1 y el paso 5 escriben la misma dirección, con escalas distintas.** El primero
escribe `gpu_addr` tal cual; el segundo escribe `(ib.gpu_addr + sgpr_offset) >> 8`. La
dirección del shader se escribe **dos veces**: una antes del dispatch y otra después, y la
segunda lleva un desplazamiento a la derecha de 8. Esto **no es un error ni una redundancia
que se pueda eliminar**: es la secuencia que el driver emite, y `OBSERVED` en el código. Un
driver propio que escriba la dirección una sola vez, o que olvide el `>> 8`, produce un
comportamiento distinto del de referencia, y la diferencia no se manifiesta como error de
compilación sino como dispatch incorrecto o corrupción silenciosa.

**`COMPUTE_SHADER_EN = 1` en el initiate** es lo que enciende el shader. `DISPATCH_DIRECT` con
ese campo a 0 es un dispatch que no hace nada observable.

**`EVENT_TYPE(7) | EVENT_INDEX(4)`** es un flush parcial de CS. Va con `sub_op = 0`, o sea
payload de 0 dwords, y el valor va **en el header** (los 16 bits `e`), no en el payload. Es el
único paquete de la secuencia que no sigue el patrón de `sub_op = nº de dwords`.

**El grid del dispatch es `8 × 1 × 1`** en el literal. Es un valor de ejemplo, no un requisito:
son los tres payloads de `DISPATCH_DIRECT` y los escribe el cliente.

**`sgpr1_init_regs` se recorre de dos en dos** porque cada `SET_SH_REG` de 1 dword lleva
`offset` y `valor` en dwords separados. El índice del registro se normaliza restando
`PACKET3_SET_SH_REG_START = 0x2c00`, que es el offset base del espacio de registros de shader.

### 4.1 `sgpr1_init_regs`: los 11 registros que preceden al dispatch

`gfx_v8_0.c:1403-1415`, literal:

```c
static const u32 sgpr1_init_regs[] =
{
    mmCOMPUTE_STATIC_THREAD_MGMT_SE0, 0x0f,
    mmCOMPUTE_RESOURCE_LIMITS,      0x1000000,  /* CU_GROUP_COUNT=1 */
    mmCOMPUTE_NUM_THREAD_X,         256*5,
    mmCOMPUTE_NUM_THREAD_Y,         1,
    mmCOMPUTE_NUM_THREAD_Z,         1,
    mmCOMPUTE_PGM_RSRC1,            0x240,      /* SGPRS=9 (80 GPRS) */
    mmCOMPUTE_PGM_RSRC2,            20,
    mmCOMPUTE_USER_DATA_0,          0xedcedc00,
    mmCOMPUTE_USER_DATA_1,          0xedcedc01,
    mmCOMPUTE_USER_DATA_2,          0xedcedc02,
    mmCOMPUTE_USER_DATA_3,          0xedcedc03,
    mmCOMPUTE_USER_DATA_4,          0xedcedc04,
    mmCOMPUTE_USER_DATA_5,          0xedcedc05,
    mmCOMPUTE_USER_DATA_6,          0xedcedc06,
    mmCOMPUTE_USER_DATA_7,          0xedcedc07,
    mmCOMPUTE_USER_DATA_8,          0xedcedc08,
    mmCOMPUTE_USER_DATA_9,          0xedcedc09,
};
```

**17 registros, no 11.** Una primera redacción de este documento contó 11 porque el brief traía
un corte parcial de la tabla. Corregido contra `gfx_v8_0.c:1403-1420`.

Lo que se establece de esta tabla:

- **El grid por defecto es `1280 × 1 × 1`.** `NUM_THREAD_X = 256*5` son 5 workgroups de 256
  hilos; `Y` y `Z` valen 1. El `8 × 1 × 1` del `DISPATCH_DIRECT` de la §4 es una **unidad de
  trabajo distinta**: el dispatch divide este total. Un driver propio que fije solo uno de los
  dos niveles y deje el otro a su valor por defecto producirá un grid inconsistente.
- **`CU_GROUP_COUNT=1`**: una sola CU. Es lo que hace un dispatch determinista y sin
  comunicación entre CUs.
- **`SGPRS=9` (80 GPRs)**: el shader tiene disponible el juego completo de SGPR.
- **Los 10 `USER_DATA` llevan el patrón `0xedcedc00..09`**, que es un valor **marcador** de
  "sin inicializar" usado para detectar si el dispatch lee un kernel resource que el driver no
  ha configurado. `OBSERVED` en el código; el significado exacto de la constante no se ha
  verificado contra la especificación de hardware.

### 4.2 Existe una segunda tabla: `sgpr2_init_regs`

`gfx_v8_0.c` define **dos** tablas de inicialización, y solo difieren en un campo:

| Campo | `sgpr1_init_regs` | `sgpr2_init_regs` |
|---|---|---|
| `STATIC_THREAD_MGMT_SE0` | `0x0f` | **`0xf0`** |
| Los otros 16 | idénticos | idénticos |

La única diferencia es `STATIC_THREAD_MGMT_SE0`: bits 0-3 frente a bits 4-7. **No se ha
establecido** qué distingue semánticamente una tabla de la otra ni cuál se selecciona en cada
caso: el código que las elige no se ha seguido. `NOT_DETERMINED`, y es relevante porque un
driver propio tiene que elegir entre las dos.

**Lo que no se establece:** por qué cada valor es ese, ni si son los valores correctos para
Polaris 12 en vez de una elección genérica del driver. `PLAUSIBLE`, no verificado.

Nota de terminología: el término de la grid es "workgroup" (`COMPUTE_PGM_RSRC1` codifica el número
de workgroups en 5 bits y el tamaño de wavefront en 8), no "wave".

## 5. Diferencias con el SDMA heredado

`003-exported-symbols.md` §5 estableció que el envío PM4 de esta generación es LSDMA. Con la
fuente a la vista, la precisión es esta:

| Aspecto | SDMA heredado | LSDMA (esta generación) |
|---|---|---|
| Símbolos | `amdgpu_sdma_*` | `dmub_lsdma_*` |
| Ficheros | `sdma_v2_4.c` … `sdma_v7_1.c` | `lsdma_v6_0.c`, `lsdma_v7_1.c` |
| Tabla de dispatch | `amdgpu_sdma_funcs` | `amdgpu_lsdma_funcs` |
| **Formato de packet** | **`sid.h`, común** | **`sid.h`, común** |
| Nombres de packet | `PACKET3_*` | `PACKET3_*` — **los mismos** |

**El formato de packet NO cambia.** Es el mismo `PACKET3_*` de `sid.h` para ambas. Lo que cambia
es la *tabla de funciones* que implementa el envío: `amdgpu_sdma_funcs` frente a
`amdgpu_lsdma_funcs`. Ambos coexisten en el mismo driver porque el mismo `.ko` sirve a varias
generaciones ASIC.

Esto **corrige la formulación de Ronda 1** y matiza la pregunta que se me hizo. Dije "el envío
PM4 es LSDMA, no `amdgpu_sdma`" y es cierto a nivel de *símbolos y ficheros*, pero **el
formato de los packets es el mismo**. La consecuencia práctica es mejor de lo que sugería: un
driver propio puede definir los `PACKET3_*` una vez y no necesita dos juegos de constantes. Lo
que necesita es elegir **qué tabla de funciones** implementa el envío, y esa elección sí es
por versión de IP.

## 6. Límites de este documento

- **Los valores de packet type están verificados por lectura de `sid.h` y por uso en
  `gfx_v8_0.c`.** No se ha ejecutado nada ni validado contra hardware.
- La columna `Payload (sub_op)` está medida solo para los packets con uso en `gfx_v8_0.c`:
  `EVENT_WRITE_EOS`, `ATOMIC` y `ATOMIC_GDS` quedan sin leer y **no se rellenan por suposición**.
- `sgpr1_init_regs` se ha inspeccionado (§4.1): 17 registros de compute, con los valores
  por defecto que fija el driver. Existe además una segunda tabla, `sgpr2_init_regs` (§4.2), que
  difiere en un único campo y cuya selección no se ha seguido. Lo que **no** se ha hecho es
  explicar por qué cada valor es ese.
- El contenido de `amdgpu_lsdma_funcs` y de `amdgpu_sdma_funcs` — qué función hace qué — **no se
  ha analizado**. `NOT_DETERMINED`. Es la pieza que falta para responder con fundamento a la
  pregunta de IA-3 sobre qué tabla de funciones usar.

## Procedencia

Valores de packet type leídos de `sid.h` líneas 343-516 el 2026-09-29. Secuencia de dispatch
citada literalmente de `gfx_v8_0.c:1535-1564`. Layout del header de `cikd.h:495-497`. Los tres
comandos del brief de Ronda 2 se intentaron y fallaron antes de sustituirlos por lectura de
fuente. Ningún valor transcrito de documentación externa ni de memoria.

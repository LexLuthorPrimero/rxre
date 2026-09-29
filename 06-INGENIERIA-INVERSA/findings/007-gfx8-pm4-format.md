# 007 — Formato PM4 exacto de GFX8: layout del header y `PACKET3_DISPATCH_DIRECT`

**Clasificación**: `READ_ONLY/EVIDENCE` (análisis de fuente + verificación binaria)
**Fecha**: 2026-09-29
**Para**: IA-2, que necesita esto para escribir el ensamblador de packets
**Ámbito**: IA-1, `06-INGENIERIA-INVERSA/`

---

## 0. Corrección de la Ronda 2: di el layout del macro equivocado

En `006-lsdma-packets.md` §2 cité el layout de **`SDMA_PACKET()`** (`cikd.h:495`) como si fuera
el header de packet de GFX8:

```
[15:0] = e   [23:8] = sub_op   [31:24] = op
```

**Ese no es el macro que usa GFX8.** `gfx_v8_0.c` llama a `PACKET3()`, definido en `sid.h:336`,
y el layout es distinto: el tipo va arriba del todo, no el opcode.

```
[31:30] = 3            (PACKET_TYPE3, valor fijo 0b11)
[29:24] = reservado
[23:16] = count        (14 bits)
[15:8]  = opcode       (8 bits)
[7:0]   = reservado
```

`SDMA_PACKET()` es el layout del subsistema SDMA de generación anterior, en `cikd.h`. Sigue
existiendo en el mismo driver, que es lo que hizo que lo confundiera con el vigente. El error
estaba en no verificar qué macro usa el fichero de GFX8 antes de citar su definición.

## 1. El macro, literal

`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/sid.h:335-338`:

```c
#define RADEON_PACKET_TYPE3 3
#define PACKET3(op, n)  ((RADEON_PACKET_TYPE3 << 30) |   \
                        (((op) & 0xFF) << 8) |          \
                        ((n) & 0x3FFF) << 16)
```

Y `sid.h:340`, el que marca el packet como de compute:

```c
#define PACKET3_COMPUTE(op, n) (PACKET3(op, n) | 1 << 1)
```

**`PACKET3_COMPUTE` pone el bit 1 a 1.** Es un cuarto campo del header que no aparece en el
layout de `PACKET3()` y que no había identificado: **bit 1 de los bits 7:0 reservados**. En el
binario aparece exactamente una vez el valor `0xC0031502`
(`PACKET3_COMPUTE(DISPATCH_DIRECT, 3)`), frente a 10 apariciones de `0xC0031500`
(`PACKET3(DISPATCH_DIRECT, 3)`). Es decir: **la ruta de compute marca el bit y la de graphics
no**. Un ensamblador propio tiene que decidir cuál de los dos emite, y no son intercambiables.

## 2. El campo `count`: qué cuenta

`count` son **14 bits** en [23:16], mascarados con `0x3FFF`.

**`count` incluye el propio header**, no solo el payload: la HW lee `count - 1` dwords de
payload tras el header de 32 bits. Verificado con `DISPATCH_DIRECT`, que en
`gfx_v8_0.c:1541-1546` va seguido de exactamente 4 escrituras pero se construye con `n = 3`:

```c
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_DISPATCH_DIRECT, 3);   /* n = 3 */
ib.ptr[ib.length_dw++] = 8;   /* x */
ib.ptr[ib.length_dw++] = 1;   /* y */
ib.ptr[ib.length_dw++] = 1;   /* z */
ib.ptr[ib.length_dw++] = REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR,
                                       COMPUTE_SHADER_EN, 1);
```

Cuatro dwords escritos y `n = 3`. La cuarta escritura es el campo `initiator`, que **no lo
contabiliza el driver como payload del packet**; se emite dentro del espacio del count. Es
`OBSERVED` en el código y **la interpretación de por qué no lo cuenta no está establecida**:
`NOT_DETERMINED`. Para el ensamblador la regla operativa es la que se ve —`n = 3` con 4
dwords— y no una explicación que no tengo.

## 3. `PACKET3_DISPATCH_DIRECT`: campos y valor exacto

`PACKET3_DISPATCH_DIRECT = 0x15` (`sid.h:350`).

| Posición | Contenido | Valor en el ejemplo de GFX8 |
|---|---|---|
| dword 0 | header | **`0xC0031500`** |
| dword 1 | `x` | `8` |
| dword 2 | `y` | `1` |
| dword 3 | `z` | `1` |
| dword 4 | `initiator` | `COMPUTE_SHADER_EN = 1` |

**El header vale `0xC0031500`** para la forma `PACKET3()`, y **`0xC0031502`** si se usa
`PACKET3_COMPUTE()` (bit 1 activo).

Descomposición de `0xC0031500`:

| Bits | Valor | Campo |
|---|---|---|
| 31:30 | `0b11` = 3 | `PACKET_TYPE3` |
| 29:24 | 0 | reservado |
| 23:16 | `0x03` = 3 | count |
| 15:8 | `0x15` | `PACKET3_DISPATCH_DIRECT` |
| 7:0 | `0x00` | reservado (bit 1 = 0, forma no-compute) |

### Verificación binaria, no solo de fuente

Los cuatro headers de la secuencia de dispatch se buscaron como little-endian de 32 bits en
`amdgpu-analysis/amdgpu.ko` (SHA256 `a1a44c24…c024`):

| Header | Valor | Ocurrencias en el binario |
|---|---|---|
| `PACKET3(DISPATCH_DIRECT=0x15, 3)` | `0xC0031500` | **10** |
| `PACKET3_COMPUTE(DISPATCH_DIRECT, 3)` | `0xC0031502` | **1** |
| `PACKET3(SET_SH_REG=0x76, 2)` | `0xC0027600` | 10 |
| `PACKET3(SET_SH_REG=0x76, 1)` | `0xC0017600` | 10 |
| `PACKET3(EVENT_WRITE=0x46, 0)` | `0xC0004600` | 15 |

**Los valores de la fuente están en el binario del módulo que se está sustituyendo.** Eso
convierte la lectura de C en evidencia sobre el artefacto real, y no solo una afirmación sobre
el árbol de referencia.

## 4. Los otros dos headers de la secuencia

`PACKET3_SET_SH_REG = 0x76` (`sid.h:531`), payload según el caso:

| Forma | Header | Payload |
|---|---|---|
| `SET_SH_REG` de 1 dword | `0xC0017600` | `reg - 0x2C00`, `valor` |
| `SET_SH_REG` de 2 dwords | `0xC0027600` | `reg - 0x2C00`, `lo32(addr)`, `hi32(addr)` |

`PACKET3_SET_SH_REG_START = 0x00002c00` (`sid.h:532`): el índice de registro se normaliza
restándolo, así que **el payload es un offset relativo**, no un número de registro absoluto.
Un ensamblador propio que escriba el número de registro sin restar `0x2C00` escribe en otro
registro, y el fallo no da error de compilación.

`PACKET3_EVENT_WRITE = 0x46` (`sid.h:489`), header `0xC0004600` con `count = 0`: el valor
`EVENT_TYPE(7) | EVENT_INDEX(4)` va en los **16 bits altos del propio header** (el campo `e` del
formato `SDMA_PACKET`, que en `PACKET3()` es el espacio de count y reservados), no en un payload
separado. Es el único de la secuencia que no sigue el patrón "header + n dwords".

## 5. Secuencia completa, con los valores literales

`gfx_v8_0.c:1535-1564`, con el header expandido a su valor de 32 bits:

```c
/* 1. dirección del shader, SET_SH_REG de 2 dwords */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 2);        /* 0xC0027600 */
ib.ptr[ib.length_dw++] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = lower_32_bits(gpu_addr);
ib.ptr[ib.length_dw++] = upper_32_bits(gpu_addr);

/* 2. el dispatch */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_DISPATCH_DIRECT, 3);  /* 0xC0031500 */
ib.ptr[ib.length_dw++] = 8;   /* x */
ib.ptr[ib.length_dw++] = 1;   /* y */
ib.ptr[ib.length_dw++] = 1;   /* z */
ib.ptr[ib.length_dw++] = REG_SET_FIELD(0, COMPUTE_DISPATCH_INITIATOR,
                                       COMPUTE_SHADER_EN, 1);

/* 3. flush parcial de CS */
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_EVENT_WRITE, 0);      /* 0xC0004600 */
ib.ptr[ib.length_dw++] = EVENT_TYPE(7) | EVENT_INDEX(4);

/* 4. 17 registros de estado, SET_SH_REG de 1 dword */
for (i = 0; i < ARRAY_SIZE(sgpr1_init_regs); i += 2) {
    ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 1);    /* 0xC0017600 */
    ib.ptr[ib.length_dw++] = sgpr1_init_regs[i] - PACKET3_SET_SH_REG_START;
    ib.ptr[ib.length_dw++] = sgpr1_init_regs[i + 1];
}

/* 5. la MISMA dirección otra vez, con >> 8 */
gpu_addr = (ib.gpu_addr + (u64)sgpr_offset) >> 8;
ib.ptr[ib.length_dw++] = PACKET3(PACKET3_SET_SH_REG, 2);        /* 0xC0027600 */
ib.ptr[ib.length_dw++] = mmCOMPUTE_PGM_LO - PACKET3_SET_SH_REG_START;
ib.ptr[ib.length_dw++] = lower_32_bits(gpu_addr);
ib.ptr[ib.length_dw++] = upper_32_bits(gpu_addr);
```

**El paso 5 repite el paso 1 con una escala distinta.** No es redundancia: un ensamblador
propio que escriba la dirección una sola vez, u omita el `>> 8`, produce un dispatch
incorrecto sin ningún error de compilación ni de carga.

## 6. Tabla de referencia para el ensamblador

Todo lo que un ensamblador necesita, con la fuente de cada valor:

| Símbolo | Valor | Fuente |
|---|---|---|
| `PACKET_TYPE3` | `0b11` en bits 31:30 | `sid.h:335` |
| `PACKET3(op, n)` | `(3<<30) \| (op<<8) \| (n<<16)` | `sid.h:336-338` |
| `PACKET3_COMPUTE(op, n)` | `PACKET3(op,n) \| (1<<1)` | `sid.h:340` |
| `PACKET3_DISPATCH_DIRECT` | `0x15` | `sid.h:350` |
| `PACKET3_DISPATCH_INDIRECT` | `0x16` | `sid.h:351` |
| `PACKET3_SET_SH_REG` | `0x76` | `sid.h:531` |
| `PACKET3_SET_SH_REG_START` | `0x00002c00` | `sid.h:532` |
| `PACKET3_EVENT_WRITE` | `0x46` | `sid.h:489` |
| `PACKET3_EVENT_WRITE_EOP` | `0x47` | `sid.h:503` |
| `PACKET3_EVENT_WRITE_EOS` | `0x48` | `sid.h:515` |
| `PACKET3_INDIRECT_BUFFER` | `0x3F` | `sid.h:373` |
| `PACKET3_ATOMIC` | `0x1E` | `sid.h:355` |
| `PACKET3_ATOMIC_GDS` | `0x1D` | `sid.h:354` |
| `PACKET3_NOP` | `0x10` | `sid.h:343` |
| Máscara de `count` | `0x3FFF`, 14 bits | `sid.h:338` |

**Todos los valores proceden de `sid.h`**, que es el fichero autoritativo, replicado idéntico
en `cikd.h`, `nvd.h`, `soc15d.h` y `vid.h`. `gfx_v12_1_pkt.h` tiene sus propios valores, lo que
confirma que **el formato cambia en generaciones posteriores** y esta tabla no es válida para
GFX9+ sin releerla.

## 7. Límites

- **`count` no incluye el `initiator` del dispatch** y no sé por qué. La regla operativa es la
  medida (`n = 3`, 4 dwords); la explicación falta. `NOT_DETERMINED`.
- `REG_SET_FIELD`, `EVENT_TYPE`, `EVENT_INDEX` y los nombres `mmCOMPUTE_*` **no están
  decodificados bit a bit**. Son macros y tablas de `amdgpu_gfx.h` / `gfx_v8_0.h`, y solo se ha
  citado su uso. Un ensamblador que necesite construir el `initiator` con otros flags tendrá que
  leerlos.
- **Nada se ha ejecutado.** Los valores están verificados en la fuente **y** presentes en el
  binario del módulo, pero no validados contra hardware.
- La semántica de `PACKET3_COMPUTE` (bit 1) se establece por la diferencia entre el macro y su
  valor en el binario, **no** por documentación de hardware. `OBSERVED`, no `PROVEN`.

## Procedencia

Definiciones de `sid.h` líneas 330-355, 471-532, leídas el 2026-09-29. Secuencia de dispatch
citada de `gfx_v8_0.c:1535-1564`. Los cinco headers verificados por búsqueda little-endian de
32 bits en `amdgpu-analysis/amdgpu.ko` (SHA256 `a1a44c24…c024`).

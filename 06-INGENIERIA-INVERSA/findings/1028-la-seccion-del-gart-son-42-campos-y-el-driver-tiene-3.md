# 1028 · La secuencia que programa el GART en esta tarjeta son 42 campos, y el driver propio tiene máscara para 3

`CLASSIFICATION=MEASUREMENT` · `TRACK=STATIC + HOST_OBSERVATION`
`CORPUS=RESEARCH/kernelbuild/linux-7.1.3` · `HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0`
`WORK_CLASS=READ_ONLY/EVIDENCE` · `WRITE_EXECUTION=NONE` · `MODIFICATIONS=0`
`RUNTIME=OBSERVED_READ_ONLY` · `GPU INTACTA`

---

## La pregunta

Entre «el driver mapea BAR5» y «el driver tiene tablas de páginas» hay una
función concreta que hay que reproducir. En el driver de referencia para esta
ASIC es `gmc_v8_0_gart_enable()`, `gmc_v8_0.c:829-947`. ¿Qué escribe, en qué
orden, y qué de eso puede expresar hoy el driver propio?

## Qué escribe

**21 escrituras a registro, que expanden a 48 operaciones: 7 son escrituras de
registro completo y 41 son `REG_SET_FIELD` sobre 42 campos distintos.**

| registro | campos declarados | los pone la referencia | una escritura ciega pondría a cero |
|---|---|---|---|
| `mmMC_VM_MX_L1_TLB_CNTL` | — | 5 | — |
| `mmVM_L2_CNTL` | 15 | 7 | 8 |
| `mmVM_L2_CNTL2` | — | 2 | — |
| `mmVM_L2_CNTL3` | — | 3 | — |
| `mmVM_L2_CNTL4` | — | 12 | — |
| `mmVM_CONTEXT0_CNTL` | **22** | **3** | **19** |
| `mmVM_CONTEXT1_CNTL` | **22** | **10** | **12** |

Las **21 son `RREG32 → REG_SET_FIELD → WREG32`**. No hay ni una sola escritura
ciega en toda la función.

## Lo que el driver propio puede y no puede hacer

`rx550_mmio_access.h` expone:

```c
int rx550_mmio_read32 (const struct rx550_mmio_map *, struct rx550_reg, uint32_t *);
int rx550_mmio_write32(const struct rx550_mmio_map *, struct rx550_reg, uint32_t);
```

**No hay primitiva de lectura-modificación-escritura por campo.** Y
`rx550_mmio_access.h:306` ya lo dice: *"corpus programa con RREG32 →
REG_SET_FIELD → WREG32, que conserva lo demás"*. La regla está escrita; la
primitiva no existe.

La consecuencia no es teórica. `mmVM_CONTEXT0_CNTL` tiene 22 campos y la
referencia pone 3: una escritura directa pondría a cero los otros 19, y el
resultado —un contexto 0 con la caché L2, los faults y el TLB en valores
distintos de los previstos— **no falla al escribir**. Falla cuando una página
se mapea mal, mucho después, y sin señal.

## Los 42 campos, y el `__SHIFT` es derivable del `MASK`

Medido sobre `gmc_v8_0_gart_enable()` y sobre los `*_sh_mask.h` de
`include/asic_reg/`:

```
campos distintos que escribe la secuencia : 42
  con MASK y __SHIFT, ambos presentes     : 42
  faltantes                                : ninguno
  MASK y __SHIFT incoherentes              : ninguno
```

Los 8 de más de un bit:

| campo | mask | shift | ancho |
|---|---|---|---|
| `SYSTEM_ACCESS_MODE` | 0x18 | 3 | 2 |
| `PAGE_TABLE_DEPTH` (contexto 0) | 0x6 | 1 | 2 |
| `PAGE_TABLE_DEPTH` (contexto 1) | 0x6 | 1 | 2 |
| `PAGE_TABLE_BLOCK_SIZE` | 0xf000000 | 24 | 4 |
| `BANK_SELECT` | 0x3f | 0 | 6 |
| `L2_CACHE_BIGK_FRAGMENT_SIZE` | 0xf8000 | 15 | 5 |
| `CONTEXT1_IDENTITY_ACCESS_MODE` | 0x180000 | 19 | 2 |
| `EFFECTIVE_L2_QUEUE_SIZE` | 0x38000 | 15 | 3 |

**El `__SHIFT` que declaran los headers es exactamente el número de ceros
finales del `MASK`, en los 42 casos.** Se comprobó con el invariante

```
(mask >> shift) == 2^ancho - 1
```

y no hay ni una discrepancia. Es decir: **`_SHIFT` es redundante.** Una tabla
própria que sólo lleve máscaras puede derivar la posición, y la derivación es
comprobable contra el corpus entero sin copiar 42 constantes a mano — que es
justo el error que un `REG_SET_FIELD` copiado a dedo hace el día que el header
se regenera.

## Cuánto de esto tiene el driver propio

3 de 42, y sólo dos define:

```c
target_vm.h:80   #define TVM_DEPTH_FIELD_MASK      0x6u        /* 2 bits, bits 1..2   */
target_vm.h:81   #define TVM_BLOCKSIZE_FIELD_MASK  0xF000000u  /* 4 bits, 24..27     */
```

Esos dos cubren `PAGE_TABLE_DEPTH` de ambos contextos y
`PAGE_TABLE_BLOCK_SIZE`. **Los otros 39 no tienen equivalente**, y entre ellos
está todo el bloque de control de caché (`mmVM_L2_CNTL` 7, `mmVM_L2_CNTL3` 3,
`mmVM_L2_CNTL4` 12, `mmMC_VM_MX_L1_TLB_CNTL` 5) que precede a la programación
del contexto.

## La asimetría que `target_vm.h` ya tenía abierta, y que esto estrecha

`target_vm.h:257-259` declara:

```c
{ "valor de PAGE_TABLE_DEPTH",        TVM_NOT_DETERMINED, ... },
{ "valor de PAGE_TABLE_BLOCK_SIZE",   TVM_NOT_DETERMINED, ... },
```

Con el corpus a la vista la pregunta no es única, son dos:

| | contexto 0 | contexto 1 |
|---|---|---|
| `PAGE_TABLE_DEPTH` | **1**, `gmc_v8_0.c:895` | **1**, `gmc_v8_0.c:925` |
| `PAGE_TABLE_BLOCK_SIZE` | **no lo escribe** | `block_size − 9`, `gmc_v8_0.c:933` |

`PAGE_TABLE_DEPTH` está determinado en los dos contextos, y el valor de
`PAGE_TABLE_DEPTH=0` para el contexto 0 es lo que hace que la tabla del GART sea
una sola tabla y no dos niveles.

`PAGE_TABLE_BLOCK_SIZE` sólo está determinado para el contexto 1, y su valor
sale del log de esta máquina (`block size is 10-bit`) menos 9, o sea 1.

**Para el contexto 0 el campo no lo escribe nadie.** Y no lo escribe nadie por
la razón de que la secuencia es RMW: lo que hubiera queda. El corpus no
documenta el valor de reset de `mmVM_CONTEXT0_CNTL`, y `grep` sobre
`*_sh_mask.h` no lo encuentra porque los `sh_mask` no llevan resets.

Queda un `NOT_DETERMINED` real y bien delimitado, con tres salidas posibles:

1. el valor de reset es 0 y da igual;
2. a profundidad 0 el campo no se usa y da igual;
3. el valor de reset es otro y la referencia funciona por casualidad de que
   en esta máquina salió 0.

El discriminante es una lectura de `mmVM_CONTEXT0_CNTL` antes y después de un
reset, y eso sólo lo da el driver propio. **No se ha ejecutado.**

## El orden importa, y hay un orden obligatorio

```
  L843  mmMC_VM_MX_L1_TLB_CNTL      TLB L1
  L849  mmVM_L2_CNTL                caché L2
  L859  mmVM_L2_CNTL2               INVALIDATE_ALL_L1_TLBS, INVALIDATE_L2_CACHE
  L866  mmVM_L2_CNTL3               BANK_SELECT, BIGK_FRAGMENT_SIZE
  L872  mmVM_L2_CNTL4               12 campos de tapping
  L886  mmVM_CONTEXT0_PAGE_TABLE_START_ADDR   gart_start >> 12
  L887  mmVM_CONTEXT0_PAGE_TABLE_END_ADDR     gart_end   >> 12
  L888  mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR    table_addr >> 12
  L889  mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR
  L891  mmVM_CONTEXT0_CNTL2
  L893  mmVM_CONTEXT0_CNTL           ENABLE_CONTEXT=1, DEPTH=0, RANGE_PF=1
  L899  mmVM_L2_CONTEXT1_IDENTITY_APERTURE_LOW_ADDR  = 0
  L900  mmVM_L2_CONTEXT1_IDENTITY_APERTURE_HIGH_ADDR = 0
  L901  mmVM_L2_CONTEXT_IDENTITY_PHYSICAL_OFFSET     = 0
  L907  mmVM_CONTEXT1_PAGE_TABLE_START_ADDR = 0
  L908  mmVM_CONTEXT1_PAGE_TABLE_END_ADDR   = max_pfn - 1
  L910  bucle i = 1..15:  BASE_ADDR(i) = table_addr >> 12   (corte en 8)
  L921  mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR
  L923  mmVM_CONTEXT1_CNTL2 = 4
  L925  mmVM_CONTEXT1_CNTL           10 campos, DEPTH=1, BLOCK_SIZE=block_size-9
  L938  gmc_v8_0_flush_gpu_tlb(0, 0, 0)
  L941  drm_info("PCIE GART of %uM enabled (table at 0x%016llX)")
```

La invalidación va **antes** de programar la base, y hay un `flush_gpu_tlb`
**después** de los dos contextos. Un orden distinto no es «menos óptimo»: es un
contexto que puede estar activo mientras se le cambia la tabla.

## Corroboración de 1025 desde un segundo sitio

El corte en 8 del registro de tabla por VMID ya estaba corroborado por
`gmc_v8_0_emit_flush_gpu_tlb()`. Aparece **otra vez**, en `L910` de esta función,
que es un *sitio distinto* del mismo fichero y otra ruta de código:

```c
for (i = 1; i < AMDGPU_NUM_VMID; i++) {
    if (i < 8) WREG32(mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + i,     table_addr >> 12);
    else      WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + i - 8, table_addr >> 12);
}
```

Y `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + 1 = 0x54f + 1 = 0x550`, byte offset
`0x1540`, que es exactamente el `RX550_REG_CTX1_PT_BASE` que el driver tiene
hardcodeado. El valor sale bien por dos caminos independientes, que es lo que
`CORROBORATED` significa y lo que `OBSERVED` no significa.

## Los dos errores de sonda, que están aquí porque son el mismo patrón

**La primera versión buscó `_SHIFT` cuando la convención es `__SHIFT`** —
`amdgpu.h:1351` es `reg##__##field##__SHIFT`. Resultado: «41 campos sin
`_SHIFT`», que era falso. Peor: una de esas 41 la reportaba como *faltante* cuando
`MASK` estaba en `mmhub/mmhub_1_0_sh_mask.h` y no en `gmc_8_1_sh_mask.h`, así que
buscar en un solo header habría producido un segundo falso negativo.

**La segunda usó `(v>>s)&v != v` como invariante de coherencia.** No es el
invariante. El correcto es `(mask >> shift) == 2^ancho − 1`. Con el primero, 40
de 42 campos salían «incoherentes» y los 42 salían coherentes con el segundo.

Los dos son la misma cosa: **suponer una convención en vez de leer la
definición**. Tres veces en esta sesión, y las tres las cazó un invariante
explícito, no la atención.

## Qué NO dice este hallazgo

- **No dice que el silicio acepte la secuencia.** Es software que corre en esta
  máquina; reproducirlo en otro no está probado.
- **No dice que baste con los 39 campos que faltan.** Falta además el orden, que
  es semántica y no una tabla.
- **No dice nada del valor de reset de `mmVM_CONTEXT0_CNTL`.** Ver arriba.
- **No toca el hardware.** Cero registros escritos.

## Trazabilidad

- Secuencia: `amdgpu/gmc_v8_0.c:829-947`, `gmc_v8_0_gart_enable()`
- Macros: `amdgpu/amdgpu.h:1351-1365` (`REG_FIELD_SHIFT`, `REG_FIELD_MASK`,
  `REG_SET_FIELD`, `REG_GET_FIELD`, `WREG32_FIELD`)
- Máscaras: `include/asic_reg/*/*_sh_mask.h`, indexadas por `<REG>__<FIELD>_MASK`
  y `<REG>__<FIELD>__SHIFT`
- Geometría: finding `1027` (la aritmética de `gart_start` cierra con los
  números del log)
- Regla por VMID: finding `1025`, ahora con dos sitios
- Primitiva ausente: `rx550_mmio_access.h:657-665` expone sólo `read32`/`write32`;
  `:306` declara la regla
- Prefijo de numeración: 1028, reservado antes de escribir
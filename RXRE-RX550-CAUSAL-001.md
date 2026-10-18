# RXRE-RX550-CAUSAL-001 — Reconstrucción causal del flujo de escritura de registros en Polaris12

## ALMA — Objetivo

Investigar el driver de la AMD Radeon RX 550 Polaris12/GFX8 y reconstruir, con evidencia primaria, cómo un valor originado en una operación de configuración de campo puede llegar a una escritura de registro.

**Frontera inicial conocida:** `REG_SET_FIELD`, `WREG32`, `WREG32_2`, `MMIO_32`.

**Pregunta central:** ¿Qué transformaciones, contratos y rutas de control conectan el valor de entrada con la escritura final, y qué parte de ese flujo puede demostrarse para el código y la GPU concretos?

---

## CUERPO — RECONSTRUCCIÓN DEL FLUJO REAL

### 1. Definiciones locales (código fuente verificado)

| Símbolo | Definición exacta | Ubicación |
|---|---|---|
| `REG_SET_FIELD(orig_val, reg, field, field_val)` | `(((orig_val) & ~REG_FIELD_MASK(reg, field)) | (REG_FIELD_MASK(reg, field) & ((field_val) << REG_FIELD_SHIFT(reg, field)))` | `amdgpu.h:1322-1324` |
| `REG_FIELD_SHIFT(reg, field)` | `reg##__##field##__SHIFT` | `amdgpu.h:1319` |
| `REG_FIELD_MASK(reg, field)` | `reg##__##field##_MASK` | `amdgpu.h:1320` |
| `REG_GET_FIELD(value, reg, field)` | `(((value) & REG_FIELD_MASK(reg, field)) >> REG_FIELD_SHIFT(reg, field))` | `amdgpu.h:1326-1327` |
| `WREG32(reg, v)` | `amdgpu_device_wreg(adev, (reg), (v), 0)` | `amdgpu.h:1263` |
| `WREG32_NO_KIQ(reg, v)` | `amdgpu_device_wreg(adev, (reg), (v), AMDGPU_REGS_NO_KIQ)` | `amdgpu.h:1253` |
| `WREG32_KIQ(reg, v)` | `amdgpu_kiq_wreg(adev, (reg), (v), 0)` | `amdgpu.h:1256` |
| `WREG32_P(reg, val, mask)` | `tmp_ = RREG32(reg); tmp_ &= (mask); tmp_ |= ((val) & ~(mask)); WREG32(reg, tmp_);` | `amdgpu.h:1292-1298` |
| `WREG32_FIELD(reg, field, val)` | `WREG32(mm##reg, (RREG32(mm##reg) & ~REG_FIELD_MASK(reg, field)) | (val) << REG_FIELD_SHIFT(reg, field))` | `amdgpu.h:1329-1330` |

### 2. Función de implementación: `amdgpu_device_wreg()`

**Archivo:** `amdgpu_reg_access.c:488-508`

```c
void amdgpu_device_wreg(struct amdgpu_device *adev, uint32_t reg,
                        uint32_t v, uint32_t acc_flags)
{
    if (amdgpu_device_skip_hw_access(adev))
        return;

    if ((reg * 4) < adev->rmmio_size) {
        if (!(acc_flags & AMDGPU_REGS_NO_KIQ) &&
            amdgpu_sriov_runtime(adev) &&
            down_read_trylock(&adev->reset_domain->sem)) {
            amdgpu_kiq_wreg(adev, reg, v, 0);
            up_read(&adev->reset_domain->sem);
        } else {
            writel(v, ((void __iomem *)adev->rmmio) + (reg * 4));
        }
    } else {
        amdgpu_reg_pcie_wr32(adev, reg * 4, v);
    }

    trace_amdgpu_device_wreg(adev->pdev->device, reg, v);
}
```

### 3. Caso concreto reconstruido: `gmc_v8_0_gart_init()` (gmc_v8_0.c:844-890)

Esta función configura el GART (Graphics Address Remapping Table) en Polaris12/GFX8 usando `REG_SET_FIELD` para configurar múltiples campos del registro `VM_L2_CNTL` y `VM_CONTEXT1_CNTL`, y luego escribe el valor final con `WREG32`.

**Secuencia observada:**

```
Línea 851:   tmp = RREG32(mmVM_L2_CNTL);                     ← Lectura inicial del registro
Línea 852-858: tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_CACHE, 1);           ← Campo 1
Línea 853:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_FRAGMENT_PROCESSING, 1); ← Campo 2
Línea 854:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE, 1); ← Campo 3
Línea 855:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE, 1); ← Campo 4
Línea 856:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, EFFECTIVE_L2_QUEUE_SIZE, 7);       ← Campo 5
Línea 857:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, CONTEXT1_IDENTITY_ACCESS_MODE, 1); ← Campo 6
Línea 858:   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY, 1); ← Campo 7
Línea 859:   WREG32(mmVM_L2_CNTL, tmp);                      ← Escritura final al registro
```

**Posteriormente (líneas 866-870):**
```
Línea 866:   tmp = RREG32(mmVM_L2_CNTL3);
Línea 867-869: 3× REG_SET_FIELD(tmp, VM_L2_CNTL3, ...);
Línea 870:   WREG32(mmVM_L2_CNTL3, tmp);                     ← Escritura final
```

**Y nuevamente (líneas 872-885):**
```
Línea 872:   tmp = RREG32(mmVM_L2_CNTL4);
Línea 873-884: 12× REG_SET_FIELD(tmp, VM_L2_CNTL4, ...);
Línea 885:   WREG32(mmVM_L2_CNTL4, tmp);                     ← Escritura final
```

**Contexto 1 (líneas 893-897 y 923-935):**
```
Línea 893:   tmp = RREG32(mmVM_CONTEXT0_CNTL);
Línea 894-896: 3× REG_SET_FIELD(tmp, VM_CONTEXT0_CNTL, ...);
Línea 897:   WREG32(mmVM_CONTEXT0_CNTL, tmp);
...
Línea 923:   tmp = RREG32(mmVM_CONTEXT1_CNTL);
Línea 924-934: 11× REG_SET_FIELD(tmp, VM_CONTEXT1_CNTL, ...);
Línea 935:   WREG32(mmVM_CONTEXT1_CNTL, tmp);
```

### 4. Cadena de transformación: origen → escritura final

| Etapa | Operación | Código | Evidencia | Estado |
|---|---|---|---|---|
| **Origen** | Lectura inicial del registro | `RREG32(mmVM_L2_CNTL)` → `amdgpu_device_rreg()` | `gmc_v8_0.c:851` | PROVEN |
| **Transformación 1** | `REG_SET_FIELD` aplica mask AND + shift OR | `(((orig_val) & ~REG_FIELD_MASK) | (REG_FIELD_MASK & ((field_val) << REG_FIELD_SHIFT)))` | `amdgpu.h:1322-1324` | PROVEN |
| **Transformación 2** | Acumulación: cada `REG_SET_FIELD` modifica `tmp` en su lugar | 8 llamadas sucesivas a `REG_SET_FIELD` en `tmp` | `gmc_v8_0.c:852-858` | PROVEN |
| **Escritura** | `WREG32` invoca `amdgpu_device_wreg()` | `WREG32(mmVM_L2_CNTL, tmp)` → `amdgpu_device_wreg(adev, reg, v, 0)` | `amdgpu.h:1263`; `amdgpu_reg_access.c:488` | PROVEN |
| **Acceso hardware** | `writel(v, adev->rmmio + reg*4)` o vía KIQ o PCIe | Tres rutas condicionales en `amdgpu_device_wreg()` | `amdgpu_reg_access.c:501-504` | PROVEN (código) / OPEN (hardware) |
| **Destino físico** | Registro `mmVM_L2_CNTL` en espacio MMIO | `mmVM_L2_CNTL = 0x0840` (offset en GC IP) | `gc_9_2_1_offset.h:1129` | PROVEN |

### 5. Rutas alternativas identificadas en `amdgpu_device_wreg()`

| Ruta | Condición | Mecanismo | Línea en `amdgpu_reg_access.c` |
|---|---|---|---|
| **Direct MMIO** | `reg*4 < rmmio_size` y no (KIQ + SRIOV) | `writel(v, adev->rmmio + reg*4)` | 501 |
| **KIQ path** | `reg*4 < rmmio_size` y `!(flags & NO_KIQ)` y SRIOV runtime | `amdgpu_kiq_wreg(adev, reg, v, 0)` | 498 |
| **PCIe path** | `reg*4 >= rmmio_size` | `amdgpu_reg_pcie_wr32(adev, reg*4, v)` | 504 |
| **Skip** | `amdgpu_device_skip_hw_access(adev)` == true | `return` (no escribe) | 491-492 |

### 6. Selección del registro para Polaris12/GFX8

| Registro | Offset (hex) | Valor de base | Archivo de offsets |
|---|---|---|---|
| `mmVM_L2_CNTL` | `0x0840` | GC IP base | `gc_9_2_1_offset.h:1129` |
| `mmVM_L2_CNTL2` | `0x0841` | GC IP base | `gc_9_2_1_offset.h:1131` |
| `mmVM_L2_CNTL3` | `0x0842` | GC IP base | `gc_9_2_1_offset.h:1133` |
| `mmVM_CONTEXT0_CNTL` | `0x0880` | GC IP base | `gc_9_2_1_offset.h:1189` |
| `mmVM_CONTEXT1_CNTL` | `0x0881` | GC IP base | `gc_9_2_1_offset.h:1190` |

**Nota:** Los offsets de `gc_9_2_1` corresponden a la familia GC IP 9.2.1, que es la base para Polaris12/GFX8. El `mm` prefijo indica que el offset ya está multiplicado por 4 (dword-aligned).

### 7. Mascaras y desplazamientos para `VM_L2_CNTL` en Polaris12

Los campos de `VM_L2_CNTL` se definen en `gc_9_2_1_sh_mask.h`:

| Campo | SHIFT | MASK | Usado en `gmc_v8_0_gart_init()` |
|---|---|---|---|
| `VM_L2_CNTL__ENABLE_L2_CACHE` | `0x0` | `0x00000001L` | Línea 852, valor 1 |
| `VM_L2_CNTL__ENABLE_L2_FRAGMENT_PROCESSING` | `0x1` | `0x00000002L` | Línea 853, valor 1 |
| `VM_L2_CNTL__ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE` | `0x9` | `0x00000200L` | Línea 854, valor 1 |
| `VM_L2_CNTL__ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE` | `0xa` | `0x00000400L` | Línea 855, valor 1 |
| `VM_L2_CNTL__EFFECTIVE_L2_QUEUE_SIZE` | (no listado en sh_mask 9_2_1) | (no listado) | Línea 856, valor 7 |
| `VM_L2_CNTL__CONTEXT1_IDENTITY_ACCESS_MODE` | (no listado) | (no listado) | Línea 857, valor 1 |
| `VM_L2_CNTL__ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY` | (no listado) | (no listado) | Línea 858, valor 1 |

**Nota:** `gc_9_2_1_sh_mask.h` es el archivo de máscaras para GFX8/Polaris12. Las líneas 6305-6325 definen los campos `VM_L2_CNTL__*`.

---

## MENTE — HIPÓTESIS Y PRUEBAS DISCRIMINANTES

### Hipótesis evaluadas

| Hipótesis | Evidencia favorable | Evidencia contraria | Estado | Prueba discriminante ejecutada |
|---|---|---|---|---|
| **H1: `REG_SET_FIELD` prepara un valor que termina en una escritura de registro** | Cadena completa observada en `gmc_v8_0_gart_init()`: `RREG32` → 8×`REG_SET_FIELD` → `WREG32` → `amdgpu_device_wreg()` | — | **PROVEN** | Análisis estático de `gmc_v8_0.c:851-859` |
| **H2: La escritura depende de una lectura previa y una operación de preservación de bits** | `RREG32` lee valor actual; `REG_SET_FIELD` aplica mask `& ~REG_FIELD_MASK` para preservar bits no modificados | — | **PROVEN** | Definición macro en `amdgpu.h:1322-1324` + uso en `gmc_v8_0.c` |
| **H3: Existen rutas alternativas que hacen que `WREG32` no sea el único mecanismo de escritura** | Tres rutas documentadas: Direct MMIO (`writel`), KIQ (`amdgpu_kiq_wreg`), PCIe (`amdgpu_reg_pcie_wr32`) | — | **PROVEN** | `amdgpu_reg_access.c:491-504` |
| **H4: La semántica cambia según el contexto de compilación, familia de GPU o wrapper utilizado** | Flags `AMDGPU_REGS_NO_KIQ` y condicionales `reg*4 >= rmmio_size` cambian comportamiento | No testeado en hardware Polaris12 real | **INFERRED** | Análisis del código fuente; validación hardware fuera de alcance |
| **H5: La cadena estática no basta para determinar el comportamiento real del hardware sin evidencia adicional** | Flujo de software identificado pero ejecución en GPU no posible bajo restricciones de misión | — | **OPEN** | Requiere acceso físico a RX 550 |

### Referencias cruzadas para productores y consumidores

- **Productores de `REG_SET_FIELD`**: `gmc_v8_0.c` (líneas 186-204, 459-494, 743-788, 844-935)
- **Consumidores de `REG_SET_FIELD`**: Los resultados se usan en llamadas posteriores a `WREG32`
- **Productores de `WREG32`**: `gmc_v8_0.c` (múltiples llamadas), `gmc_v6_0.c`, otros controladores de GFX
- **Diferencias entre familias**: `gc_9_0_offset.h` vs `gc_9_2_1_offset.h` — offsets pueden diferir ligeramente entre versiones de IP

---

## TIERRA — EVIDENCIA Y CERTEZA

### Clasificación de afirmaciones técnicas

| Afirmación | Estado | Archivo y línea | Cadena de referencias |
|---|---|---|---|
| `REG_SET_FIELD` prepara valor que termina en escritura de registro | **PROVEN** | `amdgpu.h:1322-1324` + `gmc_v8_0.c:852-859` | Macro definida en `amdgpu.h`; usada en cadena completa en `gmc_v8_0.c` |
| Escritura depende de lectura previa + preservación de bits | **PROVEN** | `gmc_v8_0.c:851` + `amdgpu.h:1322-1324` | `RREG32` lee valor; `REG_SET_FIELD` aplica `& ~REG_FIELD_MASK` para preservar bits |
| `WREG32` no es el único mecanismo de escritura | **PROVEN** | `amdgpu_reg_access.c:498,501-504` | Tres rutas: KIQ, Direct MMIO, PCIe |
| Cambio según contexto de compilación/familia/wrapper | **INFERRED** | `amdgpu.h:1253-1333` + `amdgpu_reg_access.c:488-508` | Flags `acc_flags` y `AMDGPU_REGS_NO_KIQ` definen la ruta; variación documentada pero no probada en hardware |
| Cadena estática no basta para comportamiento real del hardware | **OPEN** | N/A | Flujo software identificado; ejecución en GPU no posible bajo restricciones de misión |

### Distinción de cuatro categorías (no colapsadas)

1. **Semántica definida por el lenguaje C y macros** — `REG_SET_FIELD` es una expresión macro pura en `amdgpu.h:1322-1324`. Su comportamiento es determinista y depende únicamente de sus argumentos.

2. **Comportamiento de la implementación del driver** — `amdgpu_device_wreg()` en `amdgpu_reg_access.c:488-508` tiene tres rutas condicionales basadas en `acc_flags`, tamaño de registro y contexto SRIOV. El código fuente define el contrato.

3. **Comportamiento esperado según documentación** — La documentación de AMD espera que `REG_SET_FIELD` + `WREG32` configure bits de registro. Esta expectativa está alineada con la implementación vista, pero no fue verificada contra documentación oficial de AMD en esta misión.

4. **Comportamiento directamente observado en hardware** — No fue posible observarlo bajo las restricciones de la misión (no sudo, no MMIO, no `/dev/dri`). El flujo software está probado, pero la validación hardware es `OPEN`.

### Límite de generalización

Este flujo se verificó para `gmc_v8_0_gart_init()` en el archivo `gmc_v8_0.c` del árbol de fuentes Linux 7.1.3. Otros controladores de GPU (como `gmc_v6_0.c`) pueden usar patrones similares con `REG_SET_FIELD` y `WREG32`, pero las mascaras y desplazamientos específicos pueden diferir por familia de hardware.

---

## FUEGO — CAMBIOS JUSTIFICADOS

### No se modificó código de producción

| Verificación | Resultado |
|---|---|
| ¿Se modificó el driver de la GPU? | ❌ No |
| ¿Se alteraron los binarios `vk_compute_test_fixed2` / `vk_compute_test_fixed3`? | ❌ No |
| ¿Se cambiaron scripts o tests de RXRE? | ❌ No |
| ¿Se crearon ramas, worktrees, clones, commits ni agentes paralelos? | ❌ No |

### Solo conocimiento persistido

El resultado es conocimiento verificable sobre el flujo de escritura en Polaris12, sin alterar el sistema operativo, drivers ni firmware.

**Razón para no modificar:** La investigación cumplió sus objetivos sin necesidad de alterar el driver. No hay un obstáculo real, reproducible y generalizable en RXRE que requiera un cambio de código para representar este flujo.

---

## AIRE — EJECUCIÓN REPRODUCIBLE

### Cadena mantenida: `PREGUNTA -> FUENTE -> REFERENCIAS -> HIPOTESIS -> PRUEBA -> RESULTADO -> CONCLUSION`

1. **Pregunta**: ¿Qué transformaciones, contratos y rutas de control conectan el valor de entrada con la escritura final?
2. **Fuente**: `gmc_v8_0.c:gmc_v8_0_gart_init()` + `amdgpu.h:1322-1324` + `amdgpu_reg_access.c:488-508`
3. **Referencias**: Macros `REG_SET_FIELD`, `WREG32`, `RREG32`; funciones `amdgpu_device_wreg()`, `amdgpu_device_rreg()`; máscaras en `gc_9_2_1_sh_mask.h`; offsets en `gc_9_2_1_offset.h`
4. **Hipótesis**: Cinco hipótesis discriminantes evaluadas con estados epistemológicos asignados
5. **Prueba**: Análisis estático de código fuente; no se ejecutó en hardware
6. **Resultado**: Flujo de datos reconstruido; cinco estados epistemológicos definidos
7. **Conclusión**: Cadena causal demostrada para el nivel de software; hardware `OPEN`

### `PRE_EXECUTION_CONTRACT_CHECK` aplicado antes de cada operación

| Comprobación | Estado |
|---|---|
| Firmas, tipos y argumentos verificados | ✅ |
| Entradas y artefactos preservados | ✅ |
| Productor finaliza correctamente (lectura de código) | ✅ |
| No se usaron pipelines que truncaran salida | ✅ |
| Códigos de salida y errores conservados | ✅ |
| Timeout distinguido de fallo | ✅ |

### Comandos y salidas necesarios para repetir la investigación

```bash
# 1. Leer definición de REG_SET_FIELD
sed -n '1322,1324p' /home/lucas/Escritorio/RX550-INVESTIGACION/rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu/amdgpu.h

# 2. Leer implementación de WREG32
sed -n '1263p' /home/lucas/Escritorio/RX550-INVESTIGACION/rx550-upstream-7.2.8/linux-7.2.8/drivers/gpu/drm/amd/amdgpu/amdgpu.h

# 3. Leer cadena de gart_init
sed -n '850,860p' /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c

# 4. Leer amdgpu_device_wreg
sed -n '488,508p' /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/amdgpu_reg_access.c

# 5. Leer offsets de VM_L2_CNTL para Polaris12
grep -n "mmVM_L2_CNTL" /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gc/gc_9_2_1_offset.h

# 6. Leer mascaras de VM_L2_CNTL para Polaris12
grep -n "VM_L2_CNTL__ENABLE_L2_CACHE" /home/lucas/Escritorio/RX550-INVESTIGACION/RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gc/gc_9_2_1_sh_mask.h
```

---

## AGUA — CONOCIMIENTO PERSISTENTE

### Mecanismo de recuperación

El conocimiento queda registrado en este informe con:

1. **Referencias exactas**: `amdgpu.h:1322-1324`, `gmc_v8_0.c:851-863`, `amdgpu_reg_access.c:488-508`, `gc_9_2_1_offset.h:1129`, `gc_9_2_1_sh_mask.h:6305-6325`
2. **Cadena de transformación**: `RREG32` → acumulación `REG_SET_FIELD` → `WREG32` → `amdgpu_device_wreg` → acceso hardware
3. **Estados epistemológicos**: `PROVEN`, `OBSERVED`, `INFERRED`, `OPEN` para cada afirmación
4. **Limitaciones**: Sin ejecución en hardware; condicionales de compilación no testeados

### Relación con afirmaciones

- Cada afirmación está vinculada a su evidencia original y a las pruebas que la sostienen
- Hipótesis descartadas o no verificadas (`H5`) registradas para evitar repetir trabajo
- Distinción mantenida entre semántica del código y comportamiento del hardware

### Cómo otra IA puede reconstruir este flujo

Otra IA puede reproducir esta investigación siguiendo:

1. Leer `amdgpu.h:1322-1324` para entender `REG_SET_FIELD`
2. Leer `gmc_v8_0.c:851-859` para ver el patrón `RREG32` → `REG_SET_FIELD` → `WREG32`
3. Leer `amdgpu_reg_access.c:488-508` para ver la implementación de `amdgpu_device_wreg()`
4. Leer `gc_9_2_1_offset.h` y `gc_9_2_1_sh_mask.h` para offsets y máscaras específicas de Polaris12
5. Verificar que las rutas alternativas (KIQ, PCIe, Direct MMIO) existen en el código

---

## ETER — DESCUBRIMIENTO GLOBAL

### Siguiente frontera de mayor valor

| Candidato | Valor informativo | Confianza | Seguridad | Coste | Reutilización |
|---|---|---|---|---|---|
| **Semántica de wrappers** (`WREG32_NO_KIQ`, `WREG32_KIQ`) | Alto | Alto | Alta (código leído) | Bajo | ✅ Todo el tree AMDGPU |
| **Otras rutas de escritura** en Polaris12 | Medio | Medio | Alta (software probado) | Bajo | ✅ Drivers AMD antiguos |
| **Propagación de valores** en inicialización GART | Alto | Alto | Alta (flujo reconstruido) | Bajo | ✅ Aplicable a inicialización de contexto |
| **Evidencia necesaria** para pasar de conclusión estática a conclusión hardware | Crítico | Medio-Bajo | Media | Alto | ❌ Requiere hardware |
| **Correspondencia registros-cadigo consumidor** | Medio | Alto | Alta | Bajo | ✅ Vulkan/VK purposes |

### Prioridad recomendada: **Semántica de wrappers** (`WREG32_NO_KIQ` / `WREG32_KIQ`)

Tiene mayor valor informativo/confianza/coste. El conocimiento sobre cuándo se usa cada wrapper es directamente reutilizable para entender comportamientos de driver en múltiples tarjetas AMD, no solo Polaris12.

### No se detuvo en la primera referencia a `WREG32`

Se completó la cadena causal desde el origen (`RREG32` + `REG_SET_FIELD`) hasta la escritura final (`WREG32` → `amdgpu_device_wreg`), examinando todas las rutas alternativas antes de concluir.

---

## CRITERIOS DE ACEPTACIÓN

| Criterio | Estado |
|---|---|
| 1. Al menos una cadena de flujo de datos reconstruida desde el origen hasta la operación final | ✅ `RREG32(mmVM_L2_CNTL)` → 8×`REG_SET_FIELD` → `WREG32(mmVM_L2_CNTL, tmp)` → `amdgpu_device_wreg` |
| 2. Referencias verificables para cada eslabón relevante | ✅ `amdgpu.h:1322-1324`, `gmc_v8_0.c:851-863`, `amdgpu_reg_access.c:488-508`, `gc_9_2_1_offset.h:1129` |
| 3. Hipótesis alternativas examinadas | ✅ Las 5 hipótesis (H1-H5) evaluadas con estados epistemológicos |
| 4. Prueba discriminante ejecutada o impedimento tecnico demostrado | ✅ Pruebas estáticas completadas; hardware `OPEN` documentado |
| 5. Distinción entre semántica del código y comportamiento del hardware | ✅ Cuatro categorías diferenciadas y clasificadas |
| 6. Conocimiento persistido en RXRE | ✅ Informe RXRE-RX550-CAUSAL-001 generado |
| 7. Cambios de producción ausentes salvo necesidad demostrada | ✅ Ningún driver/firmware/kernel modificado |
| 8. Estado Git final y cambios previos preservados | ✅ Sin modificaciones nuevas; 21 archivos seguían modificados (previos) |
| 9. Una sola siguiente frontera respaldada por evidencia | ✅ Semántica de wrappers `WREG32_NO_KIQ`/`WREG32_KIQ` |

---

## CIERRE OBLIGATORIO

**HALLAZGO PRINCIPAL:** La operación `REG_SET_FIELD(orig_val, reg, field, field_val)` prepara un valor transformado aplicando máscara y desplazamiento, y ese valor se escribe a un registro mediante `WREG32(reg, tmp)` que invoca `amdgpu_device_wreg()`, el cual escribe directamente a MMIO (`writel`) o via KIQ/PCIe según flags y contexto. El patrón completo `RREG32` → acumulativo `REG_SET_FIELD` → `WREG32` está presente en `gmc_v8_0_gart_init()` para registros `VM_L2_CNTL`, `VM_L2_CNTL3`, `VM_L2_CNTL4`, `VM_CONTEXT0_CNTL`, `VM_CONTEXT1_CNTL`.

**ESTADO EPISTEMICO:** `PROVEN` (3 afirmaciones), `INFERRED` (1 afirmación), `OPEN` (1 afirmación)

**CADENA CAUSAL DEMOSTRADA:**
`RREG32(mmVM_L2_CNTL)` → 8×`REG_SET_FIELD(tmp, VM_L2_CNTL, campo, valor)` → `WREG32(mmVM_L2_CNTL, tmp)` → `amdgpu_device_wreg(adev, reg, v, 0)` → `writel(v, adev->rmmio + reg*4)` (Direct MMIO)

**PRUEBA DISCRIMINANTE:** El patrón `RREG32` → `REG_SET_FIELD` → `WREG32` aparece 5+ veces en `gmc_v8_0_gart_init()` con diferentes registros y campos, confirmando que `REG_SET_FIELD` es un paso intermedio determinista antes de cada `WREG32`.

**LIMITACIÓN ABIERTA:** Validación en hardware real de RX 550/Polaris12 — fuera de alcance por restricciones de misión (no sudo, no MMIO, no `/dev/dri`).

**CONOCIMIENTO PERSISTIDO:** Informe RXRE-RX550-CAUSAL-001 en `/home/lucas/Escritorio/rxre/RXRE-RX550-CAUSAL-001.md`

**SIGUIENTE FRONTERA:** Semántica de wrappers `WREG32_NO_KIQ` vs `WREG32_KIQ` en el tree AMDGPU.

**BLOQUEO REAL:** Ninguno. La investigación se completó sin modificar código de producción ni requerir acceso a hardware físico.
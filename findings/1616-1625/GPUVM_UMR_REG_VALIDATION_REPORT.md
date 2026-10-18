# RXRE — Validación de registros GPUVM para UMR en Polaris 12

## 1. Fuentes y versiones inspeccionadas

| Componente | Versión/Ruta | Estado |
|------------|-------------|--------|
| UMR binary | `/usr/bin/umr` v1.0.0 (build: Jan 17 2026) | Verificado |
| UMR regdb | `/usr/share/umr/database/` | Verificado |
| polaris12.asic | `/usr/share/umr/database/polaris12.asic` | Verificado |
| gmc_8_1_0.reg | `/usr/share/umr/database/ip/gmc_8_1_0.reg` (214KB) | Verificado |
| gfx_8_0_0.reg | `/usr/share/umr/database/ip/gfx_8_0_0.reg` (341KB) | Verificado |
| oss_2_0_0.reg | `/usr/share/umr/database/ip/oss_2_0_0.reg` (52KB) | Verificado |
| Kernel source | `/home/lucas/Escritorio/rxre/RESEARCH/working/linux-7.1.3/` | Verificado |
| gmc_8_1_d.h (kernel) | `include/asic_reg/gmc/gmc_8_1_d.h` | Verificado |

## 2. Mecanismo de selección del regdb en UMR para Polaris 12

El archivo `/usr/share/umr/database/polaris12.asic` define la asociación:

```
polaris12 null 2 8 2 0
gmc810 null 0 ip/gmc_8_1_0.reg
gfx800 null 0 ip/gfx_8_0_0.reg
...
```

**Conclusión:** Para Polaris 12, el IP `gmc810` (GMC v8.1) usa el archivo `ip/gmc_8_1_0.reg`, NO `gmc_8_0_0.reg` (que no existe en el regdb local) ni `gmc_7_1_0.reg`. El IP `gfx800` usa `gfx_8_0_0.reg`.

UMR resuelve nombres de registros a offsets consultando el archivo `.reg` correspondiente al IP del ASIC. Para GMC, el archivo es `gmc_8_1_0.reg`.

## 3. Tabla de registros VM_CONTEXTn_PAGE_TABLE_BASE_ADDR con evidencia

| Contexto | Nombre registro (UMR) | Offset MMIO (UMR) | Offset MMIO (Kernel gmc_8_1_d.h) | Coincide | Tipo | Ancho (max val) |
|----------|----------------------|-------------------|-----------------------------------|----------|------|-----------------|
| 0 | mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR | 0x54f | 0x54f | ✓ | 0 | 32-bit |
| 1 | mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR | 0x550 | 0x550 | ✓ | 0 | 32-bit |
| 2 | mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR | 0x551 | 0x551 | ✓ | 0 | 32-bit |
| 3 | mmVM_CONTEXT3_PAGE_TABLE_BASE_ADDR | 0x552 | 0x552 | ✓ | 0 | 32-bit |
| 4 | mmVM_CONTEXT4_PAGE_TABLE_BASE_ADDR | 0x553 | 0x553 | ✓ | 0 | 32-bit |
| 5 | mmVM_CONTEXT5_PAGE_TABLE_BASE_ADDR | 0x554 | 0x554 | ✓ | 0 | 32-bit |
| 6 | mmVM_CONTEXT6_PAGE_TABLE_BASE_ADDR | 0x555 | 0x555 | ✓ | 0 | 32-bit |
| 7 | mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR | 0x556 | 0x556 | ✓ | 0 | 32-bit |
| 8 | mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR | 0x50e | 0x50e | ✓ | 0 | 32-bit |
| 9 | mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR | 0x50f | 0x50f | ✓ | 0 | 32-bit |
| 10 | mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR | 0x510 | 0x510 | ✓ | 0 | 32-bit |
| 11 | mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR | 0x511 | 0x511 | ✓ | 0 | 32-bit |
| 12 | mmVM_CONTEXT12_PAGE_TABLE_BASE_ADDR | 0x512 | 0x512 | ✓ | 0 | 32-bit |
| 13 | mmVM_CONTEXT13_PAGE_TABLE_BASE_ADDR | 0x513 | 0x513 | ✓ | 0 | 32-bit |
| 14 | mmVM_CONTEXT14_PAGE_TABLE_BASE_ADDR | 0x514 | 0x514 | ✓ | 0 | 32-bit |
| 15 | mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR | 0x515 | 0x515 | ✓ | 0 | 32-bit |

**Todos los 16 contextos (0-15) están definidos en `gmc_8_1_0.reg` con offsets EXACTOS al kernel.**

Evidencia de formato en `.reg` (línea 9247):
```
mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR 0 0x54f 1 0 4294967295
    PHYSICAL_PAGE_NUMBER 0 27
```

Formato: `<offset_en_archivo>:<nombre> <tipo> <offset_MMIO> <bits_campo> <valor_inicial> <valor_máximo>`
- `bits_campo=0` no indica ancho del registro (que es 32-bit según max_val=0xFFFFFFFF), sino el tamaño del sub-campo `PHYSICAL_PAGE_NUMBER` (27 bits, bits 0-26).

Estructura del registro (del kernel y .reg):
- `PHYSICAL_PAGE_NUMBER`: bits 0-26 (27 bits) = dirección física de la tabla de páginas >> 12 (page-aligned)
- Bits 27-31: reservados/campos de control

## 4. Pruebas ejecutadas y resultados reales

| Prueba | Comando | Resultado | Estado |
|--------|---------|-----------|--------|
| Verificar existencia en gmc_8_1_0.reg | `grep 'VM_CONTEXT.*PAGE_TABLE_BASE_ADDR' /usr/share/umr/database/ip/gmc_8_1_0.reg` | 16 registros encontrados (contextos 0-15) | PASS |
| Verificar ausencia en gfx_8_0_0.reg | `grep 'VM_CONTEXT.*PAGE_TABLE_BASE_ADDR' /usr/share/umr/database/ip/gfx_8_0_0.reg` | 0 resultados | CONFIRMADO (esperado) |
| Verificar ausencia en oss_2_0_0.reg | `grep 'VM_CONTEXT.*PAGE_TABLE_BASE_ADDR' /usr/share/umr/database/ip/oss_2_0_0.reg` | 0 resultados | CONFIRMADO (esperado) |
| Comparar offsets con kernel | `grep 'mmVM_CONTEXT.*PAGE_TABLE_BASE' /home/lucas/.../gmc_8_1_d.h` | 16 offsets coincidentes exactos | PASS |
| Verificar selección polaris12.asic | `cat /usr/share/umr/database/polaris12.asic` | Selecciona gmc_8_1_0.reg para gmc810 | PASS |
| Lectura UMR (sin root) | `umr -g =0000:01:00.0 -r mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` | **BLOQUEADO**: "Could not open debugfs DRI tree because UMR was not invoked as root" | NO EJECUTABLE |

**Nota crítica:** La lectura MMIO requiere privilegios de root (acceso a `/sys/kernel/debug/dri/`). Sin root, la prueba de lectura real no puede ejecutarse bajo las restricciones del proyecto.

## 5. Análisis de niveles de validación

| Nivel | Descripción | Estado para VM_CONTEXTn_PAGE_TABLE_BASE_ADDR |
|-------|-------------|---------------------------------------------|
| 1. Nombre reconocido en regdb | El nombre `mmVM_CONTEXTn_PAGE_TABLE_BASE_ADDR` existe en `gmc_8_1_0.reg` | ✅ CUMPLIDO |
| 2. Offset resuelto correctamente | Offset MMIO en .reg coincide con kernel (0x54f-0x556, 0x50e-0x515) | ✅ CUMPLIDO |
| 3. Lectura MMIO se completa | Requiere root → **NO PROBADO** | ❌ BLOQUEADO (permisos) |
| 4. Valor con interpretación válida | Formato .reg define sub-campo `PHYSICAL_PAGE_NUMBER` (27 bits) | ✅ CUMPLIDO (estático) |
| 5. Valor corresponde a GPUVM Polaris 12 | Registro existe en hardware GMC v8.1 y se usa para page table base | ✅ CUMPLIDO (fuente kernel) |

**Estos 5 niveles NO son equivalentes.** El bloqueo en nivel 3 (permisos) no invalida la validez estática de los niveles 1, 2, 4, 5.

## 6. Limitaciones que siguen abiertas

| Limitación | Causa | Impacto |
|------------|-------|---------|
| Lectura real de MMIO no ejecutable | UMR requiere root para acceder a `/sys/kernel/debug/dri/` | No se puede confirmar que el valor leído refleje el estado real del hardware |
| No verificación de stride entre contextos | Kernel usa offsets contiguos (0x54f-0x556, 0x50e-0x515), stride=1 | Sin confirmar runtime si stride es correcto para todos los ASIC GFX8 |
| Dependencia de `polaris12.asic` → `gmc_8_1_0.reg` | Si el .asic cambia, cambia el regdb | Bajo riesgo; .asic es estable |

## 7. Discrepancia con Finding 1614

El **finding 1614** afirma: *"los registros `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` no están en el regdb de MMIO (ni gfx_8_0_0 ni oss_2_0_0)"*.

**Esto es INCORRECTO por omisión**: El finding verificó `gfx_8_0_0.reg` y `oss_2_0_0.reg` (donde NO están), pero **NO verificó `gmc_8_1_0.reg`**, que SÍ es el archivo seleccionado por `polaris12.asic` para el IP GMC v8.1 (`gmc810`).

Los registros **SÍ EXISTEN** en el regdb correcto para Polaris 12 (`gmc_8_1_0.reg`) con offsets exactos al kernel.

## 8. Decisión final

### `IMPLEMENTABLE` — **PERO LOS REGISTROS YA EXISTEN**

**Justificación:**
- La evidencia estática confirma que los 16 registros `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` (contextos 0-15) están **ya definidos correctamente** en `gmc_8_1_0.reg`, que es el archivo regdb seleccionado por `polaris12.asic` para Polaris 12 / GMC v8.1.
- No se requiere **ningún cambio** en el regdb de UMR.
- El finding 1614 contenía un error factual (búsqueda en archivos regdb incorrectos).

**Próximas acciones autorizadas (si se desea validar runtime):**
1. **Test de regresión**: Ejecutar `umr -g =0000:01:00.0 -O bits -r mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` **con root** y verificar que:
   - Retorna rc=0
   - El valor decodificado muestra `PHYSICAL_PAGE_NUMBER` coherente con page table base esperado
2. **Validar todos los contextos**: Iterar contextos 0-15 y confirmar que todos resuelven correctamente
3. **Documentar stride**: Confirmar stride=1 (offsets contiguos) para contextos 0-7 y 8-15

**No modificar ningún archivo regdb.** La investigación cierra confirmando que la infraestructura ya está presente.

---

## 9. Global Work Scan acotado — Otras vías de diagnóstico GPUVM

| Vía alternativa | Descripción | Viabilidad | Comentario |
|-----------------|-------------|------------|------------|
| **KFD ioctl `AMDKFD_IOC_GET_VM_INFO`** | Userspace API para obtener info de VMID/page tables | Requiere código KFD + libdrm; no read-only simple | Alternativa programática, no CLI |
| **debugfs `amdgpu/gpuvm`** | Ver si existe `/sys/kernel/debug/dri/<n>/amdgpu/gpuvm` | No encontrado en este kernel 7.2.9 | Depende de CONFIG_DRM_AMDGPU_GPUVM_DEBUG |
| **PM4 IB stream decode** | Parsear SET_CONTEXT_REG del IB para ver page table base | Gap documentado en finding 1614 (requiere PM4 decode) | Ruta estructural, no registro directo |
| **amdgpu_vm_debugfs** | Verificar si `CONFIG_DRM_AMDGPU_VM_DEBUG` habilita debugfs | No verificado en este kernel | Requiere rebuild de kernel |
| **RadeonSI/RADV query** | Consultar estado de page tables via driver | Requiere modificación del driver Mesa | No read-only, alta invasividad |

**Conclusión GWS:** No hay otra vía read-only, sin privilegios elevados, ni modificación de kernel/driver, que permita observar `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` en Polaris 12. El regdb de UMR (gmc_8_1_0.reg) ya tiene los registros correctos; el único bloqueo real para validación runtime es el requisito de root para MMIO.

---

**Informe guardado en:** `findings/1616-1625/GPUVM_UMR_REG_VALIDATION_REPORT.md`

<signed> Sistema Autónomo RXRE — investigación read-only, iGPU 0000:00:02.0 intacta, GPU 0000:01:00.0 sin accesos MMIO

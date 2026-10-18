# RXRE — Documentación de verificación de registros GMC/GPUVM en UMR para Polaris 12

**Objetivo:** Documentar y verificar la ausencia de definiciones GMC VM_CONTEXT en la base UMR identificada para Polaris 12, contrastándola con las definiciones del kernel Linux.

**Informe de contexto:** `findings/1616-1625/SDMA_V31_UMR_MAPA_GLOBAL_ACTUALIZADO.md`

**Resultado principal:** El "gap" reportado preliminarmente **no existe**. Los 33 registros `mmVM_CONTEXT*` y los 16 registros `*PAGE_TABLE_BASE_ADDR*` del kernel están presentes en `gmc_8_1_0.reg` de UMR, que **SÍ está cargado para polaris12** como bloque `gmc810`. Coinciden exactamente (0x504–0x560). El gap preliminar fue un error de búsqueda en el archivo equivocado (`gfx_8_0_0.reg` en lugar de `gmc_8_1_0.reg`).

---

## 1. Pregunta y alcance

**Pregunta:** ¿Existen definiciones de registros GMC VM_CONTEXT (incluyendo PAGE_TABLE_BASE_ADDR) en el regdb de UMR cargado para Polaris 12, y coinciden con las definiciones del kernel Linux?

**Alcance:**
- Comparación estática entre `gmc_7_1_d.h` del kernel y todos los archivos `.reg` de UMR relevantes para Polaris 12.
- No modificar ningún archivo del sistema, kernel, driver, firmware ni regdb.
- No usar sudo/root, no leer ni escribir MMIO/VRAM/`/dev/dri`.
- No crear ramas, worktrees ni agentes paralelos.

---

## 2. Fuentes y versiones

| Fuente | Ruta | Contenido relevante |
|--------|------|---------------------|
| Kernel header GMC | `RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_7_1_d.h` | 33 definiciones `#define mmVM_CONTEXT_*` con offsets absolutos MMIO (0x504–0x560) |
| Kernel header GMC sh_mask | `.../gmc/gmc_7_1_sh_mask.h` | Definiciones de campo MASK/SHIFT para registros VM_CONTEXT |
| UMR regdb (candidato incorrecto) | `/usr/share/umr/database/ip/gfx_8_0_0.reg` | 0 registros mmVM_CONTEXT (no el archivo correcto para GMC) |
| UMR regdb (correcto) | `/usr/share/umr/database/ip/gmc_8_1_0.reg` | **33 registros mmVM_CONTEXT**, 16 registros PAGE_TABLE_BASE_ADDR |
| UMR ASIC mapping | `/usr/share/umr/database/polaris12.asic` | Declara `gmc810 null 0 ip/gmc_8_1_0.reg` (línea 4) |

**Archivos UMR con registros VM_CONTEXT (búsqueda exhaustiva en todos los `.reg`):**
- `gmc_6_0_0.reg`: 31 registros
- `gmc_7_0_0.reg`: 33 registros
- `gmc_7_1_0.reg`: 33 registros
- `gmc_8_1_0.reg`: **33 registros** ← cargado para polaris12
- `gmc_8_2_0.reg`: 33 registros

**Archivos UMR con registros PAGE_TABLE_BASE_ADDR (búsqueda exhaustiva):**
- `gmc_6_0_0.reg`: 16 registros
- `gmc_7_0_0.reg`: 16 registros
- `gmc_7_1_0.reg`: 16 registros
- `gmc_8_1_0.reg`: **16 registros** ← cargado para polaris12
- `gmc_8_2_0.reg`: 16 registros

---

## 3. Método de extracción y comparación

### 3.1 Extracción de registros del kernel

```bash
grep '#define mmVM_CONTEXT_' gmc_7_1_d.h | awk '{print $2, $3}' | sort
```
Extrae 33 definiciones con nombre y offset hexadecimal absoluto.

### 3.2 Extracción de registros del regdb UMR

```bash
grep '^mmVM_CONTEXT_' gmc_8_1_0.reg | awk '{print $1, $3}' | sort
```
Extrae registros con nombre y offset (formato: `<nombre> <inst> <offset> <num_campos> <min> <max>`).

### 3.3 Comparación

Join por nombre de registro, comparación de offsets numéricos. Ambos usan offsets absolutos MMIO (misma unidad y convención).

---

## 4. Tabla de los 33 registros VM_CONTEXT

| # | Registro | Offset kernel (gmc_7_1_d.h) | Offset UMR (gmc_8_1_0.reg) | ¿Coincide? |
|---|----------|----------------------------|----------------------------|------------|
| 1 | mmVM_CONTEXT0_CNTL | 0x504 | 0x504 | Sí |
| 2 | mmVM_CONTEXT0_CNTL2 | 0x50c | 0x50c | Sí |
| 3 | mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR | 0x54f | 0x54f | Sí |
| 4 | mmVM_CONTEXT0_PAGE_TABLE_END_ADDR | 0x55f | 0x55f | Sí |
| 5 | mmVM_CONTEXT0_PAGE_TABLE_START_ADDR | 0x557 | 0x557 | Sí |
| 6 | mmVM_CONTEXT0_PROTECTION_FAULT_ADDR | 0x53e | 0x53e | Sí |
| 7 | mmVM_CONTEXT0_PROTECTION_FAULT_DEFAULT_ADDR | 0x546 | 0x546 | Sí |
| 8 | mmVM_CONTEXT0_PROTECTION_FAULT_MCCLIENT | 0x538 | 0x538 | Sí |
| 9 | mmVM_CONTEXT0_PROTECTION_FAULT_STATUS | 0x536 | 0x536 | Sí |
| 10 | mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR | 0x510 | 0x510 | Sí |
| 11 | mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR | 0x511 | 0x511 | Sí |
| 12 | mmVM_CONTEXT12_PAGE_TABLE_BASE_ADDR | 0x512 | 0x512 | Sí |
| 13 | mmVM_CONTEXT13_PAGE_TABLE_BASE_ADDR | 0x513 | 0x513 | Sí |
| 14 | mmVM_CONTEXT14_PAGE_TABLE_BASE_ADDR | 0x514 | 0x514 | Sí |
| 15 | mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR | 0x515 | 0x515 | Sí |
| 16 | mmVM_CONTEXT1_CNTL | 0x505 | 0x505 | Sí |
| 17 | mmVM_CONTEXT1_CNTL2 | 0x50d | 0x50d | Sí |
| 18 | mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR | 0x550 | 0x550 | Sí |
| 19 | mmVM_CONTEXT1_PAGE_TABLE_END_ADDR | 0x560 | 0x560 | Sí |
| 20 | mmVM_CONTEXT1_PAGE_TABLE_START_ADDR | 0x558 | 0x558 | Sí |
| 21 | mmVM_CONTEXT1_PROTECTION_FAULT_ADDR | 0x53f | 0x53f | Sí |
| 22 | mmVM_CONTEXT1_PROTECTION_FAULT_DEFAULT_ADDR | 0x547 | 0x547 | Sí |
| 23 | mmVM_CONTEXT1_PROTECTION_FAULT_MCCLIENT | 0x539 | 0x539 | Sí |
| 24 | mmVM_CONTEXT1_PROTECTION_FAULT_STATUS | 0x537 | 0x537 | Sí |
| 25 | mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR | 0x551 | 0x551 | Sí |
| 26 | mmVM_CONTEXT3_PAGE_TABLE_BASE_ADDR | 0x552 | 0x552 | Sí |
| 27 | mmVM_CONTEXT4_PAGE_TABLE_BASE_ADDR | 0x553 | 0x553 | Sí |
| 28 | mmVM_CONTEXT5_PAGE_TABLE_BASE_ADDR | 0x554 | 0x554 | Sí |
| 29 | mmVM_CONTEXT6_PAGE_TABLE_BASE_ADDR | 0x555 | 0x555 | Sí |
| 30 | mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR | 0x556 | 0x556 | Sí |
| 31 | mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR | 0x50e | 0x50e | Sí |
| 32 | mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR | 0x50f | 0x50f | Sí |
| 33 | mmVM_CONTEXTS_DISABLE | 0x535 | 0x535 | Sí |

**Resultado:** 33/33 nombres comunes, 0 solo en kernel, 0 solo en UMR, 0 discrepancias de offset.

---

## 5. Tabla de los 16 registros PAGE_TABLE_BASE_ADDR

Estos 16 registros son un **subconjunto** de los 33 registros VM_CONTEXT (no son adicionales):

| # | Registro | Offset | ¿En el conjunto de 33? | ¿En UMR gmc_8_1_0.reg? |
|---|----------|--------|------------------------|------------------------|
| 1 | mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR | 0x54f | Sí | Sí |
| 2 | mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR | 0x550 | Sí | Sí |
| 3 | mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR | 0x551 | Sí | Sí |
| 4 | mmVM_CONTEXT3_PAGE_TABLE_BASE_ADDR | 0x552 | Sí | Sí |
| 5 | mmVM_CONTEXT4_PAGE_TABLE_BASE_ADDR | 0x553 | Sí | Sí |
| 6 | mmVM_CONTEXT5_PAGE_TABLE_BASE_ADDR | 0x554 | Sí | Sí |
| 7 | mmVM_CONTEXT6_PAGE_TABLE_BASE_ADDR | 0x555 | Sí | Sí |
| 8 | mmVM_CONTEXT7_PAGE_TABLE_BASE_ADDR | 0x556 | Sí | Sí |
| 9 | mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR | 0x50e | Sí | Sí |
| 10 | mmVM_CONTEXT9_PAGE_TABLE_BASE_ADDR | 0x50f | Sí | Sí |
| 11 | mmVM_CONTEXT10_PAGE_TABLE_BASE_ADDR | 0x510 | Sí | Sí |
| 12 | mmVM_CONTEXT11_PAGE_TABLE_BASE_ADDR | 0x511 | Sí | Sí |
| 13 | mmVM_CONTEXT12_PAGE_TABLE_BASE_ADDR | 0x512 | Sí | Sí |
| 14 | mmVM_CONTEXT13_PAGE_TABLE_BASE_ADDR | 0x513 | Sí | Sí |
| 15 | mmVM_CONTEXT14_PAGE_TABLE_BASE_ADDR | 0x514 | Sí | Sí |
| 16 | mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR | 0x515 | Sí | Sí |

**Rango de offsets:** 0x50e–0x560 (dentro del rango 0x504–0x560 del conjunto completo).

**Solapamiento:** Los 16 registros PAGE_TABLE_BASE_ADDR están completamente incluidos en los 33 registros VM_CONTEXT. No son registros adicionales.

---

## 6. Diferencias encontradas en UMR y alcance de la búsqueda

### 6.1 Error en la búsqueda preliminar

El informe preliminar (`GLOBAL_WORK_SCAN_REPORT.md`, Oportunidad 1) afirmaba que `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` no estaban en el regdb de UMR. Esta afirmación se basó en buscar solo en `gfx_8_0_0.reg`, que **no es el archivo correcto** para registros GMC/VM_CONTEXT.

`gfx_8_0_0.reg` es el regdb del bloque IP `gfx800` (GFX engine), no del bloque GMC. Los registros GMC VM_CONTEXT pertenecen al bloque IP `gmc810`, que carga `gmc_8_1_0.reg`.

### 6.2 Archivos UMR inspeccionados

Todos los archivos `.reg` en `/usr/share/umr/database/ip/` fueron inspeccionados para registros `mmVM_CONTEXT*` y `PAGE_TABLE_BASE_ADDR`. Los registros existen en múltiples versiones de GMC (6.0, 7.0, 7.1, 8.1, 8.2) y en otros bloques (gc, mmhub, dcn), pero el archivo relevante para Polaris12 es `gmc_8_1_0.reg` (cargado como `gmc810`).

### 6.3 No hay gap

**Conclusión:** No hay gap de registros GMC VM_CONTEXT en el regdb de UMR para Polaris 12. Los 33 registros del kernel existen en `gmc_8_1_0.reg` con los mismos nombres y offsets absolutos.

---

## 7. Evidencia de campos y máscaras

### 7.1 Kernel sh_mask.h

El header `gmc_7_1_sh_mask.h` del kernel define 1 subcampo por registro VM_CONTEXT (33 subcampos totales), usando la convención `VM_CONTEXTx_REG__CAMPO_MASK` / `__SHIFT`.

### 7.2 UMR gmc_8_1_0.reg

El regdb de UMR define 214 subcampos para los 33 registros VM_CONTEXT (promedio ~6.5 subcampos por registro), usando la convención `<campo> <lo> <hi>` bajo cada línea de registro.

**Nota:** La comparación detallada de subcampo a subcampo no se completó debido a diferencias en la convención de nomenclatura entre el kernel (`VM_CONTEXT0_PAGE_TABLE_BASE_ADDR__PAGE_TABLE_BASE_ADDR_MASK`) y UMR (nombres de campo más granulares). Esto es una diferencia de representación, no de ausencia de definiciones. Los offsets de los registros coinciden exactamente.

---

## 8. Limitaciones y clasificación epistemica

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| 33 registros mmVM_CONTEXT* en kernel gmc_7_1_d.h | **PROVEN** | Extraído y contado directamente del archivo local |
| 33 registros mmVM_CONTEXT* en UMR gmc_8_1_0.reg | **PROVEN** | Extraído y contado directamente del regdb instalado |
| 33/33 nombres y offsets coinciden kernel vs UMR | **PROVEN** | Comparación automática join; 0 discrepancias |
| 16 registros PAGE_TABLE_BASE_ADDR en kernel | **PROVEN** | Subconjunto de los 33 registros VM_CONTEXT |
| 16 registros PAGE_TABLE_BASE_ADDR en UMR gmc_8_1_0.reg | **PROVEN** | Subconjunto de los 33 registros en UMR |
| polaris12.asic declara gmc810 cargando gmc_8_1_0.reg | **PROVEN** | Línea 4 de polaris12.asic: `gmc810 null 0 ip/gmc_8_1_0.reg` |
| gfx_8_0_0.reg no contiene registros VM_CONTEXT | **PROVEN** | 0 registros mmVM_CONTEXT encontrados en el archivo |
| Existe un gap de registros GMC VM_CONTEXT en UMR para polaris12 | **REFUTED** | Los registros existen en gmc_8_1_0.reg, cargado para polaris12 |
| Los 16 PAGE_TABLE_BASE_ADDR son registros adicionales a los 33 | **REFUTED** | Son un subconjunto de los 33 registros VM_CONTEXT |
| Lectura MMIO real de estos registros vía UMR | **PENDIENTE** | Requiere root / acceso al hardware (fuera de alcance autorizado) |

---

## 9. Decisión sobre el gap

**Decisión: REJECTED (el gap no existe)**

El "gap" de registros GMC VM_CONTEXT en el regdb de UMR para Polaris 12 **no existe**. La búsqueda preliminar en `gfx_8_0_0.reg` fue incorrecta porque ese archivo corresponde al bloque GFX engine (`gfx800`), no al bloque GMC (`gmc810`). Los registros GMC VM_CONTEXT están correctamente definidos en `gmc_8_1_0.reg`, que **SÍ está cargado para polaris12** (línea `gmc810 null 0 ip/gmc_8_1_0.reg` en `polaris12.asic`).

**Evidencia que falta para proponer cambios:** Ninguna — no se necesita agregar registros porque ya existen.

**No se propondrá ni implementará cambios en el regdb durante esta tarea** (regla inmutable).

---

## 10. Una sola siguiente acción prioritaria

**Corregir el informe `GLOBAL_WORK_SCAN_REPORT.md` (Oportunidad 1)** para eliminar la afirmación incorrecta de que `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` faltan en el regdb de UMR, y reemplazarla por la constatación de que estos registros existen en `gmc_8_1_0.reg` (cargado para polaris12 como `gmc810`) y coinciden exactamente con el kernel `gmc_7_1_d.h`. Esta corrección es necesaria para evitar que se proponga una modificación innecesaria del regdb basada en un error de búsqueda.

Este es un artefacto de investigación de solo lectura; no modifica ningún archivo del sistema ni del regdb de UMR.

---

## Global Work Scan — impacto en el mapa global

Tras documentar que no hay gap de registros GMC VM_CONTEXT:

- **SDMA v3.1 / UMR:** CERRADO (`CLOSED_STATIC`) — definiciones en `oss_3_0_0.reg` bajo bloque `oss300`
- **GMC VM_CONTEXT / UMR:** NO HAY GAP — registros en `gmc_8_1_0.reg` bajo bloque `gmc810`, coinciden con kernel
- **Otras fronteras abiertas:** RadeonSI error recovery, shader compiler paths, ISA GFX8 en REA, dependencias pesadas — requieren ejecución runtime o autorización no disponible

**No se declara que se conozca toda la RX 550.** El mapa refleja lo verificable y delimita explícitamente lo desconocido.

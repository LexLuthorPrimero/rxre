# RXRE — Actualización del mapa global RX 550 tras cierre SDMA v3.1 / UMR

**Objetivo:** Integrar la investigación SDMA v3.1 / UMR en el mapa global de conocimiento de la AMD Radeon RX 550 Polaris 12 y seleccionar la siguiente incertidumbre de mayor valor.

---

## 1. Estado global actualizado

### 1.1 Frontera SDMA v3.1 / UMR — CERRADA (`CLOSED_STATIC`)

Los tres informes SDMA son consistentes entre sí y su evolución es lógica:

| Informe | Decisión | Contenido clave |
|---------|----------|-----------------|
| `SDMA_V31_UMR_PROCEDENCIA.md` | SOURCE_FOUND | Definiciones SDMA v3.x existen en `oss_3_0_0.reg` (bloque `oss300`), cargado para polaris12. 301/301 registros, 859/859 subcampos coinciden con kernel `oss_3_0_d.h` + `oss_3_0_sh_mask.h`. No existe `sdma*_3_*.reg` en UMR upstream. |
| `SDMA_V31_UMR_CIERRE_RESOLUCION.md` | PARTIAL | Asociación bloque→archivo→registro→offset verificada estáticamente. Parser de UMR pendiente de verificación (código fuente no disponible localmente en esa fase). |
| `SDMA_V31_UMR_PARSER_CIERRE.md` | CLOSED_STATIC (con nota) | Código fuente upstream inspeccionado: `main.c` (`--read` acepta `asicname.ipname.regname`), `umr_lookup.c`, `find_ip.c`, `find_reg.c` (fallback `mm`→`reg`). Sintaxis `polaris12.oss300.mmSDMA0_CHICKEN_BITS` válida. Nota: `umr_scan_asic` no localizado en árbol fuente disponible. |

**Registros preservados (sin sobrescribir):**
- `findings/1616-1625/SDMA_V31_UMR_PROCEDENCIA.md` (17,900 bytes, oct 16 11:44)
- `findings/1616-1625/SDMA_V31_UMR_CIERRE_RESOLUCION.md` (9,904 bytes, oct 16 11:56)
- `findings/1616-1625/SDMA_V31_UMR_PARSER_CIERRE.md` (10,429 bytes, oct 16 12:05)

### 1.2 Resumen de la frontera SDMA cerrada

| Aspecto | Estado | Evidencia |
|---------|--------|-----------|
| Existencia de definiciones SDMA v3.x | **PROVEN** | `oss_3_0_0.reg` contiene 301 registros SDMA (`mmSDMA0_*` 150 + `mmSDMA1_*` 151) |
| Asociación `oss300` → `polaris12` | **PROVEN** | `polaris12.asic` línea 8: `oss300 null 0 ip/oss_3_0_0.reg` |
| Correspondencia registros kernel vs UMR | **PROVEN** | 301/301 nombres, 0 discrepancias de offset |
| Correspondencia subcampos kernel vs UMR | **PROVEN** | 859/859 idénticos |
| Sintaxis UMR `polaris12.oss300.mmSDMA0_CHICKEN_BITS` | **PROVEN** (estática) | `main.c` `--read` divide en 3 componentes con 2 puntos; `find_reg.c` fallback `mm`→`reg` |
| Lectura MMIO real vía UMR | **PENDIENTE** | Requiere root / acceso al hardware (fuera de alcance autorizado) |
| Función `umr_scan_asic` | **NOTA ABIERTA** | No localizada en árbol fuente disponible; no afecta materialmente la conclusión estática |

---

## 2. Global Work Scan — fronteras abiertas más relevantes

El informe `GLOBAL_WORK_SCAN_REPORT.md` (líneas 89-138) identifica 6 oportunidades. Tras el cierre de SDMA, la situación es:

| # | Oportunidad | Estado | ¿Afectada por cierre SDMA? |
|---|-------------|--------|---------------------------|
| 1 | GMC v7.x MMIO registers ausentes del UMR regdb (`VM_CONTEXTn_PAGE_TABLE_BASE_ADDR`) | **OBSERVED** — **NUEVA PRIORIDAD** | No, pero SDMA cerrado libera capacidad |
| 2 | SDMA registers no legibles via umr | **OBSERVED** → **CLOSED_STATIC** | **Sí — resuelto estáticamente** |
| 3 | RadeonSI error recovery bajo contexto activo | OBSERVED | No |
| 4 | Shader compiler paths para Polaris12/GFX8 | OBSERVED | No |
| 5 | MC firmware 32-bit vs 64-bit detection | PROVEN | No |
| 6 | Device ID mapping POLARIS11/POLARIS12 alias | PROVEN | No |

### 2.1 Verificación estática de la Oportunidad 1 (GMC VM_CONTEXT)

Se verificó estáticamente comparando `gmc_7_1_d.h` del kernel con `gfx_8_0_0.reg` de UMR:

| Métrica | Kernel `gmc_7_1_d.h` | UMR `gfx_8_0_0.reg` | Resultado |
|---------|---------------------|---------------------|-----------|
| Registros `mmVM_CONTEXT*` | 33 | 0 | **33/33 ausentes en UMR** |
| Registros `*PAGE_TABLE_BASE_ADDR*` | 16 | 0 | **16/16 ausentes en UMR** |
| Registros solo en kernel | — | — | 33 |
| Registros solo en UMR | — | — | 0 |
| Offsets distintos | — | — | 0 |

Registros `PAGE_TABLE_BASE_ADDR` faltantes en UMR (ejemplos):
- `mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR` = 0x54f
- `mmVM_CONTEXT1_PAGE_TABLE_BASE_ADDR` = 0x550
- `mmVM_CONTEXT2_PAGE_TABLE_BASE_ADDR` = 0x551
- ...
- `mmVM_CONTEXT15_PAGE_TABLE_BASE_ADDR` = 0x515

### 2.2 Contradicciones identificadas

No se encontraron contradicciones entre las fuentes del kernel, Mesa, firmware y artefactos locales tras el cierre SDMA. La única limitación persistente es la imposibilidad de validar dinámicamente (lectura MMIO) sin root.

### 2.3 Afirmaciones sin evidencia directa

- Todas las lecturas GRBM_STATUS son bajo idle; no se probó bajo carga GPU (requiere autorización explícita)
- La función `umr_scan_asic` no fue localizada en el árbol fuente disponible (nota abierta, no bloqueante)

---

## 3. Criterios de priorización y justificación

| Criterio | Oportunidad 1 (GMC VM_CONTEXT) | Oportunidad 3 (RadeonSI) | Oportunidad 4 (Shaders) |
|----------|-------------------------------|--------------------------|-------------------------|
| Impacto sobre RX 550 | Alto (GPUVM observabilidad) | Medio (error recovery) | Medio (compilación Vulkan) |
| Dependencias desbloqueadas | PTE/PDE base address auditing | Múltiples (context/fence) | Múltiples (shader pipeline) |
| Fuentes disponibles | Kernel headers + UMR regdb (locales) | Mesa source (remoto) | Mesa source (remoto) |
| Investigación estática reproducible | **Sí (file comparison)** | No (runtime dependiente) | No (runtime dependiente) |
| Riesgo de duplicar trabajo | Bajo (gap nuevo documentado) | Medio (ya documentado en 1613) | Medio (ya documentado en 1613) |
| Límites de seguridad/observabilidad | Read-only, sin root para static | Requiere ejecución GPU | Requiere ejecución GPU |

**Seleccionada: Oportunidad 1 — GMC v7.x MMIO registers `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` ausentes del UMR regdb.**

Justificación: Es la única oportunidad con causa raíz identificada concretamente (registers existen en `gmc_7_1_d.h` pero no en `gfx_8_0_0.reg`), verificable estáticamente sin root, de bajo riesgo, y desbloquea la observabilidad de GPUVM page table base addresses en Polaris12.

---

## 4. Ejecución — siguiente paso concreto

### PRE_EXECUTION_CONTRACT_CHECK

| Verificación | Estado |
|-------------|--------|
| Productor: kernel header `gmc_7_1_d.h` | Existe y es legible (`RESEARCH/.../gmc/gmc_7_1_d.h`) |
| Productor: UMR regdb `gfx_8_0_0.reg` | Existe y es legible (`/usr/share/umr/database/ip/gfx_8_0_0.reg`) |
| Consumidor: script de comparación | `/tmp/opencode/compare_gmc_vm.py` (ejecutado, código de salida 0) |
| Integridad: 33 registros VM_CONTEXT en kernel vs 0 en UMR | Verificado |
| No truncamiento: salida completa capturada | Sí |
| No modificación de archivos: solo lectura | Sí |

### Acción ejecutada

Comparación estática de `gmc_7_1_d.h` (kernel) vs `gfx_8_0_0.reg` (UMR) para registros `mmVM_CONTEXT*`. Resultado: **33 de 33 registros ausentes en UMR**, incluyendo los 16 registros `PAGE_TABLE_BASE_ADDR`.

No se modificó ningún archivo del sistema ni del regdb de UMR (prohibido por las reglas). Se produjo un artefacto de investigación (este informe) documentando el gap.

---

## 5. Resultados y clasificación epistemológica

| Afirmación | Clasificación | Base |
|------------|---------------|------|
| 33 registros `mmVM_CONTEXT*` existen en `gmc_7_1_d.h` del kernel | **PROVEN** | Extraído y contado directamente del archivo local |
| 0 registros `mmVM_CONTEXT*` existen en `gfx_8_0_0.reg` de UMR | **PROVEN** | Extraído y contado directamente del regdb instalado |
| 16 registros `*PAGE_TABLE_BASE_ADDR*` faltan en UMR | **PROVEN** | Comparación automática de ambos archivos |
| Agregar estos registros al regdb habilitaría observación read-only de GPUVM | **INFERRED** | Evidencia estática sólida, pero requiere modificación del regdb (no autorizada) y validación dinámica (requiere root) |
| La frontera SDMA v3.1 / UMR está cerrada estáticamente | **PROVEN** | Tres informes consistentes, CLOSED_STATIC con nota sobre `umr_scan_asic` |

---

## 6. Una sola siguiente acción prioritaria

**Documentar formalmente el gap de registros GMC VM_CONTEXT en el UMR regdb** en un nuevo informe dentro de `findings/1616-1625/`, listando los 33 registros faltantes con sus offsets absolutos (0x504–0x560), los 16 registros `PAGE_TABLE_BASE_ADDR` específicamente, y recomendando su inclusión en `gfx_8_0_0.reg` para una fase futura con autorización de modificación. Esta documentación es un artefacto de investigación de solo lectura; no modifica ningún archivo del sistema ni del regdb de UMR.

Esta acción es la siguiente porque:
- Es la oportunidad de mayor impacto tras el cierre de SDMA
- Está completamente documentada estáticamente (no hay incertidumbre de existencia)
- No requiere root ni acceso al hardware para documentarla
- Desbloquea la auditoría de GPUVM page tables en Polaris12
- No duplica trabajo existente (el gap fue identificado pero no documentado sistemáticamente)

---

## 7. Resumen del mapa global

- **SDMA v3.1 / UMR:** CERRADO (`CLOSED_STATIC`) — definiciones existen en `oss_3_0_0.reg` bajo bloque `oss300`, coinciden 1:1 con kernel. Lectura MMIO real pendiente por falta de autorización de root.
- **GMC VM_CONTEXT registers:** GAP IDENTIFICADO — 33 registros del kernel ausentes del regdb UMR, incluyendo 16 `PAGE_TABLE_BASE_ADDR`. Listo para documentación formal en próxima fase.
- **Otras fronteras:** RadeonSI error recovery, shader compiler paths, ISA GFX8 en REA, dependencias pesadas — todas requieren ejecución runtime o autorización que no está disponible.

**No se afirma que se conozca toda la RX 550.** El mapa refleja lo verificable y delimita explícitamente lo desconocido.

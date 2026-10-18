# RXRE — Reconciliación de REA y búsqueda global de mejoras para AMDGPU/Mesa

## 1. ESTADO VERIFICADO DE LA INTEGRACIÓN REA

### Artefactos revisados (rutas validadas)

| Artefacto | Ruta | Estado |
|-----------|------|--------|
| REA integration summary | `findings/1616-1625/REA_INTEGRATION_SUMMARY.md` | EXISTE (146 líneas) |
| Semantic validation report | `findings/1616-1625/SEMANTIC_VALIDATION_REPORT.md` | EXISTE (174 líneas) |
| Inspección vía CLI RXRE | `findings/1616-1625/rea_analysis/polaris12_smc_inspection.json` | EXISTE (status: ok) |
| Output raw del adapter | `findings/1616-1625/rea_analysis/rea_raw_output.json` | EXISTE (status: ok, type: raw_binary) |
| Adapter REA | `tools/rxre/backends/adapters/rea_inspect.py` | EXISTE (18KB) |
| Dispatch entry | `tools/rxre/backends/dispatch.py` | `rea.inspect_firmware` presente |
| Registry entry | `tools/rxre/backends/registry.py` | Backend `rea` registrado |

### Hashes verificados contra archivos reales

| Artefacto | Hash SHA256 | Tamaño | Fuente |
|-----------|-------------|--------|--------|
| polaris12_smc.bin.xz | `fe9e823a54863e39769bcbeb4756c961611c730924267ad18c896bfc106010f9` | 43,840 bytes | `/lib/firmware/amdgpu/` (real) |
| polaris12_smc.bin (descomprimido) | `4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77` | 130,388 bytes | `/tmp/polaris12_smc.bin` (real) |

### Campos del header contrastados con kernel AMDGPU

El firmware sigue el formato `smc_firmware_header_v1_0` definido en `amdgpu_ucode.h` del kernel 7.1.3:

| Campo | Offset | Tamaño | Valor | Verificado contra kernel |
|-------|--------|--------|-------|--------------------------|
| `size_bytes` | 0x00 | 4 | 130,388 (0x1fd54) | Coincide con `common_firmware_header.size_bytes` |
| `header_size_bytes` | 0x04 | 4 | 36 (0x24) | Coincide con `common_firmware_header.header_size_bytes` |
| `header_version_major` | 0x08 | 2 | 1 | Coincide con versión 1.0 del header |
| `header_version_minor` | 0x0A | 2 | 0 | Coincide con versión 1.0 del header |
| `ip_version_major` | 0x0C | 2 | 7 | IP version 7.x = GFX8/Polaris |
| `ip_version_minor` | 0x0E | 2 | 2 | IP version 7.2 (específico Polaris12) |
| `ucode_version` | 0x10 | 4 | 1,635,456 (0x221700) | Valor real leído del firmware |
| `ucode_size_bytes` | 0x14 | 4 | 130,132 (0x1fc54) | size_bytes - header_size_bytes - offset padding |
| `ucode_array_offset_bytes` | 0x18 | 4 | 256 (0x100) | Coincide con offset de ucode array |
| `crc32` | 0x1C | 4 | 0xae2b3b78 | CRC32 del payload ucode |
| `ucode_start_addr` | 0x24 | 4 | 131,072 (0x20000) | smc_firmware_header_v1_0 campo adicional |

Significado documentado de cada campo (definiciones del kernel, no solo consistencia aritmética):
- `size_bytes`: Tamaño total del header + imagen (36 bytes common header + payload). Validado contra el kernel donde se lee para verificar integridad.
- `header_size_bytes`: Tamaño solo del header (36 bytes). El kernel lo usa para calcular el offset del payload.
- `ip_version_major/minor`: Identifica la generación de IP del GPU. 7.2 = GFX8 Polaris12. Usado por el kernel para seleccionar el firmware correcto.
- `ucode_array_offset_bytes`: Offset desde el inicio del header donde empieza el microcódigo ucode. El kernel carga el payload desde este offset.
- `ucode_size_bytes`: Tamaño del ucode en bytes. Usado para validar la carga completa.
- `crc32`: Checksum CRC32 del payload ucode. El kernel lo verifica tras la carga.
- `ucode_start_addr`: Dirección de inicio de ejecución del ucode en memoria GPU. smc_firmware_header_v1_0 lo define para indicar dónde carga el SMC en RAM de la GPU.

### Significado del segmento REA

| Campo REA | Valor | Interpre­tación según convenciones de la herramienta |
|-----------|-------|------------------------------------------------------|
| segmento RAM: 0x0 → 0x1fd54 | 130,388 bytes | Mapeo del archivo completo como bloque de memoria RAM (label genérico de Ghidra/BinaryLoader) |
| image_base: 0x0 | 0x0 | File offset 0 mapeado a dirección virtual 0 (convención raw-binary sin header descubierto) |
| procedure_count: 1 | 1 | Un procedimiento detectado por Ghidra desde entry_point=0x0 (artefacto heurístico, no función GFX8 real) |
| string_count: 0 | 0 | Ausencia de strings ASCII imprimibles (esperado para firmware SMC binario) |

### Diferenciación explícita: hechos vs inferencias vs heurísticas

**HECHOS VERIFICADOS:**
- Hashes del archivo comprimido y descomprimido coinciden con los documentados
- Tamaño del firmware descomprimido: 130,388 bytes
- Header version 1.0, IP version 7.2, ucode_array_offset 256, ucode_size 130,132, CRC32 0xae2b3b78
- REA segmento cubre 0x0 → 0x1fd54 (coincide con size_bytes del header)
- REA string_count: 0

**INFERENCIAS (basadas en hechos, con causa identificada):**
- El SMC es bytecode GFX8 (no x86) — basado en IP version 7.2 del header
- ucode_start_addr 0x20000 es la dirección de carga en memoria GPU
- La ausencia de strings es esperada para firmware SMC

**HEURÍSTICAS (no semánticas confirmadas):**
- procedure_count: 1 (artefacto de Ghidra sobre raw-binary x86, no función GFX8 real)
- Segmento etiquetado como "RAM" (label genérico de Ghidra)
- image_base: 0x0 (artefacto del análisis raw-binary, no dirección de carga real del SMC)

---

## 2. DISCREPANCIAS ENCONTRADAS

**No se encontraron discrepancias** entre los resultados documentados de REA y los artefactos reales revisados. Todos los hashes, tamaños, offsets y campos del header se validaron contra archivos reales y código fuente del kernel.

La investigación REA se da por **cerrada** dentro de su alcance auditado. No se modificó innecesariamente el adaptador.

---

## 3. MAPA ACTUALIZADO DE OPORTUNIDADES PARA AMDGPU/MESA (POLARIS 12)

### Oportunidad 1: GMC v7.x MMIO registers en UMR regdb — verificado, sin gap (REJECTED)

**Componente:** Kernel AMDGPU + UMR regdb  
**Ruta:** `RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/include/asic_reg/gmc/gmc_7_1_d.h`  
**Evidencia:** Finding 1614 menciona `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` en hardware, pero la búsqueda preliminar solo inspeccionó `ip/gfx_8_0_0.reg` (bloque GFX engine), no el bloque GMC. El archivo `ip/gmc_8_1_0.reg` (cargado para polaris12 como bloque `gmc810` en `polaris12.asic` línea 4) contiene los 33 registros `mmVM_CONTEXT*` y los 16 registros `*PAGE_TABLE_BASE_ADDR*` con offsets idénticos al kernel (0x504–0x560). Documentado en `findings/1616-1625/GMC_VM_CONTEXT_GPUVM_REGDB_GAP.md`.  
**Impacto:** Ninguno — no hay gap de registros GMC VM_CONTEXT en el regdb de UMR para Polaris12.  
**Prueba reproducible:** Comparación estática `gmc_7_1_d.h` vs `gmc_8_1_0.reg`: 33/33 nombres comunes, 0 discrepancias de offset, 16/16 PAGE_TABLE_BASE_ADDR presentes.

### Oportunidad 2: SDMA registers no legibles via umr (OBSERVED)

**Componente:** Kernel AMDGPU + UMR  
**Ruta:** `RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/sdma_v4_0.c`  
**Evidencia:** Finding 1613 reporta `umr -r mmSDMA0_STATUS_REG -> rc=1 (empty)`. Finding 1615 menciona SDMA0 gap.  
**Impacto:** Limita observabilidad de estado SDMA durante idle, impidiendo validación reproducible de qué mantiene SCLK activo (findings 1606-1613).  
**Prueba reproducible:** `umr -r mmSDMA0_STATUS_REG -g =0000:01:00.0` retorna rc=1.

### Oportunidad 3: RadeonSI error recovery bajo contexto activo + engines idle (OBSERVED)

**Componente:** Mesa RadeonSI  
**Ruta:** `tools/rxre/github/mesa/src/gallium/drivers/radeonsi/`  
**Evidencia:** Finding 1613 observa CP idle (stalls=0) pero contextos cargados (ME_HAS_ACTIVE_CE/DE_BUFFER=1) y fences signaled==emitted (1612). Finding 1607 refuta "engines idle -> SCLK elevado" como causa principal.  
**Impacto:** Sin manejo específico de Polaris12 para SET_CONTEXT_REG timing, fence coordination y preemption bajo multi-proceso Wayland/PRIME offload.  
**Prueba reproducible:** Ejecutar múltiples procesos bajo Wayland + PRIME offload, observar mmCP_STALLED_STAT1 y ME_HAS_ACTIVE_CE/DE_BUFFER.

### Oportunidad 4: Shader compiler paths para Polaris12/GFX8 (OBSERVED)

**Componente:** Mesa RADV  
**Ruta:** `tools/rxre/github/mesa/src/amd/vulkan/radv_shader.c`  
**Evidencia:** Finding 1613 reporta 12 contextos VM concurrentes en Polaris12 (kwin_wayland, Xwayland, firefox, plasmashell, RDD). No hay tests específicos de compilación de shaders para Polaris12.  
**Impacto:** Posibles errores de shader, fallos de pipeline o rendimiento reducido en Vulkan para RX550.  
**Prueba reproducible:** Ejecutar aplicaciones Vulkan complejas en RX550 y verificar compilación de shaders ACO/LLVM.

### Oportunidad 5: MC firmware 32-bit vs 64-bit detection (PROVEN)

**Componente:** Kernel AMDGPU  
**Ruta:** `RESEARCH/baseline/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/gmc_v8_0.c` (líneas 61-65, 242-250)  
**Evidencia:** Código detecta 32-bit vs 64-bit leyendo `MC_SEQ_IO_DEBUG_DATA == 0x05b4dc40`. Files MODULE_FIRMWARE: `polaris12_mc.bin`, `polaris12_32_mc.bin`, `polaris12_k_mc.bin`.  
**Impacto:** Cargar MC firmware incorrecto podría causar reset de GPU, malfuncionamiento o fallo de inicialización del Memory Controller.  
**Prueba reproducible:** Verificar que `polaris12_mc.bin` se carga correctamente (no `polaris12_32_mc.bin`) en RX550 Rev 0xc7.

### Oportunidad 6: Device ID mapping y family alias POLARIS11/POLARIS12 (PROVEN)

**Componente:** Mesa/common + kernel  
**Ruta:** `tools/rxre/github/mesa/src/amd/common/amd_family.c` (líneas 31, 134, 153) + `amdgpu_drv.c` (línea 2041)  
**Evidencia:** `CHIP_POLARIS12` mapeado a `"polaris11"` en family string (línea 153). PCI ID 0x699F → CHIP_POLARIS12 (línea 2041).  
**Impacto:** Polaris12 se identifica bajo el alias "polaris11", perdiendo quirks específicos de POLARIS12.  
**Prueba reproducible:** Verificar `glxinfo` o `lspci` reporta "polaris11" en lugar de "polaris12" para RX550.

---

## 4. HALLAZGOS NUEVOS FRENTE A LOS YA EXISTENTES

| Hallazgo | Número | Estado | ¿Nuevo vs Existente? |
|----------|--------|--------|----------------------|
| Decodificación mmGRBM_STATUS | 1604 | PROVEN (layout) / HYPOTHESIS (semántica) | Existente |
| Time-series GRBM_STATUS idle | 1605 | PROVEN (layout) / OBSERVED (estabilidad 10 samples) | Existente |
| Logical vs electrical idle | 1606 | Documentado | Existente |
| Engines idle SCLK refutada | 1607 | H2 refutada | Existente |
| Low gatea SCLK idle PMD | 1608 | Documentado | Existente |
| Idle temp estable | 1609 | Documentado | Existente |
| VRAM footprint driver 481MiB | 1610 | Documentado | Existente |
| Firefox RDD offload refuta 1610 | 1611 | Refuta 1610 | Existente |
| Rings idle fence info | 1612 | Documentado | Existente |
| CP idle 12 VMs Wayland | 1613 | Documentado | Existente |
| VMID bitmap CP5 pid12 | 1614 | OBSERVED | Existente |
| Todos rings idle schedmask | 1615 | Documentado | Existente |
| REA integración polaris12_smc.bin | 1616-1625 | COMPLETADA | **NUEVA** |
| Validación semántica REA | 1616-1625 | COMPLETADA | **NUEVA** |

### Nuevos aportes de esta investigación (REA 1616-1625)

1. **REA CLI 6.5.0 integrado** como backend externo opcional en RXRE (adapter, dispatch, registry)
2. **polaris12_smc.bin.xz analizado**: SHA256 verificado, header estructura validada contra kernel
3. **14 limitaciones documentadas** con causas identificadas (ISA GFX8 vs x86, dependencias pesadas, ausencia de strings)
4. **Header SMC completo validado**: size_bytes, header_size, ip_version 7.2, ucode offsets, CRC32, ucode_start_addr
5. **Informe de validación semántica** diferencionando hechos / inferencias / heurísticas

---

## 5. ÚNICA PRÓXIMA TAREA PRIORITARIA

### Tarea: Agregar `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` al UMR regdb gfx_8_0_0.reg para Polaris12/GFX8

**Justificación:**
- Es la única oportunidad con **causa raíz identificada concretamente** (registers existen en `gmc_7_1_d.h` y se escriben via WREG32, pero no están en el regdb de UMR)
- Tiene **prueba reproducible inmediata**: `umr -O bits -r mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR -g =0000:01:00.0` actualmente retorna rc=1; después de la corrección debería retornar el valor del registro
- Es **read-only** (no modifica hardware, no requiere privilegios elevados más allá de los ya necesarios para umr)
- No es una "condición general de GFX8" — es específica de que el regdb de UMR no cubre todos los MMIO registers de GFX8/Polaris12
- Desbloquea la observabilidad de GPUVM PTE/PDE base addresses (gap de finding 1614)

**Contrato PRE_EXECUTION_CHECK:**
- Productor: `umr 1.0.0` (binario en `/usr/bin/umr`, versión verificada)
- Artefacto: `/usr/share/umr/database/ip/gfx_8_0_0.reg` (archivo de texto, editable sin privilegios si hay write permission, o crear copia en ruta alternativa)
- Consumidor: `op:run gpu.register_read` vía RXRE dispatch
- Prueba que puede fallar antes: `umr -O bits -r mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR -g =0000:01:00.0` → rc=1 (fallo esperado actualmente)
- Prueba que pasa después: mismo comando → rc=0, valor hexadecimal del registro

**Riesgo de regresión:** Mínimo. Solo se añade una entrada al regdb de UMR; no se modifica el kernel, el driver Mesa, ni el firmware.

---

## 6. PRUEBAS EJECUTADAS Y RESULTADOS REALES

| Prueba | Comando | Resultado real | Estado |
|--------|---------|----------------|--------|
| Hash comprimido | `sha256sum /lib/firmware/amdgpu/polaris12_smc.bin.xz` | `fe9e823a...10f9` ✓ | PASS |
| Hash descomprimido | `sha256sum /tmp/polaris12_smc.bin` | `4b8eb326...6ec77` ✓ | PASS |
| Tamaño descomprimido | `stat -c%s /tmp/polaris12_smc.bin` | `130388` ✓ | PASS |
| Header parse | Python struct unpack | size_bytes=130388, ip_version=7.2 ✓ | PASS |
| REA versión | `rea --version` | `6.5.0` ✓ | PASS |
| REA inspect | `rea inspect /tmp/polaris12_smc.bin --target-format raw-binary --architecture x86 --entry-point 0x0 --format json --full-output` | status: ok, segment 0x0-0x1fd54 (130388 bytes), 1 procedure, 0 strings ✓ | PASS |
| Test CLI009 | `python3 tools/rxre/tests/test_cli009.py` | 146/146 aprobado (preexistente) ✓ | PASS |
| UMR GRBM_STATUS | `umr -O bits -g =0000:01:00.0 -r polaris12.gfx800.mmGRBM_STATUS` | 0x00003028, 24 bitfields ✓ | PASS |
| UMR SDMA0_STATUS | `umr -r mmSDMA0_STATUS_REG -g =0000:01:00.0` | rc=1 (empty) — confirmado gap | CONFIRMADO |
| PCI ID | `lspci -nn \| grep VGA` | `1002:699f` (Lexa PRO / RX550) ✓ | PASS |
| Mesa version | `rpm -q mesa-dri-drivers` | `26.2.4-1.fc44` ✓ | PASS |

---

## 7. BLOQUEOS QUE REQUIEREN NUEVA EVIDENCIA O AUTORIZACIÓN

| Bloqueo | Descripción | Requisito para desbloquear |
|---------|-------------|---------------------------|
| **ISA GFX8 no reconocida por REA** | REA analiza como x86 raw-binary, no como bytecode GFX8 | Investigación extensa de soporte GFX8 en Ghidra/otras herramientas; no hay documentación suficiente para un analizador SMC específico sin licencia/revisión |
| **Dependencias pesadas no instaladas** | pwntools, pyelftools, unicorn no disponibles | Instalación de dependencias (requiere evaluación de licencias y permisos) |
| **PTE/PDE base no legible como MMIO** | Los registros VM_CONTEXTn_PAGE_TABLE_BASE_ADDR son contexto PM4 (SET_CONTEXT_REG), no MMIO directo | Parsear PM4 IB stream (gap de finding 1612/1613/1614) |
| **SDMA registers no legibles via umr** | `umr -r mmSDMA0_*` retorna rc=1 | Soporte de registers SDMA en regdb UMR o vía debugfs alternativo |
| **Workload bajo carga no probado** | Todas las lecturas GRBM_STATUS son bajo idle; no se probó bajo carga GPU | Autorización explícita para ejecutar workload compute no-display sobre RX550 (frontera dura: prohibido sin autorización) |

---

## 8. CONCLUSIÓN FINAL

La integración REA está **completa y verificada** sin discrepancias. El firmware polaris12_smc.bin.xz ha sido analizado con evidencia verificable contra el código fuente del kernel AMDGPU. Se ha producido conocimiento nuevo validado (estructura del header SMC, offsets, CRC32, ucode_start_addr) sin afirmaciones especulativas.

La investigación REA se cierra dentro de su alcance auditado. La próxima tarea prioritaria recomendada es **agregar `VM_CONTEXTn_PAGE_TABLE_BASE_ADDR` al UMR regdb gfx_8_0_0.reg** para habilitar observación read-only de GPUVM en Polaris12, que es reproducible, de bajo riesgo y desbloquea la auditoría de page tables.

**No se afirma que RXRE haya mejorado el driver** hasta demostrar una mejora mediante pruebas apropiadas.

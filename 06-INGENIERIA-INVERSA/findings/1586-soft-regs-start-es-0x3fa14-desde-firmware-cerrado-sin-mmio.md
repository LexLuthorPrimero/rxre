# 1586 — `soft_regs_start = 0x3FA14` desde el firmware en disco, **sin MMIO**

## 0 · RESUMEN

El valor de `soft_regs_start` para esta placa (RX 550 / Polaris12 / 1002:699f rev c7) es **`0x3FA14` (260628)**. Sale del firmware **en disco** (`/lib/firmware/amdgpu/polaris12_smc.bin`, offset 0x130 del archivo descomprimido), y la cadena completa producer→artifact→consumer está cerrada en código fuente con **7 cruces independientes exactas**. No se requiere acceso MMIO para cerrar este hueco.

---

## 1 · SELECCIÓN DEL FIRMWARE (estático, incondicional para este device)

| Fuente | Código | Decisión |
|--------|--------|----------|
| `amdgpu.h:770` | `#define ASICID_IS_P23(did, rid) ((did == 0x6987) ...)` | **Nuestro `did = 0x699F` → falso** |
| `amdgpu_cgs.c:325-331` | `case CHIP_POLARIS12: if (ASICID_IS_P23(...)) polaris12_k_smc.bin else polaris12_smc.bin` | Carga **`polaris12_smc.bin`** (no kicker) |

La revisión `c7` *solo* califica como kicker si `did == 0x6987`. Con `0x699F` no se cumple.

---

## 2 · ESTRUCTURA DEL ARCHIVO (medido)

| Ítem | Valor | Fuente |
|------|-------|--------|
| Archivo | `/lib/firmware/amdgpu/polaris12_smc.bin.xz` | Sistema |
| Descomprimido | `/tmp/polaris12_smc.bin` | `xz -dc` |
| Tamaño | **130388 bytes** | `stat` |
| SHA256 | **`4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77`** | `sha256sum` |
| Contenedor | 256 bytes en offset 0 | `smu7_smumgr.c:424` carga desde `0x20000` |
| Imagen real | 130132 bytes (tamaño − 256) | Campo `ImageSize` |

---

## 3 · CABECERA DEL FIRMWARE (`SMU74_Firmware_Header` en offset 0x100)

| Campo | Offset archivo | Valor | Comentario |
|-------|----------------|-------|------------|
| `Digest[0..4]` | 0x100–0x110 | hash SHA256 del código | 5×u32 |
| `Version` | 0x114 | `0x00221700` (2234112) | |
| `HeaderSize` | 0x118 | `0x000000B4` (180) | Tamaño de esta cabecera |
| `Flags` | 0x11C | `0x00000000` | |
| `EntryPoint` | 0x120 | `0x00020100` | **= 0x20000 + 0x100** ✓ |
| `CodeSize` | 0x124 | `0x0001CDF0` (118256) | |
| `ImageSize` | 0x128 | `0x0001FC54` (130132) | **= filesize − 256** ✓ |
| `Rtos` | 0x12C | `0x0003CDC0` (249280) | |
| **`SoftRegisters`** | **0x130** | **`0x0003FA14` (260628)** | **← `soft_regs_start`** |
| `DpmTable` | 0x134 | `0x0003F294` (258708) | |
| `FanTable` | 0x138 | `0x0003F9F0` (260592) | |
| `CacConfigTable` | 0x13C | `0x00000000` | Ausente |
| `CacStatusTable` | 0x140 | `0x00000000` | Ausente |
| `mcRegisterTable` | 0x144 | `0x00000000` | Ausente |
| `mcArbDramTimingTable` | 0x148 | `0x0003F114` (258324) | |
| `PmFuseTable` | 0x14C | `0x0003FA8C` (260748) | |
| `Globals` | 0x150 | `0x0003BEC4` (245444) | |
| `ClockStretcherTable` | 0x154 | `0x0003F944` (260420) | |
| `VftTable` | 0x158 | `0x0003F018` (258072) | |
| `Reserved1` | 0x15C | `0x000200B4` (131252) | **= 0x20000 + HeaderSize** ✓ |
| `AvfsTable` | 0x160 | `0x0003FBA4` (261028) | |
| `AvfsCksOffGbvTable` | 0x164 | `0x0003FB94` (261012) | |
| `AvfsMeanNSigma` | 0x168 | `0x0003FB78` (260984) | |
| `AvfsSclkOffsetTable` | 0x16C | `0x0003FB68` (260968) | |

---

## 4 · CADENA PRODUCER → ARTIFACT → CONSUMER (fuente verificada)

```
polaris12_smc.bin (offset 0x130)
        │
        ▼  smu7_upload_smc_firmware_data()  [smu7_smumgr.c:418-435]
        │   mmSMC_IND_INDEX_11 = 0x20000
        │   AUTO_INCREMENT_IND_11 = 1
        │   for (; byte_count >= 4; byte_count -= 4)
        │       cgs_write_register(mmSMC_IND_DATA_11, *src++);
        │   → imagen completa escrita VERBATIM en SMC RAM 0x20000
        │
        ▼  SMC RAM 0x20030 = file offset 0x130 = 0x3FA14
        │
        ▼  smu7_read_smc_sram_dword()  [smu7_smumgr.c:229-238]
        │   smu7_set_smc_sram_address(hwmgr, 0x20030, limit)
        │       → cgs_write_register(mmSMC_IND_INDEX_11, 0x20030)
        │       → PHM_WRITE_FIELD(SMC_IND_ACCESS_CNTL, AUTO_INCREMENT_IND_11, 0)
        │   cgs_read_register(mmSMC_IND_DATA_11)  [mmio 0x1AD]
        │
        ▼  polaris10_smumgr.c:2510-2518
        │   smu7_read_smc_sram_dword(hwmgr,
        │       SMU7_FIRMWARE_HEADER_LOCATION + offsetof(SMU74_Firmware_Header, SoftRegisters),
        │       &tmp, SMC_RAM_END);
        │   data->soft_regs_start = tmp;
        │   smu_data->smu7_data.soft_regs_start = tmp;
        │
        ▼  Fallback en polaris10_start_smu() [polaris10_smumgr.c:314-316]
            smu7_read_smc_sram_dword(hwmgr, SMU7_FIRMWARE_HEADER_LOCATION +
                offsetof(SMU74_Firmware_Header, SoftRegisters),
                &(smu_data->smu7_data.soft_regs_start), 0x40000);
```

**Resultado**: `data->soft_regs_start = 0x3FA14` y `smu_data->smu7_data.soft_regs_start = 0x3FA14`.

---

## 5 · 7 CRUCES INDEPENDIENTES EXACTOS (oráculos)

Todos verificados por `tools/smu_firmware_header.py` (SELF_TESTED: pasa en archivo real, falla en mutado):

| # | Oráculo | Verificación | Estado |
|---|---------|--------------|--------|
| **O1** | `ImageSize == filesize − 256` | `0x1FC54 == 130388 − 256` | ✅ |
| **O2** | `DestAddr == 0x20000` (punto de carga SMC) | `0x20000 == 0x20000` | ✅ |
| **O3** | `EntryPoint == 0x20100` (= 0x20000 + 0x100) | Usado como umbral PC en `smu7_is_smc_ram_running` | ✅ |
| **O4** | `SoftRegisters + sizeof(SMU74_SoftRegisters) == PmFuseTable` | `0x3FA14 + 0x78 == 0x3FA8C` | ✅ |
| **O5** | `DpmTable + sizeof(DPM_table) == FanTable` | `0x3F294 + 0x75C == 0x3F9F0` (1884 bytes, hallazgo 081) | ✅ |
| **O6** | `Reserved1 == 0x20000 + HeaderSize(fw_header)` | `0x200B4 == 0x20000 + 0xB4` | ✅ |
| **O7** | Todas las tablas dentro de `[0x20000, 0x40000)` y `ImageSize <= 0x20000` | `SMC_RAM_END = 0x40000` (vegam_smumgr.h:32) | ✅ |

> **Nota**: O4 usa `sizeof(SMU74_SoftRegisters) = 120 (0x78)` medido en hallazgo **1578** (reconciliación por offset). O5 usa `sizeof(SMU74_Discrete_DpmTable) = 1884 (0x75C)` medido en hallazgo **081**. Ambos son **fuentes externas** al firmware.

---

## 6 · MAPA COMPLETO DE SMC RAM (esta placa, estático)

| Tabla | SMC RAM addr | File offset | Tamaño / Nota |
|-------|--------------|-------------|---------------|
| Firmware Header | 0x20000 | 0x100 | 180 bytes |
| **SoftRegisters** | **0x20030** | **0x130** | **120 bytes** |
| DpmTable | 0x3F294 | 0x1F194 | 1884 bytes |
| FanTable | 0x3F9F0 | 0x1F8F0 | (hasta siguiente) |
| mcArbDramTimingTable | 0x3F114 | 0x1F014 | |
| PmFuseTable | 0x3FA8C | 0x1F98C | = SoftRegs + 120 |
| Globals | 0x3BEC4 | 0x1BDC4 | |
| ClockStretcherTable | 0x3F944 | 0x1F844 | |
| VftTable | 0x3F018 | 0x1EF18 | |
| AvfsTable | 0x3FBA4 | 0x1FAA4 | |
| AvfsCksOffGbvTable | 0x3FB94 | 0x1FA94 | |
| AvfsMeanNSigma | 0x3FB78 | 0x1FA78 | |
| AvfsSclkOffsetTable | 0x3FB68 | 0x1FA68 | |
| Rtos | 0x3CDC0 | 0x1DCC0 | |
| (CacConfig, CacStatus, mcRegisterTable) | 0 | — | **Ausentes (puntero = 0)** |

Todas las direcciones caen dentro de `[0x20000, 0x40000)` = `SMC_RAM_END`.

---

## 7 · ESTADO EPISTÉMICO

| Magnitud | Estado | Justificación |
|----------|--------|---------------|
| Valor de `soft_regs_start` | **PROVEN_DERIVED** | Cadena completa producer→artifact→consumer en fuente; 7 oráculos independientes |
| Igualdad runtime (MMIO 0x1AC/0x1AD devuelve 0x3FA14) | **NOT_OVERSED** | El MMIO está deferido (no autorizado aún); el hallazgo 1579 probó la receta exacta |
| Hipótesis "SMC parchea su propia cabecera en runtime" | **NOT_DETERMINED** | Indecidible desde el árbol; no invalida el valor estático |

**LIMITACIÓN transversal**: árbol de fuente = linux-7.1.3; kernel corriendo = 7.2.9. Las direcciones de registro y el flujo de carga son estables; la lógica del driver puede haber cambiado. Artefacto y SHA256 registrados para reproducibilidad.

---

## 8 · CONSECUENCIAS INMEDIATAS

1. **`soft_regs_start` → CERRADO**. Pasa de BLOCKED (falta valor) a CLOSED.
2. **`dpm_table_start = 0x3F294`** queda disponible → permite cruce estático contra los **11 usos** registrados en hallazgo **113** (`DPM_TABLE_START`).
3. El mapa SMC RAM completo de esta placa queda **conocido estáticamente** (incluyendo tablas ausentes = 0).
4. Herramienta `tools/smu_firmware_header.py` queda en estado **SELF_TESTED** (no VALIDATED: falta cross-check con una segunda implementación independiente).

---

## 9 · ARTEFACTOS

- **Tool**: `tools/smu_firmware_header.py` (parser + 7 oráculos, SELF_TESTED)
- **Firmware descomprimido**: `/tmp/polaris12_smc.bin` (SHA256 `4b8eb326a7fbd391554fe50bc43cf04a917b01a806884ea324f5c3fe88a6ec77`)
- **Salida JSON**: ejecutar `python3 tools/smu_firmware_header.py /tmp/polaris12_smc.bin --json`

---

## 10 · PRÓXIMA ACCIÓN (Global Work Scan §58)

- [04] DEPENDENCIES desbloqueables: `dpm_table_start` → hallazgo 113 (11 usos)
- [15] IMPLEMENTATION justificada: mapa SMC RAM → driver puede usar offsets directos sin MMIO de descubrimiento
- [19] VALIDATION: cruzar `dpm_table_start` estático contra runtime si/ cuando se autorice MMIO
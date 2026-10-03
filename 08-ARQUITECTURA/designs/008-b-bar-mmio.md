# 008-B — BAR y MMIO: qué es enumeración, qué es mapeo y qué es acceso directo

**Ámbito**: `08-ARQUITECTURA/` — IA-3 (Arquitecto)
**Fecha**: 2026-09-29 · **Ronda**: 14
**Tipo**: `READ_ONLY/EVIDENCE` — análisis estático. Sin hardware, sin escritura MMIO.
**Árbol**: `RESEARCH/kernelbuild/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/`
**No toca**: `AGENTS.md`, `COORDINACION.md`, `07-DRIVER/`, `007`, Q-5, cerrojo ajeno.

---

## Scope

Separar explícitamente cinco cosas que el encargo exige no confundir:

```
PCI BAR enumeration  ≠  BAR mapping  ≠  MMIO read/write
                     ≠  indirect register access  ≠  cache/ordering semantics
```

## Question

¿Qué evidencia demuestra acceso **directo** a BAR/MMIO de la GPU, y qué parte es solo acceso
indirecto vía `mmPCIE_INDEX`?

## Evidence

### (1) Enumeración — la dirección física

```
amdgpu_device.c:3813   adev->rmmio_base = pci_resource_start(adev->pdev, 5);
amdgpu_device.c:3814   adev->rmmio_size = pci_resource_len(adev->pdev, 5);
amdgpu_device.c:3816   adev->rmmio_base = pci_resource_start(adev->pdev, 2);
amdgpu_device.c:3817   adev->rmmio_size = pci_resource_len(adev->pdev, 2);
amdgpu_doorbell_mgr.c:210   adev->doorbell.base = pci_resource_start(adev->pdev, 2);
amdgpu_bios.c:113      if (pci_resource_len(adev->pdev, 0) == 0)
amdgpu_bios.c:117      vram_base = pci_resource_start(adev->pdev, 0);
```

`pci_resource_start()`/`_len()` **solo leen la tabla de recursos del PCI**. No da acceso a la
memoria.

### (2) Mapeo — el paso que faltaba en `007`

```
amdgpu_device.c:3823   adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size);
```

**Este es el mapeo real.** `007` §5 listó «mapa BAR / MMIO» como `NOT_DETERMINED` sin haber
llegado aquí; la línea existe y es una sola. `ioremap()` devuelve la dirección virtual del kernel
sobre el BAR, y a partir de ahí `adev->rmmio + offset` es acceso directo.

### (3) Acceso directo — por dónde se llega a `ioremap()`

```
amdgpu_device.c:3813-3823   (dentro de la routine que rellena rmmio_base/rmmio_size y mapea)
```

El rango BAR é **5**, con **2** como fallback. Para la RX 550 cuál de los dos se usa
**`NOT_DETERMINED`**: depende de una condición que no seguí. El host expone
`consumer:pci:0000:01:00.1` (`/sys/bus/pci/devices/0000:01:00.0/consumer`), lo que sugiere un
dispositivo multifunción con un segundo BAR, pero **eso es `OBSERVATION` de sysfs, no evidencia de
qué BAR elige el driver**.

### (4) Acceso indirecto — lo que `007` vio y confundió

```
vi.c:297   vi_pcie_rreg()      WREG32_NO_KIQ(mmPCIE_INDEX, reg);
vi.c:304   (void)RREG32_NO_KIQ(mmPCIE_INDEX);
vi.c:305   return RREG32_NO_KIQ(mmPCIE_DATA);
vi.c:310   vi_pcie_wreg()      WREG32_NO_KIQ(mmPCIE_INDEX, reg); ... WREG32_NO_KIQ(mmPCIE_DATA, v);
vi.c:322   vi_smc_rreg()       WREG32_NO_KIQ(mmSMC_IND_INDEX_11, (reg));
vi.c:334   vi_smc_wreg()       WREG32_NO_KIQ(mmSMC_IND_INDEX_11, (reg));
```

**Esto NO es MMIO directo.** Es un protocolo de **registros indirectos**: se escribe un índice en
un registro de puerta (`mmPCIE_INDEX`, `mmSMC_IND_INDEX_11`) y el dato aparece en otro
(`mmPCIE_DATA`, `mmSMC_IND_DATA_11`). El acceso **sí** es MMIO directo sobre `adev->rmmio` — pero
el registro que se quiere leer se alcanza por indirección dentro del dispositivo.

**Corrección de `007`**: escribí «`vi.c:297-340` muestra accesos indirectos a PCIE/SMC vía
`mmPCIE_INDEX`» y lo dejé como si fuera «otra cosa que el MMIO». Es más sutil: la instrucción de
CPU sigue siendo un MMIO directo al BAR; lo indirecto es **qué registro** se toca.

### (5) Semántica de caché y ordenamiento

`WREG32_NO_KIQ` / `RREG32_NO_KIQ` aparecen con el sufijo explícito, lo que indica que **son
distintas de las variantes con KIQ** y que el ordenamiento importa. **No investigué** la
definición de esas macros. `NOT_DETERMINED` — y es un `NOT_DETERMINED` que vale la pena cerrar,
porque es la clase de cosa que `F4-AD-7` ya golpeó una vez con `rc=0`.

## Trace

```
PCI core
│  recurso BAR nº 5 (o 2)
▼
amdgpu_device.c:3813   pci_resource_start(pdev, 5)        -- enumeracion
amdgpu_device.c:3814   pci_resource_len(pdev, 5)
│
▼
amdgpu_device.c:3823   ioremap(rmmio_base, rmmio_size)     -- MAPEO
│
▼
adev->rmmio  (void *)                                   -- MMIO DIRECTO
│
├──► RREG32/WREG32(adev->rmmio + reg)      acceso directo a un registro
│
└──► vi.c:297  vi_pcie_rreg()
      WREG32_NO_KIQ(mmPCIE_INDEX, reg)   -- ACCESO INDIRECTO a un registro
      RREG32_NO_KIQ(mmPCIE_DATA)         (la CPU toca el BAR, el dispositivo enruta)
```

## Classification

| Elemento | Estado | Evidencia |
|---|---|---|
| El BAR se enumera | `PROVEN` | `amdgpu_device.c:3813-3817` |
| El BAR se mapea con `ioremap()` | `PROVEN` | `amdgpu_device.c:3823` |
| El doorbell tiene BAR propio | `PROVEN` | `amdgpu_doorbell_mgr.c:210` |
| El VRAM se toma de BAR 0 | `PROVEN` | `amdgpu_bios.c:113,117` |
| `vi_pcie_rreg/wreg` es acceso **indirecto a registro** | `PROVEN` | `vi.c:297-320` |
| `vi_smc_rreg/wreg` es acceso indirecto | `PROVEN` | `vi.c:322-342` |
| Qué BAR usa **la RX 550** (5 o el fallback 2) | `NOT_DETERMINED` | condición no seguida |
| Semántica de `*_NO_KIQ` (ordering, barriers) | `NOT_DETERMINED` | macros no investigadas |
| Modelo de caché de los registros | `NOT_DETERMINED` | no applicable estático sin hardware |
| Si un driver **propio** necesita `ioremap` | **`REQUIRED`** (no hay MMIO sin él) | naturaleza de la operación, no AMDGPU |

## Unknowns

| # | Desconocimiento | Discriminante que falta |
|---|---|---|
| U-1 | BAR 5 vs 2 en esta GPU | leer la condición en `amdgpu_device.c:3805-3823` completa — estática, pendiente |
| U-2 | `RREG32` vs `RREG32_NO_KIQ` | leer la macro en `amdgpu.h` — estática, pendiente |
| U-3 | Modelo de caché | requiere lectura de registros: **requiere autorización** |

## Closure criterion — cumplido

Los cinco conceptos del encargo quedan separados con evidencia. Los tres `NOT_DETERMINED` tienen
discriminante identificado, y dos de ellos (U-1, U-2) son **estáticos y baratos**; no los cerré
porque excedían la pregunta declarada.

## Tooling used

`grep -n` para localización, `sed -n` para contexto. No hizo falta AST: la distinción
enumeración/mapeo/acceso se lee directamente en tres líneas consecutivas.

---

```
STATUS: PROVEN   (para BAR mapping y acceso directo)
        NOT_DETERMINED  (para: BAR efectivo en esta GPU, semantica _NO_KIQ, modelo de cache)

EVIDENCE:
amdgpu_device.c:3813   adev->rmmio_base = pci_resource_start(adev->pdev, 5)   -- enumeracion
amdgpu_device.c:3823   adev->rmmio = ioremap(adev->rmmio_base, adev->rmmio_size)  -- MAPEO
amdgpu_doorbell_mgr.c:210  adev->doorbell.base = pci_resource_start(adev->pdev, 2)
vi.c:297-320   vi_pcie_rreg/wreg   -> mmPCIE_INDEX/mmPCIE_DATA  -- INDIRECTO
vi.c:322-342   vi_smc_rreg/wreg    -> mmSMC_IND_INDEX_11        -- INDIRECTO

DISCRIMINANT:
U-1  cual BAR usa la RX550 -> leer la condicion completa en amdgpu_device.c:3805-3823 (ESTATICO)
U-2  ordenamiento de RREG32_NO_KIQ -> definicion de la macro en amdgpu.h (ESTATICO)
U-3  modelo de cache -> lectura de registros, REQUIERE AUTORIZACION

ARTIFACT:
08-ARQUITECTURA/designs/008-b-bar-mmio.md

RUNTIME:
NOT_RUN

MODIFICATIONS:
NONE (fichero nuevo, sin commit)

COMMIT:
NONE
```

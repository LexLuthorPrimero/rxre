# 067 · La cadena GART de punta a punta: 256 MiB por `default`, y la tabla es un BO en VRAM

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC+HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué cierra, y qué no

La herramienta de cobertura del proyecto (`causal_map.py`) marca **GART como
entidad sin afirmación fuerte**. Al trazarlo resulta que no es que falte
estudio: es que lo estudiado no quedó como cifra verificable. `gart_size` tiene
**56 sitios en 19 ficheros** del corpus y **cero cifras** en los hallazgos.

Esta nota pone la cifra y la cadena. El resultado importante no es la cifra: es
que **la tabla GART de esta GPU es un buffer object en VRAM**, y eso no estaba en
el estado del proyecto.

## El valor: 256 MiB, y por qué

```
gmc_v8_0.c:592   case CHIP_POLARIS12: /* all engines support GPUVM */
gmc_v8_0.c:594   default:
gmc_v8_0.c:595       adev->gmc.gart_size = 256ULL << 20;
```

`CHIP_POLARIS12` es un `case` explícito que cae en `default`. El `default:` no es
el valor por defecto de la serie: es la rama "todos los motores soportan GPUVM".

El árbol completo, para que se vea que 256 no es un accidente de la rama:

```
gmc_v8_0.c:595   256ULL << 20   ← Polaris10/11/12, Vegam, default
gmc_v8_0.c:601   1024ULL << 20  ← Tonga, Fiji, Carrizo, Stoney (UVD/VCE sin GPUVM)
gmc_v8_0.c:605   amdgpu_gart_size << 20   ← si está fijado por parámetro
gmc_v8_0.c:608   += adev->pm.smu_prv_buffer_size
```

Tonga —el chip del que desciende esta arquitectura— está en la rama de 1024, y
Polaris12 en la de 256. **No es un valor heredado del hermano, es un cambio
explícito para GPUVM completo.** Un driver propio que copie la rama de Tonga
duplica la GART y rompe el cálculo de `gart_end`.

**Arbitraje por el kernel en ejecución**, que es más fuerte que la lectura del
código:

```
$ journalctl -k -b --no-pager | grep -i gart
amdgpu 0000:01:00.0: GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
amdgpu 0000:01:00.0: [drm] PCIE GART of 256M enabled (table at 0x000000F400900000).
amdgpu 0000:01:00.0: [drm] GART: num cpu pages 65536, num gpu pages 65536
```

`256M` en el log y `256ULL << 20` en el código. Dos vías independientes.

## Lo nuevo: la tabla GART está en VRAM

Esto no estaba en el estado del proyecto, y cambia la implementación.

```
gmc_v8_0.c:835   if (adev->gart.bo == NULL) {
gmc_v8_0.c:836       dev_err(adev->dev, "No VRAM object for PCIE GART.\n");
gmc_v8_0.c:840   table_addr = amdgpu_bo_gpu_offset(adev->gart.bo);
gmc_v8_0.c:942   drm_info(..., "PCIE GART of %uM enabled (table at 0x%016llX).\n",
gmc_v8_0.c:944       table_addr);
```

La dirección que el kernel imprime sale de `amdgpu_bo_gpu_offset(adev->gart.bo)`:
un **offset de GPU dentro de un buffer object**, no una dirección de RAM del
sistema.

Y el log lo corrobora por intersección de rangos:

```
VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF
tabla GART en           0x000000F400900000     ← dentro de ese rango
```

**Consecuencia para el driver propio.** La GART no se puede construir en RAM del
sistema y puntearla como una tabla plana: hay que reservar un BO, residentarlo,
obtener su offset GPU, y ese offset es lo que va a `PAGE_TABLE_BASE_ADDR`. La
cadena es `bo → amdgpu_bo_gpu_offset → table_addr → mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR`,
y `gmc_v8_0.c:889` hace exactamente `WREG32(..., table_addr >> 12)`.

Es además la diferencia entre `PROVEN_ABSENT` y `NOT_APPLICABLE`: el camino de
`map_gart()` en RAM no es un hueco de esta GPU, es una ruta que **esta GPU no
tiene**, porque su tabla vive en VRAM por construcción.

## El TLB de L1 se configura en el mismo paso

En las tres líneas siguientes a la dirección de la tabla:

```
gmc_v8_0.c:843   tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);
gmc_v8_0.c:844   REG_SET_FIELD(..., ENABLE_L1_TLB, 1);
gmc_v8_0.c:845   REG_SET_FIELD(..., ENABLE_L1_FRAGMENT_PROCESSING, 1);
gmc_v8_0.c:846   REG_SET_FIELD(..., SYSTEM_ACCESS_MODE, 3);
```

La GART se habilita con **TLB de L1 activo y procesamiento de fragmentación
activo**, y `SYSTEM_ACCESS_MODE = 3`. `mmMC_VM_MX_L1_TLB_CNTL` es uno de los
siete registros que 065 demostró que tienen dirección distinta entre familias
(GMC `0x819`, MMHUB `0x0ca3`).

## Lo que sigue abierto

| Afirmación | Estado |
|---|---|
| `gart_size = 256 MiB` para Polaris12 | `PROVEN` (código + log del host) |
| Polaris12 usa la rama `default`, no la de Tonga | `PROVEN` |
| La tabla GART es un BO en VRAM | `PROVEN` |
| Su dirección es un offset GPU, no una dirección de RAM | `PROVEN` |
| La tabla cae dentro del rango de VRAM 2048M | `PROVEN` (log) |
| L1 TLB + fragmentación se activan al habilitar la GART | `PROVEN` |
| Qué hace el hardware con `SYSTEM_ACCESS_MODE = 3` | `PROVEN` en `081` — `NOT_IN_SYS`, el acceso NO está en RAM de sistema |
| Por qué `SYSTEM_ACCESS_MODE = 3` y no otro | `PROVEN` en `081` — y `088:64` lo corrobora: es el nivel de contexto del mismo campo |
| `amdgpu_gart_size` como override, y su límite | `NOT_IN_CORPUS` (no aparece en el log: no se usó) |

El override por parámetro no se puede cerrar: `amdgpu_gart_size` no aparece en
`journalctl`, luego en esta máquina no se fijó, y la rama `else` de `gmc_v8_0.c:605`
no se ejecutó. Es un camino **no recorrido**, no uno comprobado.

## Procedencia

- `CORPUS` — `gmc_v8_0.c`, `amdgpu_gart.c`, `gmc_v10_0.c` (comparación).
- `HOST_OBSERVATION` — `journalctl -k -b`, sólo lectura. Sin escribir en la GPU.
- Herramientas: `xref.py` (quién escribe `gart_size`), `causal.py` (grafo),
  `causal_map.py` (cobertura, que.signaló el hueco), `regdb.py` (familias del
  registro L1 TLB).
- Sin `insmod`, sin MMIO write, sin tocar la GPU.
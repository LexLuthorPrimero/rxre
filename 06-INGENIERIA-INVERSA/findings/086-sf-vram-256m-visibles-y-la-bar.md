# 086 · §F VRAM: por qué hay 256 MiB visibles de 2048, y por qué no es por parámetro

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`AGENTS.md` §F pide separar *VRAM: GPUVA → GPU physical → MC → GDDR5* de la
traducción GPUVM. La geometría de GART está cerrada (`067`). La de **VRAM** no:
nadie había tracedo quién fija `vram_start`, qué límites se aplican, ni por qué
lo visible es 8 veces menor que lo total.

## El productor, y sólo hay uno

```
amdgpu_gmc.c:214   void amdgpu_gmc_vram_location(struct amdgpu_device *adev,
amdgpu_gmc.c:215                                 struct amdgpu_gmc *mc, u64 base)
amdgpu_gmc.c:220       mc->vram_start = base;
amdgpu_gmc.c:221       mc->vram_end = mc->vram_start + mc->mc_vram_size - 1;
```

## El `base` sale del hardware, y eso cierra el hueco

Decré abajo que no había leído `gmc_v8_0_vram_gtt_location`. **Lo he leído, y es
la pieza que faltaba:**

```
gmc_v8_0.c:414   u64 base = 0;
gmc_v8_0.c:416   if (!amdgpu_sriov_vf(adev))
gmc_v8_0.c:417       base = RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF;
gmc_v8_0.c:418   base <<= 24;
gmc_v8_0.c:420   amdgpu_gmc_set_agp_default(adev, mc);
gmc_v8_0.c:421   amdgpu_gmc_vram_location(adev, mc, base);
gmc_v8_0.c:422   amdgpu_gmc_gart_location(adev, mc, AMDGPU_GART_PLACEMENT_BEST_FIT);
```

**`base` se lee del hardware, no del software.** Es `MC_VM_FB_LOCATION` enmascarado
a 16 bits y desplazado 24 — o sea que la VRAM empieza en un múltiplo de 16 MiB, y
el hardware decide cuál.

Verificado contra la observación: el log da `0x000000F400000000`, y
`0xF400000000 >> 24 = 0xF400`, que cabe en 16 bits. **Cuadra exactamente.**

Eso confirma `AGENTS.md` L153 (*`vram_start` proviene de `MC_VM_FB_LOCATION`*) y
añade el detalle que faltaba: **los 16 bits bajos, y el desplazamiento de 24**. La
granularidad de la VRAM es de 16 MiB, impuesta por el hardware.

Y el orden de las tres llamadas es la dependencia circular que mencioné:

```
  L421   amdgpu_gmc_vram_location   ← fija la geometría de VRAM
  L422   amdgpu_gmc_gart_location   ← coloca la GART DENTRO de la VRAM recién fijada
```

La tabla GART se coloca después de que la VRAM existe. En una ruta con GART en
VRAM, ese orden es obligatorio, no cosmético.

## Los tres límites, y el orden importa

```
amdgpu_gmc.c:222   if (limit < mc->real_vram_size)
amdgpu_gmc.c:223       mc->real_vram_size = limit;              <- vramlimit
amdgpu_gmc.c:225   if (vis_limit && vis_limit < mc->visible_vram_size)
amdgpu_gmc.c:226       mc->visible_vram_size = vis_limit;       <- vis_vramlimit
amdgpu_gmc.c:228   if (mc->real_vram_size < mc->visible_vram_size)
amdgpu_gmc.c:229       mc->visible_vram_size = mc->real_vram_size;
```

**L228-229 es el pinzamiento**: lo visible nunca puede exceder lo real. Si un
parámetro pidiera 4 GiB visibles con 2 GiB de VRAM real, el pinzamiento lo corta.

Y `L225` tiene un `vis_limit &&` que **L222 no tiene**: `vramlimit = 0` significa
"sin límite", pero `vis_vramlimit = 0` también, por el `&&` explícito. Son
asimétricos a propósito.

## La observación, y refuta la explicación fácil

```
$ cat /sys/class/drm/card1/device/mem_info_vram_total       → 2147483648   (2048 MiB)
$ cat /sys/class/drm/card1/device/mem_info_vis_vram_total   →  268435456   ( 256 MiB)
$ cat /sys/module/amdgpu/parameters/vramlimit                →  -1
$ cat /sys/module/amdgpu/parameters/vis_vramlimit            →   0
```

**`vis_vramlimit = 0`, o sea el valor por defecto, sin tocar.** La explicación
natural —"lo visible está limitado por parámetro"— **es falsa en esta máquina**.

Y el log dice por qué:

```
amdgpu 0000:01:00.0: [drm] Detected VRAM RAM=2048M, BAR=256M
```

**Los 256 MiB son el tamaño de la BAR.** Y coincide exactamente con
`mem_info_vis_vram_total`. La BAR es lo que la CPU puede mapear; el resto de la
VRAM existe para la GPU pero no para el host.

Eso es coherente con lo que `AGENTS.md` L157 ya declara: *BAR/full-visible =
FALSE en esta RX550*. Ahora tiene el mecanismo y el número.

## Qué es la BAR y por qué el pinzamiento la respeta

El pinzamiento de L228-229 existe justo para esto: si el firmware o el
descubrimiento de VRAM dijeran "hay 4 GiB visibles" y la BAR es de 256 MiB, el
pinzamiento lo reduce a lo que la BAR puede dar. Es la regla que convierte un
reporte del firmware en algo que la CPU puede usar.

## La línea de §F que esteProducer cumple

`AGENTS.md` §F: *GPUVA → GPU physical → MC → GDDR5*.

```
  GPUVA           una VA de la VM
      ↓
  GPU physical    lo que va en el PTE (064, 075)
      ↓
  MC              mmVM_CONTEXT*_PAGE_TABLE_BASE_ADDR  (064)
      ↓
  GDDR5           amdgpu_gmc_vram_location: 0xF400000000 - 0xF47FFFFFFF
```

ElProducer de VRAM es el **último** de la cadena, y el único de los cuatro que
está en `amdgpu_gmc.c` con una función propia de 20 líneas. Los otros tres los
cerraron `064`, `075` y `085`.

**Y hay una separación que `067` ya mostró y que esta nota confirma**: la tabla
GART de esta GPU vive en **VRAM** (`0xF400900000`, dentro del rango de arriba), y
`vram_location` es quien fija ese rango. Traducir una VA de GART significa
indexar una tabla que está en la misma VRAM a la que apunta. Eso no es un problema
en esta GPU, pero es una dependencia circular que un driver propio tiene que
respetar en el orden de inicialización: **no se puede asignar la tabla GART antes
de fijar la geometría de VRAM.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `vram_start`/`vram_end` los fija `amdgpu_gmc_vram_location` | `PROVEN` (L220-221) |
| El pinzamiento visible ≤ real | `PROVEN` (L228-229) |
| `vis_vramlimit = 0` en esta máquina | `OBSERVED` (sysfs) |
| Los 256 MiB visibles son la BAR | `PROVEN` (log: `BAR=256M`) |
| La BAR es lo que el host puede mapear | `OBSERVED` |
| De dónde sale el `base`: `MC_VM_FB_LOCATION & 0xFFFF`, `<< 24` | `PROVEN` (`gmc_v8_0.c:414-418`) |
| Qué hace el pinzamiento si la BAR fuera mayor | `NOT_DETERMINED` |
| Cómo decide el firmware el tamaño de BAR | `NOT_DETERMINED` |

**La quinta estaba cerrada**: leí `gmc_v8_0_vram_gtt_location` y el
`base` sale de `MC_VM_FB_LOCATION & 0xFFFF`, desplazado 24. Ver arriba.

## Procedencia

- `CORPUS` — `amdgpu_gmc.c:204-238`, `amdgpu_drv.c:273-285`.
- `HOST_OBSERVATION` — sysfs (`mem_info_*`, `parameters/vramlimit`), `journalctl`.
  Sólo lectura.
- Encadenada con `067` (tabla GART en VRAM), `064` (PTBA y MC), `085` (§B).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.
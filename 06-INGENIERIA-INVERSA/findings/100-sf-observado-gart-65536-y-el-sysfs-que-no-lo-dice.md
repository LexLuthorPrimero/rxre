# 100 · §F OBSERVADO: 65536 entradas confirman el GART de 256 MiB, y hay un sysfs que NO lo dice

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 (SOLO drivers/gpu/drm/amd/)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`067`cerró la geometría del GART por lectura: `CHIP_POLARIS12 → default:
gart_size = 256 MiB`. Eso es **código**.

**Y hay un observable runtime que lo confirma de forma independiente**, con una
aritmética que no depende de leer el `switch`.

## El observable

```
$ cat /sys/kernel/debug/dri/0000:01:00.0/amdgpu_gtt_mm

use_type: 1
use_tt: 1
size: 6194642944
usage: 59924480
  0x0000000000000000-0x0000000000000001: 1: used
  0x0000000000000001-0x0000000000000009: 8: used
  0x0000000000000009-0x0000000000000209: 512: used
  ...
  0x00000000000036b9-0x0000010000: 51527: free
total: 65536, used 14009 free 51527
```

**`total: 65536`.** Y cada entrada cubre una página de GPU de 4 KiB:

```
65536 × 4096 = 268.435.456 bytes = 256 MiB
```

**Es el número de `067`, verificado por una vía que no pasa por el `switch`.**

Y en el lado del código, la rama correcta:

```
gmc_v8_0.c:592   case CHIP_POLARIS12: /* all engines support GPUVM */
gmc_v8_0.c:594   default:
gmc_v8_0.c:595       adev->gmc.gart_size = 256ULL << 20;
```

`256ULL << 20` = 256 MiB. **Dos fuentes independientes, mismo número.**

## Y aquí está la trampa, que es el hallazgo de verdad

`size: 6194642944`. Parece el tamaño del GART. **No lo es.**

```
amdgpu_gtt_mgr.c:53   man = ttm_manager_type(&adev->mman.bdev, TTM_PL_TT);
amdgpu_gtt_mgr.c:54   return sysfs_emit(buf, "%llu\n", man->size);
```

**Es `ttm_resource_manager.size` del gestor de TTM_PL_TT**, y el mismo valor
aparece en sysfs:

```
$ cat /sys/class/drm/card1/device/mem_info_gtt_total
6194642944
```

| magnitud | valor | páginas de 4 KiB |
|---|---|---|
| **GART** | 268.435.456 B = **256 MiB** | **65.536** |
| `mem_info_gtt_total` | 6.194.642.944 B = 5,77 GiB | 1.512.364 |

**Son 23 veces distintos.** El GART es el **4,3 %** del espacio que reporta
`mem_info_gtt_total`.

**Los dos son ciertos y los dos son TT**, pero a distinto nivel: `man->size` es
todo el espacio direccionable de la Translation Table, que incluye buffers de
usuario, y la tabla del GART es una ventana de 65.536 páginas dentro de él.

**Para un driver propio, el error que esto evita es concreto:** si dimensionas el
GART a partir de `mem_info_gtt_total`, te sale una ventana 23 veces mayor que la
que el hardware tiene, y un mapeo de 1 GiB en el GART **no cabría** — a
`067`/el hardware le darían error en `gmc_v8_0_set_gart_address`, sin ninguna
explicación útil.

## Y una limitación del corpus que no tenía registrada

Busqué el código que imprime `amdgpu_gtt_mm` y **no está en el corpus**:

```
drivers/gpu/drm/     ->  sólo existe el directorio  amd/
drivers/gpu/         ->  sólo existe  drm/
```

**El corpus es exclusivamente `drivers/gpu/drm/amd/`.** Las capas TTM, DRM core
y `drm_buddy` **no están**.

Eso tiene dos consecuencias y las dos importan:

1. **No puedo derivar la semántica de `use_type`, `use_tt` ni `usage`** desde el
   código. Los valores numéricos de esas filas los trato como
   `OBSERVED_SIN_DERIVACION`: sé lo que dicen, no sé por qué.
2. **Todo lo que he derivado en esta investigación es interno de amdgpu.**
   Si algo depende de la capa TTM —y el GART es el ejemplo canónico, porque es
   una Translation Table—, **no puedo verificarlo leyendo.** Esa es una
   limitación del trabajo, no del tema.

**No la había declarado hasta ahora**, y es la clase de cosa que hay que
declarar antes de que la descubra otro: cualquier afirmación mía sobre
comportamiento que dependa de TTM es `NOT_IN_CORPUS`, no `NOT_DETERMINED`.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| El GART de esta GPU es 256 MiB | `OBSERVED` (65536×4096) + `PROVEN` (`gmc_v8_0.c:595`) |
| `mem_info_gtt_total` es 23× el GART | `OBSERVED` |
| `mem_info_gtt_total` = `ttm_manager_type(TTM_PL_TT)->size` | `PROVEN` (`amdgpu_gtt_mgr.c:53-54`) |
| El GART es una ventana dentro del TT total | `PROVEN_DERIVED` (65536 de 1.512.364) |
| Qué es `use_type: 1` | `NOT_IN_CORPUS` |
| Qué es `use_tt: 1` | `NOT_IN_CORPUS` |
| Por qué `usage` (59.924.480) no cuadra con la suma de "used" (14.009) | `NOT_IN_CORPUS` |
| Cómo elige el driver el PLACEMENT dentro de esa ventana | `PARTIAL` — `067` cerró `BEST_FIT` |
| Si el GART puede crecer en runtime | `NOT_DETERMINED` |

**La quinta fila es la que acabo de encontrar y no puedo cerrar.** `usage` son
59.924.480 bytes = 14.629 páginas, pero la suma de los bloques "used" que el
propio fichero lista da 14.009 entradas. **El fichero se contradice a sí mismo**
si `usage` pretendiera contar las mismas entradas. Como no tengo el código que lo
imprime, no sé si `usage` mide otra cosa (bytes reservados, páginas reales,
espacio fragmentado) o si hay un bug.

**Lo dejo como discrepancia observada, no resuelta.** Y no elijo la explicación
más cómoda.

## Procedencia

- `RUNTIME` — `debugfs/amdgpu_gtt_mm`, `sysfs mem_info_gtt_total`,
  `mem_info_gtt_used`. **Sólo lectura.**
- `STATIC` — `gmc_v8_0.c:588-600`, `amdgpu_gtt_mgr.c:45-78`.
- **CORPUS GAP DECLARADO**: la implementación de `amdgpu_gtt_mm` está en la capa
  TTM, fuera de `drivers/gpu/drm/amd/`.
- Encadenada con `067` (la geometría del GART, que esto confirma por segunda
  vía), `086` (VRAM), `087` (GMC 8.1), `099` (PRT).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, sobre un error que casi no cometí.**

Busqué el código de `amdgpu_gtt_mm` en `amdgpu_gtt_mgr.c` —el fichero que
tiene el nombre de la cosa— y no estaba. Podría haber concluido "el observable
no tiene código en el corpus, no lo uso", que es justo el `NAME_NOT_FOUND`
tratado como ausencia que me ha pasado nueve veces.

Lo que hice fue `ls` del directorio padre, que mostrou que **el corpus entero
son 36 ficheros de `drivers/gpu/drm/amd/`** y nada más. Eso convirtió un
`NAME_NOT_FOUND` en una **declaración de límite del corpus**, que es
información útil en vez de un callejón sin salida.

**Y la lección es la de siempre, con una diferencia:** un `NAME_NOT_FOUND` bien
tratado no es una ausencia, es una pregunta mal—I worded— sobre dónde mirar.
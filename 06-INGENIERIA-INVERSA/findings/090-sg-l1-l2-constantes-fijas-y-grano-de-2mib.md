# 090 · §G: el driver enciende la TLB con constantes fijas y no toca ni su tamaño ni sus políticas

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`083` cerró la **configuración** de L1 y L2. Dejó abierto qué cuenta la TLB,
cuándo entra una entrada y cuándo sale. Esta nota responde las tres, y la
respuesta es incómoda: **el driver no lo sabe, porque no lo programa**.

## L1 TLB: cinco campos, cinco constantes

`gmc_v8_0.c:842-849`, único sitio de todo el driver donde se programa:

```
gmc_v8_0.c:842   /* Setup TLB control */
gmc_v8_0.c:843   tmp = RREG32(mmMC_VM_MX_L1_TLB_CNTL);
gmc_v8_0.c:844   tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, ENABLE_L1_TLB, 1);
gmc_v8_0.c:845   tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, ENABLE_L1_FRAGMENT_PROCESSING, 1)
gmc_v8_0.c:846   tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, SYSTEM_ACCESS_MODE, 3);
gmc_v8_0.c:847   tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, ENABLE_ADVANCED_DRIVER_MODEL, 1);
gmc_v8_0.c:848   tmp = REG_SET_FIELD(tmp, MC_VM_MX_L1_TLB_CNTL, SYSTEM_APERTURE_UNMAPPED_ACCESS, 0)
gmc_v8_0.c:849   WREG32(mmMC_VM_MX_L1_TLB_CNTL, tmp);
```

**Ninguno se calcula.** No hay variable, ni `min`, ni lectura de ASIC type, ni
caso por generación. Es un valor mágico, y el disable en `gmc_v8_0.c:980-984` es
su reflejo campo por campo.

**Esto vale como regla para un driver propio**: si amdgpu no variationa la
configuración de la TLB en esta generación, no hay una knobs que copiar. O se
escriben estos cinco valores, o no se escribe el registro.

## L2: siete campos, y uno sí lleva información

```
gmc_v8_0.c:850   /* Setup L2 cache */
gmc_v8_0.c:852   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_CACHE, 1);
gmc_v8_0.c:853   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_FRAGMENT_PROCESSING, 1);
gmc_v8_0.c:854   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_PTE_CACHE_LRU_UPDATE_BY_WRITE, 1);
gmc_v8_0.c:855   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_L2_PDE0_CACHE_LRU_UPDATE_BY_WRITE, 1);
gmc_v8_0.c:856   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, EFFECTIVE_L2_QUEUE_SIZE, 7);
gmc_v8_0.c:857   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, CONTEXT1_IDENTITY_ACCESS_MODE, 1);
gmc_v8_0.c:858   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL, ENABLE_DEFAULT_PAGE_OUT_TO_SYSTEM_MEMORY, 1);
```

Siete campos, seis constantes. **El séptimo es `EFFECTIVE_L2_QUEUE_SIZE = 7`**,
y es el único que **no** es una constante obvia:

```
gmc_8_1_sh_mask.h   VM_L2_CNTL__EFFECTIVE_L2_QUEUE_SIZE_MASK 0x38000
```

`0x38000` son los bits 15-17: **tres bits, valores 0-7**. El driver escribe **7,
el máximo del campo**. No es un valor arbitrario, es saturar el campo.

Y los dos `LRU_UPDATE_BY_WRITE` dicen algo concreto sobre "cuándo sale una
entrada": **el L2 actualiza su LRU cuando se escribe en la PTE** — o sea, un
escritor invalida la entrada herself, sin necesidad de un invalidate explícito
para ese caso.

## El grano del L2 es el fragmento de 2 MiB

Aqui esta la conexion que `085` no encontro, y que yo tampoco:

```
gmc_v8_0.c:865   field = adev->vm_manager.fragment_size;
gmc_v8_0.c:866   tmp = RREG32(mmVM_L2_CNTL3);
gmc_v8_0.c:867   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_ASSOCIATIVITY, 1);
gmc_v8_0.c:868   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, BANK_SELECT, field);
gmc_v8_0.c:869   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field);
```

**El `fragment_size` va directo a dos campos del L2.** Y el valor real:

```
amdgpu_vm.c:2456  if (amdgpu_vm_fragment_size == -1)
amdgpu_vm.c:2457      adev->vm_manager.fragment_size = fragment_size_default;
amdgpu_kms.c:1006  dev_info->pte_fragment_size = (1 << fragment_size) * AMDGPU_GPU_PAGE_SIZE
amdgpu_gart.h:35   #define AMDGPU_GPU_PAGE_SIZE 4096
```

`(1 << 9) * 4096 = 2.097.152 bytes = 2 MiB = 512 PTEEs de 4 KiB`.

Observado en el host:

```
amdgpu 0000:01:00.0: vm size is 64 GB, 2 levels, block size is 10-bit, fragment size is 9
```

**El grano del L2 es el fragmento de 2 MiB, y eso son 512 PTEEs.**

Y `085` decía que `fragment_size = 9` eran "8 PTEEs". **Estaba mal, por 64×.**
Lo he corregido en el propio `085`, con la corrección escrita dentro y marcada.
El "8 PTE block" del comentario de `amdgpu_vm.c:1155` son 8 PTEEs de 4 KiB =
32 KiB: es el **grano de hardware de la TLB**, y el fragmento de 2 MiB es el
**grano de software**. Son dos cosas, y yo las identifiqué porque aparecen en la
misma frase.

## Dos resultados negativos, y son la respuesta

**No existe ningún campo de tamaño de TLB en el corpus entero.** Busqué
`TLB*__(NUM|SIZE|COUNT|ENTRIES)` en todas las cabeceras `asic_reg`: los únicos
aciertos son `L2TLB_PERFCOUNTER_*`, que son contadores, no configuración.

**Y las políticas de L1 existen pero el driver no las toca.** En
`gfx_8_0_sh_mask.h`:

| registro | campos | ancho | total |
|---|---|---|---|
| `TC_CFG_L1_LOAD_POLICY0` | `POLICY_0..15` | 2 bits | 32 bits |
| `TC_CFG_L1_LOAD_POLICY1` | `POLICY_16..31` | 2 bits | 32 bits |
| `TC_CFG_L1_STORE_POLICY` | `POLICY_0..31` | 1 bit | 32 bits |

**64 políticas programables** (32 de carga de 2 bits, 32 de escritura de 1 bit),
que llenarían los tres registros exactamente, sin huecos ni solapes.

Y el driver **no escribe ninguna**:

```
gmc_v8_0.c    ATC_L2: 0   TC_CFG: 0
gfx_v8_0.c    ATC_L2: 0   TC_CFG: 0
vi.c          ATC_L2: 0   TC_CFG: 0
amdgpu_gmc.c  ATC_L2: 0   TC_CFG: 0

todo drivers/gpu/drm/amd:  mmTC_* en .c = 0
```

**Cero `mmTC_*` en todo el driver.** Con control de sanidad: `mmATC_L2_*` sí
aparece, así que el grep funciona. Pero esos están en `gfx_v9_0.c`,
`gfx_v9_4.c` y `mmhub_v1_0.c`, y el campo que se escribe es `WRITE_COUNTERS` —
son contadores RAS, no geometría.

## La sexta repetición del error de generación

A mitad de esto conté `mmATC_L2_CACHE_4K_DSM_CNTL` y `..._2M_...` y escribí
"el driver configura la TLB en dos granularidades, 4 KB y 2 MB". **Era falso.**

Los nombres son ciertos: `ATC_L2_CACHE_4K_*` y `ATC_L2_CACHE_2M_*` existen
en `mmhub_1_8_0_sh_mask.h`. Pero los tres sitios que los usan están en
`gfx_v9_4_2.c:1452-1455` y `gfx_v9_4.c:796-807`, y escriben `WRITE_COUNTERS`.

**Es la sexta vez que un nombre en el driver no es cosa de esta GPU** — `065`,
`075`, `076`, `085`, esta, y la de `gmc_v8_1` en `087`. Y es la primera vez que
la cazo yo, porque me forcé a abrir el call site antes de concluir, que es lo
que `DERIVATION_BEFORE_OBSERVATION` significa en la práctica.

Curiosidad que no es conclusión: los nombres `4K` y `2M` coinciden con el grano
del L2 que acabo de medir. **No lo doy por bueno** — son registros de GFX9.4 y
una coincidencia de nombres no es evidencia de que el hardware de GFX8 tenga la
misma estructura.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| L1 TLB: 5 campos, todos constantes | `PROVEN` (`gmc_v8_0.c:843-849`) |
| L2: 7 campos, 6 constantes | `PROVEN` (`gmc_v8_0.c:851-858`) |
| `EFFECTIVE_L2_QUEUE_SIZE = 7` es el máximo de 3 bits | `PROVEN` (máscara `0x38000`) |
| El L2 invalida por escritura a la PTE | `PROVEN` (`LRU_UPDATE_BY_WRITE` ×2) |
| El grano del L2 = fragmento de 2 MiB | `PROVEN` (`gmc_v8_0.c:865-869`) + `OBSERVED` |
| Un fragmento = 512 PTEEs de 4 KiB | `PROVEN` (`amdgpu_kms.c:1006`, `amdgpu_gart.h:35`) |
| No hay campo de tamaño de TLB | `PROVEN` (0 resultados) |
| Hay 64 políticas de L1 no programadas | `PROVEN` (`gfx_8_0_sh_mask.h` + 0 escrituras) |
| **Qué cuenta la TLB: PTEEs, bloques o páginas** | **`NOT_DETERMINED`** |
| Cuándo entra una entrada | `NOT_DETERMINED` |
| Qué son los 4 valores de una LOAD_POLICY | `NOT_DETERMINED` |

**La primera es la que `083` dejó abierta y sigue abierta.** Ahora se sabe
*por qué*: no es que falte el dato en el corpus, es que **el driver tampoco lo
tiene**. No hay campo de tamaño, no hay política programada, y no hay forma de
preguntarle al hardware con los registros que este driver usa. Para responderla
habría que buscar un registro de diagnóstico que no aparece en las cabeceras, o
medir por timing.

## Procedencia

- `STATIC` — `gmc_v8_0.c:842-870` y `:975-985`, `amdgpu_vm.c:2456-2459`,
  `amdgpu_kms.c:1006`, `amdgpu_gart.h:35-37`, `gfx_8_0_sh_mask.h`.
- `HOST_OBSERVATION` — `journalctl -k -b` (la línea de geometría de VM). Sólo
  lectura.
- Corrige `085` en sitio. Encadenada con `083` (la cierra en parte),
  `067`/`085` (el fragmento), `087` (el fichero que corre).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método.** Calculé `pte_fragment_size` con
`AMDGPU_GPU_PAGE_SIZE = 0x1000000` porque lo recordaba de otra generación, y
salió 8 GiB. El valor real es `4096` y está en `amdgpu_gart.h:35`, a cuatro
líneas de donde lo leí. **Nunca dar por buena una constante sin abrir el fichero
que la define**, aunque parezcabtenerla. Es la segunda vez hoy que una constante
recordada me da un número 64 veces mayor que el real.
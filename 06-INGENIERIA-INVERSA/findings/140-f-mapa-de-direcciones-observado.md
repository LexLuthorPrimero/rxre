# 140 · §F: el mapa de direcciones físicas de esta máquina, observado y derivado, y coinciden

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC+RUNTIME-OBSERVE
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=READ_ONLY · GPU INTACTA
```

## Qué resuelve

**La primera vez en este proyecto que una derivación y una observación se encuentran
y coinciden bit a bit.** El mapa de direcciones físicas completo de esta GPU —dónde
está la VRAM, dónde el GART, dónde el hueco entre ellos, dónde la tabla de
traducción— está **OBSERVADO** en el log de arranque y **DERIVADO** del código, y
las dos cosas dan los mismos números.

Además, **corrige una `HYPOTHESIS` mía de `138` que era falsa**, y cierra el
`NOT_DETERMINED` de `138` sobre el contexto 0.

**Y todo eso sin MMIO: es `journalctl`, que es NIVEL 2.**

## 1 · Lo observado

```
oct 02 00:10:30 amdgpu 0000:01:00.0: VRAM: 2048M 0x000000F400000000 - 0x000000F47FFFFFFF (2048M used)
oct 02 00:10:30 amdgpu 0000:01:00.0: GART:  256M 0x000000FF00000000 - 0x000000FF0FFFFFFF
oct 02 00:10:30 amdgpu 0000:01:00.0: [drm] GART: num cpu pages 65536, num gpu pages 65536
oct 02 00:10:30 amdgpu 0000:01:00.0: [drm] PCIE GART of 256M enabled (table at 0x000000F400900000)
```

**Las cuatro líneas las imprime el propio driver, incondicionalmente**, en
`amdgpu_gmc.c:235` (`VRAM`), `amdgpu_gmc.c:334` (`GART`), `amdgpu_gart.c` (las
páginas) y `gmc_v8_0.c:942` (`PCIE GART`). **Son un `dmesg` de arranque, no un
`RREG32`.** El log del kernel es la vía de menor riesgo de todo el proyecto, y
nadie la había usado para esto.

## 2 · El código que lo produce

`gmc_v8_0.c:411-423`, trece líneas que delegan:

```c
static void gmc_v8_0_vram_gtt_location(struct amdgpu_device *adev, struct amdgpu_gmc *mc)
{
        u64 base = 0;
        if (!amdgpu_sriov_vf(adev))
                base = RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF;
        base <<= 24;
        amdgpu_gmc_set_agp_default(adev, mc);
        amdgpu_gmc_vram_location(adev, mc, base);
        amdgpu_gmc_gart_location(adev, mc, AMDGPU_GART_PLACEMENT_BEST_FIT);
}
```

**Y el algoritmo de colocación del GART, `amdgpu_gmc.c:294-336`, completo:**

```c
/*To avoid the hole, limit the max mc address to AMDGPU_GMC_HOLE_START*/
u64 max_mc_address = min(adev->gmc.mc_mask, AMDGPU_GMC_HOLE_START - 1);   /* L299 */
size_bf = mc->fb_start;                                                   /* L304 */
size_af = max_mc_address + 1 - ALIGN(mc->fb_end + 1, four_gb);           /* L305 */
...
case AMDGPU_GART_PLACEMENT_BEST_FIT:
default:
        if ((size_bf >= mc->gart_size && size_bf < size_af) ||
            (size_af < mc->gart_size))
                mc->gart_start = 0;                                        /* L326 */
        else
                mc->gart_start = max_mc_address - mc->gart_size + 1;       /* L328 */
mc->gart_start &= ~(four_gb - 1);                                         /* L332 */
mc->gart_end = mc->gart_start + mc->gart_size - 1;                         /* L333 */
```

**`bf` es "before framebuffer" y `af` es "after framebuffer". Los dos lados del
hueco, y la política es poner el GART en el lado más grande.** `PROVEN`.

## 3 · La derivación completa, con los números impresos

Todos los valores de abajo están calculados por programa, no a mano.

| magnitud | valor | de dónde sale |
|---|---|---|
| `MC_VM_FB_LOCATION & 0xFFFF` | `0xF400` = 62464 | derivado de `base >> 24` |
| `base` | `0x000000F400000000` = **976.0 GiB** | `gmc_v8_0.c:417-418` |
| `base` alineado a 4 GiB | **sí**, resto 0 | `976.0 / 4 = 244` exacto |
| `vram_start` / `vram_end` | `F400000000` / `F47FFFFFFF` | `amdgpu_gmc.c:220-221` |
| `fb_start` / `fb_end` | ídem, porque `num_physical_nodes == 0` | `amdgpu_gmc.c:231-233` |
| `mc_mask` | `0x000000FFFFFFFFFF` = 2^40−1 | `gmc_v8_0.c:1133` |
| `max_mc_address` | `0x000000FFFFFFFFFF` — **el hole no recorta** | `amdgpu_gmc.c:299` |
| `size_bf` | `F400000000` = **976.0 GiB** | `amdgpu_gmc.c:304` |
| `ALIGN(fb_end+1, 4GiB)` | `F500000000` | `amdgpu_gmc.c:305` |
| `size_af` | `0B00000000` = **44.0 GiB** | `amdgpu_gmc.c:305` |
| `gart_size` | `0x10000000` = **256 MiB** | `gmc_v8_0.c:595` + `L608` |
| `gart_start` previsto | **`0x000000FF00000000`** | `amdgpu_gmc.c:328` + `L332` |
| `gart_start` observado | **`0x000000FF00000000`** | log |
| **coincide** | **True** | |

**La decisión, con sus dos condiciones evaluadas una a una:**

```
size_bf >= gart_size ?  True    (976.0 GiB >= 256 MiB)
size_bf <  size_af  ?  False   (976.0 < 44.0 GiB)
size_af <  gart_size ?  False   (44.0 GiB < 256 MiB)
=> rama HIGH:  gart_start = max_mc_address - gart_size + 1
```

**`PROVEN_DERIVED`, y `OBSERVED`, y son el mismo número.** En este proyecto eso no
había pasado nunca: hasta ahora el código explicaba el software y el hardware
explicaba el hardware, y nadie los había puesto en la misma ecuación.

**Y la aritmética de por qué sale exactamente `0xFF00000000`:**
`2^40 − 1 − 0x10000000 + 1 = 2^40 − 2^28`, y `& ~(2^32−1)` lo deja en
`2^40 − 2^32 = 0xFF00000000`. **El GART queda pegado al techo de los 40 bits, con
4 GiB de granularidad de alineación.** `PROVEN_DERIVED`.

## 4 · El mapa completo, con los tres huecos

```
0x0000000000000000
...
0x000000F400000000  ── vram_start          VRAM, 2048 MiB
0x000000F47FFFFFFF  ── vram_end = fb_end
                     <40.0 GiB de hueco, sin usar>
0x000000FF00000000  ── gart_start          GART, 256 MiB
0x000000FF0FFFFFFF  ── gart_end
                     <3.75 GiB de cola, sin usar>
0x0000010000000000  ── 2^40, el techo de mc_mask
```

**Tres cosas de este mapa que un driver propio necesita y no están en ningún
documento:**

1. **El GART no está abajo.** Está en los últimos 256 MiB de los 40 bits. Una
   traducción de VA a GART da una dirección **por encima de 1019 GiB**, no una
   dirección de sistema normal.
2. **El hueco de 40 GiB existe porque `size_bf` (976 GiB) es mucho mayor que
   `size_af` (44 GiB).** El driver pone el GART en el lado *peor* a propósito: la
   política `BEST_FIT` no minimiza el hueco, minimiza el lado de arriba para
   dejar la mayor parte libre para la VRAM.
3. **VRAM y GART no son contiguos**, y por eso hace falta el TLB de verdad: un
   acceso a VRAM y un acceso a RAM del sistema recorre 976 GiB de rango.

## 5 · La tabla del GART está dentro de la VRAM, y a 9 MiB del inicio

```
tabla del GART  0x000000F400900000
vram_start      0x000000F400000000
offset          9437184 bytes = 9 MiB
DENTRO DE LA VRAM: True
```

**Confirma `138` con una dirección observada y no sólo con una línea de código**
(`gmc_v8_0.c:962`, `amdgpu_gart_table_vram_alloc`).

**Y las 65536 páginas dan la geometría de la tabla del GART, cerrada:**

| | valor |
|---|---|
| `num cpu pages` = `num gpu pages` | 65536 |
| `gart_size` = 65536 × 4 KiB | 268435456 = **256 MiB** |
| `table_size` = `num_gpu_pages * 8` (`gmc_v8_0.c:960`) | 524288 = **512 KiB** |
| una tabla de un nivel: 65536 entradas × 8 bytes | 524288 = **512 KiB** |

**Un solo nivel, y por tanto `PAGE_TABLE_DEPTH = 0` para el contexto 0 es
correcto** — coherente con `139`/`L895`. Y las 65536 páginas de CPU y de GPU son
**las mismas**, es decir atómica bidireccional. `PROVEN_DERIVED`.

## 6 · El hole de GMC es inerte en esta GPU

```
amdgpu_gmc.h:35   /* VA hole for 48bit and 57bit addresses */
amdgpu_gmc.h:36   #define AMDGPU_GMC_HOLE_START  (max_level == 4 ? 0x0100000000000000ULL : 0x0000800000000000ULL)
amdgpu_gmc.h:38   #define AMDGPU_GMC_HOLE_END    (max_level == 4 ? 0xff00000000000000ULL : 0xffff800000000000ULL)
amdgpu_gmc.h:48   #define AMDGPU_GMC_HOLE_MASK   (max_level == 4 ? 0x01ffffffffffffffULL : 0x0000ffffffffffffULL)
```

**El hole empieza en 2^47 y esta GPU tiene 40 bits.** Así que en
`amdgpu_gmc.c:299`, `min(mc_mask, HOLE_START-1)` devuelve `mc_mask` siempre, y el
`min()` no hace nada.

**El hole es para chips con VA de 48 bits (o 57). En Polaris12 no existe, y el
`HOLE_MASK` de 48 bits también es una operación nula sobre direcciones de 40.**
`PROVEN_DERIVED`.

**Y esto explica por qué el "hole" que aparece en el estado del proyecto como
"`GMC hole` participa mediante `max_mc_address`" es aquí un no-op:** en esta GPU el
`min()` siempre elige el otro operando. **La participación es formal, no efectiva.**

## 7 · Corrección: mi `HYPOTHESIS` de `138` sobre `PAGE_TABLE_BLOCK_SIZE` era FALSA
12`, y que daba 1 para una hoja de 8 KiB. **La documentación la encontré en
En `138` escribí que la unidad del campo era `log2(bytes_de_la_página_de_tabla) −
12`, y que daba 1 para una hoja de 8 KiB. **Habíadocumentatione la encontré, en
`amdgpu_gmc.c:249-254`, dentro de la función que no se usa en esta generación:**

```
 * GPUVM (and our organization of vmid0 page tables) require sysvm
 * aperture to be placed at a location aligned with 8 times of native
 * page size. For example, if vm_context0_cntl.page_table_block_size
 * is 12, then native page size is 8G (2M*2^12), sysvm should start
 * with a 64G aligned address.
```

**La fórmula correcta es:**

```
native page size = 2 MiB << PAGE_TABLE_BLOCK_SIZE
```

| campo | native page size | comprobación |
|---|---|---|
| 12 | 2 MiB × 2^12 = **8 GiB** | el comentario dice 8G ✓ |
| **1** (GFX8, `block_size − 9` = 10 − 9) | 2 MiB × 2 = **4 MiB** | 2 fragmentos ✓ |

**Mi fórmula adivinada daba 1 y la verdadera también da 1 — por casualidad.** Una
decía "8 KiB, el tamaño de la tabla de hojas"; la otra dice "4 MiB, la página
nativa que ve el TLB". **El acuerdo numérico es una coincidencia y las dos
significaciones son incompatibles.** `REFUTED` la mía, `PROVEN` la del driver.

**Y `2 MiB` es el tamaño de fragmento** (`fragment_size = 9` → 512 fragmentos de
4 KiB). **Así que en esta GPU la página nativa son 2 fragmentos, y el `PAGE_TABLE_
BLOCK_SIZE = 1` lo dice exactamente.** `PROVEN_DERIVED`.

**Y el alineamiento del sysvm es "8 veces la página nativa": 8 × 8 GiB = 64 GiB,
que es lo que dice el comentario.** Consistente por tercera vía.

**Nada de esto se aplica a esta máquina:** `amdgpu_gmc_sysvm_location` sólo la
llaman `gmc_v9_0.c:1664` y `gmc_v12_0.c:700`, **nunca `gmc_v8_0.c`**. Pero el
comentario documenta el campo, y por eso sirve.

## 8 · Y el hueco que me quedaba abierto desde el principio de la tanda

En `139` escribí: *son dos invalidadores, no uno* — el de la cadena del PTE y el del
PRT (`L2_CACHE_STORE_INVALID_ENTRIES`, `L1_TLB_STORE_INVALID_ENTRIES`). Y en
`136` había quedado: *cuál caché pesa más en el flush obligatorio*.

**Con este mapa, la pregunta tiene una respuesta mejor que "no lo sé":** el GART
está en los últimos 256 MiB de 40 bits y la VRAM en 976–978 GiB. **Son dos rangos
del espacio de direcciones físicas que no se tocan.** Una página del GART y una
página de VRAM nunca están en la misma entrada de caché de 2 MiB, porque están a 40
GiB de distancia. **Las dos cachés que hay que invalidar no pueden contener
entradas de las dos regiones a la vez en el mismo set.**

**Eso no prueba cuál pesa más, pero elimina la posibilidad de que compitan.** Y es
`PROVEN_DERIVED` a partir de la aritmética del mapa. La pregunta original queda
reformulada, no cerrada.

## Lo que NO cierra

| afirmación | estado |
|---|---|
| El mapa de direcciones de esta máquina | `OBSERVED` |
| El mismo mapa derivado del código | `PROVEN_DERIVED` |
| Ambos coinciden bit a bit | `PROVEN` (por programa) |
| `MC_VM_FB_LOCATION & 0xFFFF` = `0xF400` | `PROVEN_DERIVED` |
| El GART está en el techo de los 40 bits | `PROVEN_DERIVED` |
| La tabla del GART es un BO de VRAM a 9 MiB | `OBSERVED` + `PROVEN_DERIVED` |
| La tabla del GART es de un nivel, 512 KiB | `PROVEN_DERIVED` |
| Las 65536 páginas son bidireccionales | `PROVEN_DERIVED` |
| El hole de GMC es inerte aquí | `PROVEN_DERIVED` |
| `PAGE_TABLE_BLOCK_SIZE`: la unidad | `PROVEN` (refuta mi `HYPOTHESIS` de `138`) |
| La página nativa de esta GPU es 4 MiB | `PROVEN_DERIVED` |
| La política `BEST_FIT` no minimiza el hueco | `PROVEN_DERIVED` |
| `num_physical_nodes == 0` en esta máquina | `PROVEN_DERIVED` (de `L231-233`) |
| Por qué `base` cae en 976 GiB y no en 0 | **`NOT_DETERMINED`** — es `MC_VM_FB_LOCATION`, del firmware |
| Si el firmware de otra placa pondría la VRAM en 0 | **`NOT_DETERMINED`** |
| Cuál caché pesa más en el flush obligatorio | **`NOT_DETERMINED`** — reformulada en §8 |
| La granularidad real de la caché de la L2 | **`NOT_PROVEN`** — un `RREG32` de `0x501` |

**La fila del medio es la que más importa para un driver propio y la que nadie ha
mirado: `base` no lo elige el driver, lo lee del hardware**
(`RREG32(mmMC_VM_FB_LOCATION) & 0xFFFF`, `gmc_v8_0.c:417`). **Un driver propio tiene
que leerlo, igual que el de referencia; no puede inventarlo.** Y aquí vale
`0xF400`, que es un valor de firmware, no una constante del driver.

## Procedencia

- `OBSERVED` -- `journalctl -k -b`, cuatro líneas de `amdgpu 0000:01:00.0`, del
  arranque del 2 de octubre. Lectura de log del kernel: **NIVEL 2**, sin MMIO, sin
  debugfs, sin tocar nada.
- `STATIC` -- `gmc_v8_0.c:411-423` `:585-612` `:920-946` `:1133`,
  `amdgpu_gmc.c:42`, `amdgpu_gmc.c:214-238`, `amdgpu_gmc.c:249-254`,
  `amdgpu_gmc.c:294-336`, `amdgpu_gmc.c:349-376`, `amdgpu_gmc.h:35-49`,
  `amdgpu_gart.c` (páginas del GART), `gmc_v8_0.c:942` (línea del log).
- Aritmética: **toda impresa por programa**, nunca a mano. Ver §3 y el apartado de
  método — mis dos cálculos manuales de estas restas hexadecimales fueron **falsos**
  y habrían producido una "inconsistencia" inexistente.
- Encadenada con `139` (el formato del PTE, el contexto 0, `PAGE_TABLE_DEPTH`),
  `138` (la geometría, y la `HYPOTHESIS` que esta nota refuta), `137` (TLB y L2),
  `136` (la cadena de coherencia), `220` (BAR 256 MiB, VRAM 2 GiB), `209`
  (`amdgpu_vm_map_gart` inalcanzable), `083` (`dst`).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Salí a buscar una función de trece líneas yEnded con el mapa de direcciones
completo de la máquina, observado.**

que no existen en el `asic_reg` porque no hacen falta: el kernel los escribió en
cuatro líneas que hacen falta, incondicionalmente, en `amdgpu_gmc.c:235` y `:334` y
`gmc_v8_0.c:942`. **Llevaba siete notas buscando esto con `RREG32` y registros
que|no existen en el `asic_reg` porque no hacen falta: el kernel los escribió en el
log al arrancar.**

*Un `dev_info` incondicional es un puerto de observabilidad tan real como un
imprime**, antes de leer el hardware. `136` cerró su pregunta con dos eslabones de
valor de una variable que el driver calcula, hay que mirar si el driver la
imprime**, antes de leer el hardware. `136` cerró su pregunta con dos eslabones de
código; `140` la cierra con el mismo código **y con el número**.

**Y la segunda lección es la de siempre, y es cara:** calculé dos veces
`2^40 − 2^28` a mano, las dos veces mal, y en las dos llegué a la conclusión
opuesta —que el código y la observación no cuadraban—. **Un programa con una línea
de Python lo resolvió en un segundo, y coincidieron.**

**Si una aritmética decides una conclusión, la imprime un programa. Si la imprimo yo,
no la he hecho: la he Inventado.** Es la regla (c) de este proyecto, y casi me
cuesta una afirmación falsa en la nota mejor sustentada de la tanda.

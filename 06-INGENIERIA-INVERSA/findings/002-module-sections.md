# 002 — Secciones del ELF de `amdgpu.ko`

**Clasificación**: `READ_ONLY/EVIDENCE`
**Fecha**: 2026-09-29
**Objeto**: `amdgpu-analysis/amdgpu.ko`, SHA256 `a1a44c2457d33c65149ef4f455173ca446564bfd19bcc9cb215fca10cf24c024`
(ver `001-amdgpu-location.md` §3)
**Volcado completo**: `amdgpu-analysis/sections.txt` (295 líneas, `readelf -S` + `objdump -h`)

---

## 1. Secciones principales con tamaño

Del total de 37 494 368 B del ELF:

| Sección | Tipo | Offset | Tamaño | % del fichero |
|---|---|---|---|---|
| `.text` | PROGBITS | `0x038868` | **9 617 163 B** (9,17 MiB) | 25,6 % |
| `.rodata` | PROGBITS | `0x9ae848` | **2 972 372 B** (2,83 MiB) | 7,9 % |
| `.data` | PROGBITS | `0x964778` | 303 312 B | 0,8 % |
| `.modinfo` | PROGBITS | `0xcae6b6` | 48 211 B | 0,1 % |
| `.bss` | NOBITS | `0x964778` | 258 240 B | 0,7 % |
| `.static_call.text` | PROGBITS | `0xceed20` | 384 B | — |
| `.init.text` | PROGBITS | `0xcae5e8` | 137 B | — |
| `.exit.text` | PROGBITS | `0xcae678` | 62 B | — |
| `.init.data` | PROGBITS | `0xcba318` | 8 B | — |
| `.exit.data` | PROGBITS | `0xcba310` | 8 B | — |
| `.ref.data` | PROGBITS | `0xcef620` | 3 816 B | — |

Comandos:

```bash
readelf -S amdgpu-analysis/amdgpu.ko > amdgpu-analysis/sections.txt
objdump -h amdgpu-analysis/amdgpu.ko >> amdgpu-analysis/sections.txt
```

**`.text` + `.rela.*` no suman el tamaño del fichero, y ninguna de las dos lo explica.** Reparto
real por tipo de sección, sobre los 35,8 MiB del ELF:

| Tipo | Suma | % |
|---|---|---|
| `PROGBITS` | 19 376 476 B (18,48 MiB) | 51,7 % |
| `RELA` | **15 734 160 B (15,01 MiB)** | 41,9 % |
| `SYMTAB` | 1 574 712 B (1,50 MiB) | 4,2 % |
| `STRTAB` | 802 725 B (0,77 MiB) | 2,1 % |
| `NOBITS` (`.bss`) | 258 240 B | 0,7 % |

**Las secciones de relocalización son 15,01 MiB, el 42 % del fichero.** Es lo esperable: un
`.ko` es relocatable y cada referencia a símbolo necesita su entrada `R_X86_64_*`. El código
ejecutable real es 9,17 MiB, no 35,8. Hay además 89 cabeceras de sección para 51 secciones con
contenido.

Comando: `readelf -SW … | sed 's/^ *\[ *[0-9]*\] *//' | awk '{s[$2]+=strtonum("0x"$5)}'`.

> Nota de método: un primer cálculo de `.rela.*` por `objdump -h` devolvió 0, porque `objdump`
> no lista las secciones `.rela.*` de este objeto. La cifra de arriba sale de `readelf -SW` y
> está verificada contra el total. Registrarlo porque un `0` de un parser se parece a un dato
> real y no lo es.

## 2. Qué sección contiene los strings de nombres de IP blocks

**`.rodata`**, 2,83 MiB, `PROGBITS` de solo lectura. Concentrada: aquí viven las tablas de
nombres de IP blocks, los nombres de ASIC y las tablas de lookup.

Comprobado: 872 cadenas coinciden con `gfx_v8|polaris|compute` (volcadas en
`amdgpu-analysis/strings-relevant.txt`), y 698 de ellas contienen `amdgpu_gfx`. Como el objeto
no está stripped, esos nombres aparecen **a la vez** en `.rodata` (tablas) y en la tabla de
símbolos; `.rodata` es la copia que el código consulta en runtime.

**Para los mapas de registros la vía correcta no es `.rodata`:** los offsets de registro no se
extraen de cadenas, se leen en
`RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/` (§6).

## 3. Qué sección contiene los símbolos exportados

**Ninguna, en el sentido de tabla de símbolos exportados: `amdgpu.ko` no exporta símbolos.**

La pregunta tiene tres respuestas distintas según qué se entienda por "exportado":

| Sentido | Dónde | Resultado |
|---|---|---|
| Tabla de símbolos dinámicos | `.dynsym` | **Ausente.** `nm -D` → `no hay símbolos`. Un `.ko` es relocatable, no un objeto ya enlazado |
| Símbolos de texto y datos | `.symtab` | 65 596 entradas, 34 773 de tipo `T`/`t`. Locales al módulo |
| API para otros módulos | `__ksymtab` | **4 símbolos**, ninguno de compute. Ver abajo |

**La API exportada real son 4 símbolos, y están en `__ksymtab`, no en `.modinfo`:**

```
isp_user_buffer_alloc      T  0x8d5040
isp_user_buffer_free       T  0x8d5180
isp_kernel_buffer_alloc    T  0x8d51a0
isp_kernel_buffer_free     T  0x8d51c0
```

Comandos: `readelf -SW … | grep __ksymtab` (`__ksymtab` 30 B, `__ksymtab_strings` 0x5e = 94 B) y
`readelf -p __ksymtab_strings …`. Los cuatro son del subsistema **ISP** (codificación de vídeo),
no de compute: cero coincidencias con `ring|gfx|compute|kfifo|sdma`.

**Lo que NO es la API exportada:** las 311 entradas `alias=` de `.modinfo` son **todas** IDs de
PCI (`pci:v00001002d00001304sv*sd*bc*sc*i*` y familiares), no símbolos. Verificado:

```bash
readelf -p .modinfo amdgpu-analysis/amdgpu.ko | sed -n 's/.*alias=\(.*\)/\1/p' | cut -c1-3 | sort | uniq -c
# 311 pci
```

Las demás claves de `.modinfo` están presentes y son coherentes con un módulo normal:
`depends=drm_exec,ttm,drm_display_helper,amdxcp,gpu-sched,…` (13 dependencias), `retpoline=Y`,
`intree=Y`, 96 pares `parm`/`parmtype`, 694 `firmware=`.

**Corrección de un error propio:** una versión anterior de este documento afirmaba "cero
`EXPORT_SYMBOL`", leído de que las 311 entradas `alias=` no eran símbolos. La inferencia iba en
la dirección correcta pero la conclusión era falsa: existen 4, en `__ksymtab`. El error fue
buscar la tabla de exportación solo en `.modinfo`; en el kernel está en una sección con nombre
propio. La consecuencia para IA-2 no cambia (§ abajo), pero el dato sí.

**Consecuencia para IA-2:** de los símbolos que el plan de compute necesita —
`amdgpu_gfx_enable_kgq`, `amdgpu_gfx_enable_kcq`, `amdgpu_fence_emit`, `amdgpu_ring_init`—
**ninguno es exportable**. Son `T` locales en `.symtab`, y la única API que el módulo ofrece a
otros son 4 funciones de ISP. Un driver propio no puede enlazar contra el driver original de
compute: tendría que **reimplementar** la secuencia de setup de la cola KCQ, no invocarla. Esto
cambia el plan de Fase 4 y por eso va en un documento sobre secciones.

## 4. `.modinfo`: inventario de las 3 clases de entrada

| Clave | Entradas | Qué es |
|---|---|---|
| `firmware=` | 694 | blobs de firmware que el módulo puede cargar |
| `alias=` | 311 | IDs de PCI que casa. **No son símbolos** |
| `parm=` / `parmtype=` | 96 / 96 | parámetros de módulo con tipo |
| `license`, `author`, `description`, `depends`, `name`, `srcversion`, `vermagic`, `intree`, `retpoline` | 1 cada | metadatos |

`license=GPL and additional rights` es la condición bajo la que se puede reutilizar código. El
módulo es GPL: un driver propio derivado de él debe cumplir GPL, y esa decisión legal es de IA-3,
no mía.

## 5. Las 96 entradas `parm`: los interruptores que gobiernan la GPU

Muestra (las que afectan a la partición de hardware y a compute):

| Parámetro | Valores | Efecto |
|---|---|---|
| `dpm` | `-1/0/1` | Power management. `-1` auto |
| `aspm` | `-1/0/1` | Active State Power Management |
| `pp_dpm_sclk` | intervalo de clocks | Rango de reloj de shader |
| `pp_dpm_mclk` | intervalo | Rango de reloj de memoria |
| `rebar` | `-1/0/1` | Resizable BAR |
| `user_queue` | `-1/0/1/2` | **User queues.** `2` = habilita UQ y deshabilita KQs |

`user_queue=2` es el interruptor más relevante para Fase 4: deshabilita las colas de kernel
(`KQ`) y deja solo las de usuario. Si un driver propio usa user queues, ese es el parámetro que
gobierna el terreno. Los 96 parámetros están en `amdgpu-analysis/sections.txt` y se pueden volcar
íntegros con `modinfo`.

## 6. Consecuencia para el método: la fuente C está disponible

`.rodata` y `.symtab` responden **qué nombres existen**, no **qué significan**. Para el contenido
—el tipo de cada parámetro de ring, el orden de escritura de registros, la estructura de una
page table— la fuente es:

```
RESEARCH/working/linux-7.1.3/drivers/gpu/drm/amd/amdgpu/
```

Archivos previstos para el mapa de compute:

| Fichero | Contenido esperado |
|---|---|
| `amdgpu.h` | `struct amdgpu_device` (líneas 858-1201), punteros a KCQ/KGQ |
| `amdgpu_ring.h` | `struct amdgpu_ring`, `amdgpu_queue`, `AMDGPU_MAX_...` |
| `amdgpu_kcq.c` / `amdgpu_kgq.c` | setup de la cola, equivalente C de `enable_kcq`/`enable_kgq` |
| `amdgpu_sdma.c` | **el más importante**: submission de paquetes PM4 |
| `amdgpu_vm.c` | page tables. `DEC-1` ya establece que la geometría es por dispositivo (`:2433-2440`) |

Esto reduce la dependencia de Ghidra, que no está instalado en este host (ver `001` §5 y el
aviso de la ronda 1).

## Procedencia

Tamaños y offsets de `readelf -SW` sobre el ELF de SHA256
`a1a44c24…`, 2026-09-29. El recuento de `alias=` por prefijo y la clasificación de `.modinfo` se
obtuvieron con `readelf -p .modinfo` y `cut`/`sort`/`uniq` sobre la misma salida. Ningún valor
transcrito.

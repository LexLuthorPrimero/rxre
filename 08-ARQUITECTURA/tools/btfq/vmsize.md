# vmsize — la geometría de page tables, modelada desde el corpus y confirmada por el host

## Qué mide

`amdgpu_vm_adjust_size` decide la geometría de page tables y la registra al
arrancar. Este script construye el modelo desde el corpus y lo compara contra
el **log real de este host**, que es una observación y no una suposición.

```
MODELO (corpus 7.1.3)          HOST (journalctl -k -b)
  vm_size    = 64 GB             vm_size    = 64 GB     coincide
  num_level  = 1                 num_level  = 1         coincide
  block_size = 10                block_size = 10        coincide
  fragment   = 9                 fragment   = 9         coincide
```

`rc=0`. El corpus predice correctamente la geometría del hardware real.

## La contradicción que casi se declara

Durante este análisis se sospechó que **el driver del host estuviera
parcheado**. El razonamiento era aparentemente sólido:

- El host registra `2 levels`.
- El corpus llama `amdgpu_vm_adjust_size(adev, 64, 9, 1, 40)`, es decir
  `max_level = 1`.
- `amdgpu_vm.c:2429` hace `num_level = min_t(max_level, tmp)`, y `min_t(1, tmp)`
  **no puede** dar 2.
- Se verificó además que `num_level` no se escribe en ningún otro sitio del
  driver: la única escritura es esa línea, y `gfxhub_v1_0.c`,
  `gfxhub_v1_2.c`, `gfxhub_v12_1.c` y `gmc_v9_0.c` solo lo leen.
- El host identifica la GPU como `POLARIS12 0x1002:0x699F` / `gfx_v8_0_0`, que es
  exactamente el ASIC de `gmc_v8_0.c`, así que no era otro ASIC.
- El log tiene exactamente **una** entrada, así que no era un segundo
  `adjust_size`.

**Era falso.** `amdgpu_vm.c:2462-2464` imprime:

```c
"vm size is %u GB, %u levels, block size is %u-bit, fragment size is %u-bit\n",
vm_size, adev->vm_manager.num_level + 1,      /* <-- el +1 */
adev->vm_manager.block_size, adev->vm_manager.fragment_size);
```

`2 levels` en el log significa `num_level == 1`, que es exactamente lo que el
corpus predice. No hay parche.

**La lección que sí sobrevive**: el razonamiento era correcto en cada paso
individual, y aun así llevaba a una contradicción falsa. La regla que lo
impide es `READ_SCOPE_GATE`: antes de declarar divergencia contra una
observación, hay que leer el **productor de esa observación** entero, no solo el
cálculo que se compara contra ella. Aquí faltaba leer el `dev_info`, que es la
transformation que convierte el estado interno en el texto del log.

Un `+1` en un `dev_info` es el tipo de detalle que produce
`PROVEN_ABSENT` falsos con una confianza muy alta, porque el resto del
razonamiento encaja perfectamente.

## Corroboración independiente

El mismo corpus predice también la geometría de GART:

- `gmc_v8_0.c:595`: `adev->gmc.gart_size = 256ULL << 20;` para `CHIP_POLARIS12`
- host: `GART: 256M 0x000000FF00000000 - 0x000000FF0FFFFFFF`
- host: `GART: num cpu pages 65536` = `256 MiB / 4 KiB` (`amdgpu_gart.c:532`)

Son geometrías independientes (GPUVM vs MC address space), calculadas por
código distinto, y ambas coinciden. Dos aciertos que no comparten la ruta de
cálculo son mucho más fuertes que uno solo.

## Los dos errores del modelo que hubo que corregir

**1. Qué magnitud se pasa a `get_block_size`.**

Mi primera versión pasaba `max_pfn` y salía `block_size = 22`, luego `23`. El
fuente en `amdgpu_vm.c:2454` pasa **`tmp`**, y `tmp` en ese punto ya fue
reescrito en `:2428` por `DIV_ROUND_UP(fls64(tmp)-1, 9) - 1`, así que vale `2`, no
`max_pfn`. Corregido, el modelo da `10` y coincide con el host.

Esto importa más allá de este script: `22` y `23` son números plausibles y no
obviamente falsos. Un error que produce un número plausible es peor que un
error visible.

**2. Que el log imprime `num_level + 1`.** Descrito arriba.

Los dos errores eran del modelo, no del corpus. En ambos casos la respuesta
correcta era leer más fuente, no ajustar el modelo para que encajara.

## Sobre `get_block_size`

```c
unsigned bits = ilog2(vm_size) + 18;
if (vm_size <= 8)
        return (bits - 9);
else
        return ((bits + 3) / 2);
```

El parámetro se llama `vm_size` pero el único llamador le pasa `tmp`, que ya no
es un tamaño de VM sino un número pequeño derivado del número de niveles. La
rama `vm_size <= 8` compara, por tanto, una magnitud que ya no significa lo que
su nombre indica.

Se reproduce **tal cual**, sin «corregirlo». El objetivo es modelar lo que el
driver hace, no lo que debería hacer. Corregirlo aquí sería inventar un driver
distinto del que corre.

## Geometría resultante

```
num_level    = 1        (+ raíz PDB0 -> 2 niveles de PDE)
block_size   = 10 bits  -> PTB de 2^10 = 1024 entradas
                         -> un PTB cubre 1024 paginas de 4 KiB = 4 MiB
fragment     = 9 bits   -> 512 entradas de fragmento
vm_size      = 64 GiB
GPUVA        = 40 bits (max_bits del adjust_size)
```

Con `fragment_size = 9`, las 1024 entradas de un PTB se agrupan en
`1024 / 2^9 = 2` páginas físicas de 2 MiB cada una.

## Clasificación epistémica

| Afirmación | Estado |
|---|---|
| `block_size = 10` en GFX8 | **PROVEN** — modelo y log coinciden, dos vías |
| `num_level = 1` (log: "2 levels") | **PROVEN** — observación directa |
| `fragment_size = 9` | **PROVEN** |
| GART = 256 MiB en POLARIS12 | **PROVEN** — corpus y log |
| el driver del host está parcheado | **REFUTED** — era el `+1` del `dev_info` |
| semántica de hardware de cada bit de PTE | **NOT_DETERMINED** — requiere runtime con root |

## Lo que sigue sin determinar

Los parámetros de módulo (`/sys/module/amdgpu/parameters/amdgpu_vm_size`,
`amdgpu_vm_block_size`, `amdgpu_vm_fragment_size`) **no son legibles sin root**.
El modelo asume el modo automático y lo dice en la salida en vez de callarlo.

Con los valores por defecto el resultado coincide con el host, así que el modo
automático está confirmado para esta máquina **indirectamente**: si el host
hubiera forzado parámetros, la coincidencia de los cuatro valores sería
coincidencia. Es la explicación más económica, no una prueba de que los
parámetros valgan `-1`.

Intentos de conseguir el código real del módulo cargado:

- `/usr/src/kernels/7.1.3-200.nobara.fc44.x86_64/drivers/gpu/drm/amd/amdgpu/`
  contiene **solo `Kconfig` y `Makefile`**; el código del driver va en un
  paquete aparte en Fedora.
- `/sys/kernel/btf/amdgpu` da la firma de `amdgpu_vm_adjust_size` pero no su
  código: BTF describe tipos, no instrucciones.

Sin root no hay vía para leer el módulo cargado.

## Uso

```sh
./vmsize.py
```

`0` si el modelo reproduce al host, `1` si diverge. Con el corpus actual
devuelve `0`.
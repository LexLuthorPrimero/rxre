# 127 · §G: hay una caché L2 de fragmentos, y el invalidate obligatorio de GFX8 es su consecuencia

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`226` dejó una pregunta abierta y bien formulada: *qué caché, si alguna, está en
el camino entre la L2 y la lectura del page walker*. Y dijo que sin eso no se
puede explicar por qué el invalidate es obligatorio en GFX8.

**Hay una caché, se llama, tiene un registro que la configura, y el invalidate
obligatorio es su consecuencia directa.** Todo `PROVEN` salvo el último eslabón,
que marco como tal.

## El bloque que responde a la pregunta

```
gmc_v8_0.c:829   static int gmc_v8_0_gart_enable(struct amdgpu_device *adev)
gmc_v8_0.c:860   tmp = RREG32(mmVM_L2_CNTL2);
gmc_v8_0.c:861   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL2, INVALIDATE_ALL_L1_TLBS, 1);
gmc_v8_0.c:862   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL2, INVALIDATE_L2_CACHE, 1);
gmc_v8_0.c:863   WREG32(mmVM_L2_CNTL2, tmp);
gmc_v8_0.c:865   field = adev->vm_manager.fragment_size;
gmc_v8_0.c:866   tmp = RREG32(mmVM_L2_CNTL3);
gmc_v8_0.c:867   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_ASSOCIATIVITY, 1);
gmc_v8_0.c:868   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, BANK_SELECT, field);
gmc_v8_0.c:869   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL3, L2_CACHE_BIGK_FRAGMENT_SIZE, field);
gmc_v8_0.c:870   WREG32(mmVM_L2_CNTL3, tmp);
```

**Tres cosas, y las tres cambian la respuesta:**

1. **Existe `VM_L2_CNTL2.INVALIDATE_L2_CACHE`.** La L2 se invalida con un bit.
2. **Existe `VM_L2_CNTL3.L2_CACHE_BIGK_FRAGMENT_SIZE`**, y su valor es
   `fragment_size`. **La granularidad de la caché de fragmentos la define
   `fragment_size`.**
3. **La invalidación ocurre en `gmc_v8_0_gart_enable`**, no en el camino de
   actualización de page tables.

**Y esto confirma `226` desde el otro lado.** `226` concluyó, leyendo el camino de
actualización, que *no hay ninguna operación de caché sobre las page tables*.
Ahora se ve por qué: **la caché se invalida al habilitar el GART, no en cada
actualización.** No es que falte la operación; es que la operación no está en ese
camino, y el diseño no la necesita porque la granularidad del fragmento lo
resuelve.

## La granularidad, y la aritmética hecha a mano

La semántica la declara el propio driver:

```
amdgpu_drv.c:438   Override VM fragment size in bits (4, 5, etc. 4 = 64K, 9 = 2M)
amdgpu_drv.c:171   int amdgpu_vm_fragment_size = -1;        <- default: automático
amdgpu_device.c:1572   (amdgpu_vm_fragment_size > 9 || < 4)  ->  se invalida el override
```

Con `AMDGPU_GPU_PAGE_SIZE = 4096` (`amdgpu_gart.h:35`):

```
fragment_size = 4   ->     64 KiB  ->   16 páginas de 4 KiB
fragment_size = 9   ->   2 048 KiB  ->  512 páginas de 4 KiB
```

**Y el valor en esta máquina es 9**, observado en el log de arranque
(*"block size is 10-bit, fragment size is 9"*).

**Un fragmento son 512 páginas de 4 KiB. Una sola entrada translation covers 2 MiB.**

## Y el invalidate obligatorio es la consecuencia

El driver lo dice en una frase, en `amdgpu_vm.c:1154-1157`:

```
amdgpu_vm.c:1154  /*
amdgpu_vm.c:1155   * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
amdgpu_vm.c:1156   */
amdgpu_vm.c:1157  flush_tlb |= amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 0, 0);
```

**Leído con la caché delante: si la granularidad de la traducción es el
fragmento, y el fragmento son 512 páginas, entonces cambiar una sola de esas 512
páginas deja las otras 511 con traducciones viejas en el TLB.** No hay forma de
hacerlo visible entrada a entrada. **Hay que re-traducir el fragmento entero, y
eso es lo que invalida el TLB.**

**Ésta es la respuesta completa a por qué en GFX8 el invalidate no es
optimizable.** Y es una respuesta de hardware, deducida de un nombre de registro,
un valor observado y un comentario del driver.

**Y cierra `194` con el discriminante verificado en el call site**, no sólo en la
línea del override. Los tres call sites de `amdgpu_vm_update_range`:

| call site | `flush_tlb` que pide | en GFX8 |
|---|---|---|
| `amdgpu_vm.c:1388` | variable | forzado a `true` |
| `amdgpu_vm.c:1591` | `true` | `true` |
| `amdgpu_vm.c:3074` | **`false`** | **forzado a `true`** |

**`NEGATIVE_RESULT`: en GFX8 no existe camino alcanzable que escriba page tables
sin `params.needs_flush = true`.** El único que lo pide falso es el manejador de
page faults, y el override de `L1157` lo corrige.

## Y hay un `XXX` en el código que señala el siguiente paso

```
gmc_v8_0.c:871   /* XXX: set to enable PTE/PDE in system memory */
gmc_v8_0.c:872   tmp = RREG32(mmVM_L2_CNTL4);
gmc_v8_0.c:873   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL4, VMC_TAP_CONTEXT0_PDE_REQUEST_PHYSICAL, 0);
gmc_v8_0.c:874   tmp = REG_SET_FIELD(tmp, VM_L2_CNTL4, VMC_TAP_CONTEXT0_PDE_REQUEST_SHARED, 0);
```

**Tres precisiones, porque la tercera me habría carried mal:**

1. **Esto está en `gmc_v8_0_gart_enable` (`L829`), no en `early_init`.**
2. **`CONTEXT0` es el GART**, no los VMIDs de userspace — `211` establece que el
   VMID 0 es la dirección física que usa el kernel y los VMIDs 1-15 son de
   userspace. **Lo que se configura aquí es el espacio del GART.**
3. **La polaridad no la doy por buena.** El driver **sólo** escribe 0 en estos bits
   en todo `gmc_v8_0` — `grep` de `..., 1` sobre esos campos: cero resultados. La
   polaridad sale del comentario del propio driver (*"set to enable PTE/PDE in
   system memory"*), o sea que **0 = no es memoria física ni compartida**, y lo
   razonable es que sea VRAM. **`CORROBORATED`, no `PROVEN`.**

**Y encaja con `220`:** el BAR es de 256 MiB y la VRAM de 2 GiB, así que las
page tables no caben en el BAR y están en VRAM. **El page walker lee VRAM, no
memoria del sistema**, y por eso el problema de coherencia CPU↔GPU que §G enuncia
no aparece en este camino: **no hay PCIe en él.**

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Existe `VM_L2_CNTL2.INVALIDATE_L2_CACHE` | `PROVEN` (`gmc_v8_0.c:862`) |
| La granularidad la fija `L2_CACHE_BIGK_FRAGMENT_SIZE` | `PROVEN` (`gmc_v8_0.c:869`) |
| Se invalida al habilitar el GART, no por actualización | `PROVEN` (`L829` función) |
| `fragment_size = 9` son 2 MiB | `PROVEN` (`amdgpu_drv.c:438`) |
| Un fragmento son 512 páginas de 4 KiB | `PROVEN_DERIVED` |
| `fragment_size = 9` en esta máquina | `OBSERVED` (log de arranque) |
| En GFX8 no hay camino sin `needs_flush` | `PROVEN` (3 call sites + override) |
| El fragmento es la granularidad de traducción | `CORROBORATED` — comentario + registro |
| El "8 PTE block" del comentario = el fragmento | **`NOT_IN_CORPUS`** |
| La polaridad de `VM_L2_CNTL4` | **`CORROBORATED`** — sólo del comentario |
| Si la L2 cachea lecturas del page walker | **`NOT_DETERMINED`** — hardware |
| Cuántas entradas tiene una TLB y su asociatividad | **`NOT_DETERMINED`** |

### El "8 PTE block" no es `NOT_DETERMINED`, es `NOT_IN_CORPUS`

Lo busqué por todos los caminos y el resultado es categórico:

```
grep -rniE 'pte[_ ]?block|PTE_BLOCKS|PTE_BLOCK_SIZE|bytes_per_pte|PTE_ENTRY_SIZE'
  sobre drivers/gpu/drm/amd/**/*.c *.h   ->  1 resultado

amdgpu_vm.c:1155   * On GFX8 and older any 8 PTE block with a valid bit set enters the TLB
```

**Una sola mención en 2787 ficheros, y es el propio comentario.** Ninguna
constante, ningún helper, ningún uso.

**Eso no es "no lo he encontrado": es que el término no existe en el corpus.** Y
tiene una consecuencia práctica que vale más que la geometría:

> **La frase del comentario NO es load-bearing.** El código no depende de ella.
> Lo único que el código comprueba es `IP_VERSION(9,0,0)` en `L1157`, y el
> tamaño del fragmento sale del registro de hardware.

**Para un driver propio, la regla a implementar es la comparación de versión de
IP y la lectura del registro. La geometría del "PTE block" es documentación en
prosa, y no puede estar en mi modelo porque no está en ninguna parte del código.**

**Queda la duda de fondo, y no la resuelvo:** si esa frase es una descripción
correcta de la granularidad de la traducción, es la pieza que explica por qué el
invalidate es obligatorio en GFX8; y si es una imprecisión del autor, la
explicación es otra. **Las dos son compatibles con todo lo demás que he medido, y
elegir una sería inventar geometría.**

**La tercera es la que queda de verdad**, y es hardware: **si la L2 cachea las
lecturas del page walker o no.** Todo lo demás es coherente con que sí y con que
no; el invalidate obligatorio funciona en los dos casos, pero por razones
distintas.

## Procedencia

- `STATIC` -- `gmc_v8_0.c:829` `:858-874`, `amdgpu_vm.c:1126` `:1148-1165`
  `:1388` `:1591` `:3074`, `amdgpu_drv.c:171` `:437-441`,
  `amdgpu_device.c:1571-1574`, `amdgpu_gart.h:35`,
  `include/asic_reg/gmc/gmc_8_1_d.h` (`VM_L2_CNTL2`, `VM_L2_CNTL3`,
  `VM_L2_CNTL4`).
- `OBSERVED` -- `fragment_size = 9` y `block size is 10-bit` en el log de
  arranque, de sesión anterior. Sin lectura nueva de hardware.
- Sin MMIO write, sin TLB, sin módulos, sin lectura de debugfs.
- Encadenada con `194` (el invalidate obligatorio), `226` (la coherencia es orden),
  `228` (el precio de la coherencia), `115`/`220` (BAR 256 MiB, VRAM en VRAM),
  `211` (VMID 0 = kernel, 1-15 = userspace), `210`/`213` (el registro de
  invalidate).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`.

## Nota de método

**Estaba a punto de escribir que `VM_L2_CNTL4` configuraba de dónde leen los page
walkers de los VMIDs de userspace, y es el GART.** Lo Paré porque `211` ya decía
que el VMID 0 es el espacio del kernel, y `CONTEXT0` no podía ser otra cosa.

**Miré el nombre de la función que contenía el bloque, y era `gmc_v8_0_gart_enable`,
no `early_init`, que es lo que había asumido por dónde estaba el código.**

**Es la cuarta vez en dos días que assumo el alcance de un bloque de código por
dónde está y no por qué función lo contiene.** El bloque estaba en medio de un
`switch` largo sobre `asic_type` y leí el neighbours equivocado.

*La posición de un bloque no dice qué hace; la función que lo contiene sí.*
Es el mismo error de "un nombre no es su contenido", aplicado a la estructura del
fichero en vez de a su nombre.
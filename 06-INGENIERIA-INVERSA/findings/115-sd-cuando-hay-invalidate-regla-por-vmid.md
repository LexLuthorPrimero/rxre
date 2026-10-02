# 115 · §D: cuándo hay invalidate -- es una marca de agua por VMID, y aquí no se puede reutilizar un VMID que necesite flush

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HARDWARE_ID
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 (PCI 1002:699f)
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=NOT_RUN · GPU INTACTA
```

## Qué resuelve

`113` dejó abierto el eslabón real: qué pone `job->vm_needs_flush`, que es lo que
decide **cuándo** hay un invalidate. Esta nota lo cierra, y el resultado es más
fuerte de lo que `113` suponía.

## Los seis escritores

`job->vm_needs_flush` es un `bool` (`amdgpu_job.h:76`) y se escribe en seis
sitios. **Ninguno es "estoy enviando un frame".**

| # | lugar | qué pone |
|---|---|---|
| 1 | `amdgpu_ids.c:307` | el valor de `needs_flush` calculado en `grab_idle` |
| 2 | `amdgpu_ids.c:334` | `vm->use_cpu_for_update` |
| 3 | `amdgpu_ids.c:367` | `|= needs_flush` de `grab_used` |
| 4 | `amdgpu_ids.c:420` | **`true` incondicional** |
| 5 | `amdgpu_ttm.c:2428` | `true` (vía TTM) |
| 6 | `amdgpu_gmc.c:758` | **`true` incondicional** |

## Y las cuatro razones por las que un VMID necesita flush

`amdgpu_ids.c:266-277`, en `amdgpu_vmid_grab_idle`:

```
amdgpu_ids.c:266   bool needs_flush = vm->use_cpu_for_update;
amdgpu_ids.c:267   uint64_t updates = amdgpu_vm_tlb_seq(vm);
amdgpu_ids.c:271   if ((*id)->owner != vm->immediate.fence_context ||
amdgpu_ids.c:273       (*id)->flushed_updates < updates ||
amdgpu_ids.c:274       !(*id)->last_flush ||
amdgpu_ids.c:275       ((*id)->last_flush->context != fence_context &&
amdgpu_ids.c:276        !dma_fence_is_signaled((*id)->last_flush)))
amdgpu_ids.c:277       needs_flush = true;
```

Las cuatro, textualmente:

1. **`vm->use_cpu_for_update`** -- las page tables las escribió la CPU, no la GPU
2. **`owner != vm->immediate.fence_context`** -- lo está usando otro contexto
3. **`flushed_updates < updates`** -- las page tables cambiaron desde el último flush
4. **`!last_flush || (last_flush de otra cola y sin señalar)`** -- no hay flush
   registrado, o hay uno en vuelo desde otra cola

`amdgpu_vmid_grab_used` (`amdgpu_ids.c:338-353`) tiene **tres** de las cuatro; el
`owner` ahí es un `continue` previo (`L341`), no un motivo de flush.

**El motivo por el que más importa es el 3.** Y para eso existe la marca de agua.

## La marca de agua: `flushed_updates`

`amdgpu_ids.c:427-431`, inmediatamente después de elegir el VMID:

```
amdgpu_ids.c:427   if (job->vm_needs_flush) {
amdgpu_ids.c:428       id->flushed_updates = amdgpu_vm_tlb_seq(vm);
amdgpu_ids.c:429       dma_fence_put(id->last_flush);
amdgpu_ids.c:430       id->last_flush = NULL;
amdgpu_ids.c:431   }
```

**`flushed_updates` es, literalmente, "qué revisión de las page tables ha visto ya
el GPU para este VMID".** Se compara contra `amdgpu_vm_tlb_seq(vm)`, y el kernel
lo dice en prosa en `amdgpu_vm.h:630-635`:

> Returns the tlb flush sequence number which indicates that the VM TLBs needs to
> be invalidated whenever the sequence number change.

**El invalidate no es por frame ni por job: es por cambio de revisión de page
tables, medido por VMID.** Eso es `PROVEN`, con las tres cosas verificadas por
separado: la comparación (`L352`), el sitio donde se escribe la marca (`L428`) y
la definición del número (`amdgpu_vm.h:630-635`).

## Y aquí no se puede reutilizar un VMID que necesite flush

Este es el resultado que `113` no tenía, y es el que cambia la utilidad de todo
lo anterior.

```
amdgpu_ids.c:355   if (needs_flush && !adev->vm_manager.concurrent_flush)
amdgpu_ids.c:356       continue;
```

**Si `concurrent_flush` es falso, un VMID que necesita flush queda descartado del
bucle de reutilización.** No se reutiliza "con flush"; no se reutiliza.

Y lo mismo en `grab_idle`, `amdgpu_ids.c:279-280`:

```
amdgpu_ids.c:279   if ((*id)->owner != vm->immediate.fence_context ||
amdgpu_ids.c:280       (!adev->vm_manager.concurrent_flush && needs_flush)) {
```

**En esta GPU, la regla es:**

> si las page tables cambiaron, el VMID no se puede reutilizar;
> hay que rotar a otro VMID, y ese camino pone `vm_needs_flush = true`
> incondicionalmente (`amdgpu_ids.c:420`).

**O sea: en la RX550, un cambio de page tables no se puede amortizar.** No es
"flush barato de vez en cuando": es "cada cambio de page tables cuesta un invalidate
y un VMID nuevo". Esa es la consecuencia operativa, y es la que importa para
escribir un driver propio.

## Cómo sé que `concurrent_flush` es falso aquí

`amdgpu_vm.c:2870-2875`, con el comentario del driver:

```
amdgpu_vm.c:2870   /* Concurrent flushes are only possible starting with Vega10 and
amdgpu_vm.c:2871    * are broken on Navi10 and Navi14.
amdgpu_vm.c:2872    */
amdgpu_vm.c:2873   adev->vm_manager.concurrent_flush = !(adev->asic_type < CHIP_VEGA10 ||
amdgpu_vm.c:2874                                      adev->asic_type == CHIP_NAVI10 ||
amdgpu_vm.c:2875                                      adev->asic_type == CHIP_NAVI14);
```

**El enum de chips no está en el corpus.** `amdgpu_drv.h` tiene 52 líneas y cero
entradas `CHIP_*`; todas las apariciones de `CHIP_*` en el corpus son usos, nunca
definiciones. **Comparar `CHIP_POLARIS12 < CHIP_VEGA10` es `NOT_IN_CORPUS`.**

Pero el driver tiene **una segunda formulación de esa misma frontera, y esa sí es
derivable**:

```
amdgpu_vm.c:1157   flush_tlb |= amdgpu_ip_version(adev, GC_HWIP, 0) < IP_VERSION(9, 0, 0);
```

(`085`). Y la versión de IP sí se deriva del corpus, toda la cadena:

| paso | fuente | valor |
|---|---|---|
| ID de dispositivo real | `lspci -nn -d 1002:` | `1002:699f`, *Lexa PRO*, rev c7 |
| ese ID es Polaris12 | `amdgpu_drv.c:2041` | `CHIP_POLARIS12` |
| Polaris12 usa el IP block de gfx8 | `vi.c:2107-2112` | `gfx_v8_0_ip_block` |
| ese IP block declara | `gfx_v8_0.c:7130-7134` | `type=GFX, major=8, minor=0, rev=0` |
| empaquetado | `amdgpu_ip.h:77-79` | `IP_VERSION(mj,mn,rv) = (mj<<24)|(mn<<16)|(rv<<8)` |

Y la aritmética, hecha a mano:

```
IP_VERSION(8,0,0) = 0x08000000
IP_VERSION(9,0,0) = 0x09000000
0x08000000 < 0x09000000   ->  verdadero
```

**Las dos formulaciones del driver — enum y versión de IP — devislan la misma
frontera GFX8/GFX9, y por la de versión de IP la respuesta es que sí.** Las dos
cosas que `115` necesita se siguen una de la otra.

**El enum ausente queda registrado como hueco de corpus**, porque afecta a toda
cita futura a `amdgpu_drv.h`: el fichero resuelve, tiene 52 líneas, y no contiene
lo que su nombre sugiere. `citecheck` lo daría por bueno.

## Un autocorrección dentro de esta misma nota

Escribí en mi razonamiento que Polaris12 es `IP_VERSION(8,1,0)`, por el nombre
`gfx_v8_0.c` y porque los registros de GMC que cito en otras notas son
`gmc_8_1_d.h`. **Lo declarado es `major=8, minor=0, rev=0`.** Lo vi al leer
`gfx_v8_0_ip_block`, no antes.

**Da igual para la comparación** -- lo que decide es el major, 8 frente a 9 -- pero
es el mismo error de siempre: **inferir un valor de un nombre de fichero en vez de
mirar la declaración.** Un nombre no es un contenido. Lo cometí siete veces hoy con
nombres de fichero y una vez aquí con un número.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| Seis escritores de `vm_needs_flush` | `PROVEN` |
| Las cuatro razones de `needs_flush` | `PROVEN` (`amdgpu_ids.c:266-277`) |
| `flushed_updates` es la marca de agua | `PROVEN` (`L428`, `amdgpu_vm.h:630-635`) |
| El invalidate es por revisión de page tables | `PROVEN_DERIVED` |
| Con `concurrent_flush` falso no se reutiliza un VMID que necesite flush | `PROVEN` (`L355`, `L279-280`) |
| El enum de chips no está en el corpus | `OBSERVED` (`amdgpu_drv.h`, 52 líneas) |
| `CHIP_POLARIS12` es esta GPU | `PROVEN` (`amdgpu_drv.c:2041` + ID observado) |
| `GC_HWIP` de esta GPU es 8.0.0 | `PROVEN` (`vi.c:2112` + `gfx_v8_0.c:7131-7133`) |
| `concurrent_flush == false` en la RX550 | `PROVEN_DERIVED` |
| Los 16 clientes usan `use_cpu_for_update` | **`NOT_DETERMINED`** |
| Si el hardware GFX8.1 se declara como 8.0.0 a propósito | **`NOT_DETERMINED`** |

**La penúltima decide la frecuencia real y no la he medido.**
`use_cpu_for_update` es el motivo 1, y `102` ya estableció que el camino de escritura
por CPU es inalcanzable sin `AMDGPU_GEM_CREATE_CPU_ACCESS_REQUIRED`. Si ningún
cliente lo pide, el motivo 1 nunca dispara. **Pero no lo he comprobado sobre los
16 clientes, y `102` no lo comprobó para esta variable.**

**Y la última es una discrepancia real que dejo abierta:** el siliconio es GFX8.1
-- hay `gmc_8_1_d.h`, `gmc_8_2_*` para contraste, y `gmc_v8_0.c` tiene un
`case CHIP_POLARIS12` propio -- y sin embargo el IP block declara `8.0.0`.
**No sé si es que la IP pública de Polaris12 se registra como 8.0.0 a propósito, o
si es que el block se reutiliza.** No lo resuelvo por suposición.

## Procedencia

- `STATIC` -- `amdgpu_ids.c:208-432`, `amdgpu_vm.c:2868-2878` y `:1157`,
  `amdgpu_vm.h:627-642`, `amdgpu_ip.h:74-86`, `vi.c:2049-2116`,
  `gfx_v8_0.c:7128-7135`, `amdgpu_drv.c:2041`, `amdgpu_job.h:76`,
  `amdgpu_gmc.c:748-762`, `amdgpu_ttm.c:2412-2428`.
- `HARDWARE_ID` -- `lspci -nn -d 1002:` da `1002:699f`, rev c7. Sólo lectura.
- Sin MMIO write, sin TLB, sin módulos, sin cambiar parámetros.
- **Corrige `113`**: `113` decía que el invalidate es raro porque el compositor
  no cambia de buffers. **Eso es cierto pero es la consecuencia, no la regla.** La
  regla es que en esta GPU un cambio de page tables no es amortizable en un
  VMID existente, porque `amdgpu_ids.c:355` descarta el VMID.
- Encadenada con `085` (el invalidate obligatorio), `094` (el presupuesto),
  `111`/`113` (la secuencia y la frecuencia), `102` (el camino CPU/SDMA),
  `108`/`109` (los motores).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.
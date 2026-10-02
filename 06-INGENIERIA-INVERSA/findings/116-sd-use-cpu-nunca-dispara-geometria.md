# 116 · §D: el motivo 1 de los cuatro no dispara nunca aquí — por geometría de memoria, no por casualidad

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 (PCI 1002:699f)
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA
```

## Qué resuelve

`115` dejó cuatro razones por las que un VMID necesita flush, y "`use_cpu_for_update`
en los 16 clientes" como `NOT_DETERMINED`. **Esta nota lo cierra, y la respuesta es
que ese motivo no puede dispararse en esta máquina.**

## No es por cliente: es un modo global del driver

`vm_needs_flush` sí se asigna por job. **`use_cpu_for_update` no.** Se calcula una
vez, al crear cada VM, desde un único valor del dispositivo:

```
amdgpu_vm.c:2626   vm->use_cpu_for_update = !!(adev->vm_manager.vm_update_mode &
amdgpu_vm.c:2627   AMDGPU_VM_USE_CPU_FOR_GFX);
amdgpu_vm.c:2735   vm->use_cpu_for_update = !!(adev->vm_manager.vm_update_mode &
amdgpu_vm.c:2736   AMDGPU_VM_USE_CPU_FOR_COMPUTE);
```

```
amdgpu_vm.h:185   #define AMDGPU_VM_USE_CPU_FOR_GFX     (1 << 0)    = 1
amdgpu_vm.h:186   #define AMDGPU_VM_USE_CPU_FOR_COMPUTE (1 << 1)    = 2
```

Dos caminos distintos, GFX y compute, **ambos leen el mismo `vm_update_mode`**. Y
ese valor se decide una vez:

```
amdgpu_vm.c:2884  #ifdef CONFIG_X86_64
amdgpu_vm.c:2885   if (amdgpu_vm_update_mode == -1) {
amdgpu_vm.c:2889       if (amdgpu_gmc_vram_full_visible(&adev->gmc) &&
amdgpu_vm.c:2890           !amdgpu_sriov_vf_mmio_access_protection(adev))
amdgpu_vm.c:2891           adev->vm_manager.vm_update_mode = AMDGPU_VM_USE_CPU_FOR_COMPUTE;
amdgpu_vm.c:2893       else
amdgpu_vm.c:2894           adev->vm_manager.vm_update_mode = 0;
amdgpu_vm.c:2895   } else
amdgpu_vm.c:2896       adev->vm_manager.vm_update_mode = amdgpu_vm_update_mode;
```

**El comentario lo dice en la línea 2881:** *"If not overridden by the user, by
default, only in large BAR systems Compute VM tables will be updated by CPU"*.

**`AMDGPU_VM_USE_CPU_FOR_GFX` = 1 no lo pone nunca el camino por defecto.** Sólo un
usuario que pase `vm_update_mode=1` por línea de órdenes. **El valor por defecto es
`-1` (`amdgpu_drv.c:174`), y el valor real en esta máquina también.**

## La cadena completa, eslabón por eslabón

**Eslabón 1 — el parámetro no está sobrescrito.** Observado:

```
/sys/module/amdgpu/parameters/vm_update_mode = -1
```

(`module_param_named(vm_update_mode, ...)` en `amdgpu_drv.c:463`. El nombre del
parámetro es `vm_update_mode`; el de la variable es `amdgpu_vm_update_mode`. No son
lo mismo, y yo probé primero el segundo.)

⇒ Se toma la rama `L2885`, la del default.

**Eslabón 2 — `vram_full_visible` es falso.** La comparación:

```
amdgpu_gmc.h:394   static inline bool amdgpu_gmc_vram_full_visible(struct amdgpu_gmc *gmc)
amdgpu_gmc.h:396       WARN_ON(gmc->real_vram_size < gmc->visible_vram_size);
amdgpu_gmc.h:398       return (gmc->real_vram_size == gmc->visible_vram_size);
```

Y los dos tamaños:

```
gmc_v8_0.c:568   adev->gmc.real_vram_size    = adev->gmc.mc_vram_size;
gmc_v8_0.c:576   adev->gmc.aper_size          = pci_resource_len(adev->pdev, 0);
gmc_v8_0.c:585   adev->gmc.visible_vram_size = adev->gmc.aper_size;
```

**Los dos, observados:**

| magnitud | valor | fuente |
|---|---|---|
| `real_vram_size` | **2147483648** = 2.00 GiB | `/sys/class/drm/card1/device/mem_info_vram_total` |
| BAR 0 (`aper_size`) | **256M** | `lspci -v -s 01:00.0`: `Memory at e0000000 (64-bit, prefetchable) [size=256M]` |

```
2147483648 != 268435456     ==>  vram_full_visible = false
```

**Y hay un atajo en el código que podría haber cambiado el resultado**, así que
hay que descartarlo explícitamente:

```
gmc_v8_0.c:578  #ifdef CONFIG_X86_64
gmc_v8_0.c:579   if ((adev->flags & AMD_IS_APU) && !amdgpu_passthrough(adev)) {
gmc_v8_0.c:581       adev->gmc.aper_size = adev->gmc.real_vram_size;
gmc_v8_0.c:582   }
gmc_v8_0.c:583  #endif
```

Si esta tarjeta fuera APU, `aper_size` valdría 2 GiB, `visible == real`, y
`vram_full_visible` sería **cierto**. **Hay que probar que no lo es.** Y el switch
que pone ese flag lo hace:

```
amdgpu_discovery.c:3105   switch (amdgpu_ip_version(adev, GC_HWIP, 0)) {
amdgpu_discovery.c:3106   case IP_VERSION(9, 1, 0):
     ... majors 9, 10, 11, 12 ...
amdgpu_discovery.c:3122       adev->flags |= AMD_IS_APU;
amdgpu_discovery.c:3124   default:
amdgpu_discovery.c:3125       break;
```

**Cero entradas `IP_VERSION(8,*,*)` en todo el switch.** Verificado contando:
`awk 'NR>=3093 && NR<=3124' | grep -cE 'IP_VERSION\(8,'` → **0**.

Como esta GPU es GFX major 8 (`115`, cadena completa), cae en `default`, y
**`AMD_IS_APU` no se pone**. El único otro sitio que lo pone
(`amdgpu_discovery.c:3297`) está en un switch de SMUIO para `IP_VERSION(13,0,11)`,
que no aplica.

**⇒ el atajo de `L579-582` no se ejecuta. `aper_size` se queda en 256 MB.**

**Eslabón 3 — `vm_update_mode` queda en 0.** De `L2889` falso ⇒ `L2894`.

**Eslabón 4 — los dos `use_cpu_for_update` quedan en falso.**

```
0 & (1 << 0)  = 0   ->  use_cpu_for_update del VM de GFX     = false   (amdgpu_vm.c:2626)
0 & (1 << 1)  = 0   ->  use_cpu_for_update del VM de compute = false   (amdgpu_vm.c:2735)
```

## La conclusión

**Para los 16 clientes, y también para el kernel, y también para el GART:**
`use_cpu_for_update` es `false`.

**Y esto no es una casualidad de esta sesión ni del compositor.** Es geometría de
memoria: 2 GiB de VRAM detrás de un BAR de 256 MiB. **Con la VRAM no enteramente
visible por el BAR, el driver no usa nunca la CPU para escribir page tables**, y
por tanto **el motivo 1 de `115` es inalcanzable por construcción**.

**Y con eso, de los cuatro motivos de `115` queda exactamente uno que depende de
que la memoria cambie, y tres que dependen del estado del scheduler:**

| motivo | dispara aquí | por qué |
|---|---|---|
| 1 `use_cpu_for_update` | **nunca** | `2 GiB != 256 MiB` ⇒ `vm_update_mode = 0` |
| 2 `owner != fence_context` | sí | otro contexto usó el VMID |
| 3 `flushed_updates < tlb_seq` | sí | las page tables cambiaron |
| 4 `!last_flush` o flush ajeno en vuelo | sí | estado del fence |

**Esto corrige el énfasis de `115`.** `115` destacó el motivo 3 porque es "el
importante", pero los motivos 2 y 4 no tienen nada que ver con page tables: son
**estado del scheduler**. **Un job puede necesitar flush porque otro contexto usó
ese VMID hace un momento, sin que ninguna page table haya cambiado.**

**Y como `concurrent_flush` es falso, un VMID que necesite flush no se reutiliza
(`amdgpu_ids.c:355`), así que los motivos 2 y 4 no sólo limitan la frecuencia:
forzan rotación de VMID.** Lo que parecía un detalle de estado del scheduler
resulta ser tan determinante como el cambio de page tables.

## Y la frontera GFX8/GFX9 la dice el corpus por partida cuádruple

`115` derivó `concurrent_flush == false` por versión de IP porque el enum de chips no
está en el corpus. Esta nota encuentra **tres enunciados más, independientes**, y
**los cuatro coinciden**:

| # | dónde | cómo lo dice |
|---|---|---|
| 1 | `amdgpu_vm.c:1157` | `GC_HWIP < IP_VERSION(9,0,0)` (`085`) |
| 2 | `amdgpu_vm.c:2870` | prosa: *"only possible starting with Vega10"* |
| 3 | `amdgpu_discovery.c:3106` | la lista de APU **empieza** en `IP_VERSION(9,1,0)` |
| 4 | `vi.c:104-106` | `ASIC_IS_P22` cubre `POLARIS10..POLARIS12`, y se acaba ahí |

**Los cuatro son del driver, ninguno necesita el enum, y los cuatroponer GFX8 antes
que GFX9.** La enumeración del APU (`#3`) es la que más me gusta: no compara nada,
simplemente **empieza** en 9.1.0, así que 8.x queda fuera por construcción.

**Para un driver propio esto es un aviso de método:** la frontera que necesito está
escrita en el corpus cuatro veces de cuatro maneras distintas, y aun así la primera
vez que la necesité me bloqueó un `grep` vacío sobre el enum. **`NOT_IN_CORPUS` es la
etiqueta de un fichero concreto, no de un dato.** El dato estaba en cuatro sitios.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| `use_cpu_for_update` es global, no por cliente | `PROVEN` (`L2626`, `L2735`) |
| `AMDGPU_VM_USE_CPU_FOR_GFX` no lo pone el default | `PROVEN` (`L2891`, `L2894`) |
| `vm_update_mode = -1` en esta máquina | `OBSERVED` |
| `real_vram_size` = 2 GiB | `OBSERVED` |
| `aper_size` = 256 MiB | `OBSERVED` (`lspci`) |
| `AMD_IS_APU` no se pone en GFX8 | `PROVEN` (`L3105-3125`, cero casos `IP_VERSION(8,*)`) |
| `vram_full_visible` = falso | `PROVEN_DERIVED` |
| `vm_update_mode` = 0 | `PROVEN_DERIVED` |
| `use_cpu_for_update` = falso en GFX y compute | `PROVEN_DERIVED` |
| Motivo 1 inalcanzable en esta máquina | `PROVEN_DERIVED` |
| Con qué frecuencia disparan los motivos 2 y 4 | **`NOT_DETERMINED`** |
| Si `amdgpu_passthrough` podría cambiar el eslabón 2 | **`NOT_DETERMINED`** |

**La penúltima es la que queda, y es la frecuencia real del invalidate.** Ya no es
`NOT_DETERMINED` por no haber leído el scheduler -- ya lo leí. Es que **no hay
observador**: los motivos 2 y 4 son estado de `dma_fence` y de una lista LRU dentro
del driver, y no se exponen en debugfs. **`NOT_DETERMINED` de verdad, no
`no-lo-he-buscado`.**

**La última la dejo anotada por prudencia:** `L579` exige `&& !amdgpu_passthrough`,
y no he comprobado el valor de `amdgpu_passthrough`. En una máquina normal es falso
y no cambia nada, pero es un predicado que no verifiqué.

## Procedencia

- `OBSERVED` -- `/sys/module/amdgpu/parameters/vm_update_mode` (= -1),
  `/sys/class/drm/card1/device/mem_info_vram_total` (= 2147483648),
  `lspci -v -s 01:00.0` (BAR 0 = 256M, rev c7). Sólo lectura, sin MMIO write.
- `STATIC` -- `amdgpu_vm.c:2618-2650`, `:2728-2750`, `:2868-2902`,
  `amdgpu_gmc.h:387-399`, `gmc_v8_0.c:566-585`,
  `amdgpu_discovery.c:3105-3125`, `amdgpu_vm.h:185-186`, `vi.c:104-106`,
  `amdgpu_drv.c:174` y `:463`, `amdgpu_ids.c:338-356` y `:266-277`.
- Encadenada con `115` (los cuatro motivos), `113`/`111` (la secuencia y la
  frecuencia), `102` (que ya había dicho que `vram_full_visible` era falso -- ahora
  verificado por una ruta independiente), `085` (el invalidate obligatorio).
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Dos notas de método, y las dos sobre mí.**

La primera: **busqué `/sys/module/amdgpu/parameters/amdgpu_vm_update_mode` y no
existe.** El nombre del parámetro es `vm_update_mode`; el de la variable interna es
`amdgpu_vm_update_mode`. Lo tenía delante en `amdgpu_drv.c:174` y `:463` y no lo
miré. **Novena vez hoy con nombres: un nombre no es su contenido.**

La segunda, y es la que me importa: **`102` ya había dicho que
`amdgpu_gmc_vram_full_visible` era falso aquí, y yo lo di por sabido al escribir
`115`.** Acabo de recorrerlo entero, por una ruta distinta, y llega a lo mismo.
**Pero lo escribí en `115` como premisa y no lo había vuelto a mirar.**

Es el error opuesto al de `111` -- allí anoté una contradicción sin resolverla,
aquí di por buena una verdad sin comprobar que sigiera siendo cierta. **Los dos
son la misma cosa: un dato que no vuelve a mirarse cuando debería.**
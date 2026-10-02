# 102 · §A/§D: el punto de despacho CPU↔SDMA, y por qué en esta GPU no hay forma de elegir CPU

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

`AGENTS.md` ya knew que "CPU page-table writer inalcanzable bajo política
efectiva" y que "SDMA es el writer efectivo". Eso es el **resultado**.

Lo que nadie había leído es **la decisión**: dónde se toma, sobre qué condición,
y qué alternativas existen. Y el resultado tiene un detalle que cambia la
lectura.

## La decisión

```
amdgpu_vm.c:2881   /* If not overridden by the user, by default, only in large BAR systems
amdgpu_vm.c:2882    * Compute VM tables will be updated by CPU
amdgpu_vm.c:2883    */
amdgpu_vm.c:2885   if (amdgpu_vm_update_mode == -1) {
amdgpu_vm.c:2889       if (amdgpu_gmc_vram_full_visible(&adev->gmc) &&
amdgpu_vm.c:2890           !amdgpu_sriov_vf_mmio_access_protection(adev))
amdgpu_vm.c:2891           adev->vm_manager.vm_update_mode = AMDGPU_VM_USE_CPU_FOR_COMPUTE;
amdgpu_vm.c:2893       else
amdgpu_vm.c:2894           adev->vm_manager.vm_update_mode = 0;
amdgpu_vm.c:2896   } else
amdgpu_vm.c:2896       adev->vm_manager.vm_update_mode = amdgpu_vm_update_mode;
```

Y la condición, que es una sola línea:

```
amdgpu_gmc.h:394   static inline bool amdgpu_gmc_vram_full_visible(struct amdgpu_gmc *gmc)
amdgpu_gmc.h:396       WARN_ON(gmc->real_vram_size < gmc->visible_vram_size);
amdgpu_gmc.h:398       return (gmc->real_vram_size == gmc->visible_vram_size);
```

**`real_vram_size == visible_vram_size`.** Eso es todo. Y es una propiedad del
**hardware**: en concreto, de lo grande que sea la BAR.

## Y los dos únicos flags que existen

```
AMDGPU_VM_USE_CPU_FOR_GFX       (1 << 0)
AMDGPU_VM_USE_CPU_FOR_COMPUTE  (1 << 1)
```

Sólo dos. Y **el camino automático de `L2891` sólo puede activar COMPUTE.**

**No hay ninguna ruta automática que active `AMDGPU_VM_USE_CPU_FOR_GFX`.** Ni
siquiera en un sistema con BAR grande. Para que una VM de graphics escriba sus
page tables por CPU hay que pasarle el parámetro a mano:

```
vm_update_mode = 1     sólo graphics
vm_update_mode = 2     sólo compute
vm_update_mode = 3     ambos
vm_update_mode = 0     nunca          <- el default efectivo de esta máquina
```

**Para un driver propio eso es la respuesta operativa:** no hay una knob que
copiar para graphics. O escribes las page tables por CPU, o no. No es un
"normalmente sí, aquí no": es que la rama no existe en el default.

## El punto de despacho, y es uno solo

```
amdgpu_vm.c:2626   vm->use_cpu_for_update = !!(adev->vm_manager.vm_update_mode &
amdgpu_vm.c:2627                                   AMDGPU_VM_USE_CPU_FOR_GFX);
amdgpu_vm.c:2635   if (vm->use_cpu_for_update)
amdgpu_vm.c:2636       vm->update_funcs = &amdgpu_vm_cpu_funcs;
amdgpu_vm.c:2637   else
amdgpu_vm.c:2638       vm->update_funcs = &amdgpu_vm_sdma_funcs;
```

**`vm->update_funcs` es el puntero que decide todo**, y se fija **una vez**, al
crear la VM. Después, cada actualización va por la tabla que se haya elegido. Es
un despacho de dos, no una decisión por operación.

Eso confirma y precisa lo que `085`/`074` tenían: el camino de CPU existe
(`amdgpu_vm_cpu_funcs`) y es real, pero **en esta ruta no se instancia**.

## La cadena completa, evaluada con valores observados

| paso | fuente | valor |
|---|---|---|
| parámetro del módulo | **sysfs, en esta máquina** | `-1` |
| `amdgpu_vm.c:2885` (`== -1`) | `PROVEN` | True |
| `real_vram_size` | `086`, log de arranque | 2048 MiB |
| `visible_vram_size` | `086`, `mem_info_vis_vram_total` | 256 MiB |
| `amdgpu_gmc.h:398` (`real == visible`) | `PROVEN` | **False** |
| `amdgpu_vm.c:2889` (`&&`) | `PROVEN` | False ⇒ va a `L2894` |
| `amdgpu_vm.c:2894` | `PROVEN` | **`vm_update_mode = 0`** |
| `amdgpu_vm.c:2626` (GFX) | `PROVEN` | `0 & 1 = 0` ⇒ `use_cpu = false` |
| `amdgpu_vm.c:2735` (COMPUTE) | `PROVEN` | `0 & 2 = 0` ⇒ `use_cpu = false` |
| `amdgpu_vm.c:2638` / `L2743` | `PROVEN` | **`&amdgpu_vm_sdma_funcs`** en ambas |

**El único input observado por mí en toda la cadena es el parámetro**, leído de
`/sys/module/amdgpu/parameters/vm_update_mode`. Los dos números de VRAM son los
de `086`. Todo lo demás es `PROVEN` por lectura.

**Y la causa raíz es hardware**: la BAR son 256 MiB y la VRAM son 2048 MiB. No
es una preferencia del driver ni una política del sistema.

## Y hay un aviso que lo dice explícitamente

```
amdgpu_vm.c:2631   WARN_ONCE((vm->use_cpu_for_update &&
amdgpu_vm.c:2632              !amdgpu_gmc_vram_full_visible(&adev->gmc)),
amdgpu_vm.c:2633              "CPU update of VM recommended only for large BAR system\n");
```

**El kernel avisa si alguien fuerza CPU sin BAR grande.** Es un `WARN_ONCE`, así
que suena una vez por proceso. En esta máquina **no aparece en el log**, y eso
es consistente: nadie ha forzado nada.

Pero es una confirmación útil: si alguien ve el texto en un log, sabrá
inmediatamente que está en la configuración que este hardware no soporta.

## El detalle que cambia la lectura: el cambio de escritor no es gratis

El camino de **compute** hace algo que el de **graphics** no hace:

```
amdgpu_vm.c:2743   if (vm->use_cpu_for_update) {
amdgpu_vm.c:2744       /* Sync with last SDMA update/clear before switching to CPU */
amdgpu_vm.c:2745       r = amdgpu_bo_sync_wait(vm->root.bo,
amdgpu_vm.c:2746                     AMDGPU_FENCE_OWNER_UNDEFINED, true);
```

**Y graphics no tiene ese sync.** No es una omisión: es que graphics **no puede
cambiar de escritor en runtime**, porque el default no lo pone y no hay código
que lo ponga. Compute sí puede, y por eso necesita sincronizar antes.

**Consecuencia para un driver propio:** si permites cambiar de escritor, el
cambio **no es un cambio de puntero**, es una barrera. `amdgpu_bo_sync_wait` con
el fence de la última operación SDMA es lo que garantiza que no haya un update
en vuelo. Sin eso, cambiar de tabla de funciones a mitad de una secuencia deja
PTEs escritas a medias por dos escritores distintos.

**Y esto es `§D` sin depender de F1**: es la semaphore entre "quién escribe" y
"cuándo se puede cambiar", y es software puro.

## Lo que NO cierra

| Afirmación | Estado |
|---|---|
| La decisión está en `amdgpu_vm.c:2881-2899` | `PROVEN` |
| La condición es `real_vram_size == visible_vram_size` | `PROVEN` (`amdgpu_gmc.h:398`) |
| El default automático sólo puede activar COMPUTE | `PROVEN` (`L2891`) |
| No hay ruta automática a GFX | `PROVEN_ABSENT` |
| `vm_update_mode` efectivo = 0 | `PROVEN_DERIVED` + `OBSERVED` (parámetro) |
| Ambas VMs usan `amdgpu_vm_sdma_funcs` | `PROVEN_DERIVED` |
| Cambiar de escritor exige sincronizar | `PROVEN` (`L2744-2746`, sólo compute) |
| Qué hace exactamente `amdgpu_vm_cpu_funcs` | `NOT_DETERMINED` — inalcanzable aquí |
| Si un modo mixto sería más rápido o más seguro | `NOT_DETERMINED` |
| Por qué AMD eligió que compute sea el único automático | `NOT_DETERMINED` |

**La sexta fila es un `PROVEN_DERIVED`, no un `PROVEN`.** El salto de "el puntero
vale `&amdgpu_vm_sdma_funcs`" a "las dos VMs lo usan" requiere saber que se crean
al menos una VM de graphics y una de compute, que no he medido. Es muy
probable, pero no lo he comprobado.

## Procedencia

- `HOST_OBSERVATION` — `/sys/module/amdgpu/parameters/vm_update_mode`. Sólo
  lectura. El resto de los números de VRAM son los de `086`.
- `STATIC` — `amdgpu_vm.c:2618-2648` y `:2728-2750` y `:2881-2899`,
  `amdgpu_gmc.h:386-399`, `amdgpu_drv.c:457-463`.
- Sin MMIO write, sin TLB, sin módulos, sin cambiar parámetros.
- Encadenada con `086` (BAR 256 MiB / VRAM 2048 MiB), `074` y `085` (el camino de
  CPU que queda fuera de ruta), `087` (GMC 8.1).
- Precisa el estado que `AGENTS.md` ya tenía; no lo contradice.
- No se editó `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de método, sobre el primer error de la sesión.**

Propuse investigar **`amdgpu_page_table_update`** como la función de la decisión.
**Esa función no existe en este kernel.** La propuse de memoria, en el informe
anterior, sin verificar el nombre. Es la undécima vez que nombro algo que no
existe, y la máscara del error fue peor que las otras: no era un nombre
parecido, era un nombre inventado con aspecto de función real.

Lo cazó el primer `grep` que hice. Si hubiera usado el `xref.py` que ya tengo
—que además de buscar nombres cuenta usos en `*.c`— lo habría visto en la misma
operación.

**Lo que debí hacer, y es la regla para el resto:** nombrar una función como
punto de partida de una tarea es una **afirmación**, y las afirmaciones se
verifican antes de que sean el punto de partida. Verificar el nombre cuesta un
`grep` de un segundo.
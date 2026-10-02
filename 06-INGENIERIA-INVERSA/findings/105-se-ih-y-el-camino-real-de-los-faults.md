# 105 · §E: el Interrupt Handler completo de GFX8, y el camino real de los faults

```
CLASSIFICATION=DOCUMENTATION · TRACK=STATIC + HOST_OBSERVATION
CORPUS=RESEARCH/working/linux-7.1.3 · HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0
WORK_CLASS=READ_ONLY/EVIDENCE · WRITE_EXECUTION=NONE · MODIFICATIONS=0
RUNTIME=OBSERVED_READ_ONLY · GPU INTACTA · sesión sway INTACTA
```

## Qué resuelve

Dominio 20 (`interrupts / IH`) del universo de `AGENTS.md`, sin ninguna iteración
propia. Es la pieza que convierte un evento de hardware en un `dma_fence`, y lo
que une `097`/`098` (fence) con `092` (faults).

**Y al seguirla he encontrado el camino real de los faults, que no es el que
`092` dejó sugerido.**

## Las cinco fuentes de interrupción de GFX8

Cada una tiene exactamente dos entradas: `.set` para habilitar/deshabilitar y
`.process` para atender.

```
gfx_v8_0.c:6989   gfx_v8_0_eop_irq_funcs          = { .set = ..., .process = gfx_v8_0_eop_irq }
gfx_v8_0.c:6994   gfx_v8_0_priv_reg_irq_funcs     = { .set = ..., .process = gfx_v8_0_priv_reg_irq }
gfx_v8_0.c:6999   gfx_v8_0_priv_inst_irq_funcs    = { .set = ..., .process = gfx_v8_0_priv_inst_irq }
gfx_v8_0.c:7004   gfx_v8_0_cp_ecc_error_irq_funcs = { .set = ..., .process = gfx_v8_0_cp_ecc_error_irq }
gfx_v8_0.c:7009   gfx_v8_0_sq_irq_funcs            = { .set = ..., .process = gfx_v8_0_sq_irq }
```

**Una de fence y cuatro de error.** Y EOP tiene ademas un **anillo dedicado de
1024 entradas**:

```
gfx_v8_0.c:1875   r = amdgpu_ring_init(adev, ring, 1024, &adev->gfx.eop_irq, irq_type, ...);
```

**1024 entradas, no una IRQ simple.** Es un anillo de interrupciones. Y los IDs
de fuente que se registran son tres, todos `AMDGPU_IRQ_CLIENTID_LEGACY`:

```
gfx_v8_0.c:1914   VISLANDS30_IV_SRCID_CP_END_OF_PIPE
gfx_v8_0.c:1919   VISLANDS30_IV_SRCID_CP_PRIV_REG
gfx_v8_0.c:1925   VISLANDS30_IV_SRCID_CP_PRIV_INST
```

## EOP: aqui se cierra el bucle con `098`

```
gfx_v8_0.c:6575   static int gfx_v8_0_eop_irq(...)
gfx_v8_0.c:6583       DRM_DEBUG("IH: CP EOP\n");
gfx_v8_0.c:6584       me_id    = (entry->ring_id & 0x0c) >> 2;
gfx_v8_0.c:6585       pipe_id  = (entry->ring_id & 0x03) >> 0;
gfx_v8_0.c:6586       queue_id = (entry->ring_id & 0x70) >> 4;
gfx_v8_0.c:6588       switch (me_id) {
gfx_v8_0.c:6590       case 0: amdgpu_fence_process(&adev->gfx.gfx_ring[0]); break;
gfx_v8_0.c:6594       case 1: case 2:  ... amdgpu_fence_process(ring);
```

**`gfx_v8_0_eop_irq` ES quien llama a `amdgpu_fence_process`.**

En `098` declare como confoundidor que leer `amdgpu_fence_info` llama a
`amdgpu_fence_process` (`amdgpu_fence.c:876`), y que mi muestreo lo invoco
758.647 veces. **Ahora se que esa es exactamente la funcion que la interrupcion
del hardware llama.** El debugfs y la IRQ convergen en el mismo sitio.

**Eso corrige el tamano del confoundidor, no lo elimina:** mi bucle lo llamo
38.000 veces por segundo, y la tasa real de fences observada fue de 138/s. Sigo
habiendo llamado la funcion mucho mas de lo que el hardware lo haria. Lo que
cambia es que **no era una funcion artificial**: es el camino real.

Y hay un detalle del diseno que importa: **el `ring_id` de la interrupcion
selecciona el anillo.** `me_id == 0` va al ring GFX; `me_id` 1 y 2 recorren los
rings de compute buscando `ring->me`, `ring->pipe` y `ring->queue`. **La IRQ no
sondea todos los rings: solo toca el que ha senalado.**

## Y los dos mensajes de fault nombran los tipos

```
gfx_v8_0.c:6638   DRM_ERROR("Illegal register access in command stream\n");
gfx_v8_0.c:6647   DRM_ERROR("Illegal instruction in command stream\n");
gfx_v8_0.c:6639   gfx_v8_0_fault(adev, entry);      <- priv_reg_irq
gfx_v8_0.c:6648   gfx_v8_0_fault(adev, entry);      <- priv_inst_irq
```

Y `gfx_v8_0_fault` (L6607-6632) decodifica `ring_id` **con los mismos tres
campos** que `gfx_v8_0_eop_irq`, y para `me_id == 0` llama a:

```
gfx_v8_0.c:6620   drm_sched_fault(&adev->gfx.gfx_ring[0].sched);
```

**Dos manejadores, decodificacion identica, caminos distintos**: EOP acaba en
`amdgpu_fence_process`, fault acaba en `drm_sched_fault`.

**Y los dos nombres software se corresponden con los tipos de `092`**:
`EXECUTE_PROTECTION_FAULT` <-> "illegal instruction", y
`READ`/`WRITE_PROTECTION_FAULT` <-> "illegal register access". La correspondencia
es de nombres, no de mecanismo, y la marco como tal.

## El camino real de los faults: no es el que `092` sugiere

`092` documento `VM_CONTEXT*_PROTECTION_FAULT_STATUS` con sus cinco campos. Y si
se leen — pero **en un handler de GMC, no en el de GFX**, y con dos condiciones:

```
gmc_v8_0.c:1458   if (amdgpu_vm_fault_stop == AMDGPU_VM_FAULT_STOP_FIRST)
gmc_v8_0.c:1459       gmc_v8_0_set_fault_enable_default(adev, false);
gmc_v8_0.c:1461   if (printk_ratelimit()) {
gmc_v8_0.c:1464       dev_err(adev->dev, "GPU fault detected: %d 0x%08x\n", entry->src_id, entry->src_data[0]);
gmc_v8_0.c:1467       task_info = amdgpu_vm_get_task_info_pasid(adev, entry->pasid);
gmc_v8_0.c:1469       amdgpu_vm_print_task_info(adev, task_info);
gmc_v8_0.c:1473       dev_err(adev->dev, "  VM_CONTEXT1_PROTECTION_FAULT_ADDR   0x%08X\n", addr);
gmc_v8_0.c:1475       dev_err(adev->dev, "  VM_CONTEXT1_PROTECTION_FAULT_STATUS 0x%08X\n", status);
gmc_v8_0.c:1478       gmc_v8_0_vm_decode_fault(adev, status, addr, mc_client, entry->pasid);
```

**Tres cosas que `092` no decia:**

**1. `printk_ratelimit()` es incondicional.** Aunque el parametro lo permita, el
mensaje sale **una vez**. El log del kernel tendra **un** `GPU fault detected`,
y el resto se pierde. Para un driver propio que depure faults, eso significa que
**hay que instrumentar el registro, no esperar mas lineas de log.**

**2. `vm_fault_stop` gobierna tres sitios**, y con `FIRST` **desactiva los 7
tipos de fault** (los mismos de `092`) llamando a
`gmc_v8_0_set_fault_enable_default(adev, false)`.

**3. Este es un tercer mecanismo que desactiva faults**, distinto del PRT de
`099` y del teardown del GART:

| mecanismo | donde | que hace |
|---|---|---|
| PRT | `gmc_v8_0_set_prt(true)` | `MASK_PDE0_FAULT` + 6 disable |
| fault_stop=FIRST | `gmc_v8_0.c:1459` | los 7 enable a 0 |
| GART off | `gmc_v8_0.c:977-978` | `WREG32(mmVM_CONTEXT0_CNTL, 0)` |

## Y el valor en esta maquina

```
$ cat /sys/module/amdgpu/parameters/vm_fault_stop
0
```

```
amdgpu_vm.h:145   AMDGPU_VM_FAULT_STOP_NEVER    0
amdgpu_vm.h:146   AMDGPU_VM_FAULT_STOP_FIRST    1
amdgpu_vm.h:147   AMDGPU_VM_FAULT_STOP_ALWAYS   2
amdgpu_drv.c:452   "0 = never, 1 = print first, 2 = always. The default ..."
```

**`NEVER`, que es el default.** Con ese valor, `gmc_v8_0.c:1458` **no** se cumple
y `gmc_v8_0_set_fault_enable_default(adev, false)` **no se llama**.

**Conclusion concreta: en esta maquina los siete tipos de fault estan
habilitados y nadie los desactiva por la via de `fault_stop`.** Solo lo haria el
PRT (`099`), que no se sabe si esta activo.

**Y eso deja el mapa de faults de `092` utilizable**: los siete enables estan
puestos, y el handler que los lee es alcanzable.

## Lo que NO cierra

| Afirmacion | Estado |
|---|---|
| 5 fuentes de IRQ, cada una con `.set` y `.process` | `PROVEN` |
| EOP tiene un anillo de 1024 entradas | `PROVEN` (`gfx_v8_0.c:1875`) |
| `gfx_v8_0_eop_irq` llama a `amdgpu_fence_process` | `PROVEN` |
| La IRQ selecciona el anillo por `ring_id` | `PROVEN` (`me/pipe/queue`) |
| Los faults van a `drm_sched_fault` | `PROVEN` (`gfx_v8_0.c:6620`) |
| El status de fault se lee en un handler **GMC** | `PROVEN` (`gmc_v8_0.c:1473-1478`) |
| `printk_ratelimit` limita a un mensaje | `PROVEN` (`gmc_v8_0.c:1461`) |
| Son 3 mecanismos distintos que desactivan faults | `PROVEN_DERIVED` |
| `vm_fault_stop = 0` en esta maquina | **`OBSERVED`** (sysfs) |
| Con 0, no se desactivan por esa via | `PROVEN_DERIVED` |
| "Illegal instruction" = `EXECUTE_PROTECTION_FAULT` | `CORROBORATED` — solo nombres |
| Cual de los tres Rings de la IRQ dispara en la practica | `NOT_DETERMINED` |
| Si hay faults activos ahora (PRT) | `NOT_DETERMINED` — el hueco de `099` |

**La penultima fila es `CORROBORATED`, no `PROVEN`, y hay que decirlo.** Los
nombres se corresponden con los de `092`, pero que `priv_inst_irq` sea el mismo
hardware que `EXECUTE_PROTECTION_FAULT_ENABLE_DEFAULT` **no esta demostrado**: uno
es un `SRCID` de interrupcion y el otro un campo de un registro de control. Que
se llamen parecido no prueba que disparen lo mismo.

**Y el hueco de `099` sigue abierto y pesa mas que esta nota**: si PRT esta
activo, los siete enables estan a 1 en la lectura pero el hardware no esta
generando faults. Un mapa de faults que no sabes si esta activo no es un mapa.

## Procedencia

- `HOST_OBSERVATION` — `/sys/module/amdgpu/parameters/vm_fault_stop`. Solo
  lectura.
- `STATIC` — `gfx_v8_0.c:6575-6655` y `:6976-7012` y `:1875` y `:1905-1925`,
  `gmc_v8_0.c:1458-1482` y `:660-756`, `amdgpu_drv.c:448-455`,
  `amdgpu_vm.h:145-147`, `amdgpu_fence.c:865-905`.
- Sin MMIO write, sin TLB, sin modulos, sin cambiar parametros.
- Encadenada con `097`/`098` (el fence y su IRQ), `092` (los 7 tipos de fault),
  `099` (PRT como tercer mecanismo de disable), `103`/`104` (el invalidate).
- No se edito `AGENTS.md` ni `OPEN-FRONTIERS.md`: son de otras sesiones.

**Una nota de metodo, y es sobre cerrar lo que deje abierto.**

En `098` declare que leer `amdgpu_fence_info` era un confoundidor porque
llamaba a `amdgpu_fence_process` y nadie habia buscado quien mas lo llamaba.
Acababa de decirlo como **"nadie ha mirado el IH"**, que era cierto y era
justo el siguiente paso.

Menos de una hora despues se que la IRQ lo llama, que el anillo es de 1024
entradas, y que el `ring_id` selecciona el anillo. **Mi propio informe anterior
contenia el confoundidor sin delimitar, y la siguiente tarea lo cerro.**

**Lo que escribo en un hallazgo es parte del estado del siguiente.** Y `098`
habria podido declarar el confoundidor en media linea si hubiera seguido una
funcion mas —`amdgpu_fence_process`— en vez de cerrar en el observable.
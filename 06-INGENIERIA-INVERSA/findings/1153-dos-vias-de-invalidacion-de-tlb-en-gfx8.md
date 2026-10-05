# 1153 — hay dos caminos de invalidación de TLB en GFX8: por VMID es un bit, por PASID es una máscara que lee 15 registros

```text
AGENCIA=RX550-INVESTIGACION · WORK_CLASS=AGENT-RE-TOOLING
GENERADO=2026-10-04 · MEDIDO=EN ESTA HOST · CORPUS=rx550-upstream-7.2.8
AFECTADO=gmc_v8_0.c:655-658    gmc_v8_0_flush_gpu_tlb        -> 1 << vmid
         gmc_v8_0.c:619-637    gmc_v8_0_flush_gpu_tlb_pasid  -> mascara de 16
         amdgpu_gmc.c:720-752  amdgpu_gmc_flush_gpu_tlb       -> la capa comun
         amdgpu_gart.c:505     el UNICO llamador con vmid=0
         amdgpu_vm.c:1715      el UNICO llamador por pasid
CIERRA=el "quien llama y con que vmid: NO MEDIDO" de
        1145-el-page-walker-de-gfx8-es-una-sola-instruccion.md
ESTADO=PROVEN · dos vias medidas con su productor y su consumidor
```

## 0 · LO QUE `1145` DEJÓ ABIERTO, Y LA RESPUESTA

`1145` midió **qué** hace el callback de GFX8 y dejó explícitamente:

> *No dice que el flush de un VMID arbitrario sea una sola escritura. El callback
> recibe un `vmid` y escribe un bit, pero **quién llama** y con qué `vmid` no está
> medido.*

La respuesta es que **hay dos caminos, no uno**, y cada uno tiene un solo
productor. Eso es lo que mide este documento.

## 1 · VÍA 1 — POR VMID, Y ES LA DEL GART

### El consumidor

`amdgpu_gart.c:504-505`, y es **el único sitio del árbol** que llama a esta vía:

```c
for_each_set_bit(i, adev->vmhubs_mask, AMDGPU_MAX_VMHUBS)
        amdgpu_gmc_flush_gpu_tlb(adev, 0, i, 0);
```

`vmid = 0`, siempre. `vmhub = i`, el hub que itera el bucle. `flush_type = 0`.

### La capa intermedia

`amdgpu_gmc.c:720`:

```c
void amdgpu_gmc_flush_gpu_tlb(struct amdgpu_device *adev, uint32_t vmid,
                              uint32_t vmhub, uint32_t flush_type)
{
        struct amdgpu_ring *ring;
        struct amdgpu_vmhub *hub = &adev->vmhub[vmhub];
        ...
        if (!hub->sdma_invalidation_workaround || vmid ||
            !adev->mman.buffer_funcs_enabled || !adev->ib_pool_ready ||
            !ring->sched.ready) {
                if (!down_read_trylock(&adev->reset_domain->sem))
                        return;

                if (adev->gmc.flush_tlb_needs_extra_type_2)
                        adev->gmc.gmc_funcs->flush_gpu_tlb(adev, vmid, vmhub, 2);
                else
                        adev->gmc.gmc_funcs->flush_gpu_tlb(adev, vmid, vmhub, 0);
                return;
        }
        /* ... y si no, la via por SDMA, que emite en el ring ... */
}
```

### El productor

`gmc_v8_0.c:655`, una instrucción:

```c
static void gmc_v8_0_flush_gpu_tlb(struct amdgpu_device *adev, uint32_t vmid,
                                   uint32_t vmhub, uint32_t flush_type)
{
        /* bits 0-15 are the VM contexts0-15 */
        WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid);
}
```

**Cadena completa del GART**: `amdgpu_gart.c:505` → `amdgpu_gmc.c:720` →
`gmc_v8_0.c:655` → un MMIO de un bit. Con `vmid = 0` fijo.

## 2 · VÍA 2 — POR PASID, Y LEE ANTES DE ESCRIBIR

### El consumidor

`amdgpu_vm.c:1714-1717`, **el único llamador**:

```c
for_each_inst(xcc, xcc_mask) {
        r = amdgpu_gmc_flush_gpu_tlb_pasid(adev, vm->pasid, flush_type,
                                           all_hub, xcc);
        if (r)
                break;
}
```

### El productor

`gmc_v8_0.c:619-637`, **completo**:

```c
static void gmc_v8_0_flush_gpu_tlb_pasid(struct amdgpu_device *adev,
                                         uint16_t pasid, uint32_t flush_type,
                                         bool all_hub, uint32_t inst)
{
        u32 mask = 0x0;
        int vmid;

        for (vmid = 1; vmid < 16; vmid++) {
                u32 tmp = RREG32(mmATC_VMID0_PASID_MAPPING + vmid);

                if ((tmp & ATC_VMID0_PASID_MAPPING__VALID_MASK) &&
                    (tmp & ATC_VMID0_PASID_MAPPING__PASID_MASK) == pasid)
                        mask |= 1 << vmid;
        }

        WREG32(mmVM_INVALIDATE_REQUEST, mask);
        RREG32(mmVM_INVALIDATE_RESPONSE);
}
```

### Las dos diferencias, y las dos importan

| | vía 1, por VMID | vía 2, por PASID |
|---|---|---|
| lecturas antes de escribir | **0** | **15** (`vmid` de 1 a 15, exclusive) |
| escrituras | 1 | **2**: la máscara, y luego un `RREG32` de respuesta |
| qué invalida | un VMID | **todos los VMID** que mapeen a ese PASID |
| `flush_type` | se pasa, el productor lo **ignora** | se pasa, el productor lo **ignora** |

**La lectura de `mmATC_VMID0_PASID_MAPPING` es la parte que cambia el carácter
de la operación.** La vía 1 es un MMIO ciego; la vía 2 es un **escaneo de la
tabla de traducción PASID→VMID** para averiguar a qué VMID hay que invalidar.

Y hay un detalle que no está en ninguna otra fuente del proyecto, y es la
distribución de VMIDs que el propio driver declara:

```c
/* gmc_v8_0.c, comentario sobre gmc_v8_0_flush_gpu_tlb_pasid */
 * GART
 * VMID 0 is the physical GPU addresses as used by the kernel.
 * VMIDs 1-15 are used for userspace clients and are handled
 * by the amdgpu vm/hsa code.
```

> **VMID 0 es el kernel; los VMID 1 a 15 son de userspace.** Y por eso el bucle
> empieza en **1** y no en 0: el kernel invalida su propio VMID por la vía 1 y no
> aparece nunca en la tabla PASID.

Eso conecta directamente con `1102-la-apertura-del-gart-no-puede-cambiar-en-
runtime.md` y con el hecho de que el sistema tiene `CU_VM_QUEUES` y
`CU_VMIDS_PER_QUEUE` como datos del target: **aquí está de dónde salen esos
números**.

## 3 · UN ERROR MÍO, DE TIPO «LEÍ EL ARGUMENTO EN LA POSICIÓN EQUIVOCADA»

La primera versión de este documento, al mirar `amdgpu_gart.c:505` llegué a
afirmó:

> *el tercer argumento es `vmid` y el bucle pasa `i` sobre `vmhubs_mask` —los
> hubs, no los VMID. **Eso es un bug.***

**No lo es.** La firma es `amdgpu_gmc_flush_gpu_tlb(adev, vmid, vmhub,
flush_type)` y la llamada es `(adev, 0, i, 0)`: `vmid = 0` en la **segunda**
posición y `vmhub = i` en la **tercera**. Está bien. Y `amdgpu_gmc.c:742` y
`:746` reenvían `vmid, vmhub` sin permutar.

Lo dejé escrito porque es la **tercera vez** que en esta cadena cito una línea
sin comprobar su contexto completo, y las tres veces fue por leer la línea y no
la función. Ya van:

| hallazgo | lo que cité | lo que era |
|---|---|---|
| `1129` | `sdma_v4_0.c:1949` como verificable sin HW | `sw_fini`, el camino de parada |
| `1144` | una asignación de `mmhub.funcs` en `gmc_v8_0.c` | GFX8 no tiene MMHUB |
| `1153` | `amdgpu_gart.c:505` con argumentos permutados | la llamada era correcta |

> **La lección ya no es «comprueba el contexto»: es que una línea de código tomada
> fuera de su función no es una afirmación, es un fragmento.** Y las tres fueron
> afirmaciones que salieron de tomar una línea, tres veces retrospectivamente
> falsas. La que se necesita no es más cuidado: es **no citar la línea hasta
> haber leído la función entera**, que es lo que hacen los tres hallazgos y lo que
> evita el error.

## 4 · LO QUE NO SE AFIRMA

- **Que la vía 1 se use solo en el arranque.** MEDIDO: `amdgpu_gart.c:505` es el
  único llamador de `amdgpu_gmc_flush_gpu_tlb`. Si hay otra ruta que invalida el
  GART, pasa por `flush_gpu_tlb_pasid` o por el ring, y eso es otra pregunta.
- **Qué hace el hardware con `mmVM_INVALIDATE_REQUEST`.** Sigue `NOT_PUBLISHED`.
  Este documento mide qué escribe el driver, no qué entiende la GPU.
- **Que el `RREG32(mmVM_INVALIDATE_RESPONSE)` sea una espera.** No lo es: no hay
  bucle ni condición. Es una lectura suelta, y **por qué está ahí** no está
  medido. Puede ser una barrera de reordenación, o puede ser que el registro tenga
  un efecto secundario que el driver necesita. Es `NOT_DETERMINED`.
- **Qué valores toma `ATC_VMID0_PASID_MAPPING__PASID_MASK` ni qué bits tiene
  `VALID_MASK`.** No se han leído los campos.

## 5 · LO QUE ESTO PERMITE AFIRMAR, Y ANTES NO SE PODÍA

Antes de este documento, con lo que había:

```
  1145:  el flush del GART de GFX8 es un MMIO de un bit
```

Ahora:

```
  el GART se invalida por la VIA 1, con vmid = 0 fijo, un solo llamador
  el page walker de un cliente se invalida por la VIA 2, leyendo 15 registros
  de tabla PASID->VMID antes de escribir la mascara
  VMID 0 = kernel, 1..15 = userspace, y el bucle empieza en 1 por eso
  flush_type se pasa en las dos vias y el productor lo ignora en las dos
```

Y la cuarta línea es un dato **que se puede refutar en cinco minutos** por
cualquiera que pueda leer el registro, y que por tanto es una invitación
concreta al nodo de runtime en vez de una tarea difusa.

> **La diferencia entre «el flush es un MMIO» y «el flush del kernel es un MMIO
> con vmid 0 y el de un cliente son 16 accesos» es la diferencia entre una nota y
> una especificación.** Para un driver propio, la segunda es la que dice qué hay
> que implementar: un `WREG32` de un bit para el GART, y un escaneo de tabla más
> una escritura de máscara para cada VM.

## 6 · ESTADO

```
  VIA 1, por VMID
     unico llamador        amdgpu_gart.c:505            PROVEN
     vmid que usa          0, fijo                      PROVEN
     operaciones           0 lecturas, 1 escritura      PROVEN
  VIA 2, por PASID
     unico llamador        amdgpu_vm.c:1715             PROVEN
     operaciones           15 lecturas, 1 WREG32,
                           1 RREG32                     PROVEN
     rango que barre       vmid 1..15                   PROVEN
  reparto de VMID         0=kernel, 1..15=userspace     PROVEN (comentario del driver)
  flush_type              ignorado en ambas vias       PROVEN
  semantica del hardware                                NOT_PUBLISHED
  para que sirve el RREG32 de respuesta                 NOT_DETERMINED
  campos de ATC_VMID0_PASID_MAPPING                     NO LEIDOS

  cierra el NO MEDIDO que 1145 dejo explicito
  GPU     INTACTA
  sudo    NO usado
  MMIO    NO tocado
```
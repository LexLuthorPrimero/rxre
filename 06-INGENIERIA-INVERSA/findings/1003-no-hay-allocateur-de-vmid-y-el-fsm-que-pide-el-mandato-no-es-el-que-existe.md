# 1003 · No hay asignador de VMID: el FSM que pedía el mandato no es el que existe

```
CLASSIFICATION=DOCUMENTATION+CONTRADICTION · TRACK=STATIC
CORPUS_A=RESEARCH/working/linux-7.1.3   (kernel en ejecución)
CORPUS_B=rx550-upstream-7.2.8/linux-7.2.8 (contraste)
HARDWARE_SCOPE=HOST-C/RX550/0000:01:00.0 · WORK_CLASS=READ_ONLY/EVIDENCE
WRITE_EXECUTION=NONE · MODIFICATIONS=0 en el corpus · RUNTIME=NOT_RUN · GPU INTACTA
AGENTE=AGENT-12 (VMID) · ESTADO=RESUELTO en su parte estática
```

## Por qué este hallazgo contradice el encargo que lo instigó

El mandato de AGENT-12 pide este estado machine:

```text
ALLOCATED → CONFIGURED → ACTIVE → INVALIDATED → REUSED → RELEASED
```

Seis estados, y un `ALLOCATED` y un `RELEASED` que disputan por la existencia de
un **asignador**. Leyendo el corpus resulta que **ese asignador no existe en
GFX8**, y por tanto dos de los seis estados pedidos no tienen contraparte real.
El estado machine que sí existe no es de *asignación*: es de **enlace**
(*binding*) de un número de VMID fijo a un contexto de envío, y se lo recorre
muchas veces el mismo proceso.

Esto no es una discrepancia de redactura. Cambia qué hay que implementar: un
driver propio que busque `ALLOCATED`/`RELEASED` implementará un asignador que
el hardware nunca exigió, y en el peor de los casos su implementación se
comportará bien y no se parecerá en nada a lo que hace el hardware.

**La evidencia que decide** es que el número de VMID **no se asigna nunca**:

```c
/* amdgpu_ids.h:65-71 */
struct amdgpu_vmid_mgr {
        struct mutex          lock;
        unsigned              num_ids;
        struct list_head      ids_lru;
        struct amdgpu_vmid    ids[AMDGPU_NUM_VMID];   /* 16 ranuras FIJAS */
        bool                  reserved_vmid;
};
```

Hay 16 ranuras **fijas**, indexadas por número. No hay bitmap libre, no hay
`ida`, no hay `find_first_zero`, no hay contador que incremente. El "número" del
VMID es literalmente **el índice en el array**:

```c
/* amdgpu_ids.c:432 */
        job->vmid = id - id_mgr->ids;
```

Y el enlace con el proceso es un campo, no una propiedad del número:

```c
/* amdgpu_ids.c:442 */
        id->owner = vm->immediate.fence_context;
```

El VMID no se "libera": se **desenlaza** poniendo el enlace en otro valor. Lo
que `042` y `046` llamaban "reservar un VMID" es, en el código, **mover una
ranura entre dos estructuras de pertenencia**: la LRU `ids_lru` y el
`vm->reserved_vmid[vmhub]` del proceso.

## El FSM que existe

Cinco estados por ranura. Cada estado se define por lo que el código
**comprueba** para seguir por él, que es la única definición que no depende de
intención.

| estado | definición operacional (la usa el código) | sitio |
|---|---|---|
| `RESERVED` | la ranura está **fuera** de `ids_lru`, colgada de `vm->reserved_vmid[vmhub]` | `amdgpu_ids.c:488-491` |
| `FREE` | está en `ids_lru` y su `active` no tiene fence pendiente para este anillo | `amdgpu_ids.c:222-231` |
| `LINKED` | `owner == vm->immediate.fence_context`: la ranura ya es de este proceso | `amdgpu_ids.c:341-342` |
| `STALE` | `owner` coincide pero `flushed_updates < tlb_seq`, o `last_flush` ausente o no senalizado | `amdgpu_ids.c:347-353` |
| `RESET` | `current_gpu_reset_count != atomic_read(&gpu_reset_counter)` | `amdgpu_ids.c:171-176` |

Y las aristas, que son las transiciones del entregable:

```text
        amdgpu_vmid_alloc_reserved      amdgpu_vmid_free_reserved
 FREE ──────────────────────────► RESERVED ──────────────────────► FREE
   │                                 (amdgpu_ids.c:488-491)       (amdgpu_ids.c:512-517)

   │  amdgpu_vmid_grab_used, con owner == fence_context
   ▼
LINKED ───── flushed_updates < tlb_seq ─────► STALE
   │                (amdgpu_ids.c:352-353)
   │
   │  grab_idle / grab_used sin needs_flush:
   │  NO hay transición. Se permanece en LINKED y se REUSA.
   │
   │  amdgpu_vmid_reset / _reset_all          (amdgpu_ids.c:537-543, 562-563)
   ▼
 RESET ── primer uso posterior fuerza flush ──► LINKED + flush obligatorio
                                              (amdgpu_vm.c:799-804)
```

### La arista que el encargo llama `REUSED` es la arista por defecto

`REUSED` no es una transición: es **el caso mayoritario**. El bucle principal de
`amdgpu_vmid_grab` va primero a `grab_used`, y sólo si no encuentra nada toma
una ranura `FREE`:

```c
/* amdgpu_ids.c:396-424 */
        r = amdgpu_vmid_grab_idle(ring, &idle, fence);
        ...
        if (amdgpu_vmid_uses_reserved(vm, vmhub)) {
                r = amdgpu_vmid_grab_reserved(vm, ring, job, &id, fence);
        } else {
                r = amdgpu_vmid_grab_used(vm, ring, job, &id);   /* REUSE */
                if (r)
                        goto error;
                if (!id) {
                        id = idle;                              /* primer uso */
                        ...
                        job->vm_needs_flush = true;
                }
                list_move_tail(&id->list, &id_mgr->ids_lru);
        }
```

`grab_used` es la condición de `REUSED` completa y verificable:

```c
/* amdgpu_ids.c:341-356 */
        if ((*id)->owner != vm->immediate.fence_context)      continue;  /* (1) */
        if (!amdgpu_vmid_compatible(*id, job))               continue;  /* (2) */
        if (!(*id)->last_flush ||
            ((*id)->last_flush->context != fence_context &&
             !dma_fence_is_signaled((*id)->last_flush)))
                                      needs_flush = true;               /* (3) */
        if ((*id)->flushed_updates < updates)                needs_flush = true; /* (4) */
        if (needs_flush && !adev->vm_manager.concurrent_flush)         continue;
```

Cuatro condiciones. (1) es el enlace, (2) es compatibilidad de recursos
GDS/GWS/OA, (3) es "el flush anterior no ha aterrizado en **este** anillo",
(4) es "el page table ha cambiado desde el último flush". **(3) y (4) deciden si
el reuse necesita invalidación**, y son las dos que un motor propio tiene que
reimplementar bien para no ejecutar con una tabla caducada.

## CONFIGURED e INVALIDATED son el mismo paquete de dos dwords

Este es el resultado que más cierra el encargo, y no aparece en ningún finding
previo. La función que escribe el PTBA **es** la que invalida:

```c
/* gmc_v8_0.c:668-683 */
static uint64_t gmc_v8_0_emit_flush_gpu_tlb(struct amdgpu_ring *ring,
                                            unsigned int vmid, uint64_t pd_addr)
{
        uint32_t reg;

        if (vmid < 8)
                reg = mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR + vmid;      /* tramo 0 */
        else
                reg = mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8;  /* tramo 1 */
        amdgpu_ring_emit_wreg(ring, reg, pd_addr >> 12);              /* CONFIGURED */

        /* bits 0-15 are the VM contexts0-15 */
        amdgpu_ring_emit_wreg(ring, mmVM_INVALIDATE_REQUEST, 1 << vmid); /* INVALIDATED */

        return pd_addr;
}
```

Cuatro consecuencias:

1. **CONFIGURED e INVALIDATED no son separables en el IB.** Los dos `emit_wreg`
   son consecutivos y no hay nada entre ellos. Un driver propio que escriba el
   PTBA y espere a revalidar por otra vía ha cambiado el contrato.
2. **La geometría de dos tramos de `037`/`042` está en el código**, y su
   consumidor es la misma función que lo produce. El `if (vmid < 8)` es la
   partición 8/8 vista desde el productor de registro, no sólo desde
   `first_kfd_vmid`.
3. **`1 << vmid` es la regla por VMID** que `115` tenía como afirmación; aquí se
   ve que es literal. El comentario del driver declara el rango (bits 0-15 =
   contexts 0-15) sin que ningún campo del registro lo imponga.
4. **El valor es `pd_addr >> 12`**: la PTBA no guarda una dirección de byte sino
   un **índice de página de 4 KiB**. Es el mismo truncamiento que `064` ya
   registró para `PAGE_TABLE_START/END_ADDR` (`gart_start >> 12`), y aquí
   confirma que es la convención del bloque y no un descuido de un sitio.

## Matiz a `042`: la partición en 8 no es sólo política

`042` concluded que "la partición en 8 no la impone el hardware, la impone el
driver", y lo dejó en `PROVEN_DERIVED`. El `if (vmid < 8)` de
`gmc_v8_0.c:673` **obliga a matizarlo**: el hardware sí impone una
discontinuidad, y está exactamente en 8, porque los contextos 8-15 viven en un
tramo de registros que no sigue al de 0-7.

Lo que queda como decisión del driver es **qué se hace con la discontinuidad**
—reservar el segundo tramo para KFD o no—, no **dónde está la discontinuidad**.
Son dos afirmaciones distintas y `042` las refundió en una. El valor 8 no es
elegible: es la posición donde el layout de registros se parte.

Esto **no refuta** `042`; acota su alcance. `042` sigue siendo correcto en que
`amdgpu_vmid_grab_reserved` es una política de reutilización escrita por
alguien. Lo que `042` no vio es que la política se apoya en una discontinuidad
del hardware que no podría haberse puesto en otro sitio.

## Los productores están CERRADOS para GFX8

Barrido de **todo** el árbol, no sólo de `amdgpu/`. Este cierre es lo que
convierte una lista de "sitios que he leído" en "sitios que existen".

**`mmVM_INVALIDATE_REQUEST` — escritores en el árbol:**

```text
gmc_v8_0.c:640    WREG32(mmVM_INVALIDATE_REQUEST, mask)        ← SDMA/PASID, vmid 1..15
gmc_v8_0.c:665    WREG32(mmVM_INVALIDATE_REQUEST, 1 << vmid)   ← flush por CPU
gmc_v8_0.c:680    emit_wreg(..., 1 << vmid)                   ← flush por IB   ★
gfx_v8_0.c:6203   amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST)   ← espera, no escritura
--- otros ASIC, fuera de scope para CHIP_POLARIS12 ---
gmc_v7_0.c:449,474,489 · gmc_v6_0.c:357,373 · gfx_v6_0.c:2388 · gfx_v7_0.c:3151
cik_sdma.c:857 · sdma_v2_4.c:794 · sdma_v3_0.c:1067 · uvd_v6_0.c:1083
```

**PTBA de la GMC — escritores en GFX8:**

```text
gmc_v8_0.c:674,676                emit, por vmid, dos tramos        ★ ruta de VM
gmc_v8_0.c:889                    mmVM_CONTEXT0_PAGE_TABLE_BASE_ADDR ← GART, VMID 0
gmc_v8_0.c:912,915                los 15 contextos al GART, en el arranque
amdgpu_amdkfd_gfx_v8.c:581        mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8  ← KFD
```

Los `mmhub_*` y `gfxhub_*` de esos barridos son SoC15 (`IP_VERSION >= 9`) y no
aplican a Polaris12, que es pre-SoC15 y por eso tiene GMC y no MMHUB. Los `dcn*`
tocan el `PAGE_TABLE_BASE_ADDR` de DCN, que es otro bloque.

**Y el lado KFD confirma la partición por el otro extremo:**

```c
/* amdgpu_amdkfd_gfx_v8.c:574-583 */
static void set_vm_context_page_table_base(struct amdgpu_device *adev,
                uint32_t vmid, uint64_t page_table_base)
{
        if (!amdgpu_amdkfd_is_kfd_vmid(adev, vmid)) {
                pr_err("trying to set page table base for wrong VMID\n");
                return;
        }
        WREG32(mmVM_CONTEXT8_PAGE_TABLE_BASE_ADDR + vmid - 8,
                        lower_32_bits(page_table_base));
}
```

Es el **mismo par de tramos** que la ruta DRM, escrito desde el otro lado, con
una guarda que **rechaza** el VMID equivocado en vez de corregirlo. Dos
consumidores independientes de la misma geometría: eso es lo que `037` pedía y
no tenía.

## La arista `RESET` y su recuperación

`INVALIDATED` por reset de GPU no es una hipótesis: tiene productor, detector y
reparación, y los tres están escritos.

```c
/* amdgpu_ids.c:171-176 */
bool amdgpu_vmid_had_gpu_reset(struct amdgpu_device *adev, struct amdgpu_vmid *id)
{
        return id->current_gpu_reset_count != atomic_read(&adev->gpu_reset_counter);
}

/* amdgpu_ids.c:530-545 — el reset de software: borra el enlace y los recursos */
void amdgpu_vmid_reset(struct amdgpu_device *adev, unsigned vmhub, unsigned vmid)
{
        ...
        id->owner = 0;
        id->gds_base = 0;  id->gds_size = 0;
        id->gws_base = 0;  id->gws_size = 0;
        id->oa_base  = 0;  id->oa_size  = 0;
}

/* amdgpu_vm.c:799-804 — el reset de hardware FUERZA flush, GDS, PASID y SPM */
        if (amdgpu_vmid_had_gpu_reset(adev, id)) {
                gds_switch_needed     = true;
                vm_flush_needed       = true;
                pasid_mapping_needed  = true;
                spm_update_needed     = true;
        }

/* amdgpu_vm.c:875-882 — la curación, al aterrizar el flush */
        if (vm_flush_needed) {
                dma_fence_put(id->last_flush);
                id->last_flush = dma_fence_get(fence);
                id->current_gpu_reset_count = atomic_read(&adev->gpu_reset_counter);
        }
```

El comentario del propio driver en `amdgpu_ids.c:528` dice para qué existe
`amdgpu_vmid_reset`: *"Reset saved GDW, GWS and OA to force switch on next
flush"*. **`RESET` es un estado cuya única función es forzar el próximo
`INVALIDATED`.** Es la confirmación más fuerte de que la cadena
`INVALIDATED → REUSED` en GFX8 no es opcional: el hardware la exige, y el driver
la provoca incluso en el camino de software.

## Lo que NO se cierra, con la razón exacta

| afirmación | estado | por qué |
|---|---|---|
| Los 16 VMID son ranuras fijas y el número es el índice | `PROVEN` | `amdgpu_ids.h:69`, `amdgpu_ids.c:432` |
| `num_ids = first_kfd_vmid = 8` en GFX8 | `PROVEN` | `amdgpu_ids.c:586-588`, rama `GC_HWIP < 10.0.0` |
| VMID 0 se excluye por ser "el VM del sistema" | `PROVEN` (software) | `amdgpu_ids.c:596`, literalmente el comentario |
| PTBA e INVALIDATE son 2 dwords consecutivos | `PROVEN` | `gmc_v8_0.c:677,680` |
| El valor de PTBA es un índice de página, no bytes | `PROVEN` | `gmc_v8_0.c:677` |
| Los productores de PTBA e INVALIDATE están cerrados | `PROVEN` | barrido de todo el árbol, 3 productores + 2 esperas, ninguno más |
| Las 4 condiciones de `REUSED` | `PROVEN` | `amdgpu_ids.c:341-356` |
| Que hace el hardware con el bit escrito | `NOT_DETERMINED` | requiere la spec primaria de GMC, no publicada |
| Si el hardware **exige** el invalidate o sólo lo recomienda | `NOT_DETERMINED` | ningún código lo dice; la evidencia es que se emite siempre |
| Semántica de hardware de `PAGE_TABLE_DEPTH` 0 vs 1 | `NOT_DETERMINED` | `064` ya lo dejó acotado y sigue abierto |
| Qué ocurre si se omite `INVALIDATE_REQUEST` | `NOT_DETERMINED` | sólo se responde en runtime, con un fallo reproducible |
| Que `INVALIDATE_REQUEST` se auto-limpia al escribirlo | `NOT_DETERMINED` | el paquete de espera es `FUNCTION(0)=always` y **no** compara. Mi primera redacción lo daba por `PROVEN_DERIVED` y era falso |
| Que el `WAIT_REG_MEM` de `gfx_v8_0.c:6199` sea una espera de completación | `REFUTADO` | el comentario dice "wait for the invalidate to complete"; el mecanismo es una espera fija de `0x20` ticks. Comentario ≠ mecanismo |

## Cierre de los dos enlaces que estaban faltantes

Los dos `NOT_READ` de la sección anterior **se cerraron** en la misma sesión, con
números de línea verificados. Y el primero de ellos **corrigió** este hallazgo:
el discriminate que se diseñó para `1003-C1` echó abajo una afirmación mía, y
queda registrada como corrección, no como resultado.

### `gfx_v8_0.c:6191-6214` · lo que sigue al invalidate, y por qué NO es una espera de completación

```c
/* gfx_v8_0.c:6191-6214 */
static void gfx_v8_0_ring_emit_vm_flush(struct amdgpu_ring *ring,
                                        unsigned vmid, uint64_t pd_addr)
{
        int usepfp = (ring->funcs->type == AMDGPU_RING_TYPE_GFX);

        amdgpu_gmc_emit_flush_gpu_tlb(ring, vmid, pd_addr);

        /* wait for the invalidate to complete */
        amdgpu_ring_write(ring, PACKET3(PACKET3_WAIT_REG_MEM, 5));
        amdgpu_ring_write(ring, (WAIT_REG_MEM_OPERATION(0) | /* wait */
                                 WAIT_REG_MEM_FUNCTION(0) |  /* always */
                                 WAIT_REG_MEM_ENGINE(0))); /* me */
        amdgpu_ring_write(ring, mmVM_INVALIDATE_REQUEST);
        amdgpu_ring_write(ring, 0);            /* el valor que se espera */
        amdgpu_ring_write(ring, 0);            /* ref */
        amdgpu_ring_write(ring, 0);            /* mask */
        amdgpu_ring_write(ring, 0x20);         /* poll interval */

        if (usepfp) {                          /* compute no tiene PFP */
                amdgpu_ring_write(ring, PACKET3(PACKET3_PFP_SYNC_ME, 0));
                amdgpu_ring_write(ring, 0x0);
        }
}
```

Cuatro consecuencias. **La primera estaba mal en mi primera redacción, y el
discriminante que diseñé para `1003-C1` la refutó.** Queda corregida aquí, y esa
corrección es el resultado más útil de este hallazgo:

1. ~~El hardware limpia `mmVM_INVALIDATE_REQUEST` por su cuenta.~~
   **REFUTADO, por mí mismo.** Escribí que el driver "espera a que el registro
   valga 0" y deduje de ahí una semántica write-1-set / hardware-clear. Es
   falso: el campo `FUNCTION` va en **0**, y `soc15d.h:178` define
   `WAIT_REG_MEM_FUNCTION(x) = x << 0`, con 0 = *always*. Un paquete `always`
   **no compara nada**: es una espera incondicional y temporizada. Los tres
   ceros siguientes (`0` valor, `0` ref, `0` mask) **no** son "el valor que se
   espera"; en un paquete `always` no tienen lectura de comparación. **No hay
   readback de `INVALIDATE_REQUEST` en este camino**, y el auto-limpiado del
   registro sigue siendo `NOT_DETERMINED`.
2. **Lo que sí queda es una divergencia entre el comentario y el mecanismo.**
   `gfx_v8_0.c:6198` dice *"wait for the invalidate to complete"*, y lo que
   emite es una espera fija de `0x20` ticks de poll sobre ME. Eso no es una
   espera de completación: es un retardo. Las dos lecturas compatibles son "el
   hardware siempre termina antes de `0x20`" y "al autor le bastaba un margen",
   y el corpus **no** las separa. Queda `NOT_DETERMINED`, no hardware-clear.
3. **La cadena de productores queda completa y es de tres eslabones:**
   `gfx_v8_0_ring_emit_vm_flush` → `amdgpu_gmc_emit_flush_gpu_tlb` →
   `gmc_v8_0_emit_flush_gpu_tlb`. El segundo eslabón es un **macro**, no una
   función: `amdgpu_gmc.h:371` lo define como
   `(r)->adev->gmc.gmc_funcs->emit_flush_gpu_tlb((r), (vmid), (addr))`. Esto
   confirma, con un caso real, el límite que `tools/vmid_map.py` declara: *"El
   grafo es textual: no preprocesa, así que una llamada a través de un macro de
   función o un puntero a función no aparece"*. El límite era correcto y ya
   tiene el ejemplo que lo respalda.
4. **El presupuesto de dwords del ring ya está escrito.** `gfx_v8_0.c:6929` y
   `:6964` reservan `VI_FLUSH_GPU_TLB_NUM_WREG * 5 + 7` y `+ 17` con el
   comentario `/* gfx_v8_0_ring_emit_vm_flush */`. Es un **contador
   independiente** que confirma el recuento de dwords del flush.

### `1003-C1` RESUELTA · sólo uno de los tres `WAIT_REG_MEM` de `gfx_v8_0.c` es `hdp_flush`

El discriminante que nombré era el campo `FUNCTION` de cada paquete. Ejecutado:

```text
gfx_v8_0.c:6046-6054   OPERATION(1) write/wait/write · FUNCTION(3) ==     → SÍ hdp_flush
                       addr=mmGPU_HDP_FLUSH_REQ, luego mmGPU_HDP_FLUSH_DONE
gfx_v8_0.c:6180-6187   MEM_SPACE(1) memoria ·     FUNCTION(3) equal  → NO: poll a VRAM
                       addr=gpu_addr de sync_seq, ref=seq, mask=0xffffffff
gfx_v8_0.c:6199-6207   OPERATION(0) wait ·        FUNCTION(0) always → NO: espera fija
                       addr=mmVM_INVALIDATE_REQUEST, ref=0, mask=0, poll=0x20
```

`gfx_v8_0.c` contiene **3** `PACKET3_WAIT_REG_MEM` y **1** es `hdp_flush`.
Censo completo: `gmc_v8_0.c` 0, `gfxhub_v2_1.c` 0, `amdgpu_cs.c` 0,
`amdgpu_vm.c` 0.

**Veredicto: `122` queda `REFUTADO` en su alcance; su observación queda intacta.**
Lo que `122` observó —10 paquetes en un anillo vivo, todos con `FUNCTION(3)`— es
un hecho de **una muestra de anillo** y sigue siendo cierto. Lo que no puede
sostener es la generalización "los `WAIT_REG_MEM` **son** `hdp_flush`": el driver
contiene al menos dos que no lo son, y uno está en el camino de invalidate de VM.
Nótese que `122` **ya citaba** `gfx_v8_0_ring_emit_vm_flush` `L6199-L6207` para
contar dwords: tenía el sitio en la mano y aun así generalizó. **Contar la
longitud de un paquete no es decodificar su función**, y esa es exactamente la
distinción que faltaba.

Esto **no invalida** la convención de longs que `122` sí estableció
(`PACKET3(op,n)` con `n` = payload − 1): esa parte es ortogonal y sigue en pie.

### `gmc_v8_0.c:625-641` · el invalidate por PASID es la inversión del mapa

```c
/* gmc_v8_0.c:625-641, función gmc_v8_0_flush_gpu_tlb_pasid */
        for (vmid = 1; vmid < 16; vmid++) {
                u32 tmp = RREG32(mmATC_VMID0_PASID_MAPPING + vmid);

                if ((tmp & ATC_VMID0_PASID_MAPPING__VALID_MASK) &&
                    (tmp & ATC_VMID0_PASID_MAPPING__PASID_MASK) == pasid)
                        mask |= 1 << vmid;
        }

        WREG32(mmVM_INVALIDATE_REQUEST, mask);
        RREG32(mmVM_INVALIDATE_RESPONSE);
```

Cierra el segundo enlace y **aclara el tercer productor** de
`INVALIDATE_REQUEST`, que el barrido ya había contado como escritor pero cuya
naturaleza no se conocía:

- Invierte `PASID → VMID`: recorre los 16 contextos, lee su LUT y OR de bits. Es
  la dirección **opuesta** a `gmc_v8_0_emit_pasid_mapping`
  (`gmc_v8_0.c:685-689`), que escribe `VMID → PASID`. El par LUT/LUT-inversa es
  lo que hace que el invalidate por PASID puedaundle todos los VMID que
  comparten PASID en **una** escritura.
- **Empieza en `vmid = 1` y excluye el 0**, igual que `amdgpu_ids.c:597`. Coincide
  con "VMID 0 es el VM del sistema" y con el hecho de que el GART no se
  invalida: la misma regla, aplicada en dos sitios distintos del driver.
- Escribe el registro y **enseguida lee `mmVM_INVALIDATE_RESPONSE`**
  (`gmc_v8_0.c:641`). Es la versión por CPU de la misma espera que el IB hace con
  `WAIT_REG_MEM`. Confirma la lectura del punto 1 anterior por un camino
  independiente: **el hardware confirma la invalidación con un segundo registro**.

**Conteo final, ya cerrado.** En GFX8 hay exactamente **tres** productores de
`INVALIDATE_REQUEST` —por VMID y por CPU (`:665`), por PASID y por CPU (`:640`),
y por VMID y por IB (`:680`)—, **una** espera de completación por IB
(`gfx_v8_0.c:6199-6207`) y **una** confirmación por CPU (`RREG32
mmVM_INVALIDATE_RESPONSE`, `:641`).

## `1003-C1` · la contradicción que esto abrió, y que se cerró aquí

`122` sostienen que los diez `WAIT_REG_MEM` del driver son flush de HDP. El
`gfx_v8_0.c:6199-6207` usa `WAIT_REG_MEM` para **esperar un registro MMIO de la
GMC**, con `OPERATION(0)` = wait y `FUNCTION(0)` = always, que no es el patrón de
un flush de HDP.

**Estado de esta contradicción: `RESOLVED`.** Se registró abierta y se cerró en
la misma sesión. Se conserva la forma con la que se formuló, porque un
discriminante bien escrito es evidencia:

```text
CONTRADICTION_ID  1003-C1                            → RESOLVED
CLAIM_A           122: los WAIT_REG_MEM son flush de HDP
CLAIM_B           1003: al menos uno espera un registro de la GMC
EVIDENCIA_A       el recuento y la clasificación de 122
EVIDENCIA_B       gfx_v8_0.c:6199-6207
DISCRIMINANTE     el valor del campo FUNCTION de cada uno de los diez WAIT_REG_MEM
                  y a qué registro apuntan. Si FUNCTION=0/"always" aparece en
                  más de uno, "todos son flush de HDP" queda refutado; si los
                  otros nueve usan FUNCTION=3/equal contra una dirección de
                  memoria, 122 sobrevive y lo que hay que corregir es su alcance.
RESULTADO         el discriminante predijo el desenlace correcto: FUNCTION(0)
                  aparece, luego 122 queda REFUTADO en su alcance
CONFOUNDERS       122 midió un anillo vivo con 10 paquetes; el driver contiene
                  3 WAIT_REG_MEM en gfx_v8_0.c y sólo 1 es hdp_flush. Muestra
                  y población no son lo mismo, y ése era el error.
```

**Consecuencia adicional: la contradicción me refutó a mí.** El mismo
discriminante echó abajo mi punto 1 —el auto-limpiado de
`INVALIDATE_REQUEST`—, porque se apoya en el mismo campo `FUNCTION`. **Un
discriminante bien aplicado no distingue entre autores: corrige a quien lo
propuso.** Por eso este hallazgo lleva dos correcciones y no una.

## Robustez entre versiones

`tools/vmid_map.py` ejecutado contra los dos corpus produce salidas que difieren
**sólo** en el recuento de ficheros y en **una** línea:

```text
7.1.3   625 ficheros .c/.h, 13208 símbolos llamados, is_kfd_vmid en línea 751
7.2.8   631 ficheros .c/.h, 13315 símbolos llamados, is_kfd_vmid en línea 766
```

Topología (`AMDGPU_NUM_VMID=16`), geometría PTBA (dos tramos, `0x54f` y `0x50e`,
header `gmc_8_1_d.h`), la partición 8/8 y el conjunto de símbolos de reserva son
idénticos. La geometría de VMID en GFX8 **no ha cambiado entre 7.1.3 y 7.2.8**.
No prueba comportamiento de hardware, pero acota la deriva de software a cero en
el alcance de este FSM.

## Por qué esto no se cierra con un finding anterior

`042` trata la política de reserva y el mapa, `064` la geometría de `CNTL`,
`115` la regla `1 << vmid`, `218` que el scheduler pide el vm-flush, `037` los
dos tramos. **Ninguno** afirma que el número no se asigna, y sin esa afirmación
el FSM del encargo no se puede construir: uno leería `ALLOCATED`/`RELEASED` y
construiría un asignador. La negación de esa premisa es lo que hace que los
otros cinco hallazgos encajen en una sola máquina de estados.

## UNLOCKS

- Un driver propio **no necesita asignador**. Necesita enlace, cuatro
  condiciones de reuse, y dos dwords por flush. Es menos código, no más.
- El punto de especialización barato es la condición (3): `last_flush->context`
  distinto de `fence_context` **sin** estar senalizado es exactamente el caso en
  que se revalida de más. Es medible en el IB —cuántos `INVALIDATE_REQUEST` se
  emiten por job— y por tanto es un cuello de botella candidato.
- La guarda de `set_vm_context_page_table_base` que hace `pr_err` en vez de
  corregir es un dato de política: el camino KFD **no puede** escribir el tramo
  equivocado, el camino DRM sí. Un driver propio tiene que elegir una de las dos
  políticas, no mezclarlas.
- La arista `RESET` da el único caso donde el driver **anula** su propia
  reutilización: tras un reset no hay reuse sin flush, aunque las cuatro
  condiciones digan que sí. Es la invariante de seguridad del ciclo.

## Evidencia y procedencia

```text
MODELO      tools/vmid_map.py 1.0.0
            sha256 db23071635a8ace8c0a8aebe699e4ac8ac537075b5bc74729fbb6d14c2b5be16
            VALIDADO: selftest 4/4 verde en esta sesión
SALIDA_A    /tmp/opencode/vmid_713.json
            sha256 6bb8a66edd2dba81fd8a131c5fbf8e265c20ba2129a23672b45eb15372618b42
SALIDA_B    /tmp/opencode/vmid_728.json
            sha256 127d1d71db503c94daa4a28d66f0df03c1ee8c84dbd4365029d001fb9bc934fc
DIFF A/B    exactamente 3 líneas: n_ficheros 625→631, n_simbolos 13208→13315,
            línea 751→766. Ningún otro campo.
LECTURAS    amdgpu_ids.c 208-638 · amdgpu_ids.h 33-82
            gmc_v8_0.c 628-648, 650-699, 725-774, 1435-1474
            amdgpu_vm.c 745-834, 868-890
            amdgpu_amdkfd_gfx_v8.c 570-592
            gfx_v8_0.c 6180-6214 · amdgpu_gmc.h 371
CIERRES     grep sobre *.c de TODO el árbol para mmVM_INVALIDATE_REQUEST y
            PAGE_TABLE_BASE_ADDR; cero escrituras a disco, cero a la GPU
VALIDACIÓN  48/48 citas file:line resuelven contra el corpus; 0 residuo CJK.
            El sha256 de este fichero no se registra aquí: un documento no puede
            contener su propio hash. Se calcula sobre el fichero, desde fuera.
ABIERTO     ninguno de este hallazgo. 1003-C1 se registró y se resolvió aquí.
            122 queda REFUTADO en su alcance; su observación de anillo sigue
            en pie, y su convención de longs no se toca.
GPU INTACTA ningún registro de MMIO leído; insmod no ejecutado
```

Sin `RUNTIME`. Todo lo que queda como `NOT_DETERMINED` requiere la
especificación primaria de GMC/VM, que no está publicada, o un discriminante de
runtime que aún no se ha diseñado.